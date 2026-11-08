# GitHub Project v2 — operator setup checklist

**GitHub repo reported:** `has_projects=true`, but the GitHub connector in this session does not expose Projects v2 creation or custom field edits. This is a concrete, human-executable setup plan — **no Project was created by this document**.

## Create board

GitHub user/org Projects → New project → Board or Table → **JAEGERS — House Edge Five-Agent Delivery**. Include Issues #1–#18 and current open PRs including #19–#22, plus this governance documentation PR when reviewed. Allow automatic inclusion of matching issues/PRs from the repo.

Fields: Status (Backlog, Ready, Claimed, In Progress, Blocked, Ready for Review, Done); Lane (A CHAT, B Antigravity, C Claude, D Grok, E Cursor, Human); Priority (P0, P1, P2); Workstream (Release, QA, Stats, ML, Analytics, Cloud, Infrastructure); Blocked by (text or relationship), Deadline, Evidence link, Compute budget. Issue claims in comments remain definitive ownership; a Project field does not enforce a lock.

Views: (1) Board by Status; (2) Board by Lane; (3) Table P0 release/adaptation; (4) Research backlog/PRs; (5) Roadmap by deadline.

Automation: new issue → Backlog, PR opened → review view, issue closed/PR merged → Done as appropriate. Avoid auto-closing issues just because a draft PR appears. The human controls merge/organizer submission.

## After creation

Paste the real project URL into GitHub #18 and update `docs/GITHUB_OPERATING_SYSTEM.md` through a PR; never invent a URL. Test one new issue from the template and one PR. Discuss branch protection/required CI with the repo admin (Cursor #16 owns the CI implementation).
