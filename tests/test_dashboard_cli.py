"""Unit tests for dashboard CLI entrypoint, argument parsing, and headless UI rendering."""

from __future__ import annotations

import os
import unittest
from pathlib import Path
from unittest.mock import patch

from dashboard.__main__ import build_streamlit_args, main, parse_args
from dashboard.adapter import get_experiment_store
from dashboard.components.ablations import (
    create_ablation_waterfall_chart,
    create_feature_group_importance_chart,
)
from dashboard.components.calibration import create_reliability_diagram
from dashboard.components.comparisons import (
    create_episode_scatter_plot,
    create_forest_plot,
)
from dashboard.components.diagnostics import (
    create_duration_histogram,
    create_memory_rss_chart,
    create_status_distribution_chart,
)
from dashboard.components.hyperparameters import (
    create_parallel_coordinates_plot,
    create_param_correlation_chart,
    create_sweep_trajectory_plot,
)
from dashboard.components.hypotheses import build_hypotheses_df
from dashboard.components.leaderboard import build_leaderboard_df
from dashboard.components.provenance_view import (
    create_4condition_bar_chart,
    create_4condition_radar_chart,
)
from dashboard.config import (
    ANCHORS,
    APP_TITLE,
    CONTEST_CONDITIONS,
    PAYOUT_CLASSES,
    format_brier,
    format_duration,
    format_points,
)
from dashboard.stats import analyze_hyperparameter_sweep


class TestDashboardCLIParser(unittest.TestCase):
    """Test suite for CLI argument parser and command synthesis."""

    def test_default_cli_arguments(self):
        """Verifies default CLI values when no arguments are passed."""
        args = parse_args([])
        self.assertEqual(args.port, 8501)
        self.assertEqual(args.host, "127.0.0.1")
        self.assertFalse(args.headless)
        self.assertFalse(args.demo)
        self.assertIsNone(args.path)

    def test_custom_port_and_host(self):
        """Verifies parsing of custom network parameters."""
        args = parse_args(["--port", "9090", "--host", "0.0.0.0"])
        self.assertEqual(args.port, 9090)
        self.assertEqual(args.host, "0.0.0.0")

    def test_headless_and_demo_flags(self):
        """Verifies boolean flag parsing for headless and demo modes."""
        args = parse_args(["--headless", "--demo"])
        self.assertTrue(args.headless)
        self.assertTrue(args.demo)

    def test_path_argument(self):
        """Verifies custom path argument parsing."""
        args = parse_args(["--path", "custom_runs/folder"])
        self.assertEqual(args.path, "custom_runs/folder")

    def test_build_streamlit_args(self):
        """Verifies formatting of command passed to Streamlit CLI runner."""
        args = parse_args(["--port", "8888", "--host", "localhost", "--headless"])
        cmd = build_streamlit_args(args)
        self.assertIn("streamlit", cmd)
        self.assertIn("run", cmd)
        self.assertTrue(any("app.py" in c for c in cmd))
        self.assertIn("--server.port=8888", cmd)
        self.assertIn("--server.address=localhost", cmd)
        self.assertIn("--server.headless=true", cmd)

    def test_main_dry_run_environment_propagation(self):
        """Verifies that main() propagates --demo and --path via environment variables."""
        test_args = ["--demo", "--path", "test_runs_dir"]
        exit_code = main(test_args, dry_run=True)
        self.assertEqual(exit_code, 0)
        self.assertEqual(os.environ.get("JAEGERS_DASHBOARD_DEMO"), "1")
        self.assertIn("test_runs_dir", os.environ.get("JAEGERS_DASHBOARD_PATH", ""))


class TestComponentBuildersSmoke(unittest.TestCase):
    """Test suite verifying pure chart and table builder routines render without error."""

    def setUp(self):
        self.store = get_experiment_store(force_demo=True)
        self.trials = self.store.list_trials()
        self.champion = self.store.get_champion()

    def test_leaderboard_dataframe_builder(self):
        """Verifies leaderboard DataFrame generation, sorting, and champion decoration."""
        df = build_leaderboard_df(self.trials)
        self.assertFalse(df.empty)
        self.assertIn("Trial ID", df.columns)
        self.assertIn("Official Points (0-60)", df.columns)
        self.assertIn("Provenance", df.columns)

        # Champion trial should be marked with trophy
        champ_rows = df[df["_raw_id"] == self.champion.trial_id]
        self.assertEqual(len(champ_rows), 1)
        self.assertTrue(champ_rows.iloc[0]["Trial ID"].startswith("🏆"))

        # Verify sorted by Official Points descending
        points_series = df["Official Points (0-60)"].dropna()
        self.assertTrue((points_series.diff().dropna() <= 0).all())

    def test_provenance_charts_builder(self):
        """Verifies 4-condition grouped bar chart and radar chart generation."""
        bar_fig = create_4condition_bar_chart(self.trials[:4])
        self.assertGreater(len(bar_fig.data), 0)
        self.assertEqual(bar_fig.layout.barmode, "group")

        radar_fig = create_4condition_radar_chart(self.trials[:4])
        self.assertGreater(len(radar_fig.data), 0)
        self.assertEqual(radar_fig.data[0].type, "scatterpolar")

    def test_comparisons_charts_builder(self):
        """Verifies paired comparison forest plot and per-episode scatter plot."""
        comp = self.store.get_paired_comparison("champion-b78abe75", "nosig-63c6396e")
        self.assertIsNotNone(comp)

        forest_fig = create_forest_plot(comp)
        self.assertGreater(len(forest_fig.data), 0)
        # Check error bar configuration
        self.assertIsNotNone(forest_fig.data[0].error_x)

        scatter_fig = create_episode_scatter_plot(comp)
        self.assertGreater(len(scatter_fig.data), 0)

    def test_ablations_charts_builder(self):
        """Verifies component ablation waterfall chart and feature importance chart."""
        ablations = self.store.list_ablations()
        self.assertGreater(len(ablations), 0)

        waterfall_fig = create_ablation_waterfall_chart(ablations, baseline_points=55.121615)
        self.assertEqual(len(waterfall_fig.data), 1)
        self.assertEqual(waterfall_fig.data[0].type, "waterfall")

        feat_imp = self.champion.feature_importance
        self.assertIsNotNone(feat_imp)
        feat_fig = create_feature_group_importance_chart(feat_imp)
        self.assertEqual(len(feat_fig.data), 1)
        self.assertEqual(feat_fig.data[0].type, "bar")

    def test_hyperparameters_charts_builder(self):
        """Verifies Optuna sweep trajectory, parallel coordinates, and correlation charts."""
        analysis = analyze_hyperparameter_sweep(self.trials, metric_key="mean_brier", maximize=False)
        self.assertGreater(len(analysis.trajectory), 0)

        traj_fig = create_sweep_trajectory_plot(analysis)
        self.assertEqual(len(traj_fig.data), 2)  # Scatter + Running Best

        par_fig = create_parallel_coordinates_plot(analysis)
        self.assertEqual(len(par_fig.data), 1)
        self.assertEqual(par_fig.data[0].type, "parcoords")

        corr_fig = create_param_correlation_chart(analysis)
        self.assertEqual(len(corr_fig.data), 1)
        self.assertEqual(corr_fig.data[0].type, "bar")

    def test_calibration_reliability_diagram_builder(self):
        """Verifies 5-class reliability diagram generation."""
        bins = self.store.get_calibration_bins()
        self.assertGreater(len(bins), 0)

        # Multi-class overlay
        fig_all = create_reliability_diagram(bins, selected_class=None)
        self.assertEqual(len(fig_all.data), 6)  # 1 diagonal + 5 classes

        # Single class highlight
        fig_single = create_reliability_diagram(bins, selected_class=20)
        self.assertEqual(len(fig_single.data), 2)  # 1 diagonal + class 20

    def test_diagnostics_charts_builder(self):
        """Verifies duration histogram, status donut chart, and peak memory chart."""
        dur_fig = create_duration_histogram(self.trials)
        self.assertEqual(len(dur_fig.data), 1)
        self.assertEqual(dur_fig.data[0].type, "histogram")

        status_fig = create_status_distribution_chart(self.trials)
        self.assertEqual(len(status_fig.data), 1)
        self.assertEqual(status_fig.data[0].type, "pie")

        logs = self.store.get_execution_logs()
        self.assertGreater(len(logs), 0)
        mem_fig = create_memory_rss_chart(logs)
        self.assertEqual(len(mem_fig.data), 1)
        self.assertEqual(mem_fig.data[0].type, "bar")

    def test_hypotheses_dataframe_builder(self):
        """Verifies pre-registered hypothesis DataFrame conversion."""
        hypotheses = self.store.list_hypotheses()
        self.assertGreater(len(hypotheses), 0)

        df = build_hypotheses_df(hypotheses)
        self.assertFalse(df.empty)
        self.assertIn("ID", df.columns)
        self.assertIn("Statement", df.columns)
        self.assertIn("Status", df.columns)
        self.assertIn("Decision", df.columns)


class TestConfigAndFormatting(unittest.TestCase):
    """Test suite for config constants and formatting helpers."""

    def test_constants_definitions(self):
        """Verifies core constants."""
        self.assertEqual(CONTEST_CONDITIONS, ("stable", "short_history", "drift", "shared_change"))
        self.assertEqual(PAYOUT_CLASSES, (0, 1, 2, 5, 20))
        self.assertIn("champion", ANCHORS)
        self.assertAlmostEqual(ANCHORS["champion"]["points"], 55.121615, places=4)

    def test_formatting_utilities(self):
        """Verifies string formatting for points, Brier, and wall time."""
        self.assertEqual(format_points(55.121615), "55.1216 / 60")
        self.assertEqual(format_points(None), "N/A")
        self.assertEqual(format_brier(0.365141), "0.365141")
        self.assertEqual(format_brier(None), "N/A")
        self.assertEqual(format_duration(45.2), "45.2s")
        self.assertEqual(format_duration(184.2), "3m 4s")
        self.assertEqual(format_duration(None), "0s")


class TestStreamlitAppHeadless(unittest.TestCase):
    """Test suite running Streamlit app under headless AppTest environment."""

    def test_app_headless_execution(self):
        """Verifies that dashboard/app.py executes headlessly without unhandled exceptions."""
        from streamlit.testing.v1 import AppTest

        app_path = Path(__file__).parent.parent / "dashboard" / "app.py"
        at = AppTest.from_file(str(app_path))
        at.run(timeout=30)

        # Confirm zero unhandled script exceptions
        self.assertEqual(len(at.exception), 0)
        # Confirm main title rendered
        self.assertGreater(len(at.title), 0)
        self.assertIn("JAEGERS", at.title[0].value)


if __name__ == "__main__":
    unittest.main()
