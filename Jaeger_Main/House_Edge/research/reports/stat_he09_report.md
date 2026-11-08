# HE-09: Bayesian, Dirichlet, Markov and decay challengers

Issue: AsvM45/jaegers#9 (lane D, agent `claude-stats`). **Verdict: no promotion.** All three candidates are far
below the champion. The study is a negative result with two useful diagnostics (below).

## Provenance

- Pre-registered in `research/configs/stats/he09/plan.json`, committed and pushed in `8a9d185`
  (2026-11-07 19:19 CT) before any result was computed.
- Models: `research/challengers/stat_he09_models.py`; evaluation: `research/challengers/stat_he09_eval.py`;
  tests: `tests/test_stat_he09_models.py` (22 passed, fixed seeds, synthetic fixtures).
- Results: `research/reports/stat_he09_results.json`. sha256 (LF-normalized) prefixes: plan `f49dd840`,
  models `45ecdb19`, eval `508a0012`, champion `10da55e6`, params `af6fd598`.
- Run: `python -m research.challengers.stat_he09_eval --out research/reports/stat_he09_results.json` from
  `Jaeger_Main/House_Edge`; Windows 11, CPython 3.13.5, numpy 2.5.4, scikit-learn 1.9.1. Not on Linux; not in
  the #8 registry (not yet published by lane A).
- **Exposure:** the three candidates use no validation information at all (fit on the fit split's histories
  and query labels only). The champion's A score is development-exposed (params and `SIZE_REGIMES` from
  validation). A = fit on TRAIN, official `score_round` on VALIDATION. B = fit on VALIDATION, five-class
  observed-outcome Brier on TRAIN (lower is better). Paired episode bootstrap, 4000 resamples.

## Candidates (as pre-registered)

| model | idea | hyperparameters chosen on fit split (train / validation) |
|---|---|---|
| `stat_dirichlet` | type-level class prior tilted by type x query signal; machine posterior from decayed counts of its own past | decay 0.97 / 0.97; strength short 50 / 20, long 10 / 20 |
| `stat_markov` | direct five-class lag-context mixture (no context, lags 1-8, all pairs; 0/1/2+ contexts), Dirichlet-smoothed toward the machine marginal, weighted by decayed predictive log-likelihood | a 1 / 1; beta 2 / 1 |
| `stat_decay_bma` | average of Dirichlet posteriors at six half-lives, weighted per machine by predictive log-likelihood | s 20 / 20 |

## Results

| model | A points | stable | short_history | drift | shared_change | B Brier | runtime (both fits) |
|---|---|---|---|---|---|---|---|
| champion (exposed) | **55.122** | .067 | .117 | .092 | .077 | **0.3651** | 37.5 s |
| FrequencyModel (lane A, defaults) | 29.991 | 1.002 | 1.005 | .999 | .997 | 0.5705 | 0.8 s |
| stat_dirichlet | 30.852 | .963 | 1.016 | .937 | .863 | 0.5635 | 1.8 s |
| stat_decay_bma | 30.925 | .948 | .992 | .942 | .879 | 0.5642 | 1.6 s |
| stat_markov | 43.975 | .324 | .470 | .365 | .299 | 0.4181 | 10.7 s |

Paired differences (95% CI):

| comparison | A points | B Brier |
|---|---|---|
| stat_dirichlet vs FrequencyModel | +0.86 [+0.50, +1.22] | -0.0071 [-0.0140, -0.0003] |
| stat_decay_bma vs FrequencyModel | +0.94 [+0.63, +1.23] | -0.0064 [-0.0128, -0.0001] |
| stat_markov vs FrequencyModel | +13.98 [+12.90, +15.04] | -0.1524 [-0.1733, -0.1317] |
| stat_markov vs champion | -11.15 [-12.23, -10.05] | +0.0530 [+0.0402, +0.0661] |
| stat_dirichlet vs champion | -24.27 [-25.01, -23.48] | +0.1983 [+0.1778, +0.2181] |
| stat_decay_bma vs champion | -24.20 [-24.93, -23.44] | +0.1990 [+0.1784, +0.2190] |

20x behaviour (validation, A):

| model | mean predicted p_20 | mean true p_20 | correlation with true p_20 | B 20x Brier component |
|---|---|---|---|---|
| champion | 0.0147 | 0.0148 | 0.94 | 0.01475 |
| FrequencyModel | 0.0137 | 0.0148 | 0.45 | 0.01539 |
| stat_dirichlet | 0.0141 | 0.0148 | 0.55 | 0.01552 |
| stat_decay_bma | 0.0142 | 0.0148 | 0.55 | 0.01542 |
| stat_markov | **0.0245** | 0.0148 | 0.50 | 0.01662 |

## Reading against the pre-registration

| model | expected | observed |
|---|---|---|
| stat_dirichlet | beats FrequencyModel; far below champion | held (+0.86 A, B confirms; -24 vs champion) |
| stat_markov | well above Dirichlet; below champion, gap mostly size regimes + stacker | above Dirichlet (+13) and below champion (-11) held; the **cause of the gap is not tested** here, and #17 suggests stacker (2.3) + size experts (1.4) explain only part of it |
| stat_decay_bma | slightly better than Dirichlet, mostly drift/shared_change | about equal to Dirichlet (+0.07 A); slightly better in stable/short_history, slightly worse in shared_change: **not held** |

## Diagnostics worth keeping

1. **Counting models without lag context are at the reference level** (~30 points, loss ratios near 1): the
   pooled reference is essentially this family. Type x signal priors and decay add under one point.
2. **Lag context is the signal**: the direct five-class lag mixture gains 14 points over counting, with no
   size regimes, no validation constants, no siblings and no stacker.
3. **Size modelling explains much of the remaining gap**: the five-class lag mixture overpredicts 20x by 65%
   (0.0245 vs 0.0148) because each context's Dirichlet spreads mass over rare classes. The champion's
   win x size factorization is almost perfectly calibrated on 20x (0.0147, r = 0.94).

## Follow-ups (none promoted)

1. Factorize `stat_markov` into P(win | lag context) x P(size | win) with an exposure-free size model (e.g. the
   train-only HMM proposed in #3) to measure how much of the 11-point gap is size modelling.
2. Add same-episode peer evidence to `stat_markov` only after lane E (#11) defines the cross-machine interface.
3. Register these runs in the #8 registry once published.
