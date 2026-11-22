"""Start a test grade from the dashboard and remember each case as it finishes.

The Tests page posts here, then reads /api/run (and the event stream) to draw the run while
the grader is still going. One run at a time. The commands are the same ones start.py uses;
the request can only pick a known suite and rules, llm, or both.

Online (TOWER_WORKSPACES=1) a grade belongs to the visitor who started it: it writes into their
workspace (root), only they see it, it reads with the AI model alone, and it grades only the demo's
events. One grade runs at a time; another visitor who asks meanwhile is told to try again shortly.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import threading
import time
import urllib.request
from collections import deque

HERE = os.path.dirname(os.path.abspath(__file__))
HITACHI = os.path.abspath(os.path.join(HERE, "..", ".."))

# The 15 given events. A request that names anything else is rejected.
ORDER = ["given"]
READERS = ("rules", "llm", "both")
_CASE = re.compile(r"^\[(?P<reader>[^\]]+)\]\s+(?P<id>\S+)\s+(?P<verdict>PASS|FAIL)\s+(?P<category>\S*)")

_lock = threading.Condition()
_seq = 0
_deltas: deque[tuple[int, dict]] = deque(maxlen=8000)
_running = False
_cancel = False
_proc: subprocess.Popen | None = None
_reader: str | None = None
_model = os.environ.get("TOWER_LLM_MODEL", "qwen2.5:0.5b")
_suites: list[dict] = []
_passed = 0
_failed = 0
_total = 0
_ok: bool | None = None
_error: str | None = None
_tail: list[str] = []
_ollama = {"at": 0.0, "ok": False, "why": "not checked"}
ONLINE = os.environ.get("TOWER_WORKSPACES", "") == "1"
RUNS = os.path.join(HITACHI, "runs")
_root = RUNS          # where the current (or last) grade writes; online, its visitor's workspace
BUSY = "Someone else is running the tests right now. Try again in a minute."


def ollama_info() -> tuple[bool, str]:
    """(usable, reason). Cached for a few seconds so the page can ask often."""
    now = time.time()
    if now - _ollama["at"] < 15:
        return bool(_ollama["ok"]), str(_ollama["why"])
    url = os.environ.get("OLLAMA_URL", "http://localhost:11434").rstrip("/")
    model = os.environ.get("TOWER_LLM_MODEL", "qwen2.5:0.5b")
    try:
        with urllib.request.urlopen(f"{url}/api/tags", timeout=2) as response:
            names = {m.get("name") for m in json.load(response).get("models", [])}
    except Exception:  # noqa: BLE001 - any failure means the button stays on the rule reader
        why = f"Ollama is not running at {url}"
        _ollama.update(at=now, ok=False, why=why)
        return False, why
    ok = model in names or f"{model}:latest" in names
    why = f"Ollama has {model}" if ok else f"{model} is not pulled"
    _ollama.update(at=now, ok=ok, why=why)
    return ok, why


def _specs():
    from tower.ui import reports

    return {s["id"]: s for s in reports.SUITES}


def _case_count(spec) -> int:
    from tower.ui import reports

    return len(reports._load_cases(spec["cases"]))  # online, only the demo's events


def _command(spec, reader: str) -> list[str]:
    if spec["id"] == "given":
        return ["tests/run_given.py", "--reader", reader]
    args = ["tests/run_cases.py", "--reader", reader, "--cases", os.path.join("tests", spec["cases"])]
    if spec["runs"] != "tests":
        args += ["--out", os.path.join("runs", spec["runs"])]
    return args


def _blank_suite(spec, total: int) -> dict:
    return {
        "id": spec["id"], "title": spec["title"], "status": "queued",
        "passed": 0, "failed": 0, "total": total, "cases": [],
    }


def _snapshot() -> dict:
    """Caller holds _lock."""
    ok, why = _ollama["ok"], _ollama["why"]
    return {
        "seq": _seq,
        "running": _running,
        "reader": _reader,
        "model": _model,
        "ollama": ok,
        "why": why,
        "passed": _passed,
        "failed": _failed,
        "total": _total,
        "ok": _ok,
        "error": _error,
        "tail": list(_tail),
        "suites": [
            {
                "id": s["id"], "title": s["title"], "status": s["status"],
                "passed": s["passed"], "failed": s["failed"], "total": s["total"],
                "cases": list(s["cases"]),
            }
            for s in _suites
        ],
    }


def _mine(root: str | None) -> bool:
    """Caller holds _lock. Whether this visitor (root) owns the current grade. Always on a laptop."""
    return not ONLINE or (root or RUNS) == _root


def _blank_snapshot() -> dict:
    """Caller holds _lock. What a visitor sees while someone else's grade is the one in memory."""
    return {"seq": _seq, "running": False, "reader": None, "model": _model, "ollama": _ollama["ok"],
            "why": _ollama["why"], "passed": 0, "failed": 0, "total": 0, "ok": None, "error": None,
            "tail": [], "suites": []}


def forget(root: str | None = None) -> None:
    """Reset tests: drop the last grade so the page stops showing cases whose files are gone."""
    global _running, _reader, _suites, _passed, _failed, _total, _ok, _error, _tail
    with _lock:
        if not _mine(root):
            return
        _running, _reader, _suites, _passed, _failed, _total, _ok, _error, _tail = False, None, [], 0, 0, 0, None, None, []
        _emit({"type": "reset"})


def status(root: str | None = None) -> dict:
    ollama_info()
    with _lock:
        return _snapshot() if _mine(root) else _blank_snapshot()


def busy_root() -> str | None:
    """The workspace a grade is writing into right now, or None."""
    with _lock:
        return _root if _running else None


def _emit(event: dict) -> None:
    """Caller holds _lock. The event's seq matches the snapshot taken just after this change."""
    global _seq
    _seq += 1
    event = dict(event)
    event["seq"] = _seq
    if event.get("type") == "reset":
        event["job"] = _snapshot()
    _deltas.append((_seq, event))
    _lock.notify_all()


def _note(text: str) -> None:
    """Caller holds _lock."""
    _tail.append(text)
    del _tail[:-12]
    _emit({"type": "log", "text": text})


def start(reader: str, suite_ids: list[str] | None, root: str | None = None) -> dict:
    """Begin a grade. ValueError is a bad request. error=already running is a 409."""
    global _running, _cancel, _reader, _model, _suites, _passed, _failed, _total, _ok, _error, _tail, _root
    if ONLINE:
        reader, suite_ids = "llm", ["given"]   # online: the AI model alone, on the demo's events
    if reader not in READERS:
        raise ValueError("reader must be rules, llm, or both")
    specs = _specs()
    if suite_ids is None:
        suite_ids = ["given"] if reader in ("llm", "both") else list(ORDER)
    if not isinstance(suite_ids, list) or not suite_ids:
        raise ValueError("suites must be a non-empty list")
    unknown = [s for s in suite_ids if s not in specs]
    if unknown:
        raise ValueError("unknown suite: " + ", ".join(unknown))
    # Keep the first of any duplicate, in the pipeline order.
    chosen = [s for s in ORDER if s in set(suite_ids)]
    ollama_info()
    model = os.environ.get("TOWER_LLM_MODEL", "qwen2.5:0.5b")
    passes = 2 if reader == "both" else 1
    planned = []
    for sid in chosen:
        planned.append(_blank_suite(specs[sid], _case_count(specs[sid]) * passes))
    with _lock:
        if _running:
            return {"error": "A run is already going" if _mine(root) else BUSY, "busy": not _mine(root)}
        _root = root or RUNS
        _running = True
        _cancel = False
        _reader = reader
        _model = model
        _suites = planned
        _passed = 0
        _failed = 0
        _total = sum(s["total"] for s in planned)
        _ok = None
        _error = None
        _tail = []
        _emit({"type": "reset"})
        total = _total
    threading.Thread(target=_worker, args=(reader, chosen), name="tower-test-run", daemon=True).start()
    return {"started": True, "reader": reader, "suites": chosen, "total": total}


def stop(root: str | None = None) -> dict:
    """End the grade that is going. Safe to call when nothing is running."""
    global _cancel
    with _lock:
        if not _mine(root):
            return _blank_snapshot()
        _cancel = True
        proc = _proc
    if proc is not None and proc.poll() is None:
        proc.terminate()
        try:
            proc.wait(timeout=3)
        except subprocess.TimeoutExpired:
            proc.kill()
    with _lock:
        return _snapshot()


def follow(root: str | None = None):
    """Yield ('state', snapshot) once, then ('update', event) for each later change, and pings.
    Online, changes to another visitor's grade are not sent (a ping instead)."""
    ok, why = ollama_info()
    with _lock:
        _ollama["ok"], _ollama["why"] = ok, why
        seq = _seq
        snap = _snapshot() if _mine(root) else _blank_snapshot()
    yield "state", snap
    while True:
        with _lock:
            if _seq == seq:
                _lock.wait(timeout=15)
            fresh = [(n, ev) for n, ev in _deltas if n > seq]
            if fresh:
                seq = fresh[-1][0]
            if not _mine(root):
                fresh = []
        if not fresh:
            yield "ping", {"seq": seq}
            continue
        for _n, ev in fresh:
            yield "update", ev


def _set_suite(sid: str, **fields) -> None:
    """Caller holds _lock."""
    for suite in _suites:
        if suite["id"] == sid:
            suite.update(fields)
            _emit({"type": "suite", "id": sid, "status": suite["status"], "total": suite["total"],
                   "passed": suite["passed"], "failed": suite["failed"]})
            return


def _add_case(sid: str, case: dict) -> None:
    """Caller holds _lock."""
    global _passed, _failed
    for suite in _suites:
        if suite["id"] != sid:
            continue
        suite["cases"].append(case)
        if case["verdict"] == "PASS":
            suite["passed"] += 1
            _passed += 1
        else:
            suite["failed"] += 1
            _failed += 1
        _emit({"type": "case", "suite": sid, "case": case,
               "passed": suite["passed"], "failed": suite["failed"]})
        return


def _finish(ok: bool, error: str | None) -> None:
    global _running, _ok, _error, _proc
    # Stay "running" while the summary is written, so a second click cannot grade the same files.
    with _lock:
        _proc = None
        _note("Saving the summary")
    try:
        from tower.ui import reports

        reports.write_summary(root=_root)
    except Exception as exc:  # noqa: BLE001 - the grade is already on disk; the page still reloads it
        with _lock:
            _note(f"Could not write the summary: {exc}")
    with _lock:
        _running = False
        _ok = ok
        _error = error
        _emit({"type": "done", "ok": ok, "error": error, "passed": _passed, "failed": _failed, "total": _total})


def _run_suite(reader: str, spec) -> int:
    """Run one suite. Return the process exit code, or -1 when it was stopped."""
    global _proc
    cmd = [sys.executable, "-u", *_command(spec, reader)]
    env = os.environ.copy()
    env["PYTHONUNBUFFERED"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"
    if ONLINE:
        from tower.ui import reports

        env["TOWER_RUNS_DIR"] = _root
        env["TOWER_TEST_IDS"] = ",".join(sorted(reports.DEMO))
    with _lock:
        if _cancel:
            _set_suite(spec["id"], status="stopped")
            return -1
        _set_suite(spec["id"], status="running")
        _note(f"Starting {spec['title']}")
    proc = subprocess.Popen(
        cmd, cwd=HITACHI, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        text=True, encoding="utf-8", errors="replace", bufsize=1, env=env,
    )
    with _lock:
        _proc = proc
        stop_now = _cancel
    if stop_now:
        proc.terminate()
    assert proc.stdout is not None
    for line in proc.stdout:
        text = line.rstrip()
        if not text:
            continue
        match = _CASE.match(text)
        with _lock:
            if match:
                name = match.group("reader")
                label = _model if name == "llm" else name
                _add_case(spec["id"], {
                    "id": match.group("id"),
                    "verdict": match.group("verdict"),
                    "reader": label,
                    "category": match.group("category"),
                })
            else:
                _note(text[:240])
    code = proc.wait()
    with _lock:
        if _proc is proc:
            _proc = None
        if _cancel:
            _set_suite(spec["id"], status="stopped")
            return -1
        _set_suite(spec["id"], status="done" if code == 0 else "failed")
        _note(f"{spec['title']} {'finished' if code == 0 else f'failed (exit {code})'}")
    return code


def _worker(reader: str, suite_ids: list[str]) -> None:
    specs = _specs()
    ok = True
    error = None
    try:
        for sid in suite_ids:
            with _lock:
                if _cancel:
                    ok = False
                    error = "Stopped"
                    for suite in list(_suites):
                        if suite["status"] in ("queued", "running"):
                            _set_suite(suite["id"], status="stopped")
                    break
            code = _run_suite(reader, specs[sid])
            if code != 0:
                ok = False
                if code == -1:
                    error = "Stopped"
                    with _lock:
                        for suite in list(_suites):
                            if suite["status"] in ("queued", "running"):
                                _set_suite(suite["id"], status="stopped")
                    break
    except Exception as exc:  # noqa: BLE001 - one broken suite must not leave the run stuck on "running"
        ok = False
        error = f"{type(exc).__name__}: {exc}"
        with _lock:
            _note(error)
            for suite in list(_suites):
                if suite["status"] == "running":
                    _set_suite(suite["id"], status="failed")
    _finish(ok, error)
