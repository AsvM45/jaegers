"""Five hundred messy messages: volume, formatting, and confusing wording.

Each case is one message the reader has to classify. A noise line stays
noise when it is wrapped in mail headers, HTML, JSON, or a pile of filler.
A rumor stays unconfirmed even when the rest of the sentence looks complete.
Dates may use words, ordinals, slashes, or odd dashes. The feed's 15
classifications are checked again at the end.
"""

from __future__ import annotations

import json
import unittest
from pathlib import Path

from enterprise import Enterprise
from tower.agents.coordinator import handle_event
from tower.agents.understand import understand
from tower.contracts import WRITE_TOOLS
from tower.graph import WorldGraph

_PLANTS = (
    "Lexington",
    "the Texas plant",
    "Jackson",
    "Princeton",
    "Huntsville",
    "Greensboro",
)
_NOISE = (
    "Please send the new brochure PDF to the front desk.",
    "The cafeteria closes early on Friday.",
    "Reminder to submit timesheets before noon.",
    "The lobby flowers were replaced this morning.",
    "Can someone book the conference room for a birthday.",
    "The printer on the second floor needs paper.",
    "Thanks for the update on the company picnic.",
    "Please share the org chart with the new hire.",
    "The visitor gate by the entrance is stuck.",
    "Do we have a spare monitor for the reception desk.",
)
_HEARSAY = (
    "Rumor, nothing confirmed, no dates:",
    "Someone mentioned",
    "Someone on the floor said",
    "This may be off and is not confirmed:",
    "Unconfirmed report:",
    "Nothing confirmed:",
)


def _outage(plant: str, left: str, right: str) -> str:
    return (
        f"{plant} lost production. Production is stopped from {left} through {right}."
    )


def _delay(left: str, right: str) -> str:
    return (
        "Shipment SH-0182 of CAM-360 for Princeton was due "
        f"{left} and will now arrive {right}."
    )


def _quality_lot() -> str:
    return "Quality alert: lot LOT-0191 has a faulty weld."


def _quality_window() -> str:
    return (
        "Quality alert: the infotainment chip sent to Jackson had a faulty weld. "
        "Anything built Thursday Feb 25 through last Monday is suspect."
    )


def _dress(text: str, style: str) -> str:
    if style == "plain":
        return text
    if style == "upper":
        return text.upper()
    if style == "gaps":
        return text.replace(" ", "  ")
    if style == "lines":
        return text.replace(" ", "\n")
    if style == "tabs":
        return text.replace(" ", "\t")
    if style == "nbsp":
        return text.replace(" ", "\u00a0")
    if style == "mail":
        return f"From: ops@example\r\nSubject: update\r\n\r\n{text}\r\nThanks"
    if style == "html":
        return f"<div><b>{text}</b></div>"
    if style == "json":
        return json.dumps({"note": text}, ensure_ascii=False)
    if style == "quote":
        return f"> {text}"
    if style == "md":
        return f"**{text}**"
    if style == "zero":
        return text.replace("a", "a\u200b", 1)
    return text


def build_cases() -> list[tuple[list[str], str]]:
    """Exactly 500 unique messages and the incident kinds each one should yield."""
    rows: list[tuple[list[str], str]] = []

    def add(kinds: list[str], text: str) -> None:
        rows.append((kinds, f"{text} [#{len(rows):03d}]"))

    wraps = ("plain", "upper", "gaps", "lines", "mail", "html", "json", "quote")
    for body in _NOISE:
        for style in wraps:
            add(["noise"], _dress(body, style))

    tails = (
        _outage("Lexington", "2027-03-24", "2027-03-25"),
        _delay("2027-03-15", "2027-03-18"),
        _quality_lot(),
        "the line is waiting on battery packs",
        "a seat material may show up sometime",
        "power failure somewhere soon",
        "shipment running behind with no window",
        "defective batch, details later",
        "dark plant, ask around",
        "chip problem, nobody has the bulletin",
    )
    for lead in _HEARSAY:
        for tail in tails:
            add(["unconfirmed"], f"{lead} {tail}")

    lot_styles = (
        "plain", "upper", "gaps", "lines", "tabs", "nbsp", "mail",
        "html", "json", "quote", "md", "zero",
    )
    for style in lot_styles:
        add(["quality_hold"], _dress(_quality_lot(), style))
        add(["quality_hold"], _dress(_quality_window(), style))
    for plant in _PLANTS:
        add(
            ["quality_hold"],
            _dress(
                f"Quality bulletin: lot LOT-0191 faulty weld, also seen near {plant}.",
                "plain",
            ),
        )
    for extra in (
        "Please read below. " + _quality_lot(),
        "URGENT // " + _quality_window(),
        "Re: Re: " + _quality_lot(),
        _quality_lot() + " End of bulletin.",
        "\ufeff" + _quality_lot(),
        _quality_lot().replace("Quality", "Qual\u200bity"),
        _quality_window().replace("Feb", "Feb\u00a0"),
        "```" + _quality_lot() + "```",
        "Note:\n\n" + _quality_window(),
        _quality_lot().replace("-", "\u2013", 1),
    ):
        add(["quality_hold"], extra)

    date_pairs = (
        ("2027-03-24", "2027-03-25"),
        ("2027\u201303\u201324", "2027\u201303\u201325"),
        ("2027/03/24", "2027/03/25"),
        ("March 24th", "March 25th"),
        ("24th of March", "25th of March"),
        ("next Tuesday", "next Thursday"),
        ("Monday Mar 22", "Wednesday Mar 24"),
    )
    styles = ("plain", "upper", "gaps", "nbsp", "lines")
    for plant in _PLANTS:
        for left, right in date_pairs:
            add(["plant_outage"], _dress(_outage(plant, left, right), "plain"))
        for style in styles:
            add(["plant_outage"], _dress(_outage(plant, "2027-03-24", "2027-03-25"), style))
        add(
            ["plant_outage"],
            f"We&apos;re dark at {plant} from 2027-03-24 through 2027-03-25.",
        )

    delay_pairs = (
        ("2027-03-15", "2027-03-18"),
        ("2027/03/15", "2027/03/18"),
        ("2027\u201303\u201315", "2027\u201303\u201318"),
        ("March 15th", "March 18th"),
        ("15th of March", "18th of March"),
        ("next Monday", "next Friday"),
        ("Monday Mar 29", "Thursday Apr 1"),
    )
    for left, right in delay_pairs:
        for style in ("plain", "upper", "gaps", "mail", "html", "json", "nbsp", "lines"):
            add(["supplier_delay"], _dress(_delay(left, right), style))
    for plant in _PLANTS:
        add(
            ["supplier_delay"],
            (
                f"The infotainment chip run for {plant} can't make it 2027-03-15. "
                "Carrier says 2027-03-18 now."
            ),
        )
    for style in ("tabs", "quote", "md", "zero"):
        add(["supplier_delay"], _dress(_delay("2027-03-15", "2027-03-18"), style))

    for plant in _PLANTS:
        add(["noise"], f"There was an outage mentioned in passing near {plant}, no window given.")
        add(["noise"], f"{plant} called about a delayed crate. No window was written down.")
    for body in (
        "There was an outage somewhere.",
        "A shipment is delayed.",
        "Quality alert for the company newsletter.",
        "The new ETA is unknown and no route was named.",
        "Production is stopped, call me.",
        "Faulty wording in the brochure draft.",
        "We are dark on ideas for the picnic.",
        "Lost production of the monthly flyer.",
        "Carrier says hello.",
        "Original drop of the conversation.",
        "Can't make it to the picnic.",
        "Will now arrive at the cafeteria.",
        "Suspect the printer jam.",
        "Contamination of the coffee urn.",
        "Waiting on the brochure PDF.",
        "Power failure of the lobby lamp.",
        "We're dark about the seating chart.",
        "Quality bulletin: bring a dessert.",
        "Outage of patience.",
        "Delayed reply, send the org chart.",
        "New ETA for the birthday cake.",
        "Production is stopped on the slide deck.",
        "Faulty staple on the flyer.",
        "Lost production of napkins.",
        "Can't make it, send the monitor.",
        "Will now arrive: the flowers.",
        "Suspect a typo in the timesheet.",
        "Carrier says the picnic is on.",
    ):
        add(["noise"], body)

    quiet = (
        "No delay expected.",
        "Plant outage drill only.",
        "If it goes past Friday, ignore this exercise.",
    )
    serious = (
        _outage("Lexington", "2027-03-24", "2027-03-25"),
        _delay("2027-03-15", "2027-03-18"),
        _quality_lot(),
        "Princeton power failure from 2027-03-24 through 2027-03-25.",
        "Jackson lost production from March 24th through March 25th.",
    )
    for lead in quiet:
        for tail in serious:
            add(["noise"], f"{lead} {tail}")

    brochure = "Please send the new brochure PDF."
    for plant in _PLANTS:
        add(
            ["noise", "plant_outage"],
            f"(1) {brochure} (2) {_outage(plant, '2027-03-24', '2027-03-25')}",
        )
        add(
            ["unconfirmed", "supplier_delay"],
            f"(1) Rumor, nothing confirmed. (2) {_delay('2027-03-15', '2027-03-18')} for {plant}",
        )
    for count in (3, 4, 5, 6):
        parts = " ".join(
            f"({index}) {_outage(_PLANTS[index % 6], '2027-03-24', '2027-03-25')}"
            for index in range(1, count + 1)
        )
        add(["plant_outage"] * count, parts)
    for count in (2, 3, 4, 5):
        parts = " ".join(f"({index}) {brochure}" for index in range(1, count + 1))
        add(["noise"] * count, parts)
    add(
        ["plant_outage", "supplier_delay", "quality_hold"],
        "(1) "
        + _outage("Lexington", "2027-03-24", "2027-03-25")
        + " (2) "
        + _delay("2027-03-15", "2027-03-18")
        + " (3) "
        + _quality_lot(),
    )
    add(
        ["noise", "noise", "unconfirmed"],
        "(1) Send the brochure. (2) Book the conference room. (3) Someone mentioned a shortage.",
    )
    add(
        ["supplier_delay", "plant_outage"],
        "(1) "
        + _delay("next Monday", "next Friday")
        + " (2) "
        + _outage("Greensboro", "2027/03/24", "2027/03/25"),
    )
    add(
        ["quality_hold", "noise"],
        "(1) " + _quality_window() + " (2) The cafeteria closes early.",
    )
    add(
        ["plant_outage"] * 8,
        " ".join(
            f"({index}) {_outage('Huntsville', 'March 24th', 'March 25th')}"
            for index in range(1, 9)
        ),
    )
    add(
        ["noise"] * 8,
        " ".join(f"({index}) {brochure}" for index in range(1, 9)),
    )

    filler = "Please send the brochure PDF. " * 400
    add(["plant_outage"], filler + _outage("Lexington", "2027-03-24", "2027-03-25"))
    add(["supplier_delay"], filler + _delay("2027-03-15", "2027-03-18"))
    add(["quality_hold"], filler + _quality_lot())
    add(["noise"], filler + "Thanks for the picnic note.")
    add(["unconfirmed"], filler + "Rumor, nothing confirmed, no dates, something may be off.")
    add(
        ["plant_outage"] * 12,
        " ".join(
            f"({index}) {_outage(_PLANTS[index % 6], '2027-03-24', '2027-03-25')}"
            for index in range(1, 13)
        ),
    )
    add(
        ["noise"] * 15,
        " ".join(f"({index}) {brochure} ref pad {index}" for index in range(1, 16)),
    )
    add(
        ["supplier_delay"] * 6,
        " ".join(
            f"({index}) {_delay('2027-03-15', '2027-03-18')}"
            for index in range(1, 7)
        ),
    )
    wide = "\n".join(
        [
            "----- Forwarded -----",
            "From: desk@example",
            "Subject: fyi",
            "",
            "see below, not the ask",
            _outage("Princeton", "24th of March", "25th of March"),
            "signature: the front desk",
        ]
    )
    add(["plant_outage"], wide)
    add(
        ["supplier_delay"],
        "SHIPMENT SH-0182 OF CAM-360 FOR PRINCETON WAS DUE MARCH 15TH AND WILL NOW ARRIVE MARCH 18TH.",
    )
    add(
        ["plant_outage"],
        "Ｌｅｘｉｎｇｔｏｎ lost production. Production is stopped from 2027-03-24 through 2027-03-25.",
    )
    add(["noise"], "outage " * 80 + "send the brochure")
    add(["noise"], "delayed " * 80 + "send the brochure")
    add(
        ["quality_hold"],
        "lot LOT-0191 " * 30 + "Quality alert: lot LOT-0191 has a faulty weld.",
    )
    add(
        ["unconfirmed", "unconfirmed", "noise"],
        "(1) Someone on the floor said the line is odd. (2) Not confirmed, no dates. "
        "(3) Please send the brochure PDF.",
    )
    add(
        ["plant_outage", "noise", "supplier_delay"],
        "(1) "
        + _outage("Jackson", "2027-03-24", "2027-03-25")
        + " (2) Book the conference room. (3) "
        + _delay("2027/03/15", "2027/03/18"),
    )
    add(["noise"], "\t".join([_NOISE[0]] * 12))
    add(["plant_outage"], "### alert\n\n" + _outage("the Texas plant", "next Tuesday", "next Thursday"))
    add(["supplier_delay"], "id,text\n9," + _delay("Monday Mar 29", "Thursday Apr 1"))

    for mark in (" -- ", " | ", " // ", " ... ", " :: "):
        add(["quality_hold"], _quality_lot().replace(": ", mark))
        add(["plant_outage"], _outage("Lexington", "2027-03-24", "2027-03-25").replace(". ", mark))
        add(["supplier_delay"], _delay("2027-03-15", "2027-03-18").replace(" ", mark, 1))
    for plant in _PLANTS:
        add(["noise"], f"No delay expected at {plant}. {_delay('2027-03-15', '2027-03-18')}")
        add(["noise"], f"If it goes past Friday, {_outage(plant, 'March 24th', 'March 25th')}")
    for copy in range(8):
        add(
            ["supplier_delay", "quality_hold"],
            f"(1) {_delay('2027-03-15', '2027-03-18')} copy {copy} (2) {_quality_lot()}",
        )
    for copy in range(10):
        add(
            ["unconfirmed"],
            f"Not confirmed. No dates. Item {copy}. {_outage('Jackson', '2027-03-24', '2027-03-25')}",
        )
        blob = ("see attached. " * (20 + copy)) + _outage(
            _PLANTS[copy % 6], "2027/03/24", "2027/03/25"
        )
        add(["plant_outage"], blob)
        add(["noise"], f"FW: picnic {copy}. " + " ".join(_NOISE))
    for copy in range(11):
        add(["quality_hold"], f"Subject: QB {copy}\n\n{_quality_window()} ref {copy}")

    if len(rows) != 500:
        raise RuntimeError(f"expected 500 cases, built {len(rows)}")
    texts = [text for _, text in rows]
    if len(set(texts)) != 500:
        raise RuntimeError("volume cases are not unique")
    return rows


CASES = build_cases()


def _check(case: unittest.TestCase, incidents, expected: list[str], text: str) -> None:
    case.assertEqual([item.kind for item in incidents], expected, text[:240])
    for item in incidents:
        if item.kind == "plant_outage":
            case.assertTrue(item.plant_id and item.outage_start and item.outage_end, text[:240])
            case.assertLessEqual(item.outage_start, item.outage_end)
        elif item.kind == "supplier_delay":
            case.assertTrue(item.blocked_from and item.blocked_until, text[:240])
            case.assertLess(item.blocked_from, item.blocked_until, text[:240])
        elif item.kind == "quality_hold":
            case.assertTrue(item.lot_id or (item.part_id and item.plant_id), text[:240])


def _bind(text: str, expected: list[str]):
    def test(self) -> None:
        _check(self, understand(self.graph, text), expected, text)

    return test


class VolumeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.graph = WorldGraph()

    def test_feed_classifications_stay_put(self) -> None:
        root = Path(__file__).resolve().parents[2]
        events = json.loads(
            (root / "Data" / "hack_the_highway_package" / "data" / "events.json").read_text(encoding="utf-8")
        )
        stored = {
            row["event_id"]: row["classification"]
            for row in json.loads((root / "runs" / "run1" / "traces.json").read_text(encoding="utf-8"))
        }
        for event in events:
            kinds = "+".join(item.kind for item in understand(self.graph, event["text"]))
            self.assertEqual(kinds, stored[event["event_id"]], event["event_id"])

    def test_sample_actions_keep_the_guardrails(self) -> None:
        box = Enterprise(self.graph.data_dir)
        noisy = [text for expected, text in CASES if expected == ["noise"]][:8]
        rumors = [text for expected, text in CASES if expected == ["unconfirmed"]][:8]
        outages = [text for expected, text in CASES if expected == ["plant_outage"]][:4]
        delays = [text for expected, text in CASES if expected == ["supplier_delay"]][:4]
        holds = [text for expected, text in CASES if expected == ["quality_hold"]][:4]
        for index, text in enumerate(noisy):
            trace = handle_event(self.graph, box, _event(f"vol-noise-{index}", text))
            self.assertEqual(trace.calls, [], text[:180])
        for index, text in enumerate(rumors):
            trace = handle_event(self.graph, box, _event(f"vol-rumor-{index}", text))
            self.assertEqual([call.tool for call in trace.calls], ["escalate"], text[:180])
        for index, text in enumerate(outages + delays + holds):
            trace = handle_event(self.graph, box, _event(f"vol-act-{index}", text))
            self.assertTrue(trace.calls, text[:180])
            self.assertFalse(any(call.tool == "escalate" for call in trace.calls), text[:180])
            for call in trace.calls:
                if call.tool in WRITE_TOOLS and "new_date" in call.args:
                    day = call.args["new_date"]
                    self.assertGreaterEqual(day, "2027-03-08", call.tool)
                    self.assertLessEqual(day, "2027-04-02", call.tool)


def _event(event_id: str, text: str) -> dict:
    return {
        "event_id": event_id,
        "received_at": "2027-03-08T08:00:00",
        "source": "volume",
        "text": text,
    }


for _index, (_expected, _text) in enumerate(CASES):
    setattr(VolumeTests, f"test_{_index:03d}", _bind(_text, _expected))
