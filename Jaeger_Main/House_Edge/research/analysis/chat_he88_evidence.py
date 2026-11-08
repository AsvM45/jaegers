"""Strict, read-only evidence adapter over the existing registry v1 contract.

No scheduler, lease or trial table is replaced. Missing evidence stays unavailable;
unknown metric provenance and mismatched comparison contexts fail closed.
"""
from __future__ import annotations

from collections import Counter
import json
import math
from pathlib import Path
import sqlite3

import numpy as np

from ..adapters import validate_predictions
from ..common import digest, file_hash, tree_hashes
from ..metrics import diagnostics, paired

STATUSES = {"PENDING", "RUNNING", "SUCCEEDED", "FAILED", "TIMEOUT", "MEMORY_LIMIT", "INTERRUPTED", "CANCELLED"}
CONDITIONS = ("stable", "short_history", "drift", "shared_change")
CONTEXT_FIELDS = ("round", "season_id", "train_sha256", "metadata_sha256",
                  "split_manifest_sha256", "environment", "execution_policy", "scorer_sha256")


def load_export(path):
    """Read only a verified portable envelope. No demo fallback or pickle loading."""
    path = Path(path)
    envelope = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(envelope, dict) or envelope.get("schema") != "jaegers.experiment_registry" or type(envelope.get("schema_version")) is not int or envelope["schema_version"] != 1:
        raise ValueError("Expected experiment_registry portable schema version 1")
    payload = {k: v for k, v in envelope.items() if k != "content_sha256"}
    if envelope.get("content_sha256") != digest(payload):
        raise ValueError("Portable registry content digest mismatch")
    trials = envelope.get("trials")
    if not isinstance(trials, list):
        raise ValueError("trials must be a list")
    seen = set()
    for trial in trials:
        if not isinstance(trial, dict) or not isinstance(trial.get("trial_id"), str) or not trial["trial_id"] or trial["trial_id"] in seen:
            raise ValueError("Missing or duplicate trial ID")
        seen.add(trial["trial_id"])
        if any(not isinstance(trial.get(k), dict) for k in ("identity", "hyperparameters", "result")):
            raise ValueError("Trial identity, hyperparameters and result must be objects")
        if not isinstance(trial.get("family"), str) or not trial["family"]:
            raise ValueError("Trial family must be named")
        config = trial["hyperparameters"]
        groups = config.get("groups", [])
        if not isinstance(groups, list) or any(not isinstance(g, str) for g in groups) or len(set(groups)) != len(groups) or not isinstance(config.get("params", {}), dict):
            raise ValueError("Invalid feature group or hyperparameter schema")
        wall = trial.get("wall_seconds")
        if wall is not None and (type(wall) not in (int, float) or not math.isfinite(wall) or wall < 0):
            raise ValueError("Trial wall time must be finite and nonnegative or missing")
        if trial.get("status") not in STATUSES:
            raise ValueError("Unknown trial status")
        if trial.get("is_synthetic") is not False:
            raise ValueError("Real-evidence view requires explicit is_synthetic=false; use existing separate demo dashboard")
        if trial.get("provenance") != "TRAIN_GROUP_CV" or trial.get("official_points") is not None:
            raise ValueError("This view accepts sampled train-grouped CV only, with no official points")
        if trial["status"] == "SUCCEEDED":
            validated_result(trial)
        elif trial.get("mean_brier") is not None:
            raise ValueError("Non-success trial must not carry a score")
    return trials


def context_key(trial):
    identity = trial.get("identity")
    if not isinstance(identity, dict) or any(identity.get(k) in (None, "", {}) for k in CONTEXT_FIELDS):
        raise ValueError("Incomplete comparison context: round, season, data, folds, scorer and runtime required")
    if not isinstance(identity.get("source_sha256"), dict) or not identity["source_sha256"] or "feature_plugins_sha256" not in identity:
        raise ValueError("Missing numerical source/feature provenance")
    if identity["round"] not in ("main", "adaptation"):
        raise ValueError("Unknown competition round")
    return digest({k: identity[k] for k in CONTEXT_FIELDS})


def validated_result(trial):
    """Recompute the existing metric from five-vector per-query evidence and folds."""
    if trial.get("status") != "SUCCEEDED":
        raise ValueError("Trial did not succeed")
    result = trial.get("result", {})
    if not isinstance(result, dict):
        raise ValueError("Result must be an object")
    if result.get("official_points") is not None:
        raise ValueError("Sampled outcome diagnostics cannot contain official points")
    if result.get("evaluation_source") != "sampled_outcome_group_cv" or trial.get("evaluation_source") != "sampled_outcome_group_cv":
        raise ValueError("Explicit sampled_outcome_group_cv provenance required")
    rows = result.get("per_query")
    if not isinstance(rows, list) or not rows:
        raise ValueError("Missing per-query evidence")
    queries, labels, conditions, predictions = [], {}, {}, {}
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError("Per-query evidence rows must be objects")
        qid, ep = row.get("query_id"), row.get("episode_id")
        if not isinstance(qid, str) or not qid or qid in predictions or not isinstance(ep, str) or not ep:
            raise ValueError("Missing or duplicate query/episode identity")
        if type(row.get("label")) is not int or row["label"] not in range(5) or row.get("condition") not in CONDITIONS:
            raise ValueError("Five-class indices and known diagnostic conditions required")
        queries.append({"query_id": qid, "episode_id": ep})
        predictions[qid], labels[qid], conditions[qid] = row["probabilities"], row["label"], row["condition"]
    validate_predictions(predictions, queries)
    ep_conditions = {}
    for q in queries:
        condition = conditions[q["query_id"]]
        if q["episode_id"] in ep_conditions and ep_conditions[q["episode_id"]] != condition:
            raise ValueError("Episode crosses condition labels")
        ep_conditions[q["episode_id"]] = condition
    if set(ep_conditions.values()) != set(CONDITIONS):
        raise ValueError("Four-condition grouped evaluation coverage required")
    calculated = diagnostics(predictions, queries, labels, conditions)
    for key in ("mean_brier", "by_condition", "per_episode", "episode_conditions"):
        if key not in result:
            raise ValueError(f"Missing metric evidence {key}")
        if isinstance(calculated[key], dict) and not isinstance(result[key], dict):
            raise ValueError(f"Stored {key} must be an object")
        if key == "episode_conditions":
            valid = calculated[key] == result[key]
        elif isinstance(calculated[key], dict):
            valid = set(calculated[key]) == set(result[key]) and all(
                math.isclose(v, result[key][k], rel_tol=1e-10, abs_tol=1e-12) for k, v in calculated[key].items())
        else:
            valid = math.isclose(calculated[key], result[key], rel_tol=1e-10, abs_tol=1e-12)
        if not valid:
            raise ValueError(f"Stored {key} disagrees with per-query evidence")
    if trial.get("mean_brier") is None or not math.isclose(trial["mean_brier"], calculated["mean_brier"], rel_tol=1e-10, abs_tol=1e-12):
        raise ValueError("Trial score disagrees with result evidence")
    manifest = {}
    folds = result.get("folds")
    if not isinstance(folds, list) or len(folds) < 2:
        raise ValueError("Missing whole-episode fold evidence")
    all_episodes = set(ep_conditions)
    seen_fold_ids = set()
    for fold in folds:
        if not isinstance(fold, dict):
            raise ValueError("Fold evidence rows must be objects")
        fit, hold = fold.get("fit_episodes", []), fold.get("heldout_episodes", [])
        fold_id = fold.get("fold")
        if type(fold_id) is not int or fold_id < 0 or fold_id in seen_fold_ids:
            raise ValueError("Invalid or duplicate fold ID")
        seen_fold_ids.add(fold_id)
        if not hold or len(set(fit)) != len(fit) or len(set(hold)) != len(hold) or set(fit) != all_episodes - set(hold) or set(fit) & set(hold):
            raise ValueError("Fit/held-out episode leakage or incomplete fold coverage")
        for ep in hold:
            if ep not in all_episodes or ep in manifest:
                raise ValueError("Repeated or unknown held-out episode")
            manifest[ep] = fold_id
    if set(manifest) != all_episodes or trial.get("identity", {}).get("split_manifest_sha256") != digest(manifest):
        raise ValueError("OOF manifest does not match preregistered split digest")
    return calculated


def comparison(candidate, baseline, bootstrap=2000, seed=0):
    if type(bootstrap) is not int or not 100 <= bootstrap <= 10000:
        raise ValueError("bootstrap must be an integer from 100 to 10000")
    if context_key(candidate) != context_key(baseline):
        raise ValueError("Different round/season, raw data, folds, scorer or runtime policy")
    a, b = validated_result(candidate), validated_result(baseline)
    # Identical episode sets alone are insufficient: sampled labels/query sets must match.
    label_key = lambda r: sorted((q["query_id"], q["episode_id"], q["label"], q["condition"]) for q in r["per_query"])
    if label_key(a) != label_key(b):
        raise ValueError("Different query IDs, sampled labels or conditions")
    output = paired(a, b, bootstrap=bootstrap, seed=seed)
    output["candidate_id"], output["baseline_id"] = candidate["trial_id"], baseline["trial_id"]
    output["metric_source"] = "sampled_outcome_group_cv"
    output["official_points"] = None
    output["source_versions_differ"] = candidate["identity"]["source_sha256"] != baseline["identity"]["source_sha256"]
    output["selection_warning"] = "Exploratory unadjusted paired episode interval; multiple comparisons and development-informed design remain."
    return output


def calibration(trial):
    result = validated_result(trial)
    bins = result["calibration"]
    classes = []
    for k, payout in enumerate((0, 1, 2, 5, 20)):
        rows = [r for r in bins if r["class"] == k]
        total = sum(r["count"] for r in rows)
        classes.append({"class_index": k, "payout": payout,
                        "ece": sum(r["count"] * abs(r["predicted"]-r["observed"]) for r in rows) / total,
                        "brier": result["class_brier"][k], "observed_count": result["class_counts"][k]})
    per_query = result["per_query"]
    p = np.asarray([r["probabilities"] for r in per_query])
    y = np.asarray([r["label"] for r in per_query])
    matrix = [p[y == k].mean(axis=0).tolist() if (y == k).any() else [None]*5 for k in range(5)]
    return {"classes": classes, "bins": bins, "mean_class_ece": float(np.mean([r["ece"] for r in classes])),
            "rare_20": {"observed_count": int((y == 4).sum()), "observed_rate": float((y == 4).mean()),
                        "mean_predicted": float(p[:, 4].mean()), "class_brier": result["class_brier"][4]},
            "mean_probability_by_observed_class": matrix,
            "warning": "ECE is a sampled-label bin diagnostic, sensitive to binning and rare-class sample size."}


def trial_rows(trials):
    """Flat filtering/export rows; failed/missing scores never become zero."""
    output = []
    for trial in trials:
        identity, config = trial.get("identity", {}), trial.get("hyperparameters", {})
        try:
            context, warning = context_key(trial), None
        except ValueError as exc:
            context, warning = None, str(exc)
        source = identity.get("source_sha256", {})
        output.append({"trial_id": trial["trial_id"], "family": trial.get("family"), "status": trial["status"],
            "attempt": trial.get("attempt"), "mean_brier": trial.get("mean_brier") if trial["status"] == "SUCCEEDED" else None,
            "wall_seconds": trial.get("wall_seconds"), "created_at": trial.get("created_at"),
            "finished_at": trial.get("finished_at"), "round": identity.get("round"), "season_id": identity.get("season_id"),
            "context": context, "source_commit": trial.get("source_commit"), "source_sha256": digest(source) if source else None,
            "data_sha256": digest(identity["train_sha256"]) if identity.get("train_sha256") else None,
            "split_sha256": identity.get("split_manifest_sha256"),
            "feature_sha256": digest({"core": source.get("feature_api.py"), "plugins": identity.get("feature_plugins_sha256"),
                                      "extensions": identity.get("feature_extensions_sha256")}) if source else None,
            "groups": ",".join(sorted(config.get("groups", []))), "seed": config.get("seed", 0),
            "hyperparameters": json.dumps(config.get("params", {}), sort_keys=True),
            "metric_source": trial.get("evaluation_source"), "official_points": None,
            "validation_target_exposure": trial.get("result", {}).get("validation_target_exposure"),
            "historical_signal_policy": trial.get("result", {}).get("historical_signal_policy"),
            "warning": warning, "error": trial.get("error_message")})
    return output


def audit_registry(root):
    """Read all durable attempts in one SQLite snapshot; report, never repair."""
    root = Path(root).resolve()
    db_path = root/"registry.sqlite"
    if not db_path.is_file():
        raise FileNotFoundError(db_path)
    with sqlite3.connect(db_path.as_uri()+"?mode=ro", uri=True) as db:
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA query_only=ON")
        db.execute("BEGIN")
        trials = [dict(r) for r in db.execute("SELECT * FROM trials ORDER BY id")]
        attempts = [dict(r) for r in db.execute("SELECT * FROM attempts ORDER BY trial_id,attempt")]
    findings = []
    def finding(trial_id, attempt, code, level="ERROR"):
        findings.append({"trial_id": trial_id, "attempt": attempt, "code": code, "level": level})
    sealed_attempts = {}
    portable = root/"exports/v1/registry.json"
    if portable.is_file():
        try:
            for record in load_export(portable):
                number, hashes = record.get("attempt"), record.get("artifact_sha256")
                if type(number) is not int or number < 0:
                    raise ValueError("Invalid sealed attempt number")
                if hashes is not None:
                    if not isinstance(hashes, dict) or not hashes or any(
                        not isinstance(k, str) or not isinstance(v, str) or len(v) != 64
                        or any(c not in "0123456789abcdef" for c in v) for k, v in hashes.items()
                    ):
                        raise ValueError("Invalid artifact seal")
                    sealed_attempts[(record["trial_id"], number)] = record
        except (OSError, ValueError, KeyError, TypeError):
            sealed_attempts = {}
            finding(None, None, "invalid_portable_artifact_seal")
    indexed = {r["id"]: r for r in trials}
    for trial in trials:
        rows = [a for a in attempts if a["trial_id"] == trial["id"]]
        if [a["attempt"] for a in rows] != list(range(1, trial["attempt"]+1)):
            finding(trial["id"], trial["attempt"], "attempt_sequence_gap")
        if rows and (rows[-1]["status"] != trial["status"] or rows[-1]["artifact"] != trial["artifact"]):
            finding(trial["id"], trial["attempt"], "latest_attempt_trial_mismatch")
    for attempt in attempts:
        tid, number, status = attempt["trial_id"], attempt["attempt"], attempt["status"]
        if tid not in indexed:
            finding(tid, number, "orphan_attempt")
            continue
        artifact = Path(attempt["artifact"]).resolve()
        if not artifact.is_relative_to(root/"trials"):
            finding(tid, number, "artifact_outside_registry")
            continue
        if status not in STATUSES:
            finding(tid, number, "unknown_attempt_status")
        if not artifact.is_dir():
            finding(tid, number, "missing_attempt_directory")
            continue
        attempt["artifact_seal_status"] = "NOT_TERMINAL"
        if status not in {"PENDING", "RUNNING"}:
            sealed = sealed_attempts.get((tid, number))
            attempt["artifact_seal_status"] = "UNAVAILABLE"
            if sealed is None:
                finding(tid, number, "terminal_artifact_seal_unavailable", "WARNING")
            else:
                try:
                    if tree_hashes(artifact) != sealed["artifact_sha256"]:
                        attempt["artifact_seal_status"] = "MISMATCH"
                        finding(tid, number, "sealed_artifact_bytes_changed")
                    else:
                        attempt["artifact_seal_status"] = "VERIFIED"
                    if sealed["status"] != status:
                        finding(tid, number, "sealed_attempt_status_conflict")
                except OSError:
                    finding(tid, number, "unreadable_terminal_artifacts")
        try:
            request = json.loads((artifact/"request.json").read_text())
            if not isinstance(request, dict):
                raise ValueError("Invalid request object")
            trial = indexed[tid]
            if request.get("trial_id") != tid or request.get("config") != json.loads(trial["config"]) or request.get("identity") != json.loads(trial["identity"]):
                finding(tid, number, "request_identity_conflict")
            manifest = json.loads((artifact/"source/source-manifest.json").read_text())
            if not isinstance(manifest, dict):
                raise ValueError("Invalid source manifest")
            if manifest != request["identity"]:
                finding(tid, number, "source_manifest_conflict")
            sources = manifest.get("source_sha256", {})
            if not isinstance(sources, dict):
                raise ValueError("Invalid source hashes")
            for name, expected in sources.items():
                source = (artifact/"source/research"/name).resolve()
                if not source.is_relative_to(artifact/"source/research") or not source.is_file() or file_hash(source) != expected:
                    finding(tid, number, "source_bytes_changed")
                    break
            for directory, key in (("research/models", "model_plugins_sha256"), ("research/features", "feature_plugins_sha256"),
                ("research/extensions", "feature_extensions_sha256"), ("research/challengers", "challenger_plugins_sha256"),
                ("slot_forecasting", "scorer_sha256"), ("jaegers_entry", "champion_sha256")):
                if key in manifest and tree_hashes(artifact/"source"/directory) != manifest[key]:
                    finding(tid, number, "plugin_or_champion_bytes_changed:"+key)
            if status == "SUCCEEDED" and not (artifact/"result.json").is_file():
                finding(tid, number, "success_missing_result")
            elif status == "SUCCEEDED":
                try:
                    result = json.loads((artifact/"result.json").read_text())
                    validated_result({"status": status, "result": result, "identity": request["identity"],
                        "evaluation_source": "sampled_outcome_group_cv",
                        "mean_brier": result.get("mean_brier") if isinstance(result, dict) else None})
                    if result.get("config") != request.get("config"):
                        finding(tid, number, "success_result_config_conflict")
                    if number == trial["attempt"] and (trial["mean_brier"] is None or not math.isclose(
                        trial["mean_brier"], result["mean_brier"], rel_tol=1e-10, abs_tol=1e-12
                    )):
                        finding(tid, number, "success_result_registry_score_conflict")
                except (OSError, ValueError, KeyError, TypeError):
                    finding(tid, number, "invalid_success_result")
            process = json.loads((artifact/"process/process.json").read_text())
            if not isinstance(process, dict):
                raise ValueError("Invalid process evidence")
            # Preserve missing readings as null; no zero-cost or zero-memory claims.
            for field in ("wall_seconds", "peak_rss_mib", "cpus", "timeout_seconds", "memory_limit_gib"):
                attempt["process_"+field] = process.get(field)
            if status == "SUCCEEDED" and process.get("status") != "SUCCEEDED":
                finding(tid, number, "success_process_conflict")
            cpus = manifest.get("execution_policy", {}).get("cpus_per_worker")
            if cpus is not None and process.get("cpus") != cpus:
                finding(tid, number, "process_cpu_policy_conflict")
        except (OSError, ValueError, KeyError, TypeError):
            finding(tid, number, "incomplete_attempt_evidence", "ERROR" if status == "SUCCEEDED" else "WARNING")
    return {"schema": "jaegers.he88_attempt_audit", "schema_version": 1, "read_only": True,
            "trial_count": len(trials), "attempt_count": len(attempts), "attempts": attempts,
            "statuses": dict(Counter(a["status"] for a in attempts)), "findings": findings,
            "ok": not any(f["level"] == "ERROR" for f in findings),
            "artifact_seal_coverage": dict(Counter(a.get("artifact_seal_status", "UNCHECKED") for a in attempts)),
            "limitation": "Single-host read-only observation, not a multi-host lease or repair service. "
                "Historical/unexported attempts without a portable seal cannot be byte-verified; "
                "ok means no detected errors, not complete seal coverage. Missing seals are explicit warnings."}
