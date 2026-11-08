# JAEGERS — Multi-agent ownership and integration

**Read first:** [GitHub coordination issue #18](https://github.com/AsvM45/jaegers/issues/18). This table describes proposed current lanes, not verified live processes or assigned GitHub usernames. Live local checkout and team decisions take precedence.

| Lane | Default issues | Source ownership | Explicit boundaries |
| --- | --- | --- | --- |
| Codex | #1 champion freeze/reproduce; #4 offline release; #6 adaptation; #8 experiment registry | `Jaeger_Main/House_Edge/research/{freeze,reproduce,release,offline,process,dataset,features,learners,models,metrics}.py`, runner and release tools; integration | Preserve original `jaegers_entry/` until verified/human approved. No auto-upload or push. |
| Antigravity | **#13 experiment analytics/dashboard**, then #14 Databricks with approval; optional independent read-only review | **new** `dashboard/`, `research/analysis/antigravity_*.py`, `research/reports/`; isolated `databricks/` | Treat existing `research/*.py`, `jaegers_entry/`, and `docs/CURRENT_STATE.md` as read-only unless explicitly delegated. |
| Human release lead | #5 organizer verification and submission; oversight of #6 | private organizer receipts, decisions, GitHub ownership | Only authorized human can approve/execute submission or paid cloud work. |
| Teammate QA/Data | #2, #7, #16 | new isolated test and feature modules by agreement | Shared feature schema owned by current agent until handoff. |
| Teammate Stats | #3, #9, #12, #17; optional #15 | independent research challengers and audit reports | No in-place champion rewrite. |
| Teammate ML | #10, #11 and support #14 | isolated model/temporal challengers | Avoid edits to agent-owned shared adapters. |
| Claude Code | review or explicitly assigned issue | own branch/unique files only | Does not duplicate an active Codex or Antigravity issue. |

## Worktree discipline

Never run Codex and Antigravity as editing agents in one working tree. For an isolated branch:

```powershell
cd "C:\Users\asvat\OneDrive\Documents\GitHub\Datathon2026\jaegers"
git fetch origin
git worktree add -b agent/antigravity-dashboard ../jaegers-antigravity origin/main
git worktree list
```

If the branch/worktree already exists, inspect `git worktree list` and open it; do not recreate or force it.

## Integration protocol

1. Before code, announce claim on GitHub issue. Read latest `docs/CURRENT_STATE.md` and any active owner notes.
2. Agree on read-only trial result/schema contract with Codex (#8), then implement in unique paths.
3. Commit only explicitly approved, reviewed branches; propose PR to `main` for integration. Avoid auto-merges. Human release lead remains responsible for protected champion/submissions.
4. Every handoff gives exact command, commit/diff, measured tests, artifact lineage, evaluation provenance, and blockers.
5. Never check in model outputs, private credentials, organizer receipts, hidden answer data or large generated studies. Keep inference fully offline; Databricks is optional research/sponsor work.

## Immediate constraint

Main-round release risk precedes dashboards. Antigravity's local analytics work must not change the Code ZIP/CSV or consume the release owner's compute budget. Where the trial registry is not yet implemented, build only the tested read-only reader/API and clearly labeled demo UI; integrate on real artifacts once available.
