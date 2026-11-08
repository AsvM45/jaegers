"""Synthetic contract fixtures only; these are not real competition measurements."""
from copy import deepcopy
import json
from pathlib import Path
import sqlite3
import sys

import pytest

REPO = Path(__file__).resolve().parents[3]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from Jaeger_Main.House_Edge.research.analysis.chat_he88_evidence import (
    audit_registry, calibration, comparison, context_key, load_export, trial_rows, validated_result,
)
from Jaeger_Main.House_Edge.research.common import digest, file_hash, write_json
from Jaeger_Main.House_Edge.research.metrics import diagnostics
from Jaeger_Main.House_Edge.research.registry import Registry


def trial_fixture(trial_id="fixture_a", probabilities=(.2,)*5, wall_seconds=1.):
    """Mimics a real-export schema for tests; no fixture is auto-loaded by the UI."""
    queries, labels, conditions, predictions = [], {}, {}, {}
    condition_names = ("stable", "short_history", "drift", "shared_change")
    manifest = {f"ep{i}": i % 2 for i in range(8)}
    for i in range(8):
        for m in range(8):
            qid = f"q{i}_{m}"
            queries.append({"query_id": qid, "episode_id": f"ep{i}"})
            labels[qid], conditions[qid], predictions[qid] = m % 5, condition_names[i % 4], list(probabilities)
    result = diagnostics(predictions, queries, labels, conditions)
    result["folds"] = [{"fold": f, "fit_episodes": [e for e, value in manifest.items() if value != f],
                        "heldout_episodes": [e for e, value in manifest.items() if value == f]} for f in range(2)]
    result["validation_target_exposure"] = False
    result["historical_signal_policy"] = "omitted"
    identity = {"round": "main", "season_id": "synthetic_test_fixture", "train_sha256": {"queries.csv": "a"*64},
                "metadata_sha256": "b"*64, "split_manifest_sha256": digest(manifest),
                "source_sha256": {"feature_api.py": "c"*64}, "feature_plugins_sha256": {},
                "feature_extensions_sha256": {}, "scorer_sha256": {"rounds.py": "d"*64},
                "environment": {"python": "test-fixture"}, "execution_policy": {"cpus_per_worker": 2}}
    return {"trial_id": trial_id, "family": "frequency", "status": "SUCCEEDED", "attempt": 1,
            "provenance": "TRAIN_GROUP_CV", "evaluation_source": "sampled_outcome_group_cv",
            "is_synthetic": False, "official_points": None, "mean_brier": result["mean_brier"],
            "result": result, "identity": identity, "wall_seconds": wall_seconds,
            "created_at": "2026-01-01T00:00:00Z", "finished_at": "2026-01-01T00:00:01Z",
            "source_commit": "test_fixture_only", "hyperparameters": {"family": "frequency", "groups": ["type"], "params": {"C": .1}}}


def write_export(path, trials):
    payload = {"schema": "jaegers.experiment_registry", "schema_version": 1, "trials": trials}
    write_json(path, dict(payload, content_sha256=digest(payload)))


def test_verified_export_reconstructs_metrics_and_never_scores_failed_rows(tmp_path):
    success = trial_fixture()
    failed = dict(deepcopy(success), trial_id="failed", status="TIMEOUT", mean_brier=None, result={})
    path = tmp_path/"registry.json"
    write_export(path, [success, failed])
    rows = load_export(path)
    assert len(rows) == 2
    assert validated_result(rows[0])["mean_brier"] == pytest.approx(.8)
    assert trial_rows(rows)[1]["mean_brier"] is None
    assert all(r["official_points"] is None for r in trial_rows(rows))


@pytest.mark.parametrize("change", [
    lambda t: t.update(provenance="unknown"), lambda t: t.update(is_synthetic=True),
    lambda t: t.update(official_points=50), lambda t: t.update(status="NEW_UNKNOWN"),
    lambda t: t.update(evaluation_source="public_validation_true_targets"),
    lambda t: t["result"].update(mean_brier=0),
    lambda t: t["result"]["per_query"][0].update(label=20),
    lambda t: t["result"]["per_query"][0].update(probabilities=[.5, .5]),
    lambda t: t["result"]["per_query"][0].update(probabilities=[-.1, .3, .3, .3, .2]),
    lambda t: t["result"]["per_query"][0].update(episode_id="unknown"),
    lambda t: t["result"]["folds"][0]["fit_episodes"].append("ep0"),
    lambda t: t["result"]["folds"][1].update(heldout_episodes=["ep0"]),
    lambda t: t["identity"].update(split_manifest_sha256="wrong"),
    lambda t: t.update(result=[]), lambda t: t.update(hyperparameters=[]),
    lambda t: t.update(identity=[]), lambda t: t.update(wall_seconds=-1),
    lambda t: t["result"].update(per_query=[None]),
    lambda t: t["result"].update(folds=[None, None]),
    lambda t: t["result"].update(by_condition=[]),
])
def test_invalid_metric_and_provenance_evidence_fails_closed(tmp_path, change):
    trial = trial_fixture()
    change(trial)
    path = tmp_path/"registry.json"
    write_export(path, [trial])
    with pytest.raises((ValueError, TypeError)):
        load_export(path)


def test_digest_duplicate_and_unsupported_schema_rejected(tmp_path):
    path = tmp_path/"registry.json"
    write_export(path, [trial_fixture()])
    payload = json.loads(path.read_text())
    payload["trials"][0]["status"] = "FAILED"
    path.write_text(json.dumps(payload))
    with pytest.raises(ValueError, match="digest"):
        load_export(path)
    write_export(path, [trial_fixture(), trial_fixture()])
    with pytest.raises(ValueError, match="duplicate"):
        load_export(path)
    path.write_text(json.dumps({"schema_version": 99}))
    with pytest.raises(ValueError, match="schema"):
        load_export(path)


@pytest.mark.parametrize("field", ["round", "season_id", "train_sha256", "split_manifest_sha256", "environment", "execution_policy", "scorer_sha256"])
def test_comparison_blocks_mismatched_context_even_with_identical_episodes(field):
    baseline, candidate = trial_fixture(), trial_fixture("fixture_b")
    candidate["identity"][field] = "adaptation" if field == "round" else "changed"
    with pytest.raises(ValueError, match="Different"):
        comparison(candidate, baseline, bootstrap=100)
    candidate["identity"].pop(field)
    with pytest.raises(ValueError, match="Incomplete"):
        context_key(candidate)


def test_paired_episode_uncertainty_and_calibration_are_recomputed():
    baseline, candidate = trial_fixture(), trial_fixture("fixture_b", (.6, .1, .1, .1, .1))
    result = comparison(candidate, baseline, bootstrap=100, seed=11)
    assert result["mean_delta_brier"] == pytest.approx(.15)
    assert result["ci95"] == pytest.approx([.15, .15])
    assert result["episodes"] == 8
    assert result["official_points"] is None
    assert result == comparison(candidate, baseline, bootstrap=100, seed=11)
    cal = calibration(baseline)
    assert cal["mean_class_ece"] == pytest.approx(.06)
    assert cal["rare_20"]["observed_count"] == 8
    assert cal["rare_20"]["class_brier"] == pytest.approx(.115)
    assert len(cal["mean_probability_by_observed_class"]) == 5
    with pytest.raises(ValueError):
        comparison(candidate, baseline, bootstrap=0)


def _attempt(registry, tid, config, identity, status):
    artifact = registry.start(tid, retry_failed=True)
    write_json(artifact/"request.json", {"trial_id": tid, "config": config, "identity": identity})
    write_json(artifact/"source/source-manifest.json", identity)
    (artifact/"source/research").mkdir(exist_ok=True)
    (artifact/"source/research/fixture.py").write_bytes(b"fixture source\n")
    write_json(artifact/"process/process.json", {"cpus": 2, "status": status})
    result = None
    if status == "SUCCEEDED":
        result = dict(trial_fixture()["result"], config=config)
        write_json(artifact/"result.json", result)
    registry.finish(tid, status, result=result)
    return artifact


def test_all_attempt_audit_preserves_failures_and_detects_source_mutation(tmp_path):
    registry = Registry(tmp_path)
    config = {"family": "frequency"}
    identity = {"source_sha256": {"fixture.py": digest(b"fixture source\n")}, "execution_policy": {"cpus_per_worker": 2},
                "split_manifest_sha256": trial_fixture()["identity"]["split_manifest_sha256"]}
    # common.digest hashes bytes directly; source file evidence uses that contract.
    with registry.coordinator():
        tid = registry.register("fixture_only", config, identity)
        _attempt(registry, tid, config, identity, "TIMEOUT")
        completed = _attempt(registry, tid, config, identity, "SUCCEEDED")
    before = {p: file_hash(p) for p in tmp_path.rglob("*") if p.is_file() and p.suffix not in (".sqlite-wal", ".sqlite-shm")}
    report = audit_registry(tmp_path)
    assert report["ok"] and report["attempt_count"] == 2
    assert report["statuses"] == {"TIMEOUT": 1, "SUCCEEDED": 1}
    assert report["attempts"][1]["process_cpus"] == 2
    assert report["attempts"][1]["process_peak_rss_mib"] is None
    assert before == {p: file_hash(p) for p in before}
    (completed/"source/research/fixture.py").write_text("changed source\n")
    damaged = audit_registry(tmp_path)
    assert not damaged["ok"]
    assert any(f["code"] == "source_bytes_changed" for f in damaged["findings"])
    write_json(completed/"source/source-manifest.json", [])
    corrupted = audit_registry(tmp_path)
    assert not corrupted["ok"]
    assert any(f["code"] == "incomplete_attempt_evidence" for f in corrupted["findings"])


@pytest.mark.parametrize("mutation, expected", [
    ("broken_json", "invalid_success_result"),
    ("changed_metric", "invalid_success_result"),
    ("changed_oof_bytes", "sealed_artifact_bytes_changed"),
    ("changed_config", "success_result_config_conflict"),
    ("changed_database_score", "success_result_registry_score_conflict"),
    ("changed_export_seal", "invalid_portable_artifact_seal"),
])
def test_audit_checks_success_results_and_existing_seals_without_repair(tmp_path, mutation, expected):
    registry = Registry(tmp_path)
    config = {"family": "frequency"}
    identity = {"source_sha256": {"fixture.py": digest(b"fixture source\n")},
                "execution_policy": {"cpus_per_worker": 2},
                "split_manifest_sha256": trial_fixture()["identity"]["split_manifest_sha256"]}
    tid = registry.register("fixture_only", config, identity)
    artifact = _attempt(registry, tid, config, identity, "SUCCEEDED")
    (artifact/"oof.csv").write_text("fixture bytes\n")
    registry.export()
    clean = audit_registry(tmp_path)
    assert clean["ok"] and clean["findings"] == []
    assert clean["artifact_seal_coverage"] == {"VERIFIED": 1}
    result_path = artifact/"result.json"
    if mutation == "broken_json":
        result_path.write_text("{ broken JSON")
    elif mutation in {"changed_metric", "changed_config"}:
        result = json.loads(result_path.read_text())
        result["mean_brier" if mutation == "changed_metric" else "config"] = 0.0 if mutation == "changed_metric" else {"family": "other"}
        write_json(result_path, result)
    elif mutation == "changed_oof_bytes":
        (artifact/"oof.csv").write_text("changed bytes\n")
    elif mutation == "changed_database_score":
        with sqlite3.connect(registry.path) as db:
            db.execute("UPDATE trials SET mean_brier=0")
    else:
        path = tmp_path/"exports/v1/registry.json"
        payload = json.loads(path.read_text())
        payload["content_sha256"] = "0"*64
        write_json(path, payload)
    paths = [p for p in tmp_path.rglob("*") if p.is_file() and p.suffix not in {".sqlite-wal", ".sqlite-shm"}]
    before = {p: file_hash(p) for p in paths}
    damaged = audit_registry(tmp_path)
    assert not damaged["ok"]
    assert expected in {f["code"] for f in damaged["findings"]}
    assert before == {p: file_hash(p) for p in paths}


def test_audit_reports_unsealed_attempt_coverage_explicitly(tmp_path):
    registry = Registry(tmp_path)
    tid = registry.register("fixture_only", {"family": "frequency"}, {})
    _attempt(registry, tid, {"family": "frequency"}, {}, "TIMEOUT")
    report = audit_registry(tmp_path)
    assert report["ok"]
    assert report["artifact_seal_coverage"] == {"UNAVAILABLE": 1}
    assert any(f["code"] == "terminal_artifact_seal_unavailable" and f["level"] == "WARNING" for f in report["findings"])


def test_audit_blocks_escaped_artifact_and_latest_status_conflict(tmp_path):
    registry = Registry(tmp_path)
    with registry.coordinator():
        tid = registry.register("fixture_only", {"family": "frequency"}, {})
        registry.start(tid)
        registry.finish(tid, "FAILED")
    with sqlite3.connect(registry.path) as db:
        db.execute("UPDATE attempts SET artifact=?,status=?", (str(tmp_path.parent), "TIMEOUT"))
    report = audit_registry(tmp_path)
    assert {f["code"] for f in report["findings"]} >= {"artifact_outside_registry", "latest_attempt_trial_mismatch"}
