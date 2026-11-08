# JAEGERS | Repository guardrails
- Public monorepo: `Jaeger_Main/House_Edge/` and `Jaeger_Main/Hitachi/` are separate. Work only in the requested subtree. Do not alter Hitachi when solving House Edge.
- At the start of a substantive task inspect `git status --short`, branch, HEAD and relevant files; preserve teammate modifications. The public remote may be behind/ahead of the local working tree.
- Scope changes narrowly, run real checks, and report observed commands/results; never invent scores, tests, acceptance or hidden labels.
- Never push, commit, overwrite a submission, upload to organizers, publish secrets or perform irreversible actions without explicit authorization. Plan-mode tasks are read-only.
- Store no secrets, credentials, hidden evaluation outputs or private information in Git. Avoid committing generated runs or unreviewed external assets.
- For House Edge, start Codex in `Jaeger_Main/House_Edge/`; obey its nested `AGENTS.md`. Use skills only when their descriptions match the task. Long docs are reference, not mandatory reading for every edit.

- Shared agent infrastructure: Codex, Claude Code and Google Antigravity use these repository guardrails. Antigravity natively reads these `AGENTS.md` files and shared `.agents/skills/`; see `docs/ANTIGRAVITY_START.md` and `.agents/rules/antigravity-coordination.md` for its scoped lane.
- Multi-agent ownership is tracked in `docs/MULTI_AGENT_OWNERSHIP.md` and GitHub issue #18. Never have two coding agents edit the same working tree. A human-approved separate worktree/branch and an explicit file scope are required for parallel implementation.
