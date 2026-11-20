"""Customer promise impact for the Overview: did the customers behind each moved build still get
their car on time?

Every customer order has a promised delivery date, set 2 to 5 days after its production order's
original build date (customer_orders.csv, production_orders.csv). When the tower reschedules or
transfers a build, this compares the new build date with each order's promise:

    on track   still built at least 2 days before the promise (the shortest lead the company plans)
    tight      built 0 or 1 day before the promise
    late       built after the promised date (by how many days)

Platinum and Gold customers are counted on their own, with whether the tower gave them a loaner.
Built from the action log on request; the company tables are read once.
"""

from __future__ import annotations

import csv
import os
from datetime import date

HERE = os.path.dirname(os.path.abspath(__file__))
HITACHI = os.path.abspath(os.path.join(HERE, "..", ".."))
DATA = os.path.join(HITACHI, "Data", "hack_the_highway_package", "data")
MIN_LEAD = 2          # days: the shortest gap between build and promise in the company's own plans
PRIORITY = {"Platinum", "Gold"}

_tables: dict | None = None


def _read(name: str) -> list[dict]:
    with open(os.path.join(DATA, name), newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _load() -> dict:
    global _tables
    if _tables is None:
        orders: dict[str, list[dict]] = {}
        for row in _read("customer_orders.csv"):
            orders.setdefault(row["production_order_id"], []).append(row)
        _tables = {
            "orders_by_po": orders,
            "build": {r["production_order_id"]: r["build_date"] for r in _read("production_orders.csv")},
            "tier": {r["customer_id"]: r["tier"] for r in _read("customers.csv")},
        }
    return _tables


def _day(text: str) -> date | None:
    try:
        return date.fromisoformat(str(text)[:10])
    except ValueError:
        return None


def payload(rows: list[dict]) -> dict:
    """rows: the feed's action log (every tool call, in order). Returns the Overview card's numbers."""
    t = _load()
    moved: dict[str, dict] = {}        # production order -> its latest move
    loaners: set[str] = set()
    for row in rows:
        if not row.get("ok"):
            continue
        tool, args = row.get("tool"), row.get("args") or {}
        if tool in ("mes.reschedule", "mes.transfer") and args.get("production_order_id") and args.get("new_date"):
            moved[args["production_order_id"]] = {"new": args["new_date"], "transfer": tool == "mes.transfer",
                                                 "event_id": row.get("event_id")}
        elif tool == "crm.assign_loaner" and args.get("customer_order_id"):
            loaners.add(args["customer_order_id"])

    counts = {"on_track": 0, "tight": 0, "late": 0}
    priority = {"on_track": 0, "tight": 0, "late": 0}
    late_orders, delays = [], []
    for po, move in moved.items():
        new, old = _day(move["new"]), _day(t["build"].get(po, ""))
        if new is None:
            continue
        if old is not None:
            delays.append((new - old).days)
        for order in t["orders_by_po"].get(po, []):
            promised = _day(order["promised_date"])
            if promised is None:
                continue
            slack = (promised - new).days
            band = "on_track" if slack >= MIN_LEAD else "tight" if slack >= 0 else "late"
            tier = t["tier"].get(order["customer_id"], "Standard")
            counts[band] += 1
            if tier in PRIORITY:
                priority[band] += 1
            if band == "late":
                late_orders.append({
                    "customer_order_id": order["customer_order_id"], "tier": tier, "dealer_id": order["dealer_id"],
                    "model": order["model"].title(), "days_late": -slack, "promised": order["promised_date"],
                    "new_build": move["new"], "loaner": order["customer_order_id"] in loaners,
                    "event_id": move["event_id"],
                })
    tier_rank = {"Platinum": 0, "Gold": 1}
    late_orders.sort(key=lambda o: (tier_rank.get(o["tier"], 2), -o["days_late"], o["customer_order_id"]))
    late_priority = [o for o in late_orders if o["tier"] in PRIORITY]
    total = sum(counts.values())
    return {
        "orders": total,
        "builds_moved": len(moved),
        "transfers": sum(m["transfer"] for m in moved.values()),
        "bands": counts,
        "priority": priority,
        "avg_delay_days": round(sum(delays) / len(delays), 1) if delays else 0,
        "max_days_late": max((o["days_late"] for o in late_orders), default=0),
        "late_priority_with_loaner": sum(o["loaner"] for o in late_priority),
        "late_priority": len(late_priority),
        "most_at_risk": late_orders[:4],
    }
