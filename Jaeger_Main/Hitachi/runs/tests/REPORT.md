# Hitachi control tower — generated tests

100 cases from `tests/cases.json`, graded by `tests/run_cases.py` against expected effects computed from the CSVs (not from tower/graph.py).

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
| T-26 | quality_hold | PASS |  |
| T-27 | noise | PASS |  |
| T-28 | compound | PASS |  |
| T-29 | supplier_delay | PASS |  |
| T-30 | noise | PASS |  |
| T-31 | supplier_delay | PASS |  |
| T-32 | plant_outage | PASS |  |
| T-33 | noise | PASS |  |
| T-34 | compound | PASS |  |
| T-35 | supplier_delay | PASS |  |
| T-36 | noise | PASS |  |
| T-37 | unconfirmed | PASS |  |
| T-38 | unconfirmed | PASS |  |
| T-39 | quality_hold | PASS |  |
| T-40 | quality_hold | PASS |  |
| T-41 | supplier_delay | PASS ⚠ |  |
| T-42 | quality_hold | PASS |  |
| T-43 | supplier_delay | PASS |  |
| T-44 | compound | PASS |  |
| T-45 | unconfirmed | PASS |  |
| T-46 | unconfirmed | PASS |  |
| T-47 | plant_outage | PASS |  |
| T-48 | compound | PASS |  |
| T-49 | noise | PASS |  |
| T-50 | quality_hold | PASS |  |
| T-51 | supplier_delay | PASS |  |
| T-52 | plant_outage | PASS |  |
| T-53 | plant_outage | PASS |  |
| T-54 | noise | PASS |  |
| T-55 | unconfirmed | PASS |  |
| T-56 | plant_outage | PASS |  |
| T-57 | quality_hold | PASS |  |
| T-58 | plant_outage | PASS |  |
| T-59 | plant_outage | PASS |  |
| T-60 | supplier_delay | PASS |  |
| T-61 | supplier_delay | PASS |  |
| T-62 | plant_outage | PASS |  |
| T-63 | compound | PASS |  |
| T-64 | quality_hold | PASS |  |
| T-65 | quality_hold | PASS |  |
| T-66 | plant_outage | PASS |  |
| T-67 | noise | PASS |  |
| T-68 | compound | PASS |  |
| T-69 | quality_hold | PASS |  |
| T-70 | supplier_delay | PASS |  |
| T-71 | plant_outage | PASS |  |
| T-72 | plant_outage | PASS |  |
| T-73 | plant_outage | PASS |  |
| T-74 | quality_hold | PASS |  |
| T-75 | supplier_delay | PASS |  |
| T-76 | supplier_delay | PASS |  |
| T-77 | supplier_delay | PASS |  |
| T-78 | supplier_delay | PASS |  |
| T-79 | quality_hold | PASS |  |
| T-80 | supplier_delay | PASS |  |
| T-81 | unconfirmed | PASS |  |
| T-82 | quality_hold | PASS |  |
| T-83 | noise | PASS |  |
| T-84 | supplier_delay | PASS |  |
| T-85 | unconfirmed | PASS |  |
| T-86 | quality_hold | PASS |  |
| T-87 | compound | PASS |  |
| T-88 | quality_hold | PASS |  |
| T-89 | plant_outage | PASS |  |
| T-90 | noise | PASS |  |
| T-91 | plant_outage | PASS |  |
| T-92 | unconfirmed | PASS |  |
| T-93 | supplier_delay | PASS |  |
| T-94 | unconfirmed | PASS |  |
| T-95 | supplier_delay | PASS |  |
| T-96 | supplier_delay | PASS |  |
| T-97 | compound | PASS |  |
| T-98 | noise | PASS |  |
| T-99 | plant_outage | PASS |  |
| T-100 | plant_outage | PASS |  |

**rules**: 100/100 pass

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

### T-26 — quality_hold — PASS
> Quality alert: Volt says the harness C sent to P_TX had a faulty weld. Anything built 2027-03-04 through Friday Mar 5 is suspect.
- Read as: `quality_hold` (reader: rules)
- Stats: {"writes": 50, "calls": 50, "moved": 0, "rescheduled": 0, "transferred": 0, "expected_moves": 0, "dealers": 0, "loaners": 0, "lots": ["LOT-0024"], "stop_sale_vins": 25, "owners": 31}

### T-27 — noise — PASS
> Blizzard warning for Anchorage, AK through the weekend; schools closed.
- Read as: `noise` (reader: rules)
- Stats: {"writes": 0, "calls": 0}

### T-28 — compound — PASS
> Morning digest, two items. (1) OUTAGE Lexington: a compressor failure. Down Wed 3/24 - March 26, both days included. (2) quality issue - harness B from Atlas Wire and Cable at P_TX, a firmware fault. builds from Mon 2/22 to 2027-02-24 affected
- Read as: `plant_outage+quality_hold` (reader: rules, rules)
- Stats: {"writes": 194, "calls": 194, "moved": 9, "rescheduled": 9, "transferred": 0, "expected_moves": 9, "dealers": 33, "loaners": 21, "lots": ["LOT-0017"], "stop_sale_vins": 86, "owners": 94}

### T-29 — supplier_delay — PASS
> heads up, Atlas Wire and Cable says the HARN-B for San Antonio won't make 2027-03-15. new ETA Wednesday Mar 17 (a port backlog)
- Read as: `supplier_delay` (reader: rules)
- Stats: {"writes": 34, "calls": 34, "moved": 4, "rescheduled": 4, "transferred": 0, "expected_moves": 4, "dealers": 23, "loaners": 7, "lots": [], "stop_sale_vins": 0, "owners": 0}

### T-30 — noise — PASS
> Reminder: open enrollment for dental and vision closes Friday. Visit the HR portal.
- Read as: `noise` (reader: rules)
- Stats: {"writes": 0, "calls": 0}

### T-31 — supplier_delay — PASS
> Our 16-inch tires delivery to the Texas plant, originally scheduled for 2027-03-22, is pushed to Tuesday Mar 23 due to a port backlog. Apologies for the inconvenience. - Brightline Rubber
- Read as: `supplier_delay` (reader: rules)
- Stats: {"writes": 9, "calls": 9, "moved": 1, "rescheduled": 1, "transferred": 0, "expected_moves": 1, "dealers": 7, "loaners": 1, "lots": [], "stop_sale_vins": 0, "owners": 0}

### T-32 — plant_outage — PASS
> Plant operations alert: P_TX lost production to a software outage on the line. No builds on Mar 25; the line restarts the following working day.
- Read as: `plant_outage` (reader: rules)
- Stats: {"writes": 23, "calls": 23, "moved": 3, "rescheduled": 3, "transferred": 0, "expected_moves": 3, "dealers": 15, "loaners": 5, "lots": [], "stop_sale_vins": 0, "owners": 0}

### T-33 — noise — PASS
> Rival automaker announces a new electric pickup for 2029; no production details given.
- Read as: `noise` (reader: rules)
- Stats: {"writes": 0, "calls": 0}

### T-34 — compound — PASS
> Morning digest, two items. (1) P_AL line is waiting on 20-inch alloy wheel (WHEEL-20) from Ironwood. original drop was Mon 3/15, new ETA is next Friday because of a truck breakdown (2) Reminder: open enrollment for dental and vision closes Friday. Visit the HR portal.
- Read as: `supplier_delay+noise` (reader: rules, rules)
- Stats: {"writes": 41, "calls": 41, "moved": 4, "rescheduled": 4, "transferred": 0, "expected_moves": 4, "dealers": 24, "loaners": 13, "lots": [], "stop_sale_vins": 0, "owners": 0}

### T-35 — supplier_delay — PASS
> Our compact wiring harness delivery to Wacky Wheels San Antonio, originally scheduled for Monday Mar 22, is pushed to 2027-03-23 due to a customs inspection. Apologies for the inconvenience. - Volt Harness Systems
- Read as: `supplier_delay` (reader: rules)
- Stats: {"writes": 9, "calls": 9, "moved": 1, "rescheduled": 1, "transferred": 0, "expected_moves": 1, "dealers": 7, "loaners": 1, "lots": [], "stop_sale_vins": 0, "owners": 0}

### T-36 — noise — PASS
> The HQ parking garage level 2 is closed for painting this weekend.
- Read as: `noise` (reader: rules)
- Stats: {"writes": 0, "calls": 0}

### T-37 — unconfirmed — PASS
> not sure if this is real but people say the Texas plant could lose power sometime. no dates
- Read as: `unconfirmed` (reader: rules)
- Stats: {"writes": 0, "calls": 1}

### T-38 — unconfirmed — PASS
> We keep hearing rumors that some cars could be delayed. Is that true? Nobody has told us anything.
- Read as: `unconfirmed` (reader: rules)
- Stats: {"writes": 0, "calls": 1}

### T-39 — quality_hold — PASS
> QUALITY BULLETIN: Lot LOT-0054 (BRAKE-KIT, from Sentinel Brake and Airbag) installed at Wacky Wheels Lexington on vehicles built Thu 2/25 to last Monday has moisture contamination. Place the lot on hold, stop sale of unsold vehicles and contact owners.
- Read as: `quality_hold` (reader: rules)
- Stats: {"writes": 172, "calls": 172, "moved": 0, "rescheduled": 0, "transferred": 0, "expected_moves": 0, "dealers": 0, "loaners": 0, "lots": ["LOT-0054"], "stop_sale_vins": 125, "owners": 130}

### T-40 — quality_hold — PASS
> quality issue - infotainment chip from Quanta Silicon at the North Carolina plant, a cracked housing. builds from 2027-03-02 to 2027-03-03 affected
- Read as: `quality_hold` (reader: rules)
- Stats: {"writes": 99, "calls": 99, "moved": 0, "rescheduled": 0, "transferred": 0, "expected_moves": 0, "dealers": 0, "loaners": 0, "lots": ["LOT-0319"], "stop_sale_vins": 52, "owners": 66}

### T-41 — supplier_delay — PASS
> Shipment SH-0275 delayed. Original ETA Mar 22; revised ETA Mar 23. Part: standard wiring harness. Destination: Wacky Wheels Huntsville (P_AL). Supplier: Atlas.
- Read as: `supplier_delay` (reader: rules)
- Stats: {"writes": 7, "calls": 7, "moved": 1, "rescheduled": 1, "transferred": 0, "expected_moves": 1, "dealers": 6, "loaners": 0, "lots": [], "stop_sale_vins": 0, "owners": 0}
- warn: only 2 kind(s) of write action (handbook rule 9 wants 3)

### T-42 — quality_hold — PASS
> Please hold lot LOT-0008 immediately: a firmware fault found in brake kit from Sterling. Used at the Texas plant, builds March 4 through last Friday.
- Read as: `quality_hold` (reader: rules)
- Stats: {"writes": 133, "calls": 133, "moved": 0, "rescheduled": 0, "transferred": 0, "expected_moves": 0, "dealers": 0, "loaners": 0, "lots": ["LOT-0008"], "stop_sale_vins": 83, "owners": 96}

### T-43 — supplier_delay — PASS
> Our 17-inch alloy wheel (WHEEL-17) delivery to the Mississippi plant, originally scheduled for March 22, is pushed to 2027-03-25 due to a snowstorm on the route. Apologies for the inconvenience. - Cobalt Wheels (SUP-03)
- Read as: `supplier_delay` (reader: rules)
- Stats: {"writes": 50, "calls": 50, "moved": 6, "rescheduled": 6, "transferred": 0, "expected_moves": 6, "dealers": 30, "loaners": 14, "lots": [], "stop_sale_vins": 0, "owners": 0}

### T-44 — compound — PASS
> Morning digest, two items. (1) Wacky Wheels Huntsville (P_AL) update: a paint-shop fire. We're dark from Wed 3/10 through Friday Mar 12; the line restarts the following working day. (2) Hi, could someone resend the login for the dealer marketing portal? Thanks, Chattanooga store.
- Read as: `plant_outage+noise` (reader: rules, rules)
- Stats: {"writes": 60, "calls": 60, "moved": 9, "rescheduled": 9, "transferred": 0, "expected_moves": 9, "dealers": 34, "loaners": 17, "lots": [], "stop_sale_vins": 0, "owners": 0}

### T-45 — unconfirmed — PASS
> Supplier contact thinks there may be a quality issue with a part lot, but has no lot number or dates.
- Read as: `unconfirmed` (reader: rules)
- Stats: {"writes": 0, "calls": 1}

### T-46 — unconfirmed — PASS
> heard from a buddy at a supplier that something might be up with 20-inch alloy wheel. nothing official
- Read as: `unconfirmed` (reader: rules)
- Stats: {"writes": 0, "calls": 1}

### T-47 — plant_outage — PASS
> Plant operations alert: P_IN lost production to a power failure. Production is stopped from Mon 3/29 through 2027-03-30 inclusive.
- Read as: `plant_outage` (reader: rules)
- Stats: {"writes": 43, "calls": 43, "moved": 6, "rescheduled": 6, "transferred": 0, "expected_moves": 6, "dealers": 27, "loaners": 10, "lots": [], "stop_sale_vins": 0, "owners": 0}

### T-48 — compound — PASS
> Morning digest, two items. (1) San Antonio is down this Thursday only (a software outage on the line). back the next working day (2) Subject: SH-0248 late Lumen here. Shipment SH-0248 (60 kWh battery pack) for Huntsville was due Monday Mar 29 and will now arrive Fri 4/2. Reason: a tooling failure.
- Read as: `plant_outage+supplier_delay` (reader: rules, rules)
- Stats: {"writes": 49, "calls": 49, "moved": 7, "rescheduled": 5, "transferred": 2, "expected_moves": 7, "dealers": 30, "loaners": 12, "lots": [], "stop_sale_vins": 0, "owners": 0}

### T-49 — noise — PASS
> IT will patch laptops tonight at 9 pm. Save your work before you leave.
- Read as: `noise` (reader: rules)
- Stats: {"writes": 0, "calls": 0}

### T-50 — quality_hold — PASS
> QUALITY BULLETIN: Lot LOT-0333 (compact wiring harness, from Ridgeline) installed at Wacky Wheels Greensboro (P_NC) on vehicles built Feb 22 to 2027-02-24 has a stitching defect. Place the lot on hold, stop sale of unsold vehicles and contact owners.
- Read as: `quality_hold` (reader: rules)
- Stats: {"writes": 77, "calls": 77, "moved": 0, "rescheduled": 0, "transferred": 0, "expected_moves": 0, "dealers": 0, "loaners": 0, "lots": ["LOT-0333"], "stop_sale_vins": 50, "owners": 52}

### T-51 — supplier_delay — PASS
> Call from Meridian Seating: minivan seats shipment into P_AL slips from Mon 3/15 to next Thursday. Cause: a quality re-check at the supplier.
- Read as: `supplier_delay` (reader: rules)
- Stats: {"writes": 28, "calls": 28, "moved": 3, "rescheduled": 3, "transferred": 0, "expected_moves": 3, "dealers": 17, "loaners": 8, "lots": [], "stop_sale_vins": 0, "owners": 0}

### T-52 — plant_outage — PASS
> OUTAGE Wacky Wheels Huntsville (P_AL): flooding in the body shop. Down March 29 - March 30, both days included.
- Read as: `plant_outage` (reader: rules)
- Stats: {"writes": 40, "calls": 40, "moved": 6, "rescheduled": 6, "transferred": 0, "expected_moves": 6, "dealers": 24, "loaners": 10, "lots": [], "stop_sale_vins": 0, "owners": 0}

### T-53 — plant_outage — PASS
> Plant operations alert: Wacky Wheels Princeton (P_IN) lost production to a software outage on the line. No builds on Tue 3/16; the line restarts the following working day.
- Read as: `plant_outage` (reader: rules)
- Stats: {"writes": 28, "calls": 28, "moved": 3, "rescheduled": 3, "transferred": 0, "expected_moves": 3, "dealers": 15, "loaners": 10, "lots": [], "stop_sale_vins": 0, "owners": 0}

### T-54 — noise — PASS
> Dealer Nashville asks whether the spring brochure PDF has the new trim colors yet.
- Read as: `noise` (reader: rules)
- Stats: {"writes": 0, "calls": 0}

### T-55 — unconfirmed — PASS
> A carrier rep hinted deliveries could slip at some point. No dates, no part named, not confirmed.
- Read as: `unconfirmed` (reader: rules)
- Stats: {"writes": 0, "calls": 1}

### T-56 — plant_outage — PASS
> Wacky Wheels Jackson update: a conveyor breakdown. We're dark from Mar 26 through 2027-03-30; the line restarts the following working day.
- Read as: `plant_outage` (reader: rules)
- Stats: {"writes": 62, "calls": 62, "moved": 9, "rescheduled": 6, "transferred": 3, "expected_moves": 9, "dealers": 36, "loaners": 17, "lots": [], "stop_sale_vins": 0, "owners": 0}

### T-57 — quality_hold — PASS
> Please hold lot LOT-0283 immediately: a faulty weld found in HARN-C from Volt. Used at Huntsville, builds Tue 3/2 through Wed 3/3.
- Read as: `quality_hold` (reader: rules)
- Stats: {"writes": 50, "calls": 50, "moved": 0, "rescheduled": 0, "transferred": 0, "expected_moves": 0, "dealers": 0, "loaners": 0, "lots": ["LOT-0283"], "stop_sale_vins": 30, "owners": 31}

### T-58 — plant_outage — PASS
> Plant operations alert: Princeton lost production to a compressor failure. Production is stopped from Wed 3/24 through Monday Mar 29 inclusive.
- Read as: `plant_outage` (reader: rules)
- Stats: {"writes": 70, "calls": 70, "moved": 12, "rescheduled": 8, "transferred": 4, "expected_moves": 12, "dealers": 36, "loaners": 22, "lots": [], "stop_sale_vins": 0, "owners": 0}

### T-59 — plant_outage — PASS
> San Antonio update: a power failure. We're dark from 2027-03-23 through Friday Mar 26; the line restarts the following working day.
- Read as: `plant_outage` (reader: rules)
- Stats: {"writes": 75, "calls": 75, "moved": 12, "rescheduled": 10, "transferred": 2, "expected_moves": 12, "dealers": 35, "loaners": 28, "lots": [], "stop_sale_vins": 0, "owners": 0}

### T-60 — supplier_delay — PASS
> Our brake kit delivery to the Indiana plant, originally scheduled for 2027-03-22, is pushed to Thu 3/25 due to a quality re-check at the supplier. Apologies for the inconvenience. - Sentinel Brake and Airbag
- Read as: `supplier_delay` (reader: rules)
- Stats: {"writes": 44, "calls": 44, "moved": 6, "rescheduled": 6, "transferred": 0, "expected_moves": 6, "dealers": 26, "loaners": 12, "lots": [], "stop_sale_vins": 0, "owners": 0}

### T-61 — supplier_delay — PASS
> Call from Ridgeline Wire: HARN-C shipment into Wacky Wheels Princeton slips from Mon 3/22 to Tue 3/23. Cause: a port backlog.
- Read as: `supplier_delay` (reader: rules)
- Stats: {"writes": 11, "calls": 11, "moved": 1, "rescheduled": 1, "transferred": 0, "expected_moves": 1, "dealers": 8, "loaners": 2, "lots": [], "stop_sale_vins": 0, "owners": 0}

### T-62 — plant_outage — PASS
> OUTAGE the Indiana plant: a software outage on the line. Down next Monday - next Wednesday, both days included.
- Read as: `plant_outage` (reader: rules)
- Stats: {"writes": 63, "calls": 63, "moved": 9, "rescheduled": 9, "transferred": 0, "expected_moves": 9, "dealers": 29, "loaners": 25, "lots": [], "stop_sale_vins": 0, "owners": 0}

### T-63 — compound — PASS
> Morning digest, two items. (1) OUTAGE Wacky Wheels Lexington (P_KY): a robot cell crash. Down Wed 3/10 - Monday Mar 15, both days included. (2) Dealer Corpus Christi wants to know if we have posters of the new Summit model for the showroom.
- Read as: `plant_outage+noise` (reader: rules, rules)
- Stats: {"writes": 75, "calls": 75, "moved": 12, "rescheduled": 12, "transferred": 0, "expected_moves": 12, "dealers": 38, "loaners": 25, "lots": [], "stop_sale_vins": 0, "owners": 0}

### T-64 — quality_hold — PASS
> QUALITY BULLETIN: Lot LOT-0302 (17-inch alloy wheel (WHEEL-17), from Cobalt) installed at Wacky Wheels Huntsville on vehicles built Feb 25 to Mar 1 has a bad batch of resin. Place the lot on hold, stop sale of unsold vehicles and contact owners.
- Read as: `quality_hold` (reader: rules)
- Stats: {"writes": 122, "calls": 122, "moved": 0, "rescheduled": 0, "transferred": 0, "expected_moves": 0, "dealers": 0, "loaners": 0, "lots": ["LOT-0302"], "stop_sale_vins": 75, "owners": 96}

### T-65 — quality_hold — PASS
> Quality alert: Quanta Silicon says the infotainment chip (CHIP-IVI) sent to the Indiana plant had a faulty weld. Anything built February 25 through Mon 3/1 is suspect.
- Read as: `quality_hold` (reader: rules)
- Stats: {"writes": 137, "calls": 137, "moved": 0, "rescheduled": 0, "transferred": 0, "expected_moves": 0, "dealers": 0, "loaners": 0, "lots": ["LOT-0190"], "stop_sale_vins": 81, "owners": 99}

### T-66 — plant_outage — PASS
> OUTAGE Lexington: a gas leak evacuation. Down Wednesday Mar 24 - Thursday Mar 25, both days included.
- Read as: `plant_outage` (reader: rules)
- Stats: {"writes": 46, "calls": 46, "moved": 6, "rescheduled": 6, "transferred": 0, "expected_moves": 6, "dealers": 25, "loaners": 15, "lots": [], "stop_sale_vins": 0, "owners": 0}

### T-67 — noise — PASS
> anyone know if the cafeteria is doing tacos again on thursday? asking for the whole team
- Read as: `noise` (reader: rules)
- Stats: {"writes": 0, "calls": 0}

### T-68 — compound — PASS
> Morning digest, two items. (1) quality issue - 12-inch displays from Orbit Optics (SUP-11) at Wacky Wheels Greensboro (P_NC), a stitching defect. builds from March 4 to March 5 affected (2) heard from a buddy at a supplier that something might be up with cloth seat set. nothing official
- Read as: `quality_hold+unconfirmed` (reader: rules, rules)
- Stats: {"writes": 52, "calls": 53, "moved": 0, "rescheduled": 0, "transferred": 0, "expected_moves": 0, "dealers": 0, "loaners": 0, "lots": ["LOT-0324"], "stop_sale_vins": 36, "owners": 31}

### T-69 — quality_hold — PASS
> QUALITY BULLETIN: Lot LOT-0344 (compact-car rubber, from Granite Tire) installed at Wacky Wheels Greensboro on vehicles built March 4 to last Friday has moisture contamination. Place the lot on hold, stop sale of unsold vehicles and contact owners.
- Read as: `quality_hold` (reader: rules)
- Stats: {"writes": 59, "calls": 59, "moved": 0, "rescheduled": 0, "transferred": 0, "expected_moves": 0, "dealers": 0, "loaners": 0, "lots": ["LOT-0344"], "stop_sale_vins": 31, "owners": 35}

### T-70 — supplier_delay — PASS
> San Antonio line is waiting on 16-inch alloy wheel from Ironwood Wheels. original drop was Monday Mar 29, new ETA is 2027-04-01 because of a missed rail connection
- Read as: `supplier_delay` (reader: rules)
- Stats: {"writes": 28, "calls": 28, "moved": 3, "rescheduled": 3, "transferred": 0, "expected_moves": 3, "dealers": 19, "loaners": 6, "lots": [], "stop_sale_vins": 0, "owners": 0}

### T-71 — plant_outage — PASS
> Plant operations alert: the Mississippi plant lost production to a conveyor breakdown. No builds on March 19; the line restarts the following working day.
- Read as: `plant_outage` (reader: rules)
- Stats: {"writes": 31, "calls": 31, "moved": 3, "rescheduled": 3, "transferred": 0, "expected_moves": 3, "dealers": 21, "loaners": 7, "lots": [], "stop_sale_vins": 0, "owners": 0}

### T-72 — plant_outage — PASS
> Plant operations alert: Wacky Wheels Greensboro lost production to a power failure. Production is stopped from this Wednesday through Thu 3/11 inclusive.
- Read as: `plant_outage` (reader: rules)
- Stats: {"writes": 38, "calls": 38, "moved": 6, "rescheduled": 6, "transferred": 0, "expected_moves": 6, "dealers": 23, "loaners": 9, "lots": [], "stop_sale_vins": 0, "owners": 0}

### T-73 — plant_outage — PASS
> Due to a compressor failure, Wacky Wheels San Antonio will not build from March 23 to March 24 (inclusive). Restart the next working day.
- Read as: `plant_outage` (reader: rules)
- Stats: {"writes": 53, "calls": 53, "moved": 6, "rescheduled": 6, "transferred": 0, "expected_moves": 6, "dealers": 29, "loaners": 18, "lots": [], "stop_sale_vins": 0, "owners": 0}

### T-74 — quality_hold — PASS
> Quality alert: Meridian Seating says the cloth seat set (SEAT-FAB) sent to Wacky Wheels San Antonio (P_TX) had a cracked housing. Anything built Mon 2/22 through 2027-02-24 is suspect.
- Read as: `quality_hold` (reader: rules)
- Stats: {"writes": 120, "calls": 120, "moved": 0, "rescheduled": 0, "transferred": 0, "expected_moves": 0, "dealers": 0, "loaners": 0, "lots": ["LOT-0025"], "stop_sale_vins": 87, "owners": 86}

### T-75 — supplier_delay — PASS
> Our infotainment chip (CHIP-IVI) delivery to San Antonio, originally scheduled for Monday Mar 29, is pushed to Thursday Apr 1 due to a port backlog. Apologies for the inconvenience. - Kestrel Electronics
- Read as: `supplier_delay` (reader: rules)
- Stats: {"writes": 46, "calls": 46, "moved": 6, "rescheduled": 4, "transferred": 2, "expected_moves": 6, "dealers": 28, "loaners": 12, "lots": [], "stop_sale_vins": 0, "owners": 0}

### T-76 — supplier_delay — PASS
> Shipment SH-0228 delayed. Original ETA Monday Mar 29; revised ETA Thursday Apr 1. Part: 17-inch all-season tire (TIRE-17). Destination: Wacky Wheels Princeton. Supplier: Brightline Rubber (SUP-01).
- Read as: `supplier_delay` (reader: rules)
- Stats: {"writes": 52, "calls": 52, "moved": 6, "rescheduled": 4, "transferred": 2, "expected_moves": 6, "dealers": 30, "loaners": 16, "lots": [], "stop_sale_vins": 0, "owners": 0}

### T-77 — supplier_delay — PASS
> Subject: SH-0319 late Quanta Silicon here. Shipment SH-0319 (CHIP-IVI) for Wacky Wheels Greensboro (P_NC) was due 2027-03-22 and will now arrive 2027-03-25. Reason: a missed rail connection.
- Read as: `supplier_delay` (reader: rules)
- Stats: {"writes": 46, "calls": 46, "moved": 6, "rescheduled": 6, "transferred": 0, "expected_moves": 6, "dealers": 30, "loaners": 10, "lots": [], "stop_sale_vins": 0, "owners": 0}

### T-78 — supplier_delay — PASS
> Call from Cobalt Wheels: 20-inch rims shipment into P_NC slips from Mon 3/29 to April 2. Cause: a truck breakdown.
- Read as: `supplier_delay` (reader: rules)
- Stats: {"writes": 36, "calls": 36, "moved": 4, "rescheduled": 2, "transferred": 2, "expected_moves": 4, "dealers": 24, "loaners": 8, "lots": [], "stop_sale_vins": 0, "owners": 0}

### T-79 — quality_hold — PASS
> quality issue - airbag modules from Sentinel Brake and Airbag at Wacky Wheels Jackson (P_MS), a bad batch of resin. builds from February 25 to 2027-03-01 affected
- Read as: `quality_hold` (reader: rules)
- Stats: {"writes": 188, "calls": 188, "moved": 0, "rescheduled": 0, "transferred": 0, "expected_moves": 0, "dealers": 0, "loaners": 0, "lots": ["LOT-0114"], "stop_sale_vins": 110, "owners": 150}

### T-80 — supplier_delay — PASS
> P_KY line is waiting on SEAT-FAB from Harbor Seating. original drop was Monday Mar 29, new ETA is Mar 30 because of a quality re-check at the supplier
- Read as: `supplier_delay` (reader: rules)
- Stats: {"writes": 10, "calls": 10, "moved": 1, "rescheduled": 1, "transferred": 0, "expected_moves": 1, "dealers": 8, "loaners": 1, "lots": [], "stop_sale_vins": 0, "owners": 0}

### T-81 — unconfirmed — PASS
> Someone said the Texas plant might have a problem soon? Can't confirm, no details.
- Read as: `unconfirmed` (reader: rules)
- Stats: {"writes": 0, "calls": 1}

### T-82 — quality_hold — PASS
> Please hold lot LOT-0153 immediately: a stitching defect found in compact-car rubber from Brightline Rubber. Used at Wacky Wheels Jackson, builds 2027-02-22 through Wed 2/24.
- Read as: `quality_hold` (reader: rules)
- Stats: {"writes": 66, "calls": 66, "moved": 0, "rescheduled": 0, "transferred": 0, "expected_moves": 0, "dealers": 0, "loaners": 0, "lots": ["LOT-0153"], "stop_sale_vins": 37, "owners": 44}

### T-83 — noise — PASS
> Heat advisory issued for Phoenix, AZ; temperatures may reach 105 F.
- Read as: `noise` (reader: rules)
- Stats: {"writes": 0, "calls": 0}

### T-84 — supplier_delay — PASS
> P_KY line is waiting on 20-inch all-season tire from Brightline Rubber (SUP-01). original drop was Mon 3/22, new ETA is 2027-03-24 because of a missed rail connection
- Read as: `supplier_delay` (reader: rules)
- Stats: {"writes": 20, "calls": 20, "moved": 2, "rescheduled": 2, "transferred": 0, "expected_moves": 2, "dealers": 15, "loaners": 3, "lots": [], "stop_sale_vins": 0, "owners": 0}

### T-85 — unconfirmed — PASS
> heard from a buddy at a supplier that something might be up with minivan seat set. nothing official
- Read as: `unconfirmed` (reader: rules)
- Stats: {"writes": 0, "calls": 1}

### T-86 — quality_hold — PASS
> quality issue - DISPLAY-12 from Kestrel Electronics (SUP-06) at Jackson, moisture contamination. builds from Thu 2/25 to Monday Mar 1 affected
- Read as: `quality_hold` (reader: rules)
- Stats: {"writes": 126, "calls": 126, "moved": 0, "rescheduled": 0, "transferred": 0, "expected_moves": 0, "dealers": 0, "loaners": 0, "lots": ["LOT-0134"], "stop_sale_vins": 74, "owners": 90}

### T-87 — compound — PASS
> Morning digest, two items. (1) Our CAM-360 delivery to Wacky Wheels Princeton (P_IN), originally scheduled for March 29, is pushed to March 30 due to a port backlog. Apologies for the inconvenience. - Orbit Optics (SUP-11) (2) Someone said the Alabama plant might have a problem soon? Can't confirm, no details.
- Read as: `supplier_delay+unconfirmed` (reader: rules, rules)
- Stats: {"writes": 10, "calls": 11, "moved": 1, "rescheduled": 1, "transferred": 0, "expected_moves": 1, "dealers": 8, "loaners": 1, "lots": [], "stop_sale_vins": 0, "owners": 0}

### T-88 — quality_hold — PASS
> Quality alert: Lumen Cells (SUP-18) says the 60 kWh battery pack sent to P_AL had a faulty weld. Anything built Feb 22 through Feb 24 is suspect.
- Read as: `quality_hold` (reader: rules)
- Stats: {"writes": 77, "calls": 77, "moved": 0, "rescheduled": 0, "transferred": 0, "expected_moves": 0, "dealers": 0, "loaners": 0, "lots": ["LOT-0245"], "stop_sale_vins": 39, "owners": 53}

### T-89 — plant_outage — PASS
> the Kentucky plant update: a paint-shop fire. We're dark from Mar 26 through Tue 3/30; the line restarts the following working day.
- Read as: `plant_outage` (reader: rules)
- Stats: {"writes": 54, "calls": 54, "moved": 9, "rescheduled": 6, "transferred": 3, "expected_moves": 9, "dealers": 29, "loaners": 16, "lots": [], "stop_sale_vins": 0, "owners": 0}

### T-90 — noise — PASS
> Dealer Oklahoma City wants to know if we have posters of the new Summit model for the showroom.
- Read as: `noise` (reader: rules)
- Stats: {"writes": 0, "calls": 0}

### T-91 — plant_outage — PASS
> OUTAGE Wacky Wheels Greensboro: a compressor failure. Down Thu 3/11 - next Tuesday, both days included.
- Read as: `plant_outage` (reader: rules)
- Stats: {"writes": 70, "calls": 70, "moved": 12, "rescheduled": 12, "transferred": 0, "expected_moves": 12, "dealers": 37, "loaners": 21, "lots": [], "stop_sale_vins": 0, "owners": 0}

### T-92 — unconfirmed — PASS
> rumor on the floor: possible shortage of something for the paint line. unverified
- Read as: `unconfirmed` (reader: rules)
- Stats: {"writes": 0, "calls": 1}

### T-93 — supplier_delay — PASS
> Subject: SH-0258 late Quanta Silicon here. Shipment SH-0258 (driver-assist chips) for Wacky Wheels Huntsville (P_AL) was due Mon 3/15 and will now arrive next Thursday. Reason: a truck breakdown.
- Read as: `supplier_delay` (reader: rules)
- Stats: {"writes": 28, "calls": 28, "moved": 3, "rescheduled": 3, "transferred": 0, "expected_moves": 3, "dealers": 20, "loaners": 5, "lots": [], "stop_sale_vins": 0, "owners": 0}

### T-94 — unconfirmed — PASS
> heard from a buddy at a supplier that something might be up with leather seat set. nothing official
- Read as: `unconfirmed` (reader: rules)
- Stats: {"writes": 0, "calls": 1}

### T-95 — supplier_delay — PASS
> Subject: SH-0278 late Ridgeline Wire (SUP-16) here. Shipment SH-0278 (HARN-B) for Huntsville was due Monday Mar 15 and will now arrive Mar 16. Reason: a tooling failure.
- Read as: `supplier_delay` (reader: rules)
- Stats: {"writes": 14, "calls": 14, "moved": 1, "rescheduled": 1, "transferred": 0, "expected_moves": 1, "dealers": 9, "loaners": 4, "lots": [], "stop_sale_vins": 0, "owners": 0}

### T-96 — supplier_delay — PASS
> Our compact wiring harness delivery to San Antonio, originally scheduled for Monday Mar 22, is pushed to 2027-03-24 due to a quality re-check at the supplier. Apologies for the inconvenience. - Volt Harness Systems (SUP-05)
- Read as: `supplier_delay` (reader: rules)
- Stats: {"writes": 18, "calls": 18, "moved": 2, "rescheduled": 2, "transferred": 0, "expected_moves": 2, "dealers": 13, "loaners": 3, "lots": [], "stop_sale_vins": 0, "owners": 0}

### T-97 — compound — PASS
> Morning digest, two items. (1) Due to a software outage on the line, Jackson will not build from next Friday to March 24 (inclusive). Restart the next working day. (2) Quality alert: Kestrel says the 12-inch display sent to Wacky Wheels Huntsville (P_AL) had loose connectors. Anything built Tuesday Mar 2 through March 3 is suspect.
- Read as: `plant_outage+quality_hold` (reader: rules, rules)
- Stats: {"writes": 136, "calls": 136, "moved": 12, "rescheduled": 12, "transferred": 0, "expected_moves": 12, "dealers": 40, "loaners": 26, "lots": ["LOT-0267"], "stop_sale_vins": 22, "owners": 41}

### T-98 — noise — PASS
> Thank-you note from the Austin dealer for the holiday gift basket.
- Read as: `noise` (reader: rules)
- Stats: {"writes": 0, "calls": 0}

### T-99 — plant_outage — PASS
> Wacky Wheels San Antonio (P_TX) update: a gas leak evacuation. We're dark from Mon 3/15 through next Tuesday; the line restarts the following working day.
- Read as: `plant_outage` (reader: rules)
- Stats: {"writes": 52, "calls": 52, "moved": 6, "rescheduled": 6, "transferred": 0, "expected_moves": 6, "dealers": 33, "loaners": 13, "lots": [], "stop_sale_vins": 0, "owners": 0}

### T-100 — plant_outage — PASS
> Plant operations alert: P_KY lost production to flooding in the body shop. Production is stopped from 2027-03-11 through Mar 12 inclusive.
- Read as: `plant_outage` (reader: rules)
- Stats: {"writes": 48, "calls": 48, "moved": 6, "rescheduled": 6, "transferred": 0, "expected_moves": 6, "dealers": 31, "loaners": 11, "lots": [], "stop_sale_vins": 0, "owners": 0}

