"""Working-day calendar. Today is Monday 2027-03-08 (index 0).

Relative dates follow one rule, checked against the delay sentences in the
feed: a new ETA has to fall after the original ETA.

"next <weekday>" means that weekday in the next calendar week
(the week of Monday 2027-03-15), not the rest of this week.
"last <weekday>" means the most recent past occurrence, never today.
"this <weekday>" means the occurrence in the current week.

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

_ISO = re.compile(r"\b(\d{4})-(\d{2})-(\d{2})\b")
_NEXT = re.compile(r"\b(next|last|this)\s+(monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b", re.I)
_NAMED = re.compile(
    r"\b(?:(monday|tuesday|wednesday|thursday|friday|saturday|sunday)\s+)?"
    r"(jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|june?|july?|aug(?:ust)?|"
    r"sep(?:t(?:ember)?)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)"
    r"\s+(\d{1,2})\b",
    re.I,
)


def idx_to_date(i: int) -> date:
    """Match enterprise.py: Mon-Fri only, index 0 is TODAY."""
    return TODAY + timedelta(days=7 * (i // 5) + (i % 5))


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


def _shift_weekday(which: str, name: str) -> date:
    target = WEEKDAYS.index(name.lower())
    if which == "next":
        next_monday = TODAY + timedelta(days=(7 - TODAY.weekday()))
        return next_monday + timedelta(days=target)
    if which == "this":
        this_monday = TODAY - timedelta(days=TODAY.weekday())
        return this_monday + timedelta(days=target)
    delta = (TODAY.weekday() - target) % 7
    if delta == 0:
        delta = 7
    return TODAY - timedelta(days=delta)


def parse_phrase(phrase: str) -> date | None:
    """Parse one date phrase. Returns None when the phrase is not a date."""
    text = phrase.strip()
    m = _ISO.fullmatch(text)
    if m:
        return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    m = _NEXT.fullmatch(text)
    if m:
        return _shift_weekday(m.group(1), m.group(2))
    m = _NAMED.fullmatch(text)
    if m:
        weekday, month, day = m.group(1), m.group(2), int(m.group(3))
        found = date(TODAY.year, MONTHS[month.lower()], day)
        if weekday and found.strftime("%A").lower() != weekday.lower():
            raise ValueError(f"{text} is a {found.strftime('%A')}, not a {weekday}")
        return found
    return None


def extract_dates(text: str) -> list[dict]:
    """Dates in reading order. Each item is phrase, iso date, and span."""
    found: list[tuple[int, int, str, date]] = []
    for m in _ISO.finditer(text):
        found.append((m.start(), m.end(), m.group(0), date(int(m.group(1)), int(m.group(2)), int(m.group(3)))))
    for m in _NEXT.finditer(text):
        found.append((m.start(), m.end(), m.group(0), _shift_weekday(m.group(1), m.group(2))))
    for m in _NAMED.finditer(text):
        span = range(m.start(), m.end())
        if any(s <= m.start() < e or s < m.end() <= e for s, e, _, _ in found):
            continue
        weekday, month, day = m.group(1), m.group(2), int(m.group(3))
        found_date = date(TODAY.year, MONTHS[month.lower()], day)
        if weekday and found_date.strftime("%A").lower() != weekday.lower():
            continue
        found.append((m.start(), m.end(), m.group(0), found_date))
    found.sort(key=lambda item: item[0])
    return [
        {"phrase": phrase, "date": when.isoformat(), "start": start, "end": end}
        for start, end, phrase, when in found
    ]
