# HE-15 follow-up: blending the champion with the factorized temporal model

Issue: AsvM45/jaegers#15. #12 (ensembles, Cursor) closed without the champion in its ensemble, so this tests the
open question: **does combining the champion with the HE-15 factorized model help?** **Answer: no.** Negative,
pre-registered result; champion unchanged.

## Provenance

- Pre-registered in `research/configs/stats/temporal_he15/plan_blend.json`, pushed in `6ba7c89`
  (2026-11-07 22:09 CT) before any blend result.
- Code: `research/challengers/stat_temporal_blend.py` (size-swap registry factory + nested-OOF blend analysis).
  Tests: `tests/test_stat_temporal_blend.py` (6 passed, including a check that nested weight selection never sees
  the held-out fold). Results: `research/reports/stat_temporal_blend_results.json`.
- Commands (from `Jaeger_Main/House_Edge`):
  `python -m research.challengers.stat_temporal_blend --registry research_runs/he15_registry --out research/reports/stat_temporal_blend_results.json`
  and `python -m research.sweep --study research/configs/stats/temporal_he15/registry_blend_study.json --out research_runs/he15_registry`.
- Windows 11, CPython 3.13.5. R = sampled-label Brier on the #8 registry's 4 grouped train folds (not points).
  A = official validation points; development-exposed for anything containing the champion.

## 1. Linear blend p = w * champion + (1 - w) * factorized

Out-of-fold train Brier over w (from registry OOF predictions; champion trial `1dc8c749`, factorized `66270e70`):

| w (champion weight) | 0.0 | 0.2 | 0.4 | 0.6 | 0.8 | 0.95 | **1.0** |
|---|---|---|---|---|---|---|---|
| OOF Brier | 0.4116 | 0.3961 | 0.3834 | 0.3736 | 0.3665 | 0.3631 | **0.3623** |

The curve falls steadily to w = 1, with no interior optimum. Nested selection (pick w on 3 folds, apply to the 4th)
chose **w = 1.0 in all four folds**, so the nested blend is the champion: delta 0.0. On official validation, with w
taken from train OOF only, the blend scores **55.1216** = the champion.

## 2. Size swap: champion P(win) x learned size-regime HMM P(size | win)

| | champion | size_swap | difference [95% CI] |
|---|---|---|---|
| A official points | 55.12 | 54.07 | **-1.05 [-1.36, -0.78]** |
| R Brier (`a9fc4231` vs `7e7411d4`) | 0.3623 | 0.3695 | **+0.0072 [+0.0027, +0.0116]** (worse) |

Replacing the champion's `SIZE_REGIMES` with the learned size HMM loses about one point. On validation that is
partly expected (those constants were read off validation targets), but the train folds, which those constants
never saw, show the same loss. So the champion's per-context size experts plus fixed regimes beat a per-type
learned regime model on both measures.

## Conclusions

1. **Don't blend the champion with the HE-15/HE-09 models.** The champion dominates them everywhere a weight is
   free to move. This also explains #12's negative result: every candidate model is far weaker than the champion.
2. **Keep `SIZE_REGIMES` in the champion** for the main round. The learned size HMM is the fallback only if the
   adaptation round's size regimes visibly change: re-estimate there and re-run this comparison on adaptation
   validation before choosing.
3. The factorized model's value is diagnostic: it showed that size modelling explained a large part of the
   five-class lag model's gap. It is not a useful ensemble partner for the champion.
