"""HE-09 paired evaluation of the statistical challengers vs the champion and lane A's FrequencyModel.

Usage (from Jaeger_Main/House_Edge):
  python -m research.challengers.stat_he09_eval --out research/reports/stat_he09_results.json
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
from pathlib import Path

import numpy as np

HE = Path(__file__).resolve().parents[2]
if str(HE) not in sys.path:
    sys.path.insert(0, str(HE))

from research.challengers import stat_he09_models as SM  # noqa: E402

PUB = HE / "public"
COLS = ("p_0", "p_1", "p_2", "p_5", "p_20")
CHAMPION = HE / "jaegers_entry/jaeger_model.py"
PARAMS = HE / "jaegers_entry/params.json"
PLAN = HE / "research/configs/stats/he09/plan.json"


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def lf_sha(path):
    return hashlib.sha256(Path(path).read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def rows(path):
    with open(path, newline="") as f:
        return list(csv.DictReader(f))


# --------------------------------------------------------------------------- model wrappers (fit split -> predict split)

class Champion:
    name = "champion"

    def fit_predict(self, fit_split, pred_split):
        spec = importlib.util.spec_from_file_location("he09_champion", CHAMPION)
        core = importlib.util.module_from_spec(spec); spec.loader.exec_module(core)
        params = json.loads(PARAMS.read_text())
        prior = core.learn_expert_prior(str(PUB / fit_split), params)
        stack = core.fit_stacker(str(PUB / fit_split), params, prior)
        q, h = core.read_split(str(PUB / pred_split))
        return core.predict(q, h, params, expert_logprior=prior, stack_w=stack), {}


class FrequencyBaseline:
    name = "frequency_model_lane_a"

    def fit_predict(self, fit_split, pred_split):
        from research.models import FrequencyModel  # lane A, read-only
        fq, fh, _ = SM.read_split(PUB / fit_split)
        pq, ph, _ = SM.read_split(PUB / pred_split)
        model = FrequencyModel().fit(fq, fh)
        return model.predict_proba(pq, ph), {"strength": model.strength, "decay": model.decay}


class Candidate:
    def __init__(self, name):
        self.name = name

    def fit_predict(self, fit_split, pred_split):
        fq, fh, fl = SM.read_split(PUB / fit_split)
        pq, ph, _ = SM.read_split(PUB / pred_split)
        model = SM.MODELS[self.name]().fit(fq, fh, fl)
        chosen = {k: getattr(model, k) for k in ("decay", "s_short", "s_long", "a", "beta", "s") if hasattr(model, k)}
        return model.predict(pq, ph), chosen


# --------------------------------------------------------------------------- metrics

def official(pred):
    from slot_forecasting.rounds import score_round
    qs = rows(PUB / "validation/queries.csv")
    with tempfile.TemporaryDirectory() as d:
        path = Path(d) / "val.csv"
        with path.open("w", newline="") as f:
            w = csv.writer(f); w.writerow(("query_id",) + COLS)
            for q in qs:
                w.writerow([q["query_id"]] + [repr(float(x)) for x in pred[q["query_id"]]])
        r = score_round(path, PUB)
    return r["technical_points"], {c: v["loss_ratio"] for c, v in r["by_condition"].items()}


def episodes_A(pred):
    tg = {r["query_id"]: (r["episode_id"], np.array([float(r[c]) for c in COLS])) for r in rows(PUB / "validation/targets.csv")}
    ref = {r["query_id"]: np.array([float(r[c]) for c in COLS]) for r in rows(PUB / "validation/reference.csv")}
    cond = {r["query_id"]: r["condition"] for r in rows(PUB / "validation/conditions.csv")}
    m, b = defaultdict(list), defaultdict(list)
    p20, t20 = [], []
    for qid, (ep, t) in tg.items():
        p = np.asarray(pred[qid], dtype=float)
        m[f"{cond[qid]}|{ep}"].append(float(((p - t) ** 2).sum())); b[f"{cond[qid]}|{ep}"].append(float(((ref[qid] - t) ** 2).sum()))
        p20.append(p[4]); t20.append(t[4])
    return ({k: float(np.mean(v)) for k, v in m.items()}, {k: float(np.mean(v)) for k, v in b.items()},
            {"mean_pred_p20": float(np.mean(p20)), "mean_target_p20": float(np.mean(t20)),
             "corr_p20": float(np.corrcoef(p20, t20)[0, 1])})


def episodes_B(pred):
    lab = {r["query_id"]: int(r["outcome"]) for r in rows(PUB / "train/labels.csv")}
    cond = {r["query_id"]: r["condition"] for r in rows(PUB / "train/conditions.csv")}
    out = defaultdict(list); c20 = []
    for q in rows(PUB / "train/queries.csv"):
        y = np.zeros(5); y[SM.PAYOUTS.index(lab[q["query_id"]])] = 1
        p = np.asarray(pred[q["query_id"]], dtype=float)
        out[f"{cond[q['query_id']]}|{q['episode_id']}"].append(float(((p - y) ** 2).sum()))
        c20.append((p[4] - y[4]) ** 2)
    return {k: float(np.mean(v)) for k, v in out.items()}, {"brier_20x_component": float(np.mean(c20))}


def _by_cond(ep):
    by = defaultdict(list)
    for k in ep:
        by[k.split("|")[0]].append(k)
    return {c: sorted(v) for c, v in sorted(by.items())}


def _points(m, ref, groups):
    return 60 / (1 + np.mean([np.mean([m[k] for k in ks]) / np.mean([ref[k] for k in ks]) for ks in groups]))


def boot_A(base, var, ref, reps=4000, seed=0):
    by = _by_cond(base); cs = list(by); rng = np.random.default_rng(seed)
    d = np.empty(reps)
    for i in range(reps):
        ks = [[by[c][j] for j in rng.integers(0, len(by[c]), len(by[c]))] for c in cs]
        d[i] = _points(var, ref, ks) - _points(base, ref, ks)
    return {"diff": float(_points(var, ref, by.values()) - _points(base, ref, by.values())),
            "ci95": [float(np.quantile(d, .025)), float(np.quantile(d, .975))]}


def boot_B(base, var, reps=4000, seed=0):
    by = _by_cond(base); cs = list(by); rng = np.random.default_rng(seed)
    stat = lambda ks: float(np.mean([np.mean([var[k] - base[k] for k in kk]) for kk in ks]))
    d = np.array([stat([[by[c][j] for j in rng.integers(0, len(by[c]), len(by[c]))] for c in cs]) for _ in range(reps)])
    return {"diff": stat(by.values()), "ci95": [float(np.quantile(d, .025)), float(np.quantile(d, .975))]}


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--out", required=True); a = ap.parse_args()
    runners = [Champion(), FrequencyBaseline()] + [Candidate(n) for n in SM.MODELS]
    res = {}
    for r in runners:
        t0 = time.time()
        pa, chosen_a = r.fit_predict("train", "validation")
        tA = time.time() - t0
        pts, ratios = official(pa)
        epA, refA, x20 = episodes_A(pa)
        pb, chosen_b = r.fit_predict("validation", "train")
        epB, b20 = episodes_B(pb)
        res[r.name] = {"A_points": pts, "A_ratios": ratios, "A_episode": epA, "A_ref": refA, "A_20x": x20,
                       "B_episode": epB, "B_20x": b20, "chosen_on_train": chosen_a, "chosen_on_validation": chosen_b,
                       "seconds_fit_predict_A": round(tA, 1), "seconds_total": round(time.time() - t0, 1)}
        bm = np.mean([np.mean([epB[k] for k in ks]) for ks in _by_cond(epB).values()])
        res[r.name]["B_mean_brier"] = float(bm)
        print(f"{r.name:24s} A={pts:.4f} B={bm:.5f} t={res[r.name]['seconds_total']}s chosen={chosen_a}", flush=True)
    comps = {}
    for base in ("champion", "frequency_model_lane_a"):
        for n, r in res.items():
            if n != base:
                comps[f"{n}_vs_{base}"] = {"A": boot_A(res[base]["A_episode"], r["A_episode"], res["champion"]["A_ref"]),
                                           "B": boot_B(res[base]["B_episode"], r["B_episode"])}
    payload = {"plan_sha256": sha(PLAN), "champion_sha256_lf": lf_sha(CHAMPION), "params_sha256_lf": lf_sha(PARAMS),
               "models_sha256_lf": lf_sha(SM.__file__), "eval_sha256_lf": lf_sha(__file__),
               "environment": {"python": sys.version.split()[0], "numpy": np.__version__},
               "results": res, "paired": comps}
    for n in list(res):
        res[n].pop("A_ref") if n != "champion" else None
    Path(a.out).write_text(json.dumps(payload, separators=(",", ":")))
    for k, v in comps.items():
        print(f"{k:50s} A {v['A']['diff']:+.3f} [{v['A']['ci95'][0]:+.3f},{v['A']['ci95'][1]:+.3f}] "
              f"B {v['B']['diff']:+.5f} [{v['B']['ci95'][0]:+.5f},{v['B']['ci95'][1]:+.5f}]")


if __name__ == "__main__":
    main()
