"""JAEGERS House Edge entry: python predict.py --data /data --out /output/submission.csv

No training step: the forecaster is an online mixture of lag-context experts run
over each machine's own history (see jaeger_model.py). Deterministic, no randomness.
"""
import argparse
import csv
import json
from pathlib import Path

from jaeger_model import predict, read_split

HERE = Path(__file__).resolve().parent


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True, help="round public folder containing test/")
    ap.add_argument("--out", required=True)
    ap.add_argument("--split", default="test")
    a = ap.parse_args()
    params = json.loads((HERE / "params.json").read_text())
    queries, hist = read_split(str(Path(a.data) / a.split))
    preds = predict(queries, hist, params)
    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["query_id", "p_0", "p_1", "p_2", "p_5", "p_20"])
        for q in queries:
            w.writerow([q["query_id"]] + [repr(float(x)) for x in preds[q["query_id"]]])


if __name__ == "__main__":
    main()
