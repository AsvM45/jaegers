# HE-03 follow-up: as-of ("causal") stacker challenger

Issue: AsvM45/jaegers#3 (agent `claude-qa`). Fixes the three train/serve look-aheads the #3 audit found in the
champion's stacker training rows, as a **challenger**; the champion is unchanged. **Verdict:** one fix is free and is
a defensible drop-in (cross-fitted expert prior); full as-of hygiene costs about 0.3 official points; the
pre-registered query-time signal head *hurts* and should be dropped. No promotion by this study.

## Provenance

- Pre-registered in `research/configs/qa_causal_stacker/plan.json`, pushed in `6747faa` (2026-11-07 22:27 CT)
  before any result.
- Code: `research/challengers/qa_causal_stacker.py`, a copy of the champion's `predict()` (champion source sha256
  LF `10da55e6...`, constants imported from the champion file) with three switches. Evaluation A:
  `research/challengers/qa_causal_stacker_eval.py`. Registry study: `research/configs/qa_causal_stacker/registry_study.json`.
- **Parity gate:** with every fix off the copy equals the champion exactly: predictions, log-likelihoods,
  stacker training matrix, and full fit+predict all 0.0 difference (tested).
- Tests: `tests/test_agent_qa_causal_stacker.py`, 12 passed, including the audit's coverage fixture (deleting late
  ticks changes early stacker rows in the champion but not with the running regime), cross-fit isolation, signal
  isolation, future-tick invariance for every variant and a registry-snapshot import test.
- Runs: main `f77c112` + this branch, Windows 11, CPython 3.13.5. A = fit on TRAIN, official `score_round` on
  VALIDATION (development-exposed), paired bootstrap of episodes. R = #8 registry, 4 grouped train folds,
  sampled-label Brier (`research/audits/qa_causal_stacker_registry.json`).
- Disclosed: the first A run failed on an import from my unmerged #15 branch (PR #52); the scoring helper was
  inlined and A was re-run. The registry run was unaffected (5/5 SUCCEEDED, 345 s).

## Results

| variant | fixes | A official points | A vs champion [95% CI] | R Brier | R vs champion [95% CI] |
|---|---|---|---|---|---|
| champion | - | **55.1216** | - | 0.36229 | - |
| **prior_only** | cross-fitted expert prior | **55.1338** | **+0.01 [-0.09, +0.11]** | 0.36220 | -0.0001 [-0.0011, +0.0009] |
| regime_only | running lam/prior regime | 54.9262 | -0.20 [-0.32, -0.07] | 0.36325 | +0.0010 [-0.0009, +0.0028] |
| causal_all_nohead | regime + prior + signal removed | 54.8358 | -0.29 [-0.43, -0.12] | 0.36399 | +0.0017 [-0.0006, +0.0041] |
| causal_all | + query-time signal head | 54.6099 | -0.51 [-0.80, -0.23] | 0.36295 | +0.0007 [-0.0033, +0.0049] |

Trial ids: champion `6403b07b`, causal_all `3c8a208e`, nohead `5127ac97`, regime `5508fbcd`, prior `1d669e1c`.

## Reading

1. **Cross-fitted expert prior: free.** Same score on both measures. The full-history prior was a real
   look-ahead but carried no measurable advantage, so it can be removed at no cost.
2. **Running regime: costs about 0.2 points on validation** (interval excludes 0); not distinguishable on train
   folds. Total coverage is a legitimate fact at the cutoff, and switching training rows to "coverage so far"
   changes how the stacker learns short-history behaviour, so the champion's rule may simply fit the
   validation conditions better. It is the price of strict as-of hygiene, not evidence of a leak benefit on test.
3. **Removing signal from historical rows: about 0.09 more**, consistent with HE-03/HE-17 (nosig about 0.1).
4. **The query-time signal head hurts** (-0.23 relative to no head). A logistic correction fitted on 768 sampled
   query outcomes appears to overfit or distort the stacker's calibration. **Pre-registered expectation not met:**
   I expected causal_all within 0.2 points; it lost 0.51.

## Recommendation (human / lane A decision)

- **Adopt the cross-fitted expert prior** in a future champion revision if any champion change is made anyway: it
  removes one audit finding at zero measured cost. It is the only variant meeting the pre-registered
  "defensible drop-in" rule (A within 0.25 points and R interval including 0).
- **Keep `causal_all_nohead` ready as the fully as-of fallback** (-0.29 points) if organizers rule that copying
  query signal or final coverage into historical rows is not allowed. Do **not** use the signal head.
- Champion remains the main-round entry; nothing here is promoted automatically.
