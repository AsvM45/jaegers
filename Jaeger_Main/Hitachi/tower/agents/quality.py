"""Quality containment for a defective part lot.

Holds the lot, stops sale of unsold vehicles, and notifies owners.
Does not reschedule production or assign loaners.
"""

from __future__ import annotations

from datetime import date

from tower.contracts import Incident, SpecialistResult, ToolCall
from tower.graph import PATH_KEEP, WorldGraph


def plan_quality(graph: WorldGraph, incidents: list[Incident]) -> SpecialistResult:
    """Plan writes for quality-hold incidents. Other kinds are ignored."""
    calls: list[ToolCall] = []
    affected_ids: list[str] = []
    graph_paths: list[list[str]] = []
    notes: list[str] = []

    for incident in incidents:
        if incident.kind != "quality_hold":
            continue
        lot, selection = _select_lot(graph, incident)
        if lot is None:
            notes.append(selection)
            continue

        vehicles = graph.affected_vehicles(
            lot["plant_id"],
            lot["part_id"],
            lot["first_build_date"],
            lot["last_build_date"],
        )
        sold = 0
        in_stock = 0
        stock_vins: dict[str, list[str]] = {}
        sold_customers: set[str] = set()
        for vehicle in vehicles:
            status = vehicle["status"]
            if status == "sold":
                sold += 1
                customer_id = vehicle.get("customer_id")
                if customer_id:
                    sold_customers.add(customer_id)
            elif status == "in_stock":
                in_stock += 1
                stock_vins.setdefault(vehicle["dealer_id"], []).append(vehicle["vin"])
        notes.append(f"{selection} {sold} sold, {in_stock} in stock.")

        calls.append(
            ToolCall(
                tool="quality.hold_lot",
                args={"lot_id": lot["lot_id"]},
                reason=f"Place lot {lot['lot_id']} on quality hold.",
            )
        )
        calls.extend(_stop_sale_calls(lot, stock_vins))
        calls.extend(_notify_calls(graph, lot, sold_customers))

        affected_ids.append(lot["lot_id"])
        affected_ids.extend(vehicle["vin"] for vehicle in vehicles)
        stored, total = graph.quality_paths(lot, vehicles, limit=PATH_KEEP)
        graph_paths.extend(stored)
        if total > len(stored):
            notes.append(
                f"Stored {len(stored)} graph paths for lot {lot['lot_id']}. "
                f"{total - len(stored)} further vehicle paths follow the same links and were not stored."
            )

    return SpecialistResult(
        agent="quality",
        affected_ids=affected_ids,
        graph_paths=graph_paths,
        calls=calls,
        notes=notes,
    )


def _select_lot(graph: WorldGraph, incident: Incident) -> tuple[dict | None, str]:
    """Use the named lot, otherwise the exact window, then overlap, then lowest lot id."""
    if incident.lot_id:
        lot = graph.lots.get(incident.lot_id)
        if lot is None:
            return None, _unmatched_note(incident)
        return lot, f"Chose lot {lot['lot_id']} because the incident names that lot."

    if not (incident.part_id and incident.plant_id and incident.build_start and incident.build_end):
        return None, (
            "Quality hold is missing a part, plant, or build window, and it names no lot. "
            "No hold was placed."
        )

    hits = graph.find_lots(
        supplier_id=incident.supplier_id,
        part_id=incident.part_id,
        plant_id=incident.plant_id,
        build_start=incident.build_start,
        build_end=incident.build_end,
    )
    if not hits:
        return None, _unmatched_note(incident)

    if len(hits) == 1:
        lot = hits[0]
        return lot, f"Chose lot {lot['lot_id']}, the only lot matching the incident."

    exact = [lot for lot in hits if _exact_window(lot, incident)]
    if len(exact) == 1:
        lot = exact[0]
        others = ", ".join(item["lot_id"] for item in hits if item["lot_id"] != lot["lot_id"])
        return lot, (
            f"Chose lot {lot['lot_id']} because its build dates "
            f"{lot['first_build_date']} through {lot['last_build_date']} "
            f"match the incident window exactly, ahead of {others}."
        )

    pool = exact or hits
    lot, detail = _tie_break(pool, incident)
    if exact:
        detail = (
            f"Several lots share the exact window {incident.build_start} through {incident.build_end}. "
            + detail
        )
    return lot, detail


def _exact_window(lot: dict, incident: Incident) -> bool:
    return bool(
        incident.build_start
        and incident.build_end
        and lot["first_build_date"] == incident.build_start
        and lot["last_build_date"] == incident.build_end
    )


def _overlap_days(lot: dict, build_start: str, build_end: str) -> int:
    start = max(lot["first_build_date"], build_start)
    end = min(lot["last_build_date"], build_end)
    if start > end:
        return 0
    return (date.fromisoformat(end) - date.fromisoformat(start)).days + 1


def _tie_break(pool: list[dict], incident: Incident) -> tuple[dict, str]:
    """Greatest inclusive date overlap, then the lowest lot id."""
    listed = ", ".join(lot["lot_id"] for lot in sorted(pool, key=lambda item: item["lot_id"]))
    if incident.build_start and incident.build_end:
        build_start = incident.build_start
        build_end = incident.build_end
        scored = [
            (_overlap_days(item, build_start, build_end), item)
            for item in pool
        ]
        scored.sort(key=lambda item: (-item[0], item[1]["lot_id"]))
        days, lot = scored[0]
        day_word = "day" if days == 1 else "days"
        tied = [item for overlap, item in scored if overlap == days]
        if len(tied) > 1:
            detail = (
                f"Tie-break among {listed}: {len(tied)} lots share the greatest inclusive overlap "
                f"of {days} {day_word}; chose {lot['lot_id']}, the lowest lot id."
            )
        else:
            detail = (
                f"Tie-break among {listed}: chose {lot['lot_id']} "
                f"with the greatest inclusive overlap ({days} {day_word}), then the lowest lot id."
            )
        return lot, detail

    lot = min(pool, key=lambda item: item["lot_id"])
    return lot, (
        f"Tie-break among {listed}: the incident has no build window, "
        f"so chose {lot['lot_id']}, the lowest lot id."
    )


def _unmatched_note(incident: Incident) -> str:
    filters = []
    if incident.supplier_id:
        filters.append(f"supplier {incident.supplier_id}")
    if incident.part_id:
        filters.append(f"part {incident.part_id}")
    if incident.plant_id:
        filters.append(f"plant {incident.plant_id}")
    if incident.build_start or incident.build_end:
        filters.append(f"window {incident.build_start or '?'} through {incident.build_end or '?'}")
    target = ", ".join(filters) if filters else "the incident fields"
    if incident.lot_id:
        return (
            f"Lot {incident.lot_id} is absent from the graph, and no lot matched {target}. "
            "No hold was placed."
        )
    return f"No lot matched {target}. No hold was placed."


def _stop_sale_calls(lot: dict, by_dealer: dict[str, list[str]]) -> list[ToolCall]:
    calls = []
    for dealer_id in sorted(by_dealer):
        vins = sorted(by_dealer[dealer_id])
        calls.append(
            ToolCall(
                tool="dealer.stop_sale",
                args={"dealer_id": dealer_id, "vins": vins},
                reason=(
                    f"Stop sale of {len(vins)} in-stock vehicle(s) at {dealer_id} "
                    f"built with lot {lot['lot_id']}."
                ),
            )
        )
    return calls


def _notify_calls(graph: WorldGraph, lot: dict, customer_ids: set[str]) -> list[ToolCall]:
    part_name = graph.parts[lot["part_id"]]["name"]
    message = f"The {part_name} from lot {lot['lot_id']} is on quality hold."
    return [
        ToolCall(
            tool="crm.notify_customer",
            args={"customer_id": customer_id, "message": message},
            reason=f"Notify customer {customer_id} that lot {lot['lot_id']} is on quality hold.",
        )
        for customer_id in sorted(customer_ids)
    ]
