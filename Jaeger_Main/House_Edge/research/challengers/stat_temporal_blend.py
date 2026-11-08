"""HE-15 follow-up: champion x factorized blends (pre-registered in research/configs/stats/temporal_he15/plan_blend.json).

  size_swap     champion P(win) x the factorized model's learned size-regime HMM P(size | win)   (registry factory)
  blend_linear  p = w * champion + (1 - w) * factorized; w picked on train out-of-fold predictions only

Usage (from Jaeger_Main/House_Edge):
  python -m research.challengers.stat_temporal_blend --registry research_runs/he15_registry \
      --out research/reports/stat_temporal_blend_results.json
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

import numpy as np

HE = Path(__file__).resolve().parents[2]
if str(HE) not in sys.path:
    sys.path.insert(0, str(HE))

from research.adapters import JaegerModel, Serializable, validate_predictions  # noqa: E402
from research.challengers import stat_temporal_models as T  # noqa: E402

PUB = HE / "public"
COLS = ("p_0", "p_1", "p_2", "p_5", "p_20")
GRID = tuple(round(x, 2) for x in np.arange(0, 1.0001, 0.05))


# --------------------------------------------------------------------------- size swap (registry model)

def swap_size(champ, size):
    """champ: (N,5) champion probabilities; size: (N,4) size distribution. Keeps champion P(win)."""
    champ, size = np.asarray(champ, float), np.asarray(size, float)
    pw = 1.0 - champ[:, 0]
    p = np.column_stack([champ[:, 0], pw[:, None] * size / size.sum(1, keepdims=True)])
    return p / p.sum(1, keepdims=True)


class SizeSwapModel(Serializable):
    def __init__(self, restarts=3, iters=40):
        self.restarts, self.iters = restarts, iters

    def fit(self, queries, history, labels):
        self.champion = JaegerModel(json.loads((HE / "jaegers_entry/params.json").read_text())).fit(queries, history, labels)
        self.factorized = T.TemporalFactorized(self.restarts, self.iters).fit(queries, history, labels)
        return self

    def predict_proba(self, queries, history):
        c = self.champion.predict_proba(queries, history)
        champ = np.array([c[q["query_id"]] for q in queries])
        size = self.factorized._size_predict(self.factorized.size_params, queries, history)
        p = swap_size(champ, size)
        return validate_predictions({q["query_id"]: p[i] for i, q in enumerate(queries)}, queries)


def factory(config, cache_path=None):
    if config.get("model") != "size_swap":
        raise ValueError("stat_temporal_blend factory only builds model 'size_swap'")
    return SizeSwapModel(**config.get("params", {}))


# --------------------------------------------------------------------------- linear blend analysis

def blend(a, b, w):
    return {k: w * np.asarray(a[k]) + (1 - w) * np.asarray(b[k]) for k in a}


def read_preds(path):
    with open(path, newline="") as f:
        return {r["query_id"]: np.array([float(r[c]) for c in COLS]) for r in csv.DictReader(f)}


def _rows(path):
    with open(path, newline="") as f:
        return list(csv.DictReader(f))


def oof_brier(pred, keys, labels):
    return float(np.mean([((pred[k] - np.eye(5)[labels[k]]) ** 2).sum() for k in keys]))


def best_weight(champ, fact, keys, labels):
    scores = {w: oof_brier(blend({k: champ[k] for k in keys}, {k: fact[k] for k in keys}, w), keys, labels) for w in GRID}
    return min(scores, key=scores.get), scores


def nested_oof(champ, fact, folds_of_query, labels):
    """Choose w on 3 folds, apply to the 4th; returns nested blended predictions and the per-fold weights."""
    out, weights = {}, {}
    for f in sorted(set(folds_of_query.values())):
        train_keys = [k for k, g in folds_of_query.items() if g != f]
        hold = [k for k, g in folds_of_query.items() if g == f]
        w, _ = best_weight(champ, fact, train_keys, labels)
        weights[int(f)] = w
        out.update(blend({k: champ[k] for k in hold}, {k: fact[k] for k in hold}, w))
    return out, weights


def trial_dir(registry, family):
    for r in json.loads((Path(registry) / "registry.json").read_text()):
        cfg = r["config"] if isinstance(r["config"], dict) else json.loads(r["config"])
        if cfg["family"] == family and r["status"] == "SUCCEEDED":
            return Path(r["artifact"]), r["id"]
    raise FileNotFoundError(family)


def main():
    from research.dataset import conditions, read_labels
    from research.metrics import diagnostics, paired
    from research.challengers import stat_he09_models as SM
    from research.challengers.stat_he09_eval import Champion, episodes_A, boot_A
    from research.challengers.stat_temporal_eval import official, calib20

    ap = argparse.ArgumentParser()
    ap.add_argument("--registry", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()

    # ---- R: nested out-of-fold linear blend on train (registry OOF predictions)
    cdir, cid = trial_dir(a.registry, "jaeger")
    fdir, fid = trial_dir(a.registry, "stat_temporal_factorized")
    champ, fact = read_preds(cdir / "oof.csv"), read_preds(fdir / "oof.csv")
    folds = json.loads((cdir / "result.json").read_text())["folds"]
    qs = _rows(PUB / "train/queries.csv")
    fold_of_ep = {ep: f["fold"] for f in folds for ep in f["heldout_episodes"]}
    fold_of_q = {q["query_id"]: fold_of_ep[q["episode_id"]] for q in qs}
    labels, conds = read_labels(PUB / "train"), conditions(PUB / "train")
    w_global, grid_scores = best_weight(champ, fact, list(champ), labels)
    nested, fold_w = nested_oof(champ, fact, fold_of_q, labels)
    d_champ = diagnostics(champ, qs, labels, conds)
    d_nest = diagnostics(nested, qs, labels, conds)
    R = {"champion_trial": cid, "factorized_trial": fid, "global_oof_weight_on_champion": w_global,
         "grid_oof_brier": grid_scores, "nested_fold_weights": fold_w,
         "champion_brier": d_champ["mean_brier"], "nested_blend_brier": d_nest["mean_brier"],
         "nested_blend_vs_champion": paired(d_nest, d_champ, bootstrap=4000, seed=0)}

    # ---- A: official validation (both fit on train; w from train OOF only)
    vq = _rows(PUB / "validation/queries.csv")
    champ_v, _ = Champion().fit_predict("train", "validation")
    fq, fh, fl = SM.read_split(PUB / "train"); _, vh, _ = SM.read_split(PUB / "validation")
    fz = T.TemporalFactorized().fit(fq, fh, fl)
    fact_v = fz.predict_proba(vq, vh)
    size_v = fz._size_predict(fz.size_params, vq, vh)
    cm = np.array([champ_v[q["query_id"]] for q in vq])
    swap_v = {q["query_id"]: p for q, p in zip(vq, swap_size(cm, size_v))}
    blend_v = blend({k: np.asarray(champ_v[k]) for k in champ_v}, fact_v, w_global)
    eA_c, ref, _ = episodes_A(champ_v)
    A = {}
    for name, pred in (("champion", champ_v), ("blend_linear", blend_v), ("size_swap", swap_v)):
        pts, ratios = official(pred, vq)
        A[name] = {"official_points": pts, "loss_ratios": ratios, "calibration_20x": calib20(pred)}
        if name != "champion":
            A[name]["vs_champion_points"] = boot_A(eA_c, episodes_A(pred)[0], ref)
    res = {"R_nested_oof": R, "A_official_validation": A,
           "notes": "R = sampled-label Brier on 4 grouped train folds (not points); A = official points, development-exposed for anything containing the champion."}
    Path(a.out).write_text(json.dumps(res, indent=1, default=float))
    print(json.dumps({"w_global": w_global, "nested_fold_weights": fold_w, "R": R["nested_blend_vs_champion"],
                      "A": {k: {"pts": round(v["official_points"], 4), "vs": v.get("vs_champion_points")} for k, v in A.items()}}, indent=1, default=float))


if __name__ == "__main__":
    main()
