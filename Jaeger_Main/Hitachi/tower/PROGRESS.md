# Wacky Wheels control tower — build log

Working only in `Jaeger_Main/Hitachi`. The company tables, the policy handbook, and `enterprise.py` are the source of truth. Event ids are never mapped to canned answers.

## How the five agents split

| Agent | Owns | Does not touch |
|---|---|---|
| Supply Chain Planner | `tower/agents/supply_chain.py` | Other agents, the UI, the graph |
| Quality Containment | `tower/agents/quality.py` | Scheduling and loaners |
| Dealer and Customer Care | `tower/agents/dealer_customer.py` | Which orders are affected |
| Coordinator | `tower/agents/understand.py`, `tower/agents/coordinator.py`, `tower/run.py` | Specialist internals |
| Control-tower UI | `tower/ui/` | Tool decisions |

Georgi and the coordinator share the structure: contracts, the knowledge graph, the calendar, and this log.

## Step 1 — Read the challenge

Wacky Wheels has no parts buffer. A message is a supplier delay, a plant outage, a quality hold, noise, an unconfirmed report, or a compound of those. Confirmed incidents follow the handbook. Noise writes nothing. An unconfirmed report is `escalate` and nothing else. Only affected records change.

Scoring is 50% action accuracy, 20% graph and reasoning, 10% agent architecture, 10% efficiency, 10% the control-tower view.

The feed has 15 events. The shapes match the six test cases: 3 delays, 3 outages, 3 quality holds, 3 noise, 1 compound, 2 unconfirmed.

## Step 2 — Structure that is already in code

- `tower/contracts.py` — incidents, tool calls, specialist results, the per-event trace.
- `tower/calendar_util.py` — working days and relative dates. Today is Monday 2027-03-08.
- `tower/graph.py` — the ontology loaded from the CSVs. `python tower/selfcheck.py` passed: 6 plants, 540 production orders, 3,263 customer orders, 5,348 vehicles (2,927 sold, 2,421 in stock), 364 shipments, 364 lots. Calendar indexes match `calendar.csv`.
- `tower/schedule.py` — per-event slot board and loaner pools. Each event starts from the tables again.

The graph answers who is affected. Specialists turn that into tool calls. The coordinator is the only code that calls `Enterprise`.

## Decisions locked with Georgi

1. **Next weekday.** Locked. "next Monday" is 2027-03-15 and "next Friday" is 2027-03-19. "last Monday" is 2027-03-01.
2. **Delay window.** A build is affected from the original ETA up to, not including, the new ETA, at the receiving plant, on models whose bill of materials contains the part. `covers_days` is not a second filter. The handbook states the window directly.
3. **Slots.** Locked. Same plant first, on or after the new ETA or the restart day. Transfer only when that plant has no free slot through 2027-04-02. Transfer goes to the earliest free day at another plant that builds the model. Equal days break toward the lower plant id.
4. **Understanding.** Locked. A deterministic reader uses aliases, ids, and the calendar. A model is added later only if a message breaks that reader. Event ids are never a lookup key.
5. **UI.** One local page, Python standard library only, beside the run. It shows the event, the affected records, the graph path, the decisions, the actions, and the audit trail.

## Step 3 — Specialists, coordinator, UI

- Dealer and Customer Care is in `tower/agents/dealer_customer.py`. Checked: one notice per dealer, then Platinum before Gold, then earlier promised date, then lower order id. A pool of 2 at one dealer assigned the two earlier Platinum orders and left the Gold customer waiting.
- Quality Containment is in `tower/agents/quality.py`. A named lot is held only when that id exists. A window of part, plant, and build dates can select a lot. An unknown lot id does not fall through to a different lot. LOT-0191 resolves to one hold, 25 stop-sale calls, and 76 owner notices (76 sold, 40 in stock).
- Supply Chain Planner is in `tower/agents/supply_chain.py`. Checked through `Enterprise`: the Princeton camera delay moves 3 orders, all accepted; the Lexington outage moves 6, all accepted. Filling the home plant turns those 6 into transfers, and the tools accept them.
- The coordinator read all 15 events and wrote `runs/run1/action_log.jsonl` (768 calls, all accepted) and `runs/run1/traces.json`.
- A handbook check on that log found no mismatches: noise has no calls, the two rumors only escalate, every moved order is inside the incident window, each dealer is notified once with exactly its affected orders, loaners stay inside tier and pool limits, and the three quality lots are LOT-0130, LOT-0017, and LOT-0191, each matching the stated build window.
- The UI is still writing.

## Not started

- A full run of the 15 events into `runs/run1/action_log.jsonl`
- Review of that log against the handbook, event by event
- Demo path: event arrives, graph path, agents act, audit trail
