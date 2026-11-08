# JAEGERS: required multi-agent collaboration protocol

**Applies to Codex, Claude Code, Antigravity and human contributors.** This project uses the same collaboration discipline as a human software team: explicit tasks, one accountable owner, separate workspaces, dependency communication, reviewable pull requests, and tested handoffs. See [issue #18](https://github.com/AsvM45/jaegers/issues/18) and [owner matrix](MULTI_AGENT_OWNERSHIP.md).

## Non-negotiable before writing

1. Read the applicable `AGENTS.md`, this protocol, issue #18 and your assigned issue. Check `git status --short`, HEAD and `git worktree list`.
2. **Each concurrently editing agent must have its OWN Git branch AND its OWN physical Git worktree or clone**. Separate chat windows in one directory are not separate worktrees. Never switch branches in another agent's checkout, reset its dirty work, or force-push its branch.
3. Claim **one active editing issue per agent**. Post a named owner, exact branch/worktree, exclusive file-write allowlist, read-only dependencies, intended tests and human reviewer. A shared GitHub assignee is *not* an agent identity. Non-editing issue reservations are allowed; one person may manage several issues but execute one active file-edit scope at a time.
4. Add this machine-readable issue comment marker as part of the human-readable claim (use exact file paths or directory prefixes ending `/`, separated by `|`):

```text
<!-- jaegers-claim:v1 agent=claude-qa branch=agent/claude-qa-he02-tests paths=Jaeger_Main/House_Edge/tests/test_qa_he02.py|Jaeger_Main/House_Edge/research/audits/ -->
```

5. Treat all unclaimed files as read-only unless the issue owner explicitly delegates them. Overlapping file scope, changed interfaces or uncertain ownership means **BLOCKED pending handshake**, not permission for two agents to edit in parallel.

## Git worktree setup (PowerShell)

```powershell
$repo = "C:\Users\asvat\OneDrive\Documents\GitHub\Datathon2026\jaegers"
cd $repo
git fetch origin
git status --short
git worktree list
# Example; use your unique agent/issue slug and new folder:
git worktree add -b agent/claude-qa-he02-tests ../jaegers-claude-qa origin/main
# Open ../jaegers-claude-qa in ONLY that agent's editor/terminal.
```

Branch names: `agent/<unique-agent-and-issue-slug>` or `human/<unique-person-and-issue-slug>`. GitHub Copilot **cloud** sessions automatically create `copilot/<unique-slug>` branches; these are also accepted by the gate **only when the same full issue claim, Agent-ID, exact changed-file allowlist, PR metadata and no-overlap checks succeed**. There is no bot exemption.

**Copilot cloud PR handoff:** An auto-created draft PR may initially have only a generated description and no stand-alone issue claim, so it is intentionally blocked. Wait for that agent's code changes, verify its exact branch and changed paths, post a truthful agent-owner claim comment, and populate the PR fields `Agent-ID:`, `Issue: #NN`, `Worktree:`, `Tests:`, `Handoff:` with observed evidence. A user may need to approve GitHub Actions runs on a Copilot-generated PR before the required check can execute. Do not treat a bot assignment, pending approval, or a passing unit test as a human review. [GitHub Cloud agent API documentation](https://docs.github.com/en/copilot/how-tos/use-copilot-agents/cloud-agent/use-cloud-agent-via-the-api). If the worktree already exists, inspect and reuse only for the original owner/issue; never recreate it forcibly.

## Cooperate as teammates

- **Coordinate interfaces FIRST:** owners of `research/*` adapters, feature schemas, trial registry and dashboards agree on function signatures, data contracts, versioned schema, example records and error handling before parallel implementation. A consumer reads the shared interface but does not modify the owner's module. Create uniquely named adapters/extensions when needed.
- **Communicate progress:** leave issue comments with real test commands, measured outcomes, source/data hashes, current blockers, and a clear next step. Never invent scores or CI passes.
- **Request reviews:** one issue = one branch = one PR. Include an explicit file list, changed contracts, test outputs, experiment provenance, release risk and who must review. Respond to review findings instead of treating review as opposition.
- **Handoffs require consent:** old owner posts `<!-- jaegers-handoff:v1 branch=agent/previous-branch -->`; the new owner posts a fresh named claim. A stalled agent is not an automatic ownership transfer.
- **Integrate serially:** investigate conflicting open PRs, get review, rebase after each integration, rerun tests, then merge with human authorization. No direct pushes to `main` by unattended agents and no auto-merge of consequential changes.
- **Separate private state:** don't put organizer tokens, private receipts, test hidden labels, model artifacts or large generated runs in GitHub issues or PRs. Only human release owner uploads entries, approves champion promotion, or approves paid cloud actions.

## PR check and limits

`.github/workflows/agent-collaboration.yml` invokes `tools/check_agent_pr.py` from the trusted base branch on new PRs. It rejects invalid branch/name/issue claims, unclaimed modified paths and filenames overlapping other open PRs. It is a **procedural gate**, not proof of separate physical worktrees, a truthful AI identity, or correct statistical methods. Existing PRs #19–#21 predate this protocol; they are grandfathered for *metadata* only, not for conflicting changed files.

**GitHub admin requirement:** After a tested workflow run, configure a repository branch ruleset to require PRs and the `Agent ownership and concurrent-PR overlap` check before merging `main`; restrict direct pushes and require a reviewer. Until admin protection is enabled and checked, no claim of technical enforcement is warranted.

## Contest-specific priorities

Before main deadline, frozen champion and tested offline CSV/ZIP (#1/#4), human submission (#5), independent statistical and temporal QA (#2/#3) are P0. The adaptation round (#6) begins with a new kit. Agent-owned experiment registry (#8), model challengers (#9–#12/#15/#17), dashboard (#13), CI (#16) and optional Databricks (#14) must not delay release. Historical as-of uses observations strictly before each tick; missing tick is unknown; public validation is development-exposed. The existing champion, `slot_forecasting/`, and `Jaeger_Main/Hitachi/` are protected.

## Definition of done

Issue READY FOR REVIEW: scoped changed files, actual tests/metrics, interface compatibility, source hashes and unresolved limitations documented; PR opened and reviewers notified. Issue DONE: the evidence has been reviewed and approved and integration verified, or the non-code work is demonstrably finished. An unmerged PR or a claimed local run is not an accepted organizer release.
