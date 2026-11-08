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
from datetime import date

from tower.calendar_util import extract_dates, is_working_day, next_working_day
from tower.contracts import Incident

# '(1)', '(2)' ... markers split a compound message into sections.
_MARKER = re.compile(r"\((\d+)\)")
# Outage messages often end "the line restarts the following working day". Any date after this
# phrase is about the restart, not the outage, so _operational_dates drops it.
# Wording for the restart day after an outage. Dates after it are not outage days.
_RESTART = re.compile(r"restarts the following working day|\bback on\b|\bback up\b|\brestarts? on\b", re.I)
# Record ids written in a message. One that is not in the tables makes the message unclear.
_ID_SHAPE = re.compile(r"\b(?:SH|LOT|PO|CO|SUP)-\d+\b|\bP_[A-Z]{2}\b")

# Keyword groups for the rule reader. A keyword alone is not enough: each kind also needs the
# entities and dates it can act on (see _read_section). Matching is case-insensitive, on whole
# words, with curly apostrophes folded to straight ones (see _hits and _fold).
_QUALITY = (
    "quality alert",
    "quality bulletin",
    "faulty",
    "contamination",
    "suspect",
    "on hold",
    "defect",
    "defective",
    "recall",
)
_OUTAGE = (
    "outage",
    "power failure",
    "we're dark",
    "we are dark",
    "production is stopped",
    "lost production",
    "we're down",
    "we are down",
    "is down",
    "are down",
    "is dark",
    "shut down",
    "shutdown",
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
    "won't land",
    "will not land",
    "won't arrive",
    "will not arrive",
    "slipped",
    "pushed to",
    "running late",
    "is late",
    "new arrival",
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
    "unverified",
    "no official word",
    "claims",
    "can't confirm",
    "cannot confirm",
    "heard",
)


# Entry point called by the coordinator. Returns one Incident per section.
def understand(graph, text: str, llm=None) -> list[Incident]:
    """Split a message into sections and classify each one.

    With an llm (tower.agents.llm_reader.LLMReader), the model reads each
    section and code verifies it; the rule reader is the fallback and veto.
    """
    if llm is None:
        return [_read_section(graph, section) for section in _sections(text)]
    return [_read_with_llm(graph, section, llm) for section in _sections(text)]


# Kinds that lead to no operational change.
_QUIET = frozenset({"noise", "unconfirmed"})


# Decision order: model error -> rules; model and rules disagree on the kind -> rules;
# noise/unconfirmed -> rules' summary plus the model's reason; real incident -> built from the
# model's phrases, or rules if a phrase fails verification.
def _read_with_llm(graph, section: str, llm) -> Incident:
    """Model proposes, code verifies. Disagreement on the kind goes to the rules."""
    from tower.agents.llm_reader import LLMUnavailable

    # The rule reading is always computed: it is the fallback and the referee for the model.
    rules = _read_section(graph, section)
    try:
        fields = llm.extract(section)
    except (LLMUnavailable, ValueError) as exc:
        return _fallback(rules, f"{llm.model} gave no usable answer ({exc}); used the rule reader.")

    said = f"{llm.model} read '{fields['kind']}': {fields['reason'] or 'no reason given'}"
    if fields["kind"] != rules.kind:
        return _fallback(
            rules,
            said,
            f"rule check reads '{rules.kind}', which wins: a kind disagreement is never acted on "
            "from the model alone.",
        )
    # Both agree it is noise or a rumor: nothing to resolve, so keep the rule reading and credit
    # the model, whose reason goes first in the evidence.
    if fields["kind"] in _QUIET:
        rules.evidence.insert(0, said)
        rules.reader = llm.model
        return rules

    # A real incident: rebuild it from the model's phrases. Every phrase must be verbatim in the
    # text and resolve through the graph.
    built, problem = _incident_from_fields(graph, section, fields)
    if built is None:
        return _fallback(rules, said, f"model output failed verification ({problem}); used the rule reader.")
    if built.kind != rules.kind:
        return _fallback(
            rules,
            said,
            f"model fields build a '{built.kind}' but the rule check reads '{rules.kind}'; used the rule reader.",
        )
    # Same kind both ways. Fields may still differ (e.g. a different date phrase); the model's
    # verified reading is used and the differences are recorded for the audit.
    diffs = _field_diffs(built, rules)
    if diffs:
        # A disputed date or id could move the wrong orders, so the checked rule reading is used.
        return _fallback(
            rules,
            said,
            "model fields differ from the rule check on " + "; ".join(diffs) + "; used the rule reading.",
        )
    built.evidence.insert(0, said)
    built.evidence.append("rule check agrees on every field")
    built.reader = llm.model
    return built


def _fallback(rules: Incident, *notes: str) -> Incident:
    """Return the rule reading, with notes on why the model was not used at the top of the evidence."""
    rules.evidence[:0] = list(notes)
    rules.reader = "rules"
    return rules


# Model output field -> graph entity type it must resolve to.
_FIELD_TYPE = {
    "plant": "plant",
    "part": "part",
    "supplier": "supplier",
    "lot_id": "lot",
    "shipment_id": "shipment",
}


# Entity fields each kind cannot act without. Anything else is optional:
# an optional phrase that fails verification is dropped, not fatal.
_NEEDED = {
    "quality_hold": {"plant"},
    "plant_outage": {"plant"},
    "supplier_delay": set(),
}


def _ground(graph, section: str, phrase: str, entity_type: str):
    """Resolve a phrase, or the alias in the message that contains it ("Texas" -> "the Texas plant")."""
    # First try: the phrase itself is a known name.
    found = [m for m in graph.resolve_mentions(phrase) if m.entity_type == entity_type]
    if found:
        return found[0]
    # Otherwise the model copied part of a longer alias. Find where the phrase sits in the message
    # and use the alias of the right type that covers that spot.
    at = _fold(section).find(_fold(phrase))
    for mention in graph.resolve_mentions(section):
        if mention.entity_type == entity_type and mention.start <= at < mention.end:
            return mention
    return None


def _incident_from_fields(graph, section: str, fields: dict) -> tuple[Incident | None, str]:
    """Resolve the model's phrases with code. Every phrase must be in the text."""
    folded = _fold(section)
    kind = fields["kind"]
    dropped = []
    # A date phrase that is not in the message is invented, and it rejects the whole reading.
    for name in ("start_date", "end_date"):
        phrase = fields[name]
        if phrase and _fold(phrase) not in folded:
            return None, f"{name} '{phrase}' is not in the message"

    picked = {}
    for name, entity_type in _FIELD_TYPE.items():
        phrase = fields[name]
        mention = None
        if phrase:
            problem = None
            if _fold(phrase) not in folded:
                problem = f"{name} '{phrase}' is not in the message"
            else:
                mention = _ground(graph, section, phrase, entity_type)
                if mention is None:
                    problem = f"{name} '{phrase}' does not resolve to a known {entity_type}"
            if problem:
                if name in _NEEDED[kind]:
                    return None, problem
                dropped.append(problem)
        # Same (chosen, aliases, extras) shape that _pick gives the rule reader, so the builders
        # below serve both paths.
        picked[entity_type] = (mention, [mention.alias] if mention else [], [])

    built, problem = _build(graph, kind, picked, fields)
    if built is not None and dropped:
        built.evidence.append("dropped optional model field: " + "; ".join(dropped))
    return built, problem


def _build(graph, kind: str, picked: dict, fields: dict) -> tuple[Incident | None, str]:
    """Check the model's reading has what its kind needs, then build the Incident.

    Returns (incident, "") or (None, reason). The checks mirror the rule reader's conditions
    in _read_section, so neither path can act on less evidence than the other.
    """
    # Each date phrase must parse to exactly one calendar date ("next Friday", "2027-03-24").
    dates = []
    for name in ("start_date", "end_date"):
        phrase = fields[name]
        if not phrase:
            return None, f"{name} is empty"
        parsed = extract_dates(phrase)
        if len(parsed) != 1:
            return None, f"{name} '{phrase}' is not one calendar date"
        dates.append({**parsed[0], "phrase": phrase})

    hits = [f"{kind} (model)"]
    plant, part, lot, supplier, shipment = (picked[k][0] for k in ("plant", "part", "lot", "supplier", "shipment"))
    if kind == "quality_hold":
        if plant is None or (part is None and lot is None):
            return None, "quality hold needs a plant and a part or lot"
        if dates[1]["date"] < dates[0]["date"]:
            return None, "build window ends before it starts"
        return _quality(graph, picked, dates, hits), ""
    if kind == "plant_outage":
        if plant is None:
            return None, "outage needs a plant"
        if dates[1]["date"] < dates[0]["date"]:
            return None, "outage ends before it starts"
        return _outage(picked, dates, hits, []), ""
    if shipment is None and None in (supplier, part, plant):
        return None, "delay needs a shipment, or a supplier, part, and plant"
    return _delay(graph, picked, dates, hits), ""


def _field_diffs(built: Incident, rules: Incident) -> list[str]:
    """Fields where the model's incident and the rule incident disagree, for the evidence."""
    names = (
        "plant_id", "part_id", "supplier_id", "lot_id", "shipment_id",
        "blocked_from", "blocked_until", "outage_start", "outage_end", "build_start", "build_end",
    )
    return [
        f"{name} {getattr(built, name)} vs {getattr(rules, name)}"
        for name in names
        if getattr(built, name) != getattr(rules, name)
    ]


def _sections(text: str) -> list[str]:
    """Numbered parts of a compound message, or the whole text."""
    marks = list(_MARKER.finditer(text))
    # A single "(1)" is not a list; it is more likely a stray parenthesis.
    if len(marks) < 2:
        return [text]
    chunks = []
    for index, mark in enumerate(marks):
        stop = marks[index + 1].start() if index + 1 < len(marks) else len(text)
        # Text before "(1)" (e.g. "Morning digest, two items.") is a header and is dropped.
        chunk = text[mark.end():stop].strip()
        if chunk:
            chunks.append(chunk)
    return chunks or [text]


# The rule reader. Kinds are tried in priority order; each needs its keywords AND the fields to
# act on, otherwise it falls through to rumor, then noise.
def _read_section(graph, section: str) -> Incident:
    """Deterministic reading of one section. Always returns an Incident (noise at worst)."""
    mentions = graph.resolve_mentions(section)
    dates, restart_notes = _operational_dates(section)
    quality_hits = _hits(section, _QUALITY)
    outage_hits = _hits(section, _OUTAGE)
    delay_hits = _hits(section, _DELAY)
    rumor_hits = _hits(section, _RUMOR)
    # For each entity type: (first mention, its aliases, other ids of that type).
    picked = {kind: _pick(mentions, kind) for kind in ("plant", "part", "lot", "supplier", "shipment")}

    plant = picked["plant"][0]
    part = picked["part"][0]
    lot = picked["lot"][0]
    supplier = picked["supplier"][0]
    shipment = picked["shipment"][0]

    # Quality first: a bulletin can also say "on hold" or "delayed", and the hold is what matters.
    if quality_hits and plant is not None and (part is not None or lot is not None) and len(dates) >= 2:
        return _quality(graph, picked, dates, quality_hits)
    if outage_hits and plant is not None and len(dates) >= 1:
        return _outage(picked, dates, outage_hits, restart_notes)
    # A delay is located by a shipment id, or by supplier + part + plant together.
    if delay_hits and len(dates) >= 2 and (shipment is not None or None not in (supplier, part, plant)):
        return _delay(graph, picked, dates, delay_hits)
    # Rumor wording, or an incident too incomplete to act on, is escalated, not ignored.
    if rumor_hits:
        return _unconfirmed(section, picked, dates, rumor_hits, inverted=False)
    # Incident wording about our records, but not enough to act on (or an id that does not
    # exist): rule 8 says escalate rather than guess or ignore.
    if (quality_hits or outage_hits or delay_hits) and (mentions or _ID_SHAPE.search(section)):
        return _unclear(graph, section, picked, dates, quality_hits + outage_hits + delay_hits)
    return _noise(section, picked, quality_hits, outage_hits, delay_hits)


# --- Builders: turn resolved entities and dates into an Incident with a summary and evidence
# lines. Both the rule reader and the model path use them.
def _quality(graph, picked, dates, hits) -> Incident:
    """Quality-hold Incident. The first two dates are the suspect build window."""
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

    # A named lot fills in whatever the message left out. The message's own values are never
    # overwritten.
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
    """Plant-outage Incident: the first two dates are the first and last day down, inclusive."""
    plant = picked["plant"]
    plant_id = plant[0].entity_id
    start = dates[0]["date"]
    end = dates[1]["date"] if len(dates) > 1 else start
    evidence = [f"outage language: {', '.join(hits)}", _date_line(dates)]
    if len(dates) == 1:
        evidence.append(f"one date given, so a single-day outage on {start}")
    evidence.extend(restart_notes)
    evidence.extend(_chosen_lines(picked, ("plant", "part")))
    if len(dates) > 2:
        evidence.append(f"used the first two dates {start} and {end}")
    # Use the name as the message wrote it ("the Kentucky plant") in the summary.
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


# A delay blocks builds from the original ETA (first date) until the new ETA (second date). If the
# new ETA is not later, the message is treated as unconfirmed.
def _delay(graph, picked, dates, hits) -> Incident:
    """Supplier-delay Incident, or unconfirmed when the dates run backwards."""
    supplier, part, plant, shipment = (
        picked["supplier"],
        picked["part"],
        picked["plant"],
        picked["shipment"],
    )
    supplier_id = supplier[0].entity_id if supplier[0] is not None else None
    part_id = part[0].entity_id if part[0] is not None else None
    plant_id = plant[0].entity_id if plant[0] is not None else None
    # A date on a weekend becomes the next working day: nothing builds on weekends anyway.
    blocked_from, blocked_until = _roll(dates[0]["date"]), _roll(dates[1]["date"])
    rolled = [
        f"'{item['phrase']}' ({item['date']}) is a weekend; using the next working day {_roll(item['date'])}"
        for item in dates[:2]
        if _roll(item["date"]) != item["date"]
    ]
    shipment_id = None
    evidence = [f"delay language: {', '.join(hits)}", _date_line(dates)]
    evidence.extend(rolled)
    evidence.extend(_chosen_lines(picked, ("shipment", "supplier", "part", "plant")))
    if len(dates) > 2:
        evidence.append(f"used the first two dates {blocked_from} and {blocked_until}")

    # Three ways to tie the delay to a shipment: a named shipment that exists (fills any gaps),
    # a named one that does not (noted and left unset), or a lookup by supplier, part, plant
    # and original ETA (used only when exactly one row matches).
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

    # A new ETA on or before the original is contradictory. Do not guess; escalate.
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
    """Unconfirmed Incident: the coordinator escalates it and writes nothing.

    inverted=True is the delay-with-backwards-dates case. It keeps the delay's fields and
    evidence so a human can see what was read. Otherwise it is a plain rumor.
    """
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


def _unclear(graph, section, picked, dates, hits) -> Incident:
    """Sounds like an incident about our records but cannot be pinned down. Escalate it."""
    unknown = [tok for tok in dict.fromkeys(_ID_SHAPE.findall(section)) if not graph.resolve_mentions(tok)]
    if unknown:
        why = f"it names {', '.join(unknown)}, which is not in the company records"
    else:
        why = "the plant, part, lot, shipment, or dates needed to act are missing"
    summary = (
        f"The message reads like an incident ({', '.join(hits)}) but is not specific enough to act on: "
        f"{why}. It is escalated for a human to confirm."
    )
    evidence = [f"incident language without enough detail: {', '.join(hits)}"]
    if dates:
        evidence.append(_date_line(dates))
    evidence.extend(_chosen_lines(picked, ("plant", "part", "supplier", "shipment", "lot")))
    if unknown:
        evidence.append("unknown record ids: " + ", ".join(unknown))
    return Incident(kind="unconfirmed", summary=summary, evidence=evidence)


def _noise(section, picked, quality_hits, outage_hits, delay_hits) -> Incident:
    """Noise Incident. The evidence says which incident wording was seen but incomplete, if any."""
    # Quote the message, on one line and at most 180 characters, in the summary.
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
    # Every date is after the restart phrase: the trimming would leave nothing, so keep them all.
    if not earlier:
        return dates, []
    ignored = [item for item in dates if item["start"] >= restart.start()]
    note = f"ignored trailing wording '{restart.group(0)}'; it is not an extra outage day"
    if ignored:
        shown = ", ".join(f"'{item['phrase']}' = {item['date']}" for item in ignored)
        note += f"; ignored dates {shown}"
    return earlier, [note]


def _roll(iso_day: str) -> str:
    """The same day, or the next working day when it falls on a weekend."""
    day = date.fromisoformat(iso_day)
    return iso_day if is_working_day(day) else next_working_day(day).isoformat()


def _fold(text: str) -> str:
    """Casefold and straighten curly apostrophes, so "we\u2019re dark" matches "we're dark"."""
    return (
        text.replace("\u2019", "'")
        .replace("\u2018", "'")
        .replace("\u02bc", "'")
        .casefold()
    )


def _hits(text: str, phrases: tuple[str, ...]) -> list[str]:
    """Keywords from phrases found in text as whole words ("suspect" does not match "suspected")."""
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
    """Evidence lines: which words resolved to which id, plus any other ids of the same type."""
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
    """Evidence line listing each date phrase and the ISO date it resolved to."""
    shown = ", ".join(f"'{item['phrase']}' = {item['date']}" for item in dates)
    return f"dates: {shown}"


def _plant_name(graph, picked_plant, plant_id: str | None) -> str:
    """Display name for the plant, as in _party_name."""
    return _party_name(graph, picked_plant, plant_id, "plant")


def _party_name(graph, picked, entity_id: str | None, kind: str) -> str:
    """Business label for the first resolved id. A raw id is shown by its table name."""
    table = {"plant": graph.plants, "part": graph.parts, "supplier": graph.suppliers}[kind]
    # Prefer the official name when the message used the id or the name itself; keep a nickname
    # ("the Texas plant") as written, so the summary reads like the message.
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
    """What is on hold, for the summary: "lot LOT-0191, <part>", the lot, or the part."""
    part = _party_name(graph, None, part_id, "part") if part_id else None
    if lot_id and part:
        return f"lot {lot_id}, {part}"
    if lot_id:
        return f"lot {lot_id}"
    return part or "an unnamed part"
