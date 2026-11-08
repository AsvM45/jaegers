# JAEGERS — Autonomous Engineer Operating Policy (v1)

**Applies:** CHAT/Codex, Claude Code, Google Antigravity, Cursor, Grok, and humans working on `Jaeger_Main/House_Edge/`. **Binding PR/claim checker:** [AGENT_COLLABORATION_PROTOCOL.md](AGENT_COLLABORATION_PROTOCOL.md) and `.github/workflows/agent-collaboration.yml` on main. Follow its branch, PR metadata and claim format as the stricter rule. **Start:** [Context](AGENT_CONTEXT.md), [Ownership](MULTI_AGENT_OWNERSHIP.md), [GitHub #18](https://github.com/AsvM45/jaegers/issues/18), and the latest issue claims/PRs. This document is a policy, **not proof of any running agent**.

## Behave as an accountable engineer

Take ownership of a defined deliverable, not merely a prompt response. Inspect real code and requirements, form a falsifiable plan, implement small vertical slices, run actual tests, investigate failures, review your own changes, record negative results, and leave an independently usable handoff. Continue through bounded implementation milestones within the active session instead of stopping at a speculative plan. Raise focused questions only for genuine blockers, decisions that affect other owners, or human-only approvals.

**Initiative is not unlimited authority.** Agents may decide internal implementation details and local experiments inside their claim. They must not silently seize another issue, mutate another worktree, promote a model, use private credentials, spend cloud money, contact organizers, or publish/reveal sensitive materials.

## Work agreement and permissions

- READ: inspect released organizer kit, repository, issue, PR, context, permitted public references; never read sensitive third-party/private sources without authorization.
- BUILD: edit only *your own claimed paths in your own worktree*; create tests/configs, install local development dependencies, and run CPU/time-bounded experiments. A user may authorize deeper work in issue instructions.
- SHARE: an issue-specific authorized agent may commit and push **its own named feature branch** and open a **draft PR** for review. This is **not** permission to push `main`, merge, reset others, tag release, or publish private data. If workspace or instruction policy is stricter, obey it and report the required authorization.
- RELEASE: only the human release lead can approve model promotion, organizer upload or replacement, human communication, paid workspace/cloud services, changes to protected source, or irreversible operations. No GitHub PR/check proves organizer acceptance.

## Claim and ownership protocol

- **One implementing owner per issue, one active editing issue per agent, one isolated Git worktree per agent.** Later issues may be RESERVED, not worked concurrently.
- Before editing: `git status --short`, `git branch --show-current`, `git rev-parse HEAD`, `git worktree list`; check latest #18 and issue claim/comments. A shared GitHub login is not an agent ID.
- Claim in issue with human-readable owner, worktree, exact paths, tests, reviewer and the **binding machine-readable marker** `<!-- jaegers-claim:v1 agent=<agent-id> branch=agent/<slug> paths=<exact-path|directory-prefix/> -->` using real values that satisfy the checker; see `docs/AGENT_COLLABORATION_PROTOCOL.md`. A handoff needs the checker-defined `jaegers-handoff:v1` marker. If claimed, do not compete. Require explicit handoff; never infer an unattended agent has abandoned its files.
- Exclusive owner of an implementation file controls its modifications. Others make nonoverlapping modules or propose an API contract/patch in issue comments. No same-worktree or same-file parallel edits.
- State terms: `UNCLAIMED`, `RESERVED`, `IN_PROGRESS`, `BLOCKED`, `READY_FOR_REVIEW`, `DONE`. Claim states and actual execution evidence are separate.
- Reviewer may inspect another issue without claiming implementation. The human project lead arbitrates contested ownership.

## Engineering loop (repeat per bounded unit)

1. Read AGENTS chain, issue with comments, [context](AGENT_CONTEXT.md), ownership and only relevant skills/organizer source.
2. Articulate measurable acceptance, dependencies, writable paths, runtime budget and baseline. Confirm real local HEAD and dirty changes.
3. Write smallest tested change that moves an outcome. Reuse existing models/adapters; avoid duplicate scaffolding or unnecessary refactoring.
4. Run focused unit tests and a genuine end-to-end smoke. Capture exact command and output, failures, seeds, provenance and environment. Fix regressions or report BLOCKED.
5. Self-review `git diff --check`, scope vs allowlist, code review, secrets and input/output contracts. Provide PR/diff against original base. Avoid merging your own work without independent review.
6. Leave issue update: `agent | branch/commit | changed paths | commands/tests actually run | observed metrics + evaluation source | risks | next task`. Ready for review is not done until reviewed/accepted.
7. If useful, propose one follow-up issue or Discussion, **do not automatically claim it**. For truly long-running tasks, use an actual configured scheduler; never pretend a background process exists.

## Research rigor and release safety

- Predict **five categorical probabilities** ordered `0,1,2,5,20`. Train pseudo-labels are real observed payouts at tick t, while features use only ticks **<t** for target and siblings; missing exact tick is unknown. Episodes do not share identity. Historical signal(t) is not provided.
- Distinguish **sampled-outcome grouped-CV Brier**, **public-validation true-probability official four-condition points**, and **test format-only**. Public validation was already used in champion design (including SIZE_REGIMES); public score is development-exposed, not hidden/unbiased.
- Preserve original champion and known-good submission fallback; publish no hidden labels (none available), private receipts or secrets.
- For organizer scoring and timing, use the active kit's `RULES.md`, `DATA.md`, `rounds.py` and current organizer notices, not older inconsistent guides. Main closes Nov 7 at 9PM CT; adaptation closes Nov 8 at 11AM CT per kit. Human confirms actual acceptance and rule differences.
- The official offline predictor must work with **no internet** and must not depend on Databricks. Dashboard/cloud study may be separate, explicitly authorized, and scientifically honest.

## GitHub is the default shared working memory

[Canonical docs](GITHUB_OPERATING_SYSTEM.md) live in the main repo. Issues = scoped implementation and claims; Projects = views/priority/dependencies; Discussions = open hypotheses, decisions and RFCs; PRs = reviewed source changes; Actions = automated, read-only-by-default tests; repo docs = versioned knowledge; Wiki = published readable mirror of **reviewed public** docs; Releases = human-approved final artifacts. Conversation transcripts, signed NDAs, email, credentials, local run histories, user personal files and organizer receipts **must not** be bulk-synced to this public repository.

## Context freshness and escalation

Source precedence: (1) actual released organizer kit/current organizer announcement; (2) actual local HEAD/diff/test output; (3) latest PR and issue claim/handoff; (4) dated `docs/CURRENT_STATE.md`; (5) summary docs and historical Library research. If two sources conflict, say so explicitly and cite both. Escalate immediately on time/compute overrun, scoring/leakage doubts, conflicting implementation claims, destructive change or paid resource need.

Read only relevant sections; a 100-page historical document is **not** an instruction to reread all pages each session.