"""Per-event slot board and loaner pools.

Each event starts from the tables. Moving an order here is how the supply
planner sees capacity. The coordinator then replays the same moves through
enterprise.Enterprise so the action log is what the tools actually accepted.
"""

from __future__ import annotations

from collections import defaultdict

from tower.calendar_util import LAST_IDX, date_to_idx, idx_to_date, next_working_day
from tower.graph import WorldGraph


class PlantSchedule:
    def __init__(self, graph: WorldGraph):
        self.graph = graph
        self.capacity = {plant_id: plant["slots_per_day"] for plant_id, plant in graph.plants.items()}
        self.loc: dict[str, tuple[str, int]] = {}
        self.slots: dict[tuple[str, int], set[str]] = defaultdict(set)
        for po_id, po in graph.orders.items():
            if po["idx"] < 0:
                continue
            self.loc[po_id] = (po["plant_id"], po["idx"])
            self.slots[(po["plant_id"], po["idx"])].add(po_id)

    def free_count(self, plant_id: str, idx: int) -> int:
        return self.capacity[plant_id] - len(self.slots[(plant_id, idx)])

    def release(self, po_id: str) -> None:
        """Take an affected order off its current day so the slot can be reused."""
        if po_id not in self.loc:
            return
        plant_id, idx = self.loc.pop(po_id)
        self.slots[(plant_id, idx)].discard(po_id)

    def commit(self, po_id: str, plant_id: str, idx: int) -> None:
        if self.free_count(plant_id, idx) <= 0:
            raise RuntimeError(f"no free slot at {plant_id} on {idx_to_date(idx).isoformat()}")
        self.slots[(plant_id, idx)].add(po_id)
        self.loc[po_id] = (plant_id, idx)


class LoanerPools:
    def __init__(self, graph: WorldGraph):
        self.left = dict(graph.loaners)

    def available(self, dealer_id: str) -> int:
        return self.left.get(dealer_id, 0)

    def take(self, dealer_id: str) -> bool:
        if self.left.get(dealer_id, 0) <= 0:
            return False
        self.left[dealer_id] -= 1
        return True


def restart_index(outage_end_iso: str) -> int:
    """First working day after an inclusive outage end. May fall past the window."""
    from datetime import date

    return date_to_idx(next_working_day(date.fromisoformat(outage_end_iso)))


def window_indexes() -> range:
    return range(0, LAST_IDX + 1)
