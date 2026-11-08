# Given test cases — the 15 events in `data/events.json`

Each event is graded twice:

1. **Effects**: the action log is compared with hand-written expected answers (`tests/given_cases.json`) by the independent CSV grader in `tests/run_cases.py`. It checks the right orders moved and no others, slots after the disruption, transfers only when the home plant is full, one notice per dealer with exactly its orders, loaners by tier, priority and pool, the lots held, stop-sale VINs and owners notified.
2. **Evidence**: the graph path, reasons and action kinds the docx asks for per test case.

## Summary by docx test case

| Test case | Events | rules: effects | qwen2.5:0.5b: effects | qwen3:0.6b: effects | qwen3:1.7b: effects | Evidence | Required evidence |
|---|---|---|---|---|---|---|---|
| TC1 Supplier Delay | E-09, E-10, E-12 | 3/3 | 3/3 | 3/3 | 3/3 | ✅ | Shipment → Part → Model (BOM) → ProductionOrder → CustomerOrder → Dealer / Customer |
| TC2 Plant Outage | E-04, E-08, E-11 | 3/3 | 3/3 | 3/3 | 3/3 | ✅ | Plant → ProductionOrder → CustomerOrder → Dealer / Customer |
| TC3 Quality Hold | E-03, E-14, E-15 | 3/3 | 3/3 | 3/3 | 3/3 | ✅ | Lot → ProductionOrder → Vehicle → Dealer / Customer |
| TC4 Noise | E-05, E-06, E-07 | 3/3 | 3/3 | 3/3 | 3/3 | ✅ | the reason the event was judged not relevant |
| TC5 Compound Incident | E-01 | 1/1 | 1/1 | 1/1 | 1/1 | ✅ | one graph path per incident |
| TC6 Unconfirmed Report | E-02, E-13 | 2/2 | 2/2 | 2/2 | 2/2 | ✅ | the reason the report was not actionable |

- **rules**: 15/15 events pass on effects · 768 tool calls · 0 failed
- **qwen2.5:0.5b**: 15/15 events pass on effects · 768 tool calls · 0 failed
- **qwen3:0.6b**: 15/15 events pass on effects · 768 tool calls · 0 failed
- **qwen3:1.7b**: 15/15 events pass on effects · 768 tool calls · 0 failed

## Details — rules reader

### E-01 — TC5 Compound Incident — PASS
> Morning digest, two items. (1) San Antonio update: a software outage on the line. We're dark from next Friday through Monday Mar 22; the line restarts the following working day. (2) Quick heads up from Quanta: the infotainment chip run for Princeton can't make it next Monday. Carrier says next Friday now (severe weather on the route).

- **Read as:** `plant_outage+supplier_delay` (reader: rules, rules)
  - plant_outage: `{"plant_id": "P_TX", "outage_start": "2027-03-19", "outage_end": "2027-03-22"}`
  - supplier_delay: `{"supplier_id": "SUP-12", "part_id": "CHIP-IVI", "plant_id": "P_IN", "shipment_id": "SH-0190", "blocked_from": "2027-03-15", "blocked_until": "2027-03-19"}`
- **Expected:** [{"kind": "plant_outage", "plant_id": "P_TX", "outage_start": "2027-03-19", "outage_end": "2027-03-22"}, {"kind": "supplier_delay", "supplier_id": "SUP-12", "part_id": "CHIP-IVI", "plant_id": "P_IN", "blocked_from": "2027-03-15", "blocked_until": "2027-03-19"}]; escalate=false
- **Calls:** {'mes.reschedule': 14, 'dealer.notify': 41, 'crm.assign_loaner': 26}
- ✅ summary and reason recorded
- ✅ no failed tool calls
- ✅ outage path Plant → PO → CO → Dealer / Customer
- ✅ delay path for the second incident
- ✅ ≥3 kinds of action (rule 9): 3
- **Graph path (1 of 96):** Plant P_TX → ProductionOrder PO-0058 → CustomerOrder CO-00247 → Dealer D18 / Customer C6387
- **Summary:** The message reports a plant outage at Wacky Wheels San Antonio (P_TX) from 2027-03-19 through 2027-03-22 and a supplier delay of infotainment chip (CHIP-IVI) from Quanta Silicon (SUP-12) into Wacky Wheels Princeton (P_IN) from 2027-03-15 until 2027-03-19 on shipment SH-0190. Affected records: 14 production orders and 122 customer orders. The tower completed 14 reschedules, 41 dealer notices, and 26 loaner assignments.

### E-02 — TC6 Unconfirmed Report — PASS
> Rumor from a supplier rep: something may be off with a seat material coming up. No dates, no details, nothing confirmed.

- **Read as:** `unconfirmed` (reader: rules)
  - unconfirmed: `{}`
- **Expected:** no incident; escalate=true
- **Calls:** {'escalate': 1}
- ✅ summary and reason recorded
- ✅ no failed tool calls
- ✅ escalate only, no writes
- ✅ escalation gives a reason
- **Summary:** The report is not safe to act on because it is unconfirmed (nothing confirmed, rumor, may be off, no dates) and does not name a specific shipment, outage, or lot to change. No operational records were changed. The tower escalated the report and wrote nothing else.

### E-03 — TC3 Quality Hold — PASS
> Quality alert: Kestrel says the infotainment chip sent to Jackson had a faulty weld. Anything built Thursday Feb 25 through last Monday is suspect.

- **Read as:** `quality_hold` (reader: rules)
  - quality_hold: `{"supplier_id": "SUP-06", "part_id": "CHIP-IVI", "plant_id": "P_MS", "build_start": "2027-02-25", "build_end": "2027-03-01"}`
- **Expected:** [{"kind": "quality_hold", "lots": ["LOT-0130"]}]; escalate=false
- **Calls:** {'quality.hold_lot': 1, 'dealer.stop_sale': 37, 'crm.notify_customer': 150}
- ✅ summary and reason recorded
- ✅ no failed tool calls
- ✅ lot path Lot → PO → Vehicle → Dealer / Customer
- ✅ ≥3 kinds of action (rule 9): 3
- **Graph path (1 of 32):** Lot LOT-0130 → Part CHIP-IVI → Supplier SUP-06 → Plant P_MS
- **Summary:** The message reports a quality hold on infotainment chip (CHIP-IVI) at Wacky Wheels Jackson (P_MS) for builds 2027-02-25 through 2027-03-01. Affected records: 261 quality records. The tower completed 1 lot hold, 37 stop-sales, and 150 customer notices.

### E-04 — TC2 Plant Outage — PASS
> The Kentucky plant update: a software outage on the line. We're dark from next Tuesday through next Thursday; the line restarts the following working day.

- **Read as:** `plant_outage` (reader: rules)
  - plant_outage: `{"plant_id": "P_KY", "outage_start": "2027-03-16", "outage_end": "2027-03-18"}`
- **Expected:** [{"kind": "plant_outage", "plant_id": "P_KY", "outage_start": "2027-03-16", "outage_end": "2027-03-18"}]; escalate=false
- **Calls:** {'mes.reschedule': 9, 'dealer.notify': 32, 'crm.assign_loaner': 18}
- ✅ summary and reason recorded
- ✅ no failed tool calls
- ✅ outage path Plant → PO → CO → Dealer / Customer
- ✅ ≥3 kinds of action (rule 9): 3
- **Graph path (1 of 64):** Plant P_KY → ProductionOrder PO-0139 → CustomerOrder CO-00717 → Dealer D42 / Customer C5240
- **Summary:** The message reports a plant outage at Wacky Wheels Lexington (P_KY) from 2027-03-16 through 2027-03-18. Affected records: 9 production orders and 79 customer orders. The tower completed 9 reschedules, 32 dealer notices, and 18 loaner assignments.

### E-05 — TC4 Noise — PASS
> Dealer Amarillo, TX asks where to find the new brochure PDF.

- **Read as:** `noise` (reader: rules)
  - noise: `{}`
- **Expected:** no incident; escalate=false
- **Calls:** none
- ✅ summary and reason recorded
- ✅ no failed tool calls
- ✅ no calls at all
- **Summary:** "Dealer Amarillo, TX asks where to find the new brochure PDF" is not an operational disruption because it does not report a supplier delay, a plant outage, or a quality hold. No operational records are affected. Nothing was written.

### E-06 — TC4 Noise — PASS
> Dealer Little Rock, AR asks where to find the new brochure PDF.

- **Read as:** `noise` (reader: rules)
  - noise: `{}`
- **Expected:** no incident; escalate=false
- **Calls:** none
- ✅ summary and reason recorded
- ✅ no failed tool calls
- ✅ no calls at all
- **Summary:** "Dealer Little Rock, AR asks where to find the new brochure PDF" is not an operational disruption because it does not report a supplier delay, a plant outage, or a quality hold. No operational records are affected. Nothing was written.

### E-07 — TC4 Noise — PASS
> Dealer Pensacola, FL asks where to find the new brochure PDF.

- **Read as:** `noise` (reader: rules)
  - noise: `{}`
- **Expected:** no incident; escalate=false
- **Calls:** none
- ✅ summary and reason recorded
- ✅ no failed tool calls
- ✅ no calls at all
- **Summary:** "Dealer Pensacola, FL asks where to find the new brochure PDF" is not an operational disruption because it does not report a supplier delay, a plant outage, or a quality hold. No operational records are affected. Nothing was written.

### E-08 — TC2 Plant Outage — PASS
> Plant operations alert: Wacky Wheels Lexington (P_KY) lost production to a power failure. Production is stopped from 2027-03-24 through 2027-03-25 inclusive.

- **Read as:** `plant_outage` (reader: rules)
  - plant_outage: `{"plant_id": "P_KY", "outage_start": "2027-03-24", "outage_end": "2027-03-25"}`
- **Expected:** [{"kind": "plant_outage", "plant_id": "P_KY", "outage_start": "2027-03-24", "outage_end": "2027-03-25"}]; escalate=false
- **Calls:** {'mes.reschedule': 6, 'dealer.notify': 25, 'crm.assign_loaner': 15}
- ✅ summary and reason recorded
- ✅ no failed tool calls
- ✅ outage path Plant → PO → CO → Dealer / Customer
- ✅ ≥3 kinds of action (rule 9): 3
- **Graph path (1 of 64):** Plant P_KY → ProductionOrder PO-0157 → CustomerOrder CO-00876 → Dealer D07 / Customer C5020
- **Summary:** The message reports a plant outage at Wacky Wheels Lexington (P_KY) from 2027-03-24 through 2027-03-25. Affected records: 6 production orders and 56 customer orders. The tower completed 6 reschedules, 25 dealer notices, and 15 loaner assignments.

### E-09 — TC1 Supplier Delay — PASS
> Quick heads up from Orbit: the surround-view cameras run for Huntsville can't make it Monday Mar 29. Carrier says Thursday Apr 1 now (a customs inspection).

- **Read as:** `supplier_delay` (reader: rules)
  - supplier_delay: `{"supplier_id": "SUP-11", "part_id": "CAM-360", "plant_id": "P_AL", "shipment_id": "SH-0256", "blocked_from": "2027-03-29", "blocked_until": "2027-04-01"}`
- **Expected:** [{"kind": "supplier_delay", "supplier_id": "SUP-11", "part_id": "CAM-360", "plant_id": "P_AL", "blocked_from": "2027-03-29", "blocked_until": "2027-04-01"}]; escalate=false
- **Calls:** {'mes.reschedule': 4, 'mes.transfer': 2, 'dealer.notify': 26, 'crm.assign_loaner': 10}
- ✅ summary and reason recorded
- ✅ no failed tool calls
- ✅ graph path starts at the Shipment
- ✅ ≥3 kinds of action (rule 9): 4
- **Graph path (1 of 64):** Shipment SH-0256 → Part CAM-360 → Model SUMMIT (BOM) → Plant P_AL → ProductionOrder PO-0436 → CustomerOrder CO-02567 → Dealer D25 / Customer C1467
- **Summary:** The message reports a supplier delay of surround-view camera kit (CAM-360) from Orbit Optics (SUP-11) into Wacky Wheels Huntsville (P_AL) from 2027-03-29 until 2027-04-01 on shipment SH-0256. Affected records: 6 production orders and 54 customer orders. The tower completed 4 reschedules, 2 transfers, 26 dealer notices, and 10 loaner assignments.

### E-10 — TC1 Supplier Delay — PASS
> Huntsville line is waiting on 60 kWh battery packs from Lumen. Original drop was Monday Mar 29, new ETA is Thursday Apr 1 because of a truck breakdown.

- **Read as:** `supplier_delay` (reader: rules)
  - supplier_delay: `{"supplier_id": "SUP-18", "part_id": "BATT-60", "plant_id": "P_AL", "shipment_id": "SH-0248", "blocked_from": "2027-03-29", "blocked_until": "2027-04-01"}`
- **Expected:** [{"kind": "supplier_delay", "supplier_id": "SUP-18", "part_id": "BATT-60", "plant_id": "P_AL", "blocked_from": "2027-03-29", "blocked_until": "2027-04-01"}]; escalate=false
- **Calls:** {'mes.reschedule': 3, 'dealer.notify': 18, 'crm.assign_loaner': 7}
- ✅ summary and reason recorded
- ✅ no failed tool calls
- ✅ graph path starts at the Shipment
- ✅ ≥3 kinds of action (rule 9): 3
- **Graph path (1 of 58):** Shipment SH-0248 → Part BATT-60 → Model NOVA (BOM) → Plant P_AL → ProductionOrder PO-0437 → CustomerOrder CO-02575 → Dealer D04 / Customer C6785
- **Summary:** The message reports a supplier delay of 60 kWh battery pack (BATT-60) from Lumen Cells (SUP-18) into Wacky Wheels Huntsville (P_AL) from 2027-03-29 until 2027-04-01 on shipment SH-0248. Affected records: 3 production orders and 29 customer orders. The tower completed 3 reschedules, 18 dealer notices, and 7 loaner assignments.

### E-11 — TC2 Plant Outage — PASS
> Jackson update: a power failure. We're dark from Friday Mar 26 through Tuesday Mar 30; the line restarts the following working day.

- **Read as:** `plant_outage` (reader: rules)
  - plant_outage: `{"plant_id": "P_MS", "outage_start": "2027-03-26", "outage_end": "2027-03-30"}`
- **Expected:** [{"kind": "plant_outage", "plant_id": "P_MS", "outage_start": "2027-03-26", "outage_end": "2027-03-30"}]; escalate=false
- **Calls:** {'mes.reschedule': 6, 'mes.transfer': 3, 'dealer.notify': 36, 'crm.assign_loaner': 17}
- ✅ summary and reason recorded
- ✅ no failed tool calls
- ✅ outage path Plant → PO → CO → Dealer / Customer
- ✅ ≥3 kinds of action (rule 9): 4
- **Graph path (1 of 64):** Plant P_MS → ProductionOrder PO-0253 → CustomerOrder CO-01460 → Dealer D02 / Customer C5325
- **Summary:** The message reports a plant outage at Wacky Wheels Jackson (P_MS) from 2027-03-26 through 2027-03-30. Affected records: 9 production orders and 79 customer orders. The tower completed 6 reschedules, 3 transfers, 36 dealer notices, and 17 loaner assignments.

### E-12 — TC1 Supplier Delay — PASS
> Subject: Shipment SH-0182 delayed
From: dispatch@orbit.example

Our shipment SH-0182 of CAM-360 (surround-view camera kit) for Wacky Wheels Princeton (P_IN) was due 2027-03-15 and will now arrive 2027-03-18. Reason: port congestion.

- **Read as:** `supplier_delay` (reader: rules)
  - supplier_delay: `{"supplier_id": "SUP-11", "part_id": "CAM-360", "plant_id": "P_IN", "shipment_id": "SH-0182", "blocked_from": "2027-03-15", "blocked_until": "2027-03-18"}`
- **Expected:** [{"kind": "supplier_delay", "supplier_id": "SUP-11", "part_id": "CAM-360", "plant_id": "P_IN", "shipment_id": "SH-0182", "blocked_from": "2027-03-15", "blocked_until": "2027-03-18"}]; escalate=false
- **Calls:** {'mes.reschedule': 3, 'dealer.notify': 14, 'crm.assign_loaner': 10}
- ✅ summary and reason recorded
- ✅ no failed tool calls
- ✅ graph path starts at the Shipment
- ✅ ≥3 kinds of action (rule 9): 3
- **Graph path (1 of 52):** Shipment SH-0182 → Part CAM-360 → Model VOYAGER (BOM) → Plant P_IN → ProductionOrder PO-0316 → CustomerOrder CO-01756 → Dealer D07 / Customer C4130
- **Summary:** The message reports a supplier delay of surround-view camera kit (CAM-360) from Orbit Optics (SUP-11) into Wacky Wheels Princeton (P_IN) from 2027-03-15 until 2027-03-18 on shipment SH-0182. Affected records: 3 production orders and 26 customer orders. The tower completed 3 reschedules, 14 dealer notices, and 10 loaner assignments.

### E-13 — TC6 Unconfirmed Report — PASS
> Someone on the floor mentioned a possible shortage of something electronic sometime soon. Not confirmed by anyone.

- **Read as:** `unconfirmed` (reader: rules)
  - unconfirmed: `{}`
- **Expected:** no incident; escalate=true
- **Calls:** {'escalate': 1}
- ✅ summary and reason recorded
- ✅ no failed tool calls
- ✅ escalate only, no writes
- ✅ escalation gives a reason
- **Summary:** The report is not safe to act on because it is unconfirmed (not confirmed, someone on the floor mentioned, someone on the floor) and does not name a specific shipment, outage, or lot to change. No operational records were changed. The tower escalated the report and wrote nothing else.

### E-14 — TC3 Quality Hold — PASS
> Quality alert: Atlas says the heavy-duty wiring harness sent to the Texas plant had a moisture contamination. Anything built Monday Feb 22 through Wednesday Feb 24 is suspect.

- **Read as:** `quality_hold` (reader: rules)
  - quality_hold: `{"supplier_id": "SUP-07", "part_id": "HARN-B", "plant_id": "P_TX", "build_start": "2027-02-22", "build_end": "2027-02-24"}`
- **Expected:** [{"kind": "quality_hold", "lots": ["LOT-0017"]}]; escalate=false
- **Calls:** {'quality.hold_lot': 1, 'dealer.stop_sale': 36, 'crm.notify_customer': 94}
- ✅ summary and reason recorded
- ✅ no failed tool calls
- ✅ lot path Lot → PO → Vehicle → Dealer / Customer
- ✅ ≥3 kinds of action (rule 9): 3
- **Graph path (1 of 32):** Lot LOT-0017 → Part HARN-B → Supplier SUP-07 → Plant P_TX
- **Summary:** The message reports a quality hold on heavy-duty wiring harness (HARN-B) at Wacky Wheels San Antonio (P_TX) for builds 2027-02-22 through 2027-02-24. Affected records: 181 quality records. The tower completed 1 lot hold, 36 stop-sales, and 94 customer notices.

### E-15 — TC3 Quality Hold — PASS
> QUALITY BULLETIN QB-368: Lot LOT-0191 (CHIP-IVI, supplier SUP-12) installed at P_IN on vehicles built 2027-03-02 to 2027-03-03 has a faulty weld. Place the lot on hold, stop sale of unsold vehicles and contact owners.

- **Read as:** `quality_hold` (reader: rules)
  - quality_hold: `{"supplier_id": "SUP-12", "part_id": "CHIP-IVI", "plant_id": "P_IN", "lot_id": "LOT-0191", "build_start": "2027-03-02", "build_end": "2027-03-03"}`
- **Expected:** [{"kind": "quality_hold", "lots": ["LOT-0191"]}]; escalate=false
- **Calls:** {'quality.hold_lot': 1, 'dealer.stop_sale': 25, 'crm.notify_customer': 76}
- ✅ summary and reason recorded
- ✅ no failed tool calls
- ✅ lot path Lot → PO → Vehicle → Dealer / Customer
- ✅ ≥3 kinds of action (rule 9): 3
- **Graph path (1 of 32):** Lot LOT-0191 → Part CHIP-IVI → Supplier SUP-12 → Plant P_IN
- **Summary:** The message reports a quality hold on lot LOT-0191 at Wacky Wheels Princeton (P_IN) for builds 2027-03-02 through 2027-03-03. Affected records: 117 quality records. The tower completed 1 lot hold, 25 stop-sales, and 76 customer notices.

## Details — qwen2.5:0.5b reader

### E-01 — TC5 Compound Incident — PASS
> Morning digest, two items. (1) San Antonio update: a software outage on the line. We're dark from next Friday through Monday Mar 22; the line restarts the following working day. (2) Quick heads up from Quanta: the infotainment chip run for Princeton can't make it next Monday. Carrier says next Friday now (severe weather on the route).

- **Read as:** `plant_outage+supplier_delay` (reader: rules, rules)
  - plant_outage: `{"plant_id": "P_TX", "outage_start": "2027-03-19", "outage_end": "2027-03-22", "model_reason": "qwen2.5:0.5b: unconfirmed: a possible problem that nobody has confirmed (hearsay, guesses, vague reports without specifics)"}`
  - supplier_delay: `{"supplier_id": "SUP-12", "part_id": "CHIP-IVI", "plant_id": "P_IN", "shipment_id": "SH-0190", "blocked_from": "2027-03-15", "blocked_until": "2027-03-19", "model_reason": "qwen2.5:0.5b: The message reports that the infotainment chip for Princeton's vehicles cannot be delivered on time, and that the carrier is advising that it will be delivered next Friday."}`
- **Expected:** [{"kind": "plant_outage", "plant_id": "P_TX", "outage_start": "2027-03-19", "outage_end": "2027-03-22"}, {"kind": "supplier_delay", "supplier_id": "SUP-12", "part_id": "CHIP-IVI", "plant_id": "P_IN", "blocked_from": "2027-03-15", "blocked_until": "2027-03-19"}]; escalate=false
- **Calls:** {'mes.reschedule': 14, 'dealer.notify': 41, 'crm.assign_loaner': 26}
- ✅ summary and reason recorded
- ✅ no failed tool calls
- ✅ outage path Plant → PO → CO → Dealer / Customer
- ✅ delay path for the second incident
- ✅ ≥3 kinds of action (rule 9): 3
- **Graph path (1 of 96):** Plant P_TX → ProductionOrder PO-0058 → CustomerOrder CO-00247 → Dealer D18 / Customer C6387
- **Summary:** The message reports a plant outage at Wacky Wheels San Antonio (P_TX) from 2027-03-19 through 2027-03-22 and a supplier delay of infotainment chip (CHIP-IVI) from Quanta Silicon (SUP-12) into Wacky Wheels Princeton (P_IN) from 2027-03-15 until 2027-03-19 on shipment SH-0190. Affected records: 14 production orders and 122 customer orders. The tower completed 14 reschedules, 41 dealer notices, and 26 loaner assignments.

### E-02 — TC6 Unconfirmed Report — PASS
> Rumor from a supplier rep: something may be off with a seat material coming up. No dates, no details, nothing confirmed.

- **Read as:** `unconfirmed` (reader: qwen2.5:0.5b)
  - unconfirmed: `{"model_reason": "qwen2.5:0.5b: supplier_delay: a delivery of parts will arrive later than planned (a new date replaces the planned one)."}`
- **Expected:** no incident; escalate=true
- **Calls:** {'escalate': 1}
- ✅ summary and reason recorded
- ✅ no failed tool calls
- ✅ escalate only, no writes
- ✅ escalation gives a reason
- **Summary:** The report is not safe to act on: supplier_delay: a delivery of parts will arrive later than planned (a new date replaces the planned one). It is escalated for a human to confirm. No operational records were changed. The tower escalated the report and wrote nothing else.

### E-03 — TC3 Quality Hold — PASS
> Quality alert: Kestrel says the infotainment chip sent to Jackson had a faulty weld. Anything built Thursday Feb 25 through last Monday is suspect.

- **Read as:** `quality_hold` (reader: rules)
  - quality_hold: `{"supplier_id": "SUP-06", "part_id": "CHIP-IVI", "plant_id": "P_MS", "build_start": "2027-02-25", "build_end": "2027-03-01", "model_reason": "qwen2.5:0.5b: Quality alert: Parts sent to Jackson are faulty and must be held. Parts built after this date are suspect."}`
- **Expected:** [{"kind": "quality_hold", "lots": ["LOT-0130"]}]; escalate=false
- **Calls:** {'quality.hold_lot': 1, 'dealer.stop_sale': 37, 'crm.notify_customer': 150}
- ✅ summary and reason recorded
- ✅ no failed tool calls
- ✅ lot path Lot → PO → Vehicle → Dealer / Customer
- ✅ ≥3 kinds of action (rule 9): 3
- **Graph path (1 of 32):** Lot LOT-0130 → Part CHIP-IVI → Supplier SUP-06 → Plant P_MS
- **Summary:** The message reports a quality hold on infotainment chip (CHIP-IVI) at Wacky Wheels Jackson (P_MS) for builds 2027-02-25 through 2027-03-01. Affected records: 261 quality records. The tower completed 1 lot hold, 37 stop-sales, and 150 customer notices.

### E-04 — TC2 Plant Outage — PASS
> The Kentucky plant update: a software outage on the line. We're dark from next Tuesday through next Thursday; the line restarts the following working day.

- **Read as:** `plant_outage` (reader: rules)
  - plant_outage: `{"plant_id": "P_KY", "outage_start": "2027-03-16", "outage_end": "2027-03-18", "model_reason": "qwen2.5:0.5b: unconfirmed: a possible problem that nobody has confirmed (hearsay, guesses, vague reports without specifics)"}`
- **Expected:** [{"kind": "plant_outage", "plant_id": "P_KY", "outage_start": "2027-03-16", "outage_end": "2027-03-18"}]; escalate=false
- **Calls:** {'mes.reschedule': 9, 'dealer.notify': 32, 'crm.assign_loaner': 18}
- ✅ summary and reason recorded
- ✅ no failed tool calls
- ✅ outage path Plant → PO → CO → Dealer / Customer
- ✅ ≥3 kinds of action (rule 9): 3
- **Graph path (1 of 64):** Plant P_KY → ProductionOrder PO-0139 → CustomerOrder CO-00717 → Dealer D42 / Customer C5240
- **Summary:** The message reports a plant outage at Wacky Wheels Lexington (P_KY) from 2027-03-16 through 2027-03-18. Affected records: 9 production orders and 79 customer orders. The tower completed 9 reschedules, 32 dealer notices, and 18 loaner assignments.

### E-05 — TC4 Noise — PASS
> Dealer Amarillo, TX asks where to find the new brochure PDF.

- **Read as:** `noise` (reader: rules)
  - noise: `{"model_reason": "qwen2.5:0.5b: Dealer Amarillo, TX asks where to find the new brochure PDF"}`
- **Expected:** no incident; escalate=false
- **Calls:** none
- ✅ summary and reason recorded
- ✅ no failed tool calls
- ✅ no calls at all
- **Summary:** "Dealer Amarillo, TX asks where to find the new brochure PDF" is not an operational disruption because it does not report a supplier delay, a plant outage, or a quality hold. No operational records are affected. Nothing was written.

### E-06 — TC4 Noise — PASS
> Dealer Little Rock, AR asks where to find the new brochure PDF.

- **Read as:** `noise` (reader: rules)
  - noise: `{"model_reason": "qwen2.5:0.5b: The message is about a customer's request for information about a new brochure PDF."}`
- **Expected:** no incident; escalate=false
- **Calls:** none
- ✅ summary and reason recorded
- ✅ no failed tool calls
- ✅ no calls at all
- **Summary:** "Dealer Little Rock, AR asks where to find the new brochure PDF" is not an operational disruption because it does not report a supplier delay, a plant outage, or a quality hold. No operational records are affected. Nothing was written.

### E-07 — TC4 Noise — PASS
> Dealer Pensacola, FL asks where to find the new brochure PDF.

- **Read as:** `noise` (reader: rules)
  - noise: `{"model_reason": "qwen2.5:0.5b: The message is about a customer asking for information about a new brochure PDF."}`
- **Expected:** no incident; escalate=false
- **Calls:** none
- ✅ summary and reason recorded
- ✅ no failed tool calls
- ✅ no calls at all
- **Summary:** "Dealer Pensacola, FL asks where to find the new brochure PDF" is not an operational disruption because it does not report a supplier delay, a plant outage, or a quality hold. No operational records are affected. Nothing was written.

### E-08 — TC2 Plant Outage — PASS
> Plant operations alert: Wacky Wheels Lexington (P_KY) lost production to a power failure. Production is stopped from 2027-03-24 through 2027-03-25 inclusive.

- **Read as:** `plant_outage` (reader: rules)
  - plant_outage: `{"plant_id": "P_KY", "outage_start": "2027-03-24", "outage_end": "2027-03-25", "model_reason": "qwen2.5:0.5b: Power failure causing production to be delayed or stopped"}`
- **Expected:** [{"kind": "plant_outage", "plant_id": "P_KY", "outage_start": "2027-03-24", "outage_end": "2027-03-25"}]; escalate=false
- **Calls:** {'mes.reschedule': 6, 'dealer.notify': 25, 'crm.assign_loaner': 15}
- ✅ summary and reason recorded
- ✅ no failed tool calls
- ✅ outage path Plant → PO → CO → Dealer / Customer
- ✅ ≥3 kinds of action (rule 9): 3
- **Graph path (1 of 64):** Plant P_KY → ProductionOrder PO-0157 → CustomerOrder CO-00876 → Dealer D07 / Customer C5020
- **Summary:** The message reports a plant outage at Wacky Wheels Lexington (P_KY) from 2027-03-24 through 2027-03-25. Affected records: 6 production orders and 56 customer orders. The tower completed 6 reschedules, 25 dealer notices, and 15 loaner assignments.

### E-09 — TC1 Supplier Delay — PASS
> Quick heads up from Orbit: the surround-view cameras run for Huntsville can't make it Monday Mar 29. Carrier says Thursday Apr 1 now (a customs inspection).

- **Read as:** `supplier_delay` (reader: rules)
  - supplier_delay: `{"supplier_id": "SUP-11", "part_id": "CAM-360", "plant_id": "P_AL", "shipment_id": "SH-0256", "blocked_from": "2027-03-29", "blocked_until": "2027-04-01", "model_reason": "qwen2.5:0.5b: supplier_delay: a delivery of parts will arrive later than planned (a new date replaces the planned one)."}`
- **Expected:** [{"kind": "supplier_delay", "supplier_id": "SUP-11", "part_id": "CAM-360", "plant_id": "P_AL", "blocked_from": "2027-03-29", "blocked_until": "2027-04-01"}]; escalate=false
- **Calls:** {'mes.reschedule': 4, 'mes.transfer': 2, 'dealer.notify': 26, 'crm.assign_loaner': 10}
- ✅ summary and reason recorded
- ✅ no failed tool calls
- ✅ graph path starts at the Shipment
- ✅ ≥3 kinds of action (rule 9): 4
- **Graph path (1 of 64):** Shipment SH-0256 → Part CAM-360 → Model SUMMIT (BOM) → Plant P_AL → ProductionOrder PO-0436 → CustomerOrder CO-02567 → Dealer D25 / Customer C1467
- **Summary:** The message reports a supplier delay of surround-view camera kit (CAM-360) from Orbit Optics (SUP-11) into Wacky Wheels Huntsville (P_AL) from 2027-03-29 until 2027-04-01 on shipment SH-0256. Affected records: 6 production orders and 54 customer orders. The tower completed 4 reschedules, 2 transfers, 26 dealer notices, and 10 loaner assignments.

### E-10 — TC1 Supplier Delay — PASS
> Huntsville line is waiting on 60 kWh battery packs from Lumen. Original drop was Monday Mar 29, new ETA is Thursday Apr 1 because of a truck breakdown.

- **Read as:** `supplier_delay` (reader: rules)
  - supplier_delay: `{"supplier_id": "SUP-18", "part_id": "BATT-60", "plant_id": "P_AL", "shipment_id": "SH-0248", "blocked_from": "2027-03-29", "blocked_until": "2027-04-01", "model_reason": "qwen2.5:0.5b: Huntsville line is waiting on parts from Lumen, with a new ETA of Thursday April 1 due to a truck breakdown."}`
- **Expected:** [{"kind": "supplier_delay", "supplier_id": "SUP-18", "part_id": "BATT-60", "plant_id": "P_AL", "blocked_from": "2027-03-29", "blocked_until": "2027-04-01"}]; escalate=false
- **Calls:** {'mes.reschedule': 3, 'dealer.notify': 18, 'crm.assign_loaner': 7}
- ✅ summary and reason recorded
- ✅ no failed tool calls
- ✅ graph path starts at the Shipment
- ✅ ≥3 kinds of action (rule 9): 3
- **Graph path (1 of 58):** Shipment SH-0248 → Part BATT-60 → Model NOVA (BOM) → Plant P_AL → ProductionOrder PO-0437 → CustomerOrder CO-02575 → Dealer D04 / Customer C6785
- **Summary:** The message reports a supplier delay of 60 kWh battery pack (BATT-60) from Lumen Cells (SUP-18) into Wacky Wheels Huntsville (P_AL) from 2027-03-29 until 2027-04-01 on shipment SH-0248. Affected records: 3 production orders and 29 customer orders. The tower completed 3 reschedules, 18 dealer notices, and 7 loaner assignments.

### E-11 — TC2 Plant Outage — PASS
> Jackson update: a power failure. We're dark from Friday Mar 26 through Tuesday Mar 30; the line restarts the following working day.

- **Read as:** `plant_outage` (reader: rules)
  - plant_outage: `{"plant_id": "P_MS", "outage_start": "2027-03-26", "outage_end": "2027-03-30", "model_reason": "qwen2.5:0.5b: power failure: a delivery is late, delayed, slipping or postponed; a new or revised ETA or arrival date."}`
- **Expected:** [{"kind": "plant_outage", "plant_id": "P_MS", "outage_start": "2027-03-26", "outage_end": "2027-03-30"}]; escalate=false
- **Calls:** {'mes.reschedule': 6, 'mes.transfer': 3, 'dealer.notify': 36, 'crm.assign_loaner': 17}
- ✅ summary and reason recorded
- ✅ no failed tool calls
- ✅ outage path Plant → PO → CO → Dealer / Customer
- ✅ ≥3 kinds of action (rule 9): 4
- **Graph path (1 of 64):** Plant P_MS → ProductionOrder PO-0253 → CustomerOrder CO-01460 → Dealer D02 / Customer C5325
- **Summary:** The message reports a plant outage at Wacky Wheels Jackson (P_MS) from 2027-03-26 through 2027-03-30. Affected records: 9 production orders and 79 customer orders. The tower completed 6 reschedules, 3 transfers, 36 dealer notices, and 17 loaner assignments.

### E-12 — TC1 Supplier Delay — PASS
> Subject: Shipment SH-0182 delayed
From: dispatch@orbit.example

Our shipment SH-0182 of CAM-360 (surround-view camera kit) for Wacky Wheels Princeton (P_IN) was due 2027-03-15 and will now arrive 2027-03-18. Reason: port congestion.

- **Read as:** `supplier_delay` (reader: qwen2.5:0.5b)
  - supplier_delay: `{"supplier_id": "SUP-11", "part_id": "CAM-360", "plant_id": "P_IN", "shipment_id": "SH-0182", "blocked_from": "2027-03-15", "blocked_until": "2027-03-18", "model_reason": "qwen2.5:0.5b: supplier_delay: a delivery of parts will arrive later than planned (a new date replaces the planned one)."}`
- **Expected:** [{"kind": "supplier_delay", "supplier_id": "SUP-11", "part_id": "CAM-360", "plant_id": "P_IN", "shipment_id": "SH-0182", "blocked_from": "2027-03-15", "blocked_until": "2027-03-18"}]; escalate=false
- **Calls:** {'mes.reschedule': 3, 'dealer.notify': 14, 'crm.assign_loaner': 10}
- ✅ summary and reason recorded
- ✅ no failed tool calls
- ✅ graph path starts at the Shipment
- ✅ ≥3 kinds of action (rule 9): 3
- **Graph path (1 of 52):** Shipment SH-0182 → Part CAM-360 → Model VOYAGER (BOM) → Plant P_IN → ProductionOrder PO-0316 → CustomerOrder CO-01756 → Dealer D07 / Customer C4130
- **Summary:** The message reports a supplier delay of surround-view camera kit (CAM-360) from Orbit Optics (SUP-11) into Wacky Wheels Princeton (P_IN) from 2027-03-15 until 2027-03-18 on shipment SH-0182. Affected records: 3 production orders and 26 customer orders. The tower completed 3 reschedules, 14 dealer notices, and 10 loaner assignments.

### E-13 — TC6 Unconfirmed Report — PASS
> Someone on the floor mentioned a possible shortage of something electronic sometime soon. Not confirmed by anyone.

- **Read as:** `unconfirmed` (reader: qwen2.5:0.5b)
  - unconfirmed: `{"model_reason": "qwen2.5:0.5b: unconfirmed: not about the company's deliveries, plants or part quality (announcements, questions, news elsewhere)."}`
- **Expected:** no incident; escalate=true
- **Calls:** {'escalate': 1}
- ✅ summary and reason recorded
- ✅ no failed tool calls
- ✅ escalate only, no writes
- ✅ escalation gives a reason
- **Summary:** The report is not safe to act on: unconfirmed: not about the company's deliveries, plants or part quality (announcements, questions, news elsewhere). It is escalated for a human to confirm. No operational records were changed. The tower escalated the report and wrote nothing else.

### E-14 — TC3 Quality Hold — PASS
> Quality alert: Atlas says the heavy-duty wiring harness sent to the Texas plant had a moisture contamination. Anything built Monday Feb 22 through Wednesday Feb 24 is suspect.

- **Read as:** `quality_hold` (reader: rules)
  - quality_hold: `{"supplier_id": "SUP-07", "part_id": "HARN-B", "plant_id": "P_TX", "build_start": "2027-02-22", "build_end": "2027-02-24", "model_reason": "qwen2.5:0.5b: Quality alert: Parts sent to the Texas plant have moisture contamination. Parts built on or after February 22 through March 24 are suspect."}`
- **Expected:** [{"kind": "quality_hold", "lots": ["LOT-0017"]}]; escalate=false
- **Calls:** {'quality.hold_lot': 1, 'dealer.stop_sale': 36, 'crm.notify_customer': 94}
- ✅ summary and reason recorded
- ✅ no failed tool calls
- ✅ lot path Lot → PO → Vehicle → Dealer / Customer
- ✅ ≥3 kinds of action (rule 9): 3
- **Graph path (1 of 32):** Lot LOT-0017 → Part HARN-B → Supplier SUP-07 → Plant P_TX
- **Summary:** The message reports a quality hold on heavy-duty wiring harness (HARN-B) at Wacky Wheels San Antonio (P_TX) for builds 2027-02-22 through 2027-02-24. Affected records: 181 quality records. The tower completed 1 lot hold, 36 stop-sales, and 94 customer notices.

### E-15 — TC3 Quality Hold — PASS
> QUALITY BULLETIN QB-368: Lot LOT-0191 (CHIP-IVI, supplier SUP-12) installed at P_IN on vehicles built 2027-03-02 to 2027-03-03 has a faulty weld. Place the lot on hold, stop sale of unsold vehicles and contact owners.

- **Read as:** `quality_hold` (reader: qwen2.5:0.5b)
  - quality_hold: `{"supplier_id": "SUP-12", "part_id": "CHIP-IVI", "plant_id": "P_IN", "lot_id": "LOT-0191", "build_start": "2027-03-02", "build_end": "2027-03-03", "model_reason": "qwen2.5:0.5b: The message reports that a part lot (LOT-0191) has a faulty weld and needs to be held. This is a quality hold."}`
- **Expected:** [{"kind": "quality_hold", "lots": ["LOT-0191"]}]; escalate=false
- **Calls:** {'quality.hold_lot': 1, 'dealer.stop_sale': 25, 'crm.notify_customer': 76}
- ✅ summary and reason recorded
- ✅ no failed tool calls
- ✅ lot path Lot → PO → Vehicle → Dealer / Customer
- ✅ ≥3 kinds of action (rule 9): 3
- **Graph path (1 of 32):** Lot LOT-0191 → Part CHIP-IVI → Supplier SUP-12 → Plant P_IN
- **Summary:** The message reports a quality hold on lot LOT-0191 at Wacky Wheels Princeton (P_IN) for builds 2027-03-02 through 2027-03-03. Affected records: 117 quality records. The tower completed 1 lot hold, 25 stop-sales, and 76 customer notices.

## Details — qwen3:0.6b reader

### E-01 — TC5 Compound Incident — PASS
> Morning digest, two items. (1) San Antonio update: a software outage on the line. We're dark from next Friday through Monday Mar 22; the line restarts the following working day. (2) Quick heads up from Quanta: the infotainment chip run for Princeton can't make it next Monday. Carrier says next Friday now (severe weather on the route).

- **Read as:** `plant_outage+supplier_delay` (reader: rules, qwen3:0.6b)
  - plant_outage: `{"plant_id": "P_TX", "outage_start": "2027-03-19", "outage_end": "2027-03-22", "model_reason": "qwen3:0.6b: A plant outage has occurred, with the outage lasting from next Friday through Monday, and the line will restart on the following working day. This is a plant_outage."}`
  - supplier_delay: `{"supplier_id": "SUP-12", "part_id": "CHIP-IVI", "plant_id": "P_IN", "shipment_id": "SH-0190", "blocked_from": "2027-03-15", "blocked_until": "2027-03-19", "model_reason": "qwen3:0.6b: A supplier says a part shipment will arrive late, with the original and the new date, so it is a supplier delay."}`
- **Expected:** [{"kind": "plant_outage", "plant_id": "P_TX", "outage_start": "2027-03-19", "outage_end": "2027-03-22"}, {"kind": "supplier_delay", "supplier_id": "SUP-12", "part_id": "CHIP-IVI", "plant_id": "P_IN", "blocked_from": "2027-03-15", "blocked_until": "2027-03-19"}]; escalate=false
- **Calls:** {'mes.reschedule': 14, 'dealer.notify': 41, 'crm.assign_loaner': 26}
- ✅ summary and reason recorded
- ✅ no failed tool calls
- ✅ outage path Plant → PO → CO → Dealer / Customer
- ✅ delay path for the second incident
- ✅ ≥3 kinds of action (rule 9): 3
- **Graph path (1 of 244):** Plant P_TX → ProductionOrder PO-0058 → CustomerOrder CO-00247 → Dealer D18 / Customer C6387
- **Summary:** The message reports a plant outage at Wacky Wheels San Antonio (P_TX) from 2027-03-19 through 2027-03-22 and a supplier delay of infotainment chip (CHIP-IVI) from Quanta Silicon (SUP-12) into Wacky Wheels Princeton (P_IN) from 2027-03-15 until 2027-03-19 on shipment SH-0190. Affected records: 14 production orders and 122 customer orders. The tower completed 14 reschedules, 41 dealer notices, and 26 loaner assignments.

### E-02 — TC6 Unconfirmed Report — PASS
> Rumor from a supplier rep: something may be off with a seat material coming up. No dates, no details, nothing confirmed.

- **Read as:** `unconfirmed` (reader: qwen3:0.6b)
  - unconfirmed: `{"model_reason": "qwen3:0.6b: A rumor or vague report about a possible problem, so it is unconfirmed."}`
- **Expected:** no incident; escalate=true
- **Calls:** {'escalate': 1}
- ✅ summary and reason recorded
- ✅ no failed tool calls
- ✅ escalate only, no writes
- ✅ escalation gives a reason
- **Summary:** The report is not safe to act on because it is unconfirmed (rumor, nothing confirmed, no dates, no details, may be) and does not name a specific shipment, outage, or lot to change. No operational records were changed. The tower escalated the report and wrote nothing else.

### E-03 — TC3 Quality Hold — PASS
> Quality alert: Kestrel says the infotainment chip sent to Jackson had a faulty weld. Anything built Thursday Feb 25 through last Monday is suspect.

- **Read as:** `quality_hold` (reader: qwen3:0.6b)
  - quality_hold: `{"supplier_id": "SUP-06", "part_id": "CHIP-IVI", "plant_id": "P_MS", "build_start": "2027-02-25", "build_end": "2027-03-01", "model_reason": "qwen3:0.6b: A part or lot is defective for vehicles built in a stated date range, so it is a quality_hold."}`
- **Expected:** [{"kind": "quality_hold", "lots": ["LOT-0130"]}]; escalate=false
- **Calls:** {'quality.hold_lot': 1, 'dealer.stop_sale': 37, 'crm.notify_customer': 150}
- ✅ summary and reason recorded
- ✅ no failed tool calls
- ✅ lot path Lot → PO → Vehicle → Dealer / Customer
- ✅ ≥3 kinds of action (rule 9): 3
- **Graph path (1 of 261):** Lot LOT-0130 → Part CHIP-IVI → Supplier SUP-06 → Plant P_MS
- **Summary:** The message reports a quality hold on infotainment chip (CHIP-IVI) at Wacky Wheels Jackson (P_MS) for builds 2027-02-25 through 2027-03-01. Affected records: 261 quality records. The tower completed 1 lot hold, 37 stop-sales, and 150 customer notices.

### E-04 — TC2 Plant Outage — PASS
> The Kentucky plant update: a software outage on the line. We're dark from next Tuesday through next Thursday; the line restarts the following working day.

- **Read as:** `plant_outage` (reader: qwen3:0.6b)
  - plant_outage: `{"plant_id": "P_KY", "outage_start": "2027-03-16", "outage_end": "2027-03-18", "model_reason": "qwen3:0.6b: A plant outage is affecting the line, with the outage lasting from Tuesday through Thursday, and the line will restart on the following working day. This is a plant_outage."}`
- **Expected:** [{"kind": "plant_outage", "plant_id": "P_KY", "outage_start": "2027-03-16", "outage_end": "2027-03-18"}]; escalate=false
- **Calls:** {'mes.reschedule': 9, 'dealer.notify': 32, 'crm.assign_loaner': 18}
- ✅ summary and reason recorded
- ✅ no failed tool calls
- ✅ outage path Plant → PO → CO → Dealer / Customer
- ✅ ≥3 kinds of action (rule 9): 3
- **Graph path (1 of 158):** Plant P_KY → ProductionOrder PO-0139 → CustomerOrder CO-00717 → Dealer D42 / Customer C5240
- **Summary:** The message reports a plant outage at Wacky Wheels Lexington (P_KY) from 2027-03-16 through 2027-03-18. Affected records: 9 production orders and 79 customer orders. The tower completed 9 reschedules, 32 dealer notices, and 18 loaner assignments.

### E-05 — TC4 Noise — PASS
> Dealer Amarillo, TX asks where to find the new brochure PDF.

- **Read as:** `noise` (reader: qwen3:0.6b)
  - noise: `{"model_reason": "qwen3:0.6b: A dealer is providing information about a brochure, which is not about operations, so it is noise."}`
- **Expected:** no incident; escalate=false
- **Calls:** none
- ✅ summary and reason recorded
- ✅ no failed tool calls
- ✅ no calls at all
- **Summary:** "Dealer Amarillo, TX asks where to find the new brochure PDF" is not an operational disruption because it does not report a supplier delay, a plant outage, or a quality hold. No operational records are affected. Nothing was written.

### E-06 — TC4 Noise — PASS
> Dealer Little Rock, AR asks where to find the new brochure PDF.

- **Read as:** `noise` (reader: qwen3:0.6b)
  - noise: `{"model_reason": "qwen3:0.6b: A dealer is providing information about a brochure, which is not about operations, so it is noise."}`
- **Expected:** no incident; escalate=false
- **Calls:** none
- ✅ summary and reason recorded
- ✅ no failed tool calls
- ✅ no calls at all
- **Summary:** "Dealer Little Rock, AR asks where to find the new brochure PDF" is not an operational disruption because it does not report a supplier delay, a plant outage, or a quality hold. No operational records are affected. Nothing was written.

### E-07 — TC4 Noise — PASS
> Dealer Pensacola, FL asks where to find the new brochure PDF.

- **Read as:** `noise` (reader: qwen3:0.6b)
  - noise: `{"model_reason": "qwen3:0.6b: A dealer is providing information about a brochure, which is not about operations, so it is noise."}`
- **Expected:** no incident; escalate=false
- **Calls:** none
- ✅ summary and reason recorded
- ✅ no failed tool calls
- ✅ no calls at all
- **Summary:** "Dealer Pensacola, FL asks where to find the new brochure PDF" is not an operational disruption because it does not report a supplier delay, a plant outage, or a quality hold. No operational records are affected. Nothing was written.

### E-08 — TC2 Plant Outage — PASS
> Plant operations alert: Wacky Wheels Lexington (P_KY) lost production to a power failure. Production is stopped from 2027-03-24 through 2027-03-25 inclusive.

- **Read as:** `plant_outage` (reader: qwen3:0.6b)
  - plant_outage: `{"plant_id": "P_KY", "outage_start": "2027-03-24", "outage_end": "2027-03-25", "model_reason": "qwen3:0.6b: A plant outage caused a loss of production, so it is a plant_outage."}`
- **Expected:** [{"kind": "plant_outage", "plant_id": "P_KY", "outage_start": "2027-03-24", "outage_end": "2027-03-25"}]; escalate=false
- **Calls:** {'mes.reschedule': 6, 'dealer.notify': 25, 'crm.assign_loaner': 15}
- ✅ summary and reason recorded
- ✅ no failed tool calls
- ✅ outage path Plant → PO → CO → Dealer / Customer
- ✅ ≥3 kinds of action (rule 9): 3
- **Graph path (1 of 112):** Plant P_KY → ProductionOrder PO-0157 → CustomerOrder CO-00876 → Dealer D07 / Customer C5020
- **Summary:** The message reports a plant outage at Wacky Wheels Lexington (P_KY) from 2027-03-24 through 2027-03-25. Affected records: 6 production orders and 56 customer orders. The tower completed 6 reschedules, 25 dealer notices, and 15 loaner assignments.

### E-09 — TC1 Supplier Delay — PASS
> Quick heads up from Orbit: the surround-view cameras run for Huntsville can't make it Monday Mar 29. Carrier says Thursday Apr 1 now (a customs inspection).

- **Read as:** `supplier_delay` (reader: qwen3:0.6b)
  - supplier_delay: `{"supplier_id": "SUP-11", "part_id": "CAM-360", "plant_id": "P_AL", "shipment_id": "SH-0256", "blocked_from": "2027-03-29", "blocked_until": "2027-04-01", "model_reason": "qwen3:0.6b: A supplier says a part shipment will arrive late, with the original and the new date, so it is a supplier delay."}`
- **Expected:** [{"kind": "supplier_delay", "supplier_id": "SUP-11", "part_id": "CAM-360", "plant_id": "P_AL", "blocked_from": "2027-03-29", "blocked_until": "2027-04-01"}]; escalate=false
- **Calls:** {'mes.reschedule': 4, 'mes.transfer': 2, 'dealer.notify': 26, 'crm.assign_loaner': 10}
- ✅ summary and reason recorded
- ✅ no failed tool calls
- ✅ graph path starts at the Shipment
- ✅ ≥3 kinds of action (rule 9): 4
- **Graph path (1 of 108):** Shipment SH-0256 → Part CAM-360 → Model SUMMIT (BOM) → Plant P_AL → ProductionOrder PO-0436 → CustomerOrder CO-02567 → Dealer D25 / Customer C1467
- **Summary:** The message reports a supplier delay of surround-view camera kit (CAM-360) from Orbit Optics (SUP-11) into Wacky Wheels Huntsville (P_AL) from 2027-03-29 until 2027-04-01 on shipment SH-0256. Affected records: 6 production orders and 54 customer orders. The tower completed 4 reschedules, 2 transfers, 26 dealer notices, and 10 loaner assignments.

### E-10 — TC1 Supplier Delay — PASS
> Huntsville line is waiting on 60 kWh battery packs from Lumen. Original drop was Monday Mar 29, new ETA is Thursday Apr 1 because of a truck breakdown.

- **Read as:** `supplier_delay` (reader: qwen3:0.6b)
  - supplier_delay: `{"supplier_id": "SUP-18", "part_id": "BATT-60", "plant_id": "P_AL", "shipment_id": "SH-0248", "blocked_from": "2027-03-29", "blocked_until": "2027-04-01", "model_reason": "qwen3:0.6b: A supplier says a part shipment will arrive late, with the original and the new date, so it is a supplier delay."}`
- **Expected:** [{"kind": "supplier_delay", "supplier_id": "SUP-18", "part_id": "BATT-60", "plant_id": "P_AL", "blocked_from": "2027-03-29", "blocked_until": "2027-04-01"}]; escalate=false
- **Calls:** {'mes.reschedule': 3, 'dealer.notify': 18, 'crm.assign_loaner': 7}
- ✅ summary and reason recorded
- ✅ no failed tool calls
- ✅ graph path starts at the Shipment
- ✅ ≥3 kinds of action (rule 9): 3
- **Graph path (1 of 58):** Shipment SH-0248 → Part BATT-60 → Model NOVA (BOM) → Plant P_AL → ProductionOrder PO-0437 → CustomerOrder CO-02575 → Dealer D04 / Customer C6785
- **Summary:** The message reports a supplier delay of 60 kWh battery pack (BATT-60) from Lumen Cells (SUP-18) into Wacky Wheels Huntsville (P_AL) from 2027-03-29 until 2027-04-01 on shipment SH-0248. Affected records: 3 production orders and 29 customer orders. The tower completed 3 reschedules, 18 dealer notices, and 7 loaner assignments.

### E-11 — TC2 Plant Outage — PASS
> Jackson update: a power failure. We're dark from Friday Mar 26 through Tuesday Mar 30; the line restarts the following working day.

- **Read as:** `plant_outage` (reader: rules)
  - plant_outage: `{"plant_id": "P_MS", "outage_start": "2027-03-26", "outage_end": "2027-03-30", "model_reason": "qwen3:0.6b: A power failure has occurred, with the line being dark from Friday Mar 26 through Tuesday Mar 30, and the line will restart on the following working day. This is a plant_outage."}`
- **Expected:** [{"kind": "plant_outage", "plant_id": "P_MS", "outage_start": "2027-03-26", "outage_end": "2027-03-30"}]; escalate=false
- **Calls:** {'mes.reschedule': 6, 'mes.transfer': 3, 'dealer.notify': 36, 'crm.assign_loaner': 17}
- ✅ summary and reason recorded
- ✅ no failed tool calls
- ✅ outage path Plant → PO → CO → Dealer / Customer
- ✅ ≥3 kinds of action (rule 9): 4
- **Graph path (1 of 158):** Plant P_MS → ProductionOrder PO-0253 → CustomerOrder CO-01460 → Dealer D02 / Customer C5325
- **Summary:** The message reports a plant outage at Wacky Wheels Jackson (P_MS) from 2027-03-26 through 2027-03-30. Affected records: 9 production orders and 79 customer orders. The tower completed 6 reschedules, 3 transfers, 36 dealer notices, and 17 loaner assignments.

### E-12 — TC1 Supplier Delay — PASS
> Subject: Shipment SH-0182 delayed
From: dispatch@orbit.example

Our shipment SH-0182 of CAM-360 (surround-view camera kit) for Wacky Wheels Princeton (P_IN) was due 2027-03-15 and will now arrive 2027-03-18. Reason: port congestion.

- **Read as:** `supplier_delay` (reader: qwen3:0.6b)
  - supplier_delay: `{"supplier_id": "SUP-11", "part_id": "CAM-360", "plant_id": "P_IN", "shipment_id": "SH-0182", "blocked_from": "2027-03-15", "blocked_until": "2027-03-18", "model_reason": "qwen3:0.6b: A shipment is delayed due to port congestion, so it is a supplier_delay."}`
- **Expected:** [{"kind": "supplier_delay", "supplier_id": "SUP-11", "part_id": "CAM-360", "plant_id": "P_IN", "shipment_id": "SH-0182", "blocked_from": "2027-03-15", "blocked_until": "2027-03-18"}]; escalate=false
- **Calls:** {'mes.reschedule': 3, 'dealer.notify': 14, 'crm.assign_loaner': 10}
- ✅ summary and reason recorded
- ✅ no failed tool calls
- ✅ graph path starts at the Shipment
- ✅ ≥3 kinds of action (rule 9): 3
- **Graph path (1 of 52):** Shipment SH-0182 → Part CAM-360 → Model VOYAGER (BOM) → Plant P_IN → ProductionOrder PO-0316 → CustomerOrder CO-01756 → Dealer D07 / Customer C4130
- **Summary:** The message reports a supplier delay of surround-view camera kit (CAM-360) from Orbit Optics (SUP-11) into Wacky Wheels Princeton (P_IN) from 2027-03-15 until 2027-03-18 on shipment SH-0182. Affected records: 3 production orders and 26 customer orders. The tower completed 3 reschedules, 14 dealer notices, and 10 loaner assignments.

### E-13 — TC6 Unconfirmed Report — PASS
> Someone on the floor mentioned a possible shortage of something electronic sometime soon. Not confirmed by anyone.

- **Read as:** `unconfirmed` (reader: qwen3:0.6b)
  - unconfirmed: `{"model_reason": "qwen3:0.6b: A rumor or vague report about a possible problem with a part or lot is not confirmed, so it is unconfirmed."}`
- **Expected:** no incident; escalate=true
- **Calls:** {'escalate': 1}
- ✅ summary and reason recorded
- ✅ no failed tool calls
- ✅ escalate only, no writes
- ✅ escalation gives a reason
- **Summary:** The report is not safe to act on because it is unconfirmed (not confirmed, possible, someone on the floor mentioned) and does not name a specific shipment, outage, or lot to change. No operational records were changed. The tower escalated the report and wrote nothing else.

### E-14 — TC3 Quality Hold — PASS
> Quality alert: Atlas says the heavy-duty wiring harness sent to the Texas plant had a moisture contamination. Anything built Monday Feb 22 through Wednesday Feb 24 is suspect.

- **Read as:** `quality_hold` (reader: qwen3:0.6b)
  - quality_hold: `{"supplier_id": "SUP-07", "part_id": "HARN-B", "plant_id": "P_TX", "build_start": "2027-02-22", "build_end": "2027-02-24", "model_reason": "qwen3:0.6b: A quality hold is reported for a part or lot built in a stated date range, indicating a defect. This is a quality_hold."}`
- **Expected:** [{"kind": "quality_hold", "lots": ["LOT-0017"]}]; escalate=false
- **Calls:** {'quality.hold_lot': 1, 'dealer.stop_sale': 36, 'crm.notify_customer': 94}
- ✅ summary and reason recorded
- ✅ no failed tool calls
- ✅ lot path Lot → PO → Vehicle → Dealer / Customer
- ✅ ≥3 kinds of action (rule 9): 3
- **Graph path (1 of 181):** Lot LOT-0017 → Part HARN-B → Supplier SUP-07 → Plant P_TX
- **Summary:** The message reports a quality hold on heavy-duty wiring harness (HARN-B) at Wacky Wheels San Antonio (P_TX) for builds 2027-02-22 through 2027-02-24. Affected records: 181 quality records. The tower completed 1 lot hold, 36 stop-sales, and 94 customer notices.

### E-15 — TC3 Quality Hold — PASS
> QUALITY BULLETIN QB-368: Lot LOT-0191 (CHIP-IVI, supplier SUP-12) installed at P_IN on vehicles built 2027-03-02 to 2027-03-03 has a faulty weld. Place the lot on hold, stop sale of unsold vehicles and contact owners.

- **Read as:** `quality_hold` (reader: qwen3:0.6b)
  - quality_hold: `{"supplier_id": "SUP-12", "part_id": "CHIP-IVI", "plant_id": "P_IN", "lot_id": "LOT-0191", "build_start": "2027-03-02", "build_end": "2027-03-03", "model_reason": "qwen3:0.6b: A quality hold is reported for a part or lot, indicating a defect in the weld. This is a quality_hold."}`
- **Expected:** [{"kind": "quality_hold", "lots": ["LOT-0191"]}]; escalate=false
- **Calls:** {'quality.hold_lot': 1, 'dealer.stop_sale': 25, 'crm.notify_customer': 76}
- ✅ summary and reason recorded
- ✅ no failed tool calls
- ✅ lot path Lot → PO → Vehicle → Dealer / Customer
- ✅ ≥3 kinds of action (rule 9): 3
- **Graph path (1 of 117):** Lot LOT-0191 → Part CHIP-IVI → Supplier SUP-12 → Plant P_IN
- **Summary:** The message reports a quality hold on lot LOT-0191 at Wacky Wheels Princeton (P_IN) for builds 2027-03-02 through 2027-03-03. Affected records: 117 quality records. The tower completed 1 lot hold, 25 stop-sales, and 76 customer notices.

## Details — qwen3:1.7b reader

### E-01 — TC5 Compound Incident — PASS
> Morning digest, two items. (1) San Antonio update: a software outage on the line. We're dark from next Friday through Monday Mar 22; the line restarts the following working day. (2) Quick heads up from Quanta: the infotainment chip run for Princeton can't make it next Monday. Carrier says next Friday now (severe weather on the route).

- **Read as:** `plant_outage+supplier_delay` (reader: qwen3:1.7b, qwen3:1.7b)
  - plant_outage: `{"plant_id": "P_TX", "outage_start": "2027-03-19", "outage_end": "2027-03-22", "model_reason": "qwen3:1.7b: This is a plant_outage because a manufacturing line is temporarily shut down and will restart the following working day, affecting production."}`
  - supplier_delay: `{"supplier_id": "SUP-12", "part_id": "CHIP-IVI", "plant_id": "P_IN", "shipment_id": "SH-0190", "blocked_from": "2027-03-15", "blocked_until": "2027-03-19", "model_reason": "qwen3:1.7b: supplier_delay: The infotainment chip delivery is postponed to next Friday due to severe weather on the route, affecting the production schedule at Princeton."}`
- **Expected:** [{"kind": "plant_outage", "plant_id": "P_TX", "outage_start": "2027-03-19", "outage_end": "2027-03-22"}, {"kind": "supplier_delay", "supplier_id": "SUP-12", "part_id": "CHIP-IVI", "plant_id": "P_IN", "blocked_from": "2027-03-15", "blocked_until": "2027-03-19"}]; escalate=false
- **Calls:** {'mes.reschedule': 14, 'dealer.notify': 41, 'crm.assign_loaner': 26}
- ✅ summary and reason recorded
- ✅ no failed tool calls
- ✅ outage path Plant → PO → CO → Dealer / Customer
- ✅ delay path for the second incident
- ✅ ≥3 kinds of action (rule 9): 3
- **Graph path (1 of 96):** Plant P_TX → ProductionOrder PO-0058 → CustomerOrder CO-00247 → Dealer D18 / Customer C6387
- **Summary:** The message reports a plant outage at Wacky Wheels San Antonio (P_TX) from 2027-03-19 through 2027-03-22 and a supplier delay of infotainment chip (CHIP-IVI) from Quanta Silicon (SUP-12) into Wacky Wheels Princeton (P_IN) from 2027-03-15 until 2027-03-19 on shipment SH-0190. Affected records: 14 production orders and 122 customer orders. The tower completed 14 reschedules, 41 dealer notices, and 26 loaner assignments.

### E-02 — TC6 Unconfirmed Report — PASS
> Rumor from a supplier rep: something may be off with a seat material coming up. No dates, no details, nothing confirmed.

- **Read as:** `unconfirmed` (reader: qwen3:1.7b)
  - unconfirmed: `{"model_reason": "qwen3:1.7b: The message reports a possible problem with a seat material from a supplier, but no specific details or dates are provided, making it unconfirmed."}`
- **Expected:** no incident; escalate=true
- **Calls:** {'escalate': 1}
- ✅ summary and reason recorded
- ✅ no failed tool calls
- ✅ escalate only, no writes
- ✅ escalation gives a reason
- **Summary:** The report is not safe to act on: The message reports a possible problem with a seat material from a supplier, but no specific details or dates are provided, making it unconfirmed. It is escalated for a human to confirm. No operational records were changed. The tower escalated the report and wrote nothing else.

### E-03 — TC3 Quality Hold — PASS
> Quality alert: Kestrel says the infotainment chip sent to Jackson had a faulty weld. Anything built Thursday Feb 25 through last Monday is suspect.

- **Read as:** `quality_hold` (reader: qwen3:1.7b)
  - quality_hold: `{"supplier_id": "SUP-06", "part_id": "CHIP-IVI", "plant_id": "P_MS", "lot_id": "LOT-0130", "build_start": "2027-02-25", "build_end": "2027-03-01", "model_reason": "qwen3:1.7b: The message reports a quality issue with infotainment chips, indicating that any vehicles built from Thursday, February 25 through last Monday are suspect. This is a quality_hold situation as the defect is confirmed and action is required to hold those vehicles."}`
- **Expected:** [{"kind": "quality_hold", "lots": ["LOT-0130"]}]; escalate=false
- **Calls:** {'quality.hold_lot': 1, 'dealer.stop_sale': 37, 'crm.notify_customer': 150}
- ✅ summary and reason recorded
- ✅ no failed tool calls
- ✅ lot path Lot → PO → Vehicle → Dealer / Customer
- ✅ ≥3 kinds of action (rule 9): 3
- **Graph path (1 of 32):** Lot LOT-0130 → Part CHIP-IVI → Supplier SUP-06 → Plant P_MS
- **Summary:** The message reports a quality hold on lot LOT-0130 at Wacky Wheels Jackson (P_MS) for builds 2027-02-25 through 2027-03-01. Affected records: 261 quality records. The tower completed 1 lot hold, 37 stop-sales, and 150 customer notices.

### E-04 — TC2 Plant Outage — PASS
> The Kentucky plant update: a software outage on the line. We're dark from next Tuesday through next Thursday; the line restarts the following working day.

- **Read as:** `plant_outage` (reader: qwen3:1.7b)
  - plant_outage: `{"plant_id": "P_KY", "outage_start": "2027-03-16", "outage_end": "2027-03-18", "model_reason": "qwen3:1.7b: plant_outage: The Kentucky plant is experiencing a software outage, causing it to be dark from next Tuesday through next Thursday. The line is expected to restart the following working day."}`
- **Expected:** [{"kind": "plant_outage", "plant_id": "P_KY", "outage_start": "2027-03-16", "outage_end": "2027-03-18"}]; escalate=false
- **Calls:** {'mes.reschedule': 9, 'dealer.notify': 32, 'crm.assign_loaner': 18}
- ✅ summary and reason recorded
- ✅ no failed tool calls
- ✅ outage path Plant → PO → CO → Dealer / Customer
- ✅ ≥3 kinds of action (rule 9): 3
- **Graph path (1 of 64):** Plant P_KY → ProductionOrder PO-0139 → CustomerOrder CO-00717 → Dealer D42 / Customer C5240
- **Summary:** The message reports a plant outage at Wacky Wheels Lexington (P_KY) from 2027-03-16 through 2027-03-18. Affected records: 9 production orders and 79 customer orders. The tower completed 9 reschedules, 32 dealer notices, and 18 loaner assignments.

### E-05 — TC4 Noise — PASS
> Dealer Amarillo, TX asks where to find the new brochure PDF.

- **Read as:** `noise` (reader: qwen3:1.7b)
  - noise: `{"model_reason": "qwen3:1.7b: This message is about a request for information regarding a new brochure PDF, which is not related to the company's deliveries, plants, part quality, or any potential issues. It is a general inquiry about a document, not involving any of the specified categories."}`
- **Expected:** no incident; escalate=false
- **Calls:** none
- ✅ summary and reason recorded
- ✅ no failed tool calls
- ✅ no calls at all
- **Summary:** "Dealer Amarillo, TX asks where to find the new brochure PDF" is not an operational disruption because it does not report a supplier delay, a plant outage, or a quality hold. No operational records are affected. Nothing was written.

### E-06 — TC4 Noise — PASS
> Dealer Little Rock, AR asks where to find the new brochure PDF.

- **Read as:** `noise` (reader: qwen3:1.7b)
  - noise: `{"model_reason": "qwen3:1.7b: This message is about a request for information regarding a new brochure PDF, which is not related to the company's deliveries, plants, part quality, or any potential issues. It is a general inquiry about where to find a document, not related to the specific operations or events mentioned in the company's messages."}`
- **Expected:** no incident; escalate=false
- **Calls:** none
- ✅ summary and reason recorded
- ✅ no failed tool calls
- ✅ no calls at all
- **Summary:** "Dealer Little Rock, AR asks where to find the new brochure PDF" is not an operational disruption because it does not report a supplier delay, a plant outage, or a quality hold. No operational records are affected. Nothing was written.

### E-07 — TC4 Noise — PASS
> Dealer Pensacola, FL asks where to find the new brochure PDF.

- **Read as:** `noise` (reader: qwen3:1.7b)
  - noise: `{"model_reason": "qwen3:1.7b: This message is about a request for information regarding a brochure PDF, which is not related to the company's deliveries, plants, part quality, or any potential issues. It is a general inquiry about where to find a document, not related to the specific operations or events mentioned in the company's messages."}`
- **Expected:** no incident; escalate=false
- **Calls:** none
- ✅ summary and reason recorded
- ✅ no failed tool calls
- ✅ no calls at all
- **Summary:** "Dealer Pensacola, FL asks where to find the new brochure PDF" is not an operational disruption because it does not report a supplier delay, a plant outage, or a quality hold. No operational records are affected. Nothing was written.

### E-08 — TC2 Plant Outage — PASS
> Plant operations alert: Wacky Wheels Lexington (P_KY) lost production to a power failure. Production is stopped from 2027-03-24 through 2027-03-25 inclusive.

- **Read as:** `plant_outage` (reader: qwen3:1.7b)
  - plant_outage: `{"plant_id": "P_KY", "outage_start": "2027-03-24", "outage_end": "2027-03-25", "model_reason": "qwen3:1.7b: plant_outage: A power failure caused the production at Wacky Wheels Lexington to stop from March 24 to March 25, 2027."}`
- **Expected:** [{"kind": "plant_outage", "plant_id": "P_KY", "outage_start": "2027-03-24", "outage_end": "2027-03-25"}]; escalate=false
- **Calls:** {'mes.reschedule': 6, 'dealer.notify': 25, 'crm.assign_loaner': 15}
- ✅ summary and reason recorded
- ✅ no failed tool calls
- ✅ outage path Plant → PO → CO → Dealer / Customer
- ✅ ≥3 kinds of action (rule 9): 3
- **Graph path (1 of 64):** Plant P_KY → ProductionOrder PO-0157 → CustomerOrder CO-00876 → Dealer D07 / Customer C5020
- **Summary:** The message reports a plant outage at Wacky Wheels Lexington (P_KY) from 2027-03-24 through 2027-03-25. Affected records: 6 production orders and 56 customer orders. The tower completed 6 reschedules, 25 dealer notices, and 15 loaner assignments.

### E-09 — TC1 Supplier Delay — PASS
> Quick heads up from Orbit: the surround-view cameras run for Huntsville can't make it Monday Mar 29. Carrier says Thursday Apr 1 now (a customs inspection).

- **Read as:** `supplier_delay` (reader: qwen3:1.7b)
  - supplier_delay: `{"supplier_id": "SUP-11", "part_id": "CAM-360", "plant_id": "P_AL", "shipment_id": "SH-0256", "blocked_from": "2027-03-29", "blocked_until": "2027-04-01", "model_reason": "qwen3:1.7b: This is a supplier_delay message. The surround-view cameras from Huntsville are delayed due to a customs inspection, which is a reason for the delay in delivery. The carrier has updated the arrival date to Thursday, April 1, indicating a postponement of the delivery schedule."}`
- **Expected:** [{"kind": "supplier_delay", "supplier_id": "SUP-11", "part_id": "CAM-360", "plant_id": "P_AL", "blocked_from": "2027-03-29", "blocked_until": "2027-04-01"}]; escalate=false
- **Calls:** {'mes.reschedule': 4, 'mes.transfer': 2, 'dealer.notify': 26, 'crm.assign_loaner': 10}
- ✅ summary and reason recorded
- ✅ no failed tool calls
- ✅ graph path starts at the Shipment
- ✅ ≥3 kinds of action (rule 9): 4
- **Graph path (1 of 64):** Shipment SH-0256 → Part CAM-360 → Model SUMMIT (BOM) → Plant P_AL → ProductionOrder PO-0436 → CustomerOrder CO-02567 → Dealer D25 / Customer C1467
- **Summary:** The message reports a supplier delay of surround-view camera kit (CAM-360) from Orbit Optics (SUP-11) into Wacky Wheels Huntsville (P_AL) from 2027-03-29 until 2027-04-01 on shipment SH-0256. Affected records: 6 production orders and 54 customer orders. The tower completed 4 reschedules, 2 transfers, 26 dealer notices, and 10 loaner assignments.

### E-10 — TC1 Supplier Delay — PASS
> Huntsville line is waiting on 60 kWh battery packs from Lumen. Original drop was Monday Mar 29, new ETA is Thursday Apr 1 because of a truck breakdown.

- **Read as:** `supplier_delay` (reader: qwen3:1.7b)
  - supplier_delay: `{"supplier_id": "SUP-18", "part_id": "BATT-60", "plant_id": "P_AL", "shipment_id": "SH-0248", "blocked_from": "2027-03-29", "blocked_until": "2027-04-01", "model_reason": "qwen3:1.7b: supplier_delay: The Huntsville line is waiting on 60 kWh battery packs from Lumen, with the original delivery date replaced by a new ETA of Thursday April 1 due to a truck breakdown."}`
- **Expected:** [{"kind": "supplier_delay", "supplier_id": "SUP-18", "part_id": "BATT-60", "plant_id": "P_AL", "blocked_from": "2027-03-29", "blocked_until": "2027-04-01"}]; escalate=false
- **Calls:** {'mes.reschedule': 3, 'dealer.notify': 18, 'crm.assign_loaner': 7}
- ✅ summary and reason recorded
- ✅ no failed tool calls
- ✅ graph path starts at the Shipment
- ✅ ≥3 kinds of action (rule 9): 3
- **Graph path (1 of 58):** Shipment SH-0248 → Part BATT-60 → Model NOVA (BOM) → Plant P_AL → ProductionOrder PO-0437 → CustomerOrder CO-02575 → Dealer D04 / Customer C6785
- **Summary:** The message reports a supplier delay of 60 kWh battery pack (BATT-60) from Lumen Cells (SUP-18) into Wacky Wheels Huntsville (P_AL) from 2027-03-29 until 2027-04-01 on shipment SH-0248. Affected records: 3 production orders and 29 customer orders. The tower completed 3 reschedules, 18 dealer notices, and 7 loaner assignments.

### E-11 — TC2 Plant Outage — PASS
> Jackson update: a power failure. We're dark from Friday Mar 26 through Tuesday Mar 30; the line restarts the following working day.

- **Read as:** `plant_outage` (reader: qwen3:1.7b)
  - plant_outage: `{"plant_id": "P_MS", "outage_start": "2027-03-26", "outage_end": "2027-03-30", "model_reason": "qwen3:1.7b: A power failure caused the plant to be dark from Friday, March 26, through Tuesday, March 30, and the line will restart the following working day."}`
- **Expected:** [{"kind": "plant_outage", "plant_id": "P_MS", "outage_start": "2027-03-26", "outage_end": "2027-03-30"}]; escalate=false
- **Calls:** {'mes.reschedule': 6, 'mes.transfer': 3, 'dealer.notify': 36, 'crm.assign_loaner': 17}
- ✅ summary and reason recorded
- ✅ no failed tool calls
- ✅ outage path Plant → PO → CO → Dealer / Customer
- ✅ ≥3 kinds of action (rule 9): 4
- **Graph path (1 of 64):** Plant P_MS → ProductionOrder PO-0253 → CustomerOrder CO-01460 → Dealer D02 / Customer C5325
- **Summary:** The message reports a plant outage at Wacky Wheels Jackson (P_MS) from 2027-03-26 through 2027-03-30. Affected records: 9 production orders and 79 customer orders. The tower completed 6 reschedules, 3 transfers, 36 dealer notices, and 17 loaner assignments.

### E-12 — TC1 Supplier Delay — PASS
> Subject: Shipment SH-0182 delayed
From: dispatch@orbit.example

Our shipment SH-0182 of CAM-360 (surround-view camera kit) for Wacky Wheels Princeton (P_IN) was due 2027-03-15 and will now arrive 2027-03-18. Reason: port congestion.

- **Read as:** `supplier_delay` (reader: qwen3:1.7b)
  - supplier_delay: `{"supplier_id": "SUP-11", "part_id": "CAM-360", "plant_id": "P_IN", "shipment_id": "SH-0182", "blocked_from": "2027-03-15", "blocked_until": "2027-03-18", "model_reason": "qwen3:1.7b: A shipment of CAM-360 for Wacky Wheels Princeton (P_IN) was delayed from the 2027-03-15 original date to 2027-03-18 due to port congestion, which is a cause of the delay."}`
- **Expected:** [{"kind": "supplier_delay", "supplier_id": "SUP-11", "part_id": "CAM-360", "plant_id": "P_IN", "shipment_id": "SH-0182", "blocked_from": "2027-03-15", "blocked_until": "2027-03-18"}]; escalate=false
- **Calls:** {'mes.reschedule': 3, 'dealer.notify': 14, 'crm.assign_loaner': 10}
- ✅ summary and reason recorded
- ✅ no failed tool calls
- ✅ graph path starts at the Shipment
- ✅ ≥3 kinds of action (rule 9): 3
- **Graph path (1 of 52):** Shipment SH-0182 → Part CAM-360 → Model VOYAGER (BOM) → Plant P_IN → ProductionOrder PO-0316 → CustomerOrder CO-01756 → Dealer D07 / Customer C4130
- **Summary:** The message reports a supplier delay of surround-view camera kit (CAM-360) from Orbit Optics (SUP-11) into Wacky Wheels Princeton (P_IN) from 2027-03-15 until 2027-03-18 on shipment SH-0182. Affected records: 3 production orders and 26 customer orders. The tower completed 3 reschedules, 14 dealer notices, and 10 loaner assignments.

### E-13 — TC6 Unconfirmed Report — PASS
> Someone on the floor mentioned a possible shortage of something electronic sometime soon. Not confirmed by anyone.

- **Read as:** `unconfirmed` (reader: qwen3:1.7b)
  - unconfirmed: `{"model_reason": "qwen3:1.7b: The message reports a possible shortage of something electronic that has not been confirmed by anyone, indicating uncertainty about the actual situation."}`
- **Expected:** no incident; escalate=true
- **Calls:** {'escalate': 1}
- ✅ summary and reason recorded
- ✅ no failed tool calls
- ✅ escalate only, no writes
- ✅ escalation gives a reason
- **Summary:** The report is not safe to act on: The message reports a possible shortage of something electronic that has not been confirmed by anyone, indicating uncertainty about the actual situation. It is escalated for a human to confirm. No operational records were changed. The tower escalated the report and wrote nothing else.

### E-14 — TC3 Quality Hold — PASS
> Quality alert: Atlas says the heavy-duty wiring harness sent to the Texas plant had a moisture contamination. Anything built Monday Feb 22 through Wednesday Feb 24 is suspect.

- **Read as:** `quality_hold` (reader: qwen3:1.7b)
  - quality_hold: `{"supplier_id": "SUP-07", "part_id": "HARN-B", "plant_id": "P_TX", "lot_id": "LOT-0017", "build_start": "2027-02-22", "build_end": "2027-02-24", "model_reason": "qwen3:1.7b: The message reports that parts (heavy-duty wiring harness) are contaminated with moisture and will be held due to defects, affecting vehicles built from Monday Feb 22 through Wednesday Feb 24."}`
- **Expected:** [{"kind": "quality_hold", "lots": ["LOT-0017"]}]; escalate=false
- **Calls:** {'quality.hold_lot': 1, 'dealer.stop_sale': 36, 'crm.notify_customer': 94}
- ✅ summary and reason recorded
- ✅ no failed tool calls
- ✅ lot path Lot → PO → Vehicle → Dealer / Customer
- ✅ ≥3 kinds of action (rule 9): 3
- **Graph path (1 of 32):** Lot LOT-0017 → Part HARN-B → Supplier SUP-07 → Plant P_TX
- **Summary:** The message reports a quality hold on lot LOT-0017 at Wacky Wheels San Antonio (P_TX) for builds 2027-02-22 through 2027-02-24. Affected records: 181 quality records. The tower completed 1 lot hold, 36 stop-sales, and 94 customer notices.

### E-15 — TC3 Quality Hold — PASS
> QUALITY BULLETIN QB-368: Lot LOT-0191 (CHIP-IVI, supplier SUP-12) installed at P_IN on vehicles built 2027-03-02 to 2027-03-03 has a faulty weld. Place the lot on hold, stop sale of unsold vehicles and contact owners.

- **Read as:** `quality_hold` (reader: qwen3:1.7b)
  - quality_hold: `{"supplier_id": "SUP-12", "part_id": "CHIP-IVI", "plant_id": "P_IN", "lot_id": "LOT-0191", "build_start": "2027-03-02", "build_end": "2027-03-03", "model_reason": "qwen3:1.7b: The message reports a quality issue with a lot of chips installed in vehicles, causing the lot to be placed on hold, vehicles to be stopped from being sold, and contact with owners. This is a quality_hold situation as the defect is identified in the parts used in the vehicles."}`
- **Expected:** [{"kind": "quality_hold", "lots": ["LOT-0191"]}]; escalate=false
- **Calls:** {'quality.hold_lot': 1, 'dealer.stop_sale': 25, 'crm.notify_customer': 76}
- ✅ summary and reason recorded
- ✅ no failed tool calls
- ✅ lot path Lot → PO → Vehicle → Dealer / Customer
- ✅ ≥3 kinds of action (rule 9): 3
- **Graph path (1 of 32):** Lot LOT-0191 → Part CHIP-IVI → Supplier SUP-12 → Plant P_IN
- **Summary:** The message reports a quality hold on lot LOT-0191 at Wacky Wheels Princeton (P_IN) for builds 2027-03-02 through 2027-03-03. Affected records: 117 quality records. The tower completed 1 lot hold, 25 stop-sales, and 76 customer notices.

