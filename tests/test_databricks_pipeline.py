"""Unit Test Suite for Databricks Lakehouse Pipeline (Milestone 1)

Verifies:
1. MockSparkSession & MockDataFrame PySpark API compatibility (zero-dependency offline engine).
2. MockMLflow experiment tracking, metrics, parameters, tags, and run searching.
3. Unified session resolver fallback logic.
4. Bronze Layer ingestion, cryptographic SHA-256 checksum audit logging, and metadata tagging.
5. Silver Layer domain quality assertions, payout indexing, deduplication, and episode summarization.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

# Add repository paths for clean imports
REPO_ROOT = Path(__file__).resolve().parents[1]
DATABRICKS_DIR = REPO_ROOT / "Jaeger_Main" / "House_Edge" / "databricks"
import sys
if str(DATABRICKS_DIR) not in sys.path:
    sys.path.insert(0, str(DATABRICKS_DIR))

from src.bronze import compute_file_sha256, run_bronze_ingest
from src.mock_engine import (
    MockColumn,
    MockDataFrame,
    MockMLflow,
    MockSparkSession,
    avg,
    col,
    count,
    lit,
    sum,
    when,
)
from src.session import assert_real_mlflow, assert_real_spark, get_mlflow, get_spark_session
from src.silver import run_silver_pipeline, refresh_views


class TestServerlessStartupAndLiveGuardrails(unittest.TestCase):
    """Regression tests for Databricks Serverless Python-script execution without `__file__`
    and strict live-runtime guardrails.
    """

    def test_exec_without_dunder_file_all_task_scripts(self):
        """Executes all 5 task entrypoints via exec(compile(...)) with `__file__` absent."""
        src_dir = DATABRICKS_DIR / "src"
        task_scripts = [
            "bronze.py",
            "silver.py",
            "gold.py",
            "parity.py",
            "mlflow_tracking.py",
        ]
        for script_name in task_scripts:
            script_path = src_dir / script_name
            source = script_path.read_text(encoding="utf-8")

            # Case 1: Databricks Serverless wrapper provides `filename` in globals, no `__file__`
            ns_with_filename = {"__name__": "__serverless_exec__", "filename": str(script_path)}
            self.assertNotIn("__file__", ns_with_filename)
            exec(compile(source, str(script_path), "exec"), ns_with_filename)
            self.assertEqual(
                Path(ns_with_filename["_SRC_DIR"]).resolve(),
                src_dir.resolve(),
                f"{script_name} failed to resolve _SRC_DIR with filename fallback",
            )

            # Case 2: Neither `__file__` nor `filename` in globals (pure code-object inspection)
            ns_minimal = {"__name__": "__serverless_exec__"}
            self.assertNotIn("__file__", ns_minimal)
            exec(compile(source, str(script_path), "exec"), ns_minimal)
            self.assertEqual(
                Path(ns_minimal["_SRC_DIR"]).resolve(),
                src_dir.resolve(),
                f"{script_name} failed to resolve _SRC_DIR via frame co_filename inspection",
            )

    def test_session_rejects_mock_when_require_live(self):
        """Verifies that live verification explicitly rejects MockSparkSession and MockMLflow."""
        with self.assertRaises(RuntimeError):
            get_spark_session(force_mock=True, require_live=True)
        with self.assertRaises(RuntimeError):
            get_mlflow(force_mock=True, require_live=True)
        with self.assertRaises(RuntimeError):
            assert_real_spark(MockSparkSession())
        with self.assertRaises(RuntimeError):
            assert_real_mlflow(MockMLflow())

    def test_bronze_fails_on_missing_split_directory(self):
        """Verifies that run_bronze_ingest raises FileNotFoundError when a required split is absent."""
        tmp = tempfile.mkdtemp()
        spark = MockSparkSession()
        try:
            with self.assertRaises(FileNotFoundError):
                run_bronze_ingest(
                    spark=spark,
                    data_dir=tmp,
                    catalog="test_cat",
                    schema="test_sch",
                    splits=["train", "validation", "test"],
                )
        finally:
            spark.stop()
            shutil.rmtree(tmp, ignore_errors=True)


class TestMockEngine(unittest.TestCase):
    """Tests the offline MockSparkSession, MockDataFrame, and MockMLflow engines."""

    def setUp(self):
        self.spark = MockSparkSession()

    def tearDown(self):
        self.spark.stop()

    def test_create_dataframe_and_basic_ops(self):
        pdf = pd.DataFrame({
            "id": [1, 2, 3, 4],
            "machine": ["m1", "m2", "m1", "m2"],
            "payout": [0, 1, 5, 20]
        })
        df = self.spark.createDataFrame(pdf)
        self.assertEqual(df.count(), 4)
        self.assertEqual(df.columns, ["id", "machine", "payout"])
        
        # Test select and filter
        filtered = df.filter(col("payout") > 0)
        self.assertEqual(filtered.count(), 3)

        # Test withColumn
        with_col = df.withColumn("is_win", when(col("payout") > 0, 1).otherwise(0))
        self.assertIn("is_win", with_col.columns)
        win_sum = with_col.toPandas()["is_win"].sum()
        self.assertEqual(win_sum, 3)

    def test_when_otherwise_chained(self):
        pdf = pd.DataFrame({"payout": [0, 1, 2, 5, 20, 99]})
        df = self.spark.createDataFrame(pdf)
        df_indexed = df.withColumn(
            "payout_index",
            when(col("payout") == 0, 0)
            .when(col("payout") == 1, 1)
            .when(col("payout") == 2, 2)
            .when(col("payout") == 5, 3)
            .when(col("payout") == 20, 4)
            .otherwise(-1)
        )
        res = df_indexed.toPandas()["payout_index"].tolist()
        self.assertEqual(res, [0, 1, 2, 3, 4, -1])

    def test_groupby_and_agg(self):
        pdf = pd.DataFrame({
            "episode_id": ["e1", "e1", "e2", "e2"],
            "payout": [1, 5, 0, 20]
        })
        df = self.spark.createDataFrame(pdf)
        agg_df = df.groupBy("episode_id").agg(
            sum(col("payout")).alias("total_payout"),
            count(col("payout")).alias("spin_count")
        )
        agg_pdf = agg_df.toPandas().sort_values("episode_id").reset_index(drop=True)
        self.assertEqual(len(agg_pdf), 2)
        self.assertEqual(agg_pdf.loc[0, "total_payout"], 6)
        self.assertEqual(agg_pdf.loc[0, "spin_count"], 2)
        self.assertEqual(agg_pdf.loc[1, "total_payout"], 20)

    def test_joins_and_deduplication(self):
        left_pdf = pd.DataFrame({"id": [1, 2, 3], "val_a": ["a", "b", "c"]})
        right_pdf = pd.DataFrame({"id": [2, 3, 4], "val_b": ["x", "y", "z"]})
        df_left = self.spark.createDataFrame(left_pdf)
        df_right = self.spark.createDataFrame(right_pdf)

        joined = df_left.join(df_right, on="id", how="inner")
        self.assertEqual(joined.count(), 2)

        # Deduplication
        dup_pdf = pd.DataFrame({"k": [1, 1, 2], "v": ["a", "a", "b"]})
        dup_df = self.spark.createDataFrame(dup_pdf).dropDuplicates(subset=["k"])
        self.assertEqual(dup_df.count(), 2)

    def test_table_persistence_and_sql(self):
        pdf = pd.DataFrame({"cat": ["A", "B", "A"], "score": [10, 20, 30]})
        df = self.spark.createDataFrame(pdf)
        df.write.format("delta").mode("overwrite").saveAsTable("test_catalog.test_schema.scores")

        # Read back via table()
        read_df = self.spark.table("scores")
        self.assertEqual(read_df.count(), 3)

        # Query via sql()
        sql_df = self.spark.sql("SELECT cat, SUM(score) as total FROM scores GROUP BY cat ORDER BY cat")
        res = sql_df.toPandas()
        self.assertEqual(len(res), 2)
        self.assertEqual(res.loc[0, "total"], 40)
        self.assertEqual(res.loc[1, "total"], 20)

    def test_mock_mlflow_lifecycle(self):
        mlflow = MockMLflow(storage_file="test_mock_runs.json")
        with mlflow.start_run(run_name="unit_test_run") as run:
            run_id = run.info.run_id
            mlflow.log_param("model_type", "lightgbm")
            mlflow.log_params({"learning_rate": 0.05, "max_depth": 6})
            mlflow.log_metric("brier_score", 0.1542)
            mlflow.log_metrics({"ece": 0.021, "log_loss": 0.892})
            mlflow.set_tag("git_commit", "5f3311e4")
            mlflow.log_dict({"metric": "test"}, "artifacts/info.json")

        self.assertIsNone(mlflow.active_run())
        runs_df = mlflow.search_runs()
        self.assertEqual(len(runs_df), 1)
        self.assertEqual(runs_df.loc[0, "run_id"], run_id)
        self.assertEqual(runs_df.loc[0, "params.model_type"], "lightgbm")
        self.assertAlmostEqual(float(runs_df.loc[0, "metrics.brier_score"]), 0.1542)

        # Cleanup test ledger
        if os.path.exists("test_mock_runs.json"):
            os.remove("test_mock_runs.json")


class TestSessionResolver(unittest.TestCase):
    """Tests runtime session and MLflow resolution."""

    def test_get_spark_session_fallback(self):
        spark = get_spark_session(force_mock=True)
        self.assertIsNotNone(spark)
        self.assertTrue(hasattr(spark, "createDataFrame"))
        self.assertTrue(hasattr(spark, "table"))

    def test_get_mlflow_fallback(self):
        ml = get_mlflow(force_mock=True)
        self.assertIsNotNone(ml)
        self.assertTrue(hasattr(ml, "start_run"))
        self.assertTrue(hasattr(ml, "log_metrics"))


class TestMedallionBronzeAndSilver(unittest.TestCase):
    """Tests Bronze ingestion, SHA-256 verification, and Silver quality constraints."""

    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.spark = MockSparkSession()

        # Build synthetic test directory structure mirroring public/
        for split in ("train", "validation"):
            s_dir = os.path.join(self.test_dir, split)
            os.makedirs(s_dir, exist_ok=True)

            # queries.csv
            q_df = pd.DataFrame({
                "query_id": [f"q_{split}_1", f"q_{split}_2"],
                "episode_id": [f"ep_{split}_1", f"ep_{split}_1"],
                "machine_id": ["m000", "m001"],
                "machine_type": ["steady", "balanced"],
                "signal": [1, -1],
                "cutoff": [200, 210]
            })
            q_df.to_csv(os.path.join(s_dir, "queries.csv"), index=False)

            # history.csv
            h_df = pd.DataFrame({
                "episode_id": [f"ep_{split}_1", f"ep_{split}_1", f"ep_{split}_1"],
                "machine_id": ["m000", "m000", "m001"],
                "tick": [0, 1, 0],
                "payout": [0, 2, 5]
            })
            h_df.to_csv(os.path.join(s_dir, "history.csv"), index=False)

            # conditions.csv
            c_df = pd.DataFrame({
                "query_id": [f"q_{split}_1", f"q_{split}_2"],
                "condition": ["stable", "drift"]
            })
            c_df.to_csv(os.path.join(s_dir, "conditions.csv"), index=False)

            # labels.csv
            l_df = pd.DataFrame({
                "query_id": [f"q_{split}_1", f"q_{split}_2"],
                "outcome": [2, 5]
            })
            l_df.to_csv(os.path.join(s_dir, "labels.csv"), index=False)

    def tearDown(self):
        self.spark.stop()
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_bronze_ingestion_and_sha256(self):
        summary = run_bronze_ingest(
            spark=self.spark,
            data_dir=self.test_dir,
            catalog="test_cat",
            schema="test_sch",
            splits=["train", "validation"]
        )

        self.assertIn("bronze_queries", summary["tables"])
        self.assertEqual(summary["tables"]["bronze_queries"], 4)
        self.assertEqual(summary["tables"]["bronze_history"], 6)
        self.assertIn("bronze_audit_log", summary["tables"])

        # Verify SHA-256 in audit log matches real cryptographic hash
        audit_table = self.spark.table("bronze_audit_log").toPandas()
        for _, row in audit_table.iterrows():
            fpath = row["file_path"]
            with open(fpath, "rb") as f:
                expected_sha = hashlib.sha256(f.read()).hexdigest()
            self.assertEqual(row["sha256_checksum"], expected_sha)
            self.assertEqual(row["status"], "SUCCESS")

    def test_silver_validation_and_deduplication(self):
        # First ingest clean data
        run_bronze_ingest(
            spark=self.spark,
            data_dir=self.test_dir,
            catalog="test_cat",
            schema="test_sch",
            splits=["train", "validation"]
        )

        # Inject invalid payout (99) and duplicate spin into bronze_history
        raw_h = self.spark.table("bronze_history").toPandas()
        corrupted_row = {
            "episode_id": "ep_train_1",
            "machine_id": "m000",
            "tick": 999,
            "payout": 99,  # Invalid payout
            "split": "train",
            "_source_file": "corrupted",
            "_source_sha256": "fake",
            "_ingested_at": "2026-01-01"
        }
        duplicate_row = raw_h.iloc[0].to_dict()  # Exact duplicate of tick 0
        corrupted_h = pd.concat([raw_h, pd.DataFrame([corrupted_row, duplicate_row])], ignore_index=True)
        self.spark.createDataFrame(corrupted_h).write.format("delta").mode("overwrite").saveAsTable("test_cat.test_sch.bronze_history")

        # Run Silver pipeline
        silver_summary = run_silver_pipeline(
            spark=self.spark,
            catalog="test_cat",
            schema="test_sch"
        )

        # Verify invalid payout (99) was rejected
        self.assertEqual(silver_summary["rejected_spins"], 1)
        self.assertEqual(silver_summary["duplicates_dropped"], 1)

        # Verify silver_spins domain constraints
        silver_spins = self.spark.table("silver_spins").toPandas()
        self.assertTrue(set(silver_spins["payout"].unique()).issubset({0, 1, 2, 5, 20}))
        self.assertTrue(set(silver_spins["payout_index"].unique()).issubset({0, 1, 2, 3, 4}))
        self.assertTrue(set(silver_spins["is_win"].unique()).issubset({0, 1}))

        # Verify silver_episodes dimension summary
        silver_episodes = self.spark.table("silver_episodes").toPandas()
        self.assertGreater(len(silver_episodes), 0)
        self.assertIn("machine_count", silver_episodes.columns)
        self.assertIn("total_spins_observed", silver_episodes.columns)

        # Verify refresh_views
        refresh_views(self.spark, catalog="test_cat", schema="test_sch")

    def test_real_public_data_medallion_pipeline(self):
        real_public_dir = REPO_ROOT / "Jaeger_Main" / "House_Edge" / "public"
        if not real_public_dir.exists():
            self.skipTest("Real public data directory not found")

        # Ingest real train split
        summary = run_bronze_ingest(
            spark=self.spark,
            data_dir=str(real_public_dir),
            catalog="jaegers_dev",
            schema="house_edge",
            splits=["train"]
        )
        self.assertIn("bronze_queries", summary["tables"])
        self.assertEqual(summary["tables"]["bronze_queries"], 768)
        self.assertEqual(summary["tables"]["bronze_history"], 139944)

        # Run Silver pipeline on real ingested train split
        silver_res = run_silver_pipeline(
            spark=self.spark,
            catalog="jaegers_dev",
            schema="house_edge"
        )
        self.assertEqual(silver_res["silver_queries"], 768)
        self.assertEqual(silver_res["silver_spins"], 139944)
        self.assertEqual(silver_res["rejected_queries"], 0)
        self.assertEqual(silver_res["rejected_spins"], 0)
        self.assertEqual(silver_res["duplicates_dropped"], 0)


if __name__ == "__main__":
    unittest.main()

