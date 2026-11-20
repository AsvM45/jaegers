# Control tower — test summary

Written 2026-11-16 14:47 from the saved results by `tower/ui/reports.py`. Each test's expected output is its answer key traced through the company graph (`tests/run_cases.py`, independent of `tower/graph.py`); the grader also replays every action in the enterprise simulator and checks it against the handbook.

## The tower, per suite and reader

| Suite | Reader | Incident type | Records and dates | Full output | Grader | Report |
|---|---|---|---|---|---|---|
| Given tests | AI model | 15/15 | 15/15 | 15/15 | 15/15 | [given/REPORT.md](given/REPORT.md) |
| Given tests | Rule reader | 15/15 | 15/15 | 15/15 | 15/15 | [given/REPORT.md](given/REPORT.md) |
| Blind tests | AI model | 36/40 | 36/40 | 36/40 | 36/40 | [blind/REPORT.md](blind/REPORT.md) |
| Blind tests | Rule reader | 30/40 | 29/40 | 29/40 | 29/40 | [blind/REPORT.md](blind/REPORT.md) |
| Blind tests (100) | AI model | 99/100 | 92/100 | 92/100 | 92/100 | [blind100/REPORT.md](blind100/REPORT.md) |
| Blind tests (100) | Rule reader | 79/100 | 72/100 | 72/100 | 72/100 | [blind100/REPORT.md](blind100/REPORT.md) |

Suites: **Given tests**: The 15 given events, graded against the docx test cases TC1–TC6; **Blind tests**: 40 unseen messages, each built from a real scenario in the company records; **Blind tests (100)**: 100 unseen messages, each built from a real scenario in the company records. Never tuned on.

