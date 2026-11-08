"""Reproducible export engine for JAEGERS experiment analysis and reports.

Provides:
- CSV export for experiment leaderboards, condition breakdowns, and component ablations.
- JSON export for trial configurations, run manifests, and hypothesis tracking records.
- Markdown report generation matching the format and standards of research/report.py.
- Safe file export utilities.
"""

from __future__ import annotations

import csv
from datetime import datetime, timezone
import io
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Union

from .schema import (
    ComponentAblation,
    HypothesisRecord,
    PairedComparison,
    TrialDetail,
    TrialRecord,
)


def _iso_now() -> str:
    """Return current UTC timestamp in ISO 8601 format."""
    return datetime.now(timezone.utc).isoformat()


def export_leaderboard_csv(trials: Sequence[TrialRecord]) -> str:
    """Export experiment leaderboard to CSV string.

    Columns:
        trial_id, study_name, family, status, provenance, is_champion,
        official_points, mean_brier, wall_seconds, source_commit, created_at
    """
    output = io.StringIO()
    writer = csv.writer(output, lineterminator="\n")
    headers = [
        "trial_id",
        "study_name",
        "family",
        "status",
        "provenance",
        "is_champion",
        "official_points",
        "mean_brier",
        "wall_seconds",
        "source_commit",
        "created_at",
    ]
    writer.writerow(headers)

    for t in trials:
        writer.writerow(
            [
                t.trial_id,
                t.study_name,
                t.family,
                t.status,
                t.provenance.value,
                "TRUE" if t.is_champion else "FALSE",
                f"{t.official_points:.6f}" if t.official_points is not None else "",
                f"{t.mean_brier:.6f}" if t.mean_brier is not None else "",
                f"{t.wall_seconds:.2f}",
                t.source_commit,
                t.created_at,
            ]
        )

    return output.getvalue()


def export_condition_breakdown_csv(trials: Sequence[TrialRecord]) -> str:
    """Export 4-condition contest breakdown to CSV string.

    Columns:
        trial_id, family, provenance, stable, short_history, drift,
        shared_change, mean_ratio, official_points
    """
    output = io.StringIO()
    writer = csv.writer(output, lineterminator="\n")
    headers = [
        "trial_id",
        "family",
        "provenance",
        "stable",
        "short_history",
        "drift",
        "shared_change",
        "mean_ratio",
        "official_points",
    ]
    writer.writerow(headers)

    for t in trials:
        if t.condition_losses:
            cl = t.condition_losses
            writer.writerow(
                [
                    t.trial_id,
                    t.family,
                    t.provenance.value,
                    f"{cl.stable:.6f}",
                    f"{cl.short_history:.6f}",
                    f"{cl.drift:.6f}",
                    f"{cl.shared_change:.6f}",
                    f"{cl.mean_ratio:.6f}",
                    f"{t.official_points:.6f}" if t.official_points is not None else f"{cl.points_60:.6f}",
                ]
            )
        elif t.episode_conditions and t.per_episode_errors:
            # Aggregate per-condition mean errors
            cond_map = t.episode_conditions
            err_map = t.per_episode_errors
            groups = sorted(set(cond_map.values()))
            cond_means: Dict[str, float] = {}
            for g in groups:
                vals = [err_map[ep] for ep in err_map if cond_map.get(ep) == g]
                if vals:
                    cond_means[g] = sum(vals) / len(vals)
            writer.writerow(
                [
                    t.trial_id,
                    t.family,
                    t.provenance.value,
                    f"{cond_means.get('stable', 0.0):.6f}",
                    f"{cond_means.get('short_history', 0.0):.6f}",
                    f"{cond_means.get('drift', 0.0):.6f}",
                    f"{cond_means.get('shared_change', 0.0):.6f}",
                    f"{sum(cond_means.values()) / max(1, len(cond_means)):.6f}",
                    "",
                ]
            )

    return output.getvalue()


def export_ablations_csv(ablations: Sequence[ComponentAblation]) -> str:
    """Export pre-registered component ablations to CSV string.

    Columns:
        variant_name, removed_component, hypothesis, official_points,
        official_points_delta, ci95_low, ci95_high, train_brier_delta,
        supported, direction
    """
    output = io.StringIO()
    writer = csv.writer(output, lineterminator="\n")
    headers = [
        "variant_name",
        "removed_component",
        "hypothesis",
        "official_points",
        "official_points_delta",
        "ci95_low",
        "ci95_high",
        "train_brier_delta",
        "supported",
        "direction",
    ]
    writer.writerow(headers)

    for a in ablations:
        writer.writerow(
            [
                a.variant_name,
                a.removed_component,
                a.hypothesis,
                f"{a.official_points:.6f}",
                f"{a.official_points_delta:.6f}",
                f"{a.ci95_points[0]:.6f}",
                f"{a.ci95_points[1]:.6f}",
                f"{a.train_brier_delta:.6f}" if a.train_brier_delta is not None else "",
                "TRUE" if a.supported else "FALSE",
                a.direction,
            ]
        )

    return output.getvalue()


def export_trial_config_json(trial: Union[TrialRecord, TrialDetail, Dict[str, Any]]) -> str:
    """Export full configuration and metadata of a trial to formatted JSON string."""
    if isinstance(trial, TrialDetail):
        payload = {
            "trial_id": trial.record.trial_id,
            "study_name": trial.record.study_name,
            "family": trial.record.family,
            "status": trial.record.status,
            "provenance": trial.record.provenance.value,
            "hyperparameters": trial.raw_config or trial.record.hyperparameters,
            "source_commit": trial.record.source_commit,
            "wall_seconds": trial.record.wall_seconds,
            "official_points": trial.record.official_points,
            "mean_brier": trial.record.mean_brier,
            "condition_losses": trial.record.condition_losses.as_dict() if trial.record.condition_losses else None,
            "feature_importance": trial.record.feature_importance,
            "exported_at": _iso_now(),
        }
    elif isinstance(trial, TrialRecord):
        payload = {
            "trial_id": trial.trial_id,
            "study_name": trial.study_name,
            "family": trial.family,
            "status": trial.status,
            "provenance": trial.provenance.value,
            "hyperparameters": trial.hyperparameters,
            "source_commit": trial.source_commit,
            "wall_seconds": trial.wall_seconds,
            "official_points": trial.official_points,
            "mean_brier": trial.mean_brier,
            "condition_losses": trial.condition_losses.as_dict() if trial.condition_losses else None,
            "feature_importance": trial.feature_importance,
            "exported_at": _iso_now(),
        }
    else:
        payload = dict(trial)
        payload["exported_at"] = _iso_now()

    return json.dumps(payload, indent=2, sort_keys=True)


def export_run_manifest_json(
    trials: Sequence[TrialRecord], store_metadata: Optional[Dict[str, Any]] = None
) -> str:
    """Export complete experiment run manifest to formatted JSON string."""
    statuses: Dict[str, int] = {}
    for t in trials:
        statuses[t.status] = statuses.get(t.status, 0) + 1

    manifest = {
        "manifest_version": "1.0.0",
        "generated_at": _iso_now(),
        "total_runs": len(trials),
        "status_counts": statuses,
        "is_synthetic": any(t.is_synthetic for t in trials),
        "metadata": store_metadata or {},
        "trials": [t.to_dict() for t in trials],
    }
    return json.dumps(manifest, indent=2, sort_keys=True)


def export_hypotheses_json(hypotheses: Sequence[HypothesisRecord]) -> str:
    """Export tracked hypotheses to formatted JSON string."""
    records = []
    for h in hypotheses:
        records.append(
            {
                "id": h.id,
                "preregistered_timestamp": h.preregistered_timestamp,
                "component": h.component,
                "statement": h.statement,
                "expected_direction": h.expected_direction,
                "observed_points_diff": h.observed_points_diff,
                "observed_brier_diff": h.observed_brier_diff,
                "verdict": h.verdict,
                "decision": h.decision,
                "linked_trial_id": h.linked_trial_id,
            }
        )

    payload = {
        "hypotheses_version": "1.0.0",
        "exported_at": _iso_now(),
        "count": len(records),
        "hypotheses": records,
    }
    return json.dumps(payload, indent=2, sort_keys=True)


def generate_markdown_report(
    trials: Sequence[TrialRecord],
    baseline_id: Optional[str] = None,
    comparisons: Optional[Sequence[PairedComparison]] = None,
    title: str = "House Edge experiment evidence",
) -> str:
    """Generate Markdown report matching the format and standards of research/report.py.

    Includes:
    - Summary of completed runs and distinct configurations.
    - Scientific and metric provenance disclaimers.
    - Table of runs: Trial, Family, Brier, Seconds, Exposure / Provenance.
    - Condition diagnostics table: stable, short_history, drift, shared_change.
    - Paired episode differences with 95% bootstrap intervals.
    - Failure traces section.

    Args:
        trials: Sequence of TrialRecords.
        baseline_id: Optional baseline trial_id for comparisons.
        comparisons: Optional sequence of PairedComparison results.
        title: Report title header (default "House Edge experiment evidence").

    Returns:
        Markdown string.
    """
    now_str = _iso_now()
    succeeded = [t for t in trials if t.status == "SUCCEEDED"]
    failed = [t for t in trials if t.status not in ("SUCCEEDED", "PENDING", "RUNNING")]

    configs = set()
    for t in succeeded:
        try:
            configs.add(json.dumps(t.hyperparameters, sort_keys=True))
        except (TypeError, ValueError):
            configs.add(str(t.hyperparameters))

    distinct_configs = len(configs)

    lines: List[str] = [
        f"# {title}",
        "",
        f"Generated {now_str}.",
        "",
        f"Completed runs: {len(succeeded)}; distinct configurations: {distinct_configs}.",
        "Repeated source versions are separate runs, not additional scientific hypotheses.",
        "",
        "These are sampled-label episode-grouped Brier losses, not official competition points.",
        "",
        "| Trial | Family | Brier ↓ | Seconds | Validation-target exposure |",
        "| --- | --- | ---: | ---: | --- |",
    ]

    # Sort succeeded runs by mean_brier if available, else official_points descending
    sorted_succeeded = sorted(
        succeeded,
        key=lambda x: (x.mean_brier if x.mean_brier is not None else float("inf")),
    )

    for r in sorted_succeeded:
        brier_str = f"{r.mean_brier:.6f}" if r.mean_brier is not None else "N/A"
        exposure = r.provenance.value
        lines.append(
            f"| {r.trial_id[:12]} | {r.family} | {brier_str} | {r.wall_seconds:.2f} | {exposure} |"
        )

    # Condition diagnostics
    lines.extend(
        [
            "",
            "## Condition diagnostics",
            "",
            "| Trial | stable | short_history | drift | shared_change |",
            "| --- | ---: | ---: | ---: | ---: |",
        ]
    )

    for r in sorted_succeeded:
        if r.condition_losses:
            cl = r.condition_losses
            vals = f"{cl.stable:.6f} | {cl.short_history:.6f} | {cl.drift:.6f} | {cl.shared_change:.6f}"
            lines.append(f"| {r.trial_id[:12]} | {vals} |")
        elif r.episode_conditions and r.per_episode_errors:
            c_map = r.episode_conditions
            e_map = r.per_episode_errors
            vals_list = []
            for c in ("stable", "short_history", "drift", "shared_change"):
                c_vals = [e_map[ep] for ep in e_map if c_map.get(ep) == c]
                if c_vals:
                    vals_list.append(f"{sum(c_vals)/len(c_vals):.6f}")
                else:
                    vals_list.append("N/A")
            lines.append(f"| {r.trial_id[:12]} | {' | '.join(vals_list)} |")
        else:
            lines.append(f"| {r.trial_id[:12]} | N/A | N/A | N/A | N/A |")

    # Paired episode differences
    if baseline_id or comparisons:
        lines.extend(
            [
                "",
                "## Paired episode differences",
                "",
                "Negative values favor the candidate. Bootstrap resamples whole episodes within conditions.",
                "",
            ]
        )
        if comparisons:
            for cmp in comparisons:
                ci_str = f"[{cmp.ci95_low:.6f}, {cmp.ci95_high:.6f}]"
                lines.append(
                    f"- {cmp.candidate_id[:12]}: delta {cmp.mean_delta:.6f}; 95% interval {ci_str}."
                )
        elif baseline_id:
            lines.append(f"Baseline selected: {baseline_id[:12]}. No paired differences calculated.")

    # Failures section
    lines.extend(["", "## Failures", ""])
    if failed:
        for f in failed:
            err = f.error_message or "inspect recorded attempt logs"
            lines.append(f"- {f.trial_id[:12]}: {f.status}; {err}.")
    else:
        lines.append("None recorded.")

    return "\n".join(lines) + "\n"


def export_to_file(content: str, filepath: Union[str, Path]) -> Path:
    """Write string content to target file safely with UTF-8 encoding.

    Creates parent directories if necessary.

    Args:
        content: String content to write.
        filepath: Target file path.

    Returns:
        Resolved Path object.
    """
    path = Path(filepath).resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path
