# Hitachi control tower — held-out tests, set 1

100 cases from `tests/holdout_cases.json`, graded by `tests/run_cases.py` against expected effects computed from the CSVs (not from tower/graph.py).

| Case | Category | rules | qwen3:0.6b | Edge case? |
|---|---|---|---|---|
| H-001 | quality_hold | PASS | PASS |  |
| H-002 | noise | PASS | PASS |  |
| H-003 | supplier_delay | PASS | PASS |  |
| H-004 | noise | PASS | PASS |  |
| H-005 | compound | FAIL ⚠ | PASS |  |
| H-006 | noise | PASS | PASS |  |
| H-007 | supplier_delay | FAIL ⚠ | FAIL ⚠ |  |
| H-008 | compound | FAIL ⚠ | FAIL ⚠ |  |
| H-009 | noise | PASS | PASS |  |
| H-010 | quality_hold | PASS | PASS |  |
| H-011 | plant_outage | PASS | PASS |  |
| H-012 | compound | PASS | PASS |  |
| H-013 | compound | PASS | PASS |  |
| H-014 | supplier_delay | PASS | PASS |  |
| H-015 | quality_hold | FAIL ⚠ | FAIL ⚠ |  |
| H-016 | compound | FAIL | FAIL |  |
| H-017 | plant_outage | PASS | PASS |  |
| H-018 | plant_outage | PASS | PASS |  |
| H-019 | plant_outage | PASS | PASS |  |
| H-020 | supplier_delay | PASS | PASS |  |
| H-021 | noise | PASS | PASS |  |
| H-022 | supplier_delay | PASS | PASS |  |
| H-023 | supplier_delay | FAIL ⚠ | PASS |  |
| H-024 | noise | PASS | PASS |  |
| H-025 | noise | PASS | PASS |  |
| H-026 | supplier_delay | PASS | PASS |  |
| H-027 | unconfirmed | PASS | PASS |  |
| H-028 | compound | PASS | PASS |  |
| H-029 | compound | PASS | PASS |  |
| H-030 | quality_hold | PASS | PASS |  |
| H-031 | quality_hold | PASS | PASS |  |
| H-032 | plant_outage | PASS | PASS |  |
| H-033 | unconfirmed | PASS | PASS |  |
| H-034 | noise | PASS | PASS |  |
| H-035 | compound | PASS | PASS |  |
| H-036 | unconfirmed | PASS | PASS |  |
| H-037 | compound | FAIL ⚠ | PASS |  |
| H-038 | supplier_delay | PASS | PASS |  |
| H-039 | plant_outage | PASS | PASS |  |
| H-040 | quality_hold | PASS | PASS |  |
| H-041 | supplier_delay | PASS | PASS |  |
| H-042 | supplier_delay | FAIL ⚠ | FAIL ⚠ |  |
| H-043 | unconfirmed | PASS | PASS |  |
| H-044 | plant_outage | PASS | PASS |  |
| H-045 | plant_outage | PASS | PASS |  |
| H-046 | supplier_delay | PASS | PASS |  |
| H-047 | supplier_delay | FAIL ⚠ | FAIL ⚠ |  |
| H-048 | plant_outage | PASS | PASS |  |
| H-049 | supplier_delay | FAIL ⚠ | FAIL ⚠ |  |
| H-050 | plant_outage | PASS | PASS |  |
| H-051 | unconfirmed | PASS | PASS |  |
| H-052 | supplier_delay | PASS | PASS |  |
| H-053 | quality_hold | FAIL ⚠ | FAIL ⚠ |  |
| H-054 | supplier_delay | PASS | PASS |  |
| H-055 | unconfirmed | PASS | PASS |  |
| H-056 | quality_hold | PASS | PASS |  |
| H-057 | supplier_delay | FAIL ⚠ | FAIL ⚠ |  |
| H-058 | quality_hold | PASS | PASS |  |
| H-059 | plant_outage | PASS | PASS |  |
| H-060 | noise | PASS | PASS |  |
| H-061 | noise | PASS | PASS |  |
| H-062 | noise | PASS | PASS |  |
| H-063 | noise | PASS | PASS |  |
| H-064 | quality_hold | PASS | PASS |  |
| H-065 | compound | FAIL ⚠ | PASS |  |
| H-066 | noise | PASS | PASS |  |
| H-067 | quality_hold | PASS | PASS |  |
| H-068 | quality_hold | PASS | PASS |  |
| H-069 | quality_hold | PASS | PASS |  |
| H-070 | plant_outage | PASS | PASS |  |
| H-071 | compound | PASS | PASS |  |
| H-072 | compound | FAIL ⚠ | PASS |  |
| H-073 | supplier_delay | FAIL ⚠ | FAIL ⚠ |  |
| H-074 | plant_outage | PASS | PASS |  |
| H-075 | noise | PASS | PASS |  |
| H-076 | quality_hold | PASS | PASS |  |
| H-077 | unconfirmed | PASS | PASS |  |
| H-078 | plant_outage | FAIL ⚠ | PASS |  |
| H-079 | supplier_delay | PASS | PASS |  |
| H-080 | plant_outage | PASS | PASS |  |
| H-081 | quality_hold | PASS | PASS |  |
| H-082 | unconfirmed | FAIL | FAIL |  |
| H-083 | supplier_delay | FAIL ⚠ | FAIL ⚠ |  |
| H-084 | unconfirmed | PASS | PASS |  |
| H-085 | plant_outage | PASS | PASS |  |
| H-086 | plant_outage | FAIL ⚠ | PASS |  |
| H-087 | plant_outage | FAIL ⚠ | PASS |  |
| H-088 | unconfirmed | PASS | PASS |  |
| H-089 | quality_hold | PASS | PASS |  |
| H-090 | compound | FAIL ⚠ | FAIL ⚠ |  |
| H-091 | compound | FAIL | PASS |  |
| H-092 | plant_outage | FAIL ⚠ | FAIL ⚠ |  |
| H-093 | unconfirmed | PASS | PASS |  |
| H-094 | quality_hold | PASS | PASS |  |
| H-095 | plant_outage | PASS | PASS |  |
| H-096 | unconfirmed | PASS | PASS |  |
| H-097 | supplier_delay | FAIL ⚠ | PASS |  |
| H-098 | supplier_delay | PASS | PASS |  |
| H-099 | quality_hold | PASS | PASS |  |
| H-100 | supplier_delay | PASS | PASS |  |

**rules**: 76/100 pass
**qwen3:0.6b**: 86/100 pass

## Details — rules reader

### H-001 — quality_hold — PASS
> Nonconformance report: 20-inch alloy wheels lot LOT-0237 from Cobalt, used at Wacky Wheels Princeton on builds 2/22 to 2027-02-24, shows contaminated grease. Contain and hold.
- Read as: `quality_hold` (reader: rules)
- Stats: {"writes": 67, "calls": 67, "moved": 0, "rescheduled": 0, "transferred": 0, "expected_moves": 0, "dealers": 0, "loaners": 0, "lots": ["LOT-0237"], "stop_sale_vins": 31, "owners": 46}

### H-002 — noise — PASS
> The vending machine on floor 3 is out of order again.
- Read as: `noise` (reader: rules)
- Stats: {"writes": 0, "calls": 0}

### H-003 — supplier_delay — PASS
> Shipment SH-0339: arrival moved from March 22nd to the 24th. Reason: a labor shortage. Supplier: Harbor Seating. Part: SEAT-FAB. Ship to: Greensboro.
- Read as: `supplier_delay` (reader: rules)
- Stats: {"writes": 51, "calls": 51, "moved": 6, "rescheduled": 6, "transferred": 0, "expected_moves": 6, "dealers": 32, "loaners": 13, "lots": [], "stop_sale_vins": 0, "owners": 0}

### H-004 — noise — PASS
> A minor earthquake was felt near Lima, Peru; no damage reported.
- Read as: `noise` (reader: rules)
- Stats: {"writes": 0, "calls": 0}

### H-005 — compound — FAIL
> Daily summary. (1) Fleet sales promotion extended through the end of the quarter. (2) Production at Lexington is suspended starting 3/18 after an electrical fire; we expect to be back up on March 24th.
- Read as: `noise+noise` (reader: rules, rules)
- Stats: {"writes": 0, "calls": 0, "moved": 0, "rescheduled": 0, "transferred": 0, "expected_moves": 12, "dealers": 0, "loaners": 0, "lots": [], "stop_sale_vins": 0, "owners": 0}
- FAIL: incident kinds ['none'] expected ['plant_outage']
- FAIL: 12 affected PO(s) not moved: ['PO-0145', 'PO-0146', 'PO-0147', 'PO-0148', 'PO-0149']
- FAIL: dealer set: extra [], missing ['D01', 'D02', 'D03', 'D06', 'D07']
- FAIL: loaners: extra [], missing ['CO-00770', 'CO-00771', 'CO-00772', 'CO-00787', 'CO-00789']
- warn: only 0 kind(s) of write action (handbook rule 9 wants 3)

### H-006 — noise — PASS
> Please update your email signature to the new logo by end of month.
- Read as: `noise` (reader: rules)
- Stats: {"writes": 0, "calls": 0}

### H-007 — supplier_delay — FAIL
> Voicemail from SUP-01: the 16-inch all-season tires order headed to Jackson is rescheduled from 3/29 to 2027-03-31.
- Read as: `noise` (reader: rules)
- Stats: {"writes": 0, "calls": 0, "moved": 0, "rescheduled": 0, "transferred": 0, "expected_moves": 2, "dealers": 0, "loaners": 0, "lots": [], "stop_sale_vins": 0, "owners": 0}
- FAIL: incident kinds ['none'] expected ['supplier_delay']
- FAIL: 2 affected PO(s) not moved: ['PO-0258', 'PO-0261']
- FAIL: dealer set: extra [], missing ['D01', 'D02', 'D03', 'D04', 'D06']
- FAIL: loaners: extra [], missing ['CO-01501', 'CO-01502', 'CO-01508', 'CO-01529', 'CO-01533']
- warn: only 0 kind(s) of write action (handbook rule 9 wants 3)

### H-008 — compound — FAIL
> Northgate Tire Co flagged porosity in the castings in 17-inch all-season tire shipped to Lexington; vehicles assembled 2 Mar through 3/3 are affected. Also, not sure if true, but a friend at Granite Tire says they may run short on parts soon.
- Read as: `unconfirmed` (reader: rules)
- Stats: {"writes": 0, "calls": 1, "moved": 0, "rescheduled": 0, "transferred": 0, "expected_moves": 0, "dealers": 0, "loaners": 0, "lots": [], "stop_sale_vins": 0, "owners": 0}
- FAIL: incident kinds ['none'] expected ['quality_hold']
- FAIL: lots held [] expected ['LOT-0099']
- FAIL: stop-sale VINs: got 0 expected 59 (extra [], missing ['AUR0001425', 'AUR0001428', 'AUR0001430'])
- FAIL: owners notified: got 0 expected 61 (extra [], missing ['C0110', 'C0157', 'C0169'])
- warn: only 0 kind(s) of write action (handbook rule 9 wants 3)

### H-009 — noise — PASS
> The Lexington plant's open house for families is on Saturday. Refreshments provided.
- Read as: `noise` (reader: rules)
- Stats: {"writes": 0, "calls": 0}

### H-010 — quality_hold — PASS
> Containment request: hold LOT-0205. harness B, delamination. Builds at the Princeton plant between 22 Feb and February 24th.
- Read as: `quality_hold` (reader: rules)
- Stats: {"writes": 67, "calls": 67, "moved": 0, "rescheduled": 0, "transferred": 0, "expected_moves": 0, "dealers": 0, "loaners": 0, "lots": ["LOT-0205"], "stop_sale_vins": 31, "owners": 46}

### H-011 — plant_outage — PASS
> P_TX will be offline Wednesday the 17th through Thursday the 18th because of a chemical spill.
- Read as: `plant_outage` (reader: rules)
- Stats: {"writes": 44, "calls": 44, "moved": 6, "rescheduled": 6, "transferred": 0, "expected_moves": 6, "dealers": 26, "loaners": 12, "lots": [], "stop_sale_vins": 0, "owners": 0}

### H-012 — compound — PASS
> Daily summary. (1) SUP-08 can't ship the brake kit to Wacky Wheels San Antonio on 22 Mar as planned; earliest is March 26th (weather at the port). (2) A minor earthquake was felt near Lima, Peru; no damage reported.
- Read as: `supplier_delay+noise` (reader: rules, rules)
- Stats: {"writes": 76, "calls": 76, "moved": 12, "rescheduled": 12, "transferred": 0, "expected_moves": 12, "dealers": 39, "loaners": 25, "lots": [], "stop_sale_vins": 0, "owners": 0}

### H-013 — compound — PASS
> Sterling can't ship the airbag module to the Kentucky plant on 3/29 as planned; earliest is 31 Mar (weather at the port). Also, the Greensboro plant's open house for families is on Saturday. Refreshments provided.
- Read as: `supplier_delay` (reader: rules)
- Stats: {"writes": 42, "calls": 42, "moved": 6, "rescheduled": 6, "transferred": 0, "expected_moves": 6, "dealers": 26, "loaners": 10, "lots": [], "stop_sale_vins": 0, "owners": 0}

### H-014 — supplier_delay — PASS
> We regret to inform you that delivery of leather seat set to the San Antonio plant, slated for the 22nd, has been postponed until 26 Mar. Regards, Meridian
- Read as: `supplier_delay` (reader: rules)
- Stats: {"writes": 31, "calls": 31, "moved": 4, "rescheduled": 4, "transferred": 0, "expected_moves": 4, "dealers": 21, "loaners": 6, "lots": [], "stop_sale_vins": 0, "owners": 0}

### H-015 — quality_hold — FAIL
> Meridian Seating flagged porosity in the castings in minivan seat set shipped to Wacky Wheels Huntsville; vehicles assembled 2/25 through Monday the 1st are affected.
- Read as: `noise` (reader: rules)
- Stats: {"writes": 0, "calls": 0, "moved": 0, "rescheduled": 0, "transferred": 0, "expected_moves": 0, "dealers": 0, "loaners": 0, "lots": [], "stop_sale_vins": 0, "owners": 0}
- FAIL: incident kinds ['none'] expected ['quality_hold']
- FAIL: lots held [] expected ['LOT-0290']
- FAIL: stop-sale VINs: got 0 expected 39 (extra [], missing ['AUR0003877', 'AUR0003881', 'AUR0003883'])
- FAIL: owners notified: got 0 expected 51 (extra [], missing ['C0186', 'C0318', 'C0325'])
- warn: only 0 kind(s) of write action (handbook rule 9 wants 3)

### H-016 — compound — FAIL
> Two updates: 1) fyi TIRE-20 from Northgate into the Alabama plant is running behind, expected Monday the 15th but more like 2027-03-18 now 2) We regret to inform you that delivery of 17-inch all-season tires to P_KY, slated for Mon 15 March, has been postponed until Thu 18 March. Regards, Northgate Tire Co
- Read as: `supplier_delay+unconfirmed` (reader: rules, rules)
- Stats: {"writes": 32, "calls": 33, "moved": 3, "rescheduled": 3, "transferred": 0, "expected_moves": 9, "dealers": 19, "loaners": 10, "lots": [], "stop_sale_vins": 0, "owners": 0}
- FAIL: incident kinds ['supplier_delay'] expected ['supplier_delay', 'supplier_delay']
- FAIL: escalated although the event is actionable / noise
- FAIL: 6 affected PO(s) not moved: ['PO-0136', 'PO-0138', 'PO-0139', 'PO-0141', 'PO-0142']
- FAIL: dealer set: extra [], missing ['D02', 'D03', 'D06', 'D13', 'D15']
- FAIL: dealer D08 order list: extra [], missing ['CO-00694', 'CO-00695', 'CO-00745']
- FAIL: dealer D12 order list: extra [], missing ['CO-00707']
- FAIL: dealer D23 order list: extra [], missing ['CO-00693', 'CO-00710', 'CO-00720']
- FAIL: dealer D25 order list: extra [], missing ['CO-00718', 'CO-00722', 'CO-00738']
- FAIL: dealer D26 order list: extra [], missing ['CO-00766']
- FAIL: dealer D31 order list: extra [], missing ['CO-00761']
- FAIL: dealer D35 order list: extra [], missing ['CO-00742']
- FAIL: dealer D38 order list: extra [], missing ['CO-00711', 'CO-00737', 'CO-00744']
- FAIL: dealer D43 order list: extra [], missing ['CO-00714']
- FAIL: dealer D44 order list: extra [], missing ['CO-00715', 'CO-00723', 'CO-00740']
- FAIL: dealer D45 order list: extra [], missing ['CO-00724', 'CO-00764']
- FAIL: dealer D49 order list: extra [], missing ['CO-00739']
- FAIL: loaners: extra ['CO-02294', 'CO-02332', 'CO-02350'], missing ['CO-00687', 'CO-00688', 'CO-00692', 'CO-00707', 'CO-00709']

### H-017 — plant_outage — PASS
> Wacky Wheels Lexington will be offline 15 Mar through 16 Mar because of an electrical fire.
- Read as: `plant_outage` (reader: rules)
- Stats: {"writes": 52, "calls": 52, "moved": 6, "rescheduled": 6, "transferred": 0, "expected_moves": 6, "dealers": 29, "loaners": 17, "lots": [], "stop_sale_vins": 0, "owners": 0}

### H-018 — plant_outage — PASS
> Line stoppage at the Greensboro plant: a roof collapse in the paint shop. No production from the 15th to 3/16.
- Read as: `plant_outage` (reader: rules)
- Stats: {"writes": 47, "calls": 47, "moved": 6, "rescheduled": 6, "transferred": 0, "expected_moves": 6, "dealers": 29, "loaners": 12, "lots": [], "stop_sale_vins": 0, "owners": 0}

### H-019 — plant_outage — PASS
> Production at the Lexigton plant is suspended starting 3/29 after a roof collapse in the paint shop; we expect to be back up on 31 Mar.
- Read as: `plant_outage` (reader: rules)
- Stats: {"writes": 42, "calls": 42, "moved": 6, "rescheduled": 6, "transferred": 0, "expected_moves": 6, "dealers": 26, "loaners": 10, "lots": [], "stop_sale_vins": 0, "owners": 0}

### H-020 — supplier_delay — PASS
> fyi compact wiring harness from Ridgeline into Princeton is running behind, expected Mon 15 March but more like the 17th now
- Read as: `supplier_delay` (reader: rules)
- Stats: {"writes": 19, "calls": 19, "moved": 2, "rescheduled": 2, "transferred": 0, "expected_moves": 2, "dealers": 11, "loaners": 6, "lots": [], "stop_sale_vins": 0, "owners": 0}

### H-021 — noise — PASS
> Snow expected in Denver, CO this weekend; travel advisories in effect.
- Read as: `noise` (reader: rules)
- Stats: {"writes": 0, "calls": 0}

### H-022 — supplier_delay — PASS
> Shipment SH-0020: arrival moved from Mon 29 March to March 30th. Reason: weather at the port. Supplier: Atlas Wire and Cable. Part: heavy-duty wiring harness. Ship to: the San Antonio plant.
- Read as: `supplier_delay` (reader: rules)
- Stats: {"writes": 23, "calls": 23, "moved": 2, "rescheduled": 2, "transferred": 0, "expected_moves": 2, "dealers": 14, "loaners": 7, "lots": [], "stop_sale_vins": 0, "owners": 0}

### H-023 — supplier_delay — FAIL
> Voicemail from Granite Tire: the small all-season rubber order headed to Wacky Wheels Greensboro is rescheduled from Mon 15 March to Tuesday the 16th.
- Read as: `noise` (reader: rules)
- Stats: {"writes": 0, "calls": 0, "moved": 0, "rescheduled": 0, "transferred": 0, "expected_moves": 1, "dealers": 0, "loaners": 0, "lots": [], "stop_sale_vins": 0, "owners": 0}
- FAIL: incident kinds ['none'] expected ['supplier_delay']
- FAIL: 1 affected PO(s) not moved: ['PO-0496']
- FAIL: dealer set: extra [], missing ['D03', 'D07', 'D08', 'D10', 'D25']
- FAIL: loaners: extra [], missing ['CO-02854', 'CO-02856']
- warn: only 0 kind(s) of write action (handbook rule 9 wants 3)

### H-024 — noise — PASS
> Insurance renewal paperwork is due to HR by Friday.
- Read as: `noise` (reader: rules)
- Stats: {"writes": 0, "calls": 0}

### H-025 — noise — PASS
> Volunteer day at the Greensboro food bank is next Saturday. Sign up on the portal.
- Read as: `noise` (reader: rules)
- Stats: {"writes": 0, "calls": 0}

### H-026 — supplier_delay — PASS
> ETA change: HARN-A for Wacky Wheels Princeton. Was 2027-03-22, now the 26th. - SUP-05 logistics
- Read as: `supplier_delay` (reader: rules)
- Stats: {"writes": 32, "calls": 32, "moved": 4, "rescheduled": 4, "transferred": 0, "expected_moves": 4, "dealers": 20, "loaners": 8, "lots": [], "stop_sale_vins": 0, "owners": 0}

### H-027 — unconfirmed — PASS
> Apparently freight problems are causing delays somewhere upstream. Not confirmed.
- Read as: `unconfirmed` (reader: rules)
- Stats: {"writes": 0, "calls": 1}

### H-028 — compound — PASS
> Two updates: 1) Huntsville will be offline 3/12 through March 17th because of a press line breakdown. 2) We regret to inform you that delivery of ADAS chips to the Princton plant, slated for March 29th, has been postponed until Tuesday the 30th. Regards, Quanta
- Read as: `plant_outage+supplier_delay` (reader: rules, rules)
- Stats: {"writes": 82, "calls": 82, "moved": 13, "rescheduled": 13, "transferred": 0, "expected_moves": 13, "dealers": 41, "loaners": 28, "lots": [], "stop_sale_vins": 0, "owners": 0}

### H-029 — compound — PASS
> Orbit flagged contaminated grease in 12-inch displays shipped to Wacky Wheels Lexington; vehicles assembled Mon 22 February through 2/24 are affected. Also, not sure if true, but a friend at Harbor Seating says they may run short on parts soon.
- Read as: `quality_hold+unconfirmed` (reader: rules, rules)
- Stats: {"writes": 69, "calls": 70, "moved": 0, "rescheduled": 0, "transferred": 0, "expected_moves": 0, "dealers": 0, "loaners": 0, "lots": ["LOT-0065"], "stop_sale_vins": 39, "owners": 44}

### H-030 — quality_hold — PASS
> Nonconformance report: cloth seats lot LOT-0338 from Harbor, used at the Greensboro plant on builds 2/25 to 2027-03-01, shows water ingress. Contain and hold.
- Read as: `quality_hold` (reader: rules)
- Stats: {"writes": 187, "calls": 187, "moved": 0, "rescheduled": 0, "transferred": 0, "expected_moves": 0, "dealers": 0, "loaners": 0, "lots": ["LOT-0338"], "stop_sale_vins": 122, "owners": 151}

### H-031 — quality_hold — PASS
> Nonconformance report: harness C lot LOT-0282 from Volt, used at the Huntsville plant on builds February 25th to March 1st, shows a software checksum error. Contain and hold.
- Read as: `quality_hold` (reader: rules)
- Stats: {"writes": 73, "calls": 73, "moved": 0, "rescheduled": 0, "transferred": 0, "expected_moves": 0, "dealers": 0, "loaners": 0, "lots": ["LOT-0282"], "stop_sale_vins": 39, "owners": 51}

### H-032 — plant_outage — PASS
> the Mississippi plant will be offline Tue 30 March through Thu 1 April because of a burst water main.
- Read as: `plant_outage` (reader: rules)
- Stats: {"writes": 55, "calls": 55, "moved": 9, "rescheduled": 2, "transferred": 7, "expected_moves": 9, "dealers": 31, "loaners": 15, "lots": [], "stop_sale_vins": 0, "owners": 0}

### H-033 — unconfirmed — PASS
> is it true P_NC might lose power next month? someone was talking about it
- Read as: `unconfirmed` (reader: rules)
- Stats: {"writes": 0, "calls": 1}

### H-034 — noise — PASS
> Volunteer day at the Huntsville food bank is next Saturday. Sign up on the portal.
- Read as: `noise` (reader: rules)
- Stats: {"writes": 0, "calls": 0}

### H-035 — compound — PASS
> Line stoppage at Princeton: a roof collapse in the paint shop. No production from 2027-03-23 to Wed 24 March. Also, containment request: hold LOT-0192. infotainment chips, water ingress. Builds at P_IN between 3/4 and 2027-03-05.
- Read as: `plant_outage+quality_hold` (reader: rules, rules)
- Stats: {"writes": 142, "calls": 142, "moved": 6, "rescheduled": 6, "transferred": 0, "expected_moves": 6, "dealers": 26, "loaners": 13, "lots": ["LOT-0192"], "stop_sale_vins": 50, "owners": 72}

### H-036 — unconfirmed — PASS
> unverified: the San Antonio plant may shut a line at some point
- Read as: `unconfirmed` (reader: rules)
- Stats: {"writes": 0, "calls": 1}

### H-037 — compound — FAIL
> Daily summary. (1) A minor earthquake was felt near Lima, Peru; no damage reported. (2) the San Antonio plant closed 3/23 - the 26th (an electrical fire). will update
- Read as: `noise+noise` (reader: rules, rules)
- Stats: {"writes": 0, "calls": 0, "moved": 0, "rescheduled": 0, "transferred": 0, "expected_moves": 12, "dealers": 0, "loaners": 0, "lots": [], "stop_sale_vins": 0, "owners": 0}
- FAIL: incident kinds ['none'] expected ['plant_outage']
- FAIL: 12 affected PO(s) not moved: ['PO-0064', 'PO-0065', 'PO-0066', 'PO-0067', 'PO-0068']
- FAIL: dealer set: extra [], missing ['D02', 'D03', 'D04', 'D06', 'D07']
- FAIL: loaners: extra [], missing ['CO-00308', 'CO-00309', 'CO-00316', 'CO-00319', 'CO-00321']
- warn: only 0 kind(s) of write action (handbook rule 9 wants 3)

### H-038 — supplier_delay — PASS
> ETA change: standard wiring harness for Princeton. Was the 15th, now 3/17. - Volt logistics
- Read as: `supplier_delay` (reader: rules)
- Stats: {"writes": 20, "calls": 20, "moved": 2, "rescheduled": 2, "transferred": 0, "expected_moves": 2, "dealers": 13, "loaners": 5, "lots": [], "stop_sale_vins": 0, "owners": 0}

### H-039 — plant_outage — PASS
> No production at P_KY on the 17th due to a press line breakdown. Normal schedule the next working day.
- Read as: `plant_outage` (reader: rules)
- Stats: {"writes": 26, "calls": 26, "moved": 3, "rescheduled": 3, "transferred": 0, "expected_moves": 3, "dealers": 16, "loaners": 7, "lots": [], "stop_sale_vins": 0, "owners": 0}

### H-040 — quality_hold — PASS
> Containment request: hold LOT-0040. 20-inch tires, a software checksum error. Builds at the San Antonio plant between 2027-03-04 and Fri 5 March.
- Read as: `quality_hold` (reader: rules)
- Stats: {"writes": 98, "calls": 98, "moved": 0, "rescheduled": 0, "transferred": 0, "expected_moves": 0, "dealers": 0, "loaners": 0, "lots": ["LOT-0040"], "stop_sale_vins": 58, "owners": 65}

### H-041 — supplier_delay — PASS
> We regret to inform you that delivery of brake kits to P_AL, slated for 3/22, has been postponed until 3/26. Regards, Sterling Safety
- Read as: `supplier_delay` (reader: rules)
- Stats: {"writes": 54, "calls": 54, "moved": 8, "rescheduled": 8, "transferred": 0, "expected_moves": 8, "dealers": 33, "loaners": 13, "lots": [], "stop_sale_vins": 0, "owners": 0}

### H-042 — supplier_delay — FAIL
> ETA change: 20-inch alloy wheels for Princeton. Was the 29th, now Thu 1 April. - SUP-03 logistics
- Read as: `unconfirmed` (reader: rules)
- Stats: {"writes": 0, "calls": 1, "moved": 0, "rescheduled": 0, "transferred": 0, "expected_moves": 3, "dealers": 0, "loaners": 0, "lots": [], "stop_sale_vins": 0, "owners": 0}
- FAIL: incident kinds ['none'] expected ['supplier_delay']
- FAIL: escalated although the event is actionable / noise
- FAIL: 3 affected PO(s) not moved: ['PO-0347', 'PO-0350', 'PO-0353']
- FAIL: dealer set: extra [], missing ['D06', 'D07', 'D08', 'D16', 'D21']
- FAIL: loaners: extra [], missing ['CO-02064', 'CO-02068', 'CO-02069', 'CO-02089', 'CO-02092']
- warn: only 0 kind(s) of write action (handbook rule 9 wants 3)

### H-043 — unconfirmed — PASS
> Heard Orbit Optics could be behind on something, didn't catch what. Will call back.
- Read as: `unconfirmed` (reader: rules)
- Stats: {"writes": 0, "calls": 1}

### H-044 — plant_outage — PASS
> Huntsville will be offline 3/26 through March 29th because of a roof collapse in the paint shop.
- Read as: `plant_outage` (reader: rules)
- Stats: {"writes": 43, "calls": 43, "moved": 6, "rescheduled": 6, "transferred": 0, "expected_moves": 6, "dealers": 26, "loaners": 11, "lots": [], "stop_sale_vins": 0, "owners": 0}

### H-045 — plant_outage — PASS
> the Lexngton plant down all day Tuesday the 9th (an IT system failure).
- Read as: `plant_outage` (reader: rules)
- Stats: {"writes": 28, "calls": 28, "moved": 3, "rescheduled": 3, "transferred": 0, "expected_moves": 3, "dealers": 19, "loaners": 6, "lots": [], "stop_sale_vins": 0, "owners": 0}

### H-046 — supplier_delay — PASS
> Shipment SH-0018: arrival moved from next Monday to March 19th. Reason: a labor shortage. Supplier: SUP-07. Part: HARN-B. Ship to: Wacky Wheels San Antonio.
- Read as: `supplier_delay` (reader: rules)
- Stats: {"writes": 52, "calls": 52, "moved": 8, "rescheduled": 8, "transferred": 0, "expected_moves": 8, "dealers": 30, "loaners": 14, "lots": [], "stop_sale_vins": 0, "owners": 0}

### H-047 — supplier_delay — FAIL
> We regret to inform you that delivery of surround-view camera kits to the Alabama plant, slated for Monday the 22nd, has been postponed until 2027-03-25. Regards, Orbit
- Read as: `unconfirmed` (reader: rules)
- Stats: {"writes": 0, "calls": 1, "moved": 0, "rescheduled": 0, "transferred": 0, "expected_moves": 6, "dealers": 0, "loaners": 0, "lots": [], "stop_sale_vins": 0, "owners": 0}
- FAIL: incident kinds ['none'] expected ['supplier_delay']
- FAIL: escalated although the event is actionable / noise
- FAIL: 6 affected PO(s) not moved: ['PO-0421', 'PO-0423', 'PO-0424', 'PO-0426', 'PO-0427']
- FAIL: dealer set: extra [], missing ['D01', 'D02', 'D03', 'D05', 'D06']
- FAIL: loaners: extra [], missing ['CO-02435', 'CO-02441', 'CO-02452', 'CO-02463', 'CO-02466']
- warn: only 0 kind(s) of write action (handbook rule 9 wants 3)

### H-048 — plant_outage — PASS
> No production at Lexington on March 26th due to an electrical fire. Normal schedule the next working day.
- Read as: `plant_outage` (reader: rules)
- Stats: {"writes": 27, "calls": 27, "moved": 3, "rescheduled": 3, "transferred": 0, "expected_moves": 3, "dealers": 17, "loaners": 7, "lots": [], "stop_sale_vins": 0, "owners": 0}

### H-049 — supplier_delay — FAIL
> ETA change: 17-inch alloy wheels for Wacky Wheels Huntsville. Was the 29th, now April 1st. - Cobalt logistics
- Read as: `unconfirmed` (reader: rules)
- Stats: {"writes": 0, "calls": 1, "moved": 0, "rescheduled": 0, "transferred": 0, "expected_moves": 6, "dealers": 0, "loaners": 0, "lots": [], "stop_sale_vins": 0, "owners": 0}
- FAIL: incident kinds ['none'] expected ['supplier_delay']
- FAIL: escalated although the event is actionable / noise
- FAIL: 6 affected PO(s) not moved: ['PO-0437', 'PO-0438', 'PO-0440', 'PO-0441', 'PO-0443']
- FAIL: dealer set: extra [], missing ['D02', 'D04', 'D06', 'D08', 'D10']
- FAIL: loaners: extra [], missing ['CO-02575', 'CO-02578', 'CO-02579', 'CO-02587', 'CO-02590']
- warn: only 0 kind(s) of write action (handbook rule 9 wants 3)

### H-050 — plant_outage — PASS
> Production at the Princeton plant is suspended starting March 12th after a press line breakdown; we expect to be back up on next Tuesday.
- Read as: `plant_outage` (reader: rules)
- Stats: {"writes": 50, "calls": 50, "moved": 6, "rescheduled": 6, "transferred": 0, "expected_moves": 6, "dealers": 32, "loaners": 12, "lots": [], "stop_sale_vins": 0, "owners": 0}

### H-051 — unconfirmed — PASS
> Not sure if true, but a friend at Ridgeline Wire says they may run short on parts soon.
- Read as: `unconfirmed` (reader: rules)
- Stats: {"writes": 0, "calls": 1}

### H-052 — supplier_delay — PASS
> fyi brake kits from Sentinel into Greensboro is running behind, expected the 29th but more like 2027-04-01 now
- Read as: `supplier_delay` (reader: rules)
- Stats: {"writes": 57, "calls": 57, "moved": 9, "rescheduled": 4, "transferred": 5, "expected_moves": 9, "dealers": 34, "loaners": 14, "lots": [], "stop_sale_vins": 0, "owners": 0}

### H-053 — quality_hold — FAIL
> Kestrel flagged a software checksum error in center screens shipped to the Huntsville plant; vehicles assembled February 25th through 2027-03-01 are affected.
- Read as: `noise` (reader: rules)
- Stats: {"writes": 0, "calls": 0, "moved": 0, "rescheduled": 0, "transferred": 0, "expected_moves": 0, "dealers": 0, "loaners": 0, "lots": [], "stop_sale_vins": 0, "owners": 0}
- FAIL: incident kinds ['none'] expected ['quality_hold']
- FAIL: lots held [] expected ['LOT-0266']
- FAIL: stop-sale VINs: got 0 expected 36 (extra [], missing ['AUR0003844', 'AUR0003846', 'AUR0003848'])
- FAIL: owners notified: got 0 expected 45 (extra [], missing ['C0194', 'C0473', 'C0601'])
- warn: only 0 kind(s) of write action (handbook rule 9 wants 3)

### H-054 — supplier_delay — PASS
> We regret to inform you that delivery of airbag module to the Kentucky plant, slated for the 29th, has been postponed until March 30th. Regards, Sterling Safety
- Read as: `supplier_delay` (reader: rules)
- Stats: {"writes": 25, "calls": 25, "moved": 3, "rescheduled": 3, "transferred": 0, "expected_moves": 3, "dealers": 18, "loaners": 4, "lots": [], "stop_sale_vins": 0, "owners": 0}

### H-055 — unconfirmed — PASS
> Heard Cobalt Wheels could be behind on something, didn't catch what. Will call back.
- Read as: `unconfirmed` (reader: rules)
- Stats: {"writes": 0, "calls": 1}

### H-056 — quality_hold — PASS
> Containment request: hold LOT-0202. harness A, contaminated grease. Builds at Wacky Wheels Princeton between Thu 25 February and Mon 1 March.
- Read as: `quality_hold` (reader: rules)
- Stats: {"writes": 76, "calls": 76, "moved": 0, "rescheduled": 0, "transferred": 0, "expected_moves": 0, "dealers": 0, "loaners": 0, "lots": ["LOT-0202"], "stop_sale_vins": 44, "owners": 46}

### H-057 — supplier_delay — FAIL
> SUP-14 can't ship the 20-inch alloy wheels to Huntsville on Mon 22 March as planned; earliest is 2027-03-24 (a labor shortage).
- Read as: `unconfirmed` (reader: rules)
- Stats: {"writes": 0, "calls": 1, "moved": 0, "rescheduled": 0, "transferred": 0, "expected_moves": 2, "dealers": 0, "loaners": 0, "lots": [], "stop_sale_vins": 0, "owners": 0}
- FAIL: incident kinds ['none'] expected ['supplier_delay']
- FAIL: escalated although the event is actionable / noise
- FAIL: 2 affected PO(s) not moved: ['PO-0421', 'PO-0424']
- FAIL: dealer set: extra [], missing ['D02', 'D08', 'D12', 'D16', 'D20']
- FAIL: loaners: extra [], missing ['CO-02435', 'CO-02441', 'CO-02463', 'CO-02466', 'CO-02468']
- warn: only 0 kind(s) of write action (handbook rule 9 wants 3)

### H-058 — quality_hold — PASS
> Nonconformance report: surround-view camera kits lot LOT-0060 from Orbit, used at Wacky Wheels Lexington on builds Thursday the 4th to March 5th, shows contaminated grease. Contain and hold.
- Read as: `quality_hold` (reader: rules)
- Stats: {"writes": 94, "calls": 94, "moved": 0, "rescheduled": 0, "transferred": 0, "expected_moves": 0, "dealers": 0, "loaners": 0, "lots": ["LOT-0060"], "stop_sale_vins": 49, "owners": 65}

### H-059 — plant_outage — PASS
> San Antonio will be offline March 17th through Friday the 19th because of an IT system failure.
- Read as: `plant_outage` (reader: rules)
- Stats: {"writes": 55, "calls": 55, "moved": 9, "rescheduled": 9, "transferred": 0, "expected_moves": 9, "dealers": 30, "loaners": 16, "lots": [], "stop_sale_vins": 0, "owners": 0}

### H-060 — noise — PASS
> The San Antonio plant's open house for families is on Saturday. Refreshments provided.
- Read as: `noise` (reader: rules)
- Stats: {"writes": 0, "calls": 0}

### H-061 — noise — PASS
> Can we get the new window stickers in Spanish as well? - Shreveport
- Read as: `noise` (reader: rules)
- Stats: {"writes": 0, "calls": 0}

### H-062 — noise — PASS
> Fleet sales promotion extended through the end of the quarter.
- Read as: `noise` (reader: rules)
- Stats: {"writes": 0, "calls": 0}

### H-063 — noise — PASS
> Who left a blue umbrella in conference room B?
- Read as: `noise` (reader: rules)
- Stats: {"writes": 0, "calls": 0}

### H-064 — quality_hold — PASS
> Recall alert - brake kits from Sentinel Brake and Airbag at Lexington, build dates 2027-02-22 to 2/24: water ingress.
- Read as: `quality_hold` (reader: rules)
- Stats: {"writes": 178, "calls": 178, "moved": 0, "rescheduled": 0, "transferred": 0, "expected_moves": 0, "dealers": 0, "loaners": 0, "lots": ["LOT-0053"], "stop_sale_vins": 127, "owners": 139}

### H-065 — compound — FAIL
> Stock markets closed higher today on strong tech earnings. Also, production at Wacky Wheels Jackson is suspended starting 3/24 after an IT system failure; we expect to be back up on March 30th.
- Read as: `noise` (reader: rules)
- Stats: {"writes": 0, "calls": 0, "moved": 0, "rescheduled": 0, "transferred": 0, "expected_moves": 12, "dealers": 0, "loaners": 0, "lots": [], "stop_sale_vins": 0, "owners": 0}
- FAIL: incident kinds ['none'] expected ['plant_outage']
- FAIL: 12 affected PO(s) not moved: ['PO-0247', 'PO-0248', 'PO-0249', 'PO-0250', 'PO-0251']
- FAIL: dealer set: extra [], missing ['D02', 'D03', 'D05', 'D06', 'D07']
- FAIL: loaners: extra [], missing ['CO-01419', 'CO-01423', 'CO-01424', 'CO-01427', 'CO-01428']
- warn: only 0 kind(s) of write action (handbook rule 9 wants 3)

### H-066 — noise — PASS
> Volunteer day at the Jackson food bank is next Saturday. Sign up on the portal.
- Read as: `noise` (reader: rules)
- Stats: {"writes": 0, "calls": 0}

### H-067 — quality_hold — PASS
> Containment request: hold LOT-0040. 20-inch all-season tires, water ingress. Builds at San Antonio between Thu 4 March and the 5th.
- Read as: `quality_hold` (reader: rules)
- Stats: {"writes": 98, "calls": 98, "moved": 0, "rescheduled": 0, "transferred": 0, "expected_moves": 0, "dealers": 0, "loaners": 0, "lots": ["LOT-0040"], "stop_sale_vins": 58, "owners": 65}

### H-068 — quality_hold — PASS
> Nonconformance report: compact wiring harness lot LOT-0281 from SUP-05, used at the Huntsville plant on builds Mon 22 February to February 24th, shows a software checksum error. Contain and hold.
- Read as: `quality_hold` (reader: rules)
- Stats: {"writes": 74, "calls": 74, "moved": 0, "rescheduled": 0, "transferred": 0, "expected_moves": 0, "dealers": 0, "loaners": 0, "lots": ["LOT-0281"], "stop_sale_vins": 45, "owners": 47}

### H-069 — quality_hold — PASS
> Recall alert - BRAKE-KIT from Sterling at the Mississippi plant, build dates 2027-02-22 to February 24th: delamination.
- Read as: `quality_hold` (reader: rules)
- Stats: {"writes": 131, "calls": 131, "moved": 0, "rescheduled": 0, "transferred": 0, "expected_moves": 0, "dealers": 0, "loaners": 0, "lots": ["LOT-0121"], "stop_sale_vins": 78, "owners": 97}

### H-070 — plant_outage — PASS
> No production at the Lexingon plant on March 18th due to a press line breakdown. Normal schedule the next working day.
- Read as: `plant_outage` (reader: rules)
- Stats: {"writes": 29, "calls": 29, "moved": 3, "rescheduled": 3, "transferred": 0, "expected_moves": 3, "dealers": 18, "loaners": 8, "lots": [], "stop_sale_vins": 0, "owners": 0}

### H-071 — compound — PASS
> Daily summary. (1) fyi 16-inch alloy wheel from Ironwood into the San Antonio plant is running behind, expected next Mon but more like Tue 16 March now (2) We regret to inform you that delivery of 17-inch rims to the Jacson plant, slated for the 15th, has been postponed until Thursday the 18th. Regards, SUP-03
- Read as: `supplier_delay+supplier_delay` (reader: rules, rules)
- Stats: {"writes": 55, "calls": 55, "moved": 7, "rescheduled": 7, "transferred": 0, "expected_moves": 7, "dealers": 34, "loaners": 14, "lots": [], "stop_sale_vins": 0, "owners": 0}

### H-072 — compound — FAIL
> Two updates: 1) Volunteer day at the Jackson food bank is next Saturday. Sign up on the portal. 2) Production at Jackson is suspended starting the 16th after a substation failure; we expect to be back up on 23 Mar.
- Read as: `noise+noise` (reader: rules, rules)
- Stats: {"writes": 0, "calls": 0, "moved": 0, "rescheduled": 0, "transferred": 0, "expected_moves": 15, "dealers": 0, "loaners": 0, "lots": [], "stop_sale_vins": 0, "owners": 0}
- FAIL: incident kinds ['none'] expected ['plant_outage']
- FAIL: 15 affected PO(s) not moved: ['PO-0229', 'PO-0230', 'PO-0231', 'PO-0232', 'PO-0233']
- FAIL: dealer set: extra [], missing ['D03', 'D04', 'D06', 'D07', 'D08']
- FAIL: loaners: extra [], missing ['CO-01249', 'CO-01250', 'CO-01253', 'CO-01262', 'CO-01265']
- warn: only 0 kind(s) of write action (handbook rule 9 wants 3)

### H-073 — supplier_delay — FAIL
> Voicemail from Meridian Seating: the SEAT-FAB order headed to Jackson is rescheduled from the 15th to Fri 19 March.
- Read as: `noise` (reader: rules)
- Stats: {"writes": 0, "calls": 0, "moved": 0, "rescheduled": 0, "transferred": 0, "expected_moves": 8, "dealers": 0, "loaners": 0, "lots": [], "stop_sale_vins": 0, "owners": 0}
- FAIL: incident kinds ['none'] expected ['supplier_delay']
- FAIL: 8 affected PO(s) not moved: ['PO-0226', 'PO-0228', 'PO-0229', 'PO-0231', 'PO-0232']
- FAIL: dealer set: extra [], missing ['D02', 'D03', 'D05', 'D06', 'D07']
- FAIL: loaners: extra [], missing ['CO-01222', 'CO-01223', 'CO-01242', 'CO-01249', 'CO-01250']
- warn: only 0 kind(s) of write action (handbook rule 9 wants 3)

### H-074 — plant_outage — PASS
> Line stoppage at Greensboro: a burst water main. No production from March 12th to 15 Mar.
- Read as: `plant_outage` (reader: rules)
- Stats: {"writes": 44, "calls": 44, "moved": 6, "rescheduled": 6, "transferred": 0, "expected_moves": 6, "dealers": 25, "loaners": 13, "lots": [], "stop_sale_vins": 0, "owners": 0}

### H-075 — noise — PASS
> The quarterly sales webinar moves to Thursday afternoon. Same link as before.
- Read as: `noise` (reader: rules)
- Stats: {"writes": 0, "calls": 0}

### H-076 — quality_hold — PASS
> Nonconformance report: brake kits lot LOT-0005 from Sterling Safety, used at the Texas plant on builds Mon 22 February to 2/24, shows delamination. Contain and hold.
- Read as: `quality_hold` (reader: rules)
- Stats: {"writes": 184, "calls": 184, "moved": 0, "rescheduled": 0, "transferred": 0, "expected_moves": 0, "dealers": 0, "loaners": 0, "lots": ["LOT-0005"], "stop_sale_vins": 127, "owners": 141}

### H-077 — unconfirmed — PASS
> Heard Harbor Seating could be behind on something, didn't catch what. Will call back.
- Read as: `unconfirmed` (reader: rules)
- Stats: {"writes": 0, "calls": 1}

### H-078 — plant_outage — FAIL
> Production at P_NC is suspended starting 10 Mar after a press line breakdown; we expect to be back up on Fri 12 March.
- Read as: `noise` (reader: rules)
- Stats: {"writes": 0, "calls": 0, "moved": 0, "rescheduled": 0, "transferred": 0, "expected_moves": 6, "dealers": 0, "loaners": 0, "lots": [], "stop_sale_vins": 0, "owners": 0}
- FAIL: incident kinds ['none'] expected ['plant_outage']
- FAIL: 6 affected PO(s) not moved: ['PO-0487', 'PO-0488', 'PO-0489', 'PO-0490', 'PO-0491']
- FAIL: dealer set: extra [], missing ['D02', 'D03', 'D04', 'D05', 'D06']
- FAIL: loaners: extra [], missing ['CO-02768', 'CO-02771', 'CO-02781', 'CO-02793', 'CO-02795']
- warn: only 0 kind(s) of write action (handbook rule 9 wants 3)

### H-079 — supplier_delay — PASS
> ETA change: 17-inch tires for Wacky Wheels Lexington. Was Mon 22 March, now 3/25. - SUP-02 logistics
- Read as: `supplier_delay` (reader: rules)
- Stats: {"writes": 46, "calls": 46, "moved": 6, "rescheduled": 6, "transferred": 0, "expected_moves": 6, "dealers": 28, "loaners": 12, "lots": [], "stop_sale_vins": 0, "owners": 0}

### H-080 — plant_outage — PASS
> Line stoppage at Greensboro: an electrical fire. No production from 2027-03-10 to 3/11.
- Read as: `plant_outage` (reader: rules)
- Stats: {"writes": 38, "calls": 38, "moved": 6, "rescheduled": 6, "transferred": 0, "expected_moves": 6, "dealers": 23, "loaners": 9, "lots": [], "stop_sale_vins": 0, "owners": 0}

### H-081 — quality_hold — PASS
> Recall alert - minivan seats from SUP-15 at the Kentucky plant, build dates February 25th to Mon 1 March: contaminated grease.
- Read as: `quality_hold` (reader: rules)
- Stats: {"writes": 68, "calls": 68, "moved": 0, "rescheduled": 0, "transferred": 0, "expected_moves": 0, "dealers": 0, "loaners": 0, "lots": ["LOT-0094"], "stop_sale_vins": 39, "owners": 43}

### H-082 — unconfirmed — FAIL
> Some folks think a batch of airbags might be bad. No lot number, no dates.
- Read as: `noise` (reader: rules)
- Stats: {"writes": 0, "calls": 0}
- FAIL: expected an escalate, none made

### H-083 — supplier_delay — FAIL
> Cobalt can't ship the 16-inch alloy wheels to P_NC on Monday the 15th as planned; earliest is the 17th (weather at the port).
- Read as: `unconfirmed` (reader: rules)
- Stats: {"writes": 0, "calls": 1, "moved": 0, "rescheduled": 0, "transferred": 0, "expected_moves": 2, "dealers": 0, "loaners": 0, "lots": [], "stop_sale_vins": 0, "owners": 0}
- FAIL: incident kinds ['none'] expected ['supplier_delay']
- FAIL: escalated although the event is actionable / noise
- FAIL: 2 affected PO(s) not moved: ['PO-0497', 'PO-0500']
- FAIL: dealer set: extra [], missing ['D05', 'D08', 'D12', 'D20', 'D26']
- FAIL: loaners: extra [], missing ['CO-02860', 'CO-02864', 'CO-02886', 'CO-02890']
- warn: only 0 kind(s) of write action (handbook rule 9 wants 3)

### H-084 — unconfirmed — PASS
> Not sure if true, but a friend at Sterling Safety says they may run short on parts soon.
- Read as: `unconfirmed` (reader: rules)
- Stats: {"writes": 0, "calls": 1}

### H-085 — plant_outage — PASS
> Line stoppage at the Indiana plant: a substation failure. No production from 2027-03-10 to next Monday.
- Read as: `plant_outage` (reader: rules)
- Stats: {"writes": 76, "calls": 76, "moved": 12, "rescheduled": 12, "transferred": 0, "expected_moves": 12, "dealers": 40, "loaners": 24, "lots": [], "stop_sale_vins": 0, "owners": 0}

### H-086 — plant_outage — FAIL
> Production at Jackson is suspended starting Tue 23 March after a roof collapse in the paint shop; we expect to be back up on 2027-03-26.
- Read as: `noise` (reader: rules)
- Stats: {"writes": 0, "calls": 0, "moved": 0, "rescheduled": 0, "transferred": 0, "expected_moves": 9, "dealers": 0, "loaners": 0, "lots": [], "stop_sale_vins": 0, "owners": 0}
- FAIL: incident kinds ['none'] expected ['plant_outage']
- FAIL: 9 affected PO(s) not moved: ['PO-0244', 'PO-0245', 'PO-0246', 'PO-0247', 'PO-0248']
- FAIL: dealer set: extra [], missing ['D02', 'D03', 'D04', 'D05', 'D06']
- FAIL: loaners: extra [], missing ['CO-01384', 'CO-01385', 'CO-01389', 'CO-01395', 'CO-01396']
- warn: only 0 kind(s) of write action (handbook rule 9 wants 3)

### H-087 — plant_outage — FAIL
> Production at San Antonio is suspended starting March 22nd after a substation failure; we expect to be back up on March 29th.
- Read as: `noise` (reader: rules)
- Stats: {"writes": 0, "calls": 0, "moved": 0, "rescheduled": 0, "transferred": 0, "expected_moves": 15, "dealers": 0, "loaners": 0, "lots": [], "stop_sale_vins": 0, "owners": 0}
- FAIL: incident kinds ['none'] expected ['plant_outage']
- FAIL: 15 affected PO(s) not moved: ['PO-0061', 'PO-0062', 'PO-0063', 'PO-0064', 'PO-0065']
- FAIL: dealer set: extra [], missing ['D02', 'D03', 'D04', 'D06', 'D07']
- FAIL: loaners: extra [], missing ['CO-00278', 'CO-00283', 'CO-00284', 'CO-00296', 'CO-00308']
- warn: only 0 kind(s) of write action (handbook rule 9 wants 3)

### H-088 — unconfirmed — PASS
> Chatter about a port strike that could hit deliveries. No specifics.
- Read as: `unconfirmed` (reader: rules)
- Stats: {"writes": 0, "calls": 1}

### H-089 — quality_hold — PASS
> Containment request: hold LOT-0074. standard wiring harness, delamination. Builds at Lexington between 25 Feb and 1 Mar.
- Read as: `quality_hold` (reader: rules)
- Stats: {"writes": 68, "calls": 68, "moved": 0, "rescheduled": 0, "transferred": 0, "expected_moves": 0, "dealers": 0, "loaners": 0, "lots": ["LOT-0074"], "stop_sale_vins": 54, "owners": 35}

### H-090 — compound — FAIL
> Daily summary. (1) Ridgeline Wire flagged porosity in the castings in harness A shipped to the Greensboro plant; vehicles assembled 2027-03-04 through 5 Mar are affected. (2) Apparently freight problems are causing delays somewhere upstream. Not confirmed.
- Read as: `noise+unconfirmed` (reader: rules, rules)
- Stats: {"writes": 0, "calls": 1, "moved": 0, "rescheduled": 0, "transferred": 0, "expected_moves": 0, "dealers": 0, "loaners": 0, "lots": [], "stop_sale_vins": 0, "owners": 0}
- FAIL: incident kinds ['none'] expected ['quality_hold']
- FAIL: lots held [] expected ['LOT-0328']
- FAIL: stop-sale VINs: got 0 expected 36 (extra [], missing ['AUR0005166', 'AUR0005167', 'AUR0005168'])
- FAIL: owners notified: got 0 expected 31 (extra [], missing ['C0016', 'C0081', 'C0085'])
- warn: only 0 kind(s) of write action (handbook rule 9 wants 3)

### H-091 — compound — FAIL
> Line stoppage at Wacky Wheels Jackson: a roof collapse in the paint shop. No production from March 24th to 2027-03-25. Also, ridgeline flagged an incorrect torque spec in compact wiring harness shipped to Princeton; vehicles assembled the 4th through the 5th are affected.
- Read as: `plant_outage` (reader: rules)
- Stats: {"writes": 42, "calls": 42, "moved": 6, "rescheduled": 6, "transferred": 0, "expected_moves": 6, "dealers": 27, "loaners": 9, "lots": [], "stop_sale_vins": 0, "owners": 0}
- FAIL: incident kinds ['plant_outage'] expected ['plant_outage', 'quality_hold']
- FAIL: lots held [] expected ['LOT-0212']
- FAIL: stop-sale VINs: got 0 expected 27 (extra [], missing ['AUR0003359', 'AUR0003362', 'AUR0003364'])
- FAIL: owners notified: got 0 expected 32 (extra [], missing ['C0039', 'C0124', 'C0222'])

### H-092 — plant_outage — FAIL
> Lexington closed 16 Mar - Friday the 19th (a chemical spill). will update
- Read as: `noise` (reader: rules)
- Stats: {"writes": 0, "calls": 0, "moved": 0, "rescheduled": 0, "transferred": 0, "expected_moves": 12, "dealers": 0, "loaners": 0, "lots": [], "stop_sale_vins": 0, "owners": 0}
- FAIL: incident kinds ['none'] expected ['plant_outage']
- FAIL: 12 affected PO(s) not moved: ['PO-0139', 'PO-0140', 'PO-0141', 'PO-0142', 'PO-0143']
- FAIL: dealer set: extra [], missing ['D01', 'D02', 'D03', 'D04', 'D05']
- FAIL: loaners: extra [], missing ['CO-00725', 'CO-00727', 'CO-00729', 'CO-00736', 'CO-00737']
- warn: only 0 kind(s) of write action (handbook rule 9 wants 3)

### H-093 — unconfirmed — PASS
> Possibly an issue brewing at P_NC. Nobody can confirm anything yet.
- Read as: `unconfirmed` (reader: rules)
- Stats: {"writes": 0, "calls": 1}

### H-094 — quality_hold — PASS
> Atlas flagged contaminated grease in harness B shipped to the Texas plant; vehicles assembled 2/22 through February 24th are affected.
- Read as: `quality_hold` (reader: rules)
- Stats: {"writes": 131, "calls": 131, "moved": 0, "rescheduled": 0, "transferred": 0, "expected_moves": 0, "dealers": 0, "loaners": 0, "lots": ["LOT-0017"], "stop_sale_vins": 86, "owners": 94}

### H-095 — plant_outage — PASS
> No production at Lexington on 2027-03-23 due to a severe storm. Normal schedule the next working day.
- Read as: `plant_outage` (reader: rules)
- Stats: {"writes": 27, "calls": 27, "moved": 3, "rescheduled": 3, "transferred": 0, "expected_moves": 3, "dealers": 18, "loaners": 6, "lots": [], "stop_sale_vins": 0, "owners": 0}

### H-096 — unconfirmed — PASS
> is it true Huntsville might lose power next month? someone was talking about it
- Read as: `unconfirmed` (reader: rules)
- Stats: {"writes": 0, "calls": 1}

### H-097 — supplier_delay — FAIL
> Voicemail from Sentinel: the airbag module order headed to Jackson is rescheduled from 15 Mar to Tue 16 March.
- Read as: `noise` (reader: rules)
- Stats: {"writes": 0, "calls": 0, "moved": 0, "rescheduled": 0, "transferred": 0, "expected_moves": 3, "dealers": 0, "loaners": 0, "lots": [], "stop_sale_vins": 0, "owners": 0}
- FAIL: incident kinds ['none'] expected ['supplier_delay']
- FAIL: 3 affected PO(s) not moved: ['PO-0226', 'PO-0227', 'PO-0228']
- FAIL: dealer set: extra [], missing ['D02', 'D05', 'D06', 'D09', 'D10']
- FAIL: loaners: extra [], missing ['CO-01222', 'CO-01223', 'CO-01242']
- warn: only 0 kind(s) of write action (handbook rule 9 wants 3)

### H-098 — supplier_delay — PASS
> ETA change: brake kits for the Lexington plant. Was the 22nd, now 25 Mar. - Sentinel logistics
- Read as: `supplier_delay` (reader: rules)
- Stats: {"writes": 59, "calls": 59, "moved": 9, "rescheduled": 9, "transferred": 0, "expected_moves": 9, "dealers": 34, "loaners": 16, "lots": [], "stop_sale_vins": 0, "owners": 0}

### H-099 — quality_hold — PASS
> Nonconformance report: 20-inch all-season tire lot LOT-0299 from SUP-02, used at Huntsville on builds March 2nd to March 3rd, shows contaminated grease. Contain and hold.
- Read as: `quality_hold` (reader: rules)
- Stats: {"writes": 59, "calls": 59, "moved": 0, "rescheduled": 0, "transferred": 0, "expected_moves": 0, "dealers": 0, "loaners": 0, "lots": ["LOT-0299"], "stop_sale_vins": 26, "owners": 43}

### H-100 — supplier_delay — PASS
> We regret to inform you that delivery of airbag modules to the Lexigton plant, slated for Monday the 29th, has been postponed until Wed 31 March. Regards, Sterling Safety
- Read as: `supplier_delay` (reader: rules)
- Stats: {"writes": 42, "calls": 42, "moved": 6, "rescheduled": 6, "transferred": 0, "expected_moves": 6, "dealers": 26, "loaners": 10, "lots": [], "stop_sale_vins": 0, "owners": 0}

## Details — qwen3:0.6b reader

### H-001 — quality_hold — PASS
> Nonconformance report: 20-inch alloy wheels lot LOT-0237 from Cobalt, used at Wacky Wheels Princeton on builds 2/22 to 2027-02-24, shows contaminated grease. Contain and hold.
- Read as: `quality_hold` (reader: qwen3:0.6b)
- Stats: {"writes": 67, "calls": 67, "moved": 0, "rescheduled": 0, "transferred": 0, "expected_moves": 0, "dealers": 0, "loaners": 0, "lots": ["LOT-0237"], "stop_sale_vins": 31, "owners": 46}

### H-002 — noise — PASS
> The vending machine on floor 3 is out of order again.
- Read as: `noise` (reader: rules)
- Stats: {"writes": 0, "calls": 0}

### H-003 — supplier_delay — PASS
> Shipment SH-0339: arrival moved from March 22nd to the 24th. Reason: a labor shortage. Supplier: Harbor Seating. Part: SEAT-FAB. Ship to: Greensboro.
- Read as: `supplier_delay` (reader: rules)
- Stats: {"writes": 51, "calls": 51, "moved": 6, "rescheduled": 6, "transferred": 0, "expected_moves": 6, "dealers": 32, "loaners": 13, "lots": [], "stop_sale_vins": 0, "owners": 0}

### H-004 — noise — PASS
> A minor earthquake was felt near Lima, Peru; no damage reported.
- Read as: `noise` (reader: qwen3:0.6b)
- Stats: {"writes": 0, "calls": 0}

### H-005 — compound — PASS
> Daily summary. (1) Fleet sales promotion extended through the end of the quarter. (2) Production at Lexington is suspended starting 3/18 after an electrical fire; we expect to be back up on March 24th.
- Read as: `noise+plant_outage` (reader: qwen3:0.6b, qwen3:0.6b)
- Stats: {"writes": 69, "calls": 69, "moved": 12, "rescheduled": 12, "transferred": 0, "expected_moves": 12, "dealers": 35, "loaners": 22, "lots": [], "stop_sale_vins": 0, "owners": 0}

### H-006 — noise — PASS
> Please update your email signature to the new logo by end of month.
- Read as: `noise` (reader: qwen3:0.6b)
- Stats: {"writes": 0, "calls": 0}

### H-007 — supplier_delay — FAIL
> Voicemail from SUP-01: the 16-inch all-season tires order headed to Jackson is rescheduled from 3/29 to 2027-03-31.
- Read as: `noise` (reader: rules)
- Stats: {"writes": 0, "calls": 0, "moved": 0, "rescheduled": 0, "transferred": 0, "expected_moves": 2, "dealers": 0, "loaners": 0, "lots": [], "stop_sale_vins": 0, "owners": 0}
- FAIL: incident kinds ['none'] expected ['supplier_delay']
- FAIL: 2 affected PO(s) not moved: ['PO-0258', 'PO-0261']
- FAIL: dealer set: extra [], missing ['D01', 'D02', 'D03', 'D04', 'D06']
- FAIL: loaners: extra [], missing ['CO-01501', 'CO-01502', 'CO-01508', 'CO-01529', 'CO-01533']
- warn: only 0 kind(s) of write action (handbook rule 9 wants 3)

### H-008 — compound — FAIL
> Northgate Tire Co flagged porosity in the castings in 17-inch all-season tire shipped to Lexington; vehicles assembled 2 Mar through 3/3 are affected. Also, not sure if true, but a friend at Granite Tire says they may run short on parts soon.
- Read as: `unconfirmed` (reader: rules)
- Stats: {"writes": 0, "calls": 1, "moved": 0, "rescheduled": 0, "transferred": 0, "expected_moves": 0, "dealers": 0, "loaners": 0, "lots": [], "stop_sale_vins": 0, "owners": 0}
- FAIL: incident kinds ['none'] expected ['quality_hold']
- FAIL: lots held [] expected ['LOT-0099']
- FAIL: stop-sale VINs: got 0 expected 59 (extra [], missing ['AUR0001425', 'AUR0001428', 'AUR0001430'])
- FAIL: owners notified: got 0 expected 61 (extra [], missing ['C0110', 'C0157', 'C0169'])
- warn: only 0 kind(s) of write action (handbook rule 9 wants 3)

### H-009 — noise — PASS
> The Lexington plant's open house for families is on Saturday. Refreshments provided.
- Read as: `noise` (reader: qwen3:0.6b)
- Stats: {"writes": 0, "calls": 0}

### H-010 — quality_hold — PASS
> Containment request: hold LOT-0205. harness B, delamination. Builds at the Princeton plant between 22 Feb and February 24th.
- Read as: `quality_hold` (reader: qwen3:0.6b)
- Stats: {"writes": 67, "calls": 67, "moved": 0, "rescheduled": 0, "transferred": 0, "expected_moves": 0, "dealers": 0, "loaners": 0, "lots": ["LOT-0205"], "stop_sale_vins": 31, "owners": 46}

### H-011 — plant_outage — PASS
> P_TX will be offline Wednesday the 17th through Thursday the 18th because of a chemical spill.
- Read as: `plant_outage` (reader: qwen3:0.6b)
- Stats: {"writes": 44, "calls": 44, "moved": 6, "rescheduled": 6, "transferred": 0, "expected_moves": 6, "dealers": 26, "loaners": 12, "lots": [], "stop_sale_vins": 0, "owners": 0}

### H-012 — compound — PASS
> Daily summary. (1) SUP-08 can't ship the brake kit to Wacky Wheels San Antonio on 22 Mar as planned; earliest is March 26th (weather at the port). (2) A minor earthquake was felt near Lima, Peru; no damage reported.
- Read as: `supplier_delay+noise` (reader: rules, qwen3:0.6b)
- Stats: {"writes": 76, "calls": 76, "moved": 12, "rescheduled": 12, "transferred": 0, "expected_moves": 12, "dealers": 39, "loaners": 25, "lots": [], "stop_sale_vins": 0, "owners": 0}

### H-013 — compound — PASS
> Sterling can't ship the airbag module to the Kentucky plant on 3/29 as planned; earliest is 31 Mar (weather at the port). Also, the Greensboro plant's open house for families is on Saturday. Refreshments provided.
- Read as: `supplier_delay` (reader: rules)
- Stats: {"writes": 42, "calls": 42, "moved": 6, "rescheduled": 6, "transferred": 0, "expected_moves": 6, "dealers": 26, "loaners": 10, "lots": [], "stop_sale_vins": 0, "owners": 0}

### H-014 — supplier_delay — PASS
> We regret to inform you that delivery of leather seat set to the San Antonio plant, slated for the 22nd, has been postponed until 26 Mar. Regards, Meridian
- Read as: `supplier_delay` (reader: rules)
- Stats: {"writes": 31, "calls": 31, "moved": 4, "rescheduled": 4, "transferred": 0, "expected_moves": 4, "dealers": 21, "loaners": 6, "lots": [], "stop_sale_vins": 0, "owners": 0}

### H-015 — quality_hold — FAIL
> Meridian Seating flagged porosity in the castings in minivan seat set shipped to Wacky Wheels Huntsville; vehicles assembled 2/25 through Monday the 1st are affected.
- Read as: `noise` (reader: rules)
- Stats: {"writes": 0, "calls": 0, "moved": 0, "rescheduled": 0, "transferred": 0, "expected_moves": 0, "dealers": 0, "loaners": 0, "lots": [], "stop_sale_vins": 0, "owners": 0}
- FAIL: incident kinds ['none'] expected ['quality_hold']
- FAIL: lots held [] expected ['LOT-0290']
- FAIL: stop-sale VINs: got 0 expected 39 (extra [], missing ['AUR0003877', 'AUR0003881', 'AUR0003883'])
- FAIL: owners notified: got 0 expected 51 (extra [], missing ['C0186', 'C0318', 'C0325'])
- warn: only 0 kind(s) of write action (handbook rule 9 wants 3)

### H-016 — compound — FAIL
> Two updates: 1) fyi TIRE-20 from Northgate into the Alabama plant is running behind, expected Monday the 15th but more like 2027-03-18 now 2) We regret to inform you that delivery of 17-inch all-season tires to P_KY, slated for Mon 15 March, has been postponed until Thu 18 March. Regards, Northgate Tire Co
- Read as: `supplier_delay+unconfirmed` (reader: rules, rules)
- Stats: {"writes": 32, "calls": 33, "moved": 3, "rescheduled": 3, "transferred": 0, "expected_moves": 9, "dealers": 19, "loaners": 10, "lots": [], "stop_sale_vins": 0, "owners": 0}
- FAIL: incident kinds ['supplier_delay'] expected ['supplier_delay', 'supplier_delay']
- FAIL: escalated although the event is actionable / noise
- FAIL: 6 affected PO(s) not moved: ['PO-0136', 'PO-0138', 'PO-0139', 'PO-0141', 'PO-0142']
- FAIL: dealer set: extra [], missing ['D02', 'D03', 'D06', 'D13', 'D15']
- FAIL: dealer D08 order list: extra [], missing ['CO-00694', 'CO-00695', 'CO-00745']
- FAIL: dealer D12 order list: extra [], missing ['CO-00707']
- FAIL: dealer D23 order list: extra [], missing ['CO-00693', 'CO-00710', 'CO-00720']
- FAIL: dealer D25 order list: extra [], missing ['CO-00718', 'CO-00722', 'CO-00738']
- FAIL: dealer D26 order list: extra [], missing ['CO-00766']
- FAIL: dealer D31 order list: extra [], missing ['CO-00761']
- FAIL: dealer D35 order list: extra [], missing ['CO-00742']
- FAIL: dealer D38 order list: extra [], missing ['CO-00711', 'CO-00737', 'CO-00744']
- FAIL: dealer D43 order list: extra [], missing ['CO-00714']
- FAIL: dealer D44 order list: extra [], missing ['CO-00715', 'CO-00723', 'CO-00740']
- FAIL: dealer D45 order list: extra [], missing ['CO-00724', 'CO-00764']
- FAIL: dealer D49 order list: extra [], missing ['CO-00739']
- FAIL: loaners: extra ['CO-02294', 'CO-02332', 'CO-02350'], missing ['CO-00687', 'CO-00688', 'CO-00692', 'CO-00707', 'CO-00709']

### H-017 — plant_outage — PASS
> Wacky Wheels Lexington will be offline 15 Mar through 16 Mar because of an electrical fire.
- Read as: `plant_outage` (reader: qwen3:0.6b)
- Stats: {"writes": 52, "calls": 52, "moved": 6, "rescheduled": 6, "transferred": 0, "expected_moves": 6, "dealers": 29, "loaners": 17, "lots": [], "stop_sale_vins": 0, "owners": 0}

### H-018 — plant_outage — PASS
> Line stoppage at the Greensboro plant: a roof collapse in the paint shop. No production from the 15th to 3/16.
- Read as: `plant_outage` (reader: qwen3:0.6b)
- Stats: {"writes": 47, "calls": 47, "moved": 6, "rescheduled": 6, "transferred": 0, "expected_moves": 6, "dealers": 29, "loaners": 12, "lots": [], "stop_sale_vins": 0, "owners": 0}

### H-019 — plant_outage — PASS
> Production at the Lexigton plant is suspended starting 3/29 after a roof collapse in the paint shop; we expect to be back up on 31 Mar.
- Read as: `plant_outage` (reader: qwen3:0.6b)
- Stats: {"writes": 42, "calls": 42, "moved": 6, "rescheduled": 6, "transferred": 0, "expected_moves": 6, "dealers": 26, "loaners": 10, "lots": [], "stop_sale_vins": 0, "owners": 0}

### H-020 — supplier_delay — PASS
> fyi compact wiring harness from Ridgeline into Princeton is running behind, expected Mon 15 March but more like the 17th now
- Read as: `supplier_delay` (reader: rules)
- Stats: {"writes": 19, "calls": 19, "moved": 2, "rescheduled": 2, "transferred": 0, "expected_moves": 2, "dealers": 11, "loaners": 6, "lots": [], "stop_sale_vins": 0, "owners": 0}

### H-021 — noise — PASS
> Snow expected in Denver, CO this weekend; travel advisories in effect.
- Read as: `noise` (reader: qwen3:0.6b)
- Stats: {"writes": 0, "calls": 0}

### H-022 — supplier_delay — PASS
> Shipment SH-0020: arrival moved from Mon 29 March to March 30th. Reason: weather at the port. Supplier: Atlas Wire and Cable. Part: heavy-duty wiring harness. Ship to: the San Antonio plant.
- Read as: `supplier_delay` (reader: rules)
- Stats: {"writes": 23, "calls": 23, "moved": 2, "rescheduled": 2, "transferred": 0, "expected_moves": 2, "dealers": 14, "loaners": 7, "lots": [], "stop_sale_vins": 0, "owners": 0}

### H-023 — supplier_delay — PASS
> Voicemail from Granite Tire: the small all-season rubber order headed to Wacky Wheels Greensboro is rescheduled from Mon 15 March to Tuesday the 16th.
- Read as: `supplier_delay` (reader: qwen3:0.6b)
- Stats: {"writes": 10, "calls": 10, "moved": 1, "rescheduled": 1, "transferred": 0, "expected_moves": 1, "dealers": 7, "loaners": 2, "lots": [], "stop_sale_vins": 0, "owners": 0}

### H-024 — noise — PASS
> Insurance renewal paperwork is due to HR by Friday.
- Read as: `noise` (reader: qwen3:0.6b)
- Stats: {"writes": 0, "calls": 0}

### H-025 — noise — PASS
> Volunteer day at the Greensboro food bank is next Saturday. Sign up on the portal.
- Read as: `noise` (reader: qwen3:0.6b)
- Stats: {"writes": 0, "calls": 0}

### H-026 — supplier_delay — PASS
> ETA change: HARN-A for Wacky Wheels Princeton. Was 2027-03-22, now the 26th. - SUP-05 logistics
- Read as: `supplier_delay` (reader: rules)
- Stats: {"writes": 32, "calls": 32, "moved": 4, "rescheduled": 4, "transferred": 0, "expected_moves": 4, "dealers": 20, "loaners": 8, "lots": [], "stop_sale_vins": 0, "owners": 0}

### H-027 — unconfirmed — PASS
> Apparently freight problems are causing delays somewhere upstream. Not confirmed.
- Read as: `unconfirmed` (reader: qwen3:0.6b)
- Stats: {"writes": 0, "calls": 1}

### H-028 — compound — PASS
> Two updates: 1) Huntsville will be offline 3/12 through March 17th because of a press line breakdown. 2) We regret to inform you that delivery of ADAS chips to the Princton plant, slated for March 29th, has been postponed until Tuesday the 30th. Regards, Quanta
- Read as: `plant_outage+supplier_delay` (reader: qwen3:0.6b, rules)
- Stats: {"writes": 82, "calls": 82, "moved": 13, "rescheduled": 13, "transferred": 0, "expected_moves": 13, "dealers": 41, "loaners": 28, "lots": [], "stop_sale_vins": 0, "owners": 0}

### H-029 — compound — PASS
> Orbit flagged contaminated grease in 12-inch displays shipped to Wacky Wheels Lexington; vehicles assembled Mon 22 February through 2/24 are affected. Also, not sure if true, but a friend at Harbor Seating says they may run short on parts soon.
- Read as: `quality_hold+unconfirmed` (reader: rules, qwen3:0.6b)
- Stats: {"writes": 69, "calls": 70, "moved": 0, "rescheduled": 0, "transferred": 0, "expected_moves": 0, "dealers": 0, "loaners": 0, "lots": ["LOT-0065"], "stop_sale_vins": 39, "owners": 44}

### H-030 — quality_hold — PASS
> Nonconformance report: cloth seats lot LOT-0338 from Harbor, used at the Greensboro plant on builds 2/25 to 2027-03-01, shows water ingress. Contain and hold.
- Read as: `quality_hold` (reader: qwen3:0.6b)
- Stats: {"writes": 187, "calls": 187, "moved": 0, "rescheduled": 0, "transferred": 0, "expected_moves": 0, "dealers": 0, "loaners": 0, "lots": ["LOT-0338"], "stop_sale_vins": 122, "owners": 151}

### H-031 — quality_hold — PASS
> Nonconformance report: harness C lot LOT-0282 from Volt, used at the Huntsville plant on builds February 25th to March 1st, shows a software checksum error. Contain and hold.
- Read as: `quality_hold` (reader: qwen3:0.6b)
- Stats: {"writes": 73, "calls": 73, "moved": 0, "rescheduled": 0, "transferred": 0, "expected_moves": 0, "dealers": 0, "loaners": 0, "lots": ["LOT-0282"], "stop_sale_vins": 39, "owners": 51}

### H-032 — plant_outage — PASS
> the Mississippi plant will be offline Tue 30 March through Thu 1 April because of a burst water main.
- Read as: `plant_outage` (reader: qwen3:0.6b)
- Stats: {"writes": 55, "calls": 55, "moved": 9, "rescheduled": 2, "transferred": 7, "expected_moves": 9, "dealers": 31, "loaners": 15, "lots": [], "stop_sale_vins": 0, "owners": 0}

### H-033 — unconfirmed — PASS
> is it true P_NC might lose power next month? someone was talking about it
- Read as: `unconfirmed` (reader: qwen3:0.6b)
- Stats: {"writes": 0, "calls": 1}

### H-034 — noise — PASS
> Volunteer day at the Huntsville food bank is next Saturday. Sign up on the portal.
- Read as: `noise` (reader: qwen3:0.6b)
- Stats: {"writes": 0, "calls": 0}

### H-035 — compound — PASS
> Line stoppage at Princeton: a roof collapse in the paint shop. No production from 2027-03-23 to Wed 24 March. Also, containment request: hold LOT-0192. infotainment chips, water ingress. Builds at P_IN between 3/4 and 2027-03-05.
- Read as: `plant_outage+quality_hold` (reader: qwen3:0.6b, qwen3:0.6b)
- Stats: {"writes": 142, "calls": 142, "moved": 6, "rescheduled": 6, "transferred": 0, "expected_moves": 6, "dealers": 26, "loaners": 13, "lots": ["LOT-0192"], "stop_sale_vins": 50, "owners": 72}

### H-036 — unconfirmed — PASS
> unverified: the San Antonio plant may shut a line at some point
- Read as: `unconfirmed` (reader: qwen3:0.6b)
- Stats: {"writes": 0, "calls": 1}

### H-037 — compound — PASS
> Daily summary. (1) A minor earthquake was felt near Lima, Peru; no damage reported. (2) the San Antonio plant closed 3/23 - the 26th (an electrical fire). will update
- Read as: `noise+plant_outage` (reader: qwen3:0.6b, qwen3:0.6b)
- Stats: {"writes": 75, "calls": 75, "moved": 12, "rescheduled": 10, "transferred": 2, "expected_moves": 12, "dealers": 35, "loaners": 28, "lots": [], "stop_sale_vins": 0, "owners": 0}

### H-038 — supplier_delay — PASS
> ETA change: standard wiring harness for Princeton. Was the 15th, now 3/17. - Volt logistics
- Read as: `supplier_delay` (reader: qwen3:0.6b)
- Stats: {"writes": 20, "calls": 20, "moved": 2, "rescheduled": 2, "transferred": 0, "expected_moves": 2, "dealers": 13, "loaners": 5, "lots": [], "stop_sale_vins": 0, "owners": 0}

### H-039 — plant_outage — PASS
> No production at P_KY on the 17th due to a press line breakdown. Normal schedule the next working day.
- Read as: `plant_outage` (reader: rules)
- Stats: {"writes": 26, "calls": 26, "moved": 3, "rescheduled": 3, "transferred": 0, "expected_moves": 3, "dealers": 16, "loaners": 7, "lots": [], "stop_sale_vins": 0, "owners": 0}

### H-040 — quality_hold — PASS
> Containment request: hold LOT-0040. 20-inch tires, a software checksum error. Builds at the San Antonio plant between 2027-03-04 and Fri 5 March.
- Read as: `quality_hold` (reader: qwen3:0.6b)
- Stats: {"writes": 98, "calls": 98, "moved": 0, "rescheduled": 0, "transferred": 0, "expected_moves": 0, "dealers": 0, "loaners": 0, "lots": ["LOT-0040"], "stop_sale_vins": 58, "owners": 65}

### H-041 — supplier_delay — PASS
> We regret to inform you that delivery of brake kits to P_AL, slated for 3/22, has been postponed until 3/26. Regards, Sterling Safety
- Read as: `supplier_delay` (reader: qwen3:0.6b)
- Stats: {"writes": 54, "calls": 54, "moved": 8, "rescheduled": 8, "transferred": 0, "expected_moves": 8, "dealers": 33, "loaners": 13, "lots": [], "stop_sale_vins": 0, "owners": 0}

### H-042 — supplier_delay — FAIL
> ETA change: 20-inch alloy wheels for Princeton. Was the 29th, now Thu 1 April. - SUP-03 logistics
- Read as: `unconfirmed` (reader: rules)
- Stats: {"writes": 0, "calls": 1, "moved": 0, "rescheduled": 0, "transferred": 0, "expected_moves": 3, "dealers": 0, "loaners": 0, "lots": [], "stop_sale_vins": 0, "owners": 0}
- FAIL: incident kinds ['none'] expected ['supplier_delay']
- FAIL: escalated although the event is actionable / noise
- FAIL: 3 affected PO(s) not moved: ['PO-0347', 'PO-0350', 'PO-0353']
- FAIL: dealer set: extra [], missing ['D06', 'D07', 'D08', 'D16', 'D21']
- FAIL: loaners: extra [], missing ['CO-02064', 'CO-02068', 'CO-02069', 'CO-02089', 'CO-02092']
- warn: only 0 kind(s) of write action (handbook rule 9 wants 3)

### H-043 — unconfirmed — PASS
> Heard Orbit Optics could be behind on something, didn't catch what. Will call back.
- Read as: `unconfirmed` (reader: qwen3:0.6b)
- Stats: {"writes": 0, "calls": 1}

### H-044 — plant_outage — PASS
> Huntsville will be offline 3/26 through March 29th because of a roof collapse in the paint shop.
- Read as: `plant_outage` (reader: qwen3:0.6b)
- Stats: {"writes": 43, "calls": 43, "moved": 6, "rescheduled": 6, "transferred": 0, "expected_moves": 6, "dealers": 26, "loaners": 11, "lots": [], "stop_sale_vins": 0, "owners": 0}

### H-045 — plant_outage — PASS
> the Lexngton plant down all day Tuesday the 9th (an IT system failure).
- Read as: `plant_outage` (reader: rules)
- Stats: {"writes": 28, "calls": 28, "moved": 3, "rescheduled": 3, "transferred": 0, "expected_moves": 3, "dealers": 19, "loaners": 6, "lots": [], "stop_sale_vins": 0, "owners": 0}

### H-046 — supplier_delay — PASS
> Shipment SH-0018: arrival moved from next Monday to March 19th. Reason: a labor shortage. Supplier: SUP-07. Part: HARN-B. Ship to: Wacky Wheels San Antonio.
- Read as: `supplier_delay` (reader: qwen3:0.6b)
- Stats: {"writes": 52, "calls": 52, "moved": 8, "rescheduled": 8, "transferred": 0, "expected_moves": 8, "dealers": 30, "loaners": 14, "lots": [], "stop_sale_vins": 0, "owners": 0}

### H-047 — supplier_delay — FAIL
> We regret to inform you that delivery of surround-view camera kits to the Alabama plant, slated for Monday the 22nd, has been postponed until 2027-03-25. Regards, Orbit
- Read as: `plant_outage` (reader: qwen3:0.6b)
- Stats: {"writes": 64, "calls": 64, "moved": 12, "rescheduled": 6, "transferred": 0, "expected_moves": 6, "dealers": 36, "loaners": 16, "lots": [], "stop_sale_vins": 0, "owners": 0}
- FAIL: incident kinds ['plant_outage'] expected ['supplier_delay']
- FAIL: 6 unaffected PO(s) moved: ['PO-0422', 'PO-0425', 'PO-0428', 'PO-0430', 'PO-0431']
- FAIL: dealer set: extra ['D11', 'D18', 'D22', 'D31', 'D35'], missing []
- FAIL: dealer D02 order list: extra ['CO-02498', 'CO-02515'], missing []
- FAIL: dealer D03 order list: extra ['CO-02523', 'CO-02525', 'CO-02539'], missing []
- FAIL: dealer D05 order list: extra ['CO-02518'], missing []
- FAIL: dealer D06 order list: extra ['CO-02501', 'CO-02503', 'CO-02505'], missing []
- FAIL: dealer D08 order list: extra ['CO-02471', 'CO-02528'], missing []
- FAIL: dealer D12 order list: extra ['CO-02448'], missing []
- FAIL: dealer D19 order list: extra ['CO-02522'], missing []
- FAIL: dealer D20 order list: extra ['CO-02529', 'CO-02532', 'CO-02536'], missing []
- FAIL: dealer D23 order list: extra ['CO-02444', 'CO-02520', 'CO-02535'], missing []
- FAIL: dealer D24 order list: extra ['CO-02469'], missing []
- FAIL: dealer D25 order list: extra ['CO-02445', 'CO-02449', 'CO-02476'], missing []
- FAIL: dealer D26 order list: extra ['CO-02470', 'CO-02497', 'CO-02500'], missing []
- FAIL: dealer D29 order list: extra ['CO-02475'], missing []
- FAIL: dealer D32 order list: extra ['CO-02451'], missing []
- FAIL: dealer D36 order list: extra ['CO-02474', 'CO-02530'], missing []
- FAIL: dealer D39 order list: extra ['CO-02472', 'CO-02519'], missing []
- FAIL: dealer D44 order list: extra ['CO-02524'], missing []
- FAIL: dealer D45 order list: extra ['CO-02504', 'CO-02540'], missing []
- FAIL: dealer D46 order list: extra ['CO-02446', 'CO-02450', 'CO-02499'], missing []
- FAIL: loaners: extra ['CO-02502', 'CO-02523', 'CO-02528', 'CO-02530', 'CO-02539'], missing []
- warn: PO-0421 rescheduled to 2027-03-26 though P_AL still has a free slot on 2027-03-25
- warn: PO-0423 rescheduled to 2027-03-29 though P_AL still has a free slot on 2027-03-25
- warn: PO-0424 rescheduled to 2027-03-29 though P_AL still has a free slot on 2027-03-25
- warn: PO-0426 rescheduled to 2027-03-30 though P_AL still has a free slot on 2027-03-25
- warn: PO-0427 rescheduled to 2027-03-31 though P_AL still has a free slot on 2027-03-25
- warn: PO-0429 rescheduled to 2027-04-01 though P_AL still has a free slot on 2027-03-25

### H-048 — plant_outage — PASS
> No production at Lexington on March 26th due to an electrical fire. Normal schedule the next working day.
- Read as: `plant_outage` (reader: qwen3:0.6b)
- Stats: {"writes": 27, "calls": 27, "moved": 3, "rescheduled": 3, "transferred": 0, "expected_moves": 3, "dealers": 17, "loaners": 7, "lots": [], "stop_sale_vins": 0, "owners": 0}

### H-049 — supplier_delay — FAIL
> ETA change: 17-inch alloy wheels for Wacky Wheels Huntsville. Was the 29th, now April 1st. - Cobalt logistics
- Read as: `unconfirmed` (reader: rules)
- Stats: {"writes": 0, "calls": 1, "moved": 0, "rescheduled": 0, "transferred": 0, "expected_moves": 6, "dealers": 0, "loaners": 0, "lots": [], "stop_sale_vins": 0, "owners": 0}
- FAIL: incident kinds ['none'] expected ['supplier_delay']
- FAIL: escalated although the event is actionable / noise
- FAIL: 6 affected PO(s) not moved: ['PO-0437', 'PO-0438', 'PO-0440', 'PO-0441', 'PO-0443']
- FAIL: dealer set: extra [], missing ['D02', 'D04', 'D06', 'D08', 'D10']
- FAIL: loaners: extra [], missing ['CO-02575', 'CO-02578', 'CO-02579', 'CO-02587', 'CO-02590']
- warn: only 0 kind(s) of write action (handbook rule 9 wants 3)

### H-050 — plant_outage — PASS
> Production at the Princeton plant is suspended starting March 12th after a press line breakdown; we expect to be back up on next Tuesday.
- Read as: `plant_outage` (reader: qwen3:0.6b)
- Stats: {"writes": 50, "calls": 50, "moved": 6, "rescheduled": 6, "transferred": 0, "expected_moves": 6, "dealers": 32, "loaners": 12, "lots": [], "stop_sale_vins": 0, "owners": 0}

### H-051 — unconfirmed — PASS
> Not sure if true, but a friend at Ridgeline Wire says they may run short on parts soon.
- Read as: `unconfirmed` (reader: qwen3:0.6b)
- Stats: {"writes": 0, "calls": 1}

### H-052 — supplier_delay — PASS
> fyi brake kits from Sentinel into Greensboro is running behind, expected the 29th but more like 2027-04-01 now
- Read as: `supplier_delay` (reader: rules)
- Stats: {"writes": 57, "calls": 57, "moved": 9, "rescheduled": 4, "transferred": 5, "expected_moves": 9, "dealers": 34, "loaners": 14, "lots": [], "stop_sale_vins": 0, "owners": 0}

### H-053 — quality_hold — FAIL
> Kestrel flagged a software checksum error in center screens shipped to the Huntsville plant; vehicles assembled February 25th through 2027-03-01 are affected.
- Read as: `noise` (reader: rules)
- Stats: {"writes": 0, "calls": 0, "moved": 0, "rescheduled": 0, "transferred": 0, "expected_moves": 0, "dealers": 0, "loaners": 0, "lots": [], "stop_sale_vins": 0, "owners": 0}
- FAIL: incident kinds ['none'] expected ['quality_hold']
- FAIL: lots held [] expected ['LOT-0266']
- FAIL: stop-sale VINs: got 0 expected 36 (extra [], missing ['AUR0003844', 'AUR0003846', 'AUR0003848'])
- FAIL: owners notified: got 0 expected 45 (extra [], missing ['C0194', 'C0473', 'C0601'])
- warn: only 0 kind(s) of write action (handbook rule 9 wants 3)

### H-054 — supplier_delay — PASS
> We regret to inform you that delivery of airbag module to the Kentucky plant, slated for the 29th, has been postponed until March 30th. Regards, Sterling Safety
- Read as: `supplier_delay` (reader: rules)
- Stats: {"writes": 25, "calls": 25, "moved": 3, "rescheduled": 3, "transferred": 0, "expected_moves": 3, "dealers": 18, "loaners": 4, "lots": [], "stop_sale_vins": 0, "owners": 0}

### H-055 — unconfirmed — PASS
> Heard Cobalt Wheels could be behind on something, didn't catch what. Will call back.
- Read as: `unconfirmed` (reader: qwen3:0.6b)
- Stats: {"writes": 0, "calls": 1}

### H-056 — quality_hold — PASS
> Containment request: hold LOT-0202. harness A, contaminated grease. Builds at Wacky Wheels Princeton between Thu 25 February and Mon 1 March.
- Read as: `quality_hold` (reader: qwen3:0.6b)
- Stats: {"writes": 76, "calls": 76, "moved": 0, "rescheduled": 0, "transferred": 0, "expected_moves": 0, "dealers": 0, "loaners": 0, "lots": ["LOT-0202"], "stop_sale_vins": 44, "owners": 46}

### H-057 — supplier_delay — FAIL
> SUP-14 can't ship the 20-inch alloy wheels to Huntsville on Mon 22 March as planned; earliest is 2027-03-24 (a labor shortage).
- Read as: `unconfirmed` (reader: rules)
- Stats: {"writes": 0, "calls": 1, "moved": 0, "rescheduled": 0, "transferred": 0, "expected_moves": 2, "dealers": 0, "loaners": 0, "lots": [], "stop_sale_vins": 0, "owners": 0}
- FAIL: incident kinds ['none'] expected ['supplier_delay']
- FAIL: escalated although the event is actionable / noise
- FAIL: 2 affected PO(s) not moved: ['PO-0421', 'PO-0424']
- FAIL: dealer set: extra [], missing ['D02', 'D08', 'D12', 'D16', 'D20']
- FAIL: loaners: extra [], missing ['CO-02435', 'CO-02441', 'CO-02463', 'CO-02466', 'CO-02468']
- warn: only 0 kind(s) of write action (handbook rule 9 wants 3)

### H-058 — quality_hold — PASS
> Nonconformance report: surround-view camera kits lot LOT-0060 from Orbit, used at Wacky Wheels Lexington on builds Thursday the 4th to March 5th, shows contaminated grease. Contain and hold.
- Read as: `quality_hold` (reader: qwen3:0.6b)
- Stats: {"writes": 94, "calls": 94, "moved": 0, "rescheduled": 0, "transferred": 0, "expected_moves": 0, "dealers": 0, "loaners": 0, "lots": ["LOT-0060"], "stop_sale_vins": 49, "owners": 65}

### H-059 — plant_outage — PASS
> San Antonio will be offline March 17th through Friday the 19th because of an IT system failure.
- Read as: `plant_outage` (reader: qwen3:0.6b)
- Stats: {"writes": 55, "calls": 55, "moved": 9, "rescheduled": 9, "transferred": 0, "expected_moves": 9, "dealers": 30, "loaners": 16, "lots": [], "stop_sale_vins": 0, "owners": 0}

### H-060 — noise — PASS
> The San Antonio plant's open house for families is on Saturday. Refreshments provided.
- Read as: `noise` (reader: qwen3:0.6b)
- Stats: {"writes": 0, "calls": 0}

### H-061 — noise — PASS
> Can we get the new window stickers in Spanish as well? - Shreveport
- Read as: `noise` (reader: rules)
- Stats: {"writes": 0, "calls": 0}

### H-062 — noise — PASS
> Fleet sales promotion extended through the end of the quarter.
- Read as: `noise` (reader: qwen3:0.6b)
- Stats: {"writes": 0, "calls": 0}

### H-063 — noise — PASS
> Who left a blue umbrella in conference room B?
- Read as: `noise` (reader: rules)
- Stats: {"writes": 0, "calls": 0}

### H-064 — quality_hold — PASS
> Recall alert - brake kits from Sentinel Brake and Airbag at Lexington, build dates 2027-02-22 to 2/24: water ingress.
- Read as: `quality_hold` (reader: qwen3:0.6b)
- Stats: {"writes": 178, "calls": 178, "moved": 0, "rescheduled": 0, "transferred": 0, "expected_moves": 0, "dealers": 0, "loaners": 0, "lots": ["LOT-0053"], "stop_sale_vins": 127, "owners": 139}

### H-065 — compound — PASS
> Stock markets closed higher today on strong tech earnings. Also, production at Wacky Wheels Jackson is suspended starting 3/24 after an IT system failure; we expect to be back up on March 30th.
- Read as: `plant_outage` (reader: qwen3:0.6b)
- Stats: {"writes": 70, "calls": 70, "moved": 12, "rescheduled": 8, "transferred": 4, "expected_moves": 12, "dealers": 37, "loaners": 21, "lots": [], "stop_sale_vins": 0, "owners": 0}

### H-066 — noise — PASS
> Volunteer day at the Jackson food bank is next Saturday. Sign up on the portal.
- Read as: `noise` (reader: qwen3:0.6b)
- Stats: {"writes": 0, "calls": 0}

### H-067 — quality_hold — PASS
> Containment request: hold LOT-0040. 20-inch all-season tires, water ingress. Builds at San Antonio between Thu 4 March and the 5th.
- Read as: `quality_hold` (reader: qwen3:0.6b)
- Stats: {"writes": 98, "calls": 98, "moved": 0, "rescheduled": 0, "transferred": 0, "expected_moves": 0, "dealers": 0, "loaners": 0, "lots": ["LOT-0040"], "stop_sale_vins": 58, "owners": 65}

### H-068 — quality_hold — PASS
> Nonconformance report: compact wiring harness lot LOT-0281 from SUP-05, used at the Huntsville plant on builds Mon 22 February to February 24th, shows a software checksum error. Contain and hold.
- Read as: `quality_hold` (reader: qwen3:0.6b)
- Stats: {"writes": 74, "calls": 74, "moved": 0, "rescheduled": 0, "transferred": 0, "expected_moves": 0, "dealers": 0, "loaners": 0, "lots": ["LOT-0281"], "stop_sale_vins": 45, "owners": 47}

### H-069 — quality_hold — PASS
> Recall alert - BRAKE-KIT from Sterling at the Mississippi plant, build dates 2027-02-22 to February 24th: delamination.
- Read as: `quality_hold` (reader: qwen3:0.6b)
- Stats: {"writes": 131, "calls": 131, "moved": 0, "rescheduled": 0, "transferred": 0, "expected_moves": 0, "dealers": 0, "loaners": 0, "lots": ["LOT-0121"], "stop_sale_vins": 78, "owners": 97}

### H-070 — plant_outage — PASS
> No production at the Lexingon plant on March 18th due to a press line breakdown. Normal schedule the next working day.
- Read as: `plant_outage` (reader: rules)
- Stats: {"writes": 29, "calls": 29, "moved": 3, "rescheduled": 3, "transferred": 0, "expected_moves": 3, "dealers": 18, "loaners": 8, "lots": [], "stop_sale_vins": 0, "owners": 0}

### H-071 — compound — PASS
> Daily summary. (1) fyi 16-inch alloy wheel from Ironwood into the San Antonio plant is running behind, expected next Mon but more like Tue 16 March now (2) We regret to inform you that delivery of 17-inch rims to the Jacson plant, slated for the 15th, has been postponed until Thursday the 18th. Regards, SUP-03
- Read as: `supplier_delay+supplier_delay` (reader: rules, rules)
- Stats: {"writes": 55, "calls": 55, "moved": 7, "rescheduled": 7, "transferred": 0, "expected_moves": 7, "dealers": 34, "loaners": 14, "lots": [], "stop_sale_vins": 0, "owners": 0}

### H-072 — compound — PASS
> Two updates: 1) Volunteer day at the Jackson food bank is next Saturday. Sign up on the portal. 2) Production at Jackson is suspended starting the 16th after a substation failure; we expect to be back up on 23 Mar.
- Read as: `noise+plant_outage` (reader: qwen3:0.6b, qwen3:0.6b)
- Stats: {"writes": 83, "calls": 83, "moved": 15, "rescheduled": 15, "transferred": 0, "expected_moves": 15, "dealers": 37, "loaners": 31, "lots": [], "stop_sale_vins": 0, "owners": 0}

### H-073 — supplier_delay — FAIL
> Voicemail from Meridian Seating: the SEAT-FAB order headed to Jackson is rescheduled from the 15th to Fri 19 March.
- Read as: `noise` (reader: rules)
- Stats: {"writes": 0, "calls": 0, "moved": 0, "rescheduled": 0, "transferred": 0, "expected_moves": 8, "dealers": 0, "loaners": 0, "lots": [], "stop_sale_vins": 0, "owners": 0}
- FAIL: incident kinds ['none'] expected ['supplier_delay']
- FAIL: 8 affected PO(s) not moved: ['PO-0226', 'PO-0228', 'PO-0229', 'PO-0231', 'PO-0232']
- FAIL: dealer set: extra [], missing ['D02', 'D03', 'D05', 'D06', 'D07']
- FAIL: loaners: extra [], missing ['CO-01222', 'CO-01223', 'CO-01242', 'CO-01249', 'CO-01250']
- warn: only 0 kind(s) of write action (handbook rule 9 wants 3)

### H-074 — plant_outage — PASS
> Line stoppage at Greensboro: a burst water main. No production from March 12th to 15 Mar.
- Read as: `plant_outage` (reader: qwen3:0.6b)
- Stats: {"writes": 44, "calls": 44, "moved": 6, "rescheduled": 6, "transferred": 0, "expected_moves": 6, "dealers": 25, "loaners": 13, "lots": [], "stop_sale_vins": 0, "owners": 0}

### H-075 — noise — PASS
> The quarterly sales webinar moves to Thursday afternoon. Same link as before.
- Read as: `noise` (reader: qwen3:0.6b)
- Stats: {"writes": 0, "calls": 0}

### H-076 — quality_hold — PASS
> Nonconformance report: brake kits lot LOT-0005 from Sterling Safety, used at the Texas plant on builds Mon 22 February to 2/24, shows delamination. Contain and hold.
- Read as: `quality_hold` (reader: qwen3:0.6b)
- Stats: {"writes": 184, "calls": 184, "moved": 0, "rescheduled": 0, "transferred": 0, "expected_moves": 0, "dealers": 0, "loaners": 0, "lots": ["LOT-0005"], "stop_sale_vins": 127, "owners": 141}

### H-077 — unconfirmed — PASS
> Heard Harbor Seating could be behind on something, didn't catch what. Will call back.
- Read as: `unconfirmed` (reader: qwen3:0.6b)
- Stats: {"writes": 0, "calls": 1}

### H-078 — plant_outage — PASS
> Production at P_NC is suspended starting 10 Mar after a press line breakdown; we expect to be back up on Fri 12 March.
- Read as: `plant_outage` (reader: qwen3:0.6b)
- Stats: {"writes": 38, "calls": 38, "moved": 6, "rescheduled": 6, "transferred": 0, "expected_moves": 6, "dealers": 23, "loaners": 9, "lots": [], "stop_sale_vins": 0, "owners": 0}

### H-079 — supplier_delay — PASS
> ETA change: 17-inch tires for Wacky Wheels Lexington. Was Mon 22 March, now 3/25. - SUP-02 logistics
- Read as: `supplier_delay` (reader: qwen3:0.6b)
- Stats: {"writes": 46, "calls": 46, "moved": 6, "rescheduled": 6, "transferred": 0, "expected_moves": 6, "dealers": 28, "loaners": 12, "lots": [], "stop_sale_vins": 0, "owners": 0}

### H-080 — plant_outage — PASS
> Line stoppage at Greensboro: an electrical fire. No production from 2027-03-10 to 3/11.
- Read as: `plant_outage` (reader: qwen3:0.6b)
- Stats: {"writes": 38, "calls": 38, "moved": 6, "rescheduled": 6, "transferred": 0, "expected_moves": 6, "dealers": 23, "loaners": 9, "lots": [], "stop_sale_vins": 0, "owners": 0}

### H-081 — quality_hold — PASS
> Recall alert - minivan seats from SUP-15 at the Kentucky plant, build dates February 25th to Mon 1 March: contaminated grease.
- Read as: `quality_hold` (reader: qwen3:0.6b)
- Stats: {"writes": 68, "calls": 68, "moved": 0, "rescheduled": 0, "transferred": 0, "expected_moves": 0, "dealers": 0, "loaners": 0, "lots": ["LOT-0094"], "stop_sale_vins": 39, "owners": 43}

### H-082 — unconfirmed — FAIL
> Some folks think a batch of airbags might be bad. No lot number, no dates.
- Read as: `noise` (reader: rules)
- Stats: {"writes": 0, "calls": 0}
- FAIL: expected an escalate, none made

### H-083 — supplier_delay — FAIL
> Cobalt can't ship the 16-inch alloy wheels to P_NC on Monday the 15th as planned; earliest is the 17th (weather at the port).
- Read as: `unconfirmed` (reader: rules)
- Stats: {"writes": 0, "calls": 1, "moved": 0, "rescheduled": 0, "transferred": 0, "expected_moves": 2, "dealers": 0, "loaners": 0, "lots": [], "stop_sale_vins": 0, "owners": 0}
- FAIL: incident kinds ['none'] expected ['supplier_delay']
- FAIL: escalated although the event is actionable / noise
- FAIL: 2 affected PO(s) not moved: ['PO-0497', 'PO-0500']
- FAIL: dealer set: extra [], missing ['D05', 'D08', 'D12', 'D20', 'D26']
- FAIL: loaners: extra [], missing ['CO-02860', 'CO-02864', 'CO-02886', 'CO-02890']
- warn: only 0 kind(s) of write action (handbook rule 9 wants 3)

### H-084 — unconfirmed — PASS
> Not sure if true, but a friend at Sterling Safety says they may run short on parts soon.
- Read as: `unconfirmed` (reader: qwen3:0.6b)
- Stats: {"writes": 0, "calls": 1}

### H-085 — plant_outage — PASS
> Line stoppage at the Indiana plant: a substation failure. No production from 2027-03-10 to next Monday.
- Read as: `plant_outage` (reader: qwen3:0.6b)
- Stats: {"writes": 76, "calls": 76, "moved": 12, "rescheduled": 12, "transferred": 0, "expected_moves": 12, "dealers": 40, "loaners": 24, "lots": [], "stop_sale_vins": 0, "owners": 0}

### H-086 — plant_outage — PASS
> Production at Jackson is suspended starting Tue 23 March after a roof collapse in the paint shop; we expect to be back up on 2027-03-26.
- Read as: `plant_outage` (reader: qwen3:0.6b)
- Stats: {"writes": 59, "calls": 59, "moved": 9, "rescheduled": 9, "transferred": 0, "expected_moves": 9, "dealers": 34, "loaners": 16, "lots": [], "stop_sale_vins": 0, "owners": 0}

### H-087 — plant_outage — PASS
> Production at San Antonio is suspended starting March 22nd after a substation failure; we expect to be back up on March 29th.
- Read as: `plant_outage` (reader: qwen3:0.6b)
- Stats: {"writes": 86, "calls": 86, "moved": 15, "rescheduled": 10, "transferred": 5, "expected_moves": 15, "dealers": 40, "loaners": 31, "lots": [], "stop_sale_vins": 0, "owners": 0}

### H-088 — unconfirmed — PASS
> Chatter about a port strike that could hit deliveries. No specifics.
- Read as: `unconfirmed` (reader: qwen3:0.6b)
- Stats: {"writes": 0, "calls": 1}

### H-089 — quality_hold — PASS
> Containment request: hold LOT-0074. standard wiring harness, delamination. Builds at Lexington between 25 Feb and 1 Mar.
- Read as: `quality_hold` (reader: qwen3:0.6b)
- Stats: {"writes": 68, "calls": 68, "moved": 0, "rescheduled": 0, "transferred": 0, "expected_moves": 0, "dealers": 0, "loaners": 0, "lots": ["LOT-0074"], "stop_sale_vins": 54, "owners": 35}

### H-090 — compound — FAIL
> Daily summary. (1) Ridgeline Wire flagged porosity in the castings in harness A shipped to the Greensboro plant; vehicles assembled 2027-03-04 through 5 Mar are affected. (2) Apparently freight problems are causing delays somewhere upstream. Not confirmed.
- Read as: `noise+unconfirmed` (reader: rules, qwen3:0.6b)
- Stats: {"writes": 0, "calls": 1, "moved": 0, "rescheduled": 0, "transferred": 0, "expected_moves": 0, "dealers": 0, "loaners": 0, "lots": [], "stop_sale_vins": 0, "owners": 0}
- FAIL: incident kinds ['none'] expected ['quality_hold']
- FAIL: lots held [] expected ['LOT-0328']
- FAIL: stop-sale VINs: got 0 expected 36 (extra [], missing ['AUR0005166', 'AUR0005167', 'AUR0005168'])
- FAIL: owners notified: got 0 expected 31 (extra [], missing ['C0016', 'C0081', 'C0085'])
- warn: only 0 kind(s) of write action (handbook rule 9 wants 3)

### H-091 — compound — PASS
> Line stoppage at Wacky Wheels Jackson: a roof collapse in the paint shop. No production from March 24th to 2027-03-25. Also, ridgeline flagged an incorrect torque spec in compact wiring harness shipped to Princeton; vehicles assembled the 4th through the 5th are affected.
- Read as: `plant_outage+quality_hold` (reader: qwen3:0.6b, qwen3:0.6b)
- Stats: {"writes": 94, "calls": 94, "moved": 6, "rescheduled": 6, "transferred": 0, "expected_moves": 6, "dealers": 27, "loaners": 9, "lots": ["LOT-0212"], "stop_sale_vins": 27, "owners": 32}

### H-092 — plant_outage — FAIL
> Lexington closed 16 Mar - Friday the 19th (a chemical spill). will update
- Read as: `noise` (reader: qwen3:0.6b)
- Stats: {"writes": 0, "calls": 0, "moved": 0, "rescheduled": 0, "transferred": 0, "expected_moves": 12, "dealers": 0, "loaners": 0, "lots": [], "stop_sale_vins": 0, "owners": 0}
- FAIL: incident kinds ['none'] expected ['plant_outage']
- FAIL: 12 affected PO(s) not moved: ['PO-0139', 'PO-0140', 'PO-0141', 'PO-0142', 'PO-0143']
- FAIL: dealer set: extra [], missing ['D01', 'D02', 'D03', 'D04', 'D05']
- FAIL: loaners: extra [], missing ['CO-00725', 'CO-00727', 'CO-00729', 'CO-00736', 'CO-00737']
- warn: only 0 kind(s) of write action (handbook rule 9 wants 3)

### H-093 — unconfirmed — PASS
> Possibly an issue brewing at P_NC. Nobody can confirm anything yet.
- Read as: `unconfirmed` (reader: qwen3:0.6b)
- Stats: {"writes": 0, "calls": 1}

### H-094 — quality_hold — PASS
> Atlas flagged contaminated grease in harness B shipped to the Texas plant; vehicles assembled 2/22 through February 24th are affected.
- Read as: `quality_hold` (reader: qwen3:0.6b)
- Stats: {"writes": 131, "calls": 131, "moved": 0, "rescheduled": 0, "transferred": 0, "expected_moves": 0, "dealers": 0, "loaners": 0, "lots": ["LOT-0017"], "stop_sale_vins": 86, "owners": 94}

### H-095 — plant_outage — PASS
> No production at Lexington on 2027-03-23 due to a severe storm. Normal schedule the next working day.
- Read as: `plant_outage` (reader: rules)
- Stats: {"writes": 27, "calls": 27, "moved": 3, "rescheduled": 3, "transferred": 0, "expected_moves": 3, "dealers": 18, "loaners": 6, "lots": [], "stop_sale_vins": 0, "owners": 0}

### H-096 — unconfirmed — PASS
> is it true Huntsville might lose power next month? someone was talking about it
- Read as: `unconfirmed` (reader: qwen3:0.6b)
- Stats: {"writes": 0, "calls": 1}

### H-097 — supplier_delay — PASS
> Voicemail from Sentinel: the airbag module order headed to Jackson is rescheduled from 15 Mar to Tue 16 March.
- Read as: `supplier_delay` (reader: qwen3:0.6b)
- Stats: {"writes": 26, "calls": 26, "moved": 3, "rescheduled": 3, "transferred": 0, "expected_moves": 3, "dealers": 20, "loaners": 3, "lots": [], "stop_sale_vins": 0, "owners": 0}

### H-098 — supplier_delay — PASS
> ETA change: brake kits for the Lexington plant. Was the 22nd, now 25 Mar. - Sentinel logistics
- Read as: `supplier_delay` (reader: qwen3:0.6b)
- Stats: {"writes": 59, "calls": 59, "moved": 9, "rescheduled": 9, "transferred": 0, "expected_moves": 9, "dealers": 34, "loaners": 16, "lots": [], "stop_sale_vins": 0, "owners": 0}

### H-099 — quality_hold — PASS
> Nonconformance report: 20-inch all-season tire lot LOT-0299 from SUP-02, used at Huntsville on builds March 2nd to March 3rd, shows contaminated grease. Contain and hold.
- Read as: `quality_hold` (reader: qwen3:0.6b)
- Stats: {"writes": 59, "calls": 59, "moved": 0, "rescheduled": 0, "transferred": 0, "expected_moves": 0, "dealers": 0, "loaners": 0, "lots": ["LOT-0299"], "stop_sale_vins": 26, "owners": 43}

### H-100 — supplier_delay — PASS
> We regret to inform you that delivery of airbag modules to the Lexigton plant, slated for Monday the 29th, has been postponed until Wed 31 March. Regards, Sterling Safety
- Read as: `supplier_delay` (reader: rules)
- Stats: {"writes": 42, "calls": 42, "moved": 6, "rescheduled": 6, "transferred": 0, "expected_moves": 6, "dealers": 26, "loaners": 10, "lots": [], "stop_sale_vins": 0, "owners": 0}

