# Scientific evaluation, as-of information, and provenance

**Verified against:** organizer kit excerpts and [House Edge integration contracts](../../Jaeger_Main/House_Edge/research/CONTRACTS.md), [historical feature witness](../release/GROK_HISTORICAL_FEATURE_COMPLIANCE.md), and repository status through Nov 8, 2026. This is research methodology, not an organizer ruling.

## Prediction contract

A query refers to an `episode_id`, `machine_id`, `machine_type`, `signal` and `cutoff`. Its required forecast is

```text
query_id,p_0,p_1,p_2,p_5,p_20
```

with five nonnegative finite probabilities summing to one. The five underlying payouts are 0, 1, 2, 5 and 20 times stake; **classification accuracy is not the final objective**. The underlying simulator's true five probabilities are available for public validation but **not** for main test or round-two test.

## Episode and as-of boundaries

- Eight machines share an episode; earlier payouts from sibling machines may inform a prediction.
- Each episode is a separate simulation; do not infer persistent identity from reused machine suffixes or impose a universal chronological order across episodes.
- For target tick `t`, use outcomes at **exact tick strictly before `t`** for both target and sibling machine features.
- Missing observations are unknown, not 0×. Lag 2 means the event at tick `t-2` if observed, not "second-most-recent row."
- `signal` supplied for the **current query cutoff** is not a known historical `signal(t)` for every earlier tick.
- If a historical observed tick `t` is used to create a supervised pseudo-example, its observed outcome at `t` may be the label; it must not enter its own features. The true simulator probability vector at `t` is not supplied.
- A learned model fit on permitted training episodes, a historical pseudo-training row, and a live query-time feature vector have **different information sets**; do not conflate them.

## Scoring and statistical comparisons

For five-vectors `p` and `p_hat` at an organizer validation query, squared probability loss is

```text
L = sum_k (p_hat[k] - p[k])**2
```

The 60/40 released ZIP version reports a round score from condition-normalized error:

```text
E_episode = mean(loss for 8 machines in an episode)
E_condition = mean(E_episode among episodes in that condition)
R = (1/4) * sum_conditions(E_condition / max(B_condition, 1e-9))
round_points = round_max_points / (1+R)
```

where `B_condition` comes from the organizer's fixed reference forecast, and the four conditions are stable, short_history, drift, shared_change. A separately supplied participant guide describes 80/20 rather than 60/40; preserve that **source conflict** and use the actual scored kit/organizer ruling for the round. Values around 55.12/60 in reports are **local public-development validation**; do not call them percent accuracy or hidden competition points.

For historical tick outcomes without true target probability vectors, compare candidate predictions using observed-label one-hot Brier/squared loss, accurately labeling the distinct target. The expected observed-label Brier is minimized by the true probabilities, but its noisy finite-sample value is **not** the same statistic as organizer true-vector error.

## Experimental design and winner's curse

Use whole-episode outer folds to prevent shared latent information appearing on both sides. Walk-forward/rolling-origin evaluation *within* a training episode is useful for temporal mechanisms, but is not equivalent to independence across episodes. Use hierarchical/episode-level bootstrap for uncertainty, preserve sample size and cluster structure, and report per-condition errors and performance drift. Thousands of rolling rows from 96 episodes are not thousands of independent episodes.

Record every trial: immutable source/data hash, Git SHA, seed, feature groups, hyperparameters, exact split/fold, evaluator type, elapsed time/resource cap, prediction artifacts and failures. Keep negative trials. Search methods (grid/Optuna) optimize development data and increase selection bias; reserve a held-out audit partition if possible and never turn repeated inspection of that partition into a new independent test.

**Parameters** are fit by the learner on training data (for example, coefficients/boosting-tree splits). **Hyperparameters** govern that fitting (for example, regularization, window, maximum depth). Compare full pipeline changes, not just model family names.

## Model families and learned signals

The repo includes an expert-mixture/stacker champion and additive research on Markov/HMM, factorized size, Bayesian priors, causal historical features, structural cross-machine evidence and ablations. A research PR can be correct and scientifically useful **even when it loses to the champion**. Do not promote an experimental model solely on development-exposed public validation; test out-of-fold behavior, causal admissibility, runtime and cold reproduction. The latest detailed negative/positive studies are linked from [research docs](../../Jaeger_Main/House_Edge/RESEARCH.md) and [current state](../CURRENT_STATE.md).

## Historical compliance remains unresolved

The merged [independent Grok witness](../release/GROK_HISTORICAL_FEATURE_COMPLIANCE.md) reports `NOT_CERTIFIED` and demonstrates feature dependence on post-historical-t observations in the prior and final coverage, plus copied query-time signal. That is evidence about historical training-row provenance, **not** proof that the test answers leaked or that an organizer disqualified the model. The staff interpretation must be captured as a source if obtained.

## Report outcomes honestly

Use one of: `TESTED`, `AUTHOR-REPORTED`, `DEVELOPMENT-EXPOSED`, `NOT_CERTIFIED`, `BLOCKED`, or `SUBMITTED + receipt`. A local valid CSV/ZIP and a green Actions check are not an organizer receipt. No hidden-test truth or private organizer points should appear in public documentation.


## Experiment-factory acceptance protocol (Drive v7 reconciled)

The original v7 research plan proposed three distinct evaluations: (1) **historical rolling-origin sampled-payout** training/test diagnostics, (2) **episode-grouped out-of-fold sampled-label Brier** for transferable mechanisms, and (3) **official public-validation true-vector condition-normalized** scores for final development comparison. These cannot be interchanged. A pseudorow's historical observed payout can be its label, but every feature and any fitted prior used at time t must have the proper information availability; current-query signal is not a known past signal. See the [historical-feature witness](../release/GROK_HISTORICAL_FEATURE_COMPLIANCE.md).

For each trial, record code/data/fold hashes, model+feature signature, actual labels/source, search-selection exposure, seed, package/environment, per-episode losses, timing, artifacts and failure state. Freeze the split manifest before search and preserve negative trials. A paired bootstrap samples **episodes**, not individual spins or correlated pseudorows. Confidence intervals are descriptive when many model variants have been tried on the same exposed validation episodes.

**Falsification controls from the archived design:** permute current query signal, remove sibling-machine context, perturb deliberately future outcomes (predictions must not move), compare true-tick lags vs observed-row positions in sparse histories, test calibration for payout 20×, run no-stacker and train-only-prior alternatives, and measure interaction effect under matched folds. Treat any result as a hypothesis until repeated under the same relevant evaluation.

A "universal experiment factory" is not a license to declare hidden-test gains. Large unbounded Cartesian-product searches are unscientific after repeated validation exposure; enumerate only a bounded grammar, estimate compute before launching, and report invalid/unsupported combinations. 
