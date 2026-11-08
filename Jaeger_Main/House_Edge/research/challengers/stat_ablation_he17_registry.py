"""HE-17 -> #8 registry bridge for code-level ablations of the champion.

Parameter-only ablations run through the registry's own `family: jaeger` path. Variants that change
module-level structure (expert list, size regimes) or the stacker's training (dropped column, shuffled
labels) cannot be expressed as params, so this factory rebuilds them.

Self-contained on purpose: registry workers run from a frozen source snapshot that contains only
`research/*.py`, `research/{challengers,models,features,extensions}/`, `jaegers_entry/` and
`slot_forecasting/` (see `research/sweep.py:snapshot_source`). So the variant's `change` travels inside the
trial config, and tests check it is identical to the pre-registered
`research/configs/stats/ablations/he17_ablations.json`.

Trial config:
    {"family": "he17_single_lag_only", "factory": "research.challengers.stat_ablation_he17_registry:factory",
     "variant": "single_lag_only", "change": {"experts": "single_lag_only"}, "supervision": "query"}

Each fit loads a FRESH copy of jaegers_entry/jaeger_model.py, so patches never reach the shared champion
module. Note: the shared worker derives `validation_target_exposure` / `historical_signal_policy` from
`family == "jaeger"`, so for these champion-derived variants both result.json flags are wrong; the correct
values come from `exposure_flags()` and are recorded in the report.
"""
from __future__ import annotations

import csv
import importlib.util
import json
import tempfile
from pathlib import Path

import numpy as np

from research.adapters import Serializable, validate_predictions

HE = Path(__file__).resolve().parents[2]
CHAMPION = HE / "jaegers_entry" / "jaeger_model.py"
PARAMS = HE / "jaegers_entry" / "params.json"
CODE_LEVEL = ("nosig", "single_lag_only", "binary_categories_only", "train_size_regimes",
              "control_shuffled_stack_labels")
KNOWN_KEYS = {"params", "drop_stack_cols", "experts", "size_regimes", "shuffle_stack_labels"}


def fresh_core(tag):
    spec = importlib.util.spec_from_file_location(f"he17_reg_core_{tag}", CHAMPION)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def resolve_params(base, change):
    p = dict(base)
    for k, v in change.get("params", {}).items():
        p[k] = p[v[1:]] if isinstance(v, str) and v.startswith("=") else v
    return p


def apply_module_changes(core, change):
    if change.get("experts") == "single_lag_only":
        core.EXPERTS = [e for e in core.EXPERTS if e[1] == 0]
    elif change.get("experts") == "binary_only":
        core.EXPERTS = [e for e in core.EXPERTS if e[2] in (1, 2)]
    elif change.get("experts"):
        raise ValueError(change["experts"])
    for ty, arr in change.get("size_regimes", {}).items():
        a = np.asarray(arr, dtype=float)
        core.SIZE_REGIMES[ty] = a / a.sum(axis=1, keepdims=True)
    return core


def exposure_flags(change):
    """Correct provenance for a champion-derived variant (the worker's family-based flags are not)."""
    keeps_signal = 13 not in change.get("drop_stack_cols", []) and change.get("params", {}).get("stack", True)
    return {"validation_target_exposure": True,  # params were tuned on validation
            "size_regimes_from_validation": "size_regimes" not in change,
            "historical_signal_policy": "unsupported_copied_signal" if keeps_signal else "omitted"}


def _write_split(folder, queries, history):
    cols = ("query_id", "episode_id", "machine_id", "machine_type", "signal", "cutoff")
    with (folder / "queries.csv").open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols); w.writeheader(); w.writerows({k: q[k] for k in cols} for q in queries)
    with (folder / "history.csv").open("w", newline="") as f:
        w = csv.writer(f); w.writerow(("episode_id", "machine_id", "tick", "payout"))
        for ep, m in sorted({(q["episode_id"], q["machine_id"]) for q in queries}):
            for t, v in sorted(history[(ep, m)].items()):
                w.writerow((ep, m, t, v))


class HE17AblationModel(Serializable):
    def __init__(self, name, change):
        if name not in CODE_LEVEL:
            raise ValueError(f"Unknown code-level HE-17 variant {name!r}")
        if set(change) - KNOWN_KEYS:
            raise ValueError(f"Unknown change keys {sorted(set(change) - KNOWN_KEYS)}")
        self.name, self.change = name, change
        self.params = resolve_params(json.loads(PARAMS.read_text()), change)

    def _core(self):
        return apply_module_changes(fresh_core(self.name), self.change)

    def fit(self, queries, history, labels=None):
        core = self._core()
        with tempfile.TemporaryDirectory(prefix="he17-fit-") as d:
            _write_split(Path(d), queries, history)
            self.prior = core.learn_expert_prior(d, self.params)
        self.cols, self.model = None, None
        if self.params.get("stack"):
            from sklearn.ensemble import HistGradientBoostingClassifier
            _, X, y = core.predict(queries, history, self.params, expert_logprior=self.prior, collect=True)
            drop = set(self.change.get("drop_stack_cols", []))
            self.cols = [i for i in range(1, X.shape[1]) if i not in drop]
            if self.change.get("shuffle_stack_labels"):
                y = np.random.default_rng(0).permutation(y)
            p = self.params
            self.model = HistGradientBoostingClassifier(
                learning_rate=p.get("stack_lr", 0.05), max_leaf_nodes=p.get("stack_leaves", 15),
                max_iter=p.get("stack_iters", 300), l2_regularization=p.get("stack_l2", 1.0),
                early_stopping=False, random_state=0).fit(X[:, self.cols], y)
        return self

    def _stack(self, F):
        pr = np.clip(self.model.predict_proba(F[:, self.cols])[:, 1], 1e-6, 1 - 1e-6)
        return np.log(pr / (1 - pr))

    def predict_proba(self, queries, history):
        stack = self._stack if self.model is not None else None
        pred = self._core().predict(queries, history, self.params, expert_logprior=self.prior, stack_w=stack)
        return validate_predictions(pred, queries)


def factory(config, cache_path=None):
    return HE17AblationModel(config["variant"], config["change"])
