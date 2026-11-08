# Evidence-based adversarial technical audit

## Model architecture at current inspected HEAD
- 73 experts: base + single and pair lags 1–8 with binary and 3-state contexts.
- Beta-style smoothed nonzero probability; exponentially discounted counts and expert likelihoods; cross-machine within-episode boosting of expert rankings.
- Conditional winning-amount distribution uses two fixed payout-size regime shapes per machine type; current model has context-specific size experts and episode sibling weighting.
- `fit_stacker()` constructs historical win/non-win examples after 20 observed spins and trains deterministic HistGradientBoostingClassifier with settings from params; current entry calls this on round training histories every run.
- Predict command reads `/data/train` for expert priors and stacker fitting, then `/data/test` for outputs.

## Actionable review items (priority order)
1. **P0: Query-time signal used in historical training rows.** `stack_features` makes `sig = [q["signal"]]` once; `predict(... collect=True)` invokes it at historical ticks `t`, using final cutoff signal. Earlier `signal(t)` is not part of history CSV. This violates a strict past-only *feature-availability assumption* unless organizer independently establishes signal stability/availability. Do not call it proven cheating; instead test no historical signal and isolate score impact.
2. **P0: Public-validation target parameters.** `SIZE_REGIMES` describes shapes as read from released validation `targets.csv`. This is selection-data exposure; no independent claim can be made from same validation 55.12/60. Inspect legality with organizer and compare train-only reconstruction/ablation on episode-held-out evaluation.
3. **P0: Release dependencies.** Current `jaegers_entry` imports NumPy, new scikit-learn, but tracks no `requirements.txt`; old README mentions `numpy==2.5.3` and 'no training step'. Determine exact tested compatible versions for Python 3.13/Linux; check packaging root and offline provisioning.
4. **P0: Exact numerical reproducibility.** Current repo tracks no generated official test CSV or archive. `check_submission.py` can score public validation but test only format. Need match actual intended CSV and reproducer to tolerance 1e-8.
5. **P1: Split integrity.** Make a read-only frozen baseline; diagnose 55.12 claim, score by four conditions, compare from *untouched* train episodes where possible. Abnormal improvement alone is not proof of hidden-test success.
6. **P1: Previous README and runtime.** Resolve claimed ~5 seconds/one CPU and 'no training' versus actual fit_stacker (~20 seconds indicated in source) with fresh measured runtime under limits.
7. **P1: Comparison ablations.** Freeze expert-only/no stack, train-signal-removed stack, size regime prior from training only, short-history strength, sibling weight, and global pseudo-example training (all evaluated on same episode folds).
8. **P2: Interface/test organization.** Add targeted pytest once P0 safe; do not refactor organizer `slot_forecasting` implementation without a reproducible necessity.

## Important scientific distinction
Past-only features and independent evaluation are **different**. Historical example labels are observed payouts at t, not hidden true simulator probabilities. Train-only episodes can support multiclass Brier selection; public validation targets permit exact competition loss, but selecting many models on them makes that score biased as a generalization estimate. Test history is legitimate input; test unknown query outcomes never are.
