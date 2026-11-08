"""Adapters around existing forecasting code; all outputs are five-class probabilities."""
import importlib.util
from pathlib import Path
import tempfile
import csv
import numpy as np
import joblib
from .common import ROOT, file_hash

PAYOUTS = (0, 1, 2, 5, 20)
_CORES = {}


def core_module(source=None):
    source = Path(source or ROOT / "jaegers_entry/jaeger_model.py").resolve()
    key = file_hash(source)
    if key not in _CORES:
        spec = importlib.util.spec_from_file_location("jaeger_core_" + key[:12], source)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        _CORES[key] = module
    return _CORES[key]


def validate_predictions(predictions, queries):
    expected = [q["query_id"] for q in queries]
    if len(set(expected)) != len(expected) or set(predictions) != set(expected):
        raise ValueError("Prediction IDs differ from query IDs")
    for key, value in predictions.items():
        a = np.asarray(value, dtype=float)
        if a.shape != (5,) or not np.isfinite(a).all() or (a < 0).any() or (a > 1).any() or abs(a.sum()-1) > 1e-6:
            raise ValueError(f"Invalid five-category probability vector: {key}")
    return predictions


class Serializable:
    def save(self, path):
        # Trusted local model artifacts only; never load untrusted joblib files.
        joblib.dump(self, path)

    @staticmethod
    def load(path):
        return joblib.load(path)


class WinStack:
    def __init__(self, estimator, columns):
        self.estimator, self.columns = estimator, columns

    def __call__(self, features):
        p = np.clip(self.estimator.predict_proba(features[:, self.columns])[:, 1], 1e-6, 1-1e-6)
        return np.log(p / (1-p))


class JaegerModel(Serializable):
    def __init__(self, params, causal=False, source=None):
        self.params = dict(params)
        self.causal = causal
        self.source = str(Path(source or ROOT / "jaegers_entry/jaeger_model.py").resolve())
        if causal:
            # Predeclared fixed smoothing: total end-of-history coverage cannot decide
            # the forgetting/prior regime of an earlier pseudo-example.
            self.params["lam_short"] = self.params["lam"]
            self.params["prior_short"] = self.params["prior"]

    def fit(self, queries, history, labels=None):
        core = core_module(self.source)
        # Reuse the original prior fitter through a temporary fold-local split.
        with tempfile.TemporaryDirectory(prefix="jaeger-fit-") as directory:
            folder = Path(directory)
            columns = ("query_id", "episode_id", "machine_id", "machine_type", "signal", "cutoff")
            with (folder / "queries.csv").open("w", newline="") as f:
                w = csv.DictWriter(f, fieldnames=columns)
                w.writeheader(); w.writerows(queries)
            keys = {(q["episode_id"], q["machine_id"]) for q in queries}
            with (folder / "history.csv").open("w", newline="") as f:
                w = csv.writer(f); w.writerow(("episode_id", "machine_id", "tick", "payout"))
                for ep, machine in sorted(keys):
                    for tick, payout in sorted(history[(ep, machine)].items()):
                        w.writerow((ep, machine, tick, payout))
            self.prior = core.learn_expert_prior(str(folder), self.params)
        self.stack = None
        if self.params.get("stack"):
            from sklearn.ensemble import HistGradientBoostingClassifier
            _, X, y = core.predict(queries, history, self.params, expert_logprior=self.prior, collect=True)
            columns = [i for i in range(1, X.shape[1]) if not (self.causal and i == 13)]
            estimator = HistGradientBoostingClassifier(
                learning_rate=self.params.get("stack_lr", .05), max_leaf_nodes=self.params.get("stack_leaves", 15),
                max_iter=self.params.get("stack_iters", 300), l2_regularization=self.params.get("stack_l2", 1.),
                early_stopping=False, random_state=0).fit(X[:, columns], y)
            self.stack = WinStack(estimator, columns)
        return self

    def predict_proba(self, queries, history):
        prediction = core_module(self.source).predict(queries, history, self.params,
                            expert_logprior=self.prior, stack_w=self.stack)
        return validate_predictions(prediction, queries)


class FrequencyModel(Serializable):
    """Hierarchical Dirichlet / recency estimator, learned only on fit episodes."""
    def __init__(self, strength=20., decay=1., peer=0., window=None):
        self.strength, self.decay, self.peer, self.window = strength, decay, peer, window

    def fit(self, queries, history, labels=None):
        self.priors = {}
        for ty in ("steady", "balanced", "jackpot"):
            counts = np.ones(5)
            for q in queries:
                if q["machine_type"] == ty:
                    for t, y in history[(q["episode_id"], q["machine_id"])].items():
                        if t < int(q["cutoff"]):
                            counts[PAYOUTS.index(y)] += 1
            self.priors[ty] = counts / counts.sum()
        return self

    def predict_proba(self, queries, history):
        result = {}
        for q in queries:
            cutoff = int(q["cutoff"])
            counts = self.strength * self.priors[q["machine_type"]].copy()
            for (ep, machine), rows in history.items():
                if ep != q["episode_id"]:
                    continue
                weight = 1. if machine == q["machine_id"] else self.peer
                if weight == 0:
                    continue
                for t, y in rows.items():
                    if t < cutoff and (self.window is None or t >= cutoff-self.window):
                        counts[PAYOUTS.index(y)] += weight * self.decay ** (cutoff-1-t)
            result[q["query_id"]] = counts / counts.sum()
        return validate_predictions(result, queries)
