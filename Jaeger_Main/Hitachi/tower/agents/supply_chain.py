"""Supply-chain planner for supplier delays and plant outages.

Handbook rules 1-3. The graph decides who is affected. This module only
moves those production orders:

- same plant first, on the earliest free day at or after the new ETA or the
  restart day, and only through the planning window (indexes 0..19)
- transfer only when that plant has no free legal day in that range, to the
  earliest free day at another plant that builds the model
- a day inside any plant_outage for the destination plant is not a legal slot,
  inclusive, including a day freed by releasing the outage orders
- a delayed part blocks only the receiving plant, and an outage blocks builds
  at that plant on the outage days
"""

from __future__ import annotations

from collections import defaultdict
from datetime import date

from tower.calendar_util import LAST_IDX, date_to_idx, idx_to_date, is_working_day, next_working_day
from tower.contracts import Incident, SpecialistResult, ToolCall
from tower.graph import PATH_KEEP, WorldGraph
from tower.optimize import recommend
from tower.schedule import PlantSchedule, restart_index

# Exclusive end. LAST_IDX is 19, so this is range(..., 20): today through 2027-04-02.
_HORIZON = LAST_IDX + 1
# ISO date for each planning index. Placement only asks for these days.
_DAY = tuple(idx_to_date(index).isoformat() for index in range(_HORIZON))

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
    omitted = [0]
    pending: dict[str, _Slot] = {}

    for incident in incidents:
        if incident.kind == "supplier_delay":
            _take_delay(graph, incident, pending, graph_paths, notes, omitted)
        elif incident.kind == "plant_outage":
            _take_outage(graph, incident, pending, graph_paths, notes, omitted)
    if omitted[0]:
        notes.append(
            f"Stored {len(graph_paths)} graph paths. "
            f"{omitted[0]} further paths follow the same links and were not stored."
        )

    calls: list[ToolCall] = []
    windows = _outage_windows(incidents)
    blocked = _blocked_indexes(windows)
    # Original build day, then id, so earlier orders take earlier free slots.
    place_order = sorted(pending, key=lambda po_id: (graph.orders[po_id]["idx"], po_id))
    for po_id in place_order:
        schedule.release(po_id)
    for po_id in place_order:
        earliest, kind, constraint = pending[po_id]
        _place(graph, schedule, po_id, earliest, kind, constraint, windows, blocked, calls, notes)

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
    omitted: list[int],
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
        date.fromisoformat(blocked_from)
        until_d = date.fromisoformat(blocked_until)
    except (TypeError, ValueError) as exc:
        notes.append(
            f"Skipped supplier delay of {part_id} at {plant_id}: "
            f"{blocked_from} .. {blocked_until} is not a date window ({exc})."
        )
        return
    until_work = until_d if is_working_day(until_d) else next_working_day(until_d)
    try:
        earliest = date_to_idx(until_work)
    except ValueError as exc:
        notes.append(
            f"Skipped supplier delay of {part_id} at {plant_id}: "
            f"{blocked_from} .. {blocked_until} has no working-day restart ({exc})."
        )
        return

    orders = graph.affected_orders_delay(plant_id, part_id, blocked_from, blocked_until)
    _cite_delay(graph, incident, part_id, plant_id, orders, graph_paths, notes, omitted)
    for po in orders:
        _keep_later(pending, po["production_order_id"], earliest, "delay", until_work.isoformat())


def _take_outage(
    graph: WorldGraph,
    incident: Incident,
    pending: dict[str, _Slot],
    graph_paths: list[list[str]],
    notes: list[str],
    omitted: list[int],
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
    _store_paths(
        graph_paths,
        omitted,
        graph.outage_paths(plant_id, orders, graph.customer_orders_for(order_ids), limit=PATH_KEEP),
    )
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
    omitted: list[int],
) -> None:
    customer_orders = graph.customer_orders_for([po["production_order_id"] for po in orders])
    if incident.shipment_id and incident.shipment_id in graph.shipments:
        _store_paths(
            graph_paths,
            omitted,
            graph.delay_paths(
                graph.shipments[incident.shipment_id],
                orders,
                customer_orders,
                limit=PATH_KEEP,
            ),
        )
        return
    if incident.shipment_id:
        notes.append(
            f"Shipment {incident.shipment_id} is not in the graph; the delay path starts at the part and the plant."
        )
    _store_paths(
        graph_paths,
        omitted,
        _paths_from_part_and_plant(graph, part_id, plant_id, orders, customer_orders, limit=PATH_KEEP),
    )


def _store_paths(paths: list[list[str]], omitted: list[int], built: tuple[list[list[str]], int]) -> None:
    stored, total = built
    paths.extend(stored)
    omitted[0] += total - len(stored)


def _paths_from_part_and_plant(
    graph: WorldGraph,
    part_id: str,
    plant_id: str,
    orders: list[dict],
    customer_orders: list[dict],
    limit: int = PATH_KEEP,
) -> tuple[list[list[str]], int]:
    """Same chain as delay_paths, starting at Part and Plant when no shipment is known."""
    by_po: dict[str, list[dict]] = defaultdict(list)
    for co in customer_orders:
        by_po[co["production_order_id"]].append(co)
    paths: list[list[str]] = []
    if not orders:
        models = [f"Model {model} (BOM)" for model in sorted(graph.models_by_part.get(part_id, ()))]
        if limit > 0:
            paths.append([
                f"Part {part_id}",
                f"Plant {plant_id}",
                *models,
                "No future production order in the blocked window",
            ])
        return paths, 1
    total = 0
    for po in orders:
        head = [
            f"Part {part_id}",
            f"Plant {plant_id}",
            f"Model {po['model']} (BOM)",
            f"ProductionOrder {po['production_order_id']}",
        ]
        linked = by_po.get(po["production_order_id"], [])
        if not linked:
            total += 1
            if len(paths) < limit:
                paths.append([*head, "No customer order"])
            continue
        for co in linked:
            total += 1
            if len(paths) < limit:
                paths.append([
                    *head,
                    f"CustomerOrder {co['customer_order_id']}",
                    f"Dealer {co['dealer_id']} / Customer {co['customer_id']}",
                ])
    return paths, total


def _outage_windows(incidents: list[Incident]) -> dict[str, list[tuple[str, str]]]:
    """Inclusive outage dates per plant. A day in here is not a build day."""
    windows: dict[str, list[tuple[str, str]]] = defaultdict(list)
    for incident in incidents:
        if incident.kind != "plant_outage":
            continue
        plant_id = incident.plant_id
        start = incident.outage_start
        end = incident.outage_end
        if not (plant_id and start and end):
            continue
        try:
            date.fromisoformat(start)
            date.fromisoformat(end)
        except (TypeError, ValueError):
            continue
        windows[plant_id].append((start, end))
    return windows


def _inside_outage(windows: dict[str, list[tuple[str, str]]], plant_id: str, day: str) -> bool:
    return any(start <= day <= end for start, end in windows.get(plant_id, ()))


def _blocked_indexes(windows: dict[str, list[tuple[str, str]]]) -> dict[str, set[int]]:
    """Planning indexes whose date falls inside an inclusive outage window."""
    blocked: dict[str, set[int]] = {}
    for plant_id in windows:
        closed: set[int] = set()
        for idx, day in enumerate(_DAY):
            if _inside_outage(windows, plant_id, day):
                closed.add(idx)
        blocked[plant_id] = closed
    return blocked


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
    windows: dict[str, list[tuple[str, str]]],
    blocked: dict[str, set[int]],
    calls: list[ToolCall],
    notes: list[str],
) -> None:
    home = graph.orders[po_id]["plant_id"]
    model = graph.orders[po_id]["model"]
    # Same plant first, on the earliest free day at or after the constraint.
    # A day inside an outage is not a legal slot, even if releasing orders freed it.
    home_closed = blocked.get(home)
    for idx in range(max(earliest, 0), _HORIZON):
        if home_closed is not None and idx in home_closed:
            continue
        if schedule.free_count(home, idx) <= 0:
            continue
        new_date = _DAY[idx]
        schedule.commit(po_id, home, idx)
        calls.append(ToolCall(
            tool="mes.reschedule",
            args={"production_order_id": po_id, "new_date": new_date},
            reason=_reason(kind, constraint, new_date, None),
        ))
        notes.append(recommend(po_id, home, home, new_date, kind))
        return

    best: tuple[int, str] | None = None
    for plant_id in graph.plants_for_model(model):
        if plant_id == home:
            continue
        # Transfer goes to the earliest free legal day. A later index cannot beat
        # the best (index, plant) already found, so those days are not scanned.
        limit = _HORIZON if best is None else best[0] + 1
        closed = blocked.get(plant_id)
        for idx in range(limit):
            if closed is not None and idx in closed:
                continue
            if schedule.free_count(plant_id, idx) <= 0:
                continue
            candidate = (idx, plant_id)
            if best is None or candidate < best:
                best = candidate
            break
    if best is None:
        if windows:
            notes.append(
                f"No legal slot for {po_id} ({model}): a day inside a plant outage is not "
                f"a feasible build day, and no outage-free slot remains in the window."
            )
        else:
            notes.append(
                f"No free slot for {po_id} ({model}): {home} has none on or after the constraint, "
                f"and no other plant that builds {model} has a free day in the window."
            )
        return
    idx, plant_id = best
    schedule.commit(po_id, plant_id, idx)
    new_date = _DAY[idx]
    calls.append(ToolCall(
        tool="mes.transfer",
        args={"production_order_id": po_id, "to_plant_id": plant_id, "new_date": new_date},
        reason=_reason(kind, constraint, new_date, plant_id),
    ))
    notes.append(recommend(po_id, home, plant_id, new_date, kind))
