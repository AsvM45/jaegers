# HE-15: regime-switching / HMM / temporal challengers

Issue: AsvM45/jaegers#15 (agent `claude-stats`). **Verdict: no promotion** (all candidates are below the champion),
but one positive, pre-registered result: **learned size regimes fix the five-class lag model's 20x calibration and
add +2.2 official points**, without any validation-derived constants.

## Provenance

- Pre-registered in `research/configs/stats/temporal_he15/plan.json`, pushed in `a75d812` (2026-11-07 21:52 CT)
  before any result.
- Models: `research/challengers/stat_temporal_models.py` (registry factory included). Evaluation A:
  `research/challengers/stat_temporal_eval.py`. Tests: `tests/test_stat_temporal_models.py` (19 passed).
- Results: `stat_temporal_official.json` (A), `stat_temporal_official_paired.json` (paired A intervals),
  `stat_temporal_registry_results.json` (R).
- Runs: main `f77c112` + this branch, Windows 11, CPython 3.13.5, `requirements-research.txt`. Not on Linux.
- **A** = fit on TRAIN, official `score_round` on VALIDATION. The candidates use no validation information; the
  champion's 55.12 is development-exposed. **R** = #8 registry, 4 condition-stratified whole-episode train folds,
  sampled-label five-class Brier (not points), intervals from `research.metrics.paired`.
- SARIMA/SARIMAX were **not run** (no seasonality evidence was sought or claimed); scalar expected-payout ARIMA is
  excluded by the issue.

## Results

| model | A official points | R Brier (lower better) | 20x: mean pred (true 0.0148) | 20x corr | fit+predict A |
|---|---|---|---|---|---|
| champion (exposed) | 55.12 | **0.3623** (`1dc8c749`) | 0.0147 | 0.94 | - |
| **stat_temporal_factorized** | **46.18** | 0.4116 (`66270e70`) | **0.0155** | **0.88** | 78 s |
| stat_markov (HE-09) | 43.98 | 0.4177 (`175adaba`) | 0.0245 | 0.50 | 14 s |
| stat_temporal_hmm | 31.85 | 0.5544 (`fc33d899`) | 0.0138 | 0.65 | 44 s |
| stat_temporal_ar1 | 30.83 | 0.5627 (`b661abd9`) | 0.0134 | 0.52 | 0.6 s |
| FrequencyModel | 29.99 | 0.5705 (`b66b1800`) | 0.0137 | 0.45 | - |

Paired comparisons:

| comparison | A official points diff [95% CI] | R Brier diff [95% CI] |
|---|---|---|
| factorized vs HE-09 markov | **+2.21 [+1.69, +2.76]** | -0.0061 [-0.0149, +0.0030] |
| factorized vs champion | about -8.9 | +0.0493 [+0.0380, +0.0607] |
| hmm vs FrequencyModel | about +1.9 | -0.0161 [-0.0266, -0.0059] |
| ar1 vs FrequencyModel | about +0.8 | -0.0078 [-0.0153, -0.0000] |

Both models chose K = 3 states on the fit split (by query-label log score).

## Reading against the pre-registration

| model | expected | observed |
|---|---|---|
| stat_temporal_hmm | about the counting baselines (~31) | 31.85: held; beats FrequencyModel on both A and R |
| stat_temporal_factorized | better than markov and better-calibrated 20x; below champion | held: +2.21 points (interval > 0), 20x corr 0.50 -> 0.88; R points the same way but its interval spans 0 |
| stat_temporal_ar1 | weak sanity baseline | held |

Why A and R differ for the factorized model: R scores one sampled outcome per query, so a better-calibrated rare
class (20x at ~1.5%) barely moves it; A scores against the true probability vectors, where 20x calibration matters.

## What this tells us

1. **Hidden size regimes are learnable from history alone.** A 3-state size HMM over win ticks gives 20x
   predictions nearly as well calibrated as the champion's validation-derived `SIZE_REGIMES` (mean 0.0155 vs
   0.0147). That is the exposure-free regime estimator #3 and #17 asked for, and the obvious tool if the
   adaptation round's size regimes change.
2. **Regimes alone are not the signal**: the full HMM without lag context stays near the counting baselines.
3. **Next (not done here):** try the size HMM as a replacement for `SIZE_REGIMES` inside the champion, or
   blend the factorized model with the champion out of fold. Both need lane A / #12 coordination.
