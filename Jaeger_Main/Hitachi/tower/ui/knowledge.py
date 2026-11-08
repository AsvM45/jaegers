"""Knowledge-graph data for the orb graph viewer (orb-graph/public), as {nodes, links}.

Three views, chosen with ?view= on /api/knowledge_graph:

    network   every supplier, part, model, plant and dealer, and how they connect (default)
    schema    the 11 node types and 16 edge types of the ontology, sized by record count
    event     the records one event's graph paths touched (&event=E-01), read from the run traces

The full record graph has about 17,000 nodes, too many to lay out in a browser, so the network
view keeps the entities the agents reason about and leaves out orders, customers and vehicles.
"""

from __future__ import annotations

import csv
import json
import os
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
HITACHI = os.path.abspath(os.path.join(HERE, "..", ".."))
DATA = os.path.join(HITACHI, "Data", "hack_the_highway_package", "data")

# One fixed color per node type, shared by all three views.
COLORS = {
    "Supplier": "#ffb02e", "Part": "#2fd8ff", "Model": "#9b7bff", "Plant": "#5cff9d",
    "Dealer": "#ff4fd0", "Shipment": "#ff8a3d", "Lot": "#ff6b57", "ProductionOrder": "#4f8bff",
    "CustomerOrder": "#3ee0c0", "Customer": "#c7d2ff", "Vehicle": "#f5e15c",
}
EVENT_NODE_CAP = 400

_network = None


def _rows(name: str) -> list[dict]:
    with open(os.path.join(DATA, name), newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def network() -> dict:
    """Suppliers, parts, models, plants and dealers. Built once; the CSVs do not change."""
    global _network
    if _network is not None:
        return _network
    nodes, links, seen = [], [], set()

    def node(kind, key, label, detail):
        nodes.append({"id": f"{kind} {key}", "type": kind, "label": label, "detail": detail})

    def link(a, b, rel):
        k = (a, b, rel)
        if k not in seen:
            seen.add(k)
            links.append({"source": a, "target": b, "relation": rel})

    for r in _rows("suppliers.csv"):
        node("Supplier", r["supplier_id"], r["supplier_id"], f'{r["name"]}, {r["city"]}')
    for r in _rows("parts.csv"):
        node("Part", r["part_id"], r["part_id"], r["name"])
    for r in _rows("models.csv"):
        node("Model", r["model"], r["model"], f'{r["segment"]} model')
    for r in _rows("plants.csv"):
        node("Plant", r["plant_id"], r["plant_id"], f'{r["name"]}, {r["slots_per_day"]} slots a day')
    for r in _rows("dealers.csv"):
        node("Dealer", r["dealer_id"], r["dealer_id"], f'{r["name"]}, {r["city"]}')

    for r in _rows("bom.csv"):
        link(f'Part {r["part_id"]}', f'Model {r["model"]}', "USED_IN")
    for r in _rows("plant_models.csv"):
        link(f'Plant {r["plant_id"]}', f'Model {r["model"]}', "CAN_BUILD")
    for r in _rows("inbound_shipments.csv"):
        link(f'Supplier {r["supplier_id"]}', f'Part {r["part_id"]}', "SUPPLIES")
    # Each dealer links to the one plant that builds most of its orders. Linking every plant a
    # dealer has ever bought from ties all 50 dealers to every plant and piles them into one ball.
    po_plant = {r["production_order_id"]: r["plant_id"] for r in _rows("production_orders.csv")}
    by_dealer: dict[str, Counter] = {}
    for r in _rows("customer_orders.csv"):
        plant = po_plant.get(r["production_order_id"])
        if plant:
            by_dealer.setdefault(r["dealer_id"], Counter())[plant] += 1
    for dealer, plants in sorted(by_dealer.items()):
        plant, orders = plants.most_common(1)[0]
        link(f"Plant {plant}", f"Dealer {dealer}", "MAIN_PLANT")
        for n in nodes:
            if n["id"] == f"Dealer {dealer}":
                n["detail"] += f" · {orders} of {sum(plants.values())} orders from {plant}"

    # Wider spacing than the viewer's default: 100 orbs with hubs need room to read.
    _network = {"title": "Company network", "colors": COLORS, "nodes": nodes, "links": links,
                "layout": {"charge": 2.6, "distance": 1.6, "gravity": 0.5}}
    return _network


def schema(onto: dict) -> dict:
    """The ontology itself: one orb per node type, one link per edge type."""
    return {
        "title": "Ontology schema",
        "colors": COLORS,
        "nodes": [{"id": n["type"], "type": n["type"], "label": n["type"],
                   "detail": f'{n["count"]:,} records in {n["table"]}'} for n in onto["nodes"]],
        "links": [{"source": e["from"], "target": e["to"], "relation": e["relation"]} for e in onto["edges"]],
        "layout": {"charge": 2.0, "distance": 1.8},
    }


def event(traces_path: str, event_id: str) -> dict:
    """The records on one event's graph paths, capped at EVENT_NODE_CAP orbs."""
    traces = []
    if os.path.isfile(traces_path):
        with open(traces_path, encoding="utf-8") as handle:
            traces = json.load(handle)
    trace = next((t for t in traces if t.get("event_id") == event_id), None)
    title = f"{event_id} graph paths"
    if trace is None:
        return {"title": title, "colors": COLORS, "nodes": [], "links": []}

    ids, links, seen, truncated = {}, [], set(), False
    for result in trace.get("results", []):
        for path in result.get("graph_paths", []):
            # "Dealer D18 / Customer C6387" is two records at the end of one path.
            steps = []
            for step in path:
                steps.extend(s.strip() for s in str(step).split(" / "))
            steps = [s.replace(" (BOM)", "") for s in steps if " " in s]
            new = [s for s in steps if s not in ids]
            if len(ids) + len(new) > EVENT_NODE_CAP:
                truncated = True
                break
            for s in new:
                ids[s] = s.split(" ", 1)[0]
            # A trailing Dealer/Customer pair both hang off the step before them.
            for i in range(1, len(steps)):
                a = steps[i - 1]
                if a.split(" ", 1)[0] == "Dealer" and steps[i].startswith("Customer "):
                    a = steps[i - 2] if i >= 2 else a
                k = tuple(sorted((a, steps[i])))
                if a != steps[i] and k not in seen:
                    seen.add(k)
                    links.append({"source": a, "target": steps[i]})
        if truncated:
            break
    counts = Counter(ids.values())
    return {
        "title": title + (f" (first {len(ids)} records)" if truncated else ""),
        "colors": COLORS,
        "nodes": [{"id": s, "type": kind, "label": s.split(" ", 1)[1], "detail": kind} for s, kind in ids.items()],
        "links": links,
        "counts": dict(counts),
        "layout": {"charge": 1.8, "distance": 1.3, "gravity": 0.6},
    }
