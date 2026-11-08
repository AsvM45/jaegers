"""Read-only lookup tools the reader model can call when a message leaves something out.

Two tools, kept few on purpose so a small model can use them:

    search_records(text)                         fuzzy name search: plants, parts, suppliers, lots, shipments
    lookup(what, part, plant, supplier, date_from, date_to)
        what = "shipments"       inbound shipments (supplier, part, plant, due date)
               "lots"            part lots (supplier, part, plant, build window)
               "plants_building" plants whose models use a part
               "orders"          how many production orders a plant has on those days

They only read the company tables through WorldGraph. Nothing they return is acted on directly:
records and dates they find become extra options for the model's final pick, and code checks
that pick like any other.
"""

from __future__ import annotations

import difflib
import json

SCHEMAS = [
    {"type": "function", "function": {
        "name": "search_records",
        "description": "Find plants, parts, suppliers, lots or shipments whose name, nickname or id looks like the text (typos are fine).",
        "parameters": {"type": "object", "properties": {"text": {"type": "string"}}, "required": ["text"]},
    }},
    {"type": "function", "function": {
        "name": "lookup",
        "description": ("Look up company records. what: 'shipments' (due dates of inbound parts), 'lots' (part lots and "
                        "their build dates), 'plants_building' (plants that use a part), 'orders' (production at a plant "
                        "on some days). Give ids where you know them (from search_records); dates as YYYY-MM-DD."),
        "parameters": {"type": "object", "properties": {
            "what": {"type": "string", "enum": ["shipments", "lots", "plants_building", "orders"]},
            "part": {"type": "string"}, "plant": {"type": "string"}, "supplier": {"type": "string"},
            "date_from": {"type": "string"}, "date_to": {"type": "string"},
        }, "required": ["what"]},
    }},
]

_KEEP = 8  # rows returned per call, so answers stay short for a small model


class Lookups:
    """Executes tool calls against the graph and remembers every record and date it returned."""

    def __init__(self, graph, section: str = "", grounded: set[str] | None = None):
        self.graph = graph
        # Only results tied to the message count: a name search for words that are in the message,
        # or a lookup filtered by a record the message names (or a search of it found).
        self.section = section.casefold()
        self.grounded: set[str] = set(grounded or ())
        self.records: dict[str, str] = {}   # entity id -> entity type, for every record a tool returned
        self.dates: set[str] = set()        # ISO dates a tool returned (due dates, build windows)
        self.log: list[str] = []            # one line per call, for the trace

    def call(self, name: str, args: dict) -> str:
        try:
            out = self.search_records(**args) if name == "search_records" else self.lookup(**args)
        except TypeError as exc:
            out = {"error": f"bad arguments: {exc}"}
        text = json.dumps(out)
        self.log.append(f"{name}({', '.join(f'{k}={v}' for k, v in args.items() if v)}) -> "
                        f"{len(out.get('rows', [])) if isinstance(out, dict) else 0} rows")
        return text

    def _id(self, value: str | None, entity_type: str) -> str | None:
        """Accept an id or a name for a record; return its id."""
        if not value:
            return None
        table = {"plant": self.graph.plants, "part": self.graph.parts, "supplier": self.graph.suppliers}.get(entity_type, {})
        if value in table:
            return value
        hit = self.graph._alias_map.get(value.casefold())
        if hit and hit[0] == entity_type:
            return hit[1]
        return value

    def search_records(self, text: str) -> dict:
        names = self.graph._alias_map
        close = difflib.get_close_matches(text.casefold(), list(names), n=_KEEP, cutoff=0.6)
        in_message = bool(text.strip()) and text.casefold().strip() in self.section
        rows, seen = [], set()
        for alias in close:
            etype, eid = names[alias]
            if (etype, eid) in seen:
                continue
            seen.add((etype, eid))
            if in_message:
                self.records[eid] = etype
                self.grounded.add(eid)
            rows.append({"type": etype, "id": eid, "matched": alias})
        if not in_message:
            return {"rows": rows, "note": "the searched text is not in the message, so these are not used"}
        return {"rows": rows}

    def lookup(self, what: str, part: str = "", plant: str = "", supplier: str = "",
               date_from: str = "", date_to: str = "") -> dict:
        g = self.graph
        part_id, plant_id, supplier_id = self._id(part, "part"), self._id(plant, "plant"), self._id(supplier, "supplier")
        if not ({part_id, plant_id, supplier_id} & self.grounded):
            return {"rows": [], "note": "filter by a plant, part or supplier the message names (search_records finds them)"}
        rows = []
        if what == "shipments":
            for r in g.find_shipments(supplier_id, part_id, plant_id):
                if date_from and r["eta_date"] < date_from or date_to and r["eta_date"] > date_to:
                    continue
                rows.append({k: r[k] for k in ("shipment_id", "supplier_id", "part_id", "plant_id", "eta_date")})
                self.records[r["shipment_id"]] = "shipment"
                self.dates.add(r["eta_date"])
        elif what == "lots":
            both = bool(date_from and date_to)
            for r in g.find_lots(supplier_id, part_id, plant_id, date_from if both else None, date_to if both else None):
                rows.append({k: r[k] for k in ("lot_id", "supplier_id", "part_id", "plant_id", "first_build_date", "last_build_date")})
                self.records[r["lot_id"]] = "lot"
                self.dates.update((r["first_build_date"], r["last_build_date"]))
        elif what == "plants_building":
            plants = sorted({p for m in g.models_by_part.get(part_id or "", ()) for p in g.plants_for_model(m)})
            rows = [{"plant_id": p, "name": g.plants[p]["name"]} for p in plants]
            for p in plants:
                self.records[p] = "plant"
        elif what == "orders":
            orders = g.affected_orders_outage(plant_id, date_from, date_to or date_from) if plant_id and date_from else []
            rows = [{"plant_id": plant_id, "production_orders": len(orders)}]
        for row in rows:
            for key, etype in (("plant_id", "plant"), ("part_id", "part"), ("supplier_id", "supplier")):
                if row.get(key):
                    self.records.setdefault(row[key], etype)
        more = max(0, len(rows) - _KEEP)
        return {"rows": rows[:_KEEP], **({"more": more} if more else {})}
