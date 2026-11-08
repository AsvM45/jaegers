# Platform bootstrapping: Codex, Claude Code, Antigravity, Grok Build, Cursor

**One canonical behavioral policy:** [AGENT_OPERATING_POLICY](AGENT_OPERATING_POLICY.md). **One task source:** current issue + latest comments and [#18](https://github.com/AsvM45/jaegers/issues/18). **One compact knowledge source:** [AGENT_CONTEXT](AGENT_CONTEXT.md). **One independent working tree per editing agent**. These directions do not launch agents automatically.

## Common startup prompt (customize issue + lane)

> You are an accountable JAEGERS House Edge engineer assigned issue **#N** in lane **<A/B/C/D/E>**. First read applicable AGENTS.md, docs/AGENT_OPERATING_POLICY.md, docs/AGENT_CONTEXT.md, docs/MULTI_AGENT_OWNERSHIP.md, latest issue #N comments, #18, relevant code and organizer rules. Check branch, HEAD, dirty tree and worktree ownership. If #N is claimed by a different agent, STOP and request handoff. Post claim with exact writable/read-only paths. Implement and test the smallest complete vertical slice, fix errors, record actual evidence, and open a draft PR on your OWN feature branch only if authorized. No other lane, Hitachi edits, champion promotion, cloud spend, contest uploads or main merges. Do not merely plan; execute until your issue acceptance criteria or a real blocker.

## A — CHAT/Codex (issues #1 #4 #8 #6)

- Start in the **already claimed existing** working tree; do not recreate/reset/switch it.
- Root + nested `AGENTS.md`, `.codex/config.toml`, `.codex/tasks/*` and `.agents/skills/*` are already present. Use relevant skills when matched; do not reload entire history.
- Release `#4` takes priority over an unbounded search. Keep `research/CONTRACTS.md` API published for dashboard, Grok and Cursor; validate if the file is actually committed/current.
- Review exact permission and user instructions before committing/pushing a branch; never main/organizer submission.

## B — Google Antigravity (issue #13, later #14)

- Use existing `docs/ANTIGRAVITY_START.md` plus `.agents/rules/antigravity-coordination.md` and the dashboard skill. Own **new** `dashboard/**`, isolated tests and optional `databricks/**`.
- Start a dedicated `agent/antigravity-dashboard` worktree from a fresh base when not already present.
- Consume versioned read-only trial schema from #8; empty registry shows **no runs yet**, synthetic fixtures visibly labeled.
- No Databricks billable resources until permission and no cloud runtime dependency in final predictor.

## C — Claude Code (issues #3 #2 #7 #17 #9, already claimed; #9 PR #28)

- `CLAUDE.md` imports root AGENTS; nested House Edge AGENTS applies. `.claude/skills/` contains relevant skills.
- Existing PRs #19/#20/#21 and claimed worktrees take precedence. **Review or finish these**, do not create duplicate issue implementation.
- Scope: fresh audit, QA and additive extension files; original `jaegers_entry` and existing A `research/*.py` read-only. Hand off source-level findings with uncertainty.

## D — Grok Build (issue #15, later #12 if unclaimed)

- Official Grok Build documentation confirms **automatic support for root/nested AGENTS.md, CLAUDE.md and Claude Code instructions/skills**, so no duplicated conflicting core policy is needed; project-specific Grok skills may live in `.grok/skills/` if useful, but keep canonical text in repo docs.
- Use `docs/GROK_START.md`. Claim **#15 only** before starting; run distinct state-space/HMM/changepoint/temporal probability studies in unique `research/challengers/stat_temporal_*.py` and own tests. Claude already owns #9 with PR #28; do not duplicate its Dirichlet/Markov/decay models or rewrite shared `research/models.py`.
- Grok should produce valid five-class distributions with tested as-of features and real grouped comparisons, not speculative novelty. After #15 review, may request #12 if unclaimed; **Claude has claimed #9 and #17** and proposed [PR #22](https://github.com/AsvM45/jaegers/pull/22), so do not duplicate.

## E — Cursor (issue #16, later #10/#11)

- Cursor supports root/nested `AGENTS.md`; additionally `.cursor/rules/jaegers-agent.mdc` is present for discoverable ownership/issue reminders.
- Current #16 is **CLAIMED** on `agent/cursor-he16-ci`; do not start #10/#11 until #16 handoff and explicit issue claim.
- Cursor CI files are unique to the #16 issue. Do not edit `tests/test_temporal.py`, champion, A's runner, or Claude's QA tests in parallel.

## Evidence / session handoff template

```text
AGENT: <platform/session> | ISSUE: #N | STATUS: IN_PROGRESS / BLOCKED / READY_FOR_REVIEW
BRANCH/WORKTREE/BASE: <...> | CHANGED PATHS: <...>
DATA/CODE/SPLIT SHA: <...> | EXPOSURE: <train_sampled | public_true_target | test_format_only>
COMMANDS RUN: <...> | OBSERVED OUTPUT: <...> | FAILURES: <...>
READY PR/DIFF: <link> | NEEDS HUMAN: <specific action> | NEXT: <one bounded item>
```

## Context economy

Read your issue plus [AGENT_CONTEXT](AGENT_CONTEXT.md) first, not whole 84KB historical design or all chat exports. The detailed [research v7 reference](research/EXPERIMENT_FACTORY_v7.md) is an *archived design*, not current implementation proof. GitHub issue comments and PRs are more recent and relevant.