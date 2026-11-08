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
import logging
import os
import sys
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

# Support both relative package imports and direct script execution
_SRC_DIR = os.path.dirname(os.path.abspath(__file__))
if _SRC_DIR not in sys.path:
    sys.path.insert(0, _SRC_DIR)

try:
    from .mock_engine import MockColumn, col, lit, when
    from .session import get_spark_session
except (ImportError, ValueError):
    from mock_engine import MockColumn, col, lit, when
    from session import get_spark_session

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
    force_mock: bool = False
) -> Dict[str, Any]:
    """Executes the Silver cleaning, validation, and dimension aggregation pipeline.

    Args:
        spark: Active SparkSession or MockSparkSession.
        catalog: Target Unity Catalog catalog name.
        schema: Target Unity Catalog schema name.
        force_mock: If True, forces MockSparkSession.

    Returns:
        Dictionary summarizing validated rows, rejected rows, and output tables.
    """
    if spark is None:
        spark = get_spark_session(catalog=catalog, schema=schema, force_mock=force_mock)

    logger.info("Starting Silver Layer Processing & Validation")
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
        pdf_queries["machine_type"].isin(VALID_MACHINE_TYPES) &
        pdf_queries["signal"].isin(VALID_SIGNALS) &
        (pdf_queries["cutoff"] >= 192) &
        (pdf_queries["cutoff"] <= 256) &
        pdf_queries["query_id"].notna()
    )
    rejected_q = pdf_queries[~valid_q_mask]
    clean_queries = pdf_queries[valid_q_mask].drop_duplicates(subset=["query_id"]).copy()

    # Attach optional condition and outcome columns if available
    try:
        df_conditions = spark.table(bronze_c_table)
        pdf_conditions = df_conditions.toPandas()[["query_id", "condition"]].drop_duplicates(subset=["query_id"])
        clean_queries = clean_queries.merge(pdf_conditions, on="query_id", how="left")
    except Exception:
        clean_queries["condition"] = "unknown"

    try:
        df_labels = spark.table(bronze_l_table)
        pdf_labels = df_labels.toPandas()[["query_id", "outcome"]].drop_duplicates(subset=["query_id"])
        clean_queries = clean_queries.merge(pdf_labels, on="query_id", how="left")
    except Exception:
        clean_queries["outcome"] = None

    # -----------------------------------------------------------------------
    # 2. Clean, Validate and Enrich Spins (History)
    # -----------------------------------------------------------------------
    valid_h_mask = (
        pdf_history["payout"].isin(VALID_PAYOUTS) &
        (pdf_history["tick"] >= 0) &
        pdf_history["episode_id"].notna() &
        pdf_history["machine_id"].notna()
    )
    rejected_h = pdf_history[~valid_h_mask]
    clean_history = pdf_history[valid_h_mask].copy()

    # Deduplicate spins on primary key (episode_id, machine_id, tick)
    dedup_history = clean_history.drop_duplicates(subset=["episode_id", "machine_id", "tick"]).copy()
    duplicates_dropped = len(clean_history) - len(dedup_history)

    # Compute derived columns: payout_index (0..4) and is_win (0/1)
    dedup_history["payout_index"] = dedup_history["payout"].map(PAYOUT_TO_INDEX).astype(int)
    dedup_history["is_win"] = (dedup_history["payout"] > 0).astype(int)

    # Select standard silver_spins columns
    silver_spins_pdf = dedup_history[[
        "episode_id", "machine_id", "tick", "payout", "payout_index", "is_win", "split"
    ]].copy()

    # -----------------------------------------------------------------------
    # 3. Create Episode Summary Dimension (silver_episodes)
    # -----------------------------------------------------------------------
    # Group queries to extract episode level parameters
    ep_queries = clean_queries.groupby(["episode_id", "split"], as_index=False).agg(
        machine_count=("machine_id", "nunique"),
        min_cutoff=("cutoff", "min"),
        max_cutoff=("cutoff", "max"),
        condition=("condition", "first")
    )

    # Group spins to count observed history ticks
    ep_spins = silver_spins_pdf.groupby(["episode_id", "split"], as_index=False).agg(
        total_spins_observed=("tick", "count"),
        total_payout_sum=("payout", "sum"),
        win_count=("is_win", "sum")
    )

    silver_episodes_pdf = ep_queries.merge(ep_spins, on=["episode_id", "split"], how="left")
    silver_episodes_pdf["total_spins_observed"] = silver_episodes_pdf["total_spins_observed"].fillna(0).astype(int)
    silver_episodes_pdf["win_rate"] = (
        silver_episodes_pdf["win_count"] / silver_episodes_pdf["total_spins_observed"].replace(0, 1)
    ).round(4)

    # -----------------------------------------------------------------------
    # 4. Record Quality Audit Metrics
    # -----------------------------------------------------------------------
    quality_metrics = [
        {
            "metric_name": "queries_total_ingested",
            "value": initial_q_count,
            "recorded_at": timestamp_str
        },
        {
            "metric_name": "queries_valid",
            "value": len(clean_queries),
            "recorded_at": timestamp_str
        },
        {
            "metric_name": "queries_rejected",
            "value": len(rejected_q),
            "recorded_at": timestamp_str
        },
        {
            "metric_name": "spins_total_ingested",
            "value": initial_h_count,
            "recorded_at": timestamp_str
        },
        {
            "metric_name": "spins_valid",
            "value": len(silver_spins_pdf),
            "recorded_at": timestamp_str
        },
        {
            "metric_name": "spins_rejected",
            "value": len(rejected_h),
            "recorded_at": timestamp_str
        },
        {
            "metric_name": "spins_duplicates_removed",
            "value": duplicates_dropped,
            "recorded_at": timestamp_str
        },
        {
            "metric_name": "episodes_summarized",
            "value": len(silver_episodes_pdf),
            "recorded_at": timestamp_str
        }
    ]
    pdf_quality = pd.DataFrame(quality_metrics)

    # -----------------------------------------------------------------------
    # 5. Save Silver Tables
    # -----------------------------------------------------------------------
    target_q_name = get_qualified_table_name("silver_queries", catalog, schema)
    target_s_name = get_qualified_table_name("silver_spins", catalog, schema)
    target_e_name = get_qualified_table_name("silver_episodes", catalog, schema)
    target_m_name = get_qualified_table_name("silver_quality_metrics", catalog, schema)

    spark_silver_q = spark.createDataFrame(clean_queries)
    spark_silver_q.write.format("delta").mode("overwrite").saveAsTable(target_q_name)

    spark_silver_s = spark.createDataFrame(silver_spins_pdf)
    spark_silver_s.write.format("delta").mode("overwrite").saveAsTable(target_s_name)

    spark_silver_e = spark.createDataFrame(silver_episodes_pdf)
    spark_silver_e.write.format("delta").mode("overwrite").saveAsTable(target_e_name)

    spark_silver_m = spark.createDataFrame(pdf_quality)
    spark_silver_m.write.format("delta").mode("overwrite").saveAsTable(target_m_name)

    summary = {
        "silver_queries": len(clean_queries),
        "silver_spins": len(silver_spins_pdf),
        "silver_episodes": len(silver_episodes_pdf),
        "silver_quality_metrics": len(pdf_quality),
        "rejected_queries": len(rejected_q),
        "rejected_spins": len(rejected_h),
        "duplicates_dropped": duplicates_dropped
    }

    logger.info("Silver Layer Processing completed successfully: %s", summary)
    return summary


def refresh_views(spark: Any, catalog: Optional[str] = None, schema: Optional[str] = None) -> None:
    """Refreshes analytical SQL views across Bronze and Silver tables."""
    logger.info("Refreshing Lakehouse analytical views in catalog=%s, schema=%s", catalog, schema)
    # Registers or refreshes common analytical views
    view_query = f"""
    CREATE TEMPORARY VIEW IF NOT EXISTS v_machine_summary AS
    SELECT 
        machine_type,
        COUNT(*) as query_count,
        AVG(cutoff) as avg_cutoff
    FROM silver_queries
    GROUP BY machine_type
    """
    try:
        spark.sql(view_query)
        logger.info("Analytical view v_machine_summary refreshed")
    except Exception as e:
        logger.warning("Could not refresh view: %s", e)


def main() -> None:
    parser = argparse.ArgumentParser(description="JAEGERS House Edge Silver Layer Processing")
    parser.add_argument("--catalog", type=str, default="jaegers_dev", help="Unity Catalog catalog name")
    parser.add_argument("--schema", type=str, default="house_edge", help="Unity Catalog schema name")
    parser.add_argument("--action", type=str, default="process", choices=["process", "refresh_views"], help="Pipeline action to run")
    parser.add_argument("--force-mock", action="store_true", help="Force offline mock engine")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    spark = get_spark_session(catalog=args.catalog, schema=args.schema, force_mock=args.force_mock)

    if args.action == "refresh_views":
        refresh_views(spark, args.catalog, args.schema)
    else:
        summary = run_silver_pipeline(spark=spark, catalog=args.catalog, schema=args.schema, force_mock=args.force_mock)
        print(f"Silver Pipeline Summary: {summary}")


if __name__ == "__main__":
    main()
