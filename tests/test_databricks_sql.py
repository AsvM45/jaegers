"""Unit Tests for Databricks SQL Monitoring Queries, Lakeview Dashboard & Notebooks

Validates:
1. SQL syntax, CTE structure, window functions, and semantic execution of all 5 queries
   in `dbsql_monitoring.sql`.
2. Valid JSON schema, 12-column grid bounds, datasets, and 4-page structure of
   `dbsql_dashboard_spec.json`.
3. Valid Python syntax (ast.parse), `# Databricks notebook source` headers, and cell
   delimiters of all 3 demonstration notebooks.
"""

from __future__ import annotations

import ast
import importlib
import json
import math
import os
import re
import sqlite3
import sys
import unittest
from pathlib import Path
from typing import Any, Dict, List, Tuple

# Resolve base directories
_TEST_DIR = os.path.dirname(os.path.abspath(__file__))
_REPO_ROOT = os.path.abspath(os.path.join(_TEST_DIR, ".."))
_DATABRICKS_DIR = os.path.join(_REPO_ROOT, "Jaeger_Main", "House_Edge", "databricks")
_SRC_DIR = os.path.join(_DATABRICKS_DIR, "src")
_SQL_DIR = os.path.join(_DATABRICKS_DIR, "sql")
_NOTEBOOKS_DIR = os.path.join(_DATABRICKS_DIR, "notebooks")
_REPORTS_DIR = os.path.join(_REPO_ROOT, "Jaeger_Main", "House_Edge", "research", "reports")
if not os.path.isdir(_REPORTS_DIR):
    _REPORTS_DIR = os.path.join(_REPO_ROOT, "research", "reports")


class TestDatabricksSQLMonitoring(unittest.TestCase):
    """Validates the 5 production Databricks SQL monitoring queries."""

    @classmethod
    def setUpClass(cls):
        cls.sql_file_path = os.path.join(_SQL_DIR, "dbsql_monitoring.sql")
        cls.assertTrue(os.path.exists(cls.sql_file_path), f"File not found: {cls.sql_file_path}")
        with open(cls.sql_file_path, "r", encoding="utf-8") as f:
            cls.raw_sql = f.read()

        # Parse queries split by comment headers
        cls.queries = cls._extract_queries(cls.raw_sql)

    @staticmethod
    def _extract_queries(raw_sql: str) -> Dict[str, str]:
        """Extracts individual queries by their QUERY header comments."""
        query_blocks: Dict[str, str] = {}
        pattern = re.compile(r"-- QUERY\s+(\d+):\s+([a-zA-Z0-9_]+)", re.IGNORECASE)
        splits = pattern.split(raw_sql)

        # splits structure: [preamble, q_num1, q_name1, content1, q_num2, q_name2, content2, ...]
        if len(splits) >= 4:
            for i in range(1, len(splits), 3):
                q_num = splits[i].strip()
                q_name = splits[i + 1].strip()
                raw_chunk = splits[i + 2].strip()
                # Clean up comments and extract SQL statement
                lines = [line for line in raw_chunk.split(";")[0].splitlines() if not line.strip().startswith("--")]
                clean_query = "\n".join(lines).strip()
                query_blocks[q_name] = clean_query
        return query_blocks

    def test_query_inventory_and_naming(self):
        """Verifies that all 5 required production queries are present in dbsql_monitoring.sql."""
        expected_queries = {
            "model_leaderboard_provenance",
            "payout_calibration_reliability",
            "regime_and_data_drift",
            "episode_outlier_error_diagnosis",
            "bronze_ingestion_audit_lineage",
        }
        extracted_names = set(self.queries.keys())
        missing = expected_queries - extracted_names
        self.assertEqual(len(missing), 0, f"Missing required queries: {missing}. Found: {extracted_names}")

    def test_cte_structure_and_window_functions(self):
        """Validates that each query uses structured CTEs and required window functions."""
        for q_name, sql in self.queries.items():
            self.assertTrue(sql.upper().startswith("WITH "), f"Query {q_name} must begin with WITH clause")
            self.assertIn("SELECT", sql.upper(), f"Query {q_name} must contain a final SELECT clause")

        # Query 1: Leaderboard must use ROW_NUMBER / DENSE_RANK and partition by evaluation_provenance
        q1 = self.queries["model_leaderboard_provenance"].upper()
        self.assertIn("PARTITION BY EVALUATION_PROVENANCE", q1)
        self.assertIn("ORDER BY MEAN_BRIER", q1)

        # Query 2: Calibration must compute NTILE(10) deciles and bin calibration error
        q2 = self.queries["payout_calibration_reliability"].upper()
        self.assertIn("NTILE(10)", q2)
        self.assertIn("BIN_CALIBRATION_ERROR", q2)

        # Query 3: Drift must compute percentages across splits
        q3 = self.queries["regime_and_data_drift"].upper()
        self.assertIn("MACHINE_TYPE", q3)
        self.assertIn("SPLIT", q3)

        # Query 4: Diagnosis must compute multi-class Brier loss and rank by episode_mean_brier
        q4 = self.queries["episode_outlier_error_diagnosis"].upper()
        self.assertIn("EPISODE_MEAN_BRIER", q4)
        self.assertIn("ORDER BY EPISODE_MEAN_BRIER DESC", q4)

        # Query 5: Audit lineage must check SHA-256 and record counts
        q5 = self.queries["bronze_ingestion_audit_lineage"].upper()
        self.assertIn("SHA256_CHECKSUM", q5)
        self.assertIn("BRONZE_AUDIT_LOG", q5)

    def test_semantic_query_execution_in_sqlite(self):
        """Executes all 5 queries against an in-memory database with mock schema to verify semantics."""
        conn = sqlite3.connect(":memory:")

        # Register Databricks SQL helper functions into SQLite
        conn.create_function("power", 2, lambda x, y: (float(x) ** float(y)) if x is not None and y is not None else 0.0)
        conn.create_function("substring", 3, lambda s, start, length: s[start - 1 : start - 1 + length] if s else "")

        cursor = conn.cursor()

        # Create mock tables mirroring Databricks schemas
        cursor.execute("""
            CREATE TABLE gold_model_evaluations (
                run_id TEXT,
                model_name TEXT,
                model_type TEXT,
                evaluation_provenance TEXT,
                champion_status TEXT,
                mean_brier REAL,
                log_loss REAL,
                ece_calibration REAL,
                brier_stable REAL,
                brier_short_history REAL,
                brier_drift REAL,
                brier_shared_change REAL,
                git_commit TEXT,
                created_at TEXT
            )
        """)
        cursor.execute("""
            INSERT INTO gold_model_evaluations VALUES
            ('run-1', 'champ_mixture', 'mixture_of_experts', 'official_public_validation', 'champion', 0.125, 0.450, 0.012, 0.110, 0.130, 0.140, 0.120, '5f3311e', '2026-11-08T00:00:00Z'),
            ('run-2', 'chall_baseline', 'baseline_lags', 'official_public_validation', 'challenger', 0.145, 0.520, 0.025, 0.120, 0.160, 0.180, 0.150, '5f3311e', '2026-11-08T00:00:00Z'),
            ('run-3', 'cv_mixture', 'mixture_of_experts', 'sampled_outcome_group_cv', 'champion', 0.128, 0.460, 0.014, 0.115, 0.135, 0.142, 0.125, '5f3311e', '2026-11-08T00:00:00Z')
        """)

        cursor.execute("""
            CREATE TABLE gold_predictions (
                query_id INTEGER,
                model_name TEXT,
                p_0 REAL,
                p_1 REAL,
                p_2 REAL,
                p_5 REAL,
                p_20 REAL
            )
        """)
        cursor.execute("""
            CREATE TABLE silver_queries (
                query_id INTEGER,
                episode_id INTEGER,
                machine_id INTEGER,
                machine_type TEXT,
                signal INTEGER,
                cutoff INTEGER,
                split TEXT,
                outcome INTEGER
            )
        """)
        cursor.execute("""
            CREATE TABLE silver_episodes (
                episode_id INTEGER,
                split TEXT,
                total_spins_observed INTEGER,
                total_payout_sum REAL,
                win_count INTEGER,
                win_rate REAL
            )
        """)
        cursor.execute("""
            CREATE TABLE bronze_audit_log (
                dataset_name TEXT,
                split TEXT,
                file_path TEXT,
                sha256_checksum TEXT,
                record_count INTEGER,
                file_size_bytes INTEGER,
                ingested_at TEXT,
                status TEXT
            )
        """)

        # Populate sample rows
        for qid in range(1, 31):
            cursor.execute(
                "INSERT INTO silver_queries VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (qid, (qid % 3) + 1, 0, "steady" if qid % 2 == 0 else "jackpot", 0, 200, "validation", (qid % 5) * (0 if qid % 2 == 0 else 1))
            )
            cursor.execute(
                "INSERT INTO gold_predictions VALUES (?, ?, ?, ?, ?, ?, ?)",
                (qid, "champ_mixture", 0.60, 0.20, 0.10, 0.06, 0.04)
            )

        cursor.execute("INSERT INTO silver_episodes VALUES (1, 'validation', 180, 50, 20, 0.1111)")
        cursor.execute("INSERT INTO silver_episodes VALUES (2, 'validation', 195, 80, 30, 0.1538)")
        cursor.execute("INSERT INTO silver_episodes VALUES (3, 'validation', 120, 25, 10, 0.0833)")

        cursor.execute("""
            INSERT INTO bronze_audit_log VALUES
            ('queries', 'train', '/data/train/queries.csv', 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855', 1000, 45000, '2026-11-08T00:00:00Z', 'SUCCESS'),
            ('history', 'train', '/data/train/history.csv', 'ca978112ca1bbdcafac231b39a23dc4da786eff8147c4e72b9807785afee48bb', 250000, 12000000, '2026-11-08T00:00:00Z', 'SUCCESS')
        """)

        conn.commit()

        # Execute each query and verify it runs without error and returns results
        for q_name, sql in self.queries.items():
            cursor.execute(sql)
            rows = cursor.fetchall()
            self.assertGreater(len(rows), 0, f"Query {q_name} executed but returned 0 rows!")

        conn.close()


class TestDatabricksDashboardSpec(unittest.TestCase):
    """Validates the declarative AI/BI Lakeview dashboard JSON specification."""

    @classmethod
    def setUpClass(cls):
        cls.spec_path = os.path.join(_SQL_DIR, "dbsql_dashboard_spec.json")
        cls.assertTrue(os.path.exists(cls.spec_path), f"File not found: {cls.spec_path}")
        with open(cls.spec_path, "r", encoding="utf-8") as f:
            cls.spec = json.load(f)

    def test_top_level_structure(self):
        """Verifies top-level schema properties."""
        self.assertIn("version", self.spec)
        self.assertIn("displayName", self.spec)
        self.assertIn("datasets", self.spec)
        self.assertIn("pages", self.spec)
        self.assertIsInstance(self.spec["datasets"], list)
        self.assertIsInstance(self.spec["pages"], list)
        self.assertGreaterEqual(len(self.spec["datasets"]), 4)
        self.assertEqual(len(self.spec["pages"]), 4, "Dashboard must contain exactly 4 interactive pages.")

    def test_interactive_pages_inventory(self):
        """Verifies the existence and naming of all 4 required dashboard pages."""
        expected_pages = [
            "Executive Model Leaderboard",
            "House Edge & Calibration Curves",
            "Feature & Regime Drift",
            "Lakehouse Lineage & Health",
        ]
        page_titles = [p.get("displayName") for p in self.spec["pages"]]
        for ep in expected_pages:
            self.assertIn(ep, page_titles, f"Missing expected page: '{ep}' in {page_titles}")

    def test_grid_layout_bounds_and_widgets(self):
        """Verifies 12-column grid placement constraints: 0 <= x < 12, width <= 12, x + width <= 12."""
        widget_types = set()
        for page in self.spec["pages"]:
            layout = page.get("layout", [])
            self.assertGreater(len(layout), 0, f"Page {page.get('displayName')} has no layout widgets")
            for item in layout:
                pos = item.get("position", {})
                x = pos.get("x", 0)
                y = pos.get("y", 0)
                width = pos.get("width", 0)
                height = pos.get("height", 0)

                self.assertGreaterEqual(x, 0, f"Negative x coordinate: {x}")
                self.assertGreaterEqual(y, 0, f"Negative y coordinate: {y}")
                self.assertGreater(width, 0, f"Width must be > 0: {width}")
                self.assertGreater(height, 0, f"Height must be > 0: {height}")
                self.assertLessEqual(x + width, 12, f"Widget exceeds 12-column grid: x={x}, width={width}")

                widget = item.get("widget", {})
                if "spec" in widget:
                    w_type = widget["spec"].get("widgetType")
                    widget_types.add(w_type)
                elif "multilineTextboxSpec" in widget:
                    widget_types.add("textbox")

        # Verify diverse widget coverage (counters, tables, charts, textboxes)
        self.assertIn("counter", widget_types)
        self.assertIn("table", widget_types)
        self.assertIn("bar", widget_types)
        self.assertIn("line", widget_types)
        self.assertIn("textbox", widget_types)


class TestDatabricksDemonstrationNotebooks(unittest.TestCase):
    """Validates the 3 demonstration notebooks in Jaeger_Main/House_Edge/databricks/notebooks/."""

    @classmethod
    def setUpClass(cls):
        cls.notebook_names = [
            "01_delta_lakehouse_pipeline.py",
            "02_pyspark_feature_parity.py",
            "03_mlflow_model_governance.py",
        ]

    def test_notebooks_exist_and_headers(self):
        """Verifies all 3 notebooks exist and conform to Databricks source notebook standards."""
        for nb_name in self.notebook_names:
            nb_path = os.path.join(_NOTEBOOKS_DIR, nb_name)
            self.assertTrue(os.path.exists(nb_path), f"Notebook missing: {nb_path}")

            with open(nb_path, "r", encoding="utf-8") as f:
                content = f.read()

            # Must start with # Databricks notebook source
            self.assertTrue(
                content.startswith("# Databricks notebook source"),
                f"Notebook {nb_name} must begin with '# Databricks notebook source'",
            )
            # Must contain cell separators and markdown documentation
            self.assertIn("# COMMAND ----------", content, f"Notebook {nb_name} missing cell separators")
            self.assertIn("# MAGIC %md", content, f"Notebook {nb_name} missing markdown cells")

    def test_notebooks_valid_python_syntax(self):
        """Verifies that all 3 notebooks can be parsed as valid Python AST without syntax errors."""
        for nb_name in self.notebook_names:
            nb_path = os.path.join(_NOTEBOOKS_DIR, nb_name)
            with open(nb_path, "r", encoding="utf-8") as f:
                content = f.read()

            try:
                ast.parse(content, filename=nb_name)
            except SyntaxError as e:
                self.fail(f"Notebook {nb_name} has invalid Python syntax: {e}")

    def test_notebooks_imports_and_symbols(self):
        """Verifies all import statements in demonstration notebooks resolve to valid symbols in src."""
        if _SRC_DIR not in sys.path:
            sys.path.insert(0, _SRC_DIR)

        for nb_name in self.notebook_names:
            nb_path = os.path.join(_NOTEBOOKS_DIR, nb_name)
            with open(nb_path, "r", encoding="utf-8") as f:
                content = f.read()

            tree = ast.parse(content, filename=nb_name)
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom):
                    mod_name = node.module
                    if not mod_name:
                        continue
                    if mod_name in ("session", "bronze", "silver", "gold", "parity", "mlflow_tracking", "mock_engine"):
                        try:
                            mod = importlib.import_module(mod_name)
                        except Exception as exc:
                            self.fail(f"Notebook {nb_name} failed to import module '{mod_name}': {exc}")
                        for alias in node.names:
                            symbol = alias.name
                            if symbol == "*":
                                continue
                            self.assertTrue(
                                hasattr(mod, symbol),
                                f"Notebook {nb_name} imports non-existent symbol '{symbol}' from '{mod_name}'",
                            )


class TestDocumentationAndSponsorValue(unittest.TestCase):
    """Validates technical documentation and formal sponsor value reports."""

    def test_readme_exists_and_sections(self):
        """Verifies databricks/README.md covers all required architecture sections."""
        readme_path = os.path.join(_DATABRICKS_DIR, "README.md")
        self.assertTrue(os.path.exists(readme_path), f"README missing: {readme_path}")
        with open(readme_path, "r", encoding="utf-8") as f:
            content = f.read()

        required_terms = [
            "Medallion Architecture",
            "Bronze",
            "Silver",
            "Gold",
            "Strict Temporal Isolation",
            "Bitwise Parity",
            "MLflow",
            "Declarative Automation Bundle",
            "Zero Cloud Spend",
            "Zero Runtime Competition Inference Dependency",
        ]
        for term in required_terms:
            self.assertIn(term.lower(), content.lower(), f"README.md missing section or term: '{term}'")

    def test_sponsor_value_report_exists_and_rubric(self):
        """Verifies research/reports/antigravity_databricks_sponsor_value.md covers judging rubric."""
        report_path = os.path.join(_REPORTS_DIR, "antigravity_databricks_sponsor_value.md")
        self.assertTrue(os.path.exists(report_path), f"Report missing: {report_path}")
        with open(report_path, "r", encoding="utf-8") as f:
            content = f.read()

        rubric_criteria = [
            "Originality",
            "Technical Implementation",
            "Meaningful Advantage",
            "Strict Temporal Boundary",
            "SHA-256",
            "Grouped Map Pandas UDF",
            "Bitwise Parity",
            "Zero Cloud Spend",
            "Zero Runtime Dependency",
        ]
        for crit in rubric_criteria:
            self.assertIn(crit.lower(), content.lower(), f"Sponsor report missing rubric topic: '{crit}'")


if __name__ == "__main__":
    unittest.main()
