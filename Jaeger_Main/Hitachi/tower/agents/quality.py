"""Quality containment for a defective part lot.

Holds the lot, stops sale of unsold vehicles, and notifies owners.
Does not reschedule production or assign loaners.
"""

from __future__ import annotations

from tower.contracts import Incident, SpecialistResult, ToolCall
from tower.graph import WorldGraph


def plan_quality(graph: WorldGraph, incidents: list[Incident]) -> SpecialistResult:
    """Plan writes for quality-hold incidents. Other kinds are ignored."""
    calls: list[ToolCall] = []
    affected_ids: list[str] = []
    graph_paths: list[list[str]] = []
    notes: list[str] = []

    for incident in incidents:
        if incident.kind != "quality_hold":
            continue
        # Step A: decide which lot or lots the message is about.
        lots, selection = _select_lots(graph, incident)
        if not lots:
            notes.append(selection)
            continue

        # Step B: the cars built with them (each lot's plant and build dates, on models whose
        # bill of materials has the part). A car is counted once even if two lots reach it.
        # The lot's own dates are used, not the message's: the message only picks the lot, and
        # the lot record says which builds it actually went into.
        by_vin: dict[str, dict] = {}
        for lot in lots:
            for vehicle in graph.affected_vehicles(
                lot["plant_id"], lot["part_id"], lot["first_build_date"], lot["last_build_date"]
            ):
                by_vin[vehicle["vin"]] = vehicle
        vehicles = [by_vin[vin] for vin in sorted(by_vin)]
        sold = sum(vehicle["status"] == "sold" for vehicle in vehicles)
        in_stock = sum(vehicle["status"] == "in_stock" for vehicle in vehicles)
        notes.append(f"{selection} {sold} sold, {in_stock} in stock.")

        # Step C: hold each lot, stop sale of unsold cars (one call per dealer across all lots),
        # then notify each owner of a sold car once.
        lot_ids = [lot["lot_id"] for lot in lots]
        for lot_id in lot_ids:
            calls.append(
                ToolCall(
                    tool="quality.hold_lot",
                    args={"lot_id": lot_id},
                    reason=f"Place lot {lot_id} on quality hold.",
                )
            )
        calls.extend(_stop_sale_calls(lot_ids, vehicles))
        calls.extend(_notify_calls(graph, lots[0]["part_id"], lot_ids, vehicles))

        affected_ids.extend(lot_ids)
        affected_ids.extend(vehicle["vin"] for vehicle in vehicles)
        # Cite each lot with only its own vehicles. Every selected lot shares the part and plant
        # (find_lots filtered on both), so the build dates are enough to tell them apart.
        for lot in lots:
            in_lot = [v for v in vehicles if lot["first_build_date"] <= v["build_date"] <= lot["last_build_date"]]
            graph_paths.extend(graph.quality_paths(lot, in_lot))

    return SpecialistResult(
        agent="quality",
        affected_ids=affected_ids,
        graph_paths=graph_paths,
        calls=calls,
        notes=notes,
    )


def _select_lots(graph: WorldGraph, incident: Incident) -> tuple[list[dict], str]:
    """The named lot; otherwise the one lot whose build dates match exactly; otherwise every
    lot whose build dates overlap the stated window, since each may hold suspect parts.

    Returns (lots, note) or ([], note). The note explains the choice in the trace either way.
    """
    # A named lot is used only if it exists. An unknown id never falls back to a window
    # search, which could hold the wrong lot.
    if incident.lot_id:
        lot = graph.lots.get(incident.lot_id)
        if lot is None:
            return [], _unmatched_note(incident)
        return [lot], f"Chose lot {lot['lot_id']} because the incident names that lot."

    # Without a lot id, a window search needs part, plant and both dates, or it is too broad.
    if not (incident.part_id and incident.plant_id and incident.build_start and incident.build_end):
        return [], (
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
        return [], _unmatched_note(incident)
    if len(hits) == 1:
        return hits, f"Chose lot {hits[0]['lot_id']}, the only lot matching the incident."

    # Several candidates overlap the window. A single lot whose dates match exactly wins.
    exact = [lot for lot in hits if _exact_window(lot, incident)]
    if len(exact) == 1:
        lot = exact[0]
        others = ", ".join(item["lot_id"] for item in hits if item["lot_id"] != lot["lot_id"])
        return exact, (
            f"Chose lot {lot['lot_id']} because its build dates "
            f"{lot['first_build_date']} through {lot['last_build_date']} "
            f"match the incident window exactly, ahead of {others}."
        )

    # Still ambiguous: containment errs on the safe side and holds every overlapping lot.
    listed = ", ".join(lot["lot_id"] for lot in hits)
    return hits, (
        f"Held lots {listed}: their build dates overlap the stated window "
        f"{incident.build_start} through {incident.build_end}, so each may contain suspect parts."
    )


def _exact_window(lot: dict, incident: Incident) -> bool:
    """The lot's first and last build dates equal the message's window."""
    return bool(
        incident.build_start
        and incident.build_end
        and lot["first_build_date"] == incident.build_start
        and lot["last_build_date"] == incident.build_end
    )


def _unmatched_note(incident: Incident) -> str:
    """Explain, for the trace, which filters found no lot. The coordinator then escalates."""
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


# Group unsold VINs by dealer so each dealer gets a single stop_sale call (fewest calls).
def _stop_sale_calls(lot_ids: list[str], vehicles: list[dict]) -> list[ToolCall]:
    label = _lot_label(lot_ids)
    by_dealer: dict[str, list[str]] = {}
    for vehicle in vehicles:
        if vehicle["status"] != "in_stock":
            continue
        by_dealer.setdefault(vehicle["dealer_id"], []).append(vehicle["vin"])
    calls = []
    for dealer_id in sorted(by_dealer):
        vins = sorted(by_dealer[dealer_id])
        calls.append(
            ToolCall(
                tool="dealer.stop_sale",
                args={"dealer_id": dealer_id, "vins": vins},
                reason=f"Stop sale of {len(vins)} in-stock vehicle(s) at {dealer_id} built with {label}.",
            )
        )
    return calls


# One notice per distinct owner, even if they own several affected cars. All selected lots are
# the same part, so the first lot's part names it.
def _notify_calls(graph: WorldGraph, part_id: str, lot_ids: list[str], vehicles: list[dict]) -> list[ToolCall]:
    label = _lot_label(lot_ids)
    message = f"The {graph.parts[part_id]['name']} from {label} is on quality hold."
    customer_ids = sorted({
        vehicle["customer_id"]
        for vehicle in vehicles
        if vehicle["status"] == "sold" and vehicle.get("customer_id")
    })
    return [
        ToolCall(
            tool="crm.notify_customer",
            args={"customer_id": customer_id, "message": message},
            reason=f"Notify customer {customer_id} that {label} is on quality hold.",
        )
        for customer_id in customer_ids
    ]


def _lot_label(lot_ids: list[str]) -> str:
    """"lot LOT-0130" or "lots LOT-0130, LOT-0131 and LOT-0132", for reasons and messages."""
    if len(lot_ids) == 1:
        return f"lot {lot_ids[0]}"
    return "lots " + ", ".join(lot_ids[:-1]) + " and " + lot_ids[-1]
