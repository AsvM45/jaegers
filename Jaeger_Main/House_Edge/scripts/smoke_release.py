"""Local HE-16 smoke gate. Does not fit the champion or upload anything.

From Jaeger_Main/House_Edge:

    python scripts/smoke_release.py --self-test
    python scripts/smoke_release.py --compare frozen.csv reproduced.csv --manifest release.json

--self-test rejects an invalid five-class simplex, rejects a history tick at or
after cutoff, and checks normalized forecast parity at 1e-8. GitHub Actions runs
this same command. Cold ZIP reproduction remains issue #4; if the frozen CSV or
manifest is absent this command exits 3 with status BLOCKED.
"""
import argparse
import hashlib
import json
import sys
import tempfile
from pathlib import Path

HOUSE = Path(__file__).resolve().parents[1]
if str(HOUSE) not in sys.path:
    sys.path.insert(0, str(HOUSE))

PARITY_LIMIT = 1e-8


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_forecast(path, rows):
    from slot_forecasting.io import write_submission
    write_submission(path, rows)


def self_test():
    from slot_forecasting.schema import Play, Query, ValidationError, index_history, probabilities

    try:
        probabilities((0.5, 0.5, 0.5, 0.5, 0.5), "invalid simplex")
    except ValidationError:
        simplex = "rejected"
    else:
        raise SystemExit("SELF_TEST_FAILED: invalid simplex was accepted")

    try:
        index_history(
            [Query("q", "e", "m", "steady", 0, 4)],
            [Play("e", "m", 4, 0)],
        )
    except ValidationError as exc:
        if "Future" not in str(exc):
            raise SystemExit(f"SELF_TEST_FAILED: unexpected future-tick error: {exc}") from exc
        future = "rejected"
    else:
        raise SystemExit("SELF_TEST_FAILED: future tick at cutoff was accepted")

    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary)
        left, right, far = root / "left.csv", root / "near.csv", root / "far.csv"
        base = {"q1": (0.4, 0.3, 0.2, 0.05, 0.05)}
        near = {"q1": (0.4 + 1e-9, 0.3 - 1e-9, 0.2, 0.05, 0.05)}
        over = {"q1": (0.4 + 1e-7, 0.3 - 1e-7, 0.2, 0.05, 0.05)}
        write_forecast(left, base)
        write_forecast(right, near)
        write_forecast(far, over)
        near_report = compare_forecasts(left, right)
        try:
            compare_forecasts(left, far)
        except ValueError as exc:
            if "Prediction mismatch" not in str(exc):
                raise
            far_rejected = True
        else:
            raise SystemExit("SELF_TEST_FAILED: difference above 1e-8 was accepted")
    return {
        "status": "SELF_TEST_PASSED",
        "invalid_simplex": simplex,
        "future_tick": future,
        "parity_limit": PARITY_LIMIT,
        "near_difference": near_report["max_normalized_probability_difference"],
        "over_limit_rejected": far_rejected,
        "champion_fit": False,
    }


def compare_forecasts(left, right, manifest=None):
    left, right = Path(left), Path(right)
    missing = [str(path) for path in (left, right) if not path.is_file()]
    if manifest is not None and not Path(manifest).is_file():
        missing.append(str(manifest))
    if missing:
        return {"status": "BLOCKED", "missing": missing, "parity_limit": PARITY_LIMIT}
    from research.reproduce import compare

    report = compare(left, right)
    report.update(
        status="PARITY_PASSED",
        parity_limit=PARITY_LIMIT,
        left_sha256=sha256(left),
        right_sha256=sha256(right),
    )
    if manifest is not None:
        report["manifest_sha256"] = sha256(manifest)
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-test", action="store_true", help="Run the offline synthetic gate")
    parser.add_argument("--compare", nargs=2, metavar=("LEFT", "RIGHT"), help="Normalized parity of two forecast CSVs")
    parser.add_argument("--manifest", type=Path, help="Optional frozen manifest recorded by SHA-256 only")
    args = parser.parse_args(argv)
    if args.self_test:
        print(json.dumps(self_test(), sort_keys=True))
        return 0
    if args.compare:
        report = compare_forecasts(args.compare[0], args.compare[1], args.manifest)
        print(json.dumps(report, sort_keys=True))
        if report["status"] == "BLOCKED":
            return 3
        return 0
    parser.print_help()
    return 2


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ValueError as exc:
        print(json.dumps({"status": "PARITY_FAILED", "error": str(exc), "parity_limit": PARITY_LIMIT}))
        raise SystemExit(2) from exc
