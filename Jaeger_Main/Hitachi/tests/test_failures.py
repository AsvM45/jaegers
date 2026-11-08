"""What the tower does when a call fails, the model fails, or a message has no usable information.

    python tests/test_failures.py

No network and no Ollama needed: tool failures are injected into the enterprise tools, the HTTP
path runs against enterprise_server's own handler on a local port, and the model is a stand-in
that fails on purpose. Every check prints ok or FAIL; the exit code is the number of failures.

Tool calls
  - one failed write is logged as failed, not retried, and every other planned call still runs
  - when every write fails, the incident is escalated to a human once
  - when escalate fails too, the event still finishes and nothing is retried
  - the enterprise server down or unreachable is a failed call, not a crash
  - the enterprise server rejecting a call (HTTP 4xx) is a failed call
  - the same write is never sent twice in an event; a call with wrong arguments is never sent
  - noise makes no calls, even when every tool would fail
No information
  - an empty message, a rumor, a plant with no dates, an unknown shipment or lot: no writes,
    and anything that reads like an incident is escalated once
  - a real outage that touches no orders makes no calls (there is nothing to fix)
The model
  - Ollama down, or broken output: the rule reader takes over and the calls are the same
  - the model names an incident but cannot fill it in, or fails half way: no writes, one
    escalate that asks for what is missing
"""

from __future__ import annotations

import os
import socket
import sys
import tempfile
import threading
import traceback

# Any real model client in this process must fail fast instead of reaching a running Ollama.
os.environ["OLLAMA_URL"] = "http://127.0.0.1:9"

HITACHI = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HITACHI)

from enterprise import Enterprise, ToolError, load_events  # noqa: E402
from tower.agents.coordinator import handle_event  # noqa: E402
from tower.agents.llm_reader import TOOL_MODEL, LLMUnavailable  # noqa: E402
from tower.contracts import WRITE_TOOLS, ToolCall  # noqa: E402
from tower.gateway import Gateway  # noqa: E402
from tower.graph import WorldGraph  # noqa: E402
from tower.run import _ServerTools  # noqa: E402

GRAPH = WorldGraph()
EVENTS = {e["event_id"]: e for e in load_events(os.path.join(GRAPH.data_dir, "events.json"))}
RESULTS: list[tuple[bool, str]] = []


def check(name):
    """Decorator: run the check now, record ok/FAIL, keep going after a failure."""
    def wrap(fn):
        try:
            detail = fn()
            RESULTS.append((True, name))
            print(f"ok    {name}" + (f"  ({detail})" if detail else ""))
        except Exception as exc:  # noqa: BLE001  report every failing check, not just the first
            RESULTS.append((False, name))
            print(f"FAIL  {name}: {exc}")
            traceback.print_exc(limit=2)
        return fn
    return wrap


class Flaky:
    """Enterprise wrapper that fails the calls fail(tool, n) picks; n counts calls so far."""

    def __init__(self, fail=lambda tool, n: False, error=ToolError):
        self.enterprise, self.fail, self.error, self.rows = Enterprise(GRAPH.data_dir), fail, error, []

    def call(self, event_id, tool, args):
        if self.fail(tool, len(self.rows)):
            self.rows.append({"tool": tool, "args": args, "ok": False})
            raise self.error("injected failure")
        result = self.enterprise.call(event_id, tool, args)
        self.rows.append({"tool": tool, "args": args, "ok": True})
        return result


def run(event, fail=lambda tool, n: False, llm=None):
    tools = Flaky(fail)
    trace = handle_event(GRAPH, tools, event, llm)
    return trace, tools.rows


def message(text, event_id="T-1"):
    return {"event_id": event_id, "source": "test", "received_at": "2027-03-08T08:00:00", "text": text}


def tools_used(rows):
    return [r["tool"] for r in rows]


def only_one_escalate(rows):
    assert tools_used(rows) == ["escalate"], f"expected one escalate and nothing else, got {tools_used(rows)}"


# ---------------------------------------------------------------- tool calls

OUTAGE, QUALITY, NOISE = EVENTS["E-04"], EVENTS["E-15"], EVENTS["E-05"]
_, BASE = run(OUTAGE)
assert BASE and all(r["ok"] for r in BASE), "E-04 must run cleanly before failures are injected"


@check("one failed write: logged, not retried, the rest still run")
def _():
    first = next(i for i, r in enumerate(BASE) if r["tool"] == "mes.reschedule")
    trace, rows = run(OUTAGE, lambda tool, n: n == first)
    failed = [r for r in rows if not r["ok"]]
    assert len(failed) == 1 and failed[0]["tool"] == "mes.reschedule", failed
    assert len(rows) == len(BASE), f"{len(rows)} calls, expected {len(BASE)} (no retry, nothing skipped)"
    assert "escalate" not in tools_used(rows), "other writes succeeded, so no escalation"
    assert "1 failed call" in trace.summary, trace.summary
    return f"{len(rows) - 1} other calls ran"


@check("every write fails: escalated to a human once")
def _():
    _trace, rows = run(OUTAGE, lambda tool, n: tool in WRITE_TOOLS)
    writes = [r for r in rows if r["tool"] in WRITE_TOOLS]
    assert writes and not any(r["ok"] for r in writes)
    assert tools_used(rows).count("escalate") == 1 and rows[-1]["tool"] == "escalate" and rows[-1]["ok"]
    assert "no successful operational write" in rows[-1]["args"]["reason"], rows[-1]["args"]["reason"]
    return f"{len(writes)} writes failed"


@check("every write fails on a quality hold: escalated once")
def _():
    _trace, rows = run(QUALITY, lambda tool, n: tool in WRITE_TOOLS)
    assert tools_used(rows).count("escalate") == 1 and rows[-1]["tool"] == "escalate"


@check("escalate fails too: the event still finishes, nothing retried")
def _():
    trace, rows = run(OUTAGE, lambda tool, n: True)
    assert tools_used(rows).count("escalate") == 1, "escalate tried once, not retried"
    assert not any(r["ok"] for r in rows)
    assert trace.summary
    return f"{len(rows)} calls, all failed, trace written"


def _free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@check("enterprise server unreachable: every call fails, the run goes on")
def _():
    dead = _ServerTools(f"http://127.0.0.1:{_free_port()}")
    try:
        dead.call("E-04", "escalate", {"reason": "test"})
        raise AssertionError("an unreachable server must raise ToolError")
    except ToolError as exc:
        assert "no answer" in str(exc), exc
    trace = handle_event(GRAPH, dead, OUTAGE)
    assert "No operational write succeeded" in trace.summary, trace.summary
    return "ToolError instead of a crash, incident escalated"


@check("enterprise server over HTTP: good calls work, a rejected call is a failed call")
def _():
    from enterprise_server import Server, make_handler

    with tempfile.TemporaryDirectory() as tmp:
        ent = Enterprise(GRAPH.data_dir)
        port = _free_port()
        server = Server(("127.0.0.1", port), make_handler(ent, list(EVENTS.values()),
                                                           os.path.join(tmp, "action_log.jsonl"), threading.Lock()))
        threading.Thread(target=server.serve_forever, daemon=True).start()
        try:
            http = _ServerTools(f"http://127.0.0.1:{port}")
            rows = []

            class Recorder:
                def call(self, event_id, tool, args):
                    try:
                        out = http.call(event_id, tool, args)
                    except ToolError:
                        rows.append(False)
                        raise
                    rows.append(True)
                    return out

            handle_event(GRAPH, Recorder(), OUTAGE)
            assert len(rows) == len(BASE) and all(rows), f"{rows.count(True)}/{len(BASE)} calls ok over HTTP"
            try:
                http.call("E-04", "mes.reschedule", {"production_order_id": "PO-9999", "new_date": "2027-03-19"})
                raise AssertionError("an unknown production order must be rejected")
            except ToolError as exc:
                rejected = str(exc)
            assert "no answer" not in rejected, f"the server should have answered: {rejected}"
        finally:
            server.shutdown()
            server.server_close()
    return f"{len(rows)} calls ok, then the server said: {rejected}"


@check("the same write is not sent twice; a call with wrong arguments is not sent")
def _():
    tools = Flaky()
    door, executed = Gateway(tools), []
    order = next(r["args"] for r in BASE if r["tool"] == "mes.reschedule")
    call = ToolCall(tool="mes.reschedule", args=dict(order), reason="test", agent="test")
    assert door.execute("E-04", call, executed) is True
    assert door.execute("E-04", call, executed) is False, "duplicate write must not be sent"
    bad = ToolCall(tool="mes.reschedule", args={"order": "PO-0001"}, reason="test", agent="test")
    assert door.execute("E-04", bad, executed) is False
    unknown = ToolCall(tool="mes.delete_everything", args={}, reason="test", agent="test")
    assert door.execute("E-04", unknown, executed) is False
    assert len(tools.rows) == 1, f"only the first call may reach the tools, {len(tools.rows)} did"


@check("noise makes no calls, even when every tool would fail")
def _():
    _trace, rows = run(NOISE, lambda tool, n: True)
    assert rows == [], rows


# ---------------------------------------------------------------- no information

@check("empty message: no calls")
def _():
    for text in ("", "   \n  "):
        _trace, rows = run(message(text))
        assert rows == [], rows


@check("rumor with no details (E-02, E-13): one escalate, nothing else")
def _():
    for eid in ("E-02", "E-13"):
        only_one_escalate(run(EVENTS[eid])[1])


@check("plant down with no dates: one escalate, no writes")
def _():
    only_one_escalate(run(message("Huntsville plant is down."))[1])


@check("delay naming a shipment that does not exist: one escalate, no writes")
def _():
    only_one_escalate(run(message("Shipment SH-9999 is delayed to 2027-03-20."))[1])


@check("quality alert naming a lot that does not exist: one escalate, no writes")
def _():
    only_one_escalate(run(message("Quality alert: lot LOT-0999 is defective."))[1])


@check("real outage that touches no orders (a weekend): no calls")
def _():
    trace, rows = run(message("The Kentucky plant is dark from Saturday Mar 13 through Sunday Mar 14."))
    assert rows == [], tools_used(rows)
    return trace.summary[:80]


# ---------------------------------------------------------------- the model

class FakeModel:
    """Stands in for LLMReader. Named like the lookup model, so that step reuses it (no Ollama)."""

    def __init__(self, classify=None, fill=None, investigate=None):
        self.model, self.url, self.timeout, self.calls = TOOL_MODEL, "http://127.0.0.1:9", 1.0, 0
        self._classify, self._fill, self._investigate = classify, fill, investigate

    @staticmethod
    def _act(step, *args):
        if isinstance(step, Exception):
            raise step
        return step(*args) if callable(step) else step

    def classify(self, section):
        return self._act(self._classify, section)

    def fill(self, section, kind, options, previous=None, problem=None, findings=""):
        return self._act(self._fill, section, kind, options)

    def investigate(self, section, kind, problem, lookups, max_calls=6):
        return self._act(self._investigate if self._investigate is not None else "", section)

    def extract(self, section, previous=None, problem=None):
        raise LLMUnavailable("not used")


def same_calls(a, b):
    return [(r["tool"], r["args"]) for r in a] == [(r["tool"], r["args"]) for r in b]


@check("Ollama down: the rule reader takes over, same calls as rules only")
def _():
    trace, rows = run(OUTAGE, llm=FakeModel(classify=LLMUnavailable("connection refused")))
    assert same_calls(rows, BASE), "calls differ from the rule reader's"
    assert all(i.reader == "rules" for i in trace.incidents)


@check("model returns broken output: the rule reader takes over, same calls")
def _():
    _trace, rows = run(OUTAGE, llm=FakeModel(classify=ValueError("model returned non-JSON: 'Sure! Here'")))
    assert same_calls(rows, BASE)


@check("model names an outage but picks nothing: one escalate asking what is missing")
def _():
    blank = lambda section, kind, options: {"plant": "", "first_day": "", "last_day": "", "end_meaning": "last day down"}
    trace, rows = run(OUTAGE, llm=FakeModel(classify={"kind": "plant_outage", "reason": "the plant is dark for days"},
                                            fill=blank))
    only_one_escalate(rows)
    asked = [i.question for i in trace.incidents if getattr(i, "question", "")]
    assert asked, "the escalation should ask for what is missing"
    return f"asked: {asked[0]}"


@check("model answers step 1, then Ollama dies: no writes, one escalate")
def _():
    trace, rows = run(OUTAGE, llm=FakeModel(classify={"kind": "plant_outage", "reason": "the plant is dark for days"},
                                            fill=LLMUnavailable("connection reset"),
                                            investigate=LLMUnavailable("connection reset")))
    only_one_escalate(rows)


@check("model calls a brochure question an outage: no writes")
def _():
    _trace, rows = run(NOISE, llm=FakeModel(classify={"kind": "plant_outage", "reason": "a plant is mentioned somewhere"},
                                            fill=lambda s, k, o: {"plant": "", "first_day": "", "last_day": "",
                                                                  "end_meaning": "last day down"}))
    assert not [r for r in rows if r["tool"] in WRITE_TOOLS], tools_used(rows)


if __name__ == "__main__":
    failed = sum(not ok for ok, _ in RESULTS)
    print(f"\n{len(RESULTS) - failed}/{len(RESULTS)} failure checks pass")
    sys.exit(failed)
