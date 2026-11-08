# JAEGERS — Current five-agent ownership map

**Single coordination source:** [#18](https://github.com/AsvM45/jaegers/issues/18), latest issue claim comments. **Agent policy:** [AGENT_OPERATING_POLICY](AGENT_OPERATING_POLICY.md); **source context:** [AGENT_CONTEXT](AGENT_CONTEXT.md). Agent claims and actual local worktree trump default reservations below. The shared GitHub login is not an agent identity.

| Lane / platform | Sole implementation issue set | What is confirmed vs reserved | Owned code boundaries |
| --- | --- | --- | --- |
| **A CHAT/Codex** | #1, #4, #8, later #6 | #1/#4/#8 explicitly claimed; branch `chat/house-edge-release-research-core` reported locally. One issue actively edited at a time. | Existing shared `research/{freeze,reproduce,release,offline,process,registry,sweep,worker,common,dataset,features,learners,models,metrics,adapters,feature_api}.py` and release tooling; `jaegers_entry` champion protected. |
| **B Antigravity** | #13, later #14 | #13 reserved with handoff but no confirmed live run. | New `dashboard/**`, `research/analysis/antigravity_*`, later approved `databricks/**`. A-owned `research/*.py` read-only. |
| **C Claude Code / InTheHiggsField** | #3, #2, #7 and claimed #17 | Explicit issue claims; PR [#22](https://github.com/AsvM45/jaegers/pull/22) for #17, plus [#19](https://github.com/AsvM45/jaegers/pull/19), [#20](https://github.com/AsvM45/jaegers/pull/20), [#21](https://github.com/AsvM45/jaegers/pull/21) open. | New `research/audits/**`, `research/extensions/qa_*`, `research/challengers/signal_*`, `tests/test_agent_qa_*`. Shared code read-only. |
| **D Grok Build (planned)** | #9, later #12/#15 if still unclaimed | Not yet claimed/running; one issue at a time after named claim. | New `research/challengers/stat_*`, `research/configs/stats/**`, `research/reports/stat_*`, `tests/test_stat_*`; shared adapters read-only. |
| **E Cursor** | #16, later #10/#11 | #16 explicitly claimed (branch `agent/cursor-he16-ci`), not evidence complete. #10/#11 reserved pending handoff. | For #16 only: `.github/workflows/house-edge-ci.yml`, `tests/test_release*.py`, `scripts/smoke_release.py`; after handoff, unique `research/challengers/ml_*` and `temporal_*`. |
| **Human** | #5 organizer submission and #18 coordination | Human approval gate; not counted among the five coding agents. | Organizer receipt private, merge approval, model promotion, secrets, paid cloud authorization and conflict mediation. |

## Rules of engagement

1. **One owner per implementation issue, one active editing issue per agent, and one worktree per agent.** Reservations do not mean live work. Before a write: check the current issue's latest claim/handoff, #18, `git worktree list`, `git status --short`, HEAD and branch.
2. Latest issue claim comments trump stale tables. Never overwrite or switch/reset another agent checkout. The binding current governance is [AGENT_COLLABORATION_PROTOCOL.md](AGENT_COLLABORATION_PROTOCOL.md), including machine-readable claim markers, isolated branch + physical worktree, and the existing Actions PR overlap gate. No modeler writes A's common adapters/feature registry without explicit handoff; create isolated additional modules and request interface changes.
3. Claude PRs #19–#22 are review-ready proposals; don't reimplement their tests/audit. Cursor already claims #16; don't give CI to C or Grok. Grok gets #9 **only after it claims**; #17 is already Claude-claimed and has PR #22.
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
git worktree add -b agent/grok-he09 ../jaegers-grok-he09 origin/main
```

Only if not already present. Do **not** run this for another agent's branch.