"""Comprehensive Unit Test Suite for PySpark Feature Parity & Strict Temporal Invariance

Tests:
1. Feature Manifest & Column Sequence: 471 features (468 historical + 3 query).
2. Parity across steady, balanced, and jackpot machines against offline NumPy FeatureComputer.
3. Strict Temporal Boundary Invariant: perturbing history at tick >= cutoff produces 0.0 change.
4. Peer machine future isolation: sibling spins at tick >= cutoff do not leak into peer aggregations.
5. Missing history edge cases: smooth Dirichlet uniform prior [0.2, 0.2, 0.2, 0.2, 0.2] fallback.
6. Real public train data parity verification.
7. Native PySpark feature expressions.
8. End-to-end Gold Delta Lake pipeline execution.
"""

from __future__ import annotations

import os
from pathlib import Path
import shutil
import sys
import tempfile
import types
import unittest

import numpy as np
import pandas as pd

# Safe mock for joblib if not installed in runtime environment
if "joblib" not in sys.modules:
    try:
        import joblib  # noqa: F401
    except ImportError:
        sys.modules["joblib"] = types.ModuleType("joblib")

# Add repository root and Databricks src directory to path
REPO_ROOT = Path(__file__).resolve().parents[1]
DATABRICKS_DIR = REPO_ROOT / "Jaeger_Main" / "House_Edge" / "databricks"
if str(DATABRICKS_DIR) not in sys.path:
    sys.path.insert(0, str(DATABRICKS_DIR))

from src.bronze import run_bronze_ingest
from src.gold import (
    ALL_FEATURE_GROUPS,
    FEATURE_NAMES,
    HISTORICAL_FEATURE_NAMES,
    QUERY_FEATURE_NAMES,
    compute_gold_features,
    compute_query_features,
    get_feature_names,
    get_gold_feature_schema,
    get_historical_feature_names,
    get_native_feature_expressions,
    run_gold_pipeline,
)
from src.mock_engine import MockSparkSession, col, lit, when
from src.parity import ParityAuditResult, verify_feature_parity
from src.silver import run_silver_pipeline


class TestFeatureManifestAndMetadata(unittest.TestCase):
    """Verifies feature manifest structure, column counts, and schema definitions."""

    def test_feature_manifest_counts(self):
        names = get_feature_names()
        historical_names = get_historical_feature_names()
        self.assertEqual(len(names), 471)
        self.assertEqual(len(historical_names), 468)
        self.assertEqual(len(QUERY_FEATURE_NAMES), 3)

        # Check unique column names
        self.assertEqual(len(names), len(set(names)), "Feature names must be strictly unique")

    def test_group_breakdown(self):
        names = get_feature_names()
        counts_by_group: dict[str, int] = {}
        for n in names:
            g = n.split("/")[0]
            counts_by_group[g] = counts_by_group.get(g, 0) + 1

        expected_counts = {
            "type": 3,
            "lags": 48,
            "pairs": 280,
            "windows": 18,
            "decays": 18,
            "transitions": 48,
            "missingness": 11,
            "changes": 7,
            "peers": 11,
            "type_lag": 24,
            "current_signal": 3,
        }
        self.assertEqual(counts_by_group, expected_counts)

    def test_gold_feature_schema(self):
        schema = get_gold_feature_schema()
        self.assertEqual(len(schema), 6 + 471)  # 6 metadata + 471 features
        self.assertEqual(schema.names[:6], ["query_id", "episode_id", "machine_id", "cutoff", "split", "condition"])
        self.assertEqual(schema.names[6:], FEATURE_NAMES)

    def test_manifest_matches_research_registry(self):
        try:
            from Jaeger_Main.House_Edge.research.feature_api import FeatureComputer, REGISTRY
        except ImportError:
            from research.feature_api import FeatureComputer, REGISTRY

        fc = FeatureComputer({("ep1", "m0"): {0: 0}})
        q = {"query_id": "q1", "episode_id": "ep1", "machine_id": "m0", "machine_type": "steady", "cutoff": 1, "signal": 0}
        _, ref_names = fc.row(q, groups=list(REGISTRY.keys()))
        self.assertEqual(get_feature_names(), list(ref_names))


class TestFeatureParitySynthetic(unittest.TestCase):
    """Verifies PySpark vs. NumPy parity across synthetic multi-machine scenarios."""

    def setUp(self):
        self.spark = MockSparkSession()

        # Build synthetic dataset with steady, balanced, and jackpot machines
        q_records = [
            {"query_id": "q_steady", "episode_id": "ep1", "machine_id": "m0", "machine_type": "steady", "signal": 1, "cutoff": 50, "split": "train", "condition": "stable"},
            {"query_id": "q_balanced", "episode_id": "ep1", "machine_id": "m1", "machine_type": "balanced", "signal": 0, "cutoff": 60, "split": "train", "condition": "drift"},
            {"query_id": "q_jackpot", "episode_id": "ep1", "machine_id": "m2", "machine_type": "jackpot", "signal": -1, "cutoff": 45, "split": "train", "condition": "short_history"},
        ]
        s_records = [
            # m0 (steady)
            {"episode_id": "ep1", "machine_id": "m0", "tick": 5, "payout": 1, "payout_index": 1, "is_win": 1, "split": "train"},
            {"episode_id": "ep1", "machine_id": "m0", "tick": 15, "payout": 2, "payout_index": 2, "is_win": 1, "split": "train"},
            {"episode_id": "ep1", "machine_id": "m0", "tick": 30, "payout": 0, "payout_index": 0, "is_win": 0, "split": "train"},
            {"episode_id": "ep1", "machine_id": "m0", "tick": 49, "payout": 1, "payout_index": 1, "is_win": 1, "split": "train"},
            # m1 (balanced)
            {"episode_id": "ep1", "machine_id": "m1", "tick": 10, "payout": 5, "payout_index": 3, "is_win": 1, "split": "train"},
            {"episode_id": "ep1", "machine_id": "m1", "tick": 25, "payout": 1, "payout_index": 1, "is_win": 1, "split": "train"},
            {"episode_id": "ep1", "machine_id": "m1", "tick": 59, "payout": 2, "payout_index": 2, "is_win": 1, "split": "train"},
            # m2 (jackpot)
            {"episode_id": "ep1", "machine_id": "m2", "tick": 2, "payout": 20, "payout_index": 4, "is_win": 1, "split": "train"},
            {"episode_id": "ep1", "machine_id": "m2", "tick": 44, "payout": 0, "payout_index": 0, "is_win": 0, "split": "train"},
        ]

        self.spark.createDataFrame(pd.DataFrame(q_records)).write.format("delta").mode("overwrite").saveAsTable("silver_queries")
        self.spark.createDataFrame(pd.DataFrame(s_records)).write.format("delta").mode("overwrite").saveAsTable("silver_spins")

    def tearDown(self):
        self.spark.stop()

    def test_synthetic_parity_audit(self):
        result: ParityAuditResult = verify_feature_parity(
            spark=self.spark,
            tolerance=1e-5,
            check_temporal_boundary=True,
            force_mock=True
        )
        self.assertEqual(result.status, "PASSED")
        self.assertEqual(result.total_queries_checked, 3)
        self.assertEqual(result.total_features_checked, 471)
        self.assertTrue(result.column_manifest_match)
        self.assertLess(result.max_abs_difference, 1e-5)
        self.assertEqual(result.nan_count, 0)
        self.assertEqual(result.inf_count, 0)
        self.assertEqual(result.null_count, 0)
        self.assertTrue(result.temporal_boundary_pass)


class TestStrictTemporalBoundaryInvariant(unittest.TestCase):
    """Tests strict temporal boundary: tick < cutoff invariance under future perturbations."""

    def setUp(self):
        self.spark = MockSparkSession()

    def tearDown(self):
        self.spark.stop()

    def test_future_spin_perturbation_invariant(self):
        cutoff = 100
        q_df = pd.DataFrame([{
            "query_id": "q_boundary",
            "episode_id": "ep_b",
            "machine_id": "m0",
            "machine_type": "steady",
            "signal": 0,
            "cutoff": cutoff,
            "split": "train",
            "condition": "stable"
        }])
        # Real past spins (all strictly tick < 100)
        s_past = pd.DataFrame([
            {"episode_id": "ep_b", "machine_id": "m0", "tick": 10, "payout": 1, "payout_index": 1, "is_win": 1, "split": "train"},
            {"episode_id": "ep_b", "machine_id": "m0", "tick": 50, "payout": 2, "payout_index": 2, "is_win": 1, "split": "train"},
            {"episode_id": "ep_b", "machine_id": "m0", "tick": 99, "payout": 5, "payout_index": 3, "is_win": 1, "split": "train"},
            {"episode_id": "ep_b", "machine_id": "m1", "tick": 40, "payout": 0, "payout_index": 0, "is_win": 0, "split": "train"},
        ])

        # Compute baseline Gold features
        df_base = compute_gold_features(
            spark=self.spark,
            df_queries=self.spark.createDataFrame(q_df),
            df_spins=self.spark.createDataFrame(s_past)
        )
        base_features = df_base.toPandas()[FEATURE_NAMES].values.astype(np.float32)[0]

        # Add malicious future spins at tick = 100 (exactly at cutoff), 101, 150, 255 with payout 20
        s_future = pd.DataFrame([
            {"episode_id": "ep_b", "machine_id": "m0", "tick": 100, "payout": 20, "payout_index": 4, "is_win": 1, "split": "train"},
            {"episode_id": "ep_b", "machine_id": "m0", "tick": 101, "payout": 20, "payout_index": 4, "is_win": 1, "split": "train"},
            {"episode_id": "ep_b", "machine_id": "m0", "tick": 150, "payout": 20, "payout_index": 4, "is_win": 1, "split": "train"},
            {"episode_id": "ep_b", "machine_id": "m0", "tick": 255, "payout": 20, "payout_index": 4, "is_win": 1, "split": "train"},
            # Also add future spins on sibling peer machine m1
            {"episode_id": "ep_b", "machine_id": "m1", "tick": 100, "payout": 20, "payout_index": 4, "is_win": 1, "split": "train"},
            {"episode_id": "ep_b", "machine_id": "m1", "tick": 200, "payout": 20, "payout_index": 4, "is_win": 1, "split": "train"},
        ])
        s_combined = pd.concat([s_past, s_future], ignore_index=True)

        df_perturbed = compute_gold_features(
            spark=self.spark,
            df_queries=self.spark.createDataFrame(q_df),
            df_spins=self.spark.createDataFrame(s_combined)
        )
        perturbed_features = df_perturbed.toPandas()[FEATURE_NAMES].values.astype(np.float32)[0]

        # Verify bitwise exact identity: max absolute difference must be exactly 0.0
        max_diff = np.max(np.abs(perturbed_features - base_features))
        self.assertEqual(max_diff, 0.0, f"Temporal leakage detected: max diff = {max_diff}")


class TestMissingHistoryEdgeCases(unittest.TestCase):
    """Tests sparse history and smooth fallback to Dirichlet uniform prior [0.2, 0.2, 0.2, 0.2, 0.2]."""

    def setUp(self):
        self.spark = MockSparkSession()

    def tearDown(self):
        self.spark.stop()

    def test_completely_empty_history(self):
        q_df = pd.DataFrame([{
            "query_id": "q_empty",
            "episode_id": "ep_empty",
            "machine_id": "m0",
            "machine_type": "jackpot",
            "signal": 0,
            "cutoff": 200,
            "split": "train",
            "condition": "short_history"
        }])
        s_df = pd.DataFrame(columns=["episode_id", "machine_id", "tick", "payout", "payout_index", "is_win", "split"])

        df_gold = compute_gold_features(
            spark=self.spark,
            df_queries=self.spark.createDataFrame(q_df),
            df_spins=self.spark.createDataFrame(s_df)
        )
        pdf = df_gold.toPandas()

        # Check zero NaNs, Infs, Nulls
        feature_vals = pdf[FEATURE_NAMES].values.astype(np.float32)[0]
        self.assertFalse(np.isnan(feature_vals).any(), "Found NaNs in empty history features")
        self.assertFalse(np.isinf(feature_vals).any(), "Found Infs in empty history features")

        # 1. Windows: frequencies must be exactly 0.2 uniform prior
        for w in (8, 24, 64):
            for i in range(5):
                val = pdf.loc[0, f"windows/freq{w}_{i}"]
                self.assertAlmostEqual(val, 0.2, places=5)
            self.assertEqual(pdf.loc[0, f"windows/count{w}_0"], 0.0)

        # 2. Decays: frequencies must be exactly 0.2, mass 0.0
        for d in (0.9, 0.97, 0.995):
            for i in range(5):
                val = pdf.loc[0, f"decays/freq{d}_{i}"]
                self.assertAlmostEqual(val, 0.2, places=5)
            self.assertEqual(pdf.loc[0, f"decays/mass{d}_0"], 0.0)

        # 3. Transitions: conditionals must be 0.2, count 0.0
        for k in range(1, 9):
            for i in range(5):
                val = pdf.loc[0, f"transitions/conditional{k}_{i}"]
                self.assertAlmostEqual(val, 0.2, places=5)
            self.assertEqual(pdf.loc[0, f"transitions/count{k}_0"], 0.0)

        # 4. Missingness: coverage_0=0.0, coverage_1=0.0, coverage_2=cutoff=200
        self.assertEqual(pdf.loc[0, "missingness/coverage_0"], 0.0)
        self.assertEqual(pdf.loc[0, "missingness/coverage_1"], 0.0)
        self.assertEqual(pdf.loc[0, "missingness/coverage_2"], 200.0)
        for i in range(8):
            self.assertEqual(pdf.loc[0, f"missingness/lag_known_{i}"], 0.0)

        # 5. Peers: freq and recent must be 0.2, mass 0.0
        for i in range(5):
            self.assertAlmostEqual(pdf.loc[0, f"peers/freq_{i}"], 0.2, places=5)
            self.assertAlmostEqual(pdf.loc[0, f"peers/recent_{i}"], 0.2, places=5)
        self.assertEqual(pdf.loc[0, "peers/mass_0"], 0.0)


class TestRealPublicDataParity(unittest.TestCase):
    """Verifies parity on real competition data from public/train/."""

    def setUp(self):
        self.spark = MockSparkSession()
        self.public_dir = REPO_ROOT / "Jaeger_Main" / "House_Edge" / "public"

    def tearDown(self):
        self.spark.stop()

    def test_public_train_parity(self):
        if not self.public_dir.exists():
            self.skipTest("Public dataset directory not found")

        # Ingest real training data
        run_bronze_ingest(
            spark=self.spark,
            data_dir=str(self.public_dir),
            catalog="test_real",
            schema="house_edge",
            splits=["train"]
        )

        run_silver_pipeline(
            spark=self.spark,
            catalog="test_real",
            schema="house_edge"
        )

        # Verify parity across 30 sampled queries
        audit: ParityAuditResult = verify_feature_parity(
            spark=self.spark,
            catalog="test_real",
            schema="house_edge",
            max_queries=30,
            tolerance=1e-5,
            check_temporal_boundary=True,
            force_mock=True
        )

        self.assertEqual(audit.status, "PASSED")
        self.assertTrue(audit.column_manifest_match)
        self.assertLess(audit.max_abs_difference, 1e-5)
        self.assertEqual(audit.nan_count, 0)
        self.assertEqual(audit.inf_count, 0)
        self.assertEqual(audit.null_count, 0)
        self.assertTrue(audit.temporal_boundary_pass)


class TestNativeExpressionsAndPipeline(unittest.TestCase):
    """Tests native Spark Column expressions and end-to-end pipeline."""

    def setUp(self):
        self.spark = MockSparkSession()

    def tearDown(self):
        self.spark.stop()

    def test_native_expressions(self):
        pdf = pd.DataFrame({
            "machine_type": ["steady", "balanced", "jackpot"],
            "signal": [-1, 0, 1]
        })
        df = self.spark.createDataFrame(pdf)
        exprs = get_native_feature_expressions()

        df_transformed = df.select([
            col("machine_type"),
            col("signal"),
            exprs["type/onehot_0"].alias("type/onehot_0"),
            exprs["type/onehot_1"].alias("type/onehot_1"),
            exprs["type/onehot_2"].alias("type/onehot_2"),
            exprs["current_signal/signal_0"].alias("current_signal/signal_0"),
            exprs["current_signal/signal_1"].alias("current_signal/signal_1"),
            exprs["current_signal/signal_2"].alias("current_signal/signal_2"),
        ])
        res = df_transformed.toPandas()

        self.assertEqual(res.loc[0, "type/onehot_0"], 1.0)
        self.assertEqual(res.loc[0, "current_signal/signal_0"], 1.0)
        self.assertEqual(res.loc[1, "type/onehot_1"], 1.0)
        self.assertEqual(res.loc[1, "current_signal/signal_1"], 1.0)
        self.assertEqual(res.loc[2, "type/onehot_2"], 1.0)
        self.assertEqual(res.loc[2, "current_signal/signal_2"], 1.0)

    def test_end_to_end_gold_pipeline(self):
        q_df = pd.DataFrame([{
            "query_id": "q_pipe_1", "episode_id": "ep_pipe", "machine_id": "m0",
            "machine_type": "steady", "signal": 0, "cutoff": 200, "split": "train", "condition": "stable"
        }])
        s_df = pd.DataFrame([
            {"episode_id": "ep_pipe", "machine_id": "m0", "tick": 10, "payout": 1, "payout_index": 1, "is_win": 1, "split": "train"}
        ])

        self.spark.createDataFrame(q_df).write.format("delta").mode("overwrite").saveAsTable("silver_queries")
        self.spark.createDataFrame(s_df).write.format("delta").mode("overwrite").saveAsTable("silver_spins")

        summary = run_gold_pipeline(spark=self.spark, force_mock=True)
        self.assertEqual(summary["status"], "SUCCESS")
        self.assertEqual(summary["total_queries"], 1)
        self.assertEqual(summary["feature_count"], 471)

        gold_table = self.spark.table("gold_features")
        self.assertEqual(gold_table.count(), 1)
        self.assertEqual(len(gold_table.columns), 477)


if __name__ == "__main__":
    unittest.main()
