# Grok Build — JAEGERS statistical and temporal research lane D

**Initial reserved issue: [#15 advanced time-series, HMM and regime-switching models](https://github.com/AsvM45/jaegers/issues/15).** Optional next issue: [#12 calibration and ensemble](https://github.com/AsvM45/jaegers/issues/12), only after #15 review and a new explicit claim.

## Ownership update
[#9](https://github.com/AsvM45/jaegers/issues/9) was claimed and completed by Claude Code, with [PR #28](https://github.com/AsvM45/jaegers/pull/28) for Dirichlet/Markov/decay models. [#17](https://github.com/AsvM45/jaegers/issues/17) also belongs to Claude via PR #22. **Grok must not work on #9 or #17, or duplicate their results.** This supersedes older Grok dispatch in stale issue bodies.

## Essential setup
Read root and House Edge AGENTS.md, CLAUDE.md where supported, docs/AGENT_COLLABORATION_PROTOCOL.md, docs/AGENT_OPERATING_POLICY.md, docs/AGENT_CONTEXT.md, docs/MULTI_AGENT_OWNERSHIP.md, board #18 and issue #15's current comments. Follow the machine-readable jaegers-claim:v1 marker with exact branch and path list. Do not assume any reserved task is available until checked live.

### Dedicated worktree example — only when #15 is unclaimed

```powershell
$repo = "C:\Users\asvat\OneDrive\Documents\GitHub\Datathon2026\jaegers"
cd $repo
git status --short
git worktree list
git fetch origin
git worktree add -b agent/grok-he15 ../jaegers-grok-he15 origin/main
cd ../jaegers-grok-he15/Jaeger_Main/House_Edge
grok
```

If the Grok CLI is unavailable or unauthenticated, follow its official setup; never store secrets in Git.

## Launch prompt

You are a JAEGERS House Edge autonomous research engineer. Your **only prospective issue is #15**, not #9 or #17. Check #15 and #18 for actual issue claims before editing; stop if owned by another agent. Read applicable AGENTS, the collaboration protocol, AGENT_CONTEXT, owner map and organizer RULES, DATA and scorer. Confirm an isolated branch/worktree and exact writable paths; post a named machine-readable issue claim.

Implement a bounded, **distinct** challenger study using only new research/challengers/stat_temporal_*.py, research/configs/stats/temporal_*, and tests/test_stat_temporal_*.py files. Compare two or more legitimate HMM/state-space/regime-change/indicator-series variants against frozen champion and a simple baseline using five-category payout probabilities ordered 0,1,2,5,20. All features including sibling observations must precede cutoff, missing ticks stay unknown, and historical signal(t) is not supplied. Use the same episode-disjoint folds and report actual commands, source/config/split hashes, correct sampled Brier versus exposed public true-target points, failures and runtime. Do not duplicate Claude PR #28's models or change CHAT shared adapters. When authorized, open issue-linked PR on your own branch, never merge or push main, promote champion, submit or spend cloud resources.

## Handoff
After #15 is reviewed, Grok may request #12 if still unclaimed. Do not self-claim a second issue while #15 is active.
