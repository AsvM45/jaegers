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

### B. Bitwise Parity with Zero-Shuffle Distributed UDFs
To ensure models trained offline score identically in production, features are computed via an episode-partitioned Grouped Map Pandas UDF (`applyInPandas`). Because all 8 machines for a given episode reside within the same episode partition, cross-machine peer statistics are calculated locally in memory with **zero network shuffle**:
- **Historical Groups (10):** `type` (3), `lags` (48), `pairs` (280), `windows` (18), `decays` (18), `transitions` (48), `missingness` (11), `changes` (7), `peers` (11), `type_lag` (24).
- **Query Group (1):** `current_signal` (3).
- **Total:** 471 canonical features.
- **Parity Tolerance:** $\max |X_{\text{spark}} - X_{\text{numpy}}| < 10^{-6}$ (exact bitwise parity).

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
databricks auth login --host https://<databricks-instance>

# 2. Validate bundle configuration
databricks bundle validate

# 3. Deploy to development environment
databricks bundle deploy -t dev

# 4. Trigger the end-to-end Lakehouse pipeline
databricks bundle run house_edge_etl_and_training

# 5. Deploy to production (with approval)
databricks bundle deploy -t prod
```

### Multi-Task DAG Architecture
The workflow executes 6 orchestrated tasks:
1. `bronze_ingest` $\rightarrow$ Ingests CSVs and records SHA-256 checksums.
2. `silver_clean_and_validate` $\rightarrow$ Enforces quality constraints and removes duplicates.
3. `gold_asof_features` $\rightarrow$ Computes 471 past-only features.
4. `verify_feature_parity` $\rightarrow$ Runs automated bitwise parity gate against NumPy reference.
5. `mlflow_track_models` $\rightarrow$ Trains models, evaluates condition Brier scores, and logs artifacts.
6. `refresh_monitoring_views` $\rightarrow$ Refreshes DBSQL materialized views and dashboard datasets.

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
