> **UPDATE / ACTIVE PROJECT POLICY (Nov 7 2026):** This document is a historical planning or evidence snapshot, NOT the live multi-agent operating agreement. Read [Autonomous Engineer Policy](AGENT_OPERATING_POLICY.md), [Current Scientific Context](AGENT_CONTEXT.md), [Ownership](MULTI_AGENT_OWNERSHIP.md), [GitHub #18](https://github.com/AsvM45/jaegers/issues/18), and current PR/issue comments before implementation. New Grok/Cursor/Claude/Antigravity/CHAT issue claims supersede older owner tables. Main code/runtime truth is the actual local checkout and official organizer kit; never treat this document as a completed test or organizer receipt.

# Antigravity startup — JAEGERS House Edge

## Native compatibility (no duplicate configuration needed)

Google Antigravity **already reads** the repository and nested `AGENTS.md` files and the existing `.agents/skills/*/SKILL.md` bundles. Its own additional `.agents/rules/antigravity-coordination.md` rule supplies multi-agent lane boundaries. Use the existing six JAEGERS skills; no copies of Codex/Claude skills or extra `GEMINI.md` are required.

Docs: https://antigravity.google/docs/rules/ and https://antigravity.google/docs/skills

## Recommended start (Windows PowerShell)

1. From the existing local `jaegers` checkout, check `git status --short` and **do not discard local Codex changes**.
2. Fetch and create a separate worktree/branch, rather than opening the directory Codex is editing:

```powershell
$repo = "C:\Users\asvat\OneDrive\Documents\GitHub\Datathon2026\jaegers"
cd $repo
git fetch origin
git worktree list
git worktree add -b agent/antigravity-dashboard ../jaegers-antigravity origin/main
```

If already created, reuse it instead. Open the resulting `jaegers-antigravity` directory in the Antigravity IDE. Prefer starting its agent in `Jaeger_Main/House_Edge/` with that folder inside the worktree. The root and nested `AGENTS.md` and skills will apply. The current team coordination issue is https://github.com/AsvM45/jaegers/issues/18.

## Paste this first prompt in Antigravity

```text
You are Antigravity working in a DEDICATED JAEGERS Git worktree, separate from
the active Codex checkout. Read the applicable AGENTS.md files, the
.agent(s)/rules Antigravity collaboration rule if discovered,
docs/MULTI_AGENT_OWNERSHIP.md, docs/ANTIGRAVITY_START.md,
docs/CURRENT_STATE.md, and GitHub issues #13, #14, and #18.

Your current ownership is ISSUE #13: a read-only interactive experiment
analytics dashboard, hypothesis reporting, and comparison tools. Codex owns
release, champion, dataset/features/model adapters, and experiment registry.
Do not edit its shared files or the original jaegers_entry model.

Inspect current branch/HEAD/status and the actual research/trial schemas.
First establish a read-only data contract and build the dashboard using
isolated dashboard/ files and independently testable helpers. Use Streamlit
and Plotly if appropriate. Display model comparisons, per-condition diagnostics,
paired episode differences, calibration, feature ablations, hyperparameter
effects, failures, runtime, and metric provenance. Never fabricate performance.
If real trial results are not present, show "no runs yet" and keep any demo data
explicitly labeled synthetic.

Implement code, run genuine bounded tests, fix defects, and document
startup commands, changed paths, results, integration requirements and
blockers. After issue #13 is testable, propose the next scoped issue
(Databricks #14 only after approved workspace/cost access). Do not push,
merge, auto-submit, spend cloud money, overwrite teammates, or change Hitachi.
Do not return another long plan: start implementation within your scope.
```

## Handoff to Codex and the humans

- Send a GitHub issue #13 progress update and an own-feature-branch draft PR when the issue/human permission allows, with real tests and metrics after a tested milestone.
- Issue #14 is **separate** Databricks research; keep cloud dependencies out of submission runner.
- If you want independent read-only review instead, explicitly invoke the `jaegers-antigravity-review` skill and select a specific issue/claim.
- Keep Antigravity file ownership separate. Never use its model changes to bypass Codex's reproducibility and release gates.

**Antigravity rules are supported by the IDE, App and CLI.** In some versions UI locations differ; check the active Skills/Rules in Customizations. Do not assume installing a repo config starts or schedules an agent automatically.
