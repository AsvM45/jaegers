"""Hyperparameter sweep trajectories, parallel coordinates, and parameter correlations."""

from __future__ import annotations

from typing import List, Optional

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from ..adapter import ExperimentStore
from ..config import COLOR_PALETTE, apply_plotly_dark_theme, format_brier
from ..schema import HyperparameterSweepAnalysis, TrialRecord
from ..stats import analyze_hyperparameter_sweep


def create_sweep_trajectory_plot(analysis: HyperparameterSweepAnalysis) -> go.Figure:
    """Create optimization trajectory plot with individual trial metrics and running best."""
    fig = go.Figure()

    steps = [p["step"] for p in analysis.trajectory]
    metrics = [p["metric"] for p in analysis.trajectory]
    running_best = [p["running_best"] for p in analysis.trajectory]
    trial_ids = [p["trial_id"] for p in analysis.trajectory]

    # Individual trial evaluations scatter
    fig.add_trace(
        go.Scatter(
            x=steps,
            y=metrics,
            mode="markers",
            marker=dict(size=8, color=COLOR_PALETTE["primary"], opacity=0.7),
            name="Trial Evaluation",
            hoverinfo="text",
            hovertext=[f"Step {s}: {tid}<br>Metric: {m:.6f}" for s, tid, m in zip(steps, trial_ids, metrics)],
        )
    )

    # Running best step line
    fig.add_trace(
        go.Scatter(
            x=steps,
            y=running_best,
            mode="lines",
            line=dict(color=COLOR_PALETTE["champion"], width=2.5, shape="hv"),
            name=f"Running Best ({analysis.best_metric_value:.6f})",
        )
    )

    fig.update_layout(
        title=f"Hyperparameter Optimization Trajectory (Best: {analysis.best_trial_id})",
        xaxis_title="Trial Sequence / Step",
        yaxis_title="Objective Metric (Lower is Better)",
        height=400,
    )
    apply_plotly_dark_theme(fig)
    return fig


def create_parallel_coordinates_plot(analysis: HyperparameterSweepAnalysis) -> go.Figure:
    """Create parallel coordinates plot showing multi-dimensional parameter search configurations."""
    fig = go.Figure()

    p_data = analysis.parallel_coords_data
    if not p_data or not p_data.get("dimensions"):
        fig.add_annotation(text="Insufficient multi-dimensional parameters for parallel coordinates", showarrow=False)
        apply_plotly_dark_theme(fig)
        return fig

    dims = []
    for d in p_data["dimensions"]:
        dims.append(
            dict(
                label=d.get("label", d.get("name", "")),
                values=d["values"],
            )
        )

    color_vals = p_data.get("color", p_data.get("metrics", []))

    fig.add_trace(
        go.Parcoords(
            line=dict(
                color=color_vals,
                colorscale="Viridis",
                showscale=True,
                colorbar=dict(title="Metric"),
            ),
            dimensions=dims,
        )
    )

    fig.update_layout(
        title="Multi-Dimensional Hyperparameter Search Space",
        height=450,
    )
    apply_plotly_dark_theme(fig)
    return fig


def create_param_correlation_chart(analysis: HyperparameterSweepAnalysis) -> go.Figure:
    """Create bar chart showing Pearson correlation between each hyperparameter and objective."""
    fig = go.Figure()

    corrs = analysis.param_correlations
    if not corrs:
        fig.add_annotation(text="No numeric parameter correlations available", showarrow=False)
        apply_plotly_dark_theme(fig)
        return fig

    # Sort descending
    sorted_corrs = sorted(corrs.items(), key=lambda x: abs(x[1]), reverse=True)
    params = [k for k, _ in sorted_corrs]
    values = [v for _, v in sorted_corrs]

    colors = [COLOR_PALETTE["danger"] if v > 0 else COLOR_PALETTE["success"] for v in values]

    fig.add_trace(
        go.Bar(
            x=params,
            y=values,
            marker=dict(color=colors),
            text=[f"{v:+.3f}" for v in values],
            textposition="auto",
        )
    )

    fig.add_hline(y=0.0, line_width=1, line_color=COLOR_PALETTE["text_muted"])

    fig.update_layout(
        title="Parameter Sensitivity & Correlation with Loss (Negative = Loss Decreases as Param Increases)",
        xaxis_title="Hyperparameter",
        yaxis_title="Pearson Correlation (r)",
        height=380,
    )
    apply_plotly_dark_theme(fig)
    return fig


def render_hyperparameters_view(store: ExperimentStore) -> None:
    """Render hyperparameter sweep exploration, parallel coordinates, and sensitivities."""
    st.subheader("🎛️ Hyperparameter Optimization & Sweep Space")
    st.markdown(
        "Exploration of automated Optuna search trials, parameter correlation with predictive loss, "
        "and multi-dimensional parallel coordinate trajectories."
    )

    trials = store.list_trials()
    trials_with_params = [t for t in trials if t.hyperparameters]

    if not trials_with_params:
        st.info("No trials with logged hyperparameters found in store.")
        return

    # User metric choice
    opt_col1, opt_col2 = st.columns([2, 1])
    with opt_col1:
        metric_choice = st.selectbox(
            "Optimization Objective Metric:",
            ["mean_brier", "official_points"],
            index=0,
            help="mean_brier (minimize) or official_points (maximize)",
        )
    with opt_col2:
        study_filter = st.selectbox(
            "Filter by Study:",
            ["ALL"] + sorted(list({t.study_name for t in trials_with_params})),
            index=0,
        )

    eval_trials = trials_with_params
    if study_filter != "ALL":
        eval_trials = [t for t in eval_trials if t.study_name == study_filter]

    maximize = (metric_choice == "official_points")
    analysis = analyze_hyperparameter_sweep(eval_trials, metric_key=metric_choice, maximize=maximize)

    if not analysis.trajectory:
        st.warning("Could not construct sweep trajectory from the selected trials.")
        return

    # Top KPI summary
    kpi1, kpi2, kpi3 = st.columns(3)
    with kpi1:
        st.metric("Total Sweep Trials", len(analysis.trajectory))
    with kpi2:
        st.metric("Best Trial ID", analysis.best_trial_id)
    with kpi3:
        st.metric(
            f"Best {metric_choice}",
            format_brier(analysis.best_metric_value) if "brier" in metric_choice else f"{analysis.best_metric_value:.4f}",
        )

    st.markdown("---")

    tab1, tab2, tab3 = st.tabs(["📈 Optimization Trajectory", "🌐 Parallel Coordinates", "📊 Parameter Correlations"])

    with tab1:
        traj_fig = create_sweep_trajectory_plot(analysis)
        st.plotly_chart(traj_fig, use_container_width=True)

    with tab2:
        par_fig = create_parallel_coordinates_plot(analysis)
        st.plotly_chart(par_fig, use_container_width=True)

    with tab3:
        corr_fig = create_param_correlation_chart(analysis)
        st.plotly_chart(corr_fig, use_container_width=True)

        if analysis.param_importance_rank:
            st.markdown("### 🏆 Parameter Importance Ranking")
            rank_df = pd.DataFrame(
                [{"Hyperparameter": p, "Relative Correlation": f"{s:.4f}"} for p, s in analysis.param_importance_rank]
            )
            st.dataframe(rank_df, use_container_width=True, hide_index=True)
