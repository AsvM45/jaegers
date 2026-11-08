"""Dealer notices and loaner assignments for affected customer orders.

The coordinator decides which orders are affected. This agent only tells each
dealer once and spends that dealer's loaner pool. Platinum comes before Gold,
then the earlier promised date, then the lower customer order id.
"""

from __future__ import annotations

from collections import defaultdict

from tower.contracts import SpecialistResult, ToolCall
from tower.graph import PATH_KEEP, WorldGraph
from tower.schedule import LoanerPools

_AGENT = "dealer_customer"
_LOANER_TIERS = frozenset({"Platinum", "Gold"})


def plan_dealer_customer(
    graph: WorldGraph,
    pools: LoanerPools,
    customer_orders: list[dict],
    reason: str,
) -> SpecialistResult:
    """Plan one dealer.notify per dealer, then loaners until each pool is empty."""
    if not customer_orders:
        return SpecialistResult(
            agent=_AGENT,
            affected_ids=[],
            graph_paths=[],
            calls=[],
            notes=["No affected customer orders. No dealer notices or loaners."],
        )

    unique: dict[str, dict] = {}
    for order in customer_orders:
        unique.setdefault(order["customer_order_id"], order)
    orders = [unique[order_id] for order_id in sorted(unique)]

    by_dealer: dict[str, list[dict]] = defaultdict(list)
    for order in orders:
        by_dealer[order["dealer_id"]].append(order)

    calls: list[ToolCall] = []
    loaners = 0
    skipped = 0
    message = _dealer_message(reason)
    known_tiers: dict[str, str] = {}

    for dealer_id in sorted(by_dealer):
        dealer_orders = by_dealer[dealer_id]
        order_ids = [order["customer_order_id"] for order in dealer_orders]
        calls.append(
            ToolCall(
                tool="dealer.notify",
                args={
                    "dealer_id": dealer_id,
                    "customer_order_ids": order_ids,
                    "message": message,
                },
                reason=(
                    f"One notice to {dealer_id} for "
                    f"{_counted(len(order_ids), 'affected customer order', 'affected customer orders')}."
                ),
            )
        )

        eligible = []
        for order in dealer_orders:
            tier = _remembered_tier(graph, known_tiers, order["customer_id"])
            if tier in _LOANER_TIERS:
                eligible.append(order)
        eligible.sort(key=lambda order: _loaner_key(graph, order, known_tiers[order["customer_id"]]))
        left = pools.available(dealer_id)
        for index, order in enumerate(eligible):
            if left <= 0 or not pools.take(dealer_id):
                skipped += len(eligible) - index
                break
            left -= 1
            tier = known_tiers[order["customer_id"]]
            calls.append(
                ToolCall(
                    tool="crm.assign_loaner",
                    args={"customer_order_id": order["customer_order_id"]},
                    reason=(
                        f"{tier} customer {order['customer_id']} takes the next "
                        f"loaner at {dealer_id}."
                    ),
                )
            )
            loaners += 1

    notes = [_summary(len(by_dealer), loaners, skipped)]
    paths = [
        _path(graph, order, _remembered_tier(graph, known_tiers, order["customer_id"]))
        for order in orders[:PATH_KEEP]
    ]
    if len(orders) > PATH_KEEP:
        notes.append(
            f"Stored {PATH_KEEP} graph paths. "
            f"{len(orders) - PATH_KEEP} further customer orders follow the same dealer link and were not stored."
        )
    return SpecialistResult(
        agent=_AGENT,
        affected_ids=[order["customer_order_id"] for order in orders],
        graph_paths=paths,
        calls=calls,
        notes=notes,
    )


def _tier(graph: WorldGraph, customer_id: str) -> str:
    customer = graph.customers.get(customer_id) or {}
    return str(customer.get("tier") or "Unknown")


def _remembered_tier(graph: WorldGraph, known: dict[str, str], customer_id: str) -> str:
    tier = known.get(customer_id)
    if tier is None:
        tier = _tier(graph, customer_id)
        known[customer_id] = tier
    return tier


def _loaner_key(graph: WorldGraph, order: dict, tier: str | None = None) -> tuple[int, str, str]:
    """Platinum before Gold, then the earlier promised date, then the lower customer order id."""
    if tier is None:
        tier = _tier(graph, order["customer_id"])
    platinum_first = 0 if tier == "Platinum" else 1
    return (platinum_first, order["promised_date"], order["customer_order_id"])


def _path(graph: WorldGraph, order: dict, tier: str | None = None) -> list[str]:
    if tier is None:
        tier = _tier(graph, order["customer_id"])
    return [
        f"CustomerOrder {order['customer_order_id']}",
        f"Dealer {order['dealer_id']}",
        f"Customer {order['customer_id']} ({tier})",
    ]


def _dealer_message(reason: str) -> str:
    text = " ".join(reason.split())
    if text and text[-1] not in ".!?":
        text += "."
    if not text:
        text = "Customer orders at your store are delayed."
    return (
        f"{text} Platinum and Gold customers receive a loaner while this "
        "dealer's pool has cars left."
    )


def _counted(n: int, one: str, many: str) -> str:
    return f"{n} {one if n == 1 else many}"


def _summary(notices: int, loaners: int, skipped: int) -> str:
    return (
        f"Sent {_counted(notices, 'dealer notice', 'dealer notices')} and assigned "
        f"{_counted(loaners, 'loaner', 'loaners')}. "
        f"{_counted(skipped, 'eligible customer was', 'eligible customers were')} "
        "skipped because the pool was empty."
    )
