"""Automated PySpark vs. NumPy Feature Parity Verifier

Compares PySpark Gold features against offline NumPy/Pandas `FeatureComputer`
from `research/features.py`:
1. Checks that the column manifest and column order match 100% across all 471 features.
2. Checks that absolute numerical differences satisfy: max |X_spark - X_numpy| < 10^-5.
3. Asserts zero NaNs, Infs, or Nulls emitted anywhere in the Gold feature output.
4. Verifies strict temporal boundary invariance: modifying, perturbing, or adding
   spins at tick >= cutoff leaves all Gold features completely unchanged.
"""

from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
import datetime
import logging
import os
from pathlib import Path
import sys
import time

import types
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union

import numpy as np
import pandas as pd

# Safe mock for joblib if not installed in runtime environment
if "joblib" not in sys.modules:
    try:
        import joblib  # noqa: F401
    except ImportError:
        sys.modules["joblib"] = types.ModuleType("joblib")

# Support both relative package imports and direct script execution
_SRC_DIR = os.path.dirname(os.path.abspath(__file__))
if _SRC_DIR not in sys.path:
    sys.path.insert(0, _SRC_DIR)

try:
    from .bronze import run_bronze_ingest
    from .gold import (
        ALL_FEATURE_GROUPS,
        FEATURE_NAMES,
        HISTORICAL_FEATURE_NAMES,
        compute_gold_features,
        get_feature_names,
        get_qualified_table_name,
        run_gold_pipeline,
    )
    from .mock_engine import MockSparkSession
    from .session import get_spark_session
    from .silver import run_silver_pipeline
except (ImportError, ValueError):
    from bronze import run_bronze_ingest
    from gold import (
        ALL_FEATURE_GROUPS,
        FEATURE_NAMES,
        HISTORICAL_FEATURE_NAMES,
        compute_gold_features,
        get_feature_names,
        get_qualified_table_name,
        run_gold_pipeline,
    )
    from mock_engine import MockSparkSession
    from session import get_spark_session
    from silver import run_silver_pipeline


logger = logging.getLogger("jaegers.databricks.parity")


def _get_offline_feature_computer():
    """Dynamically imports FeatureComputer and REGISTRY from research module."""
    house_edge_root = Path(__file__).resolve().parents[2]
    repo_root = house_edge_root.parents[1]
    for p in (str(house_edge_root), str(repo_root)):
        if p not in sys.path:
            sys.path.insert(0, p)
    try:
        from Jaeger_Main.House_Edge.research.feature_api import FeatureComputer, REGISTRY
        return FeatureComputer, REGISTRY
    except ImportError:
        try:
            from research.feature_api import FeatureComputer, REGISTRY
            return FeatureComputer, REGISTRY
        except ImportError:
            from research.features import FeatureComputer, REGISTRY
            return FeatureComputer, REGISTRY



@dataclass
class ParityAuditResult:
    """Structured audit report for PySpark vs. NumPy feature parity verification."""
    status: str
    total_queries_checked: int
    total_features_checked: int
    column_manifest_match: bool
    max_abs_difference: float
    mean_abs_difference: float
    nan_count: int
    inf_count: int
    null_count: int
    temporal_boundary_pass: bool
    elapsed_seconds: float
    timestamp: str
    details: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @property
    def max_absolute_difference(self) -> float:
        return self.max_abs_difference

    @property
    def total_features(self) -> int:
        return self.total_features_checked

    @property
    def temporal_boundary_passed(self) -> bool:
        return self.temporal_boundary_pass

    def print_summary(self) -> None:
        print("\n" + "=" * 70)
        print("  JAEGERS PYSPARK FEATURE PARITY AUDIT REPORT")
        print("=" * 70)
        print(f"  Overall Status:             {self.status}")
        print(f"  Total Queries Verified:     {self.total_queries_checked}")
        print(f"  Total Feature Columns:      {self.total_features_checked} (468 historical + 3 query)")
        print(f"  Column Manifest Match:      {'YES (100% exact order)' if self.column_manifest_match else 'NO'}")
        print(f"  Max Absolute Difference:    {self.max_abs_difference:.2e} (threshold: 1.00e-05)")
        print(f"  Mean Absolute Difference:   {self.mean_abs_difference:.2e}")
        print(f"  NaN / Inf / Null Count:     NaN={self.nan_count}, Inf={self.inf_count}, Null={self.null_count}")
        print(f"  Strict Cutoff Invariant:    {'PASSED (Bitwise exact 0.0 diff)' if self.temporal_boundary_pass else 'FAILED'}")
        print(f"  Execution Time:             {self.elapsed_seconds:.3f} s")
        print("=" * 70 + "\n")


def verify_feature_parity(
    spark: Optional[Any] = None,
    catalog: Optional[str] = None,
    schema: Optional[str] = None,
    queries_table: Optional[str] = None,
    spins_table: Optional[str] = None,
    gold_table: Optional[str] = None,
    query_ids: Optional[Sequence[str]] = None,
    max_queries: Optional[int] = None,
    tolerance: float = 1e-5,
    check_temporal_boundary: bool = True,
    force_mock: bool = False,
    data_dir: Optional[str] = None,
) -> ParityAuditResult:
    """Automated verification comparing PySpark Gold features against offline NumPy FeatureComputer.

    Performs 4 rigorous checks:
    1. Manifest check: Feature column names and ordering match 100%.
    2. Numerical parity: max |X_spark - X_numpy| < tolerance (10^-5).
    3. Health check: Zero NaNs, Infs, or Nulls emitted.
    4. Temporal boundary invariant: perturbing history at t >= cutoff produces 0.0 change.
    """
    start_time = time.time()
    if spark is None:
        spark = get_spark_session(catalog=catalog, schema=schema, force_mock=force_mock)

    q_name = queries_table or get_qualified_table_name("silver_queries", catalog, schema)
    s_name = spins_table or get_qualified_table_name("silver_spins", catalog, schema)
    g_name = gold_table or get_qualified_table_name("gold_features", catalog, schema)

    # 0. Ensure Silver tables exist in the session; auto-ingest from public data if missing
    need_ingest = False
    try:
        spark.table(q_name)
        spark.table(s_name)
    except Exception:
        need_ingest = True

    if need_ingest:
        logger.info("Silver tables %s or %s not found; running Bronze & Silver auto-ingestion", q_name, s_name)
        resolved_data_dir = data_dir
        if not (resolved_data_dir and os.path.exists(os.path.join(resolved_data_dir, "train"))):
            candidates = [
                os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "public")),
                os.path.join(os.getcwd(), "Jaeger_Main", "House_Edge", "public"),
                os.path.join(os.getcwd(), "public"),
                "Jaeger_Main/House_Edge/public",
            ]
            for cand in candidates:
                if os.path.exists(os.path.join(cand, "train")):
                    resolved_data_dir = cand
                    break
        if not resolved_data_dir or not os.path.exists(resolved_data_dir):
            resolved_data_dir = "Jaeger_Main/House_Edge/public"

        run_bronze_ingest(
            spark=spark,
            data_dir=resolved_data_dir,
            catalog=catalog,
            schema=schema,
            splits=("train",),
            force_mock=force_mock,
        )
        run_silver_pipeline(
            spark=spark,
            catalog=catalog,
            schema=schema,
            force_mock=force_mock,
        )

    # 1. Ensure Gold table exists, or compute it
    try:
        df_gold = spark.table(g_name)
    except Exception:
        logger.info("Gold table %s not found; running gold pipeline to generate it", g_name)
        run_gold_pipeline(
            spark=spark,
            catalog=catalog,
            schema=schema,
            queries_table=q_name,
            spins_table=s_name,
            target_table=g_name,
            force_mock=force_mock
        )
        df_gold = spark.table(g_name)

    pdf_gold = df_gold.toPandas()
    pdf_queries = spark.table(q_name).toPandas()
    pdf_spins = spark.table(s_name).toPandas()

    # Filter query subset if requested
    if query_ids:
        pdf_queries = pdf_queries[pdf_queries["query_id"].isin(query_ids)]
        pdf_gold = pdf_gold[pdf_gold["query_id"].isin(query_ids)]
    elif max_queries and len(pdf_queries) > max_queries:
        # Sample across distinct machine types if possible
        steady_q = pdf_queries[pdf_queries["machine_type"] == "steady"].head(max(1, max_queries // 3))
        balanced_q = pdf_queries[pdf_queries["machine_type"] == "balanced"].head(max(1, max_queries // 3))
        jackpot_q = pdf_queries[pdf_queries["machine_type"] == "jackpot"].head(max(1, max_queries // 3))
        sampled = pd.concat([steady_q, balanced_q, jackpot_q]).drop_duplicates(subset=["query_id"]).head(max_queries)
        sample_ids = sampled["query_id"].tolist()
        pdf_queries = pdf_queries[pdf_queries["query_id"].isin(sample_ids)]
        pdf_gold = pdf_gold[pdf_gold["query_id"].isin(sample_ids)]

    n_queries = len(pdf_queries)
    if n_queries == 0:
        raise ValueError("No queries available for parity verification")

    # -----------------------------------------------------------------------
    # Check 1: Column Manifest & Sequence Check
    # -----------------------------------------------------------------------
    expected_manifest = get_feature_names()
    actual_columns = list(pdf_gold.columns)
    manifest_match = all(name in actual_columns for name in expected_manifest)
    # Check exact sequence of feature columns
    feature_start_idx = -1
    for idx, col_name in enumerate(actual_columns):
        if col_name == expected_manifest[0]:
            feature_start_idx = idx
            break

    sequence_match = False
    if feature_start_idx >= 0:
        actual_feature_sequence = actual_columns[feature_start_idx: feature_start_idx + len(expected_manifest)]
        sequence_match = (actual_feature_sequence == expected_manifest)

    # -----------------------------------------------------------------------
    # Check 2: Offline Reference Generation & Numerical Parity Check
    # -----------------------------------------------------------------------
    FeatureComputer, REGISTRY = _get_offline_feature_computer()
    all_groups = list(REGISTRY.keys())

    # Build reference history dictionary from Silver spins
    history_dict: Dict[Tuple[str, str], Dict[int, int]] = {}
    for _, row in pdf_spins.iterrows():
        ep_id = str(row["episode_id"])
        m_id = str(row["machine_id"])
        t = int(row["tick"])
        p = int(row["payout"])
        history_dict.setdefault((ep_id, m_id), {})[t] = p

    # Ensure all episode/machine combinations in queries exist in history
    for _, q in pdf_queries.iterrows():
        ep_id = str(q["episode_id"])
        m_id = str(q["machine_id"])
        history_dict.setdefault((ep_id, m_id), {})

    fc = FeatureComputer(history_dict)

    spark_features_matrix = []
    numpy_features_matrix = []

    # Map gold rows by query_id for fast lookup
    gold_by_id = pdf_gold.set_index("query_id")

    for _, q_row in pdf_queries.iterrows():
        qid = q_row["query_id"]
        q_dict = q_row.to_dict()

        # Offline numpy reference
        ref_vec, ref_names = fc.row(q_dict, groups=all_groups)
        numpy_features_matrix.append(ref_vec)

        # PySpark gold output
        gold_row = gold_by_id.loc[qid]
        spark_vec = gold_row[expected_manifest].values.astype(np.float32)
        spark_features_matrix.append(spark_vec)

    X_spark = np.vstack(spark_features_matrix).astype(np.float32)
    X_numpy = np.vstack(numpy_features_matrix).astype(np.float32)

    abs_diffs = np.abs(X_spark - X_numpy)
    max_abs_diff = float(np.max(abs_diffs))
    mean_abs_diff = float(np.mean(abs_diffs))

    # -----------------------------------------------------------------------
    # Check 3: Zero NaN, Inf, and Null Check
    # -----------------------------------------------------------------------
    nan_count = int(np.isnan(X_spark).sum())
    inf_count = int(np.isinf(X_spark).sum())
    null_count = int(pdf_gold[expected_manifest].isna().sum().sum())

    # -----------------------------------------------------------------------
    # Check 4: Strict Temporal Boundary Invariant Check
    # -----------------------------------------------------------------------
    temporal_boundary_pass = True
    if check_temporal_boundary:
        # Pick test queries across different machine types
        test_queries = pdf_queries.head(min(5, len(pdf_queries))).copy().reset_index(drop=True)

        for i, q in test_queries.iterrows():
            qid = str(q["query_id"])
            cutoff = int(q["cutoff"])
            ep_id = str(q["episode_id"])
            m_id = str(q["machine_id"])
            base_vec = X_spark[i]

            # Corrupt history by injecting large payouts at tick >= cutoff for target machine
            future_spins = [
                {"episode_id": ep_id, "machine_id": m_id, "tick": cutoff, "payout": 20, "payout_index": 4, "is_win": 1, "split": "train"},
                {"episode_id": ep_id, "machine_id": m_id, "tick": cutoff + 1, "payout": 20, "payout_index": 4, "is_win": 1, "split": "train"},
                {"episode_id": ep_id, "machine_id": m_id, "tick": 255, "payout": 20, "payout_index": 4, "is_win": 1, "split": "train"},
            ]
            # Also inject future spins for sibling peer machines at tick >= cutoff
            peer_machines = set(pdf_spins[pdf_spins["episode_id"] == ep_id]["machine_id"].unique())
            for other_m in peer_machines:
                if other_m != m_id:
                    future_spins.append({
                        "episode_id": ep_id, "machine_id": other_m, "tick": cutoff,
                        "payout": 20, "payout_index": 4, "is_win": 1, "split": "train"
                    })
                    future_spins.append({
                        "episode_id": ep_id, "machine_id": other_m, "tick": cutoff + 5,
                        "payout": 20, "payout_index": 4, "is_win": 1, "split": "train"
                    })

            df_corrupted_spins = spark.createDataFrame(
                pd.concat([pdf_spins, pd.DataFrame(future_spins)], ignore_index=True)
            )
            df_single_q = spark.createDataFrame(pd.DataFrame([q.to_dict()]))

            df_perturbed_gold = compute_gold_features(
                spark=spark,
                df_queries=df_single_q,
                df_spins=df_corrupted_spins
            )
            pdf_perturbed = df_perturbed_gold.toPandas()
            perturbed_vec = pdf_perturbed.iloc[0][expected_manifest].values.astype(np.float32)

            diff = float(np.max(np.abs(perturbed_vec - base_vec)))
            if diff > 0.0:
                logger.error("Temporal boundary violation on query %s: max diff = %f", qid, diff)
                temporal_boundary_pass = False


    # -----------------------------------------------------------------------
    # Final Assessment
    # -----------------------------------------------------------------------
    numerical_pass = (max_abs_diff <= tolerance)
    health_pass = (nan_count == 0 and inf_count == 0 and null_count == 0)
    overall_passed = (manifest_match and sequence_match and numerical_pass and health_pass and temporal_boundary_pass)

    elapsed = time.time() - start_time
    result = ParityAuditResult(
        status="PASSED" if overall_passed else "FAILED",
        total_queries_checked=n_queries,
        total_features_checked=len(expected_manifest),
        column_manifest_match=(manifest_match and sequence_match),
        max_abs_difference=max_abs_diff,
        mean_abs_difference=mean_abs_diff,
        nan_count=nan_count,
        inf_count=inf_count,
        null_count=null_count,
        temporal_boundary_pass=temporal_boundary_pass,
        elapsed_seconds=round(elapsed, 3),
        timestamp=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        details={
            "tolerance": tolerance,
            "queries_verified": n_queries,
            "manifest_match": manifest_match,
            "sequence_match": sequence_match,
            "numerical_pass": numerical_pass,
            "health_pass": health_pass,
        }
    )

    if overall_passed:
        logger.info("Feature Parity Audit PASSED cleanly: max_diff=%e", max_abs_diff)
    else:
        logger.error("Feature Parity Audit FAILED: %s", result.to_dict())

    return result


# Convenience alias matching notebook and external caller conventions
run_parity_audit = verify_feature_parity


def main() -> None:
    parser = argparse.ArgumentParser(description="JAEGERS House Edge PySpark vs. NumPy Feature Parity Verifier")
    parser.add_argument("--catalog", type=str, default="jaegers_dev", help="Unity Catalog catalog name")
    parser.add_argument("--schema", type=str, default="house_edge", help="Unity Catalog schema name")
    parser.add_argument("--queries-table", type=str, default=None, help="Source silver queries table")
    parser.add_argument("--spins-table", type=str, default=None, help="Source silver spins table")
    parser.add_argument("--gold-table", type=str, default=None, help="Gold features table to verify")
    parser.add_argument("--data-dir", type=str, default=None, help="Root directory containing raw split subdirectories")
    parser.add_argument("--max-queries", type=int, default=50, help="Maximum number of queries to sample")
    parser.add_argument("--tolerance", type=float, default=1e-5, help="Maximum acceptable absolute difference")
    parser.add_argument("--skip-temporal", action="store_true", help="Skip future perturbation check")
    parser.add_argument("--force-mock", action="store_true", help="Force offline mock engine")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    res = verify_feature_parity(
        catalog=args.catalog,
        schema=args.schema,
        queries_table=args.queries_table,
        spins_table=args.spins_table,
        gold_table=args.gold_table,
        max_queries=args.max_queries,
        tolerance=args.tolerance,
        check_temporal_boundary=not args.skip_temporal,
        force_mock=args.force_mock,
        data_dir=args.data_dir,
    )
    res.print_summary()
    sys.exit(0 if res.status == "PASSED" else 1)


if __name__ == "__main__":
    main()
