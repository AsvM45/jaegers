# Control tower — test summary

Written 2026-11-08 03:30 from the saved results by `tower/ui/reports.py`. Each test's expected output is its answer key traced through the company graph (`tests/run_cases.py`, independent of `tower/graph.py`); the grader also replays every action in the enterprise simulator and checks it against the handbook.

## The tower, per suite and reader

| Suite | Reader | Incident type | Records and dates | Full output | Grader | Report |
|---|---|---|---|---|---|---|
| Given tests | qwen3:0.6b | 15/15 | 15/15 | 15/15 | 15/15 | [given/REPORT.md](given/REPORT.md) |
| Given tests | rules | 15/15 | 15/15 | 15/15 | 15/15 | [given/REPORT.md](given/REPORT.md) |
| Held-out tests (set 2) | qwen3:0.6b | 67/100 | 66/100 | 66/100 | 66/100 | [holdout2/REPORT.md](holdout2/REPORT.md) |
| Held-out tests (set 2) | rules | 50/100 | 50/100 | 50/100 | 50/100 | [holdout2/REPORT.md](holdout2/REPORT.md) |
| Held-out tests (set 1) | qwen3:0.6b | 84/100 | 84/100 | 84/100 | 84/100 | [holdout/REPORT.md](holdout/REPORT.md) |
| Held-out tests (set 1) | rules | 76/100 | 76/100 | 76/100 | 76/100 | [holdout/REPORT.md](holdout/REPORT.md) |
| Generated tests | qwen3:0.6b | 100/100 | 100/100 | 100/100 | 100/100 | [tests/REPORT.md](tests/REPORT.md) |
| Generated tests | qwen3:1.7b | 16/25 | 15/25 | 15/25 | 15/25 | [tests/REPORT.md](tests/REPORT.md) |
| Generated tests | rules | 100/100 | 100/100 | 100/100 | 100/100 | [tests/REPORT.md](tests/REPORT.md) |

Suites: **Given tests**: The 15 events in events.json, graded against docx TC1–TC6; **Held-out tests (set 2)**: 100 fresh messages, written after the fixes; never tuned on (tests/make_holdout2.py); **Held-out tests (set 1)**: 100 messages; used to diagnose the reader, so no longer blind (tests/make_holdout.py); **Generated tests**: 100 messages: 25 hand-made edge cases + 75 from real records (tests/make_cases.py).

## qwen3:0.6b on its own (no rule check)

Run 2026-11-08 03:07 with `tests/run_model.py`: the model reads each message, code only looks up the records and dates it named (one retry with feedback when they do not check out), and the reading is traced through the graph and compared with the expected graph.

| Set | Incident type | Records and dates | Full output |
|---|---|---|---|
| holdout2 | 10/15 | 10/15 | 10/15 |

