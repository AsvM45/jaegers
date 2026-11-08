# JAEGERS House Edge — Warehouse-backed universal experiment factory (v7 curated synthesis)

**Document type:** NEW PUBLIC-REPO CURATED SYNTHESIS of the recent ChatGPT Library artifact titled `JAEGERS_House_Edge_Warehouse_Experiment_Factory_Implementation_Handoff_v7.md`. Original file is ~84 KB, dated Nov 7, 2026. **Not a verbatim full-file import**: its complete bytes were not exportable by the available Library connection during this GitHub migration. Do not pass this document off as that original artifact. **Status:** architecture/research PLAN, not test results, implementation or sponsor approval. Current source/issue precedence: [agent context](../AGENT_CONTEXT.md), [issue #8](https://github.com/AsvM45/jaegers/issues/8), [operating policy](../AGENT_OPERATING_POLICY.md).

## Central design

A **declarative experiment compiler** translates model family × training mode × legal feature groups/interactions × feature transformations × hyperparameter schema × split manifest × budget into immutable trial definitions. A **separate transactional coordinator** claims and leases trials, enforces CPU/RAM/time limits, and appends immutable attempt results. An evaluation adapter validates the five-payout probability contract and causal data visibility, computes episode-grouped observed-label Brier or public true-target official condition loss in explicitly different contexts, and attaches full source/split/target-exposure provenance. An independent release gate promotes only offline-reproducible challengers.

```text
Organizer released immutable CSV/manifest
  -> local curated dataset (Pandas/DuckDB/Parquet), optional Databricks Delta Bronze-Silver-Gold
  -> strict as-of feature registry and cache
  -> declarative search grammar and constraint compiler
  -> resource estimate / dedup / finite trial IDs
  -> transactional worker queue and bounded local execution
  -> five-class probability validator + episode-grouped evaluator
  -> immutable run artifacts + canonical trial ledger
  -> optional MLflow mirror / Streamlit or Databricks SQL reporting
  -> human-reviewed champion promotion and cold local ZIP/CSV reproduction
```

**Important separations:** (1) Data warehouse is not a task queue; (2) MLflow is not durable worker leasing; (3) Spark feature transformation is not proof Spark makes tiny datasets faster; (4) public validation true targets are not train labels/hidden test data; (5) cloud experimentation is not part of the offline competition inference dependency tree.

## Finite enumeration versus realistic broad exploration

A complete search is mathematically possible only for a **declared finite constrained grammar**. Support `enumerate --strategy exhaustive --max-trials N` to **count and emit** all allowed configurations *without launching an unbounded number*; explain rejected combinations and estimated compute. For practical studies `study --strategy staged`:

1. Frozen champion + simple statistical baselines; legal feature/signal contracts verified.
2. One-group ablations and controlled alternative priors, decay/windows.
3. Pairwise/fractional-factorial feature interaction screening to cover important two-way combinations efficiently.
4. Model-family shootout with identical episode group folds and resource budgets.
5. Conditional Optuna/random search on promising model families, pruning/early stop by transparent rules.
6. Selected 3+ way interactions and complementary challengers only where 1/2 way evidence supports.
7. A few preregistered finalists, paired bootstrap/uncertainty, calibration, ensemble weights from development out-of-fold predictions.
8. Freeze and cold-reproduce a new model, separate human approval.

20 binary feature groups already imply `2^20=1,048,576` subsets. Blind exhaustive sweeps and repeated public-target tuning are statistically and computationally misleading.

## Feature and model namespaces

Candidate feature groups: machine type, exact current query signal, history length, coverage/missing masks, observed payout frequencies, conditional positive-payout sizes, rolling true-tick windows, exponentially decayed counts, lags 1–8, transitions and n-grams, time-since-last rare outcome, entropy and shrinkage, drift/change scores, sibling lagged effects, episode-level soft condition posterior, champion expert outputs and selected interactions. Historical pseudo-row signal must be absent unless independently observed at that earlier t. Make feature dependencies explicit.

Model families: original JAEGERS 73 expert mixture/size/stack; smoothed multinomial/Dirichlet/empirical Bayes; Markov/context transitions; logistic/elastic-net classifiers; random forest/ExtraTrees; scikit-learn HistGradientBoosting/XGBoost/LightGBM/CatBoost; state-space/changepoint/HMM; indicator-category ARIMA/SARIMA only if justified, with a proper five-vector adapter; lightweight neural sequence models if budget justifies; calibrated mixtures and simple convex ensembles.

Training modes: true provided train query sampled labels, real historical as-of payout examples, legal episode-local adaptive updates, direct five-class vs factorized `P(win)P(size|win)`, and two-stage query-only signal head when historical signal is unavailable. Fitting a target from a historical tick requires all features strictly from earlier ticks.

## Required experiment identity / trial records

Key by code Git SHA/dirty hash + released data and manifest SHA + fold/episode IDs SHA + feature schema/version/flags + model family/resolved hyperparameters + train mode + seed + environment. Durable fields:
- trial_id, attempt_id, worker lease owner/deadline/heartbeat, status, start/end and errors;
- data release/round/split, training source, true-target exposure, query signal availability;
- model weights/hyperparameters, feature flags and transformed column signature;
- train grouped observed-label Brier/other proper diagnostic, separate public true-vector normalized condition errors and official points where available;
- per-query/episode predictions and error artifacts; provenance, runtime/CPU/memory, warnings and output hashes.

Canonical local coordinator may start as SQLite with a single writer and safe atomic JSON/Parquet attempts. For multiple hosts use PostgreSQL / appropriate transactional store rather than naïvely sharing one SQLite file. Local object/query reading via DuckDB/Parquet; optional MLflow mirror, not substitute for an immutable run ledger. Watch transient OneDrive atomic rename failures and implement bounded retries+idempotent artifacts; note CHAT #8 comments report one such local failure.

## Databricks vertical slice (separate sponsor system)

Optional: permitted CSV → Bronze Delta tables (version/hash) → Silver typed per-episode/machine/tick tables → Gold *strict as-of* features using PySpark SQL; assert exact parity with local Python on query IDs and sparse ticks. Log **real** local/Databricks experiments to MLflow with run IDs/provenance, and build a SQL/MLflow comparison that supports a real technical decision. Add job scheduling only after permissions/budget and local core stable. Do not hallucinate Databricks access, engine speedup or cloud studies.

## Release and scientific gates

Official organizer score uses true probability vectors with equal four-condition weighting; train observed-label Brier is not the same. Main public score **55.121615** was reported locally, but source regime constants were derived from public validation targets, so it is a development-exposed result. No current hidden test score is available.

Only promote when source/split leakage tests, episode-grouped comparisons, rare class calibration, runtime limits, and cold offline package reproduction pass. Local runner must remain Python CPU + NumPy/sklearn where needed, without network. Main and adaptation artifacts must not overwrite each other. Human is responsible for organizer communication/submission.

## Follow-up / source availability

This is a faithful technical **synthesis of the key themes**, not a full 84KB byte-for-byte migration. The source was listed in ChatGPT Library on Nov 8, but raw-byte materialization failed in this tool session. To migrate the full artifact, upload the Markdown original or make it an authorized repository/Drive text document, review for public-safe content, then replace this synopsis in a PR. No raw conversation exports should be copied into the public repo.
