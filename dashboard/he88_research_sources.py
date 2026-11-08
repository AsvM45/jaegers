"""Read-only HE-87 aggregate-report adapter, separate from full registry evidence.

Reported module/data hashes are checked against the selected checkout. Aggregate
records do not acquire missing per-query predictions, timing or runtime lineage.
"""
from pathlib import Path
import csv
import json
import math

import plotly.graph_objects as go

from Jaeger_Main.House_Edge.research.common import digest, file_hash

CONDITIONS = ("stable", "short_history", "drift", "shared_change")


def _number(value):
    if type(value) not in (int, float) or not math.isfinite(value) or not 0 <= value <= 2:
        raise ValueError("Aggregate Brier must be finite and between zero and two")
    return float(value)


def load_he87_summary(path, house_root=None):
    path = Path(path).resolve()
    root = Path(house_root).resolve() if house_root else path.parents[2]
    report = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(report, dict) or report.get("status") != "MEASURED_NOT_PROMOTED" or report.get("evaluation_source") != "sampled_outcome_group_cv" or report.get("official_points") is not None:
        raise ValueError("Expected measured, unpromoted HE-87 sampled-group-CV report")
    if report.get("public_validation_peeks") != 0 or report.get("validation_files_opened") is not False:
        raise ValueError("Expected explicit train-only HE-87 provenance")
    sources = {"features": root/"research/challengers/grok_he87_features.py",
               "models": root/"research/challengers/grok_he87_models.py",
               "experiment": root/"research/challengers/grok_he87_experiment.py"}
    if not isinstance(report.get("source_sha256"), dict):
        raise ValueError("Missing HE-87 source hash mapping")
    if any(not p.is_file() or file_hash(p) != report.get("source_sha256", {}).get(k) for k, p in sources.items()):
        raise ValueError("HE-87 reported source hashes do not match inspected checkout")
    expected_inputs = {name: file_hash(root/"public/train"/name) for name in
                       ("queries.csv", "history.csv", "labels.csv", "conditions.csv")}
    if expected_inputs != report.get("data_sha256"):
        raise ValueError("HE-87 train-file hashes do not match inspected checkout")
    protocol = root/"research/configs/grok_he87_protocol.json"
    if not protocol.is_file() or file_hash(protocol) != report.get("protocol_sha256"):
        raise ValueError("HE-87 protocol hash mismatch")
    folds = report.get("folds")
    if not isinstance(folds, dict) or not folds or any(type(f) is not int or f < 0 for f in folds.values()) or digest(folds) != report.get("fold_manifest_sha256"):
        raise ValueError("HE-87 fold manifest hash mismatch")
    if len(folds) != report.get("n_episodes") or len(set(folds.values())) != report.get("fold_count"):
        raise ValueError("HE-87 episode/fold count mismatch")
    if type(report.get("fold_count")) is not int or report["fold_count"] < 2 or set(folds.values()) != set(range(report["fold_count"])):
        raise ValueError("At least two contiguous HE-87 grouped folds required")
    with (root/"public/train/queries.csv").open(newline="", encoding="utf-8") as stream:
        query_rows = list(csv.DictReader(stream))
    if {q.get("episode_id") for q in query_rows} != set(folds) or len(query_rows) != report.get("n_queries"):
        raise ValueError("HE-87 query/episode coverage differs from released train inputs")
    candidates = report.get("candidates")
    if not isinstance(candidates, list) or not candidates:
        raise ValueError("No HE-87 candidate summaries")
    rows, names = [], set()
    for candidate in candidates:
        if not isinstance(candidate, dict) or not isinstance(candidate.get("name"), str) or not candidate["name"] or candidate["name"] in names:
            raise ValueError("Invalid or duplicate candidate summary")
        names.add(candidate["name"])
        if candidate.get("evaluation_source") != "sampled_outcome_group_cv" or candidate.get("official_points") is not None:
            raise ValueError("Mixed metric provenance in HE-87 summary")
        losses = candidate.get("by_condition")
        errors = candidate.get("per_episode")
        ep_conditions = candidate.get("episode_conditions")
        if not isinstance(losses, dict) or set(losses) != set(CONDITIONS) or not isinstance(errors, dict) or set(errors) != set(folds) or not isinstance(ep_conditions, dict) or set(ep_conditions) != set(folds):
            raise ValueError("Incomplete HE-87 condition/episode evidence")
        if set(ep_conditions.values()) != set(CONDITIONS):
            raise ValueError("Unknown or missing HE-87 episode conditions")
        score = _number(candidate.get("mean_brier"))
        if not math.isclose(score, sum(_number(losses[c]) for c in CONDITIONS)/4, rel_tol=1e-9, abs_tol=1e-12):
            raise ValueError("HE-87 mean disagrees with condition errors")
        for condition in CONDITIONS:
            values = [_number(errors[ep]) for ep in folds if ep_conditions[ep] == condition]
            if not values or not math.isclose(sum(values)/len(values), losses[condition], rel_tol=1e-9, abs_tol=1e-12):
                raise ValueError("HE-87 condition error disagrees with episode errors")
        rows.append({"name": candidate["name"], "reported_mean_brier": score,
                     **{c: losses[c] for c in CONDITIONS}, "reported_20x_ece": candidate.get("class_20_ece"),
                     "reported_fit_seconds": candidate.get("fit_seconds"), "official_points": None,
                     "evidence_level": "source-checked aggregate; per-query probabilities unavailable"})
    payload = {"schema": "jaegers.he88_external_summary", "schema_version": 1, "source_format": "HE87 aggregate adapter v1",
               "source_content_sha256": file_hash(path), "declared_source_sha256": report["source_sha256"],
               "data_sha256": expected_inputs, "fold_manifest_sha256": report["fold_manifest_sha256"],
               "protocol_sha256": report["protocol_sha256"], "n_queries": report.get("n_queries"),
               "n_episodes": len(folds), "rows": rows, "negative_results": report.get("negative_results", []),
               "warnings": ["Module/data/protocol hashes and episode aggregates match the inspected checkout; full dependency lineage and raw probabilities remain unavailable.",
                    "Reported fit times use the campaign's accounting; shared-mixture cost is apportioned and is excluded from registry Pareto comparisons.",
                    "Cross-source ranking, per-query metric reconstruction and fresh class calibration are unavailable for these aggregate-only records.",
                    "Frozen champion references retain their documented historical-signal and development-exposure caveats."]}
    payload["content_sha256"] = digest(payload)
    return payload


def summary_figures(summary):
    rows = sorted(summary["rows"], key=lambda r: r["reported_mean_brier"])
    performance = go.Figure(go.Bar(x=[r["reported_mean_brier"] for r in rows], y=[r["name"] for r in rows], orientation="h"))
    performance.update_layout(title="HE-87 reported candidate errors · one campaign", yaxis={"autorange": "reversed"},
                              xaxis_title="Source-checked aggregate sampled Brier ↓", height=max(450, 24*len(rows)))
    condition = go.Figure(go.Heatmap(x=list(CONDITIONS), y=[r["name"] for r in rows],
                                    z=[[r[c] for c in CONDITIONS] for r in rows], colorscale="Viridis_r"))
    condition.update_layout(title="HE-87 reported condition errors", height=max(450, 24*len(rows)))
    for figure in (performance, condition):
        figure.update_layout(template="plotly_white", margin={"l": 230, "r": 35, "t": 65, "b": 50})
    return {"reported_errors": performance, "reported_conditions": condition}
