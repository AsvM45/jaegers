# Grok Build — JAEGERS statistical research lane D

**Default reserved issue:** [#9 Bayesian / Dirichlet / Markov challenger](https://github.com/AsvM45/jaegers/issues/9). Future, **not concurrent**: [#17 ablations](https://github.com/AsvM45/jaegers/issues/17), [#12 ensembles](https://github.com/AsvM45/jaegers/issues/12), [#15 advanced temporal](https://github.com/AsvM45/jaegers/issues/15).

Grok Build official docs say it reads `AGENTS.md`, `CLAUDE.md`, and Claude Code skills, so shared repository policy and skills apply; no duplicate long Grok-only rule set is necessary. The Grok CLI is `grok`, after normal product authentication (never store tokens in Git). [Grok Build docs](https://docs.x.ai/build/overview), [skills compatibility](https://docs.x.ai/build/features/skills-plugins-marketplaces).

## New isolated Grok worktree — only if not already in use

```powershell
$repo = "C:\Users\asvat\OneDrive\Documents\GitHub\Datathon2026\jaegers"
cd $repo
git worktree list
git fetch origin
git worktree add -b agent/grok-he09 ../jaegers-grok-he09 origin/main
cd "../jaegers-grok-he09/Jaeger_Main/House_Edge"
grok
```

**Before invoking**, confirm the #9 issue is still unclaimed and `agent/grok-he09` not already present. If so, claim #9 with your distinct session/worktree name.

## Grok launch prompt

> You own JAEGERS issue #9, not any other issue. Read applicable AGENTS.md and CLAUDE.md, docs/AGENT_OPERATING_POLICY.md, docs/AGENT_CONTEXT.md, docs/MULTI_AGENT_OWNERSHIP.md, docs/GROK_START.md, latest GitHub #9 and #18 claim comments, organizer House Edge RULES.md/DATA.md and the existing research adapter contracts. Verify isolated worktree and source state; claim only #9 before implementation. Build and validate 3 distinct Bayesian/Dirichlet/Markov/recency challenger configurations in NEW research/challengers/stat_*.py, tests/test_stat_*.py and research/configs/stats files, leaving protected champion, flat research/models.py, features.py, learners.py, and other agents' work read-only. Every predictor must emit valid five-class [0,1,2,5,20] probabilities based on tick<cutoff observations, with no missing-tick-as-zero confusion or historical query signal leakage. Use same episode folds and legitimate observed-outcome Brier; record official public-validation true-vector results only where available and label selection exposure. Run real smoke tests, compare against frozen champion, log failed models and actual runtimes, open an issue-linked PR on your own branch when authorized, and report evidence. No cloud spend, main push, organizer upload or cross-lane work. Work until acceptance/real blocker, not just a plan.

## Handoff and next issue

After #9 review, owner may request next assignment. Grok does not auto-claim #12/#15/#17. For interface needs request A's #8 schema/adapter approval; don't overwrite it.