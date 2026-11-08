"""Domain map a page or another module can import.

Read model only. This module does not load company tables and does not call
Enterprise.
"""

from __future__ import annotations

DOMAINS = (
    {
        "id": "procurement",
        "fact": "ShipmentDelayed",
        "owns": "supplier delays and inbound parts",
    },
    {
        "id": "planning",
        "fact": "PlantDown",
        "owns": "plant outages and build slots",
    },
    {
        "id": "inventory",
        "fact": "LotHeld",
        "owns": "quality lots and stock holds",
    },
    {
        "id": "orders",
        "fact": "CustomerCommitment",
        "owns": "dealer notices and loaners",
    },
    {
        "id": "gateway",
        "fact": "EnterpriseCall",
        "owns": "the only door to enterprise writes",
    },
)


def payload() -> dict:
    return {
        "domains": [dict(row) for row in DOMAINS],
        "shape": "modular monolith",
    }
