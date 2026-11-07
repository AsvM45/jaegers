"""Read one message into incidents.

The function takes the message text and the company graph. It does not take
an event id, and it does not keep a table of answers. A compound message
with two or more markers such as (1) and (2) becomes one incident per
section. Anything else is a single section.

Classification priority, first match wins:
quality hold, plant outage, supplier delay, unconfirmed rumor, noise.
"""

from __future__ import annotations

import re

from tower.calendar_util import extract_dates
from tower.contracts import Incident

_MARKER = re.compile(r"\((\d+)\)")
_RESTART = re.compile(r"restarts the following working day", re.I)

_QUALITY = (
    "quality alert",
    "quality bulletin",
    "faulty",
    "contamination",
    "suspect",
    "on hold",
)
_OUTAGE = (
    "outage",
    "power failure",
    "we're dark",
    "we are dark",
    "production is stopped",
    "lost production",
)
_DELAY = (
    "delayed",
    "can't make it",
    "cannot make it",
    "new eta",
    "will now arrive",
    "original drop",
    "carrier says",
    "waiting on",
)
_RUMOR = (
    "rumor",
    "not confirmed",
    "nothing confirmed",
    "no dates",
    "possible",
    "may be off",
    "someone mentioned",
    "someone on the floor",
)


def understand(graph, text: str) -> list[Incident]:
    """Split a message into sections and classify each one."""
    return [_read_section(graph, section) for section in _sections(text)]


def _sections(text: str) -> list[str]:
    """Numbered parts of a compound message, or the whole text."""
    marks = list(_MARKER.finditer(text))
    if len(marks) < 2:
        return [text]
    chunks = []
    for index, mark in enumerate(marks):
        stop = marks[index + 1].start() if index + 1 < len(marks) else len(text)
        chunk = text[mark.end():stop].strip()
        if chunk:
            chunks.append(chunk)
    return chunks or [text]


def _read_section(graph, section: str) -> Incident:
    mentions = graph.resolve_mentions(section)
    dates, restart_notes = _operational_dates(section)
    quality_hits = _hits(section, _QUALITY)
    outage_hits = _hits(section, _OUTAGE)
    delay_hits = _hits(section, _DELAY)
    rumor_hits = _hits(section, _RUMOR)
    picked = {kind: _pick(mentions, kind) for kind in ("plant", "part", "lot", "supplier", "shipment")}

    plant = picked["plant"][0]
    part = picked["part"][0]
    lot = picked["lot"][0]
    supplier = picked["supplier"][0]
    shipment = picked["shipment"][0]

    if quality_hits and plant is not None and (part is not None or lot is not None) and len(dates) >= 2:
        return _quality(graph, picked, dates, quality_hits)
    if outage_hits and plant is not None and len(dates) >= 2:
        return _outage(picked, dates, outage_hits, restart_notes)
    if delay_hits and len(dates) >= 2 and (shipment is not None or None not in (supplier, part, plant)):
        return _delay(graph, picked, dates, delay_hits)
    if rumor_hits:
        return _unconfirmed(section, picked, dates, rumor_hits, inverted=False)
    return _noise(section, picked, quality_hits, outage_hits, delay_hits)


def _quality(graph, picked, dates, hits) -> Incident:
    plant, part, lot, supplier = picked["plant"], picked["part"], picked["lot"], picked["supplier"]
    plant_id = plant[0].entity_id
    part_id = part[0].entity_id if part[0] is not None else None
    lot_id = lot[0].entity_id if lot[0] is not None else None
    supplier_id = supplier[0].entity_id if supplier[0] is not None else None
    start, end = dates[0]["date"], dates[1]["date"]
    evidence = [f"quality language: {', '.join(hits)}", _date_line(dates)]
    evidence.extend(_chosen_lines(picked, ("plant", "part", "lot", "supplier")))
    if len(dates) > 2:
        evidence.append(f"used the first two dates {start} and {end}")

    if lot_id and lot_id in graph.lots:
        row = graph.lots[lot_id]
        filled = []
        if part_id is None:
            part_id = row["part_id"]
            filled.append(f"part {part_id}")
        if supplier_id is None:
            supplier_id = row["supplier_id"]
            filled.append(f"supplier {supplier_id}")
        if plant_id is None:
            plant_id = row["plant_id"]
            filled.append(f"plant {plant_id}")
        if filled:
            evidence.append(f"copied {', '.join(filled)} from lot {lot_id}")

    summary = (
        f"Quality hold on {_hold_subject(graph, lot_id, part_id)} "
        f"at {_plant_name(graph, plant, plant_id)}, "
        f"covering builds from {start} through {end} inclusive."
    )
    return Incident(
        kind="quality_hold",
        summary=summary,
        supplier_id=supplier_id,
        part_id=part_id,
        plant_id=plant_id,
        lot_id=lot_id,
        build_start=start,
        build_end=end,
        evidence=evidence,
    )


def _outage(picked, dates, hits, restart_notes) -> Incident:
    plant = picked["plant"]
    plant_id = plant[0].entity_id
    start, end = dates[0]["date"], dates[1]["date"]
    evidence = [f"outage language: {', '.join(hits)}", _date_line(dates)]
    evidence.extend(restart_notes)
    evidence.extend(_chosen_lines(picked, ("plant", "part")))
    if len(dates) > 2:
        evidence.append(f"used the first two dates {start} and {end}")
    name = plant[1][0] if plant[1] else plant_id
    summary = f"{name} ({plant_id}) cannot build from {start} through {end} inclusive."
    return Incident(
        kind="plant_outage",
        summary=summary,
        plant_id=plant_id,
        outage_start=start,
        outage_end=end,
        evidence=evidence,
    )


def _delay(graph, picked, dates, hits) -> Incident:
    supplier, part, plant, shipment = (
        picked["supplier"],
        picked["part"],
        picked["plant"],
        picked["shipment"],
    )
    supplier_id = supplier[0].entity_id if supplier[0] is not None else None
    part_id = part[0].entity_id if part[0] is not None else None
    plant_id = plant[0].entity_id if plant[0] is not None else None
    blocked_from, blocked_until = dates[0]["date"], dates[1]["date"]
    shipment_id = None
    evidence = [f"delay language: {', '.join(hits)}", _date_line(dates)]
    evidence.extend(_chosen_lines(picked, ("shipment", "supplier", "part", "plant")))
    if len(dates) > 2:
        evidence.append(f"used the first two dates {blocked_from} and {blocked_until}")

    mentioned = shipment[0]
    if mentioned is not None and mentioned.entity_id in graph.shipments:
        shipment_id = mentioned.entity_id
        row = graph.shipments[shipment_id]
        filled = []
        if supplier_id is None:
            supplier_id = row["supplier_id"]
            filled.append(f"supplier {supplier_id}")
        if part_id is None:
            part_id = row["part_id"]
            filled.append(f"part {part_id}")
        if plant_id is None:
            plant_id = row["plant_id"]
            filled.append(f"plant {plant_id}")
        if filled:
            evidence.append(f"filled {', '.join(filled)} from shipment {shipment_id}")
        evidence.append(
            f"text dates {blocked_from} until {blocked_until} win over stored ETA {row['eta_date']} "
            f"on {shipment_id}"
        )
    elif mentioned is not None:
        evidence.append(f"shipment {mentioned.entity_id} is not in the shipment table")
    elif supplier_id and part_id and plant_id:
        found = graph.find_shipments(supplier_id, part_id, plant_id, eta=blocked_from)
        found_ids = [row["shipment_id"] for row in found]
        if len(found) == 1:
            shipment_id = found_ids[0]
            evidence.append(
                f"find_shipments({supplier_id}, {part_id}, {plant_id}, eta={blocked_from}) "
                f"returned {shipment_id}"
            )
        else:
            shown = ", ".join(found_ids) if found_ids else "no rows"
            evidence.append(
                f"find_shipments({supplier_id}, {part_id}, {plant_id}, eta={blocked_from}) "
                f"returned {shown}; shipment_id left unset"
            )

    if blocked_until <= blocked_from:
        evidence.append(
            f"dates are inverted: {blocked_until} is not strictly after {blocked_from}"
        )
        return _unconfirmed(
            "",
            picked,
            dates,
            hits,
            inverted=True,
            evidence=evidence,
            supplier_id=supplier_id,
            part_id=part_id,
            plant_id=plant_id,
            shipment_id=shipment_id,
            blocked_from=blocked_from,
            blocked_until=blocked_until,
        )

    who = _party_name(graph, supplier, supplier_id, "supplier")
    what = _party_name(graph, part, part_id, "part")
    where = _party_name(graph, plant, plant_id, "plant")
    load = f" Shipment {shipment_id} matches the original ETA." if shipment_id else (
        " No unique shipment matched that original ETA."
    )
    summary = (
        f"{who} will deliver {what} to {where} late, blocking builds from {blocked_from} "
        f"until {blocked_until}.{load}"
    )
    return Incident(
        kind="supplier_delay",
        summary=summary,
        supplier_id=supplier_id,
        part_id=part_id,
        plant_id=plant_id,
        shipment_id=shipment_id,
        blocked_from=blocked_from,
        blocked_until=blocked_until,
        evidence=evidence,
    )


def _unconfirmed(
    section,
    picked,
    dates,
    hits,
    inverted: bool,
    evidence: list[str] | None = None,
    supplier_id: str | None = None,
    part_id: str | None = None,
    plant_id: str | None = None,
    shipment_id: str | None = None,
    blocked_from: str | None = None,
    blocked_until: str | None = None,
) -> Incident:
    if inverted:
        summary = (
            f"The dates are inverted ({dates[0]['phrase']} = {blocked_from}, then "
            f"{dates[1]['phrase']} = {blocked_until}), so it is not safe to act "
            f"because the new ETA is not after the original ETA."
        )
        lines = list(evidence or [])
    else:
        quoted = ", ".join(hits)
        summary = (
            f"The report is not safe to act on because it is unconfirmed ({quoted}) "
            f"and does not name a specific shipment, outage, or lot to change."
        )
        lines = [f"rumor language: {quoted}"]
        if dates:
            lines.append(_date_line(dates))
        lines.extend(_chosen_lines(picked, ("plant", "part", "supplier", "shipment", "lot")))
    return Incident(
        kind="unconfirmed",
        summary=summary,
        supplier_id=supplier_id,
        part_id=part_id,
        plant_id=plant_id,
        shipment_id=shipment_id,
        blocked_from=blocked_from,
        blocked_until=blocked_until,
        evidence=lines,
    )


def _noise(section, picked, quality_hits, outage_hits, delay_hits) -> Incident:
    excerpt = " ".join(section.split()).strip().rstrip(".")
    if len(excerpt) > 180:
        excerpt = excerpt[:177].rstrip() + "..."
    summary = (
        f'"{excerpt}" is not an operational disruption because it does not report '
        f"a supplier delay, a plant outage, or a quality hold."
    )
    evidence = ["no confirmed supplier delay, plant outage, or quality hold"]
    if quality_hits:
        evidence.append(
            "quality wording was incomplete (needs a plant, a part or lot, and two dates): "
            + ", ".join(quality_hits)
        )
    if outage_hits:
        evidence.append(
            "outage wording was incomplete (needs a plant and two dates): " + ", ".join(outage_hits)
        )
    if delay_hits:
        evidence.append(
            "delay wording was incomplete (needs two dates and a shipment, or a supplier, part, and plant): "
            + ", ".join(delay_hits)
        )
    evidence.extend(_chosen_lines(picked, ("plant", "part", "supplier", "shipment", "lot")))
    return Incident(kind="noise", summary=summary, evidence=evidence)


def _operational_dates(section: str) -> tuple[list[dict], list[str]]:
    """Dates in reading order, without a trailing restart day."""
    dates = extract_dates(section)
    restart = _RESTART.search(section)
    if not restart:
        return dates, []
    earlier = [item for item in dates if item["start"] < restart.start()]
    if not earlier:
        return dates, []
    ignored = [item for item in dates if item["start"] >= restart.start()]
    note = "ignored trailing wording 'restarts the following working day'; it is not an extra outage day"
    if ignored:
        shown = ", ".join(f"'{item['phrase']}' = {item['date']}" for item in ignored)
        note += f"; ignored dates {shown}"
    return earlier, [note]


def _fold(text: str) -> str:
    return (
        text.replace("\u2019", "'")
        .replace("\u2018", "'")
        .replace("\u02bc", "'")
        .casefold()
    )


def _hits(text: str, phrases: tuple[str, ...]) -> list[str]:
    folded = _fold(text)
    found = []
    for phrase in phrases:
        pattern = r"(?<![a-z0-9])" + re.escape(_fold(phrase)) + r"(?![a-z0-9])"
        if re.search(pattern, folded):
            found.append(phrase)
    return found


def _pick(mentions, entity_type: str):
    """First mention of a type, its aliases, and later mentions of other ids."""
    chosen = None
    aliases: list[str] = []
    extras = []
    seen = set()
    for mention in mentions:
        if mention.entity_type != entity_type:
            continue
        if chosen is None:
            chosen = mention
            aliases.append(mention.alias)
            continue
        if mention.entity_id == chosen.entity_id:
            if mention.alias not in aliases:
                aliases.append(mention.alias)
            continue
        if mention.entity_id not in seen:
            seen.add(mention.entity_id)
            extras.append(mention)
    return chosen, aliases, extras


def _chosen_lines(picked, kinds: tuple[str, ...]) -> list[str]:
    lines = []
    for kind in kinds:
        chosen, aliases, extras = picked[kind]
        if chosen is None:
            continue
        shown = ", ".join(f"'{alias}'" for alias in aliases)
        lines.append(f"{kind}: {shown} -> {chosen.entity_id}")
        for extra in extras:
            lines.append(f"other {kind}: '{extra.alias}' -> {extra.entity_id}")
    return lines


def _date_line(dates: list[dict]) -> str:
    shown = ", ".join(f"'{item['phrase']}' = {item['date']}" for item in dates)
    return f"dates: {shown}"


def _plant_name(graph, picked_plant, plant_id: str | None) -> str:
    return _party_name(graph, picked_plant, plant_id, "plant")


def _party_name(graph, picked, entity_id: str | None, kind: str) -> str:
    """Business label for the first resolved id. A raw id is shown by its table name."""
    table = {"plant": graph.plants, "part": graph.parts, "supplier": graph.suppliers}[kind]
    if picked is not None and picked[0] is not None:
        entity_id = picked[0].entity_id
        alias = picked[1][0] if picked[1] else picked[0].alias
        row = table.get(entity_id)
        official = row.get("name") if row else None
        if official and alias.casefold() in {entity_id.casefold(), official.casefold()}:
            return f"{official} ({entity_id})"
        return f"{alias} ({entity_id})"
    if not entity_id:
        return f"an unnamed {kind}"
    row = table.get(entity_id)
    if row and row.get("name"):
        return f"{row['name']} ({entity_id})"
    return entity_id


def _hold_subject(graph, lot_id: str | None, part_id: str | None) -> str:
    part = _party_name(graph, None, part_id, "part") if part_id else None
    if lot_id and part:
        return f"lot {lot_id}, {part}"
    if lot_id:
        return f"lot {lot_id}"
    return part or "an unnamed part"
