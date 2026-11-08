"""Runtime performance telemetry, memory usage, and failure diagnostics component."""

from __future__ import annotations

from typing import List, Optional

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from ..adapter import ExperimentStore
from ..config import COLOR_PALETTE, apply_plotly_dark_theme, format_duration
from ..schema import ExecutionLog, TrialRecord


def create_duration_histogram(trials: List[TrialRecord]) -> go.Figure:
    """Create histogram of execution durations across all trials."""
    fig = go.Figure()

    durations = [t.wall_seconds for t in trials if t.wall_seconds > 0]
    if not durations:
        fig.add_annotation(text="No trial execution durations available", showarrow=False)
        apply_plotly_dark_theme(fig)
        return fig

    fig.add_trace(
        go.Histogram(
            x=durations,
            nbinsx=15,
            marker=dict(
                color=COLOR_PALETTE["primary"],
                line=dict(color=COLOR_PALETTE["text"], width=1),
            ),
            name="Duration (s)",
        )
    )

    fig.update_layout(
        title="Worker Execution Duration Distribution (Seconds)",
        xaxis_title="Wall Seconds",
        yaxis_title="Trial Count",
        height=380,
    )
    apply_plotly_dark_theme(fig)
    return fig


def create_status_distribution_chart(trials: List[TrialRecord]) -> go.Figure:
    """Create donut chart showing trial execution status breakdown."""
    fig = go.Figure()

    status_counts: dict[str, int] = {}
    for t in trials:
        status_counts[t.status] = status_counts.get(t.status, 0) + 1

    labels = list(status_counts.keys())
    values = list(status_counts.values())

    color_map = {
        "SUCCEEDED": COLOR_PALETTE["success"],
        "FAILED": COLOR_PALETTE["danger"],
        "CORRUPTED": COLOR_PALETTE["danger"],
        "RUNNING": COLOR_PALETTE["primary"],
        "UNKNOWN": COLOR_PALETTE["text_muted"],
    }
    colors = [color_map.get(lbl, COLOR_PALETTE["warning"]) for lbl in labels]

    fig.add_trace(
        go.Pie(
            labels=labels,
            values=values,
            hole=0.45,
            marker=dict(colors=colors),
            textinfo="label+percent+value",
        )
    )

    fig.update_layout(
        title="Trial Status Breakdown",
        height=380,
    )
    apply_plotly_dark_theme(fig)
    return fig


def create_memory_rss_chart(logs: List[ExecutionLog]) -> go.Figure:
    """Create bar chart of peak resident memory (RSS GiB) across executed trials."""
    fig = go.Figure()

    valid_logs = [l for l in logs if l.memory_peak_gib is not None]
    if not valid_logs:
        fig.add_annotation(text="No peak memory RSS telemetry available", showarrow=False)
        apply_plotly_dark_theme(fig)
        return fig

    t_ids = [l.trial_id for l in valid_logs]
    mems = [l.memory_peak_gib for l in valid_logs]

    fig.add_trace(
        go.Bar(
            x=t_ids,
            y=mems,
            marker=dict(
                color=COLOR_PALETTE["purple"],
                line=dict(color=COLOR_PALETTE["text"], width=1),
            ),
            text=[f"{m:.2f} GiB" for m in mems],
            textposition="auto",
            name="Peak RSS",
        )
    )

    fig.update_layout(
        title="Peak Memory Usage Across Trials (GiB)",
        xaxis_title="Trial ID",
        yaxis_title="Peak Memory (GiB)",
        height=380,
    )
    apply_plotly_dark_theme(fig)
    return fig


def render_diagnostics_view(store: ExperimentStore) -> None:
    """Render runtime telemetry, resource utilization, and failure stack traces."""
    st.subheader("⏱️ Runtime Telemetry & Failure Diagnostics")
    st.markdown(
        "Monitoring of execution wall times, peak resident memory footprints, "
        "and syntax-highlighted failure logs for anomalous or crashed trials."
    )

    trials = store.list_trials()
    logs = store.get_execution_logs()

    if not trials and not logs:
        st.info("No runtime diagnostics or execution telemetry available in store.")
        return

    # Top KPI highlights
    durations = [t.wall_seconds for t in trials if t.wall_seconds > 0]
    avg_duration = sum(durations) / len(durations) if durations else 0.0
    failed_trials = [t for t in trials if t.status in ("FAILED", "CORRUPTED")]

    kpi1, kpi2, kpi3, kpi4 = st.columns(4)
    with kpi1:
        st.metric("Total Trials Tracked", len(trials))
    with kpi2:
        st.metric("Mean Wall Duration", format_duration(avg_duration))
    with kpi3:
        st.metric("Total Failed Trials", len(failed_trials))
    with kpi4:
        st.metric("Execution Logs Captured", len(logs))

    st.markdown("---")

    # Visualizations
    tab1, tab2, tab3 = st.tabs(["⏱️ Duration Distribution", "🥧 Status Breakdown", "💾 Memory Peak RSS"])

    with tab1:
        dur_fig = create_duration_histogram(trials)
        st.plotly_chart(dur_fig, use_container_width=True)

    with tab2:
        status_fig = create_status_distribution_chart(trials)
        st.plotly_chart(status_fig, use_container_width=True)

    with tab3:
        mem_fig = create_memory_rss_chart(logs)
        st.plotly_chart(mem_fig, use_container_width=True)

    # Failure Inspector Section
    st.markdown("### 💥 Failure & Error Log Inspector")

    error_logs = [l for l in logs if l.status in ("FAILED", "CORRUPTED") or l.error_message or l.traceback]

    if not error_logs and not failed_trials:
        st.success("🎉 Zero trial failures or corrupted logs detected!")
    else:
        st.warning(f"Detected {max(len(error_logs), len(failed_trials))} failed or interrupted trials.")

        # If we have structured logs, show them
        if error_logs:
            for l in error_logs:
                with st.expander(
                    f"❌ Trial: {l.trial_id} (Attempt #{l.attempt}) — {l.error_category or 'Error'}",
                    expanded=False,
                ):
                    st.write(f"**Error Category:** `{l.error_category}`")
                    st.write(f"**Duration Before Crash:** {format_duration(l.wall_seconds)}")
                    if l.memory_peak_gib:
                        st.write(f"**Peak Memory at Crash:** {l.memory_peak_gib:.2f} GiB")
                    if l.error_message:
                        st.error(f"Message: {l.error_message}")
                    if l.traceback:
                        st.markdown("**Traceback:**")
                        st.code(l.traceback, language="python")
                    if l.stderr_snippet:
                        st.markdown("**Stderr Output:**")
                        st.code(l.stderr_snippet, language="bash")
        else:
            for ft in failed_trials:
                with st.expander(f"❌ Trial: {ft.trial_id} (Status: {ft.status})", expanded=False):
                    st.write(f"**Error Message:** {ft.error_message or 'No message captured'}")
                    st.write(f"**Wall Duration:** {format_duration(ft.wall_seconds)}")
