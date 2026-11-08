"""Gold Layer PySpark Feature Pipeline with Strict Cutoff & Exact Parity

Enforces strict temporal boundary: for any query with cutoff T, only observations
strictly where tick < cutoff are joined and transformed (zero future records).
Transforms Silver queries and spins into curated Gold features matching the
authoritative 471-feature manifest from `research/feature_api.py`:
- 10 Historical Groups (468 features) + 1 Query-only Group (3 features) = 471 features.

Supports distributed execution via episode-grouped Map Pandas UDF (`applyInPandas`)
partitioned by `episode_id` for zero-shuffle parallel execution on Databricks Serverless
Spark as well as offline execution with `mock_engine`.
Saves output to `gold_features` Delta table.
"""

from __future__ import annotations

import argparse
import datetime
import inspect
from itertools import combinations
import logging
import os
import sys
import time
import types
from typing import Any, Dict, List, Optional, Sequence

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
                if os.path.isfile(os.path.join(cand_dir, "session.py")) or os.path.isfile(os.path.join(cand_dir, "gold.py")):
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
    from .mock_engine import (
        FloatType,
        IntegerType,
        MockColumn,
        MockDataFrame,
        MockSparkSession,
        StringType,
        StructField,
        StructType,
        col,
        lit,
        when,
    )
    from .session import assert_real_spark, get_spark_session, is_live_required, is_mock_spark
except ImportError:
    from mock_engine import (
        FloatType,
        IntegerType,
        MockColumn,
        MockDataFrame,
        MockSparkSession,
        StringType,
        StructField,
        StructType,
        col,
        lit,
        when,
    )
    from session import assert_real_spark, get_spark_session, is_live_required, is_mock_spark


logger = logging.getLogger("jaegers.databricks.gold")

# Canonical feature group definitions
HISTORICAL_FEATURE_GROUPS = (
    "type",
    "lags",
    "pairs",
    "windows",
    "decays",
    "transitions",
    "missingness",
    "changes",
    "peers",
    "type_lag",
)
HISTORICAL_GROUPS = HISTORICAL_FEATURE_GROUPS
ALL_FEATURE_GROUPS = HISTORICAL_FEATURE_GROUPS + ("current_signal",)

MACHINE_TYPES = ("steady", "balanced", "jackpot")
PAYOUTS = (0, 1, 2, 5, 20)
OUTPUT_CLASSES = (0, 1, 2, 5, 20)
PAYOUT_TO_INDEX = {0: 0, 1: 1, 2: 2, 5: 3, 20: 4}
METADATA_COLS = ["query_id", "episode_id", "machine_id", "cutoff", "split", "condition"]


def generate_feature_manifest() -> List[str]:
    """Generates the exact, deterministic sequence of all 471 feature column names."""
    names: List[str] = []

    # 1. type (3)
    names.extend([f"type/onehot_{i}" for i in range(3)])

    # 2. lags (48): lag1..lag8, 6 categories each
    for k in range(1, 9):
        names.extend([f"lags/lag{k}_{i}" for i in range(6)])

    # 3. pairs (280): 28 combinations * 10 categories
    for a, b in combinations(range(8), 2):
        names.extend([f"pairs/pair{a+1}_{b+1}_{i}" for i in range(10)])

    # 4. windows (18): 3 widths * (5 freq + 1 count)
    for w in (8, 24, 64):
        names.extend([f"windows/freq{w}_{i}" for i in range(5)])
        names.append(f"windows/count{w}_0")

    # 5. decays (18): 3 decays * (5 freq + 1 mass)
    for d in (0.9, 0.97, 0.995):
        names.extend([f"decays/freq{d}_{i}" for i in range(5)])
        names.append(f"decays/mass{d}_0")

    # 6. transitions (48): 8 lags * (5 conditional + 1 count)
    for k in range(1, 9):
        names.extend([f"transitions/conditional{k}_{i}" for i in range(5)])
        names.append(f"transitions/count{k}_0")

    # 7. missingness (11): 3 coverage + 8 lag_known
    names.extend([f"missingness/coverage_{i}" for i in range(3)])
    names.extend([f"missingness/lag_known_{i}" for i in range(8)])

    # 8. changes (7): 5 drift + 2 distance
    names.extend([f"changes/recent_minus_past_{i}" for i in range(5)])
    names.extend([f"changes/distance_{i}" for i in range(2)])

    # 9. peers (11): 5 freq + 5 recent + 1 mass
    names.extend([f"peers/freq_{i}" for i in range(5)])
    names.extend([f"peers/recent_{i}" for i in range(5)])
    names.append("peers/mass_0")

    # 10. type_lag (24): 3 types * 8 lag interactions
    names.extend([f"type_lag/interaction_{i}" for i in range(24)])

    # 11. current_signal (3)
    names.extend([f"current_signal/signal_{i}" for i in range(3)])

    return names


FEATURE_NAMES = generate_feature_manifest()
HISTORICAL_FEATURE_NAMES = FEATURE_NAMES[:468]
QUERY_FEATURE_NAMES = FEATURE_NAMES[468:]
_SAFE_FEATURE_NAMES = [f"f_{i}" for i in range(len(FEATURE_NAMES))]


def get_feature_names() -> List[str]:
    """Returns the ordered list of all 471 feature column names."""
    return list(FEATURE_NAMES)


def get_historical_feature_names() -> List[str]:
    """Returns the ordered list of all 468 historical feature column names."""
    return list(HISTORICAL_FEATURE_NAMES)


def get_gold_feature_schema(use_native: bool = False, safe_names: bool = False) -> Any:
    """Builds and returns the StructType schema for the Gold features table."""
    feat_cols = _SAFE_FEATURE_NAMES if safe_names else FEATURE_NAMES
    if use_native:
        from pyspark.sql import types as T  # type: ignore
        fields = [
            T.StructField("query_id", T.StringType(), False),
            T.StructField("episode_id", T.StringType(), False),
            T.StructField("machine_id", T.StringType(), False),
            T.StructField("cutoff", T.IntegerType(), False),
            T.StructField("split", T.StringType(), False),
            T.StructField("condition", T.StringType(), True),
        ]
        for col_name in feat_cols:
            fields.append(T.StructField(col_name, T.FloatType(), False))
        return T.StructType(fields)

    st = StructType([
        StructField("query_id", StringType(), False),
        StructField("episode_id", StringType(), False),
        StructField("machine_id", StringType(), False),
        StructField("cutoff", IntegerType(), False),
        StructField("split", StringType(), False),
        StructField("condition", StringType(), True),
    ])
    for col_name in feat_cols:
        st.add(StructField(col_name, FloatType(), False))
    return st


def get_qualified_table_name(table_base: str, catalog: Optional[str] = None, schema: Optional[str] = None) -> str:
    """Returns a qualified table name (catalog.schema.table) or simple base name."""
    parts = [p for p in (catalog, schema, table_base) if p]
    return ".".join(parts)


def _distribution_smoothed(values: np.ndarray, weights: Optional[np.ndarray] = None) -> np.ndarray:
    """Computes Dirichlet-smoothed 5-class distribution with +0.5 Laplace prior."""
    counts = np.bincount(values.astype(np.int64), weights=weights, minlength=5).astype(np.float64) + 0.5
    return counts / counts.sum()


def compute_query_features(
    query: Dict[str, Any],
    history_by_machine: Dict[str, Dict[int, int]],
    all_episode_machines: Sequence[str],
    groups: Sequence[str] = ALL_FEATURE_GROUPS,
) -> np.ndarray:
    """Extracts the exact feature vector for a single query from past-only spins (tick < cutoff)."""
    cutoff = int(query["cutoff"])
    machine = str(query["machine_id"])
    machine_type = str(query["machine_type"])
    signal = int(query.get("signal", 0))

    # Target machine past-only spins: strictly tick < cutoff
    raw_target_spins = history_by_machine.get(machine, {})
    past_target = {
        int(t): PAYOUT_TO_INDEX.get(int(p), 0)
        for t, p in raw_target_spins.items()
        if int(t) < cutoff
    }

    ordered_ticks = sorted(past_target.keys())
    ticks = np.array(ordered_ticks, dtype=np.int32)
    labels = np.array([past_target[t] for t in ordered_ticks], dtype=np.int8)

    # Lags 1..8: lookup at cutoff - k
    lag = [past_target.get(cutoff - k, -1) for k in range(1, 9)]
    type_index = MACHINE_TYPES.index(machine_type) if machine_type in MACHINE_TYPES else 0

    output: List[float] = []

    for group in groups:
        if group == "type":
            eye3 = np.eye(3, dtype=np.float32)
            output.extend(eye3[type_index].tolist())

        elif group == "lags":
            eye6 = np.eye(6, dtype=np.float32)
            for val in lag:
                output.extend(eye6[val + 1].tolist())

        elif group == "pairs":
            eye10 = np.eye(10, dtype=np.float32)
            for a, b in combinations(range(8), 2):
                ca = -1 if lag[a] < 0 else min(lag[a], 2)
                cb = -1 if lag[b] < 0 else min(lag[b], 2)
                idx = 0 if ca < 0 or cb < 0 else 1 + ca * 3 + cb
                output.extend(eye10[idx].tolist())

        elif group == "windows":
            for width in (8, 24, 64):
                mask = ticks >= (cutoff - width)
                w_labels = labels[mask]
                freq = _distribution_smoothed(w_labels)
                output.extend(freq.tolist())
                output.append(float(np.log1p(len(w_labels))))

        elif group == "decays":
            for decay in (0.9, 0.97, 0.995):
                if len(ticks) > 0:
                    weights = decay ** (cutoff - 1 - ticks)
                    freq = _distribution_smoothed(labels, weights=weights)
                    mass = float(np.log1p(weights.sum()))
                else:
                    freq = np.full(5, 0.2, dtype=np.float64)
                    mass = 0.0
                output.extend(freq.tolist())
                output.append(mass)

        elif group == "transitions":
            for k in range(1, 9):
                target_val = lag[k - 1]
                if target_val >= 0:
                    matched = [
                        past_target[t]
                        for t in ordered_ticks
                        if past_target.get(t - k, -2) == target_val
                    ]
                else:
                    matched = []
                freq = _distribution_smoothed(np.array(matched, dtype=np.int64))
                output.extend(freq.tolist())
                output.append(float(np.log1p(len(matched))))

        elif group == "missingness":
            n_ticks = len(ticks)
            coverage_0 = float(n_ticks / max(cutoff, 1))
            coverage_1 = float(np.log1p(n_ticks))
            coverage_2 = float((cutoff - 1 - ticks[-1]) if n_ticks > 0 else cutoff)
            output.extend([coverage_0, coverage_1, coverage_2])
            output.extend([1.0 if v >= 0 else 0.0 for v in lag])

        elif group == "changes":
            recent_mask = ticks >= (cutoff - 24)
            earlier_mask = (ticks >= (cutoff - 64)) & (ticks < (cutoff - 24))
            recent = _distribution_smoothed(labels[recent_mask])
            earlier = _distribution_smoothed(labels[earlier_mask])
            diff = recent - earlier
            l1_dist = float(np.abs(diff).sum())
            entropy = float(-np.sum(recent * np.log(recent)))
            output.extend(diff.tolist())
            output.extend([l1_dist, entropy])

        elif group == "peers":
            peer_counts = np.zeros(5, dtype=np.float64)
            peer_recent = np.zeros(5, dtype=np.float64)
            for other_m in all_episode_machines:
                if other_m == machine:
                    continue
                other_spins = history_by_machine.get(other_m, {})
                for t, p in other_spins.items():
                    if t < cutoff:
                        p_idx = PAYOUT_TO_INDEX.get(int(p), 0)
                        peer_counts[p_idx] += 1.0
                        if t >= (cutoff - 24):
                            peer_recent[p_idx] += 1.0

            freq = (peer_counts + 0.5) / (peer_counts.sum() + 2.5)
            recent = (peer_recent + 0.5) / (peer_recent.sum() + 2.5)
            mass = float(np.log1p(peer_counts.sum()))
            output.extend(freq.tolist())
            output.extend(recent.tolist())
            output.append(mass)

        elif group == "type_lag":
            wins = np.array([0.0 if x < 0 else (1.0 if x > 0 else 0.0) for x in lag], dtype=np.float32)
            onehot = np.eye(3, dtype=np.float32)[type_index]
            interaction = (onehot[:, None] * wins[None, :]).ravel()
            output.extend(interaction.tolist())

        elif group == "current_signal":
            sig_idx = max(0, min(2, signal + 1))
            eye3 = np.eye(3, dtype=np.float32)
            output.extend(eye3[sig_idx].tolist())

        else:
            raise ValueError(f"Unknown feature group: {group}")

    return np.asarray(output, dtype=np.float32)


def _extract_episode_records(episode_pdf: pd.DataFrame, feature_col_names: Sequence[str]) -> pd.DataFrame:
    """Internal helper computing episode feature rows with configurable feature column names."""
    out_cols = list(METADATA_COLS) + list(feature_col_names)
    if len(episode_pdf) == 0:
        return pd.DataFrame(columns=out_cols)

    queries = episode_pdf[episode_pdf["record_type"] == "query"]
    spins = episode_pdf[episode_pdf["record_type"] == "spin"]

    if len(queries) == 0:
        return pd.DataFrame(columns=out_cols)

    history_by_machine: Dict[str, Dict[int, int]] = {}
    if len(spins) > 0:
        for m_id, group in spins.groupby("machine_id"):
            m_key = str(m_id[0] if isinstance(m_id, tuple) else m_id)
            history_by_machine[m_key] = dict(
                zip(group["tick"].astype(int), group["payout"].astype(int))
            )

    all_machines = sorted(list(
        set(queries["machine_id"].astype(str).unique()).union(
            set(spins["machine_id"].astype(str).unique()) if len(spins) > 0 else set()
        )
    ))

    records: List[Dict[str, Any]] = []
    for _, q_row in queries.iterrows():
        q_dict = q_row.to_dict()
        vec = compute_query_features(
            query=q_dict,
            history_by_machine=history_by_machine,
            all_episode_machines=all_machines,
            groups=ALL_FEATURE_GROUPS,
        )

        rec: Dict[str, Any] = {
            "query_id": str(q_dict["query_id"]),
            "episode_id": str(q_dict["episode_id"]),
            "machine_id": str(q_dict["machine_id"]),
            "cutoff": np.int32(int(q_dict["cutoff"])),
            "split": str(q_dict.get("split", "train")),
            "condition": str(q_dict.get("condition", "unknown")),
        }
        for name, val in zip(feature_col_names, vec):
            rec[name] = np.float32(val)
        records.append(rec)

    return pd.DataFrame(records, columns=out_cols)


def extract_episode_features_udf(episode_pdf: pd.DataFrame) -> pd.DataFrame:
    """Grouped Map Pandas UDF partitioned by `episode_id` returning canonical FEATURE_NAMES."""
    return _extract_episode_records(episode_pdf, FEATURE_NAMES)


def _extract_episode_features_safe_udf(episode_pdf: pd.DataFrame) -> pd.DataFrame:
    """Grouped Map Pandas UDF using punctuation-free column identifiers for Catalyst unpacking."""
    return _extract_episode_records(episode_pdf, _SAFE_FEATURE_NAMES)


def compute_gold_features(
    spark: Any,
    df_queries: Any,
    df_spins: Any,
    catalog: Optional[str] = None,
    schema: Optional[str] = None,
) -> Any:
    """Transforms Silver queries and spins DataFrames into Gold features DataFrame.

    Partitions by `episode_id` and executes `applyInPandas`.
    On live PySpark, uses punctuation-safe intermediate identifiers inside `applyInPandas`
    (so Catalyst struct unpacking does not misinterpret `.` in `decays/freq0.9_0` as nested fields)
    and immediately restores the exact 471 canonical `FEATURE_NAMES` via `.toDF(...)`.
    """
    if is_mock_spark(spark):
        gold_schema = get_gold_feature_schema(use_native=False, safe_names=False)
        df_q_prep = df_queries.select(
            col("episode_id"),
            col("query_id"),
            col("machine_id"),
            col("machine_type"),
            col("signal"),
            col("cutoff"),
            col("split"),
            (col("condition") if "condition" in df_queries.columns else lit("unknown")).alias("condition"),
            lit("query").alias("record_type"),
            lit(-1).alias("tick"),
            lit(-1).alias("payout"),
        )
        df_s_prep = df_spins.select(
            col("episode_id"),
            lit("").alias("query_id"),
            col("machine_id"),
            lit("").alias("machine_type"),
            lit(0).alias("signal"),
            lit(-1).alias("cutoff"),
            col("split"),
            lit("unknown").alias("condition"),
            lit("spin").alias("record_type"),
            col("tick"),
            col("payout"),
        )
        df_combined = df_q_prep.unionByName(df_s_prep)
        return (
            df_combined
            .groupBy("episode_id")
            .applyInPandas(extract_episode_features_udf, schema=gold_schema)
        )

    # Real PySpark / Spark Connect path
    from pyspark.sql import functions as F  # type: ignore

    safe_schema = get_gold_feature_schema(use_native=True, safe_names=True)
    df_q_prep = df_queries.select(
        F.col("episode_id").cast("string").alias("episode_id"),
        F.col("query_id").cast("string").alias("query_id"),
        F.col("machine_id").cast("string").alias("machine_id"),
        F.col("machine_type").cast("string").alias("machine_type"),
        F.col("signal").cast("int").alias("signal"),
        F.col("cutoff").cast("int").alias("cutoff"),
        F.col("split").cast("string").alias("split"),
        (F.col("condition").cast("string") if "condition" in df_queries.columns else F.lit("unknown")).alias("condition"),
        F.lit("query").alias("record_type"),
        F.lit(-1).cast("int").alias("tick"),
        F.lit(-1).cast("int").alias("payout"),
    )
    df_s_prep = df_spins.select(
        F.col("episode_id").cast("string").alias("episode_id"),
        F.lit("").alias("query_id"),
        F.col("machine_id").cast("string").alias("machine_id"),
        F.lit("").alias("machine_type"),
        F.lit(0).cast("int").alias("signal"),
        F.lit(-1).cast("int").alias("cutoff"),
        F.col("split").cast("string").alias("split"),
        F.lit("unknown").alias("condition"),
        F.lit("spin").alias("record_type"),
        F.col("tick").cast("int").alias("tick"),
        F.col("payout").cast("int").alias("payout"),
    )

    df_combined = df_q_prep.unionByName(df_s_prep)
    df_safe_gold = (
        df_combined
        .groupBy("episode_id")
        .applyInPandas(_extract_episode_features_safe_udf, schema=safe_schema)
    )
    canonical_cols = list(METADATA_COLS) + list(FEATURE_NAMES)
    return df_safe_gold.toDF(*canonical_cols)


def get_native_feature_expressions() -> Dict[str, MockColumn]:
    """Provides pure PySpark Column expressions for machine type and signal features."""
    exprs: Dict[str, MockColumn] = {
        "type/onehot_0": when(col("machine_type") == "steady", 1.0).otherwise(0.0),
        "type/onehot_1": when(col("machine_type") == "balanced", 1.0).otherwise(0.0),
        "type/onehot_2": when(col("machine_type") == "jackpot", 1.0).otherwise(0.0),
        "current_signal/signal_0": when(col("signal") == -1, 1.0).otherwise(0.0),
        "current_signal/signal_1": when(col("signal") == 0, 1.0).otherwise(0.0),
        "current_signal/signal_2": when(col("signal") == 1, 1.0).otherwise(0.0),
    }
    return exprs


def run_gold_pipeline(
    spark: Optional[Any] = None,
    catalog: Optional[str] = None,
    schema: Optional[str] = None,
    queries_table: Optional[str] = None,
    spins_table: Optional[str] = None,
    target_table: Optional[str] = None,
    force_mock: bool = False,
    require_live: bool = False,
) -> Dict[str, Any]:
    """Executes the Gold feature pipeline, saving output to the Gold Delta table."""
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
    t_name = target_table or get_qualified_table_name("gold_features", catalog, schema)

    logger.info("Starting Gold Feature Pipeline: queries=%s, spins=%s -> target=%s", q_name, s_name, t_name)

    df_queries = spark.table(q_name)
    df_spins = spark.table(s_name)

    df_gold = compute_gold_features(
        spark=spark,
        df_queries=df_queries,
        df_spins=df_spins,
        catalog=catalog,
        schema=schema,
    )

    # Save to Gold Delta Lake table (overwriteSchema enabled for full 477-column schema)
    writer = df_gold.write.format("delta").mode("overwrite")
    if not is_mock_spark(spark):
        writer = writer.option("overwriteSchema", "true")
    writer.saveAsTable(t_name)

    elapsed = time.time() - start_time
    total_queries = int(df_gold.count())
    feature_count = len(FEATURE_NAMES)

    summary = {
        "status": "SUCCESS",
        "gold_table": t_name,
        "total_queries": total_queries,
        "feature_count": feature_count,
        "historical_features": len(HISTORICAL_FEATURE_NAMES),
        "query_features": len(QUERY_FEATURE_NAMES),
        "elapsed_seconds": round(elapsed, 3),
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    }

    logger.info("Gold Feature Pipeline completed successfully: %s", summary)
    return summary


# Convenience alias matching notebook and external caller conventions
run_gold_feature_pipeline = run_gold_pipeline


def main() -> None:
    parser = argparse.ArgumentParser(description="JAEGERS House Edge Gold Layer Feature Pipeline")
    parser.add_argument("--catalog", type=str, default="jaegers_dev", help="Unity Catalog catalog name")
    parser.add_argument("--schema", type=str, default="house_edge", help="Unity Catalog schema name")
    parser.add_argument("--queries-table", type=str, default=None, help="Source silver queries table")
    parser.add_argument("--spins-table", type=str, default=None, help="Source silver spins table")
    parser.add_argument("--target-table", type=str, default=None, help="Destination gold features table")
    parser.add_argument("--force-mock", action="store_true", help="Force offline mock engine")
    parser.add_argument("--require-live", action="store_true", help="Reject mock engine fallback")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    summary = run_gold_pipeline(
        catalog=args.catalog,
        schema=args.schema,
        queries_table=args.queries_table,
        spins_table=args.spins_table,
        target_table=args.target_table,
        force_mock=args.force_mock,
        require_live=args.require_live,
    )
    print(f"Gold Pipeline Result: {summary}")


if __name__ == "__main__":
    main()
