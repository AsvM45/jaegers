"""Calendar check on saved runs: no incident window may start after it ends.

    python tests/check_dates.py                    # the live feed (runs/run1) and every saved test run
    python tests/check_dates.py runs/run1          # one folder

For each incident in each traces.json it checks, with the company calendar:
  supplier delay   blocked from <= blocked until
  plant outage     outage start <= outage end
  quality hold     build start  <= build end
and flags a supplier delay whose dates fall on a weekend (the tower moves those to the next working day),
or that blocks more than 15 working days: the usual sign of a day read in the wrong month
("arriving March 31st instead of the 29th" read as April 29).
Exit code 1 when anything is out of order.
"""

from __future__ import annotations

import glob
import json
import os
import sys
from datetime import date

HITACHI = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HITACHI)

from tower.calendar_util import is_working_day  # noqa: E402

MAX_DELAY_DAYS = 15
WINDOWS = {"supplier_delay": ("blocked_from", "blocked_until"), "plant_outage": ("outage_start", "outage_end"),
           "quality_hold": ("build_start", "build_end")}


def check(path: str) -> list[str]:
    problems = []
    with open(path, encoding="utf-8") as handle:
        traces = json.load(handle)
    for trace in traces:
        for inc in trace.get("incidents", []):
            keys = WINDOWS.get(inc.get("kind"))
            if not keys or not inc.get(keys[0]) or not inc.get(keys[1]):
                continue
            start, end = date.fromisoformat(inc[keys[0]]), date.fromisoformat(inc[keys[1]])
            where = f"{os.path.relpath(path, HITACHI)} {trace.get('event_id')} {inc['kind']}"
            if start > end:
                problems.append(f"{where}: {keys[0]} {start} is after {keys[1]} {end}")
            if inc["kind"] == "supplier_delay":
                for key, day in zip(keys, (start, end)):
                    if not is_working_day(day):
                        problems.append(f"{where}: {key} {day} is a weekend")
                working = sum(is_working_day(date.fromordinal(o)) for o in range(start.toordinal(), end.toordinal()))
                if working > MAX_DELAY_DAYS:
                    problems.append(f"{where}: blocks {working} working days ({start} to {end}); check the dates")
    return problems


def main() -> int:
    folders = sys.argv[1:] or ["runs/run1", *sorted(glob.glob("runs/*/*/")), "runs/submission"]
    files = []
    for folder in folders:
        path = os.path.join(HITACHI, folder, "traces.json")
        if os.path.isfile(path):
            files.append(path)
    problems, incidents = [], 0
    for path in files:
        problems += check(path)
        with open(path, encoding="utf-8") as handle:
            incidents += sum(len(t.get("incidents", [])) for t in json.load(handle))
    for p in problems:
        print("✗", p)
    print(f"{len(files)} runs, {incidents} incidents checked: "
          + ("every window is in order." if not problems else f"{len(problems)} problems."))
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
