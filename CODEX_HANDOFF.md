# JAEGERS — Codex / CHAT current handoff entrypoint

**Binding rule:** [docs/AGENT_COLLABORATION_PROTOCOL.md](docs/AGENT_COLLABORATION_PROTOCOL.md), including machine-readable claim and required PR metadata. **Current policy:** [docs/AGENT_OPERATING_POLICY.md](docs/AGENT_OPERATING_POLICY.md) + [docs/AGENT_CONTEXT.md](docs/AGENT_CONTEXT.md) + [docs/MULTI_AGENT_OWNERSHIP.md](docs/MULTI_AGENT_OWNERSHIP.md). **Live ownership:** [GitHub #18](https://github.com/AsvM45/jaegers/issues/18), issue #1/#4/#8 claims. Repo has five distinct agent lanes including Grok and Cursor; do not take their implementation work.

The original JAEGERS House Edge predictor and `jaegers_entry/` must remain a protected fallback. Core priorities: verified 5-class official development validation score, cold offline code ZIP + CSV and human release gate #4/#5, bounded immutable trial registry #8, adaptation #6. Do not launch broad experiments near a release deadline.

CHAT owns the existing shared `research/*.py` and reportedly has local uncommitted `research/CONTRACTS.md`, `research/{registry,sweep,worker,adapters,feature_api}.py` and `chat/house-edge-release-research-core`. These are **reported in issue comments, not guaranteed remote**; inspect local checkout and preserve. Do not overwrite PRs #19–#22, Cursor's #16 or Antigravity's dashboard #13.

Start with applicable root/nested `AGENTS.md`, `docs/CURRENT_STATE.md` (dated), task-specific `.codex/tasks/` and matched `.agents/skills/`. If data conflicts, use official organizer kit and actual local code/test runs. Source hashes and score provenance required; no fake hidden-test result.

Agent is authorized for scoped local coding, dependencies and bounded tests in its own worktree; own-branch commit/push/draft PR only with issue-level permission. No main merge, organizer submission, paid resources, private data or irreversible action without human approval.

GitHub workflow including Discussions/Projects/Wiki is described in [docs/GITHUB_OPERATING_SYSTEM.md](docs/GITHUB_OPERATING_SYSTEM.md).