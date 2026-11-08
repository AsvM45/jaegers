"""Two hundred ninety more buyer-style messages, so the full suite is 1000 tests.

Noise stays noise. A rumor only escalates. A named outage, a late shipment,
and a known lot still follow the handbook.
"""

from __future__ import annotations

import unittest

from enterprise import TOOLS, Enterprise
from tower.agents.coordinator import handle_event
from tower.graph import WorldGraph

_PLANTS = ("Lexington", "the Texas plant", "Jackson", "Princeton", "Huntsville", "Greensboro")
_PAIRS = (
    ("2027-03-15", "2027-03-18"),
    ("2027-03-16", "2027-03-19"),
    ("2027-03-17", "2027-03-22"),
    ("2027-03-22", "2027-03-25"),
    ("March 15th", "March 18th"),
    ("next Monday", "next Friday"),
)


def _outage(plant: str, left: str, right: str) -> str:
    return (
        f"{plant} lost production to a power failure. "
        f"Production is stopped from {left} through {right} inclusive."
    )


def _delay(left: str, right: str) -> str:
    return (
        "Shipment SH-0182 of CAM-360 for Princeton was due "
        f"{left} and will now arrive {right}."
    )


def build_cases() -> list[tuple[list[str], str, str]]:
    rows: list[tuple[list[str], str, str]] = []

    def add(kinds: list[str], text: str, lane: str) -> None:
        rows.append((kinds, f"{text} ref {len(rows):03d}", lane))

    for index in range(80):
        add(["noise"], f"Please send the brochure PDF to desk {index}. The picnic memo is unchanged.", "noise")
    for index in range(50):
        add(
            ["unconfirmed"],
            f"Rumor, nothing confirmed, no dates. Item {index} may be off and is not specific.",
            "escalate",
        )
    for index in range(60):
        plant = _PLANTS[index % len(_PLANTS)]
        if index % 2 == 0:
            add(["supplier_delay"], _delay("2027-03-15", "2027-03-18") + f" Lane {index}.", "supply")
        else:
            add(["plant_outage"], _outage(plant, "2027-03-24", "2027-03-25") + f" Lane {index}.", "supply")
    for index in range(50):
        left, right = _PAIRS[index % len(_PAIRS)]
        add(["supplier_delay"], _delay(left, right) + f" Carrier note {index}.", "delay")
    for index in range(30):
        add(
            ["quality_hold"],
            f"QUALITY BULLETIN {index}: Lot LOT-0191 has a faulty weld. Place the lot on hold.",
            "recall",
        )
    for index in range(20):
        add(
            ["noise", "plant_outage"],
            f"(1) Please send the brochure PDF {index}. (2) {_outage('Lexington', '2027-03-24', '2027-03-25')}",
            "compound",
        )
    if len(rows) != 290:
        raise RuntimeError(f"expected 290 scale cases, built {len(rows)}")
    return rows


CASES = build_cases()


class ScaleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.graph = WorldGraph()
        cls.box = Enterprise(cls.graph.data_dir)

    def _check(self, index: int, kinds: list[str], text: str, lane: str) -> None:
        event_id = f"scale-{index:03d}"
        trace = handle_event(
            self.graph,
            self.box,
            {
                "event_id": event_id,
                "received_at": "2027-03-08T08:00:00",
                "source": lane,
                "text": text,
            },
        )
        state = getattr(self.box, "_state", None)
        if isinstance(state, dict):
            state.pop(event_id, None)
        self.assertEqual([item.kind for item in trace.incidents], kinds, text[:200])
        tools = [call.tool for call in trace.calls]
        for call in trace.calls:
            self.assertIn(call.tool, TOOLS)
            for key in TOOLS[call.tool]["args"]:
                self.assertIn(key, call.args)
        if lane == "noise":
            self.assertEqual(trace.calls, [])
            return
        if lane == "escalate":
            self.assertEqual(tools, ["escalate"])
            self.assertGreater(len(trace.calls[0].args["reason"]), 8)
            return
        self.assertNotIn("escalate", tools)
        if lane == "recall":
            self.assertIn("quality.hold_lot", tools)
            self.assertNotIn("mes.reschedule", tools)
            self.assertNotIn("crm.assign_loaner", tools)
        if lane in {"supply", "compound", "recall"}:
            self.assertTrue(any(TOOLS[call.tool]["writes"] for call in trace.calls))


def _bind(index: int, kinds: list[str], text: str, lane: str):
    def test(self) -> None:
        self._check(index, kinds, text, lane)

    return test


for _index, (_kinds, _text, _lane) in enumerate(CASES):
    setattr(ScaleTests, f"test_{_index:03d}_{_lane}", _bind(_index, _kinds, _text, _lane))
