# Databricks notebook source
# MAGIC %md
# MAGIC # JAEGERS House Edge: Governed Model Benchmark Lane & Ablation Analytics (#86)
# MAGIC 
# MAGIC **Team:** JAEGERS (Antigravity Sponsor & Model Governance Lane)  
# MAGIC **Framework:** Databricks Delta Lakehouse, MLflow Tracking, and Provenance-Isolated Benchmarking  
# MAGIC **Core Capabilities:**
# MAGIC - Read-only ingestion of all frozen House Edge research studies (`HE-09`, `HE-17`, Temporal Experts, Seed Ensembles, Structural Walk-Forward, Causal OOF Stacker Audit, ML Family Screens) and live Databricks Serverless evaluation runs (`Job 888066060424343`).
# MAGIC - Strict evaluation provenance isolation (`sampled_outcome_group_cv` vs `official_public_validation` vs `dev_exposed_public_validation_sampled_outcome`).
# MAGIC - Paired 2,000-sample episode bootstrap 95% confidence interval (`CI95`) hypothesis promotion gating.
# MAGIC - Rare `20x` jackpot calibration bias and 5-class Brier decomposition (`0x`, `1x`, `2x`, `5x`, `20x`).
# MAGIC - Anti-leakage governance flags (`validation_target_exposure` and `historical_signal_policy`).

# COMMAND ----------

# MAGIC %md
# MAGIC ## 1. Initialize Runtime Session & Benchmark Lane Module

# COMMAND ----------

import os
import sys
import pandas as pd

current_dir = os.path.dirname(os.path.abspath(__file__)) if "__file__" in locals() else os.getcwd()
src_dir = os.path.abspath(os.path.join(current_dir, "..", "src"))
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

from session import get_spark_session, get_mlflow
from benchmark_lane import (
    VALID_PROVENANCE_TIERS,
    ingest_repository_benchmarks,
    rank_models_within_provenance,
    assert_single_provenance_comparison,
    materialize_benchmark_tables,
    log_benchmark_study_to_mlflow,
)

spark = get_spark_session(app_name="jaegers_governed_benchmark_notebook")
mlflow = get_mlflow()
print(f"Active Spark Session: {type(spark).__name__}")
print(f"Active MLflow Client: {type(mlflow).__name__}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 2. Ingest Read-Only Repository Benchmark Studies & Live Serverless Runs

# COMMAND ----------

bundle = ingest_repository_benchmarks(include_live_serverless=True)
df_registry = bundle["registry"]
df_comparisons = bundle["comparisons"]
df_episodes = bundle["episodes"]

print(f"Ingested {len(df_registry)} benchmark trial records across {df_registry['study_name'].nunique()} studies.")
print(f"Ingested {len(df_comparisons)} paired bootstrap CI95 comparisons.")
print(f"Ingested {len(df_episodes)} episode-level loss diagnostic records.")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 3. Provenance-Partitioned Rankings (Anti-Conflation Guardrail)
# MAGIC 
# MAGIC Never compare scores across incompatible `evaluation_provenance` tiers:
# MAGIC 1. `sampled_outcome_group_cv`: 5-fold grouped CV against discrete spin outcomes (`mean_brier ~ 0.362`).
# MAGIC 2. `official_public_validation`: Public validation against true 5-element probability distributions (`mean_brier ~ 0.0566`, `official_points ~ 55.12`).
# MAGIC 3. `dev_exposed_public_validation_sampled_outcome`: Public validation queries evaluated against realized discrete spin outcomes (`mean_brier ~ 0.5503`).

# COMMAND ----------

for tier in VALID_PROVENANCE_TIERS:
    ranked = rank_models_within_provenance(df_registry, evaluation_provenance=tier, exclude_target_exposed=True)
    verified_tier = assert_single_provenance_comparison(ranked)
    print(f"\n=== Top 5 Clean Candidates in Provenance Tier: {verified_tier} (Total: {len(ranked)}) ===")
    cols = ["rank_in_provenance", "study_name", "model_name", "model_family", "mean_brier", "official_points", "wall_seconds"]
    print(ranked[cols].head(5).to_string(index=False))

# COMMAND ----------

# MAGIC %md
# MAGIC ## 4. Paired Bootstrap 95% CI Hypothesis Promotion Gate

# COMMAND ----------

supported = df_comparisons[df_comparisons["supported_improvement"] == True]
print(f"Supported improvements clearing 95% bootstrap CI: {len(supported)} / {len(df_comparisons)}")
print(
    df_comparisons[
        ["evaluation_provenance", "study_name", "candidate_model", "reference_model", "metric_type", "mean_delta", "ci95_low", "ci95_high", "supported_improvement"]
    ].head(15).to_string(index=False)
)

# COMMAND ----------

# MAGIC %md
# MAGIC ## 5. Materialize Delta Governance Tables & Sync MLflow Runs

# COMMAND ----------

table_counts = materialize_benchmark_tables(spark=spark, catalog="workspace", schema="house_edge")
print(f"Materialized Delta Governance Tables: {table_counts}")

logged_ids = log_benchmark_study_to_mlflow(
    df_registry,
    study_name="he17_feature_ablation_official",
)
print(f"Logged {len(logged_ids)} official ablation trials to MLflow.")
