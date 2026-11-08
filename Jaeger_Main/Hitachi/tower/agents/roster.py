"""The control tower's agents: one coordinator and three specialists (docx, "Multi-agent orchestration").

Each agent has a card: a name, its responsibility, which incidents it takes, and the only
enterprise tools it may plan. The coordinator hands each specialist its incidents, checks every
planned call against that agent's tools before executing anything, and records each handoff in
the event trace so the UI can show who did what.

The understanding step (understand.py + llm_reader.py, Qwen2.5 0.5B with a rule check) is the
coordinator's own first step, not a specialist: the docx asks the system to "use an LLM to
understand each event", and the coordinator owns that decision.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass

from tower.agents.dealer_customer import plan_dealer_customer
from tower.agents.quality import plan_quality
from tower.agents.supply_chain import plan_supply
from tower.contracts import SpecialistResult


@dataclass(frozen=True)
class AgentCard:
    """Who an agent is and what it may do. tools is an allowlist the coordinator enforces."""

    id: str
    title: str
    responsibility: str
    takes: str
    tools: frozenset[str]
    handbook_rules: str

    def to_dict(self) -> dict:
        out = asdict(self)
        out["tools"] = sorted(self.tools)
        return out


class Agent:
    """Base class. Specialists plan; only the coordinator calls tools."""

    card: AgentCard

    @property
    def id(self) -> str:
        return self.card.id

    def allows(self, tool: str) -> bool:
        return tool in self.card.tools


class SupplyChainPlanner(Agent):
    card = AgentCard(
        id="supply_chain",
        title="Supply Chain Planner",
        responsibility="Moves every production order a supplier delay or plant outage blocks to the "
                       "earliest feasible slot, at the same plant first, transferring only when it must.",
        takes="supplier_delay and plant_outage incidents",
        tools=frozenset({"mes.reschedule", "mes.transfer"}),
        handbook_rules="1, 2, 3",
    )

    def plan(self, graph, schedule, incidents) -> SpecialistResult:
        return plan_supply(graph, schedule, incidents)


class QualityAgent(Agent):
    card = AgentCard(
        id="quality",
        title="Quality",
        responsibility="Holds the defective lot, stops sale of unsold vehicles built with it, and "
                       "contacts the owners of sold ones.",
        takes="quality_hold incidents",
        tools=frozenset({"quality.hold_lot", "dealer.stop_sale", "crm.notify_customer"}),
        handbook_rules="6",
    )

    def plan(self, graph, incidents) -> SpecialistResult:
        return plan_quality(graph, incidents)


class DealerCustomerCare(Agent):
    card = AgentCard(
        id="dealer_customer",
        title="Dealer Network & Customer Care",
        responsibility="Sends one notice to each dealer with an affected customer order, listing only "
                       "those orders, and assigns loaners by tier and promised date within each pool.",
        takes="customer orders behind the production orders the Supply Chain Planner moved",
        tools=frozenset({"dealer.notify", "crm.assign_loaner"}),
        handbook_rules="4, 5",
    )

    def plan(self, graph, pools, orders, reason) -> SpecialistResult:
        return plan_dealer_customer(graph, pools, orders, reason)


class CoordinatorCard(Agent):
    """The coordinator's card. Its behavior lives in coordinator.handle_event."""

    card = AgentCard(
        id="coordinator",
        title="Coordinator",
        responsibility="Reads each message with the LLM and a rule check, routes each real incident "
                       "to the specialist that owns it, validates every planned call, executes them in "
                       "a fixed order, and escalates rumors and anything that changed nothing.",
        takes="every event in the feed",
        tools=frozenset({"escalate"}),
        handbook_rules="7, 8, 9, 10",
    )


COORDINATOR = CoordinatorCard()
SUPPLY = SupplyChainPlanner()
QUALITY = QualityAgent()
DEALER = DealerCustomerCare()
SPECIALISTS = (SUPPLY, QUALITY, DEALER)
BY_ID = {a.id: a for a in (COORDINATOR, *SPECIALISTS)}


def roster() -> list[dict]:
    """Every agent's card, for the UI and the design card."""
    return [a.card.to_dict() for a in (COORDINATOR, *SPECIALISTS)]
