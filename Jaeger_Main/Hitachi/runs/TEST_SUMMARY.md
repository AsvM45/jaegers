# Control tower — test summary

Written 2026-11-08 10:16 from the saved results by `tower/ui/reports.py`. Each test's expected output is its answer key traced through the company graph (`tests/run_cases.py`, independent of `tower/graph.py`); the grader also replays every action in the enterprise simulator and checks it against the handbook.

## The tower, per suite and reader

| Suite | Reader | Incident type | Records and dates | Full output | Grader | Report |
|---|---|---|---|---|---|---|
| Given tests | qwen2.5:0.5b | 15/15 | 15/15 | 15/15 | 15/15 | [given/REPORT.md](given/REPORT.md) |
| Given tests | rules | 15/15 | 15/15 | 15/15 | 15/15 | [given/REPORT.md](given/REPORT.md) |
| Given tests | qwen3:0.6b | 15/15 | 15/15 | 15/15 | 15/15 | [given/REPORT.md](given/REPORT.md) |
| Held-out tests (set 2) | rules | 190/190 | 190/190 | 190/190 | 190/190 | [holdout2/REPORT.md](holdout2/REPORT.md) |
| Held-out tests (set 2) | qwen3:0.6b | 71/100 | 70/100 | 70/100 | 70/100 | [holdout2/REPORT.md](holdout2/REPORT.md) |
| Held-out tests (set 1) | rules | 146/146 | 146/146 | 146/146 | 146/146 | [holdout/REPORT.md](holdout/REPORT.md) |
| Held-out tests (set 1) | qwen3:0.6b | 86/100 | 86/100 | 86/100 | 86/100 | [holdout/REPORT.md](holdout/REPORT.md) |
| Generated tests | rules | 100/100 | 100/100 | 100/100 | 100/100 | [tests/REPORT.md](tests/REPORT.md) |
| Generated tests | qwen3:0.6b | 100/100 | 100/100 | 100/100 | 100/100 | [tests/REPORT.md](tests/REPORT.md) |
| Generated tests | qwen3:1.7b | 16/25 | 15/25 | 15/25 | 15/25 | [tests/REPORT.md](tests/REPORT.md) |
| Stress tests | rules | 149/149 | 149/149 | 149/149 | 149/149 | [stress/REPORT.md](stress/REPORT.md) |
| Accuracy paraphrases | rules | 23/23 | 23/23 | 23/23 | 23/23 | [accuracy/REPORT.md](accuracy/REPORT.md) |

Suites: **Given tests**: The 15 events in events.json, graded against docx TC1–TC6; **Held-out tests (set 2)**: 190 messages: the original 100 plus two regressions for each miss (tests/make_holdout2.py, tests/make_regression.py); **Held-out tests (set 1)**: 146 messages: the original 100 plus two regressions for each miss (tests/make_holdout.py, tests/make_regression.py); **Generated tests**: 100 messages: 25 hand-made edge cases + 75 from real records (tests/make_cases.py); **Stress tests**: 149 messages: 74 normal, 45 edge cases, 30 overload (tests/make_stress.py); **Accuracy paraphrases**: 23 messages: ordinary wording the reader used to miss, plus noise guards (tests/accuracy_cases.json).

## qwen2.5:0.5b on its own (no rule check)

Run 2026-11-08 09:05 with `tests/run_model.py`: the model reads each message, code only looks up the records and dates it named (one retry with feedback when they do not check out), and the reading is traced through the graph and compared with the expected graph.

| Set | Incident type | Records and dates | Full output |
|---|---|---|---|
| given | 4/15 | 4/15 | 4/15 |

## qwen3:0.6b on its own (no rule check)

Run 2026-11-08 09:09 with `tests/run_model.py`: the model reads each message, code only looks up the records and dates it named (one retry with feedback when they do not check out), and the reading is traced through the graph and compared with the expected graph.

| Set | Incident type | Records and dates | Full output |
|---|---|---|---|
| given | 3/15 | 3/15 | 3/15 |

## qwen3:1.7b on its own (no rule check)

Run 2026-11-08 05:49 with `tests/run_model.py`: the model reads each message, code only looks up the records and dates it named (one retry with feedback when they do not check out), and the reading is traced through the graph and compared with the expected graph.

| Set | Incident type | Records and dates | Full output |
|---|---|---|---|
| holdout2 | 34/40 | 34/40 | 34/40 |

