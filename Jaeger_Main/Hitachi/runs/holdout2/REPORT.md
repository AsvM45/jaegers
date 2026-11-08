# Hitachi control tower — held-out tests, set 2

100 cases from `tests/holdout2_cases.json`, graded by `tests/run_cases.py` against expected effects computed from the CSVs (not from tower/graph.py).

| Case | Category | rules | qwen3:0.6b | Edge case? |
|---|---|---|---|---|
| H2-001 | plant_outage | PASS | PASS |  |
| H2-002 | noise | PASS | PASS |  |
| H2-003 | compound | FAIL ⚠ | FAIL ⚠ |  |
| H2-004 | compound | PASS | PASS |  |
| H2-005 | supplier_delay | FAIL ⚠ | FAIL ⚠ |  |
| H2-006 | unconfirmed | PASS | PASS |  |
| H2-007 | plant_outage | PASS | PASS |  |
| H2-008 | unconfirmed | PASS | PASS |  |
| H2-009 | plant_outage | PASS | PASS |  |
| H2-010 | supplier_delay | PASS | PASS |  |
| H2-011 | quality_hold | FAIL ⚠ | PASS |  |
| H2-012 | supplier_delay | PASS | PASS |  |
| H2-013 | noise | PASS | PASS |  |
| H2-014 | quality_hold | PASS | PASS |  |
| H2-015 | plant_outage | PASS | PASS |  |
| H2-016 | supplier_delay | FAIL ⚠ | FAIL ⚠ |  |
| H2-017 | supplier_delay | FAIL ⚠ | FAIL ⚠ |  |
| H2-018 | supplier_delay | PASS | PASS |  |
| H2-019 | quality_hold | FAIL ⚠ | PASS |  |
| H2-020 | plant_outage | PASS | PASS |  |
| H2-021 | supplier_delay | FAIL ⚠ | FAIL ⚠ |  |
| H2-022 | quality_hold | FAIL ⚠ | PASS |  |
| H2-023 | plant_outage | PASS | PASS |  |
| H2-024 | quality_hold | FAIL ⚠ | PASS |  |
| H2-025 | quality_hold | FAIL ⚠ | PASS |  |
| H2-026 | supplier_delay | FAIL ⚠ | FAIL ⚠ |  |
| H2-027 | compound | FAIL | PASS |  |
| H2-028 | quality_hold | FAIL ⚠ | PASS |  |
| H2-029 | unconfirmed | PASS | PASS |  |
| H2-030 | noise | PASS | PASS |  |
| H2-031 | unconfirmed | FAIL | FAIL |  |
| H2-032 | supplier_delay | FAIL ⚠ | FAIL ⚠ |  |
| H2-033 | quality_hold | FAIL ⚠ | PASS |  |
| H2-034 | noise | PASS | PASS |  |
| H2-035 | plant_outage | PASS | PASS |  |
| H2-036 | plant_outage | PASS | PASS |  |
| H2-037 | supplier_delay | PASS | PASS |  |
| H2-038 | quality_hold | FAIL ⚠ | PASS |  |
| H2-039 | compound | PASS | PASS |  |
| H2-040 | quality_hold | FAIL ⚠ | PASS |  |
| H2-041 | compound | FAIL | FAIL |  |
| H2-042 | noise | PASS | PASS |  |
| H2-043 | plant_outage | PASS | PASS |  |
| H2-044 | compound | FAIL ⚠ | FAIL ⚠ |  |
| H2-045 | unconfirmed | PASS | PASS |  |
| H2-046 | unconfirmed | FAIL | FAIL |  |
| H2-047 | supplier_delay | FAIL ⚠ | PASS |  |
| H2-048 | plant_outage | PASS | PASS |  |
| H2-049 | supplier_delay | FAIL ⚠ | FAIL ⚠ |  |
| H2-050 | plant_outage | PASS | PASS |  |
| H2-051 | noise | PASS | PASS |  |
| H2-052 | unconfirmed | PASS | PASS |  |
| H2-053 | noise | PASS | PASS |  |
| H2-054 | supplier_delay | FAIL ⚠ | FAIL ⚠ |  |
| H2-055 | quality_hold | FAIL ⚠ | PASS |  |
| H2-056 | unconfirmed | FAIL | FAIL |  |
| H2-057 | quality_hold | FAIL ⚠ | FAIL ⚠ |  |
| H2-058 | compound | FAIL | FAIL |  |
| H2-059 | quality_hold | PASS | PASS |  |
| H2-060 | plant_outage | FAIL ⚠ | FAIL ⚠ |  |
| H2-061 | plant_outage | FAIL ⚠ | PASS |  |
| H2-062 | plant_outage | PASS | PASS |  |
| H2-063 | compound | FAIL ⚠ | FAIL |  |
| H2-064 | noise | PASS | PASS |  |
| H2-065 | unconfirmed | FAIL | FAIL |  |
| H2-066 | plant_outage | PASS | PASS |  |
| H2-067 | supplier_delay | PASS | PASS |  |
| H2-068 | unconfirmed | PASS | PASS |  |
| H2-069 | compound | FAIL ⚠ | PASS |  |
| H2-070 | supplier_delay | PASS | PASS |  |
| H2-071 | quality_hold | PASS | PASS |  |
| H2-072 | plant_outage | FAIL ⚠ | PASS |  |
| H2-073 | noise | PASS | PASS |  |
| H2-074 | plant_outage | PASS | PASS |  |
| H2-075 | supplier_delay | FAIL ⚠ | FAIL ⚠ |  |
| H2-076 | unconfirmed | PASS | PASS |  |
| H2-077 | quality_hold | FAIL ⚠ | PASS |  |
| H2-078 | compound | FAIL | FAIL |  |
| H2-079 | supplier_delay | PASS | PASS |  |
| H2-080 | noise | PASS | PASS |  |
| H2-081 | compound | FAIL | FAIL |  |
| H2-082 | compound | FAIL | FAIL |  |
| H2-083 | supplier_delay | FAIL ⚠ | FAIL ⚠ |  |
| H2-084 | compound | FAIL | PASS |  |
| H2-085 | noise | PASS | PASS |  |
| H2-086 | supplier_delay | FAIL ⚠ | PASS |  |
| H2-087 | supplier_delay | FAIL ⚠ | FAIL ⚠ |  |
| H2-088 | noise | PASS | PASS |  |
| H2-089 | compound | FAIL ⚠ | PASS |  |
| H2-090 | noise | PASS | PASS |  |
| H2-091 | noise | PASS | PASS |  |
| H2-092 | plant_outage | PASS | PASS |  |
| H2-093 | plant_outage | PASS | PASS |  |
| H2-094 | plant_outage | PASS | PASS |  |
| H2-095 | quality_hold | FAIL ⚠ | PASS |  |
| H2-096 | quality_hold | FAIL ⚠ | FAIL ⚠ |  |
| H2-097 | unconfirmed | FAIL | FAIL |  |
| H2-098 | supplier_delay | FAIL ⚠ | FAIL ⚠ |  |
| H2-099 | supplier_delay | FAIL ⚠ | FAIL ⚠ |  |
| H2-100 | quality_hold | FAIL ⚠ | FAIL ⚠ |  |

**rules**: 50/100 pass
**qwen3:0.6b**: 70/100 pass

## Details — rules reader

### H2-001 — plant_outage — PASS
> Emergency: a boiler failure at Wacky Wheels Lexington. Assembly paused March 26th through March 30th.
- Read as: `plant_outage` (reader: rules)
- Stats: {"writes": 54, "calls": 54, "moved": 9, "rescheduled": 6, "transferred": 3, "expected_moves": 9, "dealers": 29, "loaners": 16, "lots": [], "stop_sale_vins": 0, "owners": 0}

### H2-002 — noise — PASS
> A car magazine review praises the ride quality of our Summit model.
- Read as: `noise` (reader: rules)
- Stats: {"writes": 0, "calls": 0}

### H2-003 — compound — FAIL
> Ridgeline missed the the 22nd delivery of harness A to Wacky Wheels Greensboro. Revised date: 2027-03-23. Separately, ridgeline Wire issued a defect notice for HARN-B supplied to the Huntsille plant, production dates March 4th through March 5th: seal leaks.
- Read as: `quality_hold` (reader: rules)
- Stats: {"writes": 0, "calls": 1, "moved": 0, "rescheduled": 0, "transferred": 0, "expected_moves": 1, "dealers": 0, "loaners": 0, "lots": [], "stop_sale_vins": 0, "owners": 0}
- FAIL: incident kinds ['quality_hold'] expected ['quality_hold', 'supplier_delay']
- FAIL: escalated although the event is actionable / noise
- FAIL: 1 affected PO(s) not moved: ['PO-0511']
- FAIL: dealer set: extra [], missing ['D02', 'D04', 'D07', 'D11', 'D20']
- FAIL: loaners: extra [], missing ['CO-02994', 'CO-02995']
- FAIL: lots held [] expected ['LOT-0280']
- FAIL: stop-sale VINs: got 0 expected 28 (extra [], missing ['AUR0004275', 'AUR0004276', 'AUR0004277'])
- FAIL: owners notified: got 0 expected 33 (extra [], missing ['C0170', 'C0353', 'C0890'])
- warn: only 0 kind(s) of write action (handbook rule 9 wants 3)

### H2-004 — compound — PASS
> A) Inbound 16-inch rims (Ironwood) to the Jackson plant: original delivery 15 Mar; now arriving Tue 16 March because of a machine breakdown at their site. B) Reminder to fill out the employee engagement survey.
- Read as: `supplier_delay` (reader: rules)
- Stats: {"writes": 11, "calls": 11, "moved": 1, "rescheduled": 1, "transferred": 0, "expected_moves": 1, "dealers": 9, "loaners": 1, "lots": [], "stop_sale_vins": 0, "owners": 0}

### H2-005 — supplier_delay — FAIL
> Update on SH-0096 (SEAT-VAN): no longer Monday the 29th, expect 31 Mar. Destination the Lexigton plant. Shipper Harbor.
- Read as: `noise` (reader: rules)
- Stats: {"writes": 0, "calls": 0, "moved": 0, "rescheduled": 0, "transferred": 0, "expected_moves": 2, "dealers": 0, "loaners": 0, "lots": [], "stop_sale_vins": 0, "owners": 0}
- FAIL: incident kinds ['none'] expected ['supplier_delay']
- FAIL: 2 affected PO(s) not moved: ['PO-0168', 'PO-0171']
- FAIL: dealer set: extra [], missing ['D02', 'D03', 'D04', 'D06', 'D08']
- FAIL: loaners: extra [], missing ['CO-00978', 'CO-01002', 'CO-01006', 'CO-01007']
- warn: only 0 kind(s) of write action (handbook rule 9 wants 3)

### H2-006 — unconfirmed — PASS
> Could be a problem with paint supply, no details yet.
- Read as: `unconfirmed` (reader: rules)
- Stats: {"writes": 0, "calls": 1}

### H2-007 — plant_outage — PASS
> Princeton is idle 2027-03-17 to Monday the 22nd due to an ammonia leak.
- Read as: `plant_outage` (reader: rules)
- Stats: {"writes": 74, "calls": 74, "moved": 12, "rescheduled": 12, "transferred": 0, "expected_moves": 12, "dealers": 35, "loaners": 27, "lots": [], "stop_sale_vins": 0, "owners": 0}

### H2-008 — unconfirmed — PASS
> Hearing Lexington might go down for maintenance soon, no dates.
- Read as: `unconfirmed` (reader: rules)
- Stats: {"writes": 0, "calls": 1}

### H2-009 — plant_outage — PASS
> Emergency: a boiler failure at the Lexington plant. Assembly paused Thursday the 25th through March 30th.
- Read as: `plant_outage` (reader: rules)
- Stats: {"writes": 68, "calls": 68, "moved": 12, "rescheduled": 6, "transferred": 6, "expected_moves": 12, "dealers": 34, "loaners": 22, "lots": [], "stop_sale_vins": 0, "owners": 0}

### H2-010 — supplier_delay — PASS
> Per Volt, harness C for the San Antonio plant got pushed out a few days: 2027-03-15 -> 2027-03-18.
- Read as: `supplier_delay` (reader: rules)
- Stats: {"writes": 31, "calls": 31, "moved": 3, "rescheduled": 3, "transferred": 0, "expected_moves": 3, "dealers": 21, "loaners": 7, "lots": [], "stop_sale_vins": 0, "owners": 0}

### H2-011 — quality_hold — FAIL
> Please quarantine LOT-0350: seal leaks in 20-inch all-season tires. the Greensoro plant builds February 25th through Monday the 1st.
- Read as: `noise` (reader: rules)
- Stats: {"writes": 0, "calls": 0, "moved": 0, "rescheduled": 0, "transferred": 0, "expected_moves": 0, "dealers": 0, "loaners": 0, "lots": [], "stop_sale_vins": 0, "owners": 0}
- FAIL: incident kinds ['none'] expected ['quality_hold']
- FAIL: lots held [] expected ['LOT-0350']
- FAIL: stop-sale VINs: got 0 expected 38 (extra [], missing ['AUR0004777', 'AUR0004784', 'AUR0004785'])
- FAIL: owners notified: got 0 expected 56 (extra [], missing ['C0002', 'C0060', 'C0071'])
- warn: only 0 kind(s) of write action (handbook rule 9 wants 3)

### H2-012 — supplier_delay — PASS
> Inbound 20-inch all-season tire (Brightline Rubber) to the Greensboro plant: original delivery 3/22; now arriving 3/25 because of a strike at their warehouse.
- Read as: `supplier_delay` (reader: rules)
- Stats: {"writes": 30, "calls": 30, "moved": 3, "rescheduled": 3, "transferred": 0, "expected_moves": 3, "dealers": 19, "loaners": 8, "lots": [], "stop_sale_vins": 0, "owners": 0}

### H2-013 — noise — PASS
> Reminder to fill out the employee engagement survey.
- Read as: `noise` (reader: rules)
- Stats: {"writes": 0, "calls": 0}

### H2-014 — quality_hold — PASS
> Ironwood Wheels issued a defect notice for 20-inch alloy wheel supplied to Wacky Wheels San Antonio, production dates 4 Mar through 2027-03-05: excess solder.
- Read as: `quality_hold` (reader: rules)
- Stats: {"writes": 98, "calls": 98, "moved": 0, "rescheduled": 0, "transferred": 0, "expected_moves": 0, "dealers": 0, "loaners": 0, "lots": ["LOT-0048"], "stop_sale_vins": 58, "owners": 65}

### H2-015 — plant_outage — PASS
> Wacky Wheels Huntsville is idle Fri 26 March to Tuesday the 30th due to a conveyor motor burnout.
- Read as: `plant_outage` (reader: rules)
- Stats: {"writes": 51, "calls": 51, "moved": 9, "rescheduled": 6, "transferred": 3, "expected_moves": 9, "dealers": 28, "loaners": 14, "lots": [], "stop_sale_vins": 0, "owners": 0}

### H2-016 — supplier_delay — FAIL
> P_AL receiving: the TIRE-17 truck from Northgate won't show 3/29. Carrier now quoting April 2nd.
- Read as: `noise` (reader: rules)
- Stats: {"writes": 0, "calls": 0, "moved": 0, "rescheduled": 0, "transferred": 0, "expected_moves": 8, "dealers": 0, "loaners": 0, "lots": [], "stop_sale_vins": 0, "owners": 0}
- FAIL: incident kinds ['none'] expected ['supplier_delay']
- FAIL: 8 affected PO(s) not moved: ['PO-0437', 'PO-0438', 'PO-0440', 'PO-0441', 'PO-0443']
- FAIL: dealer set: extra [], missing ['D02', 'D04', 'D06', 'D07', 'D08']
- FAIL: loaners: extra [], missing ['CO-02575', 'CO-02578', 'CO-02579', 'CO-02587', 'CO-02590']
- warn: only 0 kind(s) of write action (handbook rule 9 wants 3)

### H2-017 — supplier_delay — FAIL
> Update on SH-0138 (standard wiring harness): no longer 3/15, expect Wed 17 March. Destination Jackson. Shipper Ridgeline.
- Read as: `noise` (reader: rules)
- Stats: {"writes": 0, "calls": 0, "moved": 0, "rescheduled": 0, "transferred": 0, "expected_moves": 4, "dealers": 0, "loaners": 0, "lots": [], "stop_sale_vins": 0, "owners": 0}
- FAIL: incident kinds ['none'] expected ['supplier_delay']
- FAIL: 4 affected PO(s) not moved: ['PO-0226', 'PO-0227', 'PO-0229', 'PO-0230']
- FAIL: dealer set: extra [], missing ['D02', 'D03', 'D04', 'D06', 'D07']
- FAIL: loaners: extra [], missing ['CO-01222', 'CO-01223', 'CO-01249', 'CO-01250', 'CO-01253']
- warn: only 0 kind(s) of write action (handbook rule 9 wants 3)

### H2-018 — supplier_delay — PASS
> Per Quanta, CHIP-IVI for the Lexigton plant got pushed out a few days: 2027-03-22 -> March 26th.
- Read as: `supplier_delay` (reader: rules)
- Stats: {"writes": 75, "calls": 75, "moved": 12, "rescheduled": 12, "transferred": 0, "expected_moves": 12, "dealers": 38, "loaners": 25, "lots": [], "stop_sale_vins": 0, "owners": 0}

### H2-019 — quality_hold — FAIL
> QA hold: lot LOT-0230 (20-inch all-season tires from Brightline) used at the Princeton plant, builds February 25th to March 1st. Issue: wrong thread pitch.
- Read as: `noise` (reader: rules)
- Stats: {"writes": 0, "calls": 0, "moved": 0, "rescheduled": 0, "transferred": 0, "expected_moves": 0, "dealers": 0, "loaners": 0, "lots": [], "stop_sale_vins": 0, "owners": 0}
- FAIL: incident kinds ['none'] expected ['quality_hold']
- FAIL: lots held [] expected ['LOT-0230']
- FAIL: stop-sale VINs: got 0 expected 41 (extra [], missing ['AUR0002933', 'AUR0002934', 'AUR0002938'])
- FAIL: owners notified: got 0 expected 45 (extra [], missing ['C0322', 'C0544', 'C0561'])
- warn: only 0 kind(s) of write action (handbook rule 9 wants 3)

### H2-020 — plant_outage — PASS
> Emergency: a transformer fire at San Antonio. Assembly paused Fri 19 March through Wed 24 March.
- Read as: `plant_outage` (reader: rules)
- Stats: {"writes": 76, "calls": 76, "moved": 12, "rescheduled": 12, "transferred": 0, "expected_moves": 12, "dealers": 39, "loaners": 25, "lots": [], "stop_sale_vins": 0, "owners": 0}

### H2-021 — supplier_delay — FAIL
> P_KY receiving: the leather seat set truck from Meridian won't show March 29th. Carrier now quoting 2027-04-01.
- Read as: `noise` (reader: rules)
- Stats: {"writes": 0, "calls": 0, "moved": 0, "rescheduled": 0, "transferred": 0, "expected_moves": 3, "dealers": 0, "loaners": 0, "lots": [], "stop_sale_vins": 0, "owners": 0}
- FAIL: incident kinds ['none'] expected ['supplier_delay']
- FAIL: 3 affected PO(s) not moved: ['PO-0167', 'PO-0170', 'PO-0173']
- FAIL: dealer set: extra [], missing ['D02', 'D08', 'D11', 'D12', 'D19']
- FAIL: loaners: extra [], missing ['CO-00968', 'CO-00970', 'CO-00973', 'CO-01000', 'CO-01020']
- warn: only 0 kind(s) of write action (handbook rule 9 wants 3)

### H2-022 — quality_hold — FAIL
> QA hold: lot LOT-0328 (harness A from Ridgeline Wire) used at the Greensboro plant, builds 4 Mar to Friday the 5th. Issue: wrong thread pitch.
- Read as: `noise` (reader: rules)
- Stats: {"writes": 0, "calls": 0, "moved": 0, "rescheduled": 0, "transferred": 0, "expected_moves": 0, "dealers": 0, "loaners": 0, "lots": [], "stop_sale_vins": 0, "owners": 0}
- FAIL: incident kinds ['none'] expected ['quality_hold']
- FAIL: lots held [] expected ['LOT-0328']
- FAIL: stop-sale VINs: got 0 expected 36 (extra [], missing ['AUR0005166', 'AUR0005167', 'AUR0005168'])
- FAIL: owners notified: got 0 expected 31 (extra [], missing ['C0016', 'C0081', 'C0085'])
- warn: only 0 kind(s) of write action (handbook rule 9 wants 3)

### H2-023 — plant_outage — PASS
> Wacky Wheels Princeton is idle Thu 18 March to 3/22 due to an ammonia leak.
- Read as: `plant_outage` (reader: rules)
- Stats: {"writes": 53, "calls": 53, "moved": 9, "rescheduled": 9, "transferred": 0, "expected_moves": 9, "dealers": 30, "loaners": 14, "lots": [], "stop_sale_vins": 0, "owners": 0}

### H2-024 — quality_hold — FAIL
> Please quarantine LOT-0269: wrong thread pitch in sliding door module. the Huntsville plant builds February 22nd through February 24th.
- Read as: `noise` (reader: rules)
- Stats: {"writes": 0, "calls": 0, "moved": 0, "rescheduled": 0, "transferred": 0, "expected_moves": 0, "dealers": 0, "loaners": 0, "lots": [], "stop_sale_vins": 0, "owners": 0}
- FAIL: incident kinds ['none'] expected ['quality_hold']
- FAIL: lots held [] expected ['LOT-0269']
- FAIL: stop-sale VINs: got 0 expected 45 (extra [], missing ['AUR0003608', 'AUR0003610', 'AUR0003613'])
- FAIL: owners notified: got 0 expected 47 (extra [], missing ['C0049', 'C0361', 'C0577'])
- warn: only 0 kind(s) of write action (handbook rule 9 wants 3)

### H2-025 — quality_hold — FAIL
> Please quarantine LOT-0111: seal leaks in 20-inch alloy wheels. Wacky Wheels Lexington builds 3/2 through the 3rd.
- Read as: `noise` (reader: rules)
- Stats: {"writes": 0, "calls": 0, "moved": 0, "rescheduled": 0, "transferred": 0, "expected_moves": 0, "dealers": 0, "loaners": 0, "lots": [], "stop_sale_vins": 0, "owners": 0}
- FAIL: incident kinds ['none'] expected ['quality_hold']
- FAIL: lots held [] expected ['LOT-0111']
- FAIL: stop-sale VINs: got 0 expected 26 (extra [], missing ['AUR0001451', 'AUR0001452', 'AUR0001456'])
- FAIL: owners notified: got 0 expected 36 (extra [], missing ['C0062', 'C0376', 'C0447'])
- warn: only 0 kind(s) of write action (handbook rule 9 wants 3)

### H2-026 — supplier_delay — FAIL
> Northgate Tire Co missed the next Mon delivery of 20-inch all-season tire to the Hutsville plant. Revised date: March 18th.
- Read as: `noise` (reader: rules)
- Stats: {"writes": 0, "calls": 0, "moved": 0, "rescheduled": 0, "transferred": 0, "expected_moves": 3, "dealers": 0, "loaners": 0, "lots": [], "stop_sale_vins": 0, "owners": 0}
- FAIL: incident kinds ['none'] expected ['supplier_delay']
- FAIL: 3 affected PO(s) not moved: ['PO-0406', 'PO-0409', 'PO-0412']
- FAIL: dealer set: extra [], missing ['D07', 'D08', 'D10', 'D12', 'D17']
- FAIL: loaners: extra [], missing ['CO-02294', 'CO-02298', 'CO-02301', 'CO-02302', 'CO-02323']
- warn: only 0 kind(s) of write action (handbook rule 9 wants 3)

### H2-027 — compound — FAIL
> Please quarantine LOT-0217: wrong thread pitch in leather seats. Wacky Wheels Princeton builds 2027-02-22 through 2027-02-24. Separately, somebody thinks the latest driver-assist chip batch could be defective; no lot or dates.
- Read as: `quality_hold` (reader: rules)
- Stats: {"writes": 82, "calls": 82, "moved": 0, "rescheduled": 0, "transferred": 0, "expected_moves": 0, "dealers": 0, "loaners": 0, "lots": ["LOT-0217"], "stop_sale_vins": 38, "owners": 58}
- FAIL: expected an escalate, none made

### H2-028 — quality_hold — FAIL
> QA hold: lot LOT-0239 (20-inch rims from SUP-03) used at the Prineton plant, builds the 2nd to Wednesday the 3rd. Issue: intermittent shorts.
- Read as: `noise` (reader: rules)
- Stats: {"writes": 0, "calls": 0, "moved": 0, "rescheduled": 0, "transferred": 0, "expected_moves": 0, "dealers": 0, "loaners": 0, "lots": [], "stop_sale_vins": 0, "owners": 0}
- FAIL: incident kinds ['none'] expected ['quality_hold']
- FAIL: lots held [] expected ['LOT-0239']
- FAIL: stop-sale VINs: got 0 expected 35 (extra [], missing ['AUR0003202', 'AUR0003204', 'AUR0003207'])
- FAIL: owners notified: got 0 expected 34 (extra [], missing ['C0033', 'C0416', 'C1085'])
- warn: only 0 kind(s) of write action (handbook rule 9 wants 3)

### H2-029 — unconfirmed — PASS
> Gossip says Quanta Silicon is in financial trouble; could affect supply. Nothing confirmed.
- Read as: `unconfirmed` (reader: rules)
- Stats: {"writes": 0, "calls": 1}

### H2-030 — noise — PASS
> Parking permits must be renewed by the end of the month.
- Read as: `noise` (reader: rules)
- Stats: {"writes": 0, "calls": 0}

### H2-031 — unconfirmed — FAIL
> Possible labor action at Lexington? Not confirmed.
- Read as: `noise` (reader: rules)
- Stats: {"writes": 0, "calls": 0}
- FAIL: expected an escalate, none made

### H2-032 — supplier_delay — FAIL
> Update on SH-0140 (harness A): no longer the 29th, expect Thu 1 April. Destination the Jackson plant. Shipper SUP-16.
- Read as: `noise` (reader: rules)
- Stats: {"writes": 0, "calls": 0, "moved": 0, "rescheduled": 0, "transferred": 0, "expected_moves": 6, "dealers": 0, "loaners": 0, "lots": [], "stop_sale_vins": 0, "owners": 0}
- FAIL: incident kinds ['none'] expected ['supplier_delay']
- FAIL: 6 affected PO(s) not moved: ['PO-0256', 'PO-0257', 'PO-0259', 'PO-0260', 'PO-0262']
- FAIL: dealer set: extra [], missing ['D02', 'D03', 'D04', 'D05', 'D06']
- FAIL: loaners: extra [], missing ['CO-01488', 'CO-01489', 'CO-01490', 'CO-01491', 'CO-01492']
- warn: only 0 kind(s) of write action (handbook rule 9 wants 3)

### H2-033 — quality_hold — FAIL
> Field reports of excess solder traced to airbag modules from Sterling Safety at the Kentucky plant; affected build window 4 Mar to the 5th.
- Read as: `noise` (reader: rules)
- Stats: {"writes": 0, "calls": 0, "moved": 0, "rescheduled": 0, "transferred": 0, "expected_moves": 0, "dealers": 0, "loaners": 0, "lots": [], "stop_sale_vins": 0, "owners": 0}
- FAIL: incident kinds ['none'] expected ['quality_hold']
- FAIL: lots held [] expected ['LOT-0052']
- FAIL: stop-sale VINs: got 0 expected 79 (extra [], missing ['AUR0001603', 'AUR0001606', 'AUR0001607'])
- FAIL: owners notified: got 0 expected 97 (extra [], missing ['C0058', 'C0122', 'C0149'])
- warn: only 0 kind(s) of write action (handbook rule 9 wants 3)

### H2-034 — noise — PASS
> Fire drill at the Princeton office building Thursday at 10 am. Plan to be outside for 15 minutes.
- Read as: `noise` (reader: rules)
- Stats: {"writes": 0, "calls": 0}

### H2-035 — plant_outage — PASS
> P_MS is idle 2027-03-11 to Fri 12 March due to an ammonia leak.
- Read as: `plant_outage` (reader: rules)
- Stats: {"writes": 42, "calls": 42, "moved": 6, "rescheduled": 6, "transferred": 0, "expected_moves": 6, "dealers": 29, "loaners": 7, "lots": [], "stop_sale_vins": 0, "owners": 0}

### H2-036 — plant_outage — PASS
> Lexington production halted from 30 Mar after a conveyor motor burnout; restart planned Thu 1 April.
- Read as: `plant_outage` (reader: rules)
- Stats: {"writes": 45, "calls": 45, "moved": 6, "rescheduled": 4, "transferred": 2, "expected_moves": 6, "dealers": 26, "loaners": 13, "lots": [], "stop_sale_vins": 0, "owners": 0}

### H2-037 — supplier_delay — PASS
> Inbound BRAKE-KIT (SUP-17) to P_IN: original delivery next Monday; now arriving the 18th because of a raw-material shortage.
- Read as: `supplier_delay` (reader: rules)
- Stats: {"writes": 49, "calls": 49, "moved": 6, "rescheduled": 6, "transferred": 0, "expected_moves": 6, "dealers": 24, "loaners": 19, "lots": [], "stop_sale_vins": 0, "owners": 0}

### H2-038 — quality_hold — FAIL
> Field reports of a mislabeled part number traced to 60 kWh battery packs from Helix Power at Wacky Wheels Princeton; affected build window February 22nd to 2/24.
- Read as: `noise` (reader: rules)
- Stats: {"writes": 0, "calls": 0, "moved": 0, "rescheduled": 0, "transferred": 0, "expected_moves": 0, "dealers": 0, "loaners": 0, "lots": [], "stop_sale_vins": 0, "owners": 0}
- FAIL: incident kinds ['none'] expected ['quality_hold']
- FAIL: lots held [] expected ['LOT-0173']
- FAIL: stop-sale VINs: got 0 expected 38 (extra [], missing ['AUR0002702', 'AUR0002706', 'AUR0002710'])
- FAIL: owners notified: got 0 expected 58 (extra [], missing ['C0045', 'C0261', 'C0798'])
- warn: only 0 kind(s) of write action (handbook rule 9 wants 3)

### H2-039 — compound — PASS
> Per Meridian Seating, leather seats for Wacky Wheels San Antonio got pushed out a few days: Monday the 22nd -> 24 Mar. Separately, meridian issued a defect notice for SEAT-FAB supplied to the Texas plant, production dates 4 Mar through 3/5: excess solder.
- Read as: `supplier_delay+quality_hold` (reader: rules, rules)
- Stats: {"writes": 113, "calls": 113, "moved": 2, "rescheduled": 2, "transferred": 0, "expected_moves": 2, "dealers": 13, "loaners": 3, "lots": ["LOT-0028"], "stop_sale_vins": 55, "owners": 65}

### H2-040 — quality_hold — FAIL
> QA hold: lot LOT-0063 (infotainment chips from Quanta) used at the Lexington plant, builds 3/2 to the 3rd. Issue: brittle plastic clips.
- Read as: `noise` (reader: rules)
- Stats: {"writes": 0, "calls": 0, "moved": 0, "rescheduled": 0, "transferred": 0, "expected_moves": 0, "dealers": 0, "loaners": 0, "lots": [], "stop_sale_vins": 0, "owners": 0}
- FAIL: incident kinds ['none'] expected ['quality_hold']
- FAIL: lots held [] expected ['LOT-0063']
- FAIL: stop-sale VINs: got 0 expected 85 (extra [], missing ['AUR0001425', 'AUR0001428', 'AUR0001430'])
- FAIL: owners notified: got 0 expected 97 (extra [], missing ['C0062', 'C0110', 'C0157'])
- warn: only 0 kind(s) of write action (handbook rule 9 wants 3)

### H2-041 — compound — FAIL
> Two notes: 1) Jackson is idle Wed 24 March to 29 Mar due to a transformer fire. 2) Heads up: we're losing P_AL for 10 Mar through 3/11 (a cyberattack on the line controllers).
- Read as: `plant_outage+noise` (reader: rules, rules)
- Stats: {"writes": 70, "calls": 70, "moved": 12, "rescheduled": 8, "transferred": 4, "expected_moves": 18, "dealers": 37, "loaners": 21, "lots": [], "stop_sale_vins": 0, "owners": 0}
- FAIL: incident kinds ['plant_outage'] expected ['plant_outage', 'plant_outage']
- FAIL: 6 affected PO(s) not moved: ['PO-0397', 'PO-0398', 'PO-0399', 'PO-0400', 'PO-0401']
- FAIL: dealer set: extra [], missing ['D04', 'D17', 'D19', 'D21']
- FAIL: dealer D02 order list: extra [], missing ['CO-02220']
- FAIL: dealer D03 order list: extra [], missing ['CO-02218', 'CO-02235', 'CO-02242']
- FAIL: dealer D06 order list: extra [], missing ['CO-02250', 'CO-02252']
- FAIL: dealer D07 order list: extra [], missing ['CO-02265']
- FAIL: dealer D08 order list: extra [], missing ['CO-02238']
- FAIL: dealer D10 order list: extra [], missing ['CO-02223', 'CO-02231']
- FAIL: dealer D12 order list: extra [], missing ['CO-02237']
- FAIL: dealer D18 order list: extra [], missing ['CO-02232']
- FAIL: dealer D20 order list: extra [], missing ['CO-02221']
- FAIL: dealer D22 order list: extra [], missing ['CO-02236', 'CO-02262']
- FAIL: dealer D24 order list: extra [], missing ['CO-02256']
- FAIL: dealer D25 order list: extra [], missing ['CO-02225', 'CO-02226', 'CO-02243']
- FAIL: dealer D26 order list: extra [], missing ['CO-02227', 'CO-02253', 'CO-02254']
- FAIL: dealer D27 order list: extra [], missing ['CO-02219', 'CO-02230']
- FAIL: dealer D31 order list: extra [], missing ['CO-02244', 'CO-02251']
- FAIL: dealer D32 order list: extra [], missing ['CO-02229']
- FAIL: dealer D35 order list: extra [], missing ['CO-02222', 'CO-02259']
- FAIL: dealer D43 order list: extra [], missing ['CO-02228']
- FAIL: dealer D44 order list: extra [], missing ['CO-02239', 'CO-02261']
- FAIL: dealer D45 order list: extra [], missing ['CO-02217', 'CO-02224', 'CO-02233']
- FAIL: dealer D46 order list: extra [], missing ['CO-02240']
- FAIL: dealer D47 order list: extra [], missing ['CO-02255']
- FAIL: loaners: extra ['CO-01488', 'CO-01496'], missing ['CO-02222', 'CO-02224', 'CO-02227', 'CO-02230', 'CO-02232']

### H2-042 — noise — PASS
> Fire drill at the Huntsville office building Thursday at 10 am. Plan to be outside for 15 minutes.
- Read as: `noise` (reader: rules)
- Stats: {"writes": 0, "calls": 0}

### H2-043 — plant_outage — PASS
> Emergency: a cyberattack on the line controllers at P_NC. Assembly paused 2027-03-17 through next Thursday.
- Read as: `plant_outage` (reader: rules)
- Stats: {"writes": 50, "calls": 50, "moved": 6, "rescheduled": 6, "transferred": 0, "expected_moves": 6, "dealers": 33, "loaners": 11, "lots": [], "stop_sale_vins": 0, "owners": 0}

### H2-044 — compound — FAIL
> Fire drill at the Princeton office building Thursday at 10 am. Plan to be outside for 15 minutes. Separately, the Indiana plant production halted from 10 Mar after a transformer fire; restart planned March 12th.
- Read as: `plant_outage` (reader: rules)
- Stats: {"writes": 0, "calls": 1, "moved": 0, "rescheduled": 0, "transferred": 0, "expected_moves": 6, "dealers": 0, "loaners": 0, "lots": [], "stop_sale_vins": 0, "owners": 0}
- FAIL: plant_outage fields: outage_start=2027-03-11 (expected 2027-03-10), outage_end=2027-03-10 (expected 2027-03-11)
- FAIL: escalated although the event is actionable / noise
- FAIL: 6 affected PO(s) not moved: ['PO-0307', 'PO-0308', 'PO-0309', 'PO-0310', 'PO-0311']
- FAIL: dealer set: extra [], missing ['D03', 'D06', 'D07', 'D08', 'D09']
- FAIL: loaners: extra [], missing ['CO-01677', 'CO-01680', 'CO-01685', 'CO-01691', 'CO-01692']
- warn: only 0 kind(s) of write action (handbook rule 9 wants 3)

### H2-045 — unconfirmed — PASS
> A driver mentioned possible delays at the border. Unverified.
- Read as: `unconfirmed` (reader: rules)
- Stats: {"writes": 0, "calls": 1}

### H2-046 — unconfirmed — FAIL
> Possible labor action at Wacky Wheels Lexington? Not confirmed.
- Read as: `noise` (reader: rules)
- Stats: {"writes": 0, "calls": 0}
- FAIL: expected an escalate, none made

### H2-047 — supplier_delay — FAIL
> Princeton receiving: the 20-inch rims truck from SUP-03 won't show Monday the 15th. Carrier now quoting next Tue.
- Read as: `noise` (reader: rules)
- Stats: {"writes": 0, "calls": 0, "moved": 0, "rescheduled": 0, "transferred": 0, "expected_moves": 1, "dealers": 0, "loaners": 0, "lots": [], "stop_sale_vins": 0, "owners": 0}
- FAIL: incident kinds ['none'] expected ['supplier_delay']
- FAIL: 1 affected PO(s) not moved: ['PO-0317']
- FAIL: dealer set: extra [], missing ['D06', 'D23', 'D24', 'D26', 'D29']
- FAIL: loaners: extra [], missing ['CO-01763']
- warn: only 0 kind(s) of write action (handbook rule 9 wants 3)

### H2-048 — plant_outage — PASS
> the Hunsville plant production halted from Tuesday the 30th after ice damage to the roof; restart planned 2 Apr.
- Read as: `plant_outage` (reader: rules)
- Stats: {"writes": 59, "calls": 59, "moved": 9, "rescheduled": 2, "transferred": 7, "expected_moves": 9, "dealers": 33, "loaners": 17, "lots": [], "stop_sale_vins": 0, "owners": 0}

### H2-049 — supplier_delay — FAIL
> Heads-up: Meridian Seating says the SEAT-VAN bound for P_AL slid from March 29th to 4/1.
- Read as: `noise` (reader: rules)
- Stats: {"writes": 0, "calls": 0, "moved": 0, "rescheduled": 0, "transferred": 0, "expected_moves": 3, "dealers": 0, "loaners": 0, "lots": [], "stop_sale_vins": 0, "owners": 0}
- FAIL: incident kinds ['none'] expected ['supplier_delay']
- FAIL: 3 affected PO(s) not moved: ['PO-0438', 'PO-0441', 'PO-0444']
- FAIL: dealer set: extra [], missing ['D04', 'D06', 'D08', 'D12', 'D16']
- FAIL: loaners: extra [], missing ['CO-02587', 'CO-02590', 'CO-02615', 'CO-02640', 'CO-02641']
- warn: only 0 kind(s) of write action (handbook rule 9 wants 3)

### H2-050 — plant_outage — PASS
> Wacky Wheels Princeton is idle Tuesday the 23rd to 3/29 due to an ammonia leak.
- Read as: `plant_outage` (reader: rules)
- Stats: {"writes": 78, "calls": 78, "moved": 15, "rescheduled": 8, "transferred": 7, "expected_moves": 15, "dealers": 38, "loaners": 25, "lots": [], "stop_sale_vins": 0, "owners": 0}

### H2-051 — noise — PASS
> Please welcome our new CFO, who starts on Monday.
- Read as: `noise` (reader: rules)
- Stats: {"writes": 0, "calls": 0}

### H2-052 — unconfirmed — PASS
> rumor: chip shortage coming, no idea when
- Read as: `unconfirmed` (reader: rules)
- Stats: {"writes": 0, "calls": 1}

### H2-053 — noise — PASS
> Lunch and learn on EV battery chemistry in the big conference room today.
- Read as: `noise` (reader: rules)
- Stats: {"writes": 0, "calls": 0}

### H2-054 — supplier_delay — FAIL
> Per Ironwood, 16-inch alloy wheels for Jackson got pushed out a few days: Mon 22 March -> Wednesday the 24th.
- Read as: `unconfirmed` (reader: rules)
- Stats: {"writes": 0, "calls": 1, "moved": 0, "rescheduled": 0, "transferred": 0, "expected_moves": 2, "dealers": 0, "loaners": 0, "lots": [], "stop_sale_vins": 0, "owners": 0}
- FAIL: incident kinds ['none'] expected ['supplier_delay']
- FAIL: escalated although the event is actionable / noise
- FAIL: 2 affected PO(s) not moved: ['PO-0243', 'PO-0246']
- FAIL: dealer set: extra [], missing ['D04', 'D08', 'D10', 'D12', 'D16']
- FAIL: loaners: extra [], missing ['CO-01374', 'CO-01402', 'CO-01405', 'CO-01407']
- warn: only 0 kind(s) of write action (handbook rule 9 wants 3)

### H2-055 — quality_hold — FAIL
> Please quarantine LOT-0275: brittle plastic clips in standard wiring harness. the Huntsville plant builds the 2nd through 3/3.
- Read as: `noise` (reader: rules)
- Stats: {"writes": 0, "calls": 0, "moved": 0, "rescheduled": 0, "transferred": 0, "expected_moves": 0, "dealers": 0, "loaners": 0, "lots": [], "stop_sale_vins": 0, "owners": 0}
- FAIL: incident kinds ['none'] expected ['quality_hold']
- FAIL: lots held [] expected ['LOT-0275']
- FAIL: stop-sale VINs: got 0 expected 22 (extra [], missing ['AUR0004117', 'AUR0004125', 'AUR0004130'])
- FAIL: owners notified: got 0 expected 41 (extra [], missing ['C0255', 'C0409', 'C0441'])
- warn: only 0 kind(s) of write action (handbook rule 9 wants 3)

### H2-056 — unconfirmed — FAIL
> Possible labor action at Huntsville? Not confirmed.
- Read as: `noise` (reader: rules)
- Stats: {"writes": 0, "calls": 0}
- FAIL: expected an escalate, none made

### H2-057 — quality_hold — FAIL
> Field reports of wrong thread pitch traced to 12-inch displays from Orbit Optics at the Greensbro plant; affected build window the 4th to Friday the 5th.
- Read as: `noise` (reader: rules)
- Stats: {"writes": 0, "calls": 0, "moved": 0, "rescheduled": 0, "transferred": 0, "expected_moves": 0, "dealers": 0, "loaners": 0, "lots": [], "stop_sale_vins": 0, "owners": 0}
- FAIL: incident kinds ['none'] expected ['quality_hold']
- FAIL: lots held [] expected ['LOT-0324']
- FAIL: stop-sale VINs: got 0 expected 36 (extra [], missing ['AUR0005166', 'AUR0005167', 'AUR0005168'])
- FAIL: owners notified: got 0 expected 31 (extra [], missing ['C0016', 'C0081', 'C0085'])
- warn: only 0 kind(s) of write action (handbook rule 9 wants 3)

### H2-058 — compound — FAIL
> Shift report. (1) Per Atlas, standard wiring harness for Lexington got pushed out a few days: 3/29 -> March 30th. (2) Field reports of excess solder traced to 17-inch all-season tires from Granite at Jackson; affected build window 2027-02-25 to 3/1.
- Read as: `supplier_delay+noise` (reader: rules, rules)
- Stats: {"writes": 10, "calls": 10, "moved": 1, "rescheduled": 1, "transferred": 0, "expected_moves": 1, "dealers": 8, "loaners": 1, "lots": [], "stop_sale_vins": 0, "owners": 0}
- FAIL: incident kinds ['supplier_delay'] expected ['quality_hold', 'supplier_delay']
- FAIL: lots held [] expected ['LOT-0158']
- FAIL: stop-sale VINs: got 0 expected 74 (extra [], missing ['AUR0002037', 'AUR0002038', 'AUR0002041'])
- FAIL: owners notified: got 0 expected 90 (extra [], missing ['C0038', 'C0088', 'C0089'])

### H2-059 — quality_hold — PASS
> Quanta Silicon issued a defect notice for driver-assist chips supplied to the Jackson plant, production dates March 4th through 3/5: intermittent shorts.
- Read as: `quality_hold` (reader: rules)
- Stats: {"writes": 57, "calls": 57, "moved": 0, "rescheduled": 0, "transferred": 0, "expected_moves": 0, "dealers": 0, "loaners": 0, "lots": ["LOT-0128"], "stop_sale_vins": 25, "owners": 38}

### H2-060 — plant_outage — FAIL
> Heads up: we're losing the Grensboro plant for 3/18 through 23 Mar (a boiler failure).
- Read as: `noise` (reader: rules)
- Stats: {"writes": 0, "calls": 0, "moved": 0, "rescheduled": 0, "transferred": 0, "expected_moves": 12, "dealers": 0, "loaners": 0, "lots": [], "stop_sale_vins": 0, "owners": 0}
- FAIL: incident kinds ['none'] expected ['plant_outage']
- FAIL: 12 affected PO(s) not moved: ['PO-0505', 'PO-0506', 'PO-0507', 'PO-0508', 'PO-0509']
- FAIL: dealer set: extra [], missing ['D01', 'D02', 'D03', 'D04', 'D05']
- FAIL: loaners: extra [], missing ['CO-02933', 'CO-02940', 'CO-02942', 'CO-02945', 'CO-02948']
- warn: only 0 kind(s) of write action (handbook rule 9 wants 3)

### H2-061 — plant_outage — FAIL
> Heads up: we're losing the North Carolina plant for 2027-03-11 through Fri 12 March (a boiler failure).
- Read as: `noise` (reader: rules)
- Stats: {"writes": 0, "calls": 0, "moved": 0, "rescheduled": 0, "transferred": 0, "expected_moves": 6, "dealers": 0, "loaners": 0, "lots": [], "stop_sale_vins": 0, "owners": 0}
- FAIL: incident kinds ['none'] expected ['plant_outage']
- FAIL: 6 affected PO(s) not moved: ['PO-0490', 'PO-0491', 'PO-0492', 'PO-0493', 'PO-0494']
- FAIL: dealer set: extra [], missing ['D02', 'D03', 'D04', 'D07', 'D08']
- FAIL: loaners: extra [], missing ['CO-02795', 'CO-02797', 'CO-02801', 'CO-02803', 'CO-02809']
- warn: only 0 kind(s) of write action (handbook rule 9 wants 3)

### H2-062 — plant_outage — PASS
> Huntsville is idle 3/11 to 12 Mar due to a conveyor motor burnout.
- Read as: `plant_outage` (reader: rules)
- Stats: {"writes": 46, "calls": 46, "moved": 6, "rescheduled": 6, "transferred": 0, "expected_moves": 6, "dealers": 28, "loaners": 12, "lots": [], "stop_sale_vins": 0, "owners": 0}

### H2-063 — compound — FAIL
> Lunch and learn on EV battery chemistry in the big conference room today. Separately, heads up: we're losing Jackson for 2027-03-22 through Tuesday the 23rd (a boiler failure).
- Read as: `noise` (reader: rules)
- Stats: {"writes": 0, "calls": 0, "moved": 0, "rescheduled": 0, "transferred": 0, "expected_moves": 6, "dealers": 0, "loaners": 0, "lots": [], "stop_sale_vins": 0, "owners": 0}
- FAIL: incident kinds ['none'] expected ['plant_outage']
- FAIL: 6 affected PO(s) not moved: ['PO-0241', 'PO-0242', 'PO-0243', 'PO-0244', 'PO-0245']
- FAIL: dealer set: extra [], missing ['D02', 'D03', 'D04', 'D06', 'D08']
- FAIL: loaners: extra [], missing ['CO-01357', 'CO-01361', 'CO-01366', 'CO-01369', 'CO-01371']
- warn: only 0 kind(s) of write action (handbook rule 9 wants 3)

### H2-064 — noise — PASS
> The holiday schedule for next year has been posted.
- Read as: `noise` (reader: rules)
- Stats: {"writes": 0, "calls": 0}

### H2-065 — unconfirmed — FAIL
> Possible labor action at the North Carolina plant? Not confirmed.
- Read as: `noise` (reader: rules)
- Stats: {"writes": 0, "calls": 0}
- FAIL: expected an escalate, none made

### H2-066 — plant_outage — PASS
> Huntsville is idle on Monday the 29th because of an ammonia leak.
- Read as: `plant_outage` (reader: rules)
- Stats: {"writes": 25, "calls": 25, "moved": 3, "rescheduled": 3, "transferred": 0, "expected_moves": 3, "dealers": 16, "loaners": 6, "lots": [], "stop_sale_vins": 0, "owners": 0}

### H2-067 — supplier_delay — PASS
> Inbound compact wiring harness (Ridgeline) to the North Carolina plant: original delivery March 29th; now arriving 2 Apr because of a missed vessel.
- Read as: `supplier_delay` (reader: rules)
- Stats: {"writes": 32, "calls": 32, "moved": 4, "rescheduled": 2, "transferred": 2, "expected_moves": 4, "dealers": 22, "loaners": 6, "lots": [], "stop_sale_vins": 0, "owners": 0}

### H2-068 — unconfirmed — PASS
> Gossip says Granite Tire is in financial trouble; could affect supply. Nothing confirmed.
- Read as: `unconfirmed` (reader: rules)
- Stats: {"writes": 0, "calls": 1}

### H2-069 — compound — FAIL
> Two notes: 1) P_NC receiving: the harness B truck from Volt won't show 29 Mar. Carrier now quoting Tue 30 March. 2) Heavy rain expected in Seattle, WA through Wednesday.
- Read as: `noise+noise` (reader: rules, rules)
- Stats: {"writes": 0, "calls": 0, "moved": 0, "rescheduled": 0, "transferred": 0, "expected_moves": 1, "dealers": 0, "loaners": 0, "lots": [], "stop_sale_vins": 0, "owners": 0}
- FAIL: incident kinds ['none'] expected ['supplier_delay']
- FAIL: 1 affected PO(s) not moved: ['PO-0528']
- FAIL: dealer set: extra [], missing ['D03', 'D05', 'D06', 'D09', 'D12']
- FAIL: loaners: extra [], missing ['CO-03146', 'CO-03151']
- warn: only 0 kind(s) of write action (handbook rule 9 wants 3)

### H2-070 — supplier_delay — PASS
> Inbound airbag modules (Sterling) to the Kentucky plant: original delivery March 29th; now arriving 2027-03-31 because of a derailment.
- Read as: `supplier_delay` (reader: rules)
- Stats: {"writes": 42, "calls": 42, "moved": 6, "rescheduled": 6, "transferred": 0, "expected_moves": 6, "dealers": 26, "loaners": 10, "lots": [], "stop_sale_vins": 0, "owners": 0}

### H2-071 — quality_hold — PASS
> Meridian Seating issued a defect notice for leather seat set supplied to Lexington, production dates 2027-02-25 through March 1st: wrong thread pitch.
- Read as: `quality_hold` (reader: rules)
- Stats: {"writes": 73, "calls": 73, "moved": 0, "rescheduled": 0, "transferred": 0, "expected_moves": 0, "dealers": 0, "loaners": 0, "lots": ["LOT-0090"], "stop_sale_vins": 32, "owners": 52}

### H2-072 — plant_outage — FAIL
> Heads up: we're losing Huntsville for Wed 10 March through Thursday the 11th (a boiler failure).
- Read as: `noise` (reader: rules)
- Stats: {"writes": 0, "calls": 0, "moved": 0, "rescheduled": 0, "transferred": 0, "expected_moves": 6, "dealers": 0, "loaners": 0, "lots": [], "stop_sale_vins": 0, "owners": 0}
- FAIL: incident kinds ['none'] expected ['plant_outage']
- FAIL: 6 affected PO(s) not moved: ['PO-0397', 'PO-0398', 'PO-0399', 'PO-0400', 'PO-0401']
- FAIL: dealer set: extra [], missing ['D02', 'D03', 'D04', 'D06', 'D07']
- FAIL: loaners: extra [], missing ['CO-02222', 'CO-02224', 'CO-02227', 'CO-02230', 'CO-02232']
- warn: only 0 kind(s) of write action (handbook rule 9 wants 3)

### H2-073 — noise — PASS
> Town hall slides are posted on the intranet.
- Read as: `noise` (reader: rules)
- Stats: {"writes": 0, "calls": 0}

### H2-074 — plant_outage — PASS
> the San Antonio plant is idle 3/23 to the 24th due to ice damage to the roof.
- Read as: `plant_outage` (reader: rules)
- Stats: {"writes": 53, "calls": 53, "moved": 6, "rescheduled": 6, "transferred": 0, "expected_moves": 6, "dealers": 29, "loaners": 18, "lots": [], "stop_sale_vins": 0, "owners": 0}

### H2-075 — supplier_delay — FAIL
> San Antonio receiving: the infotainment chips truck from SUP-06 won't show Mon 15 March. Carrier now quoting next Tue.
- Read as: `noise` (reader: rules)
- Stats: {"writes": 0, "calls": 0, "moved": 0, "rescheduled": 0, "transferred": 0, "expected_moves": 2, "dealers": 0, "loaners": 0, "lots": [], "stop_sale_vins": 0, "owners": 0}
- FAIL: incident kinds ['none'] expected ['supplier_delay']
- FAIL: 2 affected PO(s) not moved: ['PO-0047', 'PO-0048']
- FAIL: dealer set: extra [], missing ['D02', 'D07', 'D08', 'D13', 'D16']
- FAIL: loaners: extra [], missing ['CO-00152', 'CO-00153', 'CO-00154', 'CO-00155', 'CO-00156']
- warn: only 0 kind(s) of write action (handbook rule 9 wants 3)

### H2-076 — unconfirmed — PASS
> Hearing Princeton might go down for maintenance soon, no dates.
- Read as: `unconfirmed` (reader: rules)
- Stats: {"writes": 0, "calls": 1}

### H2-077 — quality_hold — FAIL
> Please quarantine LOT-0077: intermittent shorts in HARN-B. Lexington builds 22 Feb through 2027-02-24.
- Read as: `noise` (reader: rules)
- Stats: {"writes": 0, "calls": 0, "moved": 0, "rescheduled": 0, "transferred": 0, "expected_moves": 0, "dealers": 0, "loaners": 0, "lots": [], "stop_sale_vins": 0, "owners": 0}
- FAIL: incident kinds ['none'] expected ['quality_hold']
- FAIL: lots held [] expected ['LOT-0077']
- FAIL: stop-sale VINs: got 0 expected 46 (extra [], missing ['AUR0000934', 'AUR0000936', 'AUR0000937'])
- FAIL: owners notified: got 0 expected 45 (extra [], missing ['C0188', 'C0369', 'C0435'])
- warn: only 0 kind(s) of write action (handbook rule 9 wants 3)

### H2-078 — compound — FAIL
> First, the Lexington plant is idle the 23rd to Mon 29 March due to a conveyor motor burnout. Second, emergency: a conveyor motor burnout at Wacky Wheels San Antonio. Assembly paused Thursday the 25th through 2027-03-29.
- Read as: `plant_outage` (reader: rules)
- Stats: {"writes": 83, "calls": 83, "moved": 15, "rescheduled": 8, "transferred": 7, "expected_moves": 24, "dealers": 39, "loaners": 29, "lots": [], "stop_sale_vins": 0, "owners": 0}
- FAIL: incident kinds ['plant_outage'] expected ['plant_outage', 'plant_outage']
- FAIL: 9 affected PO(s) not moved: ['PO-0070', 'PO-0071', 'PO-0072', 'PO-0073', 'PO-0074']
- FAIL: dealer set: extra [], missing ['D09', 'D47']
- FAIL: dealer D02 order list: extra [], missing ['CO-00412']
- FAIL: dealer D03 order list: extra [], missing ['CO-00375', 'CO-00397', 'CO-00423']
- FAIL: dealer D04 order list: extra [], missing ['CO-00398', 'CO-00402']
- FAIL: dealer D06 order list: extra [], missing ['CO-00388', 'CO-00404', 'CO-00405']
- FAIL: dealer D07 order list: extra [], missing ['CO-00395', 'CO-00413', 'CO-00417']
- FAIL: dealer D08 order list: extra [], missing ['CO-00408', 'CO-00420', 'CO-00430']
- FAIL: dealer D10 order list: extra [], missing ['CO-00369', 'CO-00393']
- FAIL: dealer D12 order list: extra [], missing ['CO-00411', 'CO-00415']
- FAIL: dealer D16 order list: extra [], missing ['CO-00443']
- FAIL: dealer D17 order list: extra [], missing ['CO-00427']
- FAIL: dealer D20 order list: extra [], missing ['CO-00380', 'CO-00386']
- FAIL: dealer D21 order list: extra [], missing ['CO-00362', 'CO-00378', 'CO-00391']
- FAIL: dealer D23 order list: extra [], missing ['CO-00365', 'CO-00383', 'CO-00384']
- FAIL: dealer D24 order list: extra [], missing ['CO-00410', 'CO-00422']
- FAIL: dealer D25 order list: extra [], missing ['CO-00357', 'CO-00371', 'CO-00372']
- FAIL: dealer D26 order list: extra [], missing ['CO-00359', 'CO-00360', 'CO-00366']
- FAIL: dealer D27 order list: extra [], missing ['CO-00364', 'CO-00379', 'CO-00382']
- FAIL: dealer D28 order list: extra [], missing ['CO-00426']
- FAIL: dealer D29 order list: extra [], missing ['CO-00436']
- FAIL: dealer D31 order list: extra [], missing ['CO-00437']
- FAIL: dealer D32 order list: extra [], missing ['CO-00368', 'CO-00421', 'CO-00434']
- FAIL: dealer D34 order list: extra [], missing ['CO-00390', 'CO-00414']
- FAIL: dealer D35 order list: extra [], missing ['CO-00406']
- FAIL: dealer D38 order list: extra [], missing ['CO-00361']
- FAIL: dealer D43 order list: extra [], missing ['CO-00394']
- FAIL: dealer D44 order list: extra [], missing ['CO-00358', 'CO-00376', 'CO-00431']
- FAIL: dealer D45 order list: extra [], missing ['CO-00367', 'CO-00403', 'CO-00409']
- FAIL: dealer D46 order list: extra [], missing ['CO-00363', 'CO-00389', 'CO-00407']
- FAIL: loaners: extra ['CO-00858', 'CO-00935', 'CO-00942', 'CO-00956', 'CO-00968'], missing ['CO-00357', 'CO-00364', 'CO-00369', 'CO-00375', 'CO-00383']

### H2-079 — supplier_delay — PASS
> Per SUP-05, HARN-C for P_TX got pushed out a few days: 3/22 -> March 23rd.
- Read as: `supplier_delay` (reader: rules)
- Stats: {"writes": 9, "calls": 9, "moved": 1, "rescheduled": 1, "transferred": 0, "expected_moves": 1, "dealers": 7, "loaners": 1, "lots": [], "stop_sale_vins": 0, "owners": 0}

### H2-080 — noise — PASS
> Dealer Nashville asks for the updated accessory price sheets.
- Read as: `noise` (reader: rules)
- Stats: {"writes": 0, "calls": 0}

### H2-081 — compound — FAIL
> First, kestrel Electronics issued a defect notice for infotainment chip supplied to Jackson, production dates 2027-02-22 through 2/24: a mislabeled part number. Second, a driver mentioned possible delays at the border. Unverified.
- Read as: `quality_hold` (reader: rules)
- Stats: {"writes": 183, "calls": 183, "moved": 0, "rescheduled": 0, "transferred": 0, "expected_moves": 0, "dealers": 0, "loaners": 0, "lots": ["LOT-0129"], "stop_sale_vins": 116, "owners": 142}
- FAIL: expected an escalate, none made

### H2-082 — compound — FAIL
> Two notes: 1) Per Atlas, HARN-A for P_AL got pushed out a few days: 3/29 -> April 2nd. 2) Field reports of excess solder traced to minivan seats from Harbor at the Princeon plant; affected build window 25 Feb to Monday the 1st.
- Read as: `supplier_delay+noise` (reader: rules, rules)
- Stats: {"writes": 36, "calls": 36, "moved": 4, "rescheduled": 2, "transferred": 2, "expected_moves": 4, "dealers": 23, "loaners": 9, "lots": [], "stop_sale_vins": 0, "owners": 0}
- FAIL: incident kinds ['supplier_delay'] expected ['quality_hold', 'supplier_delay']
- FAIL: lots held [] expected ['LOT-0222']
- FAIL: stop-sale VINs: got 0 expected 37 (extra [], missing ['AUR0002911', 'AUR0002912', 'AUR0002913'])
- FAIL: owners notified: got 0 expected 53 (extra [], missing ['C0166', 'C0372', 'C0452'])

### H2-083 — supplier_delay — FAIL
> Wacky Wheels Jackson receiving: the airbag modules truck from Sentinel Brake and Airbag won't show next Mon. Carrier now quoting 2027-03-19.
- Read as: `noise` (reader: rules)
- Stats: {"writes": 0, "calls": 0, "moved": 0, "rescheduled": 0, "transferred": 0, "expected_moves": 12, "dealers": 0, "loaners": 0, "lots": [], "stop_sale_vins": 0, "owners": 0}
- FAIL: incident kinds ['none'] expected ['supplier_delay']
- FAIL: 12 affected PO(s) not moved: ['PO-0226', 'PO-0227', 'PO-0228', 'PO-0229', 'PO-0230']
- FAIL: dealer set: extra [], missing ['D02', 'D03', 'D04', 'D05', 'D06']
- FAIL: loaners: extra [], missing ['CO-01222', 'CO-01223', 'CO-01242', 'CO-01249', 'CO-01250']
- warn: only 0 kind(s) of write action (handbook rule 9 wants 3)

### H2-084 — compound — FAIL
> Two notes: 1) Heads up: we're losing Princeton for 16 Mar through Thursday the 18th (a conveyor motor burnout). 2) Per Quanta, infotainment chip for Wacky Wheels Lexington got pushed out a few days: 3/29 -> Tue 30 March.
- Read as: `noise+supplier_delay` (reader: rules, rules)
- Stats: {"writes": 25, "calls": 25, "moved": 3, "rescheduled": 3, "transferred": 0, "expected_moves": 12, "dealers": 18, "loaners": 4, "lots": [], "stop_sale_vins": 0, "owners": 0}
- FAIL: incident kinds ['supplier_delay'] expected ['plant_outage', 'supplier_delay']
- FAIL: 9 affected PO(s) not moved: ['PO-0319', 'PO-0320', 'PO-0321', 'PO-0322', 'PO-0323']
- FAIL: dealer set: extra [], missing ['D01', 'D03', 'D06', 'D07', 'D08']
- FAIL: dealer D02 order list: extra [], missing ['CO-01803', 'CO-01811', 'CO-01832']
- FAIL: dealer D04 order list: extra [], missing ['CO-01854']
- FAIL: dealer D15 order list: extra [], missing ['CO-01837', 'CO-01844']
- FAIL: dealer D20 order list: extra [], missing ['CO-01786', 'CO-01791', 'CO-01793']
- FAIL: dealer D23 order list: extra [], missing ['CO-01797', 'CO-01834', 'CO-01853']
- FAIL: dealer D25 order list: extra [], missing ['CO-01782', 'CO-01789', 'CO-01790']
- FAIL: dealer D26 order list: extra [], missing ['CO-01819', 'CO-01826', 'CO-01842']
- FAIL: dealer D27 order list: extra [], missing ['CO-01831']
- FAIL: dealer D29 order list: extra [], missing ['CO-01846', 'CO-01848']
- FAIL: dealer D31 order list: extra [], missing ['CO-01784', 'CO-01807', 'CO-01821']
- FAIL: dealer D32 order list: extra [], missing ['CO-01802', 'CO-01817']
- FAIL: dealer D38 order list: extra [], missing ['CO-01815', 'CO-01816', 'CO-01829']
- FAIL: dealer D43 order list: extra [], missing ['CO-01851']
- FAIL: dealer D44 order list: extra [], missing ['CO-01785', 'CO-01787', 'CO-01809']
- FAIL: dealer D45 order list: extra [], missing ['CO-01788', 'CO-01804', 'CO-01810']
- FAIL: loaners: extra ['CO-00968'], missing ['CO-01780', 'CO-01781', 'CO-01783', 'CO-01785', 'CO-01786']

### H2-085 — noise — PASS
> Reminder: submit March expense reports through the finance portal.
- Read as: `noise` (reader: rules)
- Stats: {"writes": 0, "calls": 0}

### H2-086 — supplier_delay — FAIL
> Update on SH-0211 (HARN-C): no longer the 22nd, expect the 25th. Destination the Indiana plant. Shipper Ridgeline Wire.
- Read as: `noise` (reader: rules)
- Stats: {"writes": 0, "calls": 0, "moved": 0, "rescheduled": 0, "transferred": 0, "expected_moves": 3, "dealers": 0, "loaners": 0, "lots": [], "stop_sale_vins": 0, "owners": 0}
- FAIL: incident kinds ['none'] expected ['supplier_delay']
- FAIL: 3 affected PO(s) not moved: ['PO-0331', 'PO-0334', 'PO-0337']
- FAIL: dealer set: extra [], missing ['D01', 'D02', 'D03', 'D06', 'D07']
- FAIL: loaners: extra [], missing ['CO-01893', 'CO-01894', 'CO-01915', 'CO-01939', 'CO-01940']
- warn: only 0 kind(s) of write action (handbook rule 9 wants 3)

### H2-087 — supplier_delay — FAIL
> Inbound infotainment chips (Kestrel) to the Texas plant: original delivery March 15th; now arriving March 19th because of a strike at their warehouse.
- Read as: `unconfirmed` (reader: rules)
- Stats: {"writes": 0, "calls": 1, "moved": 0, "rescheduled": 0, "transferred": 0, "expected_moves": 8, "dealers": 0, "loaners": 0, "lots": [], "stop_sale_vins": 0, "owners": 0}
- FAIL: incident kinds ['none'] expected ['supplier_delay']
- FAIL: escalated although the event is actionable / noise
- FAIL: 8 affected PO(s) not moved: ['PO-0047', 'PO-0048', 'PO-0050', 'PO-0051', 'PO-0053']
- FAIL: dealer set: extra [], missing ['D02', 'D03', 'D04', 'D06', 'D07']
- FAIL: loaners: extra [], missing ['CO-00152', 'CO-00153', 'CO-00154', 'CO-00155', 'CO-00161']
- warn: only 0 kind(s) of write action (handbook rule 9 wants 3)

### H2-088 — noise — PASS
> Dealer Montgomery asks for the updated accessory price sheets.
- Read as: `noise` (reader: rules)
- Stats: {"writes": 0, "calls": 0}

### H2-089 — compound — FAIL
> Reminder: submit March expense reports through the finance portal. Also, heads up: we're losing the Lexington plant for 3/29 through Thu 1 April (a cyberattack on the line controllers).
- Read as: `noise` (reader: rules)
- Stats: {"writes": 0, "calls": 0, "moved": 0, "rescheduled": 0, "transferred": 0, "expected_moves": 12, "dealers": 0, "loaners": 0, "lots": [], "stop_sale_vins": 0, "owners": 0}
- FAIL: incident kinds ['none'] expected ['plant_outage']
- FAIL: 12 affected PO(s) not moved: ['PO-0166', 'PO-0167', 'PO-0168', 'PO-0169', 'PO-0170']
- FAIL: dealer set: extra [], missing ['D02', 'D03', 'D04', 'D06', 'D07']
- FAIL: loaners: extra [], missing ['CO-00968', 'CO-00970', 'CO-00973', 'CO-00978', 'CO-00992']
- warn: only 0 kind(s) of write action (handbook rule 9 wants 3)

### H2-090 — noise — PASS
> Heavy rain expected in Seattle, WA through Wednesday.
- Read as: `noise` (reader: rules)
- Stats: {"writes": 0, "calls": 0}

### H2-091 — noise — PASS
> Dealer Asheville asks for the updated accessory price sheets.
- Read as: `noise` (reader: rules)
- Stats: {"writes": 0, "calls": 0}

### H2-092 — plant_outage — PASS
> Wacky Wheels Jackson is idle on Tuesday the 30th because of a transformer fire.
- Read as: `plant_outage` (reader: rules)
- Stats: {"writes": 27, "calls": 27, "moved": 3, "rescheduled": 3, "transferred": 0, "expected_moves": 3, "dealers": 19, "loaners": 5, "lots": [], "stop_sale_vins": 0, "owners": 0}

### H2-093 — plant_outage — PASS
> the Princeon plant is idle on Tue 30 March because of a conveyor motor burnout.
- Read as: `plant_outage` (reader: rules)
- Stats: {"writes": 31, "calls": 31, "moved": 3, "rescheduled": 3, "transferred": 0, "expected_moves": 3, "dealers": 21, "loaners": 7, "lots": [], "stop_sale_vins": 0, "owners": 0}

### H2-094 — plant_outage — PASS
> the Alabama plant: no builds 3/17 (a cyberattack on the line controllers), resuming the next working day.
- Read as: `plant_outage` (reader: rules)
- Stats: {"writes": 27, "calls": 27, "moved": 3, "rescheduled": 3, "transferred": 0, "expected_moves": 3, "dealers": 18, "loaners": 6, "lots": [], "stop_sale_vins": 0, "owners": 0}

### H2-095 — quality_hold — FAIL
> QA hold: lot LOT-0176 (60 kWh battery packs from SUP-09) used at the Indiana plant, builds Thursday the 4th to March 5th. Issue: brittle plastic clips.
- Read as: `noise` (reader: rules)
- Stats: {"writes": 0, "calls": 0, "moved": 0, "rescheduled": 0, "transferred": 0, "expected_moves": 0, "dealers": 0, "loaners": 0, "lots": [], "stop_sale_vins": 0, "owners": 0}
- FAIL: incident kinds ['none'] expected ['quality_hold']
- FAIL: lots held [] expected ['LOT-0176']
- FAIL: stop-sale VINs: got 0 expected 23 (extra [], missing ['AUR0003415', 'AUR0003416', 'AUR0003420'])
- FAIL: owners notified: got 0 expected 40 (extra [], missing ['C0035', 'C0152', 'C0262'])
- warn: only 0 kind(s) of write action (handbook rule 9 wants 3)

### H2-096 — quality_hold — FAIL
> Please quarantine LOT-0075: seal leaks in HARN-A. the Kentucky plant builds March 2nd through 3/3.
- Read as: `noise` (reader: rules)
- Stats: {"writes": 0, "calls": 0, "moved": 0, "rescheduled": 0, "transferred": 0, "expected_moves": 0, "dealers": 0, "loaners": 0, "lots": [], "stop_sale_vins": 0, "owners": 0}
- FAIL: incident kinds ['none'] expected ['quality_hold']
- FAIL: lots held [] expected ['LOT-0075']
- FAIL: stop-sale VINs: got 0 expected 26 (extra [], missing ['AUR0001425', 'AUR0001428', 'AUR0001430'])
- FAIL: owners notified: got 0 expected 35 (extra [], missing ['C0110', 'C0157', 'C0663'])
- warn: only 0 kind(s) of write action (handbook rule 9 wants 3)

### H2-097 — unconfirmed — FAIL
> Unclear reports that a supplier may miss deliveries next month.
- Read as: `noise` (reader: rules)
- Stats: {"writes": 0, "calls": 0}
- FAIL: expected an escalate, none made

### H2-098 — supplier_delay — FAIL
> Per Kestrel, infotainment chips for P_AL got pushed out a few days: 22 Mar -> 26 Mar.
- Read as: `unconfirmed` (reader: rules)
- Stats: {"writes": 0, "calls": 1, "moved": 0, "rescheduled": 0, "transferred": 0, "expected_moves": 12, "dealers": 0, "loaners": 0, "lots": [], "stop_sale_vins": 0, "owners": 0}
- FAIL: incident kinds ['none'] expected ['supplier_delay']
- FAIL: escalated although the event is actionable / noise
- FAIL: 12 affected PO(s) not moved: ['PO-0421', 'PO-0422', 'PO-0423', 'PO-0424', 'PO-0425']
- FAIL: dealer set: extra [], missing ['D01', 'D02', 'D03', 'D05', 'D06']
- FAIL: loaners: extra [], missing ['CO-02435', 'CO-02441', 'CO-02452', 'CO-02463', 'CO-02466']
- warn: only 0 kind(s) of write action (handbook rule 9 wants 3)

### H2-099 — supplier_delay — FAIL
> Wacky Wheels Jackson receiving: the HARN-A truck from Ridgeline won't show Monday the 22nd. Carrier now quoting 26 Mar.
- Read as: `noise` (reader: rules)
- Stats: {"writes": 0, "calls": 0, "moved": 0, "rescheduled": 0, "transferred": 0, "expected_moves": 8, "dealers": 0, "loaners": 0, "lots": [], "stop_sale_vins": 0, "owners": 0}
- FAIL: incident kinds ['none'] expected ['supplier_delay']
- FAIL: 8 affected PO(s) not moved: ['PO-0241', 'PO-0242', 'PO-0244', 'PO-0245', 'PO-0247']
- FAIL: dealer set: extra [], missing ['D02', 'D03', 'D04', 'D05', 'D06']
- FAIL: loaners: extra [], missing ['CO-01357', 'CO-01361', 'CO-01366', 'CO-01369', 'CO-01371']
- warn: only 0 kind(s) of write action (handbook rule 9 wants 3)

### H2-100 — quality_hold — FAIL
> Please quarantine LOT-0245: excess solder in BATT-60. P_AL builds Mon 22 February through 24 Feb.
- Read as: `noise` (reader: rules)
- Stats: {"writes": 0, "calls": 0, "moved": 0, "rescheduled": 0, "transferred": 0, "expected_moves": 0, "dealers": 0, "loaners": 0, "lots": [], "stop_sale_vins": 0, "owners": 0}
- FAIL: incident kinds ['none'] expected ['quality_hold']
- FAIL: lots held [] expected ['LOT-0245']
- FAIL: stop-sale VINs: got 0 expected 39 (extra [], missing ['AUR0003575', 'AUR0003578', 'AUR0003580'])
- FAIL: owners notified: got 0 expected 53 (extra [], missing ['C0051', 'C0097', 'C0358'])
- warn: only 0 kind(s) of write action (handbook rule 9 wants 3)

## Details — qwen3:0.6b reader

### H2-001 — plant_outage — PASS
> Emergency: a boiler failure at Wacky Wheels Lexington. Assembly paused March 26th through March 30th.
- Read as: `plant_outage` (reader: qwen3:0.6b)
- Stats: {"writes": 54, "calls": 54, "moved": 9, "rescheduled": 6, "transferred": 3, "expected_moves": 9, "dealers": 29, "loaners": 16, "lots": [], "stop_sale_vins": 0, "owners": 0}

### H2-002 — noise — PASS
> A car magazine review praises the ride quality of our Summit model.
- Read as: `noise` (reader: qwen3:0.6b)
- Stats: {"writes": 0, "calls": 0}

### H2-003 — compound — FAIL
> Ridgeline missed the the 22nd delivery of harness A to Wacky Wheels Greensboro. Revised date: 2027-03-23. Separately, ridgeline Wire issued a defect notice for HARN-B supplied to the Huntsille plant, production dates March 4th through March 5th: seal leaks.
- Read as: `quality_hold` (reader: rules)
- Stats: {"writes": 0, "calls": 1, "moved": 0, "rescheduled": 0, "transferred": 0, "expected_moves": 1, "dealers": 0, "loaners": 0, "lots": [], "stop_sale_vins": 0, "owners": 0}
- FAIL: incident kinds ['quality_hold'] expected ['quality_hold', 'supplier_delay']
- FAIL: escalated although the event is actionable / noise
- FAIL: 1 affected PO(s) not moved: ['PO-0511']
- FAIL: dealer set: extra [], missing ['D02', 'D04', 'D07', 'D11', 'D20']
- FAIL: loaners: extra [], missing ['CO-02994', 'CO-02995']
- FAIL: lots held [] expected ['LOT-0280']
- FAIL: stop-sale VINs: got 0 expected 28 (extra [], missing ['AUR0004275', 'AUR0004276', 'AUR0004277'])
- FAIL: owners notified: got 0 expected 33 (extra [], missing ['C0170', 'C0353', 'C0890'])
- warn: only 0 kind(s) of write action (handbook rule 9 wants 3)

### H2-004 — compound — PASS
> A) Inbound 16-inch rims (Ironwood) to the Jackson plant: original delivery 15 Mar; now arriving Tue 16 March because of a machine breakdown at their site. B) Reminder to fill out the employee engagement survey.
- Read as: `supplier_delay` (reader: qwen3:0.6b)
- Stats: {"writes": 11, "calls": 11, "moved": 1, "rescheduled": 1, "transferred": 0, "expected_moves": 1, "dealers": 9, "loaners": 1, "lots": [], "stop_sale_vins": 0, "owners": 0}

### H2-005 — supplier_delay — FAIL
> Update on SH-0096 (SEAT-VAN): no longer Monday the 29th, expect 31 Mar. Destination the Lexigton plant. Shipper Harbor.
- Read as: `noise` (reader: rules)
- Stats: {"writes": 0, "calls": 0, "moved": 0, "rescheduled": 0, "transferred": 0, "expected_moves": 2, "dealers": 0, "loaners": 0, "lots": [], "stop_sale_vins": 0, "owners": 0}
- FAIL: incident kinds ['none'] expected ['supplier_delay']
- FAIL: 2 affected PO(s) not moved: ['PO-0168', 'PO-0171']
- FAIL: dealer set: extra [], missing ['D02', 'D03', 'D04', 'D06', 'D08']
- FAIL: loaners: extra [], missing ['CO-00978', 'CO-01002', 'CO-01006', 'CO-01007']
- warn: only 0 kind(s) of write action (handbook rule 9 wants 3)

### H2-006 — unconfirmed — PASS
> Could be a problem with paint supply, no details yet.
- Read as: `unconfirmed` (reader: qwen3:0.6b)
- Stats: {"writes": 0, "calls": 1}

### H2-007 — plant_outage — PASS
> Princeton is idle 2027-03-17 to Monday the 22nd due to an ammonia leak.
- Read as: `plant_outage` (reader: qwen3:0.6b)
- Stats: {"writes": 74, "calls": 74, "moved": 12, "rescheduled": 12, "transferred": 0, "expected_moves": 12, "dealers": 35, "loaners": 27, "lots": [], "stop_sale_vins": 0, "owners": 0}

### H2-008 — unconfirmed — PASS
> Hearing Lexington might go down for maintenance soon, no dates.
- Read as: `unconfirmed` (reader: qwen3:0.6b)
- Stats: {"writes": 0, "calls": 1}

### H2-009 — plant_outage — PASS
> Emergency: a boiler failure at the Lexington plant. Assembly paused Thursday the 25th through March 30th.
- Read as: `plant_outage` (reader: qwen3:0.6b)
- Stats: {"writes": 68, "calls": 68, "moved": 12, "rescheduled": 6, "transferred": 6, "expected_moves": 12, "dealers": 34, "loaners": 22, "lots": [], "stop_sale_vins": 0, "owners": 0}

### H2-010 — supplier_delay — PASS
> Per Volt, harness C for the San Antonio plant got pushed out a few days: 2027-03-15 -> 2027-03-18.
- Read as: `supplier_delay` (reader: rules)
- Stats: {"writes": 31, "calls": 31, "moved": 3, "rescheduled": 3, "transferred": 0, "expected_moves": 3, "dealers": 21, "loaners": 7, "lots": [], "stop_sale_vins": 0, "owners": 0}

### H2-011 — quality_hold — PASS
> Please quarantine LOT-0350: seal leaks in 20-inch all-season tires. the Greensoro plant builds February 25th through Monday the 1st.
- Read as: `quality_hold` (reader: qwen3:0.6b)
- Stats: {"writes": 82, "calls": 82, "moved": 0, "rescheduled": 0, "transferred": 0, "expected_moves": 0, "dealers": 0, "loaners": 0, "lots": ["LOT-0350"], "stop_sale_vins": 38, "owners": 56}

### H2-012 — supplier_delay — PASS
> Inbound 20-inch all-season tire (Brightline Rubber) to the Greensboro plant: original delivery 3/22; now arriving 3/25 because of a strike at their warehouse.
- Read as: `supplier_delay` (reader: rules)
- Stats: {"writes": 30, "calls": 30, "moved": 3, "rescheduled": 3, "transferred": 0, "expected_moves": 3, "dealers": 19, "loaners": 8, "lots": [], "stop_sale_vins": 0, "owners": 0}

### H2-013 — noise — PASS
> Reminder to fill out the employee engagement survey.
- Read as: `noise` (reader: qwen3:0.6b)
- Stats: {"writes": 0, "calls": 0}

### H2-014 — quality_hold — PASS
> Ironwood Wheels issued a defect notice for 20-inch alloy wheel supplied to Wacky Wheels San Antonio, production dates 4 Mar through 2027-03-05: excess solder.
- Read as: `quality_hold` (reader: qwen3:0.6b)
- Stats: {"writes": 98, "calls": 98, "moved": 0, "rescheduled": 0, "transferred": 0, "expected_moves": 0, "dealers": 0, "loaners": 0, "lots": ["LOT-0048"], "stop_sale_vins": 58, "owners": 65}

### H2-015 — plant_outage — PASS
> Wacky Wheels Huntsville is idle Fri 26 March to Tuesday the 30th due to a conveyor motor burnout.
- Read as: `plant_outage` (reader: qwen3:0.6b)
- Stats: {"writes": 51, "calls": 51, "moved": 9, "rescheduled": 6, "transferred": 3, "expected_moves": 9, "dealers": 28, "loaners": 14, "lots": [], "stop_sale_vins": 0, "owners": 0}

### H2-016 — supplier_delay — FAIL
> P_AL receiving: the TIRE-17 truck from Northgate won't show 3/29. Carrier now quoting April 2nd.
- Read as: `noise` (reader: rules)
- Stats: {"writes": 0, "calls": 0, "moved": 0, "rescheduled": 0, "transferred": 0, "expected_moves": 8, "dealers": 0, "loaners": 0, "lots": [], "stop_sale_vins": 0, "owners": 0}
- FAIL: incident kinds ['none'] expected ['supplier_delay']
- FAIL: 8 affected PO(s) not moved: ['PO-0437', 'PO-0438', 'PO-0440', 'PO-0441', 'PO-0443']
- FAIL: dealer set: extra [], missing ['D02', 'D04', 'D06', 'D07', 'D08']
- FAIL: loaners: extra [], missing ['CO-02575', 'CO-02578', 'CO-02579', 'CO-02587', 'CO-02590']
- warn: only 0 kind(s) of write action (handbook rule 9 wants 3)

### H2-017 — supplier_delay — FAIL
> Update on SH-0138 (standard wiring harness): no longer 3/15, expect Wed 17 March. Destination Jackson. Shipper Ridgeline.
- Read as: `noise` (reader: rules)
- Stats: {"writes": 0, "calls": 0, "moved": 0, "rescheduled": 0, "transferred": 0, "expected_moves": 4, "dealers": 0, "loaners": 0, "lots": [], "stop_sale_vins": 0, "owners": 0}
- FAIL: incident kinds ['none'] expected ['supplier_delay']
- FAIL: 4 affected PO(s) not moved: ['PO-0226', 'PO-0227', 'PO-0229', 'PO-0230']
- FAIL: dealer set: extra [], missing ['D02', 'D03', 'D04', 'D06', 'D07']
- FAIL: loaners: extra [], missing ['CO-01222', 'CO-01223', 'CO-01249', 'CO-01250', 'CO-01253']
- warn: only 0 kind(s) of write action (handbook rule 9 wants 3)

### H2-018 — supplier_delay — PASS
> Per Quanta, CHIP-IVI for the Lexigton plant got pushed out a few days: 2027-03-22 -> March 26th.
- Read as: `supplier_delay` (reader: rules)
- Stats: {"writes": 75, "calls": 75, "moved": 12, "rescheduled": 12, "transferred": 0, "expected_moves": 12, "dealers": 38, "loaners": 25, "lots": [], "stop_sale_vins": 0, "owners": 0}

### H2-019 — quality_hold — PASS
> QA hold: lot LOT-0230 (20-inch all-season tires from Brightline) used at the Princeton plant, builds February 25th to March 1st. Issue: wrong thread pitch.
- Read as: `quality_hold` (reader: qwen3:0.6b)
- Stats: {"writes": 69, "calls": 69, "moved": 0, "rescheduled": 0, "transferred": 0, "expected_moves": 0, "dealers": 0, "loaners": 0, "lots": ["LOT-0230"], "stop_sale_vins": 41, "owners": 45}

### H2-020 — plant_outage — PASS
> Emergency: a transformer fire at San Antonio. Assembly paused Fri 19 March through Wed 24 March.
- Read as: `plant_outage` (reader: qwen3:0.6b)
- Stats: {"writes": 76, "calls": 76, "moved": 12, "rescheduled": 12, "transferred": 0, "expected_moves": 12, "dealers": 39, "loaners": 25, "lots": [], "stop_sale_vins": 0, "owners": 0}

### H2-021 — supplier_delay — FAIL
> P_KY receiving: the leather seat set truck from Meridian won't show March 29th. Carrier now quoting 2027-04-01.
- Read as: `noise` (reader: rules)
- Stats: {"writes": 0, "calls": 0, "moved": 0, "rescheduled": 0, "transferred": 0, "expected_moves": 3, "dealers": 0, "loaners": 0, "lots": [], "stop_sale_vins": 0, "owners": 0}
- FAIL: incident kinds ['none'] expected ['supplier_delay']
- FAIL: 3 affected PO(s) not moved: ['PO-0167', 'PO-0170', 'PO-0173']
- FAIL: dealer set: extra [], missing ['D02', 'D08', 'D11', 'D12', 'D19']
- FAIL: loaners: extra [], missing ['CO-00968', 'CO-00970', 'CO-00973', 'CO-01000', 'CO-01020']
- warn: only 0 kind(s) of write action (handbook rule 9 wants 3)

### H2-022 — quality_hold — PASS
> QA hold: lot LOT-0328 (harness A from Ridgeline Wire) used at the Greensboro plant, builds 4 Mar to Friday the 5th. Issue: wrong thread pitch.
- Read as: `quality_hold` (reader: qwen3:0.6b)
- Stats: {"writes": 52, "calls": 52, "moved": 0, "rescheduled": 0, "transferred": 0, "expected_moves": 0, "dealers": 0, "loaners": 0, "lots": ["LOT-0328"], "stop_sale_vins": 36, "owners": 31}

### H2-023 — plant_outage — PASS
> Wacky Wheels Princeton is idle Thu 18 March to 3/22 due to an ammonia leak.
- Read as: `plant_outage` (reader: qwen3:0.6b)
- Stats: {"writes": 53, "calls": 53, "moved": 9, "rescheduled": 9, "transferred": 0, "expected_moves": 9, "dealers": 30, "loaners": 14, "lots": [], "stop_sale_vins": 0, "owners": 0}

### H2-024 — quality_hold — PASS
> Please quarantine LOT-0269: wrong thread pitch in sliding door module. the Huntsville plant builds February 22nd through February 24th.
- Read as: `quality_hold` (reader: qwen3:0.6b)
- Stats: {"writes": 74, "calls": 74, "moved": 0, "rescheduled": 0, "transferred": 0, "expected_moves": 0, "dealers": 0, "loaners": 0, "lots": ["LOT-0269"], "stop_sale_vins": 45, "owners": 47}

### H2-025 — quality_hold — PASS
> Please quarantine LOT-0111: seal leaks in 20-inch alloy wheels. Wacky Wheels Lexington builds 3/2 through the 3rd.
- Read as: `quality_hold` (reader: qwen3:0.6b)
- Stats: {"writes": 55, "calls": 55, "moved": 0, "rescheduled": 0, "transferred": 0, "expected_moves": 0, "dealers": 0, "loaners": 0, "lots": ["LOT-0111"], "stop_sale_vins": 26, "owners": 36}

### H2-026 — supplier_delay — FAIL
> Northgate Tire Co missed the next Mon delivery of 20-inch all-season tire to the Hutsville plant. Revised date: March 18th.
- Read as: `noise` (reader: rules)
- Stats: {"writes": 0, "calls": 0, "moved": 0, "rescheduled": 0, "transferred": 0, "expected_moves": 3, "dealers": 0, "loaners": 0, "lots": [], "stop_sale_vins": 0, "owners": 0}
- FAIL: incident kinds ['none'] expected ['supplier_delay']
- FAIL: 3 affected PO(s) not moved: ['PO-0406', 'PO-0409', 'PO-0412']
- FAIL: dealer set: extra [], missing ['D07', 'D08', 'D10', 'D12', 'D17']
- FAIL: loaners: extra [], missing ['CO-02294', 'CO-02298', 'CO-02301', 'CO-02302', 'CO-02323']
- warn: only 0 kind(s) of write action (handbook rule 9 wants 3)

### H2-027 — compound — PASS
> Please quarantine LOT-0217: wrong thread pitch in leather seats. Wacky Wheels Princeton builds 2027-02-22 through 2027-02-24. Separately, somebody thinks the latest driver-assist chip batch could be defective; no lot or dates.
- Read as: `quality_hold+unconfirmed` (reader: qwen3:0.6b, qwen3:0.6b)
- Stats: {"writes": 82, "calls": 83, "moved": 0, "rescheduled": 0, "transferred": 0, "expected_moves": 0, "dealers": 0, "loaners": 0, "lots": ["LOT-0217"], "stop_sale_vins": 38, "owners": 58}

### H2-028 — quality_hold — PASS
> QA hold: lot LOT-0239 (20-inch rims from SUP-03) used at the Prineton plant, builds the 2nd to Wednesday the 3rd. Issue: intermittent shorts.
- Read as: `quality_hold` (reader: qwen3:0.6b)
- Stats: {"writes": 58, "calls": 58, "moved": 0, "rescheduled": 0, "transferred": 0, "expected_moves": 0, "dealers": 0, "loaners": 0, "lots": ["LOT-0239"], "stop_sale_vins": 35, "owners": 34}

### H2-029 — unconfirmed — PASS
> Gossip says Quanta Silicon is in financial trouble; could affect supply. Nothing confirmed.
- Read as: `unconfirmed` (reader: qwen3:0.6b)
- Stats: {"writes": 0, "calls": 1}

### H2-030 — noise — PASS
> Parking permits must be renewed by the end of the month.
- Read as: `noise` (reader: qwen3:0.6b)
- Stats: {"writes": 0, "calls": 0}

### H2-031 — unconfirmed — FAIL
> Possible labor action at Lexington? Not confirmed.
- Read as: `noise` (reader: rules)
- Stats: {"writes": 0, "calls": 0}
- FAIL: expected an escalate, none made

### H2-032 — supplier_delay — FAIL
> Update on SH-0140 (harness A): no longer the 29th, expect Thu 1 April. Destination the Jackson plant. Shipper SUP-16.
- Read as: `noise` (reader: rules)
- Stats: {"writes": 0, "calls": 0, "moved": 0, "rescheduled": 0, "transferred": 0, "expected_moves": 6, "dealers": 0, "loaners": 0, "lots": [], "stop_sale_vins": 0, "owners": 0}
- FAIL: incident kinds ['none'] expected ['supplier_delay']
- FAIL: 6 affected PO(s) not moved: ['PO-0256', 'PO-0257', 'PO-0259', 'PO-0260', 'PO-0262']
- FAIL: dealer set: extra [], missing ['D02', 'D03', 'D04', 'D05', 'D06']
- FAIL: loaners: extra [], missing ['CO-01488', 'CO-01489', 'CO-01490', 'CO-01491', 'CO-01492']
- warn: only 0 kind(s) of write action (handbook rule 9 wants 3)

### H2-033 — quality_hold — PASS
> Field reports of excess solder traced to airbag modules from Sterling Safety at the Kentucky plant; affected build window 4 Mar to the 5th.
- Read as: `quality_hold` (reader: qwen3:0.6b)
- Stats: {"writes": 132, "calls": 132, "moved": 0, "rescheduled": 0, "transferred": 0, "expected_moves": 0, "dealers": 0, "loaners": 0, "lots": ["LOT-0052"], "stop_sale_vins": 79, "owners": 97}

### H2-034 — noise — PASS
> Fire drill at the Princeton office building Thursday at 10 am. Plan to be outside for 15 minutes.
- Read as: `noise` (reader: qwen3:0.6b)
- Stats: {"writes": 0, "calls": 0}

### H2-035 — plant_outage — PASS
> P_MS is idle 2027-03-11 to Fri 12 March due to an ammonia leak.
- Read as: `plant_outage` (reader: qwen3:0.6b)
- Stats: {"writes": 42, "calls": 42, "moved": 6, "rescheduled": 6, "transferred": 0, "expected_moves": 6, "dealers": 29, "loaners": 7, "lots": [], "stop_sale_vins": 0, "owners": 0}

### H2-036 — plant_outage — PASS
> Lexington production halted from 30 Mar after a conveyor motor burnout; restart planned Thu 1 April.
- Read as: `plant_outage` (reader: qwen3:0.6b)
- Stats: {"writes": 45, "calls": 45, "moved": 6, "rescheduled": 4, "transferred": 2, "expected_moves": 6, "dealers": 26, "loaners": 13, "lots": [], "stop_sale_vins": 0, "owners": 0}

### H2-037 — supplier_delay — PASS
> Inbound BRAKE-KIT (SUP-17) to P_IN: original delivery next Monday; now arriving the 18th because of a raw-material shortage.
- Read as: `supplier_delay` (reader: qwen3:0.6b)
- Stats: {"writes": 49, "calls": 49, "moved": 6, "rescheduled": 6, "transferred": 0, "expected_moves": 6, "dealers": 24, "loaners": 19, "lots": [], "stop_sale_vins": 0, "owners": 0}

### H2-038 — quality_hold — PASS
> Field reports of a mislabeled part number traced to 60 kWh battery packs from Helix Power at Wacky Wheels Princeton; affected build window February 22nd to 2/24.
- Read as: `quality_hold` (reader: qwen3:0.6b)
- Stats: {"writes": 82, "calls": 82, "moved": 0, "rescheduled": 0, "transferred": 0, "expected_moves": 0, "dealers": 0, "loaners": 0, "lots": ["LOT-0173"], "stop_sale_vins": 38, "owners": 58}

### H2-039 — compound — PASS
> Per Meridian Seating, leather seats for Wacky Wheels San Antonio got pushed out a few days: Monday the 22nd -> 24 Mar. Separately, meridian issued a defect notice for SEAT-FAB supplied to the Texas plant, production dates 4 Mar through 3/5: excess solder.
- Read as: `supplier_delay+quality_hold` (reader: qwen3:0.6b, qwen3:0.6b)
- Stats: {"writes": 113, "calls": 113, "moved": 2, "rescheduled": 2, "transferred": 0, "expected_moves": 2, "dealers": 13, "loaners": 3, "lots": ["LOT-0028"], "stop_sale_vins": 55, "owners": 65}

### H2-040 — quality_hold — PASS
> QA hold: lot LOT-0063 (infotainment chips from Quanta) used at the Lexington plant, builds 3/2 to the 3rd. Issue: brittle plastic clips.
- Read as: `quality_hold` (reader: qwen3:0.6b)
- Stats: {"writes": 130, "calls": 130, "moved": 0, "rescheduled": 0, "transferred": 0, "expected_moves": 0, "dealers": 0, "loaners": 0, "lots": ["LOT-0063"], "stop_sale_vins": 85, "owners": 97}

### H2-041 — compound — FAIL
> Two notes: 1) Jackson is idle Wed 24 March to 29 Mar due to a transformer fire. 2) Heads up: we're losing P_AL for 10 Mar through 3/11 (a cyberattack on the line controllers).
- Read as: `plant_outage+noise` (reader: qwen3:0.6b, qwen3:0.6b)
- Stats: {"writes": 70, "calls": 70, "moved": 12, "rescheduled": 8, "transferred": 4, "expected_moves": 18, "dealers": 37, "loaners": 21, "lots": [], "stop_sale_vins": 0, "owners": 0}
- FAIL: incident kinds ['plant_outage'] expected ['plant_outage', 'plant_outage']
- FAIL: 6 affected PO(s) not moved: ['PO-0397', 'PO-0398', 'PO-0399', 'PO-0400', 'PO-0401']
- FAIL: dealer set: extra [], missing ['D04', 'D17', 'D19', 'D21']
- FAIL: dealer D02 order list: extra [], missing ['CO-02220']
- FAIL: dealer D03 order list: extra [], missing ['CO-02218', 'CO-02235', 'CO-02242']
- FAIL: dealer D06 order list: extra [], missing ['CO-02250', 'CO-02252']
- FAIL: dealer D07 order list: extra [], missing ['CO-02265']
- FAIL: dealer D08 order list: extra [], missing ['CO-02238']
- FAIL: dealer D10 order list: extra [], missing ['CO-02223', 'CO-02231']
- FAIL: dealer D12 order list: extra [], missing ['CO-02237']
- FAIL: dealer D18 order list: extra [], missing ['CO-02232']
- FAIL: dealer D20 order list: extra [], missing ['CO-02221']
- FAIL: dealer D22 order list: extra [], missing ['CO-02236', 'CO-02262']
- FAIL: dealer D24 order list: extra [], missing ['CO-02256']
- FAIL: dealer D25 order list: extra [], missing ['CO-02225', 'CO-02226', 'CO-02243']
- FAIL: dealer D26 order list: extra [], missing ['CO-02227', 'CO-02253', 'CO-02254']
- FAIL: dealer D27 order list: extra [], missing ['CO-02219', 'CO-02230']
- FAIL: dealer D31 order list: extra [], missing ['CO-02244', 'CO-02251']
- FAIL: dealer D32 order list: extra [], missing ['CO-02229']
- FAIL: dealer D35 order list: extra [], missing ['CO-02222', 'CO-02259']
- FAIL: dealer D43 order list: extra [], missing ['CO-02228']
- FAIL: dealer D44 order list: extra [], missing ['CO-02239', 'CO-02261']
- FAIL: dealer D45 order list: extra [], missing ['CO-02217', 'CO-02224', 'CO-02233']
- FAIL: dealer D46 order list: extra [], missing ['CO-02240']
- FAIL: dealer D47 order list: extra [], missing ['CO-02255']
- FAIL: loaners: extra ['CO-01488', 'CO-01496'], missing ['CO-02222', 'CO-02224', 'CO-02227', 'CO-02230', 'CO-02232']

### H2-042 — noise — PASS
> Fire drill at the Huntsville office building Thursday at 10 am. Plan to be outside for 15 minutes.
- Read as: `noise` (reader: qwen3:0.6b)
- Stats: {"writes": 0, "calls": 0}

### H2-043 — plant_outage — PASS
> Emergency: a cyberattack on the line controllers at P_NC. Assembly paused 2027-03-17 through next Thursday.
- Read as: `plant_outage` (reader: rules)
- Stats: {"writes": 50, "calls": 50, "moved": 6, "rescheduled": 6, "transferred": 0, "expected_moves": 6, "dealers": 33, "loaners": 11, "lots": [], "stop_sale_vins": 0, "owners": 0}

### H2-044 — compound — FAIL
> Fire drill at the Princeton office building Thursday at 10 am. Plan to be outside for 15 minutes. Separately, the Indiana plant production halted from 10 Mar after a transformer fire; restart planned March 12th.
- Read as: `plant_outage` (reader: rules)
- Stats: {"writes": 0, "calls": 1, "moved": 0, "rescheduled": 0, "transferred": 0, "expected_moves": 6, "dealers": 0, "loaners": 0, "lots": [], "stop_sale_vins": 0, "owners": 0}
- FAIL: plant_outage fields: outage_start=2027-03-11 (expected 2027-03-10), outage_end=2027-03-10 (expected 2027-03-11)
- FAIL: escalated although the event is actionable / noise
- FAIL: 6 affected PO(s) not moved: ['PO-0307', 'PO-0308', 'PO-0309', 'PO-0310', 'PO-0311']
- FAIL: dealer set: extra [], missing ['D03', 'D06', 'D07', 'D08', 'D09']
- FAIL: loaners: extra [], missing ['CO-01677', 'CO-01680', 'CO-01685', 'CO-01691', 'CO-01692']
- warn: only 0 kind(s) of write action (handbook rule 9 wants 3)

### H2-045 — unconfirmed — PASS
> A driver mentioned possible delays at the border. Unverified.
- Read as: `unconfirmed` (reader: qwen3:0.6b)
- Stats: {"writes": 0, "calls": 1}

### H2-046 — unconfirmed — FAIL
> Possible labor action at Wacky Wheels Lexington? Not confirmed.
- Read as: `noise` (reader: rules)
- Stats: {"writes": 0, "calls": 0}
- FAIL: expected an escalate, none made

### H2-047 — supplier_delay — PASS
> Princeton receiving: the 20-inch rims truck from SUP-03 won't show Monday the 15th. Carrier now quoting next Tue.
- Read as: `supplier_delay` (reader: qwen3:0.6b)
- Stats: {"writes": 11, "calls": 11, "moved": 1, "rescheduled": 1, "transferred": 0, "expected_moves": 1, "dealers": 9, "loaners": 1, "lots": [], "stop_sale_vins": 0, "owners": 0}

### H2-048 — plant_outage — PASS
> the Hunsville plant production halted from Tuesday the 30th after ice damage to the roof; restart planned 2 Apr.
- Read as: `plant_outage` (reader: rules)
- Stats: {"writes": 59, "calls": 59, "moved": 9, "rescheduled": 2, "transferred": 7, "expected_moves": 9, "dealers": 33, "loaners": 17, "lots": [], "stop_sale_vins": 0, "owners": 0}

### H2-049 — supplier_delay — FAIL
> Heads-up: Meridian Seating says the SEAT-VAN bound for P_AL slid from March 29th to 4/1.
- Read as: `noise` (reader: rules)
- Stats: {"writes": 0, "calls": 0, "moved": 0, "rescheduled": 0, "transferred": 0, "expected_moves": 3, "dealers": 0, "loaners": 0, "lots": [], "stop_sale_vins": 0, "owners": 0}
- FAIL: incident kinds ['none'] expected ['supplier_delay']
- FAIL: 3 affected PO(s) not moved: ['PO-0438', 'PO-0441', 'PO-0444']
- FAIL: dealer set: extra [], missing ['D04', 'D06', 'D08', 'D12', 'D16']
- FAIL: loaners: extra [], missing ['CO-02587', 'CO-02590', 'CO-02615', 'CO-02640', 'CO-02641']
- warn: only 0 kind(s) of write action (handbook rule 9 wants 3)

### H2-050 — plant_outage — PASS
> Wacky Wheels Princeton is idle Tuesday the 23rd to 3/29 due to an ammonia leak.
- Read as: `plant_outage` (reader: qwen3:0.6b)
- Stats: {"writes": 78, "calls": 78, "moved": 15, "rescheduled": 8, "transferred": 7, "expected_moves": 15, "dealers": 38, "loaners": 25, "lots": [], "stop_sale_vins": 0, "owners": 0}

### H2-051 — noise — PASS
> Please welcome our new CFO, who starts on Monday.
- Read as: `noise` (reader: qwen3:0.6b)
- Stats: {"writes": 0, "calls": 0}

### H2-052 — unconfirmed — PASS
> rumor: chip shortage coming, no idea when
- Read as: `unconfirmed` (reader: qwen3:0.6b)
- Stats: {"writes": 0, "calls": 1}

### H2-053 — noise — PASS
> Lunch and learn on EV battery chemistry in the big conference room today.
- Read as: `noise` (reader: qwen3:0.6b)
- Stats: {"writes": 0, "calls": 0}

### H2-054 — supplier_delay — FAIL
> Per Ironwood, 16-inch alloy wheels for Jackson got pushed out a few days: Mon 22 March -> Wednesday the 24th.
- Read as: `unconfirmed` (reader: rules)
- Stats: {"writes": 0, "calls": 1, "moved": 0, "rescheduled": 0, "transferred": 0, "expected_moves": 2, "dealers": 0, "loaners": 0, "lots": [], "stop_sale_vins": 0, "owners": 0}
- FAIL: incident kinds ['none'] expected ['supplier_delay']
- FAIL: escalated although the event is actionable / noise
- FAIL: 2 affected PO(s) not moved: ['PO-0243', 'PO-0246']
- FAIL: dealer set: extra [], missing ['D04', 'D08', 'D10', 'D12', 'D16']
- FAIL: loaners: extra [], missing ['CO-01374', 'CO-01402', 'CO-01405', 'CO-01407']
- warn: only 0 kind(s) of write action (handbook rule 9 wants 3)

### H2-055 — quality_hold — PASS
> Please quarantine LOT-0275: brittle plastic clips in standard wiring harness. the Huntsville plant builds the 2nd through 3/3.
- Read as: `quality_hold` (reader: qwen3:0.6b)
- Stats: {"writes": 58, "calls": 58, "moved": 0, "rescheduled": 0, "transferred": 0, "expected_moves": 0, "dealers": 0, "loaners": 0, "lots": ["LOT-0275"], "stop_sale_vins": 22, "owners": 41}

### H2-056 — unconfirmed — FAIL
> Possible labor action at Huntsville? Not confirmed.
- Read as: `noise` (reader: rules)
- Stats: {"writes": 0, "calls": 0}
- FAIL: expected an escalate, none made

### H2-057 — quality_hold — FAIL
> Field reports of wrong thread pitch traced to 12-inch displays from Orbit Optics at the Greensbro plant; affected build window the 4th to Friday the 5th.
- Read as: `noise` (reader: rules)
- Stats: {"writes": 0, "calls": 0, "moved": 0, "rescheduled": 0, "transferred": 0, "expected_moves": 0, "dealers": 0, "loaners": 0, "lots": [], "stop_sale_vins": 0, "owners": 0}
- FAIL: incident kinds ['none'] expected ['quality_hold']
- FAIL: lots held [] expected ['LOT-0324']
- FAIL: stop-sale VINs: got 0 expected 36 (extra [], missing ['AUR0005166', 'AUR0005167', 'AUR0005168'])
- FAIL: owners notified: got 0 expected 31 (extra [], missing ['C0016', 'C0081', 'C0085'])
- warn: only 0 kind(s) of write action (handbook rule 9 wants 3)

### H2-058 — compound — FAIL
> Shift report. (1) Per Atlas, standard wiring harness for Lexington got pushed out a few days: 3/29 -> March 30th. (2) Field reports of excess solder traced to 17-inch all-season tires from Granite at Jackson; affected build window 2027-02-25 to 3/1.
- Read as: `supplier_delay+noise` (reader: qwen3:0.6b, rules)
- Stats: {"writes": 10, "calls": 10, "moved": 1, "rescheduled": 1, "transferred": 0, "expected_moves": 1, "dealers": 8, "loaners": 1, "lots": [], "stop_sale_vins": 0, "owners": 0}
- FAIL: incident kinds ['supplier_delay'] expected ['quality_hold', 'supplier_delay']
- FAIL: lots held [] expected ['LOT-0158']
- FAIL: stop-sale VINs: got 0 expected 74 (extra [], missing ['AUR0002037', 'AUR0002038', 'AUR0002041'])
- FAIL: owners notified: got 0 expected 90 (extra [], missing ['C0038', 'C0088', 'C0089'])

### H2-059 — quality_hold — PASS
> Quanta Silicon issued a defect notice for driver-assist chips supplied to the Jackson plant, production dates March 4th through 3/5: intermittent shorts.
- Read as: `quality_hold` (reader: qwen3:0.6b)
- Stats: {"writes": 57, "calls": 57, "moved": 0, "rescheduled": 0, "transferred": 0, "expected_moves": 0, "dealers": 0, "loaners": 0, "lots": ["LOT-0128"], "stop_sale_vins": 25, "owners": 38}

### H2-060 — plant_outage — FAIL
> Heads up: we're losing the Grensboro plant for 3/18 through 23 Mar (a boiler failure).
- Read as: `noise` (reader: rules)
- Stats: {"writes": 0, "calls": 0, "moved": 0, "rescheduled": 0, "transferred": 0, "expected_moves": 12, "dealers": 0, "loaners": 0, "lots": [], "stop_sale_vins": 0, "owners": 0}
- FAIL: incident kinds ['none'] expected ['plant_outage']
- FAIL: 12 affected PO(s) not moved: ['PO-0505', 'PO-0506', 'PO-0507', 'PO-0508', 'PO-0509']
- FAIL: dealer set: extra [], missing ['D01', 'D02', 'D03', 'D04', 'D05']
- FAIL: loaners: extra [], missing ['CO-02933', 'CO-02940', 'CO-02942', 'CO-02945', 'CO-02948']
- warn: only 0 kind(s) of write action (handbook rule 9 wants 3)

### H2-061 — plant_outage — PASS
> Heads up: we're losing the North Carolina plant for 2027-03-11 through Fri 12 March (a boiler failure).
- Read as: `plant_outage` (reader: qwen3:0.6b)
- Stats: {"writes": 40, "calls": 40, "moved": 6, "rescheduled": 6, "transferred": 0, "expected_moves": 6, "dealers": 23, "loaners": 11, "lots": [], "stop_sale_vins": 0, "owners": 0}

### H2-062 — plant_outage — PASS
> Huntsville is idle 3/11 to 12 Mar due to a conveyor motor burnout.
- Read as: `plant_outage` (reader: qwen3:0.6b)
- Stats: {"writes": 46, "calls": 46, "moved": 6, "rescheduled": 6, "transferred": 0, "expected_moves": 6, "dealers": 28, "loaners": 12, "lots": [], "stop_sale_vins": 0, "owners": 0}

### H2-063 — compound — FAIL
> Lunch and learn on EV battery chemistry in the big conference room today. Separately, heads up: we're losing Jackson for 2027-03-22 through Tuesday the 23rd (a boiler failure).
- Read as: `plant_outage` (reader: qwen3:0.6b)
- Stats: {"writes": 27, "calls": 27, "moved": 3, "rescheduled": 3, "transferred": 0, "expected_moves": 6, "dealers": 17, "loaners": 7, "lots": [], "stop_sale_vins": 0, "owners": 0}
- FAIL: plant_outage fields: outage_start=2027-03-23 (expected 2027-03-22)
- FAIL: 3 affected PO(s) not moved: ['PO-0241', 'PO-0242', 'PO-0243']
- FAIL: dealer set: extra [], missing ['D03', 'D12', 'D15', 'D23', 'D24']
- FAIL: dealer D06 order list: extra [], missing ['CO-01372']
- FAIL: dealer D16 order list: extra [], missing ['CO-01374']
- FAIL: dealer D25 order list: extra [], missing ['CO-01356', 'CO-01362', 'CO-01375']
- FAIL: dealer D27 order list: extra [], missing ['CO-01365']
- FAIL: dealer D35 order list: extra [], missing ['CO-01363']
- FAIL: dealer D37 order list: extra [], missing ['CO-01358']
- FAIL: dealer D44 order list: extra [], missing ['CO-01361']
- FAIL: loaners: extra [], missing ['CO-01357', 'CO-01361', 'CO-01366', 'CO-01369', 'CO-01371']

### H2-064 — noise — PASS
> The holiday schedule for next year has been posted.
- Read as: `noise` (reader: qwen3:0.6b)
- Stats: {"writes": 0, "calls": 0}

### H2-065 — unconfirmed — FAIL
> Possible labor action at the North Carolina plant? Not confirmed.
- Read as: `noise` (reader: rules)
- Stats: {"writes": 0, "calls": 0}
- FAIL: expected an escalate, none made

### H2-066 — plant_outage — PASS
> Huntsville is idle on Monday the 29th because of an ammonia leak.
- Read as: `plant_outage` (reader: rules)
- Stats: {"writes": 25, "calls": 25, "moved": 3, "rescheduled": 3, "transferred": 0, "expected_moves": 3, "dealers": 16, "loaners": 6, "lots": [], "stop_sale_vins": 0, "owners": 0}

### H2-067 — supplier_delay — PASS
> Inbound compact wiring harness (Ridgeline) to the North Carolina plant: original delivery March 29th; now arriving 2 Apr because of a missed vessel.
- Read as: `supplier_delay` (reader: qwen3:0.6b)
- Stats: {"writes": 32, "calls": 32, "moved": 4, "rescheduled": 2, "transferred": 2, "expected_moves": 4, "dealers": 22, "loaners": 6, "lots": [], "stop_sale_vins": 0, "owners": 0}

### H2-068 — unconfirmed — PASS
> Gossip says Granite Tire is in financial trouble; could affect supply. Nothing confirmed.
- Read as: `unconfirmed` (reader: qwen3:0.6b)
- Stats: {"writes": 0, "calls": 1}

### H2-069 — compound — PASS
> Two notes: 1) P_NC receiving: the harness B truck from Volt won't show 29 Mar. Carrier now quoting Tue 30 March. 2) Heavy rain expected in Seattle, WA through Wednesday.
- Read as: `supplier_delay+noise` (reader: qwen3:0.6b, qwen3:0.6b)
- Stats: {"writes": 11, "calls": 11, "moved": 1, "rescheduled": 1, "transferred": 0, "expected_moves": 1, "dealers": 8, "loaners": 2, "lots": [], "stop_sale_vins": 0, "owners": 0}

### H2-070 — supplier_delay — PASS
> Inbound airbag modules (Sterling) to the Kentucky plant: original delivery March 29th; now arriving 2027-03-31 because of a derailment.
- Read as: `supplier_delay` (reader: qwen3:0.6b)
- Stats: {"writes": 42, "calls": 42, "moved": 6, "rescheduled": 6, "transferred": 0, "expected_moves": 6, "dealers": 26, "loaners": 10, "lots": [], "stop_sale_vins": 0, "owners": 0}

### H2-071 — quality_hold — PASS
> Meridian Seating issued a defect notice for leather seat set supplied to Lexington, production dates 2027-02-25 through March 1st: wrong thread pitch.
- Read as: `quality_hold` (reader: rules)
- Stats: {"writes": 73, "calls": 73, "moved": 0, "rescheduled": 0, "transferred": 0, "expected_moves": 0, "dealers": 0, "loaners": 0, "lots": ["LOT-0090"], "stop_sale_vins": 32, "owners": 52}

### H2-072 — plant_outage — PASS
> Heads up: we're losing Huntsville for Wed 10 March through Thursday the 11th (a boiler failure).
- Read as: `plant_outage` (reader: qwen3:0.6b)
- Stats: {"writes": 43, "calls": 43, "moved": 6, "rescheduled": 6, "transferred": 0, "expected_moves": 6, "dealers": 26, "loaners": 11, "lots": [], "stop_sale_vins": 0, "owners": 0}

### H2-073 — noise — PASS
> Town hall slides are posted on the intranet.
- Read as: `noise` (reader: qwen3:0.6b)
- Stats: {"writes": 0, "calls": 0}

### H2-074 — plant_outage — PASS
> the San Antonio plant is idle 3/23 to the 24th due to ice damage to the roof.
- Read as: `plant_outage` (reader: qwen3:0.6b)
- Stats: {"writes": 53, "calls": 53, "moved": 6, "rescheduled": 6, "transferred": 0, "expected_moves": 6, "dealers": 29, "loaners": 18, "lots": [], "stop_sale_vins": 0, "owners": 0}

### H2-075 — supplier_delay — FAIL
> San Antonio receiving: the infotainment chips truck from SUP-06 won't show Mon 15 March. Carrier now quoting next Tue.
- Read as: `noise` (reader: rules)
- Stats: {"writes": 0, "calls": 0, "moved": 0, "rescheduled": 0, "transferred": 0, "expected_moves": 2, "dealers": 0, "loaners": 0, "lots": [], "stop_sale_vins": 0, "owners": 0}
- FAIL: incident kinds ['none'] expected ['supplier_delay']
- FAIL: 2 affected PO(s) not moved: ['PO-0047', 'PO-0048']
- FAIL: dealer set: extra [], missing ['D02', 'D07', 'D08', 'D13', 'D16']
- FAIL: loaners: extra [], missing ['CO-00152', 'CO-00153', 'CO-00154', 'CO-00155', 'CO-00156']
- warn: only 0 kind(s) of write action (handbook rule 9 wants 3)

### H2-076 — unconfirmed — PASS
> Hearing Princeton might go down for maintenance soon, no dates.
- Read as: `unconfirmed` (reader: rules)
- Stats: {"writes": 0, "calls": 1}

### H2-077 — quality_hold — PASS
> Please quarantine LOT-0077: intermittent shorts in HARN-B. Lexington builds 22 Feb through 2027-02-24.
- Read as: `quality_hold` (reader: qwen3:0.6b)
- Stats: {"writes": 71, "calls": 71, "moved": 0, "rescheduled": 0, "transferred": 0, "expected_moves": 0, "dealers": 0, "loaners": 0, "lots": ["LOT-0077"], "stop_sale_vins": 46, "owners": 45}

### H2-078 — compound — FAIL
> First, the Lexington plant is idle the 23rd to Mon 29 March due to a conveyor motor burnout. Second, emergency: a conveyor motor burnout at Wacky Wheels San Antonio. Assembly paused Thursday the 25th through 2027-03-29.
- Read as: `plant_outage` (reader: qwen3:0.6b)
- Stats: {"writes": 83, "calls": 83, "moved": 15, "rescheduled": 8, "transferred": 7, "expected_moves": 24, "dealers": 39, "loaners": 29, "lots": [], "stop_sale_vins": 0, "owners": 0}
- FAIL: incident kinds ['plant_outage'] expected ['plant_outage', 'plant_outage']
- FAIL: 9 affected PO(s) not moved: ['PO-0070', 'PO-0071', 'PO-0072', 'PO-0073', 'PO-0074']
- FAIL: dealer set: extra [], missing ['D09', 'D47']
- FAIL: dealer D02 order list: extra [], missing ['CO-00412']
- FAIL: dealer D03 order list: extra [], missing ['CO-00375', 'CO-00397', 'CO-00423']
- FAIL: dealer D04 order list: extra [], missing ['CO-00398', 'CO-00402']
- FAIL: dealer D06 order list: extra [], missing ['CO-00388', 'CO-00404', 'CO-00405']
- FAIL: dealer D07 order list: extra [], missing ['CO-00395', 'CO-00413', 'CO-00417']
- FAIL: dealer D08 order list: extra [], missing ['CO-00408', 'CO-00420', 'CO-00430']
- FAIL: dealer D10 order list: extra [], missing ['CO-00369', 'CO-00393']
- FAIL: dealer D12 order list: extra [], missing ['CO-00411', 'CO-00415']
- FAIL: dealer D16 order list: extra [], missing ['CO-00443']
- FAIL: dealer D17 order list: extra [], missing ['CO-00427']
- FAIL: dealer D20 order list: extra [], missing ['CO-00380', 'CO-00386']
- FAIL: dealer D21 order list: extra [], missing ['CO-00362', 'CO-00378', 'CO-00391']
- FAIL: dealer D23 order list: extra [], missing ['CO-00365', 'CO-00383', 'CO-00384']
- FAIL: dealer D24 order list: extra [], missing ['CO-00410', 'CO-00422']
- FAIL: dealer D25 order list: extra [], missing ['CO-00357', 'CO-00371', 'CO-00372']
- FAIL: dealer D26 order list: extra [], missing ['CO-00359', 'CO-00360', 'CO-00366']
- FAIL: dealer D27 order list: extra [], missing ['CO-00364', 'CO-00379', 'CO-00382']
- FAIL: dealer D28 order list: extra [], missing ['CO-00426']
- FAIL: dealer D29 order list: extra [], missing ['CO-00436']
- FAIL: dealer D31 order list: extra [], missing ['CO-00437']
- FAIL: dealer D32 order list: extra [], missing ['CO-00368', 'CO-00421', 'CO-00434']
- FAIL: dealer D34 order list: extra [], missing ['CO-00390', 'CO-00414']
- FAIL: dealer D35 order list: extra [], missing ['CO-00406']
- FAIL: dealer D38 order list: extra [], missing ['CO-00361']
- FAIL: dealer D43 order list: extra [], missing ['CO-00394']
- FAIL: dealer D44 order list: extra [], missing ['CO-00358', 'CO-00376', 'CO-00431']
- FAIL: dealer D45 order list: extra [], missing ['CO-00367', 'CO-00403', 'CO-00409']
- FAIL: dealer D46 order list: extra [], missing ['CO-00363', 'CO-00389', 'CO-00407']
- FAIL: loaners: extra ['CO-00858', 'CO-00935', 'CO-00942', 'CO-00956', 'CO-00968'], missing ['CO-00357', 'CO-00364', 'CO-00369', 'CO-00375', 'CO-00383']

### H2-079 — supplier_delay — PASS
> Per SUP-05, HARN-C for P_TX got pushed out a few days: 3/22 -> March 23rd.
- Read as: `supplier_delay` (reader: qwen3:0.6b)
- Stats: {"writes": 9, "calls": 9, "moved": 1, "rescheduled": 1, "transferred": 0, "expected_moves": 1, "dealers": 7, "loaners": 1, "lots": [], "stop_sale_vins": 0, "owners": 0}

### H2-080 — noise — PASS
> Dealer Nashville asks for the updated accessory price sheets.
- Read as: `noise` (reader: qwen3:0.6b)
- Stats: {"writes": 0, "calls": 0}

### H2-081 — compound — FAIL
> First, kestrel Electronics issued a defect notice for infotainment chip supplied to Jackson, production dates 2027-02-22 through 2/24: a mislabeled part number. Second, a driver mentioned possible delays at the border. Unverified.
- Read as: `quality_hold` (reader: qwen3:0.6b)
- Stats: {"writes": 183, "calls": 183, "moved": 0, "rescheduled": 0, "transferred": 0, "expected_moves": 0, "dealers": 0, "loaners": 0, "lots": ["LOT-0129"], "stop_sale_vins": 116, "owners": 142}
- FAIL: expected an escalate, none made

### H2-082 — compound — FAIL
> Two notes: 1) Per Atlas, HARN-A for P_AL got pushed out a few days: 3/29 -> April 2nd. 2) Field reports of excess solder traced to minivan seats from Harbor at the Princeon plant; affected build window 25 Feb to Monday the 1st.
- Read as: `supplier_delay+noise` (reader: rules, rules)
- Stats: {"writes": 36, "calls": 36, "moved": 4, "rescheduled": 2, "transferred": 2, "expected_moves": 4, "dealers": 23, "loaners": 9, "lots": [], "stop_sale_vins": 0, "owners": 0}
- FAIL: incident kinds ['supplier_delay'] expected ['quality_hold', 'supplier_delay']
- FAIL: lots held [] expected ['LOT-0222']
- FAIL: stop-sale VINs: got 0 expected 37 (extra [], missing ['AUR0002911', 'AUR0002912', 'AUR0002913'])
- FAIL: owners notified: got 0 expected 53 (extra [], missing ['C0166', 'C0372', 'C0452'])

### H2-083 — supplier_delay — FAIL
> Wacky Wheels Jackson receiving: the airbag modules truck from Sentinel Brake and Airbag won't show next Mon. Carrier now quoting 2027-03-19.
- Read as: `noise` (reader: rules)
- Stats: {"writes": 0, "calls": 0, "moved": 0, "rescheduled": 0, "transferred": 0, "expected_moves": 12, "dealers": 0, "loaners": 0, "lots": [], "stop_sale_vins": 0, "owners": 0}
- FAIL: incident kinds ['none'] expected ['supplier_delay']
- FAIL: 12 affected PO(s) not moved: ['PO-0226', 'PO-0227', 'PO-0228', 'PO-0229', 'PO-0230']
- FAIL: dealer set: extra [], missing ['D02', 'D03', 'D04', 'D05', 'D06']
- FAIL: loaners: extra [], missing ['CO-01222', 'CO-01223', 'CO-01242', 'CO-01249', 'CO-01250']
- warn: only 0 kind(s) of write action (handbook rule 9 wants 3)

### H2-084 — compound — PASS
> Two notes: 1) Heads up: we're losing Princeton for 16 Mar through Thursday the 18th (a conveyor motor burnout). 2) Per Quanta, infotainment chip for Wacky Wheels Lexington got pushed out a few days: 3/29 -> Tue 30 March.
- Read as: `plant_outage+supplier_delay` (reader: qwen3:0.6b, rules)
- Stats: {"writes": 74, "calls": 74, "moved": 12, "rescheduled": 12, "transferred": 0, "expected_moves": 12, "dealers": 34, "loaners": 28, "lots": [], "stop_sale_vins": 0, "owners": 0}

### H2-085 — noise — PASS
> Reminder: submit March expense reports through the finance portal.
- Read as: `noise` (reader: qwen3:0.6b)
- Stats: {"writes": 0, "calls": 0}

### H2-086 — supplier_delay — PASS
> Update on SH-0211 (HARN-C): no longer the 22nd, expect the 25th. Destination the Indiana plant. Shipper Ridgeline Wire.
- Read as: `supplier_delay` (reader: qwen3:0.6b)
- Stats: {"writes": 28, "calls": 28, "moved": 3, "rescheduled": 3, "transferred": 0, "expected_moves": 3, "dealers": 19, "loaners": 6, "lots": [], "stop_sale_vins": 0, "owners": 0}

### H2-087 — supplier_delay — FAIL
> Inbound infotainment chips (Kestrel) to the Texas plant: original delivery March 15th; now arriving March 19th because of a strike at their warehouse.
- Read as: `unconfirmed` (reader: rules)
- Stats: {"writes": 0, "calls": 1, "moved": 0, "rescheduled": 0, "transferred": 0, "expected_moves": 8, "dealers": 0, "loaners": 0, "lots": [], "stop_sale_vins": 0, "owners": 0}
- FAIL: incident kinds ['none'] expected ['supplier_delay']
- FAIL: escalated although the event is actionable / noise
- FAIL: 8 affected PO(s) not moved: ['PO-0047', 'PO-0048', 'PO-0050', 'PO-0051', 'PO-0053']
- FAIL: dealer set: extra [], missing ['D02', 'D03', 'D04', 'D06', 'D07']
- FAIL: loaners: extra [], missing ['CO-00152', 'CO-00153', 'CO-00154', 'CO-00155', 'CO-00161']
- warn: only 0 kind(s) of write action (handbook rule 9 wants 3)

### H2-088 — noise — PASS
> Dealer Montgomery asks for the updated accessory price sheets.
- Read as: `noise` (reader: rules)
- Stats: {"writes": 0, "calls": 0}

### H2-089 — compound — PASS
> Reminder: submit March expense reports through the finance portal. Also, heads up: we're losing the Lexington plant for 3/29 through Thu 1 April (a cyberattack on the line controllers).
- Read as: `plant_outage` (reader: qwen3:0.6b)
- Stats: {"writes": 67, "calls": 67, "moved": 12, "rescheduled": 2, "transferred": 10, "expected_moves": 12, "dealers": 36, "loaners": 19, "lots": [], "stop_sale_vins": 0, "owners": 0}

### H2-090 — noise — PASS
> Heavy rain expected in Seattle, WA through Wednesday.
- Read as: `noise` (reader: qwen3:0.6b)
- Stats: {"writes": 0, "calls": 0}

### H2-091 — noise — PASS
> Dealer Asheville asks for the updated accessory price sheets.
- Read as: `noise` (reader: qwen3:0.6b)
- Stats: {"writes": 0, "calls": 0}

### H2-092 — plant_outage — PASS
> Wacky Wheels Jackson is idle on Tuesday the 30th because of a transformer fire.
- Read as: `plant_outage` (reader: rules)
- Stats: {"writes": 27, "calls": 27, "moved": 3, "rescheduled": 3, "transferred": 0, "expected_moves": 3, "dealers": 19, "loaners": 5, "lots": [], "stop_sale_vins": 0, "owners": 0}

### H2-093 — plant_outage — PASS
> the Princeon plant is idle on Tue 30 March because of a conveyor motor burnout.
- Read as: `plant_outage` (reader: rules)
- Stats: {"writes": 31, "calls": 31, "moved": 3, "rescheduled": 3, "transferred": 0, "expected_moves": 3, "dealers": 21, "loaners": 7, "lots": [], "stop_sale_vins": 0, "owners": 0}

### H2-094 — plant_outage — PASS
> the Alabama plant: no builds 3/17 (a cyberattack on the line controllers), resuming the next working day.
- Read as: `plant_outage` (reader: rules)
- Stats: {"writes": 27, "calls": 27, "moved": 3, "rescheduled": 3, "transferred": 0, "expected_moves": 3, "dealers": 18, "loaners": 6, "lots": [], "stop_sale_vins": 0, "owners": 0}

### H2-095 — quality_hold — PASS
> QA hold: lot LOT-0176 (60 kWh battery packs from SUP-09) used at the Indiana plant, builds Thursday the 4th to March 5th. Issue: brittle plastic clips.
- Read as: `quality_hold` (reader: qwen3:0.6b)
- Stats: {"writes": 56, "calls": 56, "moved": 0, "rescheduled": 0, "transferred": 0, "expected_moves": 0, "dealers": 0, "loaners": 0, "lots": ["LOT-0176"], "stop_sale_vins": 23, "owners": 40}

### H2-096 — quality_hold — FAIL
> Please quarantine LOT-0075: seal leaks in HARN-A. the Kentucky plant builds March 2nd through 3/3.
- Read as: `noise` (reader: rules)
- Stats: {"writes": 0, "calls": 0, "moved": 0, "rescheduled": 0, "transferred": 0, "expected_moves": 0, "dealers": 0, "loaners": 0, "lots": [], "stop_sale_vins": 0, "owners": 0}
- FAIL: incident kinds ['none'] expected ['quality_hold']
- FAIL: lots held [] expected ['LOT-0075']
- FAIL: stop-sale VINs: got 0 expected 26 (extra [], missing ['AUR0001425', 'AUR0001428', 'AUR0001430'])
- FAIL: owners notified: got 0 expected 35 (extra [], missing ['C0110', 'C0157', 'C0663'])
- warn: only 0 kind(s) of write action (handbook rule 9 wants 3)

### H2-097 — unconfirmed — FAIL
> Unclear reports that a supplier may miss deliveries next month.
- Read as: `noise` (reader: rules)
- Stats: {"writes": 0, "calls": 0}
- FAIL: expected an escalate, none made

### H2-098 — supplier_delay — FAIL
> Per Kestrel, infotainment chips for P_AL got pushed out a few days: 22 Mar -> 26 Mar.
- Read as: `unconfirmed` (reader: rules)
- Stats: {"writes": 0, "calls": 1, "moved": 0, "rescheduled": 0, "transferred": 0, "expected_moves": 12, "dealers": 0, "loaners": 0, "lots": [], "stop_sale_vins": 0, "owners": 0}
- FAIL: incident kinds ['none'] expected ['supplier_delay']
- FAIL: escalated although the event is actionable / noise
- FAIL: 12 affected PO(s) not moved: ['PO-0421', 'PO-0422', 'PO-0423', 'PO-0424', 'PO-0425']
- FAIL: dealer set: extra [], missing ['D01', 'D02', 'D03', 'D05', 'D06']
- FAIL: loaners: extra [], missing ['CO-02435', 'CO-02441', 'CO-02452', 'CO-02463', 'CO-02466']
- warn: only 0 kind(s) of write action (handbook rule 9 wants 3)

### H2-099 — supplier_delay — FAIL
> Wacky Wheels Jackson receiving: the HARN-A truck from Ridgeline won't show Monday the 22nd. Carrier now quoting 26 Mar.
- Read as: `quality_hold` (reader: qwen3:0.6b)
- Stats: {"writes": 0, "calls": 1, "moved": 0, "rescheduled": 0, "transferred": 0, "expected_moves": 8, "dealers": 0, "loaners": 0, "lots": [], "stop_sale_vins": 0, "owners": 0}
- FAIL: incident kinds ['quality_hold'] expected ['supplier_delay']
- FAIL: escalated although the event is actionable / noise
- FAIL: 8 affected PO(s) not moved: ['PO-0241', 'PO-0242', 'PO-0244', 'PO-0245', 'PO-0247']
- FAIL: dealer set: extra [], missing ['D02', 'D03', 'D04', 'D05', 'D06']
- FAIL: loaners: extra [], missing ['CO-01357', 'CO-01361', 'CO-01366', 'CO-01369', 'CO-01371']
- warn: only 0 kind(s) of write action (handbook rule 9 wants 3)

### H2-100 — quality_hold — FAIL
> Please quarantine LOT-0245: excess solder in BATT-60. P_AL builds Mon 22 February through 24 Feb.
- Read as: `noise` (reader: rules)
- Stats: {"writes": 0, "calls": 0, "moved": 0, "rescheduled": 0, "transferred": 0, "expected_moves": 0, "dealers": 0, "loaners": 0, "lots": [], "stop_sale_vins": 0, "owners": 0}
- FAIL: incident kinds ['none'] expected ['quality_hold']
- FAIL: lots held [] expected ['LOT-0245']
- FAIL: stop-sale VINs: got 0 expected 39 (extra [], missing ['AUR0003575', 'AUR0003578', 'AUR0003580'])
- FAIL: owners notified: got 0 expected 53 (extra [], missing ['C0051', 'C0097', 'C0358'])
- warn: only 0 kind(s) of write action (handbook rule 9 wants 3)

