# JAEGERS House Edge — Shared Agent Context (current summary + historical facts)

**Audience:** all coding agents including Grok. **Review status:** facts grounded in committed repo, organizer kit, visible PR/issue discussion, and selected Library artifacts. This **does not** expose live local process state. Always inspect current HEAD and [#18](https://github.com/AsvM45/jaegers/issues/18). Further detail: [Operating policy](AGENT_OPERATING_POLICY.md), [validation protocol](VALIDATION_PROTOCOL.md), [owner map](MULTI_AGENT_OWNERSHIP.md), [artifact provenance](LIBRARY_ARTIFACTS.md).

## Objective and data

House Edge predicts a **five-class conditional payout probability vector** for gross outcomes `[0,1,2,5,20]` on each requested machine next spin. Every episode contains eight related machines at a shared cutoff. Machine types `steady/balanced/jackpot`. Each query has an observed `signal∈{-1,0,1}` at its current cutoff; the kit **does not supply historical signal(t)**. Four episode conditions: stable, short_history, drift, shared_change. True test conditions are hidden.

Main released data: train 96 episodes/768 queries with sampled query labels; validation 96/768 with sampled labels **and true five-vector targets**; test 192/1,536 with query + historical payout inputs but **no final-query truth**. Histories may be sparse (missing tick != payout zero), local cutoff 192–256, and exact lags up to 8 matter. A valid as-of training pseudo-row at observed historical tick t uses **only earlier** payout rows on target + siblings as features and the actual payout at t as its label; no current-cutoff query signal may be assumed historically available. Do not leak across episodes sharing machine-id suffix.

Submission header exactly `query_id,p_0,p_1,p_2,p_5,p_20`. Every query once, finite nonnegative probabilities summing to 1 within official tolerance. Test scorer validates format/IDs only; hidden quality is not locally observable.

## Official scoring

`L_q = sum_k (pred[q,k] - true_prob[q,k])²`. Average machine losses per episode, episode losses per condition, divide condition errors by round's frozen reference condition errors, average all four condition ratios to R. Main `points=60/(1+R)`; adaptation `40/(1+R)` **per inspected kit**. `slot_forecasting/scoring.py` computes a DIFFERENT 0–100 diagnostic; **use `rounds.py` / `check_submission.py --split validation`**. Observed-label one-hot Brier is a proper training/evaluation surrogate *in expectation*, not identical to true-vector official loss on finite data.

Older separately uploaded guide says 80/20 and different portal. A human must reconcile with organizers. Kit says main deadline **Sat Nov 7, 9PM CT**, adaptation releases then and closes **Sun Nov 8, 11AM CT**. Generic Devpost deadline may be earlier. Main latest Form response can replace an earlier valid response even if the latest is invalid. ZIP root README and `reproduce.json`, pinned dependencies, no network at prediction time, 2CPU/16GiB/30min runtime, normalized parity `1e-8`, CSV<=10MB and ZIP<=100MB per kit.

## Existing model and known caveats

Protected champion: `Jaeger_Main/House_Edge/jaegers_entry/`, expert mixture with **73 lag contexts**, weighted past evidence, episode siblings, win probability times positive-size conditional regimes, size experts, and scikit-learn histogram-gradient-boosted win stacker; NumPy and scikit-learn are used, even if old README disagrees. At source commit `b78abe75`, commit message reported ~55.12/60 public validation. Committed `docs/CURRENT_STATE.md` later reported local official development **55.121615/60** and five passing temporal tests; underlying run artifacts are gitignored and not independently rerun by this document. Preserve champion; do not infer hidden-test performance, organizer rank or accepted upload.

Claude's [#3 audit / PR #19](https://github.com/AsvM45/jaegers/pull/19) reported development public scores: champion **55.1216**, no-signal **55.0001**, causal **54.6433**, no-stacker **52.8362**; train/serve skew sources: query signal copied into old historical stack training rows, final-history nobs prior choice and expert log-prior based on final machine LL. Current test query-time signal is allowed at inference, but historical per-tick availability remains unresolved; these findings alone do not prove rule violation. `SIZE_REGIMES` came from public validation true targets; development score **not** untouched generalization. Claude QA [PR #20](https://github.com/AsvM45/jaegers/pull/20) reports 32 independent tests passing; feature contract [PR #21](https://github.com/AsvM45/jaegers/pull/21) reports 12 tests passing and new **not yet wired** `qa_size_streak` group. Results are PR-reported until reviewed/CI-verified.

## Repository implementation map and live coordination

Public main snapshot checked at `26f23435175ea71e1cb6217d15d67614e6d87792` (Nov 7 ~6:32PM CT). It includes `research/{dataset,features,learners,models,metrics,freeze,release,offline,reproduce,process}.py`, `tests/test_temporal.py`, requirements files, Linux tooling, Codex/Claude/Antigravity instructions. CHAT [#8 issue comments](https://github.com/AsvM45/jaegers/issues/8) report **uncommitted** local `research/CONTRACTS.md`, `research/{adapters,feature_api,registry,sweep,worker}.py` and a two-trial smoke plus failed attempt; these are **not yet remote default branch guarantees**. A temporary OneDrive atomic-write failure was found and a retry reportedly added, awaiting verified resume results.

Owners when reconciled (always defer to latest claim comments):
- A CHAT/Codex: #1, #4, #8, #6 (core release/registry), local branch `chat/house-edge-release-research-core` per issue.
- B Antigravity: #13 dashboard reserved; #14 Databricks after release safe, authorized workspace, and real trials.
- C Claude Code / `InTheHiggsField`: #2/#3/#7, separately claimed #17 and now #9 statistical challengers; PRs #19/#20/#21/#22 and [#28](https://github.com/AsvM45/jaegers/pull/28) are open. Issue #9 reports completed studies: Dirichlet ~30.85, decay-BMA ~30.93, Markov ~43.98 vs original champion ~55.12 official public validation, with 22 unit tests reported. These are development-exposed PR-reported results, not independently rerun. Do not duplicate #9.
- D **Grok suggested assignment**: #15 advanced temporal/state-space as first reserved issue, later #12 ensembles if still unclaimed. **#9 and #17 are already Claude-claimed (PRs #28/#22) and are not available to Grok.** **Not active/claimed until explicit claim comment**.
- E Cursor: #16 **already claimed**, later #10/#11 supervised ML/temporal only after #16 handoff and explicit re-claim. No presumption of concurrent work or of a sixth agent.
- Human lead: #5 organizer submission/receipt and #18 assignment/conflict mediation.

Current scope rules are [MULTI_AGENT_OWNERSHIP.md](MULTI_AGENT_OWNERSHIP.md); agents MUST respect unique worktrees and paths. No direct changes to `Jaeger_Main/Hitachi/`.

## Research and planned infrastructure

Existing/future Python ecosystem: Python 3.13, stdlib, NumPy, scikit-learn; optional Pandas, DuckDB, Parquet/PyArrow, Optuna, XGBoost, LightGBM, CatBoost, statsmodels, HMM/state-space models. Core aim is a *small reproducible experiment factory*: legal as-of features, episode-grouped folds, five-class adapter contract, immutable data/code/config/seed/source/feature hashes, bounded trial scheduling, failed-run preservation, per-condition official validation and sampled-label diagnostics explicitly separate, candidate champion promotion only after cold reproduction. Avoid treating many correlated historical rows as independent episodes; cap HPO, avoid repeated public-target overfit.

Analytics: read-only Streamlit/Plotly dashboard (#13), actual study provenance and paired episode diagnostics. Databricks sponsor (#14): genuine Delta Bronze/Silver/Gold, PySpark exact-tick parity vs local features, MLflow tracking of *real* runs, no cloud in offline predictor. Architecture v7 and latest human guide from ChatGPT Library are historical **design specifications**; no automatic proof they were implemented.

## Reading map (minimal context first)

| Need | First files |
|---|---|
| Current task and who owns it | [#18 board](https://github.com/AsvM45/jaegers/issues/18) + your issue comments + [ownership](MULTI_AGENT_OWNERSHIP.md) |
| Base statistical contract | `Jaeger_Main/House_Edge/RULES.md`, `DATA.md`, [VALIDATION_PROTOCOL](VALIDATION_PROTOCOL.md) |
| Current implementation | `docs/CURRENT_STATE.md` (dated report), relevant `research/*.py`, PR diffs |
| Packaging | `Jaeger_Main/House_Edge/SUBMISSION_README.md`, `build_entry.py`, `check_submission.py`, #4 |
| Experiment model research | [ENGINEERING_SPEC](ENGINEERING_SPEC.md) (older v5 design), [library artifact manifest](LIBRARY_ARTIFACTS.md), #8/#9/#10 |
| Five-agent workflow | [AGENT_OPERATING_POLICY](AGENT_OPERATING_POLICY.md), [GITHUB_OPERATING_SYSTEM](GITHUB_OPERATING_SYSTEM.md), [PLATFORM_START](PLATFORM_START.md) |
| Databricks sponsor | [DATABRICKS_PLAN](DATABRICKS_PLAN.md), issue #14; no workspace proven |
