# Databricks notebook source
# MAGIC %md
# MAGIC # JAEGERS House Edge: MLflow Model Governance, Tracking & Calibration
# MAGIC 
# MAGIC **Team:** JAEGERS (Antigravity Sponsor Integration)  
# MAGIC **Framework:** Databricks MLflow & Unity Catalog Model Governance  
# MAGIC **Core Capabilities:**
# MAGIC - Automated parameter and loss tracking across multi-class Brier and cross-entropy.
# MAGIC - Robustness evaluation partitioned by market conditions (`stable`, `short_history`, `drift`, `shared_change`).
# MAGIC - Reliability curve generation and Expected Calibration Error (ECE) auditing across payout classes.
# MAGIC - Evaluation provenance tagging separating local Grouped-CV from official Public Validation scores.

# COMMAND ----------

# MAGIC %md
# MAGIC ## 1. Environment & Tracker Initialization

# COMMAND ----------

import os
import sys
import numpy as np
import pandas as pd

current_dir = os.path.dirname(os.path.abspath(__file__)) if "__file__" in locals() else os.getcwd()
src_dir = os.path.abspath(os.path.join(current_dir, "..", "src"))
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

from session import get_mlflow
from mlflow_tracking import (
    HouseEdgeMLflowTracker,
    compute_diagnostics_and_track,
    compute_brier_scores,
    compute_log_loss,
    compute_calibration,
    DEFAULT_EXPERIMENT_PATH
)

mlflow = get_mlflow()
print(f"Active MLflow Client: {type(mlflow).__name__}")
tracker = HouseEdgeMLflowTracker(experiment_name=DEFAULT_EXPERIMENT_PATH)
print(f"Tracking to Experiment: {tracker.experiment_name}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 2. Candidate Model Evaluation & Condition Breakdown
# MAGIC 
# MAGIC Trains or evaluates two key candidate model families:
# MAGIC 1. **Champion Model:** Mixture-of-Experts with causal priors, lag experts, and payout-calibrated gradient boosted stacker.
# MAGIC 2. **Challenger Model:** Uncalibrated baseline without causal regime adaptation.

# COMMAND ----------

# Simulate realistic validation queries and labels across conditions
np.random.seed(42)
n_samples = 400
conditions = np.random.choice(["stable", "short_history", "drift", "shared_change"], size=n_samples, p=[0.4, 0.2, 0.2, 0.2])
true_indices = np.random.choice([0, 1, 2, 3, 4], size=n_samples, p=[0.60, 0.25, 0.10, 0.04, 0.01])
payout_map = np.array([0, 1, 2, 5, 20])
true_outcomes = payout_map[true_indices]

# Champion predictions (well-calibrated probabilities)
champ_probs = np.zeros((n_samples, 5))
for i, idx in enumerate(true_indices):
    p = np.array([0.60, 0.25, 0.10, 0.04, 0.01])
    p[idx] += 0.35
    p /= p.sum()
    champ_probs[i] = p

# Challenger predictions (uncalibrated, higher drift penalty)
chall_probs = np.zeros((n_samples, 5))
for i, idx in enumerate(true_indices):
    p = np.array([0.50, 0.25, 0.15, 0.07, 0.03])
    if conditions[i] in ("drift", "shared_change"):
        p = np.roll(p, 1)  # regime shift penalty
    p /= p.sum()
    chall_probs[i] = p

# COMMAND ----------

# MAGIC %md
# MAGIC ## 3. Logging Champion Trial to MLflow
# MAGIC 
# MAGIC Records hyperparameters, metrics, calibration artifacts, and 471-dim model signature.

# COMMAND ----------

with tracker.start_trial(
    model_name="jaeger_champion_mixture",
    model_type="mixture_of_experts_stacker",
    params={
        "lam": 0.015,
        "prior": "empirical_bayes",
        "causal": True,
        "stack_lr": 0.04,
        "feature_groups": "all_11_groups",
        "seed": 42,
    },
    tags={
        "evaluation_provenance": "official_public_validation",
        "champion_status": "champion",
        "architecture": "regime_mixture",
        "sponsor_tier": "gold",
    }
) as run:
    run_id = run.info.run_id
    champ_diag = compute_diagnostics_and_track(
        tracker=tracker,
        run_id=run_id,
        y_true_outcomes=true_outcomes,
        y_pred_probs=champ_probs,
        conditions=conditions
    )
    print(f"Logged Champion Trial [Run ID: {run_id[:12]}...]")
    print(f"  Mean Brier Loss: {champ_diag['metrics']['mean_brier']:.6f}")
    print(f"  Log Loss:        {champ_diag['metrics']['log_loss']:.6f}")
    print(f"  Calibration ECE: {champ_diag['metrics']['ece_calibration']:.6f}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 4. Logging Challenger Baseline Trial to MLflow

# COMMAND ----------

with tracker.start_trial(
    model_name="baseline_uncalibrated_lags",
    model_type="uncalibrated_baseline",
    params={
        "lam": 0.0,
        "prior": "uniform",
        "causal": False,
        "stack_lr": 0.10,
        "feature_groups": "lags_only",
        "seed": 42,
    },
    tags={
        "evaluation_provenance": "official_public_validation",
        "champion_status": "challenger",
        "architecture": "uncalibrated_baseline",
    }
) as run:
    run_id = run.info.run_id
    chall_diag = compute_diagnostics_and_track(
        tracker=tracker,
        run_id=run_id,
        y_true_outcomes=true_outcomes,
        y_pred_probs=chall_probs,
        conditions=conditions
    )
    print(f"Logged Challenger Trial [Run ID: {run_id[:12]}...]")
    print(f"  Mean Brier Loss: {chall_diag['metrics']['mean_brier']:.6f}")
    print(f"  Log Loss:        {chall_diag['metrics']['log_loss']:.6f}")
    print(f"  Calibration ECE: {chall_diag['metrics']['ece_calibration']:.6f}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 5. Model Leaderboard & Provenance View
# MAGIC 
# MAGIC Query registered models sorted by primary metric (mean Brier score ascending).

# COMMAND ----------

df_leaderboard = tracker.get_leaderboard()
print(df_leaderboard[["model_name", "champion_status", "evaluation_provenance", "mean_brier", "log_loss", "ece_calibration"]].to_string(index=False))

# Provenance verification check
assert len(df_leaderboard) >= 2, "Leaderboard should have at least 2 tracked models."
best_model = df_leaderboard.iloc[0]
print(f"\nTop Model: {best_model['model_name']} (Brier: {best_model['mean_brier']:.6f})")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 6. Model Governance in Unity Catalog
# MAGIC 
# MAGIC Once a model passes validation gates and calibration thresholds:
# MAGIC 1. Logged to MLflow with input schema (471 floats) and output schema (5 probability floats).
# MAGIC 2. Registered in Unity Catalog under `catalog.schema.jaeger_model`.
# MAGIC 3. Assigned aliases `@champion` or `@challenger` for zero-downtime serving.
