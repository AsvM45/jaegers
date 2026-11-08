# HE-02 QA contracts: run note and findings

Issue: AsvM45/jaegers#2 (lane C). Test module: `tests/test_agent_qa_contracts.py` (new file only;
champion, organizer scorer, shared `research/*.py` and `tests/test_temporal.py` untouched).

## How to run

From `Jaeger_Main/House_Edge`, in an environment built from `requirements-research.txt`:

```
python -m pytest tests/test_agent_qa_contracts.py -q
```

Observed 2026-11-07 on Windows 11, CPython 3.13.5, pytest 9.2.0, numpy 2.5.4, scikit-learn 1.9.1
(fresh venv from `requirements-research.txt`): **32 passed in ~6 s**; whole `tests/` folder
(with `test_temporal.py`): **37 passed**. Not run on Linux or in CI (#16).

## What is covered

| Area | Tests |
|---|---|
| Official scorer parity | `score_round` = 30 on reference, 60 on truth, and equals an independent re-derivation (1e-9) for 3 submissions; negative control: a condition-pooled formula differs |
| Test split is format-only | `public/test` holds only queries/history/sample; `check_submission --split test` prints no loss |
| Submission contract | exact IDs accepted; missing/duplicate/extra ID, NaN, negative, sum != 1 rejected by `read_submission` |
| Champion causality | payouts at/after cutoff on target or siblings change nothing; earlier sibling payouts do (positive control) |
| Boundaries | shared machine IDs across episodes stay isolated; missing `c-2` differs from 0x; CSV row order irrelevant; simplex/ID completeness |
| Feature registry (`research/features.py`, read-only) | same cutoff/episode/order contracts; missing lag-2 flagged unknown; `current_signal` blocked for historical rows |
| Grouped folds (`research/dataset.py`) | episodes in exactly one fold, condition-balanced, order-independent; condition-crossing episode rejected |
| End to end | champion CLI (stacker on) runs on a train/test subset containing only queries+history, i.e. no labels, conditions or targets are read |
| Negative controls | five deliberately leaky predictors (future, sibling future, machine-ID pooling, missing-as-zero, row-order) make the checkers fail |

Shared-module tests `pytest.skip` (not fail) if lane A renames `research/features.py` /
`research/dataset.py`; re-point the two imports after that integration.

## Findings

1. **Equal-cutoff fixtures cannot detect a future-tick leak in the champion.** `predict()` sizes its
   tick array to the largest cutoff (`jaeger_model.py:84-86`), so with one shared cutoff a filter bug
   like `t <= cut + 5` is masked. Mutation check: with equal cutoffs that mutant passed every cutoff
   test; with per-episode cutoffs (as in the real kit, 192-256) it is caught. The existing
   `tests/test_temporal.py::fixture` uses one cutoff for all episodes; suggest lane A varies it.
2. Mutation check for identity leakage (episode pooling keyed by `machine_id`) is caught by
   `assert_episode_isolated`.
3. FYI for #4: `requirements-runtime.txt` pins numpy 2.5.4 / threadpoolctl 3.8.0, while the staged
   entry `requirements.txt` used for the regenerated main CSV pins 2.5.3 / 3.7.0. The champion's
   output was byte-identical under both locally, but the ZIP and docs should name one set.
