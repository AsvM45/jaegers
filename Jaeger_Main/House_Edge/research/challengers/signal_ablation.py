"""HE-03: matched ablation of the historical-signal issue in the JAEGERS stacker.

Read-only use of jaegers_entry/jaeger_model.py (champion source is imported, never edited).

Variants (identical code path; only the listed change differs):
  champion  - params.json as shipped, stacker uses all 14 features (col 13 = query-time signal)
  nosig     - stacker refit without col 13 (signal); everything else identical
  causal    - nosig + lam_short=lam, prior_short=prior (teammate's JaegerModel(causal=True) recipe)
  nostack   - stacker disabled (context: how much the stacker adds at all)

Directions:
  A  fit prior+stacker on TRAIN, score VALIDATION true targets with the official
     slot_forecasting.rounds.score_round, plus a paired per-episode bootstrap.
  B  fit prior+stacker on VALIDATION, score TRAIN observed next-payout labels (Brier,
     five-class one-hot). Independent of validation target vectors except SIZE_REGIMES.

Usage (from Jaeger_Main/House_Edge):
  python -m research.challengers.signal_ablation --out research/audits/historical_signal_results.json
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
import tempfile
import time
from collections import defaultdict
from pathlib import Path

import numpy as np

HE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(HE))
sys.path.insert(0, str(HE / "jaegers_entry"))
import jaeger_model as jm  # noqa: E402
from slot_forecasting.rounds import score_round  # noqa: E402

PUB = HE / "public"
COLS = ("p_0", "p_1", "p_2", "p_5", "p_20")
SIGNAL_COL = 13


def variant_params(base, name):
    p = dict(base)
    if name == "causal":
        p["lam_short"], p["prior_short"] = p["lam"], p["prior"]
    if name == "nostack":
        p["stack"] = False
    return p


def fit(split, base, name):
    p = variant_params(base, name)
    prior = jm.learn_expert_prior(str(PUB / split), p)
    if not p.get("stack"):
        return p, prior, None
    from sklearn.ensemble import HistGradientBoostingClassifier
    q, h = jm.read_split(str(PUB / split))
    _, X, y = jm.predict(q, h, p, expert_logprior=prior, collect=True)
    cols = [i for i in range(1, X.shape[1]) if not (name in ("nosig", "causal") and i == SIGNAL_COL)]
    model = HistGradientBoostingClassifier(
        learning_rate=p.get("stack_lr", 0.05), max_leaf_nodes=p.get("stack_leaves", 15),
        max_iter=p.get("stack_iters", 300), l2_regularization=p.get("stack_l2", 1.0),
        early_stopping=False, random_state=0).fit(X[:, cols], y)

    def log_odds(F):
        pr = np.clip(model.predict_proba(F[:, cols])[:, 1], 1e-6, 1 - 1e-6)
        return np.log(pr / (1 - pr))
    return p, prior, log_odds


def predict(split, fitted):
    p, prior, stack = fitted
    q, h = jm.read_split(str(PUB / split))
    return q, jm.predict(q, h, p, expert_logprior=prior, stack_w=stack)


def read_rows(path):
    with open(path, newline="") as f:
        return list(csv.DictReader(f))


def official_points(queries, pred):
    with tempfile.TemporaryDirectory() as d:
        path = Path(d) / "val.csv"
        with path.open("w", newline="") as f:
            w = csv.writer(f)
            w.writerow(("query_id",) + COLS)
            for qq in queries:
                w.writerow([qq["query_id"]] + [repr(float(x)) for x in pred[qq["query_id"]]])
        r = score_round(path, PUB)
    return r["technical_points"], {c: v["loss_ratio"] for c, v in r["by_condition"].items()}


def episode_losses_validation(pred):
    tg = {r["query_id"]: (r["episode_id"], np.array([float(r[c]) for c in COLS])) for r in read_rows(PUB / "validation/targets.csv")}
    ref = {r["query_id"]: np.array([float(r[c]) for c in COLS]) for r in read_rows(PUB / "validation/reference.csv")}
    cond = {r["query_id"]: r["condition"] for r in read_rows(PUB / "validation/conditions.csv")}
    model, base = defaultdict(list), defaultdict(list)
    for qid, (ep, t) in tg.items():
        model[(cond[qid], ep)].append(((np.array(pred[qid]) - t) ** 2).sum())
        base[(cond[qid], ep)].append(((ref[qid] - t) ** 2).sum())
    return {k: np.mean(v) for k, v in model.items()}, {k: np.mean(v) for k, v in base.items()}


def points_from(model_ep, ref_ep, keys_by_cond):
    ratios = [np.mean([model_ep[k] for k in ks]) / np.mean([ref_ep[k] for k in ks]) for ks in keys_by_cond]
    return 60 / (1 + np.mean(ratios))


def paired_bootstrap_validation(a, b, ref, reps=4000, seed=0):
    rng = np.random.default_rng(seed)
    by_c = defaultdict(list)
    for k in a:
        by_c[k[0]].append(k)
    conds = sorted(by_c)
    diffs = []
    for _ in range(reps):
        ks = [[by_c[c][i] for i in rng.integers(0, len(by_c[c]), len(by_c[c]))] for c in conds]
        diffs.append(points_from(b, ref, ks) - points_from(a, ref, ks))
    diffs = np.array(diffs)
    point = points_from(b, ref, [by_c[c] for c in conds]) - points_from(a, ref, [by_c[c] for c in conds])
    return {"diff_points": float(point), "ci95": [float(np.quantile(diffs, .025)), float(np.quantile(diffs, .975))],
            "p_le_0": float((diffs <= 0).mean())}


def episode_brier_train(queries, pred):
    lab = {r["query_id"]: int(r["outcome"]) for r in read_rows(PUB / "train/labels.csv")}
    cond = {r["query_id"]: r["condition"] for r in read_rows(PUB / "train/conditions.csv")}
    out = defaultdict(list)
    for qq in queries:
        y = np.zeros(5); y[jm.PAYOUTS.index(lab[qq["query_id"]])] = 1
        out[(cond[qq["query_id"]], qq["episode_id"])].append(((np.array(pred[qq["query_id"]]) - y) ** 2).sum())
    return {k: float(np.mean(v)) for k, v in out.items()}


def paired_bootstrap_brier(a, b, reps=4000, seed=0):
    """b - a in condition-averaged Brier (negative = b better)."""
    rng = np.random.default_rng(seed)
    by_c = defaultdict(list)
    for k in a:
        by_c[k[0]].append(k)
    conds = sorted(by_c)
    stat = lambda ks: np.mean([np.mean([b[k] - a[k] for k in kk]) for kk in ks])
    diffs = np.array([stat([[by_c[c][i] for i in rng.integers(0, len(by_c[c]), len(by_c[c]))] for c in conds]) for _ in range(reps)])
    return {"diff_brier": float(stat([by_c[c] for c in conds])),
            "ci95": [float(np.quantile(diffs, .025)), float(np.quantile(diffs, .975))],
            "p_ge_0": float((diffs >= 0).mean()),
            "by_condition": {c: float(np.mean([b[k] - a[k] for k in by_c[c]])) for c in conds}}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--variants", default="champion,nosig,causal,nostack")
    args = ap.parse_args()
    base = json.loads((HE / "jaegers_entry/params.json").read_text())
    names = args.variants.split(",")
    res = {"source_sha256": {}, "A_train_to_validation": {}, "B_validation_to_train": {}}
    import hashlib
    for f in ("jaegers_entry/jaeger_model.py", "jaegers_entry/params.json"):
        res["source_sha256"][f] = hashlib.sha256((HE / f).read_bytes()).hexdigest()
    epA, epB = {}, {}
    for n in names:
        t0 = time.time()
        q, pred = predict("validation", fit("train", base, n))
        pts, ratios = official_points(q, pred)
        epA[n], refA = episode_losses_validation(pred)
        qt, predt = predict("train", fit("validation", base, n))
        epB[n] = episode_brier_train(qt, predt)
        res["A_train_to_validation"][n] = {"official_points": pts, "loss_ratios": ratios}
        res["B_validation_to_train"][n] = {"mean_condition_brier": float(np.mean([np.mean([v for k, v in epB[n].items() if k[0] == c]) for c in sorted({k[0] for k in epB[n]})]))}
        print(f"{n}: A points={pts:.6f}  B brier={res['B_validation_to_train'][n]['mean_condition_brier']:.6f}  ({time.time()-t0:.0f}s)", flush=True)
    for n in names[1:]:
        res["A_train_to_validation"][n]["paired_vs_champion"] = paired_bootstrap_validation(epA["champion"], epA[n], refA)
        res["B_validation_to_train"][n]["paired_vs_champion"] = paired_bootstrap_brier(epB["champion"], epB[n])
    Path(args.out).write_text(json.dumps(res, indent=2))
    print(json.dumps({k: v for k, v in res.items() if k != "source_sha256"}, indent=1))


if __name__ == "__main__":
    main()
