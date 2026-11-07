"""Run the control tower over the event feed.

Launch from the Hitachi directory:

    python -m tower.run

Each event gets a fresh enterprise world, a fresh plant schedule, and a fresh
loaner pool. The action log matches enterprise_server.py: one JSON object per
call, with keys event_id, tool, args, and ok.
"""

from __future__ import annotations

import json
import os
import sys

_HITACHI = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _HITACHI not in sys.path:
    sys.path.insert(0, _HITACHI)

from enterprise import Enterprise, ToolError, load_events
from tower.agents.coordinator import handle_event
from tower.graph import WorldGraph


class _CallLog:
    """Record every Enterprise.call the coordinator makes."""

    def __init__(self, enterprise, records: list[dict]):
        self._enterprise = enterprise
        self._records = records

    def call(self, event_id, tool, args):
        try:
            result = self._enterprise.call(event_id, tool, args)
        except ToolError:
            self._records.append({"event_id": event_id, "tool": tool, "args": args, "ok": False})
            raise
        self._records.append({"event_id": event_id, "tool": tool, "args": args, "ok": True})
        return result


def run_all() -> None:
    graph = WorldGraph()
    enterprise = Enterprise(graph.data_dir)
    events = load_events(os.path.join(graph.data_dir, "events.json"))
    records: list[dict] = []
    logged = _CallLog(enterprise, records)
    traces = [handle_event(graph, logged, event) for event in events]

    out_dir = os.path.join(_HITACHI, "runs", "run1")
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, "action_log.jsonl"), "w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record) + "\n")
    with open(os.path.join(out_dir, "traces.json"), "w", encoding="utf-8") as handle:
        json.dump([trace.to_dict() for trace in traces], handle, indent=2)
        handle.write("\n")


if __name__ == "__main__":
    run_all()
