"""Producer/actual dashboard-reader parity, failure retention and sealed evidence."""
import json
from pathlib import Path
import sys
import pytest
from research.common import digest, file_hash, write_json
from research.registry import Registry, export_snapshot

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from dashboard.adapter import DirectoryStore


def completed(tmp_path):
    registry = Registry(tmp_path / "runs")
    trial = registry.register("example", {"family": "frequency", "seed": 0}, {"head": "source", "data": "hash"})
    artifact = registry.start(trial)
    result = {"evaluation_source": "sampled_outcome_group_cv", "mean_brier": 0.4,
              "by_condition": {k: 0.4 for k in ("stable", "short_history", "drift", "shared_change")},
              "per_episode": {"ep": 0.4}, "episode_conditions": {"ep": "stable"},
              "calibration": [], "official_points": None}
    write_json(artifact / "result.json", result)
    (artifact / "oof.csv").write_text("fixture\n")
    registry.finish(trial, "SUCCEEDED", result, wall_seconds=1)
    return registry, trial, artifact


def test_portable_export_uses_real_dashboard_reader_without_source_artifacts(tmp_path):
    registry, trial, artifact = completed(tmp_path)
    before = file_hash(registry.path)
    out = tmp_path / "portable"
    data = export_snapshot(registry.rows(), out)
    assert data["schema_version"] == 1
    assert data["content_sha256"] == digest({k: v for k, v in data.items() if k != "content_sha256"})
    record = data["trials"][0]
    assert record["artifact_sha256"]["oof.csv"] == file_hash(artifact / "oof.csv")
    # The exported folder contains only JSON; the consumer must not need DB/model files.
    rows = DirectoryStore(out).list_trials()
    assert len(rows) == 1 and rows[0].trial_id == trial
    assert rows[0].family == "frequency" and rows[0].mean_brier == 0.4
    assert rows[0].official_points is None and rows[0].condition_losses is None
    assert rows[0].per_episode_errors == {"ep": 0.4}
    assert file_hash(registry.path) == before
    first = (out / "registry.json").read_bytes()
    export_snapshot(registry.rows(), out)
    assert (out / "registry.json").read_bytes() == first


def test_legacy_export_and_failures_remain_compatible(tmp_path):
    registry, trial, artifact = completed(tmp_path)
    failed = registry.register("failed", {"family": "frequency", "seed": 1}, {})
    registry.start(failed)
    registry.finish(failed, "FAILED", error="intentional fixture")
    rows = registry.export()
    assert json.loads((registry.root / "registry.json").read_text()) == rows
    snapshot = json.loads((registry.root / "exports/v1/registry.json").read_text())
    failure = next(row for row in snapshot["trials"] if row["trial_id"] == failed)
    assert failure["error_message"] == "intentional fixture" and failure["mean_brier"] is None


def test_sealed_artifact_mutation_is_rejected_without_overwriting_snapshot(tmp_path):
    registry, trial, artifact = completed(tmp_path)
    out = tmp_path / "export"
    export_snapshot(registry.rows(), out)
    before = (out / "registry.json").read_bytes()
    (artifact / "oof.csv").write_text("changed\n")
    with pytest.raises(ValueError, match="Sealed trial artifact bytes changed"):
        export_snapshot(registry.rows(), out)
    assert (out / "registry.json").read_bytes() == before


def test_missing_or_incompatible_metric_evidence_is_rejected(tmp_path):
    registry, trial, artifact = completed(tmp_path)
    (artifact / "result.json").unlink()
    with pytest.raises(ValueError, match="lacks result evidence"):
        export_snapshot(registry.rows(), tmp_path / "export")
    write_json(artifact / "result.json", {"evaluation_source": "public_true_probability_validation"})
    with pytest.raises(ValueError, match="explicit sampled_outcome_group_cv"):
        export_snapshot(registry.rows(), tmp_path / "export")
