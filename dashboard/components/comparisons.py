"""Paired episode statistical difference analysis and bootstrap uncertainty visualization."""

from __future__ import annotations

from typing import Optional

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from ..adapter import ExperimentStore
from ..config import (
    COLOR_PALETTE,
    CONDITION_COLORS,
    apply_plotly_dark_theme,
    format_brier,
)
from ..provenance import get_provenance_badge, validate_comparison_compatibility
from ..schema import PairedComparison, TrialRecord


def create_forest_plot(comp: PairedComparison) -> go.Figure:
    """Create forest plot displaying mean delta and 95% bootstrap confidence interval.

    Convention:
        Delta = Error(Candidate) - Error(Baseline).
        Negative Delta (< 0) -> Candidate is Better (Lower Error).
        Positive Delta (> 0) -> Candidate is Worse (Degradation).
    """
    fig = go.Figure()

    # Determine status color
    if comp.supported_improvement:
        marker_color = COLOR_PALETTE["success"]  # Green
        status_text = "Supported Improvement (95% CI < 0)"
    elif comp.ci95_low > 0:
        marker_color = COLOR_PALETTE["danger"]   # Red
        status_text = "Significant Degradation (95% CI > 0)"
    else:
        marker_color = COLOR_PALETTE["warning"]  # Amber
        status_text = "Inconclusive (95% CI spans 0)"

    # Main overall comparison trace
    fig.add_trace(
        go.Scatter(
            x=[comp.mean_delta],
            y=["Overall Mean Delta"],
            error_x=dict(
                type="data",
                symmetric=False,
                array=[comp.ci95_high - comp.mean_delta],
                arrayminus=[comp.mean_delta - comp.ci95_low],
                color=marker_color,
                thickness=3,
                width=10,
            ),
            mode="markers",
            marker=dict(size=14, color=marker_color, symbol="diamond"),
            name=f"Overall Delta ({comp.mean_delta:.6f})",
            hoverinfo="text",
            hovertext=(
                f"Overall Delta: {comp.mean_delta:.6f}<br>"
                f"95% CI: [{comp.ci95_low:.6f}, {comp.ci95_high:.6f}]<br>"
                f"P(Δ < 0): {comp.p_improvement:.1%}<br>"
                f"Verdict: {status_text}"
            ),
        )
    )

    # Condition-level delta points if available
    if comp.by_condition_delta:
        cond_names = list(comp.by_condition_delta.keys())
        cond_deltas = [comp.by_condition_delta[c] for c in cond_names]
        colors = [CONDITION_COLORS.get(c, COLOR_PALETTE["primary"]) for c in cond_names]

        fig.add_trace(
            go.Scatter(
                x=cond_deltas,
                y=[f"Condition: {c}" for c in cond_names],
                mode="markers",
                marker=dict(size=10, color=colors, symbol="circle"),
                name="Condition Deltas",
                hoverinfo="text",
                hovertext=[f"Condition {c}: Δ = {d:.6f}" for c, d in zip(cond_names, cond_deltas)],
            )
        )

    # Reference zero line
    fig.add_vline(x=0.0, line_width=1.5, line_dash="dash", line_color=COLOR_PALETTE["text_muted"])

    # Annotation zones
    fig.add_annotation(
        x=-0.001,
        y=0.98,
        yref="paper",
        xref="x",
        text="← Candidate Better (Lower Error)",
        showarrow=False,
        font=dict(color=COLOR_PALETTE["success"], size=11),
    )
    fig.add_annotation(
        x=0.001,
        y=0.98,
        yref="paper",
        xref="x",
        text="Candidate Worse (Degradation) →",
        showarrow=False,
        font=dict(color=COLOR_PALETTE["danger"], size=11),
    )

    fig.update_layout(
        title=f"Forest Plot: Paired Episode Difference (95% Bootstrap CI, B={comp.bootstrap_iterations})",
        xaxis_title="Loss Difference Δ = Error(Cand) - Error(Base)",
        yaxis_title="",
        height=380,
    )
    apply_plotly_dark_theme(fig)
    return fig


def create_episode_scatter_plot(comp: PairedComparison) -> go.Figure:
    """Create scatter plot of per-episode error differences."""
    fig = go.Figure()

    if not comp.episode_deltas:
        fig.add_annotation(text="No per-episode error differences available", showarrow=False)
        apply_plotly_dark_theme(fig)
        return fig

    episodes = list(comp.episode_deltas.keys())
    deltas = list(comp.episode_deltas.values())

    colors = [COLOR_PALETTE["success"] if d < 0 else COLOR_PALETTE["danger"] for d in deltas]

    fig.add_trace(
        go.Scatter(
            x=episodes,
            y=deltas,
            mode="markers+lines",
            marker=dict(size=9, color=colors),
            line=dict(color=COLOR_PALETTE["grid"], width=1, dash="dot"),
            name="Episode Δ",
            hoverinfo="text",
            hovertext=[f"Episode: {ep}<br>Δ: {d:.6f}" for ep, d in zip(episodes, deltas)],
        )
    )

    fig.add_hline(y=0.0, line_width=1.5, line_dash="dash", line_color=COLOR_PALETTE["text_muted"])
    fig.add_hline(y=comp.mean_delta, line_width=1.5, line_color=COLOR_PALETTE["primary"], line_dash="solid")

    fig.update_layout(
        title="Per-Episode Loss Differences Across Held-Out Episodes",
        xaxis_title="Held-Out Episode",
        yaxis_title="Episode Δ = Cand - Base",
        height=380,
    )
    apply_plotly_dark_theme(fig)
    return fig


def render_comparisons_view(store: ExperimentStore) -> None:
    """Render paired comparison selector, compatibility blocker, and statistical plots."""
    st.subheader("⚖️ Paired Episode Statistical Comparisons")
    st.markdown(
        "Direct model-to-model paired difference testing across held-out evaluation episodes. "
        "Evaluates the statistical hypothesis $P(\\Delta < 0)$ using stratified bootstrap confidence intervals."
    )

    trials = store.list_trials()
    if len(trials) < 2:
        st.info("At least two trials are required to perform model comparisons.")
        return

    champion = store.get_champion()
    champ_id = champion.trial_id if champion else trials[0].trial_id

    trial_ids = [t.trial_id for t in trials]

    sel_col1, sel_col2, sel_col3 = st.columns([2, 2, 1.5])
    with sel_col1:
        candidate_id = st.selectbox("Candidate Model:", trial_ids, index=min(1, len(trial_ids) - 1))
    with sel_col2:
        default_base_idx = trial_ids.index(champ_id) if champ_id in trial_ids else 0
        baseline_id = st.selectbox("Baseline Reference Model:", trial_ids, index=default_base_idx)
    with sel_col3:
        n_boot = st.selectbox("Bootstrap Resamples:", [500, 1000, 2000, 5000], index=2)

    cand_trial = next((t for t in trials if t.trial_id == candidate_id), None)
    base_trial = next((t for t in trials if t.trial_id == baseline_id), None)

    if not cand_trial or not base_trial:
        st.error("Selected trials not found in store.")
        return

    # Compatibility check
    is_valid, blocker_reason = validate_comparison_compatibility(cand_trial, base_trial)

    if not is_valid:
        st.markdown(
            f"""
            <div style="background-color: #3b181e; border: 2px solid #ef4444; border-radius: 8px; padding: 18px; margin: 20px 0;">
                <h4 style="color: #ef4444; margin-top: 0;">🚫 Comparison Blocked by Provenance Engine</h4>
                <p style="color: #fca5a5; font-size: 14px; margin-bottom: 8px;">
                    {blocker_reason}
                </p>
                <div style="color: #cbd5e1; font-size: 12px;">
                    <strong>Candidate:</strong> {cand_trial.trial_id} ({cand_trial.provenance.value} {get_provenance_badge(cand_trial.provenance)})<br>
                    <strong>Baseline:</strong> {base_trial.trial_id} ({base_trial.provenance.value} {get_provenance_badge(base_trial.provenance)})
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        return

    # Compute comparison
    with st.spinner("Computing paired condition-stratified bootstrap..."):
        comp = store.get_paired_comparison(candidate_id, baseline_id, bootstrap=n_boot)

    if not comp:
        st.warning("Could not compute paired comparison. Check that models provide compatible per-episode errors.")
        return

    # Statistical Highlights Banner
    st.markdown("### 📈 Statistical Difference Summary")

    stat_col1, stat_col2, stat_col3, stat_col4 = st.columns(4)
    with stat_col1:
        st.metric("Mean Δ Brier", f"{comp.mean_delta:.6f}")
    with stat_col2:
        ci_str = f"[{comp.ci95_low:.6f}, {comp.ci95_high:.6f}]"
        st.metric("95% Bootstrap CI", ci_str)
    with stat_col3:
        st.metric("P(Δ < 0)", f"{comp.p_improvement:.1%}")
    with stat_col4:
        if comp.supported_improvement:
            st.success("✅ Supported Improvement")
        elif comp.ci95_low > 0:
            st.error("❌ Significant Degradation")
        else:
            st.warning("⚠️ Inconclusive Difference")

    # Plots
    plot_tab1, plot_tab2 = st.tabs(["🌲 Forest Plot (95% CI)", "📉 Per-Episode Scatter"])

    with plot_tab1:
        forest_fig = create_forest_plot(comp)
        st.plotly_chart(forest_fig, use_container_width=True)

    with plot_tab2:
        scatter_fig = create_episode_scatter_plot(comp)
        st.plotly_chart(scatter_fig, use_container_width=True)

    # Condition breakdown table
    if comp.by_condition_delta:
        st.markdown("### 🏷️ Condition-Level Differences")
        cond_rows = []
        for cond, delta in comp.by_condition_delta.items():
            status = "Candidate Better" if delta < 0 else "Candidate Worse"
            cond_rows.append({"Condition": cond, "Delta Brier": delta, "Outcome": status})
        st.dataframe(pd.DataFrame(cond_rows), use_container_width=True, hide_index=True)
