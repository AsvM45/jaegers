"""HE-16 release smoke: scorer contract, simplex, future ticks, and 1e-8 parity.

These tests do not edit the champion or tests/test_temporal.py. Official round
points come from slot_forecasting.rounds.score_round. score_predictions remains
the separate 0-100 diagnostic.
"""
from copy import deepcopy
import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest

from research.features import FeatureComputer, validate_groups
from scripts.smoke_release import HOUSE, compare_forecasts, self_test
from slot_forecasting.rounds import score_round
from slot_forecasting.schema import CONDITIONS, Play, Query, ValidationError, index_history, probabilities
from slot_forecasting.scoring import score_predictions

HOUSE_ROOT = Path(__file__).resolve().parents[1]


def _query():
    return {
        "query_id": "q",
        "episode_id": "e1",
        "machine_id": "a",
        "machine_type": "steady",
        "signal": 0,
        "cutoff": 8,
    }


def _history():
    payouts = (0, 1, 2, 5, 20)
    return {
        ("e1", "a"): {tick: payouts[tick % 5] for tick in range(10)},
        ("e1", "b"): {tick: 1 for tick in range(10)},
    }


def test_invalid_simplex_is_rejected():
    with pytest.raises(ValidationError, match="sum to 1"):
        probabilities((0.5, 0.5, 0.5, 0.5, 0.5))
    with pytest.raises(ValidationError):
        probabilities((1.0, 0.0, 0.0, 0.0, float("nan")))


def test_future_tick_at_cutoff_is_rejected():
    with pytest.raises(ValidationError, match="Future data leak"):
        index_history([Query("q", "e", "m", "steady", 0, 4)], [Play("e", "m", 4, 0)])


def test_feature_rows_ignore_future_ticks_and_other_episodes():
    groups = ("lags", "missingness", "peers")
    query = _query()
    baseline = FeatureComputer(_history()).row(query, groups)[0]
    leaked = _history()
    leaked[("e1", "a")][8] = 20
    leaked[("e1", "b")][9] = 0
    leaked[("e2", "a")] = {tick: 20 for tick in range(12)}
    changed = FeatureComputer(leaked).row(query, groups)[0]
    np.testing.assert_array_equal(baseline, changed)


def test_missing_exact_lag_stays_missing():
    history = _history()
    del history[("e1", "a")][6]
    values, names = FeatureComputer(history).row(_query(), ("lags",))
    assert values[names.index("lags/lag2_0")] == 1
    assert values[names.index("lags/lag2_1")] == 0


def test_historical_groups_reject_query_signal():
    with pytest.raises(ValueError, match="Current signal"):
        validate_groups(("lags", "current_signal"), historical=True)


def test_diagnostic_score_is_not_the_round_point_scale():
    from slot_forecasting.schema import Target

    perfect = score_predictions({"q1": (1, 0, 0, 0, 0)}, [Target("q1", "e1", (1, 0, 0, 0, 0), 0)])
    assert perfect["score"] == 100
    assert perfect["probability_error"] == 0
    opposite = score_predictions({"q1": (1, 0, 0, 0, 0)}, [Target("q1", "e1", (0, 1, 0, 0, 0), 1)])
    assert opposite["score"] == 0
    assert opposite["probability_error"] == 2


def test_score_round_reports_main_points_and_four_conditions():
    public = HOUSE_ROOT / "public"
    result = score_round(public / "validation" / "sample_submission.csv", public)
    assert result["round"] == "main"
    assert result["max_points"] == 60
    assert 0 <= result["technical_points"] <= 60
    assert set(result["by_condition"]) == set(CONDITIONS)


def test_test_split_checker_does_not_score_hidden_answers():
    submission = HOUSE_ROOT / "public" / "test" / "sample_submission.csv"
    proc = subprocess.run(
        [sys.executable, str(HOUSE_ROOT / "check_submission.py"), str(submission), "--data", str(HOUSE_ROOT / "public"), "--split", "test"],
        cwd=HOUSE_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    assert "does not calculate your event score" in proc.stdout
    assert "Validation points" not in proc.stdout


def test_self_test_and_parity_limit(tmp_path):
    report = self_test()
    assert report["status"] == "SELF_TEST_PASSED"
    assert report["near_difference"] <= 1e-8
    left = tmp_path / "left.csv"
    right = tmp_path / "right.csv"
    from slot_forecasting.io import write_submission

    write_submission(left, {"q1": (0.4, 0.3, 0.2, 0.05, 0.05)})
    swapped = {"q1": (0.4 + 1e-7, 0.3 - 1e-7, 0.2, 0.05, 0.05)}
    write_submission(right, swapped)
    with pytest.raises(ValueError, match="Prediction mismatch"):
        compare_forecasts(left, right)
    blocked = compare_forecasts(tmp_path / "missing-a.csv", tmp_path / "missing-b.csv", tmp_path / "missing.json")
    assert blocked["status"] == "BLOCKED"


def test_smoke_command_passes_and_blocks_missing_manifest():
    assert HOUSE == HOUSE_ROOT
    passed = subprocess.run(
        [sys.executable, str(HOUSE_ROOT / "scripts" / "smoke_release.py"), "--self-test"],
        cwd=HOUSE_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert passed.returncode == 0, passed.stderr
    payload = json.loads(passed.stdout)
    assert payload["status"] == "SELF_TEST_PASSED"
    blocked = subprocess.run(
        [sys.executable, str(HOUSE_ROOT / "scripts" / "smoke_release.py"), "--compare", "no-left.csv", "no-right.csv"],
        cwd=HOUSE_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert blocked.returncode == 3
    assert json.loads(blocked.stdout)["status"] == "BLOCKED"


def test_reorder_keeps_normalized_parity(tmp_path):
    from slot_forecasting.io import write_rows
    from slot_forecasting.schema import SUBMISSION_COLUMNS

    rows = [
        {"query_id": "b", "p_0": "0.2", "p_1": "0.2", "p_2": "0.2", "p_5": "0.2", "p_20": "0.2"},
        {"query_id": "a", "p_0": "1", "p_1": "0", "p_2": "0", "p_5": "0", "p_20": "0"},
    ]
    first, second = tmp_path / "first.csv", tmp_path / "second.csv"
    write_rows(first, SUBMISSION_COLUMNS, rows)
    write_rows(second, SUBMISSION_COLUMNS, list(reversed(deepcopy(rows))))
    report = compare_forecasts(first, second)
    assert report["status"] == "PARITY_PASSED"
    assert report["max_normalized_probability_difference"] == 0
    assert report["identical_bytes"] is False
