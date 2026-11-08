# Adversarial findings

The six failures from the first run are fixed. The suite is `tower/tests/test_adversarial.py`.

## Fixed

- An explicit "not confirmed" outage or delay is `escalate` and nothing else.
- Labeled ETAs bind "original drop" and "new ETA" even when the new date is written first. An inverted window is unconfirmed.
- "March 32" is skipped. It does not raise out of `handle_event`.
- A quality bulletin that only names a known lot holds that lot and copies plant, part, supplier, and build dates from the lot row.
- A transfer does not land inside another plant's outage.
- Hearsay ("not confirmed", "nothing confirmed", "unconfirmed", "rumor", "someone mentioned", "someone on the floor", "may be off", "no dates") is classified before a quality hold, an outage, or a delay.
- Every plant dark for the whole window moves no builds and does not overfill a day. A half-window outage at every plant stays inside capacity. Forty copies of one outage move each order once.

## Still not required by the handbook tests

- A Sunday new ETA is not used as a tool date. Friday orders in that window move to Monday.
- Rule 9 (three different action kinds on every real incident) is not enforced. A past disruption with no future orders, and a quality-only hold, cannot all produce a reschedule, a dealer notice, and a loaner.
- When no legal slot remains, the affected customer orders are still notified and eligible loaners are still assigned. The unplaced production orders stay on their original day.
- Rule 3 lets a transfer land on any free day at another plant, including before the new ETA or the restart. Same-plant reschedules stay on or after that day. The stored E-09 and E-11 logs do that. Do not treat those early transfer dates as scoring errors.
