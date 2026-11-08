# Wacky Wheels control tower — design notes

The one-page submission card is [DESIGN_CARD.md](DESIGN_CARD.md). This page is the same system in short form. The company tables, `policy_handbook.md`, and `enterprise.py` are the source of truth. Event ids are never an answer key.

## Architecture

One coordinator and three specialists. The coordinator reads each message with Qwen2.5 0.5B (`qwen2.5:0.5b` through Ollama) and a rule check, hands each real incident to the specialist that owns it, and is the only code that calls Enterprise. Supply Chain Planner owns delays, outages, and slots. Quality Containment owns lots, stop-sale, and owners. Dealer and Customer Care owns one notice per dealer and loaners. The dashboard shows the feed, the cited graph path, the actions, and the audit trail.

Each event gets a fresh plant schedule, a fresh loaner pool, and a fresh enterprise world. Writes go through `tower/gateway.py`: the tool name and arguments must match `GET /tools`, and the same write is not sent twice in that event.

## LLM versus code

Qwen2.5 0.5B labels each section and quotes the plant, part, supplier, lot, shipment, and dates. Code checks that every quote is in the message, resolves names through `aliases.csv`, turns "next Friday" into a date from Monday 2027-03-08, and runs the rule reader as a check. A reading is used only when it matches the rules. Otherwise the rules decide, and the trace says why. Specialists traverse `WorldGraph` and return tool calls. No `mes.get_schedule` or `crm.loaner_availability` calls are made, because the local graph already has those facts.

## Guardrails

Noise writes nothing. An unconfirmed report is `escalate` only. Hearsay, drills, negated delays, and conditionals are not acted on. A confirmed incident with no future orders stays that kind and is not escalated. A failed write is recorded, not retried, and escalated once. Only affected records change. A transfer cannot land inside another plant's outage.

## Evaluation

`python -m tower.run --reader llm --overwrite --notify dry-run` writes `runs/run1/action_log.jsonl` and `traces.json`. `python tests/run_given.py` grades the 15 events against TC1–TC6. `python -m tower._audit_run` checks the log against the handbook. The ontology export is `runs/ontology/`.

## What we would improve

A learned ranker is not used for slots, because the handbook asks for the earliest feasible day. The knowledge-graph page is the force-directed view of the company; each event page cites the path the agents actually walked.
