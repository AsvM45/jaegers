"""Reproducible data exports (CSV, JSON) and markdown report generator."""

from __future__ import annotations

import streamlit as st

from ..adapter import ExperimentStore
from ..export import (
    export_ablations_csv,
    export_condition_breakdown_csv,
    export_hypotheses_json,
    export_leaderboard_csv,
    export_run_manifest_json,
    export_trial_config_json,
    generate_markdown_report,
)


def render_export_view(store: ExperimentStore) -> None:
    """Render download buttons for CSV, JSON, and markdown research reports."""
    st.subheader("📥 Reproducible Data & Report Exports")
    st.markdown(
        "Export experiment artifacts, condition matrices, trial configurations, and publication-ready "
        "Markdown evidence reports conforming to the team's `research/report.py` contract."
    )

    trials = store.list_trials()
    ablations = store.list_ablations()
    hypotheses = store.list_hypotheses()
    champion = store.get_champion()

    champ_id = champion.trial_id if champion else (trials[0].trial_id if trials else "champion-b78abe75")

    # CSV Exports Section
    st.markdown("### 📊 Tabular CSV Downloads")
    csv_col1, csv_col2, csv_col3 = st.columns(3)

    with csv_col1:
        st.markdown("**Leaderboard Summary**")
        st.caption("All trials, status, provenance, points, Brier, duration, and commits.")
        leaderboard_csv = export_leaderboard_csv(trials)
        st.download_button(
            label="⬇️ Download Leaderboard CSV",
            data=leaderboard_csv,
            file_name="jaegers_leaderboard.csv",
            mime="text/csv",
            use_container_width=True,
        )

    with csv_col2:
        st.markdown("**4-Condition Matrix**")
        st.caption("Condition loss ratios across stable, short, drift, and shared change.")
        condition_csv = export_condition_breakdown_csv(trials)
        st.download_button(
            label="⬇️ Download Conditions CSV",
            data=condition_csv,
            file_name="jaegers_conditions.csv",
            mime="text/csv",
            use_container_width=True,
        )

    with csv_col3:
        st.markdown("**Component Ablations**")
        st.caption("HE-17 12-variant ablation delta points, 95% CIs, and hypotheses.")
        ablations_csv = export_ablations_csv(ablations)
        st.download_button(
            label="⬇️ Download Ablations CSV",
            data=ablations_csv,
            file_name="jaegers_ablations.csv",
            mime="text/csv",
            use_container_width=True,
        )

    st.markdown("---")

    # JSON Exports Section
    st.markdown("### 🔧 Machine-Readable JSON Downloads")
    json_col1, json_col2, json_col3 = st.columns(3)

    with json_col1:
        st.markdown("**Full Run Manifest**")
        st.caption("Complete trial registry with hyperparameters, logs, and metrics.")
        manifest_json = export_run_manifest_json(trials)
        st.download_button(
            label="⬇️ Download Manifest JSON",
            data=manifest_json,
            file_name="jaegers_run_manifest.json",
            mime="application/json",
            use_container_width=True,
        )

    with json_col2:
        st.markdown("**Champion Trial Config**")
        trial_options = [t.trial_id for t in trials]
        selected_tid = st.selectbox("Select Trial:", trial_options, index=0 if trial_options else 0)
        selected_trial = next((t for t in trials if t.trial_id == selected_tid), champion)

        if selected_trial:
            trial_json = export_trial_config_json(selected_trial)
            st.download_button(
                label=f"⬇️ Download {selected_tid} Config JSON",
                data=trial_json,
                file_name=f"{selected_tid}_config.json",
                mime="application/json",
                use_container_width=True,
            )

    with json_col3:
        st.markdown("**Hypotheses Audit Board**")
        st.caption("Pre-registered hypotheses with verification outcomes.")
        hypo_json = export_hypotheses_json(hypotheses)
        st.download_button(
            label="⬇️ Download Hypotheses JSON",
            data=hypo_json,
            file_name="jaegers_hypotheses.json",
            mime="application/json",
            use_container_width=True,
        )

    st.markdown("---")

    # Markdown Report Section
    st.markdown("### 📝 Publication-Ready Markdown Report")
    st.markdown(
        "Generates evidence reports matching the schema specified in `Jaeger_Main/House_Edge/research/report.py`."
    )

    # Precompute comparisons with champion for other trials if possible
    comparisons = []
    for t in trials:
        if t.trial_id != champ_id:
            c = store.get_paired_comparison(t.trial_id, champ_id)
            if c:
                comparisons.append(c)

    md_report = generate_markdown_report(trials, baseline_id=champ_id, comparisons=comparisons)

    st.download_button(
        label="⬇️ Download Full Evidence Report (report.md)",
        data=md_report,
        file_name="house_edge_experiment_report.md",
        mime="text/markdown",
        use_container_width=True,
    )

    with st.expander("👁️ Interactive Markdown Report Preview", expanded=False):
        st.markdown(md_report)
