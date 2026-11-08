"""Control-tower coordinator: the one coordinating agent of the docx.

Understand the message, hand each real incident to the specialist agent that owns it (roster.py),
check every planned call against that agent's allowed tools, then send the accepted calls through
the enterprise gateway in a fixed order: supply, quality, dealer. Noise writes nothing. An
unconfirmed report is escalate and nothing else. A confirmed incident is escalated once when a
write was attempted and every write failed; a confirmed incident with nothing to write is left
alone. Every handoff is recorded in the trace.

Every Enterprise.call goes through tower.gateway. The gateway records a call that is not in
enterprise.TOOLS, or whose arguments do not match that schema, and does not send it. A second
identical write in the same event is not sent either. Reads and escalate are not part of that
ledger. Relative dates in a message are measured from the day it was received (event_day).
"""

from __future__ import annotations

from tower.agents.roster import COORDINATOR, DEALER, QUALITY, SUPPLY, Agent
from tower.agents.understand import understand
from tower.calendar_util import event_day
from tower.contracts import EventTrace, ToolCall
from tower.gateway import Gateway, _arg_ok, _execute, _schema_ok, _write_key
from tower.schedule import LoanerPools, PlantSchedule

# tower/tests/test_edges.py imports _execute and the gateway checks from here.
__all__ = [
    "handle_event",
    "_execute",
    "_schema_ok",
    "_arg_ok",
    "_write_key",
]

# Kinds that change records, and the two that go to the supply planner. Quality holds go to the
# quality agent; noise and unconfirmed never reach a specialist.
_REAL = frozenset({"supplier_delay", "plant_outage", "quality_hold"})
_SUPPLY = frozenset({"supplier_delay", "plant_outage"})
_GUARDRAIL = (
    "Noise writes nothing; an unconfirmed report is escalate only; "
    "confirmed incidents change only the affected records."
)
# Singular/plural wording for the plain-English event summary. Only write tools are listed;
# reads and escalate are not counted as "completed" work.
_WRITE_WORDS = {
    "mes.reschedule": ("reschedule", "reschedules"),
    "mes.transfer": ("transfer", "transfers"),
    "dealer.notify": ("dealer notice", "dealer notices"),
    "dealer.stop_sale": ("stop-sale", "stop-sales"),
    "crm.assign_loaner": ("loaner assignment", "loaner assignments"),
    "crm.notify_customer": ("customer notice", "customer notices"),
    "quality.hold_lot": ("lot hold", "lot holds"),
}


# THE PIPELINE. run.py calls this once per event.
def handle_event(graph, enterprise, event: dict, llm=None) -> EventTrace:
    """Classify one event, plan it, and execute the accepted tool calls.

    enterprise is anything with call(event_id, tool, args): Enterprise itself, run._CallLog,
    or a test fake. llm is an LLMReader, or None for the rule reader only.
    Specialists only plan. Every call that reaches Enterprise is made here, in _execute.
    """
    # Step 1 - understand: read the message into incidents.
    incidents = understand(graph, event["text"], llm, anchor=event_day(event.get("received_at")))
    real = [incident for incident in incidents if incident.kind in _REAL]
    classification = "+".join(incident.kind for incident in incidents)
    results = []
    executed: list[tuple[ToolCall, bool]] = []
    door = Gateway(enterprise)   # schema check and this event's write ledger
    readers = sorted({incident.reader for incident in incidents})
    handoffs: list[dict] = [{
        "from": COORDINATOR.id,
        "to": "reader",
        "task": "Read the message into incidents (LLM proposes, rule check verifies).",
        "returned": f"{len(incidents)} incident{'' if len(incidents) == 1 else 's'}: {classification}"
                    f" (read by {', '.join(readers)})",
    }]

    # Quiet path: noise -> no calls; unconfirmed -> exactly one escalate to a human.
    if not real:
        if any(incident.kind == "unconfirmed" for incident in incidents):
            reason = " ".join(
                incident.summary for incident in incidents if incident.kind == "unconfirmed"
            )
            door.execute(
                event["event_id"],
                ToolCall(tool="escalate", args={"reason": reason}, reason=reason, agent=COORDINATOR.id),
                executed,
            )
            handoffs.append(_tool_handoff("Unconfirmed report: escalate to a human, change nothing.", executed))
        else:
            handoffs.append({"from": COORDINATOR.id, "to": COORDINATOR.id,
                             "task": "Noise: no specialist is needed.", "returned": "No tool calls."})
        summary = _quiet_summary(incidents, escalated=bool(executed))
    else:
        # Real path. A fresh slot board and loaner pools, shared by every incident in this event.
        schedule = PlantSchedule(graph)
        pools = LoanerPools(graph)
        supply_incidents = [incident for incident in incidents if incident.kind in _SUPPLY]
        quality_incidents = [incident for incident in incidents if incident.kind == "quality_hold"]
        supply_result = None
        quality_result = None
        dealer_result = None

        # Steps 2-3 - find impact and plan: each specialist queries the graph and returns planned
        # calls.
        if supply_incidents:
            supply_result = _accept(SUPPLY, SUPPLY.plan(graph, schedule, supply_incidents),
                                    _task(supply_incidents), handoffs)
            results.append(supply_result)
        if quality_incidents:
            quality_result = _accept(QUALITY, QUALITY.plan(graph, quality_incidents),
                                     _task(quality_incidents), handoffs)
            results.append(quality_result)

        # Dealer and Customer Care only sees customer orders behind the production orders the
        # supply planner moved. Quality holds skip it (rule 6 has no dealer notice or loaner).
        orders = []
        if supply_result is not None:
            orders = graph.customer_orders_for(supply_result.affected_ids)
        if orders:
            reason = " ".join(incident.summary for incident in real)
            dealer_result = _accept(
                DEALER, DEALER.plan(graph, pools, orders, reason),
                f"Notify dealers and assign loaners for {len(orders)} customer orders behind the "
                f"{len(supply_result.affected_ids)} moved production orders.", handoffs)
            results.append(dealer_result)

        # Step 4 - act, in a fixed order: production moves, then quality, then dealers and
        # loaners.
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
            if call.writes:
                attempted_writes += 1
                successful_writes += ok
        handoffs.append(_tool_handoff(
            "Execute the accepted calls in order: production moves, quality, dealers and loaners.", executed))
        # Failed calls are not retried: the tools reject only invalid moves (full slot, empty pool),
        # and retrying the same args would fail the same way and cost efficiency points.
        if attempted_writes and successful_writes == 0:
            # Guardrail: every write was rejected, so the incident goes to a human instead of
            # disappearing. A confirmed incident with nothing to write (no future orders) is left
            # alone: there is nothing for a human to fix.
            reason = _failed_write_reason(real, executed)
            door.execute(
                event["event_id"],
                ToolCall(tool="escalate", args={"reason": reason}, reason=reason, agent=COORDINATOR.id),
                executed,
            )
            handoffs.append(_tool_handoff("Confirmed incident changed nothing: escalate.", executed[-1:]))
        # Rule 8 still applies inside a real event: a rumor section goes to a human.
        rumors = [incident.summary for incident in incidents if incident.kind == "unconfirmed"]
        if rumors and (successful_writes > 0 or not attempted_writes):
            reason = " ".join(rumors)
            door.execute(
                event["event_id"],
                ToolCall(tool="escalate", args={"reason": reason}, reason=reason, agent=COORDINATOR.id),
                executed,
            )
            handoffs.append(_tool_handoff("Rumor inside a real event: escalate that part.", executed[-1:]))
        summary = _real_summary(
            graph,
            incidents,
            supply_result,
            quality_result,
            dealer_result,
            executed,
            successful_writes,
        )

    # Step 5 - record everything the UI and the audit need for this event.
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
        handoffs=handoffs,
    )


def _task(incidents) -> str:
    """The instruction a specialist receives: its incidents, in one line."""
    return "Plan for " + "; ".join(f"{i.kind}: {i.summary.rstrip('.')}" for i in incidents) + "."


def _accept(agent: Agent, result, task: str, handoffs: list[dict]):
    """Validate a specialist's plan before anything runs: keep only calls to tools on the agent's
    card, tag each with the agent, and record the handoff. A refused call is never executed."""
    kept, refused = [], []
    for call in result.calls:
        if agent.allows(call.tool):
            call.agent = agent.id
            kept.append(call)
        else:
            refused.append(call)
    if refused:
        result.calls = kept
        result.notes.append(
            f"Coordinator refused {len(refused)} planned call(s) outside {agent.card.title}'s tools: "
            + ", ".join(sorted({c.tool for c in refused})) + "."
        )
    handoffs.append({
        "from": COORDINATOR.id,
        "to": agent.id,
        "task": task,
        "returned": f"{len(result.affected_ids)} affected records, {len(result.calls) + len(refused)} planned calls",
        "accepted": len(kept),
        "refused": [c.tool for c in refused],
    })
    return result


def _tool_handoff(task: str, executed: list[tuple[ToolCall, bool]]) -> dict:
    """The coordinator's own step of calling the enterprise tools."""
    failed = sum(not ok for _call, ok in executed)
    return {
        "from": COORDINATOR.id,
        "to": "enterprise",
        "task": task,
        "returned": f"{len(executed)} call{'' if len(executed) == 1 else 's'}, {failed} failed",
    }


def _failed_write_reason(real, executed: list[tuple[ToolCall, bool]]) -> str:
    """Escalation text for a confirmed incident that changed nothing. It says whether writes
    were tried and rejected, or none were planned at all."""
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
    """Summary for noise and unconfirmed events: what was read and that nothing was written."""
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


# --- Plain-English summary helpers for the trace and UI.
def _real_summary(graph, incidents, supply_result, quality_result, dealer_result, executed, successful_writes) -> str:
    """Three sentences for the UI: what was reported, what it touched, what the tower did."""
    headlines = [_headline(graph, incident) for incident in incidents]
    what = "The message reports " + _join(headlines) + "."
    affected = _affected_sentence(supply_result, quality_result, dealer_result)
    done = _done_sentence(executed, successful_writes)
    return f"{what} {affected} {done}"


def _headline(graph, incident) -> str:
    """One noun phrase per incident, e.g. "a plant outage at Wacky Wheels Lexington (P_KY) ..."."""
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
    """Counts of affected records per specialist that ran."""
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
    """Successful writes counted by tool, in first-seen order, plus a count of failed calls."""
    if successful_writes == 0:
        if not any(call.writes for call, _ok in executed):
            return "No future record needed to change, so nothing was written."
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
    """"Name (ID)" when the table has a name, else the bare id."""
    if not entity_id:
        return "an unnamed record"
    row = table.get(entity_id)
    if row and row.get("name"):
        return f"{row['name']} ({entity_id})"
    return entity_id


def _count(n: int, singular: str, plural: str | None = None) -> str:
    """"1 reschedule" / "3 reschedules"; plural defaults to singular + "s"."""
    word = singular if n == 1 else (plural or singular + "s")
    return f"{n} {word}"


def _join(items: list[str]) -> str:
    """English list: "a", "a and b", "a, b, and c"."""
    if not items:
        return ""
    if len(items) == 1:
        return items[0]
    if len(items) == 2:
        return f"{items[0]} and {items[1]}"
    return ", ".join(items[:-1]) + ", and " + items[-1]
