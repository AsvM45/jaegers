> **UPDATE / ACTIVE PROJECT POLICY (Nov 7 2026):** This document is a historical planning or evidence snapshot, NOT the live multi-agent operating agreement. Read [Autonomous Engineer Policy](AGENT_OPERATING_POLICY.md), [Current Scientific Context](AGENT_CONTEXT.md), [Ownership](MULTI_AGENT_OWNERSHIP.md), [GitHub #18](https://github.com/AsvM45/jaegers/issues/18), and current PR/issue comments before implementation. New Grok/Cursor/Claude/Antigravity/CHAT issue claims supersede older owner tables. Main code/runtime truth is the actual local checkout and official organizer kit; never treat this document as a completed test or organizer receipt.

# JAEGERS House Edge — Codex / Astra Engineering Specification v5

**Purpose:** a single authoritative, repo-aware, evidence-audited plan for GPT-6 Astra in PLAN MODE first and later bounded Codex implementation. This document supersedes prior v2-v4 execution plans for the inspected commit. It incorporates the two uploaded LLM conversation exports (historical summary and post-v4 clarification) but does not treat conversational summaries as current execution evidence.

**Public repo:** https://github.com/AsvM45/jaegers
**GitHub snapshot:** `b78abe75db15688e652b30b9d5388a151f2b7acd` (Nov 7 2026, 22:45:10 UTC)
**Challenge subtree:** `Jaeger_Main/House_Edge/`. **Separate untouched subtree:** `Jaeger_Main/Hitachi/`.
**Primary:** House Edge main and adaptation. **Secondary:** Databricks *only if meaningful and safe for the deadline*.
**No code changes or submissions are claimed by this specification.** The remote latest commit advertises 55.12/60 validation points; that claim was not independently reproduced here, and organizer-private test score is unavailable.

## 0. One-paragraph Astra execution contract
First use native `/plan` mode, not implementation. Inspect actual local Git branch/HEAD, dirty files, all current runtime source and organizer scorer; reconcile them against the repo snapshot and the provided documents. Treat source-only observations as hypotheses until reproduced. Propose P0 blockers, issue ownership, acceptance tests, and a staged schedule protecting today's main deadline. Do not edit, install packages, commit, push, upload, replace a teammate's code, or start a long experimental sweep until a human has approved the plan. Use `.codex/tasks/00-astra-plan-only.md` exactly for this pass.

## 1. Authority and conflict register
1. Live local checkout and released organizer code (after hash/version inspection) determine what Codex can run; public GitHub snapshot is an audit reference, not a live lock. Check local updates before edits.
2. The main kit's `RULES.md`, `public/metadata.json`, `rounds.py` all say **60 main + 40 adaptation**, main deadline Sat 2026-11-07 21:00 Central, adaptation releases then and closes Sun 2026-11-08 11:00 Central. The separate participant DOCX claims 80/20 and a different upload route. The proper reconciliation requires organizer confirmation; do not synthesize a new answer.
3. The Devpost sponsor project submission time was previously reported as 10:30 AM Sunday; reconfirm actual fields and cutoff rather than assuming adaptation's later cutoff applies.
4. Test `public/test/queries.csv` and `history.csv` already are the *real main-round test inputs*. There is no surprise new main test query set at 9 PM. Only true next-spin odds and sampled next-spin labels/conditions are hidden. The separate adaptation kit is new at 9 PM.
5. Current code's `SIZE_REGIMES` were explicitly read from **public validation true targets**, according to source comment. Such use may be allowed as model selection; it still contaminates the independence of any 55.12 validation report on those same targets. Never imply a source-governed ban without organizer evidence.

## 2. Actual current code architecture (read-only source review)
`jaegers_entry/jaeger_model.py` now implements 73 lag-pattern experts (no-lag + binary/ternary lag-one and pairs up to 8); each updates discounted win/loss context counts, maintains log likelihood of expert success, and weights in same-episode sibling-machine evidence. It models positive payout as P(win) and conditional magnitude P(size|win) using fixed machine-type-specific two-regime mixtures; new size-context experts further refine those mixtures. `learn_expert_prior` estimates global lag-expert prior from available training histories. The latest two commits added HistGradientBoosting-based stacker trained on historical observed wins, then separate prior concentration for short-history machines. `params.json` sets `stack=true` and `size_experts=true`. `predict.py` fits a stacker on `/data/train` then produces forecasts from `/data/test`, writing `query_id,p_0,p_1,p_2,p_5,p_20`.

The latest commit message says **55.12/60** on public validation, prior 54.99, prior 51.55; *these are not observed independently rerun results*. Do not infer hidden test, competition rank, score calibration, accepted upload or repeatable cold execution.

### P0 risk 1: future signal in rolling historical stacker
`predict()` builds `sig` once from each organizer query's **cutoff-time `signal`**. Inside the `collect=True` loop for historical observed tick `t`, it invokes `stack_features()` which includes this `sig` column. Data do not supply a documented historical `signal(t)` for each earlier tick. Under the strict as-of contract, that column may carry later information into the row labeled `payout(t)`. **This is a concrete source-level concern, not a proven contest-rules violation.** Experiments must test omission of historical signal, correct training/inference feature semantics, and score on grouped episodes; do not just assert the current score represents a legitimate improvement. The stacker must not be trained on historical outcomes and unsupported future query context. If historical signal is defensibly constant and known, record source proof.

### P0 risk 2: public validation target-derived regimes
Hardcoded arrays under `SIZE_REGIMES` are described as read off public validation targets. Do not use validation true vectors in a benchmark that is then claimed to be independent unseen generalization. Compare train-side-estimated regimes, inspect model selection history if available, and keep `validation_target_exposure=true` in trial records for original candidate. This is not automatic disqualification under the published kit; legality is a distinct question from unbiased evaluation.

### P0 risk 3: package drift and installed dependencies
The actual entry currently imports **NumPy and scikit-learn** (gradient boosting stacker); tracked `jaegers_entry/` has no `requirements.txt` at HEAD. Its README still states no training step, a ~5s inference, older ~51.1 validation result, and NumPy only. A valid code ZIP must have exact compatible dependency pins at the ZIP root, provided according to organizer runtime rules, and a README matching current behavior. Verify Python 3.13 wheels and offline provisioning. The contest rerun is offline for inference; Databricks, HTTP APIs or live pip installation inside `predict.py` must not be needed.

### P0 risk 4: scorer and last-response rules
Do not score with `slot_forecasting.scoring.score_predictions()` generic 0-100 diagnostic. Use `check_submission.py --split validation` / `rounds.score_round` for main 60-point R. Test checker has *no hidden target truth* and only checks schema/IDs/simplex. Latest form response received before cutoff supersedes older even if its code later fails; therefore do not send replacements based on a new commit score alone. Preserve exact actual intended CSV and ZIP bytes, hashes, verified cold reproduction and receipt.

## 3. Data and statistical target
Train: 96 episodes*8 machines = 768 queries; validation same; test 192*8=1536. Each episode is a self-contained scenario with eight related machines sharing a query cutoff. Types `steady`, `balanced`, `jackpot`; current signal `-1/0/+1` with unspecified causal meaning; conditions `stable, short_history, drift, shared_change` only public on train/validation. Episodes have no common global clock and machine suffix `m000` is not cross-episode identity.

At query `cutoff=c`, all features drawn from payouts must use **source tick <c**, including sibling machines. Exact lag `k` means `c-k`, never kth most recent observed row. Short history has 40 recent + 24 older sampled observations in this release; absent ticks are unknown not zero payout. Payout categories `0,1,2,5,20`; output finite, nonnegative and normalized.

**Official score:** for each query q, `Lq = sum_k (pred_qk - ptrue_qk)^2`; average across 8 machines in an episode, then episodes within condition. `Rc=Ec/max(Bc,1e-9)` where Bc is frozen reference true-vector loss. `R=mean(Rc across 4 conditions)`; main points `60/(1+R)`, adaptation `40/(1+R)` in current kit. This is not top-class hit accuracy, not normalized categorical cross entropy, and not expected return.

**Data distinction:** `train/labels.csv` contains observed sampled next payout, not the true conditional probabilities. `validation/targets.csv` contains true probability vectors for query cutoffs, highly informative but dangerous when over-tuned. `test/history.csv` contains *genuine earlier outcomes* and is legitimate as-of input; test's query-cutoff next payout, true five-vector and true condition are hidden. A scorer cannot judge test quality locally.

## 4. Valid historical pseudo-supervision, test-history adaptation, and CV
A derived as-of training example at an observed historical tick t is `(X[<t], y=payout[t])`: y is real observed history, not a guessed target and not the true simulator probability vector. For all sibling machines, use only ticks <t. A row for an unobserved missing tick has no label. Query-time signal is not a historical time series, so do **not** fill the current signal value into every past t without explicit provenance. Keep `machine_type` interpretation grounded as static category when supported; keep IDs as group indices rather than predictive identity shortcuts.

One-hot Brier is proper in expectation: `E(||p_hat - e_Y||² | X) = ||p_hat-p||² + 1-||p||²`. This supports learning from observed payout labels. But overlapping history windows are correlated and can't create more independent episodes, nor can Brier from sampled labels be relabeled as exact public validation R.

**Three separate operations:** (i) rolling pseudo-example construction creates legitimate supervised rows; (ii) temporal walk-forward within an episode diagnoses forward generalization under drift; (iii) episode-grouped outer folds test transfer to separate eight-machine scenarios. Apply the same predeclared local past-only adaptation to a held-out episode during evaluation that the final test predictor would use. Do not random-split machines within the same episode or order unrelated episodes globally by cutoff tick.

Test histories may also be used for episode-specific adaptation and potentially pseudo-example local learning, according to the supplied kit's organizer-released-data/past-only rule. Do not access or guess hidden query labels. Explicitly mark this as a transductive allowed-input procedure and mirror its assumptions on held-out validation episodes.

## 5. Controlled model development priorities
**A: Frozen current JAEGERS** — independently reproduce validation score and frozen release, with honest validation exposure.
**B: Leakage-ablation current stacker** — remove unsupported historical query signal (and test optional separately learned signal-aware head at final cutoff), verify grouped comparison.
**C: Historical pseudo-supervised learner** — as-of features, sampled observed outcome five-class Brier, episode-grouped cross-validation; start with smoothed categorical/penalized logistic or modest XGBoost.
**D: Explicit per-episode adaptation** — global prior updated from the held-out episode's earlier observed payouts, compare with A because A already performs local history adaptation.
**E: Robust 2-4 model convex ensemble** — weights sum to 1, compare on matched folds and per-condition errors. Never blindly ensemble overfitting.
**F: ARIMA/SARIMA/SARIMAX** — optional only when a justified temporal hypothesis exists. A scalar mean payout forecast does NOT solve a five-category probability problem. Forecast categorical indicators/compositional transforms then project to simplex, time-bound fits, preserve missingness, and validate seasonality before SARIMA.
**G: Condition classifier/gate** — only if soft probabilities improve downstream five-vector squared loss. The 64-observation fingerprint identifies short_history in current release, not necessarily adaptation; others may be weakly distinguishable.

**Statistical cautions:** Many feature toggles can yield `2^K` combinations; prioritize preregistered feature families, pair interactions, bounded Optuna or random sweeps, and paired episode-level loss. Repeated public validation search causes winner's curse. State provenance on every metric, preserve a frozen champion and reject an uplift that depends on a handful of favorable episodes.

## 6. Trial registry: exact minimal schema
```
trial_id: SHA256(canonical_config + source_hash + split_hash + seed + env_lock)
code_head: full commit SHA or dirty-tree digest
raw_data_hashes: organizer files used
round: main|adaptation
model: {family, exact params, source path}
feature_groups: enabled and disabled lists + lineage
historical_signal_policy: omitted|proved_stable|actual_historical_series
training_supervision: query_sampled_labels|asof_observed_history|public_validation_true_targets
validation_target_exposure: true|false
split_manifest_sha256: ...
evaluation_source: sampled_outcome_group_cv|public_true_probability_validation|test_format_only|organizer_hidden
per_episode_errors: artifact URI
per_condition_R: where available
score_main_60: null unless exact public_true_probability_validation computed
output_csv_sha256: ...
code_zip_sha256: ...
wall_seconds: ...
peak_memory_mib: ...
status: PENDING|RUNNING|SUCCEEDED|FAILED|TIMEOUT|CANCELLED
error: null or recorded exception
```
Every attempt is append-only, immutable per trial ID with atomic completion. Use one writer or locked SQLite metadata; no simultaneous unprotected writes to shared CSV. Preserve failed trials and configs. Audit an already-exposed public validation slice honestly; do not label it untouched. Test workers under total physical CPU/RAM; avoid nested BLAS thread oversubscription. Start with 3 cheap smoke trials rather than a 1000-trial run before the 9 PM deadline.

## 7. Release and adaptation contract
1. Check actual local HEAD and dirty edits; freeze current model copy outside Git, with configuration and source hash.
2. Independently run current `predict.py --data public --split validation --out ...`; score with **official** checker and capture per-condition ratios. Generate the **actual** main test CSV from the same source/config.
3. Reconcile historical signal and public validation target exposure before claiming robustness. If a P0 scientific fix changes predictions, compare exact current and revised candidate using grouped evaluation, with human choosing final model.
4. Pin exact NumPy and scikit-learn wheel-compatible versions, update README, and confirm organizer's offline environment can prepare them. Source ZIP root must include `README.md`,`reproduce.json`,`predict.py`,`jaeger_model.py`,`params.json`,`requirements.txt` (if required).
5. Build ZIP with original `build_entry.py`, extract clean, run `reproduce.json` command from clean environment with no runtime network and same /data scheme. Exact CSV query IDs, probabilities, 1e-8 normalized difference, 10MB/100MB limits and 30min/2CPU/16GiB caps as source dictates.
6. Hash **the actual saved/uploaded** CSV and code ZIP and keep human receipt. A local checker is only a local checker; no autonomous portal upload.
7. Main cutoff is **Sat Nov 7 9 PM Central**. At release of new round-two kit, verify metadata/hashes and redo data checks on new IDs; new 40-point adaptation entry due **Sun Nov 8 11 AM Central**. Keep main/adaptation artifacts separate. Human controls all official submissions.

## 8. Databricks / PySpark sponsor work (P2)
Databricks is notebook + Spark/PySpark distributed processing + Delta managed tables + Unity Catalog + optional MLflow model run tracking/jobs. Pandas is local in-memory DataFrame; PySpark is Python interface to Spark's (often distributed/lazy) DataFrame engine. Raw House Edge data are small; experiment parallelism is more useful than data parallelism. Sponsor evidence should be honest: ingest organizer-approved public data into Delta Bronze, typed Silver and past-only Gold features; prove parity against local Pandas; track real trials with MLflow and show actual decision impact or improved reproducibility. Do not claim speedup without benchmarking. It must not be a network dependency for official offline inference.

## 9. Astra plan-mode response contract
Provide: exact local HEAD/status and what changed since the audited public snapshot; P0 high-risk evidence matrix (signal, size constants, dependencies/README, scorer, cold package, rules/receipt); issue table with one owner and acceptance per task; top two alternative architectures and rejection reasons; tests to run first; resource and deadline stop gates; questions ONLY for organizer-only missing facts; explicit no-write confirmation. Ask approval before implementation. Do not claim independent reviewer if this is same-context adversarial review.

## 10. Four-person coordination and GitHub safety
Assign **A** release/integration/frozen artifact, **B** leakage/metrics/splits, **C** challenger ML and as-of data, **D** experiment harness/Databricks after release. Each member can work on scoped modules/configs without simultaneous edits to `jaegers_entry` or the same registry. No GitHub issues currently visible; plan-mode output is an issue proposal, not created GitHub issues. No unapproved pushes or public profile modifications. Review tracked `.idea` files later separately; do not consume cutoff time on cosmetic cleanup.

## 11. Do not do
- Don't restart at pooled_recent because an older report called it best; existing JAEGERS candidate is stronger on *development* validation (subject to audit).
- Don't treat a visible `55.12/60` commit message as a test result or contest placement.
- Don't use historical query `signal` on older ticks without proven historical availability.
- Don't move past same-episode data across train and held-out halves.
- Don't claim a `score_predictions` diagnostic 0–100 as an official round score.
- Don't put Databricks/Spark/MLflow in code ZIP unless truly supported and necessary; network-free inference is mandatory.
- Don't generate synthetic casino spins from guessed odds and describe them as independent observations.
- Don't let automated feature search tune against the 192-episode private test: targets are hidden.
- Don't do a new main submission without a clean package reproduction and exact human verification.
- Don't auto-run an implementation phase after the initial Astra plan-mode review.

## 12. Source register
- Current GitHub remote audit, main commit b78abe75...; code under `Jaeger_Main/House_Edge/jaegers_entry/` and organizer kit under `Jaeger_Main/House_Edge/`.
- Two user-provided historical exports supplied with this conversation: `TAMU_Datathon_2026_Complete_Conversation_LLM_Export(1).md` and `House_Edge_Post_v4_Conversation_Complete_LLM_Export(1).md` (archived separately; not blindly treated as live evidence).
- Original organizer 60/40 kit already tracked in repo; older uploaded DOCX conflicts as above.
- Official Codex context economy guidance: https://developers.openai.com/blog/rethinking-skills-and-prompts-for-gpt-6-astra
- Official Codex repo skill and AGENTS practices: https://developers.openai.com/blog/skills-agents-sdk
- Official plan-mode guidance: https://developers.openai.com/blog/run-long-horizon-tasks-with-codex


## 13. Precise scientific experiment design and failure modes

### 13.1 Three complementary information sources and why they are different

**Original query supervision.** The supplied `public/train/labels.csv` provides observed categories at 768 original query cutoffs. It can train a classifier on the exact feature-distribution scenario the organizer asks about, but each class label is one random draw. A model predicting category probabilities should use a proper score and not optimize only argmax accuracy. True target conditional distributions are *not* in training.

**Historical as-of observations.** A history has observed `(tick, payout)` rows. Every observed tick t can generate a potential example with response `payout[t]`, provided that *all* features depend only on inputs strictly older than t. The target at t is not synthetic, but adjacent rows share state and history; use episode-grouped fit/evaluation and avoid assuming row-level sample independence. The no-historical-signal policy is especially crucial with the current gradient-boosted stacker, where the present implementation contains final query `signal` in historical features.

**Validation true probabilities.** The release supplies 768 target probability vectors on validation. These enable the exact technical objective, and thus high power for ranking models, but using the same targets to reverse-engineer payout-regime constants and then to estimate generalization gives optimistic development scores. Clearly mark whether the validation set was used to fit model structure, constants, hyperparameters, ensemble weights or feature design. An independent estimate cannot be recovered by renaming a repeatedly inspected split 'audit'.

### 13.2 Weighting for pseudo-supervised global learning

The official objective equally weights four *conditions*, then episodes, then machines. Historical pseudo-example training may disproportionately weight long episodes or machines with more observed ticks unless corrected. Compare three weighting protocols: (1) uniform historical row as a baseline diagnostic, (2) per-machine uniform total weight, (3) per-episode uniform total weight. If condition labels are available only for fit episodes, consider class balancing within train folds but do not allow oracle test conditions. Ensure weights are computed from fit-fold data and recorded in config. Do not present a sampled-label Brier reduction as a proportional predicted official 60-point increase; the irreducible stochastic variance differs by condition.

### 13.3 Proposed training interfaces

A minimal feature row carries `episode_id`, `machine_id`, `asof_tick`, `query_cutoff`, `source_split`, `has_signal_at_asof`, `feature_schema_version`, and five target-category indicators only if the observed payout at the label tick exists. IDs and split names must remain metadata/group keys; they are generally not generalizable numeric predictive features. A `FeatureBuilder` accepts typed query/history and an explicit `asof_tick` argument and refuses source rows with tick >= asof. A `ModelAdapter.fit(X, y, weights, config)` may learn global parameters; `predict_proba(query, observed_history, config)` produces a five-vector. A separately specified `adapt_to_episode(history_before_cutoff)` can fit local state before final prediction without seeing the held-out query answer.

A generic learned model must also provide `save()/load()` or deterministically retrain in the official time budget. Avoid Python pickles from untrusted sources and record sklearn compatibility. The current JAEGERS model currently refits stacker at inference, meaning the artifact is code+config rather than a checkpoint; that is acceptable only if the exact rerun is deterministic and within organizer runtime/dependency rules.

### 13.4 Concrete model-family hypothesis matrix

| Family | What signal it could capture | Why it could fail | Entry gate |
|---|---|---|---|
| Existing 73-context experts | lag pairs, recent changes, sibling consensus | sparse context counts; validation-target regime bias | frozen exact reproduction |
| Bayesian Dirichlet with type signal | stable priors, scarce jackpots | ignores lag-sensitive switching | train-only pooled prior |
| N-gram/Markov predictor | short-lag categorical transitions | combinatorial sparsity | smoothed lag states |
| Multinomial logistic/elastic net | interpretable interactions and regularization | wrong linear logit assumptions | episode-grouped CV |
| HistGradientBoosting / XGBoost | nonlinear interactions and thresholds | future `signal` in pseudo-rows; too many overlapping samples | provenance-safe as-of rows |
| Small random forest/ExtraTrees | robust nonlinear screening | rare class calibration | Brier and simplex tests |
| ARIMA on indicator series | linear temporal dependence in a category | binary noisy series, Gaussian assumptions, missing ticks | time index and stable convergence |
| SARIMA on indicators | real periodic behavior if present | no verified seasonality; overfit short histories | training-only periodicity test |
| Hidden Markov/state-space | latent switching regimes | identifiability/fit time | tiny bounded model and comparison |
| Soft condition gate | blend sparse, drift, shared experts | 96 train episode labels with only 24/class; mistaken gate | beat fixed blend on held-out episodes |
| Convex ensemble | complementary model errors | excessive correlation/weight overfit | out-of-fold weights and robustness |

For ARIMA/SARIMA, never fit a single scalar expectation of the monetary payout and claim it predicts a full categorical distribution. Work with five event-indicator sequences, or probabilistically coherent compositional representation, then clip/project estimates into the 5-simplex and assess calibration. Capture fit failures explicitly and cap time. SARIMAX exogenous regressors must be known at the corresponding historical ticks; final query signal is not historical. One cannot fix this by forward-filling an unknown signal series.

### 13.5 Feature registry details and interactions

Every feature family needs a unique key, owner, sources, definition, allowed observation time, missingness encoding, dependency list and checkable effect on the feature matrix. Suggested families:

- `coverage`: history count, first/last observed tick, density of known ticks, missingness in lag windows and number of observations in recent windows.
- `type_context`: one-hot `steady/balanced/jackpot`, with an optional smoothed categorical prior learned from fit data; machine type itself must be treated as observable context.
- `signal_current`: current query signal; allowed only for actual organizer query prediction, not automatically for historical pseudo-rows. Train a query-supervised head if needed.
- `full_count`: counts/percent of five categories over full known historical ticks with explicit sample count and prior.
- `recent_count`: 10/20/40/80 actual-tick window counts; missing entries ignored not treated as payout zero. Require a minimum support flag.
- `ewma`: multiscale exponentially weighted five-category counts (e.g. half-lives 8/24/64), event-time convention recorded.
- `lag_values`: actual ticks c-1 through c-8 encoded into five categories plus missing flags; a missing tick cannot slip to the next observed one.
- `lag_pairs`: allowed 28 pairs of lag positions 1-8, with categorical joint contexts and regularization to avoid sparse overfitting.
- `drift`: differences in early vs recent category frequencies, recent-minus-global posteriors, changepoint scores, entropy of last window.
- `sibling`: other seven machines' recent win rates, lagged payout summaries, peer drift signatures and missing masks, all strictly before target cutoff; no cross-episode joining.
- `interactions`: `type×signal` for known query rows only; `type×recency`, `lag×type`, `drift×sibling`; feature dependencies must be enforced.

Evidence must come from paired ablation rather than tree's split importance alone. If `type×signal` changes model quality, show the per-condition impact and validation-use history. A feature may hurt raw Brier yet help score relative to a small baseline denominator in one condition; report both diagnostics clearly.

### 13.6 Explicit search economy

**No blind exhaustive search.** With 20 independent feature switches, `2^20 = 1,048,576` subsets before models, interactions, folds or seeds; the winner of a massive public validation search is likely partially selected for noise. Stages:

1. **Smoke**: three small trials (frozen champion, a no-historical-signal ablation, a simple pooled categorical model) to test framework integrity.
2. **Single groups**: one factor off/on at a time, shared folds/seeds, identify broad failures and improvement hypotheses.
3. **Small pair interactions**: only interactions with a stated mechanism and valid dependencies; count and cap them.
4. **Family screen**: representative Bayesian, lag/Markov, logistic, boosting and optionally compact AR approaches using the same fixed legal inputs.
5. **Focused Optuna**: optimize only top family/family-specific knobs under max trial/time budget; use a local SQLite study with one coordinator and at most bounded workers; no implicit network calls.
6. **Finalists**: require matched episode predictions, per-condition relative loss, paired bootstrap over episodes, reproducible runtime; select only a few.
7. **Release**: freeze and independently cold-rerun winner, never allow trial workers to overwrite the official upload path.

The script must not depend on LLMs to decide every trial. It must be deterministic/config-driven, with LLM assistance used for code changes or interpreting findings. Track failed/nonconvergent models rather than omitting them. An artifact's experiment count is not scientific evidence of generalization.

### 13.7 Example machine-readable trial configuration

```yaml
trial_name: no_historical_signal_stack_v1
baseline_ref: b78abe75... / exact champion source SHA
round: main
model_family: jaegers_hgb_stack
model_params:
  stack: true
  stack_lr: 0.05
  stack_leaves: 15
  stack_iters: 300
feature_flags:
  current_query_signal_for_final_prediction: true
  copy_current_signal_to_historical_stack_rows: false
  lag_experts: true
  sibling_evidence: true
  size_experts: true
training:
  source: organizer_train_observed_histories
  asof: strict_prior_tick
  episode_balance: uniform
validation:
  outer: grouped_by_episode
  public_true_targets: limited_finalist_selection
  expose_full_validation_score_as_independent: false
resources:
  max_workers: 1
  max_wall_seconds: 120
  no_network_at_inference: true
```

This is a **design example**, not executable code or a measured trial. Astra should reconcile actual source parameter interfaces before implementation.

### 13.8 Independent review and release confidence labels

**GitHub remote inspected** means source metadata and text were read. **Local reproduced** means a specific local environment ran the model and scorer with recorded output. **Offline verified** means a ZIP extracted and the declared reproduction command recreated numerical outputs under constrained offline conditions. **Human submitted** requires receipt/timestamp and hashes of exact bytes. **Organizer accepted** requires explicit organizer confirmation. A code source review in ChatGPT does not imply any of the latter. An adversarial review by the same assistant must be labeled same-context, not an independent model. Record strongly rejected model alternatives and rationales. One high validation score is not a robust hidden-test guarantee.
