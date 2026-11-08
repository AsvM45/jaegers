---
trigger: always_on
description: "JAEGERS Antigravity multi-agent collaboration, branch isolation, House Edge scope and evidence standards."
---

# Antigravity collaboration rules — JAEGERS

These supplement, not replace, the root and House Edge `AGENTS.md`. **Also read `docs/AGENT_OPERATING_POLICY.md`, `docs/AGENT_CONTEXT.md`, `docs/MULTI_AGENT_OWNERSHIP.md` and latest #18 / #13 claims before writing.** The existing six `.agents/skills/jaegers-*/SKILL.md` workflows are shared with Codex; load matching skills on demand.

- Read `docs/MULTI_AGENT_OWNERSHIP.md`, `docs/ANTIGRAVITY_START.md`, and the relevant GitHub issue before working. Verify actual branch, HEAD, `git status --short`, and the latest `docs/CURRENT_STATE.md`; repository snapshots can be stale.
- Default Antigravity lane: **issue #13 — read-only experiment analytics dashboard and reporting**. After it is testable, and only with approved access, consider **issue #14 — Databricks sponsor work**. Independent read-only leakage/QA review is permitted if assigned. Do not silently take ownership of Codex's tasks #1, #4, #6, #8 or human teammate issues.
- Use a **dedicated Git worktree/branch**, not the Codex agent's working directory. Coordinate any common interface with the owner before changes. No editing `jaegers_entry/`, `research/dataset.py`, `research/features.py`, `research/learners.py`, `research/models.py`, `research/metrics.py`, `research/release.py`, or `research/process.py` unless the owner explicitly delegates it.
- New work belongs in `dashboard/`, `research/analysis/antigravity_*.py`, `research/reports/`, and isolated tests or `databricks/`. Avoid modifying `Jaeger_Main/Hitachi/`.
- Do not launch expensive/full sweeps, change model promotion, alter release CSV/ZIP, contact organizers, submit entries, push main, merge PRs, or spend on cloud services without human approval. The claimed issue may authorize commits and PRs on Antigravity's **own dedicated feature branch**, following `docs/AGENT_OPERATING_POLICY.md`; otherwise ask the human. For ordinary isolated code/tests, work iteratively and report exact commands and results.
- Preserve split provenance: sampled-label grouped-CV Brier is not official main points; public validation is development-exposed; hidden-test truths are unavailable. For dashboards use real run artifacts; explicitly label any synthetic UI fixtures as demonstration-only.
- Keep progress in issue comments or a narrowly scoped handoff, not by overwriting other agents' `docs/CURRENT_STATE.md`. GitHub `#18` is the coordination board.

- Use the live ownership table and #18 for other lanes; older issue reservations are not current claims. Shared adapters live in `research/adapters.py` and `research/feature_api.py`; their compatibility packages remain core-owned.
- The legacy `agy` startup-only branch history is consolidated during the main-round handoff. Reuse an existing isolated worktree where appropriate, verify its owner, and agree any migration to an `agent/...` branch before editing. Setup is not proof of an active agent.
- Follow the binding collaboration protocol for named claims, explicit file scope, branch/PR metadata and CI. Preserve real evidence and obtain human authorization for merge, upload, promotion or paid resources.
