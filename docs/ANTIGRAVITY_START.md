# JAEGERS — Starting Antigravity in its assigned branch

## Existing configuration

Agent **B / Antigravity** is an independent contributor like the other engineers. It reads repository/nested `AGENTS.md`, the existing `.agents/skills/` collection and `.agents/rules/antigravity-coordination.md`. Its only current implementing issue is [#13](https://github.com/AsvM45/jaegers/issues/13): read-only experiment analytics/dashboard. Issue [#14](https://github.com/AsvM45/jaegers/issues/14), the Databricks sponsor slice, is **reserved but blocked** until the necessary evidence, workspace permission and release safety exist. The human team dispatch board is [#18](https://github.com/AsvM45/jaegers/issues/18).

The remote `agy` branch **already exists**. Do not start a second agent in Codex's directory or create a fresh unrelated branch.

## PowerShell: separate worktree on the existing `agy` branch

```powershell
$repo = "C:\Users\asvat\OneDrive\Documents\GitHub\Datathon2026\jaegers"
cd $repo
git status --short
git fetch origin
git worktree list
git branch --list agy
```

If `agy` has **no local branch** and is **not already checked out** by a worktree:

```powershell
git worktree add -b agy ../jaegers-antigravity origin/agy
```

If a **local** `agy` branch already exists but has no worktree:

```powershell
git worktree add ../jaegers-antigravity agy
```

If `git worktree list` already shows an Antigravity worktree, **open that existing directory** rather than re-adding it. Never use `--force` to take someone else's worktree. Within its directory run `git branch --show-current` (must be `agy`) and `git status --short`.

Open `../jaegers-antigravity` as the workspace in the Antigravity IDE. Start the agent there. Do not assume committing agent instructions remotely actually starts a session.

## First task — implementation, not replanning

```text
You are Agent B / Antigravity, an independent JAEGERS engineering team member.
You are in your OWN Git worktree on the EXISTING branch `agy`. Verify the
branch/HEAD/status and stop if the branch or worktree isn't isolated.

Read applicable AGENTS.md, .agents/rules/antigravity-coordination.md,
docs/MULTI_AGENT_OWNERSHIP.md, docs/CURRENT_STATE.md, issues #13 and #18.
Read relevant skills only for the task. Do not take over other agents' issues.

In GitHub issue #13 post your named implementation claim with the actual
worktree path, branch `agy`, your exclusive writable file prefixes
(dashboard/ and independent dashboard-specific tests/reports), and intended
tests. Check that no other implementer already holds the claim.

Implement #13 now, in new files you own. Build a genuinely read-only
experiment registry adapter and an interactive dashboard with Streamlit/
Plotly if appropriate: runs, model comparisons, evaluation source/provenance,
per-condition errors where valid, grouped Brier, calibration, paired episode
uncertainty, feature ablations, hyperparameter exploration and failures.
Distinguish actual experiments from synthetic fixtures. Handle empty,
failed and schema-mismatched registries honestly.

Agent A owns champion, core research files and experiment registry. Obtain
a read-only trial-schema handshake from #8; while blocked, implement and test
only an adapter against a versioned, explicitly DEMO fixture. Do not edit
jaegers_entry/, existing research/*.py modules, release scripts, Hitachi,
other agents' files or docs/CURRENT_STATE.md.

Iteratively implement, run tests and fix issues. Within this user-approved
branch-level collaboration policy, commit and push ONLY scoped changes to
`agy` once tested, then open a PR targeting main for human review.
Never merge, push main, upload a competition entry, incur cloud cost or
alter other agents' work.

Important: draft governance PR #23 proposes agent/<slug> branch naming
which conflicts with existing branch `agy`. Flag this to the human owner
before opening a PR if that validation is active; do not silently rename.
Keep the issue updated with evidence, commit/PR links and blockers.

Only after #13 is reviewed and its interface is stable may you explicitly
claim #14 for Databricks, subject to workspace/cost authorization.

Start working; do not stop with another plan.
```

## Observable completion criteria

- Issue #13 shows an actual Antigravity claim with branch/worktree and allowed paths.
- `agy` contains dashboard or isolated-test commits **ahead of** `main`.
- The code runs with documented startup command and tests; any fixture is labeled DEMO.
- Issue #13 links a human-reviewable PR with scope and observed results.
- No changes to `jaegers_entry/`, shared `research/*.py`, release artifacts or `Hitachi/`.

**Governance note:** [draft PR #23](https://github.com/AsvM45/jaegers/pull/23) would require `agent/<slug>` branch naming if merged. Preserve the explicitly assigned `agy` lane until the human coordinator approves a consistent naming policy; this repository guide does not bypass an active CI gate.
