"""Buyer scenarios drawn from control-tower, risk, visibility, recall, and audit products.

Palantir-style cases require an ontology object, a graph path, and a schema-valid
action. Planning cases replan only the plant the disruption names. Risk-monitor
cases drop unrelated news and escalate rumors. Visibility cases revise an ETA or
refuse an inverted one. Recall cases hold the lot and do not reschedule. Audit
cases open one human ticket, with a reason, and never a silent write.
"""

from __future__ import annotations

import unittest
from datetime import date

from enterprise import TOOLS, Enterprise
from tower.agents.coordinator import handle_event
from tower.graph import WorldGraph

_PLANTS = (
    ("Lexington", "P_KY"),
    ("the Texas plant", "P_TX"),
    ("Jackson", "P_MS"),
    ("Princeton", "P_IN"),
    ("Huntsville", "P_AL"),
    ("Greensboro", "P_NC"),
)
_SUPPLY = frozenset({"mes.reschedule", "mes.transfer"})
_RECALL_FORBIDDEN = frozenset({
    "mes.reschedule",
    "mes.transfer",
    "dealer.notify",
    "crm.assign_loaner",
})


def _outage(plant: str, left: str = "2027-03-24", right: str = "2027-03-25") -> str:
    return (
        f"{plant} lost production to a power failure. "
        f"Production is stopped from {left} through {right} inclusive."
    )


def _eta(left: str = "2027-03-15", right: str = "2027-03-18") -> str:
    return (
        "Subject: Shipment SH-0182 delayed. Our shipment SH-0182 of CAM-360 "
        f"for Princeton was due {left} and will now arrive {right}."
    )


def _lot() -> str:
    return (
        "QUALITY BULLETIN: Lot LOT-0191 (CHIP-IVI) installed at Princeton "
        "has a faulty weld. Place the lot on hold."
    )


def build_cases() -> list[dict]:
    rows: list[dict] = []

    def add(lane: str, kinds: list[str], text: str, **extra) -> None:
        rows.append({"lane": lane, "kinds": kinds, "text": text, **extra})

    for name, plant_id in _PLANTS:
        add("replan", ["plant_outage"], _outage(name), plant=plant_id, head="Plant", writes=True)
    for left, right in (
        ("2027-03-15", "2027-03-18"),
        ("March 15th", "March 18th"),
        ("2027/03/15", "2027/03/18"),
        ("next Monday", "next Friday"),
    ):
        add("replan", ["supplier_delay"], _eta(left, right), plant="P_IN", head="Shipment", writes=True)
    for _ in range(4):
        add("recall", ["quality_hold"], _lot(), head="Lot", writes=True)
    add("schema", ["noise"], "Quality bulletin: lot LOT-9999 has a faulty weld. That lot is not in the book.")
    add("schema", ["noise"], "Transfer production order PO-99999 to Lexington on 2027-03-18.")
    add("schema", ["noise"], "Stop sale of VIN ZZ-NOT-A-CAR at every dealer.")
    add(
        "compound",
        ["plant_outage", "supplier_delay"],
        f"(1) {_outage('Lexington')} (2) {_eta()}",
        heads=("Plant", "Shipment"),
        writes=True,
    )
    add(
        "compound",
        ["supplier_delay", "quality_hold"],
        f"(1) {_eta()} (2) {_lot()}",
        heads=("Shipment", "Lot"),
        writes=True,
    )
    add(
        "compound",
        ["plant_outage", "quality_hold"],
        f"(1) {_outage('Jackson')} (2) {_lot()}",
        heads=("Plant", "Lot"),
        writes=True,
    )

    for name, plant_id in _PLANTS:
        add(
            "replan",
            ["supplier_delay"],
            (
                f"The infotainment chip run for {name} can't make it 2027-03-16. "
                "Carrier says 2027-03-19 now."
            ),
            plant=plant_id,
        )
    for style, text in (
        ("mail", "From: planning@example\n\n" + _outage("Lexington")),
        ("upper", _outage("Lexington").upper()),
        ("slash", _outage("Lexington", "2027/03/24", "2027/03/25")),
        ("words", _outage("Lexington", "March 24th", "March 25th")),
    ):
        add("replan", ["plant_outage"], text, plant="P_KY", restart="2027-03-26", writes=True, tag=style)
    for copy in range(4):
        add(
            "replan",
            ["plant_outage", "plant_outage"],
            f"(1) {_outage('Lexington')} (2) {_outage('Lexington')} copy {copy}",
            plant="P_KY",
            once=True,
            writes=True,
        )
    for left, right in (
        ("2027-03-15", "2027-03-18"),
        ("2027-03-16", "2027-03-19"),
        ("2027-03-17", "2027-03-22"),
        ("2027-03-18", "2027-03-23"),
        ("2027-03-22", "2027-03-25"),
    ):
        add(
            "replan",
            ["supplier_delay"],
            _eta(left, right),
            plant="P_IN",
            window=True,
            writes=True,
        )

    for text in (
        "Hurricane warning for a coastal county. Send the brochure PDF.",
        "The price list for accessories was updated this morning.",
        "Weather in a city we do not build in is sunny. Picnic is on.",
        "Cyber notice: reset your email password before Friday.",
        "Staff meeting at a restaurant downtown. Book the conference room.",
        "Port gossip with no shipment, no part, and no plant.",
        "Marketing asks where the new brochure PDF lives.",
        "A factory fire was reported overseas. No site of ours is named.",
        "Commodity prices moved overnight. Update the slide deck.",
        "The parking gate by the visitor entrance is stuck.",
        "Please share the org chart with the new hire.",
        "Timesheets are due before noon.",
        "The lobby flowers were replaced.",
        "Conference room booking for a birthday.",
        "Printer on the second floor needs paper.",
    ):
        add("noise", ["noise"], text)
    for text in (
        "Rumor from a supplier rep: something may be off with a seat material. No dates, nothing confirmed.",
        "Someone on the floor mentioned a possible shortage of something electronic. Not confirmed.",
        "Unconfirmed: Lexington might be dark next week. No dates.",
        "Nothing confirmed about a chip problem at Princeton.",
        "Someone mentioned a battery issue. No dates, not confirmed.",
        "This may be off. A plant somewhere may be down. Nothing confirmed.",
        "Not confirmed: shipment trouble on an unnamed lane. No dates.",
        "Rumor only. Quality of a seat material may be off. No dates, nothing confirmed.",
        "Someone on the floor said a lot failed. Not confirmed, no dates.",
        "Unconfirmed report of a late truck. No dates and nothing confirmed.",
    ):
        add("escalate", ["unconfirmed"], text)

    for left, right in (
        ("2027-03-15", "2027-03-19"),
        ("2027-03-16", "2027-03-22"),
        ("Monday Mar 15", "Thursday Mar 18"),
        ("15th of March", "18th of March"),
        ("2027-03-23", "2027-03-26"),
    ):
        add("replan", ["supplier_delay"], _eta(left, right), plant="P_IN", head="Shipment", writes=True)
    for plant in ("Huntsville", "Princeton", "Jackson", "Lexington", "Greensboro"):
        add(
            "replan",
            ["supplier_delay"],
            (
                f"The surround-view cameras run for {plant} can't make it Monday Mar 29. "
                "Carrier says Thursday Apr 1 now (a customs inspection)."
            ),
        )
    for text in (
        "No delay expected. Shipment SH-0182 of CAM-360 for Princeton was due 2027-03-15 and will now arrive 2027-03-18.",
        "No delay expected on the Huntsville camera run.",
        "Plant outage drill at Lexington from 2027-03-24 through 2027-03-25.",
        "If it goes past Friday, Princeton can't make the chip run. Original drop 2027-03-15, new ETA 2027-03-18.",
        "Drill message: lot LOT-0191 faulty weld. This is an exercise.",
    ):
        add("noise", ["noise"], text)
    for text in (
        "Volt says the heavy-duty wiring harness to the Texas plant is delayed. The new ETA is 2027-03-09 and the original drop was 2027-03-18.",
        "Shipment SH-0182 for Princeton was due 2027-03-18 and will now arrive 2027-03-15.",
        "The infotainment chip for Princeton was due 2027-03-19. Carrier says 2027-03-15 now.",
        "CAM-360 for Huntsville original drop 2027-04-01, new ETA 2027-03-29.",
        "Lexington battery packs were due next Friday and will now arrive next Monday.",
    ):
        add("escalate", ["unconfirmed"], text)

    for copy in range(10):
        add("recall", ["quality_hold"], f"Campaign {copy}. {_lot()}", head="Lot", writes=True)
    for text in (
        "Quality alert: the infotainment chip sent to Jackson had a faulty weld. Anything built Thursday Feb 25 through last Monday is suspect.",
        "Quality bulletin: infotainment chip at Jackson, faulty weld, Thursday Feb 25 through last Monday.",
        "Suspect infotainment chip contamination at Jackson from 2027-02-25 through 2027-03-01.",
        "Quality alert: faulty weld on the infotainment chip sent to Jackson. Builds from February 25 through March 1 are suspect.",
        "Quality bulletin for Jackson. The infotainment chip is faulty. Window Thursday Feb 25 through last Monday.",
    ):
        add("recall", ["quality_hold"], text, writes=True)
    for text in (
        "Quality alert for the company newsletter.",
        "Faulty staple on the flyer.",
        "Suspect a typo in the timesheet.",
        "Contamination of the coffee urn.",
        "Quality bulletin: bring a dessert.",
    ):
        add("noise", ["noise"], text)
    for copy in range(5):
        add(
            "recall",
            ["quality_hold"],
            f"Recall desk {copy}. {_lot()} Stop sale of unsold vehicles and contact owners.",
            head="Lot",
            writes=True,
            recall=True,
        )

    for text in (
        "Acknowledged. Please send the brochure PDF.",
        "Ticket closed. The picnic memo needs no action.",
        "Pager note: lobby flowers look fine.",
        "Severity low. Share the org chart.",
        "Incident channel renamed. Book the conference room.",
        "On call rotation for next week. Bring a monitor.",
        "Status page is green. Timesheets are due.",
        "Postmortem of the picnic. No operational note.",
        "Duplicate page for the brochure request.",
        "Human ack only: the visitor gate sign was reprinted.",
    ):
        add("noise", ["noise"], text)
    for text in (
        "Rumor, nothing confirmed, no dates: a seat material may be off.",
        "Not confirmed by anyone. Someone mentioned a shortage.",
        "Unconfirmed plant trouble. No dates.",
        "Nothing confirmed. May be off. No dates.",
        "Someone on the floor mentioned an issue. Not confirmed.",
        "Rumor only, no dates, nothing confirmed, may be off.",
        "Not confirmed: possible electronic shortage sometime soon.",
        "Someone mentioned a late truck. No dates. Nothing confirmed.",
        "Unconfirmed quality gossip. No lot, no dates.",
        "Rumor from a supplier rep. Nothing confirmed.",
    ):
        add("escalate", ["unconfirmed"], text)
    for copy in range(5):
        add(
            "escalate",
            ["unconfirmed", "unconfirmed"],
            (
                f"(1) Rumor, nothing confirmed, no dates, item {copy}. "
                "(2) Someone on the floor mentioned a shortage. Not confirmed."
            ),
        )
    for word in ("Rumor", "Unconfirmed", "nothing confirmed", "no dates", "not confirmed"):
        add(
            "escalate",
            ["unconfirmed"],
            f"{word}: a supplier issue may be off and nothing is specific enough to plan.",
        )
    for name, plant_id in _PLANTS:
        add(
            "replan",
            ["plant_outage"],
            _outage(name) + " Keep the published planning horizon.",
            plant=plant_id,
            head="Plant",
        )
    for text in (
        "Milestone update: the truck checked in. Send the brochure PDF.",
        "Geofence ping far from our plants. Book the conference room.",
        "Carrier check-call. The picnic memo is unchanged.",
        "Dwell alert on a lane we do not use. Share the org chart.",
        "Status arrived for an unnamed parcel. Timesheets are due.",
    ):
        add("noise", ["noise"], text)

    if len(rows) != 150:
        raise RuntimeError(f"expected 150 buyer cases, built {len(rows)}")
    return rows


CASES = build_cases()


def _paths(trace) -> list[list[str]]:
    found = []
    for result in trace.results:
        found.extend(result.graph_paths)
    return found


def _tools(trace) -> list[str]:
    return [call.tool for call in trace.calls]


class BuyerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.graph = WorldGraph()
        cls.box = Enterprise(cls.graph.data_dir)

    def _run(self, index: int, case: dict):
        event_id = f"buyer-{index:03d}"
        trace = handle_event(
            self.graph,
            self.box,
            {
                "event_id": event_id,
                "received_at": "2027-03-08T08:00:00",
                "source": case["lane"],
                "text": case["text"],
            },
        )
        state = getattr(self.box, "_state", None)
        if isinstance(state, dict):
            state.pop(event_id, None)
        return trace

    def _assert_schema(self, trace) -> None:
        for call in trace.calls:
            self.assertIn(call.tool, TOOLS, call.tool)
            for key in TOOLS[call.tool]["args"]:
                self.assertIn(key, call.args, call.tool)
            self.assertTrue(str(call.reason).strip(), call.tool)

    def _assert_plant(self, trace, plant_id: str) -> None:
        for call in trace.calls:
            if call.tool not in _SUPPLY:
                continue
            order = self.graph.orders[call.args["production_order_id"]]
            self.assertEqual(order["plant_id"], plant_id, call.args["production_order_id"])

    def _check(self, trace, case: dict) -> None:
        self.assertEqual([item.kind for item in trace.incidents], case["kinds"], case["text"][:220])
        self._assert_schema(trace)
        tools = _tools(trace)
        lane = case["lane"]
        if lane == "noise" or case["kinds"] == ["noise"]:
            self.assertEqual(trace.calls, [], case["text"][:180])
            return
        if lane == "escalate" or set(case["kinds"]) <= {"unconfirmed", "noise"}:
            self.assertEqual(tools, ["escalate"], tools)
            self.assertGreater(len(trace.calls[0].args["reason"]), 8)
            return
        self.assertNotIn("escalate", tools, case["text"][:180])
        if case.get("plant"):
            self._assert_plant(trace, case["plant"])
        if case.get("head"):
            self.assertTrue(
                any(path and path[0].startswith(case["head"]) for path in _paths(trace)),
                case["text"][:180],
            )
        if case.get("heads"):
            heads = {path[0].split()[0] for path in _paths(trace) if path}
            for head in case["heads"]:
                self.assertIn(head, heads, case["text"][:180])
        if case.get("restart"):
            for call in trace.calls:
                if call.tool == "mes.reschedule":
                    self.assertGreaterEqual(call.args["new_date"], case["restart"])
        if case.get("window"):
            incident = next(item for item in trace.incidents if item.kind == "supplier_delay")
            for call in trace.calls:
                if call.tool not in _SUPPLY:
                    continue
                built = self.graph.orders[call.args["production_order_id"]]["build_date"]
                self.assertGreaterEqual(built, incident.blocked_from)
                self.assertLess(built, incident.blocked_until)
        if case.get("once"):
            moved = [
                call.args["production_order_id"]
                for call in trace.calls
                if call.tool in _SUPPLY
            ]
            self.assertEqual(len(moved), len(set(moved)))
        if case.get("recall") or (case["kinds"] == ["quality_hold"]):
            self.assertIn("quality.hold_lot", tools)
            self.assertTrue(_RECALL_FORBIDDEN.isdisjoint(tools), tools)
        if case.get("writes"):
            self.assertTrue(any(call.tool in TOOLS and TOOLS[call.tool]["writes"] for call in trace.calls))
        for call in trace.calls:
            if "new_date" in call.args:
                day = date.fromisoformat(call.args["new_date"])
                self.assertLess(day.weekday(), 5)
                self.assertGreaterEqual(call.args["new_date"], "2027-03-08")
                self.assertLessEqual(call.args["new_date"], "2027-04-02")


def _bind(index: int, case: dict):
    def test(self) -> None:
        self._check(self._run(index, case), case)

    test.__doc__ = case["lane"]
    return test


for _index, _case in enumerate(CASES):
    setattr(BuyerTests, f"test_{_index:03d}_{_case['lane']}", _bind(_index, _case))
