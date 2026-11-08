# Wacky Wheels ontology

Exported by `python -m tower.ontology` from the company CSVs, which are the same tables `tower/graph.py` loads. Counts are records in the tables.

```mermaid
flowchart LR
    Supplier["Supplier<br/>18"]
    Part["Part<br/>20"]
    Model["Model<br/>6"]
    Plant["Plant<br/>6"]
    Shipment["Shipment<br/>364"]
    Lot["Lot<br/>364"]
    ProductionOrder["ProductionOrder<br/>540"]
    CustomerOrder["CustomerOrder<br/>3,263"]
    Customer["Customer<br/>7,000"]
    Dealer["Dealer<br/>50"]
    Vehicle["Vehicle<br/>5,348"]
    Shipment -->|SUPPLIED_BY| Supplier
    Shipment -->|CARRIES| Part
    Shipment -->|DELIVERS_TO| Plant
    Part -->|USED_IN (BOM)| Model
    Plant -->|CAN_BUILD| Model
    ProductionOrder -->|SCHEDULED_AT| Plant
    ProductionOrder -->|BUILDS| Model
    CustomerOrder -->|FILLED_BY| ProductionOrder
    CustomerOrder -->|PLACED_BY| Customer
    CustomerOrder -->|SOLD_THROUGH| Dealer
    Lot -->|OF_PART| Part
    Lot -->|FROM_SUPPLIER| Supplier
    Lot -->|USED_AT| Plant
    Vehicle -->|BUILT_BY| ProductionOrder
    Vehicle -->|AT_DEALER| Dealer
    Vehicle -->|OWNED_BY| Customer
```

## Node types

| Type | Table | Id | Records | Attributes |
|---|---|---|---|---|
| Supplier | `suppliers.csv` | `supplier_id` | 18 | name, city |
| Part | `parts.csv` | `part_id` | 20 | name, category |
| Model | `models.csv` | `model` | 6 | segment |
| Plant | `plants.csv` | `plant_id` | 6 | name, city, slots_per_day |
| Shipment | `inbound_shipments.csv` | `shipment_id` | 364 | supplier_id, part_id, plant_id, eta_date, covers_days |
| Lot | `part_lots.csv` | `lot_id` | 364 | part_id, supplier_id, plant_id, first_build_date, last_build_date |
| ProductionOrder | `production_orders.csv` | `production_order_id` | 540 | plant_id, build_date, model, units |
| CustomerOrder | `customer_orders.csv` | `customer_order_id` | 3,263 | production_order_id, dealer_id, customer_id, model, promised_date |
| Customer | `customers.csv` | `customer_id` | 7,000 | name, tier |
| Dealer | `dealers.csv` | `dealer_id` | 50 | name, city, region, transit_days |
| Vehicle | `finished_vehicles.csv` | `vin` | 5,348 | production_order_id, model, plant_id, build_date, dealer_id, status, customer_id |

## Edge types

| From | Relation | To | Source | Links |
|---|---|---|---|---|
| Shipment | SUPPLIED_BY | Supplier | `inbound_shipments.csv` (supplier_id) | 364 |
| Shipment | CARRIES | Part | `inbound_shipments.csv` (part_id) | 364 |
| Shipment | DELIVERS_TO | Plant | `inbound_shipments.csv` (plant_id) | 364 |
| Part | USED_IN (BOM) | Model | `bom.csv` (part_id → model) | 47 |
| Plant | CAN_BUILD | Model | `plant_models.csv` (plant_id → model) | 18 |
| ProductionOrder | SCHEDULED_AT | Plant | `production_orders.csv` (plant_id) | 540 |
| ProductionOrder | BUILDS | Model | `production_orders.csv` (model) | 540 |
| CustomerOrder | FILLED_BY | ProductionOrder | `customer_orders.csv` (production_order_id) | 3,263 |
| CustomerOrder | PLACED_BY | Customer | `customer_orders.csv` (customer_id) | 3,263 |
| CustomerOrder | SOLD_THROUGH | Dealer | `customer_orders.csv` (dealer_id) | 3,263 |
| Lot | OF_PART | Part | `part_lots.csv` (part_id) | 364 |
| Lot | FROM_SUPPLIER | Supplier | `part_lots.csv` (supplier_id) | 364 |
| Lot | USED_AT | Plant | `part_lots.csv` (plant_id) | 364 |
| Vehicle | BUILT_BY | ProductionOrder | `finished_vehicles.csv` (production_order_id) | 5,348 |
| Vehicle | AT_DEALER | Dealer | `finished_vehicles.csv` (dealer_id) | 5,348 |
| Vehicle | OWNED_BY | Customer | `finished_vehicles.csv` (customer_id) | 2,927 |

Name resolution: 61 aliases in `aliases.csv` map nicknames to part, plant, supplier ids. Official names, ids, "the"-less forms and one-letter typos of plant and supplier names are added in code.

## Traversals the agents use

- **supplier_delay**: Shipment → Part → Model (BOM) → ProductionOrder (receiving plant, blocked window) → CustomerOrder → Dealer / Customer
- **plant_outage**: Plant → ProductionOrder (outage days) → CustomerOrder → Dealer / Customer
- **quality_hold**: Lot → ProductionOrder (lot plant, lot build dates, models using the part) → Vehicle → Dealer (in stock) / Customer (sold)
- **rescheduling**: ProductionOrder → Model → Plant (CAN_BUILD) for transfers; Plant.slots_per_day for capacity
- **loaners**: CustomerOrder → Customer (tier) and Dealer (loaner pool)
