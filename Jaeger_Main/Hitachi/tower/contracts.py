"""Shared types for the Wacky Wheels control tower.

The coordinator owns the pipeline. Specialists accept these types and return
plans. Nothing in here calls a tool or reads an event id's expected answer.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Literal

# The five kinds of message the handbook defines. A compound message becomes several Incidents,
# one per section.
IncidentKind = Literal[
    "supplier_delay",
    "plant_outage",
    "quality_hold",
    "noise",
    "unconfirmed",
]

# Tools that change the world. Reads and escalate are not in this set.
WRITE_TOOLS = frozenset({
    "mes.reschedule",
    "mes.transfer",
    "dealer.notify",
    "dealer.stop_sale",
    "crm.assign_loaner",
    "crm.notify_customer",
    "quality.hold_lot",
})


# Produced by WorldGraph.resolve_mentions(). start/end are character offsets in the text.
@dataclass
class Mention:
    """One entity spotted in event text, resolved through aliases or an id."""

    alias: str
    entity_type: str
    entity_id: str
    start: int
    end: int


# Output of step 1 (understand.py). Each kind fills only the fields it needs; the rest stay None.
@dataclass
class Incident:
    """One incident inside an event. A compound message yields several."""

    kind: IncidentKind
    summary: str
    supplier_id: str | None = None
    part_id: str | None = None
    plant_id: str | None = None
    shipment_id: str | None = None
    lot_id: str | None = None
    # Supplier delay: builds are blocked on [blocked_from, blocked_until).
    blocked_from: str | None = None
    blocked_until: str | None = None
    # Plant outage, inclusive working days.
    outage_start: str | None = None
    outage_end: str | None = None
    # Quality window used to identify the lot, inclusive.
    build_start: str | None = None
    build_end: str | None = None
    evidence: list[str] = field(default_factory=list)
    # Who produced this reading: the model name when its output was verified,
    # or "rules" when the deterministic reader was used.
    reader: str = "rules"

    def to_dict(self) -> dict[str, Any]:
        """Plain dict for traces.json; every field is already JSON-safe."""
        return asdict(self)


# One planned enterprise tool call plus a plain-English reason. Specialists create these; only the
# coordinator executes them.
@dataclass
class ToolCall:
    """A planned call: tool name and args exactly as POST /act takes them, plus the reason
    shown in the trace and UI."""

    tool: str
    args: dict[str, Any]
    reason: str

    @property
    def writes(self) -> bool:
        """True for calls that change the world. The coordinator counts these to decide
        whether a confirmed incident did anything, or must be escalated."""
        return self.tool in WRITE_TOOLS

    def to_dict(self) -> dict[str, Any]:
        return {"tool": self.tool, "args": self.args, "reason": self.reason, "writes": self.writes}


# What a specialist hands back to the coordinator: the affected records, the graph paths that
# prove it, and its planned calls.
@dataclass
class SpecialistResult:
    """One specialist's answer: affected ids, the graph paths that cite them, and planned calls."""

    agent: str
    affected_ids: list[str]
    graph_paths: list[list[str]]
    calls: list[ToolCall]
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "agent": self.agent,
            "affected_ids": self.affected_ids,
            "graph_paths": self.graph_paths,
            "calls": [c.to_dict() for c in self.calls],
            "notes": self.notes,
        }


# One per event. run.py writes the list to runs/run1/traces.json and the UI reads it.
@dataclass
class EventTrace:
    """What the control tower shows for one event, and what we keep for audit."""

    event_id: str
    source: str
    received_at: str
    text: str
    classification: str
    incidents: list[Incident]
    results: list[SpecialistResult]
    calls: list[ToolCall]
    summary: str
    guardrail: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "source": self.source,
            "received_at": self.received_at,
            "text": self.text,
            "classification": self.classification,
            "incidents": [i.to_dict() for i in self.incidents],
            "results": [r.to_dict() for r in self.results],
            "calls": [c.to_dict() for c in self.calls],
            "summary": self.summary,
            "guardrail": self.guardrail,
        }
