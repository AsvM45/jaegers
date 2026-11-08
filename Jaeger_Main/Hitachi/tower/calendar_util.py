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

# Working-day index: 0 = today, -10 = two weeks back (already built), 19 = 2027-04-02 (end of the
# planning window).
TODAY = date(2027, 3, 8)
FIRST_IDX, LAST_IDX = -10, 19
WEEKDAYS = ("monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday")
# Month names and abbreviations, for phrases like 'Thursday Apr 1'.
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

# Three date shapes appear in messages: ISO (2027-03-24), relative (next Friday / last Monday) and
# named (Monday Mar 22).
_ISO = re.compile(r"\b(\d{4})-(\d{2})-(\d{2})\b")
_NEXT = re.compile(r"\b(next|last|this)\s+(monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b", re.I)
_NAMED = re.compile(
    r"\b(?:(monday|tuesday|wednesday|thursday|friday|saturday|sunday)\s+)?"
    r"(jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|june?|july?|aug(?:ust)?|"
    r"sep(?:t(?:ember)?)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)"
    r"\s+(\d{1,2})\b",
    re.I,
)


# "today" / "tomorrow" / "yesterday", and a weekday on its own ("Thursday").
_RELDAY = re.compile(r"\b(today|tomorrow|yesterday)\b", re.I)
_RELDAY_SHIFT = {"today": 0, "tomorrow": 1, "yesterday": -1}
_BARE = re.compile(r"\b(monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b", re.I)


# Index <-> date. Five working days make one calendar week; weekends are skipped.
def idx_to_date(i: int) -> date:
    """Match enterprise.py: Mon-Fri only, index 0 is TODAY."""
    return TODAY + timedelta(days=7 * (i // 5) + (i % 5))


def date_to_idx(d: date) -> int:
    """Inverse of idx_to_date. Raises ValueError on a weekend, which has no index.

    Python's // and % floor toward minus infinity, so past dates map correctly too:
    last Friday (2027-03-05) is -1, and Monday a week ago is -5.
    """
    days = (d - TODAY).days
    if days % 7 > 4:
        raise ValueError(f"{d.isoformat()} is a weekend")
    return 5 * (days // 7) + days % 7


def is_working_day(d: date) -> bool:
    """Monday to Friday. The calendar has no holidays (calendar.csv agrees)."""
    return d.weekday() < 5


def next_working_day(d: date) -> date:
    """The first weekday strictly after d. This is the plant restart day."""
    n = d + timedelta(days=1)
    while n.weekday() >= 5:
        n += timedelta(days=1)
    return n


def iso(d: date) -> str:
    """Shorthand for YYYY-MM-DD, the format every table and tool uses."""
    return d.isoformat()


def _shift_weekday(which: str, name: str) -> date:
    """Resolve "next/this/last <weekday>" against TODAY, using the rules in the module docstring."""
    target = WEEKDAYS.index(name.lower())
    # "next X": X in the week that starts next Monday, even if X is still ahead this week.
    if which == "next":
        next_monday = TODAY + timedelta(days=(7 - TODAY.weekday()))
        return next_monday + timedelta(days=target)
    # "this X": X in the current Monday-to-Sunday week, past or future.
    if which == "this":
        this_monday = TODAY - timedelta(days=TODAY.weekday())
        return this_monday + timedelta(days=target)
    # "last X": the most recent X strictly before today. On a Monday, "last Monday" is a week ago.
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
        # Named dates carry no year; every message is about the simulation year. When a weekday
        # is given too, it must agree with the calendar, or the phrase is rejected.
        weekday, month, day = m.group(1), m.group(2), int(m.group(3))
        found = date(TODAY.year, MONTHS[month.lower()], day)
        if weekday and found.strftime("%A").lower() != weekday.lower():
            raise ValueError(f"{text} is a {found.strftime('%A')}, not a {weekday}")
        return found
    m = _RELDAY.fullmatch(text)
    if m:
        return TODAY + timedelta(days=_RELDAY_SHIFT[m.group(1).lower()])
    m = _BARE.fullmatch(text)
    if m:
        return TODAY + timedelta(days=(WEEKDAYS.index(m.group(1).lower()) - TODAY.weekday()) % 7)
    return None


# Used by both readers: scans text left to right and returns every date phrase with its position.
# A named date whose weekday does not match the calendar is skipped as a typo.
def extract_dates(text: str) -> list[dict]:
    """Dates in reading order. Each item is phrase, iso date, and span."""
    found: list[tuple[int, int, str, date]] = []
    for m in _ISO.finditer(text):
        found.append((m.start(), m.end(), m.group(0), date(int(m.group(1)), int(m.group(2)), int(m.group(3)))))
    for m in _NEXT.finditer(text):
        found.append((m.start(), m.end(), m.group(0), _shift_weekday(m.group(1), m.group(2))))
    for m in _NAMED.finditer(text):
        span = range(m.start(), m.end())
        # Skip a named match that overlaps one already found, e.g. the "Monday" of "next Monday".
        if any(s <= m.start() < e or s < m.end() <= e for s, e, _, _ in found):
            continue
        weekday, month, day = m.group(1), m.group(2), int(m.group(3))
        found_date = date(TODAY.year, MONTHS[month.lower()], day)
        if weekday and found_date.strftime("%A").lower() != weekday.lower():
            continue
        found.append((m.start(), m.end(), m.group(0), found_date))
    # The three passes ran separately; put the results back in reading order, because the
    # readers take "first date = start, second date = end".

    def _free(start: int, end: int) -> bool:
        return not any(s < end and start < e for s, e, _, _ in found)

    for m in _RELDAY.finditer(text):
        if _free(m.start(), m.end()):
            found.append((m.start(), m.end(), m.group(0), TODAY + timedelta(days=_RELDAY_SHIFT[m.group(1).lower()])))
    found.sort(key=lambda item: item[0])
    # A weekday on its own ("this Wednesday and Thursday") is the first such day on or
    # after the date just before it in the text, or on or after today when there is none.
    for m in _BARE.finditer(text):
        if not _free(m.start(), m.end()):
            continue
        earlier = [item[3] for item in found if item[0] < m.start()]
        ref = earlier[-1] if earlier else TODAY
        target = WEEKDAYS.index(m.group(1).lower())
        found.append((m.start(), m.end(), m.group(0), ref + timedelta(days=(target - ref.weekday()) % 7)))
        found.sort(key=lambda item: item[0])
    return [
        {"phrase": phrase, "date": when.isoformat(), "start": start, "end": end}
        for start, end, phrase, when in found
    ]
