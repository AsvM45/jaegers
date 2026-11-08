"""Load the graph and check the calendar against the company tables."""

from __future__ import annotations

import os
import sys
from collections import Counter
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tower.calendar_util import TODAY, date_to_idx, extract_dates, idx_to_date, parse_phrase
from tower.graph import WorldGraph


def main() -> None:
    """Run every check and print the evidence. A failed assert names what broke."""
    graph = WorldGraph()
    counts = graph.counts()
    print("COUNTS", counts)
    # Sanity checks: table sizes, the calendar mapping, date phrases and alias resolution.
    assert counts["plants"] == 6
    assert counts["production_orders"] == 540
    assert counts["vehicles"] == 5348

    # Calendar file is the authority for index  -10..19.
    import csv
    with open(os.path.join(graph.data_dir, "calendar.csv"), newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            idx = int(row["day_index"])
            assert idx_to_date(idx).isoformat() == row["date"], row
            assert date_to_idx(date.fromisoformat(row["date"])) == idx

    # The relative-date readings locked in PROGRESS.md ("next" means next calendar week), plus
    # every named-date shape that appears in the 15 events.
    phrases = {
        "next Monday": "2027-03-15",
        "next Friday": "2027-03-19",
        "next Tuesday": "2027-03-16",
        "next Thursday": "2027-03-18",
        "last Monday": "2027-03-01",
        "Monday Mar 22": "2027-03-22",
        "Thursday Feb 25": "2027-02-25",
        "Friday Mar 26": "2027-03-26",
        "Tuesday Mar 30": "2027-03-30",
        "Thursday Apr 1": "2027-04-01",
        "2027-03-24": "2027-03-24",
    }
    for phrase, expected in phrases.items():
        got = parse_phrase(phrase)
        assert got is not None and got.isoformat() == expected, (phrase, got)
    assert parse_phrase("next Monday").isoformat() < parse_phrase("next Friday").isoformat()

    # Printed rather than asserted: shows how a message with repeated phrases is split up.
    sample = extract_dates(
        "We're dark from next Friday through Monday Mar 22. Can't make it next Monday. Carrier says next Friday."
    )
    print("SAMPLE DATES", sample)

    # Spot-check the records the structured events name, so a bad data path fails here first.
    shipment = graph.shipments["SH-0182"]
    assert shipment["part_id"] == "CAM-360"
    assert shipment["plant_id"] == "P_IN"
    assert shipment["eta_date"] == "2027-03-15"

    lot = graph.lots["LOT-0191"]
    print("LOT-0191", lot)

    # Alias resolution: a nickname (Quanta), a part name, a city, a lot id and a phrase
    # ("the Texas plant") must all resolve.
    mentions = graph.resolve_mentions(
        "Quanta says the infotainment chip for Princeton is late. Lot LOT-0191 at P_IN. the Texas plant."
    )
    print("MENTIONS", [(m.alias, m.entity_type, m.entity_id) for m in mentions])
    kinds = {m.entity_id for m in mentions}
    assert "SUP-12" in kinds and "CHIP-IVI" in kinds and "P_IN" in kinds and "LOT-0191" in kinds and "P_TX" in kinds

    print("VEHICLE STATUS", Counter(v["status"] for v in graph.vehicles.values()))
    print("TIERS", Counter(c["tier"] for c in graph.customers.values()))
    print("TODAY", TODAY.isoformat())
    print("OK")


if __name__ == "__main__":
    main()
