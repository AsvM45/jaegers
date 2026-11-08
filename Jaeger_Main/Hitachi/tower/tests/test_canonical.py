"""Fact names and domains for the five incident kinds.

The customs sentence is a real partner notice. It must still classify as
supplier_delay, and planners still receive an Incident.
"""

from __future__ import annotations

import unittest

from tower.agents.understand import understand
from tower.canonical import domain_name, fact_name
from tower.contracts import Incident
from tower.graph import WorldGraph

_CUSTOMS = (
    "Volt says the heavy-duty wiring harness to the Texas plant is on hold at customs, "
    "original drop 2027-03-09, new ETA 2027-03-16."
)

_NAMES = (
    ("supplier_delay", "ShipmentDelayed", "procurement"),
    ("plant_outage", "PlantDown", "planning"),
    ("quality_hold", "LotHeld", "inventory"),
    ("noise", "Ignored", "none"),
    ("unconfirmed", "Unconfirmed", "none"),
)


class CanonicalTests(unittest.TestCase):
    def test_five_kinds_keep_their_fact_and_domain(self) -> None:
        for kind, fact, domain in _NAMES:
            with self.subTest(kind=kind):
                self.assertEqual(fact_name(kind), fact)
                self.assertEqual(domain_name(kind), domain)

    def test_unknown_kind_is_unconfirmed(self) -> None:
        self.assertEqual(fact_name("not-a-kind"), "Unconfirmed")
        self.assertEqual(domain_name("not-a-kind"), "none")

    def test_customs_hold_sentence_stays_supplier_delay(self) -> None:
        incidents = understand(WorldGraph(), _CUSTOMS)
        self.assertEqual(len(incidents), 1)
        incident = incidents[0]
        self.assertIsInstance(incident, Incident)
        self.assertEqual(incident.kind, "supplier_delay")
        self.assertEqual(fact_name(incident.kind), "ShipmentDelayed")
        self.assertEqual(domain_name(incident.kind), "procurement")


if __name__ == "__main__":
    unittest.main()
