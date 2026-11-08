"""Write test cases T-26..T-100 into tests/cases.json (T-01..T-25 are kept exactly as they are).

    python tests/make_cases.py            # run once; the result is stored, not regenerated per run

Each case starts from a real scenario in the company tables: a shipment whose delay really blocks
builds, a plant outage on working days that hits orders, or a lot with built vehicles; or noise,
or a rumor. The hand-written answer ("expect") comes from that scenario, computed by code. The
message text is then written in varied, human ways: ids, full names or the nicknames in
aliases.csv; ISO dates, "Mar 15" or "next Tuesday"; emails, chat, alerts and digests that
combine two items. Seeded, so the same command always writes the same 75 cases.

The expected outputs the tests are scored against are made separately, once, by the larger model
(python tests/llm_judge.py build).
"""

from __future__ import annotations

import json
import os
import random
import sys
from collections import defaultdict
from datetime import date, timedelta

HITACHI = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TESTS = os.path.join(HITACHI, "tests")
for p in (HITACHI, TESTS):
    if p not in sys.path:
        sys.path.insert(0, p)

import run_cases as rc  # noqa: E402
from enterprise import date_to_idx, idx_to_date  # noqa: E402

CASES = os.path.join(TESTS, "cases.json")
KEEP = 25            # T-01..T-25 are hand-made and stay untouched
TOTAL = 100
SEED = 26
TODAY = date(2027, 3, 8)

# How many new cases of each kind (75 in all).
MIX = {"supplier_delay": 18, "plant_outage": 16, "quality_hold": 14, "noise": 10,
       "unconfirmed": 9, "compound": 8}

NOISE = [
    ("dealer email", "Dealer {city} asks whether the spring brochure PDF has the new trim colors yet."),
    ("news wire", "Blizzard warning for Anchorage, AK through the weekend; schools closed."),
    ("internal memo", "Reminder: open enrollment for dental and vision closes Friday. Visit the HR portal."),
    ("dealer email", "Hi, could someone resend the login for the dealer marketing portal? Thanks, {city} store."),
    ("news wire", "Rival automaker announces a new electric pickup for 2029; no production details given."),
    ("internal memo", "The HQ parking garage level 2 is closed for painting this weekend."),
    ("email", "Updated price list for accessories (floor mats, roof racks) is attached. Effective April 1."),
    ("ops chat", "anyone know if the cafeteria is doing tacos again on thursday? asking for the whole team"),
    ("news wire", "Heat advisory issued for Phoenix, AZ; temperatures may reach 105 F."),
    ("dealer email", "Dealer {city} wants to know if we have posters of the new Summit model for the showroom."),
    ("internal memo", "IT will patch laptops tonight at 9 pm. Save your work before you leave."),
    ("email", "Thank-you note from the {city} dealer for the holiday gift basket."),
]
RUMORS = [
    ("ops chat", "heard from a buddy at a supplier that something might be up with {part_name}. nothing official"),
    ("phone note", "A carrier rep hinted deliveries could slip at some point. No dates, no part named, not confirmed."),
    ("ops chat", "Someone said {plant_alias} might have a problem soon? Can't confirm, no details."),
    ("dealer email", "We keep hearing rumors that some cars could be delayed. Is that true? Nobody has told us anything."),
    ("phone note", "Supplier contact thinks there may be a quality issue with a part lot, but has no lot number or dates."),
    ("ops chat", "rumor on the floor: possible shortage of something for the paint line. unverified"),
    ("email", "Unconfirmed: a trucking company might strike next month. No routes or shipments named."),
    ("ops chat", "not sure if this is real but people say {plant_alias} could lose power sometime. no dates"),
]
OUTAGE_CAUSES = ["a power failure", "a software outage on the line", "a paint-shop fire", "flooding in the body shop",
                 "a conveyor breakdown", "a compressor failure", "a robot cell crash", "a gas leak evacuation"]
DELAY_CAUSES = ["a truck breakdown", "a customs inspection", "a tooling failure", "a port backlog",
                "a quality re-check at the supplier", "a missed rail connection", "a snowstorm on the route"]
DEFECTS = ["a faulty weld", "moisture contamination", "a stitching defect", "a cracked housing",
           "a firmware fault", "loose connectors", "a bad batch of resin"]


class World:
    def __init__(self):
        self.truth = rc.Truth()
        self.plants = {r["plant_id"]: r for r in rc.rd("plants.csv")}
        self.parts = {r["part_id"]: r for r in rc.rd("parts.csv")}
        self.suppliers = {r["supplier_id"]: r for r in rc.rd("suppliers.csv")}
        self.shipments = rc.rd("inbound_shipments.csv")
        self.dealers = rc.rd("dealers.csv")
        self.aliases = defaultdict(list)
        for r in rc.rd("aliases.csv"):
            if r["alias"] not in self.aliases[r["entity_id"]]:
                self.aliases[r["entity_id"]].append(r["alias"])


# ---- ways to write names and dates

def plant_name(w: World, rng: random.Random, pid: str) -> str:
    p = w.plants[pid]
    return rng.choice([pid, p["name"], f"{p['name']} ({pid})", *w.aliases[pid]])


def part_name(w: World, rng: random.Random, part_id: str) -> str:
    p = w.parts[part_id]
    return rng.choice([part_id, p["name"], f"{p['name']} ({part_id})", *w.aliases[part_id]])


def supplier_name(w: World, rng: random.Random, sid: str) -> str:
    s = w.suppliers[sid]
    return rng.choice([s["name"], s["name"], f"{s['name']} ({sid})", *w.aliases[sid]])


def say_date(rng: random.Random, d: date, relative_ok: bool = True) -> str:
    """One way a person might write this date."""
    forms = [d.isoformat(), f"{d.strftime('%b')} {d.day}", f"{d.strftime('%A %b')} {d.day}",
             f"{d.strftime('%B')} {d.day}", f"{d.strftime('%a')} {d.month}/{d.day}"]
    monday = TODAY - timedelta(days=TODAY.weekday())
    week = (d - monday).days // 7
    if relative_ok and week in (-1, 0, 1) and d.weekday() < 5:
        word = {-1: "last", 0: "this", 1: "next"}[week]
        forms += [f"{word} {d.strftime('%A')}"] * 2
    return rng.choice(forms)


def day(i: int) -> date:
    return idx_to_date(i)


# ---- scenarios (expected answer computed by code)

def supplier_delay(w: World, rng: random.Random) -> tuple[str, str, dict] | None:
    sh = rng.choice(w.shipments)
    eta = date_to_idx(date.fromisoformat(sh["eta_date"]))
    if not 1 <= eta <= 15:
        return None
    new = min(eta + rng.randint(1, 4), 19)
    inc = {"kind": "supplier_delay", "supplier_id": sh["supplier_id"], "part_id": sh["part_id"],
           "plant_id": sh["plant_id"], "blocked_from": day(eta).isoformat(), "blocked_until": day(new).isoformat()}
    if not w.truth.affected(inc):
        return None
    sup, part, plant = (supplier_name(w, rng, sh["supplier_id"]), part_name(w, rng, sh["part_id"]),
                        plant_name(w, rng, sh["plant_id"]))
    was, now, why = say_date(rng, day(eta)), say_date(rng, day(new)), rng.choice(DELAY_CAUSES)
    sid = sh["shipment_id"]
    texts = [
        ("supplier email", f"Subject: {sid} late\n{sup} here. Shipment {sid} ({part}) for {plant} was due {was} "
                           f"and will now arrive {now}. Reason: {why}."),
        ("ops chat", f"heads up, {sup} says the {part} for {plant} won't make {was}. new ETA {now} ({why})"),
        ("email", f"Our {part} delivery to {plant}, originally scheduled for {was}, is pushed to {now} due to {why}. "
                  f"Apologies for the inconvenience. - {sup}"),
        ("phone note", f"Call from {sup}: {part} shipment into {plant} slips from {was} to {now}. Cause: {why}."),
        ("supplier email", f"Shipment {sid} delayed. Original ETA {was}; revised ETA {now}. Part: {part}. "
                           f"Destination: {plant}. Supplier: {sup}."),
        ("ops chat", f"{plant} line is waiting on {part} from {sup}. original drop was {was}, new ETA is {now} because of {why}"),
    ]
    source, text = rng.choice(texts)
    return source, text, {"incidents": [inc], "escalate": False}


def plant_outage(w: World, rng: random.Random) -> tuple[str, str, dict] | None:
    pid = rng.choice(sorted(w.plants))
    start = rng.randint(1, 16)
    end = min(start + rng.choice([0, 0, 1, 1, 2, 3]), 19)
    inc = {"kind": "plant_outage", "plant_id": pid, "outage_start": day(start).isoformat(),
           "outage_end": day(end).isoformat()}
    if not w.truth.affected(inc):
        return None
    plant, why = plant_name(w, rng, pid), rng.choice(OUTAGE_CAUSES)
    a, b = say_date(rng, day(start)), say_date(rng, day(end))
    if start == end:
        texts = [("plant alert", f"Plant operations alert: {plant} lost production to {why}. No builds on {a}; "
                                 f"the line restarts the following working day."),
                 ("ops chat", f"{plant} is down {a} only ({why}). back the next working day")]
    else:
        texts = [("plant alert", f"Plant operations alert: {plant} lost production to {why}. Production is stopped "
                                 f"from {a} through {b} inclusive."),
                 ("ops chat", f"{plant} update: {why}. We're dark from {a} through {b}; the line restarts the "
                              f"following working day."),
                 ("email", f"Due to {why}, {plant} will not build from {a} to {b} (inclusive). Restart the next working day."),
                 ("plant alert", f"OUTAGE {plant}: {why}. Down {a} - {b}, both days included.")]
    source, text = rng.choice(texts)
    return source, text, {"incidents": [inc], "escalate": False}


def quality_hold(w: World, rng: random.Random) -> tuple[str, str, dict] | None:
    lot = w.truth.lots[rng.choice(sorted(w.truth.lots))]
    if not w.truth.lot_vehicles(lot["lot_id"]):
        return None
    first, last = date.fromisoformat(lot["first_build_date"]), date.fromisoformat(lot["last_build_date"])
    # Without the lot id, the part, plant, supplier and window must point at this lot alone.
    same = [x for x in w.truth.lots.values() if x["part_id"] == lot["part_id"] and x["plant_id"] == lot["plant_id"]
            and x["supplier_id"] == lot["supplier_id"] and x["first_build_date"] <= lot["last_build_date"]
            and x["last_build_date"] >= lot["first_build_date"]]
    with_id = len(same) > 1 or rng.random() < 0.45
    sup, part, plant = (supplier_name(w, rng, lot["supplier_id"]), part_name(w, rng, lot["part_id"]),
                        plant_name(w, rng, lot["plant_id"]))
    a, b, defect = say_date(rng, first), say_date(rng, last), rng.choice(DEFECTS)
    if with_id:
        texts = [("quality bulletin", f"QUALITY BULLETIN: Lot {lot['lot_id']} ({part}, from {sup}) installed at {plant} on "
                                      f"vehicles built {a} to {b} has {defect}. Place the lot on hold, stop sale of unsold "
                                      f"vehicles and contact owners."),
                 ("email", f"Please hold lot {lot['lot_id']} immediately: {defect} found in {part} from {sup}. "
                           f"Used at {plant}, builds {a} through {b}.")]
    else:
        texts = [("quality bulletin", f"Quality alert: {sup} says the {part} sent to {plant} had {defect}. Anything built "
                                      f"{a} through {b} is suspect."),
                 ("ops chat", f"quality issue - {part} from {sup} at {plant}, {defect}. builds from {a} to {b} affected")]
    source, text = rng.choice(texts)
    return source, text, {"incidents": [{"kind": "quality_hold", "lots": [lot["lot_id"]]}], "escalate": False}


def noise(w: World, rng: random.Random) -> tuple[str, str, dict]:
    source, text = rng.choice(NOISE)
    return source, text.format(city=rng.choice(w.dealers)["city"].split(",")[0]), {"incidents": [], "escalate": False}


def rumor(w: World, rng: random.Random) -> tuple[str, str, dict]:
    source, text = rng.choice(RUMORS)
    part = w.parts[rng.choice(sorted(w.parts))]["name"]
    plant = rng.choice(w.aliases[rng.choice(sorted(w.plants))])
    return source, text.format(part_name=part, plant_alias=plant), {"incidents": [], "escalate": True}


def compound(w: World, rng: random.Random) -> tuple[str, str, dict] | None:
    pair = rng.choice([("plant_outage", "supplier_delay"), ("supplier_delay", "noise"), ("quality_hold", "unconfirmed"),
                       ("plant_outage", "noise"), ("supplier_delay", "unconfirmed"), ("plant_outage", "quality_hold")])
    parts = []
    for kind in pair:
        made = None
        for _ in range(300):
            made = MAKERS[kind](w, rng)
            if made:
                break
        if not made:
            return None
        parts.append(made)
    # Two outages or delays at one plant would interact; keep the pair independent.
    incs = [i for _s, _t, e in parts for i in e["incidents"]]
    plants = [i.get("plant_id") for i in incs if i.get("plant_id")]
    if len(plants) != len(set(plants)):
        return None
    text = "Morning digest, two items. " + " ".join(f"({n}) {t}" for n, (_s, t, _e) in enumerate(parts, 1))
    return "daily digest", text, {"incidents": incs, "escalate": any(e["escalate"] for _s, _t, e in parts)}


MAKERS = {"supplier_delay": supplier_delay, "plant_outage": plant_outage, "quality_hold": quality_hold,
          "noise": noise, "unconfirmed": rumor, "compound": compound}


def main() -> None:
    w, rng = World(), random.Random(SEED)
    kept = [c for c in json.load(open(CASES, encoding="utf-8")) if int(c["id"].split("-")[1]) <= KEEP]
    plan = [k for k, n in MIX.items() for _ in range(n)]
    rng.shuffle(plan)
    new, seen = [], {c["text"] for c in kept}
    for kind in plan:
        for _ in range(500):
            made = MAKERS[kind](w, rng)
            if made and made[1] not in seen:
                break
        else:
            raise SystemExit(f"could not make a {kind} case")
        source, text, expect = made
        seen.add(text)
        new.append({"id": f"T-{len(kept) + len(new) + 1:02d}", "category": kind, "source": source,
                    "text": text, "expect": expect})
    cases = kept + new
    assert len(cases) == TOTAL, len(cases)
    with open(CASES, "w", encoding="utf-8") as handle:
        handle.write("[\n" + ",\n\n".join("  " + json.dumps(c, ensure_ascii=False) for c in cases) + "\n]\n")
    print(f"{len(kept)} kept + {len(new)} new = {len(cases)} cases -> {CASES}")
    for k in MIX:
        print(f"  {k:15} {sum(c['category'] == k for c in new)}")


if __name__ == "__main__":
    main()
