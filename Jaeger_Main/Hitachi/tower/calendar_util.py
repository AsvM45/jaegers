"""Working-day calendar, read from the company's calendar.csv: today is the row with
day_index 0 (Monday 2027-03-08), and the planning window is the table's first to last index.

Relative dates follow one rule, checked against the delay sentences in the
feed: a new ETA has to fall after the original ETA.

"next <weekday>" means that weekday in the next calendar week
(the week after today's), not the rest of this week.
"last <weekday>" means the most recent past occurrence, never today.
"this <weekday>" means the occurrence in the current week.

That reading is the one that keeps "next Monday" before "next Friday"
when both appear in the same delay notice. It is recorded in PROGRESS.md
so we can flip it in one place if we decide otherwise.
"""

from __future__ import annotations

import csv
import os
import re
from datetime import date, timedelta

# calendar.csv, beside the other company tables. (Not imported from tower.graph, which imports us.)
_CALENDAR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                         "Data", "hack_the_highway_package", "data", "calendar.csv")


def _load_calendar(path: str = _CALENDAR) -> tuple[date, int, int]:
    """(today, first index, last index) from the calendar table, not from constants in code."""
    with open(path, newline="", encoding="utf-8") as handle:
        rows = {int(r["day_index"]): date.fromisoformat(r["date"]) for r in csv.DictReader(handle)}
    return rows[0], min(rows), max(rows)


# Working-day index: 0 = today, FIRST_IDX = two weeks back (already built), LAST_IDX = the end of
# the planning window. Currently 2027-03-08, -10 and 19.
TODAY, FIRST_IDX, LAST_IDX = _load_calendar()
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

# Date shapes people write: ISO (2027-03-24); relative (next Friday / last Monday); month and
# day, with an optional weekday, ordinal and year (Monday Mar 22, Thu. March 25th, Mar 3, 2027);
# day and month (22 March, 22nd of March); and month/day (3/24, Wed 3/24, 3/24/27).
_WEEKDAY = (r"(mon(?:day)?|tue(?:s(?:day)?)?|wed(?:nesday)?|thu(?:r(?:s(?:day)?)?)?|fri(?:day)?"
            r"|sat(?:urday)?|sun(?:day)?)\.?,?")
_MONTH = (r"(jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|june?|july?|aug(?:ust)?|"
          r"sep(?:t(?:ember)?)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)\.?")
_ORD = r"(?:st|nd|rd|th)?"
_YEAR = r"(?:,?\s+(20\d\d))?"
_ISO = re.compile(r"\b(\d{4})-(\d{2})-(\d{2})\b")
_NEXT = re.compile(r"\b(next|last|this|coming)\s+(mon(?:day)?|tue(?:s(?:day)?)?|wed(?:nesday)?|thu(?:r(?:s(?:day)?)?)?"
                   r"|fri(?:day)?|sat(?:urday)?|sun(?:day)?)\b\.?", re.I)
_NAMED = re.compile(r"\b(?:" + _WEEKDAY + r"\s+)?" + _MONTH + r"\s+(\d{1,2})" + _ORD + r"\b" + _YEAR, re.I)
_DAY_MONTH = re.compile(r"\b(?:" + _WEEKDAY + r"\s+)?(\d{1,2})" + _ORD + r"\s+(?:of\s+)?" + _MONTH + r"(?![a-z])" + _YEAR, re.I)
# Not a fraction: "3/4 capacity", "3/4-inch", "1/2 of the lot".
_SLASH = re.compile(r"\b(?:" + _WEEKDAY + r"\s+)?(\d{1,2})/(\d{1,2})(?:/(\d{2}|\d{4}))?\b(?![/\d])"
                    r"(?!\s*-?\s*(?:inch|in\b|capacity|full|of\b|mile|ton|scale|time))", re.I)
# A day with no month: "the 24th", "Monday the 29th", "Wed. 17th". The month comes from context
# (see _day_only_date). Needs "the" or a weekday, and an ordinal, so counts like "4 lots" are not dates;
# "the 4th quarter" style uses are excluded.
_DAY_ONLY = re.compile(r"\b(?:" + _WEEKDAY + r"\s+(?:the\s+)?|the\s+)(\d{1,2})(st|nd|rd|th)\b"
                       r"(?!\s+(?:quarter|floor|time|shift|place|row|generation|gen|edition|anniversary|of\s+(?!" +
                       r"jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)))", re.I)
# The second end of a range written once: the "24" of "Feb 22-24" or "Feb 22 to 24".
_RANGE_END = re.compile(r"\s*(?:[-\u2013\u2014]|to|through|thru)\s*(\d{1,2})" + _ORD + r"\b(?!\s*[/:])", re.I)


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
    target = [w[:3] for w in WEEKDAYS].index(name.lower()[:3])
    which = which.lower()
    # "next X": X in the week that starts next Monday, even if X is still ahead this week.
    if which in ("next", "coming"):
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


def _same_weekday(d: date, written: str) -> bool:
    """'Thu', 'Thurs.' and 'Thursday' all name Thursday."""
    return d.strftime("%A").lower()[:3] == written.lower().rstrip(".,")[:3]


def _named_date(pattern, m) -> tuple[str | None, date | None]:
    """(weekday as written, date) for a _NAMED, _DAY_MONTH or _SLASH match. Messages without a
    year are about the simulation year (today's). None for an impossible date like Feb 30."""
    if pattern is _NAMED:
        weekday, month, day, year = m.group(1), MONTHS[m.group(2).lower().rstrip(".")], int(m.group(3)), m.group(4)
    elif pattern is _DAY_MONTH:
        weekday, day, month, year = m.group(1), int(m.group(2)), MONTHS[m.group(3).lower().rstrip(".")], m.group(4)
    else:
        weekday, month, day, year = m.group(1), int(m.group(2)), int(m.group(3)), m.group(4)
    y = int(year) if year else TODAY.year
    y = 2000 + y if y < 100 else y
    try:
        return weekday, date(y, month, day)
    except ValueError:
        return weekday, None


def _day_only_date(day: int, weekday: str | None, ref: date | None) -> date | None:
    """The date a bare day refers to. With an earlier date in the message (ref), the first match on
    or after it, in ref's month or the next ("2/25 through Monday the 1st" is March 1). Without one,
    today's month in the calendar table. A weekday given with the day must match."""
    months = [(ref.year, ref.month), ((ref.year + ref.month // 12), ref.month % 12 + 1)] if ref else [(TODAY.year, TODAY.month)]
    for year, month in months:
        try:
            d = date(year, month, day)
        except ValueError:
            continue
        if ref and d < ref:
            continue
        if weekday and not _same_weekday(d, weekday):
            continue
        return d
    return None


def parse_phrase(phrase: str) -> date | None:
    """Parse one date phrase. Returns None when the phrase is not a date."""
    text = phrase.strip()
    m = _ISO.fullmatch(text)
    if m:
        return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    m = _NEXT.fullmatch(text)
    if m:
        return _shift_weekday(m.group(1), m.group(2))
    for pattern in (_NAMED, _DAY_MONTH, _SLASH):
        m = pattern.fullmatch(text)
        if m:
            # A weekday given with the date must agree with the calendar, or the phrase is rejected.
            weekday, found = _named_date(pattern, m)
            if found is None:
                return None
            if weekday and not _same_weekday(found, weekday):
                raise ValueError(f"{text} is a {found.strftime('%A')}, not a {weekday}")
            return found
    m = _DAY_ONLY.fullmatch(text) or re.fullmatch(r"(\d{1,2})(st|nd|rd|th)", text, re.I)
    if m:
        weekday = m.group(1) if m.re is _DAY_ONLY else None
        day = int(m.group(2) if m.re is _DAY_ONLY else m.group(1))
        return _day_only_date(day, weekday, None)
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
    for pattern in (_NAMED, _DAY_MONTH, _SLASH):
        for m in pattern.finditer(text):
            # Skip a match that overlaps one already found, e.g. the "Monday" of "next Monday".
            if any(s < m.end() and m.start() < e for s, e, _, _ in found):
                continue
            weekday, found_date = _named_date(pattern, m)
            if found_date is None or (weekday and not _same_weekday(found_date, weekday)):
                continue
            found.append((m.start(), m.end(), m.group(0), found_date))
            # "Feb 22-24": the second end of the range keeps the month of the first.
            end = _RANGE_END.match(text, m.end())
            if pattern is _NAMED and end:
                try:
                    second = found_date.replace(day=int(end.group(1)))
                except ValueError:
                    second = None
                if second and second > found_date:
                    found.append((end.start(1), end.end(), end.group(1), second))
    # The three passes ran separately; put the results back in reading order, because the
    # readers take "first date = start, second date = end".

    def _free(start: int, end: int) -> bool:
        return not any(s < end and start < e for s, e, _, _ in found)

    for m in _RELDAY.finditer(text):
        if _free(m.start(), m.end()):
            found.append((m.start(), m.end(), m.group(0), TODAY + timedelta(days=_RELDAY_SHIFT[m.group(1).lower()])))
    found.sort(key=lambda item: item[0])
    # A day with no month takes its month from the date before it in the message, if any.
    for m in _DAY_ONLY.finditer(text):
        if not _free(m.start(), m.end()):
            continue
        earlier = [item[3] for item in found if item[0] < m.start()]
        when = _day_only_date(int(m.group(2)), m.group(1), earlier[-1] if earlier else None)
        if when:
            found.append((m.start(), m.end(), m.group(0), when))
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
