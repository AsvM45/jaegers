# Hitachi control tower — generated test run

25 cases from `tests/cases.json`, graded by `tests/run_cases.py` against expected effects computed from the CSVs (not from tower/graph.py).

| Case | Category | rules | Edge case? |
|---|---|---|---|
| T-01 | supplier_delay | PASS |  |
| T-02 | supplier_delay | PASS |  |
| T-03 | supplier_delay | PASS |  |
| T-04 | supplier_delay | PASS | yes |
| T-05 | supplier_delay | PASS |  |
| T-06 | unconfirmed | PASS | yes |
| T-07 | plant_outage | PASS |  |
| T-08 | plant_outage | PASS | yes |
| T-09 | plant_outage | PASS |  |
| T-10 | plant_outage | PASS |  |
| T-11 | quality_hold | PASS |  |
| T-12 | quality_hold | PASS |  |
| T-13 | quality_hold | PASS | yes |
| T-14 | unconfirmed | PASS |  |
| T-15 | noise | PASS |  |
| T-16 | noise | PASS |  |
| T-17 | noise | PASS |  |
| T-18 | noise | PASS |  |
| T-19 | unconfirmed | PASS |  |
| T-20 | unconfirmed | PASS |  |
| T-21 | compound | PASS |  |
| T-22 | compound | PASS |  |
| T-23 | compound | PASS | yes |
| T-24 | compound | PASS |  |
| T-25 | plant_outage | PASS | yes |

**rules**: 25/25 pass

## Details — rules reader

### T-01 — supplier_delay — PASS
> Subject: SH-0090 late Meridian Seating here. Shipment SH-0090 (SEAT-LEA, leather seat set) for Wacky Wheels Lexington (P_KY) was due 2027-03-15 and will now arrive 2027-03-17. Reason: tooling failure.
- Read as: `supplier_delay` (reader: rules)
- Stats: {"writes": 23, "calls": 23, "moved": 2, "rescheduled": 2, "transferred": 0, "expected_moves": 2, "dealers": 15, "loaners": 6, "lots": [], "stop_sale_vins": 0, "owners": 0}

### T-02 — supplier_delay — PASS
> ugh, Greensboro is waiting on harness B from Volt. the Monday Mar 22 drop slipped to Wednesday Mar 24, driver got sick
- Read as: `supplier_delay` (reader: rules)
- Stats: {"writes": 23, "calls": 23, "moved": 2, "rescheduled": 2, "transferred": 0, "expected_moves": 2, "dealers": 15, "loaners": 6, "lots": [], "stop_sale_vins": 0, "owners": 0}

### T-03 — supplier_delay — PASS
> Heads up: Redwood's van door modules for the Alabama plant, due next Monday, won't land until next Thursday. Trailer stuck at the border.
- Read as: `supplier_delay` (reader: rules)
- Stats: {"writes": 28, "calls": 28, "moved": 3, "rescheduled": 3, "transferred": 0, "expected_moves": 3, "dealers": 17, "loaners": 8, "lots": [], "stop_sale_vins": 0, "owners": 0}

### T-04 — supplier_delay — PASS
> Ridgeline Wire: the compact wiring harness run for Lexington scheduled for Monday Mar 22 is delayed. New arrival Saturday Mar 27.
- Edge: New ETA falls on a Saturday. Expected: builds resume the next working day (Mon Mar 29).
- Read as: `supplier_delay` (reader: rules)
- Stats: {"writes": 46, "calls": 46, "moved": 5, "rescheduled": 5, "transferred": 0, "expected_moves": 5, "dealers": 31, "loaners": 10, "lots": [], "stop_sale_vins": 0, "owners": 0}

### T-05 — supplier_delay — PASS
> Subject: Shipment SH-0318 delayed From: logistics@quanta.example  Our shipment SH-0318 of CHIP-IVI (infotainment chip) for Wacky Wheels Greensboro (P_NC) was due 2027-03-15 and will now arrive 2027-04-01. Reason: wafer shortage.
- Read as: `supplier_delay` (reader: rules)
- Stats: {"writes": 110, "calls": 110, "moved": 26, "rescheduled": 4, "transferred": 22, "expected_moves": 26, "dealers": 49, "loaners": 35, "lots": [], "stop_sale_vins": 0, "owners": 0}

### T-06 — unconfirmed — PASS
> Shipment SH-9999 for Princeton was due Monday Mar 15 and will now arrive Wednesday Mar 17.
- Edge: Names a shipment id that does not exist and no part. Expected: escalate, nothing written.
- Read as: `unconfirmed` (reader: rules)
- Stats: {"writes": 0, "calls": 1}

### T-07 — plant_outage — PASS
> Plant operations alert: Wacky Wheels Jackson (P_MS) lost production to a compressor failure. Production is stopped from 2027-03-15 through 2027-03-16 inclusive.
- Read as: `plant_outage` (reader: rules)
- Stats: {"writes": 48, "calls": 48, "moved": 6, "rescheduled": 6, "transferred": 0, "expected_moves": 6, "dealers": 31, "loaners": 11, "lots": [], "stop_sale_vins": 0, "owners": 0}

### T-08 — plant_outage — PASS
> North Carolina plant took on water overnight. We're down this Wednesday and Thursday, back on Friday.
- Edge: 'this Wednesday' relative to Monday Mar 8 = 2027-03-10.
- Read as: `plant_outage` (reader: rules)
- Stats: {"writes": 38, "calls": 38, "moved": 6, "rescheduled": 6, "transferred": 0, "expected_moves": 6, "dealers": 23, "loaners": 9, "lots": [], "stop_sale_vins": 0, "owners": 0}

### T-09 — plant_outage — PASS
> Greensboro update: a fire suppression test failed. We're dark from Monday Mar 29 through Friday Apr 2; the line restarts the following working day.
- Read as: `plant_outage` (reader: rules)
- Stats: {"writes": 80, "calls": 80, "moved": 15, "rescheduled": 0, "transferred": 15, "expected_moves": 15, "dealers": 41, "loaners": 24, "lots": [], "stop_sale_vins": 0, "owners": 0}

### T-10 — plant_outage — PASS
> Princeton is down tomorrow for an emergency transformer swap. One day only.
- Read as: `plant_outage` (reader: rules)
- Stats: {"writes": 21, "calls": 21, "moved": 3, "rescheduled": 3, "transferred": 0, "expected_moves": 3, "dealers": 15, "loaners": 3, "lots": [], "stop_sale_vins": 0, "owners": 0}

### T-11 — quality_hold — PASS
> QUALITY BULLETIN QB-401: Lot LOT-0091 (SEAT-LEA, supplier SUP-04) installed at P_KY on vehicles built 2027-03-02 to 2027-03-03 has a stitching defect. Place the lot on hold, stop sale of unsold vehicles and contact owners.
- Read as: `quality_hold` (reader: rules)
- Stats: {"writes": 55, "calls": 55, "moved": 0, "rescheduled": 0, "transferred": 0, "expected_moves": 0, "dealers": 0, "loaners": 0, "lots": ["LOT-0091"], "stop_sale_vins": 26, "owners": 36}

### T-12 — quality_hold — PASS
> Quality alert: Redwood says the sliding doors sent to Huntsville have a cracked hinge. Anything built Thursday Feb 25 through Monday Mar 1 is suspect.
- Read as: `quality_hold` (reader: rules)
- Stats: {"writes": 73, "calls": 73, "moved": 0, "rescheduled": 0, "transferred": 0, "expected_moves": 0, "dealers": 0, "loaners": 0, "lots": ["LOT-0270"], "stop_sale_vins": 39, "owners": 51}

### T-13 — quality_hold — PASS
> Quality alert: Meridian says the leather seats sent to the Kentucky plant failed flammability testing. Anything built Monday Feb 22 through Monday Mar 1 is suspect.
- Edge: Build window spans two lots (LOT-0089 and LOT-0090). Expected: both lots held, vehicles from both windows.
- Read as: `quality_hold` (reader: rules)
- Stats: {"writes": 132, "calls": 132, "moved": 0, "rescheduled": 0, "transferred": 0, "expected_moves": 0, "dealers": 0, "loaners": 0, "lots": ["LOT-0089", "LOT-0090"], "stop_sale_vins": 78, "owners": 97}

### T-14 — unconfirmed — PASS
> QUALITY BULLETIN QB-999: Lot LOT-0999 installed at P_TX has a defect. Place the lot on hold.
- Read as: `unconfirmed` (reader: rules)
- Stats: {"writes": 0, "calls": 1}

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

### T-20 — unconfirmed — PASS
> Unverified social media post claims the Texas plant may shut down soon. No official word.
- Read as: `unconfirmed` (reader: rules)
- Stats: {"writes": 0, "calls": 1}

### T-21 — compound — PASS
> Morning digest, two items. (1) Huntsville update: a conveyor failure. We're dark from next Tuesday through next Thursday; the line restarts the following working day. (2) Lumen says the 60 kWh battery packs for Huntsville due next Monday will now arrive next Friday.
- Read as: `plant_outage+supplier_delay` (reader: rules, rules)
- Stats: {"writes": 70, "calls": 70, "moved": 10, "rescheduled": 10, "transferred": 0, "expected_moves": 10, "dealers": 34, "loaners": 26, "lots": [], "stop_sale_vins": 0, "owners": 0}

### T-22 — compound — PASS
> Digest. (1) QUALITY BULLETIN QB-410: Lot LOT-0143 (HARN-C, supplier SUP-05) installed at P_MS on vehicles built 2027-03-02 to 2027-03-03 has a short circuit. Place the lot on hold, stop sale of unsold vehicles and contact owners. (2) Jackson update: a power failure. We're dark from Monday Mar 22 through Tuesday Mar 23; the line restarts the following working day.
- Read as: `quality_hold+plant_outage` (reader: rules, rules)
- Stats: {"writes": 103, "calls": 103, "moved": 6, "rescheduled": 6, "transferred": 0, "expected_moves": 6, "dealers": 29, "loaners": 14, "lots": ["LOT-0143"], "stop_sale_vins": 23, "owners": 34}

### T-23 — compound — PASS
> Morning digest, two items. (1) Princeton update: a software outage on the line. We're dark from next Wednesday through next Thursday; the line restarts the following working day. (2) Rumor from a supplier rep: something may be off with tires coming up. No dates, no details, nothing confirmed.
- Edge: Real outage plus a rumor. Expected: outage actions, and the rumor part escalated.
- Read as: `plant_outage+unconfirmed` (reader: rules, rules)
- Stats: {"writes": 54, "calls": 55, "moved": 6, "rescheduled": 6, "transferred": 0, "expected_moves": 6, "dealers": 30, "loaners": 18, "lots": [], "stop_sale_vins": 0, "owners": 0}

### T-24 — compound — PASS
> Morning digest, two items. (1) The new brochure PDF is on the dealer portal. (2) Quick heads up from Atlas: the heavy-duty wiring harness run for Princeton can't make it Monday Mar 22. Carrier says Wednesday Mar 24 now (a customs inspection).
- Read as: `noise+supplier_delay` (reader: rules, rules)
- Stats: {"writes": 16, "calls": 16, "moved": 2, "rescheduled": 2, "transferred": 0, "expected_moves": 2, "dealers": 11, "loaners": 3, "lots": [], "stop_sale_vins": 0, "owners": 0}

### T-25 — plant_outage — PASS
> Lexingtn line is dark Monday Mar 15 through Tuesday Mar 16 due to a power failure; restarts the following working day.
- Edge: Typo in plant name ('Lexingtn'). Expected: still read as P_KY, or escalate rather than guess.
- Read as: `plant_outage` (reader: rules)
- Stats: {"writes": 52, "calls": 52, "moved": 6, "rescheduled": 6, "transferred": 0, "expected_moves": 6, "dealers": 29, "loaners": 17, "lots": [], "stop_sale_vins": 0, "owners": 0}

