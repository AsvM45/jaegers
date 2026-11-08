# JAEGERS — Canonical ChatGPT Project Source & Decision Record

**Snapshot:** 2026-11-08, updated source reconciliation · baseline main `c11c8fedab0b`  
**Project:** TAMU Datathon 2026, JAEGERS / House Edge / Hitachi / Databricks  
**Repository:** https://github.com/AsvM45/jaegers  
**Inspected `main` commit:** `c11c8fedab0b102f939914633c106ac3fe83844a`  
**Document type:** CURATED CONTINUITY SOURCE, not a literal chat transcript or an instruction to change source files.  
**Audience:** Future ChatGPT conversations and human collaborators. For coding agents, start with the repository's `AGENTS.md`, nested instructions, and the assigned GitHub Issue instead.

> **READ THIS FIRST:** This is a time-stamped factual and decision-history summary. It is NOT live telemetry and does not prove an agent is currently executing or that an organizer accepted a submission. Before acting, query current GitHub Issues, PRs, `main` HEAD, Actions and organizer rules. Any statement below marked REPORTED, PLANNED, BLOCKED or UNVERIFIED must remain labeled that way.

## 1. Authority and minimum retrieval order

1. **Authoritative challenge rules and data:** `Jaeger_Main/House_Edge/RULES.md`, `DATA.md`, `public/metadata.json`, `check_submission.py`, `slot_forecasting/rounds.py`, `contest.py`, relevant Hitachi package, and any newer direct organizer statement. Preserve source conflicts; never assume a user-reported time changes a challenge-specific deadline.
2. **Actual implementation:** current GitHub `main`, specific feature branch where work remains unmerged, tests, run artifacts, and release hashes. Code outranks documentation, unless the issue is precisely about a documented design decision.
3. **Live team execution:** [coordination issue #18](https://github.com/AsvM45/jaegers/issues/18), [all issues](https://github.com/AsvM45/jaegers/issues), [PRs](https://github.com/AsvM45/jaegers/pulls), [Actions](https://github.com/AsvM45/jaegers/actions), [Git commit activity](https://github.com/AsvM45/jaegers/commits/main). Issue claims are NOT proof that a local process is running.
4. **Canonical technical guides:** [README](https://github.com/AsvM45/jaegers/blob/main/README.md), [CURRENT_STATE](https://github.com/AsvM45/jaegers/blob/main/docs/CURRENT_STATE.md), [system overview](https://github.com/AsvM45/jaegers/blob/main/docs/architecture/SYSTEM_OVERVIEW.md), [science/provenance](https://github.com/AsvM45/jaegers/blob/main/docs/science/EVALUATION_AND_PROVENANCE.md), [runbook](https://github.com/AsvM45/jaegers/blob/main/docs/runbooks/CI_AND_RELEASE.md), [collaboration protocol](https://github.com/AsvM45/jaegers/blob/main/docs/AGENT_COLLABORATION_PROTOCOL.md).
5. **Research concepts and historical alternatives:** `docs/research/`, and dated `docs/archive/drive/` source copies. These are ideas and old snapshots, not evidence that methods were implemented.
6. **This ChatGPT source and old exports:** interpret decisions and fill in context, never override verified current code or organizer requirements.

For a new conversation, read **sections 1–4 and 10–12** first; use the remaining sections only when relevant. Do not load the 548 KB legacy transcript by default.

## 2. User decisions and priorities, distilled from the long conversation

- **Objective:** Maximize legitimate chances of a prize while building technically serious, résumé-worthy engineering and applied mathematics. Quality, reproducibility and scientific validity matter more than superficial complexity. The four-person team can split only when an independent workstream is genuinely parallelizable and does not compromise the main submission.
- **Primary challenge choice:** House Edge probabilistic forecasting was selected after an extensive review of TAMU Datathon tracks, prizes, historical winner patterns, possible MLH sponsor stacking, and career fit. Hitachi / Hack the Highway remained a strong second challenge and subsequently developed into real separate code. H-E-B was explicitly excluded; Poker Bot was rejected as too specialized to short-deck algorithmic competition for the user's desired learning. No equal claim of completed work exists for all other tracks.
- **House Edge rationale:** A strong example of distribution forecasting, latent regimes, sequential inference, cross-machine information, calibration, uncertainty, experimental design, offline deployment and scientific ML. It aligns with applied mathematics and broader ML systems research. Poker's extremely constrained decision-time environment was less attractive to the user.
- **Experiment philosophy:** Try many model families, combinations of features, hyperparameters, preprocessing and ensembles, but only within a **well-defined, leakage-safe, reproducible and budgeted** study. Large hypothesis searches increase selection bias against repeatedly inspected public validation; grouped out-of-fold comparisons, fixed folds, negative-result logs and paired episodes are mandatory.
- **Cloud boundary:** Databricks is the collaborative ETL, experiment tracking and sponsor demonstration layer, **not** a dependency of the final offline House Edge predictor. The user has an existing **14-day competition Databricks trial**; use that rather than creating a redundant Free Edition workspace, check its spend/credit constraints, and never publish access tokens.
- **Collaboration philosophy:** Coding agents should work like accountable human engineers: one issue and named claim per active editing agent, separate branch AND physical worktree, exclusive writable paths, issue-linked PR, explicit handoff and evidence. The repo is the shared knowledge/coordination surface, not a pile of Drive PDFs and long private chat dumps.
- **GitHub consolidation decision:** Retire inactive branches **after a lossless inventory**, do not squash/force-rewrite the canonical `main` history, and preserve uncommitted/ignored experiment outputs. The desired long-term state is one canonical `main` with only short-lived active branches.
- **Documentation decision:** `docs/` plus concise README and staged Wiki are canonical human/agent reference; GitHub Issues and PRs are live execution evidence. Historical plans belong in an explicitly marked archive. Drive should become a temporary backup, not a parallel source of truth, but **must not be deleted until migration, permissions and verification are complete**.
- **Administrative judgment:** The user first chose to defer enforcing stricter branch protection. Later, a live required governance check was added by the team; see #75 and actual ruleset for current state. Do not treat earlier “0 required checks” snapshots as permanent facts.

## 3. Competition data contract and math — House Edge

### 3.1 Data objects

For each pre-generated query, predict a five-component vector in this exact order:

`query_id,p_0,p_1,p_2,p_5,p_20`

Payout classes are `{0,1,2,5,20}` times stake, and all probabilities must be finite, nonnegative and sum to 1. **The target is a probability distribution**, not a sampled next payout, expected profit, winning class, or top-1 classification accuracy.

- One **episode** contains eight potentially related machines at one episode-specific prediction cutoff.
- Reused machine suffixes in different episodes do not imply persistent machine identity.
- Machine types: `steady`, `balanced`, `jackpot`.
- Four evaluation conditions: `stable`, `short_history`, `drift`, `shared_change` (train/validation metadata; hidden on main test).
- `signal` is one of `{-1,0,1}` at the current query cutoff. The released data do not provide historical signal values at arbitrary earlier ticks. Its causal interpretation is unspecified.
- **As-of information:** for a forecast at tick `t`, target and all sibling history features must use observations at **ticks strictly smaller than t**; missing historical tick is unknown, not a zero payout, and exact lag `t−2` differs from second most recently observed row.

Main released kit in the inspected version: train **96 episodes / 768 queries**, public validation **96 / 768**, main test **192 / 1,536**. Train exposes observed query labels, validation additionally exposes true conditional five-probability targets, and test contains input histories/queries with **no true next-spin targets or conditions**. The official hidden test score cannot be computed locally.

### 3.2 Statistical objective

For prediction `p_hat` and true five-vector `p` on validation query `q`:

`L_q = Σ_k (p_hat[q,k] − p[q,k])²`

Average over eight machines per episode, then episodes per condition. Normalize each condition error `E_c` by its frozen official reference error `B_c`, average four condition ratios, and calculate `round_points = round_max_points/(1+R)`. The inspected 60/40 organizer ZIP specifies **main 60 + adaptation 40**; an older participant DOCX specifies **80/20**. **This discrepancy is unresolved absent an authoritative organizer ruling**. A score of 55.12/60 means public development validation points, not "55.12% accuracy." Sampled observed-label Brier is useful as a proper expected surrogate, not identical to finite-sample true-vector validation loss.

### 3.3 Historical pseudo-training examples vs temporal CV

A valid historical-as-of supervised row for tick `t` can use a real observed payout at `t` as its label, with features constructed strictly from earlier ticks (target and same-episode siblings). It is **not fake/synthetic data**. It may be used within allowed organizer-released histories, including query episodes, as permitted by their specific rules. The true latent probability vector at that historical tick is still unknown. Constructing many rows increases *correlated supervised data*, not the number of independent episodes.

**Creating rows ≠ evaluating rows:** rolling historical as-of construction creates data; walk-forward or expanding-window evaluation measures chronological forecasting; episode-grouped outer folds test transfer to independent scenarios. Default row-shuffled K-fold is not trustworthy for highly overlapping histories.

### 3.4 Current model architecture and known caveats

Original protected champion under `Jaeger_Main/House_Edge/jaegers_entry/`:

- **73 context experts:** context-free expert plus lag-pattern experts over lags 1–8; discounted and prior-smoothed win/loss evidence, with exact-tick missingness handling.
- Evidence-weighted expert mixture using model and same-episode sibling predictive log-likelihood.
- Win-rate `w` combined with conditional positive payout-size distribution `q`: `[1−w,w*q1,w*q2,w*q5,w*q20]`.
- Payout-size regimes / size experts, and `HistGradientBoostingClassifier` correction/stacker for win probability.
- Offline Python/NumPy/scikit-learn inference; no Databricks runtime requirement.

The often cited champion **~55.121615 / 60** is *repeatedly exposed public validation*. Another frozen CPU/Linux candidate reportedly scored approximately **55.09 / 60**. Different builds, parameters and frozen artifacts must never be conflated. Some payout-size regime templates were informed by public validation true targets, limiting independent evidence. Current historical training-row witness is marked **NOT_CERTIFIED**, because final-history coverage, a global learned expert prior and query-time signal can influence earlier pseudo-training rows. These are substantiated train/serve provenance concerns, **not proof of illicit hidden test labels or organizer disqualification**; staff interpretation remains outstanding.

## 4. Implementation and competition snapshot (verified at 2026-11-08 09:43 UTC)

- **`main`**: `c11c8fedab0b102f939914633c106ac3fe83844a`; 446 source/tree entries in recursive listing. This supersedes old Nov 7 handoffs and intermediate reports.
- **Open GitHub PRs:** 0 at inspection. **Open issues:** #5, #6, #14, #18, #65, #75. Closed issue count depends on the same time-stamped API query; never copy old issue counts from the conversation.
- **House Edge core:** champion/release, episode-grouped research registry, deterministic test suites, model challengers, ablation/negative studies, read-only Streamlit dashboard, frozen release diagnostics and independent historical-feature witness are merged. Challenger research did **not** automatically displace the champion.
- **Adaptation #6:** Grok's takeover PR #67 was merged, superseded Claude #61 closed. Orchestrator and tests merged, but **authentic adaptation kit, cold Linux adaptation CSV+ZIP and organizer receipt remain unverified** (`BLOCKED_KIT_MISSING` as of docs checkpoint). The main-round frozen pair must not be overwritten with adaptation outputs.
- **Databricks #14:** notebook/job YAML and PySpark/Delta/MLflow code merged; 49 offline/mock tests confirmed by GitHub Actions, but **real Databricks workspace execution not yet verified**. The user has a 14-day competition trial. AGY owns the live workspace pilot. Run with approved spend limits and record genuine Spark/Delta/MLflow evidence; only then claim live sponsor implementation.
- **Hitachi:** base `Jaeger_Main/Hitachi/` exists on `main`; expanded control-tower app, simulated enterprise event actions and adversarial tests live on the separate `hitachi` branch. Preserve until integrated/assessed. Never claim branch-only tests ran on `main`; current Hitachi CI may SKIP when `tower/` is absent on the checked-out branch.
- **Branch audit #65:** read-only audit merged and issue remains open; actual branch deletion awaits exact tip checks and clean worktree/owner signoff. The current remote list has many agent branches; a merged PR tip or ancestor relationship is a **retirement candidate**, not proof local untracked/ignored evidence is safely backed up.
- **Documentation #66:** wiki-level documentation branch merged in PR #72 (commit `9dcbb917...`), including architecture/science/runbooks/agent ADR; it still contains older source summaries and some stale `AGENTS.md` or issue body snapshots. Thus documentation **exists** but needs accuracy/ingestion review, not a complete rewrite from scratch.
- **Actions:** GitHub contains `agent-collaboration.yml`, `house-edge-ci.yml`, `hitachi-ci.yml`, `databricks-offline-ci.yml`, and `docs-checks.yml`. Source gating is not a real cloud Databricks run or accepted organizer receipt.
- **Admin #75:** active basic ruleset now requires `Agent ownership and concurrent-PR overlap`, but an adversarial enforcement check, potential independent approval policy, and optional UI publication remain open. An earlier policy of zero mandatory checks was superseded by actual changes.
- **Organizer submissions #5:** no independently verified main/adaptation upload receipt or actual hidden score in available GitHub evidence. Do not infer submission from a valid local file or green CI. General Devpost close time is Sunday Nov 8 **10:30 AM Central**; specific House Edge guide says main Sat Nov 7 **9 PM** / adaptation Sun Nov 8 **11 AM**. Different portals/deadlines; verify authoritative current organizers before acting.
- **Recent technical integration:** GitHub commit #74 incorporated Databricks YAML handoff; the most recent House Edge and Databricks offline workflow runs at `c11c8fed` were green. That does not establish real cloud execution.

**Critical external gates:** (a) correct official receipt and sponsor submission, (b) genuine adaptation kit and reproduction, (c) Databricks live workspace run, (d) physical worktree branch-retirement signoffs. Coding is not automatically the next highest-value activity.

## 5. Databricks plan and safe trial use

The full `Jaeger_Main/House_Edge/databricks/` source proposes Bronze raw ingestion, Silver validated/normalized episode records, Gold as-of 471-column features, real Spark feature parity checks, MLflow experiment provenance and Databricks SQL analytical dashboards. The code's marketing language (e.g. “bitwise parity,” “zero shuffle,” “production”) must be verified under actual Spark and not repeated as proven without a run ID and metrics. Its 49-test offline suite uses a mock engine; it is a useful unit/regression layer, **not** verified real cloud behavior.

User has activated the **14-day competition Databricks trial**, no separate signup needed. AGY should use a local approved authenticated workspace without sharing credentials in Git. First verify workspace host/expiration, effective allowed compute and budget, CLI authentication, `databricks bundle validate -t dev`, bundle paths/resources, then a minimal genuine Spark/Delta job. Compare sample rows and feature order/values with local NumPy/Pandas, verify cutoff and sibling episode constraints, create a real MLflow run with provenance and inspect actual SQL output. Report `LIVE_VERIFIED` only with actual job IDs, table metadata, numeric error, resource/cost usage and rerun commands; otherwise `PARTIAL` or `BLOCKED_ACCESS`. No large trial sweeps or paid overages without explicit owner approval.

The final House Edge competition inference remains fully offline; it cannot call Databricks or assume network/credentials in the organizer's sandbox.

## 6. Model exploration and engineering methodology

Historically requested families include statistical baselines, hierarchical Dirichlet/Bayesian shrinkage, ARIMA/SARIMA, Markov/HMM/AR state models, temporal drift and changepoint, cross-machine dependence/latent episode factors, tree learners (XGBoost/CatBoost where feasible), calibration, logistic and discriminative stackers, deep and probabilistic sequence approaches where justified, causal feature variants, ensemble/blend/stacking, parameter/hyperparameter interaction studies, and conditional/Optuna searches.

Design **a search grammar** covering model family × feature group(s) × interactions × transforms × training mode × hyperparameter schema × split manifest × compute budget. Encode a trial identity with code, config, dataset and fold hashes. Provide versioned results and durable failed/negative trials. Separate data engineering from experiment scheduling and evaluation. Use pairwise/covering-array sampling and staged search before combinatorial explosion. Keep any optimizer's public validation exposure count visible. Real scientific results require exact eval source, comparable episodes, uncertainty intervals and a frozen incumbent control.

Past investigations found many challengers worse than champion; examples: HMM/factorized-size candidate ~46.18/60 vs champion ~55.12/60 public validation; structural XOR/XNOR challenger reported ~+0.39 public points with grouped walk-forward Brier benefit but selection/validation caveats, **not** automatically promoted. Check source reports for current detailed trial numbers rather than assuming this summary is exhaustive.

## 7. Secondary challenge: Hitachi / Hack the Highway

This is genuinely separate from House Edge. The source includes a challenge package with enterprise data and policies, an event action tool environment, and a `tower/` control-tower style implementation on branch `hitachi`. It emphasizes agent routing, operational constraints, action correctness, knowledge graph/context, adverse event workflows, telemetry and adversarial testing. Agent reports include a 15-event trace and dozens of edge tests; they are developer evidence, **not** judging proof. Do not silently merge the `hitachi` branch into House Edge main source or treat branch-only implementation as nonexistent.

The earlier strategy analysis chose House Edge as the primary technically/statistically rich challenge, not because Hitachi lacked value; if actual award tracking matters, verify separate Hitachi submission/demo status. Do not assume other MLH sponsor combinations are automatically eligible.

## 8. Agent workflow and platform policy

Participants in the multiagent system: ChatGPT/CHAT/Codex, Claude, Grok/Cursor, Antigravity/AGY and human maintainers. Their names are *roles or claimed agent identities*, not verified independent GitHub users. Current `main` contains `AGENTS.md`, nested `AGENTS.md`, `CLAUDE.md`, `.codex`, `.agents/skills`, `.github/agents`, and platform-specific startup references.

1. Read live claim, current code, scope, and actual Git worktree state before any edit. One active editing issue per agent.
2. Branch and **physical worktree** must both be unique to the editing agent. Branch naming `agent/<name>-<issue>-<topic>` preferred.
3. Write only claimed paths; document API changes/hand-offs before overlapping another agent. Stop on conflicting active claim.
4. PR must explain actual diff, tests, provenance, negative outcomes and explicit owner. No claimed score without data.
5. Agents may commit/push their own branch per the issue's permission, but no blind merges, force-pushes, organizer submissions, hidden-data uploads, secret publication or cloud-cost actions.
6. Current GitHub governance Action checks PR metadata and overlapping paths, but cannot validate truthful human/AI identity or physical worktree isolation. An enforced required check may now block merges, but actual enforcement verification is #75.
7. GitHub Projects, Wiki and Discussions are complementary views, **not** independent authoritative duplicate task lists. Issues, PRs, and `docs/` remain canonical. Existing Wiki pages are staged in `docs/wiki/`; repository-level `has_wiki=true` is not proof published pages exist. Projects feature enabled does not prove a board is populated. Discussions currently disabled at prior check.
8. GitHub Actions value: quick PR-scoped CI, release reproducibility, offline Databricks and Hitachi tests, docs links, guarded manual real cloud checks, scheduled bounded regression. Skip unapproved expensive model sweeps and public private-data artifacts.

## 9. Shared Drive research synthesis and retirement decision

**Decision updated 2026-11-08:** the two user-authored complete Drive Markdown originals were reviewed and their unique architecture/search/materialization/test concepts integrated into [the working experiment factory specification](research/EXPERIMENT_FACTORY_v7.md) and [the current human guide](research/EXPERIMENT_FACTORY_GUIDE.md). The texts are preserved separately as dated provenance in `docs/archive/drive/`, not as operational instructions. No full personal study guide or third-party organizer kit belongs in the public repository.

The Nov 7 architecture PDF was an older descriptive state snapshot; its still-accurate ideas are represented by [current architecture](architecture/SYSTEM_OVERVIEW.md) and scientific documentation, not republished verbatim. The separate personal mathematics reference is deliberately **excluded** from GitHub and the ChatGPT project-source ZIP at the user's request.

Drive remains a temporary, read-only backup until the consolidated repository files are verified on `main`. Do not delete, share or reclassify its originals automatically.

**Wiki and Projects:** GitHub reports both repository capabilities enabled, but this connector offers no Wiki publishing or Projects v2 management actions. Pages in `docs/wiki/` are staged repo files, **not** evidence of a live Wiki. Issues #18/#5/#6/#14/#65/#75 are current execution entrypoints; do not create a second task database.


## 10. ChatGPT project source audit (23 listed file entries at snapshot)

- **Keep as authoritative primary reference:** uploaded organizer House Edge ZIP + original participant DOCX **together** (they conflict on scoring/portal), Hitachi `hack_the_highway_student_package.zip`, and optional user-supplied relevant original guides. The GitHub repo's checked-in official rules outrank secondary summaries.
- **Keep only if the project may revisit that track:** `TAMU Datathon — Build Your Own Dataset Challenge.md` and `Heads Up Participant Guide.docx` (the chosen project does not actively pursue either). Their contents should not be loaded into every House Edge chat.
- **Demote to historical archive:** `TAMU_Datathon_2026_Complete_Conversation_LLM_Export.md` (~548 KB), `House_Edge_Post_v4_Conversation_Complete_LLM_Export.md` (~61 KB), and the Nov 7 `JAEGERS_AI_Handoff_GitHub_Coordination...md` (~21 KB). They include stale project snapshots and old suggestions; useful for chronological reasoning, bad as an agent's initial instructions. The same two exports exist as repeated mounted/uploaded titles in the project view. Do not import the giant raw conversation into public GitHub as the canonical source.
- **Demote/remove from source list when possible:** 13 challenge-track screenshots, because official challenge/guide text and code are more searchable, maintainable and authoritative. Preserve privately only if an organizer screenshot supplies otherwise unavailable prize/track text.
- **Replace their role with this file:** curated, compact, source-linked, explicitly date-stamped project context. For new chats, point first to this file plus the live repository, not all legacy exports. ChatGPT project-file controls, not GitHub, govern removal from the project's attached-source list; no such removal is implied by writing a new file.

## 11. Conflict register and non-negotiable honesty

| Question | Evidence | Current interpretation |
| --- | --- | --- |
| 60/40 vs 80/20 | Technical organizer kit vs older participant DOCX | Source conflict remains unless current organizer resolves it. Do not silently pick the convenient one. |
| Main 9 PM vs overall Devpost 10:30 AM vs adaptation 11 AM | Distinct portals/guides | These are different deadlines. Devpost overall cutoff is not a main-form extension. |
| Public 55.12/60 vs frozen ~55.09/60 | Different model package/environment development evaluations | Preserve identity; never substitute hidden score or call it accuracy. |
| Is historical stacker causal? | Grok #55 witness, source/tick tests | `NOT_CERTIFIED`: historical provenance changes with post-t data; actual organizer rule decision unresolved. |
| Is Databricks deployed? | Mock/offline tests and merged code | Not proven: need real workspace job/table/MLflow run evidence. |
| Was the team submitted/accepted? | Local package / Github PRs | Not proven: require actual receipt and correct round/portal. |
| Is Hitachi merged? | `hitachi` development branch vs `main` | Expanded tower exists on separate branch; main-only check may skip. |
| Is Wiki live? | `docs/wiki` and `has_wiki=true` | Source staging exists; no verified publication to Wiki repository. |
| Are current cloud credentials available? | User has a 14-day trial | Trial availability ≠ connected authenticated Databricks workspace/job access here. |

Use evidence labels: **SOURCE**, **MERGED**, **TESTED**, **REPORTED**, **PLANNED**, **BLOCKED**, **NOT_CERTIFIED**, **SUBMITTED_WITH_RECEIPT**, **UNKNOWN**. “Tests passed” needs exact suite/runtime/commit and source. No fabricated scores, external service acceptance, PR merges, job execution or agent-run status.

## 12. New-chat operating checklist

If a user asks to continue this project:

1. Refresh main SHA and relevant issues/PRs; note what changed since this snapshot. Ignore stale branch ownership in old transcripts.
2. Identify whether this is House Edge, Hitachi, Databricks, repository operations, a cross-track strategy decision, or mathematical education. Read just the relevant code/spec, not all archived artifacts.
3. For engineering, read root+nested agent rules and exact issue first; check collaborator worktrees/claims and current branch.
4. For tests/research, distinguish `sampled-outcome grouped CV` from `true-vector public validation` from `hidden-test organizer score`; ensure episode grouping, as-of tick cutoff, hashes and uncertainty; preserve negative results and default fallback.
5. For a submission request, verify portal, deadline, exact paired files, SHA-256, Linux cold-run and receipt. Never infer success from GitHub CI.
6. For Databricks, use existing 14-day trial, verify actual host/auth/credits, keep secrets off GitHub, start with a bounded real sample, then record live provenance.
7. For source/documentation migrations, check whether the material is user-created, third-party licensed, public-safe, current, and already represented. Publish only reviewed originals or annotated extracts; do not delete Drive/project sources without verified alternative.
8. Offer precise next actions and perform available connected-app actions directly; do not repeatedly ask users for details already known from the current conversation.

## 13. Principal links

- Repo: https://github.com/AsvM45/jaegers
- Code/README: https://github.com/AsvM45/jaegers/blob/main/README.md
- Live state: https://github.com/AsvM45/jaegers/blob/main/docs/CURRENT_STATE.md
- Architecture: https://github.com/AsvM45/jaegers/blob/main/docs/architecture/SYSTEM_OVERVIEW.md
- Scientific validation: https://github.com/AsvM45/jaegers/blob/main/docs/science/EVALUATION_AND_PROVENANCE.md
- House Edge rules: https://github.com/AsvM45/jaegers/blob/main/Jaeger_Main/House_Edge/RULES.md
- Agent coordination: https://github.com/AsvM45/jaegers/issues/18
- Competition release: https://github.com/AsvM45/jaegers/issues/5
- Adaptation: https://github.com/AsvM45/jaegers/issues/6
- Databricks: https://github.com/AsvM45/jaegers/issues/14
- Branch cleanup: https://github.com/AsvM45/jaegers/issues/65
- Admin follow-up: https://github.com/AsvM45/jaegers/issues/75
- Wiki source: https://github.com/AsvM45/jaegers/tree/main/docs/wiki
- Drive legacy folder: https://drive.google.com/drive/u/0/folders/1zzGNFTYaqIsuzioLSxZVjZKqJCyJ4Mkh

---
**Provenance:** Curated from this conversation's visible user decisions, current repo reads at the SHA above, the actual Drive folder and extracted historical docs, and project-upload file inventory. It intentionally does not reconstruct every assistant turn, unobserved local run, or private organizer result. For raw chronology use the older chat exports as historical records only, never as live agent instructions.