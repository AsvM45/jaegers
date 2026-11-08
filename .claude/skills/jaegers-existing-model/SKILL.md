---
name: jaegers-existing-model
description: Use when inspecting or modifying existing jaeger_model.py, its lag experts, payout-size regime mixture, or gradient-boosted stacker.
---

# jaegers-existing-model

1. Read actual `jaegers_entry/jaeger_model.py`, `predict.py`, `params.json`, `README.md`; compare to HEAD and any dirty local edits before proposing changes.
2. Preserve frozen baseline. Explain the model: 73 lag experts (1 base + 2*(8+28)), exponential counts and log-likelihood, sibling evidence, size-regime mixture, optional HistGradientBoosting stacker.
3. Check stacker training `stack_features` includes query-time signal across historical pseudo-examples; signal(t) not documented. Test a no-signal historical stack and compare on episode-held-out folds.
4. `SIZE_REGIMES` source comment says derived from validation targets. Verify allowed use but mark public-validation selection exposure and create independent train-side comparisons when possible.
5. Watch output normalization, missing observations, model prior refit from `data/train`, `collect=True` behavior, memory/runtime on 2 CPU.
6. Do not silently replace observed score with a commit message. Distinguish local exact scorer results from user-reported scores.
