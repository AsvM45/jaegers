# Wacky Wheels control tower — design card

One coordinating agent and three specialists. The company tables, `policy_handbook.md`, and `enterprise.py` are the source of truth. Event ids are never an answer key.

## Architecture

The coordinator reads a message, asks the specialist that owns each real incident, and is the only code that calls Enterprise. Supply Chain Planner owns delays, outages, and slots. Quality Containment owns lots, stop-sale, and owners. Dealer and Customer Care owns one notice per dealer and loaners. A fifth local page shows the feed, the cited graph path, the actions, and the audit.

Each event gets a fresh plant schedule, a fresh loaner pool, and a fresh enterprise world. Writes go through `tower/gateway.py`: the tool name and arguments must match `GET /tools`, and the same write is not sent twice in that event.

## LLM versus code

No language model is used. The reader is deterministic Python: aliases, ids, and the working-day calendar. Relative dates are measured from the event day (the feed is Monday 2027-03-08). Specialists traverse `WorldGraph` and return tool calls. Efficiency score: zero inference cost, no failed hallucinated tools, and no wasted `mes.get_schedule` or `crm.loaner_availability` calls because the local graph already has those facts.

If a later message broke the reader, a small local model could be added only for that sentence. It would still have to produce an `Incident` that the graph validates before any write.

## Guardrails

Noise writes nothing. An unconfirmed report is `escalate` only. Hearsay, drills, negated delays, and conditionals are not acted on. A confirmed incident with no future orders stays that kind and is not escalated. A failed write is recorded, not retried, and escalated once. Only affected records change. A transfer cannot land inside another plant's outage.

## Evaluation

`python -m tower.run --out runs/run1` writes `action_log.jsonl` and `traces.json`. `python -m tower._audit_run` checks that log against the handbook using the incidents in the traces. `python -m unittest tower.tests.test_edges tower.tests.test_adversarial` covers windows, rumors, colliding incidents, and the gateway.

## What we would improve

A cited path is stored for the first 32 affected records; the rest are counted. A learned ranker is not used for slots, because the handbook asks for the earliest feasible day. The page draws those cited paths as SVG; a force-directed view of the whole company graph would not help a judge replay one event.
