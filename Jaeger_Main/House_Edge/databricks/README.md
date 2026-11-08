# JAEGERS House Edge: Databricks Lakehouse & MLflow Sponsor Architecture

Enterprise-grade Lakehouse integration, PySpark feature engineering, MLflow model governance, and Databricks SQL monitoring for the JAEGERS House Edge competitive forecasting system.

---

## 1. System Architecture

The JAEGERS Databricks platform follows the industry-standard **Medallion Architecture** (Bronze $\rightarrow$ Silver $\rightarrow$ Gold) designed specifically for competitive slot machine forecasting under regime shifts:

```
[ Raw CSV Assets ] (train, validation, test)
        │
        ▼
┌────────────────────────────────────────────────────────┐
│  BRONZE LAYER: Raw Cryptographic Ingestion            │
│  - bronze_queries, bronze_history, bronze_labels       │
│  - bronze_conditions, bronze_audit_log                │
│  - Immutable ingestion with SHA-256 integrity checksum │
└────────────────────────────────────────────────────────┘
        │
        ▼
┌────────────────────────────────────────────────────────┐
│  SILVER LAYER: Cleaned, Curated & Deduplicated        │
│  - Payout constraint: payout IN (0, 1, 2, 5, 20)       │
│  - Machine type validation: steady / balanced / jackpot│
│  - Signal validation: -1, 0, 1                         │
│  - Primary key deduplication: (episode_id, machine, tick)│
│  - silver_queries, silver_spins, silver_episodes       │
└────────────────────────────────────────────────────────┘
        │
        ▼
┌────────────────────────────────────────────────────────┐
│  GOLD LAYER: Distributed Temporal Feature Store        │
│  - Strict < cutoff past-only join (Zero Lookahead)     │
│  - 471 Canonical Features across 11 Groups            │
│  - Grouped Map Pandas UDF partitioned by episode_id    │
│  - 100% Bitwise Parity with NumPy offline models       │
└────────────────────────────────────────────────────────┘
        │
        ├──────────────────────────┬──────────────────────────┐
        ▼                          ▼                          ▼
┌───────────────┐          ┌───────────────┐          ┌───────────────┐
│ MLflow Engine │          │ DBSQL Queries │          │ AI/BI Lakeview│
│ Tracking & ECE│          │ 5 Production  │          │ 4-Page JSON   │
│ Model Aliases │          │ Analytical SQL│          │ Dashboard Spec│
└───────────────┘          └───────────────┘          └───────────────┘
```

---

## 2. Key Technical Innovations

### A. Strict Temporal Isolation (`tick < cutoff`)
In competitive forecasting, lookahead leakage is catastrophic. The Gold feature pipeline enforces temporal isolation at the data engine level:
$$\text{Observations joined} = \{ \text{spin} \in \text{history} \mid \text{spin.tick} < \text{query.cutoff} \}$$
Any observation at $t \ge \text{cutoff}$ is strictly excluded. Perturbation tests prove that mutating future spins produces **0.00** numerical change in generated features.

### B. Episode-Partitioned Distributed UDFs & Numerical Parity (`Bitwise Parity`)
To ensure models trained offline score consistently with the Lakehouse feature store, features are computed via an episode-partitioned Grouped Map Pandas UDF (`applyInPandas`). Spark executes a single `Exchange hashpartitioning(episode_id)` shuffle stage to co-locate all 8 machines and spin history for an episode onto the same worker partition, after which cross-machine peer statistics (`peers/*`) are calculated in memory without a second cross-machine join shuffle:
- **Historical Groups (10):** `type` (3), `lags` (48), `pairs` (280), `windows` (18), `decays` (18), `transitions` (48), `missingness` (11), `changes` (7), `peers` (11), `type_lag` (24).
- **Query Group (1):** `current_signal` (3).
- **Total:** 471 canonical features.
- **Parity Tolerance & Live Measurement:** Gate threshold $\max |X_{\text{spark}} - X_{\text{numpy}}| < 10^{-5}$; on the 150-query × 471-feature live audit (`workspace.house_edge.gold_parity_audit`), the measured `float32` difference was `max_abs_difference = 0.0` (`mean_abs_difference = 0.0`).

### C. MLflow Experiment Tracking & Governance
The `HouseEdgeMLflowTracker` module tracks:
- **Parameters:** `model_type`, `lam`, `prior`, `causal`, `stack_lr`, `feature_groups`, `seed`.
- **Primary Metric:** Multi-class Brier score ($0 \le \text{Brier} \le 2$).
- **Secondary Metrics:** Log loss (cross-entropy), Expected Calibration Error (ECE across 10 deciles).
- **Condition Robustness:** Split by market regime (`brier_stable`, `brier_short_history`, `brier_drift`, `brier_shared_change`).
- **Artifacts:** Reliability diagrams (`calibration_curve.png`), structured deciles (`calibration_data.json`), and 471-dim model signatures.
- **Provenance Tags:** Explicitly distinguishes `sampled_outcome_group_cv` from `official_public_validation`.

### D. Databricks SQL & AI/BI Lakeview Dashboard
Five production DBSQL queries in `sql/dbsql_monitoring.sql`:
1. `model_leaderboard_provenance`: Ranked model comparison with condition degradation percentages.
2. `payout_calibration_reliability`: 10-decile reliability diagram data for all 5 payouts (0x, 1x, 2x, 5x, 20x).
3. `regime_and_data_drift`: Split-level population stability and machine type shifts.
4. `episode_outlier_error_diagnosis`: Highest-error episodes cross-referenced with tick sparsity.
5. `bronze_ingestion_audit_lineage`: SHA-256 cryptographic verification and data volume auditing.

Accompanied by a 4-page declarative Lakeview dashboard specification in `sql/dbsql_dashboard_spec.json`.

---

## 3. Directory Layout

```
Jaeger_Main/House_Edge/databricks/
├── README.md                              # This technical architecture document
├── databricks.yml                         # Declarative Automation Bundle (DAB) spec
├── resources/
│   └── house_edge_workflow.job.yml        # Lakeflow multi-task DAG job definition
├── src/
│   ├── __init__.py
│   ├── session.py                         # Unified Spark & MLflow runtime session resolver
│   ├── mock_engine.py                     # Zero-dependency offline Spark & MLflow engine
│   ├── bronze.py                          # Bronze layer raw ingest & SHA-256 audit
│   ├── silver.py                          # Silver layer validation, deduplication & rollups
│   ├── gold.py                            # Gold layer feature pipeline (471 features, < cutoff)
│   ├── parity.py                          # Mathematical parity verification harness
│   └── mlflow_tracking.py                 # MLflow experiment tracking & model governance
├── sql/
│   ├── dbsql_monitoring.sql               # 5 production Databricks SQL analytical queries
│   └── dbsql_dashboard_spec.json          # Declarative 4-page AI/BI Lakeview dashboard
└── notebooks/
    ├── 01_delta_lakehouse_pipeline.py     # Medallion pipeline walkthrough
    ├── 02_pyspark_feature_parity.py       # Parity verification & scaling comparisons
    └── 03_mlflow_model_governance.py      # MLflow tracking, calibration & drift report
```

---

## 4. Declarative Automation Bundle (DAB)

The Databricks workflow is configured as a native Declarative Automation Bundle in `databricks.yml` and `resources/house_edge_workflow.job.yml`.

### Deployment & Execution Commands

```bash
# 1. Authenticate with Databricks CLI
databricks auth login --host https://dbc-b8d39219-3689.cloud.databricks.com

# 2. Validate bundle configuration
databricks bundle validate -t dev

# 3. Deploy to development environment (workspace.house_edge)
databricks bundle deploy -t dev

# 4. Trigger individual tasks or the full 6-task Lakehouse pipeline
databricks bundle run -t dev --only bronze_ingest house_edge_medallion_pipeline
databricks bundle run -t dev house_edge_medallion_pipeline
```

### Multi-Task DAG Architecture (`house_edge_medallion_pipeline`)
The workflow executes 6 orchestrated Serverless Python tasks (`environment_version: "1"` / Spark 4.2.0):
1. `bronze_ingest` $\rightarrow$ Ingests CSVs from `/Volumes/workspace/house_edge/raw_data/public`, enforces complete split coverage (`train`, `validation`, `test`), and records SHA-256 checksums.
2. `silver_clean_and_validate` $\rightarrow$ Enforces quality constraints (`payout IN (0,1,2,5,20)`, `cutoff BETWEEN 192 AND 256`) and deduplicates spins.
3. `gold_asof_features` $\rightarrow$ Computes 471 past-only features (`tick < cutoff`) via `applyInPandas` with Delta column mapping (`delta.columnMapping.mode = 'name'`).
4. `verify_feature_parity` $\rightarrow$ Runs automated bitwise parity gate (`max_abs_difference = 0.00e+00`) and future-spin perturbation test (`temporal_boundary_pass = true`), writing to `gold_parity_audit`.
5. `mlflow_track_models` $\rightarrow$ Evaluates real multi-class models on the 768 public validation queries, logs runs to `/Shared/jaegers_house_edge_experiments`, and materializes `gold_model_evaluations` and `gold_predictions`.
6. `refresh_monitoring_views` $\rightarrow$ Materializes `monitoring_machine_summary` and persistent Unity Catalog view `v_machine_summary`.

### Live Verification Summary (`STATUS: LIVE_VERIFIED`)

| Resource / Artifact | Live Identifier / Table | Observed Live Result |
|---|---|---|
| **Databricks Workspace** | `https://dbc-b8d39219-3689.cloud.databricks.com` | Serverless Spark 4.2.0 (`workspace.house_edge`) |
| **Lakeflow Job** | Job ID `50563036183908` (`house_edge_medallion_pipeline`) | Stagewise runs (`925919734693613`, `108955288790552`, `579892603954941`, `617153822117765`, `12718307334842`, `253019094752490`) + Full 6-task DAG Run `888066060424343` (`TERMINATED SUCCESS`) |
| **Bronze Delta Tables** | `workspace.house_edge.bronze_queries` (`3,072` rows), `bronze_history` (`564,000` rows), `bronze_labels` (`1,536` rows), `bronze_conditions` (`1,536` rows), `bronze_audit_log` (`10` rows) | Verified `format = 'delta'` (`DESCRIBE DETAIL`), 100% SHA-256 checksums recorded |
| **Silver Delta Tables** | `workspace.house_edge.silver_queries` (`3,072` rows), `silver_spins` (`564,000` rows), `silver_episodes` (`384` rows), `silver_quality_metrics` (`8` rows) | `rejected_queries = 0`, `rejected_spins = 0`, `duplicates_dropped = 0` |
| **Gold Feature Store** | `workspace.house_edge.gold_features` (`3,072` rows × `477` cols = 6 metadata + 471 features) | `768` train + `768` validation + `1,536` test rows |
| **Parity & Cutoff Audit** | `workspace.house_edge.gold_parity_audit` | `status = 'PASSED'`, `max_abs_difference = 0.0`, `mean_abs_difference = 0.0`, `temporal_boundary_pass = true` (150 queries × 471 features) |
| **MLflow Experiment & Runs** | Experiment `/Shared/jaegers_house_edge_experiments` (`experiment_id = 4062806637201469`) | Runs `8f04cbec276044c9a99ae5c3569d227d` (`mean_brier=0.550263`), `8ae86a39ba9448e29c67d5c8a8398be5` (`mean_brier=0.553299`), `21c2911be6ff4e38a21a0174c40b0910` (`mean_brier=0.557804`) |
| **Monitoring Views & SQL** | `workspace.house_edge.monitoring_machine_summary`, `v_machine_summary`, `gold_model_evaluations`, `gold_predictions` | All 5 production queries in `sql/dbsql_monitoring.sql` verified live on Serverless SQL Warehouse |

---

## 5. Zero Cloud Spend & 100% Offline Testing

To ensure zero unauthorized cloud spend during competition development, every component includes a transparent offline fallback:
- When running in an environment without Databricks PySpark or Java installed, `session.get_spark_session()` seamlessly loads `mock_engine.MockSparkSession`.
- When running without a live Databricks MLflow tracking server, `session.get_mlflow()` loads `mock_engine.MockMLflow`.
- **Result:** The entire pipeline, test suite, and notebooks run 100% locally in standard Python 3.13 without internet access or cloud billing.

### Running the Test Suite Locally

```bash
# Run all isolated Databricks tests
python -m unittest discover -s tests -p "test_databricks_*.py" -v
```

---

## 6. Competition Integrity Guardrail: Zero Runtime Competition Inference Dependency

**Crucial Competition Rule:** Final competition inference must execute in an air-gapped, offline evaluation sandbox without external network calls.

- The Databricks Lakehouse implementation operates exclusively as an **offline development, feature store, and model governance layer**.
- The competition entrypoint (`Jaeger_Main/House_Edge/jaegers_entry/` and `offline_runner.py`) has **zero runtime dependency** on Databricks cloud APIs, tokens, or network sockets.
- Models developed and governed in Databricks export pure NumPy / LightGBM weight artifacts that execute seamlessly in the competition submission sandbox.
