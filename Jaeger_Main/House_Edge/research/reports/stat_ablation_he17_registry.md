# HE-17 follow-up: ablations rerun through the #8 trial registry

Issue: AsvM45/jaegers#17 (agent `claude-stats`). Closes the remaining acceptance item "#8 registry integration
pending" and adds the third, independent estimate the HE-17 report asked for. **Verdict unchanged: no promotion.**

## What ran

- Study: `research/configs/stats/ablations/he17_registry_study.json`: champion, the 12 pre-registered ablations
  (`he17_ablations.json`, pre-registered in `b697dd8`) and lane A's `JaegerModel(causal=True)`; 14 trials.
- Parameter-only ablations use the registry's own `family: jaeger` path. Code-level ones (`nosig`, `single_lag_only`,
  `binary_categories_only`, `train_size_regimes`, shuffled-label control) use the self-contained factory
  `research/challengers/stat_ablation_he17_registry.py`; tests assert each inline `change` equals the pre-registration.
- Command (from `Jaeger_Main/House_Edge`):
  `python -m research.sweep --study research/configs/stats/ablations/he17_registry_study.json --out research_runs/he17_registry_v2`
- Run: main `fc7054e` + this branch, Windows 11, CPython 3.13.5, `requirements-research.txt`; **14/14 SUCCEEDED**, 517 s.
  Artifacts stay in the ignored `research_runs/`; summary in `stat_ablation_he17_registry_results.json`.
- A first run (`research_runs/he17_registry`) had the 5 factory trials FAIL: the factory imported
  `research.analysis`, which the registry's frozen worker snapshot does not contain. Fixed by making the factory
  self-contained; a regression test now imports it inside a snapshot-shaped copy.
- **Metric:** observed-outcome five-class Brier, 4 condition-stratified whole-episode train folds (lower is better).
  **Not official points**, and no validation targets are used for scoring. Intervals: `research.metrics.paired`,
  4000 episode resamples, seed 0. All variants are champion-derived (params tuned on validation), so
  `validation_target_exposure` is true for all of them even where the worker's family-based flag says otherwise;
  correct per-variant flags are in the JSON (`flags`).

## Results (delta = variant minus champion; positive = worse)

| variant | trial id | Brier | delta [95% CI] | stable | short_history | drift | shared_change |
|---|---|---|---|---|---|---|---|
| **champion** | `3c6dcebb2c1a2e09` | **0.3623** | - | .367 | .445 | .320 | .317 |
| nostack | `caf59648bbfe2b69` | 0.3728 | +0.0105 [+0.0060, +0.0151] | .374 | .459 | .331 | .327 |
| no_size_experts | `b3c162126c2d1d13` | 0.3710 | +0.0087 [+0.0029, +0.0146] | .375 | .444 | .333 | .332 |
| single_lag_only | `48d85d75fd1d9851` | 0.5346 | +0.1723 [+0.1518, +0.1928] | .505 | .602 | .524 | .508 |
| slower_forgetting (lam .99) | `90a0117ffdcae854` | 0.4772 | +0.1150 [+0.0991, +0.1305] | .375 | .453 | .533 | .548 |
| faster_forgetting (lam .90) | `b06907ceec8c24bb` | 0.3683 | +0.0060 [+0.0022, +0.0104] | .372 | .444 | .327 | .330 |
| train_size_regimes | `d33061bf74682bb8` | 0.3659 | +0.0036 [+0.0001, +0.0072] | .371 | .447 | .323 | .323 |
| causal (lane A) | `c106dbf55647f857` | 0.3643 | +0.0020 [-0.0000, +0.0042] | .370 | .451 | .321 | .316 |
| binary_categories_only | `50612a61fe9c6750` | 0.3633 | +0.0010 [-0.0033, +0.0051] | .368 | .447 | .319 | .319 |
| nosig | `9ecac067418b166f` | 0.3632 | +0.0009 [-0.0007, +0.0025] | .369 | .447 | .321 | .316 |
| no_expert_prior | `98cd752fb6949526` | 0.3629 | +0.0006 [-0.0018, +0.0031] | .367 | .450 | .320 | .316 |
| no_short_history_prior | `54c708ec6f3ab901` | 0.3625 | +0.0002 [-0.0014, +0.0019] | .366 | .450 | .319 | .314 |
| no_peer_evidence | `cfbe0fd59bc5c270` | 0.3616 | -0.0007 [-0.0039, +0.0023] | .366 | .448 | .317 | .315 |
| **control: shuffled stacker labels** | `b552834c32128779` | 0.5989 | +0.2366 [+0.2157, +0.2589] | .593 | .634 | .595 | .574 |

## Three estimates side by side

A = train -> validation official points (development-exposed); B = validation -> train Brier (HE-17, PR #22);
R = this registry run (4 grouped folds on train).

| variant | A points diff | B Brier diff | R Brier diff | reading |
|---|---|---|---|---|
| nostack | -2.29 | +0.0076 | +0.0105 | real, all three agree |
| no_size_experts | -1.44 | +0.0086 | +0.0087 | real, all three agree |
| single_lag_only | -23.0 | +0.170 | +0.172 | real, all three agree |
| slower_forgetting | -15.8 | +0.114 | +0.115 | real, all three agree |
| faster_forgetting | -1.65 | +0.0067 | +0.0060 | real, all three agree |
| train_size_regimes | -0.63 | +0.0035 | +0.0036 | small but consistent |
| binary_categories_only | -1.10 | +0.0017 | +0.0010 (ns) | **only A shows it** |
| no_peer_evidence | -0.66 | -0.0016 | -0.0007 (ns) | **only A shows it** |
| no_short_history_prior | -0.48 | +0.0007 | +0.0002 (ns) | **only A shows it** |
| no_expert_prior | -0.43 | +0.0002 | +0.0006 (ns) | **only A shows it** |
| nosig | -0.12 | -0.0004 | +0.0009 (ns) | not measurable outside A |
| control (shuffled) | 27.8 pts | +0.246 | +0.237 | harness sensitive |

## Reading

1. The structural components (lag-pair experts, forgetting rate, stacker, size experts) are confirmed by all three
   estimates.
2. **Peer evidence, the expert prior, short-history smoothing and 3-way categories help only on the public validation
   split their settings were tuned on.** With roughly twice the queries per condition and no tuning exposure, the
   registry run finds no effect for any of them. Treat their 0.4-1.1 point validation gains as likely selection
   effects, not as reasons to keep added complexity. Removing them is not recommended either: none of them hurts.
3. Lane A's `causal` variant is borderline worse (+0.0020, interval touching 0), consistent with HE-03.

## Status

All HE-17 acceptance items now have evidence: pre-registered ablations with paired episode intervals (PR #22, on
main via #40) and registered trial IDs with a third estimate (this PR). No promotion; champion unchanged.
