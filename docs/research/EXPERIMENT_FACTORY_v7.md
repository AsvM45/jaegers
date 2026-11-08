# JAEGERS — Experiment factory: reconciled technical architecture (v7 → current)

**Status:** CURRENT ARCHITECTURE + IMPLEMENTED/PLANNED GAP ANALYSIS · Updated 2026-11-08 · [Current state](../CURRENT_STATE.md) · [Live #18](https://github.com/AsvM45/jaegers/issues/18)

**Origins:** [Complete Nov 7 v7 proposal](../archive/drive/EXPERIMENT_FACTORY_V7_ORIGINAL_2026-11-07.md) and [complete Nov 7 human guide](../archive/drive/EXPERIMENT_FACTORY_HUMAN_GUIDE_ORIGINAL_2026-11-07.md). This document **integrates and updates** those originals against the code, rather than presenting the plan as already implemented. The two complete source texts are kept for mathematical and design provenance, not as current agent instructions. The standalone personal math guide is excluded from GitHub.

## Executive decision and boundaries

Build a reproducible experimental system for five-class probability forecasting, with a local-first canonical runner and optional Databricks research/analytics acceleration. **Data warehouse ≠ trial queue ≠ evaluator ≠ experiment viewer.** The final organizer predictor and ZIP must work **offline** on the mandated CPU environment. A cloud pipeline must prove actual value separately; an offline mock does not qualify as a live Databricks execution.

### Actual code status versus design

| Capability | Current implementation/evidence | Unverified or future work |
| --- | --- | --- |
| Frozen JAEGERS champion | `Jaeger_Main/House_Edge/jaegers_entry/`: 73 exact-lag experts, sibling context, positive payout-size regimes, boosted win stacker; development-exposed validation ~55.12/60 | Hidden score, organizer receipt and as-of historical stacker legality |
| Data/evaluation | `research/dataset.py`, `features.py`, `feature_api.py`, `metrics.py`, `CONTRACTS.md`, grouped-fold validation and temporal tests | Independent confirmation for every new feature family and historical prior |
| Experiment results | `research/registry.py`, adapters/worker scripts, trial history and ablation/negative findings integrated | Full declarative compiler covering arbitrary valid model+feature+interaction grammar, reliable multi-host lease service |
| Dashboard | `dashboard/` read-only Streamlit plus tests integrated | Public deployment, live service uptime or external judging |
| Databricks | `databricks/` Bronze/Silver/Gold/MLflow/SQL bundle source and 49 offline tests with GitHub Actions passing | Actual competition-trial workspace job, real Delta table/MLflow run, Spark-to-NumPy parity measured there |
| Hitachi | Separate challenge enterprise code under `Jaeger_Main/Hitachi/`; expanded `tower/` on `hitachi` branch | Merge into main; main CI may legitimately skip tower tests |
| Documentation & governance | README, runbooks, scoped agent policy, required ownership check and 5 workflows | Verified live Wiki/Projects board (feature enabled ≠ created/published) |

Issue [#14](https://github.com/AsvM45/jaegers/issues/14) owns real Databricks work; [#65](https://github.com/AsvM45/jaegers/issues/65) owns safe branch retirement. Do not reassign existing active issues based on older v7 staffing tables.

## Data and mathematics

There are eight related machines in each independent episode. For each `query_id`, output the distribution over payout multipliers `[0,1,2,5,20]` with header `query_id,p_0,p_1,p_2,p_5,p_20`. Only true tick `< cutoff` history from the target and siblings is allowed; missing ticks are missing, not zero. Historical supervised rolling-origin examples use observed payout at tick `t` as the label and features strictly earlier than `t`. The dataset does **not** provide historical `signal(t)`; do not paste the query-cutoff signal into old training rows. Keep entire episodes together during cross-validation.

Training sampled-payout one-hot Brier is a proper surrogate loss but **not** the organizer's public true-probability target error. The official public validation score under the inspected 60/40 kit is `round_points = max_points / (1 + mean_condition (E_condition / B_condition))`. The separately supplied participant guide conflicts on 60/40 versus 80/20; preserve that conflict until an organizer resolves it. Historical pseudo-example train/serve as-of compliance remains **NOT_CERTIFIED**, not proven either compliant or invalid.

### Data model from the v7 source

| Layer | Grain / keys | Contract |
| --- | --- | --- |
| Bronze | One source file / ingestion manifest, exact bytes and SHA | Preserve original split, round, type/schema, source license, validated audit checksum; append-only |
| Silver queries | `(round, split, query_id)` | Unique IDs; `(episode_id, machine_id, cutoff, machine_type, signal)`; no hidden answer import |
| Silver history | `(round, split, episode_id, machine_id, tick)` | Unique tick per machine; payout in supported five categories; distinguish unobserved ticks |
| Silver outcomes | Label or public validation target with `data_source` | Keep sampled payout and true probability vector in **different tables** with provenance |
| Gold features | `(source_hash, feature_version, round, split, episode_id, machine_id, asof_tick)` | Deterministic schema, ordering and missingness; every source tick strictly earlier than as-of tick |
| Trial ledger | `trial_id` and `attempt_id` | Immutable normalized specs, claims/attempts, final status, logs, metrics, artifact hashes |

The source proposal suggests DuckDB/Parquet for fast local analytics and Delta Lake tables for governed Databricks execution; neither automatically improves tiny-data latency. Partition modestly by release/round/split, and never shard away the eight-machine episode context. Always record input SHA and content version to prevent cache reuse across different episodes/data revisions.

## Model and feature families

**Existing:** champion's 73 context experts, Bayesian-style shrinkage, time decay and separate win-vs-positive-size factorization; stored challengers include frequency/Dirichlet/Markov/temporal/structural studies with mostly negative development evidence. Do not assume ARIMA/SARIMA or HMM has beaten the champion.

**Searchable future families from v7** (each requires a probability-simplex adapter and episode-grouped validation):
- Descriptive/frequency: Dirichlet-multinomial, empirical Bayes, shrinkage priors, weighted recent outcome counts, posterior predictive checks.
- Lag mechanism: exact-tick Markov orders, context trees, conditional mutual information, lag interaction ablations, change in sibling/own lag effects.
- Drift/regime: EWMA, discount filters, hazard/Bayesian online changepoint, HMM/state-space, local stationary/volatile router and controlled time-series categorical baselines.
- Cross-machine: hierarchical episode random effects, latent factors/partial pooling, lagged peer influence networks and cochange indicators.
- Payout-size geometry: factorized P(win) × P(size|win), smoothed 4-way conditional size models, rare payout calibration and mixture regimes.
- General ML: logistic/elastic-net, forests, HistGradientBoosting, XGBoost/LightGBM/CatBoost adapters; small neural sequences only after a bounded justification.
- Calibration/ensembles: temperature/Dirichlet calibration, constrained convex stacking, distributional uncertainty, error-correlation tests; never tune unrestricted ensembles on the exposed public validation set.

Feature groups should have deterministic names, types, availability rules, interactions and dependencies: query machine type, query-time signal, absolute-tick lags, true-tick rolling windows, recency-weighted statistics, transitions, coverage masks, sibling history, drift/change scores and modeled latent regime estimates. For a final `t` historical pseudorow, **only** features truly available by t are legal; do not use final-length `nobs` or priors fitted from post-t history.

## Declarative search and resource budget

A bounded declarative trial specification contains a dataset/source digest, episode-fold digest, legal feature groups, transformations, conditional hyperparameter schema, model family, train mode, seed, scoring provenance and limits `max_trials`, `max_wall_time`, `max_workers`, `max_memory`. `trial_id = hash(canonical_spec + code/data/fold/feature_versions)`.

Three search modes from the original design: (1) **exhaustively enumerate a declared *finite* grammar** with count and budget *before* execution; (2) covering arrays / factorial screening for a controlled set of interactions; (3) staged conditional search (random/Optuna) focused on promising families. Twenty on/off feature groups already create `2^20=1,048,576` subsets, before model/hyperparameters. Never claim an unbounded 'try everything' engine is feasible.

Recommended stages: baseline and invariant tests → one-factor ablations → pairwise feature/interactions → model-family shootout on the **same grouped folds** → bounded conditional hyperparameter search → a small pre-registered finalist/ensemble screen → independent release gates. Each stage records *negative* and failed runs.

A durable scheduler is a **proposed extension**: atomic trial claim/lease, idempotent attempt IDs, heartbeat, expiration/requeue, bounded retries, priorities and resource checks. SQLite single-writer/atomic artifacts may suit one local host; a multi-host executor warrants a transactional coordinator such as Postgres, not shared OneDrive SQLite or MLflow as queue. The current registry/worker does not imply every proposed fault-tolerance feature has been implemented.

## Validation, falsification, and reproducibility

Every runner must test schema/order/simplex, exact tick boundary, no same-tick sibling leakage, sparse tick missingness, episode uniqueness, deterministic IDs, repeated-run hash, fold isolation, feature/cache invalidation and error handling. Falsification controls from v7: remove sibling signals, permute query signal, inject future outcomes, shuffle correlated episodes incorrectly as a negative control, compare win-vs-size errors and stress rare 20× calibration.

Report paired **per-episode** deltas with uncertainty; naive row-level bootstrap is invalid when eight related machines and overlapping windows are correlated. Preserve trial selection provenance; many trials on exposed validation create winner's curse. Source hierarchy: official kit and code/tests → issue/CI logs → current docs → historical v7 assumptions.

Every attempt should capture: `trial_id,attempt_id,status,worker,started/finished,source_sha,code_sha,split_sha,feature_signature,model/hyperparams,seed,train_source,metric_source,per_episode_metrics,wall_seconds,resource_usage,artifact_sha,exception`. Mock and live results must be distinguished. Full source contract: [science](../science/EVALUATION_AND_PROVENANCE.md) and [`research/CONTRACTS.md`](../../Jaeger_Main/House_Edge/research/CONTRACTS.md).

## Databricks vertical slice, now trial-ready only in principle

The team reports a **14-day competition Databricks trial**. Actual workspace identity/authentication, quota and completed jobs must be confirmed privately; trial access alone does not establish successful execution. The implementation bundle is under `Jaeger_Main/House_Edge/databricks/`; prefer `dev` target and bounded sample data. Authenticate locally, `databricks bundle validate -t dev`, inspect plan and permissions, deploy with approved limits, run a real job, read back actual Bronze/Silver/Gold **Delta** tables, compare 471 feature columns by ID and float tolerance against local reference, log true MLflow run with hashes, inspect dashboard SQL, and record URLs, duration and expense. Failure to run = `BLOCKED`, not `VERIFIED`.

The Databricks README claims "zero shuffle" and "bitwise parity <1e-6"; neither follows merely from `applyInPandas` or toleranced numerical agreement. Evidence must include physical Spark plan/shuffle and measured numerical differences; **bitwise** means equal bits, whereas `1e-6` is an approximate tolerance.

## Release gates and operational sequence

Protect the existing CPU-pinned CSV/ZIP (ignored local artifacts). Submit only the exact paired files after independent schema/hash/reproducibility checks and human confirmation. No cloud dependency during organizer replay. Main and adaptation kits have distinct query IDs and must never share files accidentally. The currently open [#5](https://github.com/AsvM45/jaegers/issues/5) and [#6](https://github.com/AsvM45/jaegers/issues/6) are human release gates, not completed receipts.

Priority now: (1) correct submitted/accepted receipts, (2) real Databricks pilot, (3) scientific/regression checks, (4) safe branch retirement, (5) incremental documentation/UX. The old v7 immediate Codex prompts and Nov 7 ownership schedules are historical only. GitHub source/worktree claims in #18 override them.

## Original documents retained for provenance

- [Original v7 engineering design](../archive/drive/EXPERIMENT_FACTORY_V7_ORIGINAL_2026-11-07.md) — dated proposal, ~84.6k retrieved characters.
- [Original explanatory guide](../archive/drive/EXPERIMENT_FACTORY_HUMAN_GUIDE_ORIGINAL_2026-11-07.md) — dated proposal, ~17.9k retrieved characters.
- [Human-facing current interpretation](EXPERIMENT_FACTORY_GUIDE.md), [system overview](../architecture/SYSTEM_OVERVIEW.md), [current status](../CURRENT_STATE.md).

