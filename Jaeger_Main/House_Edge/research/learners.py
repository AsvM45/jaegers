"""Standard library model families on shared past-only features, with local artifacts."""
import json
from pathlib import Path
import numpy as np
from .common import digest
from .features import FeatureComputer, feature_columns, validate_groups
from .models import Serializable, validate_predictions


def estimator(family, params, seed):
    if family == "logistic":
        from sklearn.pipeline import make_pipeline
        from sklearn.preprocessing import StandardScaler
        from sklearn.linear_model import LogisticRegression
        return make_pipeline(StandardScaler(), LogisticRegression(C=params.get("C", 1.), max_iter=400,
                                   random_state=seed, solver="lbfgs"))
    if family in ("random_forest", "extra_trees"):
        from sklearn.ensemble import RandomForestClassifier, ExtraTreesClassifier
        cls = RandomForestClassifier if family == "random_forest" else ExtraTreesClassifier
        return cls(n_estimators=params.get("trees", 120), min_samples_leaf=params.get("leaf", 10),
                   max_depth=params.get("depth"), max_features=params.get("max_features", .7),
                   n_jobs=1, random_state=seed)
    if family == "hist_boost":
        from sklearn.ensemble import HistGradientBoostingClassifier
        return HistGradientBoostingClassifier(max_iter=params.get("iters", 100),
            learning_rate=params.get("lr", .05), max_leaf_nodes=params.get("leaves", 15),
            l2_regularization=params.get("l2", 1.), early_stopping=False, random_state=seed)
    if family == "naive_bayes":
        from sklearn.naive_bayes import GaussianNB
        return GaussianNB(var_smoothing=params.get("smoothing", 1e-3))
    if family == "lda":
        from sklearn.discriminant_analysis import LinearDiscriminantAnalysis
        return LinearDiscriminantAnalysis(solver="lsqr", shrinkage=params.get("shrinkage", "auto"))
    if family == "xgboost":
        from xgboost import XGBClassifier
        return XGBClassifier(n_estimators=params.get("iters", 100), max_depth=params.get("depth", 3),
            learning_rate=params.get("lr", .05), reg_lambda=params.get("l2", 5.), n_jobs=1,
            tree_method="hist", objective="multi:softprob", num_class=5, random_state=seed)
    if family == "lightgbm":
        from lightgbm import LGBMClassifier
        return LGBMClassifier(n_estimators=params.get("iters", 100), num_leaves=params.get("leaves", 15),
            learning_rate=params.get("lr", .05), reg_lambda=params.get("l2", 5.), n_jobs=1,
            random_state=seed, verbosity=-1, deterministic=True, force_col_wise=True)
    raise ValueError(f"Unknown model family: {family}")


class HistoricalModel(Serializable):
    def __init__(self, family, groups, params=None, cache=None, supervision="historical", seed=0, calibration=None):
        validate_groups(groups, historical=supervision != "query")
        self.family, self.groups, self.params = family, list(groups), dict(params or {})
        self.cache, self.supervision, self.seed, self.calibration = cache, supervision, seed, calibration
        self.temperature = 1.

    def fit(self, queries, history, labels):
        fit_episodes = {q["episode_id"] for q in queries}
        if self.supervision == "query":
            computer = FeatureComputer(history)
            rows = [computer.row(q, self.groups) for q in queries]
            X = np.array([r[0] for r in rows]); self.columns = rows[0][1]
            y = np.array([labels[q["query_id"]] for q in queries])
            episodes = np.array([q["episode_id"] for q in queries])
            query_rows = np.ones(len(y), dtype=bool)
        else:
            path = Path(self.cache)
            meta = json.loads((path / "complete.json").read_text())
            from .common import file_hash
            if file_hash(path / "train.npz") != meta["archive_sha256"]:
                raise ValueError("Feature cache bytes changed")
            columns = feature_columns(meta["columns"], self.groups)
            self.columns = [meta["columns"][i] for i in columns]
            with np.load(path / "train.npz", allow_pickle=False) as archive:
                keep = np.isin(archive["episode"], sorted(fit_episodes))
                X = archive["X"][keep][:, columns]; y = archive["y"][keep]
                episodes = archive["episode"][keep]; query_rows = archive["kind"][keep] == "query"
        if not set(episodes).issubset(fit_episodes):
            raise ValueError("Held-out episode entered fitting data")
        self.estimator = estimator(self.family, self.params, self.seed)
        train = np.ones(len(y), dtype=bool)
        if self.calibration:
            ordered = sorted(fit_episodes, key=digest)
            calibration_episodes = ordered[::5]
            train = ~np.isin(episodes, calibration_episodes)
            cal = ~train & query_rows
            if not cal.any():
                raise ValueError("Empty episode-held-out calibration partition")
        # Equal total fitting weight per episode, independent of historical row count.
        unique, counts = np.unique(episodes[train], return_counts=True)
        weights = {ep: len(y[train])/(len(unique)*n) for ep,n in zip(unique, counts)}
        w = np.array([weights[ep] for ep in episodes[train]])
        if self.family == "logistic":
            self.estimator.fit(X[train], y[train], logisticregression__sample_weight=w)
        elif self.family == "lda":
            self.estimator.fit(X[train], y[train])
        else:
            self.estimator.fit(X[train], y[train], sample_weight=w)
        if self.calibration:
            predictions = self._probabilities(X[cal])
            onehot = np.eye(5)[y[cal]]
            options = (.5, .75, 1., 1.5, 2.)
            self.temperature = min(options, key=lambda t: np.mean(np.sum((self._temper(predictions,t)-onehot)**2, axis=1)))
        self.fit_episodes = sorted(fit_episodes)
        return self

    @staticmethod
    def _temper(p, temperature):
        z = np.log(np.clip(p, 1e-9, 1))/temperature
        z -= z.max(axis=1, keepdims=True)
        e = np.exp(z)
        return e/e.sum(axis=1, keepdims=True)

    def _probabilities(self, X):
        p = self.estimator.predict_proba(X)
        result = np.zeros((len(X), 5))
        result[:, np.asarray(self.estimator.classes_, dtype=int)] = p
        return result

    def predict_proba(self, queries, history):
        computer = FeatureComputer(history)
        rows = [computer.row(q, self.groups) for q in queries]
        if rows[0][1] != self.columns:
            raise ValueError("Training and inference feature schema differ")
        p = self._temper(self._probabilities(np.array([r[0] for r in rows])), self.temperature)
        return validate_predictions({q["query_id"]: row for q,row in zip(queries,p)}, queries)

    def importance(self):
        model = self.estimator
        if hasattr(model, "steps"):
            model = model.steps[-1][1]
        if hasattr(model, "feature_importances_"):
            values = model.feature_importances_
            kind = "impurity_importance_not_causal"
        elif hasattr(model, "coef_"):
            values = np.mean(np.abs(model.coef_), axis=0)
            kind = "absolute_coefficient_not_causal"
        else:
            return {"kind": "unavailable", "values": {}}
        return {"kind": kind, "values": {name:float(v) for name,v in zip(self.columns,values)}}
