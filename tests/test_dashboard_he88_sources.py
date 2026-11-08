"""Synthetic fixtures for the limited, source-checked external summary contract."""
from copy import deepcopy
import json
from pathlib import Path

import pytest

from dashboard.he88_research_sources import load_he87_summary, summary_figures
from Jaeger_Main.House_Edge.research.common import digest, file_hash, write_json
from Jaeger_Main.House_Edge.tests.test_chat_he88_evidence import trial_fixture, write_export
from Jaeger_Main.House_Edge.research.reporting.chat_he88_report import export_report


def external_fixture(tmp_path):
    root = tmp_path/"fixture_house"
    for name in ("features", "models", "experiment"):
        path = root/f"research/challengers/grok_he87_{name}.py"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("# synthetic test fixture only\n")
    train = root/"public/train"
    train.mkdir(parents=True)
    (train/"queries.csv").write_text("query_id,episode_id\n"+"".join(f"q{i}_{m},ep{i}\n" for i in range(8) for m in range(8)))
    for name in ("history.csv", "labels.csv", "conditions.csv"):
        (train/name).write_text("synthetic fixture only\n")
    protocol = root/"research/configs/grok_he87_protocol.json"
    write_json(protocol, {"fixture_only": True})
    trial = trial_fixture()
    result = trial["result"]
    folds = {f"ep{i}": i % 2 for i in range(8)}
    report = {"status": "MEASURED_NOT_PROMOTED", "evaluation_source": "sampled_outcome_group_cv", "official_points": None,
              "public_validation_peeks": 0, "validation_files_opened": False,
              "source_sha256": {n: file_hash(root/f"research/challengers/grok_he87_{n}.py") for n in ("features", "models", "experiment")},
              "data_sha256": {p.name: file_hash(p) for p in train.iterdir()}, "protocol_sha256": file_hash(protocol),
              "folds": folds, "fold_manifest_sha256": digest(folds), "fold_count": 2, "n_episodes": 8, "n_queries": 64,
              "candidates": [dict({k: v for k, v in result.items() if k != "per_query"}, name="synthetic_candidate", fit_seconds=None)]}
    path = root/"research/reports/grok_he87_results.json"
    write_json(path, report)
    return path, report


def test_external_adapter_checks_source_data_episodes_and_preserves_unknowns(tmp_path):
    path, _ = external_fixture(tmp_path)
    before = path.read_bytes()
    summary = load_he87_summary(path)
    assert summary["rows"][0]["reported_mean_brier"] == pytest.approx(.8)
    assert summary["rows"][0]["reported_fit_seconds"] is None
    assert summary["rows"][0]["official_points"] is None
    assert summary["warnings"]
    assert path.read_bytes() == before
    assert set(summary_figures(summary)) == {"reported_errors", "reported_conditions"}
    path.parents[1].joinpath("challengers/grok_he87_models.py").write_text("changed fixture source")
    with pytest.raises(ValueError, match="source hashes"):
        load_he87_summary(path)


@pytest.mark.parametrize("change", [lambda r: r.update(official_points=60), lambda r: r.update(evaluation_source="public_validation"),
    lambda r: r.update(source_sha256=[]), lambda r: r.update(data_sha256={}),
    lambda r: r.update(protocol_sha256="incorrect"), lambda r: r.update(n_queries=999),
    lambda r: r["candidates"][0].update(mean_brier=0), lambda r: r["candidates"][0].update(by_condition={}),
    lambda r: r["candidates"].append(deepcopy(r["candidates"][0]))])
def test_invalid_external_evidence_is_rejected(tmp_path, change):
    path, report = external_fixture(tmp_path)
    change(report)
    write_json(path, report)
    with pytest.raises(ValueError):
        load_he87_summary(path)


def test_external_summary_is_separate_in_offline_report_exports(tmp_path):
    external, _ = external_fixture(tmp_path)
    registry = tmp_path/"registry.json"
    write_export(registry, [trial_fixture()])
    out = tmp_path/"report"
    report = export_report(registry, out, external_report=external)
    assert len(report["trials"]) == 1 and len(report["external_summary"]["rows"]) == 1
    assert "external_reader" in report["reporting_source_sha256"]
    assert (out/"external_summary.csv").is_file() and (out/"external_summary.json").is_file()
    assert "per-query probabilities unavailable" in (out/"external_summary.csv").read_text()


def test_external_summary_can_render_when_registry_is_missing(tmp_path, monkeypatch):
    from streamlit.testing.v1 import AppTest
    source, _ = external_fixture(tmp_path)
    monkeypatch.setenv("JAEGERS_HE88_REGISTRY", str(tmp_path/"no_registry.json"))
    root = Path(__file__).resolve().parents[1]
    app = AppTest.from_file(str(root/"dashboard/he88_app.py")).run(timeout=30)
    next(field for field in app.text_input if field.label == "HE-87 aggregate report (optional)").set_value(str(source))
    app.run(timeout=30)
    assert not app.exception
    assert not app.error
    assert len(app.dataframe) == 1
