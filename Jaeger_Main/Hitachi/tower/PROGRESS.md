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
4. **Understanding.** Qwen3 0.6B (`qwen3:0.6b`, 752M parameters, local through Ollama) reads each message section and returns its kind plus exact phrases for the plant, part, supplier, lot, shipment, and two dates (`tower/agents/llm_reader.py`). Code checks that each phrase appears in the text, resolves it through aliases and the calendar, and runs the deterministic reader as a check. A kind disagreement or a failed check falls back to the rule reader, and the trace records why (`Incident.reader`, `evidence`). `python -m tower.run --reader rules` skips the model. Event ids are never a lookup key.
   Latest run: the model's reading was used on 11 of 16 sections. The rules were used on 5: 2 wrong kinds (E-09, E-10) and 3 bad phrases (E-01 outage, E-03, E-11). Actions match the rules-only run exactly, apart from dealer message wording.
   Model benchmark on the 15 events (kinds right / readings verified / s per call): qwen2.5:0.5b 10/7/2.1, **qwen3:0.6b 14/11/3.2**, gemma3:1b 11/9/4.9, llama3.2:1b 14/14/4.0, qwen2.5:1.5b 14/11/4.2, qwen3:1.7b 14/14/5.1. All six give identical actions; Qwen3 0.6B is the smallest with the best kind accuracy.
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

## Channels — Gmail, Outlook, Slack, Teams and more

`tower/channels/` (see its README). Inbound sources (Gmail, Outlook, Slack, Teams, IMAP) turn messages into events with the same shape as events.json, and `python -m tower.channels watch` runs them live into `runs/live/`. Outbound dispatch reads a finished run and sends escalations (Slack, Teams, PagerDuty), ops summaries, dealer notices and customer notices (Outlook, Gmail, SMTP, Google Chat, webhook).

- Off by default. `python -m tower.run --notify dry-run|send` turns it on.
- Checked: with dry-run on, `action_log.jsonl` and `traces.json` are byte-identical to a plain run (768 calls).
- Checked: a Slack message with E-10's text produces exactly E-10's tool calls.
- Guardrails: only accepted calls notify; dry-run is the default; a redirect inbox is on in the example config; no email goes to an address missing from `contacts.json`; a message cap applies, with escalations first; a sent-ledger stops repeat sends; the tower skips its own posts so they never loop back as events.
- Tests: `python tests/test_channels.py` (23, no network).

## Step 4 — Accuracy fixes from tests/cases.json (25/25 with rules and with qwen3:0.6b)

General reader and policy fixes; no case or event ids are used anywhere.

- More wording: "won't land", "we're down", "is dark", "slipped", "unverified", "no official word", "defect", and more. Dates: "today", "tomorrow", and a bare weekday read from the date just before it. "back on Friday" counts as a restart day, not an outage day.
- Names: aliases also match without a leading "the". A capitalised word one typo away from exactly one plant or supplier name resolves ("Lexingtn" -> P_KY).
- A new ETA on a weekend rolls to the next working day. An outage with one date is a single-day outage.
- Incident wording about our records that cannot be resolved (missing fields, or an unknown id like SH-9999 or LOT-0999) is `unconfirmed` and escalated, not noise.
- A quality window that matches no single lot exactly holds every overlapping lot. There is still one stop-sale per dealer and one notice per owner.
- A rumor section inside a real event is also escalated.
- When the model's fields differ from the rule check, the rule reading is used.
- E-01..E-15 actions are unchanged: 768 calls, 0 failed, audit PROBLEMS 0.
