---
name: jaegers-statistics
description: "Use for Grok House Edge Bayesian/Dirichlet, Markov, decay, ablation and ensemble challenger research assigned in issues #9, #12, #15."
---

# Grok statistical challenger workflow
1. Read root/nested `AGENTS.md`, `CLAUDE.md`, `docs/AGENT_OPERATING_POLICY.md`, `docs/AGENT_CONTEXT.md`, `docs/MULTI_AGENT_OWNERSHIP.md`, `docs/GROK_START.md`, #18 and the single active issue.
2. Claim #9 only when unclaimed. Work in a dedicated worktree. Write ONLY new `research/challengers/stat_*.py`, `research/configs/stats/*`, `tests/test_stat_*.py`. A's shared research modules are read-only.
3. Produce valid payout-class five-vectors [0,1,2,5,20] using as-of observations strictly before each tick, with explicit missing-tick and historical-signal availability.
4. Compare hierarchical Dirichlet, Bayesian shrinkage, EWMA, Markov and lagged transitions on paired whole-episode folds. Observed sampled Brier is different from exposed public true-probability validation points; hidden test truth is not known.
5. Run real bounded smoke/tests, capture exact commands, versions, source/config/split hashes, runtime and failures. Open own-branch PR for review if authorized. Do not modify champion, merge main, submit, or use paid cloud.
6. Request next issue only after #9 review; do not work on reserved #12/#15; #17 was claimed by Claude and has PR #22 simultaneously.
