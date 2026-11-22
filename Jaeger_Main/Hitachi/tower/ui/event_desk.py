"""Event run and event add for the dashboard.

Event run walks the 15 given events, then any event added from the chat, and reports each one
as it finishes. It does not replace runs/run1.

Event add takes one chat message, reads it with the model (rule reader as the backup when
Ollama is not running), and keeps the event beside
the official feed. The official events.json is never written.

Workspaces (TOWER_WORKSPACES=1, the online version): each visitor gets a Desk of their own, with
its own feed, added events, chat, run and test runs, under runs/ws/<id>/. A new workspace starts
empty: nothing handled, no tests run. Without workspaces there is one Desk, on runs/run1 and
runs/desk, as before.
"""

from __future__ import annotations

import json
import os
import threading
import time
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

_graph = None
_graph_lock = threading.Lock()


def _read(path: str, fallback):
    if not os.path.isfile(path):
        return fallback
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def _write(path: str, payload) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2)
        handle.write("\n")
    os.replace(tmp, path)


def _graph_once():
    """The company graph, built once and shared by every workspace (it is only read)."""
    global _graph
    with _graph_lock:
        if _graph is None:
            from tower.graph import WorldGraph

            _graph = WorldGraph()
    return _graph


def _official() -> list[dict]:
    """The given events: online, only the demo ones."""
    with open(OFFICIAL, encoding="utf-8") as handle:
        data = json.load(handle)
    events = data["events"] if isinstance(data, dict) else data
    return [e for e in events if isinstance(e, dict) and e.get("event_id") and shown(e["event_id"])]


def shown(event_id: str) -> bool:
    """False for a given event left out of the short online demo. Added events are always shown."""
    return not DEMO_EVENTS or not str(event_id).startswith("E-") or event_id in DEMO_EVENTS


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




# Events read at the same time during a run. Two keeps both CPUs of a small host busy (the model
# answers two requests at once with OLLAMA_NUM_PARALLEL=2); events still land in the feed in order.
RUN_PARALLEL = max(1, int(os.environ.get("TOWER_RUN_PARALLEL", "2")))

# The run the Event feed shows (the same folder tower/ui/server.py reads). Event run starts it
# empty and writes each event into it as it finishes, so the feed fills in live. The frozen
# submission copy lives in runs/submission and is never touched.
FEED_DIR = os.path.join(HITACHI, os.environ.get("TOWER_RUN_DIR", os.path.join("runs", "run1")))
FEED_NAMES = ("traces.json", "action_log.jsonl", "outbox.jsonl")
# The short online demo: the feed shows, and Run the demo reads, only these given events (one of each
# kind). The other given events stay in events.json and the stored run, unshown. Empty (on a laptop):
# all of them, as before.
DEMO_EVENTS = {e.strip() for e in os.environ.get("TOWER_DEMO_EVENTS", "").split(",") if e.strip()}
DESK_NAMES = ("events.json", "traces.json", "action_log.jsonl", "chat.json")


class Desk:
    """One event feed: its files (the feed's run folder and the added events), its run, its updates."""

    def __init__(self, desk_dir: str, feed_dir: str, backups: str, tests_dir: str | None = None):
        self.desk_dir = desk_dir
        self.feed_dir = feed_dir
        self.backups = backups               # where Reset events (and, online, Reset tests) keeps its backups
        self.tests_dir = tests_dir or os.path.join(HITACHI, "runs")   # where this desk's test runs are saved
        self.events_path = os.path.join(desk_dir, "events.json")
        self.traces_path = os.path.join(desk_dir, "traces.json")
        self.log_path = os.path.join(desk_dir, "action_log.jsonl")
        self.chat_path = os.path.join(desk_dir, "chat.json")
        self.feed_traces = os.path.join(feed_dir, "traces.json")
        self.feed_log = os.path.join(feed_dir, "action_log.jsonl")
        self.feed_outbox = os.path.join(feed_dir, "outbox.jsonl")
        self.files = threading.Lock()
        self.lock = threading.Condition()
        self.seq = 0
        self.deltas: deque[tuple[int, dict]] = deque(maxlen=4000)
        self.running = False
        self.cancel = False
        # Each run has an id. Stop retires the current id, so a worker still reading an event (a model
        # call can take 10-20 s) throws its result away instead of writing it into the feed.
        self.run_id = 0
        self.current: str | None = None
        self.done = 0
        self.total = 0
        self.error: str | None = None
        self.seen: list[dict] = []
        self.used = time.time()

    # Files.
    def stamp_paths(self) -> list[str]:
        return [self.events_path, self.traces_path, self.log_path, self.chat_path]

    def saved_events(self) -> list[dict]:
        with self.files:
            data = _read(self.events_path, [])
        return list(data) if isinstance(data, list) else []

    def saved_traces(self) -> list[dict]:
        with self.files:
            data = _read(self.traces_path, [])
        return list(data) if isinstance(data, list) else []

    def saved_log(self) -> list[dict]:
        if not os.path.isfile(self.log_path):
            return []
        rows = []
        with open(self.log_path, encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if line:
                    rows.append(json.loads(line))
        return rows

    def messages(self) -> list[dict]:
        with self.files:
            data = _read(self.chat_path, [])
        return list(data) if isinstance(data, list) else []

    def _clear_feed(self) -> None:
        with self.files:
            os.makedirs(self.feed_dir, exist_ok=True)
            _write(self.feed_traces, [])
            for path in (self.feed_log, self.feed_outbox):
                open(path, "w", encoding="utf-8").close()

    def _save_to_feed(self, trace: dict, records: list[dict]) -> None:
        """Add one finished event to the feed's run, replacing an older copy of the same event."""
        with self.files:
            traces = [t for t in _read(self.feed_traces, []) if t.get("event_id") != trace.get("event_id")]
            traces.append(trace)
            _write(self.feed_traces, traces)
            with open(self.feed_log, "a", encoding="utf-8") as handle:
                for record in records:
                    handle.write(json.dumps(record) + "\n")

    def _append_saved(self, event: dict, trace: dict, records: list[dict], reply: str) -> None:
        with self.files:
            events = _read(self.events_path, [])
            traces = _read(self.traces_path, [])
            chat = _read(self.chat_path, [])
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
            _write(self.events_path, events)
            _write(self.traces_path, traces)
            _write(self.chat_path, chat[-200:])
            with open(self.log_path, "a", encoding="utf-8") as handle:
                for record in records:
                    handle.write(json.dumps(record) + "\n")

    def add_message(self, text: str) -> dict:
        """Read one chat message as a new event. ValueError is a bad message."""
        if not isinstance(text, str):
            raise ValueError("text is required")
        text = text.strip()
        if not text or len(text) > 4000:
            raise ValueError("text must be 1 to 4000 characters")
        if any(ord(ch) < 32 and ch not in "\n\t" for ch in text):
            raise ValueError("text has unsupported characters")
        with self.files:
            existing = _read(self.events_path, [])
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
        self._append_saved(event, trace, records, reply)
        return {
            "event": event,
            "reply": reply,
            "classification": trace.get("classification") or "",
            "outcome": _outcome(records),
        }

    # The run.
    def _snapshot(self) -> dict:
        """Caller holds self.lock."""
        return {
            "seq": self.seq,
            "running": self.running,
            "current": self.current,
            "done": self.done,
            "total": self.total,
            "error": self.error,
            "events": list(self.seen),
        }

    def status(self) -> dict:
        with self.lock:
            return self._snapshot()

    def _emit(self, event: dict) -> None:
        """Caller holds self.lock."""
        self.seq += 1
        event = dict(event)
        event["seq"] = self.seq
        if event.get("type") == "reset":
            event["job"] = self._snapshot()
        self.deltas.append((self.seq, event))
        self.lock.notify_all()

    def start(self) -> dict:
        """Walk the feed. error=already running is a 409. Online (DEMO_EVENTS), only the demo events."""
        events = _official() if DEMO_EVENTS else _official() + self.saved_events()
        with self.lock:
            if self.running:
                return {"error": "An event run is already going"}
            self.run_id += 1
            run_id = self.run_id
            self.running = True
            self.cancel = False
            self.current = None
            self.done = 0
            self.total = len(events)
            self.error = None
            self.seen = []
            self._emit({"type": "reset"})
            total = self.total
        self._clear_feed()
        threading.Thread(target=_reader().warm, name="tower-model-warm", daemon=True).start()
        threading.Thread(target=self._worker, args=(events, run_id), name="tower-event-run", daemon=True).start()
        return {"started": True, "total": total}

    def forget(self) -> None:
        """Reset events: drop the run list and retire any run still reading, so nothing old reappears."""
        with self.lock:
            self.run_id += 1
            self.running, self.cancel, self.current, self.done, self.total, self.error, self.seen = (
                False, False, None, 0, 0, None, [])
            self._emit({"type": "reset"})

    def stop(self) -> dict:
        """End the run now. The event being read is dropped when it finishes; nothing more is written."""
        with self.lock:
            self.cancel = True
            if self.running:
                self.run_id += 1
                self.running = False
                self.current = None
                self.error = "Stopped"
                self._emit({"type": "done", "ok": False, "error": self.error, "done": self.done, "total": self.total})
            return self._snapshot()

    def follow(self):
        """Yield ('state', snapshot) once, then ('update', event) and pings."""
        with self.lock:
            seq = self.seq
            snap = self._snapshot()
        yield "state", snap
        while True:
            with self.lock:
                if self.seq == seq:
                    self.lock.wait(timeout=15)
                fresh = [(n, ev) for n, ev in self.deltas if n > seq]
                if fresh:
                    seq = fresh[-1][0]
            if not fresh:
                yield "ping", {"seq": seq}
                continue
            for _n, ev in fresh:
                yield "update", ev

    def _worker(self, events: list[dict], run_id: int) -> None:
        from concurrent.futures import ThreadPoolExecutor

        ok = True
        error = None
        reading: list[str] = []          # events being read right now
        finished: dict[int, tuple] = {}  # index -> (trace, records), waiting for the ones before it
        next_out = 0

        def stopped() -> bool:
            return run_id != self.run_id

        def read(index: int, event: dict):
            with self.lock:
                if stopped():
                    return index, None
                reading.append(event["event_id"])
                self.current = ", ".join(reading)
                self._emit({"type": "reading", "id": event["event_id"]})
            trace, records = _handle(event)
            with self.lock:
                if event["event_id"] in reading:
                    reading.remove(event["event_id"])   # read: no longer "being read", even if it waits its turn
                self.current = ", ".join(reading) or None
            return index, (trace, records)

        try:
            with ThreadPoolExecutor(max_workers=RUN_PARALLEL, thread_name_prefix="tower-event") as pool:
                futures = [pool.submit(read, i, event) for i, event in enumerate(events)]
                for future in futures:
                    index, result = future.result()
                    with self.lock:
                        if stopped() or result is None:
                            return  # stopped: stop() already reported the end of the run
                        finished[index] = result
                        # Publish in the feed's order: an event that finished early waits for the ones before it.
                        while next_out in finished:
                            event = events[next_out]
                            trace, records = finished.pop(next_out)
                            row = {
                                "id": event["event_id"],
                                "classification": trace.get("classification") or "noise",
                                "outcome": _outcome(records),
                                "summary": (trace.get("summary") or "").split("\n", 1)[0][:180],
                            }
                            if event.get("event_id", "").startswith("E-"):
                                self._save_to_feed(trace, records)   # added events are already in the desk files
                            self.seen.append(row)
                            self.done += 1
                            self.current = ", ".join(reading) or None
                            self._emit({"type": "event", "event": row, "done": self.done, "total": self.total})
                            next_out += 1
        except Exception as exc:  # noqa: BLE001 - a failed event must not leave the run stuck
            ok = False
            error = f"{type(exc).__name__}: {exc}"
        with self.lock:
            if run_id != self.run_id:
                return
            self.running = False
            self.current = None
            self.error = None if ok else error
            self._emit({"type": "done", "ok": ok, "error": self.error, "done": self.done, "total": self.total})


# The desk on this computer (no workspaces): runs/run1 and runs/desk, as before.
DEFAULT = Desk(DESK, FEED_DIR, os.path.join(HITACHI, "runs", ".reset"))

# Workspaces: one Desk per visitor, under runs/ws/<id>/ (desk/, run1/, tests/, .reset/). Ids are random,
# made by the server. An open tab checks in every few seconds (once a minute in the background), so a
# workspace with no requests for IDLE_MINUTES belongs to a closed tab: a background sweep deletes it,
# off the request path. At most MAX_WORKSPACES are kept.
WORKSPACES = os.environ.get("TOWER_WORKSPACES", "") == "1"
WS_ROOT = os.path.join(HITACHI, "runs", "ws")
IDLE_MINUTES = float(os.environ.get("TOWER_WS_IDLE_MINUTES", "10"))
MAX_WORKSPACES = int(os.environ.get("TOWER_WS_MAX", "200"))
_ws: dict[str, Desk] = {}
_ws_lock = threading.Lock()


def _ws_desk(root: str) -> Desk:
    return Desk(os.path.join(root, "desk"), os.path.join(root, "run1"), os.path.join(root, ".reset"),
                os.path.join(root, "tests"))


# Online, a first visit (no cookie yet) reads this empty desk. It is never written, so it never exists
# on disk: every page shows its empty state. ("_blank" cannot be a workspace id: ids are 16+ characters.)
BLANK = _ws_desk(os.path.join(WS_ROOT, "_blank")) if WORKSPACES else DEFAULT


def _seed(desk: Desk) -> None:
    """A new workspace starts fresh: nothing handled, no events added, no tests run."""
    os.makedirs(desk.desk_dir, exist_ok=True)
    os.makedirs(desk.feed_dir, exist_ok=True)
    os.makedirs(desk.tests_dir, exist_ok=True)


def _prune_workspaces(now: float, make_room: bool = True) -> None:
    """Caller holds _ws_lock. Drop idle workspaces (never one that is running), oldest first; with
    make_room, also the oldest ones past MAX_WORKSPACES, so a new one fits."""
    import shutil

    from tower.ui import runner

    grading = runner.busy_root()
    idle = sorted((d.used, wid) for wid, d in _ws.items() if not d.running and d.tests_dir != grading)
    over = max(0, len(_ws) - MAX_WORKSPACES + 1) if make_room else 0
    for used, wid in idle:
        if now - used < IDLE_MINUTES * 60 and over <= 0:
            break
        _ws.pop(wid, None)
        shutil.rmtree(os.path.join(WS_ROOT, wid), ignore_errors=True)
        over -= 1


_sweeper: threading.Thread | None = None


def _sweep_forever() -> None:
    while True:
        time.sleep(60)
        with _ws_lock:
            _prune_workspaces(time.time(), make_room=False)


def get(workspace: str | None = None) -> Desk:
    """The desk for this visitor's workspace, made (from the demo data) the first time it is used.
    Without workspaces, or without an id, the shared desk."""
    if not WORKSPACES or not workspace:
        return DEFAULT
    global _sweeper
    now = time.time()
    with _ws_lock:
        if _sweeper is None:
            _sweeper = threading.Thread(target=_sweep_forever, name="tower-ws-sweep", daemon=True)
            _sweeper.start()
        desk = _ws.get(workspace)
        if desk is None:
            if len(_ws) >= MAX_WORKSPACES:
                _prune_workspaces(now)
            root = os.path.join(WS_ROOT, workspace)
            desk = _ws_desk(root)
            if not os.path.isdir(root):
                _seed(desk)
            _ws[workspace] = desk
        desk.used = now
    return desk


def stop_all() -> None:
    """Shutting down: end every run."""
    DEFAULT.stop()
    with _ws_lock:
        desks = list(_ws.values())
    for desk in desks:
        desk.stop()


# The module-level calls other code uses on this computer: the shared desk.
def stamp_paths() -> list[str]:
    return DEFAULT.stamp_paths()


def saved_events() -> list[dict]:
    return DEFAULT.saved_events()


def saved_traces() -> list[dict]:
    return DEFAULT.saved_traces()


def saved_log() -> list[dict]:
    return DEFAULT.saved_log()


def messages() -> list[dict]:
    return DEFAULT.messages()


def add_message(text: str) -> dict:
    return DEFAULT.add_message(text)


def status() -> dict:
    return DEFAULT.status()


def start() -> dict:
    return DEFAULT.start()


def stop() -> dict:
    return DEFAULT.stop()


def forget() -> None:
    DEFAULT.forget()


def follow():
    return DEFAULT.follow()
