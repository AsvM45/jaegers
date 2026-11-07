"""Supply-chain planner for supplier delays and plant outages.

Handbook rules 1-3. The graph decides who is affected. This module only
moves those production orders:

- same plant first, on the earliest free day at or after the new ETA or the
  restart day, and only through the planning window (indexes 0..19)
- transfer only when that plant has no free day in that range, to the
  earliest free day at another plant that builds the model
- a delayed part blocks only the receiving plant, and an outage blocks only
  that plant, so the other plant may build on any open day in the window
"""

from __future__ import annotations

from collections import defaultdict
from datetime import date

from tower.calendar_util import LAST_IDX, date_to_idx, idx_to_date
from tower.contracts import Incident, SpecialistResult, ToolCall
from tower.graph import WorldGraph
from tower.schedule import PlantSchedule, restart_index

# Exclusive end. LAST_IDX is 19, so this is range(..., 20): today through 2027-04-02.
_HORIZON = LAST_IDX + 1

# production order id -> (earliest index, "delay" | "outage", constraint date)
_Slot = tuple[int, str, str]


def plan_supply(
    graph: WorldGraph,
    schedule: PlantSchedule,
    incidents: list[Incident],
) -> SpecialistResult:
    """Return reschedule and transfer calls for one event's supply incidents."""
    notes: list[str] = []
    graph_paths: list[list[str]] = []
    pending: dict[str, _Slot] = {}

    for incident in incidents:
        if incident.kind == "supplier_delay":
            _take_delay(graph, incident, pending, graph_paths, notes)
        elif incident.kind == "plant_outage":
            _take_outage(graph, incident, pending, graph_paths, notes)

    calls: list[ToolCall] = []
    # Original build day, then id, so earlier orders take earlier free slots.
    place_order = sorted(pending, key=lambda po_id: (graph.orders[po_id]["idx"], po_id))
    for po_id in place_order:
        schedule.release(po_id)
    for po_id in place_order:
        earliest, kind, constraint = pending[po_id]
        _place(graph, schedule, po_id, earliest, kind, constraint, calls, notes)

    return SpecialistResult(
        agent="supply_chain",
        affected_ids=sorted(pending),
        graph_paths=graph_paths,
        calls=calls,
        notes=notes,
    )


def _keep_later(pending: dict[str, _Slot], po_id: str, earliest: int, kind: str, constraint: str) -> None:
    """Two incidents on one order: the later earliest day is the binding one."""
    current = pending.get(po_id)
    if current is None or earliest > current[0]:
        pending[po_id] = (earliest, kind, constraint)


def _take_delay(
    graph: WorldGraph,
    incident: Incident,
    pending: dict[str, _Slot],
    graph_paths: list[list[str]],
    notes: list[str],
) -> None:
    plant_id = incident.plant_id
    part_id = incident.part_id
    blocked_from = incident.blocked_from
    blocked_until = incident.blocked_until
    if not (plant_id and part_id and blocked_from and blocked_until):
        notes.append(
            "Skipped supplier delay: plant_id, part_id, blocked_from, and blocked_until are required "
            f"(plant_id={plant_id!r}, part_id={part_id!r}, "
            f"blocked_from={blocked_from!r}, blocked_until={blocked_until!r})."
        )
        return
    try:
        date_to_idx(date.fromisoformat(blocked_from))
        earliest = date_to_idx(date.fromisoformat(blocked_until))
    except (TypeError, ValueError) as exc:
        notes.append(
            f"Skipped supplier delay of {part_id} at {plant_id}: "
            f"{blocked_from} .. {blocked_until} is not a working-day window ({exc})."
        )
        return

    orders = graph.affected_orders_delay(plant_id, part_id, blocked_from, blocked_until)
    _cite_delay(graph, incident, part_id, plant_id, orders, graph_paths, notes)
    for po in orders:
        _keep_later(pending, po["production_order_id"], earliest, "delay", blocked_until)


def _take_outage(
    graph: WorldGraph,
    incident: Incident,
    pending: dict[str, _Slot],
    graph_paths: list[list[str]],
    notes: list[str],
) -> None:
    plant_id = incident.plant_id
    outage_start = incident.outage_start
    outage_end = incident.outage_end
    if not (plant_id and outage_start and outage_end):
        notes.append(
            "Skipped plant outage: plant_id, outage_start, and outage_end are required "
            f"(plant_id={plant_id!r}, outage_start={outage_start!r}, outage_end={outage_end!r})."
        )
        return
    try:
        date.fromisoformat(outage_start)
        earliest = restart_index(outage_end)
    except (TypeError, ValueError) as exc:
        notes.append(
            f"Skipped plant outage at {plant_id}: "
            f"cannot take the working day after {outage_end} ({exc})."
        )
        return

    orders = graph.affected_orders_outage(plant_id, outage_start, outage_end)
    order_ids = [po["production_order_id"] for po in orders]
    graph_paths.extend(graph.outage_paths(plant_id, orders, graph.customer_orders_for(order_ids)))
    restart = idx_to_date(earliest).isoformat()
    for po in orders:
        _keep_later(pending, po["production_order_id"], earliest, "outage", restart)


def _cite_delay(
    graph: WorldGraph,
    incident: Incident,
    part_id: str,
    plant_id: str,
    orders: list[dict],
    graph_paths: list[list[str]],
    notes: list[str],
) -> None:
    customer_orders = graph.customer_orders_for([po["production_order_id"] for po in orders])
    if incident.shipment_id and incident.shipment_id in graph.shipments:
        graph_paths.extend(graph.delay_paths(graph.shipments[incident.shipment_id], orders, customer_orders))
        return
    if incident.shipment_id:
        notes.append(
            f"Shipment {incident.shipment_id} is not in the graph; the delay path starts at the part and the plant."
        )
    graph_paths.extend(_paths_from_part_and_plant(graph, part_id, plant_id, orders, customer_orders))


def _paths_from_part_and_plant(
    graph: WorldGraph,
    part_id: str,
    plant_id: str,
    orders: list[dict],
    customer_orders: list[dict],
) -> list[list[str]]:
    """Same chain as delay_paths, starting at Part and Plant when no shipment is known."""
    by_po: dict[str, list[dict]] = defaultdict(list)
    for co in customer_orders:
        by_po[co["production_order_id"]].append(co)
    if not orders:
        models = [f"Model {model} (BOM)" for model in sorted(graph.models_by_part.get(part_id, ()))]
        return [[
            f"Part {part_id}",
            f"Plant {plant_id}",
            *models,
            "No future production order in the blocked window",
        ]]
    paths: list[list[str]] = []
    for po in orders:
        head = [
            f"Part {part_id}",
            f"Plant {plant_id}",
            f"Model {po['model']} (BOM)",
            f"ProductionOrder {po['production_order_id']}",
        ]
        linked = by_po.get(po["production_order_id"], [])
        if not linked:
            paths.append([*head, "No customer order"])
            continue
        for co in linked:
            paths.append([
                *head,
                f"CustomerOrder {co['customer_order_id']}",
                f"Dealer {co['dealer_id']} / Customer {co['customer_id']}",
            ])
    return paths


def _reason(kind: str, constraint: str, new_date: str, to_plant: str | None) -> str:
    if kind == "delay":
        why = f"supplier delay blocks this build until the new ETA {constraint}"
    else:
        why = f"plant outage restarts on {constraint}"
    if to_plant is None:
        return f"{why}; rescheduled to {new_date}."
    return (
        f"{why}; home plant has no free slot in the window, "
        f"transferred to {to_plant} on {new_date}."
    )


def _place(
    graph: WorldGraph,
    schedule: PlantSchedule,
    po_id: str,
    earliest: int,
    kind: str,
    constraint: str,
    calls: list[ToolCall],
    notes: list[str],
) -> None:
    home = graph.orders[po_id]["plant_id"]
    model = graph.orders[po_id]["model"]
    for idx in range(max(earliest, 0), _HORIZON):
        if schedule.free_count(home, idx) > 0:
            schedule.commit(po_id, home, idx)
            new_date = idx_to_date(idx).isoformat()
            calls.append(ToolCall(
                tool="mes.reschedule",
                args={"production_order_id": po_id, "new_date": new_date},
                reason=_reason(kind, constraint, new_date, None),
            ))
            return

    best: tuple[int, str] | None = None
    for plant_id in graph.plants_for_model(model):
        if plant_id == home:
            continue
        for idx in range(_HORIZON):
            if schedule.free_count(plant_id, idx) > 0:
                candidate = (idx, plant_id)
                if best is None or candidate < best:
                    best = candidate
                break
    if best is None:
        notes.append(
            f"No free slot for {po_id} ({model}): {home} has none on or after the constraint, "
            f"and no other plant that builds {model} has a free day in the window."
        )
        return
    idx, plant_id = best
    schedule.commit(po_id, plant_id, idx)
    new_date = idx_to_date(idx).isoformat()
    calls.append(ToolCall(
        tool="mes.transfer",
        args={"production_order_id": po_id, "to_plant_id": plant_id, "new_date": new_date},
        reason=_reason(kind, constraint, new_date, plant_id),
    ))
