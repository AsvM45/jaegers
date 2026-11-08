---
trigger: always_on
description: "JAEGERS Antigravity multi-agent collaboration, branch isolation, House Edge scope and evidence standards."
---

# Antigravity collaboration rules — JAEGERS

These supplement, not replace, the root and House Edge `AGENTS.md`. The existing six `.agents/skills/jaegers-*/SKILL.md` workflows are shared with Codex; load matching skills on demand.

- Read `docs/MULTI_AGENT_OWNERSHIP.md`, `docs/ANTIGRAVITY_START.md`, and the relevant GitHub issue before working. Verify actual branch, HEAD, `git status --short`, and the latest `docs/CURRENT_STATE.md`; repository snapshots can be stale.
- Default Antigravity lane: **issue #13 — read-only experiment analytics dashboard and reporting**. After it is testable, and only with approved access, consider **issue #14 — Databricks sponsor work**. Independent read-only leakage/QA review is permitted if assigned. Do not silently take ownership of Codex's tasks #1, #4, #6, #8 or human teammate issues.
- Use a **dedicated Git worktree/branch**, not the Codex agent's working directory. Coordinate any common interface with the owner before changes. No editing `jaegers_entry/`, `research/dataset.py`, `research/features.py`, `research/learners.py`, `research/models.py`, `research/metrics.py`, `research/release.py`, or `research/process.py` unless the owner explicitly delegates it.
- New work belongs in `dashboard/`, `research/analysis/antigravity_*.py`, `research/reports/`, and isolated tests or `databricks/`. Avoid modifying `Jaeger_Main/Hitachi/`.
- **Branch permission (human policy):** after a verified named #13 claim, Antigravity may write, test, commit, and push **only** its exclusive `agy` branch within the agreed file scope; it may open a PR to `main` for human review. Never push to `main`, merge/self-approve, rewrite history, or push other agents' branches. A push to `agy` is not a release approval.
- **Governance PR #23 compatibility check:** the draft collaboration gate proposes `agent/<slug>` branch names and would reject `agy` if merged unchanged. Before opening a PR, verify the current accepted policy and ask the human governance owner to document an `agy` exception or approve an explicit branch migration. Do not secretly rename or force-update `agy`.
- Do not launch expensive/full sweeps, change model promotion, alter release CSV/ZIP, contact organizers, submit entries, or spend on cloud services without approval. For ordinary isolated code/tests, work iteratively and report exact commands and results.
- Preserve split provenance: sampled-label grouped-CV Brier is not official main points; public validation is development-exposed; hidden-test truths are unavailable. For dashboards use real run artifacts; explicitly label any synthetic UI fixtures as demonstration-only.
- **Activity proof:** reservation is not a claim. Post `AGENT=ANTIGRAVITY; ISSUE=#13; WORKTREE=<actual>; BRANCH=agy; STATUS=CLAIMED; START=<time>` in #13 before editing. Include exact writable path prefixes (see governance PR #23), then progress notes, a tested commit on `agy`, and a PR for review. Never claim completion from setup alone.
- Keep progress in issue comments or a narrowly scoped handoff, not by overwriting other agents' `docs/CURRENT_STATE.md`. GitHub `#18` is the coordination board.
