"""Package a frozen candidate with exact dependencies and verify cold reproduction."""
import argparse
import json
from pathlib import Path
import shutil
import shlex
import sys
from .common import ROOT, environment, file_hash, require_python, tree_hashes, write_json
from .process import run
from .reproduce import compare


def stage(entry, data, predictions, out):
    require_python()
    entry, data, predictions, out = (Path(x).resolve() for x in (entry, data, predictions, out))
    out.mkdir(parents=True, exist_ok=False)
    source = out / "source"
    shutil.copytree(entry, source, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    for name in ("README.md", "requirements.txt"):
        target = source / name
        if target.exists():
            target.chmod(target.stat().st_mode | 0o200)
    shutil.copyfile(ROOT / "requirements-runtime.txt", source / "requirements.txt")
    declared_command = json.loads((source / "reproduce.json").read_text())["command"]
    metadata = json.loads((data / "metadata.json").read_text())
    readme = f"""# JAEGERS House Edge {metadata['round']} candidate

Season: {metadata['season_id']}. CPython 3.13; exact dependencies in requirements.txt.
Command from ZIP root: {shlex.join(declared_command)}
The command fits expert priors and a gradient-boosted win stacker on /data/train,
then forecasts /data/test using earlier same-episode history. Settings: params.json.
Stacker random_state=0, early_stopping=False. No downloads or external APIs at inference.
Dependencies are provisioned BEFORE the offline run. /submission and /data are read-only.
Budget: 2 CPUs, 16 GiB, 30 minutes; /tmp 128 MiB and /output 32 MiB.
Forecast SHA-256: {file_hash(predictions)}
Historical query-signal availability remains unresolved. Size regimes and parameter
selection used public validation targets; public scores are development-exposed.
See external audit records for measured runtime and cold reproduction status.
This package is not evidence of organizer receipt or acceptance.
"""
    (source / "README.md").write_text(readme, encoding="utf-8")
    shutil.copyfile(predictions, out / "submission.csv")
    run([sys.executable, ROOT / "check_submission.py", out / "submission.csv", "--data", data], ROOT, out / "checker")
    run([sys.executable, ROOT / "build_entry.py", "--source", source, "--out", out / "code.zip"], ROOT, out / "builder")
    from slot_forecasting.submission_contract import extract_archive
    config = extract_archive((out / "code.zip").read_bytes(), out / "extracted")
    sizes = {"csv_bytes": (out / "submission.csv").stat().st_size, "zip_bytes": (out / "code.zip").stat().st_size}
    if sizes["csv_bytes"] > 10_000_000 or sizes["zip_bytes"] > 100_000_000:
        raise ValueError("Artifact exceeds organizer upload limits")
    report = {"status": "PACKAGE_STAGED", "environment": environment(), "reproduce": config,
              "csv_sha256": file_hash(out / "submission.csv"), "zip_sha256": file_hash(out / "code.zip"),
              "source_sha256": tree_hashes(source), "sizes": sizes, "offline_verified": False,
              "historical_signal_availability": "UNRESOLVED", "validation_target_exposure": True}
    write_json(out / "release.json", report)
    return report


def verify(release, reproduced, sandbox_evidence):
    release = Path(release).resolve()
    report = json.loads((release / "release.json").read_text())
    if file_hash(release / "code.zip") != report["zip_sha256"] or file_hash(release / "submission.csv") != report["csv_sha256"]:
        raise ValueError("Release artifact bytes changed")
    if any((release / "offline").glob("attempt-*/verification_failure.json")):
        raise ValueError("Release has a recorded verification failure; preserve it and stage a separate candidate")
    parity = compare(release / "submission.csv", reproduced)
    evidence = json.loads(Path(sandbox_evidence).read_text())
    required = ("network_disabled", "submission_read_only", "data_read_only", "python_313",
                "cpu_limit_enforced", "memory_limit_enforced", "time_limit_enforced")
    if not all(evidence.get(k) is True for k in required):
        raise ValueError("Incomplete offline environment evidence")
    if evidence.get("status") != "SUCCEEDED":
        raise ValueError("Offline reproduction failed")
    report.update(status="OFFLINE_PACKAGE_VERIFIED", offline_verified=True, parity=parity,
                  offline_evidence=evidence, reproduced_sha256=file_hash(reproduced))
    write_json(release / "verification.json", report)
    return report


def record_failure(release, attempt_root, error):
    """Invalidate the latest verification pointer while preserving every attempt."""
    release, attempt_root = Path(release), Path(attempt_root)
    failure = {"status": "FAILED", "error": str(error)}
    write_json(attempt_root / "verification_failure.json", failure)
    report = json.loads((release / "release.json").read_text())
    report.update(status="OFFLINE_VERIFICATION_FAILED", offline_verified=False,
                  failed_attempt=str(attempt_root.relative_to(release)), failure=failure)
    write_json(release / "verification.json", report)
    return report


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--entry", required=True)
    p.add_argument("--data", default=str(ROOT / "public"))
    p.add_argument("--predictions", required=True)
    p.add_argument("--out", required=True)
    a = p.parse_args()
    print(json.dumps(stage(a.entry, a.data, a.predictions, a.out), indent=2))
