"""Adversarial cases for the control tower.

Each test builds its own WorldGraph. When a test executes tools it builds its
own Enterprise. Assertions follow the policy handbook: weekday tool dates in
the planning window, no writes for noise, escalate-only for unconfirmed
reports, and moves only for affected orders.
"""

from __future__ import annotations

import unittest
from collections import Counter
from datetime import date, timedelta

from enterprise import Enterprise, ToolError
from tower.agents.coordinator import handle_event
from tower.agents.dealer_customer import plan_dealer_customer
from tower.agents.quality import plan_quality
from tower.agents.supply_chain import plan_supply
from tower.agents.understand import understand
from tower.calendar_util import LAST_IDX, idx_to_date
from tower.contracts import WRITE_TOOLS, Incident
from tower.graph import WorldGraph
from tower.schedule import LoanerPools, PlantSchedule

WINDOW_START = "2027-03-08"
WINDOW_END = "2027-04-02"
SUPPLY_TOOLS = ("mes.reschedule", "mes.transfer")


def event(event_id: str, text: str) -> dict:
    return {
        "event_id": event_id,
        "received_at": "2027-03-08T08:00:00",
        "source": "adversarial",
        "text": text,
    }


def write_calls(calls) -> list:
    return [call for call in calls if call.tool in WRITE_TOOLS]


def supply_calls(calls) -> list:
    return [call for call in calls if call.tool in SUPPLY_TOOLS]


def _numbered(lines: list[str]) -> str:
    return " ".join(f"({index}) {line}" for index, line in enumerate(lines, 1))


def _all_plant_outage(start: str, end: str) -> str:
    names = (
        "the Texas plant",
        "Lexington",
        "Jackson",
        "Princeton",
        "Huntsville",
        "Greensboro",
    )
    lines = [
        f"Power failure at {name} from {start} through {end}. Production is stopped."
        for name in names
    ]
    return _numbered(lines)


def next_working_day(day: date) -> date:
    """First weekday strictly after day. This is the plant restart."""
    cursor = day + timedelta(days=1)
    while cursor.weekday() >= 5:
        cursor += timedelta(days=1)
    return cursor


def customer_of(graph: WorldGraph, tier: str) -> str:
    matches = [cid for cid, row in graph.customers.items() if row.get("tier") == tier]
    if not matches:
        raise AssertionError(f"no {tier} customer in the customer table")
    return sorted(matches)[0]


def order_row(order_id: str, customer_id: str, promised: str, dealer_id: str = "D27") -> dict:
    return {
        "customer_order_id": order_id,
        "production_order_id": "PO-0031",
        "dealer_id": dealer_id,
        "customer_id": customer_id,
        "model": "RANGER",
        "promised_date": promised,
    }


def fill_plant(schedule: PlantSchedule, plant_id: str) -> None:
    """Occupy every remaining home-plant slot in the planning window."""
    for idx in range(LAST_IDX + 1):
        serial = 0
        while schedule.free_count(plant_id, idx) > 0:
            schedule.slots[(plant_id, idx)].add(f"FILL-{plant_id}-{idx}-{serial}")
            serial += 1


def future_orders(graph: WorldGraph, plant_id: str, start: str, end: str, *, inclusive: bool) -> list[dict]:
    """Movable orders at plant_id on the disruption dates."""
    hits = []
    for order in graph.orders.values():
        if order["idx"] < 0 or order["plant_id"] != plant_id:
            continue
        if inclusive:
            inside = start <= order["build_date"] <= end
        else:
            inside = start <= order["build_date"] < end
        if inside:
            hits.append(order)
    return hits


def models_using(graph: WorldGraph, part_id: str) -> set[str]:
    return set(graph.models_by_part.get(part_id, ()))


class TowerTest(unittest.TestCase):
    def setUp(self) -> None:
        self.graph = WorldGraph()

    def enterprise(self) -> Enterprise:
        return Enterprise(self.graph.data_dir)

    def handle(self, event_id: str, text: str, enterprise: Enterprise | None = None):
        box = enterprise or self.enterprise()
        trace = handle_event(self.graph, box, event(event_id, text))
        return box, trace

    def assert_no_writes(self, calls, msg: str | None = None) -> None:
        found = [(call.tool, call.args) for call in write_calls(calls)]
        self.assertEqual(found, [], msg or "handbook forbids operational writes here")

    def assert_one_escalate(self, calls) -> None:
        tools = [call.tool for call in calls]
        if tools != ["escalate"]:
            self.fail(
                "an unconfirmed report is escalate and nothing else; "
                f"got {dict(Counter(tools))}"
            )

    def assert_weekday_in_window(self, iso_date: str, label: str) -> None:
        day = date.fromisoformat(iso_date)
        self.assertLess(day.weekday(), 5, f"{label} {iso_date} is a weekend")
        self.assertGreaterEqual(iso_date, WINDOW_START, label)
        self.assertLessEqual(iso_date, WINDOW_END, label)

    def assert_only_these_orders_moved(self, box: Enterprise, event_id: str, moved: dict[str, tuple[str, str]]) -> None:
        """Every other future order stays on its original plant and day."""
        state = box.state(event_id)
        for order_id, order in self.graph.orders.items():
            if order["idx"] < 0:
                self.assertNotIn(order_id, state["loc"])
                continue
            location = state["loc"][order_id]
            if order_id in moved:
                plant_id, iso_date = moved[order_id]
                self.assertEqual(location[0], plant_id, order_id)
                self.assertEqual(idx_to_date(location[1]).isoformat(), iso_date, order_id)
            else:
                self.assertEqual(location, (order["plant_id"], order["idx"]), order_id)

    def moved_by(self, calls) -> dict[str, tuple[str, str]]:
        moved: dict[str, tuple[str, str]] = {}
        for call in supply_calls(calls):
            order_id = call.args["production_order_id"]
            self.assertNotIn(order_id, moved, f"{order_id} was moved more than once")
            if call.tool == "mes.reschedule":
                plant_id = self.graph.orders[order_id]["plant_id"]
            else:
                plant_id = call.args["to_plant_id"]
            self.assert_weekday_in_window(call.args["new_date"], call.tool)
            moved[order_id] = (plant_id, call.args["new_date"])
        return moved


class GuardrailTests(TowerTest):
    def test_brochure_mentions_dealer_and_plant_but_writes_nothing(self) -> None:
        text = (
            "Blue Ridge Wacky Wheels attached the spring brochure and price list "
            "for shoppers visiting the Texas plant."
        )
        _box, trace = self.handle("adv-guard-brochure", text)
        self.assertTrue(trace.incidents)
        self.assertTrue(all(item.kind == "noise" for item in trace.incidents))
        self.assertEqual(trace.calls, [])

    def test_rumor_with_no_dates_escalates_once(self) -> None:
        text = "I heard a rumor about the Texas plant, but there are no dates."
        box, trace = self.handle("adv-guard-rumor", text)
        self.assertTrue(all(item.kind == "unconfirmed" for item in trace.incidents))
        self.assert_one_escalate(trace.calls)
        state = box.state("adv-guard-rumor")
        self.assertTrue(state["escalated"])
        self.assertEqual(state["held"], set())
        self.assertEqual(state["loaned"], set())
        self.assertEqual(list(state["notified"]), [])

    def test_unconfirmed_outage_writes_nothing(self) -> None:
        text = (
            "The Texas plant outage from 2027-03-09 through 2027-03-11 is not confirmed."
        )
        _box, trace = self.handle("adv-guard-outage-unconfirmed", text)
        self.assert_one_escalate(trace.calls)

    def test_unconfirmed_delay_writes_nothing(self) -> None:
        text = (
            "Volt says the heavy-duty wiring harness to the Texas plant is delayed, "
            "original drop 2027-03-09, new ETA 2027-03-16, but this is not confirmed."
        )
        _box, trace = self.handle("adv-guard-delay-unconfirmed", text)
        self.assert_one_escalate(trace.calls)

    def test_unconfirmed_quality_bulletin_writes_nothing(self) -> None:
        text = "Quality bulletin: lot LOT-0191 is faulty and on hold. Not confirmed."
        _box, trace = self.handle("adv-guard-quality-unconfirmed", text)
        self.assertEqual([item.kind for item in trace.incidents], ["unconfirmed"])
        self.assert_one_escalate(trace.calls)

    def test_floor_mention_of_an_outage_writes_nothing(self) -> None:
        text = (
            "Someone on the floor mentioned a power failure at Jackson "
            "from Friday Mar 26 through Tuesday Mar 30."
        )
        _box, trace = self.handle("adv-guard-floor-outage", text)
        self.assertEqual([item.kind for item in trace.incidents], ["unconfirmed"])
        self.assert_one_escalate(trace.calls)

    def test_empty_text_writes_nothing(self) -> None:
        _box, trace = self.handle("adv-guard-empty", "")
        self.assertTrue(all(item.kind == "noise" for item in trace.incidents))
        self.assertEqual(trace.calls, [])

    def test_whitespace_only_writes_nothing(self) -> None:
        _box, trace = self.handle("adv-guard-whitespace", " \n\t  ")
        self.assertTrue(all(item.kind == "noise" for item in trace.incidents))
        self.assertEqual(trace.calls, [])


class DateTests(TowerTest):
    def test_inverted_eta_when_original_is_stated_first(self) -> None:
        text = (
            "Volt says the heavy-duty wiring harness to the Texas plant is delayed. "
            "The original drop was 2027-03-18 and the new ETA is 2027-03-09."
        )
        _box, trace = self.handle("adv-date-inverted-original-first", text)
        self.assertEqual([item.kind for item in trace.incidents], ["unconfirmed"])
        self.assert_one_escalate(trace.calls)

    def test_inverted_eta_when_new_date_is_stated_first(self) -> None:
        text = (
            "Volt says the heavy-duty wiring harness to the Texas plant is delayed. "
            "The new ETA is 2027-03-09 and the original drop was 2027-03-18."
        )
        _box, trace = self.handle("adv-date-inverted-new-first", text)
        self.assertEqual([item.kind for item in trace.incidents], ["unconfirmed"])
        self.assert_one_escalate(trace.calls)

    def test_weekend_new_eta_is_not_a_tool_date(self) -> None:
        # 2027-03-12 is Friday. 2027-03-14 is Sunday.
        text = (
            "Volt says the heavy-duty wiring harness to the Texas plant is delayed, "
            "original drop 2027-03-12, new ETA 2027-03-14."
        )
        box, trace = self.handle("adv-date-weekend", text)
        self.assertEqual([item.kind for item in trace.incidents], ["supplier_delay"])
        moved = self.moved_by(trace.calls)
        friday = [
            order["production_order_id"]
            for order in future_orders(self.graph, "P_TX", "2027-03-12", "2027-03-12", inclusive=True)
            if order["model"] in models_using(self.graph, "HARN-B")
        ]
        self.assertTrue(friday)
        for order_id in friday:
            self.assertIn(order_id, moved)
            self.assertGreaterEqual(moved[order_id][1], "2027-03-15", order_id)
        for call in supply_calls(trace.calls):
            self.assert_weekday_in_window(call.args["new_date"], call.tool)
        self.assert_only_these_orders_moved(box, "adv-date-weekend", moved)

    def test_next_monday_and_next_friday(self) -> None:
        text = (
            "Volt says the heavy-duty wiring harness to the Texas plant is delayed, "
            "original drop next Monday, new ETA next Friday."
        )
        incidents = understand(self.graph, text)
        self.assertEqual(len(incidents), 1)
        incident = incidents[0]
        self.assertEqual(incident.kind, "supplier_delay")
        self.assertEqual(incident.blocked_from, "2027-03-15")
        self.assertEqual(incident.blocked_until, "2027-03-19")

        box, trace = self.handle("adv-date-next-weekday", text)
        models = models_using(self.graph, "HARN-B")
        moved = self.moved_by(trace.calls)
        for order_id, (_plant, new_date) in moved.items():
            order = self.graph.orders[order_id]
            self.assertEqual(order["plant_id"], "P_TX")
            self.assertIn(order["model"], models)
            self.assertGreaterEqual(order["build_date"], "2027-03-15")
            self.assertLess(order["build_date"], "2027-03-19")
            self.assertGreaterEqual(new_date, "2027-03-19")
        for order in self.graph.orders.values():
            outside = (
                order["plant_id"] != "P_TX"
                or order["model"] not in models
                or order["build_date"] < "2027-03-15"
                or order["build_date"] >= "2027-03-19"
                or order["idx"] < 0
            )
            if outside:
                self.assertNotIn(order["production_order_id"], moved)
        self.assert_only_these_orders_moved(box, "adv-date-next-weekday", moved)

    def test_outage_ending_on_last_planning_day(self) -> None:
        text = (
            "The Texas plant reports an outage from 2027-04-02 through 2027-04-02. "
            "Production is stopped."
        )
        restart = next_working_day(date(2027, 4, 2)).isoformat()
        self.assertGreater(restart, WINDOW_END)

        box, trace = self.handle("adv-date-last-day", text)
        affected = {
            order["production_order_id"]
            for order in future_orders(self.graph, "P_TX", "2027-04-02", "2027-04-02", inclusive=True)
        }
        self.assertTrue(affected)
        moved = self.moved_by(trace.calls)
        self.assertEqual(set(moved), affected)
        for order_id, (plant_id, new_date) in moved.items():
            self.assertNotEqual(plant_id, "P_TX", order_id)
            self.assertIn(self.graph.orders[order_id]["model"], self.graph.models_by_plant[plant_id])
            self.assert_weekday_in_window(new_date, order_id)
            self.assertGreaterEqual(new_date, WINDOW_START)
        self.assertFalse(any(call.tool == "mes.reschedule" for call in trace.calls))
        self.assert_only_these_orders_moved(box, "adv-date-last-day", moved)

    def test_impossible_calendar_date_does_not_escape(self) -> None:
        text = "The Texas plant outage from 2027-03-09 through March 32. Production is stopped."
        try:
            _box, trace = self.handle("adv-date-march-32", text)
        except Exception as exc:
            self.fail(f"handle_event raised {type(exc).__name__}: {exc}")
        self.assert_no_writes(trace.calls)


class QualityTests(TowerTest):
    def _lot_vehicles(self, lot: dict) -> list[dict]:
        models = models_using(self.graph, lot["part_id"])
        return [
            vehicle
            for vehicle in self.vehicles_view()
            if vehicle["plant_id"] == lot["plant_id"]
            and vehicle["model"] in models
            and lot["first_build_date"] <= vehicle["build_date"] <= lot["last_build_date"]
        ]

    def vehicles_view(self) -> list[dict]:
        return list(self.graph.vehicles.values())

    def test_unknown_lot_produces_no_writes(self) -> None:
        lot = self.graph.lots["LOT-0191"]
        incident = Incident(
            kind="quality_hold",
            lot_id="LOT-NOPE",
            part_id=lot["part_id"],
            plant_id=lot["plant_id"],
            supplier_id=lot["supplier_id"],
            build_start=lot["first_build_date"],
            build_end=lot["last_build_date"],
            summary="Unknown lot LOT-NOPE.",
        )
        result = plan_quality(self.graph, [incident])
        self.assertEqual(result.calls, [])
        self.assertEqual(result.affected_ids, [])

    def test_quality_hold_with_only_a_part_id_writes_nothing(self) -> None:
        incident = Incident(
            kind="quality_hold",
            part_id="CHIP-IVI",
            summary="Quality hold names only a part.",
        )
        result = plan_quality(self.graph, [incident])
        self.assertEqual(result.calls, [])

        _box, trace = self.handle(
            "adv-quality-part-only",
            "Quality alert: the infotainment chip is faulty.",
        )
        self.assert_no_writes(trace.calls)
        self.assertEqual(trace.calls, [])

    def test_lot_0191_holds_stops_sale_and_notifies_without_loaners(self) -> None:
        lot = self.graph.lots["LOT-0191"]
        text = (
            f"Quality bulletin: lot {lot['lot_id']}, the infotainment chip, is faulty "
            f"at the Indiana plant. Suspect builds run from {lot['first_build_date']} "
            f"through {lot['last_build_date']}."
        )
        box, trace = self.handle("adv-quality-lot-0191", text)
        self.assertEqual([item.kind for item in trace.incidents], ["quality_hold"])
        self._assert_lot_containment(box, "adv-quality-lot-0191", trace.calls, lot)

    def test_sold_vehicle_with_empty_customer_id_is_not_notified(self) -> None:
        lot = self.graph.lots["LOT-0191"]
        models = models_using(self.graph, lot["part_id"])
        model = sorted(models)[0]
        self.graph.vehicles["VIN-EMPTY-CUST"] = {
            "vin": "VIN-EMPTY-CUST",
            "production_order_id": "PO-0289",
            "model": model,
            "plant_id": lot["plant_id"],
            "build_date": lot["first_build_date"],
            "dealer_id": "D27",
            "status": "sold",
            "customer_id": "",
        }
        incident = Incident(
            kind="quality_hold",
            lot_id=lot["lot_id"],
            summary="Hold LOT-0191, including a sold vehicle with no customer id.",
        )
        result = plan_quality(self.graph, [incident])
        for call in result.calls:
            if call.tool == "crm.notify_customer":
                self.assertTrue(call.args["customer_id"])
                self.assertNotEqual(call.args["customer_id"], "")
            if call.tool == "dealer.stop_sale":
                self.assertNotIn("VIN-EMPTY-CUST", call.args["vins"])
        notified = {
            call.args["customer_id"]
            for call in result.calls
            if call.tool == "crm.notify_customer"
        }
        self.assertNotIn("", notified)
        vehicles = self._lot_vehicles(lot)
        expected = {
            vehicle["customer_id"]
            for vehicle in vehicles
            if vehicle["status"] == "sold" and vehicle["customer_id"]
        }
        self.assertEqual(notified, expected)

    def test_quality_bulletin_that_only_names_the_lot(self) -> None:
        text = "Quality bulletin: lot LOT-0191 is faulty and on hold."
        box, trace = self.handle("adv-quality-lot-only", text)
        self.assertEqual([item.kind for item in trace.incidents], ["quality_hold"])
        lot = self.graph.lots["LOT-0191"]
        self._assert_lot_containment(box, "adv-quality-lot-only", trace.calls, lot)

    def _assert_lot_containment(self, box: Enterprise, event_id: str, calls, lot: dict) -> None:
        vehicles = self._lot_vehicles(lot)
        in_stock = [vehicle for vehicle in vehicles if vehicle["status"] == "in_stock"]
        sold = [vehicle for vehicle in vehicles if vehicle["status"] == "sold" and vehicle["customer_id"]]
        expected_vins = {vehicle["vin"] for vehicle in in_stock}
        expected_customers = {vehicle["customer_id"] for vehicle in sold}

        holds = [call for call in calls if call.tool == "quality.hold_lot"]
        self.assertEqual([call.args["lot_id"] for call in holds], [lot["lot_id"]])

        stopped: list[str] = []
        for call in calls:
            if call.tool != "dealer.stop_sale":
                continue
            for vin in call.args["vins"]:
                vehicle = self.graph.vehicles[vin]
                self.assertEqual(vehicle["dealer_id"], call.args["dealer_id"])
                self.assertEqual(vehicle["status"], "in_stock")
                stopped.append(vin)
        self.assertEqual(set(stopped), expected_vins)
        self.assertEqual(len(stopped), len(expected_vins))

        notified = [call.args["customer_id"] for call in calls if call.tool == "crm.notify_customer"]
        self.assertEqual(set(notified), expected_customers)
        self.assertEqual(len(notified), len(expected_customers))
        self.assertNotIn("", notified)

        forbidden = {"mes.reschedule", "mes.transfer", "crm.assign_loaner"}
        used = {call.tool for call in calls}
        self.assertTrue(forbidden.isdisjoint(used), sorted(used & forbidden))

        state = box.state(event_id)
        self.assertEqual(state["held"], {lot["lot_id"]})
        self.assertEqual(state["stopped"], expected_vins)
        self.assertEqual(state["customers"], expected_customers)
        self.assertEqual(state["loaned"], set())


class SupplyTests(TowerTest):
    def test_delay_with_no_future_orders_does_not_move(self) -> None:
        text = (
            "Volt says the heavy-duty wiring harness to the Texas plant is delayed, "
            "original drop 2027-02-23, new ETA 2027-03-08."
        )
        box, trace = self.handle("adv-supply-delay-empty", text)
        self.assertEqual(supply_calls(trace.calls), [])
        self.assert_only_these_orders_moved(box, "adv-supply-delay-empty", {})

    def test_outage_with_no_future_orders_does_not_move(self) -> None:
        text = (
            "The Texas plant reports an outage from 2027-02-22 through 2027-02-26. "
            "Production is stopped."
        )
        box, trace = self.handle("adv-supply-outage-empty", text)
        self.assertEqual(supply_calls(trace.calls), [])
        self.assert_only_these_orders_moved(box, "adv-supply-outage-empty", {})

    def test_two_incidents_move_a_shared_order_once(self) -> None:
        delay_until = "2027-03-16"
        outage_end = "2027-03-10"
        restart = next_working_day(date.fromisoformat(outage_end)).isoformat()
        later = max(delay_until, restart)
        models = models_using(self.graph, "HARN-B")
        plant_id = "P_TX"

        delay = Incident(
            kind="supplier_delay",
            supplier_id="SUP-05",
            part_id="HARN-B",
            plant_id=plant_id,
            blocked_from="2027-03-09",
            blocked_until=delay_until,
            summary="Harness delay through 2027-03-16.",
        )
        outage = Incident(
            kind="plant_outage",
            plant_id=plant_id,
            outage_start="2027-03-09",
            outage_end=outage_end,
            summary="Texas outage through 2027-03-10.",
        )
        both: set[str] = set()
        delay_only: set[str] = set()
        outage_only: set[str] = set()
        for order in self.graph.orders.values():
            if order["idx"] < 0 or order["plant_id"] != plant_id:
                continue
            in_delay = (
                order["model"] in models
                and "2027-03-09" <= order["build_date"] < delay_until
            )
            in_outage = "2027-03-09" <= order["build_date"] <= outage_end
            order_id = order["production_order_id"]
            if in_delay and in_outage:
                both.add(order_id)
            elif in_delay:
                delay_only.add(order_id)
            elif in_outage:
                outage_only.add(order_id)
        self.assertTrue(both)
        self.assertTrue(delay_only)
        self.assertTrue(outage_only)

        schedule = PlantSchedule(self.graph)
        result = plan_supply(self.graph, schedule, [delay, outage])
        moved = self.moved_by(result.calls)
        self.assertEqual(set(moved), both | delay_only | outage_only)
        for order_id in both:
            self.assertGreaterEqual(moved[order_id][1], later, order_id)
        for order_id in delay_only:
            self.assertGreaterEqual(moved[order_id][1], delay_until, order_id)
        for order_id in outage_only:
            self.assertGreaterEqual(moved[order_id][1], restart, order_id)

        box = self.enterprise()
        for call in result.calls:
            try:
                box.call("adv-supply-two", call.tool, call.args)
            except ToolError as exc:
                self.fail(f"Enterprise.call rejected {call.tool} {call.args}: {exc}")
        self.assert_only_these_orders_moved(box, "adv-supply-two", moved)

    def test_full_home_plant_transfers_and_enterprise_accepts(self) -> None:
        plant_id = "P_TX"
        start, end = "2027-03-09", "2027-03-10"
        affected = {
            order["production_order_id"]
            for order in future_orders(self.graph, plant_id, start, end, inclusive=True)
        }
        self.assertTrue(affected)
        schedule = PlantSchedule(self.graph)
        fill_plant(schedule, plant_id)
        for idx in range(LAST_IDX + 1):
            self.assertEqual(schedule.free_count(plant_id, idx), 0)

        incident = Incident(
            kind="plant_outage",
            plant_id=plant_id,
            outage_start=start,
            outage_end=end,
            summary="Texas outage with every home slot already full.",
        )
        try:
            result = plan_supply(self.graph, schedule, [incident])
        except Exception as exc:
            self.fail(f"plan_supply raised {type(exc).__name__}: {exc}")

        moved = self.moved_by(result.calls)
        self.assertEqual(set(moved), affected)
        for order_id, (dest, new_date) in moved.items():
            call_tools = [
                call.tool
                for call in result.calls
                if call.args.get("production_order_id") == order_id
            ]
            self.assertEqual(call_tools, ["mes.transfer"], order_id)
            self.assertNotEqual(dest, plant_id)
            model = self.graph.orders[order_id]["model"]
            self.assertIn(model, self.graph.models_by_plant[dest], order_id)
            self.assert_weekday_in_window(new_date, order_id)
        # Rule 3: a transfer may use any free day, including before the restart.
        self.assertTrue(
            any(new_date < "2027-03-11" for _dest, new_date in moved.values()),
            "expected a transfer onto a day before the home plant restarts",
        )

        box = self.enterprise()
        for call in result.calls:
            try:
                box.call("adv-supply-full", call.tool, call.args)
            except ToolError as exc:
                self.fail(f"Enterprise.call rejected {call.tool} {call.args}: {exc}")
        self.assert_only_these_orders_moved(box, "adv-supply-full", moved)
        self._assert_capacity(box, "adv-supply-full")

    def test_order_outside_the_window_is_not_moved(self) -> None:
        text = (
            "Volt says the heavy-duty wiring harness to the Texas plant is delayed, "
            "original drop 2027-02-24, new ETA 2027-03-12."
        )
        models = models_using(self.graph, "HARN-B")
        box, trace = self.handle("adv-supply-outside", text)
        moved = self.moved_by(trace.calls)
        past = [
            order["production_order_id"]
            for order in self.graph.orders.values()
            if order["plant_id"] == "P_TX"
            and order["idx"] < 0
            and order["model"] in models
            and "2027-02-24" <= order["build_date"] < WINDOW_START
        ]
        self.assertTrue(past)
        for order_id, (_plant, new_date) in moved.items():
            order = self.graph.orders[order_id]
            self.assertGreaterEqual(order["idx"], 0, order_id)
            self.assertEqual(order["plant_id"], "P_TX", order_id)
            self.assertIn(order["model"], models, order_id)
            self.assertGreaterEqual(order["build_date"], WINDOW_START, order_id)
            self.assertLess(order["build_date"], "2027-03-12", order_id)
            self.assertGreaterEqual(new_date, "2027-03-12", order_id)
        for order_id in past:
            self.assertNotIn(order_id, moved)
        on_new_eta = [
            order["production_order_id"]
            for order in self.graph.orders.values()
            if order["plant_id"] == "P_TX" and order["build_date"] == "2027-03-12"
        ]
        self.assertTrue(on_new_eta)
        for order_id in on_new_eta:
            self.assertNotIn(order_id, moved)
        self.assert_only_these_orders_moved(box, "adv-supply-outside", moved)

    def test_two_outages_do_not_schedule_builds_during_the_outage(self) -> None:
        windows = {
            "P_TX": ("2027-03-09", "2027-03-11"),
            "P_KY": ("2027-03-09", "2027-03-11"),
        }
        schedule = PlantSchedule(self.graph)
        for plant_id in self.graph.plants:
            fill_plant(schedule, plant_id)
        for plant_id in self.graph.plants:
            for idx in range(LAST_IDX + 1):
                self.assertEqual(schedule.free_count(plant_id, idx), 0, plant_id)

        incidents = [
            Incident(
                kind="plant_outage",
                plant_id=plant_id,
                outage_start=start,
                outage_end=end,
                summary=f"{plant_id} outage {start} through {end}.",
            )
            for plant_id, (start, end) in windows.items()
        ]
        try:
            result = plan_supply(self.graph, schedule, incidents)
        except Exception as exc:
            self.fail(f"plan_supply raised {type(exc).__name__}: {exc}")

        violations = []
        for call in supply_calls(result.calls):
            order_id = call.args["production_order_id"]
            if call.tool == "mes.reschedule":
                dest = self.graph.orders[order_id]["plant_id"]
            else:
                dest = call.args["to_plant_id"]
            day = call.args["new_date"]
            window = windows.get(dest)
            if window and window[0] <= day <= window[1]:
                violations.append(f"{order_id} -> {dest} on {day}")
        self.assertEqual(violations, [])

    def test_every_plant_dark_for_the_whole_window_moves_no_builds(self) -> None:
        text = _all_plant_outage("2027-03-08", "2027-04-02")
        box, trace = self.handle("adv-overload-full", text)
        tools = {call.tool for call in trace.calls}
        self.assertTrue(tools <= {"dealer.notify", "crm.assign_loaner"}, tools)
        self.assertIn("dealer.notify", tools)
        self.assertEqual(self.moved_by(trace.calls), {})
        self._assert_capacity(box, "adv-overload-full")
        self._assert_future_orders_unmoved(box, "adv-overload-full")

    def test_half_window_outage_at_every_plant_stays_inside_capacity(self) -> None:
        text = _all_plant_outage("2027-03-08", "2027-03-19")
        box, trace = self.handle("adv-overload-half", text)
        moved = self.moved_by(trace.calls)
        self.assertTrue(moved)
        for order_id, (_plant, new_date) in moved.items():
            self.assertGreaterEqual(new_date, "2027-03-22", order_id)
        self._assert_capacity(box, "adv-overload-half")
        state = box.state("adv-overload-half")
        for order_id, order in self.graph.orders.items():
            if order["idx"] < 0 or order_id in moved:
                continue
            self.assertEqual(state["loc"][order_id], (order["plant_id"], order["idx"]), order_id)

    def test_forty_copies_of_one_outage_move_each_order_once(self) -> None:
        line = (
            "Power failure at the Texas plant from 2027-03-09 through 2027-03-11. "
            "Production is stopped."
        )
        once = self.handle("adv-overload-once", f"(1) {line}")[1]
        many = self.handle("adv-overload-forty", _numbered([line] * 40))[1]
        self.assertEqual(self.moved_by(once.calls), self.moved_by(many.calls))
        self.assertEqual(len(many.incidents), 40)

    def _assert_future_orders_unmoved(self, box: Enterprise, event_id: str) -> None:
        state = box.state(event_id)
        for order_id, order in self.graph.orders.items():
            if order["idx"] < 0:
                continue
            self.assertEqual(state["loc"][order_id], (order["plant_id"], order["idx"]), order_id)

    def _assert_capacity(self, box: Enterprise, event_id: str) -> None:
        state = box.state(event_id)
        for (plant_id, _idx), occupants in state["slots"].items():
            self.assertLessEqual(len(occupants), box.plants[plant_id]["slots"], plant_id)


class DealerTests(TowerTest):
    def test_empty_customer_order_list_makes_no_calls(self) -> None:
        pools = LoanerPools(self.graph)
        result = plan_dealer_customer(self.graph, pools, [], "No orders.")
        self.assertEqual(result.calls, [])
        self.assertEqual(result.affected_ids, [])

    def test_loaner_pool_of_one_priority(self) -> None:
        platinum = customer_of(self.graph, "Platinum")
        gold = customer_of(self.graph, "Gold")
        standard = customer_of(self.graph, "Standard")

        with self.subTest(rule="platinum before an earlier gold"):
            orders = [
                order_row("CO-9001", gold, "2027-03-10"),
                order_row("CO-9002", platinum, "2027-03-20"),
                order_row("CO-9000", standard, "2027-03-09"),
            ]
            self.assertEqual(self._loaners(orders, pool=1), ["CO-9002"])

        with self.subTest(rule="earlier promised date"):
            orders = [
                order_row("CO-1002", platinum, "2027-03-20"),
                order_row("CO-1001", platinum, "2027-03-12"),
            ]
            self.assertEqual(self._loaners(orders, pool=1), ["CO-1001"])

        with self.subTest(rule="lower customer order id"):
            orders = [
                order_row("CO-2002", platinum, "2027-03-15"),
                order_row("CO-2001", platinum, "2027-03-15"),
            ]
            self.assertEqual(self._loaners(orders, pool=1), ["CO-2001"])

    def test_standard_tier_gets_no_loaner(self) -> None:
        standard = customer_of(self.graph, "Standard")
        orders = [
            order_row("CO-S1", standard, "2027-03-10"),
            order_row("CO-S2", standard, "2027-03-11"),
        ]
        pools = LoanerPools(self.graph)
        pools.left["D27"] = 4
        result = plan_dealer_customer(self.graph, pools, orders, "Standard customers are delayed.")
        assigns = [call for call in result.calls if call.tool == "crm.assign_loaner"]
        notices = [call for call in result.calls if call.tool == "dealer.notify"]
        self.assertEqual(assigns, [])
        self.assertEqual(len(notices), 1)
        self.assertEqual(set(notices[0].args["customer_order_ids"]), {"CO-S1", "CO-S2"})

    def test_duplicate_customer_order_is_notified_once(self) -> None:
        platinum = customer_of(self.graph, "Platinum")
        row = order_row("CO-DUP", platinum, "2027-03-12")
        pools = LoanerPools(self.graph)
        pools.left["D27"] = 3
        result = plan_dealer_customer(self.graph, pools, [row, dict(row)], "Duplicate row.")
        notices = [call for call in result.calls if call.tool == "dealer.notify"]
        assigns = [call for call in result.calls if call.tool == "crm.assign_loaner"]
        self.assertEqual(len(notices), 1)
        self.assertEqual(notices[0].args["customer_order_ids"].count("CO-DUP"), 1)
        self.assertEqual([call.args["customer_order_id"] for call in assigns], ["CO-DUP"])

    def test_loaner_assignments_never_exceed_the_pool(self) -> None:
        platinum = customer_of(self.graph, "Platinum")
        orders = [
            order_row("CO-3001", platinum, "2027-03-15"),
            order_row("CO-3002", platinum, "2027-03-12"),
            order_row("CO-3003", platinum, "2027-03-10"),
            order_row("CO-3004", platinum, "2027-03-11"),
        ]
        self.assertEqual(self._loaners(orders, pool=2), ["CO-3003", "CO-3004"])
        pools = LoanerPools(self.graph)
        pools.left["D27"] = 2
        result = plan_dealer_customer(self.graph, pools, orders, "More buyers than loaners.")
        self.assertLessEqual(
            sum(call.tool == "crm.assign_loaner" for call in result.calls),
            2,
        )

    def _loaners(self, orders: list[dict], pool: int) -> list[str]:
        pools = LoanerPools(self.graph)
        pools.left["D27"] = pool
        result = plan_dealer_customer(self.graph, pools, orders, "Loaner priority.")
        return [
            call.args["customer_order_id"]
            for call in result.calls
            if call.tool == "crm.assign_loaner"
        ]


class CoordinatorTests(TowerTest):
    def test_compound_message_handles_both_incidents_on_one_schedule(self) -> None:
        text = (
            "(1) The Texas plant reports an outage from 2027-03-09 through 2027-03-10. "
            "Production is stopped. "
            "(2) The Kentucky plant reports an outage from 2027-03-11 through 2027-03-12. "
            "Production is stopped."
        )
        incidents = understand(self.graph, text)
        self.assertEqual(len(incidents), 2)
        self.assertEqual(
            [(item.kind, item.plant_id, item.outage_start, item.outage_end) for item in incidents],
            [
                ("plant_outage", "P_TX", "2027-03-09", "2027-03-10"),
                ("plant_outage", "P_KY", "2027-03-11", "2027-03-12"),
            ],
        )

        box, trace = self.handle("adv-coord-compound", text)
        self.assertEqual(len(trace.incidents), 2)
        supply = [result for result in trace.results if result.agent == "supply_chain"]
        self.assertEqual(len(supply), 1)

        expected: dict[str, str] = {}
        for plant_id, start, end in (
            ("P_TX", "2027-03-09", "2027-03-10"),
            ("P_KY", "2027-03-11", "2027-03-12"),
        ):
            restart = next_working_day(date.fromisoformat(end)).isoformat()
            for order in future_orders(self.graph, plant_id, start, end, inclusive=True):
                expected[order["production_order_id"]] = restart
        self.assertTrue(any(plant == "P_TX" for plant in (self.graph.orders[i]["plant_id"] for i in expected)))
        self.assertTrue(any(self.graph.orders[i]["plant_id"] == "P_KY" for i in expected))

        moved = self.moved_by(trace.calls)
        self.assertEqual(set(moved), set(expected))
        for order_id, (plant_id, new_date) in moved.items():
            self.assertGreaterEqual(new_date, expected[order_id], order_id)
            home = self.graph.orders[order_id]["plant_id"]
            if plant_id == home:
                self.assertGreaterEqual(new_date, expected[order_id])
            else:
                self.assertIn(self.graph.orders[order_id]["model"], self.graph.models_by_plant[plant_id])
        self.assert_only_these_orders_moved(box, "adv-coord-compound", moved)
        self._assert_capacity(box, "adv-coord-compound")
        self._assert_dealer_and_loaners(trace, expected)

    def test_noise_executes_zero_calls(self) -> None:
        _box, trace = self.handle("adv-coord-noise", "Thanks, the brochure looks great.")
        self.assertTrue(all(item.kind == "noise" for item in trace.incidents))
        self.assertEqual(trace.calls, [])

    def test_toolerror_is_recorded_and_does_not_escape(self) -> None:
        affected = future_orders(self.graph, "P_TX", "2027-03-09", "2027-03-09", inclusive=True)
        self.assertGreaterEqual(len(affected), 2)
        poison = sorted(order["production_order_id"] for order in affected)[0]
        original = (self.graph.orders[poison]["plant_id"], self.graph.orders[poison]["idx"])

        probe = _BadIdEnterprise(self.graph.data_dir, poison)
        with self.assertRaises(ToolError):
            probe.call(
                "adv-coord-probe",
                "mes.reschedule",
                {"production_order_id": poison, "new_date": "2027-03-15"},
            )

        box = _BadIdEnterprise(self.graph.data_dir, poison)
        text = (
            "The Texas plant reports an outage on 2027-03-09 through 2027-03-09. "
            "Production is stopped."
        )
        try:
            trace = handle_event(self.graph, box, event("adv-coord-toolerror", text))
        except Exception as exc:
            self.fail(f"handle_event raised {type(exc).__name__}: {exc}")

        self.assertIn("fail", trace.summary.lower())
        moved = {}
        for call in supply_calls(trace.calls):
            order_id = call.args["production_order_id"]
            if order_id == poison:
                continue
            if call.tool == "mes.reschedule":
                plant_id = self.graph.orders[order_id]["plant_id"]
            else:
                plant_id = call.args["to_plant_id"]
            moved[order_id] = (plant_id, call.args["new_date"])
        self.assertTrue(moved)
        self.assert_only_these_orders_moved(box, "adv-coord-toolerror", moved)
        state = box.state("adv-coord-toolerror")
        self.assertEqual(state["loc"][poison], original)

    def _assert_capacity(self, box: Enterprise, event_id: str) -> None:
        state = box.state(event_id)
        for (plant_id, _idx), occupants in state["slots"].items():
            self.assertLessEqual(len(occupants), box.plants[plant_id]["slots"], plant_id)

    def _assert_dealer_and_loaners(self, trace, affected: dict[str, str]) -> None:
        by_dealer: dict[str, set[str]] = {}
        for order in self.graph.customer_orders.values():
            if order["production_order_id"] not in affected:
                continue
            by_dealer.setdefault(order["dealer_id"], set()).add(order["customer_order_id"])
        notices = [call for call in trace.calls if call.tool == "dealer.notify"]
        self.assertEqual({call.args["dealer_id"] for call in notices}, set(by_dealer))
        seen = []
        for call in notices:
            seen.append(call.args["dealer_id"])
            ids = call.args["customer_order_ids"]
            self.assertEqual(len(ids), len(set(ids)))
            self.assertEqual(set(ids), by_dealer[call.args["dealer_id"]])
        self.assertEqual(len(seen), len(set(seen)))

        counts: dict[str, int] = {}
        for call in trace.calls:
            if call.tool != "crm.assign_loaner":
                continue
            order = self.graph.customer_orders[call.args["customer_order_id"]]
            tier = self.graph.customers[order["customer_id"]]["tier"]
            self.assertIn(tier, ("Platinum", "Gold"))
            counts[order["dealer_id"]] = counts.get(order["dealer_id"], 0) + 1
        for dealer_id, count in counts.items():
            self.assertLessEqual(count, self.graph.loaners.get(dealer_id, 0), dealer_id)


class _BadIdEnterprise(Enterprise):
    """Force one real order id to a bad id so Enterprise.call raises ToolError."""

    def __init__(self, data_dir: str, poison_id: str):
        super().__init__(data_dir)
        self.poison_id = poison_id

    def call(self, event_id, tool, args):
        if tool in SUPPLY_TOOLS and args.get("production_order_id") == self.poison_id:
            forged = dict(args)
            forged["production_order_id"] = "PO-NOPE"
            return super().call(event_id, tool, forged)
        return super().call(event_id, tool, args)


if __name__ == "__main__":
    unittest.main()
