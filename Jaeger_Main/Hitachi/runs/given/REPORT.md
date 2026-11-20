# Given test cases — the 15 given events

Each event is graded twice:

1. **Effects**: the action log is compared with hand-written expected answers by an independent grader that works from the company tables. It checks the right orders moved and no others, slots after the disruption, transfers only when the home plant is full, one notice per dealer with exactly its orders, loaners by tier, priority and pool, the lots held, stop-sale VINs and owners notified.
2. **Evidence**: the graph path, reasons and action kinds the docx asks for per test case.

## Summary by docx test case

| Test case | Events | Rule reader: effects | AI model: effects | Evidence | Required evidence |
|---|---|---|---|---|---|
| TC1 Supplier Delay | E-09, E-10, E-12 | 3/3 | 3/3 | ✅ | Shipment → Part → Model (BOM) → ProductionOrder → CustomerOrder → Dealer / Customer |
| TC2 Plant Outage | E-04, E-08, E-11 | 3/3 | 3/3 | ✅ | Plant → ProductionOrder → CustomerOrder → Dealer / Customer |
| TC3 Quality Hold | E-03, E-14, E-15 | 3/3 | 3/3 | ✅ | Lot → ProductionOrder → Vehicle → Dealer / Customer |
| TC4 Noise | E-05, E-06, E-07 | 3/3 | 3/3 | ✅ | the reason the event was judged not relevant |
| TC5 Compound Incident | E-01 | 1/1 | 1/1 | ✅ | one graph path per incident |
| TC6 Unconfirmed Report | E-02, E-13 | 2/2 | 2/2 | ✅ | the reason the report was not actionable |

- **Rule reader**: 15/15 events pass on effects · 768 tool calls · 0 failed
- **AI model**: 15/15 events pass on effects · 768 tool calls · 0 failed

## Details — Rule reader

### E-01 — TC5 Compound Incident — PASS
> Morning digest, two items. (1) San Antonio update: a software outage on the line. We're dark from next Friday through Monday Mar 22; the line restarts the following working day. (2) Quick heads up from Quanta: the infotainment chip run for Princeton can't make it next Monday. Carrier says next Friday now (severe weather on the route).

- **Read as:** plant outage + supplier delay (reader: Rule reader)
  - plant outage: plant P_TX, outage start 2027-03-19, outage end 2027-03-22
  - supplier delay: supplier SUP-12, part CHIP-IVI, plant P_IN, shipment SH-0190, blocked from 2027-03-15, blocked until 2027-03-19
- **Expected:** plant outage: plant P_TX, outage start 2027-03-19, outage end 2027-03-22; supplier delay: supplier SUP-12, part CHIP-IVI, plant P_IN, blocked from 2027-03-15, blocked until 2027-03-19; no escalation
- **Calls:** reschedule 14, dealer notice 41, loaner 26
- ✅ summary and reason recorded
- ✅ no failed tool calls
- ✅ outage path Plant → PO → CO → Dealer / Customer
- ✅ delay path for the second incident
- ✅ ≥3 kinds of action (rule 9): 3
- **Graph path (1 of 96):** Plant P_TX → ProductionOrder PO-0058 → CustomerOrder CO-00247 → Dealer D18 / Customer C6387
- **Summary:** The message reports a plant outage at Wacky Wheels San Antonio (P_TX) from 2027-03-19 through 2027-03-22 and a supplier delay of infotainment chip (CHIP-IVI) from Quanta Silicon (SUP-12) into Wacky Wheels Princeton (P_IN) from 2027-03-15 until 2027-03-19 on shipment SH-0190. Affected records: 14 production orders and 122 customer orders. The tower completed 14 reschedules, 41 dealer notices, and 26 loaner assignments.

### E-02 — TC6 Unconfirmed Report — PASS
> Rumor from a supplier rep: something may be off with a seat material coming up. No dates, no details, nothing confirmed.

- **Read as:** unconfirmed (reader: Rule reader)
  - unconfirmed: no details
- **Expected:** no incident; escalate to a human
- **Calls:** escalate 1
- ✅ summary and reason recorded
- ✅ no failed tool calls
- ✅ escalate only, no writes
- ✅ escalation gives a reason
- **Summary:** The report is not safe to act on because it is unconfirmed (nothing confirmed, rumor, may be off, no dates) and does not name a specific shipment, outage, or lot to change. No operational records were changed. The tower escalated the report and wrote nothing else.

### E-03 — TC3 Quality Hold — PASS
> Quality alert: Kestrel says the infotainment chip sent to Jackson had a faulty weld. Anything built Thursday Feb 25 through last Monday is suspect.

- **Read as:** quality hold (reader: Rule reader)
  - quality hold: supplier SUP-06, part CHIP-IVI, plant P_MS, build start 2027-02-25, build end 2027-03-01
- **Expected:** quality hold: lots LOT-0130; no escalation
- **Calls:** lot hold 1, stop sale 37, owner notice 150
- ✅ summary and reason recorded
- ✅ no failed tool calls
- ✅ lot path Lot → PO → Vehicle → Dealer / Customer
- ✅ ≥3 kinds of action (rule 9): 3
- **Graph path (1 of 32):** Lot LOT-0130 → Part CHIP-IVI → Supplier SUP-06 → Plant P_MS
- **Summary:** The message reports a quality hold on infotainment chip (CHIP-IVI) at Wacky Wheels Jackson (P_MS) for builds 2027-02-25 through 2027-03-01. Affected records: 261 quality records. The tower completed 1 lot hold, 37 stop-sales, and 150 customer notices.

### E-04 — TC2 Plant Outage — PASS
> The Kentucky plant update: a software outage on the line. We're dark from next Tuesday through next Thursday; the line restarts the following working day.

- **Read as:** plant outage (reader: Rule reader)
  - plant outage: plant P_KY, outage start 2027-03-16, outage end 2027-03-18
- **Expected:** plant outage: plant P_KY, outage start 2027-03-16, outage end 2027-03-18; no escalation
- **Calls:** reschedule 9, dealer notice 32, loaner 18
- ✅ summary and reason recorded
- ✅ no failed tool calls
- ✅ outage path Plant → PO → CO → Dealer / Customer
- ✅ ≥3 kinds of action (rule 9): 3
- **Graph path (1 of 64):** Plant P_KY → ProductionOrder PO-0139 → CustomerOrder CO-00717 → Dealer D42 / Customer C5240
- **Summary:** The message reports a plant outage at Wacky Wheels Lexington (P_KY) from 2027-03-16 through 2027-03-18. Affected records: 9 production orders and 79 customer orders. The tower completed 9 reschedules, 32 dealer notices, and 18 loaner assignments.

### E-05 — TC4 Noise — PASS
> Dealer Amarillo, TX asks where to find the new brochure PDF.

- **Read as:** noise (reader: Rule reader)
  - noise: no details
- **Expected:** no incident; no escalation
- **Calls:** none
- ✅ summary and reason recorded
- ✅ no failed tool calls
- ✅ no calls at all
- **Summary:** "Dealer Amarillo, TX asks where to find the new brochure PDF" is not an operational disruption because it does not report a supplier delay, a plant outage, or a quality hold. No operational records are affected. Nothing was written.

### E-06 — TC4 Noise — PASS
> Dealer Little Rock, AR asks where to find the new brochure PDF.

- **Read as:** noise (reader: Rule reader)
  - noise: no details
- **Expected:** no incident; no escalation
- **Calls:** none
- ✅ summary and reason recorded
- ✅ no failed tool calls
- ✅ no calls at all
- **Summary:** "Dealer Little Rock, AR asks where to find the new brochure PDF" is not an operational disruption because it does not report a supplier delay, a plant outage, or a quality hold. No operational records are affected. Nothing was written.

### E-07 — TC4 Noise — PASS
> Dealer Pensacola, FL asks where to find the new brochure PDF.

- **Read as:** noise (reader: Rule reader)
  - noise: no details
- **Expected:** no incident; no escalation
- **Calls:** none
- ✅ summary and reason recorded
- ✅ no failed tool calls
- ✅ no calls at all
- **Summary:** "Dealer Pensacola, FL asks where to find the new brochure PDF" is not an operational disruption because it does not report a supplier delay, a plant outage, or a quality hold. No operational records are affected. Nothing was written.

### E-08 — TC2 Plant Outage — PASS
> Plant operations alert: Wacky Wheels Lexington (P_KY) lost production to a power failure. Production is stopped from 2027-03-24 through 2027-03-25 inclusive.

- **Read as:** plant outage (reader: Rule reader)
  - plant outage: plant P_KY, outage start 2027-03-24, outage end 2027-03-25
- **Expected:** plant outage: plant P_KY, outage start 2027-03-24, outage end 2027-03-25; no escalation
- **Calls:** reschedule 6, dealer notice 25, loaner 15
- ✅ summary and reason recorded
- ✅ no failed tool calls
- ✅ outage path Plant → PO → CO → Dealer / Customer
- ✅ ≥3 kinds of action (rule 9): 3
- **Graph path (1 of 64):** Plant P_KY → ProductionOrder PO-0157 → CustomerOrder CO-00876 → Dealer D07 / Customer C5020
- **Summary:** The message reports a plant outage at Wacky Wheels Lexington (P_KY) from 2027-03-24 through 2027-03-25. Affected records: 6 production orders and 56 customer orders. The tower completed 6 reschedules, 25 dealer notices, and 15 loaner assignments.

### E-09 — TC1 Supplier Delay — PASS
> Quick heads up from Orbit: the surround-view cameras run for Huntsville can't make it Monday Mar 29. Carrier says Thursday Apr 1 now (a customs inspection).

- **Read as:** supplier delay (reader: Rule reader)
  - supplier delay: supplier SUP-11, part CAM-360, plant P_AL, shipment SH-0256, blocked from 2027-03-29, blocked until 2027-04-01
- **Expected:** supplier delay: supplier SUP-11, part CAM-360, plant P_AL, blocked from 2027-03-29, blocked until 2027-04-01; no escalation
- **Calls:** reschedule 4, transfer 2, dealer notice 26, loaner 10
- ✅ summary and reason recorded
- ✅ no failed tool calls
- ✅ graph path starts at the Shipment
- ✅ ≥3 kinds of action (rule 9): 4
- **Graph path (1 of 64):** Shipment SH-0256 → Part CAM-360 → Model SUMMIT (BOM) → Plant P_AL → ProductionOrder PO-0436 → CustomerOrder CO-02567 → Dealer D25 / Customer C1467
- **Summary:** The message reports a supplier delay of surround-view camera kit (CAM-360) from Orbit Optics (SUP-11) into Wacky Wheels Huntsville (P_AL) from 2027-03-29 until 2027-04-01 on shipment SH-0256. Affected records: 6 production orders and 54 customer orders. The tower completed 4 reschedules, 2 transfers, 26 dealer notices, and 10 loaner assignments.

### E-10 — TC1 Supplier Delay — PASS
> Huntsville line is waiting on 60 kWh battery packs from Lumen. Original drop was Monday Mar 29, new ETA is Thursday Apr 1 because of a truck breakdown.

- **Read as:** supplier delay (reader: Rule reader)
  - supplier delay: supplier SUP-18, part BATT-60, plant P_AL, shipment SH-0248, blocked from 2027-03-29, blocked until 2027-04-01
- **Expected:** supplier delay: supplier SUP-18, part BATT-60, plant P_AL, blocked from 2027-03-29, blocked until 2027-04-01; no escalation
- **Calls:** reschedule 3, dealer notice 18, loaner 7
- ✅ summary and reason recorded
- ✅ no failed tool calls
- ✅ graph path starts at the Shipment
- ✅ ≥3 kinds of action (rule 9): 3
- **Graph path (1 of 58):** Shipment SH-0248 → Part BATT-60 → Model NOVA (BOM) → Plant P_AL → ProductionOrder PO-0437 → CustomerOrder CO-02575 → Dealer D04 / Customer C6785
- **Summary:** The message reports a supplier delay of 60 kWh battery pack (BATT-60) from Lumen Cells (SUP-18) into Wacky Wheels Huntsville (P_AL) from 2027-03-29 until 2027-04-01 on shipment SH-0248. Affected records: 3 production orders and 29 customer orders. The tower completed 3 reschedules, 18 dealer notices, and 7 loaner assignments.

### E-11 — TC2 Plant Outage — PASS
> Jackson update: a power failure. We're dark from Friday Mar 26 through Tuesday Mar 30; the line restarts the following working day.

- **Read as:** plant outage (reader: Rule reader)
  - plant outage: plant P_MS, outage start 2027-03-26, outage end 2027-03-30
- **Expected:** plant outage: plant P_MS, outage start 2027-03-26, outage end 2027-03-30; no escalation
- **Calls:** reschedule 6, transfer 3, dealer notice 36, loaner 17
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

- **Read as:** supplier delay (reader: Rule reader)
  - supplier delay: supplier SUP-11, part CAM-360, plant P_IN, shipment SH-0182, blocked from 2027-03-15, blocked until 2027-03-18
- **Expected:** supplier delay: supplier SUP-11, part CAM-360, plant P_IN, shipment SH-0182, blocked from 2027-03-15, blocked until 2027-03-18; no escalation
- **Calls:** reschedule 3, dealer notice 14, loaner 10
- ✅ summary and reason recorded
- ✅ no failed tool calls
- ✅ graph path starts at the Shipment
- ✅ ≥3 kinds of action (rule 9): 3
- **Graph path (1 of 52):** Shipment SH-0182 → Part CAM-360 → Model VOYAGER (BOM) → Plant P_IN → ProductionOrder PO-0316 → CustomerOrder CO-01756 → Dealer D07 / Customer C4130
- **Summary:** The message reports a supplier delay of surround-view camera kit (CAM-360) from Orbit Optics (SUP-11) into Wacky Wheels Princeton (P_IN) from 2027-03-15 until 2027-03-18 on shipment SH-0182. Affected records: 3 production orders and 26 customer orders. The tower completed 3 reschedules, 14 dealer notices, and 10 loaner assignments.

### E-13 — TC6 Unconfirmed Report — PASS
> Someone on the floor mentioned a possible shortage of something electronic sometime soon. Not confirmed by anyone.

- **Read as:** unconfirmed (reader: Rule reader)
  - unconfirmed: no details
- **Expected:** no incident; escalate to a human
- **Calls:** escalate 1
- ✅ summary and reason recorded
- ✅ no failed tool calls
- ✅ escalate only, no writes
- ✅ escalation gives a reason
- **Summary:** The report is not safe to act on because it is unconfirmed (not confirmed, someone on the floor mentioned, someone on the floor) and does not name a specific shipment, outage, or lot to change. No operational records were changed. The tower escalated the report and wrote nothing else.

### E-14 — TC3 Quality Hold — PASS
> Quality alert: Atlas says the heavy-duty wiring harness sent to the Texas plant had a moisture contamination. Anything built Monday Feb 22 through Wednesday Feb 24 is suspect.

- **Read as:** quality hold (reader: Rule reader)
  - quality hold: supplier SUP-07, part HARN-B, plant P_TX, build start 2027-02-22, build end 2027-02-24
- **Expected:** quality hold: lots LOT-0017; no escalation
- **Calls:** lot hold 1, stop sale 36, owner notice 94
- ✅ summary and reason recorded
- ✅ no failed tool calls
- ✅ lot path Lot → PO → Vehicle → Dealer / Customer
- ✅ ≥3 kinds of action (rule 9): 3
- **Graph path (1 of 32):** Lot LOT-0017 → Part HARN-B → Supplier SUP-07 → Plant P_TX
- **Summary:** The message reports a quality hold on heavy-duty wiring harness (HARN-B) at Wacky Wheels San Antonio (P_TX) for builds 2027-02-22 through 2027-02-24. Affected records: 181 quality records. The tower completed 1 lot hold, 36 stop-sales, and 94 customer notices.

### E-15 — TC3 Quality Hold — PASS
> QUALITY BULLETIN QB-368: Lot LOT-0191 (CHIP-IVI, supplier SUP-12) installed at P_IN on vehicles built 2027-03-02 to 2027-03-03 has a faulty weld. Place the lot on hold, stop sale of unsold vehicles and contact owners.

- **Read as:** quality hold (reader: Rule reader)
  - quality hold: supplier SUP-12, part CHIP-IVI, plant P_IN, lot LOT-0191, build start 2027-03-02, build end 2027-03-03
- **Expected:** quality hold: lots LOT-0191; no escalation
- **Calls:** lot hold 1, stop sale 25, owner notice 76
- ✅ summary and reason recorded
- ✅ no failed tool calls
- ✅ lot path Lot → PO → Vehicle → Dealer / Customer
- ✅ ≥3 kinds of action (rule 9): 3
- **Graph path (1 of 32):** Lot LOT-0191 → Part CHIP-IVI → Supplier SUP-12 → Plant P_IN
- **Summary:** The message reports a quality hold on lot LOT-0191 at Wacky Wheels Princeton (P_IN) for builds 2027-03-02 through 2027-03-03. Affected records: 117 quality records. The tower completed 1 lot hold, 25 stop-sales, and 76 customer notices.

## Details — AI model

### E-01 — TC5 Compound Incident — PASS
> Morning digest, two items. (1) San Antonio update: a software outage on the line. We're dark from next Friday through Monday Mar 22; the line restarts the following working day. (2) Quick heads up from Quanta: the infotainment chip run for Princeton can't make it next Monday. Carrier says next Friday now (severe weather on the route).

- **Read as:** plant outage + supplier delay (reader: AI model)
  - plant outage: plant P_TX, outage start 2027-03-19, outage end 2027-03-22
  - supplier delay: supplier SUP-12, part CHIP-IVI, plant P_IN, shipment SH-0190, blocked from 2027-03-15, blocked until 2027-03-19
- **Expected:** plant outage: plant P_TX, outage start 2027-03-19, outage end 2027-03-22; supplier delay: supplier SUP-12, part CHIP-IVI, plant P_IN, blocked from 2027-03-15, blocked until 2027-03-19; no escalation
- **Calls:** reschedule 14, dealer notice 41, loaner 26
- ✅ summary and reason recorded
- ✅ no failed tool calls
- ✅ outage path Plant → PO → CO → Dealer / Customer
- ✅ delay path for the second incident
- ✅ ≥3 kinds of action (rule 9): 3
- **Graph path (1 of 96):** Plant P_TX → ProductionOrder PO-0058 → CustomerOrder CO-00247 → Dealer D18 / Customer C6387
- **Summary:** The message reports a plant outage at Wacky Wheels San Antonio (P_TX) from 2027-03-19 through 2027-03-22 and a supplier delay of infotainment chip (CHIP-IVI) from Quanta Silicon (SUP-12) into Wacky Wheels Princeton (P_IN) from 2027-03-15 until 2027-03-19 on shipment SH-0190. Affected records: 14 production orders and 122 customer orders. The tower completed 14 reschedules, 41 dealer notices, and 26 loaner assignments.

### E-02 — TC6 Unconfirmed Report — PASS
> Rumor from a supplier rep: something may be off with a seat material coming up. No dates, no details, nothing confirmed.

- **Read as:** unconfirmed (reader: AI model)
  - unconfirmed: no details
- **Expected:** no incident; escalate to a human
- **Calls:** escalate 1
- ✅ summary and reason recorded
- ✅ no failed tool calls
- ✅ escalate only, no writes
- ✅ escalation gives a reason
- **Summary:** The report is not safe to act on: Rumor from a supplier rep: something may be off with a seat material coming up. No dates, no details, nothing confirmed. It is escalated for a human to confirm. No operational records were changed. The tower escalated the report and wrote nothing else.

### E-03 — TC3 Quality Hold — PASS
> Quality alert: Kestrel says the infotainment chip sent to Jackson had a faulty weld. Anything built Thursday Feb 25 through last Monday is suspect.

- **Read as:** quality hold (reader: AI model)
  - quality hold: supplier SUP-06, part CHIP-IVI, plant P_MS, lot LOT-0130, build start 2027-02-25, build end 2027-03-01
- **Expected:** quality hold: lots LOT-0130; no escalation
- **Calls:** lot hold 1, stop sale 37, owner notice 150
- ✅ summary and reason recorded
- ✅ no failed tool calls
- ✅ lot path Lot → PO → Vehicle → Dealer / Customer
- ✅ ≥3 kinds of action (rule 9): 3
- **Graph path (1 of 32):** Lot LOT-0130 → Part CHIP-IVI → Supplier SUP-06 → Plant P_MS
- **Summary:** The message reports a quality hold on lot LOT-0130 at Wacky Wheels Jackson (P_MS) for builds 2027-02-25 through 2027-03-01. Affected records: 261 quality records. The tower completed 1 lot hold, 37 stop-sales, and 150 customer notices.

### E-04 — TC2 Plant Outage — PASS
> The Kentucky plant update: a software outage on the line. We're dark from next Tuesday through next Thursday; the line restarts the following working day.

- **Read as:** plant outage (reader: AI model)
  - plant outage: plant P_KY, outage start 2027-03-16, outage end 2027-03-18
- **Expected:** plant outage: plant P_KY, outage start 2027-03-16, outage end 2027-03-18; no escalation
- **Calls:** reschedule 9, dealer notice 32, loaner 18
- ✅ summary and reason recorded
- ✅ no failed tool calls
- ✅ outage path Plant → PO → CO → Dealer / Customer
- ✅ ≥3 kinds of action (rule 9): 3
- **Graph path (1 of 64):** Plant P_KY → ProductionOrder PO-0139 → CustomerOrder CO-00717 → Dealer D42 / Customer C5240
- **Summary:** The message reports a plant outage at Wacky Wheels Lexington (P_KY) from 2027-03-16 through 2027-03-18. Affected records: 9 production orders and 79 customer orders. The tower completed 9 reschedules, 32 dealer notices, and 18 loaner assignments.

### E-05 — TC4 Noise — PASS
> Dealer Amarillo, TX asks where to find the new brochure PDF.

- **Read as:** noise (reader: AI model)
  - noise: no details
- **Expected:** no incident; no escalation
- **Calls:** none
- ✅ summary and reason recorded
- ✅ no failed tool calls
- ✅ no calls at all
- **Summary:** No action: This is noise as it does not relate to parts deliveries, a plant's ability to build, or part quality. No operational records are affected. Nothing was written.

### E-06 — TC4 Noise — PASS
> Dealer Little Rock, AR asks where to find the new brochure PDF.

- **Read as:** noise (reader: AI model)
  - noise: no details
- **Expected:** no incident; no escalation
- **Calls:** none
- ✅ summary and reason recorded
- ✅ no failed tool calls
- ✅ no calls at all
- **Summary:** No action: This is noise as it does not relate to parts deliveries, a plant's ability to build, or part quality. No operational records are affected. Nothing was written.

### E-07 — TC4 Noise — PASS
> Dealer Pensacola, FL asks where to find the new brochure PDF.

- **Read as:** noise (reader: AI model)
  - noise: no details
- **Expected:** no incident; no escalation
- **Calls:** none
- ✅ summary and reason recorded
- ✅ no failed tool calls
- ✅ no calls at all
- **Summary:** No action: This is a request for information about a brochure PDF, which does not relate to parts deliveries, a plant's ability to build, or part quality. No operational records are affected. Nothing was written.

### E-08 — TC2 Plant Outage — PASS
> Plant operations alert: Wacky Wheels Lexington (P_KY) lost production to a power failure. Production is stopped from 2027-03-24 through 2027-03-25 inclusive.

- **Read as:** plant outage (reader: AI model)
  - plant outage: plant P_KY, outage start 2027-03-24, outage end 2027-03-25
- **Expected:** plant outage: plant P_KY, outage start 2027-03-24, outage end 2027-03-25; no escalation
- **Calls:** reschedule 6, dealer notice 25, loaner 15
- ✅ summary and reason recorded
- ✅ no failed tool calls
- ✅ outage path Plant → PO → CO → Dealer / Customer
- ✅ ≥3 kinds of action (rule 9): 3
- **Graph path (1 of 64):** Plant P_KY → ProductionOrder PO-0157 → CustomerOrder CO-00876 → Dealer D07 / Customer C5020
- **Summary:** The message reports a plant outage at Wacky Wheels Lexington (P_KY) from 2027-03-24 through 2027-03-25. Affected records: 6 production orders and 56 customer orders. The tower completed 6 reschedules, 25 dealer notices, and 15 loaner assignments.

### E-09 — TC1 Supplier Delay — PASS
> Quick heads up from Orbit: the surround-view cameras run for Huntsville can't make it Monday Mar 29. Carrier says Thursday Apr 1 now (a customs inspection).

- **Read as:** supplier delay (reader: AI model)
  - supplier delay: supplier SUP-11, part CAM-360, plant P_AL, shipment SH-0256, blocked from 2027-03-29, blocked until 2027-04-01
- **Expected:** supplier delay: supplier SUP-11, part CAM-360, plant P_AL, blocked from 2027-03-29, blocked until 2027-04-01; no escalation
- **Calls:** reschedule 4, transfer 2, dealer notice 26, loaner 10
- ✅ summary and reason recorded
- ✅ no failed tool calls
- ✅ graph path starts at the Shipment
- ✅ ≥3 kinds of action (rule 9): 4
- **Graph path (1 of 64):** Shipment SH-0256 → Part CAM-360 → Model SUMMIT (BOM) → Plant P_AL → ProductionOrder PO-0436 → CustomerOrder CO-02567 → Dealer D25 / Customer C1467
- **Summary:** The message reports a supplier delay of surround-view camera kit (CAM-360) from Orbit Optics (SUP-11) into Wacky Wheels Huntsville (P_AL) from 2027-03-29 until 2027-04-01 on shipment SH-0256. Affected records: 6 production orders and 54 customer orders. The tower completed 4 reschedules, 2 transfers, 26 dealer notices, and 10 loaner assignments.

### E-10 — TC1 Supplier Delay — PASS
> Huntsville line is waiting on 60 kWh battery packs from Lumen. Original drop was Monday Mar 29, new ETA is Thursday Apr 1 because of a truck breakdown.

- **Read as:** supplier delay (reader: AI model)
  - supplier delay: supplier SUP-18, part BATT-60, plant P_AL, shipment SH-0248, blocked from 2027-03-29, blocked until 2027-04-01
- **Expected:** supplier delay: supplier SUP-18, part BATT-60, plant P_AL, blocked from 2027-03-29, blocked until 2027-04-01; no escalation
- **Calls:** reschedule 3, dealer notice 18, loaner 7
- ✅ summary and reason recorded
- ✅ no failed tool calls
- ✅ graph path starts at the Shipment
- ✅ ≥3 kinds of action (rule 9): 3
- **Graph path (1 of 58):** Shipment SH-0248 → Part BATT-60 → Model NOVA (BOM) → Plant P_AL → ProductionOrder PO-0437 → CustomerOrder CO-02575 → Dealer D04 / Customer C6785
- **Summary:** The message reports a supplier delay of 60 kWh battery pack (BATT-60) from Lumen Cells (SUP-18) into Wacky Wheels Huntsville (P_AL) from 2027-03-29 until 2027-04-01 on shipment SH-0248. Affected records: 3 production orders and 29 customer orders. The tower completed 3 reschedules, 18 dealer notices, and 7 loaner assignments.

### E-11 — TC2 Plant Outage — PASS
> Jackson update: a power failure. We're dark from Friday Mar 26 through Tuesday Mar 30; the line restarts the following working day.

- **Read as:** plant outage (reader: AI model)
  - plant outage: plant P_MS, outage start 2027-03-26, outage end 2027-03-30
- **Expected:** plant outage: plant P_MS, outage start 2027-03-26, outage end 2027-03-30; no escalation
- **Calls:** reschedule 6, transfer 3, dealer notice 36, loaner 17
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

- **Read as:** supplier delay (reader: AI model)
  - supplier delay: supplier SUP-11, part CAM-360, plant P_IN, shipment SH-0182, blocked from 2027-03-15, blocked until 2027-03-18
- **Expected:** supplier delay: supplier SUP-11, part CAM-360, plant P_IN, shipment SH-0182, blocked from 2027-03-15, blocked until 2027-03-18; no escalation
- **Calls:** reschedule 3, dealer notice 14, loaner 10
- ✅ summary and reason recorded
- ✅ no failed tool calls
- ✅ graph path starts at the Shipment
- ✅ ≥3 kinds of action (rule 9): 3
- **Graph path (1 of 52):** Shipment SH-0182 → Part CAM-360 → Model VOYAGER (BOM) → Plant P_IN → ProductionOrder PO-0316 → CustomerOrder CO-01756 → Dealer D07 / Customer C4130
- **Summary:** The message reports a supplier delay of surround-view camera kit (CAM-360) from Orbit Optics (SUP-11) into Wacky Wheels Princeton (P_IN) from 2027-03-15 until 2027-03-18 on shipment SH-0182. Affected records: 3 production orders and 26 customer orders. The tower completed 3 reschedules, 14 dealer notices, and 10 loaner assignments.

### E-13 — TC6 Unconfirmed Report — PASS
> Someone on the floor mentioned a possible shortage of something electronic sometime soon. Not confirmed by anyone.

- **Read as:** unconfirmed (reader: AI model)
  - unconfirmed: no details
- **Expected:** no incident; escalate to a human
- **Calls:** escalate 1
- ✅ summary and reason recorded
- ✅ no failed tool calls
- ✅ escalate only, no writes
- ✅ escalation gives a reason
- **Summary:** The report is not safe to act on: Unconfirmed: Hearsay or hedging (heard, might, apparently, rumor, not confirmed) about a possible problem. It is escalated for a human to confirm. No operational records were changed. The tower escalated the report and wrote nothing else.

### E-14 — TC3 Quality Hold — PASS
> Quality alert: Atlas says the heavy-duty wiring harness sent to the Texas plant had a moisture contamination. Anything built Monday Feb 22 through Wednesday Feb 24 is suspect.

- **Read as:** quality hold (reader: AI model)
  - quality hold: supplier SUP-07, part HARN-B, plant P_TX, lot LOT-0017, build start 2027-02-22, build end 2027-02-24
- **Expected:** quality hold: lots LOT-0017; no escalation
- **Calls:** lot hold 1, stop sale 36, owner notice 94
- ✅ summary and reason recorded
- ✅ no failed tool calls
- ✅ lot path Lot → PO → Vehicle → Dealer / Customer
- ✅ ≥3 kinds of action (rule 9): 3
- **Graph path (1 of 32):** Lot LOT-0017 → Part HARN-B → Supplier SUP-07 → Plant P_TX
- **Summary:** The message reports a quality hold on lot LOT-0017 at Wacky Wheels San Antonio (P_TX) for builds 2027-02-22 through 2027-02-24. Affected records: 181 quality records. The tower completed 1 lot hold, 36 stop-sales, and 94 customer notices.

### E-15 — TC3 Quality Hold — PASS
> QUALITY BULLETIN QB-368: Lot LOT-0191 (CHIP-IVI, supplier SUP-12) installed at P_IN on vehicles built 2027-03-02 to 2027-03-03 has a faulty weld. Place the lot on hold, stop sale of unsold vehicles and contact owners.

- **Read as:** quality hold (reader: AI model)
  - quality hold: supplier SUP-12, part CHIP-IVI, plant P_IN, lot LOT-0191, build start 2027-03-02, build end 2027-03-03
- **Expected:** quality hold: lots LOT-0191; no escalation
- **Calls:** lot hold 1, stop sale 25, owner notice 76
- ✅ summary and reason recorded
- ✅ no failed tool calls
- ✅ lot path Lot → PO → Vehicle → Dealer / Customer
- ✅ ≥3 kinds of action (rule 9): 3
- **Graph path (1 of 32):** Lot LOT-0191 → Part CHIP-IVI → Supplier SUP-12 → Plant P_IN
- **Summary:** The message reports a quality hold on lot LOT-0191 at Wacky Wheels Princeton (P_IN) for builds 2027-03-02 through 2027-03-03. Affected records: 117 quality records. The tower completed 1 lot hold, 25 stop-sales, and 76 customer notices.

