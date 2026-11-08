# JAEGERS Experiment Factory — current human-facing guide

**Updated:** 2026-11-08 · This guide reconciles the complete Nov 7 [original human proposal](../archive/drive/EXPERIMENT_FACTORY_HUMAN_GUIDE_ORIGINAL_2026-11-07.md) with the current [technical architecture](EXPERIMENT_FACTORY_v7.md) and actual repository state. **Do not confuse a future design with an implemented/verified service.**

## The goal: stop improvising experiments

Each trial needs a reproducible answer to: **what was tested, on what legal data, with which features/model/settings, and how reliable is the improvement?** Without an immutable record, testing 100 ideas mainly creates selection bias and lost history. The purpose is not simply to run more trials; it is to eliminate fake improvements and make genuine advances repeatable.

For every House Edge query, produce five probabilities in payout order 0×/1×/2×/5×/20×. Each machine belongs to an eight-machine episode. The useful historical inputs are actual observed prior payouts, including same-episode peers, strictly at ticks **earlier** than the forecast. The next-spin true five-probability target is visible on public validation only, not main test.

## The four parts of the system

1. **Reliable data:** the original challenge CSVs are immutable; local loaders and optionally Databricks Bronze/Silver/Gold tables validate data, preserve episode boundaries and record source hashes. A missing tick is unknown, not a 0× payout.
2. **Feature definitions:** one named, deterministic transform generates exact-lag/rolling/recency/peer/drift features with a declared as-of cutoff. Reusing a feature cache is safe only when source, feature version and split manifest match.
3. **Experiment engine:** a controlled trial combines legal feature groups, model family and conditional hyperparameters, training mode, fold manifest, seed and compute budget. Its recorded result includes failures and negative outcomes; MLflow is a view, not the authoritative transactional queue.
4. **Evaluation/release:** the scorer validates all five probabilities and uses episode-safe comparisons. Official true-vector points on public validation are different from historical sampled-payout Brier. Release requires a separate offline cold reproduction and human organizer receipt.

**Already available in the repo:** working Python research modules and trial registry, champion model, challenger experiments and negative-result evidence, a read-only dashboard, Databricks source/mock mode, and Actions tests. **Not yet demonstrated:** a universal model grammar across every family, large multi-host scheduling, actual Databricks workspace results, official organizer acceptance.

## What models and features to try

Begin with the existing 73-expert lag-context predictor and simple smoothed frequencies. Compare Bayesian/Dirichlet/Markov families and legitimate historical as-of supervised training. The original design also proposed regime switching and HMMs, state-space/change-point filters, cross-machine latent factors, dropout-robust histories, boosted trees, categorical ARIMA-style diagnostics, neural sequences, calibration, and constrained ensembles. These are candidate hypotheses, **not claims of completed winning implementations**.

Useful experiments isolate one mechanism: do sibling histories help shared-change episodes? Does a short window help drift but damage stable? Is the rare 20× probability miscalibrated? Does the stacker help because of legitimate features or historically unavailable query signal? A good test states a null/control, fixed episode folds, compute budget and decision threshold before running.

## 'Every combination' is not a useful default

Twenty yes/no feature switches yield **1,048,576** combinations before hyperparameter permutations. Instead: enumerate only finite grammar with count and budget, run one-group ablations, cover high-value pairwise interactions, compare model families under identical episode folds, then tune only survivors. Keep a frozen baseline and all failed/negative trials. Do not keep querying the same public validation targets until an apparent win appears.

## Databricks: what is real and what remains

The team already has a **14-day competition trial**. The source code defines a PySpark/Delta/MLflow workflow and currently passes 49 *offline* Databricks tests. This is meaningful engineering, but **not** an actual cloud run. Issue [#14](https://github.com/AsvM45/jaegers/issues/14) owns the authenticated small-sample pilot and proof: Delta table readback, row counts, Spark-to-local feature parity, real MLflow run IDs and consumed resources. There is no reason to fork the repo inside the workspace or run full sweeps before that proof.

## What you should trust

A claim saying '55.12/60' refers to **public development validation**, already exposed during model selection. It is not a hidden-test score. A valid CSV is not an organizer submission. A green Hitachi workflow that skipped tower tests is not a Hitachi test pass. A staged Wiki file is not a live GitHub Wiki page. Always follow [current state](../CURRENT_STATE.md), [science and provenance](../science/EVALUATION_AND_PROVENANCE.md), [issue #18](https://github.com/AsvM45/jaegers/issues/18), and actual commit/CI evidence.

## Minimum repeatable workflow

1. State one hypothesis and one falsification control.
2. Freeze source SHA, episode folds, feature signature, metric source and resource budget.
3. Run a small consistent test, preserving the baseline and previous results.
4. Compare paired per-episode differences and condition-specific losses; keep failures/negative evidence.
5. Require an as-of audit and independent reproduction before contemplating promotion.
6. If the improvement survives, package a *separate* offline candidate without overwriting the frozen competition pair.

For implementation details, command interfaces and resource schemas, use the [current technical specification](EXPERIMENT_FACTORY_v7.md) and actual `research/CONTRACTS.md`. The full original Drive texts are accessible as [historical provenance](../archive/drive/README.md) but should **never** supersede current code or organizer rules.
