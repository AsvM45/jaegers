# Design card — Wacky Wheels control tower (team JAEGERS)

**Model:** Qwen3 0.6B (`qwen3:0.6b`, 752M parameters, 4-bit, 522 MB), run locally through Ollama, is the tower's only model. There is no cloud. Everything else is Python standard library.

## Architecture

```
GET /events ─► Coordinator ─► 1 Understand   (Qwen3 0.6B + rule check)  → incidents
                   │          2 Hand each incident to the specialist agent that owns it:
                   │              Supply Chain Planner           mes.reschedule, mes.transfer       (rules 1–3)
                   │              Quality                        quality.hold_lot, dealer.stop_sale,
                   │                                             crm.notify_customer               (rule 6)
                   │              Dealer Network & Customer Care dealer.notify, crm.assign_loaner   (rules 4–5)
                   │            each traverses the knowledge graph (11 node types, 16 edge types)
                   │          3 Validate: drop any planned call outside that agent's tool list
                   └────────► 4 POST /act, in a fixed order ─► action_log.jsonl + per-event trace ─► UI
```

Each agent has a card in `tower/agents/roster.py`: its responsibility, the incidents it takes, the handbook rules it applies, and the only tools it may use. The coordinator is the only component that calls tools. Specialists return planned calls, each with a reason and the graph paths that justify it. Every coordinator-to-agent handoff is recorded in the trace and shown in the UI. A shared slot board and shared loaner pools let the incidents in one compound message use capacity consistently. The ontology export is in `runs/ontology/ontology.md`.

## LLM versus code

| LLM (Qwen3 0.6B) | Plain code |
|---|---|
| Labels each message section with one of the five kinds. Copies out the exact phrases for the plant, part, supplier, lot, shipment and the two dates | Checks each phrase is in the text. Resolves names through `aliases.csv` (plus typo matching). Turns phrases like "next Friday" into dates. Runs a rule reader as a check. Does every graph query, slot search, loaner decision and handbook rule |

The LLM proposes and code verifies. If the model's output fails a check, or it disagrees with the rule reader on the kind or on a field, the rule reading is used, and the trace says why. A 0.6B model therefore never decides an action on its own. That is deliberate: the action log is half the score.

## Guardrails

- **Tool allowlist per agent:** a planned call to a tool outside the agent's card is refused before anything runs, and the refusal is recorded in the trace.
- **Noise:** no tool calls at all.
- **Rumor or unclear report:** a single `escalate`. That includes an id that doesn't exist and a missing plant or date.
- **Rumor inside a real event:** also escalated.
- **Model alarm:** if Qwen reads a real incident, and every phrase it quotes checks out, but the word lists find nothing, the message is escalated rather than ignored. Wording we have never seen ("line halted", "behind schedule", "bad batch") reaches a human, and no records change on the model's word alone.
- **Only affected records change.** Affected orders come from the bill of materials, the receiving plant and the exact disruption window. Rule 1 treats the delay window as half-open; rule 2 treats an outage as inclusive.
- **Failed call:** logged, not retried, and the remaining calls still run. A confirmed incident that ends with no successful write is escalated. This is tested in `tests/test_failures.py`.
- **Batching:** list-taking tools are batched, with one notice and one stop-sale per dealer. No read calls are made and no calls are wasted.

## Evaluation

| Check | Result |
|---|---|
| 15 given events, docx TC1–TC6 (`tests/run_given.py`) | **15/15** on effects and on the required evidence |
| 100 generated cases: 25 hand-made edge cases + 75 from real records with nicknames, relative and m/d dates (`tests/run_cases.py`) | **100/100**, with the rule reader and with Qwen3 0.6B. The reader's word lists are general word families (delay/late/slip/postpone, down/halted/offline, defect/contamination/out-of-spec, heard/might/unconfirmed), not phrases from the given events; this set informed them, so it is not blind |
| Handbook audit of the submitted log (`tower/_audit_run.py`) | 0 problems |
| Official server run (`enterprise_server.py`, `POST /act`) | 768 calls, **0 failed**, identical to the in-process run |
| Model benchmark, 6 local models from 0.5B to 2.0B | All give identical actions. Qwen3 0.6B is the smallest with the best kind accuracy (14/16), at about 3 s per call and 16 calls per run |

The graders compute the expected effects straight from the CSVs, not from our graph code. The expected answers for the given events are our own hand reading of the handbook, because the organizers' answers are hidden.

## What we would improve

1. **Unseen test messages.** We fixed the reader using the generated cases, so we need a fresh, blind set to measure how it does on new wording.
2. **A bigger role for the LLM.** Fine-tune or prompt a small model well enough to split compound messages and pick dates itself, so the rules become only a safety net.
3. **Better slot choices.** Placement is greedy, earliest-first. An optimizer could reduce transfers when several disruptions compete for the same days.
4. **Retries.** Retry transient tool failures with backoff, and keep escalation for permanent ones.
