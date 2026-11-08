# HE-03 audit: historical signal and as-of lineage of the stacker

Status: **measured, recommendation made, champion untouched.** Issue: AsvM45/jaegers#3.
Audited source: `jaegers_entry/jaeger_model.py` sha256 `10da55e6…2fa0c3`, `params.json` sha256
`af6fd598…7b4e3b` (full hashes in `historical_signal_results.json`, `source_sha256`). All scores below are from real runs on 2026-11-07
(CPython 3.13.5, numpy 2.5.4, scikit-learn 1.9.1, Windows 11).

Public-validation numbers are **development scores**: params and `SIZE_REGIMES` were chosen on
those targets (see `size_regimes.md`). Nothing here says anything about the hidden test score.

## 1. Lineage of the 14 stacker features (historical row at tick t)

Rows are built in `predict(..., collect=True)` (`jaeger_model.py:185-198`): features are computed
from state *before* the spin at t is applied, label = observed win at t. Columns of `stack_features`
(`:181-182`, column 0 is a constant and is dropped by `fit_stacker`):

| col | feature | source | visible at t? |
|---|---|---|---|
| 1-4 | logit of blend, top expert, 2nd expert, base rate | counts W/N, base_w/base_n updated only with ticks < t (`:204-212`) | yes |
| 5-7, 8-10 | top weight, disagreement, top count, interactions | expert log-likelihood LL from ticks < t; sibling LL from same-episode machines, ticks < t (`:164-166`) | yes |
| (inside 1-10) | `gamma * expert_logprior` (`:168-169`) | `learn_expert_prior` = argmax of each train machine's **final** LL (`:289-297`) | **no** - pooled over all train machines, includes ticks > t |
| (inside 1-10) | smoothing regime `lam_short`/`prior_short` (`:106-108`) | `nobs` = count of observed ticks **before the cutoff**, not before t | **no** - total coverage decides how older rows are smoothed |
| 11-12 | machine type | static query field | yes (static) |
| **13** | **signal** | query-time value from `queries.csv`, copied to every historical row (`:156`, `:182`) | **unknown** - `signal(t)` is not released |
| 14 | log(1+spins seen) | running count to t (`:210`) | yes |

At test inference all three flagged items are legitimately available (the prior comes from the
train split, `nobs` and `signal` are known at the cutoff). The issue is only train/serve skew in the
stacker's training rows, not test-label leakage.

Regression fixtures: the teammate's `tests/test_temporal.py` on `origin/main` (d3a5158) already
proves both mechanisms - `test_historical_signal_finding_and_physical_removal` (changing only
query signal changes col 13 of old rows and nothing else) and
`test_final_history_coverage_leaks_into_old_features` (deleting ticks 70-127 changes rows < 60).
The in-sample expert-prior item has no fixture yet.

Probes run in this audit on the full test split (all pass, max diff 0.0): future-tick injection
(50 fake ticks at/after every cutoff), dropping a whole episode (other episodes unchanged),
removing one pre-cutoff tick (other episodes unchanged). Every split has exactly one cutoff per
episode and no history tick at/after the cutoff.

## 2. What `signal` behaves like

Win rate of train machines by query signal, in history windows relative to the cutoff c:

| window | sig -1 | sig 0 | sig +1 |
|---|---|---|---|
| early `[0, c-96)` | 0.358 | 0.402 | 0.483 |
| mid `[c-96, c-16)` | 0.365 | 0.406 | 0.484 |
| late `[c-16, c)` | 0.388 | 0.411 | 0.491 |
| next spin (label) | 0.404 | 0.386 | 0.530 |

(Validation looks the same.) The association is as strong 100+ ticks before the cutoff as just
before it, so `signal` acts like a persistent machine attribute rather than information local to
the cutoff. That makes copying it onto older rows plausible, but it does not prove `signal(t)` was
constant - only the organizers can confirm that. Signal varies across machines within every episode.

## 3. Matched ablation

Script: `research/challengers/signal_ablation.py` (imports the champion read-only).
Output: `historical_signal_results.json`. Same code path for every variant; only the listed change differs.
Paired bootstrap: 4000 resamples of episodes within condition.

**A. Fit on TRAIN, official scorer on VALIDATION targets** (`slot_forecasting.rounds.score_round`)

| variant | points | stable | short_history | drift | shared_change | vs champion (95% CI) |
|---|---|---|---|---|---|---|
| champion | **55.1216** | .0673 | .1170 | .0923 | .0774 | - |
| nosig (drop col 13, refit) | 55.0001 | .0672 | .1223 | .0945 | .0796 | -0.12 [-0.25, -0.00] |
| causal (nosig + no short-history smoothing) | 54.6433 | .0675 | .1496 | .0975 | .0775 | -0.48 [-0.70, -0.25] |
| nostack | 52.8362 | .1196 | .1845 | .1247 | .1136 | -2.29 [-2.93, -1.72] |

**B. Fit on VALIDATION, five-class Brier on TRAIN observed next-payout labels** (lower is better;
independent of validation target vectors except `SIZE_REGIMES`)

| variant | mean condition Brier | vs champion (95% CI) |
|---|---|---|
| champion | 0.36514 | - |
| nosig | 0.36473 | -0.0004 [-0.0019, +0.0011] |
| causal | 0.36545 | +0.0003 [-0.0019, +0.0026] |
| nostack | 0.37276 | +0.0076 [+0.0033, +0.0119] |

## 4. Reading

- The stacker itself is clearly real: it helps in both directions with intervals far from zero.
- Signal in the stacker: worth +0.12 points on validation (interval barely excludes 0), and
  **no measurable effect** on held-out train labels (direction B, interval spans 0). The gain is
  small and only confirmed on the selection-exposed split.
- The teammate's `causal` recipe is **not** a drop-in fix: setting `lam_short=lam, prior_short=prior`
  also removes short-history smoothing at inference, which costs 0.48 points, almost all in
  `short_history` (.117 -> .150). A proper fix would compute `nobs` as-of each historical row
  (observed spins before t) for training rows while keeping cutoff `nobs` at inference.

## 5. Recommendation

1. **Main release: keep the champion as is.** No test-label leakage was found; the flagged items
   are train/serve skew inside the stacker's training rows, and the available evidence says removing
   signal changes little. Do not swap models hours before the deadline on a 0.1-point effect.
2. **Ask organizers** (via #5) whether `signal` is constant over a machine's history. If yes, the
   copy is correct as is. If no, switch to `nosig` (expected cost about 0.1 validation points, no cost
   on held-out train labels).
3. **Challenger work (post-release):** (a) per-row as-of `nobs` for the smoothing regime, (b) expert
   prior learned cross-fitted by episode so a row's prior excludes its own machine's future,
   (c) re-run this script for each, plus an episode-grouped CV inside train for a third estimate.
