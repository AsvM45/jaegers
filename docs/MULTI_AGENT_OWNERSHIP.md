# JAEGERS — Current five-agent ownership map

**Deadline update:** team reports **Sunday Nov 8, 2026 at 10:30 AM CT** operational target; original organizer House Edge RULES.md still specifies main Sat 9PM and adaptation Sun 11AM. This is not a verified main-round extension. See [deadline handoff](DEADLINE_1030_HANDOFF.md).\n\n**Single coordination source:** [#18](https://github.com/AsvM45/jaegers/issues/18), latest issue claim comments. **Agent policy:** [AGENT_OPERATING_POLICY](AGENT_OPERATING_POLICY.md); **source context:** [AGENT_CONTEXT](AGENT_CONTEXT.md). Agent claims and actual local worktree trump default reservations below. The shared GitHub login is not an agent identity.

| Lane / platform | Sole implementation issue set | What is confirmed vs reserved | Owned code boundaries |
| --- | --- | --- | --- |
| **A CHAT/Codex** | #8 active; #1/#4 completed; #6 round-specific later | #8 now has an explicit new claim on `agent/chat-he08-completion` (registry export contract); #1/#4 closed and original release candidate frozen. One primary edit scope at a time. | Existing shared `research/{freeze,reproduce,release,offline,process,registry,sweep,worker,common,dataset,features,learners,models,metrics,adapters,feature_api}.py` and release tooling; `jaegers_entry` champion protected. |
| **B Antigravity** | #13 merged; later #14 if approved | PR #45 dashboard merged at `5f3311e`; author-reported 83 tests (not independently covered by main CI). #14 remains available only with workspace/cost permission. | New `dashboard/**`, `research/analysis/antigravity_*`, later approved `databricks/**`. A-owned `research/*.py` read-only. |
| **C Claude Code / InTheHiggsField** | #3, #2, #7, #17 and now claimed #9 | Explicit issue claims; PR [#22](https://github.com/AsvM45/jaegers/pull/22) for #17 and [#28](https://github.com/AsvM45/jaegers/pull/28) for #9, plus [#19](https://github.com/AsvM45/jaegers/pull/19), [#20](https://github.com/AsvM45/jaegers/pull/20), [#21](https://github.com/AsvM45/jaegers/pull/21) open. | New `research/audits/**`, `research/extensions/qa_*`, `research/challengers/signal_*`, `tests/test_agent_qa_*`. Shared code read-only. |
| **D Grok Build (planned)** | #15, later #12 if still unclaimed | Not yet claimed/running; one issue at a time after named claim. | New `research/challengers/stat_*`, `research/configs/stats/**`, `research/reports/stat_*`, `tests/test_stat_*`; shared adapters read-only. |
| **E Cursor** | **New #46 reserved**; #16/#10/#11/#12 closed | New task [#46](https://github.com/AsvM45/jaegers/issues/46) is NOT claimed or running. Earlier Cursor CI/ML/temporal/ensemble implementations merged. | Only new `Jaeger_Main/House_Edge/tools/cursor_portability_probe.py`, `Jaeger_Main/House_Edge/tests/test_cursor_portability_probe.py`, `docs/release/CURSOR_PORTABILITY_REPORT.md`. Existing model, research, release, CI and frozen artifacts read-only. |
| **Human** | #5 organizer submission and #18 coordination | Human approval gate; not counted among the five coding agents. | Organizer receipt private, merge approval, model promotion, secrets, paid cloud authorization and conflict mediation. |

## Rules of engagement

1. **One owner per implementation issue, one active editing issue per agent, and one worktree per agent.** Reservations do not mean live work. Before a write: check the current issue's latest claim/handoff, #18, `git worktree list`, `git status --short`, HEAD and branch.
2. Latest issue claim comments trump stale tables. Never overwrite or switch/reset another agent checkout. The binding current governance is [AGENT_COLLABORATION_PROTOCOL.md](AGENT_COLLABORATION_PROTOCOL.md), including machine-readable claim markers, isolated branch + physical worktree, and the existing Actions PR overlap gate. No modeler writes A's common adapters/feature registry without explicit handoff; create isolated additional modules and request interface changes.
3. Claude PRs #19–#22 are review-ready proposals; don't reimplement their tests/audit. Cursor completed #16/#10/#11/#12; do not reassign or redo them. Cursor can claim independent #46 if not already claimed. Grok gets #15 **only after a new machine-readable claim**; #9 is already Claude-claimed (PR #28) and #17 is Claude-claimed (PR #22).
4. A owns model/feature API integration, not everyone else's research outcomes. To propose new model, publish tested `fit/predict_proba` interface and 5-vector output, submit code + source/data/fold/metric provenance, then allow A to integrate after review.
5. **Scope:** House Edge only; separate Hitachi code unaffected. The original `jaegers_entry` champion cannot be replaced without human review/approval.
6. **Branch PR:** own feature branch/draft PR when issue-level permission allows. Never merge/push `main` or submit to organizer automatically. Only a human approves paid cloud, secrets, or external publication.
7. **Handoff:** issue comment with tested command/output, changed paths, source/config/data hashes, PR, blocker and next bounded task; don't claim completion from a PR title alone.
8. **GitHub OS:** [docs/GITHUB_OPERATING_SYSTEM](GITHUB_OPERATING_SYSTEM.md) holds Projects/Discussions/Wiki/Actions workflow. Canonical reviewed agent context is [AGENT_CONTEXT](AGENT_CONTEXT.md), not raw chats.

## Windows worktree creation example (Grok D only)

```powershell
$repo = "C:\Users\asvat\OneDrive\Documents\GitHub\Datathon2026\jaegers"
cd $repo
git worktree list
git fetch origin
git worktree add -b agent/grok-he15 ../jaegers-grok-he15 origin/main
```

Only if not already present. Do **not** run this for another agent's branch.