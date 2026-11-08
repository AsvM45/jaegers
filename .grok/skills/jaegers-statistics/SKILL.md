---
name: jaegers-statistics
description: "Use for Grok House Edge Bayesian/Dirichlet, Markov, decay, ablation and ensemble challenger research assigned in issues #15, #12."
---

# Grok statistical challenger workflow
1. Read root/nested `AGENTS.md`, `CLAUDE.md`, `docs/AGENT_OPERATING_POLICY.md`, `docs/AGENT_CONTEXT.md`, `docs/MULTI_AGENT_OWNERSHIP.md`, `docs/GROK_START.md`, #18 and the single active issue.
2. Claim #15 only when unclaimed; #9 is Claude-claimed with PR #28. Work in a dedicated worktree. Write ONLY new `research/challengers/stat_temporal_*.py`, `research/configs/stats/temporal_*`, `tests/test_stat_temporal_*.py`. Avoid Claude's `research/challengers/stat_he09_*.py`. A's shared research modules are read-only.
3. Produce valid payout-class five-vectors [0,1,2,5,20] using as-of observations strictly before each tick, with explicit missing-tick and historical-signal availability.
4. Compare regime-switching/HMM/changepoint/state-space or carefully justified indicator time-series distributions; existing Dirichlet/Markov/decay models are in Claude PR #28 on paired whole-episode folds. Observed sampled Brier is different from exposed public true-probability validation points; hidden test truth is not known.
5. Run real bounded smoke/tests, capture exact commands, versions, source/config/split hashes, runtime and failures. Open own-branch PR for review if authorized. Do not modify champion, merge main, submit, or use paid cloud.
6. Request next issue only after #15 review; do not work on reserved #12 simultaneously; #9 and #17 have Claude PRs #28 and #22.
