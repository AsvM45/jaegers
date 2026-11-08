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
import html
import unicodedata
from datetime import date, timedelta

from tower.calendar_util import TODAY, extract_dates, impossible_dates, is_working_day, next_working_day
from tower.contracts import Incident

# '(1)', '(2)' ... markers split a compound message into sections.
_MARKER = re.compile(r"\((\d+)\)")
# The same list written without the opening parenthesis: "1) ... 2) ...".
_MARKER_BARE = re.compile(r"(?:(?<=\s)|^)(\d)\)\s")
# "A) ... B) ..." and "First, ... Second, ...".
_LETTER = re.compile(r"(?:(?<=\s)|^)([A-D])\)\s")
_ORDINAL = re.compile(r"(?:(?<=\s)|^)(First|Second|Third),", re.I)
# A sentence that starts a second, separate item: "Also, ...", "Separately, ...".
_CONNECTOR = re.compile(r"(?<=[.!?])\s+(?:also|separately|in addition|additionally|and another thing|unrelated)[,:]\s+", re.I)
# Restart wording after an outage ("the line restarts the following working day", "back up
# Monday", "production resumes on the 22nd"). Dates after it are the restart, not outage days.
_RESTART = re.compile(r"\b(?:restart\w*|resum\w*|reopen\w*|back (?:on|up|online|running|in operation))\b", re.I)
# Record ids written in a message. One that is not in the tables makes the message unclear.
_ID_SHAPE = re.compile(r"\b(?:SH|LOT|PO|CO|SUP)-\d+\b|\bP_[A-Z]{2}\b")

# Word families for the rule reader, as regular expressions over the lower-cased message (curly
# apostrophes folded to straight ones, see _fold). They describe how people talk about each kind
# of incident in general; they are not taken from any particular message. A keyword alone is never
# enough: each kind also needs the records and dates it can act on (see _read_section).
_NEG = r"(?:can't|cannot|can not|won't|will not|isn't|is not|aren't|are not|not|unable to|no longer)"
_QUALITY = (
    r"quality (?:alert|bulletin|issue|problem|notice|hold|concern|escape|incident)",
    r"defect\w*", r"fault(?:y|s)?", r"contaminat\w*", r"suspect(?:ed)?", r"recall\w*",
    r"crack(?:ed|s|ing)?", r"corro\w*", r"bad (?:batch|lot|parts?|run)", r"non-?conform\w*",
    r"fail(?:ed|s)? (?:inspection|testing|qa|qc)", r"out[- ]of[- ]spec\w*",
    r"(?:inspection|audit|testing|qa|qc) (?:found|flagged|shows?|showed)",
    # Not a bare "on hold": a shipment can be "on hold at customs". Placing a lot on hold is quality.
    r"(?:place\w*\s+(?:\w+\s+){0,3}on|put\s+(?:\w+\s+){0,3}on) hold", r"hold (?:the |this |that )?lots?",
    r"stop[- ]sale",
    # A lot can be quarantined, or a defect named, without the word "quality".
    r"quarantin\w*", r"\bqa hold\b", r"field reports?", r"\bflagged\b",
    r"porosit\w*", r"checksum", r"water ingress", r"delamination", r"contaminated grease",
    r"undersized fasteners", r"torque spec", r"seal leaks?", r"thread pitch", r"mislabeled",
    r"excess solder", r"brittle plastic", r"intermittent shorts?",
)
_OUTAGE = (
    r"outages?", r"power (?:failure|cut|loss|outage)", r"blackout",
    # Words may sit between the subject and the verb: "production at Lexington is suspended".
    r"(?:production|builds?|the line|lines?|assembly|plant|operations?)"
    r"(?:\s+[\w'’-]+){0,5}\s+"
    r"(?:is |are |was |were |has |have |will be )?"
    r"(?:stopped|halted|suspended|shut down|down|offline|idle|dark|paused|closed)",
    r"(?:we're|we are|we'll be|will be|is|are|was|went|going|stays?) (?:dark|down|offline|idle)",
    # "we're losing Princeton for the 16th through the 18th" is the plant, not a parts shortage.
    r"(?:we(?:'re| are)|they(?:'re| are))\s+losing\b",
    r"shut ?down", r"shutdown", r"stoppage", r"standstill",
    r"(?:lost|losing|halt\w*|stop\w*|suspend\w*|no) (?:all )?(?:production|builds?|output)",
    _NEG + r" (?:build|produce|run (?:the line|production))",
    r"(?:down|dark|offline) (?:from|on|until|through|for)",
)
_DELAY = (
    r"delay\w*", r"late", r"later than", r"behind schedule", r"running behind",
    r"(?:new|revised|updated|adjusted) (?:eta|arrival|delivery|ship) ?(?:date|time)?", r"\beta\b",
    r"slip\w*", r"\bslid\b", r"push\w* (?:back|out|to)", r"postpon\w*", r"reschedul\w*",
    r"(?:arrival|delivery|shipment) (?:moved|moves|changed)",
    _NEG + r" (?:make it|arriv\w*|land\w*|deliver\w*|ship\w*|show|be there|reach)",
    r"(?:won'?t|will not|does(?:n't| not)|do(?:n't| not))\s+show",
    r"(?:will now|now|instead) (?:arriv\w*|land\w*|ship\w*|deliver\w*|come|com\w*)",
    r"now quoting", r"revised (?:date|eta|delivery|arrival)", r"\bno longer\b", r"missed the\b",
    r"waiting (?:on|for)", r"(?:originally|original|was|were|had been) (?:due|scheduled|planned|expected|set)",
    r"original (?:drop|date|eta|delivery)",
)
_RUMOR = (
    r"rumou?rs?\w*", r"(?:not |un)(?:confirmed|verified|official)", r"nothing (?:confirmed|official|definite)",
    r"no (?:dates?|details|specifics|confirmation|official word|word yet)",
    r"possibl[ey]", r"maybe", r"might", r"may be", r"could (?:be|slip|have)", r"perhaps",
    r"heard", r"hearsay", r"hint\w*", r"apparently", r"supposedly", r"word is", r"people (?:say|are saying)",
    r"(?:someone|somebody|people|a guy|word) (?:\w+ ){0,4}(?:said|says|say|mentioned|thinks|heard)", r"(?:can't|cannot|can not) confirm", r"not sure", r"unclear",
    r"claims?", r"speculat\w*", r"a vibe",
)
# What makes a vague message "possibly about us" (handbook: unconfirmed) rather than noise: it
# hints at trouble in our operations. A hedge with no trouble stays noise ("temperatures may
# reach 105 F", "is a plant tour possible next Friday?").
_TROUBLE = (
    r"shortages?", r"short on", r"delay\w*", r"late", r"slip\w*", r"behind", r"problems?", r"issues?",
    r"trouble", r"wrong", r"(?:off|up) with", r"strikes?", r"walkout", r"defect\w*", r"quality",
    r"outages?", r"(?:lose|lost|losing|loses) power", r"down", r"shut\w*", r"stop\w*", r"recall\w*",
    r"disrupt\w*", r"bottleneck", r"backlog",
    r"miss(?:es|ed|ing)?\s+(?:a\s+|the\s+)?(?:deliver\w*|shipment\w*)",
)


# Hearsay: checked before a quality hold, an outage or a delay, so a fully specified sentence that
# is still a rumor is escalated. The weaker _RUMOR words ("might", "possible") do not block a fully
# specified incident.
_HEARSAY = (
    r"(?:not |un)confirmed", r"nothing confirmed", r"rumou?rs?", r"someone (?:\w+ ){0,4}mentioned",
    r"someone on the floor", r"may be off", r"no dates",
)
# Non-events: checked before a quality hold, an outage or a delay.
_NON_EVENT = (r"no delay expected", r"if it goes past", r"drills?")
# Labels that bind a delay's dates when both appear, whatever their order.
_ORIGINAL_ETA = ("original drop", "was due", "due")
_NEW_ETA = ("new eta", "will now arrive")
_ZERO_WIDTH = str.maketrans("", "", "\u200b\u200c\u200d\ufeff")
_DASH = str.maketrans({"\u2013": "-", "\u2014": "-", "\u2212": "-"})
_UNICODE_SPACE = re.compile(r"[\u00a0\u1680\u2000-\u200a\u202f\u205f\u3000]+")
_SPACE_RUN = re.compile(r"[ \t\r\n\f\v]+")


def _prepare(text: str) -> str:
    """Make messy wording readable before the phrase and date scan: HTML entities, fullwidth
    letters, odd dashes, zero-width characters and broken whitespace are folded into the sentence
    a person would read, so none of them can hide a phrase or open an extra incident."""
    raw = html.unescape(unicodedata.normalize("NFKC", text or ""))
    raw = raw.translate(_ZERO_WIDTH).translate(_DASH)
    raw = _UNICODE_SPACE.sub(" ", raw)
    return _SPACE_RUN.sub(" ", raw).strip()


# Entry point called by the coordinator. Returns one Incident per section.
def understand(graph, text: str, llm=None, anchor=None) -> list[Incident]:
    """Split a message into sections and classify each one.

    With an llm (tower.agents.llm_reader.LLMReader), the model reads each section and code
    verifies it; the rule reader is the fallback and the referee. `anchor` is the date relative
    phrases are measured from (the day the event was received); None means TODAY.
    """
    text = _prepare(text)
    when = TODAY if anchor is None else anchor
    read = ((lambda part: _read_section(graph, part, when)) if llm is None
            else (lambda part: _read_with_llm(graph, part, llm, when)))
    out = []
    for section in _sections(text):
        out.extend(_read_connected(section, read))
    return out


def _read_connected(section: str, read) -> list[Incident]:
    """Read "<item>. Also, <item>." as two items when both halves are about something; otherwise as
    one, so a single report whose second sentence starts with "Also" is not cut in two."""
    cut = _CONNECTOR.search(section)
    if not cut:
        return [read(section)]
    parts = [section[:cut.start()].strip(), section[cut.end():].strip()]
    parts[1] = parts[1][:1].upper() + parts[1][1:]
    readings = [read(part) for part in parts if part]
    if len(readings) == 2 and all(r.kind != "noise" for r in readings):
        return readings
    # One half is chatter ("Stock markets closed higher. Also, <outage>"). Keep that half so a
    # date in the chatter ("today") is not treated as the first day of the outage. When the whole
    # message agrees with that half, the whole is the one that swallowed the chatter.
    whole = read(section)
    useful = [r for r in readings if r.kind != "noise"]
    if len(useful) == 1 and (whole.kind == "noise" or useful[0].kind == whole.kind):
        return useful
    return [whole]


# Kinds that lead to no operational change.
_QUIET = frozenset({"noise", "unconfirmed"})


# The model decides; code checks. Step 1: the model says what kind of event a section is and why.
# Step 2 (real incidents): it picks the records and dates that kind needs from candidates code found
# in the message and the tables. Code then checks the picks make a complete, consistent incident; a
# reading that does not check out (after one retry with the reason) is escalated to a human, never
# guessed. Word lists play no part. The rule reader is used only when the model is unavailable.
def _read_with_llm(graph, section: str, llm, anchor=None) -> Incident:
    """Model proposes, code verifies. Every incident carries the model's reasoning (model_reason)."""
    box: dict = {}
    incident = _decide_with_llm(graph, section, llm, box, anchor)
    if box.get("reason"):
        incident.model_reason = f"{llm.model}: {box['reason']}"
    return incident


def _decide_with_llm(graph, section: str, llm, box: dict, anchor=None) -> Incident:
    """The model-first reading behind _read_with_llm; box gets the model's reason."""
    from tower.agents.llm_reader import LLMUnavailable

    try:
        first = llm.classify(section)
    except (LLMUnavailable, ValueError) as exc:
        return _fallback(_read_section(graph, section, anchor),
                         f"{llm.model} gave no usable answer ({exc}); used the rule reader.")
    kind, reason = first["kind"], first["reason"]
    box["reason"] = reason
    said = f"{llm.model} read '{kind}': {reason or 'no reason given'}"
    mentions = graph.resolve_mentions(section)
    picked = {t: _pick(mentions, t) for t in ("plant", "part", "lot", "supplier", "shipment")}

    if kind == "noise":
        out = _noise(section, picked, [], [], [])
        out.evidence = [said, *out.evidence[1:]]
    elif kind == "unconfirmed":
        out = Incident(
            kind="unconfirmed",
            summary=f"The report is not safe to act on: {reason.rstrip('.')}. It is escalated for a human to confirm.",
            evidence=[said, *_chosen_lines(picked, ("plant", "part", "supplier", "shipment", "lot"))],
        )
    else:
        out = _model_incident(graph, section, llm, kind, reason, said, anchor)
    out.reader = llm.model
    return out


def model_options(graph, section: str, anchor=None) -> tuple[dict[str, list[str]], dict[str, object]]:
    """Candidates for step 2: every record the message names (through aliases.csv, ids and
    one-typo names) and every date it gives, as labels the model chooses from.
    Returns (labels by role type, label -> Mention or date item)."""
    labels: dict[str, list[str]] = {t: [] for t in ("plant", "part", "supplier", "lot", "shipment", "date")}
    lookup: dict[str, object] = {}
    for m in graph.resolve_mentions(section):
        if m.entity_type not in labels:
            continue
        label = f'"{m.alias}" = {m.entity_id}{_record_note(graph, m.entity_type, m.entity_id, m.alias)}'
        if label not in lookup:
            lookup[label] = m
            labels[m.entity_type].append(label)
    for item in extract_dates(section, anchor):
        phrase, iso = item["phrase"], item["date"]
        label = f'"{phrase}" = {date.fromisoformat(iso):%a} {iso}'
        if label not in lookup:
            lookup[label] = item
            labels["date"].append(label)
    return labels, lookup


def _record_note(graph, entity_type: str, entity_id: str, alias: str) -> str:
    """What the tables say about a record, so the model can tell candidates apart."""
    if entity_type in ("plant", "part", "supplier"):
        row = {"plant": graph.plants, "part": graph.parts, "supplier": graph.suppliers}[entity_type].get(entity_id)
        name = (row or {}).get("name", "")
        return f" ({name})" if name and name.casefold() != alias.casefold() else ""
    if entity_type == "lot" and entity_id in graph.lots:
        r = graph.lots[entity_id]
        return f" ({r['part_id']} from {r['supplier_id']} at {r['plant_id']}, builds {r['first_build_date']} to {r['last_build_date']})"
    if entity_type == "shipment" and entity_id in graph.shipments:
        r = graph.shipments[entity_id]
        return f" ({r['part_id']} from {r['supplier_id']} to {r['plant_id']}, due {r['eta_date']})"
    return ""


def _model_incident(graph, section: str, llm, kind: str, reason: str, said: str, anchor=None) -> Incident:
    """Step 2 for a real incident: the model picks records and dates, code checks them (one retry
    with the reason), and a reading that still does not check out is escalated."""
    from tower.agents.llm_reader import LLMUnavailable

    options, lookup = model_options(graph, section, anchor)
    notes = [said]
    answer, problem = None, ""
    for attempt in range(2):
        try:
            answer = llm.fill(section, kind, options, previous=answer if attempt else None,
                              problem=problem if attempt else None)
        except (LLMUnavailable, ValueError) as exc:
            problem = f"no usable answer ({exc})"
            break
        built, problem = _incident_from_choices(graph, kind, answer, lookup)
        picks = ", ".join(f"{k}={v.split(' = ')[0] if v else '-'}" for k, v in answer.items())
        notes.append(f"{'retry: ' if attempt else ''}{llm.model} picked {picks}")
        if built is not None:
            built.evidence[:0] = [*notes, "every pick checks out against the tables and the message"]
            return built
        notes.append(f"does not check out: {problem}")
    label = kind.replace("_", " ")
    return Incident(
        kind="unconfirmed",
        summary=(f"The model read this as a {label} ({reason.rstrip('.')}), but the reading does not check "
                 f"out against the tables: {problem}. It is escalated for a human to confirm."),
        evidence=notes,
    )


def _incident_from_choices(graph, kind: str, answer: dict, lookup: dict) -> tuple[Incident | None, str]:
    """Build the incident from the model's picks, with the same completeness checks as the rule
    reader. Returns (incident, "") or (None, what is missing or inconsistent)."""
    from tower.agents.llm_reader import ROLES

    def chosen(role):
        label = answer.get(role, "")
        return lookup.get(label) if label else None

    picked = {t: (None, [], []) for t in ("plant", "part", "lot", "supplier", "shipment")}
    for role, (rtype, _) in ROLES[kind].items():
        m = chosen(role) if rtype != "date" else None
        if m is not None:
            picked[rtype] = (m, [m.alias], [])
    plant, part, lot, shipment = (picked[t][0] for t in ("plant", "part", "lot", "shipment"))
    hits = [f"{kind} (model)"]

    if kind == "quality_hold":
        first, last = chosen("first_build_date"), chosen("last_build_date")
        lot_known = lot is not None and lot.entity_id in graph.lots
        if not lot_known and (plant is None or part is None):
            return None, "a quality hold needs a known lot, or a plant and a part"
        if not lot_known and (first is None or last is None):
            return None, "a quality hold needs the first and last build dates"
        dates = [d for d in (first, last) if d is not None]
        if len(dates) == 2 and dates[1]["date"] < dates[0]["date"]:
            return None, "the build window ends before it starts"
        return _quality(graph, picked, dates, hits), ""

    if kind == "plant_outage":
        first, last = chosen("first_day"), chosen("last_day")
        if plant is None:
            return None, "an outage needs a plant"
        if first is None:
            return None, "an outage needs its first day down"
        dates, notes = [first], []
        if last is not None:
            if answer.get("end_meaning") == "day work resumes":
                end = _day_before_restart(last["date"])
                notes.append(f"'{last['phrase']}' is when work resumes, so the last day down is {end}")
                last = {**last, "date": end}
            dates.append(last)
        if len(dates) == 2 and dates[1]["date"] < dates[0]["date"]:
            return None, "the outage ends before it starts"
        return _outage(picked, dates, hits, notes), ""

    original, new = chosen("original_date"), chosen("new_date")
    if shipment is None and (part is None or plant is None):
        return None, "a delay needs a shipment, or a part and a plant"
    if new is None:
        return None, "a delay needs the new arrival date"
    if original is None:
        if shipment is not None and shipment.entity_id in graph.shipments:
            eta = graph.shipments[shipment.entity_id]["eta_date"]
            original = {"phrase": f"stored ETA of {shipment.entity_id}", "date": eta}
        else:
            return None, "a delay needs the original due date"
    return _delay(graph, picked, [original, new], hits), ""


def checked_model_reading(graph, section: str, llm, fields: dict, anchor=None) -> tuple[Incident | None, str, dict, str]:
    """The model's reading of a real incident, checked against the tables and the message, with
    one retry when it fails: the model is told exactly what did not check out and answers again.

    Returns (incident or None, problem, the fields used, a note about the retry or "").
    """
    from tower.agents.llm_reader import LLMUnavailable

    built, problem = _incident_from_fields(graph, section, fields, anchor)
    if built is not None or fields["kind"] in _QUIET:
        return built, problem, fields, ""
    try:
        again = llm.extract(section, previous=fields, problem=problem)
    except (LLMUnavailable, ValueError) as exc:
        return None, problem, fields, f"retry gave no usable answer ({exc})"
    note = f"first reading failed ({problem}); retried with that feedback"
    if again["kind"] in _QUIET:
        return None, f"{problem}; on retry the model read '{again['kind']}'", again, note
    built, problem2 = _incident_from_fields(graph, section, again, anchor)
    return built, problem2 if built is None else "", again, note + ("" if built is None else ", and it checked out")


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


def _incident_from_fields(graph, section: str, fields: dict, anchor=None) -> tuple[Incident | None, str]:
    """Resolve the model's phrases with code. Every phrase must be in the text."""
    folded = _fold(section)
    kind = fields["kind"]
    dropped = []
    # Every date must be a date the message gives (or the last day down before a stated restart).
    # The model may rewrite it ("the 24th" as "March 24th"); a date that is not in the message is
    # invented, and it rejects the whole reading.
    dates = []
    for name in ("start_date", "end_date"):
        if not fields[name]:
            return None, f"{name} is empty"
        found, problem = _model_date(section, fields[name], anchor)
        if found is None:
            return None, f"{name} '{fields[name]}' {problem}"
        dates.append(found)
    # "back up on the 26th" is the restart, not a day down: an outage ends the working day before.
    restart = _RESTART.search(section)
    if kind == "plant_outage" and restart and dates[1]["start"] >= restart.start() and "note" not in dates[1]:
        last = _day_before_restart(dates[1]["date"])
        dates[1] = {**dates[1], "date": last, "note": f"'{dates[1]['phrase']}' is when work resumes, so the last day down is {last}"}

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

    built, problem = _build(graph, kind, picked, fields, dates)
    if built is not None and dropped:
        built.evidence.append("dropped optional model field: " + "; ".join(dropped))
    return built, problem


def _model_date(section: str, phrase: str, anchor=None) -> tuple[dict | None, str]:
    """Check one of the model's date phrases against the message. Returns (date item, "") or
    (None, why). Read in context when the words are in the message, so "the 1st" after "2/25" is
    March 1; otherwise the phrase must resolve to a date the message gives."""
    message = extract_dates(section, anchor)
    folded, want = _fold(section), _fold(phrase).strip()
    at = folded.find(want)
    if at >= 0:
        for item in message:
            if item["start"] <= at < item["end"] or at <= item["start"] < at + len(want):
                return {**item, "phrase": phrase}, ""
    parsed = extract_dates(phrase, anchor)
    if len(parsed) != 1:
        return None, "is not one calendar date"
    when = parsed[0]["date"]
    if any(item["date"] == when for item in message):
        source = next(item for item in message if item["date"] == when)
        return {**source, "phrase": phrase, "note": f"model wrote '{phrase}' for '{source['phrase']}'"}, ""
    restart = _RESTART.search(section)
    for item in message:
        if restart and item["start"] >= restart.start() and _day_before_restart(item["date"]) == when:
            return {**item, "phrase": phrase, "date": when,
                    "note": f"last day down before work resumes {item['date']}"}, ""
    return None, f"is {when}, which is not a date in the message"


def _build(graph, kind: str, picked: dict, fields: dict, resolved: list[dict] | None = None) -> tuple[Incident | None, str]:
    """Check the model's reading has what its kind needs, then build the Incident.

    Returns (incident, "") or (None, reason). The checks mirror the rule reader's conditions
    in _read_section, so neither path can act on less evidence than the other.
    """
    # Each date phrase must parse to exactly one calendar date ("next Friday", "2027-03-24").
    dates = resolved or []
    for name in ("start_date", "end_date") if not resolved else ():
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


def _chunks(text: str, marks: list) -> list[str]:
    """Text after each list marker. A header before the first marker is dropped."""
    chunks = []
    for index, mark in enumerate(marks):
        stop = marks[index + 1].start() if index + 1 < len(marks) else len(text)
        chunk = text[mark.end():stop].strip()
        if chunk:
            chunks.append(chunk)
    return chunks or [text]


def _sections(text: str) -> list[str]:
    """Parts of a compound message, or the whole text when it is not a list.

    Recognized lists: "(1) ... (2) ...", "1) ... 2) ...", "A) ... B) ...", and
    "First, ... Second, ...". A single marker is not a list.
    """
    marks = list(_MARKER.finditer(text))
    if len(marks) < 2:
        bare = list(_MARKER_BARE.finditer(text))
        # Only a real list: the markers count up 1, 2, ...
        if len(bare) >= 2 and [int(m.group(1)) for m in bare] == list(range(1, len(bare) + 1)):
            marks = bare
    if len(marks) < 2:
        letters = list(_LETTER.finditer(text))
        got = [m.group(1).upper() for m in letters]
        if len(got) >= 2 and got == [chr(ord("A") + i) for i in range(len(got))]:
            marks = letters
    if len(marks) < 2:
        ordinals = list(_ORDINAL.finditer(text))
        names = [m.group(1).lower() for m in ordinals]
        if len(names) >= 2 and names == ["first", "second", "third"][: len(names)]:
            marks = ordinals
    if len(marks) < 2:
        return [text]
    return _chunks(text, marks)


def _name_closed(section: str, plant) -> bool:
    """True when 'closed' follows the plant name ('Lexington closed', 'San Antonio plant closed').

    'Markets closed' does not: the word has to sit next to the resolved plant.
    """
    if plant is None:
        return False
    tail = section[plant.end: plant.end + 40]
    return re.match(r"(?:\W+(?:plant|line))?\W+closed\b", tail, re.I) is not None


# The rule reader. Kinds are tried in priority order; each needs its keywords AND the fields to
# act on, otherwise it falls through to rumor, then noise.
def _read_section(graph, section: str, anchor=None) -> Incident:
    """Deterministic reading of one section. Always returns an Incident (noise at worst).

    Order: hearsay, non-events, quality hold, plant outage, supplier delay, a weaker rumor,
    incident wording too incomplete to act on (escalate), noise.
    """
    mentions = graph.resolve_mentions(section)
    dates, restart_notes = _operational_dates(section, anchor)
    folded = _fold(section)
    quality_hits = _hits(section, _QUALITY, folded)
    outage_hits = _hits(section, _OUTAGE, folded)
    delay_hits = _hits(section, _DELAY, folded)
    rumor_hits = _hits(section, _RUMOR, folded)
    # For each entity type: (first mention, its aliases, other ids of that type).
    picked = {kind: _pick(mentions, kind) for kind in ("plant", "part", "lot", "supplier", "shipment")}

    plant = picked["plant"][0]
    part = picked["part"][0]
    lot = picked["lot"][0]
    supplier = picked["supplier"][0]
    shipment = picked["shipment"][0]
    # "Lexington closed 16 Mar" names no outage verb; the plant name itself is the subject.
    if _name_closed(section, plant):
        outage_hits = [*outage_hits, "closed"]

    # Hearsay first: a fully specified sentence that is still a rumor is escalated, never acted on.
    hearsay = _hits(section, _HEARSAY, folded)
    if hearsay:
        return _unconfirmed(section, picked, dates, hearsay, inverted=False)
    # Non-events ("no delay expected", "if it goes past", a fire drill) write nothing.
    if _hits(section, _NON_EVENT, folded):
        return _noise(section, picked, [], [], [])
    # A date that is not a real day ("March 32") leaves the window unknown: escalate, never guess.
    bad_dates = impossible_dates(section)
    if bad_dates and (quality_hits or outage_hits or delay_hits):
        unclear = _unclear(graph, section, picked, dates, quality_hits + outage_hits + delay_hits)
        unclear.summary = (f"The message names {', '.join(repr(d) for d in bad_dates)}, which is not a real date, "
                           "so its window cannot be trusted. It is escalated for a human to confirm.")
        unclear.evidence.append("impossible date: " + ", ".join(bad_dates))
        return unclear
    # Quality: a bulletin can also say "on hold" or "delayed", and the hold is what matters. A known
    # lot is enough on its own; the lot record supplies plant, part and build dates.
    lot_known = lot is not None and lot.entity_id in graph.lots
    quality_specified = plant is not None and (part is not None or lot is not None) and len(dates) >= 2
    if quality_hits and (lot_known or quality_specified):
        return _quality(graph, picked, dates, quality_hits)
    if outage_hits and plant is not None and len(dates) >= 1:
        return _outage(picked, dates, outage_hits, restart_notes)
    # A delay is located by a shipment id, or by a known part and plant (the supplier may be unnamed:
    # the shipment table supplies it). Labelled dates ("original drop", "new ETA") bind in any order.
    if delay_hits and len(dates) >= 2 and (shipment is not None or (part is not None and plant is not None)):
        return _delay(graph, picked, _bind_labeled_etas(section, dates), delay_hits)
    # Rumor wording, or an incident too incomplete to act on, is escalated, not ignored.
    if rumor_hits and (_hits(section, _TROUBLE) or quality_hits or outage_hits or delay_hits):
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
            "delay wording was incomplete (needs two dates and a shipment, or a part and a plant): "
            + ", ".join(delay_hits)
        )
    evidence.extend(_chosen_lines(picked, ("plant", "part", "supplier", "shipment", "lot")))
    return Incident(kind="noise", summary=summary, evidence=evidence)


def _bind_labeled_etas(section: str, dates: list[dict]) -> list[dict]:
    """Order a delay's dates as original ETA, then new ETA, when both labels are present.

    The date after "original drop", "was due" or "due" is the original ETA; the date after
    "new ETA" or "will now arrive" is the new one. With either label missing, reading order stays,
    so "can't make it next Monday ... next Friday" still reads first date, then second.
    """
    if len(dates) < 2:
        return dates
    original = _date_after(dates, _label_ends(section, _ORIGINAL_ETA))
    revised = _date_after(dates, _label_ends(section, _NEW_ETA))
    if original is None or revised is None or original is revised:
        return dates
    rest = [item for item in dates if item is not original and item is not revised]
    return [original, revised, *rest]


def _label_ends(text: str, phrases: tuple[str, ...]) -> list[int]:
    """End offsets of the phrases. A longer phrase owns its span."""
    occupied: list[tuple[int, int]] = []
    ends: list[int] = []
    for phrase in sorted(phrases, key=len, reverse=True):
        for match in re.finditer(rf"(?<![A-Za-z0-9]){re.escape(phrase)}(?![A-Za-z0-9])", text, re.I):
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


def _operational_dates(section: str, anchor=None) -> tuple[list[dict], list[str]]:
    """Dates in reading order, without a trailing restart day.

    A restart date is not a day down. When the message gives one start date and then when work
    resumes ("suspended starting 3/24 ... back up on 3/26"), the last day down is the working day
    before the restart, and that is added as the second date.
    """
    dates = extract_dates(section, anchor)
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
    if len(earlier) == 1 and ignored:
        last = _day_before_restart(ignored[0]["date"])
        if last and last >= earlier[0]["date"]:
            earlier = earlier + [{"phrase": f"the day before '{ignored[0]['phrase']}'", "date": last,
                                  "start": ignored[0]["start"], "end": ignored[0]["end"]}]
            note += f"; work resumes {ignored[0]['date']}, so the last day down is {last}"
    return earlier, [note]


def _day_before_restart(iso_day: str) -> str | None:
    """The working day before a restart date."""
    d = date.fromisoformat(iso_day) - timedelta(days=1)
    while not is_working_day(d):
        d -= timedelta(days=1)
    return d.isoformat()


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


_COMPILED_HITS: dict[tuple[str, ...], tuple[re.Pattern, ...]] = {}


def _hits(text: str, patterns: tuple[str, ...], folded: str | None = None) -> list[str]:
    """The words in text that match any pattern, as whole words, in reading order, each once.
    The matched words are quoted in the evidence, so the trace shows what was actually read.
    `folded` is _fold(text) when the caller already has it; the patterns are compiled once."""
    if folded is None:
        folded = _fold(text)
    compiled = _COMPILED_HITS.get(patterns)
    if compiled is None:
        compiled = tuple(re.compile(r"(?<![a-z0-9])(?:" + p + r")(?![a-z0-9])") for p in patterns)
        _COMPILED_HITS[patterns] = compiled
    found = []
    for pattern in compiled:
        for m in pattern.finditer(folded):
            if m.group(0) not in found:
                found.append(m.group(0))
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
