"""Component ablation study explorer and feature group importance visualization."""

from __future__ import annotations

from typing import Dict, List, Optional

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from ..adapter import ExperimentStore
from ..config import COLOR_PALETTE, apply_plotly_dark_theme, format_points
from ..schema import ComponentAblation
from ..stats import analyze_component_ablations


def create_ablation_waterfall_chart(
    ablations: List[ComponentAblation], baseline_points: float = 55.121615
) -> go.Figure:
    """Create waterfall chart showing cumulative or relative impact of removing components."""
    fig = go.Figure()

    analysis = analyze_component_ablations(ablations, baseline_points=baseline_points)

    x_labels = ["Baseline Champion"]
    y_vals = [baseline_points]
    measures = ["absolute"]
    text_labels = [f"{baseline_points:.4f}"]

    for item in analysis.ranked_ablations:
        x_labels.append(item.variant_name)
        # Delta points is negative when performance degrades
        y_vals.append(item.delta_points)
        measures.append("relative")
        text_labels.append(f"{item.delta_points:+.4f}")

    fig.add_trace(
        go.Waterfall(
            name="Ablation Impact",
            orientation="v",
            measure=measures,
            x=x_labels,
            y=y_vals,
            text=text_labels,
            textposition="outside",
            decreasing=dict(marker=dict(color=COLOR_PALETTE["danger"])),
            increasing=dict(marker=dict(color=COLOR_PALETTE["success"])),
            totals=dict(marker=dict(color=COLOR_PALETTE["champion"])),
            connector=dict(line=dict(color=COLOR_PALETTE["grid"], width=1, dash="dot")),
        )
    )

    fig.update_layout(
        title="Component Ablation Impact on Technical Points (HE-17 Benchmarks)",
        xaxis_title="Removed Component Variant",
        yaxis_title="Official Points (0-60 Scale)",
        waterfallgap=0.3,
        height=480,
    )
    apply_plotly_dark_theme(fig)
    return fig


def create_feature_group_importance_chart(feature_importance: Dict[str, float]) -> go.Figure:
    """Create horizontal bar chart of feature group importances."""
    fig = go.Figure()

    # Aggregate by family prefix (e.g. lags/lag1 -> lags)
    grouped: Dict[str, float] = {}
    for feat, score in feature_importance.items():
        family = feat.split("/")[0] if "/" in feat else feat.split("_")[0]
        grouped[family] = grouped.get(family, 0.0) + float(score)

    sorted_groups = sorted(grouped.items(), key=lambda x: x[1], reverse=False)
    families = [k for k, _ in sorted_groups]
    scores = [v for _, v in sorted_groups]

    fig.add_trace(
        go.Bar(
            y=families,
            x=scores,
            orientation="h",
            marker=dict(
                color=COLOR_PALETTE["primary"],
                line=dict(color=COLOR_PALETTE["text"], width=1),
            ),
            text=[f"{s:.3f}" for s in scores],
            textposition="auto",
        )
    )

    fig.update_layout(
        title="Relative Feature Family Importance Breakdown",
        xaxis_title="Aggregate Importance Score",
        yaxis_title="Feature Family",
        height=380,
    )
    apply_plotly_dark_theme(fig)
    return fig


def render_ablations_view(store: ExperimentStore) -> None:
    """Render HE-17 component ablation explorer and feature importance views."""
    st.subheader("🧩 Pre-Registered Component Ablation Explorer")
    st.markdown(
        "Scientific validation of individual architectural modules from HE-17. "
        "Each variant removes one component from the Champion model to isolate its performance contribution."
    )

    ablations = store.list_ablations()
    if not ablations:
        st.info("No pre-registered component ablations found in store.")
        return

    champion = store.get_champion()
    champ_points = champion.official_points if champion and champion.official_points else 55.121615

    # Top KPI highlights
    analysis = analyze_component_ablations(ablations, baseline_points=champ_points)

    kpi1, kpi2, kpi3 = st.columns(3)
    with kpi1:
        st.metric("Total Ablation Variants", len(ablations))
    with kpi2:
        st.metric("Max Impact Component (Most Critical)", analysis.max_impact_component)
    with kpi3:
        st.metric("Supported Degradations", f"{analysis.supported_degradations_count} / {len(ablations)}")

    st.markdown("---")

    # Waterfall Chart Tab and Table Tab
    tab1, tab2, tab3 = st.tabs(["📉 Waterfall Impact Chart", "📋 Ablation Evidence Table", "📊 Feature Group Importance"])

    with tab1:
        waterfall_fig = create_ablation_waterfall_chart(ablations, baseline_points=champ_points)
        st.plotly_chart(waterfall_fig, use_container_width=True)

    with tab2:
        table_rows = []
        for a in analysis.ranked_ablations:
            status_badge = (
                "🔴 Supported Degradation"
                if a.status == "SUPPORTED_DEGRADATION"
                else ("🟢 Supported Improvement" if a.status == "SUPPORTED_IMPROVEMENT" else "🟡 Inconclusive")
            )
            table_rows.append(
                {
                    "Variant": a.variant_name,
                    "Removed Component": a.removed_component,
                    "Hypothesis": a.hypothesis,
                    "Official Points": a.official_points,
                    "Δ Points": a.delta_points,
                    "% Δ": f"{a.pct_delta_points:+.2f}%",
                    "95% CI (Points)": f"[{a.ci95_points[0]:.4f}, {a.ci95_points[1]:.4f}]",
                    "Significance Tag": status_badge,
                }
            )
        df_abl = pd.DataFrame(table_rows)
        st.dataframe(
            df_abl.style.format(
                {
                    "Official Points": "{:.4f}",
                    "Δ Points": "{:+.4f}",
                }
            ),
            use_container_width=True,
            hide_index=True,
        )

    with tab3:
        # Check if champion or any trial has feature importance
        champ_feat_imp = champion.feature_importance if champion else None
        if not champ_feat_imp:
            # Fall back to first trial with feature importance
            trials = store.list_trials()
            for t in trials:
                if t.feature_importance:
                    champ_feat_imp = t.feature_importance
                    break

        if champ_feat_imp:
            feat_fig = create_feature_group_importance_chart(champ_feat_imp)
            st.plotly_chart(feat_fig, use_container_width=True)

            with st.expander("View Raw Feature Importance Weights", expanded=False):
                st.json(champ_feat_imp)
        else:
            st.info("Feature importance data is not available for current models.")
