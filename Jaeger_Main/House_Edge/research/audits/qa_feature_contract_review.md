# HE-07 feature contract review (lane C)

Issue: AsvM45/jaegers#7. Reviewed at `origin/main` 26f2343: `research/features.py`, `research/dataset.py`,
`research/learners.py` (all lane A, read-only). New files only: `tests/test_agent_qa_features.py`,
`research/extensions/qa_size_streak.py`, this note.

## Run

From `Jaeger_Main/House_Edge`, venv from `requirements-research.txt`:

```
python -m pytest tests/test_agent_qa_features.py -q
```

Observed 2026-11-07, Windows 11, CPython 3.13.5, pytest 9.2.0, numpy 2.5.4: **12 passed (~7 s)**;
whole `tests/` on this branch **17 passed**. Not run on Linux or in CI (#16, Cursor).

## As-of contract: verdict PASS

| Contract | Evidence |
|---|---|
| Target ticks >= origin t never read | `_past()` uses `searchsorted(side="left")`; test rewrites all ticks >= t (and adds 12 future ticks) for 40 random real train origins: rows identical |
| Sibling ticks >= t never read | same mutation applied to every machine of the episode; `peers` unchanged. Positive control: an earlier sibling tick does move `peers` |
| Exact missing lag is not 0x | on 80 real origins, `lag{k}_0` (missing slot) and `lag_known_{k-1}` match `(t-k) in history` for k=1..8, missing cases present |
| Signal query-only | `current_signal` excluded from `HISTORICAL_GROUPS`, rejected by `validate_groups(historical=True)`, changes only its own columns; cache records `historical_signal_policy: omitted` with no signal column |
| Cache rows are as-of | every historical row in a built cache equals a fresh registry row at `cutoff=t`, label = observed payout at t, t < query cutoff |
| Cache invalidation | key changes with input bytes, `stride`, and `features.py` source hash; identical inputs reuse the cache |
| Group toggles | `feature_columns` returns exactly the columns of the requested groups; dependency/duplicate/unknown groups rejected |

Notes (no action required, flagged for lane A):
- The cache key does not include numpy/Python version; float32 rows could differ across library builds.
  `environment()` exists in `common.py`; adding it to `identity` would make the key stricter.
- `row()` assigns `rows = self.history[...]` and never uses it.

## Current vs missing feature matrix

| Family (from #7 brief) | Present in registry | Gap |
|---|---|---|
| counts | `windows/count{8,24,64}`, `decays/mass*` | - |
| EWMAs | `decays/freq{.9,.97,.995}` over 5 payout classes | win rate and payout size are mixed in one 5-class distribution |
| machine type | `type/onehot` (static) | - |
| current signal | `current_signal` (query rows only) | historical signal(t) not released; correctly absent |
| lags 1-8 | `lags` one-hot incl. missing slot; `pairs` (3-way categories) | - |
| missingness | `missingness/coverage`, `lag_known` | - |
| drift / change | `changes/recent_minus_past`, distance, entropy | - |
| sibling patterns | `peers/freq`, `peers/recent`, `peers/mass` | no sibling **lagged** outcomes (sibling payout at t-k) -> belongs to lane E #11, not added here |
| type x lag | `type_lag/interaction` | - |
| size given win | - | **missing**: the champion's strongest structure (two size regimes per type) has no direct feature |
| recency of wins / streaks | - | **missing**: elapsed ticks since last win, current run length |
| champion expert summaries | - | blend/top-expert probabilities live only in the champion; exposing them is lane A/#8 territory |

## Extension: `research/extensions/qa_size_streak.py` (not wired in)

Nine columns, prefix `qa_size_streak/`: decayed size-given-win distribution over (1x, 2x, 5x, 20x) and its
win mass, log ticks since last observed win, ever-won flag, current run length over **consecutive observed**
ticks and whether it is a win run. Built only from `FeatureComputer._past`, so it inherits the as-of
contract. Tests: as-of on 40 real origins, hand-computed values, missing `cutoff-1` gives streak 0 (not a
loss), and a negative control where a leaky `_past` is caught.

Predictive value is **not measured**. Proposed handoff: lane A adds an optional `qa_size_streak` group to
`REGISTRY` (availability `past_only`, no dependencies) by calling `row()`; #8 trials then compare with/without
on episode-grouped folds. No production wiring without lane A's approval.
