"""Independently run an unchanged entry and the official organizer checker."""
import argparse
import json
from pathlib import Path
import sys
from .common import ROOT, digest, environment, file_hash, require_python, tree_hashes, write_json
from .process import run


def compare(first, second):
    from slot_forecasting.io import read_submission
    a, b = read_submission(first), read_submission(second)
    if a.keys() != b.keys():
        raise ValueError("Reproduced query IDs differ")
    difference = max(abs(x-y) for q in a for x,y in zip(a[q], b[q]))
    if difference > 1e-8:
        raise ValueError(f"Prediction mismatch: {difference}")
    return {"max_normalized_probability_difference": difference, "queries": len(a),
            "identical_bytes": Path(first).read_bytes() == Path(second).read_bytes()}


def reproduce(entry, data, out, repeat=True):
    require_python()
    entry, data, out = (Path(x).resolve() for x in (entry, data, out))
    if (entry.parent/"manifest.json").exists():
        from .freeze import verify_frozen
        verify_frozen(entry.parent,data)
    out.mkdir(parents=True, exist_ok=False)
    report = {"environment": environment(), "entry_sha256": tree_hashes(entry),
              "data_sha256": tree_hashes(data), "status": "RUNNING",
              "evaluation_source": "public_true_probability_validation",
              "validation_target_exposure": True, "processes": {}}
    write_json(out / "report.json", report)
    for split in (["validation", "validation_repeat", "test"] if repeat else ["validation", "test"]):
        actual = split.replace("_repeat", "")
        csv = out / f"{split}.csv"
        report["processes"][split] = run([sys.executable, entry / "predict.py", "--data", data,
                                          "--split", actual, "--out", csv], entry, out / split)
        report["processes"][f"{split}_check"] = run([sys.executable, ROOT / "check_submission.py", csv,
                           "--data", data, "--split", actual], ROOT, out / f"{split}_check")
        print((out / f"{split}_check/stdout.log").read_text(), flush=True)
        report[f"{split}_sha256"] = file_hash(csv)
        write_json(out / "report.json", report)
    from slot_forecasting.rounds import score_round
    report["validation"] = score_round(out / "validation.csv", data)
    if repeat:
        report["determinism"] = compare(out / "validation.csv", out / "validation_repeat.csv")
    report["status"] = "LOCAL_REPRODUCED"
    report["test_score"] = None
    report["entry_digest"] = digest(report["entry_sha256"])
    write_json(out / "report.json", report)
    return report


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--entry", required=True)
    p.add_argument("--data", default=str(ROOT / "public"))
    p.add_argument("--out", required=True)
    p.add_argument("--no-repeat", action="store_true")
    a = p.parse_args()
    result = reproduce(a.entry, a.data, a.out, not a.no_repeat)
    print(json.dumps({"status": result["status"], "points": result["validation"]["technical_points"]}))
