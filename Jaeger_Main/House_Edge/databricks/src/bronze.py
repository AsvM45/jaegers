"""Bronze Layer Ingestion for JAEGERS House Edge Delta Lakehouse

Reads raw CSVs across splits (train, validation, test), computes SHA-256 cryptographic
checksums for complete data provenance, populates the bronze audit log, and writes
raw records to Bronze Delta tables:
- bronze_queries
- bronze_history
- bronze_labels
- bronze_conditions
- bronze_audit_log
"""

from __future__ import annotations

import argparse
import datetime
import hashlib
import logging
import os
import sys
from typing import Any, Dict, List, Optional, Sequence, Tuple

import pandas as pd

# Support both relative package imports and direct script execution
_SRC_DIR = os.path.dirname(os.path.abspath(__file__))
if _SRC_DIR not in sys.path:
    sys.path.insert(0, _SRC_DIR)

try:
    from .session import get_spark_session
except (ImportError, ValueError):
    from session import get_spark_session

logger = logging.getLogger("jaegers.databricks.bronze")


def compute_file_sha256(filepath: str) -> Tuple[str, int]:
    """Computes the SHA-256 checksum and file size in bytes for a given file."""
    hasher = hashlib.sha256()
    size = 0
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
            size += len(chunk)
    return hasher.hexdigest(), size


def get_qualified_table_name(table_base: str, catalog: Optional[str] = None, schema: Optional[str] = None) -> str:
    """Returns a 3-part or 2-part Unity Catalog table name if configured, or base name."""
    parts = [p for p in (catalog, schema, table_base) if p]
    return ".".join(parts)


def run_bronze_ingest(
    spark: Optional[Any] = None,
    data_dir: str = "public",
    catalog: Optional[str] = None,
    schema: Optional[str] = None,
    splits: Sequence[str] = ("train", "validation", "test"),
    force_mock: bool = False
) -> Dict[str, Any]:
    """Executes the Bronze Medallion ingestion pipeline.

    Args:
        spark: Active SparkSession or MockSparkSession (resolved if None).
        data_dir: Root directory containing raw split subdirectories.
        catalog: Target Unity Catalog catalog name.
        schema: Target Unity Catalog schema name.
        splits: List of dataset splits to ingest.
        force_mock: If True, forces MockSparkSession.

    Returns:
        Dictionary summarizing ingested tables, row counts, and audit records.
    """
    if spark is None:
        spark = get_spark_session(catalog=catalog, schema=schema, force_mock=force_mock)

    logger.info("Starting Bronze Ingestion from root directory: %s", data_dir)
    timestamp_str = datetime.datetime.now(datetime.timezone.utc).isoformat()

    audit_records: List[Dict[str, Any]] = []
    queries_dfs: List[pd.DataFrame] = []
    history_dfs: List[pd.DataFrame] = []
    labels_dfs: List[pd.DataFrame] = []
    conditions_dfs: List[pd.DataFrame] = []

    for split in splits:
        split_dir = os.path.join(data_dir, split)
        if not os.path.isdir(split_dir):
            logger.warning("Split directory not found, skipping: %s", split_dir)
            continue

        # Ingest queries.csv
        q_path = os.path.join(split_dir, "queries.csv")
        if os.path.exists(q_path):
            sha, sz = compute_file_sha256(q_path)
            q_df = pd.read_csv(q_path)
            q_df["split"] = split
            q_df["_source_file"] = os.path.normpath(q_path)
            q_df["_source_sha256"] = sha
            q_df["_ingested_at"] = timestamp_str
            queries_dfs.append(q_df)
            audit_records.append({
                "dataset_name": "queries",
                "split": split,
                "file_path": os.path.normpath(q_path),
                "sha256_checksum": sha,
                "record_count": int(len(q_df)),
                "file_size_bytes": int(sz),
                "ingested_at": timestamp_str,
                "status": "SUCCESS"
            })
            logger.info("Ingested queries [%s]: %d rows (SHA256: %s...)", split, len(q_df), sha[:10])

        # Ingest history.csv
        h_path = os.path.join(split_dir, "history.csv")
        if os.path.exists(h_path):
            sha, sz = compute_file_sha256(h_path)
            h_df = pd.read_csv(h_path)
            h_df["split"] = split
            h_df["_source_file"] = os.path.normpath(h_path)
            h_df["_source_sha256"] = sha
            h_df["_ingested_at"] = timestamp_str
            history_dfs.append(h_df)
            audit_records.append({
                "dataset_name": "history",
                "split": split,
                "file_path": os.path.normpath(h_path),
                "sha256_checksum": sha,
                "record_count": int(len(h_df)),
                "file_size_bytes": int(sz),
                "ingested_at": timestamp_str,
                "status": "SUCCESS"
            })
            logger.info("Ingested history [%s]: %d rows (SHA256: %s...)", split, len(h_df), sha[:10])

        # Ingest labels.csv (optional for test)
        l_path = os.path.join(split_dir, "labels.csv")
        if os.path.exists(l_path):
            sha, sz = compute_file_sha256(l_path)
            l_df = pd.read_csv(l_path)
            l_df["split"] = split
            l_df["_source_file"] = os.path.normpath(l_path)
            l_df["_source_sha256"] = sha
            l_df["_ingested_at"] = timestamp_str
            labels_dfs.append(l_df)
            audit_records.append({
                "dataset_name": "labels",
                "split": split,
                "file_path": os.path.normpath(l_path),
                "sha256_checksum": sha,
                "record_count": int(len(l_df)),
                "file_size_bytes": int(sz),
                "ingested_at": timestamp_str,
                "status": "SUCCESS"
            })
            logger.info("Ingested labels [%s]: %d rows (SHA256: %s...)", split, len(l_df), sha[:10])

        # Ingest conditions.csv (optional for test)
        c_path = os.path.join(split_dir, "conditions.csv")
        if os.path.exists(c_path):
            sha, sz = compute_file_sha256(c_path)
            c_df = pd.read_csv(c_path)
            c_df["split"] = split
            c_df["_source_file"] = os.path.normpath(c_path)
            c_df["_source_sha256"] = sha
            c_df["_ingested_at"] = timestamp_str
            conditions_dfs.append(c_df)
            audit_records.append({
                "dataset_name": "conditions",
                "split": split,
                "file_path": os.path.normpath(c_path),
                "sha256_checksum": sha,
                "record_count": int(len(c_df)),
                "file_size_bytes": int(sz),
                "ingested_at": timestamp_str,
                "status": "SUCCESS"
            })
            logger.info("Ingested conditions [%s]: %d rows (SHA256: %s...)", split, len(c_df), sha[:10])

    summary: Dict[str, Any] = {
        "audit_records": audit_records,
        "tables": {}
    }

    # Write bronze_queries
    if queries_dfs:
        all_q = pd.concat(queries_dfs, ignore_index=True)
        spark_q = spark.createDataFrame(all_q)
        target_name = get_qualified_table_name("bronze_queries", catalog, schema)
        spark_q.write.format("delta").mode("overwrite").saveAsTable(target_name)
        summary["tables"]["bronze_queries"] = len(all_q)

    # Write bronze_history
    if history_dfs:
        all_h = pd.concat(history_dfs, ignore_index=True)
        spark_h = spark.createDataFrame(all_h)
        target_name = get_qualified_table_name("bronze_history", catalog, schema)
        spark_h.write.format("delta").mode("overwrite").saveAsTable(target_name)
        summary["tables"]["bronze_history"] = len(all_h)

    # Write bronze_labels
    if labels_dfs:
        all_l = pd.concat(labels_dfs, ignore_index=True)
        spark_l = spark.createDataFrame(all_l)
        target_name = get_qualified_table_name("bronze_labels", catalog, schema)
        spark_l.write.format("delta").mode("overwrite").saveAsTable(target_name)
        summary["tables"]["bronze_labels"] = len(all_l)

    # Write bronze_conditions
    if conditions_dfs:
        all_c = pd.concat(conditions_dfs, ignore_index=True)
        spark_c = spark.createDataFrame(all_c)
        target_name = get_qualified_table_name("bronze_conditions", catalog, schema)
        spark_c.write.format("delta").mode("overwrite").saveAsTable(target_name)
        summary["tables"]["bronze_conditions"] = len(all_c)

    # Write bronze_audit_log
    if audit_records:
        audit_pdf = pd.DataFrame(audit_records)
        spark_audit = spark.createDataFrame(audit_pdf)
        target_name = get_qualified_table_name("bronze_audit_log", catalog, schema)
        spark_audit.write.format("delta").mode("overwrite").saveAsTable(target_name)
        summary["tables"]["bronze_audit_log"] = len(audit_records)

    logger.info("Bronze Ingestion completed successfully: %s", summary["tables"])
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description="JAEGERS House Edge Bronze Layer Ingestion")
    parser.add_argument("--catalog", type=str, default="jaegers_dev", help="Unity Catalog catalog name")
    parser.add_argument("--schema", type=str, default="house_edge", help="Unity Catalog schema name")
    parser.add_argument("--data-dir", type=str, default="public", help="Directory containing split CSVs")
    parser.add_argument("--splits", nargs="+", default=["train", "validation", "test"], help="Splits to ingest")
    parser.add_argument("--force-mock", action="store_true", help="Force offline mock engine")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    summary = run_bronze_ingest(
        data_dir=args.data_dir,
        catalog=args.catalog,
        schema=args.schema,
        splits=args.splits,
        force_mock=args.force_mock
    )
    print(f"Bronze Ingestion Summary: {summary['tables']}")


if __name__ == "__main__":
    main()
