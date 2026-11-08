"""Formal hypothesis tracking board with decision tags and pre-registration audits."""

from __future__ import annotations

from typing import List, Optional

import pandas as pd
import streamlit as st

from ..adapter import ExperimentStore
from ..schema import HypothesisRecord


def build_hypotheses_df(hypotheses: List[HypothesisRecord]) -> pd.DataFrame:
    """Convert list of HypothesisRecords into structured display DataFrame."""
    rows = []
    for h in hypotheses:
        rows.append(
            {
                "ID": h.id,
                "Pre-registered": h.preregistered_timestamp,
                "Component": h.component,
                "Statement": h.statement,
                "Expected Direction": h.expected_direction,
                "Δ Points": h.observed_points_diff if h.observed_points_diff is not None else float("nan"),
                "Δ Brier": h.observed_brier_diff if h.observed_brier_diff is not None else float("nan"),
                "Status": h.verdict,
                "Decision": h.decision,
                "Linked Trial": h.linked_trial_id or "—",
            }
        )
    return pd.DataFrame(rows)


def render_hypotheses_view(store: ExperimentStore) -> None:
    """Render hypothesis tracking board, status filters, and decision audits."""
    st.subheader("🔬 Pre-Registered Hypothesis Tracking Board")
    st.markdown(
        "Formal tracking of scientific hypotheses pre-registered prior to running sweeps. "
        "Enforces pre-registration discipline to prevent post-hoc HARKing (Hypothesizing After Results are Known)."
    )

    hypotheses = store.list_hypotheses()
    if not hypotheses:
        st.info("No pre-registered hypotheses recorded in current store.")
        return

    # Top KPI counts
    total = len(hypotheses)
    confirmed = sum(1 for h in hypotheses if "CONFIRMED" in h.verdict.upper() or "SUPPORT" in h.verdict.upper())
    refuted = sum(1 for h in hypotheses if "REFUTED" in h.verdict.upper())
    inconclusive = sum(1 for h in hypotheses if "INCONCLUSIVE" in h.verdict.upper() or "AWAITING" in h.verdict.upper())

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Hypotheses", total)
    with col2:
        st.metric("Confirmed / Supported", confirmed)
    with col3:
        st.metric("Refuted / Rejected", refuted)
    with col4:
        st.metric("Inconclusive / Pending", inconclusive)

    st.markdown("---")

    # Filter controls
    f_col1, f_col2 = st.columns([2, 2])
    with f_col1:
        verdict_choices = ["ALL", "CONFIRMED", "REFUTED", "INCONCLUSIVE"]
        sel_verdict = st.selectbox("Status Filter:", verdict_choices, index=0)
    with f_col2:
        decision_choices = ["ALL", "PROMOTE", "REJECT", "MAINTAIN_BASELINE", "NO_PROMOTION"]
        sel_decision = st.selectbox("Decision Filter:", decision_choices, index=0)

    filtered = hypotheses
    if sel_verdict != "ALL":
        filtered = [h for h in filtered if sel_verdict in h.verdict.upper()]
    if sel_decision != "ALL":
        filtered = [h for h in filtered if h.decision.upper() == sel_decision]

    df = build_hypotheses_df(filtered)

    if df.empty:
        st.warning("No hypotheses match selected filters.")
        return

    st.dataframe(
        df.style.format(
            {
                "Δ Points": lambda x: f"{x:+.4f}" if pd.notnull(x) else "—",
                "Δ Brier": lambda x: f"{x:+.6f}" if pd.notnull(x) else "—",
            }
        ),
        use_container_width=True,
        hide_index=True,
    )

    # Detailed Hypothesis Cards
    st.markdown("### 📜 Hypothesis Audit Cards")
    for h in filtered:
        # Determine status color
        if "CONFIRMED" in h.verdict.upper() or "SUPPORT" in h.verdict.upper():
            border_color = "#10b981"
            tag_icon = "✅"
        elif "REFUTED" in h.verdict.upper():
            border_color = "#ef4444"
            tag_icon = "❌"
        else:
            border_color = "#f59e0b"
            tag_icon = "⏳"

        st.markdown(
            f"""
            <div style="background-color: #1e222d; border-left: 4px solid {border_color};
                        padding: 14px; border-radius: 6px; margin-bottom: 12px;">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <strong style="color: #e2e8f0; font-size: 15px;">{tag_icon} {h.id}: {h.component}</strong>
                    <span style="background-color: {border_color}33; color: {border_color};
                                 padding: 3px 8px; border-radius: 4px; font-weight: 600; font-size: 11px;">
                        {h.verdict} | DECISION: {h.decision}
                    </span>
                </div>
                <p style="color: #cbd5e1; font-size: 13px; margin: 8px 0 4px 0;">
                    <em>"{h.statement}"</em>
                </p>
                <div style="color: #94a3b8; font-size: 11px;">
                    <strong>Expected:</strong> {h.expected_direction} &nbsp;|&nbsp;
                    <strong>Pre-registered:</strong> {h.preregistered_timestamp} &nbsp;|&nbsp;
                    <strong>Linked Trial:</strong> {h.linked_trial_id or 'None'}
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
