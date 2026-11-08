"""Run the control tower over the event feed.

Launch from the Hitachi directory:

    python -m tower.run                 # local LLM via Ollama (default qwen3:0.6b)
    python -m tower.run --reader rules  # deterministic reader only

Each event gets a fresh enterprise world, a fresh plant schedule, and a fresh
loaner pool. The action log matches enterprise_server.py: one JSON object per
call, with keys event_id, tool, args, and ok.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.request

_HITACHI = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _HITACHI not in sys.path:
    sys.path.insert(0, _HITACHI)

from enterprise import Enterprise, ToolError, load_events
from tower.agents.coordinator import handle_event
from tower.agents.llm_reader import MODEL, OLLAMA_URL, LLMReader
from tower.graph import WorldGraph


# Wraps Enterprise so every call is also written to the action log, in the same format
# enterprise_server.py uses (event_id, tool, args, ok).
class _CallLog:
    """Record every Enterprise.call the coordinator makes."""

    # records is shared with the caller, which writes it to disk once every event is done.
    def __init__(self, enterprise, records: list[dict]):
        self._enterprise = enterprise
        self._records = records

    def call(self, event_id, tool, args):
        """Forward to Enterprise.call and log the outcome. A ToolError is logged as ok=False and
        re-raised, so the coordinator still sees the failure."""
        try:
            result = self._enterprise.call(event_id, tool, args)
        except ToolError:
            self._records.append({"event_id": event_id, "tool": tool, "args": args, "ok": False})
            raise
        self._records.append({"event_id": event_id, "tool": tool, "args": args, "ok": True})
        return result


# Stop before the run if Ollama or the model is missing, rather than silently running rules-only.
def _require_model(model: str, url: str) -> None:
    """Fail loudly rather than quietly run without the model."""
    try:
        with urllib.request.urlopen(f"{url}/api/tags", timeout=5) as response:
            names = {m["name"] for m in json.loads(response.read())["models"]}
    except OSError as exc:
        sys.exit(f"Ollama is not reachable at {url} ({exc}). Start it, or pass --reader rules.")
    if model not in names and f"{model}:latest" not in names:
        sys.exit(f"Model {model} is not pulled. Run: ollama pull {model}")


# Main loop: load the graph and tools once, then send each event through the coordinator.
# Enterprise keeps a separate world per event_id, so events never affect each other.
def run_all(reader: str = "llm", out_dir: str | None = None, events_path: str | None = None,
            notify: str = "off") -> None:
    llm = None
    if reader == "llm":
        _require_model(MODEL, OLLAMA_URL)
        llm = LLMReader()
    graph = WorldGraph()
    enterprise = Enterprise(graph.data_dir)
    events = load_events(events_path or os.path.join(graph.data_dir, "events.json"))
    records: list[dict] = []
    logged = _CallLog(enterprise, records)
    # The whole pipeline for one event happens inside handle_event (agents/coordinator.py).
    traces = [handle_event(graph, logged, event, llm) for event in events]

    out_dir = out_dir or os.path.join(_HITACHI, "runs", "run1")
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, "action_log.jsonl"), "w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record) + "\n")
    with open(os.path.join(out_dir, "traces.json"), "w", encoding="utf-8") as handle:
        json.dump([trace.to_dict() for trace in traces], handle, indent=2)
        handle.write("\n")

    readers = [incident.reader for trace in traces for incident in trace.incidents]
    used = sum(r != "rules" for r in readers)
    print(f"{len(events)} events, {len(records)} tool calls -> {out_dir}")
    if llm is not None:
        print(f"{llm.model}: {llm.calls} calls; verified on {used} of {len(readers)} incidents, "
              f"rule reader used on {len(readers) - used}")
    # Channels run after the log is written and read only the run's files, so the scored
    # action log is identical whatever --notify says.
    if notify != "off":
        from tower.channels.dispatch import notify_run, summarize
        outbox = notify_run(out_dir, graph.data_dir, notify)
        print(f"channels ({notify}): {summarize(outbox)} -> {os.path.join(out_dir, 'outbox.jsonl')}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--reader", choices=("llm", "rules"), default="llm")
    parser.add_argument("--out", help="output directory (default runs/run1)")
    parser.add_argument("--events", help="event feed JSON (default the package events.json)")
    parser.add_argument("--notify", choices=("off", "dry-run", "send"), default="off",
                        help="deliver results through tower/channels (Slack, Teams, Gmail, Outlook...)")
    cli = parser.parse_args()
    run_all(cli.reader, cli.out, cli.events, cli.notify)
