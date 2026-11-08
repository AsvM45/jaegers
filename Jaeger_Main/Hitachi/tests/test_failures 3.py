"""Failed tool calls are handled gracefully (docx: "graceful handling of failed calls").

    python tests/test_failures.py

Injects ToolErrors into the enterprise tools while the coordinator handles a real outage
(E-04) and checks the behaviour the coordinator promises:

1. One failed write is logged as ok=False, not retried, and every other planned call still runs.
2. When every write fails, the incident is escalated to a human instead of disappearing.
3. A failure on a noise event cannot happen, because noise makes no calls.
"""

from __future__ import annotations

import os
import sys

HITACHI = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HITACHI)

from enterprise import Enterprise, ToolError, load_events  # noqa: E402
from tower.agents.coordinator import handle_event  # noqa: E402
from tower.contracts import WRITE_TOOLS  # noqa: E402
from tower.graph import WorldGraph  # noqa: E402


class Flaky:
    """Enterprise wrapper that fails the calls `fail(tool, n)` picks; n counts calls so far."""

    def __init__(self, enterprise, fail):
        self.enterprise, self.fail, self.rows = enterprise, fail, []

    def call(self, event_id, tool, args):
        n = len(self.rows)
        if self.fail(tool, n):
            self.rows.append({"tool": tool, "args": args, "ok": False})
            raise ToolError("injected failure")
        result = self.enterprise.call(event_id, tool, args)
        self.rows.append({"tool": tool, "args": args, "ok": True})
        return result


def run(event, fail):
    graph = WorldGraph()
    tools = Flaky(Enterprise(graph.data_dir), fail)
    trace = handle_event(graph, tools, event)  # rule reader: no model needed for this test
    return trace, tools.rows


def main() -> None:
    events = {e["event_id"]: e for e in load_events(os.path.join(WorldGraph().data_dir, "events.json"))}
    outage, noise = events["E-04"], events["E-05"]

    base_trace, base = run(outage, lambda tool, n: False)
    assert base and all(r["ok"] for r in base)

    # 1. The first reschedule fails.
    first = next(i for i, r in enumerate(base) if r["tool"] == "mes.reschedule")
    trace, rows = run(outage, lambda tool, n: n == first)
    failed = [r for r in rows if not r["ok"]]
    assert len(failed) == 1 and failed[0]["tool"] == "mes.reschedule", failed
    assert len(rows) == len(base), "every other planned call still ran, and nothing was retried"
    assert "escalate" not in [r["tool"] for r in rows], "other writes succeeded, so no escalation"
    assert "1 failed call" in trace.summary, trace.summary
    print(f"ok  one failed write: logged ok=False, {len(rows) - 1} other calls ran, summary says so")

    # 2. Every write fails.
    trace, rows = run(outage, lambda tool, n: tool in WRITE_TOOLS)
    writes = [r for r in rows if r["tool"] in WRITE_TOOLS]
    assert writes and not any(r["ok"] for r in writes)
    assert rows[-1]["tool"] == "escalate" and rows[-1]["ok"], rows[-1]
    assert "no successful operational write" in rows[-1]["args"]["reason"]
    print(f"ok  all {len(writes)} writes failed: incident escalated to a human once")

    # 3. Noise makes no calls, so nothing can fail.
    _trace, rows = run(noise, lambda tool, n: True)
    assert rows == []
    print("ok  noise: no calls even when every tool would fail")
    print("PASS")


if __name__ == "__main__":
    main()
