"""Quantitative chart/report acceptance with clearly synthetic test-only records."""
from copy import deepcopy
import json
from pathlib import Path

import pytest

from dashboard.he88_views import build_figures, filter_trials, pareto_ids
from Jaeger_Main.House_Edge.tests.test_chat_he88_evidence import trial_fixture, write_export
from Jaeger_Main.House_Edge.research.reporting.chat_he88_report import export_report


def test_filters_keep_missing_failure_scores_and_exact_provenance():
    base, other = trial_fixture(), trial_fixture("fixture_b")
    other["hyperparameters"]["groups"].append("lags")
    failed = dict(deepcopy(base), trial_id="failed", status="FAILED", mean_brier=None, result={})
    assert len(filter_trials([base, other, failed], {"status": ["SUCCEEDED"]})) == 2
    assert filter_trials([base, other], required_groups=["lags"]) == [other]
    assert filter_trials([base, other], parameter_text='"C": 0.1') == [base, other]
    assert filter_trials([base, other], {"family": ["unknown"]}) == []


def test_pareto_never_combines_mismatched_contexts():
    base = trial_fixture(wall_seconds=2)
    better = trial_fixture("fixture_b", (.25, .25, .25, .125, .125), wall_seconds=1)
    assert pareto_ids([base, better]) == {"fixture_b"}
    changed = deepcopy(better)
    changed["identity"]["season_id"] = "other-season"
    with pytest.raises(ValueError, match="context"):
        pareto_ids([base, changed])


def test_all_supported_charts_have_actual_traces_and_uncertainty():
    base, other = trial_fixture(), trial_fixture("fixture_b", (.25, .25, .25, .125, .125))
    other["family"] = "logistic"
    other["hyperparameters"]["groups"].append("lags")
    figures, blockers = build_figures([base, other], baseline_id=base["trial_id"], bootstrap=100)
    assert not blockers
    assert set(figures) == {"status", "trajectory", "pareto", "conditions", "ablations", "parameters", "paired_ci",
                            "calibration", "probability_diagnostics", "condition_residuals"}
    assert all(len(fig.data) for fig in figures.values())
    ci = figures["paired_ci"].data[0]
    assert ci.x[0] == pytest.approx(-.01875)
    assert len(ci.error_x.array) == len(ci.error_x.arrayminus) == 1
    assert len(figures["probability_diagnostics"].data[0].z) == 5
    assert len(figures["calibration"].data) == 6
    assert "Trial cost" in figures["pareto"].layout.title.text


def test_empty_and_failed_selection_show_no_score_charts():
    figures, blockers = build_figures([])
    assert set(figures) == {"status"}
    assert blockers
    failed = dict(trial_fixture(), status="CANCELLED", mean_brier=None, result={})
    figures, _ = build_figures([failed])
    assert set(figures) == {"status"}


def test_offline_report_exports_full_provenance_and_preserves_prior_output(tmp_path):
    source, out = tmp_path/"registry.json", tmp_path/"report"
    base, other = trial_fixture(), trial_fixture("fixture_b", (.25, .25, .25, .125, .125))
    write_export(source, [base, other])
    before = source.read_bytes()
    report = export_report(source, out, baseline_id=base["trial_id"])
    assert source.read_bytes() == before
    assert report["comparisons"][0]["mean_delta_brier"] == pytest.approx(-.01875)
    assert sorted(p.name for p in out.iterdir()) == ["comparison.csv", "comparison.json", "index.html", "report.md"]
    page = (out/"index.html").read_text(encoding="utf-8")
    assert '<script src="' not in page  # no external script dependency in the export
    assert "Mean assigned probability" in page
    assert "hidden test quality is unavailable" in page
    payload = json.loads((out/"comparison.json").read_text())
    assert payload["official_points"] is None
    assert payload["trials"][0]["data_sha256"]
    with pytest.raises(FileExistsError):
        export_report(source, out)


def test_report_facets_contexts_and_labels_comparison_blockers(tmp_path):
    base, other = trial_fixture(), trial_fixture("fixture_b")
    other["identity"]["season_id"] = "another-season"
    source = tmp_path/"registry.json"
    write_export(source, [base, other])
    report = export_report(source, tmp_path/"report", baseline_id=base["trial_id"])
    assert "blocker" in report["comparisons"][0]


def test_streamlit_startup_and_real_contract_rendering(tmp_path, monkeypatch):
    from streamlit.testing.v1 import AppTest
    root = Path(__file__).resolve().parents[1]
    source = tmp_path/"registry.json"
    monkeypatch.setenv("JAEGERS_HE88_REGISTRY", str(source))
    empty = AppTest.from_file(str(root/"dashboard/he88_app.py")).run(timeout=30)
    assert not empty.exception
    assert len(empty.info) == 1
    write_export(source, [trial_fixture(), trial_fixture("fixture_b", (.25, .25, .25, .125, .125))])
    rendered = AppTest.from_file(str(root/"dashboard/he88_app.py")).run(timeout=30)
    assert not rendered.exception
    assert len(rendered.metric) == 3
    assert len(rendered.tabs) == 5
