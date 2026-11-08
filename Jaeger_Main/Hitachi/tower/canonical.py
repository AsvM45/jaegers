"""Map an incident kind to one fact name and one domain.

understand() is the only text adapter. These helpers do not read partner
wording and do not build Incident objects. Planners keep receiving Incident
objects from understand().
"""

from __future__ import annotations

# Frozen vocabulary. Unknown kinds share the unconfirmed fact and domain.
_FACTS = {
    "supplier_delay": ("ShipmentDelayed", "procurement"),
    "plant_outage": ("PlantDown", "planning"),
    "quality_hold": ("LotHeld", "inventory"),
    "noise": ("Ignored", "none"),
    "unconfirmed": ("Unconfirmed", "none"),
}
_UNKNOWN = ("Unconfirmed", "none")


def fact_name(kind: str) -> str:
    """Fact name for an incident kind. An unknown kind is Unconfirmed."""
    return _FACTS.get(kind, _UNKNOWN)[0]


def domain_name(kind: str) -> str:
    """Domain for an incident kind. An unknown kind is none."""
    return _FACTS.get(kind, _UNKNOWN)[1]
