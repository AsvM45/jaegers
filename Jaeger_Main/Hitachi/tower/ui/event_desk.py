"""Event run and event add for the dashboard.

Event run walks the 15 given events, then any event added from the chat, and reports each one
as it finishes. It does not replace runs/run1.

Event add takes one chat message, reads it with the model (rule reader as the backup when
Ollama is not running), and keeps the event beside
the official feed. The official events.json is never written.
"""

from __future__ import annotations

import json
import os
import threading
from collections import deque
from datetime import datetime, timedelta

HERE = os.path.dirname(os.path.abspath(__file__))
HITACHI = os.path.abspath(os.path.join(HERE, "..", ".."))
OFFICIAL = os.path.join(HITACHI, "Data", "hack_the_highway_package", "data", "events.json")
DESK = os.path.join(HITACHI, "runs", "desk")
EVENTS_PATH = os.path.join(DESK, "events.json")
TRACES_PATH = os.path.join(DESK, "traces.json")
LOG_PATH = os.path.join(DESK, "action_log.jsonl")
CHAT_PATH = os.path.join(DESK, "chat.json")

_files = threading.Lock()
_lock = threading.Condition()
_graph = None
_seq = 0
_deltas: deque[tuple[int, dict]] = deque(maxlen=4000)
_running = False
_cancel = False
_current: str | None = None
_done = 0
_total = 0
_error: str | None = None
_seen: list[dict] = []


def stamp_paths() -> list[str]:
    return [EVENTS_PATH, TRACES_PATH, LOG_PATH, CHAT_PATH]


def _read(path: str, fallback):
    if not os.path.isfile(path):
        return fallback
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def _write(path: str, payload) -> None:
    os.makedirs(DESK, exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2)
        handle.write("\n")
    os.replace(tmp, path)


def saved_events() -> list[dict]:
    with _files:
        data = _read(EVENTS_PATH, [])
    return list(data) if isinstance(data, list) else []


def saved_traces() -> list[dict]:
    with _files:
        data = _read(TRACES_PATH, [])
    return list(data) if isinstance(data, list) else []


def saved_log() -> list[dict]:
    if not os.path.isfile(LOG_PATH):
        return []
    rows = []
    with open(LOG_PATH, encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def messages() -> list[dict]:
    with _files:
        data = _read(CHAT_PATH, [])
    return list(data) if isinstance(data, list) else []


def _graph_once():
    global _graph
    if _graph is None:
        from tower.graph import WorldGraph

        _graph = WorldGraph()
    return _graph


def _official() -> list[dict]:
    with open(OFFICIAL, encoding="utf-8") as handle:
        data = json.load(handle)
    events = data["events"] if isinstance(data, dict) else data
    return [e for e in events if isinstance(e, dict) and e.get("event_id")]


def _outcome(records: list[dict]) -> str:
    from tower.contracts import WRITE_TOOLS

    if any(row.get("ok") and row.get("tool") in WRITE_TOOLS for row in records):
        return "acted"
    if any(row.get("tool") == "escalate" for row in records):
        return "escalated"
    return "no action"


_LLM = None


def _reader():
    """The same model-first reader the tower uses. If Ollama is down, each read falls back to the
    rule reader inside tower.agents.understand, so the desk still works offline."""
    global _LLM
    if _LLM is None:
        from tower.agents.llm_reader import LLMReader
        _LLM = LLMReader()
    return _LLM


def _handle(event: dict) -> tuple[dict, list[dict]]:
    from enterprise import Enterprise
    from tower.agents.coordinator import handle_event
    from tower.run import _CallLog, _release_event_state

    enterprise = Enterprise(_graph_once().data_dir)
    records: list[dict] = []
    logged = _CallLog(enterprise, records)
    try:
        trace = handle_event(_graph_once(), logged, event, _reader())
    finally:
        _release_event_state(enterprise, event["event_id"])
    return trace.to_dict(), records


def _append_saved(event: dict, trace: dict, records: list[dict], reply: str) -> None:
    with _files:
        events = _read(EVENTS_PATH, [])
        traces = _read(TRACES_PATH, [])
        chat = _read(CHAT_PATH, [])
        if not isinstance(events, list):
            events = []
        if not isinstance(traces, list):
            traces = []
        if not isinstance(chat, list):
            chat = []
        events.append(event)
        traces.append(trace)
        chat.append({"role": "user", "text": event["text"], "at": event["received_at"]})
        chat.append({"role": "tower", "text": reply, "event_id": event["event_id"], "at": event["received_at"]})
        _write(EVENTS_PATH, events)
        _write(TRACES_PATH, traces)
        _write(CHAT_PATH, chat[-200:])
        with open(LOG_PATH, "a", encoding="utf-8") as handle:
            for record in records:
                handle.write(json.dumps(record) + "\n")


def add_message(text: str) -> dict:
    """Read one chat message as a new event. ValueError is a bad message."""
    if not isinstance(text, str):
        raise ValueError("text is required")
    text = text.strip()
    if not text or len(text) > 4000:
        raise ValueError("text must be 1 to 4000 characters")
    if any(ord(ch) < 32 and ch not in "\n\t" for ch in text):
        raise ValueError("text has unsupported characters")
    with _files:
        existing = _read(EVENTS_PATH, [])
        taken = {e.get("event_id") for e in existing} if isinstance(existing, list) else set()
    number = 1
    while f"A-{number:03d}" in taken:
        number += 1
        if number > 999:
            raise ValueError("too many added events")
    event = {
        "event_id": f"A-{number:03d}",
        "received_at": (datetime(2027, 3, 8, 12, 0, 0) + timedelta(minutes=number)).isoformat(timespec="seconds"),
        "source": "ops chat",
        "text": text,
    }
    trace, records = _handle(event)
    reply = f"Added {event['event_id']}. {trace.get('summary') or 'Read.'}"
    _append_saved(event, trace, records, reply)
    return {
        "event": event,
        "reply": reply,
        "classification": trace.get("classification") or "",
        "outcome": _outcome(records),
    }


def _snapshot() -> dict:
    """Caller holds _lock."""
    return {
        "seq": _seq,
        "running": _running,
        "current": _current,
        "done": _done,
        "total": _total,
        "error": _error,
        "events": list(_seen),
    }


def status() -> dict:
    with _lock:
        return _snapshot()


def _emit(event: dict) -> None:
    """Caller holds _lock."""
    global _seq
    _seq += 1
    event = dict(event)
    event["seq"] = _seq
    if event.get("type") == "reset":
        event["job"] = _snapshot()
    _deltas.append((_seq, event))
    _lock.notify_all()


def start() -> dict:
    """Walk the feed. error=already running is a 409."""
    global _running, _cancel, _current, _done, _total, _error, _seen
    events = _official() + saved_events()
    with _lock:
        if _running:
            return {"error": "An event run is already going"}
        _running = True
        _cancel = False
        _current = None
        _done = 0
        _total = len(events)
        _error = None
        _seen = []
        _emit({"type": "reset"})
        total = _total
    threading.Thread(target=_worker, args=(events,), name="tower-event-run", daemon=True).start()
    return {"started": True, "total": total}


def stop() -> dict:
    global _cancel
    with _lock:
        _cancel = True
        return _snapshot()


def follow():
    """Yield ('state', snapshot) once, then ('update', event) and pings."""
    with _lock:
        seq = _seq
        snap = _snapshot()
    yield "state", snap
    while True:
        with _lock:
            if _seq == seq:
                _lock.wait(timeout=15)
            fresh = [(n, ev) for n, ev in _deltas if n > seq]
            if fresh:
                seq = fresh[-1][0]
        if not fresh:
            yield "ping", {"seq": seq}
            continue
        for _n, ev in fresh:
            yield "update", ev


def _worker(events: list[dict]) -> None:
    global _running, _current, _done, _error
    ok = True
    error = None
    try:
        for event in events:
            with _lock:
                if _cancel:
                    ok = False
                    error = "Stopped"
                    break
                _current = event["event_id"]
                _emit({"type": "reading", "id": event["event_id"]})
            trace, records = _handle(event)
            row = {
                "id": event["event_id"],
                "classification": trace.get("classification") or "noise",
                "outcome": _outcome(records),
                "summary": (trace.get("summary") or "").split("\n", 1)[0][:180],
            }
            with _lock:
                _seen.append(row)
                _done += 1
                _current = None
                _emit({"type": "event", "event": row, "done": _done, "total": _total})
    except Exception as exc:  # noqa: BLE001 - a failed event must not leave the run stuck
        ok = False
        error = f"{type(exc).__name__}: {exc}"
    with _lock:
        _running = False
        _current = None
        _error = None if ok else error
        _emit({"type": "done", "ok": ok, "error": _error, "done": _done, "total": _total})
