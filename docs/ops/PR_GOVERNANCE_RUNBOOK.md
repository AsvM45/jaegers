# JAEGERS PR governance and GitHub Agents runbook

**Contract:** issue [#69](https://github.com/AsvM45/jaegers/issues/69). **Scope:** GitHub PR ownership and merge quality. **Authority:** live issue/PR state, `AGENTS.md`, `docs/AGENT_COLLABORATION_PROTOCOL.md`, and the current trusted `tools/check_agent_pr.py`. A dated report is not live telemetry.

## One issue / one implementer / one change set

1. Read applicable root and nested AGENTS instructions. Fetch `origin/main`, the target issue and its latest comments, all open PRs, and the relevant interfaces.
2. Work on `agent/<agent-issue-slug>` or `human/<owner-issue-slug>`, in a physically separate clone or worktree. GitHub-hosted Copilot agents use their own isolated cloud environment. Avoid shared local checkouts.
3. Claim the issue with a standalone marker, not a quoted example: `<!-- jaegers-claim:v1 agent=NAME branch=agent/NAME paths=some/path.py|another/directory/ -->`. Include a human-readable owner, worktree or cloud workspace, exclusive writable paths, tests, reviewer and blockers.
4. For handoff, the previous owner must **consent and stop** and post a standalone `<!-- jaegers-handoff:v1 branch=agent/old-branch -->` marker. Then the successor posts a fresh claim in the same issue on its own branch. Do not have two active overlapping PRs.
5. Use exactly one canonical `Issue: #NN` in the PR template, report genuine test commands/results and hashes, declare data/evaluation provenance, and record non-passing tests and explicit limitations.
6. Review all changed files and GitHub Actions statuses; close an obsolete overlapping PR without merging before proceeding with the successor, preserving its branch until local evidence is audited.
7. An independent authorized human reviews and merges. Do not infer approval because a model wrote "PASS." Do not use automatic champion promotion, paid cloud, GitHub secrets, or organizer submission.

## How the automated gate works

`.github/workflows/agent-collaboration.yml` always runs on PR creation, update, edit, reopen and ready-for-review. **Do not path-filter this required gate.**

- `Agent ownership and concurrent-PR overlap`: checkout of trusted default branch, read-only GitHub token restricted to issues/PR metadata, API pagination limits and timeouts. Validates the named issue claim, changed-file allowlist, one issue line, independent ownership, conflicting open PR paths, **repeated merged PR head SHAs**, and an already-ancestor branch head. Detects an event whose head SHA is stale. No privileged `pull_request_target` checkout.
- `Agent governance unit tests`: exercises proposed policy tests from the PR head with no GitHub token/secrets. Helpful as CI but **not a security boundary**, because a malicious PR can edit its own test program.
- `Databricks offline synthetic and parity tests` and `Hitachi bounded unit and adversarial tests` live in separate path-filtered workflows. They are not always present. Do not list their jobs as unconditional required checks: path-skipped workflows may stay pending indefinitely.
- No GitHub Action can attest that an external Grok, Claude, Antigravity or Codex process is running or that two developers do not share a local worktree. Claims and branch names provide governance evidence, not cryptographic identity.

**Expected intentional failures:** a previously merged exact-head branch, head ancestor of main, empty PR diff, handoff without successor claim, conflicting active open PR, changed file outside the allowlist, stale event SHA, two canonical Issue lines. If GitHub Actions is red, diagnose and fix; do not bypass or merge first.

## Ruleset settings still needing an authorized GitHub repository administrator

Current historical ruleset: [basic #26780842](https://github.com/AsvM45/jaegers/rules/26780842), active with pull-request requirement but previously observed **0 required approvals and no mandatory status checks**. Verify live state before changing.

1. Open [Settings → Rules → Rulesets](https://github.com/AsvM45/jaegers/settings/rules), edit `basic`, and confirm it targets the default `main` branch. Keep branch deletion and non-fast-forward protection.
2. Require `Agent ownership and concurrent-PR overlap` as a status check. The check name is a **job**, not the workflow title. This job runs on all PRs.
3. Consider one non-author approval **only after** confirming another authorized human collaborator can supply it; otherwise a single-owner repository may block every merge. Never claim self-review counts as independent approval. Protect frozen release code with human signoff in either case.
4. Do not immediately require path-filtered Databricks/Hitachi checks; they are absent on unrelated PRs. Use an always-present aggregate workflow/job first if mandatory component checks are desired.
5. Save ruleset. Verify enforcement using a disposable **non-release** test PR with intentionally failing governance metadata. The test PR should be blocked from merge; close it without merging. Confirm a clean, reviewed PR is mergeable. Document actual result in issue #69 or #18.
6. The connected GitHub chat integration cannot edit repository rulesets or GitHub Projects/Wiki administration. An authorized owner must perform these account-level settings in the UI.

## GitHub Agents tab / GitHub Copilot cloud agents

- GitHub Agents tab provides real cloud coding sessions and can launch Copilot or available third-party agents, assign eligible agents to issues, monitor sessions, steer, and generate PRs. **It is not the same as a local Cursor/Claude/Antigravity session**. The latter will not automatically appear in GitHub's session dashboard.
- Before selecting a new GitHub cloud agent, verify actual Copilot entitlement and premium usage/credit controls. **GitHub Pro via Student Pack does not necessarily mean paid Copilot Pro**; Student Copilot benefits and third-party agents have their own eligibility rules.
- Good first cloud-agent task: review a well-scoped, non-release PR or write missing deterministic unit tests for an issue with no competing claim. Start from the repo's current main; reference the issue and exact files. Confirm no local agent owns the same paths.
- Require a unique issue, branch, review, tests and source evidence even for a GitHub-hosted agent. Its session automatically provides a distinct hosted work environment; don't confuse session identity with the text in a GitHub issue comment.

## Security and maintenance

- Use least privilege (`contents: read`, `issues: read`, `pull-requests: read`) for PR metadata checks and no secrets in untrusted PR-head test jobs.
- Prefer current official Actions releases compatible with the GitHub-hosted runner; verify major upgrades in Actions before integration. Review external actions and pin them to immutable full commit SHAs for higher-assurance release automation.
- Keep private organizer tokens, unpublicized target labels, receipts and raw logs out of the public repository, including Actions artifacts.
- Prefer Issues and PRs for work contracts; Projects for views of the **same issues**, versioned `docs/` for the canonical technical knowledge, optional Wiki for public-safe summaries. Do not duplicate ownership ledgers.
- Webhooks require an actual approved external receiver; ordinary Actions and issue assignments are sufficient here. Automations should not merge model/release branches unattended.

## Post-change acceptance record

After this runbook and checker are merged: record a positive trusted-base gate run and adversarial tests, note the full fixed commit SHA, **then** configure/verify the mandatory ruleset setting. Repo source being correct does not mean branch enforcement is configured.