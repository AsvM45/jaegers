# Hitachi control tower — accuracy paraphrases

23 cases from `tests/accuracy_cases.json`, graded by `tests/run_cases.py` against expected effects computed from the CSVs (not from tower/graph.py).

| Case | Category | rules | Edge case? |
|---|---|---|---|
| A-001 | plant_outage | PASS |  |
| A-002 | plant_outage | PASS |  |
| A-003 | plant_outage | PASS |  |
| A-004 | supplier_delay | PASS |  |
| A-005 | supplier_delay | PASS |  |
| A-006 | quality_hold | PASS |  |
| A-007 | quality_hold | PASS |  |
| A-008 | compound | PASS |  |
| A-009 | compound | PASS |  |
| A-010 | unconfirmed | PASS |  |
| A-011 | noise | PASS |  |
| A-012 | noise | PASS |  |
| A-013 | noise | PASS |  |
| A-014 | noise | PASS |  |
| A-015 | noise | PASS |  |
| A-016 | plant_outage | PASS |  |
| A-017 | plant_outage | PASS |  |
| A-018 | plant_outage | PASS |  |
| A-019 | supplier_delay | PASS |  |
| A-020 | quality_hold | PASS |  |
| A-021 | compound | PASS |  |
| A-022 | compound | PASS |  |
| A-023 | compound | PASS |  |

**rules**: 23/23 pass

## Details — rules reader

### A-001 — plant_outage — PASS
> The San Antonio plant will not run from March 16 through March 18.
- Read as: `plant_outage` (reader: rules)
- Stats: {"writes": 59, "calls": 59, "moved": 9, "rescheduled": 9, "transferred": 0, "expected_moves": 9, "dealers": 34, "loaners": 16, "lots": [], "stop_sale_vins": 0, "owners": 0}

### A-002 — plant_outage — PASS
> Lexington is closed for maintenance from March 16 to March 18.
- Read as: `plant_outage` (reader: rules)
- Stats: {"writes": 59, "calls": 59, "moved": 9, "rescheduled": 9, "transferred": 0, "expected_moves": 9, "dealers": 32, "loaners": 18, "lots": [], "stop_sale_vins": 0, "owners": 0}

### A-003 — plant_outage — PASS
> Assembly at Huntsville stops March 16 through March 18.
- Read as: `plant_outage` (reader: rules)
- Stats: {"writes": 66, "calls": 66, "moved": 9, "rescheduled": 9, "transferred": 0, "expected_moves": 9, "dealers": 32, "loaners": 25, "lots": [], "stop_sale_vins": 0, "owners": 0}

### A-004 — supplier_delay — PASS
> The airbag module delivery from SUP-17 to San Antonio has been moved from March 15 to March 18.
- Read as: `supplier_delay` (reader: rules)
- Stats: {"writes": 65, "calls": 65, "moved": 9, "rescheduled": 9, "transferred": 0, "expected_moves": 9, "dealers": 37, "loaners": 19, "lots": [], "stop_sale_vins": 0, "owners": 0}

### A-005 — supplier_delay — PASS
> San Antonio receiving: airbag modules from SUP-17, was March 15, now March 18.
- Read as: `supplier_delay` (reader: rules)
- Stats: {"writes": 65, "calls": 65, "moved": 9, "rescheduled": 9, "transferred": 0, "expected_moves": 9, "dealers": 37, "loaners": 19, "lots": [], "stop_sale_vins": 0, "owners": 0}

### A-006 — quality_hold — PASS
> Containment notice: scrap LOT-0001, airbag modules, San Antonio, builds February 22 to February 24.
- Read as: `quality_hold` (reader: rules)
- Stats: {"writes": 184, "calls": 184, "moved": 0, "rescheduled": 0, "transferred": 0, "expected_moves": 0, "dealers": 0, "loaners": 0, "lots": ["LOT-0001"], "stop_sale_vins": 127, "owners": 141}

### A-007 — quality_hold — PASS
> Stop using lot LOT-0001 (airbag module, San Antonio). Builds February 22 through February 24.
- Read as: `quality_hold` (reader: rules)
- Stats: {"writes": 184, "calls": 184, "moved": 0, "rescheduled": 0, "transferred": 0, "expected_moves": 0, "dealers": 0, "loaners": 0, "lots": ["LOT-0001"], "stop_sale_vins": 127, "owners": 141}

### A-008 — compound — PASS
> 1. Lexington is down March 16 through March 18. 2. Voicemail from SUP-17: the airbag module order headed to San Antonio is rescheduled from March 15 to March 19.
- Read as: `plant_outage+supplier_delay` (reader: rules, rules)
- Stats: {"writes": 100, "calls": 100, "moved": 21, "rescheduled": 21, "transferred": 0, "expected_moves": 21, "dealers": 44, "loaners": 35, "lots": [], "stop_sale_vins": 0, "owners": 0}

### A-009 — compound — PASS
> - Lexington is down March 16 through March 18. - Voicemail from SUP-17: the airbag module order headed to San Antonio is rescheduled from March 15 to March 19.
- Read as: `plant_outage+supplier_delay` (reader: rules, rules)
- Stats: {"writes": 100, "calls": 100, "moved": 21, "rescheduled": 21, "transferred": 0, "expected_moves": 21, "dealers": 44, "loaners": 35, "lots": [], "stop_sale_vins": 0, "owners": 0}

### A-010 — unconfirmed — PASS
> Someone mentioned Lexington might be down next week. Nothing confirmed.
- Read as: `unconfirmed` (reader: rules)
- Stats: {"writes": 0, "calls": 1}

### A-011 — noise — PASS
> The plant tour will not run at San Antonio from March 16 through March 18.
- Read as: `noise` (reader: rules)
- Stats: {"writes": 0, "calls": 0}

### A-012 — noise — PASS
> Please scrap the old brochure. The San Antonio picnic is March 16 and March 17.
- Read as: `noise` (reader: rules)
- Stats: {"writes": 0, "calls": 0}

### A-013 — noise — PASS
> Lexington is not down from March 16 through March 18.
- Read as: `noise` (reader: rules)
- Stats: {"writes": 0, "calls": 0}

### A-014 — noise — PASS
> The quality hold on LOT-0001 is lifted.
- Read as: `noise` (reader: rules)
- Stats: {"writes": 0, "calls": 0}

### A-015 — noise — PASS
> The cafeteria line is closed at Lexington from March 16 through March 18.
- Read as: `noise` (reader: rules)
- Stats: {"writes": 0, "calls": 0}

### A-016 — plant_outage — PASS
> San Antonio is not running from March 16 through March 18.
- Read as: `plant_outage` (reader: rules)
- Stats: {"writes": 59, "calls": 59, "moved": 9, "rescheduled": 9, "transferred": 0, "expected_moves": 9, "dealers": 34, "loaners": 16, "lots": [], "stop_sale_vins": 0, "owners": 0}

### A-017 — plant_outage — PASS
> Lexington will be closed from March 16 to March 18.
- Read as: `plant_outage` (reader: rules)
- Stats: {"writes": 59, "calls": 59, "moved": 9, "rescheduled": 9, "transferred": 0, "expected_moves": 9, "dealers": 32, "loaners": 18, "lots": [], "stop_sale_vins": 0, "owners": 0}

### A-018 — plant_outage — PASS
> Production at Princeton is cancelled from March 16 to March 18.
- Read as: `plant_outage` (reader: rules)
- Stats: {"writes": 66, "calls": 66, "moved": 9, "rescheduled": 9, "transferred": 0, "expected_moves": 9, "dealers": 31, "loaners": 26, "lots": [], "stop_sale_vins": 0, "owners": 0}

### A-019 — supplier_delay — PASS
> Airbag modules for San Antonio arrive March 18 instead of March 15.
- Read as: `supplier_delay` (reader: rules)
- Stats: {"writes": 65, "calls": 65, "moved": 9, "rescheduled": 9, "transferred": 0, "expected_moves": 9, "dealers": 37, "loaners": 19, "lots": [], "stop_sale_vins": 0, "owners": 0}

### A-020 — quality_hold — PASS
> Don't use LOT-0001.
- Read as: `quality_hold` (reader: rules)
- Stats: {"writes": 184, "calls": 184, "moved": 0, "rescheduled": 0, "transferred": 0, "expected_moves": 0, "dealers": 0, "loaners": 0, "lots": ["LOT-0001"], "stop_sale_vins": 127, "owners": 141}

### A-021 — compound — PASS
> Firstly, Lexington is down March 16 through March 18. Secondly, the airbag module order to San Antonio is rescheduled from March 15 to March 19.
- Read as: `plant_outage+supplier_delay` (reader: rules, rules)
- Stats: {"writes": 100, "calls": 100, "moved": 21, "rescheduled": 21, "transferred": 0, "expected_moves": 21, "dealers": 44, "loaners": 35, "lots": [], "stop_sale_vins": 0, "owners": 0}

### A-022 — compound — PASS
> Lexington is down March 16 through March 18; the airbag module delivery to San Antonio has been moved from March 15 to March 18.
- Read as: `plant_outage+supplier_delay` (reader: rules, rules)
- Stats: {"writes": 95, "calls": 95, "moved": 18, "rescheduled": 18, "transferred": 0, "expected_moves": 18, "dealers": 44, "loaners": 33, "lots": [], "stop_sale_vins": 0, "owners": 0}

### A-023 — compound — PASS
> Lexington is down March 16 through March 18 and San Antonio is down March 23 through March 25.
- Read as: `plant_outage+plant_outage` (reader: rules, rules)
- Stats: {"writes": 94, "calls": 94, "moved": 18, "rescheduled": 18, "transferred": 0, "expected_moves": 18, "dealers": 41, "loaners": 35, "lots": [], "stop_sale_vins": 0, "owners": 0}

