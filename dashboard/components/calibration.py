"""5-class probability calibration curves, Murphy decomposition, and rare payout (20x) tail diagnostics."""

from __future__ import annotations

from typing import List, Optional

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from ..adapter import ExperimentStore
from ..config import CLASS_COLORS, COLOR_PALETTE, PAYOUT_CLASSES, apply_plotly_dark_theme
from ..schema import CalibrationBin, RarePayoutDiagnostic


def create_reliability_diagram(
    bins: List[CalibrationBin], selected_class: Optional[int] = None
) -> go.Figure:
    """Create 5-class reliability diagram across 10 probability bins with ideal diagonal."""
    fig = go.Figure()

    # Ideal diagonal reference line
    fig.add_trace(
        go.Scatter(
            x=[0.0, 1.0],
            y=[0.0, 1.0],
            mode="lines",
            line=dict(color=COLOR_PALETTE["text_muted"], width=1.5, dash="dash"),
            name="Perfect Calibration (y = x)",
        )
    )

    # Filter bins by class if requested
    classes = [selected_class] if selected_class is not None else list(PAYOUT_CLASSES)

    for c in classes:
        c_bins = [b for b in bins if b.payout_class == c]
        if not c_bins:
            continue

        c_bins = sorted(c_bins, key=lambda b: b.bin_index)
        mean_preds = [b.mean_predicted for b in c_bins]
        obs_freqs = [b.observed_frequency for b in c_bins]
        counts = [b.sample_count for b in c_bins]

        color = CLASS_COLORS.get(c, COLOR_PALETTE["primary"])

        fig.add_trace(
            go.Scatter(
                x=mean_preds,
                y=obs_freqs,
                mode="lines+markers",
                name=f"Class {c}x",
                line=dict(color=color, width=2.5),
                marker=dict(size=8, color=color),
                hoverinfo="text",
                hovertext=[
                    f"Class: {c}x<br>Bin: [{b.bin_range[0]:.2f}, {b.bin_range[1]:.2f}]<br>"
                    f"Mean Pred: {mp:.4f}<br>Observed: {of:.4f}<br>Samples: {cnt}"
                    for b, mp, of, cnt in zip(c_bins, mean_preds, obs_freqs, counts)
                ],
            )
        )

    fig.update_layout(
        title="5-Class Reliability Diagram (10 Probability Bins)",
        xaxis_title="Mean Predicted Probability P(Y = c)",
        yaxis_title="Empirical Observed Frequency",
        xaxis=dict(range=[0.0, 1.0]),
        yaxis=dict(range=[0.0, 1.0]),
        height=450,
    )
    apply_plotly_dark_theme(fig)
    return fig


def render_calibration_view(store: ExperimentStore) -> None:
    """Render probability calibration, Murphy decomposition, and 20x jackpot diagnostics."""
    st.subheader("🎯 Probability Calibration & Rare Payout Tail Risk")
    st.markdown(
        "Reliability analysis of multi-class probabilistic forecasts across all 5 payout classes "
        "($0x, 1x, 2x, 5x, 20x$) and extreme event risk assessment."
    )

    bins = store.get_calibration_bins()
    rare_diag = store.get_rare_payout_diagnostic()

    if not bins and not rare_diag:
        st.info("No probability calibration curves or tail diagnostics available in store.")
        return

    # Top KPI highlights
    if rare_diag:
        st.markdown("### 🎰 Rare Jackpot (20x) Tail Risk Summary")
        r_col1, r_col2, r_col3, r_col4, r_col5 = st.columns(5)
        with r_col1:
            st.metric("Realized Payout MAE", f"{rare_diag.mae:.4f}" if rare_diag.mae is not None else "N/A")
        with r_col2:
            st.metric("80% Predictive CI Width", f"{rare_diag.ci80_width:.4f}" if rare_diag.ci80_width is not None else "N/A")
        with r_col3:
            st.metric("20x Calibration Correlation", f"{rare_diag.calibration_correlation:.4f}")
        with r_col4:
            st.metric("True 20x Base Rate", f"{rare_diag.true_frequency:.2%}")
        with r_col5:
            st.metric("Under/Over Prediction Ratio", f"{rare_diag.under_over_prediction_ratio:.3f}")

        st.markdown("---")

    # Reliability Diagrams
    st.markdown("### 📊 Multi-Class Reliability Diagrams")
    class_choice = st.selectbox(
        "Select Payout Class to Highlight:",
        options=["ALL (Overlay All 5 Classes)"] + [f"{c}x Payout Class" for c in PAYOUT_CLASSES],
        index=0,
    )

    selected_c = None
    if class_choice != "ALL (Overlay All 5 Classes)":
        selected_c = int(class_choice.split("x")[0])

    rel_fig = create_reliability_diagram(bins, selected_class=selected_c)
    st.plotly_chart(rel_fig, use_container_width=True)

    # Detailed Brier Decomposition & Bins Table
    st.markdown("### 📋 Murphy (1973) Brier Score Decomposition")
    st.markdown(
        "$$\\text{Brier Score} = \\text{Reliability} - \\text{Resolution} + \\text{Uncertainty}$$\n"
        "- **Reliability (Calibration Loss)**: Measures weighted deviation from ideal diagonal (lower is better, 0 is perfect).\n"
        "- **Resolution**: Measures ability to separate distinct outcome regimes (higher is better).\n"
        "- **Uncertainty**: Inherent irreducible entropy of the outcome distribution."
    )

    # Class summary metrics table
    summary_rows = []
    for c in PAYOUT_CLASSES:
        c_bins = [b for b in bins if b.payout_class == c]
        if c_bins:
            total_samples = sum(b.sample_count for b in c_bins)
            weighted_ece = sum(abs(b.mean_predicted - b.observed_frequency) * b.sample_count for b in c_bins) / max(total_samples, 1)
            max_ce = max(abs(b.mean_predicted - b.observed_frequency) for b in c_bins)
            summary_rows.append(
                {
                    "Payout Class": f"{c}x",
                    "Total Samples": total_samples,
                    "Expected Calibration Error (ECE)": weighted_ece,
                    "Maximum Calibration Error (MCE)": max_ce,
                    "Reliability Status": "Well-Calibrated" if weighted_ece < 0.05 else "Miscalibrated",
                }
            )

    if summary_rows:
        st.dataframe(
            pd.DataFrame(summary_rows).style.format(
                {
                    "Expected Calibration Error (ECE)": "{:.6f}",
                    "Maximum Calibration Error (MCE)": "{:.6f}",
                }
            ),
            use_container_width=True,
            hide_index=True,
        )

    # Raw Bin Data Expander
    with st.expander("🔍 View All 10 Calibration Bins per Payout Class", expanded=False):
        raw_rows = [
            {
                "Class": f"{b.payout_class}x",
                "Bin Index": b.bin_index,
                "Range": f"[{b.bin_range[0]:.2f}, {b.bin_range[1]:.2f}]",
                "Count": b.sample_count,
                "Mean Predicted": b.mean_predicted,
                "Observed Freq": b.observed_frequency,
                "Diff (|Pred - Obs|)": abs(b.mean_predicted - b.observed_frequency),
            }
            for b in bins
        ]
        st.dataframe(
            pd.DataFrame(raw_rows).style.format(
                {
                    "Mean Predicted": "{:.4f}",
                    "Observed Freq": "{:.4f}",
                    "Diff (|Pred - Obs|)": "{:.4f}",
                }
            ),
            use_container_width=True,
            hide_index=True,
        )
