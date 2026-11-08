---
name: jaegers-experiment-factory
description: Use for feature-group sweeps, Optuna search, trial tracking, scientific ablations, or new model families.
---

# jaegers-experiment-factory

1. First reproduce current champion candidate and freeze its config/source SHA as comparison anchor.
2. Choose a scientific hypothesis and one feature-family delta. Trials must have immutable config, git state, raw hashes, split manifest, seed, dependencies, feature lineage, score source, timings, memory, output SHA and failure state.
3. Distinguish train-label Brier proper score versus public validation true-vector official loss. Do not compute fake technical points for train-label experiments.
4. Compare candidates on matched held-out **episodes**, paired errors, all four conditions where true targets available; limit validation peeking and record exposure.
5. Feature masks must physically remove features in both train and inference; interactions declare prerequisites. Use budgeted sweeps, single process first, then bounded CPU; no brute-force 2^N explosion.
6. Only retain a challenger if non-leakage tests, robustness and offline reproduction pass. Log strongest rejected alternative and why.
