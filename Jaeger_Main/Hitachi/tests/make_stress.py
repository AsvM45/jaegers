"""Write 149 stress cases, tests/stress_cases.json, and their expected graphs.

    python tests/make_stress.py

The mix is ordinary reports, edge cases, and overload. Every case is checked with the rule
reader before it is stored, and the answer key is computed from the company tables.

    normal   74   one clear delay, outage, quality hold, noise note, or rumor
    edge     45   plurals, a one-letter plant typo, a restart day, a single-day outage,
                  a rumor after a real hold, an unknown lot, a part with no window,
                  inverted ETAs, an impossible date, and "no delay expected"
    overload 30   every plant down at once, three incidents in one note, a real report
                  buried under filler, and the same outage repeated six times
"""

from __future__ import annotations

import json
import os
import random
import sys
from datetime import date

HERE = os.path.dirname(os.path.abspath(__file__))
HITACHI = os.path.dirname(HERE)
for path in (HITACHI, HERE):
    if path not in sys.path:
        sys.path.insert(0, path)

from enterprise import date_to_idx, idx_to_date  # noqa: E402
from make_cases import World  # noqa: E402
from make_holdout import expected_graph  # noqa: E402
from tower.agents.understand import understand  # noqa: E402
from tower.calendar_util import next_working_day  # noqa: E402
from tower.graph import WorldGraph  # noqa: E402

OUT = os.path.join(HERE, "stress_cases.json")
GRAPHS = os.path.join(HERE, "expected_graphs.json")
REAL = {"supplier_delay", "plant_outage", "quality_hold"}
NOTE = (
    "149 cases: 74 normal reports, 45 edge cases, and 30 overload messages. "
    "Answer keys come from the company tables. Wording is the kind the rule reader already accepts."
)

FILLER = [
    "Please send the new brochure PDF to the front desk.",
    "Reminder to submit timesheets before noon.",
    "The lobby flowers were replaced this morning.",
    "Can someone book the conference room for a birthday.",
    "Thanks for the update on the company picnic.",
    "Please share the org chart with the new hire.",
    "Do we have a spare monitor for the reception desk.",
    "The visitor gate by the entrance is stuck.",
    "Please welcome the interns at the morning standup.",
    "The holiday calendar for next year has been posted.",
]
RUMOR = "Unclear reports that a supplier may miss deliveries next month."


def iso(index: int) -> str:
    return idx_to_date(index).isoformat()


def numbered(lines: list[str]) -> str:
    return " ".join(f"({index}) {line}" for index, line in enumerate(lines, 1))


def delay_text(inc: dict, part: str | None = None) -> str:
    name = part or inc["part_id"]
    return (f"Voicemail from {inc['supplier_id']}: the {name} order headed to {inc['plant_id']} "
            f"is rescheduled from {inc['blocked_from']} to {inc['blocked_until']}.")


def outage_text(inc: dict, plant: str | None = None) -> str:
    name = plant or inc["plant_id"]
    return (f"Heads up: we're losing {name} for {inc['outage_start']} through {inc['outage_end']} "
            f"(a boiler failure).")


def quality_text(lot: dict) -> str:
    return (f"Please quarantine {lot['lot_id']}: seal leaks in {lot['part_id']}. "
            f"{lot['plant_id']} builds {lot['first_build_date']} through {lot['last_build_date']}.")


def quality_inc(lot: dict) -> dict:
    return {"kind": "quality_hold", "lots": [lot["lot_id"]]}


class Cursor:
    def __init__(self, rows: list):
        self.rows = rows
        self.index = 0

    def take(self):
        if self.index >= len(self.rows):
            raise RuntimeError("ran out of source records")
        row = self.rows[self.index]
        self.index += 1
        return row


def collect_delays(world: World) -> list[dict]:
    found = []
    seen = set()
    for shipment in world.shipments:
        try:
            eta = date_to_idx(date.fromisoformat(shipment["eta_date"]))
        except ValueError:
            continue
        if not 1 <= eta <= 14:
            continue
        for extra in (1, 2, 3, 4):
            new = eta + extra
            if new > 18:
                continue
            inc = {"kind": "supplier_delay", "supplier_id": shipment["supplier_id"],
                   "part_id": shipment["part_id"], "plant_id": shipment["plant_id"],
                   "blocked_from": iso(eta), "blocked_until": iso(new)}
            key = tuple(inc[name] for name in ("supplier_id", "part_id", "plant_id", "blocked_from", "blocked_until"))
            if key in seen or not world.truth.affected(inc):
                continue
            seen.add(key)
            found.append(inc)
    return found


def collect_outages(world: World) -> list[dict]:
    found = []
    for plant_id in sorted(world.plants):
        for start in range(1, 14):
            for length in (0, 1, 2, 3):
                end = start + length
                if end > 16:
                    continue
                inc = {"kind": "plant_outage", "plant_id": plant_id,
                       "outage_start": iso(start), "outage_end": iso(end)}
                if world.truth.affected(inc):
                    found.append(inc)
    return found


def collect_lots(world: World) -> list[dict]:
    return [lot for lot in world.truth.lots.values() if world.truth.lot_vehicles(lot["lot_id"])]


def agrees(graph: WorldGraph, text: str, expect: dict) -> bool:
    """The rule reader must report the same incidents the answer key names."""
    incidents = understand(graph, text)
    real = [item for item in incidents if item.kind in REAL]
    want = expect["incidents"]
    if any(item.kind == "unconfirmed" for item in incidents) != expect["escalate"]:
        return False
    if sorted(item.kind for item in real) != sorted(item["kind"] for item in want):
        return False
    if not want:
        return all(item.kind in ("noise", "unconfirmed") for item in incidents)
    unused = list(real)
    for item in want:
        match = None
        for got in unused:
            if got.kind != item["kind"]:
                continue
            if item["kind"] == "supplier_delay":
                ok = (got.supplier_id == item["supplier_id"] and got.part_id == item["part_id"]
                      and got.plant_id == item["plant_id"] and got.blocked_from == item["blocked_from"]
                      and got.blocked_until == item["blocked_until"])
            elif item["kind"] == "plant_outage":
                ok = (got.plant_id == item["plant_id"] and got.outage_start == item["outage_start"]
                      and got.outage_end == item["outage_end"])
            else:
                ok = got.lot_id in item["lots"]
            if ok:
                match = got
                break
        if match is None:
            return False
        unused.remove(match)
    return not unused


def city_typos(city: str) -> list[str]:
    if " " in city or len(city) < 6:
        return []
    return [city[:index] + city[index + 1:] for index in range(2, len(city) - 2)]


def keep(graph, cases, seen, category, source, text, expect, edge):
    if text in seen or not agrees(graph, text, expect):
        return False
    seen.add(text)
    cases.append({"category": category, "source": source, "text": text, "expect": expect, "edge": edge})
    return True



def add_ok(graph, cases, seen, category, source, text, expect, edge) -> bool:
    return keep(graph, cases, seen, category, source, text, expect, edge)


def main() -> None:
    world, graph = World(), WorldGraph()
    # The last overload loop above is easier to write correctly here than inside build.
    cases = build_clean(world, graph)
    if len(cases) != 149:
        raise SystemExit(f"expected 149 cases, built {len(cases)}")
    for index, case in enumerate(cases, 1):
        case["id"] = f"S-{index:03d}"
        if not case["edge"]:
            del case["edge"]
    note = json.dumps(NOTE, ensure_ascii=False)
    body = ",\n".join("  " + json.dumps(case, ensure_ascii=False) for case in cases)
    with open(OUT, "w", encoding="utf-8", newline="\n") as handle:
        handle.write('{"_note": ' + note + ',\n "cases": [\n' + body + "\n]}\n")
    graphs = json.load(open(GRAPHS, encoding="utf-8"))
    graphs["stress"] = {case["id"]: expected_graph(world.truth, case["expect"]) for case in cases}
    with open(GRAPHS, "w", encoding="utf-8", newline="\n") as handle:
        json.dump(graphs, handle, indent=1)
        handle.write("\n")
    bands = {}
    for case in cases:
        bands[case["category"]] = bands.get(case["category"], 0) + 1
    print(f"{len(cases)} cases -> {OUT}")
    for name, count in bands.items():
        print(f"  {name:10} {count}")


def build_clean(world: World, graph: WorldGraph) -> list[dict]:
    """Same mix as the module docstring. Overload tails are assembled without a placeholder."""
    rng = random.Random(149)
    delays, outages, lots = collect_delays(world), collect_outages(world), collect_lots(world)
    rng.shuffle(delays)
    rng.shuffle(outages)
    rng.shuffle(lots)
    delay_cursor, outage_cursor, lot_cursor = Cursor(delays), Cursor(outages), Cursor(lots)
    cases: list[dict] = []
    seen: set[str] = set()

    def add(category, source, text, expect, edge) -> None:
        if not keep(graph, cases, seen, category, source, text, expect, edge):
            raise RuntimeError(f"reader rejected a {category} case: {text[:180]}")

    for _ in range(24):
        inc = delay_cursor.take()
        add("normal", "voicemail", delay_text(inc), {"incidents": [inc], "escalate": False}, "")
    for _ in range(18):
        inc = outage_cursor.take()
        add("normal", "plant alert", outage_text(inc), {"incidents": [inc], "escalate": False}, "")
    for _ in range(16):
        lot = lot_cursor.take()
        add("normal", "quality report", quality_text(lot),
            {"incidents": [quality_inc(lot)], "escalate": False}, "")
    for index, line in enumerate(FILLER):
        add("normal", "internal memo", f"{line} Note {index + 1}.",
            {"incidents": [], "escalate": False}, "")
    for line in (
        RUMOR,
        "Heard a supplier may miss a delivery sometime soon. Not confirmed.",
        "Somebody thinks a supplier may miss a shipment. Nothing confirmed.",
        "Not sure if true, but a friend says they may run short on parts soon.",
        "Apparently freight problems are causing delays somewhere upstream. Not confirmed.",
        "Unverified report: a plant may shut a line at some point, no dates.",
    ):
        add("normal", "teams message", line, {"incidents": [], "escalate": True}, "")

    made = 0
    while made < 7:
        inc = delay_cursor.take()
        name = world.parts[inc["part_id"]]["name"]
        if name.endswith("s"):
            continue
        if add_ok(graph, cases, seen, "edge", "voicemail", delay_text(inc, name + "s"),
                  {"incidents": [inc], "escalate": False}, "edge: plural part name"):
            made += 1
    made = 0
    scanned = 0
    while made < 6:
        inc = outage_cursor.take()
        scanned += 1
        city = world.plants[inc["plant_id"]]["city"].split(",")[0]
        for typo in city_typos(city):
            if add_ok(graph, cases, seen, "edge", "plant alert", outage_text(inc, f"the {typo} plant"),
                      {"incidents": [inc], "escalate": False}, "edge: one-letter plant typo"):
                made += 1
                break
        if scanned > 80 and made < 6:
            raise RuntimeError(f"only {made} plant typos resolved")

    made = 0
    while made < 5:
        inc = outage_cursor.take()
        start = date.fromisoformat(inc["outage_start"])
        end = date.fromisoformat(inc["outage_end"])
        if start == end:
            continue
        restart = next_working_day(end)
        last = restart
        while True:
            last = date.fromordinal(last.toordinal() - 1)
            if last.weekday() < 5:
                break
        text = (f"Production at {inc['plant_id']} is suspended starting {start.isoformat()} "
                f"after a boiler failure; we expect to be back up on {restart.isoformat()}.")
        fixed = dict(inc, outage_end=last.isoformat())
        add("edge", "voicemail", text, {"incidents": [fixed], "escalate": False},
            "edge: restart day is not an outage day")
        made += 1

    for offset in range(4):
        plant_id = sorted(world.plants)[offset % len(world.plants)]
        start = iso(2 + offset)
        inc = {"kind": "plant_outage", "plant_id": plant_id, "outage_start": start, "outage_end": start}
        if not world.truth.affected(inc):
            raise RuntimeError(f"single-day outage hits nothing: {inc}")
        add("edge", "plant alert", f"{plant_id} closed {start} - {start} (a chemical spill).",
            {"incidents": [inc], "escalate": False}, "edge: single-day outage")
    for _ in range(4):
        inc = outage_cursor.take()
        add("edge", "teams message",
            f"{inc['plant_id']} closed {inc['outage_start']} - {inc['outage_end']} (a chemical spill).",
            {"incidents": [inc], "escalate": False}, "edge: plant name followed by closed")
    for _ in range(4):
        lot = lot_cursor.take()
        add("edge", "shift report",
            f"{quality_text(lot)} Separately, {RUMOR[0].lower() + RUMOR[1:]}",
            {"incidents": [quality_inc(lot)], "escalate": True}, "edge: rumor after a real hold")
    for index in range(3):
        add("edge", "quality report",
            f"Quality bulletin: lot LOT-9999 has a faulty weld. That lot is not in the book. Note {index + 1}.",
            {"incidents": [], "escalate": True}, "edge: unknown lot id")
    for index in range(3):
        add("edge", "quality report",
            f"Quality alert: the infotainment chip is faulty. Note {index + 1}.",
            {"incidents": [], "escalate": True}, "edge: part named, no plant or dates")
    for _ in range(3):
        inc = delay_cursor.take()
        text = (f"ETA change: {inc['part_id']} for {inc['plant_id']}. Was due {inc['blocked_until']}, "
                f"new ETA {inc['blocked_from']}. - {inc['supplier_id']} logistics")
        add("edge", "supplier portal", text, {"incidents": [], "escalate": True}, "edge: inverted ETAs")
    for index in range(3):
        add("edge", "quality report",
            f"QA hold: lot LOT-0191, builds March 32 through March 33. Issue: seal leaks. Note {index + 1}.",
            {"incidents": [], "escalate": True}, "edge: impossible calendar date")
    for index in range(3):
        add("edge", "email",
            "Volt says the heavy-duty wiring harness to the Texas plant. No delay expected. "
            f"Original drop 2027-03-09, new ETA 2027-03-16. Note {index + 1}.",
            {"incidents": [], "escalate": False}, "edge: explicit non-event")

    plants = sorted(world.plants)
    for start in range(1, 9):
        begin, end = iso(start), iso(start + 2)
        incidents = [{"kind": "plant_outage", "plant_id": plant_id, "outage_start": begin, "outage_end": end}
                     for plant_id in plants]
        add("overload", "plant alert", numbered([outage_text(inc) for inc in incidents]),
            {"incidents": incidents, "escalate": False},
            "overload: every plant down for the same three days")

    for _ in range(8):
        used = set()
        outage = outage_cursor.take()
        while outage["plant_id"] in used:
            outage = outage_cursor.take()
        used.add(outage["plant_id"])
        delay = delay_cursor.take()
        while delay["plant_id"] in used:
            delay = delay_cursor.take()
        used.add(delay["plant_id"])
        lot = lot_cursor.take()
        while lot["plant_id"] in used:
            lot = lot_cursor.take()
        add("overload", "shift report",
            numbered([outage_text(outage), delay_text(delay), quality_text(lot)]),
            {"incidents": [outage, delay, quality_inc(lot)], "escalate": False},
            "overload: outage, delay, and quality hold in one note")

    for _ in range(6):
        inc = delay_cursor.take()
        add("overload", "daily summary", numbered(FILLER[:6] + [delay_text(inc)]),
            {"incidents": [inc], "escalate": False},
            "overload: a delay buried under six unrelated notes")

    for _ in range(4):
        inc = outage_cursor.take()
        add("overload", "plant alert", numbered([outage_text(inc)] * 6),
            {"incidents": [dict(inc) for _copy in range(6)], "escalate": False},
            "overload: the same outage repeated six times")

    for _ in range(4):
        outage = outage_cursor.take()
        delay = delay_cursor.take()
        while delay["plant_id"] == outage["plant_id"]:
            delay = delay_cursor.take()
        add("overload", "daily summary",
            numbered(FILLER[:4] + [outage_text(outage), delay_text(delay)]),
            {"incidents": [outage, delay], "escalate": False},
            "overload: filler, an outage, and a delay")
    return cases


if __name__ == "__main__":
    main()
