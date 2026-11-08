"""Export the control tower's ontology: node types, edge types, counts, and the traversals used.

    python -m tower.ontology            # writes runs/ontology/{ontology.json, ontology.md, ontology.dot}

Everything is computed from the company CSVs that tower/graph.py loads, so the export always
matches the graph the agents traverse. ontology.md holds a Mermaid diagram (rendered by GitHub
and most Markdown viewers); ontology.dot renders with Graphviz: dot -Tpng ontology.dot -o ontology.png
"""

from __future__ import annotations

import csv
import json
import os
import sys

_HITACHI = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _HITACHI not in sys.path:
    sys.path.insert(0, _HITACHI)

from tower.calendar_util import TODAY  # noqa: E402
from tower.graph import WorldGraph  # noqa: E402

# Node type -> (CSV file, id column).
NODES = {
    "Supplier": ("suppliers.csv", "supplier_id"),
    "Part": ("parts.csv", "part_id"),
    "Model": ("models.csv", "model"),
    "Plant": ("plants.csv", "plant_id"),
    "Shipment": ("inbound_shipments.csv", "shipment_id"),
    "Lot": ("part_lots.csv", "lot_id"),
    "ProductionOrder": ("production_orders.csv", "production_order_id"),
    "CustomerOrder": ("customer_orders.csv", "customer_order_id"),
    "Customer": ("customers.csv", "customer_id"),
    "Dealer": ("dealers.csv", "dealer_id"),
    "Vehicle": ("finished_vehicles.csv", "vin"),
}

# Edge -> (from type, relation, to type, CSV file, column holding the target id, or the
# (source column, target column) pair for a link table). Read the edge as "<from> <relation> <to>".
EDGES = [
    ("Shipment", "SUPPLIED_BY", "Supplier", "inbound_shipments.csv", "supplier_id"),
    ("Shipment", "CARRIES", "Part", "inbound_shipments.csv", "part_id"),
    ("Shipment", "DELIVERS_TO", "Plant", "inbound_shipments.csv", "plant_id"),
    ("Part", "USED_IN (BOM)", "Model", "bom.csv", ("part_id", "model")),
    ("Plant", "CAN_BUILD", "Model", "plant_models.csv", ("plant_id", "model")),
    ("ProductionOrder", "SCHEDULED_AT", "Plant", "production_orders.csv", "plant_id"),
    ("ProductionOrder", "BUILDS", "Model", "production_orders.csv", "model"),
    ("CustomerOrder", "FILLED_BY", "ProductionOrder", "customer_orders.csv", "production_order_id"),
    ("CustomerOrder", "PLACED_BY", "Customer", "customer_orders.csv", "customer_id"),
    ("CustomerOrder", "SOLD_THROUGH", "Dealer", "customer_orders.csv", "dealer_id"),
    ("Lot", "OF_PART", "Part", "part_lots.csv", "part_id"),
    ("Lot", "FROM_SUPPLIER", "Supplier", "part_lots.csv", "supplier_id"),
    ("Lot", "USED_AT", "Plant", "part_lots.csv", "plant_id"),
    ("Vehicle", "BUILT_BY", "ProductionOrder", "finished_vehicles.csv", "production_order_id"),
    ("Vehicle", "AT_DEALER", "Dealer", "finished_vehicles.csv", "dealer_id"),
    ("Vehicle", "OWNED_BY", "Customer", "finished_vehicles.csv", "customer_id"),
]

# The traversals each specialist uses, as the docx's evidence chains.
TRAVERSALS = {
    "supplier_delay": "Shipment → Part → Model (BOM) → ProductionOrder (receiving plant, blocked window) "
                      "→ CustomerOrder → Dealer / Customer",
    "plant_outage": "Plant → ProductionOrder (outage days) → CustomerOrder → Dealer / Customer",
    "quality_hold": "Lot → ProductionOrder (lot plant, lot build dates, models using the part) "
                    "→ Vehicle → Dealer (in stock) / Customer (sold)",
    "rescheduling": "ProductionOrder → Model → Plant (CAN_BUILD) for transfers; Plant.slots_per_day for capacity",
    "loaners": "CustomerOrder → Customer (tier) and Dealer (loaner pool)",
}


def _rows(data_dir: str, name: str) -> list[dict]:
    with open(os.path.join(data_dir, name), newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def build() -> dict:
    graph = WorldGraph()
    data = graph.data_dir
    nodes = []
    for node, (name, key) in NODES.items():
        rows = _rows(data, name)
        nodes.append({
            "type": node, "table": name, "id": key, "count": len(rows),
            "attributes": [c for c in rows[0] if c != key] if rows else [],
        })
    edges = []
    for src, rel, dst, name, col in EDGES:
        rows = _rows(data, name)
        field = col[1] if isinstance(col, tuple) else col
        count = sum(1 for r in rows if r.get(field))
        edges.append({"from": src, "relation": rel, "to": dst, "table": name,
                      "via": list(col) if isinstance(col, tuple) else col, "count": count})
    aliases = _rows(data, "aliases.csv")
    return {
        "today": TODAY.isoformat(),
        "nodes": nodes,
        "edges": edges,
        "aliases": {"count": len(aliases), "resolves_to": sorted({a["entity_type"] for a in aliases})},
        "traversals": TRAVERSALS,
    }


def to_mermaid(onto: dict) -> str:
    lines = ["flowchart LR"]
    for n in onto["nodes"]:
        lines.append(f'    {n["type"]}["{n["type"]}<br/>{n["count"]:,}"]')
    for e in onto["edges"]:
        lines.append(f'    {e["from"]} -->|{e["relation"]}| {e["to"]}')
    return "\n".join(lines)


def to_dot(onto: dict) -> str:
    lines = ["digraph ontology {", "  rankdir=LR;", '  node [shape=box, style=rounded, fontname="Helvetica"];']
    for n in onto["nodes"]:
        lines.append(f'  {n["type"]} [label="{n["type"]}\\n{n["count"]:,} records"];')
    for e in onto["edges"]:
        lines.append(f'  {e["from"]} -> {e["to"]} [label="{e["relation"]}", fontsize=10];')
    lines.append("}")
    return "\n".join(lines)


def to_markdown(onto: dict) -> str:
    out = [
        "# Wacky Wheels ontology",
        "",
        "Exported by `python -m tower.ontology` from the company CSVs, which are the same tables "
        "`tower/graph.py` loads. Counts are records in the tables.",
        "",
        "```mermaid",
        to_mermaid(onto),
        "```",
        "",
        "## Node types",
        "",
        "| Type | Table | Id | Records | Attributes |",
        "|---|---|---|---|---|",
    ]
    for n in onto["nodes"]:
        out.append(f'| {n["type"]} | `{n["table"]}` | `{n["id"]}` | {n["count"]:,} | {", ".join(n["attributes"])} |')
    out += ["", "## Edge types", "", "| From | Relation | To | Source | Links |", "|---|---|---|---|---|"]
    for e in onto["edges"]:
        via = " → ".join(e["via"]) if isinstance(e["via"], list) else e["via"]
        out.append(f'| {e["from"]} | {e["relation"]} | {e["to"]} | `{e["table"]}` ({via}) | {e["count"]:,} |')
    out += [
        "",
        f'Name resolution: {onto["aliases"]["count"]} aliases in `aliases.csv` map nicknames to '
        f'{", ".join(onto["aliases"]["resolves_to"])} ids. Official names, ids, "the"-less forms and '
        "one-letter typos of plant and supplier names are added in code.",
        "",
        "## Traversals the agents use",
        "",
    ]
    for kind, chain in onto["traversals"].items():
        out.append(f"- **{kind}**: {chain}")
    return "\n".join(out) + "\n"


def main() -> None:
    onto = build()
    out = os.path.join(_HITACHI, "runs", "ontology")
    os.makedirs(out, exist_ok=True)
    with open(os.path.join(out, "ontology.json"), "w", encoding="utf-8") as handle:
        json.dump(onto, handle, indent=2)
        handle.write("\n")
    with open(os.path.join(out, "ontology.md"), "w", encoding="utf-8") as handle:
        handle.write(to_markdown(onto))
    with open(os.path.join(out, "ontology.dot"), "w", encoding="utf-8") as handle:
        handle.write(to_dot(onto) + "\n")
    print(f"{len(onto['nodes'])} node types, {len(onto['edges'])} edge types -> {out}")


if __name__ == "__main__":
    main()
