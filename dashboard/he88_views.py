"""Additive quantitative views over strict HE-88 registry evidence."""
from __future__ import annotations

import json

import plotly.graph_objects as go

from Jaeger_Main.House_Edge.research.analysis.chat_he88_evidence import (
    CONDITIONS, calibration, comparison, context_key, trial_rows,
)

PAYOUTS = (0, 1, 2, 5, 20)


def filter_trials(trials, filters=None, required_groups=(), parameter_text=""):
    rows = {r["trial_id"]: r for r in trial_rows(trials)}
    output = []
    for trial in trials:
        row = rows[trial["trial_id"]]
        if any(row.get(key) not in values for key, values in (filters or {}).items() if values):
            continue
        if not set(required_groups).issubset(trial.get("hyperparameters", {}).get("groups", [])):
            continue
        if parameter_text and parameter_text.casefold() not in row["hyperparameters"].casefold():
            continue
        output.append(trial)
    return output


def pareto_ids(trials):
    rows = [r for r in trial_rows(trials) if r["status"] == "SUCCEEDED" and r["context"] is not None
            and r["wall_seconds"] is not None and r["mean_brier"] is not None]
    if len({r["context"] for r in rows}) > 1:
        raise ValueError("Select one comparable context for Pareto analysis")
    return {r["trial_id"] for r in rows if not any(
        other["wall_seconds"] <= r["wall_seconds"] and other["mean_brier"] <= r["mean_brier"] and
        (other["wall_seconds"] < r["wall_seconds"] or other["mean_brier"] < r["mean_brier"])
        for other in rows)}


def build_figures(trials, baseline_id=None, diagnostic_id=None, parameter="C", bootstrap=2000):
    """Never rank incompatible rounds/folds. Caller selects or facets contexts."""
    succeeded = [t for t in trials if t["status"] == "SUCCEEDED"]
    if len({context_key(t) for t in succeeded}) > 1:
        raise ValueError("Select one comparable round/data/fold/runtime context before charting")
    figures, blockers = {}, []
    rows = trial_rows(trials)
    statuses = sorted({t["status"] for t in trials})
    figures["status"] = go.Figure(go.Bar(x=statuses, y=[sum(t["status"] == s for t in trials) for s in statuses]))
    figures["status"].update_layout(title="Latest trial outcomes", yaxis_title="Trials")
    if not succeeded:
        return figures, ["No successful scored runs in this selection."]
    short = lambda t: t["trial_id"][:10] + " · " + t["family"]
    ordered = sorted(succeeded, key=lambda t: (t.get("finished_at") or t.get("created_at") or "", t["trial_id"]))
    trajectory = go.Figure()
    for family in sorted({t["family"] for t in ordered}):
        group = [t for t in ordered if t["family"] == family]
        best, running = float("inf"), []
        for trial in group:
            best = min(best, trial["mean_brier"])
            running.append(best)
        trajectory.add_trace(go.Scatter(x=[t.get("finished_at") or t["created_at"] for t in group], y=running,
            mode="lines+markers", name=family, text=[short(t) for t in group]))
    trajectory.update_layout(title="Best observed grouped Brier over time", xaxis_title="Trial completion", yaxis_title="Sampled Brier ↓")
    figures["trajectory"] = trajectory
    pareto = pareto_ids(succeeded)
    cost = go.Figure()
    for family in sorted({t["family"] for t in succeeded}):
        group = [t for t in succeeded if t["family"] == family]
        cost.add_trace(go.Scatter(x=[t["wall_seconds"] for t in group], y=[t["mean_brier"] for t in group],
            mode="markers", name=family, text=[short(t) for t in group], marker={"size": 12,
            "symbol": ["diamond" if t["trial_id"] in pareto else "circle" for t in group]}))
    cost.update_layout(title="Trial cost versus sampled error · diamonds are Pareto efficient",
                       xaxis_title="End-to-end trial wall seconds ↓", yaxis_title="Grouped sampled Brier ↓")
    figures["pareto"] = cost
    conditions = go.Figure(go.Heatmap(x=list(CONDITIONS), y=[short(t) for t in succeeded],
        z=[[t["result"]["by_condition"][c] for c in CONDITIONS] for t in succeeded], colorscale="Viridis_r",
        colorbar={"title": "Brier ↓"}))
    conditions.update_layout(title="Matched-fold condition errors")
    figures["conditions"] = conditions
    groups = sorted({g for t in succeeded for g in t["hyperparameters"].get("groups", [])})
    if groups:
        membership = go.Figure(go.Heatmap(x=groups, y=[short(t) for t in succeeded],
            z=[[int(g in t["hyperparameters"].get("groups", [])) for g in groups] for t in succeeded],
            customdata=[[t["mean_brier"] for _ in groups] for t in succeeded],
            hovertemplate="%{y}<br>%{x}: %{z}<br>Brier: %{customdata:.6f}<extra></extra>", showscale=False))
        membership.update_layout(title="Feature membership and observed error · exploratory associations")
        figures["ablations"] = membership
    numeric = [t for t in succeeded if type(t["hyperparameters"].get("params", {}).get(parameter)) in (int, float)]
    if numeric:
        sensitivity = go.Figure(go.Scatter(x=[t["hyperparameters"]["params"][parameter] for t in numeric],
            y=[t["mean_brier"] for t in numeric], text=[short(t) for t in numeric], mode="markers"))
        sensitivity.update_layout(title=f"Parameter association: {parameter}", xaxis_title=parameter, yaxis_title="Grouped sampled Brier ↓")
        figures["parameters"] = sensitivity
    if baseline_id:
        baseline = next((t for t in succeeded if t["trial_id"] == baseline_id), None)
        if baseline is None:
            blockers.append("Baseline is absent or unsuccessful in this selection.")
        else:
            comparisons = []
            for trial in succeeded:
                if trial["trial_id"] == baseline_id:
                    continue
                try:
                    result = comparison(trial, baseline, bootstrap=bootstrap)
                    comparisons.append((trial, result))
                except ValueError as exc:
                    blockers.append(short(trial) + ": " + str(exc))
            if comparisons:
                delta = [c[1]["mean_delta_brier"] for c in comparisons]
                confidence = go.Figure(go.Scatter(y=[short(c[0]) for c in comparisons], x=delta, mode="markers",
                    error_x={"type": "data", "symmetric": False,
                             "array": [max(0, c[1]["ci95"][1]-d) for c, d in zip(comparisons, delta)],
                             "arrayminus": [max(0, d-c[1]["ci95"][0]) for c, d in zip(comparisons, delta)]}))
                confidence.add_vline(x=0, line_dash="dash")
                confidence.update_layout(title="Paired episode differences with exploratory 95% intervals",
                                         xaxis_title="Candidate − baseline Brier · negative favors candidate")
                figures["paired_ci"] = confidence
    chosen = next((t for t in succeeded if t["trial_id"] == diagnostic_id), min(succeeded, key=lambda t: t["mean_brier"]))
    cal = calibration(chosen)
    reliability = go.Figure(go.Scatter(x=[0, 1], y=[0, 1], mode="lines", name="Ideal", line={"dash": "dash", "color": "gray"}))
    for k, payout in enumerate(PAYOUTS):
        bins = [b for b in cal["bins"] if b["class"] == k]
        reliability.add_trace(go.Scatter(x=[b["predicted"] for b in bins], y=[b["observed"] for b in bins],
            mode="lines+markers", name=f"Payout {payout}", customdata=[b["count"] for b in bins],
            hovertemplate="Predicted %{x:.3f}<br>Observed %{y:.3f}<br>Bin n=%{customdata}<extra>%{fullData.name}</extra>"))
    reliability.update_layout(title="Class reliability · " + short(chosen), xaxis_title="Mean forecast probability", yaxis_title="Observed class frequency")
    figures["calibration"] = reliability
    matrix = go.Figure(go.Heatmap(x=[str(p) for p in PAYOUTS], y=[str(p) for p in PAYOUTS],
        z=cal["mean_probability_by_observed_class"], zmin=0, zmax=1, colorscale="Blues"))
    matrix.update_layout(title="Mean assigned probability by observed payout · " + short(chosen),
                         xaxis_title="Predicted payout class", yaxis_title="Observed payout class")
    figures["probability_diagnostics"] = matrix
    residuals = []
    for condition in CONDITIONS:
        evidence = [r for r in chosen["result"]["per_query"] if r["condition"] == condition]
        residuals.append([sum(r["probabilities"][k] - (r["label"] == k) for r in evidence)/len(evidence) for k in range(5)])
    residual = go.Figure(go.Heatmap(x=[str(p) for p in PAYOUTS], y=list(CONDITIONS), z=residuals, zmid=0, colorscale="RdBu"))
    residual.update_layout(title="Condition calibration residuals · predicted minus observed rate")
    figures["condition_residuals"] = residual
    for figure in figures.values():
        figure.update_layout(template="plotly_white", margin={"t": 60, "b": 45, "l": 65, "r": 30}, height=420)
    return figures, blockers
