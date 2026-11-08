"""Automated PySpark vs. NumPy Feature Parity Verifier

Compares PySpark Gold features against offline NumPy/Pandas `FeatureComputer`
from `research/feature_api.py`:
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
import inspect
from itertools import combinations
import logging
import os
from pathlib import Path
import sys
import time
import types
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np
import pandas as pd

# Safe mock for joblib if not installed in runtime environment
if "joblib" not in sys.modules:
    try:
        import joblib  # noqa: F401
    except ImportError:
        sys.modules["joblib"] = types.ModuleType("joblib")


def _resolve_src_dir() -> str:
    """Safely resolves `databricks/src` directory even when `__file__` is undefined (Serverless exec)."""
    for candidate in (globals().get("__file__"), globals().get("filename")):
        if isinstance(candidate, str) and candidate and not candidate.startswith("<"):
            return os.path.dirname(os.path.abspath(candidate))
    frame = inspect.currentframe()
    try:
        cur = frame
        while cur is not None:
            co_file = cur.f_code.co_filename
            if isinstance(co_file, str) and co_file and not co_file.startswith("<"):
                cand_dir = os.path.dirname(os.path.abspath(co_file))
                if os.path.isfile(os.path.join(cand_dir, "session.py")) or os.path.isfile(os.path.join(cand_dir, "parity.py")):
                    return cand_dir
            cur = cur.f_back
    finally:
        del frame
    if sys.argv and sys.argv[0] and not sys.argv[0].startswith("-"):
        cand_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
        if os.path.isdir(cand_dir):
            return cand_dir
    cwd = os.getcwd()
    for rel in ("", "src", os.path.join("Jaeger_Main", "House_Edge", "databricks", "src")):
        cand = os.path.abspath(os.path.join(cwd, rel))
        if os.path.isfile(os.path.join(cand, "session.py")):
            return cand
    return cwd


_SRC_DIR = _resolve_src_dir()
if _SRC_DIR not in sys.path:
    sys.path.insert(0, _SRC_DIR)

try:
    from .bronze import run_bronze_ingest
    from .gold import (
        ALL_FEATURE_GROUPS,
        FEATURE_NAMES,
        HISTORICAL_FEATURE_NAMES,
        PAYOUTS,
        compute_gold_features,
        get_feature_names,
        get_qualified_table_name,
        run_gold_pipeline,
    )
    from .mock_engine import MockSparkSession
    from .session import assert_real_spark, get_spark_session, is_live_required, is_mock_spark
    from .silver import run_silver_pipeline
except (ImportError, ValueError):
    from bronze import run_bronze_ingest
    from gold import (
        ALL_FEATURE_GROUPS,
        FEATURE_NAMES,
        HISTORICAL_FEATURE_NAMES,
        PAYOUTS,
        compute_gold_features,
        get_feature_names,
        get_qualified_table_name,
        run_gold_pipeline,
    )
    from mock_engine import MockSparkSession
    from session import assert_real_spark, get_spark_session, is_live_required, is_mock_spark
    from silver import run_silver_pipeline


logger = logging.getLogger("jaegers.databricks.parity")

if __name__ not in sys.modules:
    sys.modules[__name__] = types.ModuleType(__name__)


@dataclass(frozen=True)
class _GroupSpec:
    dependencies: tuple = ()
    availability: str = "past_only"


_FALLBACK_REGISTRY = {
    "type": _GroupSpec(availability="static_machine_type"),
    "lags": _GroupSpec(),
    "pairs": _GroupSpec(("lags",)),
    "windows": _GroupSpec(),
    "decays": _GroupSpec(),
    "transitions": _GroupSpec(("lags",)),
    "missingness": _GroupSpec(),
    "changes": _GroupSpec(("windows",)),
    "peers": _GroupSpec(),
    "type_lag": _GroupSpec(("type", "lags")),
    "current_signal": _GroupSpec(availability="query_only"),
}


class _CanonicalNumpyFeatureComputer:
    """Exact standalone mirror of `research/feature_api.py:FeatureComputer` for Serverless bundles."""

    def __init__(self, history):
        self.history = history
        self.arrays = {}
        self.episodes = {}
        for (episode, machine), rows in history.items():
            ordered = sorted(rows.items())
            ticks = np.array([t for t, _ in ordered], dtype=np.int32)
            labels = np.array([PAYOUTS.index(y) for _, y in ordered], dtype=np.int8)
            self.arrays[(episode, machine)] = (ticks, labels)
            self.episodes.setdefault(episode, []).append(machine)

    def _past(self, episode, machine, cutoff):
        ticks, labels = self.arrays[(episode, machine)]
        stop = np.searchsorted(ticks, cutoff, side="left")
        return ticks[:stop], labels[:stop]

    def row(self, query, groups=ALL_FEATURE_GROUPS):
        cutoff = int(query["cutoff"])
        episode, machine = str(query["episode_id"]), str(query["machine_id"])
        ticks, labels = self._past(episode, machine, cutoff)
        past = {int(t): int(y) for t, y in zip(ticks, labels)}
        lag = [past.get(cutoff - k, -1) for k in range(1, 9)]
        type_index = ("steady", "balanced", "jackpot").index(str(query["machine_type"]))
        output, names = [], []

        def add(name, values):
            values = np.atleast_1d(values)
            output.extend(values.tolist())
            names.extend([f"{group}/{name}_{i}" for i in range(len(values))])

        def distribution(values, weights=None):
            counts = np.bincount(values, weights=weights, minlength=5).astype(float) + 0.5
            return counts / counts.sum()

        for group in groups:
            if group == "type":
                add("onehot", np.eye(3)[type_index])
            elif group == "lags":
                for k, value in enumerate(lag, 1):
                    add(f"lag{k}", np.eye(6)[value + 1])
            elif group == "pairs":
                for a, b in combinations(range(8), 2):
                    ca = -1 if lag[a] < 0 else min(lag[a], 2)
                    cb = -1 if lag[b] < 0 else min(lag[b], 2)
                    index = 0 if ca < 0 or cb < 0 else 1 + ca * 3 + cb
                    add(f"pair{a + 1}_{b + 1}", np.eye(10)[index])
            elif group == "windows":
                for width in (8, 24, 64):
                    values = labels[ticks >= cutoff - width]
                    add(f"freq{width}", distribution(values))
                    add(f"count{width}", np.log1p(len(values)))
            elif group == "decays":
                for decay in (0.9, 0.97, 0.995):
                    weights = decay ** (cutoff - 1 - ticks)
                    add(f"freq{decay}", distribution(labels, weights))
                    add(f"mass{decay}", np.log1p(weights.sum()))
            elif group == "transitions":
                for k in range(1, 9):
                    values = [y for t, y in past.items() if lag[k - 1] >= 0 and past.get(t - k, -2) == lag[k - 1]]
                    add(f"conditional{k}", distribution(values))
                    add(f"count{k}", np.log1p(len(values)))
            elif group == "missingness":
                add(
                    "coverage",
                    [
                        len(ticks) / max(cutoff, 1),
                        np.log1p(len(ticks)),
                        cutoff - 1 - ticks[-1] if len(ticks) else cutoff,
                    ],
                )
                add("lag_known", [v >= 0 for v in lag])
            elif group == "changes":
                recent = distribution(labels[ticks >= cutoff - 24])
                earlier = distribution(labels[(ticks >= cutoff - 64) & (ticks < cutoff - 24)])
                add("recent_minus_past", recent - earlier)
                add("distance", [np.abs(recent - earlier).sum(), -np.sum(recent * np.log(recent))])
            elif group == "peers":
                counts = np.zeros(5)
                peer_recent = np.zeros(5)
                for other in self.episodes[episode]:
                    if other != machine:
                        tt, yy = self._past(episode, other, cutoff)
                        counts += np.bincount(yy, minlength=5)
                        peer_recent += np.bincount(yy[tt >= cutoff - 24], minlength=5)
                add("freq", (counts + 0.5) / (counts.sum() + 2.5))
                add("recent", (peer_recent + 0.5) / (peer_recent.sum() + 2.5))
                add("mass", np.log1p(counts.sum()))
            elif group == "type_lag":
                wins = np.array([0 if x < 0 else float(x > 0) for x in lag])
                add("interaction", (np.eye(3)[type_index, :, None] * wins[None, :]).ravel())
            elif group == "current_signal":
                add("signal", np.eye(3)[int(query["signal"]) + 1])
            else:
                raise ValueError(group)
        return np.asarray(output, dtype=np.float32), names


def _get_offline_feature_computer():
    """Dynamically imports FeatureComputer and REGISTRY from research module, or uses canonical mirror."""
    src_path = Path(_SRC_DIR).resolve()
    for parent in list(src_path.parents)[:4]:
        if str(parent) not in sys.path:
            sys.path.insert(0, str(parent))
    try:
        from Jaeger_Main.House_Edge.research.feature_api import FeatureComputer, REGISTRY
        return FeatureComputer, REGISTRY
    except ImportError:
        try:
            from research.feature_api import FeatureComputer, REGISTRY
            return FeatureComputer, REGISTRY
        except ImportError:
            try:
                from research.features import FeatureComputer, REGISTRY
                return FeatureComputer, REGISTRY
            except ImportError:
                return _CanonicalNumpyFeatureComputer, _FALLBACK_REGISTRY


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
    require_live: bool = False,
    data_dir: Optional[str] = None,
) -> ParityAuditResult:
    """Automated verification comparing PySpark Gold features against offline NumPy FeatureComputer."""
    start_time = time.time()
    live_needed = is_live_required(require_live) and not force_mock
    if spark is None:
        spark = get_spark_session(
            catalog=catalog,
            schema=schema,
            force_mock=force_mock,
            require_live=live_needed,
        )
    elif live_needed:
        assert_real_spark(spark)

    q_name = queries_table or get_qualified_table_name("silver_queries", catalog, schema)
    s_name = spins_table or get_qualified_table_name("silver_spins", catalog, schema)
    g_name = gold_table or get_qualified_table_name("gold_features", catalog, schema)

    # 0. Ensure Silver tables exist in the session; auto-ingest from public data if missing (offline mode)
    need_ingest = False
    try:
        spark.table(q_name)
        spark.table(s_name)
    except Exception:
        need_ingest = True

    if need_ingest:
        if live_needed:
            raise RuntimeError(f"Required live Silver tables ({q_name}, {s_name}) do not exist in Unity Catalog")
        logger.info("Silver tables %s or %s not found; running Bronze & Silver auto-ingestion", q_name, s_name)
        resolved_data_dir = data_dir
        if not (resolved_data_dir and os.path.exists(os.path.join(resolved_data_dir, "train"))):
            candidates = [
                os.path.abspath(os.path.join(_SRC_DIR, "..", "..", "public")),
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
        if live_needed:
            raise RuntimeError(f"Required live Gold table ({g_name}) does not exist in Unity Catalog")
        logger.info("Gold table %s not found; running gold pipeline to generate it", g_name)
        run_gold_pipeline(
            spark=spark,
            catalog=catalog,
            schema=schema,
            queries_table=q_name,
            spins_table=s_name,
            target_table=g_name,
            force_mock=force_mock,
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

    # Only keep spins for the episodes under verification to speed up history construction
    target_episodes = set(pdf_queries["episode_id"].astype(str).unique())
    pdf_spins_subset = pdf_spins[pdf_spins["episode_id"].astype(str).isin(target_episodes)]

    # -----------------------------------------------------------------------
    # Check 1: Column Manifest & Sequence Check
    # -----------------------------------------------------------------------
    expected_manifest = get_feature_names()
    actual_columns = list(pdf_gold.columns)
    manifest_match = all(name in actual_columns for name in expected_manifest)
    feature_start_idx = -1
    for idx, col_name in enumerate(actual_columns):
        if col_name == expected_manifest[0]:
            feature_start_idx = idx
            break

    sequence_match = False
    if feature_start_idx >= 0:
        actual_feature_sequence = actual_columns[feature_start_idx : feature_start_idx + len(expected_manifest)]
        sequence_match = actual_feature_sequence == expected_manifest

    # -----------------------------------------------------------------------
    # Check 2: Offline Reference Generation & Numerical Parity Check
    # -----------------------------------------------------------------------
    FeatureComputer, REGISTRY = _get_offline_feature_computer()
    all_groups = list(REGISTRY.keys())

    history_dict: Dict[Tuple[str, str], Dict[int, int]] = {}
    for _, row in pdf_spins_subset.iterrows():
        ep_id = str(row["episode_id"])
        m_id = str(row["machine_id"])
        t = int(row["tick"])
        p = int(row["payout"])
        history_dict.setdefault((ep_id, m_id), {})[t] = p

    # Also ensure all machines in each target episode (from queries) exist in history_dict
    all_ep_queries = spark.table(q_name).toPandas()
    all_ep_queries = all_ep_queries[all_ep_queries["episode_id"].astype(str).isin(target_episodes)]
    for _, q in all_ep_queries.iterrows():
        ep_id = str(q["episode_id"])
        m_id = str(q["machine_id"])
        history_dict.setdefault((ep_id, m_id), {})

    fc = FeatureComputer(history_dict)

    spark_features_matrix = []
    numpy_features_matrix = []

    gold_by_id = pdf_gold.set_index("query_id")

    for _, q_row in pdf_queries.iterrows():
        qid = q_row["query_id"]
        q_dict = q_row.to_dict()

        ref_vec, _ = fc.row(q_dict, groups=all_groups)
        numpy_features_matrix.append(ref_vec)

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
        test_queries = pdf_queries.head(min(5, len(pdf_queries))).copy().reset_index(drop=True)

        for i, q in test_queries.iterrows():
            qid = str(q["query_id"])
            cutoff = int(q["cutoff"])
            ep_id = str(q["episode_id"])
            m_id = str(q["machine_id"])
            base_vec = X_spark[i]

            ep_spins_only = pdf_spins_subset[pdf_spins_subset["episode_id"].astype(str) == ep_id].copy()

            future_spins = [
                {"episode_id": ep_id, "machine_id": m_id, "tick": cutoff, "payout": 20, "payout_index": 4, "is_win": 1, "split": "train"},
                {"episode_id": ep_id, "machine_id": m_id, "tick": cutoff + 1, "payout": 20, "payout_index": 4, "is_win": 1, "split": "train"},
                {"episode_id": ep_id, "machine_id": m_id, "tick": 255, "payout": 20, "payout_index": 4, "is_win": 1, "split": "train"},
            ]
            peer_machines = set(ep_spins_only["machine_id"].astype(str).unique())
            for other_m in peer_machines:
                if other_m != m_id:
                    future_spins.append({
                        "episode_id": ep_id, "machine_id": other_m, "tick": cutoff,
                        "payout": 20, "payout_index": 4, "is_win": 1, "split": "train",
                    })
                    future_spins.append({
                        "episode_id": ep_id, "machine_id": other_m, "tick": cutoff + 5,
                        "payout": 20, "payout_index": 4, "is_win": 1, "split": "train",
                    })

            df_corrupted_spins = spark.createDataFrame(
                pd.concat([ep_spins_only, pd.DataFrame(future_spins)], ignore_index=True)
            )
            # Also include all episode queries so peer machine set is identical
            ep_all_q = all_ep_queries[all_ep_queries["episode_id"].astype(str) == ep_id].copy()
            if len(ep_all_q) == 0:
                ep_all_q = pd.DataFrame([q.to_dict()])
            df_ep_q = spark.createDataFrame(ep_all_q)

            df_perturbed_gold = compute_gold_features(
                spark=spark,
                df_queries=df_ep_q,
                df_spins=df_corrupted_spins,
            )
            pdf_perturbed = df_perturbed_gold.toPandas()
            perturbed_row = pdf_perturbed[pdf_perturbed["query_id"].astype(str) == qid].iloc[0]
            perturbed_vec = perturbed_row[expected_manifest].values.astype(np.float32)

            diff = float(np.max(np.abs(perturbed_vec - base_vec)))
            if diff > 0.0:
                logger.error("Temporal boundary violation on query %s: max diff = %f", qid, diff)
                temporal_boundary_pass = False

    # -----------------------------------------------------------------------
    # Final Assessment & Delta Persistence
    # -----------------------------------------------------------------------
    numerical_pass = max_abs_diff <= tolerance
    health_pass = nan_count == 0 and inf_count == 0 and null_count == 0
    overall_passed = manifest_match and sequence_match and numerical_pass and health_pass and temporal_boundary_pass

    elapsed = time.time() - start_time
    timestamp_str = datetime.datetime.now(datetime.timezone.utc).isoformat()
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
        timestamp=timestamp_str,
        details={
            "tolerance": tolerance,
            "queries_verified": n_queries,
            "manifest_match": manifest_match,
            "sequence_match": sequence_match,
            "numerical_pass": numerical_pass,
            "health_pass": health_pass,
        },
    )

    # Persist parity audit record to Delta table when catalog/schema provided
    if catalog and schema:
        try:
            audit_tbl = get_qualified_table_name("gold_parity_audit", catalog, schema)
            audit_df = pd.DataFrame([{
                "status": result.status,
                "total_queries_checked": int(result.total_queries_checked),
                "total_features_checked": int(result.total_features_checked),
                "column_manifest_match": bool(result.column_manifest_match),
                "max_abs_difference": float(result.max_abs_difference),
                "mean_abs_difference": float(result.mean_abs_difference),
                "nan_count": int(result.nan_count),
                "inf_count": int(result.inf_count),
                "null_count": int(result.null_count),
                "temporal_boundary_pass": bool(result.temporal_boundary_pass),
                "elapsed_seconds": float(result.elapsed_seconds),
                "timestamp": result.timestamp,
            }])
            spark.createDataFrame(audit_df).write.format("delta").mode("overwrite").saveAsTable(audit_tbl)
        except Exception as exc:
            logger.warning("Could not persist gold_parity_audit table: %s", exc)

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
    parser.add_argument("--max-queries", type=int, default=150, help="Maximum number of queries to sample")
    parser.add_argument("--tolerance", type=float, default=1e-5, help="Maximum acceptable absolute difference")
    parser.add_argument("--skip-temporal", action="store_true", help="Skip future perturbation check")
    parser.add_argument("--force-mock", action="store_true", help="Force offline mock engine")
    parser.add_argument("--require-live", action="store_true", help="Reject mock engine fallback")
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
        require_live=args.require_live,
        data_dir=args.data_dir,
    )
    res.print_summary()
    if res.status != "PASSED":
        raise RuntimeError(f"Feature parity audit failed with status: {res.status}")


if __name__ == "__main__":
    main()
