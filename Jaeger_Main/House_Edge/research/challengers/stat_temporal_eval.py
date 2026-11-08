"""HE-15 evaluation A: fit on TRAIN, official score on VALIDATION, plus 20x calibration and runtime.

Usage (from Jaeger_Main/House_Edge):
  python -m research.challengers.stat_temporal_eval --out research/reports/stat_temporal_official.json
The champion's official score is development-exposed; the temporal candidates use no validation information.
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
import tempfile
import time
from pathlib import Path

import numpy as np

HE = Path(__file__).resolve().parents[2]
if str(HE) not in sys.path:
    sys.path.insert(0, str(HE))

from research.challengers import stat_he09_models as SM  # noqa: E402
from research.challengers import stat_temporal_models as T  # noqa: E402

PUB = HE / "public"
COLS = ("p_0", "p_1", "p_2", "p_5", "p_20")


def official(pred, queries):
    from slot_forecasting.rounds import score_round
    with tempfile.TemporaryDirectory() as d:
        path = Path(d) / "val.csv"
        with path.open("w", newline="") as f:
            w = csv.writer(f); w.writerow(("query_id",) + COLS)
            for q in queries:
                w.writerow([q["query_id"]] + [repr(float(x)) for x in pred[q["query_id"]]])
        r = score_round(path, PUB)
    return r["technical_points"], {c: v["loss_ratio"] for c, v in r["by_condition"].items()}


def calib20(pred):
    with open(PUB / "validation/targets.csv", newline="") as f:
        tg = {r["query_id"]: float(r["p_20"]) for r in csv.DictReader(f)}
    p = np.array([pred[k][4] for k in tg]); t = np.array(list(tg.values()))
    return {"mean_pred_p20": float(p.mean()), "mean_target_p20": float(t.mean()), "corr_p20": float(np.corrcoef(p, t)[0, 1])}


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--out", required=True); a = ap.parse_args()
    fq, fh, fl = SM.read_split(PUB / "train")
    vq, vh, _ = SM.read_split(PUB / "validation")
    models = {"stat_markov (HE-09)": lambda: SM.MarkovMixture(), **{n: c for n, c in T.MODELS.items()}}
    res = {}
    for name, make in models.items():
        t0 = time.time()
        m = make().fit(fq, fh, fl)
        pred = m.predict_proba(vq, vh) if hasattr(m, "predict_proba") else m.predict(vq, vh)
        pts, ratios = official(pred, vq)
        res[name] = {"official_points": pts, "loss_ratios": ratios, "calibration_20x": calib20(pred),
                     "seconds": round(time.time() - t0, 1), "K": getattr(m, "K", None),
                     "diagnostics": getattr(m, "diagnostics", None)}
        print(f"{name:26s} {pts:.4f}  K={res[name]['K']}  20x={res[name]['calibration_20x']}  {res[name]['seconds']}s", flush=True)
    Path(a.out).write_text(json.dumps(res, indent=1, default=float))


if __name__ == "__main__":
    main()
