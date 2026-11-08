"""Control-tower coordinator.

Understand the message, ask the specialist that owns each real incident, then
send the accepted tool calls through the enterprise gateway in a fixed order:
supply, quality, dealer. Noise writes nothing. An unconfirmed report is
escalate and nothing else. A confirmed incident is escalated once when a
write was attempted and every write failed. A confirmed incident with
nothing to write is left alone.

Every Enterprise.call goes through tower.gateway. The gateway records a call
that is not in enterprise.TOOLS, or whose arguments do not match that schema,
and does not send it. A second identical write in the same event is not sent
either. Reads and escalate are not part of that ledger.
"""

from __future__ import annotations

from tower.agents.dealer_customer import plan_dealer_customer
from tower.agents.quality import plan_quality
from tower.agents.supply_chain import plan_supply
from tower.agents.understand import understand
from tower.calendar_util import event_day
from tower.contracts import EventTrace, ToolCall
from tower.gateway import Gateway, _arg_ok, _execute, _schema_ok, _write_key
from tower.schedule import LoanerPools, PlantSchedule

__all__ = [
    "handle_event",
    "_execute",
    "_schema_ok",
    "_arg_ok",
    "_write_key",
]

_REAL = frozenset({"supplier_delay", "plant_outage", "quality_hold"})
_SUPPLY = frozenset({"supplier_delay", "plant_outage"})
_GUARDRAIL = (
    "Noise writes nothing; an unconfirmed report is escalate only; "
    "confirmed incidents change only the affected records."
)
_WRITE_WORDS = {
    "mes.reschedule": ("reschedule", "reschedules"),
    "mes.transfer": ("transfer", "transfers"),
    "dealer.notify": ("dealer notice", "dealer notices"),
    "dealer.stop_sale": ("stop-sale", "stop-sales"),
    "crm.assign_loaner": ("loaner assignment", "loaner assignments"),
    "crm.notify_customer": ("customer notice", "customer notices"),
    "quality.hold_lot": ("lot hold", "lot holds"),
}


def handle_event(graph, enterprise, event: dict) -> EventTrace:
    """Classify one event, plan it, and execute the accepted tool calls."""
    incidents = understand(graph, event["text"], anchor=event_day(event.get("received_at")))
    real = [incident for incident in incidents if incident.kind in _REAL]
    classification = "+".join(incident.kind for incident in incidents)
    results = []
    executed: list[tuple[ToolCall, bool]] = []
    door = Gateway(enterprise)

    if not real:
        if any(incident.kind == "unconfirmed" for incident in incidents):
            reason = " ".join(
                incident.summary for incident in incidents if incident.kind == "unconfirmed"
            )
            door.execute(
                event["event_id"],
                ToolCall(tool="escalate", args={"reason": reason}, reason=reason),
                executed,
            )
        summary = _quiet_summary(incidents, escalated=bool(executed))
    else:
        schedule = PlantSchedule(graph)
        pools = LoanerPools(graph)
        supply_incidents = [incident for incident in incidents if incident.kind in _SUPPLY]
        quality_incidents = [incident for incident in incidents if incident.kind == "quality_hold"]
        supply_result = None
        quality_result = None
        dealer_result = None

        if supply_incidents:
            supply_result = plan_supply(graph, schedule, supply_incidents)
            results.append(supply_result)
        if quality_incidents:
            quality_result = plan_quality(graph, quality_incidents)
            results.append(quality_result)

        orders = []
        if supply_result is not None:
            orders = graph.customer_orders_for(supply_result.affected_ids)
        if orders:
            reason = " ".join(incident.summary for incident in real)
            dealer_result = plan_dealer_customer(graph, pools, orders, reason)
            results.append(dealer_result)

        planned: list[ToolCall] = []
        if supply_result is not None:
            planned.extend(supply_result.calls)
        if quality_result is not None:
            planned.extend(quality_result.calls)
        if dealer_result is not None:
            planned.extend(dealer_result.calls)

        attempted_writes = 0
        successful_writes = 0
        for call in planned:
            ok = door.execute(event["event_id"], call, executed)
            if not call.writes:
                continue
            attempted_writes += 1
            if ok:
                successful_writes += 1
        if attempted_writes and successful_writes == 0:
            reason = _failed_write_reason(real, executed)
            door.execute(
                event["event_id"],
                ToolCall(tool="escalate", args={"reason": reason}, reason=reason),
                executed,
            )
        summary = _real_summary(
            graph,
            incidents,
            supply_result,
            quality_result,
            dealer_result,
            executed,
            successful_writes,
        )

    return EventTrace(
        event_id=event["event_id"],
        source=event["source"],
        received_at=event["received_at"],
        text=event["text"],
        classification=classification,
        incidents=incidents,
        results=results,
        calls=[call for call, _ok in executed],
        summary=summary,
        guardrail=_GUARDRAIL,
    )


def _failed_write_reason(real, executed: list[tuple[ToolCall, bool]]) -> str:
    summaries = " ".join(incident.summary for incident in real)
    attempted = any(call.writes for call, _ok in executed)
    if attempted:
        return (
            "Confirmed incident produced no successful operational write, so it is escalated "
            "instead of leaving a half-applied story unlogged. "
            + summaries
        )
    return (
        "Confirmed incident produced no operational write, so it is escalated "
        "instead of being left unlogged. "
        + summaries
    )


def _quiet_summary(incidents, escalated: bool) -> str:
    said = " ".join(incident.summary for incident in incidents)
    if escalated:
        return (
            f"{said} "
            "No operational records were changed. "
            "The tower escalated the report and wrote nothing else."
        )
    return (
        f"{said} "
        "No operational records are affected. "
        "Nothing was written."
    )


def _real_summary(graph, incidents, supply_result, quality_result, dealer_result, executed, successful_writes) -> str:
    headlines = [_headline(graph, incident) for incident in incidents]
    what = "The message reports " + _join(headlines) + "."
    affected = _affected_sentence(supply_result, quality_result, dealer_result)
    done = _done_sentence(executed, successful_writes)
    return f"{what} {affected} {done}"


def _headline(graph, incident) -> str:
    if incident.kind == "plant_outage":
        return (
            f"a plant outage at {_named(graph.plants, incident.plant_id)} "
            f"from {incident.outage_start} through {incident.outage_end}"
        )
    if incident.kind == "supplier_delay":
        load = f" on shipment {incident.shipment_id}" if incident.shipment_id else ""
        return (
            f"a supplier delay of {_named(graph.parts, incident.part_id)} "
            f"from {_named(graph.suppliers, incident.supplier_id)} "
            f"into {_named(graph.plants, incident.plant_id)} "
            f"from {incident.blocked_from} until {incident.blocked_until}{load}"
        )
    if incident.kind == "quality_hold":
        subject = f"lot {incident.lot_id}" if incident.lot_id else _named(graph.parts, incident.part_id)
        return (
            f"a quality hold on {subject} at {_named(graph.plants, incident.plant_id)} "
            f"for builds {incident.build_start} through {incident.build_end}"
        )
    if incident.kind == "unconfirmed":
        return "an unconfirmed report that is not safe to act on"
    return "a note that is not an operational disruption"


def _affected_sentence(supply_result, quality_result, dealer_result) -> str:
    bits = []
    if supply_result is not None:
        bits.append(_count(len(supply_result.affected_ids), "production order"))
    if quality_result is not None:
        bits.append(_count(len(quality_result.affected_ids), "quality record"))
    if dealer_result is not None:
        bits.append(_count(len(dealer_result.affected_ids), "customer order"))
    if not bits:
        return "No affected records were identified."
    return "Affected records: " + _join(bits) + "."


def _done_sentence(executed: list[tuple[ToolCall, bool]], successful_writes: int) -> str:
    if successful_writes == 0:
        attempted = any(call.writes for call, _ok in executed)
        if not attempted:
            return "No operational write was required."
        return (
            "No operational write succeeded, so the tower escalated the incident "
            "instead of leaving it unlogged."
        )
    counts: dict[str, int] = {}
    order: list[str] = []
    failed = 0
    for call, ok in executed:
        if not ok:
            failed += 1
            continue
        if not call.writes:
            continue
        if call.tool not in counts:
            order.append(call.tool)
            counts[call.tool] = 0
        counts[call.tool] += 1
    pieces = []
    for tool in order:
        singular, plural = _WRITE_WORDS.get(tool, (tool, tool))
        pieces.append(_count(counts[tool], singular, plural))
    sentence = "The tower completed " + _join(pieces)
    if failed:
        word = "call" if failed == 1 else "calls"
        sentence += f"; {failed} failed {word} were not retried"
    return sentence + "."


def _named(table: dict, entity_id: str | None) -> str:
    if not entity_id:
        return "an unnamed record"
    row = table.get(entity_id)
    if row and row.get("name"):
        return f"{row['name']} ({entity_id})"
    return entity_id


def _count(n: int, singular: str, plural: str | None = None) -> str:
    word = singular if n == 1 else (plural or singular + "s")
    return f"{n} {word}"


def _join(items: list[str]) -> str:
    if not items:
        return ""
    if len(items) == 1:
        return items[0]
    if len(items) == 2:
        return f"{items[0]} and {items[1]}"
    return ", ".join(items[:-1]) + ", and " + items[-1]
