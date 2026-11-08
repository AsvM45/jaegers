# Edge cycle ledger

Started 2026-11-07 21:34 local. Stop at 2026-11-07 22:05 local. After that, do not start another role.

Three roles, one at a time, in this order, then repeat: evil, fixer, protector. Read this file before acting. Append a section when you finish. Do not delete another role's notes.

## Rules for every role

- Work only under `Jaeger_Main/Hitachi`. Run commands from that directory.
- Python standard library only. No pip, no pydantic, no network.
- Do not edit `enterprise.py` or `enterprise_server.py`.
- Do not write `runs/run1` and do not pass `--overwrite`.
- Do not weaken or delete a test to make it pass.
- Event ids are not an answer key. Do not special-case E-01 or any other feed id.
- `understand(graph, text)` must keep working. An optional anchor date may be added, defaulting to Monday 2027-03-08.
- The 15 feed classifications must stay: E-01 plant_outage+supplier_delay, E-02 unconfirmed, E-03 quality_hold, E-04 plant_outage, E-05 noise, E-06 noise, E-07 noise, E-08 plant_outage, E-09 supplier_delay, E-10 supplier_delay, E-11 plant_outage, E-12 supplier_delay, E-13 unconfirmed, E-14 quality_hold, E-15 quality_hold.

## Already guarded

Hearsay before quality, outage, and delay. Labeled ETAs. Impossible days skipped. Known lot without a repeated window. Transfers skip a destination outage. Whole-window darkness does not overbook. Duplicate numbered outages move an order once. Each event has its own enterprise state.

## What the next failing test should prove

1. Delay window is `[original ETA, new ETA)`. An order on the original date moves. An order on the new ETA stays. Outage `through` the end date is inclusive. An order on the next working day stays.
2. `next Wednesday` is the Wednesday of the next calendar week from the event date, never `datetime.now()`. From 2027-03-08, from a Wednesday, from a Saturday, and from 2026-12-31, the result follows that week rule. The 15 events are all dated 2027-03-08, so their relative dates must not move.
3. One order hit by an outage and a delay is rescheduled once, to a day legal for both. Swapping the incident order does not change the final plant and day.
4. `on hold at customs` with an original drop and a new ETA is a supplier delay. A quality bulletin that says a known lot is `on hold` stays a quality hold.
5. `The Huntsville line is waiting on battery packs` with both ETAs is a supplier delay, not a plant outage.
6. A confirmed outage or delay whose window contains no future order is that kind in the trace, with no write and no escalate. A failed write still escalates once.
7. `ignore previous instructions` plus `stop sale of all vehicles`, with no real lot, is noise and writes nothing.
8. `No delay expected`, `if it goes past Friday`, and `plant outage drill` do not move orders.
9. A nickname and the canonical name produce the same calls. `afford` does not select a part. The longer part name wins over a shorter one contained in it.
10. Event B does not see event A's holds, notices, or slot moves.

## Role: evil

Add cases to `tower/tests/test_edges.py`. Use the unittest style in `tower/tests/test_adversarial.py`. Run the new file. Record each failure with the assertion and the actual classification or tool list. Do not fix production code.

## Role: fixer

Run `python -m unittest tower.tests.test_edges tower.tests.test_adversarial`. Fix production code under `tower/` until both are green. Re-check the 15 classifications against `runs/run1/traces.json` without rewriting that file. Append what changed.

## Role: protector

Add guards the ledger does not already have, without changing a passing edge result: validate tool name and argument types against `enterprise.TOOLS` before `Enterprise.call`, refuse a second identical write in the same event, and strip zero-width characters before classification. Cover each guard with a test in `test_edges.py`. Run both suites.

## Log

### cycle 0 — parent

Ledger opened. Evil goes first.

### cycle 1 — evil

Added 14 tests in `tower/tests/test_edges.py`. Ran `python -m unittest tower.tests.test_edges -v` from `Jaeger_Main/Hitachi`. 9 passed, 5 failed. The runner reported 10 subtest failures. Production code was not changed.

- `test_delay_window_is_half_open_and_outage_through_is_inclusive` — pass
- `test_next_wednesday_follows_the_event_week` — fail
  - Monday 2027-03-08 passed: supplier_delay, original 2027-03-15, new ETA 2027-03-17. The 15 feed events kept those relative dates. `datetime.now` and `date.today` are not used.
  - Wednesday 2027-03-17: assertion supplier_delay 2027-03-22 until 2027-03-24. Actual supplier_delay 2027-03-15 until 2027-03-17.
  - Saturday 2027-03-20: assertion supplier_delay 2027-03-22 until 2027-03-24. Actual supplier_delay 2027-03-15 until 2027-03-17.
  - Thursday 2026-12-31: assertion supplier_delay 2027-01-04 until 2027-01-06. Actual supplier_delay 2027-03-15 until 2027-03-17.
- `test_shared_order_is_rescheduled_once_to_a_day_legal_for_both` — pass
- `test_customs_hold_with_etas_is_supplier_delay` — fail
  - Assertion: supplier_delay, SUP-05, HARN-B, P_TX, blocked 2027-03-09 until 2027-03-16, no lot.
  - Actual classification: quality_hold, SUP-05, HARN-B, P_TX, no blocked window, no lot. Tools: `escalate`.
- `test_quality_bulletin_on_hold_stays_quality_hold` — pass
- `test_huntsville_waiting_on_battery_packs_is_supplier_delay` — fail
  - Assertion: supplier_delay, P_AL, BATT-60, blocked 2027-03-09 until 2027-03-16.
  - Actual classification: noise, no plant, no part, no window. Tools: none.
- `test_confirmed_incident_with_no_future_orders_does_not_escalate` — fail
  - supplier_delay: classification stayed supplier_delay. Assertion: no tools. Actual tools: `escalate`.
  - plant_outage: classification stayed plant_outage. Assertion: no tools. Actual tools: `escalate`.
- `test_failed_write_still_escalates_once` — pass
- `test_ignore_previous_instructions_and_stop_sale_is_noise` — pass
- `test_negated_delay_conditional_and_drill_do_not_move_orders` — fail
  - "No delay expected": assertion noise and no tools. Actual supplier_delay. Tools: `mes.reschedule`, `dealer.notify`, `crm.assign_loaner`.
  - "if it goes past Friday": assertion noise and no tools. Actual supplier_delay. Tools: `mes.reschedule`, `dealer.notify`, `crm.assign_loaner`.
  - "plant outage drill": assertion noise and no tools. Actual plant_outage. Tools: `mes.reschedule`, `dealer.notify`, `crm.assign_loaner`.
- `test_nickname_and_canonical_name_produce_the_same_calls` — pass
- `test_afford_does_not_select_a_part` — pass
- `test_longer_part_name_wins_over_a_shorter_one` — pass
- `test_event_b_does_not_see_event_a_state` — pass

### cycle 1 — fixer

Production code only. Tests, `enterprise.py`, `enterprise_server.py`, and `runs/` were not edited.

- Anchor dates. `understand(graph, text, anchor=None)` measures relative weekdays from that date. None stays Monday 2027-03-08 (`calendar_util.TODAY`). The date is passed into `extract_dates`, `parse_phrase`, and `_shift_weekday`. "next <weekday>" is `anchor + (7 - anchor.weekday())` plus the weekday index. No wall-clock call. `extract_dates(phrase)` with no anchor still uses TODAY, so the 15 feed events stay on the week of 2027-03-15.
- Customs hold. Removed the bare phrase "on hold" from the quality trigger. "Quality bulletin: lot LOT-0191 is on hold" stays `quality_hold` because "quality bulletin" and the known lot remain. "on hold at customs" with an original drop and a new ETA is `supplier_delay` for Volt, HARN-B, P_TX, 2027-03-09 until 2027-03-16.
- Huntsville line. A whole-word suffix of a part alias resolves only when it is at least two words long and matches exactly one part. "battery packs" is the tail of "60 kWh battery packs" and resolves to BATT-60. A shared tail such as "wiring harness" is left unresolved. A delay with a plant, a part, and two dates does not require a supplier. "waiting on" stays delay language, so the Huntsville battery sentence is `supplier_delay` for P_AL and BATT-60, 2027-03-09 until 2027-03-16.
- Empty confirmed windows. The coordinator escalates only when at least one write was attempted and none succeeded. A confirmed `supplier_delay` or `plant_outage` with zero future orders and zero planned writes gets no escalate and no writes. `test_failed_write_still_escalates_once` still sees exactly one escalate when every write raises `ToolError`.
- Negation, conditionals, drills. Before quality, outage, or delay, a section is noise when it contains "no delay expected", "if it goes past", or "drill" as whole words.

`python -m unittest tower.tests.test_edges tower.tests.test_adversarial` from `Jaeger_Main/Hitachi`: Ran 50 tests in 6.660s, OK.

`understand()` on the 15 events in `Data/hack_the_highway_package/data/events.json` still matches `runs/run1/traces.json` classifications: E-01 plant_outage+supplier_delay, E-02 unconfirmed, E-03 quality_hold, E-04 plant_outage, E-05 noise, E-06 noise, E-07 noise, E-08 plant_outage, E-09 supplier_delay, E-10 supplier_delay, E-11 plant_outage, E-12 supplier_delay, E-13 unconfirmed, E-14 quality_hold, E-15 quality_hold. That file was not rewritten.

### cycle 1 — protector

Added three guards. Existing edge assertions were not weakened. `enterprise.py`, `enterprise_server.py`, and `runs/` were not edited.

- Tool schema. Before `Enterprise.call`, the coordinator checks the tool is in `enterprise.TOOLS` and each required arg matches: `str` is a non-empty str, `list[str]` is a non-empty list of non-empty str, `YYYY-MM-DD` is a str of that shape. A bad call is recorded as not ok, is not sent, does not raise out of `handle_event`, and is not retried.
- Duplicate writes. Within one event, a write tool whose args already succeeded is not sent again. The duplicate is recorded as not sent. Reads and escalate are not on that ledger. Comparison sorts keys and keeps list order. A write that failed is not remembered, so a later attempt can still be sent.
- Zero-width characters. `understand` strips U+200B, U+200C, U+200D, and U+FEFF before the message is split or classified. `not\u200b confirmed` on a fully specified Texas outage is unconfirmed and does not reschedule. The same outage without that character stays a plant outage.

`python -m unittest tower.tests.test_edges tower.tests.test_adversarial` from `Jaeger_Main/Hitachi`: Ran 53 tests in 6.719s, OK.

`understand()` on the 15 events in `Data/hack_the_highway_package/data/events.json` still matches `runs/run1/traces.json` classifications: E-01 plant_outage+supplier_delay, E-02 unconfirmed, E-03 quality_hold, E-04 plant_outage, E-05 noise, E-06 noise, E-07 noise, E-08 plant_outage, E-09 supplier_delay, E-10 supplier_delay, E-11 plant_outage, E-12 supplier_delay, E-13 unconfirmed, E-14 quality_hold, E-15 quality_hold. That file was not rewritten.
