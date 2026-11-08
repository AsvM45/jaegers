# Databricks notebook source
# MAGIC %md
# MAGIC # JAEGERS House Edge: Medallion Delta Lakehouse Pipeline Walkthrough
# MAGIC 
# MAGIC **Team:** JAEGERS (Antigravity Sponsor Integration)  
# MAGIC **Architecture:** Medallion Delta Lake (Bronze Raw -> Silver Curated -> Gold Features)  
# MAGIC **Key Innovation:** Cryptographic SHA-256 lineage auditing & strict temporal `< cutoff` isolation preventing lookahead leakage.
# MAGIC 
# MAGIC ---
# MAGIC ### Overview
# MAGIC This notebook demonstrates the end-to-end Medallion architecture for competitive gaming forecasting on Databricks:
# MAGIC 1. **Bronze Layer:** Raw ingestion of queries, history, labels, and conditions across train, validation, and test splits with automated SHA-256 checksum computation and audit logging.
# MAGIC 2. **Silver Layer:** Schema validation, domain constraints enforcement (`payout IN (0, 1, 2, 5, 20)`, `machine_type IN ('steady', 'balanced', 'jackpot')`), duplicate spin removal on `(episode_id, machine_id, tick)`, and episode-level metric rollups.
# MAGIC 3. **Gold Layer:** Distributed temporal feature engineering enforcing `history.tick < query.cutoff` across 10 historical feature groups (468 features) plus query features (3 features), producing 471 canonical features with 100% mathematical parity to offline research models.

# COMMAND ----------

# MAGIC %md
# MAGIC ## 1. Session Initialization & Imports
# MAGIC 
# MAGIC Resolves the active SparkSession or seamlessly falls back to the zero-dependency offline mock engine if executed outside a Databricks cluster.

# COMMAND ----------

import os
import sys
from pathlib import Path

# Add databricks source directory to system path
current_dir = os.path.dirname(os.path.abspath(__file__)) if "__file__" in locals() else os.getcwd()
src_dir = os.path.abspath(os.path.join(current_dir, "..", "src"))
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

from session import get_spark_session
from bronze import run_bronze_ingest
from silver import run_silver_pipeline
from gold import run_gold_pipeline, FEATURE_NAMES

spark = get_spark_session()
print(f"Active Spark Engine: {type(spark).__name__}")
print(f"Total Canonical Features: {len(FEATURE_NAMES)}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 2. Bronze Ingestion & Cryptographic Provenance
# MAGIC 
# MAGIC Ingests all raw split CSVs (`train`, `validation`, `test`) into Delta tables and records file hashes, record counts, and timestamps in `bronze_audit_log`.

# COMMAND ----------

# Resolve raw data path (checks Databricks DBFS, Unity Catalog Volumes, or local workspace fallback)
data_dir = "public" if os.path.isdir("public") else os.path.join("..", "..", "..", "public")
if not os.path.isdir(data_dir):
    data_dir = "Jaeger_Main/House_Edge/public"

print(f"Ingesting raw assets from: {data_dir}")
bronze_summary = run_bronze_ingest(spark, data_dir=data_dir, splits=["train", "validation", "test"])

print(f"Ingested Tables: {list(bronze_summary['tables'].keys())}")
print(f"Audit Log Records: {len(bronze_summary['audit_records'])}")

# Display the Bronze audit ledger
df_audit = spark.table("bronze_audit_log")
if hasattr(df_audit, "display"):
    display(df_audit)
else:
    print(df_audit.toPandas()[["split", "dataset_name", "record_count", "sha256_checksum", "status"]])

# COMMAND ----------

# MAGIC %md
# MAGIC ## 3. Silver Layer Cleaning, Domain Validation & Deduplication
# MAGIC 
# MAGIC Applies business logic rules to the raw data:
# MAGIC - Validates valid payout multipliers: `payout IN (0, 1, 2, 5, 20)`
# MAGIC - Validates machine types: `machine_type IN ('steady', 'balanced', 'jackpot')`
# MAGIC - Validates query signals: `signal IN (-1, 0, 1)`
# MAGIC - Deduplicates multiple spin records on `(episode_id, machine_id, tick)`
# MAGIC - Derives numeric payout indices (`0..4`) and binary win flags (`is_win`)
# MAGIC - Writes curated `silver_queries`, `silver_spins`, `silver_episodes`, and `silver_quality_metrics`.

# COMMAND ----------

silver_summary = run_silver_pipeline(spark)
print(f"Silver Queries Validated: {silver_summary['silver_queries']} (Rejected: {silver_summary['rejected_queries']})")
print(f"Silver Spins Validated: {silver_summary['silver_spins']} (Duplicates Dropped: {silver_summary['duplicates_dropped']})")
print(f"Silver Episodes Summarized: {silver_summary['silver_episodes']}")

df_quality = spark.table("silver_quality_metrics")
if hasattr(df_quality, "display"):
    display(df_quality)
else:
    print(df_quality.toPandas())

# COMMAND ----------

# MAGIC %md
# MAGIC ## 4. Gold Feature Engineering with Strict Temporal Cutoff Isolation
# MAGIC 
# MAGIC Transforms cleaned Silver data into Gold feature vectors. For every query at cutoff tick $T$, history is filtered strictly where $\text{tick} < T$.
# MAGIC Grouped Map Pandas UDF (`applyInPandas`) executes across episode partitions in parallel with zero shuffle overhead.

# COMMAND ----------

gold_summary = run_gold_pipeline(spark)
print(f"Gold Features Rows Generated: {gold_summary['total_queries']}")
print(f"Gold Feature Dimensions: {gold_summary['feature_count']} features (Target: 471)")

df_gold = spark.table("gold_features")
if hasattr(df_gold, "display"):
    display(df_gold)
else:
    pdf_sample = df_gold.toPandas().head(5)
    print(f"Gold Sample shape: {pdf_sample.shape}")
    print(f"Sample Query IDs: {pdf_sample['query_id'].tolist()}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 5. Pipeline Verification & Data Governance Summary
# MAGIC 
# MAGIC The Medallion Delta Lakehouse pipeline is now complete and fully governed:
# MAGIC - **Bronze:** Immutable raw record capture with cryptographic SHA-256 lineage.
# MAGIC - **Silver:** Enforced schema types, domain range checks, and primary-key deduplication.
# MAGIC - **Gold:** Leak-free, past-only feature vectors partitioned by episode for optimal query and training performance.
