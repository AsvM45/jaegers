"""Evaluation provenance rules, 4-condition comparisons, and loss ratio analysis."""

from __future__ import annotations

from typing import List, Optional

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from ..adapter import ExperimentStore
from ..config import (
    COLOR_PALETTE,
    CONTEST_CONDITIONS,
    CONDITION_COLORS,
    apply_plotly_dark_theme,
    format_points,
)
from ..provenance import PROVENANCE_METADATA, calculate_official_points, get_provenance_badge
from ..schema import ProvenanceType, TrialRecord


def create_4condition_bar_chart(trials: List[TrialRecord]) -> go.Figure:
    """Create multi-model grouped bar chart for 4 contest condition loss ratios."""
    fig = go.Figure()

    for trial in trials:
        if not trial.condition_losses:
            continue
        cl = trial.condition_losses
        champ_tag = "🏆 " if trial.is_champion else ""
        name = f"{champ_tag}{trial.trial_id}"

        ratios = [cl.stable, cl.short_history, cl.drift, cl.shared_change]
        fig.add_trace(
            go.Bar(
                name=name,
                x=list(CONTEST_CONDITIONS),
                y=ratios,
                text=[f"{r:.4f}" for r in ratios],
                textposition="auto",
            )
        )

    fig.update_layout(
        title="4-Condition Loss Ratio Comparison ($E_c / B_c$ — Lower is Better)",
        xaxis_title="Contest Condition",
        yaxis_title="Loss Ratio (vs Baseline)",
        barmode="group",
        height=450,
    )
    apply_plotly_dark_theme(fig)
    return fig


def create_4condition_radar_chart(trials: List[TrialRecord]) -> go.Figure:
    """Create radar (spider) chart comparing condition profiles across selected models."""
    fig = go.Figure()
    categories = list(CONTEST_CONDITIONS) + [CONTEST_CONDITIONS[0]]  # Close polygon

    for trial in trials:
        if not trial.condition_losses:
            continue
        cl = trial.condition_losses
        champ_tag = "🏆 " if trial.is_champion else ""
        name = f"{champ_tag}{trial.trial_id}"

        values = [cl.stable, cl.short_history, cl.drift, cl.shared_change, cl.stable]
        fig.add_trace(
            go.Scatterpolar(
                r=values,
                theta=categories,
                fill="toself",
                name=name,
                opacity=0.6,
            )
        )

    fig.update_layout(
        polar=dict(
            radialaxis=dict(
                visible=True,
                showgrid=True,
                gridcolor=COLOR_PALETTE["grid"],
                color=COLOR_PALETTE["text_muted"],
            ),
            angularaxis=dict(
                gridcolor=COLOR_PALETTE["grid"],
                color=COLOR_PALETTE["text"],
            ),
            bgcolor=COLOR_PALETTE["paper_bg"],
        ),
        showlegend=True,
        title="Condition Sensitivity Radar (Loss Ratios across 4 Regimes)",
        height=480,
    )
    apply_plotly_dark_theme(fig)
    return fig


def render_provenance_view(store: ExperimentStore) -> None:
    """Render provenance guidelines, warning cards, and 4-condition breakdowns."""
    st.subheader("🛡️ Evaluation Provenance & 4-Condition Analytics")
    st.markdown(
        "Strict separation of evaluation contexts to prevent scientific confounding, "
        "data leakage, and invalid cross-split comparisons."
    )

    # Provenance Cards & Warning Banners
    st.markdown("### 📋 Provenance Separation Standards")

    p_cols = st.columns(len(PROVENANCE_METADATA))
    for col, (ptype, meta) in zip(p_cols, PROVENANCE_METADATA.items()):
        with col:
            st.markdown(
                f"""
                <div style="background-color: #1e222d; border-top: 3px solid {meta['color']};
                            padding: 12px; border-radius: 6px; height: 260px; margin-bottom: 15px;">
                    <h5 style="color: {meta['color']}; margin-top: 0;">{meta['badge']}</h5>
                    <strong style="color: #e2e8f0; font-size: 13px;">{meta['display_name']}</strong>
                    <p style="color: #94a3b8; font-size: 11px; margin-top: 8px; line-height: 1.4;">
                        {meta['description']}
                    </p>
                </div>
                """,
                unsafe_allow_html=True,
            )

    st.markdown("---")

    # Contest Points Formula Explanation
    with st.expander("📐 Technical Points Formula Explanation ($60 / (1 + R)$)", expanded=False):
        st.latex(r"R = \frac{1}{4} \sum_{c \in \{\text{stable}, \text{short}, \text{drift}, \text{shared}\}} \frac{E_c}{\max(B_c, 10^{-9})}")
        st.latex(r"\text{Validation Points} = \frac{60}{1 + R}, \quad \text{Final Contest Points} = \frac{70}{1 + R}")
        st.markdown(
            "- **$E_c$**: Model candidate multi-class Brier error under condition $c$.\n"
            "- **$B_c$**: Baseline reference multi-class Brier error under condition $c$.\n"
            "- **$R$**: Arithmetic mean of condition loss ratios.\n"
            "- **Important Constraint**: Points are strictly defined for `PUBLIC_VALIDATION` only. "
            "Cross-validation runs on sampled labels (`TRAIN_GROUP_CV`) report unscaled Brier scores only."
        )

    # 4-Condition Analysis across trials with condition losses
    all_trials = store.list_trials()
    scored_trials = [t for t in all_trials if t.condition_losses is not None]

    if not scored_trials:
        st.info("No trials with 4-condition loss breakdowns found in store.")
        return

    st.markdown("### 📊 4-Condition Model Comparison")

    trial_choices = [t.trial_id for t in scored_trials]
    default_selection = trial_choices[: min(4, len(trial_choices))]
    selected_ids = st.multiselect(
        "Select Models to Compare:",
        options=trial_choices,
        default=default_selection,
    )

    selected_trials = [t for t in scored_trials if t.trial_id in selected_ids]

    if not selected_trials:
        st.warning("Please select at least one model to visualize.")
        return

    tab1, tab2 = st.tabs(["📊 Grouped Bar Chart", "🕸️ Radar Comparison"])

    with tab1:
        bar_fig = create_4condition_bar_chart(selected_trials)
        st.plotly_chart(bar_fig, use_container_width=True)

    with tab2:
        radar_fig = create_4condition_radar_chart(selected_trials)
        st.plotly_chart(radar_fig, use_container_width=True)

    # Condition Loss Ratios Data Table
    st.markdown("### 📑 Detailed Condition Loss Table")
    table_rows = []
    for t in selected_trials:
        cl = t.condition_losses
        table_rows.append(
            {
                "Model": f"🏆 {t.trial_id}" if t.is_champion else t.trial_id,
                "Provenance": get_provenance_badge(t.provenance),
                "Stable": cl.stable,
                "Short History": cl.short_history,
                "Drift": cl.drift,
                "Shared Change": cl.shared_change,
                "Mean Ratio R": cl.mean_ratio,
                "Official Points (0-60)": cl.points_60,
                "Contest Scale (0-70)": cl.points_70,
            }
        )
    df_cond = pd.DataFrame(table_rows)
    st.dataframe(
        df_cond.style.format(
            {
                "Stable": "{:.6f}",
                "Short History": "{:.6f}",
                "Drift": "{:.6f}",
                "Shared Change": "{:.6f}",
                "Mean Ratio R": "{:.6f}",
                "Official Points (0-60)": "{:.4f}",
                "Contest Scale (0-70)": "{:.4f}",
            }
        ),
        use_container_width=True,
        hide_index=True,
    )
