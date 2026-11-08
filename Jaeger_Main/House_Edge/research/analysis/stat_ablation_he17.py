"""HE-17: paired component ablations of the JAEGERS champion (read-only use of the champion).

Variants and hypotheses are pre-registered in research/configs/stats/ablations/he17_ablations.json.
Every variant loads a FRESH copy of jaegers_entry/jaeger_model.py from disk, so module-level
monkeypatches (expert list, size regimes) never leak between variants or into the champion.

Usage (from Jaeger_Main/House_Edge):
  python -m research.analysis.stat_ablation_he17 --out research/reports/stat_ablation_he17_results.json [--workers 3]
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import json
import sys
import tempfile
import time
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np

HE = Path(__file__).resolve().parents[2]
if str(HE) not in sys.path:
    sys.path.insert(0, str(HE))

PUB = HE / "public"
CONFIG = HE / "research/configs/stats/ablations/he17_ablations.json"
CHAMPION = HE / "jaegers_entry/jaeger_model.py"
PARAMS = HE / "jaegers_entry/params.json"
COLS = ("p_0", "p_1", "p_2", "p_5", "p_20")
PAYOUTS = (0, 1, 2, 5, 20)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def trial_id(variant):
    ident = {"variant": variant, "champion": sha(CHAMPION), "params": sha(PARAMS), "config": sha(CONFIG),
             "harness": sha(__file__)}
    return hashlib.sha256(json.dumps(ident, sort_keys=True).encode()).hexdigest()[:16]


def fresh_core(tag):
    spec = importlib.util.spec_from_file_location(f"he17_core_{tag}", CHAMPION)
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
    if "size_regimes" in change:
        for ty, arr in change["size_regimes"].items():
            a = np.asarray(arr, dtype=float)
            core.SIZE_REGIMES[ty] = a / a.sum(axis=1, keepdims=True)
    return core


def fit(core, split, params, change):
    prior = core.learn_expert_prior(str(PUB / split), params)
    if not params.get("stack"):
        return prior, None
    from sklearn.ensemble import HistGradientBoostingClassifier
    q, h = core.read_split(str(PUB / split))
    _, X, y = core.predict(q, h, params, expert_logprior=prior, collect=True)
    cols = [i for i in range(1, X.shape[1]) if i not in set(change.get("drop_stack_cols", []))]
    if change.get("shuffle_stack_labels"):
        y = np.random.default_rng(0).permutation(y)
    model = HistGradientBoostingClassifier(
        learning_rate=params.get("stack_lr", 0.05), max_leaf_nodes=params.get("stack_leaves", 15),
        max_iter=params.get("stack_iters", 300), l2_regularization=params.get("stack_l2", 1.0),
        early_stopping=False, random_state=0).fit(X[:, cols], y)

    def log_odds(F):
        pr = np.clip(model.predict_proba(F[:, cols])[:, 1], 1e-6, 1 - 1e-6)
        return np.log(pr / (1 - pr))
    return prior, log_odds


def rows(path):
    with open(path, newline="") as f:
        return list(csv.DictReader(f))


def official(queries, pred):
    from slot_forecasting.rounds import score_round
    with tempfile.TemporaryDirectory() as d:
        path = Path(d) / "val.csv"
        with path.open("w", newline="") as f:
            w = csv.writer(f); w.writerow(("query_id",) + COLS)
            for q in queries:
                w.writerow([q["query_id"]] + [repr(float(x)) for x in pred[q["query_id"]]])
        r = score_round(path, PUB)
    return r["technical_points"], {c: v["loss_ratio"] for c, v in r["by_condition"].items()}


def episode_losses_A(pred):
    tg = {r["query_id"]: (r["episode_id"], np.array([float(r[c]) for c in COLS])) for r in rows(PUB / "validation/targets.csv")}
    ref = {r["query_id"]: np.array([float(r[c]) for c in COLS]) for r in rows(PUB / "validation/reference.csv")}
    cond = {r["query_id"]: r["condition"] for r in rows(PUB / "validation/conditions.csv")}
    m, b = defaultdict(list), defaultdict(list)
    for qid, (ep, t) in tg.items():
        m[f"{cond[qid]}|{ep}"].append(float(((np.array(pred[qid]) - t) ** 2).sum()))
        b[f"{cond[qid]}|{ep}"].append(float(((ref[qid] - t) ** 2).sum()))
    return {k: float(np.mean(v)) for k, v in m.items()}, {k: float(np.mean(v)) for k, v in b.items()}


def episode_brier_B(queries, pred):
    lab = {r["query_id"]: int(r["outcome"]) for r in rows(PUB / "train/labels.csv")}
    cond = {r["query_id"]: r["condition"] for r in rows(PUB / "train/conditions.csv")}
    out = defaultdict(list)
    for q in queries:
        y = np.zeros(5); y[PAYOUTS.index(lab[q["query_id"]])] = 1
        out[f"{cond[q['query_id']]}|{q['episode_id']}"].append(float(((np.array(pred[q["query_id"]]) - y) ** 2).sum()))
    return {k: float(np.mean(v)) for k, v in out.items()}


def run_variant(variant, base_params):
    t0 = time.time()
    change = variant["change"]
    params = resolve_params(base_params, change)
    core = apply_module_changes(fresh_core(variant["name"]), change)
    prior, stack = fit(core, "train", params, change)
    qv, hv = core.read_split(str(PUB / "validation"))
    pv = core.predict(qv, hv, params, expert_logprior=prior, stack_w=stack)
    points, ratios = official(qv, pv)
    epA, refA = episode_losses_A(pv)
    tA = time.time() - t0
    prior_b, stack_b = fit(core, "validation", params, change)
    qt, ht = core.read_split(str(PUB / "train"))
    pt = core.predict(qt, ht, params, expert_logprior=prior_b, stack_w=stack_b)
    epB = episode_brier_B(qt, pt)
    return {"name": variant["name"], "trial_id": trial_id(variant), "n_experts": len(core.EXPERTS),
            "A_points": points, "A_ratios": ratios, "A_episode": epA, "A_ref": refA,
            "B_episode": epB, "seconds_A": round(tA, 1), "seconds_total": round(time.time() - t0, 1)}


def _conds(ep):
    by = defaultdict(list)
    for k in ep:
        by[k.split("|")[0]].append(k)
    return {c: sorted(v) for c, v in sorted(by.items())}


def points_from(model, ref, groups):
    return 60 / (1 + np.mean([np.mean([model[k] for k in ks]) / np.mean([ref[k] for k in ks]) for ks in groups]))


def bootstrap_A(base, var, ref, reps=4000, seed=0):
    by = _conds(base); conds = list(by); rng = np.random.default_rng(seed)
    point = points_from(var, ref, by.values()) - points_from(base, ref, by.values())
    d = np.empty(reps)
    for i in range(reps):
        ks = [[by[c][j] for j in rng.integers(0, len(by[c]), len(by[c]))] for c in conds]
        d[i] = points_from(var, ref, ks) - points_from(base, ref, ks)
    return {"diff": float(point), "ci95": [float(np.quantile(d, .025)), float(np.quantile(d, .975))]}


def bootstrap_B(base, var, reps=4000, seed=0):
    by = _conds(base); conds = list(by); rng = np.random.default_rng(seed)
    stat = lambda ks: float(np.mean([np.mean([var[k] - base[k] for k in kk]) for kk in ks]))
    d = np.array([stat([[by[c][j] for j in rng.integers(0, len(by[c]), len(by[c]))] for c in conds]) for _ in range(reps)])
    return {"diff": stat(by.values()), "ci95": [float(np.quantile(d, .025)), float(np.quantile(d, .975))],
            "by_condition": {c: float(np.mean([var[k] - base[k] for k in by[c]])) for c in conds}}


def summarize(results, config):
    base = next(r for r in results if r["name"] == config["baseline"])
    out = []
    for r in results:
        row = {k: r[k] for k in ("name", "trial_id", "n_experts", "A_points", "A_ratios", "seconds_total")}
        row["B_mean_brier"] = float(np.mean([np.mean([r["B_episode"][k] for k in ks]) for ks in _conds(r["B_episode"]).values()]))
        if r is not base:
            row["A_vs_champion"] = bootstrap_A(base["A_episode"], r["A_episode"], base["A_ref"])
            row["B_vs_champion"] = bootstrap_B(base["B_episode"], r["B_episode"])
            a, b = row["A_vs_champion"], row["B_vs_champion"]
            a_sig = a["ci95"][0] > 0 or a["ci95"][1] < 0
            same_dir = (a["diff"] > 0) == (b["diff"] < 0)  # +points and -Brier both mean better
            row["supported"] = bool(a_sig and same_dir)
            row["direction"] = "better" if a["diff"] > 0 else "worse"
        out.append(row)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--workers", type=int, default=3)
    ap.add_argument("--only", default="")
    a = ap.parse_args()
    config = json.loads(CONFIG.read_text())
    base_params = json.loads(PARAMS.read_text())
    variants = [v for v in config["variants"] if not a.only or v["name"] in a.only.split(",") or v["name"] == config["baseline"]]
    t0 = time.time()
    with ProcessPoolExecutor(max_workers=a.workers) as ex:
        results = list(ex.map(run_variant, variants, [base_params] * len(variants)))
    summary = summarize(results, config)
    payload = {"config_sha256": sha(CONFIG), "champion_sha256": sha(CHAMPION), "params_sha256": sha(PARAMS),
               "harness_sha256": sha(__file__), "wall_seconds": round(time.time() - t0, 1),
               "environment": {"python": sys.version.split()[0], "numpy": np.__version__,
                               "sklearn": __import__("sklearn").__version__},
               "summary": summary, "raw": results}
    Path(a.out).write_text(json.dumps(payload, indent=1))
    for r in summary:
        extra = ""
        if "A_vs_champion" in r:
            A, B = r["A_vs_champion"], r["B_vs_champion"]
            extra = (f" | A {A['diff']:+.3f} [{A['ci95'][0]:+.3f},{A['ci95'][1]:+.3f}]"
                     f" | B {B['diff']:+.5f} [{B['ci95'][0]:+.5f},{B['ci95'][1]:+.5f}] | supported={r['supported']}")
        print(f"{r['name']:30s} A={r['A_points']:.4f} B={r['B_mean_brier']:.5f} t={r['seconds_total']}s{extra}", flush=True)


if __name__ == "__main__":
    main()
