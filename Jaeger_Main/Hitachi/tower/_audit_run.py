"""Check runs/run1 against the handbook, using the incidents the reader produced."""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

from tower.calendar_util import date_to_idx, next_working_day
from tower.graph import WorldGraph

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    """Replay runs/run1 against handbook rules 1-6 and print every mismatch.

    This checks the actions given the reader's incidents. It cannot catch a misread message;
    tests/run_cases.py checks that against hand-written ground truth.
    """
    graph = WorldGraph()
    traces = json.loads((ROOT / "runs" / "run1" / "traces.json").read_text(encoding="utf-8"))
    rows_by_event = defaultdict(list)
    for line in (ROOT / "runs" / "run1" / "action_log.jsonl").read_text(encoding="utf-8").splitlines():
        if line.strip():
            row = json.loads(line)
            rows_by_event[row["event_id"]].append(row)

    problems = []

    # Collect every problem instead of stopping at the first, so one run shows them all.
    def add(event_id: str, message: str) -> None:
        problems.append(f"{event_id}: {message}")

    # For each event, recompute the handbook answer from its incidents and compare it with the
    # logged calls.
    for trace in traces:
        event_id = trace["event_id"]
        rows = rows_by_event[event_id]
        kinds = [incident["kind"] for incident in trace["incidents"]]
        # Rules 7-8: noise writes nothing; unconfirmed is a single escalate and nothing else.
        if kinds and all(kind == "noise" for kind in kinds):
            if rows:
                add(event_id, "noise has calls")
            continue
        if all(kind in ("noise", "unconfirmed") for kind in kinds):
            tools = [row["tool"] for row in rows]
            if tools != ["escalate"]:
                add(event_id, f"unconfirmed tools {tools}")
            continue

        # Rules 1-3: which production orders must move, and the earliest day each may move to.
        expected: dict[str, int] = {}
        for incident in trace["incidents"]:
            if incident["kind"] == "supplier_delay":
                earliest = date_to_idx(date.fromisoformat(incident["blocked_until"]))
                orders = graph.affected_orders_delay(
                    incident["plant_id"], incident["part_id"], incident["blocked_from"], incident["blocked_until"]
                )
            elif incident["kind"] == "plant_outage":
                earliest = date_to_idx(next_working_day(date.fromisoformat(incident["outage_end"])))
                orders = graph.affected_orders_outage(
                    incident["plant_id"], incident["outage_start"], incident["outage_end"]
                )
            else:
                continue
            # An order hit by two incidents in one message must clear the later constraint.
            for order in orders:
                order_id = order["production_order_id"]
                expected[order_id] = max(expected.get(order_id, 0), earliest)

        # What the log actually did with each order: (kind, new date, target plant or None).
        moved = {}
        for row in rows:
            if row["tool"] == "mes.reschedule":
                moved[row["args"]["production_order_id"]] = ("reschedule", row["args"]["new_date"], None)
            elif row["tool"] == "mes.transfer":
                moved[row["args"]["production_order_id"]] = (
                    "transfer",
                    row["args"]["new_date"],
                    row["args"]["to_plant_id"],
                )
        if set(moved) != set(expected):
            extra = sorted(set(moved) - set(expected))[:5]
            missing = sorted(set(expected) - set(moved))[:5]
            add(event_id, f"orders extra {extra} missing {missing} expected {len(expected)} got {len(moved)}")
        for order_id, info in moved.items():
            if order_id not in expected:
                continue
            new_idx = date_to_idx(date.fromisoformat(info[1]))
            if info[0] == "reschedule" and new_idx < expected[order_id]:
                add(event_id, f"{order_id} rescheduled to {info[1]} before the constraint")
            if info[0] == "transfer":
                dest = info[2]
                model = graph.orders[order_id]["model"]
                if dest not in graph.plants_by_model.get(model, []):
                    add(event_id, f"{order_id} transferred to {dest} which does not build {model}")
                if dest == graph.orders[order_id]["plant_id"]:
                    add(event_id, f"{order_id} transfer stayed at {dest}")

        # Rules 4-5: dealer notices and loaners.
        customer_orders = graph.customer_orders_for(expected)
        by_dealer = defaultdict(set)
        for order in customer_orders:
            by_dealer[order["dealer_id"]].add(order["customer_order_id"])
        notices = [row for row in rows if row["tool"] == "dealer.notify"]
        seen = []
        for notice in notices:
            dealer_id = notice["args"]["dealer_id"]
            seen.append(dealer_id)
            got = set(notice["args"]["customer_order_ids"])
            wanted = by_dealer.get(dealer_id, set())
            if got != wanted:
                add(event_id, f"notify {dealer_id} got {len(got)} expected {len(wanted)}")
        if sorted(seen) != sorted(by_dealer):
            add(event_id, f"dealer set extra {set(seen) - set(by_dealer)} missing {set(by_dealer) - set(seen)}")
        if len(seen) != len(set(seen)):
            add(event_id, "duplicate dealer notify")

        # Loaners: one per order at most, only Platinum/Gold, never more than the dealer's pool.
        # Priority order inside the pool is checked in tests/run_cases.py, not here.
        loaners = [row["args"]["customer_order_id"] for row in rows if row["tool"] == "crm.assign_loaner"]
        if len(loaners) != len(set(loaners)):
            add(event_id, "duplicate loaner")
        orders_by_id = {order["customer_order_id"]: order for order in customer_orders}
        per_dealer = Counter()
        for order_id in loaners:
            order = orders_by_id.get(order_id)
            if order is None:
                add(event_id, f"loaner for non-affected {order_id}")
                continue
            tier = graph.customers[order["customer_id"]]["tier"]
            if tier not in ("Platinum", "Gold"):
                add(event_id, f"loaner for {tier} {order_id}")
            per_dealer[order["dealer_id"]] += 1
        for dealer_id, count in per_dealer.items():
            if count > graph.loaners[dealer_id]:
                add(event_id, f"loaners {count} exceed pool {graph.loaners[dealer_id]} at {dealer_id}")

        # Rule 6: exactly one hold, stop-sale for every in-stock affected vehicle at its dealer,
        # and a notice to every owner of a sold one.
        for incident in trace["incidents"]:
            if incident["kind"] != "quality_hold":
                continue
            holds = [row for row in rows if row["tool"] == "quality.hold_lot"]
            if len(holds) != 1:
                add(event_id, f"holds {len(holds)}")
                continue
            lot = graph.lots[holds[0]["args"]["lot_id"]]
            print(
                event_id,
                "lot",
                lot["lot_id"],
                lot["part_id"],
                lot["plant_id"],
                lot["first_build_date"],
                lot["last_build_date"],
                "text",
                incident["build_start"],
                incident["build_end"],
            )
            vehicles = graph.affected_vehicles(
                lot["plant_id"], lot["part_id"], lot["first_build_date"], lot["last_build_date"]
            )
            stock = defaultdict(set)
            owners = set()
            for vehicle in vehicles:
                if vehicle["status"] == "in_stock":
                    stock[vehicle["dealer_id"]].add(vehicle["vin"])
                elif vehicle["status"] == "sold" and vehicle.get("customer_id"):
                    owners.add(vehicle["customer_id"])
            stops = [row for row in rows if row["tool"] == "dealer.stop_sale"]
            if {row["args"]["dealer_id"] for row in stops} != set(stock):
                add(event_id, "stop-sale dealer mismatch")
            for stop in stops:
                if set(stop["args"]["vins"]) != stock[stop["args"]["dealer_id"]]:
                    add(event_id, f"vins mismatch at {stop['args']['dealer_id']}")
            notified = {row["args"]["customer_id"] for row in rows if row["tool"] == "crm.notify_customer"}
            if notified != owners:
                add(event_id, f"owners got {len(notified)} expected {len(owners)}")

        # A quality hold has no reschedules, dealer notices or loaners (rule 6 does not call for them).
        supply = any(kind in ("supplier_delay", "plant_outage") for kind in kinds)
        if not supply and any(row["tool"] in ("dealer.notify", "crm.assign_loaner", "mes.reschedule", "mes.transfer") for row in rows):
            add(event_id, "quality-only event has a supply action")

    print(f"PROBLEMS {len(problems)}")
    for problem in problems:
        print(problem)


if __name__ == "__main__":
    main()
