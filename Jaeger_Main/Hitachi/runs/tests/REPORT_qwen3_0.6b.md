# Hitachi control tower — generated test run

25 cases from `tests/cases.json`, graded by `tests/run_cases.py` against expected effects computed from the CSVs (not from tower/graph.py).

| Case | Category | rules | qwen3:0.6b | Edge case? |
|---|---|---|---|---|
| T-01 | supplier_delay | PASS | PASS |  |
| T-02 | supplier_delay | PASS | PASS |  |
| T-03 | supplier_delay | FAIL ⚠ | FAIL ⚠ |  |
| T-04 | supplier_delay | FAIL ⚠ | FAIL ⚠ | yes |
| T-05 | supplier_delay | PASS | PASS |  |
| T-06 | unconfirmed | FAIL | FAIL | yes |
| T-07 | plant_outage | PASS | PASS |  |
| T-08 | plant_outage | FAIL ⚠ | FAIL ⚠ | yes |
| T-09 | plant_outage | PASS | PASS |  |
| T-10 | plant_outage | FAIL ⚠ | FAIL ⚠ |  |
| T-11 | quality_hold | PASS | PASS |  |
| T-12 | quality_hold | PASS | PASS |  |
| T-13 | quality_hold | FAIL | FAIL | yes |
| T-14 | unconfirmed | FAIL | FAIL |  |
| T-15 | noise | PASS | PASS |  |
| T-16 | noise | PASS | PASS |  |
| T-17 | noise | PASS | PASS |  |
| T-18 | noise | PASS | PASS |  |
| T-19 | unconfirmed | PASS | PASS |  |
| T-20 | unconfirmed | FAIL | FAIL |  |
| T-21 | compound | PASS | PASS |  |
| T-22 | compound | PASS | PASS |  |
| T-23 | compound | FAIL | FAIL | yes |
| T-24 | compound | PASS | PASS |  |
| T-25 | plant_outage | FAIL ⚠ | FAIL ⚠ | yes |

**rules**: 15/25 pass
**qwen3:0.6b**: 15/25 pass

## Details — rules reader

### T-01 — supplier_delay — PASS
> Subject: SH-0090 late Meridian Seating here. Shipment SH-0090 (SEAT-LEA, leather seat set) for Wacky Wheels Lexington (P_KY) was due 2027-03-15 and will now arrive 2027-03-17. Reason: tooling failure.
- Read as: `supplier_delay` (reader: rules)
- Stats: {"writes": 23, "calls": 23, "moved": 2, "rescheduled": 2, "transferred": 0, "expected_moves": 2, "dealers": 15, "loaners": 6, "lots": [], "stop_sale_vins": 0, "owners": 0}

### T-02 — supplier_delay — PASS
> ugh, Greensboro is waiting on harness B from Volt. the Monday Mar 22 drop slipped to Wednesday Mar 24, driver got sick
- Read as: `supplier_delay` (reader: rules)
- Stats: {"writes": 23, "calls": 23, "moved": 2, "rescheduled": 2, "transferred": 0, "expected_moves": 2, "dealers": 15, "loaners": 6, "lots": [], "stop_sale_vins": 0, "owners": 0}

### T-03 — supplier_delay — FAIL
> Heads up: Redwood's van door modules for the Alabama plant, due next Monday, won't land until next Thursday. Trailer stuck at the border.
- Read as: `noise` (reader: rules)
- Stats: {"writes": 0, "calls": 0, "moved": 0, "rescheduled": 0, "transferred": 0, "expected_moves": 3, "dealers": 0, "loaners": 0, "lots": [], "stop_sale_vins": 0, "owners": 0}
- FAIL: incident kinds ['none'] expected ['supplier_delay']
- FAIL: 3 affected PO(s) not moved: ['PO-0408', 'PO-0411', 'PO-0414']
- FAIL: dealer set: extra [], missing ['D02', 'D03', 'D04', 'D06', 'D10']
- FAIL: loaners: extra [], missing ['CO-02314', 'CO-02315', 'CO-02320', 'CO-02321', 'CO-02340']
- warn: only 0 kind(s) of write action (handbook rule 9 wants 3)

### T-04 — supplier_delay — FAIL
> Ridgeline Wire: the compact wiring harness run for Lexington scheduled for Monday Mar 22 is delayed. New arrival Saturday Mar 27.
- Edge: New ETA falls on a Saturday. Expected: builds resume the next working day (Mon Mar 29).
- Read as: `supplier_delay` (reader: rules)
- Stats: {"writes": 0, "calls": 1, "moved": 0, "rescheduled": 0, "transferred": 0, "expected_moves": 5, "dealers": 0, "loaners": 0, "lots": [], "stop_sale_vins": 0, "owners": 0}
- FAIL: supplier_delay fields: blocked_until=2027-03-27 (expected 2027-03-29)
- FAIL: escalated although the event is actionable / noise
- FAIL: 5 affected PO(s) not moved: ['PO-0153', 'PO-0156', 'PO-0159', 'PO-0162', 'PO-0165']
- FAIL: dealer set: extra [], missing ['D02', 'D03', 'D05', 'D06', 'D07']
- FAIL: loaners: extra [], missing ['CO-00839', 'CO-00844', 'CO-00846', 'CO-00875', 'CO-00899']
- warn: only 0 kind(s) of write action (handbook rule 9 wants 3)

### T-05 — supplier_delay — PASS
> Subject: Shipment SH-0318 delayed From: logistics@quanta.example  Our shipment SH-0318 of CHIP-IVI (infotainment chip) for Wacky Wheels Greensboro (P_NC) was due 2027-03-15 and will now arrive 2027-04-01. Reason: wafer shortage.
- Read as: `supplier_delay` (reader: rules)
- Stats: {"writes": 110, "calls": 110, "moved": 26, "rescheduled": 4, "transferred": 22, "expected_moves": 26, "dealers": 49, "loaners": 35, "lots": [], "stop_sale_vins": 0, "owners": 0}

### T-06 — unconfirmed — FAIL
> Shipment SH-9999 for Princeton was due Monday Mar 15 and will now arrive Wednesday Mar 17.
- Edge: Names a shipment id that does not exist and no part. Expected: escalate, nothing written.
- Read as: `noise` (reader: rules)
- Stats: {"writes": 0, "calls": 0}
- FAIL: expected an escalate, none made

### T-07 — plant_outage — PASS
> Plant operations alert: Wacky Wheels Jackson (P_MS) lost production to a compressor failure. Production is stopped from 2027-03-15 through 2027-03-16 inclusive.
- Read as: `plant_outage` (reader: rules)
- Stats: {"writes": 48, "calls": 48, "moved": 6, "rescheduled": 6, "transferred": 0, "expected_moves": 6, "dealers": 31, "loaners": 11, "lots": [], "stop_sale_vins": 0, "owners": 0}

### T-08 — plant_outage — FAIL
> North Carolina plant took on water overnight. We're down this Wednesday and Thursday, back on Friday.
- Edge: 'this Wednesday' relative to Monday Mar 8 = 2027-03-10.
- Read as: `noise` (reader: rules)
- Stats: {"writes": 0, "calls": 0, "moved": 0, "rescheduled": 0, "transferred": 0, "expected_moves": 6, "dealers": 0, "loaners": 0, "lots": [], "stop_sale_vins": 0, "owners": 0}
- FAIL: incident kinds ['none'] expected ['plant_outage']
- FAIL: 6 affected PO(s) not moved: ['PO-0487', 'PO-0488', 'PO-0489', 'PO-0490', 'PO-0491']
- FAIL: dealer set: extra [], missing ['D02', 'D03', 'D04', 'D05', 'D06']
- FAIL: loaners: extra [], missing ['CO-02768', 'CO-02771', 'CO-02781', 'CO-02793', 'CO-02795']
- warn: only 0 kind(s) of write action (handbook rule 9 wants 3)

### T-09 — plant_outage — PASS
> Greensboro update: a fire suppression test failed. We're dark from Monday Mar 29 through Friday Apr 2; the line restarts the following working day.
- Read as: `plant_outage` (reader: rules)
- Stats: {"writes": 80, "calls": 80, "moved": 15, "rescheduled": 0, "transferred": 15, "expected_moves": 15, "dealers": 41, "loaners": 24, "lots": [], "stop_sale_vins": 0, "owners": 0}

### T-10 — plant_outage — FAIL
> Princeton is down tomorrow for an emergency transformer swap. One day only.
- Read as: `noise` (reader: rules)
- Stats: {"writes": 0, "calls": 0, "moved": 0, "rescheduled": 0, "transferred": 0, "expected_moves": 3, "dealers": 0, "loaners": 0, "lots": [], "stop_sale_vins": 0, "owners": 0}
- FAIL: incident kinds ['none'] expected ['plant_outage']
- FAIL: 3 affected PO(s) not moved: ['PO-0304', 'PO-0305', 'PO-0306']
- FAIL: dealer set: extra [], missing ['D02', 'D03', 'D04', 'D06', 'D20']
- FAIL: loaners: extra [], missing ['CO-01655', 'CO-01657', 'CO-01673']
- warn: only 0 kind(s) of write action (handbook rule 9 wants 3)

### T-11 — quality_hold — PASS
> QUALITY BULLETIN QB-401: Lot LOT-0091 (SEAT-LEA, supplier SUP-04) installed at P_KY on vehicles built 2027-03-02 to 2027-03-03 has a stitching defect. Place the lot on hold, stop sale of unsold vehicles and contact owners.
- Read as: `quality_hold` (reader: rules)
- Stats: {"writes": 55, "calls": 55, "moved": 0, "rescheduled": 0, "transferred": 0, "expected_moves": 0, "dealers": 0, "loaners": 0, "lots": ["LOT-0091"], "stop_sale_vins": 26, "owners": 36}

### T-12 — quality_hold — PASS
> Quality alert: Redwood says the sliding doors sent to Huntsville have a cracked hinge. Anything built Thursday Feb 25 through Monday Mar 1 is suspect.
- Read as: `quality_hold` (reader: rules)
- Stats: {"writes": 73, "calls": 73, "moved": 0, "rescheduled": 0, "transferred": 0, "expected_moves": 0, "dealers": 0, "loaners": 0, "lots": ["LOT-0270"], "stop_sale_vins": 39, "owners": 51}

### T-13 — quality_hold — FAIL
> Quality alert: Meridian says the leather seats sent to the Kentucky plant failed flammability testing. Anything built Monday Feb 22 through Monday Mar 1 is suspect.
- Edge: Build window spans two lots (LOT-0089 and LOT-0090). Expected: both lots held, vehicles from both windows.
- Read as: `quality_hold` (reader: rules)
- Stats: {"writes": 73, "calls": 73, "moved": 0, "rescheduled": 0, "transferred": 0, "expected_moves": 0, "dealers": 0, "loaners": 0, "lots": ["LOT-0090"], "stop_sale_vins": 32, "owners": 52}
- FAIL: lots held ['LOT-0090'] expected ['LOT-0089', 'LOT-0090']
- FAIL: stop-sale VINs: got 32 expected 78 (extra [], missing ['AUR0000934', 'AUR0000936', 'AUR0000937'])
- FAIL: owners notified: got 52 expected 97 (extra [], missing ['C0188', 'C0369', 'C0435'])

### T-14 — unconfirmed — FAIL
> QUALITY BULLETIN QB-999: Lot LOT-0999 installed at P_TX has a defect. Place the lot on hold.
- Read as: `noise` (reader: rules)
- Stats: {"writes": 0, "calls": 0}
- FAIL: expected an escalate, none made

### T-15 — noise — PASS
> Typhoon warning issued for Okinawa this weekend; ferries cancelled.
- Read as: `noise` (reader: rules)
- Stats: {"writes": 0, "calls": 0}

### T-16 — noise — PASS
> Reminder: the 2028 accessory price list goes live on April 15. Please update your dealer price books.
- Read as: `noise` (reader: rules)
- Stats: {"writes": 0, "calls": 0}

### T-17 — noise — PASS
> Dealer Tulsa, OK asks whether the Summit can be ordered with leather seats and surround-view cameras.
- Read as: `noise` (reader: rules)
- Stats: {"writes": 0, "calls": 0}

### T-18 — noise — PASS
> FYI the cafeteria at Lexington is closed this Friday for a private event. Bring lunch.
- Read as: `noise` (reader: rules)
- Stats: {"writes": 0, "calls": 0}

### T-19 — unconfirmed — PASS
> Heard Volt might be having trouble with harness deliveries. Can't confirm, no dates yet.
- Read as: `unconfirmed` (reader: rules)
- Stats: {"writes": 0, "calls": 1}

### T-20 — unconfirmed — FAIL
> Unverified social media post claims the Texas plant may shut down soon. No official word.
- Read as: `noise` (reader: rules)
- Stats: {"writes": 0, "calls": 0}
- FAIL: expected an escalate, none made

### T-21 — compound — PASS
> Morning digest, two items. (1) Huntsville update: a conveyor failure. We're dark from next Tuesday through next Thursday; the line restarts the following working day. (2) Lumen says the 60 kWh battery packs for Huntsville due next Monday will now arrive next Friday.
- Read as: `plant_outage+supplier_delay` (reader: rules, rules)
- Stats: {"writes": 70, "calls": 70, "moved": 10, "rescheduled": 10, "transferred": 0, "expected_moves": 10, "dealers": 34, "loaners": 26, "lots": [], "stop_sale_vins": 0, "owners": 0}

### T-22 — compound — PASS
> Digest. (1) QUALITY BULLETIN QB-410: Lot LOT-0143 (HARN-C, supplier SUP-05) installed at P_MS on vehicles built 2027-03-02 to 2027-03-03 has a short circuit. Place the lot on hold, stop sale of unsold vehicles and contact owners. (2) Jackson update: a power failure. We're dark from Monday Mar 22 through Tuesday Mar 23; the line restarts the following working day.
- Read as: `quality_hold+plant_outage` (reader: rules, rules)
- Stats: {"writes": 103, "calls": 103, "moved": 6, "rescheduled": 6, "transferred": 0, "expected_moves": 6, "dealers": 29, "loaners": 14, "lots": ["LOT-0143"], "stop_sale_vins": 23, "owners": 34}

### T-23 — compound — FAIL
> Morning digest, two items. (1) Princeton update: a software outage on the line. We're dark from next Wednesday through next Thursday; the line restarts the following working day. (2) Rumor from a supplier rep: something may be off with tires coming up. No dates, no details, nothing confirmed.
- Edge: Real outage plus a rumor. Expected: outage actions, and the rumor part escalated.
- Read as: `plant_outage+unconfirmed` (reader: rules, rules)
- Stats: {"writes": 54, "calls": 54, "moved": 6, "rescheduled": 6, "transferred": 0, "expected_moves": 6, "dealers": 30, "loaners": 18, "lots": [], "stop_sale_vins": 0, "owners": 0}
- FAIL: expected an escalate, none made

### T-24 — compound — PASS
> Morning digest, two items. (1) The new brochure PDF is on the dealer portal. (2) Quick heads up from Atlas: the heavy-duty wiring harness run for Princeton can't make it Monday Mar 22. Carrier says Wednesday Mar 24 now (a customs inspection).
- Read as: `noise+supplier_delay` (reader: rules, rules)
- Stats: {"writes": 16, "calls": 16, "moved": 2, "rescheduled": 2, "transferred": 0, "expected_moves": 2, "dealers": 11, "loaners": 3, "lots": [], "stop_sale_vins": 0, "owners": 0}

### T-25 — plant_outage — FAIL
> Lexingtn line is dark Monday Mar 15 through Tuesday Mar 16 due to a power failure; restarts the following working day.
- Edge: Typo in plant name ('Lexingtn'). Expected: still read as P_KY, or escalate rather than guess.
- Read as: `noise` (reader: rules)
- Stats: {"writes": 0, "calls": 0, "moved": 0, "rescheduled": 0, "transferred": 0, "expected_moves": 6, "dealers": 0, "loaners": 0, "lots": [], "stop_sale_vins": 0, "owners": 0}
- FAIL: incident kinds ['none'] expected ['plant_outage']
- FAIL: 6 affected PO(s) not moved: ['PO-0136', 'PO-0137', 'PO-0138', 'PO-0139', 'PO-0140']
- FAIL: dealer set: extra [], missing ['D02', 'D03', 'D05', 'D06', 'D08']
- FAIL: loaners: extra [], missing ['CO-00687', 'CO-00688', 'CO-00692', 'CO-00698', 'CO-00703']
- warn: only 0 kind(s) of write action (handbook rule 9 wants 3)

## Details — qwen3:0.6b reader

### T-01 — supplier_delay — PASS
> Subject: SH-0090 late Meridian Seating here. Shipment SH-0090 (SEAT-LEA, leather seat set) for Wacky Wheels Lexington (P_KY) was due 2027-03-15 and will now arrive 2027-03-17. Reason: tooling failure.
- Read as: `supplier_delay` (reader: qwen3:0.6b)
- Stats: {"writes": 23, "calls": 23, "moved": 2, "rescheduled": 2, "transferred": 0, "expected_moves": 2, "dealers": 15, "loaners": 6, "lots": [], "stop_sale_vins": 0, "owners": 0}

### T-02 — supplier_delay — PASS
> ugh, Greensboro is waiting on harness B from Volt. the Monday Mar 22 drop slipped to Wednesday Mar 24, driver got sick
- Read as: `supplier_delay` (reader: rules)
- Stats: {"writes": 23, "calls": 23, "moved": 2, "rescheduled": 2, "transferred": 0, "expected_moves": 2, "dealers": 15, "loaners": 6, "lots": [], "stop_sale_vins": 0, "owners": 0}

### T-03 — supplier_delay — FAIL
> Heads up: Redwood's van door modules for the Alabama plant, due next Monday, won't land until next Thursday. Trailer stuck at the border.
- Read as: `noise` (reader: rules)
- Stats: {"writes": 0, "calls": 0, "moved": 0, "rescheduled": 0, "transferred": 0, "expected_moves": 3, "dealers": 0, "loaners": 0, "lots": [], "stop_sale_vins": 0, "owners": 0}
- FAIL: incident kinds ['none'] expected ['supplier_delay']
- FAIL: 3 affected PO(s) not moved: ['PO-0408', 'PO-0411', 'PO-0414']
- FAIL: dealer set: extra [], missing ['D02', 'D03', 'D04', 'D06', 'D10']
- FAIL: loaners: extra [], missing ['CO-02314', 'CO-02315', 'CO-02320', 'CO-02321', 'CO-02340']
- warn: only 0 kind(s) of write action (handbook rule 9 wants 3)

### T-04 — supplier_delay — FAIL
> Ridgeline Wire: the compact wiring harness run for Lexington scheduled for Monday Mar 22 is delayed. New arrival Saturday Mar 27.
- Edge: New ETA falls on a Saturday. Expected: builds resume the next working day (Mon Mar 29).
- Read as: `supplier_delay` (reader: qwen3:0.6b)
- Stats: {"writes": 0, "calls": 1, "moved": 0, "rescheduled": 0, "transferred": 0, "expected_moves": 5, "dealers": 0, "loaners": 0, "lots": [], "stop_sale_vins": 0, "owners": 0}
- FAIL: supplier_delay fields: blocked_until=2027-03-27 (expected 2027-03-29)
- FAIL: escalated although the event is actionable / noise
- FAIL: 5 affected PO(s) not moved: ['PO-0153', 'PO-0156', 'PO-0159', 'PO-0162', 'PO-0165']
- FAIL: dealer set: extra [], missing ['D02', 'D03', 'D05', 'D06', 'D07']
- FAIL: loaners: extra [], missing ['CO-00839', 'CO-00844', 'CO-00846', 'CO-00875', 'CO-00899']
- warn: only 0 kind(s) of write action (handbook rule 9 wants 3)

### T-05 — supplier_delay — PASS
> Subject: Shipment SH-0318 delayed From: logistics@quanta.example  Our shipment SH-0318 of CHIP-IVI (infotainment chip) for Wacky Wheels Greensboro (P_NC) was due 2027-03-15 and will now arrive 2027-04-01. Reason: wafer shortage.
- Read as: `supplier_delay` (reader: qwen3:0.6b)
- Stats: {"writes": 110, "calls": 110, "moved": 26, "rescheduled": 4, "transferred": 22, "expected_moves": 26, "dealers": 49, "loaners": 35, "lots": [], "stop_sale_vins": 0, "owners": 0}

### T-06 — unconfirmed — FAIL
> Shipment SH-9999 for Princeton was due Monday Mar 15 and will now arrive Wednesday Mar 17.
- Edge: Names a shipment id that does not exist and no part. Expected: escalate, nothing written.
- Read as: `noise` (reader: rules)
- Stats: {"writes": 0, "calls": 0}
- FAIL: expected an escalate, none made

### T-07 — plant_outage — PASS
> Plant operations alert: Wacky Wheels Jackson (P_MS) lost production to a compressor failure. Production is stopped from 2027-03-15 through 2027-03-16 inclusive.
- Read as: `plant_outage` (reader: qwen3:0.6b)
- Stats: {"writes": 48, "calls": 48, "moved": 6, "rescheduled": 6, "transferred": 0, "expected_moves": 6, "dealers": 31, "loaners": 11, "lots": [], "stop_sale_vins": 0, "owners": 0}

### T-08 — plant_outage — FAIL
> North Carolina plant took on water overnight. We're down this Wednesday and Thursday, back on Friday.
- Edge: 'this Wednesday' relative to Monday Mar 8 = 2027-03-10.
- Read as: `noise` (reader: rules)
- Stats: {"writes": 0, "calls": 0, "moved": 0, "rescheduled": 0, "transferred": 0, "expected_moves": 6, "dealers": 0, "loaners": 0, "lots": [], "stop_sale_vins": 0, "owners": 0}
- FAIL: incident kinds ['none'] expected ['plant_outage']
- FAIL: 6 affected PO(s) not moved: ['PO-0487', 'PO-0488', 'PO-0489', 'PO-0490', 'PO-0491']
- FAIL: dealer set: extra [], missing ['D02', 'D03', 'D04', 'D05', 'D06']
- FAIL: loaners: extra [], missing ['CO-02768', 'CO-02771', 'CO-02781', 'CO-02793', 'CO-02795']
- warn: only 0 kind(s) of write action (handbook rule 9 wants 3)

### T-09 — plant_outage — PASS
> Greensboro update: a fire suppression test failed. We're dark from Monday Mar 29 through Friday Apr 2; the line restarts the following working day.
- Read as: `plant_outage` (reader: rules)
- Stats: {"writes": 80, "calls": 80, "moved": 15, "rescheduled": 0, "transferred": 15, "expected_moves": 15, "dealers": 41, "loaners": 24, "lots": [], "stop_sale_vins": 0, "owners": 0}

### T-10 — plant_outage — FAIL
> Princeton is down tomorrow for an emergency transformer swap. One day only.
- Read as: `noise` (reader: rules)
- Stats: {"writes": 0, "calls": 0, "moved": 0, "rescheduled": 0, "transferred": 0, "expected_moves": 3, "dealers": 0, "loaners": 0, "lots": [], "stop_sale_vins": 0, "owners": 0}
- FAIL: incident kinds ['none'] expected ['plant_outage']
- FAIL: 3 affected PO(s) not moved: ['PO-0304', 'PO-0305', 'PO-0306']
- FAIL: dealer set: extra [], missing ['D02', 'D03', 'D04', 'D06', 'D20']
- FAIL: loaners: extra [], missing ['CO-01655', 'CO-01657', 'CO-01673']
- warn: only 0 kind(s) of write action (handbook rule 9 wants 3)

### T-11 — quality_hold — PASS
> QUALITY BULLETIN QB-401: Lot LOT-0091 (SEAT-LEA, supplier SUP-04) installed at P_KY on vehicles built 2027-03-02 to 2027-03-03 has a stitching defect. Place the lot on hold, stop sale of unsold vehicles and contact owners.
- Read as: `quality_hold` (reader: qwen3:0.6b)
- Stats: {"writes": 55, "calls": 55, "moved": 0, "rescheduled": 0, "transferred": 0, "expected_moves": 0, "dealers": 0, "loaners": 0, "lots": ["LOT-0091"], "stop_sale_vins": 26, "owners": 36}

### T-12 — quality_hold — PASS
> Quality alert: Redwood says the sliding doors sent to Huntsville have a cracked hinge. Anything built Thursday Feb 25 through Monday Mar 1 is suspect.
- Read as: `quality_hold` (reader: qwen3:0.6b)
- Stats: {"writes": 73, "calls": 73, "moved": 0, "rescheduled": 0, "transferred": 0, "expected_moves": 0, "dealers": 0, "loaners": 0, "lots": ["LOT-0270"], "stop_sale_vins": 39, "owners": 51}

### T-13 — quality_hold — FAIL
> Quality alert: Meridian says the leather seats sent to the Kentucky plant failed flammability testing. Anything built Monday Feb 22 through Monday Mar 1 is suspect.
- Edge: Build window spans two lots (LOT-0089 and LOT-0090). Expected: both lots held, vehicles from both windows.
- Read as: `quality_hold` (reader: qwen3:0.6b)
- Stats: {"writes": 73, "calls": 73, "moved": 0, "rescheduled": 0, "transferred": 0, "expected_moves": 0, "dealers": 0, "loaners": 0, "lots": ["LOT-0090"], "stop_sale_vins": 32, "owners": 52}
- FAIL: lots held ['LOT-0090'] expected ['LOT-0089', 'LOT-0090']
- FAIL: stop-sale VINs: got 32 expected 78 (extra [], missing ['AUR0000934', 'AUR0000936', 'AUR0000937'])
- FAIL: owners notified: got 52 expected 97 (extra [], missing ['C0188', 'C0369', 'C0435'])

### T-14 — unconfirmed — FAIL
> QUALITY BULLETIN QB-999: Lot LOT-0999 installed at P_TX has a defect. Place the lot on hold.
- Read as: `noise` (reader: rules)
- Stats: {"writes": 0, "calls": 0}
- FAIL: expected an escalate, none made

### T-15 — noise — PASS
> Typhoon warning issued for Okinawa this weekend; ferries cancelled.
- Read as: `noise` (reader: qwen3:0.6b)
- Stats: {"writes": 0, "calls": 0}

### T-16 — noise — PASS
> Reminder: the 2028 accessory price list goes live on April 15. Please update your dealer price books.
- Read as: `noise` (reader: qwen3:0.6b)
- Stats: {"writes": 0, "calls": 0}

### T-17 — noise — PASS
> Dealer Tulsa, OK asks whether the Summit can be ordered with leather seats and surround-view cameras.
- Read as: `noise` (reader: rules)
- Stats: {"writes": 0, "calls": 0}

### T-18 — noise — PASS
> FYI the cafeteria at Lexington is closed this Friday for a private event. Bring lunch.
- Read as: `noise` (reader: qwen3:0.6b)
- Stats: {"writes": 0, "calls": 0}

### T-19 — unconfirmed — PASS
> Heard Volt might be having trouble with harness deliveries. Can't confirm, no dates yet.
- Read as: `unconfirmed` (reader: qwen3:0.6b)
- Stats: {"writes": 0, "calls": 1}

### T-20 — unconfirmed — FAIL
> Unverified social media post claims the Texas plant may shut down soon. No official word.
- Read as: `noise` (reader: rules)
- Stats: {"writes": 0, "calls": 0}
- FAIL: expected an escalate, none made

### T-21 — compound — PASS
> Morning digest, two items. (1) Huntsville update: a conveyor failure. We're dark from next Tuesday through next Thursday; the line restarts the following working day. (2) Lumen says the 60 kWh battery packs for Huntsville due next Monday will now arrive next Friday.
- Read as: `plant_outage+supplier_delay` (reader: qwen3:0.6b, qwen3:0.6b)
- Stats: {"writes": 70, "calls": 70, "moved": 10, "rescheduled": 10, "transferred": 0, "expected_moves": 10, "dealers": 34, "loaners": 26, "lots": [], "stop_sale_vins": 0, "owners": 0}

### T-22 — compound — PASS
> Digest. (1) QUALITY BULLETIN QB-410: Lot LOT-0143 (HARN-C, supplier SUP-05) installed at P_MS on vehicles built 2027-03-02 to 2027-03-03 has a short circuit. Place the lot on hold, stop sale of unsold vehicles and contact owners. (2) Jackson update: a power failure. We're dark from Monday Mar 22 through Tuesday Mar 23; the line restarts the following working day.
- Read as: `quality_hold+plant_outage` (reader: qwen3:0.6b, rules)
- Stats: {"writes": 103, "calls": 103, "moved": 6, "rescheduled": 6, "transferred": 0, "expected_moves": 6, "dealers": 29, "loaners": 14, "lots": ["LOT-0143"], "stop_sale_vins": 23, "owners": 34}

### T-23 — compound — FAIL
> Morning digest, two items. (1) Princeton update: a software outage on the line. We're dark from next Wednesday through next Thursday; the line restarts the following working day. (2) Rumor from a supplier rep: something may be off with tires coming up. No dates, no details, nothing confirmed.
- Edge: Real outage plus a rumor. Expected: outage actions, and the rumor part escalated.
- Read as: `plant_outage+unconfirmed` (reader: qwen3:0.6b, qwen3:0.6b)
- Stats: {"writes": 54, "calls": 54, "moved": 6, "rescheduled": 6, "transferred": 0, "expected_moves": 6, "dealers": 30, "loaners": 18, "lots": [], "stop_sale_vins": 0, "owners": 0}
- FAIL: expected an escalate, none made

### T-24 — compound — PASS
> Morning digest, two items. (1) The new brochure PDF is on the dealer portal. (2) Quick heads up from Atlas: the heavy-duty wiring harness run for Princeton can't make it Monday Mar 22. Carrier says Wednesday Mar 24 now (a customs inspection).
- Read as: `noise+supplier_delay` (reader: qwen3:0.6b, qwen3:0.6b)
- Stats: {"writes": 16, "calls": 16, "moved": 2, "rescheduled": 2, "transferred": 0, "expected_moves": 2, "dealers": 11, "loaners": 3, "lots": [], "stop_sale_vins": 0, "owners": 0}

### T-25 — plant_outage — FAIL
> Lexingtn line is dark Monday Mar 15 through Tuesday Mar 16 due to a power failure; restarts the following working day.
- Edge: Typo in plant name ('Lexingtn'). Expected: still read as P_KY, or escalate rather than guess.
- Read as: `noise` (reader: rules)
- Stats: {"writes": 0, "calls": 0, "moved": 0, "rescheduled": 0, "transferred": 0, "expected_moves": 6, "dealers": 0, "loaners": 0, "lots": [], "stop_sale_vins": 0, "owners": 0}
- FAIL: incident kinds ['none'] expected ['plant_outage']
- FAIL: 6 affected PO(s) not moved: ['PO-0136', 'PO-0137', 'PO-0138', 'PO-0139', 'PO-0140']
- FAIL: dealer set: extra [], missing ['D02', 'D03', 'D05', 'D06', 'D08']
- FAIL: loaners: extra [], missing ['CO-00687', 'CO-00688', 'CO-00692', 'CO-00698', 'CO-00703']
- warn: only 0 kind(s) of write action (handbook rule 9 wants 3)

