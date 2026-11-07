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

PACKAGE_DATA = os.path.join(
    os.path.dirname(__file__),
    "..",
    "Data",
    "hack_the_highway_package",
    "data",
)


def _read(data_dir: str, name: str) -> list[dict]:
    with open(os.path.join(data_dir, name), newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


class WorldGraph:
    def __init__(self, data_dir: str | None = None):
        data_dir = os.path.abspath(data_dir or PACKAGE_DATA)
        self.data_dir = data_dir

        self.plants = {r["plant_id"]: {**r, "slots_per_day": int(r["slots_per_day"])} for r in _read(data_dir, "plants.csv")}
        self.suppliers = {r["supplier_id"]: r for r in _read(data_dir, "suppliers.csv")}
        self.parts = {r["part_id"]: r for r in _read(data_dir, "parts.csv")}
        self.models = {r["model"]: r for r in _read(data_dir, "models.csv")}
        self.dealers = {r["dealer_id"]: {**r, "transit_days": int(r["transit_days"])} for r in _read(data_dir, "dealers.csv")}
        self.customers = {r["customer_id"]: r for r in _read(data_dir, "customers.csv")}
        self.shipments = {r["shipment_id"]: {**r, "covers_days": int(r["covers_days"])} for r in _read(data_dir, "inbound_shipments.csv")}
        self.lots = {r["lot_id"]: r for r in _read(data_dir, "part_lots.csv")}
        self.loaners = {r["dealer_id"]: int(r["loaners_available"]) for r in _read(data_dir, "loaners.csv")}

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

        self.models_by_part: dict[str, set[str]] = defaultdict(set)
        self.parts_by_model: dict[str, set[str]] = defaultdict(set)
        for r in _read(data_dir, "bom.csv"):
            self.models_by_part[r["part_id"]].add(r["model"])
            self.parts_by_model[r["model"]].add(r["part_id"])

        self.plants_by_model: dict[str, list[str]] = defaultdict(list)
        self.models_by_plant: dict[str, set[str]] = defaultdict(set)
        for r in _read(data_dir, "plant_models.csv"):
            self.plants_by_model[r["model"]].append(r["plant_id"])
            self.models_by_plant[r["plant_id"]].add(r["model"])
        for model in self.plants_by_model:
            self.plants_by_model[model].sort()

        self.cos_by_po: dict[str, list[dict]] = defaultdict(list)
        for co in self.customer_orders.values():
            self.cos_by_po[co["production_order_id"]].append(co)
        for rows in self.cos_by_po.values():
            rows.sort(key=lambda r: r["customer_order_id"])

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

        pieces = sorted((re.escape(alias) for alias in self._alias_map), key=len, reverse=True)
        self._alias_re = re.compile(
            r"(?<![A-Za-z0-9])(?:" + "|".join(pieces) + r")(?![A-Za-z0-9])",
            re.I,
        )

    def _add_alias(self, alias: str, entity_type: str, entity_id: str) -> None:
        key = alias.casefold()
        current = self._alias_map.get(key)
        if current and current != (entity_type, entity_id):
            # Keep the official aliases.csv row. Ids and legal names are added later
            # and must not overwrite a nickname that already points somewhere else.
            return
        self._alias_map[key] = (entity_type, entity_id)

    def _add_aliases(self, rows: list[dict]) -> None:
        for row in rows:
            key = row["alias"].casefold()
            self._alias_map[key] = (row["entity_type"], row["entity_id"])

    def resolve_mentions(self, text: str) -> list[Mention]:
        mentions = []
        for match in self._alias_re.finditer(text):
            entity_type, entity_id = self._alias_map[match.group(0).casefold()]
            mentions.append(Mention(match.group(0), entity_type, entity_id, match.start(), match.end()))
        return mentions

    def plants_for_model(self, model: str) -> list[str]:
        return list(self.plants_by_model.get(model, []))

    def find_shipments(
        self,
        supplier_id: str | None = None,
        part_id: str | None = None,
        plant_id: str | None = None,
        eta: str | None = None,
        shipment_id: str | None = None,
    ) -> list[dict]:
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

    def find_lots(
        self,
        supplier_id: str | None = None,
        part_id: str | None = None,
        plant_id: str | None = None,
        build_start: str | None = None,
        build_end: str | None = None,
        lot_id: str | None = None,
    ) -> list[dict]:
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

    def affected_orders_delay(self, plant_id: str, part_id: str, blocked_from: str, blocked_until: str) -> list[dict]:
        """Future orders at the receiving plant whose model uses the part.

        Blocked window is [original ETA, new ETA). Already-built orders stay put.
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
        """Every still-movable order at the plant on an outage day, inclusive."""
        hits = [
            po for po in self.orders.values()
            if po["idx"] >= 0
            and po["plant_id"] == plant_id
            and start <= po["build_date"] <= end
        ]
        hits.sort(key=lambda r: (r["idx"], r["production_order_id"]))
        return hits

    def affected_vehicles(self, plant_id: str, part_id: str, build_start: str, build_end: str) -> list[dict]:
        """Finished vehicles built at the plant, in the lot window, on models that use the part."""
        models = self.models_by_part.get(part_id, set())
        hits = [
            vehicle for vehicle in self.vehicles.values()
            if vehicle["plant_id"] == plant_id
            and vehicle["model"] in models
            and build_start <= vehicle["build_date"] <= build_end
        ]
        hits.sort(key=lambda r: r["vin"])
        return hits

    def customer_orders_for(self, production_order_ids: list[str] | set[str]) -> list[dict]:
        wanted = set(production_order_ids)
        hits = [co for po in wanted for co in self.cos_by_po.get(po, [])]
        hits.sort(key=lambda r: r["customer_order_id"])
        return hits

    def delay_paths(self, shipment: dict, orders: list[dict], customer_orders: list[dict]) -> list[list[str]]:
        """Citation paths: Shipment → Part → Model → ProductionOrder → CustomerOrder → Dealer / Customer."""
        by_po: dict[str, list[dict]] = defaultdict(list)
        for co in customer_orders:
            by_po[co["production_order_id"]].append(co)
        paths = []
        models_seen = []
        for model in sorted(self.models_by_part.get(shipment["part_id"], ())):
            models_seen.append(f"Model {model} (BOM)")
        if not orders:
            return [[
                f"Shipment {shipment['shipment_id']}",
                f"Part {shipment['part_id']}",
                *models_seen,
                f"Plant {shipment['plant_id']}",
                "No future production order in the blocked window",
            ]]
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
