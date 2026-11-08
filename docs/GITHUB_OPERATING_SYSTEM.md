# GitHub as JAEGERS's shared engineering operating system

**Authoritative code and policy:** this repository's versioned `docs/` and `AGENTS.md`. **Issue execution:** [#18 coordination](https://github.com/AsvM45/jaegers/issues/18). **Currently observed repository settings:** public, `has_wiki=true`, `has_projects=true`, **`has_discussions=false`** (GitHub API read, Nov 7). This document proposes an end-state; unconfigured UI features **are not claimed active**. The connected GitHub tools can write repo files, issues and PRs, but do not expose creation of Projects v2, Discussion posts or separate wiki-repo pages. A human GitHub maintainer must enable/configure those in the UI or use appropriate authenticated admin tools.

## 1. One home for each kind of knowledge

| GitHub surface | Owns | Should NOT contain |
| --- | --- | --- |
| `docs/` on main | **Canonical reviewed** technical spec, contracts, scientific methods, agent policies, setup runbooks and source provenance; PR-reviewed, permanent and searchable | secrets, raw private conversation archives |
| GitHub Issues | Exactly one accountable owner, acceptance checks, implementation discussion, dependencies, test evidence, explicit claim/handoff | open-ended debate without deliverable |
| GitHub Projects v2 | Cross-issue triage, status, owner lane, workstream, deadline, dependencies, evidence gates, iteration/budget | source of truth for code or model metrics |
| GitHub Discussions | Research hypotheses, architecture proposals (RFC/ADR discussion), science questions, postmortems, sponsor ideas before issue scoping | issue-sized implementation with an assigned executor |
| Pull requests | Concrete source changes, test evidence, review and integration gate, link `Refs #N` (not premature auto-close) | unrelated changes from other agent |
| GitHub Actions | Cheap tests, conflict/ownership-preflight, probability/as-of/scorer invariants, artifacts provenance and CI result links | expensive full modeling sweeps, upload to organizer, model promotion, cloud cost by default |
| Wiki | **Public human-readable mirror** of curated/reviewed docs, quickstart, explanatory architecture and FAQ; links to canonical revision | source-of-truth that drifts from docs/, raw ChatGPT Library import |
| Releases | Only human-approved frozen CSV/ZIP and reproducibility manifest where competition rules/publication rights permit | private receipts/organizer tokens or unpublished evaluation data |

### Why docs/ canonical and Wiki a mirror?

GitHub Wiki is a **separate Git repository**, not the main repo's review/PR lifecycle. Keeping important contracts in `docs/` makes Code Review and Actions checks possible and prevents parallel agents silently changing an unreviewed Wiki. Maintain `docs/wiki/README.md` and associated staged pages as publishable copies; after review, a human can sync them to the wiki repo. They should link back to canonical files and source commit.

## 2. GitHub Projects v2 setup (human)

Create a project named **JAEGERS | House Edge — Five-Agent Delivery** under the team owner's GitHub account. Add all House Edge Issues #1–#18 and the open PRs #19–#21. Suggested fields:

- `Status` (single-select): Backlog, Ready, Claimed, In Progress, Blocked, Ready for Review, Done.
- `Agent lane` (single-select): A CHAT, B Antigravity, C Claude, D Grok, E Cursor, Human.
- `Priority`: P0 release, P1 research, P2 optional.
- `Workstream`: Release, Statistical QA, ML, Analytics, Databricks, Automation, Knowledge.
- `Deadline` (date), `Blocked by` (issue links/short text), `Evidence` (text link), `Compute budget` and `Source exposure` optional.
- Views: **By status** (board); **By agent** (board); **Critical path** (table, P0); **Research experiments** (table); **Reviews/PRs** (table); **Upcoming deadlines** (roadmap).

Enable built-in automations for PR merged -> Done and issue closed -> Done; **do not automatically close an issue just because a draft PR opened**. For one-claim enforcement, the latest issue claim comment/body + human owner review is authoritative; Projects field is a view, not a lock.

A person must perform this UI setup. The GitHub connector here does not expose Projects v2 field/item mutation. **Never invent a project URL**.

## 3. Discussions setup (human)

Discussions is currently disabled. Repo maintainer: GitHub repo **Settings → General → Features → Discussions** (GitHub UI wording may vary). Enable, then create categories:

1. **Research hypotheses** — e.g., effect of sibling lag interactions on shared-change;
2. **Architecture / RFCs** — trial schema, feature API, warehouse vs queue;
3. **Decisions / ADRs** — outcomes of contested choices, link PR/issue;
4. **Sponsor & Databricks** — approved technical narratives and public demos;
5. **Help / Q&A** — explain evaluation, constraints and reproducibility;
6. **Retrospectives** — negative results, failure analysis.

Discussion message structure: *Hypothesis / evidence available / assumptions / proposed test / decision needed / link to issue*. Once a hypothesis becomes a bounded deliverable, create one Issue and link back; don't spin up competing implementation owners inside a Discussion. Do not share private organizer communications or personal material.

Issue/PR template files in `.github/` provide standardized fields and evidence gates.

## 4. Actions and branch protection

**Cursor owns issue #16**; do not duplicate its `.github/workflows/house-edge-ci.yml` or compete on its branch. It is implementing CI in `agent/cursor-he16-ci`; integration after review.

Recommended CI:
- `pull_request` to `main`, read-only `GITHUB_TOKEN` with `permissions: contents: read`.
- Fast CPython 3.13 `pytest` for schema, 5-simplex, as-of, scorer parity and small deterministic fixtures; no private test truths.
- Source/path ownership preflight against explicit issue claim and allowlist, treat unexpected protected-file edits as **review blockers**, not automated destructive operations.
- Cross-open-PR shared-path collision check where possible. Detect actual overlapping paths; never infer from issue title only.
- Validate shells `.sh` LF, `git diff --check`, absence of generated runs or secrets.
- Retain CI run links/hashes, no automatic issue close until human review.
- Optional release workflow must be `workflow_dispatch` + explicit human signoff and **should produce local artifacts only**, no automatic organizer upload. Prefer no GitHub-hosted run over quota or resource surprises.

Discuss protection of `main` with repo admin: require PR reviews and passing CI where plan/settings allow; direct pushes to `main` prohibited by team policy even if GitHub technically allows them. No `pull_request_target` job running untrusted PR code with write secrets.

## 5. Wiki publication and Library migration

Source files in `docs/research/` are curated copies of **research-only safe** ChatGPT Library Markdown. Each import has an explicit as-of date, original document title, library version, and **DESIGN NOT EXECUTED** marking if appropriate. Source files may be stale; current code and PRs outrank them.

Wiki draft pages under `docs/wiki/` are Git-reviewed staging files. To publish first wiki page via browser: repo → Wiki → Create first page, then `git clone https://github.com/AsvM45/jaegers.wiki.git` and copy only **human-reviewed public pages**. Wiki is not the storage destination for every Library item. Do **not** sync signed NDA, private conversation exports, third-party challenge kits with unclear redistribution rights, personal files, credentials or organizer receipts. Git history is public and deletion is not reliable privacy remediation.

For PDF and binary artifacts, the connected GitHub file write action supports **UTF-8 text only**. Use Markdown transcriptions/summary in reviewed docs and link external PDFs only when their visibility is appropriate. Binary releases/wiki uploads require a separate authorized tool/UI workflow.

## 6. Exact human setup checklist

- [ ] Confirm Wiki is enabled; seed first wiki Home page from reviewed `docs/wiki/Home.md`, then sync staged pages.
- [ ] Enable Discussions and create recommended categories.
- [ ] Create Projects v2 and views above; add current 18 issues + relevant PRs; configure built-in automations.
- [ ] Review open PRs #19/#20/#21 and ownership; do not auto-merge, especially near submission cutoff.
- [ ] Set/confirm main branch protections and Actions workflow permissions.
- [ ] Verify whether main/adaptation submissions actually received organizer receipts before calling release done.
- [ ] Confirm any publication of Library imports is appropriate for a **public repository**.

**External background:** GitHub Docs [Projects](https://docs.github.com/en/issues/planning-and-tracking-with-projects), [Discussions](https://docs.github.com/en/discussions/collaborating-with-your-community-using-discussions/about-discussions), [Wiki](https://docs.github.com/en/communities/documenting-your-project-with-wikis), [Actions permissions](https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax).