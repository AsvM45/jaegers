# JAEGERS House Edge — Governed Model Benchmark Lane & Stage-A/B/C Technical Audit (#86)

**Engineering Owner:** Google Antigravity (`agent/antigravity-he86-benchmark`)  
**Linked Issues:** [#14](https://github.com/AsvM45/jaegers/issues/14) (Stage A), [#86](https://github.com/AsvM45/jaegers/issues/86) (Stages A–C), [#89](https://github.com/AsvM45/jaegers/issues/89) (Final Integration)  
**Target Workspace:** AWS Databricks Serverless (`workspace.house_edge`, Job ID `50563036183908`, Experiment ID `4062806637201469`)  

---

## 1. Stage A — Live Databricks Engineering & Provenance Audit (#14)

### 1.1 Stagewise and Full 6-Task DAG Execution Ledger
All six Serverless Python tasks in `house_edge_medallion_pipeline` (`Job ID: 50563036183908`) were executed both individually (stagewise validation) and as a complete end-to-end 6-task DAG (`Parent Run ID: 888066060424343`, total wall-clock duration `242,789 ms` = `4m 02.8s`) under `DATABRICKS_REQUIRE_LIVE=1` (explicitly rejecting `MockSparkSession` and `MockMLflow`):

| Task Key | Stagewise Run ID | Full DAG Task Run ID | Start (UTC, 2026-04-12) | End (UTC, 2026-04-12) | Task Duration (`ms`) | Script Wall (`s`) | Status |
| :--- | :--- | :--- | :--- | :--- | ---: | ---: | :--- |
| `bronze_ingestion` | `925919734693613` | `1068285881427297` | `11:36:14` | `11:36:45` | `30,860` | `14.12` | `TERMINATED SUCCESS` |
| `silver_normalization` | `108955288790552` | `462109200643361` | `11:36:56` | `11:37:44` | `48,300` | `26.41` | `TERMINATED SUCCESS` |
| `gold_feature_extraction` | `579892603954941` | `721483717655508` | `11:37:52` | `11:38:59` | `67,385` | `49.85` | `TERMINATED SUCCESS` |
| `verify_feature_parity` | `617153822117765` | `542657622420507` | `11:39:05` | `11:39:51` | `46,000` | `34.19` | `TERMINATED SUCCESS` |
| `mlflow_evaluation_tracking` | `12718307334842` | `845188882182422` | `11:39:05` | `11:39:48` | `42,970` | `30.89` | `TERMINATED SUCCESS` |
| `refresh_monitoring_views` | `253019094752490` | `392260434307954` | `11:39:57` | `11:40:13` | `16,581` | `6.14` | `TERMINATED SUCCESS` |

### 1.2 Root-Cause Resolution Ledger (Failed Debug Runs -> Live Fixes)

| Failed Run ID | Task Key | Exact Error / Exception | Root Cause & Engineering Fix |
| :--- | :--- | :--- | :--- |
| `332344859953641` | `bronze_ingestion` | `NameError: name '__file__' is not defined` | Databricks Serverless executes `spark_python_task` via `exec(compile(...))` without defining `__file__`. Fixed across all task scripts (`bronze.py`, `silver.py`, `gold.py`, `parity.py`, `mlflow_tracking.py`, `benchmark_lane.py`) via `_resolve_src_dir()`. |
| `552742672000825` | `verify_feature_parity` | `SystemExit: 0` | `parity.py` called `sys.exit(0)` on `PASSED`, which the Serverless IPython kernel raises as an uncaught exception. Removed `sys.exit(0)` on success; raises `RuntimeError` only when `res.status != "PASSED"`. |
| `350393923129904` | `mlflow_evaluation_tracking` | `AnalysisException: [CONFIG_NOT_AVAILABLE.WITHOUT_SUGGESTION] Configuration spark.mlflow.modelRegistryUri is not available. SQLSTATE: 42K0I` | On Serverless Spark Connect, `MlflowClient()` queries `spark.conf.get("spark.mlflow.modelRegistryUri")`, which is blocked on Spark Connect. Fixed in `session.py` (`get_mlflow`) by explicitly setting `MLFLOW_TRACKING_URI="databricks"` and `MLFLOW_REGISTRY_URI="databricks-uc"`. |

### 1.3 Technical Clarifications (Numerical Parity, Spark Shuffle Semantics & Evaluation Provenance)
1. **Numerical vs. Bitwise Parity (`gold_parity_audit`):**
   - Across `150` live validation queries × `471` canonical features (`70,650` floating-point cells), `verify_feature_parity` recorded `max_abs_difference = 0.0`, `mean_abs_difference = 0.0`, and `temporal_boundary_pass = true` because both the PySpark `applyInPandas` worker and the local reference invoke the exact same deterministic NumPy/Python feature kernel (`extract_query_features_471`) on identical `tick < cutoff` sorted spin arrays. The gating criterion is `max_abs_difference <= 1e-6`.
2. **Distributed Shuffle Semantics in `src/gold.py`:**
   - `gold.py` joins `silver_queries` with `silver_spins` on `(episode_id, split)` under the predicate `(F.col("s.tick") < F.col("q.cutoff")) | F.col("s.tick").isNull()` (preserving zero-spin queries) and dispatches `groupBy(query_cols).applyInPandas(...)`. On Spark Connect, this materializes one spin group per query across workers (`564,000` spins -> `3,072` query groups in `49.85s`).
3. **Evaluation Provenance Separation (Why Three Distinct Tiers Exist):**
   - **`sampled_outcome_group_cv` (Mean Brier ~`0.3622`–`0.5705`):** 4-fold or 5-fold grouped cross-validation on `train` (`768` queries across `96` episodes) scored against **realized discrete spin outcomes** (`outcome in {0, 1, 2, 5, 20}`, one-hot 5-vector). Because a single discrete spin has irreducible multinomial variance $\sum_k p_k(1 - p_k) \approx 0.305$, even an oracle probability predictor has expected sampled-outcome Brier around `0.305`–`0.360`.
   - **`official_public_validation` (Mean Brier / Loss Ratio ~`0.0566`–`0.0885`, Official Points ~`55.12`):** Public validation (`768` queries across `96` episodes) scored against the **true 5-element ground-truth probability vectors** `(p_0, p_1, p_2, p_5, p_20)` from `validation/labels.csv`. There is zero realization noise in the target vector, so Brier scores are ~`0.0566` and condition-normalized loss ratios are ~`0.067`–`0.117`.
   - **`dev_exposed_public_validation_sampled_outcome` (Mean Brier ~`0.5503`–`0.5569`):** Live Databricks Serverless baseline models (`empirical_bayes_k50`, `regime_dirichlet_k35`, `uncalibrated_empirical_k1`) fit on `silver_queries (split='train')` and scored against the **discrete `outcome` column** of `silver_queries (split='validation')`.
   - **Governance Rule:** `benchmark_lane.py` (`rank_models_within_provenance` and `assert_single_provenance_comparison`) strictly partitions all rankings and paired comparisons by `evaluation_provenance` and raises a `ValueError` if mixed tiers are compared without partitioning.

---

## 2. Stage B — Governed Cross-Study Model Benchmark Synthesis (#86)

`Jaeger_Main/House_Edge/databricks/src/benchmark_lane.py` ingests all **12 frozen repository benchmark JSON artifacts** plus the **3 live Databricks Serverless MLflow evaluations** (`110` total trial records across `14` study partitions, `75` paired bootstrap `CI95` comparisons, and `1,968` episode-level loss records) in strictly read-only mode.

### 2.1 Provenance Tier 1: `official_public_validation` (True 5-Vector Distribution Target, 768 Validation Queries)

| Rank | Study Name | Candidate Model | Model Family | Official Points | Condition Mean Loss Ratio | Stable Ratio | Short-History Ratio | Drift Ratio | Shared-Change Ratio | Rare 20x `corr_p20` | Target Exposed? | Wall (`s`) |
| ---: | :--- | :--- | :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | :---: | ---: |
| 1 | `qa_causal_stacker_audit_official` | `prior_only` | `causal_oof_stacker` | **55.1338** | `0.088262` | `0.0668` | `0.1167` | `0.0920` | `0.0775` | — | `False` | `40.7` |
| 2 | `he17_feature_ablation_official` | `champion` | `jaeger_regime_mixture` | **55.1216** | `0.088502` | `0.0673` | `0.1170` | `0.0923` | `0.0774` | `0.9718` | `False` | `57.4` |
| 3 | `he_temporal_blend_sweep` | `blend_linear` | `legacy_temporal_blend` | **55.1216** | `0.088502` | `0.0673` | `0.1170` | `0.0923` | `0.0774` | `0.9718` | `False` | `0.0` |
| 4 | `he17_feature_ablation_official` | `nosig` | `jaeger_regime_mixture` | **55.0001** | `0.090908` | `0.0672` | `0.1223` | `0.0945` | `0.0796` | — | `False` | `56.8` |
| 5 | `qa_causal_stacker_audit_official` | `regime_only` | `causal_oof_stacker` | **54.9262** | `0.092375` | `0.0695` | `0.1263` | `0.0935` | `0.0801` | — | `False` | `47.8` |
| 6 | `qa_causal_stacker_audit_official` | `causal_all_nohead` | `causal_oof_stacker` | **54.8358** | `0.094176` | `0.0692` | `0.1295` | `0.0970` | `0.0810` | — | `False` | `43.9` |
| 7 | `he17_feature_ablation_official` | `no_expert_prior` | `jaeger_regime_mixture` | **54.6969** | `0.096955` | `0.0696` | `0.1505` | `0.0926` | `0.0752` | — | `False` | `60.4` |
| 8 | `he17_feature_ablation_official` | `no_short_history_prior` | `jaeger_regime_mixture` | **54.6379** | `0.098139` | `0.0688` | `0.1502` | `0.0937` | `0.0799` | — | `False` | `59.2` |
| 9 | `qa_causal_stacker_audit_official` | `causal_all` | `causal_oof_stacker` | **54.6099** | `0.098701` | `0.0773` | `0.1270` | `0.1055` | `0.0850` | — | `False` | `53.3` |
| 10 | `he17_feature_ablation_official` | `train_size_regimes` | `jaeger_regime_mixture` | **54.4922** | `0.101076` | `0.0826` | `0.1230` | `0.1113` | `0.0875` | — | `False` | `47.5` |
| 11 | `he17_feature_ablation_official` | `no_peer_evidence` | `jaeger_regime_mixture` | **54.4605** | `0.101717` | `0.0717` | `0.1657` | `0.0880` | `0.0815` | — | `False` | `60.1` |
| 12 | `he17_feature_ablation_official` | `binary_categories_only` | `jaeger_regime_mixture` | **54.0261** | `0.110575` | `0.1042` | `0.1196` | `0.1104` | `0.1080` | — | `False` | `38.1` |
| 13 | `he17_feature_ablation_official` | `no_size_experts` | `jaeger_regime_mixture` | **53.6833** | `0.117666` | `0.1120` | `0.1306` | `0.1229` | `0.1052` | — | `False` | `40.7` |
| 14 | `he17_feature_ablation_official` | `faster_forgetting` | `jaeger_regime_mixture` | **53.4714** | `0.122094` | `0.1012` | `0.1256` | `0.1062` | `0.1553` | — | `False` | `59.1` |
| 15 | `he17_feature_ablation_official` | `nostack` | `jaeger_regime_mixture` | **52.8362** | `0.135585` | `0.1196` | `0.1845` | `0.1247` | `0.1136` | — | `False` | `31.7` |
| 16 | `he_temporal_expert_official` | `stat_factorized_regime` | `temporal_expert_mixture` | **48.4310** | `0.219442` | `0.1558` | `0.3385` | `0.2202` | `0.1633` | `0.8551` | `False` | `15.4` |
| 17 | `he_temporal_expert_official` | `stat_markov (HE-09)` | `temporal_expert_mixture` | **43.9750** | `0.364411` | `0.3238` | `0.4700` | `0.3648` | `0.2990` | `0.5049` | `False` | `13.9` |
| 18 | `he17_feature_ablation_official` | `slower_forgetting` | `jaeger_regime_mixture` | **39.3269** | `0.525674` | `0.1587` | `0.1437` | `0.8795` | `0.9208` | — | `False` | `59.0` |
| 19 | `he17_feature_ablation_official` | `single_lag_only` | `jaeger_regime_mixture` | **32.1148** | `0.868298` | `0.8364` | `0.9858` | `0.8512` | `0.7998` | — | `False` | `11.9` |
| 20 | `he_temporal_expert_official` | `stat_temporal_hmm` | `temporal_expert_mixture` | **31.8459** | `0.884075` | `0.8685` | `0.9481` | `0.9175` | `0.8022` | `0.6496` | `False` | `43.7` |
| 21 | `he17_feature_ablation_official` | `control_shuffled_stack_labels` | `jaeger_regime_mixture` | **27.7788** | `1.159921` | `1.1802` | `1.1794` | `1.1779` | `1.1023` | — | `False` | `46.2` |

### 2.2 Provenance Tier 2: `sampled_outcome_group_cv` (Discrete Realized Spin Target, Clean Non-Target-Exposed Candidates)

| Rank | Study Name | Candidate Model | Model Family | Mean Sampled Brier | Stable Brier | Short-History Brier | Drift Brier | Shared-Change Brier | Target Exposed? | Signal Policy | Wall (`s`) |
| ---: | :--- | :--- | :--- | ---: | ---: | ---: | ---: | ---: | :---: | :--- | ---: |
| 1 | `qa_causal_stacker_audit_cv` | `qa_prior_only` | `causal_oof_stacker` | **0.362200** | `0.3665` | `0.4454` | `0.3202` | `0.3168` | `False` | `strict_tick_lt_cutoff` | `113.10` |
| 2 | `qa_causal_stacker_audit_cv` | `qa_causal_all` | `causal_oof_stacker` | **0.362947** | `0.3650` | `0.4543` | `0.3169` | `0.3155` | `False` | `strict_tick_lt_cutoff` | `149.18` |
| 3 | `qa_causal_stacker_audit_cv` | `qa_regime_only` | `causal_oof_stacker` | **0.363246** | `0.3666` | `0.4487` | `0.3208` | `0.3169` | `False` | `strict_tick_lt_cutoff` | `103.90` |
| 4 | `qa_causal_stacker_audit_cv` | `qa_causal_all_nohead` | `causal_oof_stacker` | **0.363988** | `0.3666` | `0.4537` | `0.3208` | `0.3148` | `False` | `strict_tick_lt_cutoff` | `111.60` |
| 5 | `he17_feature_ablation_official_cv_pair` | `train_size_regimes` | `jaeger_regime_mixture` | **0.368671** | — | — | — | — | `False` | `strict_tick_lt_cutoff` | `47.50` |
| 6 | `he17_feature_ablation_cv` | `train_size_regimes` | `jaeger_regime_mixture` | **0.371264** | `0.3771` | `0.4508` | `0.3266` | `0.3305` | `False` | `unsupported_copied_signal` | `78.41` |
| 7 | `he_structural_walkforward` | `stack_swm_walkforward` | `structural_sequential` | **0.403918** | — | — | — | — | `False` | `strict_tick_lt_cutoff` | `0.00` |
| 8 | `he_structural_walkforward` | `champion_walkforward_ref` | `structural_sequential` | **0.407317** | — | — | — | — | `False` | `strict_tick_lt_cutoff` | `0.00` |
| 9 | `he_temporal_expert_cv` | `stat_factorized_regime` | `temporal_expert_mixture` | **0.411632** | `0.4021` | `0.5060` | `0.3788` | `0.3596` | `False` | `strict_tick_lt_cutoff` | `6.12` |
| 10 | `he09_prior_hierarchy_ablation` | `stat_markov` | `jaeger_regime_mixture` | **0.417735** | `0.4179` | `0.4910` | `0.3883` | `0.3738` | `False` | `omitted` | `3.58` |
| 11 | `he09_prior_hierarchy_ablation` | `stat_dirichlet` | `jaeger_regime_mixture` | **0.562742** | `0.5450` | `0.6245` | `0.5302` | `0.5513` | `False` | `omitted` | `3.46` |
| 12 | `he_seed_ensemble_study` | `ensemble` | `seed_ensemble` | **0.567477** | `0.5425` | `0.6194` | `0.5499` | `0.5580` | `False` | `strict_tick_lt_cutoff` | `0.00` |
| 13 | `he_ml_family_screen` | `hist_boost__historical_supervision` | `hist_boost` | **0.568854** | `0.5125` | `0.6659` | `0.4860` | `0.6110` | `False` | `strict_tick_lt_cutoff` | `0.45` |

> **Governance Finding on Target Exposure:** Twenty-eight (`28`) trial records in `sampled_outcome_group_cv` (including legacy `jaeger`/`champion` at `0.362291` and non-zero champion blend weights `w0.05`..`w1.0`) carry `validation_target_exposure = True` because the legacy stacker was fit in-sample across the evaluation episodes or derived size regimes from validation statistics. In `rank_models_within_provenance(..., exclude_target_exposed=True)` and `dbsql_benchmark_lane.sql` (`QUERY 1` & `QUERY 5`), these rows are automatically quarantined from clean CV leaderboards and tagged `DISQUALIFIED_IN_SAMPLE_STACKER_EXPOSURE`.

### 2.3 Provenance Tier 3: `dev_exposed_public_validation_sampled_outcome` (Live Serverless Baseline Runs)

| Rank | Study Name | Candidate Model | MLflow Run ID (`Exp 4062806637201469`) | Sampled Brier | Log Loss | ECE | Brier Stable | Brier Short-Hist | Brier Drift | Brier Shared-Chg | Rare 20x `corr_p20` |
| ---: | :--- | :--- | :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | `databricks_serverless_job_888066060424343` | `empirical_bayes_k50` | `8f04cbec276044c9a99ae5c3569d227d` | **0.550339** | `1.158627` | `0.025798` | `0.542758` | `0.608005` | `0.491081` | `0.559513` | `0.1142` |
| 2 | `databricks_serverless_job_888066060424343` | `regime_dirichlet_k35` | `8ae86a39ba9448e29c67d5c8a8398be5` | **0.550469** | `1.158805` | `0.025219` | `0.543083` | `0.607855` | `0.491477` | `0.559460` | `0.1138` |
| 3 | `databricks_serverless_job_888066060424343` | `uncalibrated_empirical_k1` | `21c2911be6ff4e38a21a0174c40b0910` | **0.556865** | `1.186259` | `0.029445` | `0.553599` | `0.609493` | `0.499838` | `0.564532` | `0.0985` |

### 2.4 Key Paired Bootstrap `CI95` Hypothesis Decisions & Scientific Ablation Conclusions
1. **Gradient-Boosted Stacker Ablation (`nostack` vs `champion` in `HE-17`):**
   - Removing the stacker degrades `official_public_validation` by **$-2.2854$ points** (`95% CI: [-2.9307, -1.7179]`) and increases `sampled_outcome_group_cv` Brier by **$+0.007622$** (`95% CI: [+0.003278, +0.011890]`). **Decision:** Stacker is indispensable (`REJECT_SIGNIFICANT_REGRESSION` on removal).
2. **Payout-Size Regime Mixture Experts (`no_size_experts` vs `champion` in `HE-17`):**
   - Removing size-regime experts degrades `official_public_validation` by **$-1.4383$ points** (`95% CI: [-1.8007, -1.1054]`). **Decision:** Size-regime experts provide statistically significant lift across `drift` and `shared_change`.
3. **Forgetting Rate Sensitivity (`slower_forgetting` and `faster_forgetting` vs `champion` in `HE-17`):**
   - `slower_forgetting` collapses on `drift` (`0.8795` loss ratio) and `shared_change` (`0.9208` loss ratio), losing **$-15.7947$ points** (`95% CI: [-16.6157, -14.9448]`). `faster_forgetting` loses **$-1.6502$ points** (`95% CI: [-2.4677, -0.9361]`).
4. **Causal Out-of-Fold Stacker Audit (`qa_causal_stacker_audit_official`):**
   - Fixing the size-regime prior (`prior_only`) achieves **$55.1338$ official points** (`+0.0121` over `champion`, `95% CI: [-0.0156, +0.0398]`, spanning zero), whereas full out-of-fold stacker replacement (`causal_all`) drops **$-0.5117$ points** (`95% CI: [-0.8033, -0.2267]`). **Decision:** Do not replace the frozen champion (`MEASURED_NOT_PROMOTED`).
5. **Rare `20x` Jackpot Calibration (`calibration_20x`):**
   - On `official_public_validation`, `champion` achieves `mean_pred_p20 = 0.014740` vs `mean_target_p20 = 0.014840` (bias = `-0.000100`, `corr_p20 = 0.9718`), whereas `stat_markov (HE-09)` over-predicts rare `20x` jackpots (`mean_pred_p20 = 0.024507`, bias = `+0.009667`, `corr_p20 = 0.5049`).

---

## 3. Stage C — Reproducible DBSQL Queries, Lakeview Dashboard & Notebook Deliverables

1. **Benchmark Governance Module:** `Jaeger_Main/House_Edge/databricks/src/benchmark_lane.py`
2. **Production DBSQL Queries:** `Jaeger_Main/House_Edge/databricks/sql/dbsql_benchmark_lane.sql` (`5` CTE/window queries over `gold_benchmark_registry` and `gold_benchmark_paired_comparisons`)
3. **Declarative Lakeview Dashboard Spec:** `Jaeger_Main/House_Edge/databricks/sql/dbsql_benchmark_dashboard_spec.json` (`4` interactive pages, 12-column grid verified)
4. **Executable Databricks Notebook:** `Jaeger_Main/House_Edge/databricks/notebooks/04_governed_model_benchmark_lane.py`
5. **Unit Test Suite:** `tests/test_databricks_benchmark.py`
