"""Multi-metric experiment leaderboard and trial inspector component."""

from __future__ import annotations

from typing import List, Optional

import pandas as pd
import streamlit as st

from ..adapter import ExperimentStore
from ..config import COLOR_PALETTE, format_brier, format_duration, format_points
from ..provenance import get_provenance_badge
from ..schema import TrialRecord


def build_leaderboard_df(trials: List[TrialRecord]) -> pd.DataFrame:
    """Transform list of TrialRecords into presentation-ready pandas DataFrame."""
    rows = []
    for r in trials:
        champ_prefix = "🏆 " if r.is_champion else ""
        badge = get_provenance_badge(r.provenance)
        short_commit = r.source_commit[:8] if r.source_commit else "—"

        rows.append(
            {
                "Trial ID": f"{champ_prefix}{r.trial_id}",
                "Status": r.status,
                "Provenance": badge,
                "Official Points (0-60)": r.official_points if r.official_points is not None else float("nan"),
                "Mean Brier": r.mean_brier if r.mean_brier is not None else float("nan"),
                "Family": r.family,
                "Study": r.study_name,
                "Duration": format_duration(r.wall_seconds),
                "Commit": short_commit,
                "Synthetic": "Yes" if r.is_synthetic else "No",
                "_raw_id": r.trial_id,
            }
        )
    df = pd.DataFrame(rows)
    if not df.empty:
        # Default sort by Official Points descending, then Mean Brier ascending
        df = df.sort_values(
            by=["Official Points (0-60)", "Mean Brier"],
            ascending=[False, True],
            na_position="last",
        ).reset_index(drop=True)
    return df


def render_leaderboard_view(store: ExperimentStore) -> None:
    """Render interactive leaderboard and trial inspector in Streamlit."""
    st.subheader("🏆 Experiment Leaderboard")
    st.markdown(
        "Sortable, multi-metric experiment registry showing evaluation provenance, official contest points, "
        "probabilistic Brier scores, execution status, and git commit provenance."
    )

    trials = store.list_trials()
    if not trials:
        st.info("No experiment trials available in current store.")
        return

    # Top summary metrics
    champion = store.get_champion()
    total_count = len(trials)
    succeeded_count = sum(1 for t in trials if t.status == "SUCCEEDED")
    failed_count = sum(1 for t in trials if t.status in ("FAILED", "CORRUPTED"))
    running_count = sum(1 for t in trials if t.status == "RUNNING")

    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        st.metric("Total Trials", total_count)
    with col2:
        champ_score = format_points(champion.official_points) if champion else "None"
        st.metric("Champion Score", champ_score)
    with col3:
        st.metric("Succeeded", succeeded_count)
    with col4:
        st.metric("Failed / Corrupted", failed_count)
    with col5:
        st.metric("Running", running_count)

    st.markdown("---")

    # Filter controls
    f_col1, f_col2, f_col3, f_col4 = st.columns([2, 1.5, 1.5, 2])

    with f_col1:
        search_query = st.text_input("🔍 Search Trial ID / Study", value="").strip().lower()

    with f_col2:
        status_options = ["ALL", "SUCCEEDED", "FAILED", "RUNNING"]
        selected_status = st.selectbox("Status Filter", status_options, index=0)

    with f_col3:
        all_families = sorted(list({t.family for t in trials if t.family}))
        family_options = ["ALL"] + all_families
        selected_family = st.selectbox("Family Filter", family_options, index=0)

    with f_col4:
        provenances = ["ALL"] + sorted(list({t.provenance.value for t in trials}))
        selected_prov = st.selectbox("Provenance Filter", provenances, index=0)

    # Apply filters
    filtered_trials = trials
    if selected_status != "ALL":
        filtered_trials = [t for t in filtered_trials if t.status == selected_status]
    if selected_family != "ALL":
        filtered_trials = [t for t in filtered_trials if t.family == selected_family]
    if selected_prov != "ALL":
        filtered_trials = [t for t in filtered_trials if t.provenance.value == selected_prov]
    if search_query:
        filtered_trials = [
            t
            for t in filtered_trials
            if search_query in t.trial_id.lower() or search_query in t.study_name.lower() or search_query in t.family.lower()
        ]

    df = build_leaderboard_df(filtered_trials)

    if df.empty:
        st.warning("No trials match the specified filters.")
        return

    # Render table with custom formatting
    display_cols = [
        "Trial ID",
        "Status",
        "Provenance",
        "Official Points (0-60)",
        "Mean Brier",
        "Family",
        "Study",
        "Duration",
        "Commit",
    ]
    st.dataframe(
        df[display_cols].style.format(
            {
                "Official Points (0-60)": lambda x: f"{x:.4f}" if pd.notnull(x) else "—",
                "Mean Brier": lambda x: f"{x:.6f}" if pd.notnull(x) else "—",
            }
        ),
        use_container_width=True,
        hide_index=True,
    )

    # Detailed Trial Inspector
    st.markdown("### 🔬 Trial Inspector")
    trial_options = [r["_raw_id"] for _, r in df.iterrows()]
    selected_trial_id = st.selectbox("Select Trial to Inspect:", trial_options, index=0)

    selected_trial = next((t for t in filtered_trials if t.trial_id == selected_trial_id), None)
    if selected_trial:
        detail = store.get_trial(selected_trial_id)
        with st.expander(f"Details: {selected_trial.trial_id} ({selected_trial.status})", expanded=True):
            det_col1, det_col2, det_col3 = st.columns(3)
            with det_col1:
                st.write("**Family:**", selected_trial.family)
                st.write("**Study:**", selected_trial.study_name)
                st.write("**Commit SHA:**", f"`{selected_trial.source_commit}`" if selected_trial.source_commit else "None")
                st.write("**Wall Duration:**", format_duration(selected_trial.wall_seconds))
            with det_col2:
                st.write("**Official Points:**", format_points(selected_trial.official_points))
                st.write("**Mean Brier:**", format_brier(selected_trial.mean_brier))
                st.write("**Champion:**", "🏆 Yes" if selected_trial.is_champion else "No")
                st.write("**Synthetic Demo:**", "Yes" if selected_trial.is_synthetic else "No")
            with det_col3:
                st.write("**Provenance:**", f"`{selected_trial.provenance.value}`")
                st.write("**Created At:**", selected_trial.created_at)
                st.write("**Finished At:**", selected_trial.finished_at or "In Progress / N/A")
                st.write("**Attempt #:**", selected_trial.attempt)

            # Condition loss breakdown if available
            if selected_trial.condition_losses:
                st.markdown("**4-Condition Loss Ratios ($E_c / B_c$):**")
                cl = selected_trial.condition_losses
                cl_cols = st.columns(4)
                with cl_cols[0]:
                    st.metric("Stable", f"{cl.stable:.6f}")
                with cl_cols[1]:
                    st.metric("Short History", f"{cl.short_history:.6f}")
                with cl_cols[2]:
                    st.metric("Drift", f"{cl.drift:.6f}")
                with cl_cols[3]:
                    st.metric("Shared Change", f"{cl.shared_change:.6f}")

            # Hyperparameters display
            if selected_trial.hyperparameters:
                st.markdown("**Hyperparameters:**")
                st.json(selected_trial.hyperparameters)

            # Feature importance if available
            if selected_trial.feature_importance:
                st.markdown("**Feature Importance:**")
                st.bar_chart(selected_trial.feature_importance)

            # Error message if failed
            if selected_trial.error_message:
                st.error(f"Error Encountered: {selected_trial.error_message}")
