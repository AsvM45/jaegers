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
- `tower/graph.py` — the ontology loaded from the CSVs. `python tests/selfcheck.py` passed: 6 plants, 540 production orders, 3,263 customer orders, 5,348 vehicles (2,927 sold, 2,421 in stock), 364 shipments, 364 lots. Calendar indexes match `calendar.csv`.
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
- The control tower page is `tower/ui/` and serves the run at http://127.0.0.1:8080 (`python start.py --serve-only`).

## Still to do

- Demo video or screenshots: an event arrives, its graph path, the agents act, the audit trail.

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

## Step 5 — Submission pieces

- **Official tool path.** `python -m tower.run --server http://127.0.0.1:8000` sends every call to `enterprise_server.py` (`GET /events`, `POST /act`). The server writes the scored `runs/run1/action_log.jsonl`. It matches the in-process log byte for byte: 768 calls, 0 failed.
- **Ontology export.** `python -m tower.ontology` writes `runs/ontology/` (`ontology.md` with a Mermaid diagram, `ontology.json`, `ontology.dot`): 11 node types and 16 edge types, with counts from the CSVs.
- **Failed calls.** `python tests/test_failures.py`. One failed write is logged and not retried, and the rest still run. If every write fails, the event is escalated once. Noise makes no calls.
- **Given tests.** `python tests/run_given.py` gives 15/15 against TC1–TC6. `tests/given_cases.json` is a test fixture that the tower never reads.
- **Design card.** `DESIGN_CARD.md`.

- **Model alarm** (since replaced: a checked model reading is now used when the word lists find nothing; see `_decide_with_llm` in `tower/agents/understand.py`). When Qwen reads a real incident, every quoted phrase checks out, and the word lists find nothing, the message becomes `unconfirmed` and is escalated, not treated as noise. Checked on four messages with new wording ("halted … flood", "behind schedule", "bad batch … failed inspection", "offline"): all four were escalated, and a dealer question stayed noise. The given tests (15/15) and generated tests (25/25) still pass.


## Break and fix — adversarial suite (backend branch)

An adversarial suite in `tower/tests/test_adversarial.py` found six handbook breaks. The fixes are in the reader, the calendar, and the supply planner: an explicit "not confirmed" escalates before an outage or delay is acted on, labeled ETAs are not taken in word order, "March 32" is skipped, a bulletin that only names a known lot still holds that lot, and a transfer cannot land inside another plant's outage. `python -m unittest tower.tests.test_adversarial` covers these cases. Hearsay is classified before a quality hold or an outage, so a lot bulletin or a plant window that is still a rumor is escalated. The 15 stored event classifications are unchanged: only E-02 and E-13 are unconfirmed. An overload with every plant dark still keeps each day inside its slot count. When the whole window is dark, no build is moved and the dealers of the affected orders are still notified. Forty copies of one outage move each order once. A later pass shortened the repeated scans in the reader, the graph, the slot board, and the three specialists. Window lookups now slice orders and vehicles by date, and a shipment route is indexed by supplier, part, and plant. A specialist stores 32 graph paths and counts the rest. The page draws the first 48 ids and the first 60 actions, and the run drops each event's slot map after the calls are logged. The 15 stored classifications still match, and the suite stayed at 36 passed. `tower/tests/FINDINGS.md` now records the fixed breaks instead of the first failed run.

## Diagnostic — scoring bottlenecks, not CPU

The 15-event pipeline is not slow: graph load 90 ms, all 15 events 29 ms, slowest E-01 at 7 ms. Quality holds are the write-heavy events (E-03 is 188 calls). Zero failed or wasted read tools.

What actually costs points, and what changed:

- Action log (50%): a Sunday new ETA no longer drops the delay. Friday builds move to Monday. A transfer may land before the restart; that is Rule 3, not a bug. The stored 768-call log still matches the handbook checker (PROBLEMS 0). Classifications of the 15 events are unchanged.
- Graph (20%): cited paths are drawn as SVG on the page. Ontology export is `tower/ontology.json` and `tower/ontology.mmd`. traces.json compacted 876 KB → 558 KB.
- Efficiency (10%): written on the backend branch before it merged with the LLM reader. After the merge the tower reads with Qwen3 0.6B plus the rule check (see Step 5 above and `DESIGN_CARD.md`).
- UX (10%): design card `DESIGN.md`, demo still of E-01 at `runs/screenshots/e01-compound.png`. Relative dates now use the event `received_at` day.

## Merge — LLM reader + backend branch

The LLM reader (Qwen3 0.6B, rule check, retry with feedback, a reason on every incident) and the backend branch (gateway, event-day anchor, hearsay first, non-events, labeled ETAs, lot-only bulletins, transfer guard, path cap, overwrite guard) are combined. `quality.py` keeps holding every lot that overlaps an ambiguous window.
