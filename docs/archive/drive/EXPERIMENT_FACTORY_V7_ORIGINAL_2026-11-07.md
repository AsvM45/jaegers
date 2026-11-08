# JAEGERS / House Edge — Warehouse-Backed Universal Experiment Factory
## Research synthesis, architecture decisions, model-search catalog, contracts, implementation backlog, and Codex handoff

**Version:** v7.0 research and implementation specification  
**Prepared:** 2026-11-07 (America/Chicago)  
**Project:** TAMU Datathon 2026 — House Edge; later reusable probabilistic-model experimentation platform  
**Repository:** https://github.com/AsvM45/jaegers  
**Challenge subtree:** `Jaeger_Main/House_Edge/`  
**Document status:** **DESIGN / RESEARCH / IMPLEMENTATION PLAN — NOT IMPLEMENTED**. No model experiments, warehouse deployments, cloud jobs, cold reproductions, code edits, submission actions, or accuracy gains were performed for this document.  
**Interpretation of requested format:** This canonical `.md` is the comprehensive Markdown handoff. A byte-identical `.mdhL` copy is supplied only to accommodate the user's literal requested suffix.

---

# 0. Executive decision record — read first

## 0.1 Answer to the request

Build a **declarative experiment compiler** on top of a **versioned dataset and feature lakehouse**, with a **separate transactional trial queue**, **pluggable model adapters**, **budget-aware search**, a **leakage-aware evaluation service**, and **immutable trial/result artifacts**. Integrate **Databricks Delta + Unity Catalog + MLflow** as a collaborative research and sponsor-credible layer, while keeping a **local DuckDB/Parquet + Python runner as the canonical development fallback**. Use Optuna for conditional model/hyperparameter search and consider NIST-style pairwise covering arrays to explore many feature interactions before escalating to higher-order combinations. Treat MLflow as an experiment-view/tracking service, **not** as an authoritative job queue or substitute for source, split, and artifact hashes.

The system should be able to **enumerate every valid combination in a finite, bounded, explicitly specified search grammar**. It cannot literally enumerate every imaginable mathematical model or every real-valued hyperparameter, and it should not execute every combination without constraints. Two complementary modes:

1. `enumerate --strategy exhaustive --max-trials N`: compile all valid configurations in a predeclared finite search domain, report exact count, rejects, resource estimate, and stop if the safety ceiling is exceeded; do not automatically launch an enormous study.
2. `study --strategy staged`: screen hypotheses and feature groups, cover all important 1-way/2-way interactions where possible, sample/TPE-tune the best families, compare finalists on disjoint episode-grouped splits, and run a final limited audit.

**Architectural separation:**

```text
          IMMUTABLE ORGANIZER DATA / MANIFESTS
                         |
             [Bronze -> Silver -> Gold]
       Raw CSV, versioned Delta/Parquet, as-of features
                         |
                FEATURE REGISTRY + CACHE
                         |
                EXPERIMENT COMPILER
 Model grammar × feature groups × training mode × HPO × adapter
                         |
           CONSTRAINT CHECK / DEDUP / BUDGET
                         |
       TRANSACTIONAL TRIAL QUEUE + WORKER LEASES
                         |
          LOCAL WORKERS / OPTIONAL CLOUD JOBS
                         |
         PROBABILITY + CAUSALITY VALIDATION
                         |
               EVALUATION SERVICE
  observed-outcome CV OR public true-vector validation
                         |
            IMMUTABLE ARTIFACTS + RUN LEDGER
        (optional MLflow mirror + Databricks SQL)
                         |
           CHAMPION PROMOTION + OFFLINE GATE
                         |
       FROZEN SUBMISSION CSV + REPRODUCIBLE ZIP
```

**A working warehouse is not sufficient.** Without the registry/runner/evaluator contracts, a warehouse merely contains data. **An MLflow study is not sufficient.** Without grouped validation and exposure control, a thousand trials merely overfit the same public targets.

## 0.2 Timing and non-negotiable release gates

The checked-in House Edge `RULES.md` states **main closes Saturday Nov. 7, 2026 at 9:00 PM Central; adaptation opens then and closes Sunday Nov. 8 at 11:00 AM Central**. The published kit specifies 60 main / 40 adaptation points, while the separately provided participant DOCX reportedly says 80/20 and differs on submission logistics. Do **not** assume that conflict has been resolved without organizer confirmation. Before these deadlines, P0 release integrity outranks the platform proposed here.

**Do now only if current human workflow and time allow:** record local HEAD and dirty state; independently reproduce the current candidate; audit historical signal; pin dependencies; generate and cold-reproduce actual CSV/ZIP; save source/output hashes; preserve accepted human submission receipts. **Do not use this handoff as authorization to modify existing champion code, push to GitHub, or submit.** The repository's `AGENTS.md` and `docs/PLAN_GATES.md` require a plan-only first pass and human approval before implementation.

## 0.3 Source provenance, current repository state and uncertainties

| Assertion | Evidence / status |
|---|---|
| Public default-branch most recent observed commit is `39086b8273581df4bd44f08c9072cb5a9095e97f` with message `agent and ai infra` | Live GitHub connector read during this research; commit at 2026-11-08 00:08:44 UTC. This advanced **beyond** the previous `b78abe75` model-score snapshot. |
| Most recent score-bearing commit is `b78abe75db15688e652b30b9d5388a151f2b7acd`, message `Made improvement to score 55.12/60` | **Commit-message claim on public validation**, not independently rerun, not hidden test, and not confirmed accepted upload. |
| Current model contains 73 predefined lag-context experts, discounted win/no-win estimation, sibling pooling, two conditional-size regimes per type, size experts, and a scikit-learn gradient-boosting stacker | Source inspection: `jaegers_entry/jaeger_model.py`; review exact checkout before action. |
| `stack_features()` includes the final query-time `signal` while `collect=True` creates historical supervised rows | Concrete source-level concern: historical signal(t) is not supplied. Needs actual as-of audit and corrected challenger; not a legal verdict. |
| `SIZE_REGIMES` have comments indicating they were read off public-validation true targets | Current same-validation score is a development/selection result, not independent confirmation. Public validation use is not automatically a rules violation. |
| Repository has scoped `AGENTS.md`, `research/`, and docs including `DATABRICKS_PLAN.md`, `VALIDATION_PROTOCOL.md`, `ENGINEERING_SPEC.md` | Live repo inspection; older docs still mention b78 as snapshot and are not automatically updated when HEAD changes. |
| Databricks warehouse, experiment scheduler, CI, and fully reproducible entry are in operation | **NOT VERIFIED**. Do not infer deployment from plans, source files, or this document. |
| Uploaded conversation exports describe historical pseudo-example rules, evaluation and architecture | User-supplied `House_Edge_Post_v4_Conversation_Complete_LLM_Export.md` and `TAMU_Datathon_2026_Complete_Conversation_LLM_Export.md`; historical context, not current execution evidence. |

**Current code sources:**
- https://github.com/AsvM45/jaegers/tree/main/Jaeger_Main/House_Edge
- https://github.com/AsvM45/jaegers/blob/main/Jaeger_Main/House_Edge/AGENTS.md
- https://github.com/AsvM45/jaegers/blob/main/docs/DATABRICKS_PLAN.md
- https://github.com/AsvM45/jaegers/blob/main/docs/VALIDATION_PROTOCOL.md
- https://github.com/AsvM45/jaegers/blob/main/docs/PLAN_GATES.md
- https://github.com/AsvM45/jaegers/blob/main/docs/ENGINEERING_SPEC.md
- https://github.com/AsvM45/jaegers/blob/main/Jaeger_Main/House_Edge/RULES.md

---

# 1. Correct statistical objective and data contract

## 1.1 Entity definitions and permitted sources

- **Round**: `main` or `adaptation`. Separate datasets, query IDs, reference baselines, weights and artifacts.
- **Episode**: eight related machines with a common query cutoff; distinct episodes are separate scenarios. Tick 200 in episode A is not a global time preceding tick 201 in episode B.
- **Machine**: identified by `(round_id, split, episode_id, machine_id)` within episode, not by the suffix `m000` across episodes.
- **Tick**: integer local time index. **Missing tick = unobserved, never payout 0.**
- **Payout**: one observed class in `{0,1,2,5,20}`. This is a sampled outcome, not the simulator's latent conditional probability vector.
- **Query**: `(query_id, episode_id, machine_id, machine_type, signal, cutoff)` where `machine_type ∈ {steady,balanced,jackpot}` and query-time `signal ∈ {-1,0,1}`; the signal's causal meaning is not specified.
- **Conditions**: `stable`, `short_history`, `drift`, `shared_change`. Visible in train/public validation metadata, hidden for public test; never supply truth condition at test inference.
- **True target**: five conditional probabilities, provided only for main public validation cutoffs; hidden for main test.

The main kit contains 96/96/192 episodes in train/public-validation/public-test, with eight queries per episode (768/768/1536 queries). The actual main test inputs are already supplied; the withheld objects are final-query outcome/probability truth, test conditions and references. The adaptation kit is separately released at the main cutoff.

## 1.2 Prediction format

For each query emit

\[
\hat{\mathbf p}_q = (\hat p_0,\hat p_1,\hat p_2,\hat p_5,\hat p_{20}),\quad
\hat p_k\in[0,1],\quad \sum_k \hat p_k=1.
\]

Required CSV header: `query_id,p_0,p_1,p_2,p_5,p_20`. No missing/duplicate/extra test IDs; finite values and sum-to-one within the organizer threshold `1e-6`.

Main kit's true-target scoring on released public validation:

\[
L_q=\sum_k(\hat p_{q,k}-p_{q,k})^2,\qquad
E_e=\frac{1}{8}\sum_{q\in e} L_q,
\]
\[
E_c=\frac{1}{N_c}\sum_{e\in c}E_e,\qquad
R=\frac{1}{4}\sum_{c\in C}\frac{E_c}{\max(B_c,10^{-9})},
\]
\[
\mathrm{round\_points}=\frac{\mathrm{round\_maximum}}{1+R}.
\]

Here `B_c` is the same condition-level error for the **frozen organizer reference**, independently defined per round. Do not substitute top-one classification accuracy, payout expected-value error, generic Brier-from-one-hot diagnostics or `slot_forecasting/scoring.py:score_predictions`'s different 0-100 diagnostic. The official code path is `check_submission.py --split validation` / `slot_forecasting.rounds`.

## 1.3 Historical as-of supervised examples: the core data multiplier

For an observed historical payout at tick `t`, construct:

```
example_id = (round, source_split, episode_id, machine_id, asof_tick=t)
features = observations at integer ticks strictly less than t
label = actual observed payout at t
signal_at_t = MISSING / NOT PROVIDED
```

This derives *real labeled forecasting examples from genuinely observed outcomes*, not fake/synthetic predictions. No row is fabricated for a missing/unobserved target tick. For query cutoff `c`, source tick must satisfy `<c` for the target machine **and all siblings**. Exact lag `k` is source tick `t-k`, not kth-most-recent row.

Historical `signal(t)` is **not supplied**. The current query signal must not be carried back to historical as-of training rows. Viable design: (a) a history-only core trained on pseudo-examples with a `historical_signal_available=false` policy; (b) a distinct query-time signal-aware adjustment fitted on authentic query rows where signal is actually observed. Mark compatibility at the feature and model level so illegal compositions cannot be compiled.

## 1.4 Proper loss and statistical limitations

For observed class `Y` and one-hot vector `e_Y`, if true conditional vector is `p(X)`,

\[
E[\|\hat p(X)-e_Y\|_2^2\mid X]
=\|\hat p(X)-p(X)\|_2^2+1-\|p(X)\|_2^2.
\]

Thus expected one-hot Brier minimization is appropriate for probability learning, but **one sampled spin is noisy** and historical windows are correlated. Thousands of pseudo-rows do not create thousands of independent episodes. The true-vector organizer loss is only directly measurable where true vector targets are released.

## 1.5 Data splits and evaluation exposure

Maintain **five distinct contexts**:

| Context | Ground truth available | Correct use | Can report official round points? |
|---|---|---|---|
| Train original queries | Sampled outcomes | Fit and episode-grouped CV | No |
| Historical as-of windows | Genuine earlier sampled payouts | Fit/temporal diagnostics with as-of constraints | No |
| Public validation queries | True five-vectors, sampled outcomes, conditions, references | Limited final candidate selection, scorer parity; source of actual publicly measurable `R` | Yes, as *public-validation development score*, with exposure flags |
| Public test queries | Inputs and past history only | Submit forecasts; format and reproducibility QA; permitted as-of episode adaptation | No |
| Organizer hidden test | True vectors withheld | Organizer-only grading | Only after organizer feedback |

**Do not create a 'new untouched validation set' by splitting a public-validation set whose targets already informed prior feature design or constants.** Episode-grouped cross-fitting can provide more defensible out-of-fold comparisons, but does not erase prior selection exposure. For clean train-only development, group whole training episodes, use observed-outcome proper scores and characterize the metric mismatch explicitly.

A held-out episode may still supply **its own past observable history for a predeclared local adaptation rule**—the same procedure permitted at actual test inference. It may not supply its final-query label/true vector to fit that prediction.

---

# 2. Proposed technology architecture and platform boundaries

## 2.1 Two-tier practical stack

| Concern | Local canonical solution | Shared / cloud extension | Why |
|---|---|---|---|
| Raw storage | Original organizer CSV/ZIP + SHA-256 manifest | Unity Catalog volume / approved storage for allowed files | Independent source provenance |
| Curated analytical tables | Parquet + DuckDB (and Pandas where convenient) | Delta Lake Bronze/Silver/Gold | Versioned SQL, data lineage, collaboration |
| Feature transformations | Pure Python/Pandas/DuckDB reference implementation | PySpark/SQL parity implementation | Identical as-of semantics across environments |
| Experiment specification | Version-controlled YAML/JSON with schema validation | Same versioned files | Reusable, reviewable, portable |
| Trial planning | Python registry/constraint compiler | Same compiler, optionally invoked in Jobs | Don't tie logic to a cloud runtime |
| Search | Explicit grid/random; Optuna | Same shared Optuna storage where appropriate | Conditional hyperparameter optimization |
| Work queue | Single-writer SQLite at initial local stage | PostgreSQL with leasing, idempotency, heartbeat | Transactional coordination, not analytical Delta tables |
| Trial execution | Python subprocess/process pool, fixed CPU/memory | Databricks Jobs `For each`/task workflows; optional workers | Parallelize *independent model fits*, not tiny raw CSV data |
| Experiment ledger | Canonical immutable manifest + artifact tree | MLflow Tracking mirrored to Databricks | Compare runs; retain source-of-truth integrity |
| Large artifacts | Content-addressed local paths | Unity Catalog volumes / object store if permitted | Models, predicted vectors, logs, cached matrices |
| Reporting | DuckDB SQL over predictions + Markdown/HTML scorecards | Databricks SQL / MLflow UI | Inspect per-episode and per-condition failures |
| Final predictor | Frozen offline Python package | **None at inference time** | Organizer forbids runtime network/external API |

**Default recommendation:** start with DuckDB + Parquet + Python + Optuna + a single-writer run ledger locally; add Databricks Delta + MLflow as a credible separate vertical slice and shared collaboration layer. PostgreSQL only becomes necessary when genuinely coordinating multiple remote processes/hosts. Ray, Kubernetes, Spark clusters, Redis, Kafka and Airflow are unnecessary in the initial release and not prerequisites for future expansion.

## 2.2 Why the warehouse and queue must be different

Warehouse responsibilities: immutable event/query data, validated versions, reusable feature materializations, experiment results and aggregations. It is optimized for analytical queries and reproducibility.

Queue responsibilities: atomic claim/lease of exactly one pending trial; heartbeat; timeout; retry with attempts; ownership; compare-and-set completion; scheduling fairness; concurrency caps. It is transactional and latency-sensitive. A Delta table alone is not the recommended sole lock/lease mechanism; SQL transactional store/one coordinator is a better fit. MLflow stores run metadata/artifacts but is **not** a general-purpose distributed scheduler.

**Do not put public validation true targets into ordinary model-worker feature tables.** Give evaluator a separate controlled join path so training/inference code cannot accidentally see withheld or held-out answers.

## 2.3 Databricks capabilities verified as of research

- Databricks Free Edition is **serverless-only, quota-limited, and without SLA**; docs list **maximum five concurrent job tasks** per account, one SQL warehouse limited to 2X-Small, and limited notebook compute. Quota excess may shut down compute for the remainder of a day (or longer in extreme cases). Exact account-specific usable capacity must be checked; no unlimited experimentation is promised. [D1]
- Databricks **Lakeflow Jobs `For each`** can run a standard nested task on a JSON array of input configurations, with concurrent iterations. The input payload has documented size limits; pass a **small ID/URI**, not a massive JSON trial specification. [D2]
- Databricks **Declarative Automation Bundles**, formerly Asset Bundles, can put jobs, notebooks and deployment definitions under source control. Not needed for first smoke test, valuable later for reliable multi-person CI/CD. [D3]
- Delta Lake supports ACID tables, schema enforcement and time travel; its Change Data Feed is opt-in and subject to retention. Time travel is a convenience, not a substitute for content hashes and retained source snapshots. [D4]
- MLflow Tracking stores run params, metrics, tags, datasets and artifact references; backed by database metadata and separate artifact storage. Databricks MLflow also has platform quotas on run/metric/tag counts. Log rich configuration and per-query predictions as **artifacts**, not thousands of parameters or metric steps. [D5]
- Optuna supports multi-process and multi-node studies via appropriate storage. Its docs **do not recommend SQLite for parallel/distributed optimization**; use a local JournalStorage or PostgreSQL for shared trial claiming. `ask/tell` is useful for an external scheduler, but Optuna notes its RDB heartbeat is intended for `optimize()`, not `ask/tell`; implement your own worker lease/heartbeat for the latter. [D6]
- DuckDB reads Parquet directly with filter/projection pushdown, making an inexpensive local query layer without a permanent warehouse server. [D7]

## 2.4 Scale transition — explicit stages

**S0 / before deadline:** no new platform dependency; safe champion and source/metric audit only.  
**S1 / local experiment engine:** immutable file hashes, DuckDB or Pandas as-of feature cache, schema-tested YAML specs, single coordinator, lightweight runs; 3 smoke trials.  
**S2 / local broad search:** Optuna study, pairwise screening, grouped CV, frozen finalist audit, per-trial filesystem artifacts, optional MLflow local UI.  
**S3 / Databricks sponsor-grade mirror:** Bronze/Silver/Gold Delta, parity checks, metadata-driven `For each` job and workspace MLflow experiment using genuine comparisons. Resource caps remain enforced.  
**S4 / collaboration:** PostgreSQL queue/Optuna backend, approved artifact store, multiple workers (laptops/cloud), access control, durable retry/resume.  
**S5 / generalized research platform:** reusable project adapters and cost-aware cross-dataset studies; never mix incomparable score scales.

---

# 3. Warehouse model: schemas, grains, security and versioning

## 3.1 Core keyspace and immutability

All tables carry `challenge_id`, `round_id`, `release_id`, `source_split` and `source_manifest_sha256` where relevant. Never use a bare `episode_id` join across releases or train/test splits; incorporate round/release/split namespace unless identifier uniqueness is independently guaranteed. Strong row grain and logical keys:

| Table | Logical unique key / grain | Data |
|---|---|---|
| `raw_source_manifest` | `source_manifest_sha256, source_path` | Original file hash, bytes, modified/ingest timestamp, source scope, release |
| `bronze_queries` | `release_id, source_split, query_id` | Original query fields and ingest identity |
| `bronze_history` | `release_id, source_split, episode_id, machine_id, tick` | Original observed payout, provenance |
| `bronze_labels` | `release_id, source_split, query_id` | Sampled next-payout class; train/validation only |
| `bronze_true_targets` | `release_id, query_id` | Five actual public-validation probabilities, evaluator-only |
| `bronze_reference` | `release_id, query_id` | Frozen public-validation reference forecast |
| `bronze_conditions` | `release_id, source_split, episode_id` (verify source grain) | Known train/public-validation condition; scorer/classifier labels, not test feature |
| `silver_query` | `release_id, source_split, query_id` | Typed validated query/context; cutoff and type/signal |
| `silver_spin` | `release_id, source_split, episode_id, machine_id, tick` | Validated observed category; sparse tick semantics |
| `silver_episode` | `release_id, source_split, episode_id` | Eight-machine count, shared cutoff, coverage statistics |
| `gold_query_features` | `feature_set_hash, release_id, source_split, query_id` | As-of final-query feature vector, current signal permitted |
| `gold_asof_examples` | `feature_set_hash, release_id, source_split, episode_id, machine_id, asof_tick` | Historical **real** outcome label + past-only features; signal unavailable |
| `split_manifest` | `split_manifest_hash, episode_group_key` | Development fold role and fixed membership |
| `feature_definition` | `feature_id, feature_version` | Source and as-of policy, compatible contexts, output schema |
| `model_definition` | `model_id, model_version` | Adapter family, fit/predict contract, allowed data and resources |
| `experiment_spec` | `study_id, spec_hash` | Full declarative search grammar, canonical revision |
| `trial_ledger` | `trial_id` | Immutable resolved config fingerprint; state transitions stored separately |
| `trial_attempts` | `trial_id, attempt_no` | Worker lease, heartbeats, failures, logs |
| `trial_predictions` | `trial_id, eval_context, fold_id, query_id` | Five-vector, provenance; at scale store Parquet artifacts instead of large Delta row writes |
| `trial_metrics` | `trial_id, eval_context, metric_name, group_key` | Real measured losses, condition ratios, runtime, diagnostic flags |
| `trial_artifacts` | `trial_id, artifact_kind, content_sha256` | Artifact path/URI, bytes, environment hash, retention |
| `release_registry` | `challenge, round, release_candidate_id` | Frozen CSV/ZIP hashes, verification state, human receipt |

**Key caveat:** Delta/Unity Catalog's declared primary keys or uniqueness claims are **not a substitute for explicit uniqueness/duplicate checks**. Enforce the row-key contract during Silver transformations and preflight tests, then store validation outcomes as artifacts.

## 3.2 Bronze / Silver / Gold responsibility

**Bronze — source faithful:** preserve raw schema and raw text representations when possible; source byte SHA256 is authoritative. Upload only organizer-permitted files. Separate restricted true target tables, even though public validation targets are legitimately released.

**Silver — validated semantic facts:** cast ticks/keys/outcomes, ensure legitimate class values, ensure eight queries/episode and a common cutoff, check no duplicate spin keys, distinguish missing from 0, prohibit history tick ≥ current cutoff for supplied test/train episodes, verify joins do not multiply rows, and store coverage masks/stats.

**Gold — materialized *views of information available at an as-of cutoff*:** construct final-query features and historical pseudo-examples as **different contracts**. Log feature family, whether signal is allowed, `max_source_tick`, missingness, the exact version/hash of source and builder, and group metadata. Derived historical rows are not independent episodes, so expose `episode_weight`, `machine_weight` and a sampling policy to fitters.

Avoid naive `queries × all-history` cross joins for every feature family. Prefix cumulative counts, windowed aggregations, exact-lag keyed joins and incremental as-of scanning are much more efficient. The canonical feature factory should be a pure function of `(observable data, asof_tick, feature_version, feature_flags)`, enabling caching and offline parity.

## 3.3 Example SQL: safe query features (illustrative Spark/Delta SQL)

```sql
-- LOGICAL EXAMPLE, NOT EXECUTED. Replace namespace and refine types from actual kit.
-- All joined rows obey the query's own cutoff. No current/future spin enters features.
SELECT
    q.release_id,
    q.source_split,
    q.query_id,
    COUNT(h.tick) AS history_observed_count,
    SUM(CASE WHEN h.payout = 0  THEN 1 ELSE 0 END) AS n_0,
    SUM(CASE WHEN h.payout = 1  THEN 1 ELSE 0 END) AS n_1,
    SUM(CASE WHEN h.payout = 2  THEN 1 ELSE 0 END) AS n_2,
    SUM(CASE WHEN h.payout = 5  THEN 1 ELSE 0 END) AS n_5,
    SUM(CASE WHEN h.payout = 20 THEN 1 ELSE 0 END) AS n_20,
    MAX(h.tick) AS max_source_tick
FROM silver_query q
LEFT JOIN silver_spin h
  ON h.release_id = q.release_id
 AND h.source_split = q.source_split
 AND h.episode_id = q.episode_id
 AND h.machine_id = q.machine_id
 AND h.tick < q.cutoff
GROUP BY q.release_id, q.source_split, q.query_id;
```

If `h` is absent, `COUNT(h.tick)=0`; that is not evidence of any particular payout class. For a sibling feature, require the same episode/split and `h.machine_id <> q.machine_id`, still `h.tick < q.cutoff`. For exact lag 2, join `h.tick = q.cutoff-2` and produce both `lag2_class` (nullable) and `lag2_observed` (boolean), **not** the second-most-recent row.

**Historical pseudo-example query**: build candidate target rows from genuinely observed `silver_spin` (`target.tick AS asof_tick`, `target.payout AS sampled_label`), then join source spin rows only when `source.tick < target.tick`, including peers. Explicitly create `signal_available=false`; do not join query cutoff signal onto those rows. For performance, implement prefix-based or batched as-of algorithms rather than materializing full quadratic source/target joins.

## 3.4 Feature materialization key / cache invalidation

```
feature_set_hash = SHA256(
  source_manifest_sha256,
  feature_registry_version,
  feature_builder_code_sha256,
  sorted_enabled_feature_ids_and_versions,
  sorted_interaction_ids_and_versions,
  asof_policy_version,
  missingness_policy_version,
  pseudo_example_warmup_policy,
  relevant_round_and_split_metadata
)
```

Cache separately for `query_cutoff` and `historical_asof` contexts. A change in feature code or allowable history must invalidate the cache; identical named features are not sufficient. Cache rows with query IDs, as-of ticks, column types, source max tick, feature/hash metadata. Never cache a feature table that mixes training fold statistics fitted on the entire dataset: **transformer fit state belongs to the particular trial/fold**, not global Gold.

## 3.5 Partitioning and storage layout

Reasonable partition axes: challenge, round/release, source split, Gold feature-set version or coarse episode hash bucket. Do **not** partition by every machine, query, experiment, or unique tick: that creates many tiny files. Coalesce writes when feasible and measure actual read patterns. Treat `public/test` data and `validation/targets.csv` according to organizer publication and team-access rules. Restrict target access to evaluation service; write only permitted aggregates/predictions to shared external dashboards.

Example logical paths (names proposed):

```text
data/
  sources/<release_hash>/original_organizer_files/
  bronze/<release_hash>/<split>/
  silver/<release_hash>/<split>/
  gold/query/<feature_set_hash>/<release_hash>/<split>/
  gold/asof/<feature_set_hash>/<release_hash>/<split>/
  splits/<manifest_sha256>.json
artifacts/
  trials/<trial_id>/attempt_<n>/
    resolved_config.json
    environment.json
    metrics.json
    predictions.parquet
    per_episode.parquet
    stdout.log
    stderr.log
    fitted_model/...  # when relevant
  releases/<round>/<candidate_hash>/
    submission.csv
    code.zip
    verification.json
```

## 3.6 Lineage and dataset exposure policy

Every feature declaration specifies: `source_table`, `entity_grain`, `lookback`, `max_source_tick_rule`, `uses_current_query_signal`, `uses_true_target`, `uses_condition_truth`, `uses_peer_history`, `historical_asof_compatible`, `required_missingness_mask`, and `builder_version`.

Hard reject compilation where:
- query-cutoff signal appears as a historical pseudo-row feature without a verified aligned historical signal stream;
- held-out query label/true target enters fit or preprocessing for that held-out prediction;
- condition truth is consumed as test-inference feature;
- sibling source tick is `>=` target as-of tick;
- an ID or release string is treated as portable latent machine identity without a predeclared, justified experiment;
- feature group requires an unavailable source or context;
- model output cannot be transformed to a valid five-vector;
- transformer fitting sees episodes outside the train side of a fold.

---

# 4. Declarative model/feature/trial registry: the foundation for 'every combo'

## 4.1 Search grammar

Define an experiment as a compositional graph:

```text
Trial = DatasetSnapshot
      × EvaluationProtocol
      × TrainingSourcePolicy
      × FeatureSet
      × PredictorFamily
      × PredictorHyperparameters
      × LocalAdaptationPolicy
      × CalibrationPolicy
      × EnsemblePolicy
      × Seed
      × ResourceBudget
```

This is not an unconditional Cartesian product; compatibility constraints prune illegal or nonsensical combinations before any worker is launched. Examples: SARIMAX requires a legitimate aligned exogenous series; a query-signal model cannot train on pseudo-rows containing copied current signal; an ensemble requires available component out-of-fold prediction artifacts; `dropout` is only a neural model hyperparameter, not a Dirichlet hyperparameter; an output adapter must yield exactly five probabilities.

### Three levels of combinatorial enumeration

- **Exhaustive finite subspace:** enumerate every legal configuration when the cardinality is small; construct a **manifest before launch** and compare executed count to expected count.
- **Interaction coverage:** generate pairwise / selected 3-way covering arrays over categorical feature/model decisions to ensure each important interaction is represented without testing the full Cartesian product. Use constraint-aware coverage, since some combinations are illegal. NIST's work formalizes t-way coverage. [R1]
- **Adaptive optimization:** randomized/TPE/Bayesian search chooses from the same typed grammar. Best for large or continuous parameter spaces. Fixed trial budget, seeds and evaluation exposure policies.

A continuous hyperparameter such as `prior_strength∈(0,∞)` **cannot** be exhaustively searched. An explicit discrete grid can.

## 4.2 Registry schema example (design — not implemented)

```yaml
registry_version: 1
feature_groups:
  - id: type
    version: 1
    contexts: [query_cutoff, historical_asof]
    columns: [type_steady, type_balanced, type_jackpot]
    dependency: []
    safety: static_type_provenance_required
  - id: signal_query
    version: 1
    contexts: [query_cutoff]
    columns: [signal_minus, signal_zero, signal_plus]
    dependency: []
    safety: absent_for_historical_asof
  - id: exact_lags_1_8
    version: 1
    contexts: [query_cutoff, historical_asof]
    columns: [lag_one_hot, lag_observed_masks]
    dependency: []
    safety: source_tick_strictly_less_than_asof
  - id: cross_peer_lags
    version: 1
    contexts: [query_cutoff, historical_asof]
    dependency: [exact_lags_1_8]
    safety: same_episode_past_only

models:
  - id: hierarchical_dirichlet
    version: 1
    modes: [fit_global, infer_local_adapt]
    supervision: [sampled_query_label, historical_asof_label]
    prediction: probability_vector_5
    runtime: python_cpu
    parameters:
      prior_concentration: {type: float, low: 0.1, high: 100.0, log: true}
      shrinkage: {type: float, low: 0.0, high: 1.0}
  - id: multinomial_logistic
    version: 1
    supervision: [sampled_query_label, historical_asof_label]
    prediction: probability_vector_5
    parameters:
      C: {type: float, low: 0.01, high: 100.0, log: true}
  - id: xgboost_multiclass
    version: 1
    supervision: [sampled_query_label, historical_asof_label]
    prediction: probability_vector_5
    parameters:
      max_depth: {type: int, low: 2, high: 5}
      n_estimators: {type: int, low: 50, high: 300}
  - id: current_jaegers_frozen
    version: 1
    supervision: [observed_histories]
    prediction: probability_vector_5
    parameters: {} # exact external params file is already fixed
```

**`parameters` nomenclature:** In a registry these are *configuration search fields*, usually hyperparameters. Underlying trained coefficients/leaf values/posterior states are the **learned model parameters**. Save both the selected configuration and the resulting fitted state, but do not conflate them.

## 4.3 Study specification example

```yaml
schema_version: 1
study_id: main_hist_asof_screen_v1
status: PROPOSED
challenge: house_edge
round_id: main
source_manifest_sha256: PLACEHOLDER_ACTUAL_HASH_REQUIRED
split_manifest_sha256: PLACEHOLDER_ACTUAL_HASH_REQUIRED
feature_registry_version: 1
model_registry_version: 1

training:
  modes: [historical_asof, original_sampled_queries]
  historical_signal_policy: omit
  pseudo_warmup_observations: 20
  weights: equalize_episode_influence
  local_episode_adaptation: [none, dirichlet_update]

features:
  mandatory: [type, history_coverage]
  optional: [freq_all, ewma_multiscale, exact_lags_1_8, peer_aggregates]
  interactions: [type_x_recency, recency_x_peer]
  incompatible:
    - [historical_asof, signal_query]

models:
  allow: [hierarchical_dirichlet, multinomial_logistic, current_jaegers_frozen]
  disallow_unregistered_imports: true

search:
  mode: pairwise_then_tpe
  max_trials: 60              # illustrative, not actual timing promise
  max_valid_combinations_to_materialize: 100000
  seeds: [11, 23]
  max_parallel_workers: 2
  failure_policy: record_and_continue

evaluation:
  primary: train_sampled_outcome_episode_grouped_cv
  guardrail: no_heldout_query_label_in_fit
  public_validation: finalist_only
  required_report: [loss_by_episode, loss_by_condition, runtime, provenance]

resources:
  per_trial_wall_seconds: 120
  per_trial_memory_mib: 2048
  worker_threads: 1
```

**The compiler validates every field, checks dependency constraints, expands legal combinations, canonicalizes resolved configs, estimates trial count and cost, and generates an immutable manifest.** Unknown model/feature names fail closed; do not dynamically `eval` arbitrary strings as Python.

## 4.4 Model adapter interface

```python
from typing import Protocol, Mapping

class ProbabilisticModel(Protocol):
    model_id: str
    def fit(self, train_examples, *, config: Mapping, seed: int) -> None: ...
    def predict_proba(self, query_rows, observable_histories) -> "Array[N,5]": ...
    def save(self, directory) -> None: ...
    @classmethod
    def load(cls, directory): ...

class ModelRegistry(Protocol):
    def list_models(self) -> list[str]: ...
    def validate_config(self, config, context) -> None: ...
    def build(self, config) -> ProbabilisticModel: ...
```

Contract: output ordered `(0,1,2,5,20)`, finite, nonnegative, unit-sum; deterministic sorting and exactly one `query_id` mapping; save/load round trip; declared feature context; CPU-compatible inference. Keep explicit adapters for `binary_win_and_size` and per-category logits. An ARIMA expected-payout scalar is **not a valid adapter** unless it is converted via a justified five-category distributional model and validated.

## 4.5 Trial identity, dedupe and comparable evaluations

```python
trial_id = sha256(canonical_json({
  "study_spec_hash": ..., "source_manifest_hash": ..., "split_manifest_hash": ...,
  "model_id_version": ..., "resolved_hyperparameters": ...,
  "feature_set_hash": ..., "training_policy_hash": ...,
  "evaluation_protocol_hash": ..., "adaptation_policy_hash": ...,
  "seed": ..., "code_commit_or_dirty_tree_hash": ...,
  "environment_lock_hash": ...
})).hexdigest()
```

**Do not include** non-semantic wall clock, worker hostname, attempt number, mutable note, or database row ID in the canonical trial identity. Store attempts separately. If an identical completed trial is requested, reuse only after verifying artifact checksums, otherwise fail with collision/corruption alert. Cross-platform floating-point string serialization must be canonical and tested.

For comparison across model families, **keep dataset version, fold manifest, seed policy, and metric provenance matched**. Never rank a model's sampled-label group-CV score numerically against another model's true-vector public validation R as if comparable.

---

# 5. Model/search catalog — complete enough for extensible implementation

This is a registry *backlog*, not a promise to run everything. **P0 / P1 / P2 / P3 below mean research sequence**, not confirmed uplift.

## 5.1 Family 0: frozen and statistical baselines (first)

| Candidate | Hypothesis / outputs | Core search dimensions |
|---|---|---|
| `frozen_jaegers` | Existing candidate remains best | Frozen exact params and hash, no uncontrolled refitting |
| `pooled_recent` | Source baseline and recovery fallback | Organizer-configured variant |
| `type_prior` | Type-specific probabilities dominate | type-level smoothing / signal optional at authentic queries |
| `dirichlet_multinomial` | Historical five-counts with categorical prior | concentration, history window, posterior mean vs blend |
| `beta_win_dirichlet_size` | Decouple win frequency and conditional size | win prior, size prior, model-specific forgetting |
| `hierarchical_dirichlet` | Borrow strength between type/episodes/machines | levels, concentration, empirical Bayes prior fit |
| `empirical_bayes` | Estimate shrinkage from training episodes | prior estimator and regularization |
| `ewma_categorical` | Drift benefits from recency | 8/24/64/128 half-lives, mixing weights |
| `logit_query_head` | Current signal corrects history-only model | training on authentic query labels, strength and regularization |

## 5.2 Family 1: lag-mechanism identification (particularly relevant)

| Candidate | What it adds beyond current 73 experts | Core hyperparameters / cautions |
|---|---|---|
| `jaegers_expert_ablation` | Measure each existing mechanism's incremental value | per-expert group flags; same evaluation |
| `bayesian_expert_posterior` | Calibrated posterior over candidate lag experts | prior, likelihood discount, shared pooling |
| `hedge_online_experts` | Multiplicative-weights online expert aggregation | learning-rate/forgetting, floor, reset |
| `sparse_logistic_lag_interactions` | Regularized pair/triple Boolean interactions | sparsity, interactions, exact lags |
| `boolean_rule_dictionary` | AND/OR/XOR/XNOR/threshold candidate rule scores | rule grammar, max lags, evidence shrinkage |
| `variable_order_markov` | Adapt context length per machine | max memory, smoothing |
| `context_tree_weighting` | Efficient mixture of suffix/context models | max depth, binary/categorical representation |
| `probabilistic_suffix_tree` | Data-driven variable-context likelihoods | context selection and count floor |
| `minimal_description_length_rules` | Penalize needlessly elaborate rules | code-length penalty, hypothesis grammar |
| `finite_state_predictor` | Learn a small categorical latent transition machine | number states, regularization |

CTW's published foundations concern efficient weighting over bounded-memory context-tree sources; adaptation to **nonconsecutive lag pairs** must be specified and tested instead of claiming standard CTW already covers those patterns. [R2]

## 5.3 Family 2: temporal drift and regime detection

| Candidate | Hypothesis | Core hyperparameters |
|---|---|---|
| `multiscale_ewma` | Different stability/drift regimes need different half-lives | half-life grid / soft weights |
| `cusum_categorical` | Categorical win/size likelihood shifts | threshold, baseline, reset strength |
| `page_hinkley` | Mean win-rate shifts identifiable | threshold, slack, forgetting |
| `bocpd_beta_binomial` | Marginalize run length and change locations | hazard prior, max retained states, prior strength |
| `bocpd_dirichlet` | Extend run-length inference to all five payouts | hazard, concentration, categorical observation family |
| `categorical_hmm` | Hidden states govern payout probabilities | 2-4 states, priors, EM restarts |
| `hidden_semi_markov` | Regime duration influences predictions | duration model and number states |
| `dynamic_logistic_state_space` | Gradually evolving win probability | process/observation noise, filter |
| `switching_state_space` | Abrupt shifts between several dynamics | number states, transition penalty |
| `recent_since_change` | Forget stale history after detected shift | posterior/change confidence threshold |
| `arima_indicator` | Predict category-indicator time series | p/d/q capped, missing-tick semantics |
| `sarima_indicator` | Genuine periodicity exists | justified season/order only; not default |

Bayesian Online Changepoint Detection models uncertainty about time since last change; foundational source [R3]. Do not treat it as proof the simulator actually changes according to its assumed hazard model.

## 5.4 Family 3: cross-machine / latent episode models

| Candidate | Hypothesis | Search dimensions |
|---|---|---|
| `peer_history_features` | Sibling recent frequencies add information | lookback, type strata, recency |
| `peer_lag_interactions` | Target responds to peer histories at exact lags | lag 1-8, pair interactions, sign |
| `episode_random_effects` | Shared within-episode factor helps | prior scale, pooling strength |
| `dynamic_factor` | Low-dimensional shared episode state drives eight machines | rank, forgetting, state noise |
| `multivariate_hmm` | Shared hidden regimes influence multiple machines | 2-4 states, emission pooling |
| `vector_autoregression_indicators` | Lagged peer categories co-predict outcomes | lag and ridge regularization |
| `factor_augmented_var` | Combine shared latent factor and local lag dynamics | rank, lag, shrinkage |
| `cross_machine_changepoint` | Episodes exhibit synchronized regime changes | joint threshold, lag tolerance |
| `graph_attention_small` | Learn variable peer relevance | tiny architecture; P3 data-limited |

**Potential failure:** fixed `m000` suffix across episodes is not persistent identity. Use an exchangeable or type-relative peer treatment unless an invariant positional meaning is demonstrated in the organizer's data documentation. Design negative controls that permute peer positions within an episode where appropriate.

## 5.5 Family 4: payout-size geometry and latent mixture identification

| Candidate | Question | Search dimensions |
|---|---|---|
| `learned_size_regimes_2` | Can training-only data estimate current fixed shapes? | prior, likelihood, blend |
| `size_regimes_K` | Is K=1/2/3 more credible than two fixed shapes? | K, Dirichlet prior, model selection |
| `low_rank_size_mixture` | Do conditional size vectors lie on low-dimensional manifold? | rank / simplex-constrained factorization |
| `logistic_normal_size` | Are conditional size probabilities smoothly correlated? | covariance prior / process noise |
| `size_changepoint` | Do payout-size regimes change abruptly? | change hazard, smoothing |
| `joint_win_size_latent_state` | Shared latent mechanism affects win and size | latent states and regularization |

**Avoid misleading evaluation:** existing `SIZE_REGIMES` code comments indicate target-derived constants. Public validation used to derive those arrays is already exposed. Re-estimation from permitted train outcomes and out-of-fold validation of new mixture structure is scientifically cleaner; do not silently label inherited arrays independent.

## 5.6 Family 5: generic supervised ML

- Regularized binary/multinomial logistic; elastic net / sparse interactions; GAM/EBM; shallow classification trees; random forest/ExtraTrees; CatBoost; XGBoost; LightGBM; scikit-learn `HistGradientBoostingClassifier`; kernel/nearest-neighbor similarities; small MLP/GRU/TCN as late challengers; carefully constrained attention or Deep Sets for peers as P3.
- Common search axes: objective (log loss/Brier where supported), class weighting, regularization strength, depth/leaf size, boosting rounds, learning rate, subsampling, feature mask, episode-weighting, label source, calibration, and seed.
- `predict_proba` must map exactly to all five target categories, even if some rare categories are absent from a training fold; install a fixed class mapping and a safe prior fallback.
- For sampled-label fits, one-hot Brier is proper *in expectation*. Training with cross entropy is also a proper learning objective but may weight rare noisy outcomes differently; final selection should use the actual relevant held-out probability metric.

## 5.7 Family 6: calibration, combinations, and uncertainty

- Fixed 2-4-way convex mixture, optimized nonnegative weights; logit pooling (guard against overconfidence); temperature scaling, binary Platt/isotonic where enough independent support, vector/Dirichlet calibration; Bayesian model averaging; risk-aware shrinkage toward robust type prior; soft condition-aware mixture-of-experts trained on **observable** conditions predictors; online per-episode expert weighting; ensemble weight uncertainty / conservative regularization.
- Any trained stacker or gate must use genuine **out-of-fold base predictions** for its training rows when evaluating on held-out data, not the same models' in-sample fit outputs. Otherwise its apparent uplift is biased.
- One-hot historical supervision plus true-vector validation must be tracked separately. No oracle condition label can enter final test inference.

## 5.8 Exploratory statistical analysis (not necessarily predictors)

- Categorical association (chi-square / likelihood ratio, small-sample caveats); cross-tab counts and confidence intervals; mutual information/conditional MI with smoothing; autocorrelation and runs tests; Bayesian posterior predictive checks; stationarity/change diagnostics; cross-correlation and lagged dependence; JS/KL/Hellinger distances; singular-value decomposition of public true-vector geometry; calibration plots per type/condition; leave-one-feature-family-out ablation and grouped permutation importance; repeated-seed variance and paired episode bootstrap.
- These are **tools for discovering or falsifying mechanisms**, not promises that every metric should become an input feature.

---

# 6. Search design: complete coverage, bounded computation, and statistical discipline

## 6.1 Why the full Cartesian product breaks down

Example *illustration only*: 20 binary feature switches give `2^20 = 1,048,576` subsets. If each is paired with 5 model families, 8 hyperparameter configs, 3 adaptation policies and 2 calibrators, the search already exceeds 250 million combinations before folds and seeds. Many combinations are illegal, redundant, or statistically unjustifiable. No practical warehouse technology removes that combinatorial or multiple-comparison cost.

The invariant should be **complete experiment *describability* and auditable combinatorial coverage**, not compulsory execution of every theoretical combination.

## 6.2 Search stages

**Stage 0 — protected champion / scorer:** Freeze, reproduce and audit current JAEGERS. No broad search until release integrity.  
**Stage 1 — feature leakage / data sanity:** Build as-of Gold parity tests, episode-fold manifest and 3-10 smoke trials; prove `feature=False` actually removes all its columns/encodings.  
**Stage 2 — mechanism-first screens:** Explicit model variants: current champion ablations, Dirichlet, recency, lag pairs, signal head, peer features; single-family and targeted pairwise tests on fixed grouped folds.  
**Stage 3 — pairwise covering array:** Cover all *legal* pairs of feature switches/model structure choices; record coverage percentage per factor pair, not just number of trials. NIST supports t-way coverage as a design/measurement concept. [R1]  
**Stage 4 — conditional Optuna / random search:** Tune only leading families with registered conditional spaces; cap wall time, model complexity, and validation target exposure; use true score only for a limited set of finalists.  
**Stage 5 — diversity-based ensemble:** Select complementary predictions from strong and structurally different candidates. Use OOF stacking, constrained weights and per-condition catastrophe checks.  
**Stage 6 — reserved confirmation:** One predeclared finalist comparison on the best available not-yet-used episode groups. Label already-seen validation accurately; future fresh adaptation provides a different distribution, not guaranteed evidence of main generalization.  
**Stage 7 — freeze and test:** Cold offline reproduction, no live cloud dependency, human-controlled submit.

## 6.3 Search objective should reflect data context

- **Training grouped CV:** minimize mean sampled-label multiclass Brier, with episode/condition balance where defined and statistically valid; never synthesize an official `R` without true probability targets and correct reference denominators.
- **Public validation:** compute **exact** `R` against actual true probability vectors using official scorer; report four condition-specific ratios and provenance. This is a model-selection measure, not an untouched final score if used repeatedly.
- **Operational guardrails:** maximum per-condition regression, runtime, RAM, calibration, failed fits, and package complexity.
- **Multiobjective exploration:** optional Pareto front of lower loss, lower runtime, simpler model; do not combine incomparable metric sources in one objective.

Conservative champion-promotion policy: no material score degradation on any condition beyond a predeclared tolerance; confirm improvement on matched folds and episode bootstrap; reject score spikes driven by one episode or one random seed; verify stability under allowed missingness and transition changes; freeze if deadline risk.

## 6.4 Candidate count and cost estimation

Before any sweep, compile:

```
valid_trial_count
rejected_illegal_count_by_reason
exact_duplicate_count
estimated_feature_build_cost
estimated_fit_cost = sum(runtime_estimate_by_model_family * folds * seeds)
expected_prediction_artifact_bytes
parallel_worker_caps
validation_target_exposures_scheduled
```

Runtime estimates must initially be **unknown**, then fit from measured smoke trials; never invent fixed throughput. Use progressive/partial budgets only when smaller training budgets predict full-budget ranking meaningfully. An early-pruning score across too few episodes can be unstable for rare 20x events or rare regimes.

## 6.5 Trial planner pseudocode (interface sketch)

```python
def compile_study(study_spec, model_registry, feature_registry, source_manifest):
    validate_known_keys(study_spec)
    assert_source_and_split_hashes_exist(study_spec)
    options = enumerate_or_sample_structured_choices(study_spec)
    for candidate in options:
        if not compatible(candidate, model_registry, feature_registry):
            record_compile_rejection(candidate, reason="compatibility")
            continue
        canonical = resolve_and_canonicalize(candidate)
        candidate_hash = sha256_json(canonical)
        if trial_result_already_exists_and_hashes_validate(candidate_hash):
            record_deduplication(candidate_hash)
            continue
        yield candidate_hash, canonical

# The coordinator then atomically registers trial records and grants work leases.
# Workers never choose their own held-out evaluation episodes or pull evaluator targets.
```

## 6.6 Trial state machine and queue correctness

```text
DRAFT -> COMPILED -> QUEUED -> LEASED -> RUNNING
                                      |      |
                                      |      +-> SUCCEEDED
                                      |      +-> PRUNED
                                      |      +-> FAILED / INVALID / TIMEOUT
                                      +-> lease expiry -> RETRYABLE -> QUEUED
```

Each attempt stores `worker_id`, `lease_token`, `lease_expires_at`, heartbeat, resource allocation, actual start/end, exit code and stdout/stderr. A completion command must compare-and-set the latest valid lease and write **content-hashed immutable result files** before marking `SUCCEEDED`. A stale worker finishing after its lease expires must not overwrite newer attempt results. A failed trial remains auditable; retries are new attempts under the same trial ID, not erased history.

Initial local implementation can avoid distributed complexity with **one coordinator** owning SQLite writes and a bounded worker pool; switch to PostgreSQL only when multiple independent hosts actually need atomic work leasing. Optuna `JournalStorage` is a documented alternative for shared local multiprocess optimization, while official FAQ explicitly warns against concurrent SQLite Optuna usage. [D6]

---

# 7. Validation, leakage and robustness: mandatory acceptance tests

## 7.1 Evaluation split protocol

1. Declare a **canonical episode group key** including release/split/episode, freeze fold membership with SHA-256, and never split eight machines from one episode across independent train/eval folds.
2. For each outer training fold, fit **global** parameters only from training-side episodes; any historical as-of examples are constructed from these episodes with past-only features.
3. For a held-out episode, run the **same predeclared** local history adaptation as would be used for a test episode; final query label and true target remain unavailable to the fit step.
4. Use optional **within-episode walk-forward** diagnostics for drift, but do not confuse them with across-episode transfer estimates.
5. Apply preprocessing (encoder, imputer, calibrator, feature selector, scaler) using only the fold's allowed fit data. An as-of-correct row can still leak evaluation information through globally fitted transforms.
6. Public validation true vectors may be used for labeled finalist selection under organizer rules, but repeated exposure must be recorded; previously targeted regime constants cannot be called independent evaluation.
7. True conditions are used for stratifying/breakdowns when provided, **not** input to a hidden-test predictor.

## 7.2 Test matrix (must automate)

| Test ID | Fixture / assertion | Result required |
|---|---|---|
| LEAK-01 | Inject/change payout at target tick `c` | Query features at `c` unchanged |
| LEAK-02 | Inject/change payout at `c+1` | Query features at `c` unchanged |
| LEAK-03 | Same-tick sibling payout mutation | Query at `c` unchanged |
| LEAK-04 | Remove tick `c-2` | Exact lag 2 missing, never shifted to other row |
| LEAK-05 | Rename other episode's machine suffix `m000` | Original episode prediction unchanged |
| LEAK-06 | Change query-time signal, regenerate historical pseudo-rows | Historical feature columns unchanged / absent signal; actual query feature can change |
| LEAK-07 | Add validation target file to training path | Fit component cannot access it by default; exposure gate required |
| LEAK-08 | Force true condition to a different label | Hidden-test prediction unchanged if only condition truth changes |
| LEAK-09 | Fit scaler/encoder across all folds intentionally | Leakage detector catches train-fold violation |
| DATA-01 | Duplicate query ID/history key | Fatal schema error |
| DATA-02 | Missing tick vs zero-payout tick | Distinct masks/features |
| DATA-03 | Invalid payout/category/tick/type | Fatal schema error |
| DATA-04 | Reorder CSV rows/episode order | Same per-query probability after normalization |
| DATA-05 | Change source byte with same filename | Cache key invalidated |
| REG-01 | Unknown model/feature flag | Compiler hard reject |
| REG-02 | Incompatible feature/model context | Compiler hard reject before worker |
| REG-03 | Disable one feature group | All relevant model input columns removed |
| TRIAL-01 | Same normalized config twice | One unique trial ID; verified cache reuse |
| TRIAL-02 | Crash worker after writing artifacts but before DB commit | Retry/reconcile without overwritten success |
| TRIAL-03 | Stale lease completion | Rejected; attempts remain auditable |
| SCORE-01 | Compare organizer official validation scorer on golden fixture | Exact matching loss ratios / points |
| SCORE-02 | Public test has no true targets | No numeric 'hidden-test score' generated |
| SCORE-03 | Five-vector finite/valid/order/normalization | Every returned row valid |
| SCORE-04 | Empty rare class in train fold | Still emits all five class probabilities via validated fallback |
| RUN-01 | Two independent same-config executions | Deterministic within documented tolerance |
| RUN-02 | Cold offline ZIP replay under source resource limits | Matches CSV after normalization <= `1e-8` per probability |
| RUN-03 | Missing wheel / unsupported platform requirement | Release blocked, no silent pip install at inference |

## 7.3 Episode bootstrap and comparison statistics

Store per-query and per-episode loss for each candidate and the frozen champion. For true-vector validation, compare paired per-episode differences within each condition, then aggregate with the same condition/reference weights as official score. Resample **whole episodes**, stratified by condition, not individual machine queries or overlapping pseudo-rows. Report observed mean/median improvement, interval and number of episodes whose error increases, plus top tail regressions. Dependence between adaptive models and resampled episodes requires cautious interpretation; a bootstrap interval is diagnostic, not a mathematical guarantee of hidden-test uplift.

## 7.4 Null controls and mechanism falsification

- Shuffle machine histories within an episode while preserving marginal payouts, where the null test is scientifically meaningful; true lag structure should degrade.
- Permute signal on training episodes *only* in an experimental diagnostic; signal-dependent improvement should weaken if informative.
- Permute sibling relationships within valid episode groups; a meaningful peer mechanism should degrade under broken alignment.
- Replace exact lag-2 with naive second-most-recent row on sparse histories; this should be caught as a deliberately bad implementation.
- Freeze current champion with and without stacking/size-experts/peer boost, changing only one mechanism per paired test.

Never use diagnostic nulls as a back door for repeatedly tuning toward a supposedly held-out final audit.

---

# 8. Reproducible experiment artifact contract

## 8.1 Every trial must save

```yaml
trial_id: "<actual content-based SHA256>"
study_id: "<registered study>"
status: "SUCCEEDED|FAILED|TIMEOUT|PRUNED|CANCELLED|INVALID"
source:
  repository_commit: "<actual full SHA>"
  dirty_tree_digest: null
  raw_manifest_sha256: "<actual>"
  training_supervision: "historical_asof|sampled_query|public_validation_true_target"
  historical_signal_policy: "omitted|proved_historical"
  validation_target_exposure: false
  split_manifest_sha256: "<actual>"
  feature_set_sha256: "<actual>"
model:
  family: "<registered adapter>"
  config_sha256: "<actual>"
  learned_state_artifact_sha256: "<actual or null>"
environment:
  python: "<actual>"
  lock_sha256: "<actual>"
  cpu: "<actual>"
  os: "<actual>"
evaluation:
  source: "sampled_outcome_group_cv|public_true_vector_validation|test_format_only"
  organizer_R: null        # null unless actually computable
  organizer_points: null   # null unless actually computed
  per_condition_ratios: null
  per_episode_artifact: "<uri>"
  bootstrap_summary_artifact: "<uri>"
resources:
  wall_seconds: null
  peak_memory_mib: null
artifacts:
  predictions_sha256: null
  stdout_sha256: null
  stderr_sha256: null
  model_sha256: null
error: null
```

For every trial, preserve attempted configurations and failures. The run metadata schema should be checked before any MLflow mirror. Large config, full prediction rows and model file should be logged as content-addressed **artifacts**; MLflow tags/metrics provide a lightweight index.

## 8.2 MLflow mirror pattern

```python
# Example API use; not executed and requires a configured/authorized tracking server.
import mlflow

with mlflow.start_run(run_name=trial_id[:12]):
    mlflow.set_tags({
        "trial_id": trial_id,
        "source_hash": source_hash,
        "feature_hash": feature_hash,
        "metric_source": evaluation_source,
        "validation_exposed": str(validation_exposed).lower(),
    })
    mlflow.log_param("model_family", model_family)
    # Log ONLY real measured metrics with correct source and level:
    if measured_R is not None:
        mlflow.log_metric("public_validation_R", measured_R)
    mlflow.log_artifact(resolved_config_path)
    mlflow.log_artifact(per_episode_metrics_path)
    mlflow.log_artifact(predictions_path)
```

Use Databricks workspace tracking only when authorized. No credentials/API keys in repo, ZIP, logs or shared screenshots. Avoid emitting thousands of per-row metrics as separate MLflow metric steps; store them in a Parquet artifact and query with DuckDB/Databricks SQL.

## 8.3 Canonical reports / SQL queries

Each study produces:

- `study_summary.md`: goals, source hashes, protocol, candidate count, attempted/succeeded/failed, unchanged champion, selected/not-selected and why.
- `trial_leaderboard.parquet`: comparable trials only, split/provenance tags, score direction, uncertainty.
- `condition_error.parquet`: one row per trial-condition with actual numerator, reference denominator, ratio and episode count.
- `paired_delta.parquet`: trial vs champion by episode and condition.
- `feature_coverage.json`: feature masks tested, valid pairs covered, invalid pairs excluded with reasons.
- `resource_report.json`: runtimes, memory, cost and failures by model family.
- `repro_report.json`: exact environment and hashes for promoted trial.

Never display a single leaderboard that mixes sampled-label Brier (lower better), official validation points (higher better) and generic accuracy into one ranked numeric metric. Partition by evaluation provenance.

---

# 9. Codex-ready implementation directory and work packages

## 9.1 Proposed tree (additive; **not currently present as a completed platform**)

```text
Jaeger_Main/House_Edge/
  AGENTS.md                         # existing scoped rules; do not replace
  jaegers_entry/                     # existing champion; freeze until verified
  experiments/
    __init__.py
    contracts.py                     # typed domain and schema validators
    manifests.py                     # raw source and snapshot SHA contracts
    registry/
      features.yaml                  # feature names, contexts, dependencies
      models.yaml                    # families, adapters, hyperparams
      constraints.yaml               # legal combinations and exclusions
    feature_factory.py               # canonical as-of Python implementation
    feature_cache.py                 # hash-indexed query/pseudo cache
    splits.py                        # grouped episode manifest / CV
    adapters/
      interface.py
      baselines.py
      dirichlet.py
      contextual_experts.py
      changepoints.py
      lag_rules.py
      boosting.py
      ensembles.py
    compiler.py                      # grid / pairwise / random / TPE config planning
    queue.py                         # single-writer local lease protocol
    workers.py                       # isolated CPU trial execution
    scoring.py                       # organizer scorer parity wrapper
    evaluate.py                      # provenance-aware evaluation
    promote.py                       # strict champion + offline preflight
    cli.py
  warehouse/
    schemas/
      bronze.sql
      silver.sql
      gold.sql
      trials.sql
    duckdb/
      ingest.py
      materialize.py
      build_views.py
    databricks/
      bronze_ingest.py
      silver_validate.py
      gold_features.py
      parity_check.py
      mlflow_mirror.py
      jobs/                       # optional declarative bundles later
  configs/
    smoke.yaml
    mechanism_screen.yaml
    pairing_coverage.yaml
    optuna_focused.yaml
    adaptation.yaml
  tests/
    test_source_contracts.py
    test_asof_leakage.py
    test_signal_contexts.py
    test_sparse_ticks.py
    test_group_splits.py
    test_gold_parity.py
    test_model_registry.py
    test_config_compiler.py
    test_trial_idempotency.py
    test_lease_recovery.py
    test_official_score_parity.py
    test_probability_simplex.py
    test_final_offline_reproduction.py
  docs/
    EXPERIMENT_FACTORY_README.md
    DATA_DICTIONARY.md
    WAREHOUSE_TABLES.md
    RESULTS_AND_EXPOSURE.md
    CHAMPION_DECISION.md
  run_records/                       # gitignored
  immutable_artifacts/               # gitignored / managed backup
```

**Do not scaffold all files immediately.** Implement a small vertical slice, test it, then add registered families and cloud extensions incrementally. Keep no model-learning code in `warehouse` and no Databricks imports in the official `jaegers_entry` package.

## 9.2 CLI design

```bash
# All subcommands below are SPECIFIED INTERFACES, NOT IMPLEMENTED COMMANDS.
he sources verify --round main --manifest sources/main.json
he warehouse ingest --backend duckdb --round main
he features build --spec configs/features_v1.yaml --context query_cutoff
he features build --spec configs/features_v1.yaml --context historical_asof
he features parity --round main --sample-manifest tests/parity_samples.json
he splits make --policy episode_grouped --seed 42 --output data/splits/main.json
he study compile --spec configs/mechanism_screen.yaml --dry-run
he study coverage --spec configs/pairing_coverage.yaml --level pairwise
he study run --spec configs/smoke.yaml --workers 1
he study resume --study-id main_smoke_v1
he study status --study-id main_smoke_v1
he study report --study-id main_smoke_v1 --baseline frozen_jaegers
he trial inspect --id <full_trial_id>
he trial replay --id <full_trial_id> --offline
he promote --trial-id <full_trial_id> --dry-run
he release validate --round main --candidate <full_trial_id>
```

All commands should show proposed/executed/blocked status, actual source hashes and failures. A `--dry-run` must not enqueue trials or write outside a safe manifest directory. `promote` never uploads anything; human chooses and uploads final artifacts.

## 9.3 Implementation issue backlog

| ID | P | Dependencies | Deliverable / acceptance tests |
|---|---|---|---|
| WH-00 | P0 | none | Read live local repo instructions and actual HEAD/dirty tree. Existing champion snapshotted; status recorded. **PLAN ONLY before human approval.** |
| WH-01 | P0 | WH-00 | Independently reproduce champion; scorer parity; actual current score/condition ratios or honest blocker. |
| WH-02 | P0 | WH-00 | Historical signal and validation-target exposure audited; no-signal challenger planned; guarded model-data contexts. |
| WH-03 | P0 | WH-01 | Offline CSV/ZIP requirements, Python3.13 pin/wheel preflight, byte/numeric reproduction and hashes; human release gate. |
| WH-04 | P1 | WH-00 | Source snapshot manifests, schema assertions, immutable round/split namespaces; corruption tests. |
| WH-05 | P1 | WH-04 | Episode grouped fold manifests, current correct evaluator source split and score provenance. |
| WH-06 | P1 | WH-04,05 | As-of feature builder: 1 query feature + 1 historical pseudo-example + exact lag/missingness and signal tests. |
| WH-07 | P1 | WH-06 | DuckDB/Parquet Gold cache with reproducible key; reuse only identical sources/builders. |
| WH-08 | P1 | WH-05,06 | Model registry + 2 adapters (frozen champion and hierarchical categorical baseline), 5-vector contracts. |
| WH-09 | P1 | WH-07,08 | Study compiler: finite grid, conditional validity, duplicate detection, deterministic count, 3 smoke trials. |
| WH-10 | P1 | WH-09 | Durable local trial ledger + single coordinator, replay/retry, crash and lease tests. |
| WH-11 | P1 | WH-10 | Paired per-episode error reports, group bootstrap, model-selection exposure gates. |
| WH-12 | P2 | WH-09,11 | Pairwise covering arrays + full combinatorial coverage report, constraints and cost preflight. |
| WH-13 | P2 | WH-10,11 | Optuna TPE conditional search; safe local storage and external worker integration. |
| WH-14 | P2 | WH-06,08 | Model additions: lag-rule Bayesian posterior, BOCPD, peer latent factors; each with targeted test. |
| WH-15 | P2 | WH-04,06 | Databricks Bronze/Silver/Gold Delta implementation; query/pseudo as-of parity with local engine. |
| WH-16 | P2 | WH-10,15 | MLflow tracking mirror and 1 genuine run comparison; source/score hashes remain authoritative. |
| WH-17 | P2 | WH-09,15,16 | Optional metadata-driven Databricks `For each` job, account quota safeguards, handoff artifact URI. |
| WH-18 | P3 | WH-10,13 | PostgreSQL multi-host leases and Optuna RDB; only if team needs independent multi-machine workers. |
| WH-19 | P3 | WH-11,14 | Safe OOF model mixtures and calibration; any score gain must survive held-out episodes. |
| WH-20 | P0 at adaptation release | WH-03 | Fresh adaptation source/round, run fallback, limited refit, separate offline CSV/ZIP, actual receipt. |

**Acceptance invariant across every issue:** exact commands and evidence logged; no Hitachi modifications; no code claims unsupported by actual execution; no secret validation/test truth in model inputs; no automatic upload or replacement of validated champion.

## 9.4 Four-person ownership (suggestion)

- **Release and scorer owner:** WH-00/01/03/20; validation/report acceptance and human-facing release ledger. This is the mandatory critical path.
- **Statistics and leakage owner:** WH-02/05/06/11; historical signal and regime-constant exposure; rigorous grouped metrics.
- **Experiment engine owner:** WH-08/09/10/12/13/14; model registry, combinatoric planner, scheduler, adapters.
- **Data and Databricks owner:** WH-04/07/15/16/17; Bronze-Silver-Gold, local parity and sponsor evidence. Coordinate feature interface with statistics owner.

One branch/worktree per owner and no simultaneous edits to `jaegers_entry/jaeger_model.py` or `params.json`. A code owner must verify local instructions, not just this plan.

---

# 10. Databricks specific implementation and proof of value

## 10.1 Sponsor vertical slice, minimal but authentic

1. **Ingest:** register original organizer files and hashes; upload a permitted public subset; Bronze Delta tables with type assumptions documented.
2. **Validate:** Silver schema contracts, episode counts, uniqueness, as-of safety checks; emit a machine-readable data-quality report.
3. **Build features:** Gold `query_features` for at least one feature family and `historical_asof` for at least one pseudo-example family using PySpark/SQL. Show source tick < target and masks for missing exact lags.
4. **Parity:** deterministic fixture of query IDs, including sparse history and cross-peer cases; compare Databricks output to local canonical feature builder column-for-column (float tolerance explicitly defined, missingness exact).
5. **Experiment:** run at least one **genuine** baseline-vs-challenger comparison using Gold and log params/metrics/artifacts to MLflow. Do not manufacture an uplift or imply Spark is faster on tiny data.
6. **Explain improvement:** evidence of lineage, reproducibility, easier team comparison, data-quality discovery, or reusable features—supported with actual demos/screenshots/logs, not a marketing claim.
7. **Export:** final inference must work with no Databricks runtime/API/internet. Cloud results may inform an offline-frozen model if organizer rules allow all source material.

## 10.2 Metadata-driven Databricks job shape

```text
Job: house_edge_research_study
  Task 1: verify_release_manifest_and_schema
  Task 2: build_or_read_gold_feature_snapshot
  Task 3: compile_study -> writes manifest file / trial IDs
  Task 4: For each trial_id (bounded concurrency and quota)
            nested task: execute_trial_from_immutable_manifest
  Task 5: reconcile_results_and_hashes
  Task 6: produce_study_scorecard_and_mlflow_links
```

According to current Databricks docs, `For each` accepts JSON inputs or upstream task values; UI input limit and task-value limits mean passing a **trial ID or manifest URI**, not every resolved candidate config inline. On Free Edition never configure concurrency above available account limits; for a high-dimensional sweep use batches across scheduled runs and record queued vs completed count. [D2]

## 10.3 Collaboration and governance

- Treat the workspace as shared research, not the sole source of model source code; Python modules and configs live in Git.
- Consider Declarative Automation Bundles later to define jobs and deployment resources as code; confirm the workspace supports the selected features before relying on them. [D3]
- MLflow experiment = a collection of model runs; `run_id` in MLflow is **not** the canonical trial's content hash. Attach `trial_id` as tag and verify one-to-one association.
- Storage quota / retention: retain own immutable source files, important per-query predictions, and frozen artifacts independently. Delta time travel and MLflow platform run retention may not keep old assets forever.
- Separately tag `model_fit_on_validation_targets`, `prior_validation_inspection`, and `metric_source` to prevent score laundering.
- No public sharing of restricted artifacts without verifying organizer rules, team permission and source visibility.

---

# 11. Release, runtime and failure response

## 11.1 Runtime and output contract (from checked organizer kit; recheck live rules)

- Final code ZIP: root `README.md`, `reproduce.json`, executable command, pinned extra dependencies if used; exact model/feature files, no external network/API calls during inference.
- Source guide documents **Python 3.13**, **2 CPU**, **16 GiB**, **30-minute wall-time**, bounded scratch/output, CSV up to 10 MB and ZIP up to 100 MB in the 60/40 kit; other participant source differs on some logistics. Confirm exact effective restrictions with staff.
- CSV exactly the 1,536 main test query IDs or the new adaptation test query IDs, once each, ordered probabilities 0/1/2/5/20; finite probabilities sum to one within 1e-6.
- Cold reproduction from extracted ZIP + organizer input directories with numeric per-probability agreement within `1e-8` after normalization, under a network-disabled environment. Pin compatible Linux/Python wheels; never assume a package is installed because it exists on a teammate laptop.
- Keep SHA256 of actual intended/saved CSV and ZIP and the actual human submission receipt. Source kit says the latest accepted response supersedes previous response even if its file checks fail; never automatically resubmit.

## 11.2 Fail closed

The compiler/runner should refuse to start a trial if: raw/source version is ambiguous; split manifest missing; target visibility policy ambiguous; model/feature not registered; unknown config field; known future-leak feature dependency; invalid class mapping; insufficient documented resources; time quota and budget exceeded; expected artifacts not writable. **A failure is a logged failure, not a zero score or a silent fallback.**

The promoter should refuse candidate release if: scorer cannot be reproduced; test CSV malformed; validation source/method ambiguous; current champion not frozen; different code/config predicts different output; dependency wheels not validated; offline replay fails; ZIP wrong root; original code changed outside declared review; human upload not authorized.

---

# 12. Immediate plan-only Codex prompt

> **ROLE:** JAEGERS House Edge data/experimentation architect. **MODE: PLAN ONLY. NO EDITS OR INSTALLS.**  
> First read the repo's actual `Jaeger_Main/House_Edge/AGENTS.md`, `docs/PLAN_GATES.md`, `docs/CURRENT_STATE.md`, `docs/VALIDATION_PROTOCOL.md`, `docs/DATABRICKS_PLAN.md`, `docs/ENGINEERING_SPEC.md`, and inspect the actual local Git status, branch and current source files. Public GitHub HEAD advanced to at least `39086b8` during this handoff, while some docs still describe the earlier `b78abe75` snapshot; determine the actual local state instead of assuming either is current. The score `55.12/60` is only a commit-message public-validation claim; reproduce it, don't promote it as fact.  
> Treat the existing `jaegers_entry/` champion as protected. Distinguish P0 release work from P1/P2 research. Audit historical pseudo-row use of cutoff-time `signal`, validation-derived `SIZE_REGIMES`, missing NumPy/sklearn dependency pins, official scorer and final CSV/ZIP reproduction. Do not touch Hitachi, do not push/commit/upload, and do not launch broad experiments.  
> Next inspect this `JAEGERS_House_Edge_Warehouse_Experiment_Factory_Implementation_Handoff_v7.md`. Produce: (1) a repository-diff-free implementation plan with 3–5 vertical milestones; (2) exact file-level changes for the first approved slice; (3) data/entity schema and explicit source/target permission boundaries; (4) a test list for Gold as-of parity, grouped CV, experiment compiler dedupe and queue safety; (5) local/Databricks environment requirements; (6) dependency/time risks and a human approval gate before each phase.  
> After human approval only, implement the smallest testable vertical slice: source manifest + 1 query feature + 1 valid as-of feature + 1 grouped split + frozen champion and simple Dirichlet adapters + exact scorer + 3 smoke trials + immutable trial ledger. Do not scaffold the entire model zoo or deploy the warehouse as the first coding action. State exact commands/results and PASS/FAIL/BLOCKED. Keep cloud optional and official inference offline.

---

# 13. Research references and evidence hierarchy

### Primary challenge/project sources (source-derived facts)

- [P1] JAEGERS House Edge repository and code: https://github.com/AsvM45/jaegers/tree/main/Jaeger_Main/House_Edge
- [P2] Scoped `AGENTS.md`: https://github.com/AsvM45/jaegers/blob/main/Jaeger_Main/House_Edge/AGENTS.md
- [P3] Source `RULES.md`: https://github.com/AsvM45/jaegers/blob/main/Jaeger_Main/House_Edge/RULES.md
- [P4] `docs/VALIDATION_PROTOCOL.md`: https://github.com/AsvM45/jaegers/blob/main/docs/VALIDATION_PROTOCOL.md
- [P5] `docs/DATABRICKS_PLAN.md`: https://github.com/AsvM45/jaegers/blob/main/docs/DATABRICKS_PLAN.md
- [P6] `docs/PLAN_GATES.md`: https://github.com/AsvM45/jaegers/blob/main/docs/PLAN_GATES.md
- [P7] `docs/ENGINEERING_SPEC.md`: https://github.com/AsvM45/jaegers/blob/main/docs/ENGINEERING_SPEC.md
- [P8] Score-bearing commit b78abe75: https://github.com/AsvM45/jaegers/commit/b78abe75db15688e652b30b9d5388a151f2b7acd
- [P9] Newer `agent and ai infra` commit 39086b8: https://github.com/AsvM45/jaegers/commit/39086b8273581df4bd44f08c9072cb5a9095e97f
- [P10] Google Drive JAEGERS Implementation Architecture v6: https://drive.google.com/file/d/18vEcQSrW0_pZSDyuMC-C4-SbUnFH8s6A/view
- [P11] Uploaded conversation exports are historical continuity evidence; not current execution artifacts.

### Current platform documentation (externally verified during this task)

- [D1] Databricks Free Edition limitations (quota, jobs, serverless): https://docs.databricks.com/aws/en/getting-started/free-edition-limitations
- [D2] Lakeflow Jobs `For each`: https://docs.databricks.com/aws/en/jobs/tasks/for-each
- [D3] Declarative Automation Bundles: https://docs.databricks.com/aws/en/dev-tools/bundles/
- [D4] Delta Lake fundamentals and Change Data Feed: https://docs.delta.io/ and https://docs.delta.io/delta-change-data-feed/
- [D5] MLflow Tracking, Databricks-hosted tracking and backend stores: https://docs.databricks.com/aws/en/mlflow/tracking ; https://mlflow.org/docs/latest/tracking/ ; https://mlflow.org/docs/latest/tracking/backend-stores/
- [D6] Optuna distributed study and SQLite caveats / ask-tell APIs: https://optuna.readthedocs.io/en/stable/tutorial/10_key_features/004_distributed.html ; https://optuna.readthedocs.io/en/stable/faq.html ; https://optuna.readthedocs.io/en/stable/reference/generated/optuna.study.Study.html ; https://optuna.readthedocs.io/en/stable/reference/generated/optuna.storages.RDBStorage.html
- [D7] DuckDB Parquet capabilities: https://duckdb.org/docs/data/parquet
- [D8] Ray Tune scheduler concepts (optional later): https://docs.ray.io/en/latest/tune/key-concepts.html

### Mathematical/scientific research

- [R1] NIST, *Combinatorial Coverage Measurement* (pairwise/t-way coverage): https://www.nist.gov/publications/combinatorial-coverage-measurement
- [R2] Willems, Shtarkov & Tjalkens, *The Context-Tree Weighting Method: Basic Properties*, IEEE Trans. Info. Theory (1995): https://research.tue.nl/en/publications/the-context-tree-weighting-method-basic-properties/ ; general finite-context extension: https://research.tue.nl/en/publications/context-weighting-for-general-finite-context-sources/
- [R3] Adams & MacKay (2007), *Bayesian Online Changepoint Detection*: https://arxiv.org/abs/0710.3742

### Evidence flags

- **SOURCE FACT:** organizer kit fields, score formula, current inspected repo contents, documented provider limitations.
- **PROPOSED ENGINEERING:** schema/table names, directory layout, model/feature registry YAML, queue and CLI, staged deployment, priorities.
- **MATHEMATICAL PRINCIPLE:** expectation identity for one-hot Brier, dependence of overlapping windows, exponential feature subset growth.
- **UNVERIFIED HYPOTHESIS:** CTW, BOCPD, symbolic lag rules, dynamic factors, learned size regimes or any new ensemble improving the competition metric.
- **UNVERIFIED EXECUTION:** no new model was run; no source changed; no Databricks warehouse was deployed; no organizer receipt/acceptance inspected. The output is a research and implementation handoff, not a fabricated achievement report.

---

# 14. Final engineering decision

**Build for combinatorial extensibility, but do not confuse exhaustive enumeration with intelligent experimentation.** The proper deliverable is a **searchable, reproducible model/feature/configuration graph** backed by immutable data and a clean evaluation protocol. Start with the existing 73-expert JAEGERS champion, fix/prove statistical and packaging risks, then launch a small vertical slice of the experiment engine. Gradually add Bayesian lag-mechanism inference, changepoint filtering, cross-machine latent states, payout-size mixtures and generic ML challengers; require every candidate to produce a valid five-vector, beat a matched baseline, survive episode-aware validation and pass cold offline reproduction.

Databricks should make the experiments **easier to reproduce, compare, share and audit**, not merely larger. Its Free Edition quotas and the small underlying dataset argue for inexpensive local model-fit parallelism first, with Delta/MLflow as a substantive, separately testable shared research layer. That architecture can later scale to genuinely exhaustive finite search studies without rebuilding the data and model contracts.
