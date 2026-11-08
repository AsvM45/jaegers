"""Build runs/tests/viewer.html: a self-contained page for browsing test results.

    python tests/build_viewer.py      # run_cases.py also calls this at the end

Reads tests/cases.json and every runs/tests/<run>/ folder that has results.json,
traces.json and action_log.jsonl. Each event's graph paths are merged into one
layered graph (nodes typed by entity, tagged with the actions taken on them),
and entity details are looked up from the CSVs. The page itself is
web/public/tests.html; web/server.js serves it at /tests.
"""

from __future__ import annotations

import csv
import json
import os
import re
from collections import defaultdict

HITACHI = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(HITACHI, "runs", "tests")
DATA = os.path.join(HITACHI, "Data", "hack_the_highway_package", "data")
TYPES = ["Shipment", "Lot", "Part", "Supplier", "Model", "Plant", "ProductionOrder",
         "CustomerOrder", "Vehicle", "Dealer", "Customer"]
_NODE = re.compile(r"^(%s) (\S+)" % "|".join(TYPES))


def _rd(name):
    with open(os.path.join(DATA, name), newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _md(iso: str) -> str:
    return iso[5:] if iso else ""


class Entities:
    """Human-readable details for every node type, from the CSVs."""

    def __init__(self):
        key = lambda rows, k: {r[k]: r for r in rows}
        self.shipments = key(_rd("inbound_shipments.csv"), "shipment_id")
        self.lots = key(_rd("part_lots.csv"), "lot_id")
        self.parts = key(_rd("parts.csv"), "part_id")
        self.suppliers = key(_rd("suppliers.csv"), "supplier_id")
        self.models = key(_rd("models.csv"), "model")
        self.plants = key(_rd("plants.csv"), "plant_id")
        self.orders = key(_rd("production_orders.csv"), "production_order_id")
        self.cos = key(_rd("customer_orders.csv"), "customer_order_id")
        self.vehicles = key(_rd("finished_vehicles.csv"), "vin")
        self.dealers = key(_rd("dealers.csv"), "dealer_id")
        self.customers = key(_rd("customers.csv"), "customer_id")
        self.pool = {r["dealer_id"]: r["loaners_available"] for r in _rd("loaners.csv")}
        self.out: dict[str, dict] = {}

    def _name(self, table, k, field="name"):
        row = table.get(k)
        return row[field] if row else k

    def get(self, typ: str, eid: str) -> dict:
        """Return {sub, rows} for a node: a short subtitle and inspector rows."""
        k = f"{typ}:{eid}"
        if k in self.out:
            return self.out[k]
        sub, rows = "", []
        if typ == "Shipment" and eid in self.shipments:
            s = self.shipments[eid]
            sub = f"ETA {_md(s['eta_date'])}"
            rows = [("Supplier", f"{self._name(self.suppliers, s['supplier_id'])} ({s['supplier_id']})"),
                    ("Part", s["part_id"]), ("Plant", s["plant_id"]), ("Planned ETA", s["eta_date"]),
                    ("Covers", f"{s['covers_days']} days")]
        elif typ == "Lot" and eid in self.lots:
            s = self.lots[eid]
            sub = f"{_md(s['first_build_date'])} – {_md(s['last_build_date'])}"
            rows = [("Part", s["part_id"]), ("Supplier", s["supplier_id"]), ("Plant", s["plant_id"]),
                    ("Builds", f"{s['first_build_date']} → {s['last_build_date']}")]
        elif typ == "Part" and eid in self.parts:
            p = self.parts[eid]
            sub = p["name"]
            rows = [("Name", p["name"]), ("Category", p["category"])]
        elif typ == "Supplier" and eid in self.suppliers:
            s = self.suppliers[eid]
            sub = s["name"]
            rows = [("Name", s["name"]), ("City", s["city"])]
        elif typ == "Model" and eid in self.models:
            sub = self.models[eid]["segment"]
            rows = [("Segment", sub)]
        elif typ == "Plant" and eid in self.plants:
            p = self.plants[eid]
            sub = p["city"]
            rows = [("Name", p["name"]), ("City", p["city"]), ("Slots / day", p["slots_per_day"])]
        elif typ == "ProductionOrder" and eid in self.orders:
            o = self.orders[eid]
            sub = f"{o['model'].title()} · {_md(o['build_date'])}"
            rows = [("Model", o["model"]), ("Plant", o["plant_id"]), ("Build date", o["build_date"]),
                    ("Units", o["units"])]
        elif typ == "CustomerOrder" and eid in self.cos:
            c = self.cos[eid]
            cust = self.customers.get(c["customer_id"], {})
            sub = f"{cust.get('tier', '')} · due {_md(c['promised_date'])}"
            rows = [("Customer", f"{cust.get('name', '')} ({c['customer_id']})"), ("Tier", cust.get("tier", "")),
                    ("Dealer", c["dealer_id"]), ("Model", c["model"]), ("Promised", c["promised_date"]),
                    ("Production order", c["production_order_id"])]
        elif typ == "Vehicle" and eid in self.vehicles:
            v = self.vehicles[eid]
            sub = "sold" if v["status"] == "sold" else "in stock"
            rows = [("Model", v["model"]), ("Plant", v["plant_id"]), ("Built", v["build_date"]),
                    ("Dealer", v["dealer_id"]), ("Status", v["status"])]
            if v["customer_id"]:
                rows.append(("Owner", v["customer_id"]))
        elif typ == "Dealer" and eid in self.dealers:
            d = self.dealers[eid]
            sub = d["city"]
            rows = [("Name", d["name"]), ("City", d["city"]), ("Region", d["region"]),
                    ("Loaner pool", self.pool.get(eid, "0"))]
        elif typ == "Customer" and eid in self.customers:
            c = self.customers[eid]
            sub = c["tier"]
            rows = [("Name", c["name"]), ("Tier", c["tier"])]
        self.out[k] = {"sub": sub, "rows": rows}
        return self.out[k]


def _parse(el: str):
    """'Dealer D20 / Customer C6723' -> [('Dealer','D20'), ('Customer','C6723')]."""
    found = []
    for part in el.split(" / "):
        m = _NODE.match(part.strip())
        if m:
            found.append((m.group(1), m.group(2)))
    return found


def _tags(calls) -> dict[str, list[list[str]]]:
    """Actions taken on each node, keyed 'Type:ID'. Each tag is [text, kind]."""
    tags = defaultdict(list)
    for c in calls:
        if not c["ok"]:
            continue
        a, t = c["args"], c["tool"]
        if t == "mes.reschedule":
            tags[f"ProductionOrder:{a['production_order_id']}"].append([f"moved → {_md(a['new_date'])}", "move"])
        elif t == "mes.transfer":
            tags[f"ProductionOrder:{a['production_order_id']}"].append(
                [f"→ {a['to_plant_id']} {_md(a['new_date'])}", "transfer"])
        elif t == "dealer.notify":
            tags[f"Dealer:{a['dealer_id']}"].append([f"notified ×{len(a['customer_order_ids'])}", "notify"])
            for co in a["customer_order_ids"]:
                tags[f"CustomerOrder:{co}"].append(["dealer told", "notify"])
        elif t == "crm.assign_loaner":
            tags[f"CustomerOrder:{a['customer_order_id']}"].append(["loaner", "loaner"])
        elif t == "dealer.stop_sale":
            tags[f"Dealer:{a['dealer_id']}"].append([f"stop-sale ×{len(a['vins'])}", "stop"])
            for v in a["vins"]:
                tags[f"Vehicle:{v}"].append(["stop-sale", "stop"])
        elif t == "crm.notify_customer":
            tags[f"Customer:{a['customer_id']}"].append(["contacted", "notify"])
        elif t == "quality.hold_lot":
            tags[f"Lot:{a['lot_id']}"].append(["held", "stop"])
    order = {"transfer": 0, "move": 1, "loaner": 2, "stop": 3, "notify": 4}
    for v in tags.values():
        v.sort(key=lambda t: order.get(t[1], 9))
    return tags


def _graph(trace, calls, ents: Entities) -> dict:
    """Merge every agent's paths into one graph: nodes, edges, and paths as index lists."""
    index: dict[str, int] = {}
    nodes, edges, paths, notes = [], set(), set(), []

    def node(typ, eid):
        k = f"{typ}:{eid}"
        if k not in index:
            index[k] = len(nodes)
            nodes.append([typ, eid])
        return index[k]

    for r in trace.get("results", []):
        notes.extend(r.get("notes", []))
        for p in r.get("graph_paths", []):
            seq = []
            for el in p:
                parsed = _parse(el)
                if not parsed:
                    continue
                if len(parsed) == 2:  # Dealer / Customer pair: both hang off the previous node
                    prev = seq[-1] if seq else None
                    for typ, eid in parsed:
                        i = node(typ, eid)
                        if prev is not None:
                            edges.add((prev, i))
                    seq.extend(node(t, e) for t, e in parsed)
                    continue
                typ, eid = parsed[0]
                i = node(typ, eid)
                if seq:
                    src = seq[-1]
                    if typ == "Customer" and nodes[src][0] == "Dealer" and len(seq) >= 2:
                        src = seq[-2]
                    edges.add((src, i))
                seq.append(i)
            if len(seq) > 1:
                paths.add(tuple(seq))
    tags = _tags(calls)
    out_nodes = []
    for typ, eid in nodes:
        info = ents.get(typ, eid)
        out_nodes.append({"t": typ, "id": eid, "sub": info["sub"], "tags": tags.get(f"{typ}:{eid}", [])})
    return {"nodes": out_nodes, "edges": sorted(edges), "paths": sorted(paths), "notes": notes}


def _run_label(folder: str) -> str:
    if folder == "rules":
        return "rules"
    return folder.removeprefix("llm_").replace("_", ":", 1)


def collect() -> dict:
    cases = json.load(open(os.path.join(HITACHI, "tests", "cases.json"), encoding="utf-8"))
    ents = Entities()
    runs = []
    for folder in sorted(os.listdir(OUT)):
        base = os.path.join(OUT, folder)
        files = [os.path.join(base, n) for n in ("results.json", "traces.json", "action_log.jsonl")]
        if not all(os.path.isfile(f) for f in files):
            continue
        results = {r["id"]: r for r in json.load(open(files[0], encoding="utf-8"))}
        traces = {t["event_id"]: t for t in json.load(open(files[1], encoding="utf-8"))}
        log = defaultdict(list)
        for line in open(files[2], encoding="utf-8"):
            if line.strip():
                row = json.loads(line)
                log[row["event_id"]].append(row)
        per_case = {}
        for case in cases:
            cid = case["id"]
            res, trace = results.get(cid), traces.get(cid, {})
            if res is None:
                continue
            rows = log.get(cid, [])
            calls = []
            for i, call in enumerate(trace.get("calls", [])):
                row = rows[i] if i < len(rows) else {}
                calls.append({"tool": call["tool"], "args": call["args"], "reason": call.get("reason", ""),
                              "ok": row.get("ok", True), "error": row.get("error")})
            incidents = [{k: v for k, v in inc.items() if v not in (None, [], "")}
                         for inc in trace.get("incidents", [])]
            per_case[cid] = {**res, "incidents": incidents, "calls": calls,
                             "graph": _graph(trace, calls, ents),
                             "agents": [{"agent": r.get("agent"), "affected": len(r.get("affected_ids", [])),
                                         "paths": len(r.get("graph_paths", []))} for r in trace.get("results", [])]}
        runs.append({"key": folder, "label": _run_label(folder), "cases": per_case})
    runs.sort(key=lambda r: (r["key"] != "rules", r["key"]))
    return {"cases": cases, "runs": runs, "entities": ents.out}


def build() -> str:
    """Write runs/tests/viewer_data.json (served by web/server.js at /api/tests) and
    runs/tests/viewer.html (the same page with the data embedded, for opening offline)."""
    payload = json.dumps(collect(), separators=(",", ":"))
    with open(os.path.join(OUT, "viewer_data.json"), "w", encoding="utf-8") as f:
        f.write(payload)
    with open(TEMPLATE, encoding="utf-8") as f:
        html = f.read().replace("__DATA__", payload.replace("</", "<\\/"))
    path = os.path.join(OUT, "viewer.html")
    with open(path, "w", encoding="utf-8") as f:
        f.write(html)
    return path


TEMPLATE = os.path.join(HITACHI, "web", "public", "tests.html")

if __name__ == "__main__":
    print(build())
