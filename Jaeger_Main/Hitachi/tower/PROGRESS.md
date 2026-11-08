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

Scoring is 50% action accuracy, 20% graph and reasoning, 10% agent architecture, 10% efficiency, 10% the control-tower view. No language model is used: the reader is deterministic Python. The one-page design card is `DESIGN.md`. The ontology export is `tower/ontology.mmd`.

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
- The control tower page is `tower/ui/` and serves the run at http://127.0.0.1:8080.

## Step 4 — Break and fix

An adversarial suite in `tower/tests/test_adversarial.py` found six handbook breaks. The fixes are in the reader, the calendar, and the supply planner: an explicit "not confirmed" escalates before an outage or delay is acted on, labeled ETAs are not taken in word order, "March 32" is skipped, a bulletin that only names a known lot still holds that lot, and a transfer cannot land inside another plant's outage. `python -m unittest tower.tests.test_adversarial` covers these cases. Hearsay is classified before a quality hold or an outage, so a lot bulletin or a plant window that is still a rumor is escalated. The 15 stored event classifications are unchanged: only E-02 and E-13 are unconfirmed. An overload with every plant dark still keeps each day inside its slot count. When the whole window is dark, no build is moved and the dealers of the affected orders are still notified. Forty copies of one outage move each order once. A later pass shortened the repeated scans in the reader, the graph, the slot board, and the three specialists. Window lookups now slice orders and vehicles by date, and a shipment route is indexed by supplier, part, and plant. A specialist stores 32 graph paths and counts the rest. The page draws the first 48 ids and the first 60 actions, and the run drops each event's slot map after the calls are logged. The 15 stored classifications still match, and the suite stayed at 36 passed. `tower/tests/FINDINGS.md` now records the fixed breaks instead of the first failed run.

## Diagnostic — scoring bottlenecks, not CPU

The 15-event pipeline is not slow: graph load 90 ms, all 15 events 29 ms, slowest E-01 at 7 ms. Quality holds are the write-heavy events (E-03 is 188 calls). Zero failed or wasted read tools.

What actually costs points, and what changed:

- Action log (50%): a Sunday new ETA no longer drops the delay. Friday builds move to Monday. A transfer may land before the restart; that is Rule 3, not a bug. The stored 768-call log still matches the handbook checker (PROBLEMS 0). Classifications of the 15 events are unchanged.
- Graph (20%): cited paths are drawn as SVG on the page. Ontology export is `tower/ontology.json` and `tower/ontology.mmd`. traces.json compacted 876 KB → 558 KB.
- Efficiency (10%): no language model. Cited in the page subtitle and `DESIGN.md`.
- UX (10%): design card `DESIGN.md`, demo still of E-01 at `runs/screenshots/e01-compound.png`. Relative dates now use the event `received_at` day.
