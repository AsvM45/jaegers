# Control-tower board

Manager: the parent agent. Four owners. Append under your heading only. Do not edit another owner's files.

This is a modular monolith for one datathon team. Do not add microservices, network calls, pip packages, or a second database. Do not edit `enterprise.py`, `enterprise_server.py`, or `runs/`. Do not weaken tests. From `Jaeger_Main/Hitachi`, `python -m unittest tower.tests.test_edges tower.tests.test_adversarial` must stay green, and the 15 feed classifications must stay the same.

## Domain map

| Design piece | Owner in this repo | Fact it owns |
|---|---|---|
| API gateway | `tower/gateway.py` | The only door to `Enterprise.call` |
| Canonical adapter | `tower/canonical.py` and `tower/agents/understand.py` | Messy text becomes one incident kind |
| Planning and optimization | `tower/optimize.py` and `tower/agents/supply_chain.py` | Slot choice and a recommendation note |
| Quality / inventory hold | `tower/agents/quality.py` | Lot hold. Do not edit in this round |
| Orders, dealers, loaners | `tower/agents/dealer_customer.py` | Notices and loaners. Do not edit in this round |
| Analytics and UI | `tower/ui/` and `tower/domains.py` | Read models only |

Operational writes stay in Enterprise, one fresh world per `event_id`. Traces and the page are the analytics side. They read; they do not write company tables.

## Frozen vocabulary

- `supplier_delay` fact name: ShipmentDelayed. Domain: procurement.
- `plant_outage` fact name: PlantDown. Domain: planning.
- `quality_hold` fact name: LotHeld. Domain: inventory.
- `noise` fact name: Ignored. Domain: none.
- `unconfirmed` fact name: Unconfirmed. Domain: none.

## File locks

- Agent 1, gateway: `tower/gateway.py`, `tower/agents/coordinator.py`
- Agent 2, interpretations: `tower/canonical.py`, `tower/agents/understand.py`, `tower/tests/test_canonical.py`
- Agent 3, optimization: `tower/optimize.py`, `tower/agents/supply_chain.py`
- Agent 4, analytics and UI: `tower/domains.py`, `tower/ui/index.html`, `tower/ui/server.py`

`tower/tests/test_edges.py` imports `_execute` from `tower.agents.coordinator`. Agent 1 must keep that name working.

Agent 3 may append one note per planned order that starts with `Recommendation: `. Do not change tool names or arguments. Do not rewrite existing note strings.

Agent 4 may show fact names from the incident kind using the vocabulary above, even before a trace stores them. Do not require a new JSON field.

## Log

### manager

The platform diagram is the target shape. This repo stays one process. The gap is that the gateway, the canonical facts, the optimizer's recommendation, and the page are not named as separate owners.
