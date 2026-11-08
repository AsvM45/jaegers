"""Comprehensive unit tests for JAEGERS dashboard statistical engine and export generator.

Tests:
- Condition-stratified paired episode bootstrap math, reproducibility, and edge cases.
- Multi-class calibration curves across 10 probability bins for all 5 payout classes.
- Expected Calibration Error (ECE), Maximum Calibration Error (MCE), and Brier decomposition.
- Murphy (1973) Brier score decomposition (Reliability, Resolution, Uncertainty).
- Rare payout (20x) tail diagnostics (MAE, 80% CI width, calibration correlation, ratio).
- Pre-registered component ablation analysis (waterfall ordering, relative deltas, significance).
- Hyperparameter and Optuna sweep analysis (trajectories, correlations, parallel coordinates).
- Formal hypothesis verification engine (CONFIRMED, REFUTED, INCONCLUSIVE).
- Reproducible export engine (CSV, JSON, Markdown matching research/report.py, file writing).
"""

from __future__ import annotations

import csv
import json
import math
from pathlib import Path
import shutil
import sys
import tempfile
from typing import Dict, List
import unittest

# Ensure repo root is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np

from dashboard.export import (
    export_ablations_csv,
    export_condition_breakdown_csv,
    export_hypotheses_json,
    export_leaderboard_csv,
    export_run_manifest_json,
    export_to_file,
    export_trial_config_json,
    generate_markdown_report,
)
from dashboard.schema import (
    CalibrationBin,
    ComponentAblation,
    ConditionLosses,
    HypothesisRecord,
    PairedComparison,
    ProvenanceType,
    TrialRecord,
)
from dashboard.stats import (
    analyze_component_ablations,
    analyze_hyperparameter_sweep,
    analyze_rare_payout_tail,
    calculate_calibration_curve,
    decompose_brier_score,
    paired_episode_bootstrap,
    verify_hypothesis,
)


class TestPairedEpisodeBootstrap(unittest.TestCase):
    """Tests for condition-stratified paired episode bootstrapping."""

    def setUp(self) -> None:
        # Create deterministic synthetic episode errors
        # 4 conditions: stable, short_history, drift, shared_change
        # 10 episodes per condition (40 total)
        self.conditions: Dict[str, str] = {}
        self.baseline_errors: Dict[str, float] = {}
        self.candidate_better: Dict[str, float] = {}
        self.candidate_worse: Dict[str, float] = {}

        cond_names = ["stable", "short_history", "drift", "shared_change"]
        for c_idx, c_name in enumerate(cond_names):
            for i in range(10):
                ep_id = f"ep_{c_name}_{i:02d}"
                self.conditions[ep_id] = c_name
                # Baseline error around 0.35 + variation
                base_err = 0.35 + 0.02 * c_idx + 0.01 * (i % 3)
                self.baseline_errors[ep_id] = base_err
                # Better candidate: 0.02 lower on all episodes
                self.candidate_better[ep_id] = base_err - 0.02
                # Worse candidate: 0.03 higher on all episodes
                self.candidate_worse[ep_id] = base_err + 0.03

    def test_paired_bootstrap_supported_improvement(self) -> None:
        """Test candidate with genuine improvement achieves supported_improvement=True."""
        res = paired_episode_bootstrap(
            candidate_errors=self.candidate_better,
            baseline_errors=self.baseline_errors,
            episode_conditions=self.conditions,
            n_resamples=1000,
            seed=42,
        )
        self.assertAlmostEqual(res.mean_delta, -0.02, places=4)
        self.assertLess(res.ci95_high, 0.0)
        self.assertTrue(res.supported_improvement)
        self.assertAlmostEqual(res.p_improvement, 1.0, places=2)
        self.assertEqual(res.n_episodes, 40)
        self.assertEqual(len(res.by_condition_delta), 4)
        for c in ["stable", "short_history", "drift", "shared_change"]:
            self.assertAlmostEqual(res.by_condition_delta[c], -0.02, places=4)

    def test_paired_bootstrap_degradation(self) -> None:
        """Test candidate with degradation achieves supported_improvement=False and p_imp ~ 0."""
        res = paired_episode_bootstrap(
            candidate_errors=self.candidate_worse,
            baseline_errors=self.baseline_errors,
            episode_conditions=self.conditions,
            n_resamples=1000,
            seed=42,
        )
        self.assertAlmostEqual(res.mean_delta, 0.03, places=4)
        self.assertGreater(res.ci95_low, 0.0)
        self.assertFalse(res.supported_improvement)
        self.assertAlmostEqual(res.p_improvement, 0.0, places=2)

    def test_paired_bootstrap_deterministic_reproducibility(self) -> None:
        """Test that same seed produces identical results."""
        r1 = paired_episode_bootstrap(
            self.candidate_better, self.baseline_errors, self.conditions, n_resamples=500, seed=123
        )
        r2 = paired_episode_bootstrap(
            self.candidate_better, self.baseline_errors, self.conditions, n_resamples=500, seed=123
        )
        self.assertEqual(r1.ci95_low, r2.ci95_low)
        self.assertEqual(r1.ci95_high, r2.ci95_high)
        self.assertEqual(r1.mean_delta, r2.mean_delta)

    def test_paired_bootstrap_single_episode_edge_case(self) -> None:
        """Test N=1 edge case returns exact difference without crashing."""
        cand_one = {"ep_01": 0.32}
        base_one = {"ep_01": 0.36}
        cond_one = {"ep_01": "stable"}

        res = paired_episode_bootstrap(cand_one, base_one, cond_one, n_resamples=500, seed=0)
        self.assertEqual(res.n_episodes, 1)
        self.assertAlmostEqual(res.mean_delta, -0.04)
        self.assertAlmostEqual(res.ci95_low, -0.04)
        self.assertAlmostEqual(res.ci95_high, -0.04)
        self.assertFalse(res.supported_improvement)  # Cannot claim supported improvement with N=1

    def test_paired_bootstrap_differing_episodes_handling(self) -> None:
        """Test differing episode sets in relaxed mode intersects, strict mode raises."""
        cand_diff = dict(self.candidate_better)
        cand_diff["extra_ep"] = 0.30

        # Relaxed mode (default) intersects shared episodes
        res = paired_episode_bootstrap(
            candidate_errors=cand_diff,
            baseline_errors=self.baseline_errors,
            episode_conditions=self.conditions,
            strict_episodes=False,
        )
        self.assertEqual(res.n_episodes, 40)

        # Strict mode raises ValueError
        with self.assertRaises(ValueError):
            paired_episode_bootstrap(
                candidate_errors=cand_diff,
                baseline_errors=self.baseline_errors,
                episode_conditions=self.conditions,
                strict_episodes=True,
            )

    def test_paired_bootstrap_empty_or_zero_shared(self) -> None:
        """Test empty input or disjoint sets raises ValueError."""
        with self.assertRaises(ValueError):
            paired_episode_bootstrap({}, self.baseline_errors, self.conditions)

        with self.assertRaises(ValueError):
            paired_episode_bootstrap({"ep_a": 0.1}, {"ep_b": 0.2}, self.conditions)


class TestCalibrationCurvesAndBrierDecomposition(unittest.TestCase):
    """Tests for multi-class calibration curves, ECE, MCE, and Brier decomposition."""

    def test_perfect_calibration_low_ece(self) -> None:
        """Test well-calibrated distribution produces very low ECE."""
        rng = np.random.default_rng(42)
        n = 1000
        # True distribution for 5 classes: (0.50, 0.25, 0.15, 0.08, 0.02)
        true_dist = np.array([0.50, 0.25, 0.15, 0.08, 0.02])
        labels = rng.choice(5, size=n, p=true_dist)

        # Predicted probabilities match true distribution with small Dirichlet noise
        probs = np.tile(true_dist, (n, 1))

        rep = calculate_calibration_curve(probs, labels, n_bins=10)
        self.assertEqual(len(rep.bins), 50)  # 5 classes * 10 bins
        self.assertLess(rep.overall_ece, 0.05)
        self.assertGreater(rep.overall_brier, 0.0)

    def test_calibration_curve_with_payout_labels(self) -> None:
        """Test calculation accepts raw payout values [0, 1, 2, 5, 20]."""
        probs = np.array(
            [
                [0.7, 0.2, 0.1, 0.0, 0.0],
                [0.1, 0.6, 0.2, 0.1, 0.0],
                [0.0, 0.1, 0.7, 0.1, 0.1],
                [0.0, 0.0, 0.1, 0.8, 0.1],
                [0.0, 0.0, 0.0, 0.2, 0.8],
            ]
        )
        labels = [0, 1, 2, 5, 20]  # Payout values directly
        conditions = ["stable", "short_history", "drift", "shared_change", "stable"]

        rep = calculate_calibration_curve(probs, labels, n_bins=10, conditions=conditions)
        self.assertEqual(len(rep.bins), 50)
        self.assertIn(20, rep.class_brier)
        self.assertIn("stable", rep.by_condition_brier)
        self.assertIn("drift", rep.by_condition_brier)
        self.assertGreater(rep.overall_mce, 0.0)

    def test_murphy_brier_score_decomposition(self) -> None:
        """Test Murphy (1973) decomposition: Brier = Reliability - Resolution + Uncertainty."""
        rng = np.random.default_rng(101)
        n = 500
        # Random probabilities
        raw = rng.exponential(scale=1.0, size=(n, 5))
        probs = raw / raw.sum(axis=1, keepdims=True)
        labels = rng.choice(5, size=n)

        decomp = decompose_brier_score(probs, labels, n_bins=10)
        brier = decomp["overall_brier"]
        rel = decomp["reliability"]
        res = decomp["resolution"]
        unc = decomp["uncertainty"]

        # Check Murphy formula: Brier ≈ Reliability - Resolution + Uncertainty
        # In discrete binning with sample means, this identity holds within small discretization residual
        reconstructed = rel - res + unc
        self.assertAlmostEqual(brier, reconstructed, delta=0.08)


class TestRarePayoutTailDiagnostics(unittest.TestCase):
    """Tests for rare jackpot class (20x) tail diagnostics."""

    def test_analyze_rare_payout_tail_math(self) -> None:
        """Test tail diagnostics calculate MAE, 80% CI width, and correlation."""
        # Create dataset where rare 20x jackpot occurs ~2% of the time
        n = 500
        probs = np.zeros((n, 5))
        probs[:, 0] = 0.70
        probs[:, 1] = 0.15
        probs[:, 2] = 0.10
        probs[:, 3] = 0.03
        probs[:, 4] = 0.02  # 2% rare jackpot predicted

        labels = [0] * 490 + [20] * 10  # 10 jackpot occurrences (2%)

        diag = analyze_rare_payout_tail(probs, labels)
        self.assertEqual(diag.payout_class, 20)
        self.assertAlmostEqual(diag.mean_predicted_prob, 0.02, places=3)
        self.assertAlmostEqual(diag.true_frequency, 0.02, places=3)
        self.assertAlmostEqual(diag.under_over_prediction_ratio, 1.0, places=1)
        self.assertIsNotNone(diag.mae)
        self.assertIsNotNone(diag.ci80_width)
        self.assertGreater(diag.ci80_width, 0.0)

    def test_zero_jackpots_handled_gracefully(self) -> None:
        """Test dataset with 0 jackpots does not trigger division by zero."""
        n = 100
        probs = np.tile([0.8, 0.1, 0.08, 0.02, 0.0], (n, 1))
        labels = [0] * n  # Zero 20x jackpots

        diag = analyze_rare_payout_tail(probs, labels)
        self.assertEqual(diag.true_frequency, 0.0)
        self.assertEqual(diag.under_over_prediction_ratio, 1.0)
        self.assertEqual(diag.calibration_correlation, 0.0)


class TestComponentAblationAnalyzer(unittest.TestCase):
    """Tests for pre-registered component ablation analyzer."""

    def test_analyze_component_ablations_waterfall_and_ranking(self) -> None:
        """Test waterfall sequencing, relative deltas, and impact sorting."""
        ablations = [
            ComponentAblation(
                variant_name="nosig",
                removed_component="Signal Feature",
                hypothesis="Dropping signal causes slight drop",
                official_points=55.000069,
                official_points_delta=-0.121546,
                ci95_points=(-0.25, 0.01),
                supported=False,
            ),
            ComponentAblation(
                variant_name="nostack",
                removed_component="GBDT Stacker",
                hypothesis="Stacker is critical to ensemble",
                official_points=52.836199,
                official_points_delta=-2.285416,
                ci95_points=(-2.50, -2.05),
                supported=True,
            ),
            ComponentAblation(
                variant_name="no_size_experts",
                removed_component="Size Experts",
                hypothesis="Size regime mixture is essential",
                official_points=53.683293,
                official_points_delta=-1.438322,
                ci95_points=(-1.65, -1.20),
                supported=True,
            ),
        ]

        res = analyze_component_ablations(ablations, baseline_points=55.121615)
        self.assertEqual(len(res.ranked_ablations), 3)
        # Most negative delta first (nostack: -2.285)
        self.assertEqual(res.ranked_ablations[0].variant_name, "nostack")
        self.assertEqual(res.max_impact_component, "GBDT Stacker")
        self.assertEqual(res.min_impact_component, "Signal Feature")
        self.assertEqual(res.supported_degradations_count, 2)
        # Waterfall steps: baseline + 3 ablations = 4 steps
        self.assertEqual(len(res.waterfall_steps), 4)
        self.assertEqual(res.waterfall_steps[0]["step"], "Baseline Champion")


class TestHyperparameterSweepAnalyzer(unittest.TestCase):
    """Tests for hyperparameter sweep trajectory and parameter correlations."""

    def test_hyperparameter_sweep_analysis(self) -> None:
        """Test trajectory calculation and parameter correlations."""
        trials = [
            TrialRecord(
                trial_id="t1",
                study_name="optuna_sweep",
                family="jaeger",
                status="SUCCEEDED",
                provenance=ProvenanceType.TRAIN_GROUP_CV,
                mean_brier=0.380,
                created_at="2026-11-01T10:00:00",
                hyperparameters={"learning_rate": 0.01, "max_depth": 3, "tag": "smoke"},
            ),
            TrialRecord(
                trial_id="t2",
                study_name="optuna_sweep",
                family="jaeger",
                status="SUCCEEDED",
                provenance=ProvenanceType.TRAIN_GROUP_CV,
                mean_brier=0.365,
                created_at="2026-11-01T10:05:00",
                hyperparameters={"learning_rate": 0.05, "max_depth": 4, "tag": "smoke"},
            ),
            TrialRecord(
                trial_id="t3",
                study_name="optuna_sweep",
                family="jaeger",
                status="SUCCEEDED",
                provenance=ProvenanceType.TRAIN_GROUP_CV,
                mean_brier=0.360,
                created_at="2026-11-01T10:10:00",
                hyperparameters={"learning_rate": 0.10, "max_depth": 5, "tag": "smoke"},
            ),
        ]

        analysis = analyze_hyperparameter_sweep(trials, metric_key="mean_brier", maximize=False)
        self.assertEqual(len(analysis.trajectory), 3)
        self.assertEqual(analysis.best_trial_id, "t3")
        self.assertAlmostEqual(analysis.best_metric_value, 0.360)
        # Trajectory running best strictly decreases
        self.assertAlmostEqual(analysis.trajectory[0]["running_best"], 0.380)
        self.assertAlmostEqual(analysis.trajectory[1]["running_best"], 0.365)
        self.assertAlmostEqual(analysis.trajectory[2]["running_best"], 0.360)
        # Numeric parameters correlated
        self.assertIn("learning_rate", analysis.param_correlations)
        self.assertIn("max_depth", analysis.param_correlations)
        self.assertNotIn("tag", analysis.param_correlations)  # String excluded


class TestHypothesisVerificationEngine(unittest.TestCase):
    """Tests for hypothesis verification engine."""

    def test_verify_hypothesis_confirmed_degradation(self) -> None:
        """Test confirming a degradation hypothesis when component removal degrades score."""
        hyp = HypothesisRecord(
            id="H-STACK",
            preregistered_timestamp="2026-11-01",
            component="GBDT Stacker",
            statement="Removing stacker significantly degrades points",
            expected_direction="worse",
        )

        res = verify_hypothesis(
            hyp,
            observed_points_diff=-2.285,
            ci95_points=(-2.50, -2.05),
        )
        self.assertEqual(res.status, "CONFIRMED")
        self.assertEqual(res.decision, "MAINTAIN_BASELINE")

    def test_verify_hypothesis_inconclusive(self) -> None:
        """Test CI spanning zero results in INCONCLUSIVE."""
        hyp = HypothesisRecord(
            id="H-SIGNAL",
            preregistered_timestamp="2026-11-01",
            component="Signal",
            statement="Dropping signal significantly degrades points",
            expected_direction="worse",
        )

        res = verify_hypothesis(
            hyp,
            observed_points_diff=-0.121,
            ci95_points=(-0.25, 0.01),
        )
        self.assertEqual(res.status, "INCONCLUSIVE")
        self.assertEqual(res.decision, "NO_PROMOTION")

    def test_verify_hypothesis_refuted(self) -> None:
        """Test unexpected result refutes hypothesis."""
        hyp = HypothesisRecord(
            id="H-NEW",
            preregistered_timestamp="2026-11-01",
            component="Feature X",
            statement="Adding Feature X improves score",
            expected_direction="better",
        )

        # But points actually degraded significantly!
        res = verify_hypothesis(
            hyp,
            observed_points_diff=-0.85,
            ci95_points=(-1.10, -0.60),
        )
        self.assertEqual(res.status, "REFUTED")
        self.assertEqual(res.decision, "REJECT")


class TestReproducibleExportEngine(unittest.TestCase):
    """Tests for CSV, JSON, Markdown, and file exports."""

    def setUp(self) -> None:
        self.temp_dir = tempfile.mkdtemp()
        self.trials = [
            TrialRecord(
                trial_id="champ_001",
                study_name="core_sweep",
                family="jaeger",
                status="SUCCEEDED",
                provenance=ProvenanceType.PUBLIC_VALIDATION,
                is_champion=True,
                official_points=55.121615,
                condition_losses=ConditionLosses(0.067316, 0.116980, 0.092323, 0.077390),
                wall_seconds=42.5,
                source_commit="deead43a",
                created_at="2026-11-01T12:00:00",
                hyperparameters={"lr": 0.05, "depth": 4},
            ),
            TrialRecord(
                trial_id="cv_002",
                study_name="core_sweep",
                family="frequency",
                status="SUCCEEDED",
                provenance=ProvenanceType.TRAIN_GROUP_CV,
                mean_brier=0.372100,
                wall_seconds=12.1,
                source_commit="deead43a",
                created_at="2026-11-01T12:05:00",
                hyperparameters={"smoothing": 0.1},
            ),
            TrialRecord(
                trial_id="fail_003",
                study_name="core_sweep",
                family="lightgbm",
                status="FAILED",
                provenance=ProvenanceType.TRAIN_GROUP_CV,
                wall_seconds=3.2,
                source_commit="deead43a",
                created_at="2026-11-01T12:10:00",
                error_message="CUDA out of memory",
            ),
        ]

    def tearDown(self) -> None:
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_export_leaderboard_csv(self) -> None:
        """Test exporting leaderboard produces valid CSV with expected columns."""
        csv_str = export_leaderboard_csv(self.trials)
        reader = list(csv.reader(csv_str.strip().split("\n")))
        self.assertEqual(len(reader), 4)  # Header + 3 trials
        self.assertIn("official_points", reader[0])
        self.assertIn("mean_brier", reader[0])
        self.assertEqual(reader[1][0], "champ_001")
        self.assertEqual(reader[1][5], "TRUE")  # is_champion

    def test_export_condition_breakdown_csv(self) -> None:
        """Test exporting condition breakdown produces condition columns."""
        csv_str = export_condition_breakdown_csv(self.trials)
        reader = list(csv.reader(csv_str.strip().split("\n")))
        self.assertGreaterEqual(len(reader), 2)
        headers = reader[0]
        for col in ["stable", "short_history", "drift", "shared_change", "mean_ratio"]:
            self.assertIn(col, headers)

    def test_export_ablations_csv(self) -> None:
        """Test exporting ablations produces valid CSV."""
        ablations = [
            ComponentAblation(
                variant_name="nostack",
                removed_component="GBDT Stacker",
                hypothesis="Stacker essential",
                official_points=52.836199,
                official_points_delta=-2.285416,
                ci95_points=(-2.50, -2.05),
                supported=True,
            )
        ]
        csv_str = export_ablations_csv(ablations)
        reader = list(csv.reader(csv_str.strip().split("\n")))
        self.assertEqual(len(reader), 2)
        self.assertEqual(reader[1][0], "nostack")
        self.assertEqual(reader[1][8], "TRUE")

    def test_export_trial_config_and_manifest_json(self) -> None:
        """Test exporting JSON configs and manifests."""
        cfg_json = export_trial_config_json(self.trials[0])
        parsed_cfg = json.loads(cfg_json)
        self.assertEqual(parsed_cfg["trial_id"], "champ_001")
        self.assertEqual(parsed_cfg["hyperparameters"]["lr"], 0.05)

        manifest_json = export_run_manifest_json(self.trials)
        parsed_manifest = json.loads(manifest_json)
        self.assertEqual(parsed_manifest["total_runs"], 3)
        self.assertEqual(parsed_manifest["status_counts"]["SUCCEEDED"], 2)
        self.assertEqual(parsed_manifest["status_counts"]["FAILED"], 1)

    def test_generate_markdown_report_matches_format(self) -> None:
        """Test Markdown report matches research/report.py structure."""
        comparisons = [
            PairedComparison(
                candidate_id="cv_002",
                baseline_id="champ_001",
                provenance=ProvenanceType.TRAIN_GROUP_CV,
                mean_delta=-0.015000,
                ci95_low=-0.025000,
                ci95_high=-0.005000,
                p_improvement=0.99,
                supported_improvement=True,
                n_episodes=40,
                bootstrap_iterations=1000,
            )
        ]

        md = generate_markdown_report(
            self.trials,
            baseline_id="champ_001",
            comparisons=comparisons,
        )

        self.assertIn("# House Edge experiment evidence", md)
        self.assertIn("Completed runs: 2; distinct configurations: 2.", md)
        self.assertIn("These are sampled-label episode-grouped Brier losses", md)
        self.assertIn("| Trial | Family | Brier ↓ | Seconds | Validation-target exposure |", md)
        self.assertIn("## Condition diagnostics", md)
        self.assertIn("## Paired episode differences", md)
        self.assertIn("- cv_002: delta -0.015000; 95% interval [-0.025000, -0.005000].", md)
        self.assertIn("## Failures", md)
        self.assertIn("- fail_003: FAILED; CUDA out of memory.", md)

    def test_export_to_file(self) -> None:
        """Test safe file writing utility."""
        target = Path(self.temp_dir) / "sub" / "report.md"
        content = "# Test Report Content\n"
        path = export_to_file(content, target)
        self.assertTrue(path.exists())
        self.assertEqual(path.read_text(encoding="utf-8"), content)


if __name__ == "__main__":
    unittest.main()
