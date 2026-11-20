"""Run the blind set (tests/blind_cases.json) through the whole tower and grade it.

    python tests/run_blind.py                  # the model, rule reader as backup (as the tower runs)
    python tests/run_blind.py --reader rules   # deterministic reader only
    python tests/run_blind.py --reader both

Each case goes through handle_event exactly like a live event: reading, specialists, gateway and
tool calls. Effects are graded by tests/run_cases.py's independent CSV grader against the answer
keys code wrote when it picked each scenario (tests/make_blind.py). Nobody tunes on this set.

Output: runs/blind/<reader>/ (shown on the dashboard's Tests page)
"""

from __future__ import annotations

import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
HITACHI = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, HITACHI)

import run_cases as rc  # noqa: E402
from tower.graph import WorldGraph  # noqa: E402

# The two blind sets: the 40 (B-001 to B-040) and the 100 (N-001 to N-100). Nobody tunes on the 100.
SETS = {"40": ("blind_cases.json", "blind"), "100": ("blind100_cases.json", "blind100")}
OUT = os.path.join(HITACHI, "runs", "blind")
CASES = os.path.join(HERE, "blind_cases.json")


def load_cases(limit: int | None = None) -> list[dict]:
    with open(CASES, encoding="utf-8") as handle:
        data = json.load(handle)
    cases = data["cases"] if isinstance(data, dict) else data
    return cases[:limit]


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--reader", choices=("rules", "llm", "both"), default="llm")
    ap.add_argument("--limit", type=int, help="only the first N cases")
    ap.add_argument("--set", choices=SETS, default="40", help="which blind set: the 40 or the 100")
    args = ap.parse_args()
    global CASES, OUT
    CASES = os.path.join(HERE, SETS[args.set][0])
    OUT = os.path.join(HITACHI, "runs", SETS[args.set][1])
    rc.OUT = OUT  # rc.run writes each reader's log, traces and results under runs/<set>/
    cases = load_cases(args.limit)
    truth, graph = rc.Truth(), WorldGraph()
    readers = ["rules", "llm"] if args.reader == "both" else [args.reader]
    for reader in readers:
        results = rc.run(reader, cases, truth, graph)
        passed = sum(r["verdict"] == "PASS" for r in results)
        print(f"{reader}: {passed}/{len(results)} blind cases pass ({args.set}-case set)")


if __name__ == "__main__":
    main()
