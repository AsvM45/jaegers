"""Main Streamlit application entrypoint for JAEGERS House Edge Experiment Analytics."""

from __future__ import annotations

import os
from pathlib import Path

import streamlit as st

from dashboard.adapter import ExperimentStore, get_experiment_store
from dashboard.components import (
    render_ablations_view,
    render_calibration_view,
    render_comparisons_view,
    render_diagnostics_view,
    render_export_view,
    render_hyperparameters_view,
    render_hypotheses_view,
    render_leaderboard_view,
    render_provenance_view,
)
from dashboard.config import (
    APP_ICON,
    APP_SUBTITLE,
    APP_TITLE,
    COLOR_PALETTE,
    MAX_OFFICIAL_POINTS,
)


def inject_custom_css() -> None:
    """Inject clean, modern CSS styling for dark theme and metrics cards."""
    st.markdown(
        """
        <style>
        /* General page layout improvements */
        .block-container {
            padding-top: 1.5rem;
            padding-bottom: 2.5rem;
        }

        /* Metric card styling */
        div[data-testid="stMetric"] {
            background-color: #1e222d;
            border: 1px solid #2a2e39;
            padding: 12px 16px;
            border-radius: 8px;
            box-shadow: 0 1px 3px rgba(0, 0, 0, 0.2);
        }

        /* Custom warning banner */
        .demo-warning-banner {
            background: linear-gradient(90deg, #b45309 0%, #d97706 100%);
            color: #ffffff;
            padding: 12px 20px;
            border-radius: 8px;
            margin-bottom: 20px;
            font-weight: 500;
            display: flex;
            align-items: center;
            box-shadow: 0 2px 4px rgba(0, 0, 0, 0.3);
        }

        /* Hero empty state container */
        .empty-hero-container {
            background-color: #1e222d;
            border: 2px dashed #4b5563;
            border-radius: 12px;
            padding: 40px;
            text-align: center;
            margin: 40px auto;
            max-width: 700px;
        }

        /* Table font and layout adjustments */
        div[data-testid="stDataFrame"] {
            border: 1px solid #2a2e39;
            border-radius: 6px;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def initialize_session_state() -> None:
    """Initialize default session state keys."""
    if "force_demo" not in st.session_state:
        # Check environment variable if CLI passed --demo
        env_demo = os.environ.get("JAEGERS_DASHBOARD_DEMO", "0") == "1"
        st.session_state.force_demo = env_demo

    if "custom_path" not in st.session_state:
        st.session_state.custom_path = os.environ.get("JAEGERS_DASHBOARD_PATH", "")

    if "active_tab" not in st.session_state:
        st.session_state.active_tab = "🏆 Leaderboard"


def load_store() -> ExperimentStore:
    """Load store based on current session state."""
    custom_path = st.session_state.custom_path.strip() or None
    force_demo = st.session_state.force_demo
    return get_experiment_store(source_path=custom_path, force_demo=force_demo)


def render_empty_state() -> None:
    """Render honest empty-state hero when zero experiment runs are found."""
    st.markdown(
        """
        <div class="empty-hero-container">
            <h2 style="color: #f3f4f6; margin-bottom: 8px;">📭 No Experiment Runs Found</h2>
            <p style="color: #9ca3af; font-size: 15px; line-height: 1.5; margin-bottom: 24px;">
                No active trial runs or SQLite registry was detected in the specified workspace path.<br>
                Expected database: <code>research_runs/main/registry.sqlite</code> or directory of JSON run results.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button("🚀 Load Synthetic Demonstration Fixtures", type="primary", use_container_width=True):
            st.session_state.force_demo = True
            st.rerun()


def main() -> None:
    """Main Streamlit application logic."""
    st.set_page_config(
        page_title=APP_TITLE,
        page_icon=APP_ICON,
        layout="wide",
        initial_sidebar_state="expanded",
    )

    initialize_session_state()
    inject_custom_css()

    # Sidebar Data Source Configuration
    st.sidebar.markdown(f"## {APP_ICON} JAEGERS")
    st.sidebar.caption("House Edge Experiment Intelligence")
    st.sidebar.markdown("---")

    st.sidebar.subheader("📁 Data Source Configuration")

    # Demo mode toggle
    demo_toggle = st.sidebar.toggle(
        "Demonstration Mode (Synthetic)",
        value=st.session_state.force_demo,
        help="Loads rich simulated fixtures covering all 13 models and HE-17 ablations.",
    )
    if demo_toggle != st.session_state.force_demo:
        st.session_state.force_demo = demo_toggle
        st.rerun()

    # Path input
    path_input = st.sidebar.text_input(
        "Custom Registry / Runs Path:",
        value=st.session_state.custom_path,
        placeholder="e.g. research_runs/main",
        help="Path to registry.sqlite or folder containing JSON trial outputs.",
    )
    if path_input != st.session_state.custom_path:
        st.session_state.custom_path = path_input
        st.rerun()

    # Quick reset button
    if st.sidebar.button("🔄 Auto-Detect Workspace", use_container_width=True):
        st.session_state.force_demo = False
        st.session_state.custom_path = ""
        st.rerun()

    st.sidebar.markdown("---")

    # Load store
    store = load_store()

    # Sidebar status indicator
    if store.is_demo_mode:
        st.sidebar.warning("⚠️ Mode: DEMONSTRATION FIXTURE")
    else:
        st.sidebar.success(f"✅ Mode: LIVE STORE ({len(store.list_trials())} runs)")

    # Sidebar Navigation
    st.sidebar.subheader("🧭 Navigation Views")
    views = [
        "🏆 Leaderboard",
        "🛡️ Provenance & Conditions",
        "⚖️ Paired Comparisons",
        "🧩 Ablations & Features",
        "🎛️ Hyperparameters",
        "🎯 Calibration & 20x Tail",
        "⏱️ Runtime Diagnostics",
        "🔬 Hypotheses Tracking",
        "📥 Reproducible Exports",
    ]
    selected_view = st.sidebar.radio("Go to View:", views, index=views.index(st.session_state.active_tab))
    st.session_state.active_tab = selected_view

    st.sidebar.markdown("---")
    st.sidebar.caption("JAEGERS Teamwork Agent B (Antigravity) • Issue #13")

    # Main Area Header
    header_col1, header_col2 = st.columns([4, 1])
    with header_col1:
        st.title(f"{APP_ICON} {APP_TITLE}")
        st.caption(APP_SUBTITLE)
    with header_col2:
        champ = store.get_champion()
        if champ and champ.official_points is not None:
            st.metric("Champion (HE-03)", f"{champ.official_points:.4f} / {MAX_OFFICIAL_POINTS:.0f}")

    # Prominent Banner if Demo Mode
    if store.is_demo_mode:
        st.markdown(
            """
            <div class="demo-warning-banner">
                <span style="font-size: 20px; margin-right: 12px;">⚠️</span>
                <div>
                    <strong>DEMONSTRATION ONLY — SYNTHETIC FIXTURE</strong><br>
                    <span style="font-size: 12px; opacity: 0.95;">
                        This dashboard is rendering simulated fixtures for offline exploration and component testing.
                        These numbers must NEVER be cited as official competition results or real model evidence.
                    </span>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    # Empty State Check
    if not store.has_runs() and not store.is_demo_mode:
        render_empty_state()
        return

    # View Router
    if selected_view == "🏆 Leaderboard":
        render_leaderboard_view(store)
    elif selected_view == "🛡️ Provenance & Conditions":
        render_provenance_view(store)
    elif selected_view == "⚖️ Paired Comparisons":
        render_comparisons_view(store)
    elif selected_view == "🧩 Ablations & Features":
        render_ablations_view(store)
    elif selected_view == "🎛️ Hyperparameters":
        render_hyperparameters_view(store)
    elif selected_view == "🎯 Calibration & 20x Tail":
        render_calibration_view(store)
    elif selected_view == "⏱️ Runtime Diagnostics":
        render_diagnostics_view(store)
    elif selected_view == "🔬 Hypotheses Tracking":
        render_hypotheses_view(store)
    elif selected_view == "📥 Reproducible Exports":
        render_export_view(store)


if __name__ == "__main__":
    main()
