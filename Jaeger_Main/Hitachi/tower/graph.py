"""Ontology over the company tables.

Nodes are the records. Edges are the relationships the handbook uses:
shipment to part and plant, part to model through the bill of materials,
model and plant to production order, production order to customer order,
customer order to dealer and customer, lot and production order to vehicle.

The graph answers "who is affected". It does not decide tool calls.
"""

from __future__ import annotations

import csv
import os
import re
from collections import defaultdict
from datetime import date

from tower.calendar_util import date_to_idx
from tower.contracts import Mention

# Default location of the company CSVs shipped by the organizers.
PACKAGE_DATA = os.path.join(
    os.path.dirname(__file__),
    "..",
    "Data",
    "hack_the_highway_package",
    "data",
)


def _read(data_dir: str, name: str) -> list[dict]:
    """Read one company CSV as a list of row dicts. Every value is a string."""
    with open(os.path.join(data_dir, name), newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


# The knowledge graph. Nodes are dicts keyed by id (one dict per table); edges are the lookup
# indexes built in __init__.
class WorldGraph:
    """The company ontology: record tables (nodes), relationship indexes (edges), and the name
    resolver that turns free-text mentions into ids.

    Read-only after __init__. Scheduling state that changes during an event lives in
    schedule.PlantSchedule, never here, so one graph is shared safely by every event.
    """

    def __init__(self, data_dir: str | None = None):
        data_dir = os.path.abspath(data_dir or PACKAGE_DATA)
        self.data_dir = data_dir

        # --- Nodes: one dictionary per table, keyed by that table's id. Numeric columns become
        # ints.
        self.plants = {r["plant_id"]: {**r, "slots_per_day": int(r["slots_per_day"])} for r in _read(data_dir, "plants.csv")}
        self.suppliers = {r["supplier_id"]: r for r in _read(data_dir, "suppliers.csv")}
        self.parts = {r["part_id"]: r for r in _read(data_dir, "parts.csv")}
        self.models = {r["model"]: r for r in _read(data_dir, "models.csv")}
        self.dealers = {r["dealer_id"]: {**r, "transit_days": int(r["transit_days"])} for r in _read(data_dir, "dealers.csv")}
        self.customers = {r["customer_id"]: r for r in _read(data_dir, "customers.csv")}
        self.shipments = {r["shipment_id"]: {**r, "covers_days": int(r["covers_days"])} for r in _read(data_dir, "inbound_shipments.csv")}
        self.lots = {r["lot_id"]: r for r in _read(data_dir, "part_lots.csv")}
        self.loaners = {r["dealer_id"]: int(r["loaners_available"]) for r in _read(data_dir, "loaners.csv")}

        # Production orders also get 'idx', their working-day index, so scheduling compares days
        # as integers.
        self.orders = {}
        for r in _read(data_dir, "production_orders.csv"):
            built = date.fromisoformat(r["build_date"])
            self.orders[r["production_order_id"]] = {
                **r,
                "units": int(r["units"]),
                "idx": date_to_idx(built),
            }
        self.customer_orders = {r["customer_order_id"]: r for r in _read(data_dir, "customer_orders.csv")}
        self.vehicles = {r["vin"]: r for r in _read(data_dir, "finished_vehicles.csv")}

        # --- Edges. Bill of materials, part <-> model: which builds need a delayed or defective
        # part.
        self.models_by_part: dict[str, set[str]] = defaultdict(set)
        self.parts_by_model: dict[str, set[str]] = defaultdict(set)
        for r in _read(data_dir, "bom.csv"):
            self.models_by_part[r["part_id"]].add(r["model"])
            self.parts_by_model[r["model"]].add(r["part_id"])

        # Which plants can build which models: the transfer targets. Sorted so the lowest plant id
        # is tried first.
        self.plants_by_model: dict[str, list[str]] = defaultdict(list)
        self.models_by_plant: dict[str, set[str]] = defaultdict(set)
        for r in _read(data_dir, "plant_models.csv"):
            self.plants_by_model[r["model"]].append(r["plant_id"])
            self.models_by_plant[r["plant_id"]].add(r["model"])
        for model in self.plants_by_model:
            self.plants_by_model[model].sort()

        # Production order -> its customer orders (cars already promised to buyers).
        self.cos_by_po: dict[str, list[dict]] = defaultdict(list)
        for co in self.customer_orders.values():
            self.cos_by_po[co["production_order_id"]].append(co)
        for rows in self.cos_by_po.values():
            rows.sort(key=lambda r: r["customer_order_id"])

        # --- Name resolution. Maps lower-cased text ('the texas plant', 'kestrel', 'p_tx') to
        # (entity_type, id). aliases.csv loads first so its nicknames win.
        self._alias_map: dict[str, tuple[str, str]] = {}
        self._add_aliases(_read(data_dir, "aliases.csv"))
        for plant_id, plant in self.plants.items():
            self._add_alias(plant_id, "plant", plant_id)
            self._add_alias(plant["name"], "plant", plant_id)
        for supplier_id, supplier in self.suppliers.items():
            self._add_alias(supplier_id, "supplier", supplier_id)
            self._add_alias(supplier["name"], "supplier", supplier_id)
        for part_id, part in self.parts.items():
            self._add_alias(part_id, "part", part_id)
            self._add_alias(part["name"], "part", part_id)
        for model in self.models:
            self._add_alias(model, "model", model)
        for shipment_id in self.shipments:
            self._add_alias(shipment_id, "shipment", shipment_id)
        for lot_id in self.lots:
            self._add_alias(lot_id, "lot", lot_id)
        for dealer_id, dealer in self.dealers.items():
            self._add_alias(dealer_id, "dealer", dealer_id)
            self._add_alias(dealer["name"], "dealer", dealer_id)

        # One regex of every alias, longest first, so 'the Texas plant' matches before 'Texas'.
        # The guards stop matches inside other words.
        pieces = sorted((re.escape(alias) for alias in self._alias_map), key=len, reverse=True)
        self._alias_re = re.compile(
            r"(?<![A-Za-z0-9])(?:" + "|".join(pieces) + r")(?![A-Za-z0-9])",
            re.I,
        )

    def _add_alias(self, alias: str, entity_type: str, entity_id: str) -> None:
        """Register one name for an entity, case-insensitively, without clobbering a nickname."""
        key = alias.casefold()
        current = self._alias_map.get(key)
        if current and current != (entity_type, entity_id):
            # Keep the official aliases.csv row. Ids and legal names are added later
            # and must not overwrite a nickname that already points somewhere else.
            return
        self._alias_map[key] = (entity_type, entity_id)

    def _add_aliases(self, rows: list[dict]) -> None:
        """Load aliases.csv. These rows are authoritative, so they overwrite unconditionally."""
        for row in rows:
            key = row["alias"].casefold()
            self._alias_map[key] = (row["entity_type"], row["entity_id"])
        # "the Texas plant" is also written "Texas plant". Add the short form unless it is taken.
        for row in rows:
            if row["alias"].casefold().startswith("the "):
                self._add_alias(row["alias"][4:], row["entity_type"], row["entity_id"])

    # Find every known name in a piece of text, in reading order.
    def resolve_mentions(self, text: str) -> list[Mention]:
        """Return a Mention for each alias found in text, with character offsets.

        finditer never returns overlapping matches, and the regex tries longer aliases first,
        so "Wacky Wheels San Antonio" yields one plant mention, not a plant plus a city.
        """
        mentions = []
        for match in self._alias_re.finditer(text):
            entity_type, entity_id = self._alias_map[match.group(0).casefold()]
            mentions.append(Mention(match.group(0), entity_type, entity_id, match.start(), match.end()))
        mentions.extend(self._typo_mentions(text, mentions))
        mentions.sort(key=lambda m: m.start)
        return mentions

    def _typo_mentions(self, text: str, exact: list[Mention]) -> list[Mention]:
        """Capitalised words one typo away from exactly one plant or supplier name ('Lexingtn' -> P_KY).

        Only plant and supplier names of six or more letters are tried, and only when the
        typo points at a single record, so ordinary words are not turned into entities.
        """
        if not hasattr(self, "_typo_names"):
            self._typo_names = {
                alias: target
                for alias, target in self._alias_map.items()
                if target[0] in ("plant", "supplier") and alias.isalpha() and len(alias) >= 6
            }
        found = []
        for match in _CAP_WORD.finditer(text):
            if any(m.start < match.end() and match.start() < m.end for m in exact):
                continue
            word = match.group(0).casefold()
            if word in self._alias_map:
                continue
            targets = {t for alias, t in self._typo_names.items() if _one_edit(word, alias)}
            if len(targets) == 1:
                entity_type, entity_id = targets.pop()
                found.append(Mention(match.group(0), entity_type, entity_id, match.start(), match.end()))
        return found

    def plants_for_model(self, model: str) -> list[str]:
        """Plants that can build a model, lowest id first. A copy, so callers may reorder it."""
        return list(self.plants_by_model.get(model, []))

    # Look up shipments by field. The delay reader uses this when a message names supplier, part
    # and plant but no shipment id.
    def find_shipments(
        self,
        supplier_id: str | None = None,
        part_id: str | None = None,
        plant_id: str | None = None,
        eta: str | None = None,
        shipment_id: str | None = None,
    ) -> list[dict]:
        """Shipments matching every filter given; None means "any". Sorted by shipment id.

        An explicit shipment_id wins outright: it returns that one row or nothing, and the other
        filters are ignored, so a mistyped id never falls through to a different shipment.
        """
        if shipment_id:
            row = self.shipments.get(shipment_id)
            return [row] if row else []
        hits = []
        for row in self.shipments.values():
            if supplier_id and row["supplier_id"] != supplier_id:
                continue
            if part_id and row["part_id"] != part_id:
                continue
            if plant_id and row["plant_id"] != plant_id:
                continue
            if eta and row["eta_date"] != eta:
                continue
            hits.append(row)
        hits.sort(key=lambda r: r["shipment_id"])
        return hits

    # Candidate lots for a quality hold: matching supplier/part/plant and a build window
    # overlapping the message's dates.
    def find_lots(
        self,
        supplier_id: str | None = None,
        part_id: str | None = None,
        plant_id: str | None = None,
        build_start: str | None = None,
        build_end: str | None = None,
        lot_id: str | None = None,
    ) -> list[dict]:
        """Lots matching every filter given; None means "any". Sorted by lot id.

        Like find_shipments, an explicit lot_id returns that lot or nothing. The date filter
        applies only when both ends of the window are known. ISO dates compare correctly as
        strings, so no parsing is needed.
        """
        if lot_id:
            row = self.lots.get(lot_id)
            return [row] if row else []
        hits = []
        for row in self.lots.values():
            if supplier_id and row["supplier_id"] != supplier_id:
                continue
            if part_id and row["part_id"] != part_id:
                continue
            if plant_id and row["plant_id"] != plant_id:
                continue
            if build_start and build_end:
                # Inclusive overlap with the lot's own build window.
                if row["last_build_date"] < build_start or row["first_build_date"] > build_end:
                    continue
            hits.append(row)
        hits.sort(key=lambda r: r["lot_id"])
        return hits

    # --- 'Who is affected' queries. These implement handbook rules 1, 2 and 6.
    def affected_orders_delay(self, plant_id: str, part_id: str, blocked_from: str, blocked_until: str) -> list[dict]:
        """Future orders at the receiving plant whose model uses the part.

        Blocked window is [original ETA, new ETA). Already-built orders stay put.
        idx >= 0 means "today or later"; negative indexes are the two weeks already built.
        Sorted by day, then id, which is the order the supply planner re-slots them in.
        """
        models = self.models_by_part.get(part_id, set())
        hits = [
            po for po in self.orders.values()
            if po["idx"] >= 0
            and po["plant_id"] == plant_id
            and po["model"] in models
            and blocked_from <= po["build_date"] < blocked_until
        ]
        hits.sort(key=lambda r: (r["idx"], r["production_order_id"]))
        return hits

    def affected_orders_outage(self, plant_id: str, start: str, end: str) -> list[dict]:
        """Every still-movable order at the plant on an outage day, inclusive.

        Unlike a delay, an outage stops every model, so there is no bill-of-materials filter.
        """
        hits = [
            po for po in self.orders.values()
            if po["idx"] >= 0
            and po["plant_id"] == plant_id
            and start <= po["build_date"] <= end
        ]
        hits.sort(key=lambda r: (r["idx"], r["production_order_id"]))
        return hits

    def affected_vehicles(self, plant_id: str, part_id: str, build_start: str, build_end: str) -> list[dict]:
        """Finished vehicles built at the plant, in the lot window, on models that use the part.

        Handbook rule 6. Returns sold and in-stock vehicles together; the quality agent splits
        them into stop-sale (in_stock) and owner notices (sold).
        """
        models = self.models_by_part.get(part_id, set())
        hits = [
            vehicle for vehicle in self.vehicles.values()
            if vehicle["plant_id"] == plant_id
            and vehicle["model"] in models
            and build_start <= vehicle["build_date"] <= build_end
        ]
        hits.sort(key=lambda r: r["vin"])
        return hits

    # Hop from production orders to their customer orders (for dealer notices and loaners).
    def customer_orders_for(self, production_order_ids: list[str] | set[str]) -> list[dict]:
        """Customer orders behind the given production orders, sorted by customer order id.

        A production order with no buyer yet contributes nothing.
        """
        wanted = set(production_order_ids)
        hits = [co for po in wanted for co in self.cos_by_po.get(po, [])]
        hits.sort(key=lambda r: r["customer_order_id"])
        return hits

    # --- Evidence: the graph paths shown in the trace and UI for each kind of incident.
    def delay_paths(self, shipment: dict, orders: list[dict], customer_orders: list[dict]) -> list[list[str]]:
        """Citation paths: Shipment → Part → Model → ProductionOrder → CustomerOrder → Dealer / Customer."""
        # Group the customer orders by production order, so each path is built in one pass.
        by_po: dict[str, list[dict]] = defaultdict(list)
        for co in customer_orders:
            by_po[co["production_order_id"]].append(co)
        paths = []
        # Every model that uses the part, for the "nothing affected" path below.
        models_seen = []
        for model in sorted(self.models_by_part.get(shipment["part_id"], ())):
            models_seen.append(f"Model {model} (BOM)")
        # Still cite a path when nothing is affected, so the trace shows why no build moved.
        if not orders:
            return [[
                f"Shipment {shipment['shipment_id']}",
                f"Part {shipment['part_id']}",
                *models_seen,
                f"Plant {shipment['plant_id']}",
                "No future production order in the blocked window",
            ]]
        # One path per affected customer order; an order with no buyer ends its path early.
        for po in orders:
            linked = by_po.get(po["production_order_id"], [])
            if not linked:
                paths.append([
                    f"Shipment {shipment['shipment_id']}",
                    f"Part {shipment['part_id']}",
                    f"Model {po['model']} (BOM)",
                    f"Plant {po['plant_id']}",
                    f"ProductionOrder {po['production_order_id']}",
                    "No customer order",
                ])
                continue
            for co in linked:
                paths.append([
                    f"Shipment {shipment['shipment_id']}",
                    f"Part {shipment['part_id']}",
                    f"Model {po['model']} (BOM)",
                    f"Plant {po['plant_id']}",
                    f"ProductionOrder {po['production_order_id']}",
                    f"CustomerOrder {co['customer_order_id']}",
                    f"Dealer {co['dealer_id']} / Customer {co['customer_id']}",
                ])
        return paths

    def outage_paths(self, plant_id: str, orders: list[dict], customer_orders: list[dict]) -> list[list[str]]:
        """Citation paths: Plant → ProductionOrder → CustomerOrder → Dealer / Customer."""
        by_po: dict[str, list[dict]] = defaultdict(list)
        for co in customer_orders:
            by_po[co["production_order_id"]].append(co)
        paths = []
        for po in orders:
            linked = by_po.get(po["production_order_id"], [])
            if not linked:
                paths.append([
                    f"Plant {plant_id}",
                    f"ProductionOrder {po['production_order_id']}",
                    "No customer order",
                ])
                continue
            for co in linked:
                paths.append([
                    f"Plant {plant_id}",
                    f"ProductionOrder {po['production_order_id']}",
                    f"CustomerOrder {co['customer_order_id']}",
                    f"Dealer {co['dealer_id']} / Customer {co['customer_id']}",
                ])
        return paths

    def quality_paths(self, lot: dict, vehicles: list[dict]) -> list[list[str]]:
        """Citation paths: Lot → ProductionOrder → Vehicle → Dealer (unsold) or Dealer / Customer (sold).

        The first path describes the lot itself (part, supplier, plant), so even a lot with no
        affected vehicles still shows where it came from.
        """
        paths = [[
            f"Lot {lot['lot_id']}",
            f"Part {lot['part_id']}",
            f"Supplier {lot['supplier_id']}",
            f"Plant {lot['plant_id']}",
        ]]
        for vehicle in vehicles:
            tail = f"Dealer {vehicle['dealer_id']}"
            if vehicle["status"] == "sold" and vehicle.get("customer_id"):
                tail = f"Dealer {vehicle['dealer_id']} / Customer {vehicle['customer_id']}"
            paths.append([
                f"Lot {lot['lot_id']}",
                f"ProductionOrder {vehicle['production_order_id']}",
                f"Vehicle {vehicle['vin']}",
                tail,
            ])
        return paths

    # Record counts, for tests/selfcheck.py and the UI's ontology panel.
    def counts(self) -> dict[str, int]:
        return {
            "plants": len(self.plants),
            "suppliers": len(self.suppliers),
            "parts": len(self.parts),
            "models": len(self.models),
            "bom_edges": sum(len(v) for v in self.parts_by_model.values()),
            "shipments": len(self.shipments),
            "lots": len(self.lots),
            "production_orders": len(self.orders),
            "customer_orders": len(self.customer_orders),
            "customers": len(self.customers),
            "dealers": len(self.dealers),
            "vehicles": len(self.vehicles),
            "aliases": len(self._alias_map),
        }


_CAP_WORD = re.compile(r"\b[A-Z][a-z]{5,}\b")


def _one_edit(a: str, b: str) -> bool:
    """True when b is a with one letter changed, added, dropped, or two neighbours swapped."""
    if a == b or abs(len(a) - len(b)) > 1:
        return False
    if len(a) == len(b):
        diff = [i for i in range(len(a)) if a[i] != b[i]]
        if len(diff) == 1:
            return True
        return len(diff) == 2 and diff[1] == diff[0] + 1 and a[diff[0]] == b[diff[1]] and a[diff[1]] == b[diff[0]]
    short, long_ = (a, b) if len(a) < len(b) else (b, a)
    return any(long_[:i] + long_[i + 1:] == short for i in range(len(long_)))
