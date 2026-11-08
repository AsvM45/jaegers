"""HE-03 follow-up evaluation A: fit on TRAIN, official score on VALIDATION, paired vs the champion.

Usage (from Jaeger_Main/House_Edge):
  python -m research.challengers.qa_causal_stacker_eval --out research/audits/qa_causal_stacker_official.json
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

HE = Path(__file__).resolve().parents[2]
if str(HE) not in sys.path:
    sys.path.insert(0, str(HE))

from research.adapters import JaegerModel  # noqa: E402
from research.challengers import qa_causal_stacker as Q  # noqa: E402
from research.challengers.stat_he09_eval import boot_A, episodes_A  # noqa: E402
from research.challengers.stat_he09_models import read_split  # noqa: E402
PUB = HE / "public"
COLS = ("p_0", "p_1", "p_2", "p_5", "p_20")


def official(pred, queries):
    """Official organizer score on public validation (slot_forecasting.rounds.score_round)."""
    import csv
    import tempfile
    from slot_forecasting.rounds import score_round
    with tempfile.TemporaryDirectory() as d:
        path = Path(d) / "val.csv"
        with path.open("w", newline="") as f:
            w = csv.writer(f); w.writerow(("query_id",) + COLS)
            for q in queries:
                w.writerow([q["query_id"]] + [repr(float(x)) for x in pred[q["query_id"]]])
        r = score_round(path, PUB)
    return r["technical_points"], {c: v["loss_ratio"] for c, v in r["by_condition"].items()}


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--out", required=True); a = ap.parse_args()
    fq, fh, fl = read_split(PUB / "train")
    vq, vh, _ = read_split(PUB / "validation")
    res, eps = {}, {}
    makers = {"champion": lambda: JaegerModel(json.loads(Q.PARAMS.read_text()))}
    makers.update({n: (lambda n=n: Q.factory({"variant": n})) for n in ("causal_all", "causal_all_nohead", "regime_only", "prior_only")})
    for name, make in makers.items():
        t0 = time.time()
        pred = make().fit(fq, fh, fl).predict_proba(vq, vh)
        pts, ratios = official(pred, vq)
        eps[name], ref, _ = episodes_A(pred)
        res[name] = {"official_points": pts, "loss_ratios": ratios, "seconds": round(time.time() - t0, 1)}
        if name != "champion":
            res[name]["vs_champion_points"] = boot_A(eps["champion"], eps[name], ref)
        print(f"{name:20s} {pts:.4f}  {res[name].get('vs_champion_points', '')}  {res[name]['seconds']}s", flush=True)
    Path(a.out).write_text(json.dumps(res, indent=1, default=float))


if __name__ == "__main__":
    main()
