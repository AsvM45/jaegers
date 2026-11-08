# Control tower — test summary

Reader model: **Qwen3 0.6B** (`qwen3:0.6b`, 752M parameters, local via Ollama), with the
deterministic rule reader as the check and fallback. Today in the data is Monday 2027-03-08.

| Suite | What it is | Rules reader | Qwen3 0.6B | Report |
|---|---|---|---|---|
| Given tests | The 15 events in `data/events.json`, mapped to docx TC1–TC6 | 15/15 | 15/15 | [runs/given/REPORT.md](given/REPORT.md) |
| Generated tests | 25 extra messages in `tests/cases.json`, 7 of them edge cases | 25/25 | 25/25 | [runs/tests/REPORT.md](tests/REPORT.md) |

Both suites grade the action log with `tests/run_cases.py`, which computes the expected effects from the
CSVs and the handbook. It does not use `tower/graph.py`. The tower never reads the expected answers.

## Given tests (docx TC1–TC6)

All six test cases pass on effects and on the evidence the docx requires: the graph path shape per
incident, a reason for every noise and unconfirmed event, at least three kinds of action per real
incident, and no failed calls. 768 tool calls, 0 failed.

## Generated tests by category

| Category | Cases | Rules | Qwen3 0.6B |
|---|---|---|---|
| supplier_delay | 5 | 5/5 | 5/5 |
| unconfirmed | 4 | 4/4 | 4/4 |
| plant_outage | 5 | 5/5 | 5/5 |
| quality_hold | 3 | 3/3 | 3/3 |
| noise | 4 | 4/4 | 4/4 |
| compound | 4 | 4/4 | 4/4 |

Edge cases covered:

- T-04: New ETA falls on a Saturday. Expected: builds resume the next working day (Mon Mar 29).
- T-06: Names a shipment id that does not exist and no part. Expected: escalate, nothing written.
- T-08: 'this Wednesday' relative to Monday Mar 8 = 2027-03-10.
- T-13: Build window spans two lots (LOT-0089 and LOT-0090). Expected: both lots held, vehicles from both windows.
- T-23: Real outage plus a rumor. Expected: outage actions, and the rumor part escalated.
- T-25: Typo in plant name ('Lexingtn'). Expected: still read as P_KY, or escalate rather than guess.

## How to re-run

```sh
python tests/run_given.py      # 15 given events  -> runs/given/REPORT.md
python tests/run_cases.py      # 25 generated     -> runs/tests/REPORT.md
python -m tower._audit_run     # handbook audit of runs/run1
```

## Limits

- The expected answers for the given events were written by hand from the message text and the CSVs.
  The organizers' answers are hidden, so these are our reading of the handbook.
- The reader was fixed using the generated cases, so 25/25 is not an unseen-data score. A fresh set of
  messages written without looking at the code would measure that.
