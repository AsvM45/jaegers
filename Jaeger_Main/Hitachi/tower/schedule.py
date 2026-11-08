"""Per-event slot board and loaner pools.

Each event starts from the tables. Moving an order here is how the supply
planner sees capacity. The coordinator then replays the same moves through
enterprise.Enterprise so the action log is what the tools actually accepted.
"""

from __future__ import annotations

from collections import defaultdict

from tower.calendar_util import date_to_idx, idx_to_date, next_working_day
from tower.graph import WorldGraph


# A scratch copy of the production calendar for one event: which orders sit in which (plant, day)
# slot. The supply planner books moves here first, so two incidents in one message cannot take the
# same slot.
class PlantSchedule:
    """Mutable (plant, day) slot board for one event. Mirrors the bookkeeping in enterprise.py."""

    def __init__(self, graph: WorldGraph):
        self.graph = graph
        self.capacity = {plant_id: plant["slots_per_day"] for plant_id, plant in graph.plants.items()}
        # loc: order -> (plant, day index). slots: (plant, day index) -> orders that day. Past
        # orders (idx < 0) are left out because they cannot move.
        self.loc: dict[str, tuple[str, int]] = {}
        self.slots: dict[tuple[str, int], set[str]] = defaultdict(set)
        for po_id, po in graph.orders.items():
            if po["idx"] < 0:
                continue
            self.loc[po_id] = (po["plant_id"], po["idx"])
            self.slots[(po["plant_id"], po["idx"])].add(po_id)

    def free_count(self, plant_id: str, idx: int) -> int:
        # A probe must not create an empty set for a day nobody has taken.
        occupied = self.slots.get((plant_id, idx))
        used = len(occupied) if occupied is not None else 0
        return self.capacity[plant_id] - used

    def release(self, po_id: str) -> None:
        """Take an affected order off its current day so the slot can be reused."""
        if po_id not in self.loc:
            return
        plant_id, idx = self.loc.pop(po_id)
        self.slots[(plant_id, idx)].discard(po_id)

    def commit(self, po_id: str, plant_id: str, idx: int) -> None:
        """Book an order into a slot. Call release() first; a full day raises instead of overbooking.

        The RuntimeError is a planner bug, not a business condition: the planner checks
        free_count before committing, so this guard should never fire in a run.
        """
        if self.free_count(plant_id, idx) <= 0:
            raise RuntimeError(f"no free slot at {plant_id} on {idx_to_date(idx).isoformat()}")
        self.slots[(plant_id, idx)].add(po_id)
        self.loc[po_id] = (plant_id, idx)


# Loaners left at each dealer for this event. take() spends one and returns False once the pool is
# empty.
class LoanerPools:
    """Per-event loaner counts, copied from loaners.csv, shared by every incident in the event."""

    def __init__(self, graph: WorldGraph):
        self.left = dict(graph.loaners)

    def available(self, dealer_id: str) -> int:
        """Loaners still free at a dealer. A dealer missing from loaners.csv has none."""
        return self.left.get(dealer_id, 0)

    def take(self, dealer_id: str) -> bool:
        """Spend one loaner. Returns False, and changes nothing, when the pool is empty."""
        if self.left.get(dealer_id, 0) <= 0:
            return False
        self.left[dealer_id] -= 1
        return True


def restart_index(outage_end_iso: str) -> int:
    """First working day after an inclusive outage end. May fall past the window."""
    from datetime import date

    return date_to_idx(next_working_day(date.fromisoformat(outage_end_iso)))
