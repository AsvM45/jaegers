"""Run the control tower over the event feed.

Launch from the Hitachi directory:

    python -m tower.run                 # local LLM via Ollama (default qwen2.5:0.5b)
    python -m tower.run --reader rules  # deterministic reader only
    python -m tower.run --server http://127.0.0.1:8000   # official path: GET /events, POST /act

    python -m tower.run --out runs/scratch   # a practice run that leaves runs/run1 alone

With --server, every tool call goes over HTTP to enterprise_server.py, which writes
the scored action_log.jsonl itself; this script then writes only traces.json.

Like enterprise_server.py, it refuses to replace a log that already has calls unless
--overwrite is given (start.py passes it: that command exists to regenerate the run).

Each event gets a fresh enterprise world, a fresh plant schedule, and a fresh
loaner pool. The action log matches enterprise_server.py: one JSON object per
call, with keys event_id, tool, args, and ok.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
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


# The docx's MCP-style path: the same .call() interface, but each call is a POST /act to
# enterprise_server.py. A 4xx answer becomes the ToolError the coordinator already handles.
class _ServerTools:
    """Enterprise tools reached over HTTP instead of in-process."""

    def __init__(self, url: str):
        self.url = url.rstrip("/")

    def events(self) -> list[dict]:
        with urllib.request.urlopen(f"{self.url}/events", timeout=30) as response:
            return json.loads(response.read())

    def call(self, event_id, tool, args):
        body = json.dumps({"event_id": event_id, "tool": tool, "args": args}).encode("utf-8")
        request = urllib.request.Request(
            f"{self.url}/act", data=body, headers={"Content-Type": "application/json"}
        )
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                return json.loads(response.read())
        except urllib.error.HTTPError as exc:
            try:
                message = json.loads(exc.read() or b"{}").get("error")
            except ValueError:
                message = None
            raise ToolError(message or f"HTTP {exc.code} from {self.url}/act") from exc
        except (urllib.error.URLError, TimeoutError, ConnectionError) as exc:
            # The server is down, the connection dropped, or the call timed out. Treat it like any
            # other failed call (recorded, not retried, the rest still run) instead of ending the run.
            reason = getattr(exc, "reason", exc)
            raise ToolError(f"no answer from {self.url}/act ({reason})") from exc


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
def _release_event_state(enterprise, event_id: str) -> None:
    """Drop this event's slot map once its calls are logged.

    Each event keeps a copy of every future order. A long feed would hold one copy per event
    for the rest of the run.
    """
    state = getattr(enterprise, "_state", None)
    if isinstance(state, dict):
        state.pop(event_id, None)


def run_all(reader: str = "llm", out_dir: str | None = None, events_path: str | None = None,
            notify: str = "off", server: str | None = None, overwrite: bool = False) -> str:
    out_dir = os.path.abspath(out_dir or os.path.join(_HITACHI, "runs", "run1"))
    log_path = os.path.join(out_dir, "action_log.jsonl")
    # runs/submission is the frozen, verified run we hand in. Nothing writes there, --overwrite or not.
    if os.path.realpath(out_dir) == os.path.realpath(os.path.join(_HITACHI, "runs", "submission")):
        raise SystemExit("runs/submission is the frozen submission and is never overwritten. Use another --out.")
    if not server and os.path.exists(log_path) and os.path.getsize(log_path) and not overwrite:
        raise SystemExit(f"{log_path} already has calls. Use --overwrite or another --out.")
    llm = None
    if reader == "llm":
        _require_model(MODEL, OLLAMA_URL)
        llm = LLMReader()
    graph = WorldGraph()
    if server:
        enterprise = _ServerTools(server)
        events = enterprise.events()
    else:
        enterprise = Enterprise(graph.data_dir)
        events = load_events(events_path or os.path.join(graph.data_dir, "events.json"))
    records: list[dict] = []
    logged = _CallLog(enterprise, records)
    # The whole pipeline for one event happens inside handle_event (agents/coordinator.py).
    traces = []
    for event in events:
        try:
            traces.append(handle_event(graph, logged, event, llm))
        finally:
            _release_event_state(enterprise, event["event_id"])

    os.makedirs(out_dir, exist_ok=True)
    # Through the server, the server's own log is the scored file; do not write a second one.
    if not server:
        with open(log_path, "w", encoding="utf-8") as handle:
            for record in records:
                handle.write(json.dumps(record) + "\n")
    with open(os.path.join(out_dir, "traces.json"), "w", encoding="utf-8") as handle:
        json.dump([trace.to_dict() for trace in traces], handle, separators=(",", ":"))
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
    return out_dir


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--reader", choices=("llm", "rules"), default="llm")
    parser.add_argument("--out", help="output directory (default runs/run1)")
    parser.add_argument("--events", help="event feed JSON (default the package events.json)")
    parser.add_argument("--notify", choices=("off", "dry-run", "send"), default="off",
                        help="deliver results through tower/channels (Slack, Teams, Gmail, Outlook...)")
    parser.add_argument("--server", help="enterprise_server.py URL, e.g. http://127.0.0.1:8000")
    parser.add_argument("--overwrite", action="store_true", help="replace an existing action_log.jsonl")
    cli = parser.parse_args(argv)
    run_all(cli.reader, cli.out, cli.events, cli.notify, cli.server, cli.overwrite)


if __name__ == "__main__":
    main()
