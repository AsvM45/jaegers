# Control tower — test summary

Written 2026-11-08 11:22 from the saved results by `tower/ui/reports.py`. Each test's expected output is its answer key traced through the company graph (`tests/run_cases.py`, independent of `tower/graph.py`); the grader also replays every action in the enterprise simulator and checks it against the handbook.

## The tower, per suite and reader

| Suite | Reader | Incident type | Records and dates | Full output | Grader | Report |
|---|---|---|---|---|---|---|
| Given tests | rules | 15/15 | 15/15 | 15/15 | 15/15 | [given/REPORT.md](given/REPORT.md) |
| Given tests | qwen2.5:0.5b | 15/15 | 15/15 | 15/15 | 15/15 | [given/REPORT.md](given/REPORT.md) |
| Given tests | qwen3:0.6b | 15/15 | 15/15 | 15/15 | 15/15 | [given/REPORT.md](given/REPORT.md) |

Suites: **Given tests**: The 15 events in events.json, graded against docx TC1–TC6.

