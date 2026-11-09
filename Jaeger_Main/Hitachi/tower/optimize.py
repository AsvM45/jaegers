"""Publish the slot the supply-chain planner already chose.

The planner still picks the day and the plant. This module only states that
choice as one sentence. It does not call a tool or change arguments.
"""

from __future__ import annotations


def recommend(order_id: str, home_plant: str, dest_plant: str, new_date: str, kind: str) -> str:
    """One sentence for a chosen slot.

    kind is the binding constraint ("delay" or "outage"). The sentence names
    the order, the plants, and the day.
    """
    if dest_plant == home_plant:
        return f"Recommendation: keep {order_id} at {home_plant} on {new_date}."
    return f"Recommendation: move {order_id} from {home_plant} to {dest_plant} on {new_date}."
