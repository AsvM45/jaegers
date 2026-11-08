# JAEGERS — Verified current state and open delivery gates

**Live source checkpoint:** commit `9eec670c8bd3b1fcdcc67f7d376cbf316dd639a8` (Nov 8, 2026, before this documentation branch). Re-check [main](https://github.com/AsvM45/jaegers/commits/main), [issues](https://github.com/AsvM45/jaegers/issues), [PRs](https://github.com/AsvM45/jaegers/pulls), and [Actions](https://github.com/AsvM45/jaegers/actions) for changes after this checkpoint.

**Evidence labels:** `MERGED` = Git history; `TESTED` = actual specified test record; `AUTHOR-REPORTED` = not independently reproduced; `BLOCKED` = missing external dependency; `NOT_CERTIFIED` = compliance question unresolved; `SUBMITTED` would require an actual organizer receipt (not currently verified).

## Engineering snapshot

| Area | Verified state | Open gate |
| --- | --- | --- |
| House Edge champion | Existing five-probability model, offline Linux-frozen main candidate and cold-reproducibility evidence, ~55.12/60 **public development validation** for the original champion. CPU-pinned release candidate has a different reported public score (~55.09/60). | Issue [#5](https://github.com/AsvM45/jaegers/issues/5) organizer receipt, exact submission selection and as-of rule clarification remain unverified. Do not mix different runtime artifacts or claim hidden points. |
| Experiment engine | Dataset loader, episode-grouped CV, registered trials/ablation screens, negative results and challenger studies merged. | Public validation is repeatedly exposed, not independent test performance. See [evaluation science](science/EVALUATION_AND_PROVENANCE.md). |
| As-of compliance | [Independent Grok historical-feature audit](release/GROK_HISTORICAL_FEATURE_COMPLIANCE.md) merged. Evidence rating `NOT_CERTIFIED`. | Staff interpretation required on historical signal/coverage and prior construction. |
| Adaptation | Grok's takeover [PR #67](https://github.com/AsvM45/jaegers/pull/67) merged, Claude's superseded #61 closed without merging. Orchestrator, verification tests, and release blocker report merged. | [Issue #6](https://github.com/AsvM45/jaegers/issues/6) remains `BLOCKED_KIT_MISSING`: no verified new kit, Linux cold adapted CSV/ZIP, or accepted organizer receipt. |
| Dashboard | Read-only local Streamlit MVP and tests merged; registry/provenance inspection supported. | Does not establish deployment or actual contest judging. |
| Databricks sponsor | Source and mock/offline pipelines merged; 49 unit/parity/MLflow/SQL tests passed on actual GitHub Actions under Python 3.13. | [Issue #14](https://github.com/AsvM45/jaegers/issues/14) separately owns real workspace evidence, not handled in this documentation pass. |
| Hitachi | Distinct challenge source exists in main; the `hitachi` branch contains the expanded `tower/` implementation and adversarial tests. | Hitachi CI on main explicitly SKIPs until tower code exists in the checked-out ref. Do not claim branch-only tests ran on main. |
| Branch cleanup | [HE-65 audit](ops/BRANCH_CONSOLIDATION_AUDIT.md) merged read-only: 10 physical checkouts inventoried, 19 conditional review candidates at the audit timestamp; **zero approved deletions**. | [Issue #65](https://github.com/AsvM45/jaegers/issues/65) still needs owner sign-offs and fresh SHA checks. No history rewrite authorized. |
| GitHub collaboration | [HE-69 governance code](ops/PR_GOVERNANCE_RUNBOOK.md), always-on PR gate, and dedicated component CI workflows merged. | Repo ruleset may not yet require check success or non-author approval. Admin UI confirmation and an enforcement test are required. |
| Canonical documentation | Docs, agent instructions and historical source exports exist; this documentation branch is modernizing navigation and separating authoritative facts from historical designs. | [Issue #66](https://github.com/AsvM45/jaegers/issues/66) owns documentation review and Wiki mirror only. |

## Competition timing and submission distinctions

The **event-wide** TAMU Datathon Devpost cutoff is **Sunday November 8, 2026 at 10:30 AM Central** as previously verified through connected Devpost; the separate House Edge guide states **Saturday 9 PM main** and **Sunday 11 AM adaptation**. The organizer's guide/ZIP and a separate DOCX also disagree on **60/40 vs 80/20** point allocation and some upload details. Neither the event-wide deadline nor the user's reported cutoff constitutes an organizer extension of the House Edge main Form.

**No confirmed organizer submission receipt or hidden-test score is available in current repository evidence.** The frozen main CSV/ZIP are intentionally Git-ignored local files, not guaranteed retrievable through GitHub. Never publish actual private receipts/tokens, replacement credentials, hidden labels or other teams' materials.

## Validated workflows and known limitations

- Current House Edge smoke checks run on GitHub Actions with Python 3.13. More extensive registry and scientific research tests are not implied by a green smoke label.
- `Databricks offline CI` runs the 49 synthetic/local-mode tests; this does **not** validate actual Databricks compute.
- `Hitachi component CI` runs the checked-out branch's `tower/tests` suite if present, and explicitly announces `SKIP` otherwise. The full tower currently lives on the `hitachi` branch.
- `Agent ownership and concurrent-PR overlap` checks issue claims and duplicate/overlapping PRs. Ruleset requirement must be confirmed separately.
- The local launch, research APIs and release commands are described in [RESEARCH.md](../Jaeger_Main/House_Edge/RESEARCH.md), [integration contracts](../Jaeger_Main/House_Edge/research/CONTRACTS.md), and [CI/release runbook](runbooks/CI_AND_RELEASE.md).

## Historical archive (preserved, not a live status declaration)

The following block is the previous `CURRENT_STATE.md` snapshot, retained verbatim so numerical release evidence and earlier decisions are not silently discarded. Its headings and claims about unfinished PRs, active owners and dashboards have been superseded by the live checkpoint above. Do **not** use this archived section for current dispatch or deadline decisions.

---

# JAEGERS House Edge ? current release and research state

> **SUPERSEDING OPERATIONAL NOTE, Nov 7 ~8:55 PM Central:** User reports a team cutoff of **Sunday Nov 8 at 10:30 AM CST**. Source challenge `RULES.md` still states **main Sat Nov 7 9 PM; adaptation Sun Nov 8 11 AM**. A new official main-round extension has NOT been confirmed. Human must inspect current Form/Discord to determine whether main is still accepted and what 10:30 covers. This note supersedes the *working deadline assumption* in the earlier section below, **not the published organizer kit itself**. The file name `REVIEW_MAIN_9PM` is the preserved frozen artifact directory, not a deadline instruction. See [deadline and release handoff](DEADLINE_1030_HANDOFF.md), [source paths](../Jaeger_Main/House_Edge/SUBMISSION_FILES_AND_DEADLINES.md), [human release #5](https://github.com/AsvM45/jaegers/issues/5), and [Cursor #46](https://github.com/AsvM45/jaegers/issues/46). The latest dashboard integration was PR #45 at `5f3311e`; 83 dashboard tests were author-reported, not covered by standard CI. **No organizer receipt has been verified.**

Updated: 2026-11-08T02:37:04.002516+00:00

## Main-round deadline and upload candidate

Main closes November 7, 2026 at **21:00 America/Chicago** (November 8, 03:00 UTC), per the kit and human deadline confirmation. No organizer upload or receipt is recorded by CHAT.

Human review/upload folder in the original checkout:
`Jaeger_Main/House_Edge/research_runs/REVIEW_MAIN_9PM/`.
Upload the matched `submission.csv` and `code.zip` only after human release review.

| Artifact | SHA-256 | Bytes |
|---|---|---:|
| submission.csv | b718f2d5e14a5a508d3c6c3658259042228a7a4d38e0221513e46e5590d9babf | 195579 |
| code.zip | 9a8a9e0e18a8d21d30474b3e007156c1f19be4f693dd3b2235019be830d3001f | 8263 |

This candidate keeps the original champion model, predictor and parameters unchanged and pins the Linux NumPy/OpenBLAS CPU policy in `reproduce.json`. Two cold Linux x86-64 Python 3.13.18 runs, using only the seven runtime distributions, disabled network, read-only code/data, two CPUs and 16 GiB memory limits, reproduced **all 1,536 queries with identical CSV bytes and maximum probability difference 0**. The two incoming CPU policies were tested on one physical host; universal hardware/build portability is not claimed. Hard aggregate scratch quota enforcement remains unavailable.

Candidate provenance and both attempts: `.chat-he08/Jaeger_Main/House_Edge/research_runs/baseline-cpu-candidate/`. The review folder is a checksum-verified copy; CSV/ZIP are read-only. No challenger promotion is implied.

## Verified scores and failed hypotheses

All scores below use the official organizer checker on **development-exposed public validation**, not hidden test.

| Configuration/runtime | Main points / 60 | Release interpretation |
|---|---:|---|
| Original champion, Windows | 55.1216153061 | Independently reproduced; failed Linux parity |
| Original champion, Linux default CPU | 55.1458245393 | Same-environment parity passed; changed-CPU parity failed |
| Same champion, explicit Linux CPU policy | 55.0908150083 | Matched upload candidate; both cold parity checks passed |

The Windows/Linux mismatch was 0.1068863090; disabling optional NumPy CPU dispatch changed the original Linux forecasts by 0.0903333471, above the required 1e-8 tolerance. Preserve those failed packages as evidence and do not mix their files with the candidate pair. The original Linux verification pointer is FAILED. Stable expert-weight sorting did not fix platform differences and was rejected. Release tooling now invalidates stale success after a recorded failure.

## Integrated implementation and tests

- Core PR #34 merged at `940dfbf0c9efd31eb565aec5af4319e507518603`. Model, audit, QA, feature, ML, temporal, ensemble and CI branches are integrated. Remaining historical documentation/governance tips are consolidated without reverting newer content. Hitachi is unchanged.
- Python 3.13 setup, frozen source/data manifests, official reproduction/checking, ZIP staging, offline verification, grouped/as-of datasets, switchable features, serialization, deterministic/source-isolated trials, grid/random/Optuna searches, bounded processes, SQLite attempts/leases, resume proofs, OOF/calibration/paired reports are implemented.
- Compatibility packages `research.models` and `research.features` re-export existing implementations from `adapters.py` and `feature_api.py`.
- Final integrated test suite: **120 passed** in 40.39 seconds; one warning comes from the deliberate leaky-extension negative control. The QA cache regression now targets the actual feature_api.py implementation. Governance: 10 local tests passed. Core GitHub ownership and House Edge CI passed; the final consolidation PR records its own checks.
- External setup/usage guide: [RESEARCH.md](../Jaeger_Main/House_Edge/RESEARCH.md). API contract: [CONTRACTS.md](../Jaeger_Main/House_Edge/research/CONTRACTS.md).

## Research evidence and remaining work

The canonical CHAT registry has **12 completed distinct configurations across three families**, four no-rewrite resume proofs, and a retained champion decision. Grouped sampled-label Brier: champion 0.3622911451 versus best screened challenger 0.5662851961; paired delta +0.2039940510, 95% episode-bootstrap interval [0.1851518350, 0.2231266999], 96 episodes. This is not official true-vector validation loss. Peer study reports are under `research/reports/` and `research/configs/`; their runs are not counted again here.

Historical pseudo-row signal/final-history construction remains an audit finding; SIZE_REGIMES and selection used public validation targets. Human release review must account for these caveats. No hidden-test performance or organizer acceptance is knowable locally.

Broad 100+ experimentation, a verified operational dashboard, cloud integration and adaptation release are **not declared complete**. Databricks access is not established. Adaptation uses a separate released kit, history, registry and package; kit deadline is November 8 at 11:00 Central. Release selection/upload/receipt and organizer announcements remain human-owned #5; #18 holds coordination.
