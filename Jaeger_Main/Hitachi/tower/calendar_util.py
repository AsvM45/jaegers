"""Working-day calendar. Today is Monday 2027-03-08 (index 0).

Relative dates follow one rule, checked against the delay sentences in the
feed: a new ETA has to fall after the original ETA.

"next <weekday>" means that weekday in the next calendar week from the
anchor, not the rest of the anchor's week. The default anchor is TODAY, so
that week starts Monday 2027-03-15. "last <weekday>" means the most recent
past occurrence, never the anchor day. "this <weekday>" means the occurrence
in the anchor's calendar week.

That reading is the one that keeps "next Monday" before "next Friday"
when both appear in the same delay notice. It is recorded in PROGRESS.md
so we can flip it in one place if we decide otherwise.
"""

from __future__ import annotations

import re
from datetime import date, timedelta

TODAY = date(2027, 3, 8)
FIRST_IDX, LAST_IDX = -10, 19
WEEKDAYS = ("monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday")
MONTHS = {
    "jan": 1, "january": 1,
    "feb": 2, "february": 2,
    "mar": 3, "march": 3,
    "apr": 4, "april": 4,
    "may": 5,
    "jun": 6, "june": 6,
    "jul": 7, "july": 7,
    "aug": 8, "august": 8,
    "sep": 9, "sept": 9, "september": 9,
    "oct": 10, "october": 10,
    "nov": 11, "november": 11,
    "dec": 12, "december": 12,
}

_MONTH = (
    r"jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|june?|july?|aug(?:ust)?|"
    r"sep(?:t(?:ember)?)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?"
)
_ISO = re.compile(r"\b(\d{4})-(\d{2})-(\d{2})\b")
_SLASH = re.compile(r"\b(\d{4})/(\d{2})/(\d{2})\b")
_NEXT = re.compile(r"\b(next|last|this)\s+(monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b", re.I)
# The year is optional, but it must not be the start of an ISO or slash date.
_NAMED = re.compile(
    r"\b(?:(monday|tuesday|wednesday|thursday|friday|saturday|sunday)\s+)?"
    rf"({_MONTH})"
    r"\s+(\d{1,2})(?:st|nd|rd|th)?(?:\s*,?\s*(\d{4})(?![\d/-]))?\b",
    re.I,
)
_DAY_FIRST = re.compile(
    rf"(?<![\w-])(\d{{1,2}})(?:st|nd|rd|th)?\s+(?:of\s+)?({_MONTH})"
    r"(?:\s*,?\s*(\d{{4}})(?![\d/-]))?\b",
    re.I,
)


def _date_for_index(i: int) -> date:
    return TODAY + timedelta(days=7 * (i // 5) + (i % 5))


# The feed and the slot board ask for FIRST_IDX..LAST_IDX. Same formula either way.
_INDEX_DATES = tuple(_date_for_index(i) for i in range(FIRST_IDX, LAST_IDX + 1))


def idx_to_date(i: int) -> date:
    """Match enterprise.py: Mon-Fri only, index 0 is TODAY."""
    slot = i - FIRST_IDX
    if 0 <= slot < len(_INDEX_DATES):
        return _INDEX_DATES[slot]
    return _date_for_index(i)


def date_to_idx(d: date) -> int:
    days = (d - TODAY).days
    if days % 7 > 4:
        raise ValueError(f"{d.isoformat()} is a weekend")
    return 5 * (days // 7) + days % 7


def is_working_day(d: date) -> bool:
    return d.weekday() < 5


def next_working_day(d: date) -> date:
    """The first weekday strictly after d. This is the plant restart day."""
    n = d + timedelta(days=1)
    while n.weekday() >= 5:
        n += timedelta(days=1)
    return n


def iso(d: date) -> str:
    return d.isoformat()


def _anchor(anchor: date | None) -> date:
    """None means Monday 2027-03-08. Callers never read the wall clock."""
    return TODAY if anchor is None else anchor


def _shift_weekday(which: str, name: str, anchor: date | None = None) -> date:
    """Weekday in the next, current, or previous calendar week from anchor."""
    base = _anchor(anchor)
    target = WEEKDAYS.index(name.lower())
    if which == "next":
        next_monday = base + timedelta(days=(7 - base.weekday()))
        return next_monday + timedelta(days=target)
    if which == "this":
        this_monday = base - timedelta(days=base.weekday())
        return this_monday + timedelta(days=target)
    delta = (base.weekday() - target) % 7
    if delta == 0:
        delta = 7
    return base - timedelta(days=delta)


def event_day(received_at: str | None) -> date:
    """Working date of an event timestamp. Missing or unreadable text is TODAY."""
    if not received_at:
        return TODAY
    text = received_at.strip()
    if "T" in text:
        text = text.split("T", 1)[0]
    elif " " in text:
        text = text.split(" ", 1)[0]
    try:
        return date.fromisoformat(text)
    except ValueError:
        return TODAY


def parse_phrase(phrase: str, anchor: date | None = None) -> date | None:
    """Parse one date phrase. Returns None when the phrase is not a date.

    Relative weekdays are measured from `anchor`. None means TODAY.
    """
    base = _anchor(anchor)
    text = phrase.strip()
    m = _ISO.fullmatch(text)
    if m:
        return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    m = _NEXT.fullmatch(text)
    if m:
        return _shift_weekday(m.group(1), m.group(2), base)
    m = _NAMED.fullmatch(text)
    if m:
        return _from_named(m.group(1), m.group(2), m.group(3), m.group(4), base, text)
    return None


def _from_named(weekday, month, day, year, base: date, text: str) -> date | None:
    """Month-name date. A missing year uses the anchor year. A wrong weekday is refused."""
    found = _safe_date(int(year) if year else base.year, MONTHS[month.lower()], int(day))
    if found is None:
        return None
    if weekday and found.strftime("%A").lower() != weekday.lower():
        raise ValueError(f"{text} is a {found.strftime('%A')}, not a {weekday}")
    return found


def _safe_date(year: int, month: int, day: int) -> date | None:
    """A real calendar day, or None for a phrase such as March 32."""
    try:
        return date(year, month, day)
    except ValueError:
        return None


def extract_dates(text: str, anchor: date | None = None) -> list[dict]:
    """Dates in reading order. Each item is phrase, iso date, and span.

    An impossible day is skipped. The caller then sees whatever dates remain.
    Relative weekdays and named days use `anchor`. None means TODAY, which
    keeps the 2027-03-08 feed on the week of Monday 2027-03-15.
    """
    base = _anchor(anchor)
    found: list[tuple[int, int, str, date]] = []
    def overlaps(start: int, end: int) -> bool:
        return any(s <= start < e or s < end <= e for s, e, _, _ in found)

    for pattern in (_ISO, _SLASH):
        for m in pattern.finditer(text):
            when = _safe_date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
            if when is None or overlaps(m.start(), m.end()):
                continue
            found.append((m.start(), m.end(), m.group(0), when))
    for m in _NEXT.finditer(text):
        if overlaps(m.start(), m.end()):
            continue
        found.append((m.start(), m.end(), m.group(0), _shift_weekday(m.group(1), m.group(2), base)))
    for m in _NAMED.finditer(text):
        if overlaps(m.start(), m.end()):
            continue
        try:
            found_date = _from_named(m.group(1), m.group(2), m.group(3), m.group(4), base, m.group(0))
        except ValueError:
            continue
        if found_date is None:
            continue
        found.append((m.start(), m.end(), m.group(0), found_date))
    for m in _DAY_FIRST.finditer(text):
        if overlaps(m.start(), m.end()):
            continue
        found_date = _safe_date(
            int(m.group(3)) if m.group(3) else base.year,
            MONTHS[m.group(2).lower()],
            int(m.group(1)),
        )
        if found_date is None:
            continue
        found.append((m.start(), m.end(), m.group(0), found_date))
    found.sort(key=lambda item: item[0])
    return [
        {"phrase": phrase, "date": when.isoformat(), "start": start, "end": end}
        for start, end, phrase, when in found
    ]
