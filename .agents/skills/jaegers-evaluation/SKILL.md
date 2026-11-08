---
name: jaegers-evaluation
description: Use when designing train/validation folds, model selection, condition diagnostics, or interpreting a House Edge score.
---

# jaegers-evaluation

1. At query cutoff c, forecast the 5-vector using only history tick<c. In as-of historical pseudo-row at t, label is observed payout(t) and features are past <t.
2. Eval layers: training episodes grouped CV with sampled one-hot Brier; optional forward-chaining inside fit episode; public validation with true probability vectors, frozen references and equal four-condition episode-averaged loss ratios; test format and reproducibility only.
3. `slot_forecasting.scoring.score_predictions` returns a generic 0–100 diagnostic, NOT the official 60/(1+R) score. For official public validation use `check_submission.py --split validation` or `rounds.score_round`.
4. Hidden main test true odds unavailable. Main 9 PM Saturday, adaptation 11 AM Sunday. Conflict older 80/20 guide vs current kit 60/40 remains unresolved absent organizer statement.
5. Condition labels are training/validation diagnostics; never feed oracle test condition. A condition classifier is useful only if its gating improves held-out forecast loss.
6. Report split source, exposure to validation target constants, fold identifiers, and whether score is independent or development-tuned.
