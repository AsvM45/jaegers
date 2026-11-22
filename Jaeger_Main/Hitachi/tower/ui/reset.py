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

Online, with a workspace per visitor, both kinds are that visitor's own (event_desk.Desk: its feed,
and its test runs under tests_dir), and the backups live in the workspace.
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


def _desk(desk=None):
    from tower.ui import event_desk

    return desk or event_desk.DEFAULT


def _root(kind: str, desk=None) -> str:
    """Where this kind's backups go."""
    return os.path.join(_desk(desk).backups, kind)


def _paths(kind: str, desk=None) -> list[str]:
    """What a kind owns, as absolute paths (files or folders; missing ones are fine)."""
    if kind == "events":
        d = _desk(desk)
        return [d.feed_traces, d.feed_log, d.feed_outbox, d.desk_dir]
    from tower.ui import reports

    root = _desk(desk).tests_dir
    suites = [os.path.join(root, s["runs"]) for s in reports.SUITES]
    model = [] if reports.ONLINE else [reports.MODEL_RUNS]
    return suites + model + [os.path.join(root, "test_log.jsonl"), os.path.join(root, "TEST_SUMMARY.md")]


def _blank(kind: str, desk=None) -> None:
    """Leave the empty files the pages read, so nothing errors and every page says 'nothing yet'."""
    if kind == "events":
        d = _desk(desk)
        os.makedirs(d.feed_dir, exist_ok=True)
        with open(d.feed_traces, "w", encoding="utf-8") as handle:
            handle.write("[]\n")
        for path in (d.feed_log, d.feed_outbox):
            open(path, "w", encoding="utf-8").close()
        return
    from tower.ui import reports

    root = _desk(desk).tests_dir
    for s in reports.SUITES:
        os.makedirs(os.path.join(root, s["runs"]), exist_ok=True)
    open(os.path.join(root, "test_log.jsonl"), "w", encoding="utf-8").close()


def _has_data(path: str) -> bool:
    if os.path.isdir(path):
        return any(_has_data(os.path.join(path, n)) for n in os.listdir(path))
    return os.path.isfile(path) and os.path.getsize(path) > 0 and open(path, "rb").read(16).strip() not in (b"", b"[]")


def _rel(path: str) -> str:
    return os.path.relpath(path, HITACHI)


def _move_out(kind: str, label: str, desk=None) -> str | None:
    """Move what the kind owns into a new backup folder. Returns the folder, or None if empty."""
    present = [p for p in _paths(kind, desk) if os.path.exists(p) and _has_data(p)]
    if not present:
        return None
    folder = os.path.join(_root(kind, desk), time.strftime("%Y-%m-%d_%H-%M-%S") + f"_{label}")
    for p in present:
        dest = os.path.join(folder, _rel(p))
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        shutil.move(p, dest)
    with open(os.path.join(folder, "reset.json"), "w", encoding="utf-8") as handle:
        json.dump({"kind": kind, "at": time.strftime("%Y-%m-%d %H:%M:%S"), "label": label,
                   "paths": [_rel(p) for p in present]}, handle, indent=2)
    _prune(kind, desk)
    return folder


def _backups(kind: str, desk=None) -> list[str]:
    root = _root(kind, desk)
    if not os.path.isdir(root):
        return []
    return sorted((os.path.join(root, d) for d in os.listdir(root) if os.path.isfile(os.path.join(root, d, "reset.json"))), reverse=True)


def _prune(kind: str, desk=None) -> None:
    for old in _backups(kind, desk)[KEEP:]:
        shutil.rmtree(old, ignore_errors=True)


def _stop(kind: str, desk=None) -> None:
    """End a running event run or test grade first, so nothing writes into the folders mid-move."""
    if kind == "events":
        _desk(desk).stop()
    else:
        from tower.ui import runner

        runner.stop(_desk(desk).tests_dir)


def _forget(kind: str, desk=None) -> None:
    """Drop the in-memory state that mirrors the files (the event run's list, the last grade)."""
    if kind == "events":
        _desk(desk).forget()
    else:
        from tower.ui import reports, runner

        runner.forget(_desk(desk).tests_dir)
        try:
            reports.write_summary(root=_desk(desk).tests_dir)
        except OSError:
            pass


def status(desk=None) -> dict:
    out = {}
    for kind in KINDS:
        found = _backups(kind, desk)
        info = json.load(open(os.path.join(found[0], "reset.json"), encoding="utf-8")) if found else None
        # The summary report is rewritten (empty) right after a reset, so it does not count as data.
        owned = [p for p in _paths(kind, desk) if os.path.exists(p) and not p.endswith("TEST_SUMMARY.md")]
        out[kind] = {"has_data": any(_has_data(p) for p in owned),
                     "undo": bool(info and info.get("label") == "reset"), "at": info["at"] if info else None}
    return out


def reset(kind: str, confirm: str, desk=None) -> dict:
    if kind not in KINDS:
        raise ValueError(f"unknown kind {kind!r}")
    if confirm != "RESET":
        raise ValueError('type RESET to confirm')
    _stop(kind, desk)
    folder = _move_out(kind, "reset", desk)
    _blank(kind, desk)
    _forget(kind, desk)
    return {"ok": True, "kind": kind, "cleared": bool(folder), **status(desk)[kind]}


def undo(kind: str, desk=None) -> dict:
    """Swap the newest reset backup back in. What is there now goes to a backup of its own."""
    if kind not in KINDS:
        raise ValueError(f"unknown kind {kind!r}")
    found = [b for b in _backups(kind, desk) if json.load(open(os.path.join(b, "reset.json"), encoding="utf-8")).get("label") == "reset"]
    if not found:
        raise ValueError("there is no reset to undo")
    source = found[0]
    _stop(kind, desk)
    _move_out(kind, "before-undo", desk)
    for p in json.load(open(os.path.join(source, "reset.json"), encoding="utf-8"))["paths"]:
        dest = os.path.join(HITACHI, p)
        if os.path.isdir(dest):
            shutil.rmtree(dest)
        elif os.path.exists(dest):
            os.remove(dest)
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        shutil.move(os.path.join(source, p), dest)
    shutil.rmtree(source, ignore_errors=True)
    _forget(kind, desk)
    return {"ok": True, "kind": kind, **status(desk)[kind]}
