# House Edge — 10:30 AM team cutoff and round-specific release handoff

**Date/time basis:** Saturday, November 7, 2026, America/Chicago. User/team says **Sunday, November 8, 2026, at 10:30 AM Central** is the operative submission cutoff. This is **user-reported**; no new official House Edge Google Form or challenge-specific organizer amendment has been verified by the repository or this review. **Do not claim that the organizer extended the main round.**

## Critical deadline conflict — resolve at organizer Form

| Evidence | Deadline | What it can establish |
| --- | --- | --- |
| User/team update in ChatGPT, Nov 7 | **Sunday Nov 8, 10:30 AM CST** | Team's most recent operational target; **which round/portal it applies to is not established** |
| Released House Edge `Jaeger_Main/House_Edge/RULES.md` | **Main closes Sat Nov 7, 9:00 PM CST** | Version-controlled original specific challenge rule; new official amendment would supersede it |
| Same House Edge `RULES.md` | **Adaptation closes Sun Nov 8, 11:00 AM CST** | Original round-two rule; 10:30 may be a prudent early buffer |
| Public TAMU Datathon event schedule | Sunday final hackathon deadlines vary by public page, including late morning/noon | General event schedule, **not proof** that the House Edge main Google Form remains open |

**Required human decision immediately:** inspect current challenge Discord/organizer announcement and actual main/adaptation Google Form, ask organizers to clarify whether the **main forecast can still be submitted after 9 PM**, whether a new adaptation kit/form has opened, and whether **10:30 AM applies to the correct form**. Record confirmed source/time and final Form receipt privately. If main has already closed, do not assume this team's 10:30 target revives main eligibility. The latest valid pre-cutoff response counts under the original kit even if an invalid later response replaces it.

## Exact frozen files — original LOCAL checkout, not GitHub-tracked binaries

In original `jaegers` root:
- `Jaeger_Main/House_Edge/research_runs/REVIEW_MAIN_9PM/submission.csv`
- `Jaeger_Main/House_Edge/research_runs/REVIEW_MAIN_9PM/code.zip`

A secondary copy was reported in the CHAT-owned worktree at `.chat-he08/Jaeger_Main/House_Edge/research_runs/baseline-cpu-candidate/release-v2/`. These are **local `research_runs/` files ignored by Git**. A GitHub clone by itself cannot download them; no live organizer upload is established.

| File | SHA-256 | Reported size |
| --- | --- | ---: |
| `submission.csv` | `b718f2d5e14a5a508d3c6c3658259042228a7a4d38e0221513e46e5590d9babf` | 195,579 bytes |
| `code.zip` | `9a8a9e0e18a8d21d30474b3e007156c1f19be4f693dd3b2235019be830d3001f` | 8,263 bytes |

The **CPU-pinned** candidate reportedly passed two cold Linux Python 3.13 runs (same x86-64 host, different CPU policies), 1,536 unique test query IDs, zero normalized difference and byte-identical CSVs. Public validation **55.0908150083/60** is a development-exposed local score, not hidden test performance. The earlier Windows/default Linux packages **failed portability** (max errors ~0.1069/~0.0903 > tolerance 1e-8). Do not upload old failed pair, mix file versions or casually regenerate frozen source/CSV.

### Independent Windows PowerShell verification

Run from the original **`jaegers` repo root**, not another agent's worktree:

```powershell
$dir = "Jaeger_Main\House_Edge\research_runs\REVIEW_MAIN_9PM"
$csv = Join-Path $dir "submission.csv"
$zip = Join-Path $dir "code.zip"
Test-Path $csv; Test-Path $zip
Get-FileHash $csv -Algorithm SHA256
Get-FileHash $zip -Algorithm SHA256
$rows = Import-Csv $csv
"Rows: $($rows.Count)"
"Unique IDs: $(($rows.query_id | Sort-Object -Unique).Count)"
python Jaeger_Main\House_Edge\check_submission.py $csv --data Jaeger_Main\House_Edge\public --split test
```

Expected from last agent report: both files found, SHA matches table, 1,536 rows/unique IDs, official **test format checker** passes (which does **not** measure hidden-test quality). Inspect ZIP for top-level `README.md`, `reproduce.json`, `requirements.txt` and correct pinned Python 3.13 runtime dependencies. Preserve `verification.json`, `decision.json` and offline attempts in their local evidence directory; do not publish private organizer receipt.

## Model quality and validity caveats

- Protected `jaegers_entry/` is a conditional categorical probability forecaster with 73 lag-context experts, decayed/frequency shrinkage, within-episode peers, positive payout-size conditional model, and gradient-boosted win-probability stacker.
- Some historical pseudo-training features reuse final-cutoff signal, coverage or fitted expert priors; this is **train/serve skew and potential strict-as-of compliance ambiguity** under organizer `RULES.md`. The actual query-time signal is permitted, but historical per-tick signal(t) is not independently supplied. Seek authoritative organizer clarification; do not falsely certify complete causal compliance.
- Public validation `SIZE_REGIMES` and hyperparameters used true target distributions for development. This is allowed validation selection in the released kit but may overfit; 55.09 is **not** unbiased held-out performance or a leaderboard prediction.
- Different CPU execution changed the original model's forecasts much more than `1e-8`; the pinned pair is a **bounded** resolution, not an all-hardware guarantee.
- Human release approval, correct round/form, exact uploaded pair and receipt remain requirements. These cannot be inferred from passing CI.

## Continue work responsibly until the user-confirmed 10:30 target

| Priority | Exclusive owner/task | Allowed work / stop condition |
| --- | --- | --- |
| **P0** | **Human #5** | Confirm organizer cutoff/round, check exact pair hashes and Form, upload if eligible, keep actual receipt; only human can submit or replace |
| **P0** | **Cursor issue #46 (new, reserved)** | Independent **read-only** artifact/ZIP/CSV audit and optionally a **different physical host** parity test; unique new tool+test+report files only. Cursor must claim first. Do not rebuild/fix champion |
| **P1** | **CHAT issue #8** | Continue exclusive claimed portable trial-registry export contract, smoke/consumer tests, dashboard read-only handshake; no release-pair changes or unbounded sweep |
| **P1** | **Claude #2/#3/#7/#9/#17** | Review existing QA/audit/ablation PR results and outstanding organizer-signal ambiguity; no overlapping writes to CHAT core. All earlier PRs merged to main |
| **P1** | **Antigravity #13/#14** | #13 dashboard merged; real trial reader verification is worthwhile. #14 cloud Databricks requires independent claim/workspace/budget permission |
| **P2** | **Grok issue #15 (reserved)** | Original state-space/HMM study in new stat_temporal files only; avoid conflicting release compute until human confirms |
| **Round-specific** | **CHAT/Human issue #6** | Adaptation gets separate current kit, IDs, study, CSV/ZIP, scorer and receipt. Never assume main artifacts are valid for the other round |

**Maintainer protocol:** all code agents read `AGENTS.md`, `AGENT_START_HERE.md`, `docs/AGENT_COLLABORATION_PROTOCOL.md`, their issue's latest comments and issue #18. One implementing claim + one physical worktree/branch per agent. Ordinary scoped work may continue in active sessions; GitHub issues do **not** launch agents or guarantee background execution. Do not contact organizers, spend, upload, push main or self-merge without authorization.

**Update contract:** this file is a newer team handoff, not a rewrite of the official `RULES.md`. When an actual organizer amendment, uploaded Form receipt or adaptation kit appears, update issue #5 first and this dated guidance by reviewed PR. Old 9PM folder names remain preserved because source files were hashed.