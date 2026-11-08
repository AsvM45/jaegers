"""Witness tests for champion historical-stacker as-of channels.

These tests pass only while the measured behavior is present. A later champion
that stops using post-tick information in a fixed historical row will fail the
corresponding assertion. That failure is the witness working, not a license to
delete the assertion and call the old path compliant.

Run from the repository root:

    python -m pytest Jaeger_Main/House_Edge/tests/test_grok_asof_evidence.py -q
"""

import importlib.util
from pathlib import Path

import pytest

TOOL = Path(__file__).resolve().parents[1] / "tools" / "grok_asof_evidence.py"
INVARIANT = (0, 4, 11, 12, 13, 14)


def _load():
    spec = importlib.util.spec_from_file_location("grok_asof_evidence", TOOL)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def witness():
    return _load().evaluate()


def _zeros(delta, indexes):
    for index in indexes:
        assert delta[index] == 0.0


def test_tool_does_not_train_or_import_the_stacker():
    text = TOOL.read_text(encoding="utf-8")
    assert "import sklearn" not in text
    assert "fit_stacker(" not in text
    assert "HistGradientBoostingClassifier" not in text
    assert "qa_causal_stacker" not in text


def test_rules_and_data_phrases_are_in_the_kit(witness):
    assert witness["rules_quote_present"]
    assert witness["data_quote_present"]
    assert witness["evidence_rating"] == "NOT_CERTIFIED"


def test_same_machine_future_changes_prior_and_fixed_row(witness):
    """The suspected prior channel is absent if this test fails."""
    item = witness["own_future_alt_persist"]
    assert item["prior_argmax"][0] != item["prior_argmax"][1]
    assert item["prior_max_abs"] > 0.5
    assert item["row_abs_delta"][5] > 0.1
    assert item["row_abs_delta"][8] > 0.4
    assert item["row_abs_delta"][1] > 1e-4
    assert item["labels"] == [0.0, 0.0]
    assert item["seen"] == [witness["expected_seen_tick20"], witness["expected_seen_tick20"]]
    assert item["gamma0_rows_equal"]
    assert item["frozen_prior_rows_equal"]
    _zeros(item["row_abs_delta"], INVARIANT)
    concern = next(row for row in witness["concerns"] if row["id"] == "same_machine_expert_prior")
    assert concern["behavior"] == "SUPPORTED"
    assert concern["rule"] == "NEEDS_ORGANIZER_RULING"


def test_prior_can_change_which_expert_is_top(witness):
    """All-loss prefix: later payouts move the selected expert's count, not its tied logit."""
    item = witness["own_future_zeros_alt"]
    assert item["prior_argmax"][0] != item["prior_argmax"][1]
    assert item["row_abs_delta"][7] > 0.01
    assert item["row_abs_delta"][5] > 0.005
    assert item["row_abs_delta"][10] > 0.1
    assert item["row_abs_delta"][2] == 0.0
    assert item["gamma0_rows_equal"]
    assert item["frozen_prior_rows_equal"]
    assert item["labels"] == [0.0, 0.0]
    _zeros(item["row_abs_delta"], INVARIANT)


def test_other_episode_future_reaches_a_fixed_row_only_through_the_prior(witness):
    item = witness["other_episode"]
    assert item["prior_max_abs"] > 0.5
    assert item["row_abs_delta"][5] > 0.05
    assert item["row_abs_delta"][8] > 0.2
    assert item["gamma0_rows_equal"]
    assert item["frozen_prior_rows_equal"]
    assert item["labels"] == [0.0, 0.0]
    assert item["seen"] == [witness["expected_seen_tick30"], witness["expected_seen_tick30"]]
    _zeros(item["row_abs_delta"], INVARIANT)
    concern = next(row for row in witness["concerns"] if row["id"] == "other_episode_expert_prior")
    assert concern["behavior"] == "SUPPORTED"
    assert concern["rule"] == "NEEDS_ORGANIZER_RULING"


def test_final_coverage_changes_early_rows_unless_regimes_match(witness):
    item = witness["coverage"]
    assert not item["rows_equal"]
    assert item["matched_rows_equal"]
    for index in (1, 2, 3, 5, 6, 7, 8, 9, 10):
        assert item["row_abs_delta"][index] > 1e-4
    _zeros(item["row_abs_delta"], (0, 4, 11, 12, 13, 14))
    assert item["seen"] == [witness["expected_seen_tick30"], witness["expected_seen_tick30"]]
    concern = next(row for row in witness["concerns"] if row["id"] == "final_history_coverage")
    assert concern["behavior"] == "SUPPORTED"


def test_query_signal_is_copied_onto_the_historical_row(witness):
    item = witness["signal"]
    assert item["only_column"] == 13
    assert item["values"] == [0.0, -1.0]
    concern = next(row for row in witness["concerns"] if row["id"] == "historical_query_signal")
    assert concern["behavior"] == "SUPPORTED"
    assert concern["rule"] == "NEEDS_ORGANIZER_RULING"


def test_asof_snapshot_ignores_same_tick_and_later_sibling_payouts(witness):
    assert witness["sibling"]["same_tick_equal"]
    assert witness["sibling"]["later_equal"]
    assert witness["cutoff_future_equal"]
    assert witness["type_columns"]["diff_columns"] == [12]
    leaked = next(row for row in witness["concerns"] if row["id"] == "snapshot_uses_later_payouts")
    hidden = next(row for row in witness["concerns"] if row["id"] == "hidden_test_label_leakage")
    cutoff = next(row for row in witness["concerns"] if row["id"] == "inference_uses_ticks_at_or_after_cutoff")
    assert leaked["behavior"] == "UNSUPPORTED"
    assert hidden["behavior"] == "UNSUPPORTED"
    assert cutoff["behavior"] == "UNSUPPORTED"


def test_every_stacker_column_has_one_measured_verdict(witness):
    indexes = [row["index"] for row in witness["columns"]]
    assert indexes == list(range(15))
    for row in witness["columns"]:
        assert row["verdict"] in {"PASS", "FAIL", "AMBIGUOUS"}
    by_name = {row["name"]: row["verdict"] for row in witness["columns"]}
    assert by_name["logit_base_rate"] == "PASS"
    assert by_name["log1p_seen"] == "PASS"
    assert by_name["type_balanced"] == "PASS"
    assert by_name["type_jackpot"] == "PASS"
    assert by_name["ones"] == "PASS"
    assert by_name["query_signal"] == "AMBIGUOUS"
    assert by_name["top_weight"] == "FAIL"
    assert by_name["log1p_top_count"] == "FAIL"
    assert by_name["logit_top_expert"] == "FAIL"
    assert by_name["logit_second_expert"] == "FAIL"
