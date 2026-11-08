# Runtime-aware diverse-model screen ? measured results

The existing JAEGERS reference remains the best observed model in this bounded train-only screen. No challenger was promoted and the frozen submission pair was not regenerated.

## Evaluation and reproducibility

- Preregistered source/config commit: `f566c8fa699382ce4ed826b8921e4f7304e8ba64`; issue #51 / PR #53.
- 35 completed configurations across 13 family tags, including repeated/reference controls. Three preflight configurations were reused, not counted again.
- 96 main TRAIN episodes / 768 held-out queries / four episode-grouped folds. Scores are observed-label Brier (lower is better), averaged per episode and condition. They are not official competition points or hidden-test estimates.
- Main screening step: 511.02 seconds; preflight: 32.63 seconds. Caps: two CPUs total, 120 seconds/trial, 30-minute study wall budget. No failures or timeouts occurred.
- Runtime: CPython 3.13, NumPy optional dispatch disabled, OpenBLAS Nehalem, Python hash seed 0. Each grid worker had one CPU/thread; the feature builder used the separately recorded coordinator context.
- Training-data digest: `00ae1fc45ea9d630997e5a51cf7e1e2f188991022187f7b53e7ebf7aa3c27e0f`.
- Split-manifest digest: `84f2aa3282c5dc8f394bdd06179f0adac2ec3865804dda99285d1b5c7e4ccc0e`.
- Runtime-context digest: `025998179df5d7bdc4782c731a4de1f1ff1efe8485c891eb7209170faaea03cf`.
- 230 combined tests passed. Both three-model preflight replay and full 35-trial replay preserved IDs, attempts and artifact bytes.

## Best configuration within each family

| Family | Mean Brier | Difference from JAEGERS reference |
|---|---:|---:|
| jaeger | 0.361702 | +0.000000 |
| stat_markov | 0.417735 | +0.056033 |
| extra_trees | 0.535957 | +0.174256 |
| lightgbm | 0.547460 | +0.185758 |
| hist_boost | 0.548303 | +0.186601 |
| random_forest | 0.549615 | +0.187914 |
| xgboost | 0.552499 | +0.190797 |
| stat_dirichlet | 0.562742 | +0.201040 |
| stat_decay_bma | 0.564383 | +0.202681 |
| frequency | 0.566285 | +0.204584 |
| logistic | 0.566783 | +0.205082 |
| lda | 0.568322 | +0.206621 |
| naive_bayes | 1.247378 | +0.885676 |

The original JAEGERS reference scored 0.361702. Its existing `causal=True` adapter scored 0.364293. The strongest non-JAEGERS alternative was the conditional Markov model at 0.417735; the strongest standard learner was ExtraTrees at 0.535957. The adapter name does not resolve every historical-training or validation-derived-constant audit concern.

## Feature hypotheses

The three bundles add one group at a time: recency; recency plus exact lags 1?8; then past-only sibling observations. Differences below are exploratory matched-fold observations; negative values improve Brier. They are not selection-adjusted significance claims.

| Learner | Add exact lags | Then add sibling observations |
|---|---:|---:|
| logistic | +0.004921 | -0.000317 |
| lda | +0.006944 | +0.000146 |
| naive_bayes | -0.010572 | -0.000578 |
| random_forest | -0.000723 | -0.000625 |
| extra_trees | -0.017293 | +0.002588 |
| hist_boost | -0.006057 | +0.001361 |
| xgboost | -0.000883 | +0.000064 |
| lightgbm | -0.003943 | -0.002241 |

Lag gains varied by learner; ExtraTrees improved most among the standard learners. Sibling gains were mixed. Gaussian Naive Bayes performed poorly despite producing valid probability outputs. These results do not support broad refinement of the weak standard learners against the stronger conditional references.

## Limitations and safe stop

This is repeated-CV exploratory selection. Public validation was not scored by this study, but JAEGERS constants and prior model design already have development-target exposure. Paired episode intervals in the local report are descriptive after selection, not proof of unseen generalization. Older records without the new runtime fields remain historical evidence; their numerical policy cannot be recovered from the new fields retroactively.

No cloud charges, organizer upload, hidden targets, model promotion or frozen release changes occurred. This stage does not claim 100 diverse experiments or complete adaptation/cloud work.

Full local evidence: `.chat-he08/Jaeger_Main/House_Edge/research_runs/chat-diverse-screen/` ? `reports/final/report.{json,md}`, `full-screen-resume-proof.json`, `stop-checkpoint.json` and `RESUME.md`. The checkpoint is STOP_READY. Every scheduled process finished. Resume only from the recorded source/runtime context; inspect the checkpoint before starting a coordinator.

See the preregistered [study configuration](../../studies/chat_diverse_screen.json) and [research commands](../../RESEARCH.md).
