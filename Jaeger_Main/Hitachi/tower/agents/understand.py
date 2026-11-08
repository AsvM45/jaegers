"""Read one message into incidents.

The function takes the message text and the company graph. It does not take
an event id, and it does not keep a table of answers. A compound message
with two or more markers such as (1) and (2) becomes one incident per
section. Anything else is a single section.

Classification priority, first match wins:
hearsay, non-event wording, quality hold, plant outage, supplier delay,
a weaker rumor, noise.

Hearsay is "not confirmed", "nothing confirmed", "unconfirmed", "rumor",
"someone mentioned", "someone on the floor", "may be off", or "no dates".
It is classified before a quality hold, an outage, or a delay, so a
fully specified sentence that is still a rumor is escalated.
"possible" stays a weaker rumor and does not block a fully specified incident.

"no delay expected", "if it goes past", and "drill" are non-events. They
are classified before a quality hold, an outage, or a delay. A bare
"on hold" is not a quality trigger; a quality bulletin or a known lot
phrase still is. A delay needs a shipment, or a known part and plant.
A supplier is not required once the part and plant are known.

Zero-width characters (U+200B, U+200C, U+200D, U+FEFF) are removed before
the message is split or classified, so one cannot hide a phrase or open
an extra incident.
"""

from __future__ import annotations

import html
import re
import unicodedata

from tower.calendar_util import TODAY, extract_dates
from tower.contracts import Incident

_MARKER = re.compile(r"\((\d+)\)")
_RESTART = re.compile(r"restarts the following working day", re.I)

_QUALITY = (
    "quality alert",
    "quality bulletin",
    "faulty",
    "contamination",
    "suspect",
)
# Whole-word non-events. Checked before quality, outage, and delay.
# The feed does not use these phrases.
_NON_EVENT = (
    "no delay expected",
    "if it goes past",
    "drill",
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
_HEARSAY = (
    "not confirmed",
    "nothing confirmed",
    "unconfirmed",
    "rumor",
    "someone mentioned",
    "someone on the floor",
    "may be off",
    "no dates",
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
_ORIGINAL_ETA = ("original drop", "was due", "due")
_NEW_ETA = ("new eta", "will now arrive")
_ZERO_WIDTH = str.maketrans("", "", "\u200b\u200c\u200d\ufeff")
_DASH = str.maketrans({"\u2013": "-", "\u2014": "-", "\u2212": "-"})
_UNICODE_SPACE = re.compile(r"[\u00a0\u1680\u2000-\u200a\u202f\u205f\u3000]+")
_SPACE_RUN = re.compile(r"[ \t\r\n\f\v]+")


def _prepare(text: str) -> str:
    """Make messy wording readable before the phrase and date scan.

    HTML entities, fullwidth letters, odd dashes, and broken whitespace are
    folded into the same sentence a person would read. The 15 feed messages
    have none of these, so their classifications stay put.
    """
    raw = html.unescape(unicodedata.normalize("NFKC", text or ""))
    raw = raw.translate(_ZERO_WIDTH).translate(_DASH)
    raw = _UNICODE_SPACE.sub(" ", raw)
    return _SPACE_RUN.sub(" ", raw).strip()


def understand(graph, text: str, anchor=None) -> list[Incident]:
    """Split a message into sections and classify each one.

    `anchor` is the date relative phrases are measured from. None means
    Monday 2027-03-08, so the feed's "next Wednesday" stays 2027-03-17.
    Zero-width characters are stripped before that split.
    """
    text = _prepare(text)
    when = TODAY if anchor is None else anchor
    return [_read_section(graph, section, when) for section in _sections(text)]


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


def _read_section(graph, section: str, anchor) -> Incident:
    mentions = graph.resolve_mentions(section)
    dates, restart_notes = _operational_dates(section, anchor)
    folded = _fold(section)
    quality_hits = _hits(section, _QUALITY, folded)
    outage_hits = _hits(section, _OUTAGE, folded)
    delay_hits = _hits(section, _DELAY, folded)
    rumor_hits = _hits(section, _RUMOR, folded)
    picked = {kind: _pick(mentions, kind) for kind in ("plant", "part", "lot", "supplier", "shipment")}

    plant = picked["plant"][0]
    part = picked["part"][0]
    lot = picked["lot"][0]
    supplier = picked["supplier"][0]
    shipment = picked["shipment"][0]

    hearsay = _hits(section, _HEARSAY, folded)
    if hearsay:
        return _unconfirmed(section, picked, dates, hearsay, inverted=False)
    if _hits(section, _NON_EVENT, folded):
        return _noise(section, picked, [], [], [])
    lot_known = lot is not None and lot.entity_id in graph.lots
    quality_specified = plant is not None and (part is not None or lot is not None) and len(dates) >= 2
    if quality_hits and (lot_known or quality_specified):
        return _quality(graph, picked, dates, quality_hits)
    if outage_hits and plant is not None and len(dates) >= 2:
        return _outage(picked, dates, outage_hits, restart_notes)
    # A shipment is enough. Otherwise a known part and plant are enough;
    # the supplier may be unnamed.
    if delay_hits and len(dates) >= 2 and (
        shipment is not None or (part is not None and plant is not None)
    ):
        return _delay(graph, picked, _bind_labeled_etas(section, dates), delay_hits)
    if rumor_hits:
        return _unconfirmed(section, picked, dates, rumor_hits, inverted=False)
    return _noise(section, picked, quality_hits, outage_hits, delay_hits)


def _quality(graph, picked, dates, hits) -> Incident:
    plant, part, lot, supplier = picked["plant"], picked["part"], picked["lot"], picked["supplier"]
    plant_id = plant[0].entity_id if plant[0] is not None else None
    part_id = part[0].entity_id if part[0] is not None else None
    lot_id = lot[0].entity_id if lot[0] is not None else None
    supplier_id = supplier[0].entity_id if supplier[0] is not None else None
    start = dates[0]["date"] if dates else None
    end = dates[1]["date"] if len(dates) > 1 else None
    evidence = [f"quality language: {', '.join(hits)}"]
    if dates:
        evidence.append(_date_line(dates))
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
        if start is None:
            start = row["first_build_date"]
            filled.append(f"build_start {start}")
        if end is None:
            end = row["last_build_date"]
            filled.append(f"build_end {end}")
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
            "delay wording was incomplete (needs two dates and a shipment, or a part and a plant): "
            + ", ".join(delay_hits)
        )
    evidence.extend(_chosen_lines(picked, ("plant", "part", "supplier", "shipment", "lot")))
    return Incident(kind="noise", summary=summary, evidence=evidence)


def _bind_labeled_etas(section: str, dates: list[dict]) -> list[dict]:
    """Order dates as original ETA, then new ETA, when both labels are present.

    The date that follows "original drop", "was due", or "due" is the original
    ETA. The date that follows "new ETA" or "will now arrive" is the new ETA.
    Word order is left as-is when either label is missing, so a notice such as
    "can't make it next Monday ... next Friday" still reads first date, then second.
    """
    if len(dates) < 2:
        return dates
    original = _date_after(dates, _label_ends(section, _ORIGINAL_ETA))
    revised = _date_after(dates, _label_ends(section, _NEW_ETA))
    if original is None or revised is None or original is revised:
        return dates
    rest = [item for item in dates if item is not original and item is not revised]
    return [original, revised, *rest]


# Longer phrases are compiled first so a short label cannot claim their span.
_COMPILED_LABELS: dict[tuple[str, ...], tuple[re.Pattern, ...]] = {}


def _compiled_labels(phrases: tuple[str, ...]) -> tuple[re.Pattern, ...]:
    compiled = _COMPILED_LABELS.get(phrases)
    if compiled is None:
        ordered = sorted(phrases, key=len, reverse=True)
        compiled = tuple(
            re.compile(
                rf"(?<![A-Za-z0-9]){re.escape(phrase)}(?![A-Za-z0-9])",
                re.IGNORECASE,
            )
            for phrase in ordered
        )
        _COMPILED_LABELS[phrases] = compiled
    return compiled


def _label_ends(text: str, phrases: tuple[str, ...]) -> list[int]:
    """End offsets of the phrases. A longer phrase owns its span."""
    occupied: list[tuple[int, int]] = []
    ends: list[int] = []
    for pattern in _compiled_labels(phrases):
        for match in pattern.finditer(text):
            span = (match.start(), match.end())
            if any(span[0] < stop and start < span[1] for start, stop in occupied):
                continue
            occupied.append(span)
            ends.append(match.end())
    return ends


def _date_after(dates: list[dict], ends: list[int]) -> dict | None:
    """The first date that starts at or after the earliest usable label."""
    for end in sorted(ends):
        for item in dates:
            if item["start"] >= end:
                return item
    return None


def _operational_dates(section: str, anchor) -> tuple[list[dict], list[str]]:
    """Dates in reading order, without a trailing restart day."""
    dates = extract_dates(section, anchor)
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


_COMPILED_HITS: dict[tuple[str, ...], tuple[re.Pattern, ...]] = {}


def _compiled_hits(phrases: tuple[str, ...]) -> tuple[re.Pattern, ...]:
    compiled = _COMPILED_HITS.get(phrases)
    if compiled is None:
        compiled = tuple(
            re.compile(r"(?<![a-z0-9])" + re.escape(_fold(phrase)) + r"(?![a-z0-9])")
            for phrase in phrases
        )
        _COMPILED_HITS[phrases] = compiled
    return compiled


def _hits(text: str, phrases: tuple[str, ...], folded: str | None = None) -> list[str]:
    """Phrases that occur as whole words. `folded` is `_fold(text)` when the caller already has it."""
    if folded is None:
        folded = _fold(text)
    found = []
    for phrase, pattern in zip(phrases, _compiled_hits(phrases)):
        if pattern.search(folded):
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
