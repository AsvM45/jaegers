# HE-09 follow-up: candidates rerun through the #8 trial registry

Issue: AsvM45/jaegers#9 (agent `claude-stats`). Closes the remaining acceptance item from PR #28: compare the
candidates "using the #8 registry when ready". **Verdict unchanged: no promotion.**

## What ran

- Study config: `research/configs/stats/he09/registry_study.json` (grid, 5 candidates, seed 0, 4 folds).
- Bridge: `research/challengers/stat_he09_registry.py` exposes the unchanged `stat_he09_models.py` through the
  registry factory contract (`factory: research.challengers.stat_he09_registry:factory`, `supervision: "query"`).
- Command (from `Jaeger_Main/House_Edge`):
  `python -m research.sweep --study research/configs/stats/he09/registry_study.json --out research_runs/he09_registry`
- Run: main `5f3311e` + this branch, Windows 11, CPython 3.13.5, packages from `requirements-research.txt`;
  5/5 trials SUCCEEDED, 107 s wall. Registry artifacts (SQLite, per-attempt source snapshot, OOF CSV,
  result.json) stay in the ignored `research_runs/he09_registry/`; the summary is
  `research/reports/stat_he09_registry_results.json`.
- **Metric:** five-class observed-outcome Brier on held-out train queries, 4 condition-stratified whole-episode
  folds (the registry's protocol). Lower is better. **These are not official points** and use no validation
  targets. Paired intervals come from lane A's `research.metrics.paired` (4000 episode resamples, seed 0).

## Results

| model | trial id | mean Brier | stable | short_history | drift | shared_change | wall s |
|---|---|---|---|---|---|---|---|
| champion (`jaeger`) | `896a115b5a3e018f` | **0.3623** | .367 | .445 | .320 | .317 | 76.2 |
| stat_markov | `049612440418129b` | 0.4177 | .384 | .515 | .401 | .371 | 21.4 |
| stat_dirichlet | `3ef11bb25b214e2d` | 0.5627 | .545 | .625 | .530 | .551 | 3.5 |
| stat_decay_bma | `6306c918cf287ca8` | 0.5644 | .549 | .619 | .539 | .550 | 3.2 |
| FrequencyModel | `acf704e718bcd9a9` | 0.5705 | .554 | .622 | .552 | .554 | 1.6 |

Paired differences (candidate minus baseline; negative = candidate better):

| comparison | delta Brier | 95% CI | supported improvement |
|---|---|---|---|
| stat_markov vs champion | +0.0554 | [+0.0424, +0.0681] | no (worse) |
| stat_dirichlet vs champion | +0.2005 | [+0.1802, +0.2210] | no (worse) |
| stat_decay_bma vs champion | +0.2021 | [+0.1818, +0.2221] | no (worse) |
| stat_markov vs FrequencyModel | -0.1528 | [-0.1739, -0.1322] | yes |
| stat_dirichlet vs FrequencyModel | -0.0078 | [-0.0156, +0.0002] | borderline (interval touches 0) |
| stat_decay_bma vs FrequencyModel | -0.0062 | [-0.0126, +0.0003] | borderline (interval touches 0) |

## Agreement with PR #28

Same ordering on every model (champion < Markov < Dirichlet ~ BMA < FrequencyModel). Brier levels are close to
PR #28's "B" direction (fit on validation, score train): champion 0.3651 vs 0.3623 here, Markov 0.4181 vs 0.4177.
One difference worth stating: PR #28 found Dirichlet and BMA beat FrequencyModel with intervals excluding 0
(-0.0071 and -0.0064); under the registry's grouped folds the effect is the same size but the intervals just touch
0. Treat that gain as small and borderline. The champion trial carries `validation_target_exposure: true`
(its constants came from validation); the HE-09 candidates carry `false` and `historical_signal_policy: omitted`.

## Status

All #9 acceptance items now have evidence: three tested candidates (PR #28), paired evaluation (PR #28) and a
registry rerun with trial IDs (this PR). No candidate is promoted; champion and shared registry code unchanged.
