# ADR-0001: GitHub surfaces for multi-agent engineering

**Decision:** use GitHub **Issues + PRs + versioned `docs/` + bounded Actions** as the authoritative workflow. Add only features with clear marginal value. **Status:** Accepted engineering recommendation, **not** proof every optional GitHub UI setting is configured. **Evidence checkpoint:** Nov 8, 2026, `9eec670c8bd3b1fcdcc67f7d376cbf316dd639a8`.

## Actual setting and recommendation matrix

| Surface | Verified state | Decision and rationale |
| --- | --- | --- |
| GitHub Issues | Active, [#18 dispatch](https://github.com/AsvM45/jaegers/issues/18), explicit issue claims | **Keep.** Single owner and acceptance contract; comments record evidence/handoffs. |
| Pull requests | Active, merged research and release code, reused-head duplicate PRs were previously merged | **Keep; harden.** Require scope tests and prevent duplicate/empty PRs. |
| GitHub Actions | Repo includes ownership, House Edge smoke, offline component workflows | **Improve.** One always-on trusted ownership gate; path-filtered unit/sponsor tests. Avoid paid cloud or hidden datasets. |
| GitHub basic ruleset #26780842 | Active, protects default branch from deletion/non-fast-forward and requires a PR, but historically had **0 approvals and 0 required status checks** | **Owner action recommended.** Require `Agent ownership and concurrent-PR overlap` and one non-author review only if a second reviewer exists. Test enforcement on a disposable PR; agent cannot change rulesets through this connector. |
| Projects v2 | Repo capability `has_projects=true`; a live board not verified | **Optional lightweight adoption.** One project board showing the **same** issues, status, owner/lane, priority, blocker/dependency and link to evidence. Do not duplicate tickets/claims. |
| Wiki | Repo capability `has_wiki=true`; `docs/wiki/` staged and published pages unverified | **Public-safe mirror.** Canonical code/docs remain in ordinary Git PRs. Publish Home/Sidebar links manually when wanted; don't edit two separate bodies independently. |
| Discussions | `has_discussions=false` at inspection | **Defer.** Only enable when a real external contributor/research community needs open-ended RFCs distinct from implementation tickets. |
| Hooks | No justified external webhook receiver | **Defer webhooks.** Actions already react to GitHub events. Optional local hooks for speed, but never treat local hooks as enforceable security. |
| CODEOWNERS | File not present at checkpoint | **Defer until named GitHub collaborators exist.** Text labels like "Grok" are not valid GitHub identities. |
| Dependabot | No reviewed update strategy at checkpoint | **Later**: alerts/update proposals after competition; pinned numerical packages require deliberate validation, not automated model changes. |
| Security documentation | No `SECURITY.md` at checkpoint | **Adopt now** for private vulnerability reporting and public data boundaries. |
| Contribution guide | No `CONTRIBUTING.md` at checkpoint | **Adopt now**: concise entry path and issue/PR claim requirements. |
| Releases/tags | No release objects found | **Later**: publish reviewed, public-safe code/checksums only; not hidden organizer materials. |
| Copilot/GitHub Agents tab | User reports enabled access; connector does not expose live sessions | **Pilot** with one isolated unclaimed issue or read-only research session, measure credit usage. Do not duplicate locally owned work. |
| Repository license | No `LICENSE` at checkpoint | **Human choice:** public visibility does not grant software reuse permission; choose a license with coauthor/starter-code obligations in mind. Do not add an unapproved MIT/Apache license. |

## Recommended implementation order

1. Finish and validate the always-on governance checker and test coverage; use current native GitHub Actions releases, read-only scopes, no privileged PR-head token or unnecessary cloud services.
2. Activate a **required status check on main** once the owner is ready; do not require individually path-filtered workflows (they may remain pending on unrelated PRs).
3. Execute Codex's read-only branch/worktree preflight; obtain owner sign-offs and protect local ignored evidence. Remove only fully integrated inactive refs after fresh SHA checks; never squash/rewrite main history.
4. Complete canonical docs with reproducible links, validation provenance and release status; stage a small public-safe GitHub Wiki Home/Sidebar.
5. Optionally pilot Projects v2 as a mirror of real issues. A view is useful only if the team genuinely checks it.
6. Post-competition decide if Discussions, CODEOWNERS, Releases, dependency automation, a license or external webhooks are worthwhile.

## Security and continuity

The public repo must exclude hidden targets, organizer token, receipts, signed agreements, access secrets, raw personal data, and ignored experiment artifacts. Check GitHub Actions artifact retention and secret/permissions boundaries; do not use `pull_request_target` to checkout untrusted code with a privileged token. An AI session being visible in the GitHub Agents tab does not guarantee statistical correctness, rule compliance or independent human review.

**Decision revision trigger:** new paid cloud service, public external contributors, another team in separate GitHub ownership, ruleset enforcement incident, or a new challenge/release workflow that materially changes requirements.
