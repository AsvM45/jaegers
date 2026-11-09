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
from bisect import bisect_left, bisect_right
from collections import defaultdict
from datetime import date

from tower.calendar_util import date_to_idx
from tower.contracts import Mention

# One citation chain per customer order explodes on a wide outage. The trace
# keeps this many paths; the rest follow the same links and are counted.
PATH_KEEP = 32

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

        # Future orders at a plant, sorted by build date, so a window is a slice.
        self.future_by_plant: dict[str, list[dict]] = defaultdict(list)
        for order in self.orders.values():
            if order["idx"] >= 0:
                self.future_by_plant[order["plant_id"]].append(order)
        for rows in self.future_by_plant.values():
            rows.sort(key=lambda order: (order["build_date"], order["production_order_id"]))

        self.vehicles_by_plant: dict[str, list[dict]] = defaultdict(list)
        for vehicle in self.vehicles.values():
            self.vehicles_by_plant[vehicle["plant_id"]].append(vehicle)
        for rows in self.vehicles_by_plant.values():
            rows.sort(key=lambda vehicle: vehicle["build_date"])

        self.shipments_by_route: dict[tuple[str, str, str], list[dict]] = defaultdict(list)
        for row in self.shipments.values():
            self.shipments_by_route[(row["supplier_id"], row["part_id"], row["plant_id"])].append(row)
        for rows in self.shipments_by_route.values():
            rows.sort(key=lambda row: row["shipment_id"])

        self.lots_by_part_plant: dict[tuple[str, str], list[dict]] = defaultdict(list)
        for lot in self.lots.values():
            self.lots_by_part_plant[(lot["part_id"], lot["plant_id"])].append(lot)

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
        self._add_part_plurals()
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
        self._index_part_suffixes()

    def _add_alias(self, alias: str, entity_type: str, entity_id: str) -> None:
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

    def _add_part_plurals(self) -> None:
        """A part said in the plural ("alloy wheels", "infotainment chips") is still that part.

        Only a trailing "s" is added, and only when that spelling is not already another record.
        """
        wanted: dict[str, str] = {}
        blocked: set[str] = set()
        for alias, (entity_type, entity_id) in self._alias_map.items():
            if entity_type != "part" or alias.endswith("s"):
                continue
            plural = alias + "s"
            current = self._alias_map.get(plural)
            if current and current != ("part", entity_id):
                blocked.add(plural)
                continue
            if plural in wanted and wanted[plural] != entity_id:
                blocked.add(plural)
                continue
            wanted[plural] = entity_id
        for plural, entity_id in wanted.items():
            if plural not in blocked:
                self._alias_map[plural] = ("part", entity_id)

    def _index_part_suffixes(self) -> None:
        """Whole-word tails of part aliases, at least two words, one part only.

        "battery packs" is the tail of "60 kWh battery packs" and of no other
        part, so it resolves. A tail shared by two parts, such as "wiring
        harness", is left unresolved. The full alias is already in the exact map.
        """
        owners: dict[str, set[str]] = defaultdict(set)
        for alias, (entity_type, entity_id) in self._alias_map.items():
            if entity_type != "part":
                continue
            words = alias.split()
            for length in range(2, len(words)):
                suffix = " ".join(words[-length:])
                if suffix in self._alias_map:
                    continue
                owners[suffix].add(entity_id)
        self._part_suffixes = {
            suffix: entity_id
            for suffix, ids in owners.items()
            if len(ids) == 1
            for entity_id in ids
        }
        if not self._part_suffixes:
            self._part_suffix_re = None
            return
        pieces = sorted((re.escape(suffix) for suffix in self._part_suffixes), key=len, reverse=True)
        self._part_suffix_re = re.compile(
            r"(?<![A-Za-z0-9])(?:" + "|".join(pieces) + r")(?![A-Za-z0-9])",
            re.I,
        )

    def resolve_mentions(self, text: str) -> list[Mention]:
        mentions = []
        occupied: list[tuple[int, int]] = []
        for match in self._alias_re.finditer(text):
            entity_type, entity_id = self._alias_map[match.group(0).casefold()]
            mentions.append(Mention(match.group(0), entity_type, entity_id, match.start(), match.end()))
            occupied.append((match.start(), match.end()))
        if self._part_suffix_re is not None:
            for match in self._part_suffix_re.finditer(text):
                span = (match.start(), match.end())
                if any(span[0] < stop and start < span[1] for start, stop in occupied):
                    continue
                entity_id = self._part_suffixes[match.group(0).casefold()]
                mentions.append(Mention(match.group(0), "part", entity_id, match.start(), match.end()))
                occupied.append(span)
        # Last, plant and supplier names written with one typo ("Lexingtn" -> P_KY).
        mentions.extend(self._typo_mentions(text, mentions))
        mentions.sort(key=lambda item: (item.start, item.end))
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
        if supplier_id and part_id and plant_id:
            rows = self.shipments_by_route.get((supplier_id, part_id, plant_id), ())
        else:
            rows = self.shipments.values()
        hits = []
        for row in rows:
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
        if part_id and plant_id:
            rows = self.lots_by_part_plant.get((part_id, plant_id), ())
        else:
            rows = self.lots.values()
        hits = []
        for row in rows:
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
            po for po in self._dated_slice(self.future_by_plant.get(plant_id, ()), blocked_from, blocked_until, inclusive_end=False)
            if po["model"] in models
        ]
        return hits

    def affected_orders_outage(self, plant_id: str, start: str, end: str) -> list[dict]:
        """Every still-movable order at the plant on an outage day, inclusive."""
        return list(self._dated_slice(self.future_by_plant.get(plant_id, ()), start, end, inclusive_end=True))

    def affected_vehicles(self, plant_id: str, part_id: str, build_start: str, build_end: str) -> list[dict]:
        """Finished vehicles built at the plant, in the lot window, on models that use the part."""
        models = self.models_by_part.get(part_id, set())
        hits = [
            vehicle for vehicle in self._dated_slice(
                self.vehicles_by_plant.get(plant_id, ()), build_start, build_end, inclusive_end=True
            )
            if vehicle["model"] in models
        ]
        hits.sort(key=lambda vehicle: vehicle["vin"])
        return hits

    @staticmethod
    def _dated_slice(rows, start: str, end: str, inclusive_end: bool) -> list[dict]:
        """Rows are sorted by build_date. The slice is that order."""
        if not rows:
            return []
        lo = bisect_left(rows, start, key=lambda row: row["build_date"])
        if inclusive_end:
            hi = bisect_right(rows, end, key=lambda row: row["build_date"])
        else:
            hi = bisect_left(rows, end, key=lambda row: row["build_date"])
        return rows[lo:hi]

    def customer_orders_for(self, production_order_ids: list[str] | set[str]) -> list[dict]:
        wanted = set(production_order_ids)
        hits = [co for po in wanted for co in self.cos_by_po.get(po, [])]
        hits.sort(key=lambda r: r["customer_order_id"])
        return hits

    def delay_paths(
        self,
        shipment: dict,
        orders: list[dict],
        customer_orders: list[dict],
        limit: int = PATH_KEEP,
    ) -> tuple[list[list[str]], int]:
        """Citation paths: Shipment → Part → Model → ProductionOrder → CustomerOrder → Dealer / Customer.

        Returns the stored paths and the full path count. Storage stops at `limit`.
        """
        by_po = _orders_by_po(customer_orders)
        paths: list[list[str]] = []
        total = 0
        models_seen = [f"Model {model} (BOM)" for model in sorted(self.models_by_part.get(shipment["part_id"], ()))]
        if not orders:
            _keep(paths, limit, [
                f"Shipment {shipment['shipment_id']}",
                f"Part {shipment['part_id']}",
                *models_seen,
                f"Plant {shipment['plant_id']}",
                "No future production order in the blocked window",
            ])
            return paths, 1
        for po in orders:
            head = [
                f"Shipment {shipment['shipment_id']}",
                f"Part {shipment['part_id']}",
                f"Model {po['model']} (BOM)",
                f"Plant {po['plant_id']}",
                f"ProductionOrder {po['production_order_id']}",
            ]
            total += _link_paths(paths, limit, head, by_po.get(po["production_order_id"], []))
        return paths, total

    def outage_paths(
        self,
        plant_id: str,
        orders: list[dict],
        customer_orders: list[dict],
        limit: int = PATH_KEEP,
    ) -> tuple[list[list[str]], int]:
        """Plant → ProductionOrder → CustomerOrder → Dealer / Customer. Storage stops at `limit`."""
        by_po = _orders_by_po(customer_orders)
        paths: list[list[str]] = []
        total = 0
        if not orders:
            total = _keep(paths, limit, [
                f"Plant {plant_id}",
                "No future production order in the outage window",
            ])
            return paths, total
        for po in orders:
            head = [
                f"Plant {plant_id}",
                f"ProductionOrder {po['production_order_id']}",
            ]
            total += _link_paths(paths, limit, head, by_po.get(po["production_order_id"], []))
        return paths, total

    def quality_paths(self, lot: dict, vehicles: list[dict], limit: int = PATH_KEEP) -> tuple[list[list[str]], int]:
        """Lot → vehicle → dealer or customer. Storage stops at `limit`, including the lot header."""
        paths: list[list[str]] = []
        total = _keep(paths, limit, [
            f"Lot {lot['lot_id']}",
            f"Part {lot['part_id']}",
            f"Supplier {lot['supplier_id']}",
            f"Plant {lot['plant_id']}",
        ])
        if not vehicles:
            total += _keep(paths, limit, [
                f"Lot {lot['lot_id']}",
                f"Part {lot['part_id']}",
                f"Plant {lot['plant_id']}",
                "No finished vehicle in the lot window",
            ])
            return paths, total
        for vehicle in vehicles:
            tail = f"Dealer {vehicle['dealer_id']}"
            if vehicle["status"] == "sold" and vehicle.get("customer_id"):
                tail = f"Dealer {vehicle['dealer_id']} / Customer {vehicle['customer_id']}"
            total += _keep(paths, limit, [
                f"Lot {lot['lot_id']}",
                f"ProductionOrder {vehicle['production_order_id']}",
                f"Vehicle {vehicle['vin']}",
                tail,
            ])
        return paths, total

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

    def ontology_export(self) -> dict:
        """Nodes, edges, and the three citation chains a judge can replay."""
        return {
            "nodes": [
                "Supplier", "Shipment", "Part", "Plant", "Model",
                "ProductionOrder", "CustomerOrder", "Dealer", "Customer",
                "Lot", "Vehicle",
            ],
            "edges": [
                ["Supplier", "ships", "Shipment"],
                ["Shipment", "part", "Part"],
                ["Shipment", "plant", "Plant"],
                ["Part", "BOM", "Model"],
                ["Plant", "builds", "ProductionOrder"],
                ["Model", "built as", "ProductionOrder"],
                ["ProductionOrder", "promised as", "CustomerOrder"],
                ["CustomerOrder", "sold by", "Dealer"],
                ["CustomerOrder", "placed by", "Customer"],
                ["Lot", "installed on", "Vehicle"],
                ["ProductionOrder", "finished as", "Vehicle"],
                ["Vehicle", "stocked at", "Dealer"],
                ["Vehicle", "sold to", "Customer"],
            ],
            "chains": [
                "Shipment → Part → Model (BOM) → ProductionOrder → CustomerOrder → Dealer / Customer",
                "Plant → ProductionOrder → CustomerOrder → Dealer / Customer",
                "Lot → ProductionOrder → Vehicle → Dealer / Customer",
            ],
            "counts": self.counts(),
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


def _orders_by_po(customer_orders: list[dict]) -> dict[str, list[dict]]:
    by_po: dict[str, list[dict]] = defaultdict(list)
    for order in customer_orders:
        by_po[order["production_order_id"]].append(order)
    return by_po


def _keep(paths: list[list[str]], limit: int, path: list[str]) -> int:
    if len(paths) < limit:
        paths.append(path)
    return 1


def _link_paths(paths: list[list[str]], limit: int, head: list[str], linked: list[dict]) -> int:
    if not linked:
        return _keep(paths, limit, [*head, "No customer order"])
    total = 0
    for order in linked:
        total += _keep(paths, limit, [
            *head,
            f"CustomerOrder {order['customer_order_id']}",
            f"Dealer {order['dealer_id']} / Customer {order['customer_id']}",
        ])
    return total
