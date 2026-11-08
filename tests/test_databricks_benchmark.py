"""Unit Tests for Governed Model Benchmark Lane, SQL Queries, Dashboard & Audit Report (#86)

Validates:
1. Read-only ingestion of all frozen House Edge research benchmark artifacts and live
   Serverless evaluations into `gold_benchmark_registry`, `gold_benchmark_paired_comparisons`,
   and `gold_benchmark_episode_diagnostics`.
2. Strict evaluation provenance isolation (`sampled_outcome_group_cv` vs
   `official_public_validation` vs `dev_exposed_public_validation_sampled_outcome`) and
   target-exposure quarantine (`validation_target_exposure`).
3. Execution of all 5 production DBSQL queries in `dbsql_benchmark_lane.sql` against
   actual ingested benchmark tables in SQLite.
4. Schema, 4-page inventory, and 12-column grid bounds of `dbsql_benchmark_dashboard_spec.json`.
5. AST syntax, `# Databricks notebook source` header, and symbol imports of
   `04_governed_model_benchmark_lane.py`.
6. Serverless `exec(compile(...))` startup without `__file__` on `benchmark_lane.py`.
"""

from __future__ import annotations

import ast
import importlib
import json
import os
import re
import sqlite3
import sys
import unittest
from typing import Dict

import pandas as pd

_TEST_DIR = os.path.dirname(os.path.abspath(__file__))
_REPO_ROOT = os.path.abspath(os.path.join(_TEST_DIR, ".."))
_DATABRICKS_DIR = os.path.join(_REPO_ROOT, "Jaeger_Main", "House_Edge", "databricks")
_SRC_DIR = os.path.join(_DATABRICKS_DIR, "src")
_SQL_DIR = os.path.join(_DATABRICKS_DIR, "sql")
_NOTEBOOKS_DIR = os.path.join(_DATABRICKS_DIR, "notebooks")
_REPORTS_DIR = os.path.join(_REPO_ROOT, "Jaeger_Main", "House_Edge", "research", "reports")

if _SRC_DIR not in sys.path:
    sys.path.insert(0, _SRC_DIR)

from session import get_spark_session
from benchmark_lane import (
    VALID_PROVENANCE_TIERS,
    assert_single_provenance_comparison,
    ingest_repository_benchmarks,
    log_benchmark_study_to_mlflow,
    materialize_benchmark_tables,
    rank_models_within_provenance,
)


class TestGovernedBenchmarkLaneIngestion(unittest.TestCase):
    """Tests read-only ingestion, provenance isolation, and Delta/MLflow persistence."""

    @classmethod
    def setUpClass(cls):
        cls.bundle = ingest_repository_benchmarks(include_live_serverless=True)
        cls.df_reg = cls.bundle["registry"]
        cls.df_comp = cls.bundle["comparisons"]
        cls.df_ep = cls.bundle["episodes"]

    @classmethod
    def tearDownClass(cls):
        if os.path.exists("mlflow_mock_runs.json"):
            try:
                os.remove("mlflow_mock_runs.json")
            except OSError:
                pass

    def test_ingested_counts_and_required_columns(self):
        """Verifies all 12 repository benchmark artifacts + live runs are ingested with required columns."""
        self.assertGreaterEqual(len(self.df_reg), 100)
        self.assertGreaterEqual(self.df_reg["study_name"].nunique(), 12)
        self.assertGreaterEqual(len(self.df_comp), 70)
        self.assertGreaterEqual(len(self.df_ep), 1500)

        required_cols = {
            "trial_id",
            "study_name",
            "model_name",
            "model_family",
            "feature_groups",
            "hyperparams_json",
            "seed",
            "fold_scheme",
            "evaluation_provenance",
            "split",
            "primary_metric_name",
            "primary_metric_value",
            "mean_brier",
            "official_points",
            "log_loss",
            "ece_calibration",
            "brier_stable",
            "brier_short_history",
            "brier_drift",
            "brier_shared_change",
            "class_brier_0",
            "class_brier_1",
            "class_brier_2",
            "class_brier_5",
            "class_brier_20",
            "mean_pred_p20",
            "mean_target_p20",
            "corr_p20",
            "validation_target_exposure",
            "historical_signal_policy",
            "wall_seconds",
            "source_artifact",
            "config_sha256",
        }
        missing = required_cols - set(self.df_reg.columns)
        self.assertEqual(len(missing), 0, f"Missing required registry columns: {missing}")

    def test_strict_provenance_isolation_and_anti_conflation(self):
        """Verifies models cannot be ranked or compared across mixed evaluation provenance tiers."""
        with self.assertRaises(ValueError):
            assert_single_provenance_comparison(self.df_reg)

        with self.assertRaises(ValueError):
            rank_models_within_provenance(self.df_reg, evaluation_provenance="invalid_tier")

        for tier in VALID_PROVENANCE_TIERS:
            ranked = rank_models_within_provenance(
                self.df_reg, evaluation_provenance=tier, exclude_target_exposed=True
            )
            self.assertGreater(len(ranked), 0, f"Expected clean trials in tier {tier}")
            verified_tier = assert_single_provenance_comparison(ranked)
            self.assertEqual(verified_tier, tier)
            self.assertTrue((~ranked["validation_target_exposure"].astype(bool)).all())
            # Verify sorted by mean_brier ascending
            briers = ranked["mean_brier"].tolist()
            self.assertEqual(briers, sorted(briers))

    def test_target_exposure_quarantine(self):
        """Verifies in-sample stacker target-exposed trials are flagged and quarantined on CV."""
        cv_all = rank_models_within_provenance(
            self.df_reg,
            evaluation_provenance="sampled_outcome_group_cv",
            exclude_target_exposed=False,
        )
        cv_clean = rank_models_within_provenance(
            self.df_reg,
            evaluation_provenance="sampled_outcome_group_cv",
            exclude_target_exposed=True,
        )
        self.assertGreater(len(cv_all), len(cv_clean))
        exposed_count = int(cv_all["validation_target_exposure"].sum())
        self.assertGreaterEqual(exposed_count, 20)

    def test_rare_20x_and_five_class_brier_populated(self):
        """Verifies rare 20x jackpot calibration and 5-class Brier columns are populated."""
        has_20x = self.df_reg[self.df_reg["corr_p20"].notna()]
        self.assertGreaterEqual(len(has_20x), 5)
        self.assertTrue((has_20x["mean_pred_p20"] > 0.0).all())
        self.assertTrue((has_20x["mean_target_p20"] > 0.0).all())

        has_cb = self.df_reg[self.df_reg["class_brier_20"].notna()]
        self.assertGreaterEqual(len(has_cb), 15)

    def test_materialize_tables_and_mlflow_sync(self):
        """Verifies Delta table materialization and MLflow logging in offline mock mode."""
        spark = get_spark_session(app_name="test_benchmark_lane", force_mock=True)
        counts = materialize_benchmark_tables(
            spark=spark, catalog="workspace", schema="house_edge"
        )
        self.assertEqual(counts["gold_benchmark_registry"], len(self.df_reg))
        self.assertEqual(counts["gold_benchmark_paired_comparisons"], len(self.df_comp))
        self.assertEqual(counts["gold_benchmark_episode_diagnostics"], len(self.df_ep))

        run_ids = log_benchmark_study_to_mlflow(
            self.df_reg,
            study_name="databricks_serverless_job_888066060424343",
            force_mock=True,
        )
        self.assertEqual(len(run_ids), 3)

    def test_exec_without_dunder_file(self):
        """Verifies benchmark_lane.py executes cleanly when `__file__` is absent."""
        script_path = os.path.join(_SRC_DIR, "benchmark_lane.py")
        with open(script_path, "r", encoding="utf-8") as f:
            source = f.read()
        exec_globals = {
            "__builtins__": __builtins__,
            "__name__": "__serverless_exec_benchmark_lane__",
            "filename": script_path,
        }
        self.assertNotIn("__file__", exec_globals)
        code = compile(source, script_path, "exec")
        exec(code, exec_globals)
        self.assertEqual(os.path.abspath(exec_globals["_SRC_DIR"]), os.path.abspath(_SRC_DIR))


class TestBenchmarkLaneSQLAndDashboard(unittest.TestCase):
    """Validates `dbsql_benchmark_lane.sql`, `dbsql_benchmark_dashboard_spec.json`, and notebook 04."""

    @classmethod
    def setUpClass(cls):
        cls.sql_path = os.path.join(_SQL_DIR, "dbsql_benchmark_lane.sql")
        with open(cls.sql_path, "r", encoding="utf-8") as f:
            cls.raw_sql = f.read()
        cls.queries = cls._extract_queries(cls.raw_sql)

    @staticmethod
    def _extract_queries(raw_sql: str) -> Dict[str, str]:
        query_blocks: Dict[str, str] = {}
        pattern = re.compile(r"-- QUERY\s+(\d+):\s+([a-zA-Z0-9_]+)", re.IGNORECASE)
        splits = pattern.split(raw_sql)
        if len(splits) >= 4:
            for i in range(1, len(splits), 3):
                q_name = splits[i + 1].strip()
                raw_chunk = splits[i + 2].strip()
                lines = [
                    line
                    for line in raw_chunk.split(";")[0].splitlines()
                    if not line.strip().startswith("--")
                ]
                query_blocks[q_name] = "\n".join(lines).strip()
        return query_blocks

    def test_sql_queries_execute_against_real_ingested_data(self):
        """Executes all 5 benchmark SQL queries in SQLite populated with real ingested benchmark rows."""
        expected_queries = {
            "provenance_partitioned_model_leaderboard",
            "paired_hypothesis_ci95_promotion_gate",
            "rare_20x_payout_and_class_brier_audit",
            "condition_regime_degradation_matrix",
            "leakage_exposure_and_runtime_pareto",
        }
        self.assertEqual(set(self.queries.keys()), expected_queries)

        bundle = ingest_repository_benchmarks(include_live_serverless=True)
        conn = sqlite3.connect(":memory:")
        conn.create_function(
            "substring",
            3,
            lambda s, start, length: s[start - 1 : start - 1 + length] if s else "",
        )
        bundle["registry"].to_sql("gold_benchmark_registry", conn, index=False)
        bundle["comparisons"].to_sql("gold_benchmark_paired_comparisons", conn, index=False)
        bundle["episodes"].to_sql("gold_benchmark_episode_diagnostics", conn, index=False)

        cursor = conn.cursor()
        for q_name, sql in self.queries.items():
            cursor.execute(sql)
            rows = cursor.fetchall()
            self.assertGreater(len(rows), 0, f"Query {q_name} returned 0 rows!")
        conn.close()

    def test_benchmark_dashboard_spec_valid(self):
        """Validates 4-page structure and 12-column grid bounds of `dbsql_benchmark_dashboard_spec.json`."""
        spec_path = os.path.join(_SQL_DIR, "dbsql_benchmark_dashboard_spec.json")
        self.assertTrue(os.path.isfile(spec_path))
        with open(spec_path, "r", encoding="utf-8") as f:
            spec = json.load(f)

        self.assertEqual(len(spec.get("datasets", [])), 4)
        self.assertEqual(len(spec.get("pages", [])), 4)
        for page in spec["pages"]:
            for item in page.get("layout", []):
                pos = item["position"]
                self.assertGreaterEqual(pos["x"], 0)
                self.assertGreater(pos["width"], 0)
                self.assertLessEqual(pos["x"] + pos["width"], 12)

    def test_notebook_04_and_report_valid(self):
        """Validates `04_governed_model_benchmark_lane.py` AST/imports and `#86` audit report."""
        nb_path = os.path.join(_NOTEBOOKS_DIR, "04_governed_model_benchmark_lane.py")
        self.assertTrue(os.path.isfile(nb_path))
        with open(nb_path, "r", encoding="utf-8") as f:
            nb_content = f.read()
        self.assertTrue(nb_content.startswith("# Databricks notebook source"))
        self.assertIn("# COMMAND ----------", nb_content)
        self.assertIn("# MAGIC %md", nb_content)
        tree = ast.parse(nb_content, filename="04_governed_model_benchmark_lane.py")
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module in ("session", "benchmark_lane"):
                mod = importlib.import_module(node.module)
                for alias in node.names:
                    self.assertTrue(hasattr(mod, alias.name))

        report_path = os.path.join(_REPORTS_DIR, "antigravity_he86_model_benchmark_audit.md")
        self.assertTrue(os.path.isfile(report_path))
        with open(report_path, "r", encoding="utf-8") as f:
            rep = f.read()
        for required_term in (
            "sampled_outcome_group_cv",
            "official_public_validation",
            "dev_exposed_public_validation_sampled_outcome",
            "888066060424343",
            "validation_target_exposure",
            "corr_p20",
        ):
            self.assertIn(required_term, rep)


if __name__ == "__main__":
    unittest.main()
