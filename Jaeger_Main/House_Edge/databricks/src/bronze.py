"""Bronze Layer Ingestion for JAEGERS House Edge Delta Lakehouse

Reads raw CSVs across splits (train, validation, test), enforces complete input coverage,
computes SHA-256 cryptographic checksums for complete data provenance, populates the
bronze audit log, and writes raw records to Bronze Delta tables:
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
import inspect
import logging
import os
import sys
from typing import Any, Dict, List, Optional, Sequence, Tuple

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
                if os.path.isfile(os.path.join(cand_dir, "session.py")) or os.path.isfile(os.path.join(cand_dir, "bronze.py")):
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
    from .session import assert_real_spark, get_spark_session, is_live_required
except (ImportError, ValueError):
    from session import assert_real_spark, get_spark_session, is_live_required

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
    force_mock: bool = False,
    require_live: bool = False,
    strict_splits: bool = True,
) -> Dict[str, Any]:
    """Executes the Bronze Medallion ingestion pipeline.

    Enforces complete input coverage across all requested splits: missing split
    directories or missing required split files raise FileNotFoundError/ValueError
    rather than silently skipping.
    """
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

    if not splits:
        raise ValueError("At least one split must be specified for Bronze ingestion")

    if not os.path.isdir(data_dir):
        raise FileNotFoundError(f"Bronze input root directory does not exist: {data_dir}")

    logger.info("Starting Bronze Ingestion from root directory: %s (splits=%s)", data_dir, list(splits))
    timestamp_str = datetime.datetime.now(datetime.timezone.utc).isoformat()

    audit_records: List[Dict[str, Any]] = []
    queries_dfs: List[pd.DataFrame] = []
    history_dfs: List[pd.DataFrame] = []
    labels_dfs: List[pd.DataFrame] = []
    conditions_dfs: List[pd.DataFrame] = []

    for split in splits:
        split_dir = os.path.join(data_dir, split)
        if not os.path.isdir(split_dir):
            if strict_splits:
                raise FileNotFoundError(f"Required split directory not found: {split_dir}")
            logger.warning("Split directory not found, skipping: %s", split_dir)
            continue

        # 1. Ingest queries.csv (mandatory for every split)
        q_path = os.path.join(split_dir, "queries.csv")
        if not os.path.isfile(q_path):
            raise FileNotFoundError(f"Required file queries.csv missing for split '{split}': {q_path}")
        sha, sz = compute_file_sha256(q_path)
        q_df = pd.read_csv(q_path)
        if len(q_df) == 0:
            raise ValueError(f"queries.csv is empty for split '{split}': {q_path}")
        q_df["query_id"] = q_df["query_id"].astype(str)
        q_df["episode_id"] = q_df["episode_id"].astype(str)
        q_df["machine_id"] = q_df["machine_id"].astype(str)
        q_df["machine_type"] = q_df["machine_type"].astype(str)
        q_df["signal"] = q_df["signal"].astype("int64")
        q_df["cutoff"] = q_df["cutoff"].astype("int64")
        q_df["split"] = str(split)
        q_df["_source_file"] = os.path.normpath(q_path)
        q_df["_source_sha256"] = sha
        q_df["_ingested_at"] = timestamp_str
        queries_dfs.append(q_df)
        audit_records.append({
            "dataset_name": "queries",
            "split": str(split),
            "file_path": os.path.normpath(q_path),
            "sha256_checksum": sha,
            "record_count": int(len(q_df)),
            "file_size_bytes": int(sz),
            "ingested_at": timestamp_str,
            "status": "SUCCESS",
        })
        logger.info("Ingested queries [%s]: %d rows (SHA256: %s...)", split, len(q_df), sha[:10])

        # 2. Ingest history.csv (mandatory for every split)
        h_path = os.path.join(split_dir, "history.csv")
        if not os.path.isfile(h_path):
            raise FileNotFoundError(f"Required file history.csv missing for split '{split}': {h_path}")
        sha, sz = compute_file_sha256(h_path)
        h_df = pd.read_csv(h_path)
        if len(h_df) == 0:
            raise ValueError(f"history.csv is empty for split '{split}': {h_path}")
        h_df["episode_id"] = h_df["episode_id"].astype(str)
        h_df["machine_id"] = h_df["machine_id"].astype(str)
        h_df["tick"] = h_df["tick"].astype("int64")
        h_df["payout"] = h_df["payout"].astype("int64")
        h_df["split"] = str(split)
        h_df["_source_file"] = os.path.normpath(h_path)
        h_df["_source_sha256"] = sha
        h_df["_ingested_at"] = timestamp_str
        history_dfs.append(h_df)
        audit_records.append({
            "dataset_name": "history",
            "split": str(split),
            "file_path": os.path.normpath(h_path),
            "sha256_checksum": sha,
            "record_count": int(len(h_df)),
            "file_size_bytes": int(sz),
            "ingested_at": timestamp_str,
            "status": "SUCCESS",
        })
        logger.info("Ingested history [%s]: %d rows (SHA256: %s...)", split, len(h_df), sha[:10])

        # 3. Ingest labels.csv (mandatory for train/validation when strict_splits=True; optional for test)
        l_path = os.path.join(split_dir, "labels.csv")
        if os.path.isfile(l_path):
            sha, sz = compute_file_sha256(l_path)
            l_df = pd.read_csv(l_path)
            l_df["query_id"] = l_df["query_id"].astype(str)
            l_df["outcome"] = l_df["outcome"].astype("int64")
            l_df["split"] = str(split)
            l_df["_source_file"] = os.path.normpath(l_path)
            l_df["_source_sha256"] = sha
            l_df["_ingested_at"] = timestamp_str
            labels_dfs.append(l_df)
            audit_records.append({
                "dataset_name": "labels",
                "split": str(split),
                "file_path": os.path.normpath(l_path),
                "sha256_checksum": sha,
                "record_count": int(len(l_df)),
                "file_size_bytes": int(sz),
                "ingested_at": timestamp_str,
                "status": "SUCCESS",
            })
            logger.info("Ingested labels [%s]: %d rows (SHA256: %s...)", split, len(l_df), sha[:10])
        elif strict_splits and split in ("train", "validation"):
            raise FileNotFoundError(f"Required file labels.csv missing for labeled split '{split}': {l_path}")

        # 4. Ingest conditions.csv (mandatory for train/validation when strict_splits=True; optional for test)
        c_path = os.path.join(split_dir, "conditions.csv")
        if os.path.isfile(c_path):
            sha, sz = compute_file_sha256(c_path)
            c_df = pd.read_csv(c_path)
            c_df["query_id"] = c_df["query_id"].astype(str)
            c_df["condition"] = c_df["condition"].astype(str)
            c_df["split"] = str(split)
            c_df["_source_file"] = os.path.normpath(c_path)
            c_df["_source_sha256"] = sha
            c_df["_ingested_at"] = timestamp_str
            conditions_dfs.append(c_df)
            audit_records.append({
                "dataset_name": "conditions",
                "split": str(split),
                "file_path": os.path.normpath(c_path),
                "sha256_checksum": sha,
                "record_count": int(len(c_df)),
                "file_size_bytes": int(sz),
                "ingested_at": timestamp_str,
                "status": "SUCCESS",
            })
            logger.info("Ingested conditions [%s]: %d rows (SHA256: %s...)", split, len(c_df), sha[:10])
        elif strict_splits and split in ("train", "validation"):
            raise FileNotFoundError(f"Required file conditions.csv missing for labeled split '{split}': {c_path}")

    if not queries_dfs or not history_dfs:
        raise RuntimeError("Bronze ingestion produced empty queries or history datasets")

    summary: Dict[str, Any] = {
        "audit_records": audit_records,
        "tables": {},
    }

    # Write bronze_queries
    all_q = pd.concat(queries_dfs, ignore_index=True)
    spark_q = spark.createDataFrame(all_q)
    target_name = get_qualified_table_name("bronze_queries", catalog, schema)
    spark_q.write.format("delta").mode("overwrite").saveAsTable(target_name)
    summary["tables"]["bronze_queries"] = int(len(all_q))

    # Write bronze_history
    all_h = pd.concat(history_dfs, ignore_index=True)
    spark_h = spark.createDataFrame(all_h)
    target_name = get_qualified_table_name("bronze_history", catalog, schema)
    spark_h.write.format("delta").mode("overwrite").saveAsTable(target_name)
    summary["tables"]["bronze_history"] = int(len(all_h))

    # Write bronze_labels
    if labels_dfs:
        all_l = pd.concat(labels_dfs, ignore_index=True)
        spark_l = spark.createDataFrame(all_l)
        target_name = get_qualified_table_name("bronze_labels", catalog, schema)
        spark_l.write.format("delta").mode("overwrite").saveAsTable(target_name)
        summary["tables"]["bronze_labels"] = int(len(all_l))

    # Write bronze_conditions
    if conditions_dfs:
        all_c = pd.concat(conditions_dfs, ignore_index=True)
        spark_c = spark.createDataFrame(all_c)
        target_name = get_qualified_table_name("bronze_conditions", catalog, schema)
        spark_c.write.format("delta").mode("overwrite").saveAsTable(target_name)
        summary["tables"]["bronze_conditions"] = int(len(all_c))

    # Write bronze_audit_log
    audit_pdf = pd.DataFrame(audit_records)
    spark_audit = spark.createDataFrame(audit_pdf)
    target_name = get_qualified_table_name("bronze_audit_log", catalog, schema)
    spark_audit.write.format("delta").mode("overwrite").saveAsTable(target_name)
    summary["tables"]["bronze_audit_log"] = int(len(audit_records))

    logger.info("Bronze Ingestion completed successfully: %s", summary["tables"])
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description="JAEGERS House Edge Bronze Layer Ingestion")
    parser.add_argument("--catalog", type=str, default="jaegers_dev", help="Unity Catalog catalog name")
    parser.add_argument("--schema", type=str, default="house_edge", help="Unity Catalog schema name")
    parser.add_argument("--data-dir", type=str, default="public", help="Directory containing split CSVs")
    parser.add_argument("--splits", nargs="+", default=["train", "validation", "test"], help="Splits to ingest")
    parser.add_argument("--force-mock", action="store_true", help="Force offline mock engine")
    parser.add_argument("--require-live", action="store_true", help="Reject mock engine fallback")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    summary = run_bronze_ingest(
        data_dir=args.data_dir,
        catalog=args.catalog,
        schema=args.schema,
        splits=args.splits,
        force_mock=args.force_mock,
        require_live=args.require_live,
    )
    print(f"Bronze Ingestion Summary: {summary['tables']}")


if __name__ == "__main__":
    main()
