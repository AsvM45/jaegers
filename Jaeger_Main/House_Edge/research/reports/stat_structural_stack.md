# Issue #58: structural XOR/XNOR lag-rule features for the stacker

Agent `claude-stats`. **Result:** adding four inputs from an online six-rule posterior to the champion's stacker
improves the champion on two independent checks: official validation **+0.39 points [+0.03, +0.84]** (55.515 vs
55.122) and a high-powered walk-forward test on train **-0.0034 Brier [-0.0041, -0.0027]**. The gain is
concentrated where intended: **short_history** (validation loss ratio 0.117 -> 0.089; walk-forward -0.0145).
The champion is unchanged; promotion is a human / lane A decision.

## Why: diagnosis (public validation used for understanding only)

- short_history is the worst condition (loss ratio 0.117 vs 0.067-0.092). Substituting the true P(win) into the
  champion's forecast drops it to 0.047; substituting the true size distribution only to 0.071. **The error is
  mainly P(win).**
- The champion is well calibrated by true-P(win) band; short-history loss comes from machines it cannot
  identify from ~64 observed ticks (24 scattered + 40 consecutive), i.e. ~30 usable lag contexts.
- **Simulator structure (train):** the best expert is almost always one of three lag pairs (1,3), (2,5), (4,7),
  and on stable machines the rule is **XNOR or XOR of win/loss at that pair** (6 hypotheses cover 152/183;
  median context purity 0.92). Siblings do not share rules beyond chance.

## Experiments (all pre-registered; files in `research/configs/stats/structural/`)

| # | pre-registration (sha256 prefix, written) | experiment | outcome |
|---|---|---|---|
| 1 | `bc9410dd` 23:04 CT | stronger train-learned expert prior, gamma 2/4/8 (registry) | gamma 8: train -0.0022 [-0.0042, -0.0003], but not via short_history; **validation 55.077 (-0.04, n.s.) -> neutral** |
| 2 | `4a00f008` 23:09 CT | standalone six-rule model P(win) vs champion P(win) (registry folds) | **worse**: +0.017 win-Brier overall, +0.012 short (n.s.) |
| 2b | exploratory, not pre-registered | same with per-machine on/off rates | ties short/stable, much worse drift/shared -> stopped |
| 3 | `0cdfa639` 23:29 CT | **champion + 4 rule-posterior stacker inputs** (this challenger) | parity 0.0; registry -0.0015 [-0.0043, +0.0013] (same direction, n.s.); **validation +0.39 [+0.03, +0.84]** |
| 4 | `bbf16f34` 23:35 CT | walk-forward train test of the unchanged model #3 (40 earlier cutoffs per held-out episode, 30,720 labels) | **-0.0034 [-0.0041, -0.0027]**; short -0.0145 [-0.0165, -0.0125]; stable -0.0020; drift +0.0009 (n.s.); shared +0.0020 |

The pre-registrations were written locally before each run and their sha256 recorded in the working session at
the stated times; they are committed here unchanged (hashes match). Experiment 4 was designed after seeing
#3's registry and validation results, and says so; its model is identical to #3.

### Experiment 3/4 details

| condition | validation loss ratio: champion -> challenger | walk-forward Brier delta [95% CI] |
|---|---|---|
| stable | 0.0673 -> 0.0645 | -0.0020 [-0.0031, -0.0010] |
| **short_history** | **0.1170 -> 0.0889** | **-0.0145 [-0.0165, -0.0125]** |
| drift | 0.0923 -> 0.0983 | +0.0009 [-0.0001, +0.0018] |
| shared_change | 0.0774 -> 0.0715 | +0.0020 [+0.0008, +0.0033] |
| **overall** | **55.122 -> 55.515 points** | **-0.0034 [-0.0041, -0.0027]** |

The two checks agree on short_history and stable. Drift is slightly worse on both. Shared_change disagrees
(better on validation, slightly worse on walk-forward), so treat it as neutral.

## Method

`research/challengers/stat_structural_stack.py`:
- `core_predict`: parity-exact copy of the champion's `predict()` (constants read from `jaegers_entry/`), whose
  stacker features accept an optional `extra` (M, T+1, F) array. `extra=None` gives the champion bit for bit.
- `SWM`: online Bayesian posterior over 6 rules {(1,3),(2,5),(4,7)} x {XNOR, XOR} + a null forgotten base rate.
  A rule abstains (null rate) when either lag is missing; missing ticks are never treated as 0x. p_on/p_off, the
  rule prior and the forgetting rate are fit on the fit split only.
- `swm_features`: per machine and tick t, from ticks < t: logit P(win), max rule posterior, null posterior,
  logit x max posterior.
- `StructuralStack`: champion fit, plus those 4 columns appended to every stacker row (historical and query);
  same HistGradientBoosting settings and seed. `factory()` for the #8 registry.

Tests (`tests/test_stat_structural_stack.py`, 7): core parity, model-without-extra equals champion, features at
tick t unchanged when ticks >= t change, true-rule recovery on synthetic XNOR machines, missing lags abstain,
future-tick and episode isolation, registry snapshot import.

## Caveats and risks

- Validation was used once for this model; its params come from the champion (validation-tuned) plus fit-split
  rule parameters. The walk-forward pseudo-queries reuse each machine's final query signal for both models.
- Runtime is about 2x the champion's fit (per-tick rule features in Python); the main test split took about 1 min
  locally, well under the 30 min limit, but **Linux cold reproduction has not been run**.
- Drift worsens slightly (+0.006 validation ratio). A drift-aware rule forgetting rate is a natural next step,
  chosen on train folds only.
- Not packaged as an entry. If adopted, the release owner must package it (entry folder, pins, Linux cold
  reproduction with the pinned CPU policy, see #6 runbook) and choose main vs adaptation use.
