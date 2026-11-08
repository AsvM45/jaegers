---
name: jaegers-databricks
description: Use for meaningful Databricks, PySpark, Delta Lake or MLflow sponsor work without affecting offline predictor.
---

# jaegers-databricks

1. First confirm the core main submission has a validated release path; do not consume critical cutoff time with cloud work.
2. Upload allowed organizer CSVs into Bronze Delta (record hashes and source split), validate and transform to Silver, create Gold past-only per-query features. Train/validation/test target handling remains separate.
3. Compare PySpark output against local Pandas feature values at fixed query IDs, including missingness and cutoff rules. Small datasets are not evidence of Spark speedups; report real collaboration or lineage improvements instead.
4. Track actual model trials in MLflow with source commit/config/data hash and evaluation provenance. Run tests offline locally as the authoritative submission path.
5. Document measured added value, screenshots/notebook or a reproducible job, sponsor opt-in and eligibility. No Databricks API calls/credentials in final competition inference.
