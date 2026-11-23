"""The company records page: the tables an event names, read-only, a page at a time.

    GET /api/records                         every table: id, row count, columns
    GET /api/records/<table>?q=&offset=&limit=   one page of rows (q matches any column, any case)

Visitors read these to write their own test messages on Add events (a supplier and a shipment for a
delay, a plant for an outage, a lot for a quality hold). The CSVs are read once and kept in memory;
the largest table (customers) is 7,000 rows. Nothing here writes.
"""

from __future__ import annotations

import csv
import os
import threading

HERE = os.path.dirname(os.path.abspath(__file__))
HITACHI = os.path.abspath(os.path.join(HERE, "..", ".."))
DATA = os.path.join(HITACHI, "Data", "hack_the_highway_package", "data")

# The tables shown, in the page's order. Anything else in the data folder is not served.
TABLES = ["suppliers", "plants", "parts", "inbound_shipments", "part_lots", "dealers",
          "production_orders", "customer_orders", "finished_vehicles", "customers"]
MAX_LIMIT = 100

_cache: dict[str, tuple[list[str], list[list[str]]]] = {}
_lock = threading.Lock()


def _load(table: str) -> tuple[list[str], list[list[str]]]:
    with _lock:
        if table not in _cache:
            with open(os.path.join(DATA, f"{table}.csv"), encoding="utf-8", newline="") as handle:
                rows = list(csv.reader(handle))
            _cache[table] = (rows[0] if rows else [], rows[1:])
        return _cache[table]


def tables() -> list[dict]:
    out = []
    for table in TABLES:
        columns, rows = _load(table)
        out.append({"id": table, "rows": len(rows), "columns": columns})
    return out


def page(table: str, q: str = "", offset: int = 0, limit: int = 25) -> dict:
    """One page of a table. KeyError when the table is not one of TABLES."""
    if table not in TABLES:
        raise KeyError(table)
    columns, rows = _load(table)
    needle = q.strip().lower()
    if needle:
        rows = [r for r in rows if any(needle in cell.lower() for cell in r)]
    limit = max(1, min(MAX_LIMIT, limit))
    offset = max(0, offset)
    return {"id": table, "columns": columns, "total": len(rows), "offset": offset, "limit": limit,
            "rows": rows[offset:offset + limit]}
