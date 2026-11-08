# JAEGERS House Edge ? current state

Updated: 2026-11-08T00:57:43.723584+00:00

## Ownership and source

- Execution owner: **CHAT** (ChatGPT/Codex `/root`), not Antigravity.
- Branch: `chat/house-edge-release-research-core`, tracking `origin/main`; branch base HEAD `d3a51587545443a63bf731bb318d1296fe301bec`.
- Claimed issues: [#1 freeze/reproduction](https://github.com/AsvM45/jaegers/issues/1),
  [#4 offline release](https://github.com/AsvM45/jaegers/issues/4),
  [#8 experiment core](https://github.com/AsvM45/jaegers/issues/8).
- [Coordination board](https://github.com/AsvM45/jaegers/issues/18) is authoritative for
  explicit agent claims. The shared `AsvM45` assignee does not identify an agent.
- Champion algorithm/params remain the b78abe75 implementation. User/team commits
  advanced integration HEAD during work; CHAT source publication is authorized; the exact remote commit is recorded on the claimed issues. No organizer upload was performed.

## Verified champion and release

| Evidence | Actual result |
| --- | --- |
| Runtime | CPython 3.13.18; pinned NumPy/scikit-learn/transitives installed on Windows and Linux |
| Windows official public development validation | 55.121615306141/60 |
| Linux official public development validation | 55.145824539263/60 |
| Repeat validation | Identical bytes within each tested platform |
| Main test checker | 1,536 exact query IDs; format only, no hidden score |
| Preferred Linux release | OFFLINE_PACKAGE_VERIFIED; identical cold CSV bytes, max normalized difference 0 |
| Initial Windows release | FAILED cross-platform parity (maximum difference 0.10688630903631191); do not upload |
| Automated checks | 22 tests passed at the latest pre-push check |

Preferred artifacts (ignored local files):

- `Jaeger_Main/House_Edge/research_runs/releases/main-b78abe75-linux/submission.csv`
- `Jaeger_Main/House_Edge/research_runs/releases/main-b78abe75-linux/code.zip`
- CSV SHA-256: `4579ffeaaf8f7ff46bfd0e45fad237648538f4c9065dfe79b4f6688f3f587797`
- ZIP SHA-256: `10d44b19836c42517cd302ba3ad4d6dfc7d73a755dfb2d71525f53242516defb`
- Sizes: CSV 195565 bytes; ZIP 8066 bytes.

Evidence: frozen `research_runs/champion-b78abe75/manifest.json`; platform-specific
`research_runs/reproduction-*/report.json`; preferred release `verification.json` and
`offline/attempt-0001/` logs. Paths above are relative to House Edge unless prefixed.
Cold run used Linux Bubblewrap, disabled networking, read-only code/data, two-CPU
 affinity, 16 GiB address-space limit and timeout. Scratch consumption was checked;
this older Bubblewrap does not enforce a hard aggregate 128 MiB tmpfs quota.

## Scientific limitations

- Query-time signal is copied into historical stacker rows. An executed mutation
  fixture confirms it; historical availability is unresolved, not an asserted violation.
- Final history coverage selects smoothing used at older pseudo-example ticks.
  An executed future-removal fixture exposes that dependence. The separate causal
  adapter omits signal and uses fixed smoothing; this is not a pure signal-only ablation.
- SIZE_REGIMES and model selection used public validation targets. Both platform
  scores are development-exposed, not pristine independent generalization estimates.
- Platform-dependent predictions are observed; the underlying cause is not proven.
  Generate and verify release CSVs in the target Linux environment.
- Independent QA/statistical review belongs to #2/#3. Champion not auto-promoted or replaced.

## Experiment core

- Implemented: hashed trial IDs, SQLite attempts/lease, four episode-stratified folds,
  past-only feature cache, grid/random/Optuna coordinator, worker resource bounds,
  frozen per-attempt source copies, real OOF metrics and calibration diagnostics.
- First smoke: two successes and one preserved OneDrive atomic-rename failure.
  Fixed bounded atomic retries; next smoke completed all three configurations.
- Source-isolated smoke completed three configurations; explicit resume proof PASSED:
  no new trials, no attempt changes, and completed artifact bytes unchanged.
- Read-only report smoke PASSED, including paired episode diagnostics. Grid/random/Optuna
  entrypoints exist; random/Optuna execution checks remain next.
- No 100-experiment count or completed broad research platform is claimed.
- Contracts: `research/CONTRACTS.md`; specialist features/models, dashboard and cloud
  remain other agents' lanes. Current results stay in ignored round-specific registries.

## Release/round blockers and next work

1. Finish random/Optuna smoke and update the already-published core guide with their evidence.
2. Record named handoffs and measured completion evidence on #1/#4/#8.
3. Human #5 must confirm organizer source/channel and choose/upload exact artifacts.
   No receipt or organizer acceptance is recorded. Mechanical reproduction does not
   resolve the historical-feature provenance questions.
4. Kit says main 60/adaptation 40, main Nov 7 21:00 Central, adaptation Nov 8 11:00.
   Older 80/20 guide conflict remains unresolved; no new announcement was verified.
5. Adaptation kit and Databricks workspace access are not established. No cloud
   integration, spend, hidden-test performance, or adaptation submission is claimed.

Use `VALIDATION_PROTOCOL.md` for evaluation rules, `ENGINEERING_SPEC.md` for design
constraints, and GitHub issues for the active backlog. Do not duplicate live status.
