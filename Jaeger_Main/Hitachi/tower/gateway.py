"""The only door to Enterprise.call.

A call that is not in enterprise.TOOLS, or whose arguments do not match that
schema, is recorded and not sent. A second identical write in the same event
is not sent either. List order matters; key order does not. Reads and
escalate are not part of that ledger. A ToolError is recorded, not retried,
and does not leave this module.
"""

from __future__ import annotations

import re

from enterprise import TOOLS, ToolError
from tower.contracts import ToolCall

_DATE_SHAPE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _schema_ok(tool: str, args) -> bool:
    """True when `tool` is in enterprise.TOOLS and every required arg matches.

    "str" is a non-empty str. "list[str]" is a non-empty list of non-empty
    str. "YYYY-MM-DD" is a str of that shape.
    """
    spec = TOOLS.get(tool)
    if spec is None or not isinstance(args, dict):
        return False
    if set(args) != set(spec["args"]):
        return False
    for name, kind in spec["args"].items():
        if not _arg_ok(kind, args.get(name)):
            return False
    return True


def _arg_ok(kind: str, value) -> bool:
    if kind == "str":
        return isinstance(value, str) and bool(value)
    if kind == "list[str]":
        return (
            isinstance(value, list)
            and bool(value)
            and all(isinstance(item, str) and item for item in value)
        )
    if kind == "YYYY-MM-DD":
        return isinstance(value, str) and _DATE_SHAPE.fullmatch(value) is not None
    return False


def _write_key(call: ToolCall) -> tuple:
    """Stable identity of a write. Key order does not matter; list order does."""
    frozen = []
    for key in sorted(call.args):
        value = call.args[key]
        if isinstance(value, list):
            value = tuple(value)
        frozen.append((key, value))
    return (call.tool, tuple(frozen))


def _execute(
    enterprise,
    event_id: str,
    call: ToolCall,
    executed: list[tuple[ToolCall, bool]],
    sent_writes: set[tuple],
) -> bool:
    """Run one call. A rejected call is recorded and is not retried.

    A tool or argument that does not match enterprise.TOOLS is recorded as
    not ok and is not sent. A write whose tool and args already succeeded in
    this event is recorded as not sent. Reads and escalate stay off that
    ledger. A ToolError is recorded and does not stop the rest.
    """
    if not _schema_ok(call.tool, call.args):
        executed.append((call, False))
        return False
    key = _write_key(call) if call.writes else None
    if key is not None and key in sent_writes:
        executed.append((call, False))
        return False
    try:
        enterprise.call(event_id, call.tool, call.args)
    except ToolError:
        executed.append((call, False))
        return False
    if key is not None:
        sent_writes.add(key)
    executed.append((call, True))
    return True


class Gateway:
    """One event's door. The write ledger lives here for that event only."""

    def __init__(self, enterprise) -> None:
        self._enterprise = enterprise
        self._sent_writes: set[tuple] = set()

    def execute(
        self,
        event_id: str,
        call: ToolCall,
        executed: list[tuple[ToolCall, bool]],
    ) -> bool:
        """Send one call through the schema check and this event's ledger."""
        return _execute(self._enterprise, event_id, call, executed, self._sent_writes)
