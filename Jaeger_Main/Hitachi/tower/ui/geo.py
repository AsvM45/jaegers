"""Where the company is: every plant, supplier and dealer with its city's location, for the Overview map.

The company tables give a city for each; this file gives each city's latitude and longitude.
GET /api/network_map returns {plants, suppliers, dealers}, each a list of
{id, name, city, lat, lon}.
"""

from __future__ import annotations

import csv
import os

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "..", "..", "Data", "hack_the_highway_package", "data")

# (latitude, longitude) of every city in plants.csv, suppliers.csv and dealers.csv.
CITY = {
    "Akron, OH": (41.08, -81.52), "Amarillo, TX": (35.22, -101.83), "Asheville, NC": (35.60, -82.55),
    "Atlanta, GA": (33.75, -84.39), "Austin, TX": (30.27, -97.74), "Baton Rouge, LA": (30.45, -91.15),
    "Birmingham, AL": (33.52, -86.80), "Bowling Green, KY": (36.99, -86.44), "Charleston, SC": (32.78, -79.93),
    "Charlotte, NC": (35.23, -80.84), "Chattanooga, TN": (35.05, -85.31), "Cincinnati, OH": (39.10, -84.51),
    "Columbia, SC": (34.00, -81.03), "Columbus, OH": (39.96, -83.00), "Corpus Christi, TX": (27.80, -97.40),
    "Dayton, OH": (39.76, -84.19), "Detroit, MI": (42.33, -83.05), "El Paso, TX": (31.76, -106.49),
    "Evansville, IN": (37.97, -87.57), "Fayetteville, AR": (36.06, -94.16), "Fort Wayne, IN": (41.08, -85.14),
    "Fremont, CA": (37.55, -121.99), "Greensboro, NC": (36.07, -79.79), "Greenville, SC": (34.85, -82.40),
    "Houston, TX": (29.76, -95.37), "Huntsville, AL": (34.73, -86.59), "Indianapolis, IN": (39.77, -86.16),
    "Jackson, MS": (32.30, -90.18), "Jacksonville, FL": (30.33, -81.66), "Jonesboro, AR": (35.84, -90.70),
    "Kerrville, TX": (30.05, -99.14), "Knoxville, TN": (35.96, -83.92), "Lafayette, LA": (30.22, -92.02),
    "Lexington, KY": (38.04, -84.50), "Little Rock, AR": (34.75, -92.29), "Louisville, KY": (38.25, -85.76),
    "Lubbock, TX": (33.58, -101.86), "Macon, GA": (32.84, -83.63), "McAllen, TX": (26.20, -98.23),
    "Memphis, TN": (35.15, -90.05), "Mobile, AL": (30.69, -88.04), "Monterrey, MX": (25.69, -100.32),
    "Montgomery, AL": (32.37, -86.30), "Nashville, TN": (36.16, -86.78), "New Orleans, LA": (29.95, -90.07),
    "Oklahoma City, OK": (35.47, -97.52), "Pensacola, FL": (30.42, -87.22), "Phoenix, AZ": (33.45, -112.07),
    "Princeton, IN": (38.36, -87.57), "Raleigh, NC": (35.78, -78.64), "Reno, NV": (39.53, -119.81),
    "Roanoke, VA": (37.27, -79.94), "San Antonio, TX": (29.42, -98.49), "San Jose, CA": (37.34, -121.89),
    "Shreveport, LA": (32.53, -93.75), "Springfield, MO": (37.21, -93.29), "St. Louis, MO": (38.63, -90.20),
    "Toledo, OH": (41.65, -83.54), "Tulsa, OK": (36.15, -95.99), "Tupelo, MS": (34.26, -88.70),
    "Tyler, TX": (32.35, -95.30),
}

_cache: dict | None = None


def _rows(name: str, key: str) -> list[dict]:
    out = []
    with open(os.path.join(DATA, name), newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            where = CITY.get(row["city"])
            if where:
                out.append({"id": row[key], "name": row["name"], "city": row["city"], "lat": where[0], "lon": where[1]})
    return out


def payload() -> dict:
    """Plants, suppliers and dealers with their locations. The tables do not change: built once."""
    global _cache
    if _cache is None:
        _cache = {
            "plants": _rows("plants.csv", "plant_id"),
            "suppliers": _rows("suppliers.csv", "supplier_id"),
            "dealers": _rows("dealers.csv", "dealer_id"),
        }
    return _cache
