# Antigravity startup ? JAEGERS House Edge

Read [AGENTS](../AGENTS.md), [collaboration protocol](AGENT_COLLABORATION_PROTOCOL.md), [operating policy](AGENT_OPERATING_POLICY.md), [current state](CURRENT_STATE.md), and the latest named claims on issues #13 and #18. These are the current rules; this guide does not duplicate them.

Antigravity's lane is the read-only analytics dashboard (#13). Databricks (#14) follows only after the dashboard interface is reviewed and workspace/cost access is authorized. Shared forecasting/release modules and Hitachi remain outside this lane.

## Reuse an isolated workspace

Inspect `git status --short`, `git branch --show-current`, `git worktree list` and `git branch -a` before creating anything. Reuse an existing Antigravity worktree only after confirming its owner. Do not force-add, reset or switch another agent's checkout.

The legacy `agy` branch contained startup instructions, not dashboard code. Its history is consolidated in the main-round handoff. Agree any migration with its owner; active implementation branches must follow the current `agent/...` policy and machine-readable issue claim. Do not silently rename or force-update `agy`.

If no Antigravity worktree exists, create an independently owned worktree and named feature branch from current main as described in the collaboration protocol. Open that directory in Antigravity; setup does not start an agent automatically.

## Implement and hand off

Post the actual agent, branch, worktree, exact file scope, intended tests and reviewer on #13 before editing. Use existing project skills when relevant. Obtain the read-only registry/schema handshake from #8, then implement in isolated dashboard/analytics files. Synthetic fixtures must be clearly marked DEMO; empty or incompatible registries must be reported honestly.

Show real runs, provenance, model/condition comparisons, calibration, paired uncertainty, feature ablations, runtime and failures. Keep dashboard/cloud dependencies out of the offline predictor. Commit/push only the claimed feature branch and open a tested PR; merges, organizer actions and paid cloud require human authorization.

Use issue comments for evidence and handoff. A reservation, setup document or branch does not establish that a dashboard or background agent is operational.
