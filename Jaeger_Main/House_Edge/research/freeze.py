"""Freeze the existing entry before experiments. Safe to bootstrap without NumPy."""
import argparse
from pathlib import Path
import shutil
from .common import ROOT, environment, file_hash, git, now, tree_hashes, write_json


def freeze(destination, data, entry=None):
    destination = Path(destination).resolve()
    data = Path(data).resolve()
    if destination.exists():
        raise FileExistsError(f"Refusing to overwrite frozen champion: {destination}")
    entry = Path(entry or ROOT / "jaegers_entry").resolve()
    source_hashes = tree_hashes(entry)
    destination.mkdir(parents=True)
    shutil.copytree(entry, destination / "entry",
                    ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    if tree_hashes(destination / "entry") != source_hashes or tree_hashes(entry) != source_hashes:
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


def verify_frozen(destination, data=None):
    import json
    destination=Path(destination).resolve()
    manifest=json.loads((destination/"manifest.json").read_text())
    if tree_hashes(destination/"entry") != manifest["source_sha256"]:
        raise ValueError("Frozen champion bytes changed")
    if data is not None and tree_hashes(data) != manifest["data_sha256"]:
        raise ValueError("Released data bytes differ from frozen manifest")
    return manifest


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", required=True)
    parser.add_argument("--data", default=str(ROOT / "public"))
    args = parser.parse_args()
    report = freeze(args.out, args.data)
    print(f"Frozen {report['head']} at {args.out}")
