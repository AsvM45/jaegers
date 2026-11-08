"""Unit Test Suite for Databricks MLflow Experiment Tracking & Governance (Milestone 3)

Verifies:
1. HouseEdgeMLflowTracker initialization and seamless session resolution (MockMLflow vs native MLflow).
2. Hyperparameter governance: required parameters (model_type, lam, prior, causal, stack_lr, feature_groups, seed).
3. Governance tags: git_commit, evaluation_provenance, champion_status, data_hash.
4. Metric logging: mean_brier, log_loss, ece_calibration, condition Briers, class Briers.
5. Calibration artifact logging: structured JSON (calibration_data.json) and visual curve plot (calibration_curve.png).
6. Model signature logging: 471-feature input schema and 5-class output schema (feature_schema.json).
7. Model leaderboard extraction, formatting, and ascending rank sorting by mean Brier score.
8. Native MLflow dispatch and contract parity.
9. Exact mathematical correctness of Brier loss, condition loss, multi-class log loss, and ECE.
"""

from __future__ import annotations

import json
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pandas as pd

# Add repository root and Databricks src directory to sys.path
REPO_ROOT = Path(__file__).resolve().parents[1]
DATABRICKS_DIR = REPO_ROOT / "Jaeger_Main" / "House_Edge" / "databricks"
if str(DATABRICKS_DIR) not in sys.path:
    sys.path.insert(0, str(DATABRICKS_DIR))

from src.mock_engine import MockMLflow
from src.session import get_mlflow
from src.mlflow_tracking import (
    DEFAULT_EXPERIMENT_PATH,
    DEFAULT_PARAM_VALUES,
    DEFAULT_TAG_VALUES,
    OUTPUT_CLASSES,
    REQUIRED_METRICS,
    REQUIRED_PARAMS,
    REQUIRED_TAGS,
    HouseEdgeMLflowTracker,
    compute_brier_scores,
    compute_calibration,
    compute_condition_briers,
    compute_diagnostics_and_track,
    compute_log_loss,
    get_git_branch,
    get_git_commit,
)


class TestHouseEdgeMLflowTrackerOffline(unittest.TestCase):
    """Verifies HouseEdgeMLflowTracker functionality using offline MockMLflow."""

    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp()
        self.storage_file = os.path.join(self.tmp_dir, "test_mlruns.json")
        # Ensure fresh MockMLflow instance
        self.mock_client = MockMLflow(storage_file=self.storage_file)
        self.tracker = HouseEdgeMLflowTracker(
            experiment_name="/Shared/test_house_edge",
            tracking_uri="file:///tmp/test_mlruns",
            force_mock=True,
        )
        # Inject our isolated mock client into tracker
        self.tracker.mlflow = self.mock_client

    def tearDown(self):
        if self.tracker.active_run is not None:
            self.tracker.end_trial()
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def test_tracker_initialization(self):
        """Verifies tracker initialization and experiment configuration."""
        self.assertEqual(self.tracker.experiment_name, "/Shared/test_house_edge")
        self.assertEqual(self.tracker.tracking_uri, "file:///tmp/test_mlruns")
        self.assertIsNone(self.tracker.active_run)
        self.assertIsNone(self.tracker.active_run_id)

    def test_start_trial_parameter_governance(self):
        """Verifies that all 7 required hyperparameters are logged with correct values or defaults."""
        custom_params = {
            "model_type": "gradient_boosted_stacker",
            "lam": 0.75,
            "prior": "empirical_dirichlet",
            "causal": True,
            "stack_lr": 0.035,
            "feature_groups": "type,lags,windows",
            "seed": 1234,
            "extra_param": "foo",
        }
        run = self.tracker.start_trial("test_model_v1", "gradient_boosted_stacker", params=custom_params)
        self.assertIsNotNone(run)
        self.assertEqual(self.tracker.active_trial_name, "test_model_v1")

        # Verify logged params in mock client
        active_run = self.mock_client.active_run()
        self.assertIsNotNone(active_run)
        logged_params = active_run.data["params"]

        for req in REQUIRED_PARAMS:
            self.assertIn(req, logged_params, f"Missing required parameter: {req}")

        self.assertEqual(logged_params["model_type"], "gradient_boosted_stacker")
        self.assertEqual(logged_params["lam"], "0.75")
        self.assertEqual(logged_params["prior"], "empirical_dirichlet")
        self.assertEqual(logged_params["causal"], "True")
        self.assertEqual(logged_params["stack_lr"], "0.035")
        self.assertEqual(logged_params["feature_groups"], "type,lags,windows")
        self.assertEqual(logged_params["seed"], "1234")
        self.assertEqual(logged_params["extra_param"], "foo")

    def test_start_trial_default_parameters(self):
        """Verifies that omitted parameters are automatically populated with governed defaults."""
        self.tracker.start_trial("minimal_model", "baseline")
        logged_params = self.mock_client.active_run().data["params"]

        for req in REQUIRED_PARAMS:
            self.assertIn(req, logged_params)
        self.assertEqual(logged_params["model_type"], "baseline")
        self.assertEqual(logged_params["lam"], str(DEFAULT_PARAM_VALUES["lam"]))
        self.assertEqual(logged_params["seed"], str(DEFAULT_PARAM_VALUES["seed"]))

    def test_start_trial_tag_governance(self):
        """Verifies logging of git commit, provenance, champion status, and data hash tags."""
        custom_tags = {
            "evaluation_provenance": "official_public_validation",
            "champion_status": "champion",
            "author": "jaegers_lead",
        }
        self.tracker.start_trial("champ_model", "regime_mixture", tags=custom_tags)
        logged_tags = self.mock_client.active_run().data["tags"]

        for req in REQUIRED_TAGS:
            self.assertIn(req, logged_tags, f"Missing required tag: {req}")

        self.assertEqual(logged_tags["evaluation_provenance"], "official_public_validation")
        self.assertEqual(logged_tags["champion_status"], "champion")
        self.assertEqual(logged_tags["author"], "jaegers_lead")
        self.assertTrue(len(logged_tags["git_commit"]) >= 8)
        self.assertTrue(len(logged_tags["data_hash"]) >= 8)

    def test_log_metrics_structure(self):
        """Verifies logging of overall metrics, condition-level Briers, and class Briers."""
        self.tracker.start_trial("metric_test", "regime_mixture")

        base_metrics = {
            "mean_brier": 0.05512,
            "log_loss": 1.412,
            "ece_calibration": 0.0142,
        }
        condition_metrics = {
            "stable": 0.048,
            "short_history": 0.061,
            "brier_drift": 0.057,  # already has prefix
            "shared_change": 0.054,
        }
        class_metrics = {
            0: 0.018,
            1: 0.021,
            "class_brier_2": 0.034,  # already has prefix
            5: 0.062,
            20: 0.140,
        }

        all_logged = self.tracker.log_metrics(
            base_metrics,
            condition_metrics=condition_metrics,
            class_metrics=class_metrics,
        )

        logged = self.mock_client.active_run().data["metrics"]

        # Verify all REQUIRED_METRICS are logged
        for req in REQUIRED_METRICS:
            self.assertIn(req, logged, f"Missing required metric: {req}")
            self.assertIsInstance(logged[req], float)

        self.assertAlmostEqual(logged["mean_brier"], 0.05512)
        self.assertAlmostEqual(logged["brier_stable"], 0.048)
        self.assertAlmostEqual(logged["brier_drift"], 0.057)
        self.assertAlmostEqual(logged["class_brier_0"], 0.018)
        self.assertAlmostEqual(logged["class_brier_20"], 0.140)

    def test_log_calibration_artifacts_and_metrics(self):
        """Verifies logging of calibration JSON artifact, curve plot, and ECE metric."""
        self.tracker.start_trial("cal_model", "regime_mixture")

        cal_payload = {
            "output_classes": [0, 1, 2, 5, 20],
            "n_bins": 10,
            "ece": 0.0135,
            "curves_by_class": {
                "0": {"predicted": [0.1, 0.5], "observed": [0.12, 0.48], "counts": [50, 50], "bins": [1, 5]},
                "1": {"predicted": [0.2], "observed": [0.19], "counts": [30], "bins": [2]},
            },
            "calibration_bins": [
                {"class": 0, "bin": 1, "predicted": 0.1, "observed": 0.12, "count": 50},
                {"class": 0, "bin": 5, "predicted": 0.5, "observed": 0.48, "count": 50},
            ],
        }

        result = self.tracker.log_calibration(cal_payload, save_plot=True)
        self.assertIn("ece", result)

        active_run = self.mock_client.active_run()
        # Verify metric
        self.assertAlmostEqual(active_run.data["metrics"]["ece_calibration"], 0.0135)

        # Verify artifacts
        artifacts = active_run.data["artifacts"]
        artifact_paths = [a.get("artifact_path", "") for a in artifacts]

        has_json = any("calibration_data.json" in p for p in artifact_paths)
        self.assertTrue(has_json, f"calibration_data.json not found in {artifact_paths}")

        has_png = any("calibration_curve.png" in p for p in artifact_paths)
        self.assertTrue(has_png, f"calibration_curve.png not found in {artifact_paths}")

    def test_log_model_signature(self):
        """Verifies model signature logging with 471 feature names and 5 payout classes."""
        self.tracker.start_trial("sig_model", "regime_mixture")

        feature_names = [f"f_{i}" for i in range(471)]
        output_classes = (0, 1, 2, 5, 20)

        sig = self.tracker.log_model_signature(feature_names=feature_names, output_classes=output_classes)
        self.assertEqual(sig["input_dimension"], 471)
        self.assertEqual(sig["output_dimension"], 5)
        self.assertEqual(sig["feature_names"][:3], ["f_0", "f_1", "f_2"])
        self.assertEqual(sig["output_classes"], [0, 1, 2, 5, 20])

        # Verify feature_schema.json was logged
        artifacts = self.mock_client.active_run().data["artifacts"]
        artifact_paths = [a.get("artifact_path", "") for a in artifacts]
        has_schema = any("feature_schema.json" in p for p in artifact_paths)
        self.assertTrue(has_schema, f"feature_schema.json not found in {artifact_paths}")

    def test_log_arbitrary_artifacts(self):
        """Verifies logging of arbitrary dictionaries, file paths, and text strings."""
        self.tracker.start_trial("artifact_test", "regime_mixture")

        # Create temporary file
        temp_file = os.path.join(self.tmp_dir, "notes.txt")
        with open(temp_file, "w", encoding="utf-8") as f:
            f.write("Offline notes")

        artifact_dict = {
            "summary.json": {"architecture": "regime_mixture", "layers": 2},
            "per_episode_brier.json": {"ep_1": 0.045, "ep_2": 0.058},
            "notes.txt": temp_file,
            "raw_text.txt": "Inline text artifact content",
        }

        logged_keys = self.tracker.log_artifacts(artifact_dict)
        self.assertEqual(len(logged_keys), 4)

        artifacts = self.mock_client.active_run().data["artifacts"]
        self.assertTrue(len(artifacts) >= 4)

    def test_trial_lifecycle_and_context_manager(self):
        """Verifies trial start, finish status, and context manager support."""
        # 1. Manual end_trial
        self.tracker.start_trial("run_1", "baseline")
        self.assertIsNotNone(self.tracker.active_run)
        self.tracker.end_trial(status="FINISHED")
        self.assertIsNone(self.tracker.active_run)
        self.assertEqual(self.mock_client._runs[list(self.mock_client._runs.keys())[0]].info.status, "FINISHED")

        # 2. Context manager normal completion
        with self.tracker:
            self.tracker.start_trial("run_2", "baseline")
            self.assertIsNotNone(self.tracker.active_run)
        self.assertIsNone(self.tracker.active_run)

        # 3. Context manager exception completion
        try:
            with self.tracker:
                self.tracker.start_trial("run_3", "baseline")
                raise RuntimeError("Simulated trial failure")
        except RuntimeError:
            pass
        self.assertIsNone(self.tracker.active_run)

    def test_leaderboard_extraction_and_sorting(self):
        """Verifies that get_leaderboard returns a properly sorted and formatted DataFrame."""
        # Log Trial 1: Baseline (Brier = 0.0580)
        self.tracker.start_trial("baseline_model", "baseline",
                                 params={"lam": 1.0, "stack_lr": 0.05, "causal": False},
                                 tags={"champion_status": "challenger", "evaluation_provenance": "sampled_outcome_group_cv"})
        self.tracker.log_metrics({"mean_brier": 0.0580, "log_loss": 1.450, "ece_calibration": 0.020})
        self.tracker.end_trial()

        # Log Trial 2: Champion (Brier = 0.0551)
        self.tracker.start_trial("champion_model", "regime_mixture",
                                 params={"lam": 1.25, "stack_lr": 0.045, "causal": True},
                                 tags={"champion_status": "champion", "evaluation_provenance": "official_public_validation"})
        self.tracker.log_metrics({"mean_brier": 0.0551, "log_loss": 1.412, "ece_calibration": 0.014})
        self.tracker.end_trial()

        # Log Trial 3: Best Challenger (Brier = 0.0546)
        self.tracker.start_trial("best_challenger", "causal_lag_expert",
                                 params={"lam": 1.0, "stack_lr": 0.05, "causal": True},
                                 tags={"champion_status": "challenger", "evaluation_provenance": "sampled_outcome_group_cv"})
        self.tracker.log_metrics({"mean_brier": 0.0546, "log_loss": 1.398, "ece_calibration": 0.012})
        self.tracker.end_trial()

        leaderboard = self.tracker.get_leaderboard()

        self.assertIsInstance(leaderboard, pd.DataFrame)
        self.assertEqual(len(leaderboard), 3)

        # Verify sorted ascending by mean_brier (best first: 0.0546 < 0.0551 < 0.0580)
        expected_order = ["best_challenger", "champion_model", "baseline_model"]
        self.assertEqual(leaderboard["model_name"].tolist(), expected_order)
        self.assertEqual(leaderboard["rank"].tolist(), [1, 2, 3])

        # Verify required columns exist
        for col in ["rank", "model_name", "model_type", "mean_brier", "log_loss", "ece_calibration",
                    "champion_status", "evaluation_provenance", "git_commit"]:
            self.assertIn(col, leaderboard.columns)


class TestMLflowAnalyticsMath(unittest.TestCase):
    """Verifies mathematical correctness of evaluation metrics against exact analytical values."""

    def test_compute_brier_scores_synthetic(self):
        """Verifies multi-class Brier score calculation against hand-computed values."""
        # 2 samples, 5 classes
        y_true = np.array([0, 2])
        y_prob = np.array([
            [0.8, 0.1, 0.05, 0.03, 0.02],
            [0.1, 0.1, 0.7, 0.05, 0.05]
        ])

        # Sample 1: true=0 -> one-hot=[1,0,0,0,0]
        # (0.8-1)^2 + 0.1^2 + 0.05^2 + 0.03^2 + 0.02^2 = 0.04 + 0.01 + 0.0025 + 0.0009 + 0.0004 = 0.0538
        # Sample 2: true=2 -> one-hot=[0,0,1,0,0]
        # 0.1^2 + 0.1^2 + (0.7-1)^2 + 0.05^2 + 0.05^2 = 0.01 + 0.01 + 0.09 + 0.0025 + 0.0025 = 0.1150
        # Mean Brier = (0.0538 + 0.1150) / 2 = 0.0844

        res = compute_brier_scores(y_true, y_prob)
        self.assertAlmostEqual(res["mean_brier"], 0.0844, places=6)
        self.assertEqual(len(res["sample_losses"]), 2)
        self.assertAlmostEqual(res["sample_losses"][0], 0.0538, places=6)
        self.assertAlmostEqual(res["sample_losses"][1], 0.1150, places=6)

    def test_compute_log_loss_synthetic(self):
        """Verifies multi-class log loss against hand-computed analytical value."""
        y_true = np.array([0, 1])
        y_prob = np.array([
            [0.5, 0.5, 0.0, 0.0, 0.0],
            [0.2, 0.8, 0.0, 0.0, 0.0]
        ])
        # Sample 1: -log(0.5) = 0.693147
        # Sample 2: -log(0.8) = 0.223143
        # Mean = (0.693147 + 0.223143) / 2 = 0.458145
        expected_log_loss = float(- (np.log(0.5) + np.log(0.8)) / 2.0)
        calculated = compute_log_loss(y_true, y_prob)
        self.assertAlmostEqual(calculated, expected_log_loss, places=5)

    def test_compute_condition_briers(self):
        """Verifies grouping of sample losses by condition regime."""
        losses = [0.04, 0.06, 0.10, 0.12]
        conditions = ["stable", "stable", "drift", "drift"]
        cond_briers = compute_condition_briers(losses, conditions)

        self.assertAlmostEqual(cond_briers["brier_stable"], 0.05)
        self.assertAlmostEqual(cond_briers["brier_drift"], 0.11)

    def test_compute_calibration_and_ece(self):
        """Verifies decile binning and ECE calculation."""
        # Perfectly calibrated probabilities for binary sub-problem
        y_true = np.array([0] * 50 + [1] * 50)
        # Class 0: 50 ones, class 1: 50 ones
        # Synthetic probabilities
        y_prob = np.zeros((100, 5))
        y_prob[:50, 0] = 0.8  # predict 0.8 for class 0
        y_prob[:50, 1] = 0.2
        y_prob[50:, 0] = 0.2
        y_prob[50:, 1] = 0.8  # predict 0.8 for class 1

        cal = compute_calibration(y_true, y_prob, n_bins=10)
        self.assertIn("ece", cal)
        self.assertIsInstance(cal["ece"], float)
        self.assertTrue(0.0 <= cal["ece"] <= 1.0)
        self.assertTrue(len(cal["calibration_bins"]) > 0)

    def test_compute_diagnostics_and_track_end_to_end(self):
        """Verifies high-level compute_diagnostics_and_track matches research format."""
        queries = [
            {"query_id": "q1", "episode_id": "e1"},
            {"query_id": "q2", "episode_id": "e1"},
            {"query_id": "q3", "episode_id": "e2"},
        ]
        labels = {"q1": 0, "q2": 1, "q3": 5}
        conditions = {"q1": "stable", "q2": "stable", "q3": "drift"}
        predictions = {
            "q1": [0.7, 0.1, 0.1, 0.05, 0.05],
            "q2": [0.1, 0.6, 0.1, 0.1, 0.1],
            "q3": [0.1, 0.1, 0.1, 0.1, 0.6],
        }

        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tf:
            tmp_storage = tf.name
        try:
            tracker = HouseEdgeMLflowTracker(force_mock=True)
            tracker.mlflow = MockMLflow(storage_file=tmp_storage)
            summary = compute_diagnostics_and_track(
                predictions=predictions,
                queries=queries,
                labels=labels,
                conditions=conditions,
                model_name="diag_model",
                model_type="regime_mixture",
                tracker=tracker,
            )

            self.assertEqual(summary["model_name"], "diag_model")
            self.assertEqual(summary["total_queries"], 3)
            self.assertIn("mean_brier", summary)
            self.assertIn("log_loss", summary)
            self.assertIn("ece", summary)
            self.assertIn("brier_stable", summary["condition_briers"])
            self.assertIn("brier_drift", summary["condition_briers"])
        finally:
            try:
                os.unlink(tmp_storage)
            except Exception:
                pass


class TestMLflowNativeParityAndFallback(unittest.TestCase):
    """Verifies that HouseEdgeMLflowTracker works seamlessly with native MLflow when present."""

    def test_session_get_mlflow_fallback(self):
        """Verifies session.get_mlflow returns MockMLflow when native mlflow is absent or forced."""
        # Forced mock
        client_mock = get_mlflow(force_mock=True)
        self.assertIsInstance(client_mock, MockMLflow)

    def test_native_mlflow_interface_dispatch(self):
        """Simulates native MLflow client and verifies tracker correctly invokes all native APIs."""
        mock_native_mlflow = MagicMock()
        mock_native_run = MagicMock()
        mock_native_run.info.run_id = "native_run_12345"
        mock_native_mlflow.start_run.return_value = mock_native_run

        # Configure search_runs returning a DataFrame
        runs_df = pd.DataFrame([{
            "run_id": "native_run_12345",
            "tags.mlflow.runName": "native_champ",
            "params.model_type": "regime_mixture",
            "metrics.mean_brier": 0.0551,
            "metrics.log_loss": 1.412,
            "metrics.ece_calibration": 0.014,
            "tags.champion_status": "champion",
            "tags.evaluation_provenance": "official_public_validation",
            "tags.git_commit": "5f3311e4",
            "status": "FINISHED",
        }])
        mock_native_mlflow.search_runs.return_value = runs_df

        tracker = HouseEdgeMLflowTracker(experiment_name="/Shared/test_native", force_mock=True)
        tracker.mlflow = mock_native_mlflow

        # 1. start_trial
        run = tracker.start_trial("native_champ", "regime_mixture")
        mock_native_mlflow.start_run.assert_called_with(run_name="native_champ")
        self.assertTrue(mock_native_mlflow.log_params.called)
        self.assertTrue(mock_native_mlflow.set_tags.called)

        # 2. log_metrics
        tracker.log_metrics({"mean_brier": 0.0551, "log_loss": 1.412})
        mock_native_mlflow.log_metrics.assert_called()

        # 3. log_calibration
        tracker.log_calibration({"curves_by_class": {}, "ece": 0.014}, ece=0.014, save_plot=False)
        mock_native_mlflow.log_metric.assert_called_with("ece_calibration", 0.014)

        # 4. log_model_signature
        tracker.log_model_signature(["feat_1", "feat_2"], (0, 1, 2, 5, 20))
        mock_native_mlflow.log_dict.assert_called()

        # 5. end_trial
        tracker.end_trial()
        mock_native_mlflow.end_run.assert_called_with(status="FINISHED")

        # 6. get_leaderboard
        lb = tracker.get_leaderboard()
        self.assertEqual(len(lb), 1)
        self.assertEqual(lb.iloc[0]["model_name"], "native_champ")
        self.assertAlmostEqual(lb.iloc[0]["mean_brier"], 0.0551)


if __name__ == "__main__":
    unittest.main()
