# Design card — Wacky Wheels control tower (team JAEGERS)

**Model:** Qwen3 0.6B (`qwen3:0.6b`, 752M parameters, 4-bit, 522 MB), run locally through Ollama. There is no cloud and no other model. Everything else is Python standard library.

## Architecture

```
GET /events ─► Coordinator ─► 1 Understand   (Qwen3 0.6B + rule check)  → incidents
                   │          2 Knowledge graph (11 node types, 16 edge types) → who is affected
                   │          3 Specialists plan tool calls:
                   │              Supply Chain Planner   reschedule / transfer
                   │              Quality Containment    hold lot / stop sale / notify owners
                   │              Dealer & Customer Care notify dealers / assign loaners
                   └────────► 4 POST /act, in a fixed order ─► action_log.jsonl + per-event trace ─► UI
```

The coordinator is the only component that calls tools. Specialists return planned calls, each with a reason and the graph paths that justify it. A shared slot board and shared loaner pools let the incidents in one compound message use capacity consistently. The ontology export is in `runs/ontology/ontology.md`.

## LLM versus code

| LLM (Qwen3 0.6B) | Plain code |
|---|---|
| Labels each message section with one of the five kinds. Copies out the exact phrases for the plant, part, supplier, lot, shipment and the two dates | Checks each phrase is in the text. Resolves names through `aliases.csv` (plus typo matching). Turns phrases like "next Friday" into dates. Runs a rule reader as a check. Does every graph query, slot search, loaner decision and handbook rule |

The LLM proposes and code verifies. If the model's output fails a check, or it disagrees with the rule reader on the kind or on a field, the rule reading is used, and the trace says why. A 0.6B model therefore never decides an action on its own. That is deliberate: the action log is half the score.

## Guardrails

- **Noise:** no tool calls at all.
- **Rumor or unclear report:** a single `escalate`. That includes an id that doesn't exist and a missing plant or date.
- **Rumor inside a real event:** also escalated.
- **Only affected records change.** Affected orders come from the bill of materials, the receiving plant and the exact disruption window. Rule 1 treats the delay window as half-open; rule 2 treats an outage as inclusive.
- **Failed call:** logged, not retried, and the remaining calls still run. A confirmed incident that ends with no successful write is escalated. This is tested in `tests/test_failures.py`.
- **Batching:** list-taking tools are batched, with one notice and one stop-sale per dealer. No read calls are made and no calls are wasted.

## Evaluation

| Check | Result |
|---|---|
| 15 given events, docx TC1–TC6 (`tests/run_given.py`) | **15/15** on effects and on the required evidence |
| 25 generated cases, including edge cases (`tests/run_cases.py`) | **25/25**, with the rule reader and with Qwen3 0.6B |
| Handbook audit of the submitted log (`tower/_audit_run.py`) | 0 problems |
| Official server run (`enterprise_server.py`, `POST /act`) | 768 calls, **0 failed**, identical to the in-process run |
| Model benchmark, 6 local models from 0.5B to 2.0B | All give identical actions. Qwen3 0.6B is the smallest with the best kind accuracy (14/16), at about 3 s per call and 16 calls per run |

The graders compute the expected effects straight from the CSVs, not from our graph code. The expected answers for the given events are our own hand reading of the handbook, because the organizers' answers are hidden.

## What we would improve

1. **Unseen test messages.** We fixed the reader using the generated cases, so we need a fresh, blind set to measure how it does on new wording.
2. **A bigger role for the LLM.** Fine-tune or prompt a small model well enough to split compound messages and pick dates itself, so the rules become only a safety net.
3. **Better slot choices.** Placement is greedy, earliest-first. An optimizer could reduce transfers when several disruptions compete for the same days.
4. **Retries.** Retry transient tool failures with backoff, and keep escalation for permanent ones.
