"""Run the control tower over the event feed.

Launch from the Hitachi directory:

    python -m tower.run --out runs/scratch

Like enterprise_server.py, it refuses to replace a log that already has calls
unless --overwrite is given. Keep practice runs out of runs/run1.

Each event gets a fresh enterprise world, a fresh plant schedule, and a fresh
loaner pool. The action log matches enterprise_server.py: one JSON object per
call, with keys event_id, tool, args, and ok.
"""

from __future__ import annotations

import argparse
import json
import os
import sys

_HITACHI = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _HITACHI not in sys.path:
    sys.path.insert(0, _HITACHI)

from enterprise import Enterprise, ToolError, load_events
from tower.agents.coordinator import handle_event
from tower.graph import WorldGraph


def _release_event_state(enterprise, event_id: str) -> None:
    """Drop this event's slot map once its calls are logged.

    Each event keeps a copy of every future order. A long feed would hold
    one copy per event for the rest of the run.
    """
    state = getattr(enterprise, "_state", None)
    if isinstance(state, dict):
        state.pop(event_id, None)


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


def run_all(out_dir: str | None = None, overwrite: bool = False) -> str:
    out_dir = os.path.abspath(out_dir or os.path.join(_HITACHI, "runs", "run1"))
    log_path = os.path.join(out_dir, "action_log.jsonl")
    if os.path.exists(log_path) and os.path.getsize(log_path) and not overwrite:
        raise SystemExit(f"{log_path} already has calls. Use --overwrite or another --out.")

    graph = WorldGraph()
    enterprise = Enterprise(graph.data_dir)
    events = load_events(os.path.join(graph.data_dir, "events.json"))
    records: list[dict] = []
    logged = _CallLog(enterprise, records)
    traces = []
    for event in events:
        try:
            traces.append(handle_event(graph, logged, event))
        finally:
            _release_event_state(enterprise, event["event_id"])

    os.makedirs(out_dir, exist_ok=True)
    with open(log_path, "w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record) + "\n")
    with open(os.path.join(out_dir, "traces.json"), "w", encoding="utf-8") as handle:
        json.dump([trace.to_dict() for trace in traces], handle, separators=(",", ":"))
        handle.write("\n")
    return out_dir


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Run the control tower over the event feed.")
    parser.add_argument("--out", default=None, help="output folder (default runs/run1)")
    parser.add_argument("--overwrite", action="store_true", help="replace an existing action_log.jsonl")
    args = parser.parse_args(argv)
    print(run_all(args.out, args.overwrite))


if __name__ == "__main__":
    main()
