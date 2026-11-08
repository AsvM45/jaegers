# JAEGERS — Public knowledge hub

This is the **source-controlled** wiki landing page for TAMU Datathon 2026's JAEGERS research project. The canonical implementation and documentation are reviewed in the ordinary [GitHub repository](https://github.com/AsvM45/jaegers). A separately published GitHub Wiki is an optional navigation mirror, not a second source of technical truth.

## Project areas

- [House Edge architecture and data flow](../architecture/SYSTEM_OVERVIEW.md) — five-class probability model, historical cutoffs, research registry, dashboard, releases.
- [Scientific evaluation](../science/EVALUATION_AND_PROVENANCE.md) — true-vector vs sampled-label Brier, episode grouping, public-validation exposure, historical `NOT_CERTIFIED`.
- [CI and offline release operations](../runbooks/CI_AND_RELEASE.md) — reproducible commands, CPU policy and signed-off artifacts.
- [Hitachi](../../Jaeger_Main/Hitachi/) — separate challenge; expanded `tower/` implementation resides on the [`hitachi` branch](https://github.com/AsvM45/jaegers/tree/hitachi/Jaeger_Main/Hitachi).
- [Current engineering evidence](../CURRENT_STATE.md) — dated source-backed overview with preserved historical snapshot.
- [GitHub agents and local worktrees](../agents/GITHUB_AGENTS_AND_WORKTREES.md) — cloud vs local sessions, issue claims, handoffs, approvals.

## Contributor and platform procedures

- [Root README](../../README.md), [contribution guide](../../CONTRIBUTING.md) and [security policy](../../SECURITY.md).
- [Existing collaboration protocol](../AGENT_COLLABORATION_PROTOCOL.md) — unique branch, physical worktree, named issue claim and handoff.
- [Governance runbook](../ops/PR_GOVERNANCE_RUNBOOK.md) — always-running PR gate, duplicate-merge protection and owner UI ruleset steps.
- [Branch-retirement audit](../ops/BRANCH_CONSOLIDATION_AUDIT.md) — no destructive changes authorized.
- [GitHub feature ADR](../adr/0001-github-engineering-features.md) — Projects/Actions/Wiki/Discussions/Agents/Releases decisions.
- [Live issue dispatch #18](https://github.com/AsvM45/jaegers/issues/18) — coordination and blockers, not evidence an agent is running.

## What the repository does **not** certify

Development-exposed public validation scores are not hidden contest results. A local packaging check is not an organizer receipt. An offline/mock Databricks test is not a live workspace experiment. A passing Hitachi workflow that reports SKIP did not run tower tests. Historical pseudo-training signal/prior behavior remains `NOT_CERTIFIED` pending organizer interpretation.

All pages are public: do not upload private participant data, organizer tokens, raw personal conversations or ignored experiment archives.