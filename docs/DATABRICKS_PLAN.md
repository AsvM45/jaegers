# Databricks: the credible sponsor slice

**Not a production dependency.** House Edge inference is Python CPU/offline, no live APIs. Raw histories are small enough for Pandas; distributing data processing isn't the bottleneck. Databricks value must be observed from lineage, reproducible tables, collaboration and experiment comparison.

1. Bronze: ingest allowed public train/validation histories, queries, labels and target tables with source hashes/version; isolate `test` true targets (not supplied) and avoid accidentally publishing protected files.
2. Silver: typed checked episode/machine/tick tables, dedupe assertions and strict source-tick visibility. Test count/grouping and missing ticks.
3. Gold: query-level past-only features with PySpark SQL/window operations; parity with equivalent Pandas features for a fixed query-ID list, masks and cutoff cases.
4. MLflow: log genuine model trials, actual score source and source-config hashes. Include a candidate comparison that informs a real selection or error analysis.
5. Evidence: notebook/job, table lineage, before-after productivity/reliability metric supported by data (not manufactured Spark speed claims), screenshots and a concise technical walkthrough.
6. Export: saved model and local feature logic that reproduces offline independently of Databricks. No secrets committed.

User-visible rubric from Databricks track: originality, technical implementation, meaningful advantage. This vertical slice should not be allowed to delay mandatory main/adaptation release.
