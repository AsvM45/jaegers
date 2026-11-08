"""Silver Layer Cleaning, Domain Validation & Deduplication for JAEGERS Delta Lakehouse

Enforces strict domain validation rules and Delta quality constraints:
- Payout validation: payout IN (0, 1, 2, 5, 20)
- Machine type validation: machine_type IN ('steady', 'balanced', 'jackpot')
- Signal validation: signal IN (-1, 0, 1)
- Cutoff validation: cutoff BETWEEN 192 AND 256
- Computes derived columns: payout_index (0..4), is_win (0/1)
- Deduplicates spins on primary key: (episode_id, machine_id, tick)
- Generates curated Silver tables:
  * silver_queries
  * silver_spins
  * silver_episodes
  * silver_quality_metrics
"""

from __future__ import annotations

import argparse
import datetime
import inspect
import logging
import os
import sys
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd


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
                if os.path.isfile(os.path.join(cand_dir, "session.py")) or os.path.isfile(os.path.join(cand_dir, "silver.py")):
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
    from .mock_engine import MockColumn, col, lit, when
    from .session import assert_real_spark, get_spark_session, is_live_required, is_mock_spark
except (ImportError, ValueError):
    from mock_engine import MockColumn, col, lit, when
    from session import assert_real_spark, get_spark_session, is_live_required, is_mock_spark

logger = logging.getLogger("jaegers.databricks.silver")

# Canonical domain valid value sets
VALID_PAYOUTS = (0, 1, 2, 5, 20)
VALID_MACHINE_TYPES = ("steady", "balanced", "jackpot")
VALID_SIGNALS = (-1, 0, 1)
PAYOUT_TO_INDEX = {0: 0, 1: 1, 2: 2, 5: 3, 20: 4}


def get_qualified_table_name(table_base: str, catalog: Optional[str] = None, schema: Optional[str] = None) -> str:
    """Returns a 3-part or 2-part Unity Catalog table name if configured, or base name."""
    parts = [p for p in (catalog, schema, table_base) if p]
    return ".".join(parts)


def run_silver_pipeline(
    spark: Optional[Any] = None,
    catalog: Optional[str] = None,
    schema: Optional[str] = None,
    force_mock: bool = False,
    require_live: bool = False,
) -> Dict[str, Any]:
    """Executes the Silver cleaning, validation, and dimension aggregation pipeline."""
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

    logger.info("Starting Silver Layer Processing & Validation (catalog=%s, schema=%s)", catalog, schema)
    timestamp_str = datetime.datetime.now(datetime.timezone.utc).isoformat()

    # Read Bronze tables
    bronze_q_table = get_qualified_table_name("bronze_queries", catalog, schema)
    bronze_h_table = get_qualified_table_name("bronze_history", catalog, schema)
    bronze_c_table = get_qualified_table_name("bronze_conditions", catalog, schema)
    bronze_l_table = get_qualified_table_name("bronze_labels", catalog, schema)

    df_queries = spark.table(bronze_q_table)
    df_history = spark.table(bronze_h_table)

    pdf_queries = df_queries.toPandas()
    pdf_history = df_history.toPandas()

    initial_q_count = len(pdf_queries)
    initial_h_count = len(pdf_history)

    # -----------------------------------------------------------------------
    # 1. Clean and Validate Queries
    # -----------------------------------------------------------------------
    valid_q_mask = (
        pdf_queries["machine_type"].isin(VALID_MACHINE_TYPES)
        & pdf_queries["signal"].isin(VALID_SIGNALS)
        & (pdf_queries["cutoff"] >= 192)
        & (pdf_queries["cutoff"] <= 256)
        & pdf_queries["query_id"].notna()
    )
    rejected_q = pdf_queries[~valid_q_mask]
    clean_queries = pdf_queries[valid_q_mask].drop_duplicates(subset=["query_id"]).copy()
    clean_queries["query_id"] = clean_queries["query_id"].astype(str)
    clean_queries["episode_id"] = clean_queries["episode_id"].astype(str)
    clean_queries["machine_id"] = clean_queries["machine_id"].astype(str)
    clean_queries["machine_type"] = clean_queries["machine_type"].astype(str)
    clean_queries["signal"] = clean_queries["signal"].astype("int64")
    clean_queries["cutoff"] = clean_queries["cutoff"].astype("int64")
    clean_queries["split"] = clean_queries["split"].astype(str)

    # Attach optional condition and outcome columns if available
    try:
        df_conditions = spark.table(bronze_c_table)
        pdf_conditions = df_conditions.toPandas()[["query_id", "condition"]].drop_duplicates(subset=["query_id"])
        pdf_conditions["query_id"] = pdf_conditions["query_id"].astype(str)
        clean_queries = clean_queries.merge(pdf_conditions, on="query_id", how="left")
        clean_queries["condition"] = clean_queries["condition"].fillna("unknown").astype(str)
    except Exception:
        clean_queries["condition"] = "unknown"

    try:
        df_labels = spark.table(bronze_l_table)
        pdf_labels = df_labels.toPandas()[["query_id", "outcome"]].drop_duplicates(subset=["query_id"])
        pdf_labels["query_id"] = pdf_labels["query_id"].astype(str)
        clean_queries = clean_queries.merge(pdf_labels, on="query_id", how="left")
    except Exception:
        clean_queries["outcome"] = np.nan

    # Use sentinel -1 for missing outcomes when converting to Spark DataFrame so Arrow type inference succeeds
    clean_queries["outcome"] = pd.to_numeric(clean_queries["outcome"], errors="coerce")

    # -----------------------------------------------------------------------
    # 2. Clean, Validate and Enrich Spins (History)
    # -----------------------------------------------------------------------
    valid_h_mask = (
        pdf_history["payout"].isin(VALID_PAYOUTS)
        & (pdf_history["tick"] >= 0)
        & pdf_history["episode_id"].notna()
        & pdf_history["machine_id"].notna()
    )
    rejected_h = pdf_history[~valid_h_mask]
    clean_history = pdf_history[valid_h_mask].copy()
    clean_history["episode_id"] = clean_history["episode_id"].astype(str)
    clean_history["machine_id"] = clean_history["machine_id"].astype(str)
    clean_history["tick"] = clean_history["tick"].astype("int64")
    clean_history["payout"] = clean_history["payout"].astype("int64")
    clean_history["split"] = clean_history["split"].astype(str)

    # Deduplicate spins on primary key (episode_id, machine_id, tick)
    dedup_history = clean_history.drop_duplicates(subset=["episode_id", "machine_id", "tick"]).copy()
    duplicates_dropped = int(len(clean_history) - len(dedup_history))

    # Compute derived columns: payout_index (0..4) and is_win (0/1)
    dedup_history["payout_index"] = dedup_history["payout"].map(PAYOUT_TO_INDEX).astype("int64")
    dedup_history["is_win"] = (dedup_history["payout"] > 0).astype("int64")

    # Select standard silver_spins columns
    silver_spins_pdf = dedup_history[[
        "episode_id", "machine_id", "tick", "payout", "payout_index", "is_win", "split"
    ]].copy()

    # -----------------------------------------------------------------------
    # 3. Create Episode Summary Dimension (silver_episodes)
    # -----------------------------------------------------------------------
    ep_queries = clean_queries.groupby(["episode_id", "split"], as_index=False).agg(
        machine_count=("machine_id", "nunique"),
        min_cutoff=("cutoff", "min"),
        max_cutoff=("cutoff", "max"),
        condition=("condition", "first"),
    )

    ep_spins = silver_spins_pdf.groupby(["episode_id", "split"], as_index=False).agg(
        total_spins_observed=("tick", "count"),
        total_payout_sum=("payout", "sum"),
        win_count=("is_win", "sum"),
    )

    silver_episodes_pdf = ep_queries.merge(ep_spins, on=["episode_id", "split"], how="left")
    silver_episodes_pdf["total_spins_observed"] = silver_episodes_pdf["total_spins_observed"].fillna(0).astype("int64")
    silver_episodes_pdf["total_payout_sum"] = silver_episodes_pdf["total_payout_sum"].fillna(0).astype("int64")
    silver_episodes_pdf["win_count"] = silver_episodes_pdf["win_count"].fillna(0).astype("int64")
    silver_episodes_pdf["win_rate"] = (
        silver_episodes_pdf["win_count"] / silver_episodes_pdf["total_spins_observed"].replace(0, 1)
    ).round(4).astype("float64")

    # -----------------------------------------------------------------------
    # 4. Record Quality Audit Metrics
    # -----------------------------------------------------------------------
    quality_metrics = [
        {"metric_name": "queries_total_ingested", "value": int(initial_q_count), "recorded_at": timestamp_str},
        {"metric_name": "queries_valid", "value": int(len(clean_queries)), "recorded_at": timestamp_str},
        {"metric_name": "queries_rejected", "value": int(len(rejected_q)), "recorded_at": timestamp_str},
        {"metric_name": "spins_total_ingested", "value": int(initial_h_count), "recorded_at": timestamp_str},
        {"metric_name": "spins_valid", "value": int(len(silver_spins_pdf)), "recorded_at": timestamp_str},
        {"metric_name": "spins_rejected", "value": int(len(rejected_h)), "recorded_at": timestamp_str},
        {"metric_name": "spins_duplicates_removed", "value": int(duplicates_dropped), "recorded_at": timestamp_str},
        {"metric_name": "episodes_summarized", "value": int(len(silver_episodes_pdf)), "recorded_at": timestamp_str},
    ]
    pdf_quality = pd.DataFrame(quality_metrics)

    # -----------------------------------------------------------------------
    # 5. Save Silver Tables
    # -----------------------------------------------------------------------
    target_q_name = get_qualified_table_name("silver_queries", catalog, schema)
    target_s_name = get_qualified_table_name("silver_spins", catalog, schema)
    target_e_name = get_qualified_table_name("silver_episodes", catalog, schema)
    target_m_name = get_qualified_table_name("silver_quality_metrics", catalog, schema)

    if is_mock_spark(spark):
        spark_silver_q = spark.createDataFrame(clean_queries)
    else:
        from pyspark.sql import functions as F  # type: ignore
        q_for_spark = clean_queries.copy()
        q_for_spark["outcome"] = q_for_spark["outcome"].fillna(-1).astype("int64")
        spark_silver_q = spark.createDataFrame(q_for_spark).withColumn(
            "outcome",
            F.when(F.col("outcome") < 0, F.lit(None).cast("int")).otherwise(F.col("outcome").cast("int")),
        )
    spark_silver_q.write.format("delta").mode("overwrite").saveAsTable(target_q_name)

    spark_silver_s = spark.createDataFrame(silver_spins_pdf)
    spark_silver_s.write.format("delta").mode("overwrite").saveAsTable(target_s_name)

    spark_silver_e = spark.createDataFrame(silver_episodes_pdf)
    spark_silver_e.write.format("delta").mode("overwrite").saveAsTable(target_e_name)

    spark_silver_m = spark.createDataFrame(pdf_quality)
    spark_silver_m.write.format("delta").mode("overwrite").saveAsTable(target_m_name)

    summary = {
        "silver_queries": int(len(clean_queries)),
        "silver_spins": int(len(silver_spins_pdf)),
        "silver_episodes": int(len(silver_episodes_pdf)),
        "silver_quality_metrics": int(len(pdf_quality)),
        "rejected_queries": int(len(rejected_q)),
        "rejected_spins": int(len(rejected_h)),
        "duplicates_dropped": int(duplicates_dropped),
    }

    logger.info("Silver Layer Processing completed successfully: %s", summary)
    return summary


def refresh_views(spark: Any, catalog: Optional[str] = None, schema: Optional[str] = None) -> Dict[str, Any]:
    """Refreshes persistent analytical monitoring views/tables across Bronze, Silver, and Gold."""
    logger.info("Refreshing Lakehouse analytical monitoring views in catalog=%s, schema=%s", catalog, schema)

    silver_q_tbl = get_qualified_table_name("silver_queries", catalog, schema)
    silver_e_tbl = get_qualified_table_name("silver_episodes", catalog, schema)
    bronze_a_tbl = get_qualified_table_name("bronze_audit_log", catalog, schema)
    target_summary_tbl = get_qualified_table_name("monitoring_machine_summary", catalog, schema)
    target_view_name = get_qualified_table_name("v_machine_summary", catalog, schema)

    if is_mock_spark(spark):
        # Offline MockSparkSession: verify silver_queries is readable and materialize summary table
        pdf_q = spark.table(silver_q_tbl).toPandas()
        summary_pdf = (
            pdf_q.groupby(["split", "machine_type"], as_index=False)
            .agg(query_count=("query_id", "count"), avg_cutoff=("cutoff", "mean"))
        )
        spark.createDataFrame(summary_pdf).write.format("delta").mode("overwrite").saveAsTable(target_summary_tbl)
        return {"status": "SUCCESS", "monitoring_table": target_summary_tbl, "rows": int(len(summary_pdf))}

    # Live Databricks Spark execution: create persistent Unity Catalog views and materialized monitoring table
    # Do NOT swallow SQL errors in live mode.
    machine_summary_sql = f"""
    SELECT
        split,
        machine_type,
        COUNT(*) AS query_count,
        ROUND(AVG(cutoff * 1.0), 2) AS avg_cutoff,
        SUM(CASE WHEN outcome IS NOT NULL THEN 1 ELSE 0 END) AS labeled_queries
    FROM {silver_q_tbl}
    GROUP BY split, machine_type
    ORDER BY split, machine_type
    """
    df_machine_summary = spark.sql(machine_summary_sql)
    df_machine_summary.write.format("delta").mode("overwrite").saveAsTable(target_summary_tbl)

    view_sql = f"CREATE OR REPLACE VIEW {target_view_name} AS {machine_summary_sql}"
    spark.sql(view_sql)

    # Also verify episode and audit tables are queryable via Spark SQL
    drift_count = spark.sql(f"SELECT COUNT(*) AS cnt FROM {silver_e_tbl}").toPandas().iloc[0]["cnt"]
    audit_count = spark.sql(f"SELECT COUNT(*) AS cnt FROM {bronze_a_tbl}").toPandas().iloc[0]["cnt"]
    row_count = df_machine_summary.count()

    result = {
        "status": "SUCCESS",
        "monitoring_table": target_summary_tbl,
        "monitoring_view": target_view_name,
        "machine_summary_rows": int(row_count),
        "silver_episodes_verified": int(drift_count),
        "bronze_audit_rows_verified": int(audit_count),
    }
    logger.info("Persistent analytical monitoring refreshed: %s", result)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="JAEGERS House Edge Silver Layer Processing")
    parser.add_argument("--catalog", type=str, default="jaegers_dev", help="Unity Catalog catalog name")
    parser.add_argument("--schema", type=str, default="house_edge", help="Unity Catalog schema name")
    parser.add_argument("--action", type=str, default="process", choices=["process", "refresh_views"], help="Pipeline action to run")
    parser.add_argument("--force-mock", action="store_true", help="Force offline mock engine")
    parser.add_argument("--require-live", action="store_true", help="Reject mock engine fallback")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    live_needed = is_live_required(args.require_live) and not args.force_mock
    spark = get_spark_session(
        catalog=args.catalog,
        schema=args.schema,
        force_mock=args.force_mock,
        require_live=live_needed,
    )

    if args.action == "refresh_views":
        res = refresh_views(spark, args.catalog, args.schema)
        print(f"Silver Monitoring Refresh Result: {res}")
    else:
        summary = run_silver_pipeline(
            spark=spark,
            catalog=args.catalog,
            schema=args.schema,
            force_mock=args.force_mock,
            require_live=live_needed,
        )
        print(f"Silver Pipeline Summary: {summary}")


if __name__ == "__main__":
    main()
