"""Reset events / Reset tests: clear one kind of data, keeping it in a backup that Undo restores.

    events  the event feed and Overview (the feed's traces, tool calls and notifications) and every
            event added on Add events, with the chat history
    tests   every saved test run (each suite's folder, the model-alone runs), the run history and
            the summary report

The two never touch each other, and neither touches the frozen submission (runs/submission), the
ontology export, the screenshots, the company tables or the test cases themselves.

A reset moves the files to runs/.reset/<kind>/<time>/ and leaves empty ones behind, so every page
shows its empty state. Undo swaps the newest backup back in (and backs up whatever is there now, so
an undo can itself be undone). The last few backups of each kind are kept. Confirmation is checked
here as well as in the page: a reset needs confirm="RESET".
"""

from __future__ import annotations

import json
import os
import shutil
import time

HITACHI = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
RUNS = os.path.join(HITACHI, "runs")
BACKUPS = os.path.join(RUNS, ".reset")
KEEP = 5
KINDS = ("events", "tests")


def _paths(kind: str) -> list[str]:
    """What a kind owns, as absolute paths (files or folders; missing ones are fine)."""
    if kind == "events":
        from tower.ui import event_desk

        feed = [os.path.join(event_desk.FEED_DIR, n) for n in ("traces.json", "action_log.jsonl", "outbox.jsonl")]
        return feed + [event_desk.DESK]
    from tower.ui import reports

    suites = [os.path.join(RUNS, s["runs"]) for s in reports.SUITES]
    return suites + [reports.MODEL_RUNS, os.path.join(RUNS, "test_log.jsonl"), os.path.join(RUNS, "TEST_SUMMARY.md")]


def _blank(kind: str) -> None:
    """Leave the empty files the pages read, so nothing errors and every page says 'nothing yet'."""
    if kind == "events":
        from tower.ui import event_desk

        os.makedirs(event_desk.FEED_DIR, exist_ok=True)
        with open(os.path.join(event_desk.FEED_DIR, "traces.json"), "w", encoding="utf-8") as handle:
            handle.write("[]\n")
        for name in ("action_log.jsonl", "outbox.jsonl"):
            open(os.path.join(event_desk.FEED_DIR, name), "w", encoding="utf-8").close()
        return
    from tower.ui import reports

    for s in reports.SUITES:
        os.makedirs(os.path.join(RUNS, s["runs"]), exist_ok=True)
    open(os.path.join(RUNS, "test_log.jsonl"), "w", encoding="utf-8").close()


def _has_data(path: str) -> bool:
    if os.path.isdir(path):
        return any(_has_data(os.path.join(path, n)) for n in os.listdir(path))
    return os.path.isfile(path) and os.path.getsize(path) > 0 and open(path, "rb").read(16).strip() not in (b"", b"[]")


def _rel(path: str) -> str:
    return os.path.relpath(path, HITACHI)


def _move_out(kind: str, label: str) -> str | None:
    """Move what the kind owns into a new backup folder. Returns the folder, or None if empty."""
    present = [p for p in _paths(kind) if os.path.exists(p) and _has_data(p)]
    if not present:
        return None
    folder = os.path.join(BACKUPS, kind, time.strftime("%Y-%m-%d_%H-%M-%S") + f"_{label}")
    for p in present:
        dest = os.path.join(folder, _rel(p))
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        shutil.move(p, dest)
    with open(os.path.join(folder, "reset.json"), "w", encoding="utf-8") as handle:
        json.dump({"kind": kind, "at": time.strftime("%Y-%m-%d %H:%M:%S"), "label": label,
                   "paths": [_rel(p) for p in present]}, handle, indent=2)
    _prune(kind)
    return folder


def _backups(kind: str) -> list[str]:
    root = os.path.join(BACKUPS, kind)
    if not os.path.isdir(root):
        return []
    return sorted((os.path.join(root, d) for d in os.listdir(root) if os.path.isfile(os.path.join(root, d, "reset.json"))), reverse=True)


def _prune(kind: str) -> None:
    for old in _backups(kind)[KEEP:]:
        shutil.rmtree(old, ignore_errors=True)


def _stop(kind: str) -> None:
    """End a running event run or test grade first, so nothing writes into the folders mid-move."""
    if kind == "events":
        from tower.ui import event_desk

        event_desk.stop()
    else:
        from tower.ui import runner

        runner.stop()


def _forget(kind: str) -> None:
    """Drop the in-memory state that mirrors the files (the event run's list, the last grade)."""
    if kind == "events":
        from tower.ui import event_desk

        event_desk.forget()
    else:
        from tower.ui import reports, runner

        runner.forget()
        try:
            reports.write_summary()
        except OSError:
            pass


def status() -> dict:
    out = {}
    for kind in KINDS:
        found = _backups(kind)
        info = json.load(open(os.path.join(found[0], "reset.json"), encoding="utf-8")) if found else None
        # The summary report is rewritten (empty) right after a reset, so it does not count as data.
        owned = [p for p in _paths(kind) if os.path.exists(p) and not p.endswith("TEST_SUMMARY.md")]
        out[kind] = {"has_data": any(_has_data(p) for p in owned),
                     "undo": bool(info and info.get("label") == "reset"), "at": info["at"] if info else None}
    return out


def reset(kind: str, confirm: str) -> dict:
    if kind not in KINDS:
        raise ValueError(f"unknown kind {kind!r}")
    if confirm != "RESET":
        raise ValueError('type RESET to confirm')
    _stop(kind)
    folder = _move_out(kind, "reset")
    _blank(kind)
    _forget(kind)
    return {"ok": True, "kind": kind, "cleared": bool(folder), **status()[kind]}


def undo(kind: str) -> dict:
    """Swap the newest reset backup back in. What is there now goes to a backup of its own."""
    if kind not in KINDS:
        raise ValueError(f"unknown kind {kind!r}")
    found = [b for b in _backups(kind) if json.load(open(os.path.join(b, "reset.json"), encoding="utf-8")).get("label") == "reset"]
    if not found:
        raise ValueError("there is no reset to undo")
    source = found[0]
    _stop(kind)
    _move_out(kind, "before-undo")
    for p in json.load(open(os.path.join(source, "reset.json"), encoding="utf-8"))["paths"]:
        dest = os.path.join(HITACHI, p)
        if os.path.isdir(dest):
            shutil.rmtree(dest)
        elif os.path.exists(dest):
            os.remove(dest)
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        shutil.move(os.path.join(source, p), dest)
    shutil.rmtree(source, ignore_errors=True)
    _forget(kind)
    return {"ok": True, "kind": kind, **status()[kind]}
