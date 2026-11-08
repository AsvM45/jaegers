# AI engineering agents: GitHub cloud sessions and local worktrees

**Owner contract:** [`docs/AGENT_COLLABORATION_PROTOCOL.md`](../AGENT_COLLABORATION_PROTOCOL.md), [governance runbook](../ops/PR_GOVERNANCE_RUNBOOK.md), [dispatch #18](https://github.com/AsvM45/jaegers/issues/18). This guide documents capabilities, not live session telemetry.

## Two different execution planes

| GitHub Agents / Copilot cloud | Local Codex, Claude, Cursor, Grok, Antigravity |
| --- | --- |
| Launchable from repository **Agents** tab, GitHub Copilot, or eligible issue assignment | Runs in editor/CLI/on a teammate machine or another authenticated service |
| GitHub tracks its own session log, PR, cloud environment and steering | GitHub normally sees only commits, issue comments, PRs and CI; it **does not automatically see local agent sessions** |
| Uses GitHub AI credits/plan-specific agent eligibility | Uses the independently purchased/configured model or coding-tool plan |
| Eligible custom agents live under `.github/agents/*.agent.md` | Repo `AGENTS.md`, `.codex/`, `.agents/skills/`, `.claude/` etc may configure each platform |

GitHub **Pro** (repository account tier) is not the same as **Copilot Pro**. A verified Copilot Student plan has included Copilot features but **does not include third-party coding agents** according to GitHub's published plan comparison (subject to account changes). Only select actual available agents in your UI; do not infer Claude/Grok eligibility from GitHub Pro or a Student Pack.

## How to start a safe GitHub-hosted task

1. Open [repository Agents](https://github.com/AsvM45/jaegers/agents) or [GitHub Copilot sessions](https://github.com/copilot); select `AsvM45/jaegers`.
2. Choose the available agent/model and **Cloud** environment. Check usage/credit limits, repository permissions, and whether third-party apps require separate authorization.
3. Choose a narrowly scoped task whose **GitHub issue is currently unclaimed**. Do not ask GitHub Copilot to work on #65, #66, #6 or #14 while their local/remote owners have active claims.
4. Post the issue's owner/claim marker and exact writable paths, or ensure the chosen agent explicitly does this before coding. Request one PR, not direct main commits.
5. Attach the issue, current `README.md`, applicable root/nested `AGENTS.md`, this guide, and existing tests; ask for source evidence, actual CI, changes limited to the allowlist and a human review.
6. Start the cloud session. Monitor logs/steer in the Agents tab and review the resulting PR. GitHub-hosted agents cannot automatically upload organizer submissions, authorize external cloud spending or prove as-of correctness.
7. If an issue is already locally claimed by Grok/Claude/AGY, **do not launch a second GitHub agent against the same files**. The GitHub session UI is not a replacement for claim protocol.

GitHub documentation: [cloud agent on GitHub](https://docs.github.com/en/copilot/how-tos/use-copilot-agents/cloud-agent/use-cloud-agent-on-github), [agent apps](https://docs.github.com/en/copilot/how-tos/use-copilot-agents/cloud-agent/use-agent-apps), [Copilot plans](https://docs.github.com/en/copilot/get-started/plans).

## Safe GitHub agent request template

```text
Repository: AsvM45/jaegers
Issue: #<UNCLAIMED_ISSUE>
Agent: <AGENT_ID>
Start from the current main and read AGENTS.md, the nested task AGENTS.md,
docs/AGENT_COLLABORATION_PROTOCOL.md and the entire issue discussion.
Claim exactly one issue with a standalone jaegers-claim:v1 marker.
Change only the files explicitly allowed by the issue; do not modify
the champion, release ZIP/CSV, another owner's branch or cloud credentials.
Run the relevant local/tests and GitHub Actions. Preserve negative results.
Open a PR with exact diff, commit hash, test outputs, blockers and reviewer.
Do not self-merge, make paid API calls or submit to the organizers.
```

## Isolated local worktree example

```powershell
cd C:\Users\asvat\OneDrive\Documents\GitHub\Datathon2026\jaegers
git fetch origin
git status --short
git worktree list --porcelain

# Only for a NEW task with a fresh, unclaimed issue:
git worktree add -b agent/example-heNN ../jaegers-example-heNN origin/main
```

Each active agent edits only its separate worktree. Local ignored `research_runs/` files belong to the relevant checkout and must be backed up before retirement; a clean `git status` does **not** prove ignored results are absent. A claimed issue is not a running process; validate actual recent pushes and task ownership.

## Control surfaces and what they cannot prove

- **Issues**: task, path owner, claim, handoff, blocker and acceptance.
- **PRs**: proposed code and review evidence; closing a superseded PR is safer than merging its already-integrated branch again.
- **Actions**: tests and governance signals; passing smoke is not scientific performance or official receipt.
- **Projects**: a view of the same issues, if enabled. Do not make duplicate tickets.
- **Wiki**: public-safe summary/navigation mirror. Canonical source stays in versioned `docs/`.
- **Discussions**: optional long-lived public proposals; currently disabled.
- **Hooks**: local pre-commit hooks are bypassable and unshared without setup; GitHub webhooks need a real external consumer and explicit permission.

See [GitHub feature ADR](../adr/0001-github-engineering-features.md) and the [owner ruleset](https://github.com/AsvM45/jaegers/rules/26780842) for any actual enforcement changes.
