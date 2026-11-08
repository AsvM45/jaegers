"""Freeze the existing entry before experiments. Safe to bootstrap without NumPy."""
import argparse
from pathlib import Path
import shutil
from .common import ROOT, environment, file_hash, git, now, tree_hashes, write_json


def freeze(destination, data):
    destination = Path(destination).resolve()
    data = Path(data).resolve()
    if destination.exists():
        raise FileExistsError(f"Refusing to overwrite frozen champion: {destination}")
    source_hashes = tree_hashes(ROOT / "jaegers_entry")
    destination.mkdir(parents=True)
    shutil.copytree(ROOT / "jaegers_entry", destination / "entry",
                    ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    if tree_hashes(destination / "entry") != source_hashes:
        raise RuntimeError("Frozen source differs from champion")
    report = {"created_at": now(), "head": git("rev-parse", "HEAD"),
              "status": git("status", "--short"), "source_sha256": source_hashes,
              "data_sha256": tree_hashes(data),
              "scorer_sha256": tree_hashes(ROOT / "slot_forecasting"),
              "checker_sha256": file_hash(ROOT / "check_submission.py"),
              "environment_at_freeze": environment(),
              "status_label": "SOURCE_FROZEN", "validation_target_exposure": True,
              "historical_signal_policy": "unsupported_query_signal_in_historical_rows"}
    write_json(destination / "manifest.json", report)
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", required=True)
    parser.add_argument("--data", default=str(ROOT / "public"))
    args = parser.parse_args()
    report = freeze(args.out, args.data)
    print(f"Frozen {report['head']} at {args.out}")
