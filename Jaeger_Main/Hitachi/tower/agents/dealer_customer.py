"""Dealer notices and loaner assignments for affected customer orders.

The coordinator decides which orders are affected. This agent only tells each
dealer once and spends that dealer's loaner pool. Platinum comes before Gold,
then the earlier promised date, then the lower customer order id.
"""

from __future__ import annotations

from collections import defaultdict

from tower.contracts import SpecialistResult, ToolCall
from tower.graph import WorldGraph
from tower.schedule import LoanerPools

# Name recorded in the trace, and the tiers rule 5 allows a loaner (Standard never gets one).
_AGENT = "dealer_customer"
_LOANER_TIERS = frozenset({"Platinum", "Gold"})


def plan_dealer_customer(
    graph: WorldGraph,
    pools: LoanerPools,
    customer_orders: list[dict],
    reason: str,
) -> SpecialistResult:
    """Plan one dealer.notify per dealer, then loaners until each pool is empty.

    pools is shared with every other incident in the same event, so a compound message can
    never hand out the same loaner twice. reason is the incident summary; it becomes the
    dealer message text.
    """
    if not customer_orders:
        return SpecialistResult(
            agent=_AGENT,
            affected_ids=[],
            graph_paths=[],
            calls=[],
            notes=["No affected customer orders. No dealer notices or loaners."],
        )

    # De-duplicate (a compound event can reach the same order twice), then group by dealer.
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

    # Rule 4: one notice per dealer listing exactly that dealer's affected orders.
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

        # Rule 5: loaners for Platinum and Gold only, in priority order, until the dealer's pool
        # is empty.
        eligible = [
            order
            for order in dealer_orders
            if _tier(graph, order["customer_id"]) in _LOANER_TIERS
        ]
        eligible.sort(key=lambda order: _loaner_key(graph, order))
        for index, order in enumerate(eligible):
            # Pool empty: everyone left in the priority list goes without. Count them for the note.
            if not pools.take(dealer_id):
                skipped += len(eligible) - index
                break
            tier = _tier(graph, order["customer_id"])
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

    return SpecialistResult(
        agent=_AGENT,
        affected_ids=[order["customer_order_id"] for order in orders],
        graph_paths=[_path(graph, order) for order in orders],
        calls=calls,
        notes=[_summary(len(by_dealer), loaners, skipped)],
    )


def _tier(graph: WorldGraph, customer_id: str) -> str:
    """Customer tier, or "Unknown" for a missing record (never loaner-eligible)."""
    customer = graph.customers.get(customer_id) or {}
    return str(customer.get("tier") or "Unknown")


# Sort key: Platinum (0) before Gold (1), then earlier promised date, then lower order id.
def _loaner_key(graph: WorldGraph, order: dict) -> tuple[int, str, str]:
    platinum_first = 0 if _tier(graph, order["customer_id"]) == "Platinum" else 1
    return (platinum_first, order["promised_date"], order["customer_order_id"])


def _path(graph: WorldGraph, order: dict) -> list[str]:
    """The tail of the graph path (CustomerOrder → Dealer → Customer), with the tier that
    decided the loaner."""
    tier = _tier(graph, order["customer_id"])
    return [
        f"CustomerOrder {order['customer_order_id']}",
        f"Dealer {order['dealer_id']}",
        f"Customer {order['customer_id']} ({tier})",
    ]


def _dealer_message(reason: str) -> str:
    """Dealer notice text: the incident summary, cleaned up, plus the loaner policy line."""
    # Collapse whitespace and newlines from the original message into one sentence.
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
    """"1 loaner" / "3 loaners"."""
    return f"{n} {one if n == 1 else many}"


def _summary(notices: int, loaners: int, skipped: int) -> str:
    """Plain-English note for the trace."""
    return (
        f"Sent {_counted(notices, 'dealer notice', 'dealer notices')} and assigned "
        f"{_counted(loaners, 'loaner', 'loaners')}. "
        f"{_counted(skipped, 'eligible customer was', 'eligible customers were')} "
        "skipped because the pool was empty."
    )
