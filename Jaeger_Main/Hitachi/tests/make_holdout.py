"""Write the held-out test set, tests/holdout_cases.json (H-001..H-100), and the expected graph of
every held-out and given case, tests/expected_graphs.json.

    python tests/make_holdout.py        # run once; both files are stored, not regenerated per run

HELD OUT: these messages were written after the reader's word lists and the model's prompt were
made general, and neither may be tuned on them. They measure how well the model and the tower read
messages they were not shaped on. (tests/cases.json is no longer blind: it informed the word lists.)

Each case comes from a real scenario in the company tables (a shipment whose delay blocks builds,
an outage on working days that hits orders, a lot with built vehicles; or noise, or a rumor), so its
answer key is computed by code. The wording deliberately differs from tests/make_cases.py: other
sources (voicemail, supplier portal, Teams), other verbs (offline, suspended, rescheduled,
nonconformance), other date styles ("the 22nd", "22 Mar", "tomorrow", "expected back <day>"),
misspelled plant names, and two-incident messages written as "1) 2)" or "Also, ..." as well as
"(1) (2)". Some of these are hard on purpose.

The expected graph is each answer key traced through the company tables by tests/run_cases.py
(independent of the tower's graph code): every production order, customer order, dealer, customer,
loaner, lot, vehicle and owner the incident touches.
"""

from __future__ import annotations

import json
import os
import random
import sys
from datetime import date, timedelta

HITACHI = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TESTS = os.path.join(HITACHI, "tests")
for p in (HITACHI, TESTS):
    if p not in sys.path:
        sys.path.insert(0, p)

import run_cases as rc  # noqa: E402
from enterprise import date_to_idx, idx_to_date  # noqa: E402
from make_cases import World  # noqa: E402  same tables, same name lists

HOLDOUT = os.path.join(TESTS, "holdout_cases.json")
GRAPHS = os.path.join(TESTS, "expected_graphs.json")
SEED = 2027
TODAY = date(2027, 3, 8)
MIX = {"supplier_delay": 22, "plant_outage": 20, "quality_hold": 18, "noise": 14, "unconfirmed": 12,
       "compound": 14}

NOISE = [
    ("teams message", "The quarterly sales webinar moves to Thursday afternoon. Same link as before."),
    ("news wire", "Snow expected in Denver, CO this weekend; travel advisories in effect."),
    ("internal memo", "Please update your email signature to the new logo by end of month."),
    ("teams message", "The vending machine on floor 3 is out of order again."),
    ("internal memo", "Congratulations to the {plant_city} softball team on winning the league!"),
    ("dealer email", "Dealer {city} requests 200 extra brochures for the spring auto show."),
    ("internal memo", "Insurance renewal paperwork is due to HR by Friday."),
    ("news wire", "Stock markets closed higher today on strong tech earnings."),
    ("internal memo", "Volunteer day at the {plant_city} food bank is next Saturday. Sign up on the portal."),
    ("dealer email", "Fleet sales promotion extended through the end of the quarter."),
    ("teams message", "Who left a blue umbrella in conference room B?"),
    ("news wire", "A minor earthquake was felt near Lima, Peru; no damage reported."),
    ("dealer email", "Can we get the new window stickers in Spanish as well? - {city}"),
    ("internal memo", "The {plant_city} plant's open house for families is on Saturday. Refreshments provided."),
]
RUMORS = [
    ("teams message", "Not sure if true, but a friend at {sup} says they may run short on parts soon."),
    ("voicemail", "Possibly an issue brewing at {plant}. Nobody can confirm anything yet."),
    ("news wire", "Chatter about a port strike that could hit deliveries. No specifics."),
    ("teams message", "Some folks think a batch of airbags might be bad. No lot number, no dates."),
    ("teams message", "unverified: {plant} may shut a line at some point"),
    ("email", "Apparently freight problems are causing delays somewhere upstream. Not confirmed."),
    ("voicemail", "Heard {sup} could be behind on something, didn't catch what. Will call back."),
    ("teams message", "is it true {plant} might lose power next month? someone was talking about it"),
]
OUTAGE_CAUSES = ["an electrical fire", "a burst water main", "an IT system failure", "a press line breakdown",
                 "a severe storm", "a chemical spill", "a substation failure", "a roof collapse in the paint shop"]
DELAY_CAUSES = ["capacity problems", "a broken press at their plant", "a labor shortage", "weather at the port",
                "a supplier of theirs being late", "a rejected shipment that had to be remade"]
DEFECTS = ["porosity in the castings", "an incorrect torque spec", "water ingress", "delamination",
           "a software checksum error", "contaminated grease", "undersized fasteners"]


def typo(word: str, rng: random.Random) -> str:
    """Drop one inner letter: Lexington -> Lexngton."""
    if len(word) < 6:
        return word
    i = rng.randint(2, len(word) - 3)
    return word[:i] + word[i + 1:]


def plant_words(w: World, rng: random.Random, pid: str) -> str:
    p = w.plants[pid]
    city = p["city"].split(",")[0]
    choices = [pid, p["name"], city, f"the {city} plant", *w.aliases[pid]]
    pick = rng.choice(choices)
    if rng.random() < 0.12 and " " not in city:
        pick = f"the {typo(city, rng)} plant"
    return pick


def part_words(w: World, rng: random.Random, part_id: str) -> str:
    p = w.parts[part_id]
    return rng.choice([part_id, p["name"], p["name"] + "s" if not p["name"].endswith("s") else p["name"],
                       *w.aliases[part_id]])


def sup_words(w: World, rng: random.Random, sid: str) -> str:
    s = w.suppliers[sid]
    return rng.choice([s["name"], s["name"].split()[0], sid, *w.aliases[sid]])


def say(rng: random.Random, d: date) -> str:
    """Date styles not used in tests/make_cases.py, plus a few plain ones."""
    ordinal = {1: "st", 2: "nd", 3: "rd", 21: "st", 22: "nd", 23: "rd", 31: "st"}.get(d.day, "th")
    forms = [f"{d.day} {d.strftime('%b')}", f"{d.strftime('%B')} {d.day}{ordinal}", d.isoformat(),
             f"{d.month}/{d.day}", f"{d.strftime('%a')} {d.day} {d.strftime('%B')}"]
    if d.month == TODAY.month:
        forms += [f"the {d.day}{ordinal}", f"{d.strftime('%A')} the {d.day}{ordinal}"]
    if d == TODAY + timedelta(days=1):
        forms += ["tomorrow"] * 3
    monday = TODAY - timedelta(days=TODAY.weekday())
    if (d - monday).days // 7 == 1 and d.weekday() < 5:
        forms += [f"next {d.strftime('%a')}", f"next {d.strftime('%A')}"]
    return rng.choice(forms)


def day(i: int) -> date:
    return idx_to_date(i)


def supplier_delay(w, rng):
    sh = rng.choice(w.shipments)
    eta = date_to_idx(date.fromisoformat(sh["eta_date"]))
    if not 1 <= eta <= 15:
        return None
    new = min(eta + rng.randint(1, 4), 19)
    inc = {"kind": "supplier_delay", "supplier_id": sh["supplier_id"], "part_id": sh["part_id"],
           "plant_id": sh["plant_id"], "blocked_from": day(eta).isoformat(), "blocked_until": day(new).isoformat()}
    if not w.truth.affected(inc):
        return None
    sup, part, plant = sup_words(w, rng, sh["supplier_id"]), part_words(w, rng, sh["part_id"]), plant_words(w, rng, sh["plant_id"])
    was, now, why, sid = say(rng, day(eta)), say(rng, day(new)), rng.choice(DELAY_CAUSES), sh["shipment_id"]
    texts = [
        ("supplier portal", f"ETA change: {part} for {plant}. Was {was}, now {now}. - {sup} logistics"),
        ("email", f"{sup} can't ship the {part} to {plant} on {was} as planned; earliest is {now} ({why})."),
        ("voicemail", f"Voicemail from {sup}: the {part} order headed to {plant} is rescheduled from {was} to {now}."),
        ("supplier portal", f"Shipment {sid}: arrival moved from {was} to {now}. Reason: {why}. Supplier: {sup}. "
                            f"Part: {part}. Ship to: {plant}."),
        ("teams message", f"fyi {part} from {sup} into {plant} is running behind, expected {was} but more like {now} now"),
        ("email", f"We regret to inform you that delivery of {part} to {plant}, slated for {was}, has been "
                  f"postponed until {now}. Regards, {sup}"),
    ]
    s, t = rng.choice(texts)
    return s, t, {"incidents": [inc], "escalate": False}


def plant_outage(w, rng):
    pid = rng.choice(sorted(w.plants))
    start = rng.randint(1, 16)
    end = min(start + rng.choice([0, 1, 1, 2, 3, 4]), 18)
    inc = {"kind": "plant_outage", "plant_id": pid, "outage_start": day(start).isoformat(),
           "outage_end": day(end).isoformat()}
    if not w.truth.affected(inc):
        return None
    plant, why = plant_words(w, rng, pid), rng.choice(OUTAGE_CAUSES)
    a, b, back = say(rng, day(start)), say(rng, day(end)), say(rng, day(end + 1))
    if start == end:
        texts = [("teams message", f"{plant} down all day {a} ({why})."),
                 ("email", f"No production at {plant} on {a} due to {why}. Normal schedule the next working day.")]
    else:
        texts = [("email", f"{plant} will be offline {a} through {b} because of {why}."),
                 ("plant alert", f"Line stoppage at {plant}: {why}. No production from {a} to {b}."),
                 ("voicemail", f"Production at {plant} is suspended starting {a} after {why}; we expect to be "
                               f"back up on {back}."),
                 ("teams message", f"{plant} closed {a} - {b} ({why}). will update")]
    s, t = rng.choice(texts)
    return s, t, {"incidents": [inc], "escalate": False}


def quality_hold(w, rng):
    lot = w.truth.lots[rng.choice(sorted(w.truth.lots))]
    if not w.truth.lot_vehicles(lot["lot_id"]):
        return None
    first, last = date.fromisoformat(lot["first_build_date"]), date.fromisoformat(lot["last_build_date"])
    same = [x for x in w.truth.lots.values() if x["part_id"] == lot["part_id"] and x["plant_id"] == lot["plant_id"]
            and x["supplier_id"] == lot["supplier_id"] and x["first_build_date"] <= lot["last_build_date"]
            and x["last_build_date"] >= lot["first_build_date"]]
    with_id = len(same) > 1 or rng.random() < 0.5
    sup, part, plant = sup_words(w, rng, lot["supplier_id"]), part_words(w, rng, lot["part_id"]), plant_words(w, rng, lot["plant_id"])
    a, b, defect, lid = say(rng, first), say(rng, last), rng.choice(DEFECTS), lot["lot_id"]
    if with_id:
        texts = [("quality report", f"Nonconformance report: {part} lot {lid} from {sup}, used at {plant} on builds "
                                    f"{a} to {b}, shows {defect}. Contain and hold."),
                 ("email", f"Containment request: hold {lid}. {part}, {defect}. Builds at {plant} between {a} and {b}.")]
    else:
        texts = [("quality report", f"{sup} flagged {defect} in {part} shipped to {plant}; vehicles assembled {a} "
                                    f"through {b} are affected."),
                 ("email", f"Recall alert - {part} from {sup} at {plant}, build dates {a} to {b}: {defect}.")]
    s, t = rng.choice(texts)
    return s, t, {"incidents": [{"kind": "quality_hold", "lots": [lid]}], "escalate": False}


def noise(w, rng):
    s, t = rng.choice(NOISE)
    plant_city = w.plants[rng.choice(sorted(w.plants))]["city"].split(",")[0]
    return s, t.format(city=rng.choice(w.dealers)["city"].split(",")[0], plant_city=plant_city), \
        {"incidents": [], "escalate": False}


def rumor(w, rng):
    s, t = rng.choice(RUMORS)
    sup = w.suppliers[rng.choice(sorted(w.suppliers))]["name"]
    plant = plant_words(w, rng, rng.choice(sorted(w.plants)))
    return s, t.format(sup=sup, plant=plant), {"incidents": [], "escalate": True}


def compound(w, rng):
    pair = rng.choice([("plant_outage", "supplier_delay"), ("supplier_delay", "noise"), ("quality_hold", "unconfirmed"),
                       ("supplier_delay", "supplier_delay"), ("plant_outage", "quality_hold"), ("noise", "plant_outage")])
    parts = []
    for kind in pair:
        for _ in range(300):
            made = MAKERS[kind](w, rng)
            if made:
                break
        else:
            return None
        parts.append(made)
    incs = [i for _s, _t, e in parts for i in e["incidents"]]
    plants = [i.get("plant_id") for i in incs if i.get("plant_id")]
    if len(plants) != len(set(plants)):
        return None
    t1, t2 = parts[0][1], parts[1][1]
    style = rng.choice(["paren", "paren", "paren", "plain_num", "also"])
    if style == "paren":
        text = f"Daily summary. (1) {t1} (2) {t2}"
    elif style == "plain_num":
        text = f"Two updates: 1) {t1} 2) {t2}"
    else:
        text = f"{t1} Also, {t2[0].lower() + t2[1:]}"
    return "daily summary", text, {"incidents": incs, "escalate": any(e["escalate"] for _s, _t, e in parts)}


MAKERS = {"supplier_delay": supplier_delay, "plant_outage": plant_outage, "quality_hold": quality_hold,
          "noise": noise, "unconfirmed": rumor, "compound": compound}


def expected_graph(truth, expect: dict) -> dict:
    """The answer key traced through the company tables to every record it touches."""
    eff = rc.expected_effects(truth, {"expect": expect})
    orders = sorted(eff["earliest"])
    cos = sorted({co["customer_order_id"] for po in orders for co in truth.cos_by_po[po]})
    vehicles = sorted({v["vin"] for lot in eff["lots"] for v in truth.lot_vehicles(lot)})
    return {
        "incidents": expect["incidents"], "escalate": expect["escalate"],
        "production_orders": orders,
        "customer_orders": cos,
        "dealers_notified": sorted(eff["notify"]),
        "customers": sorted({truth.cos[c]["customer_id"] for c in cos}),
        "loaners": sorted(eff["loaners"]),
        "lots": sorted(eff["lots"]),
        "vehicles": vehicles,
        "stop_sale_vins": sorted(v for vins in eff["stop"].values() for v in vins),
        "owners_notified": sorted(eff["owners"]),
    }


def main() -> None:
    w, rng = World(), random.Random(SEED)
    plan = [k for k, n in MIX.items() for _ in range(n)]
    rng.shuffle(plan)
    seen = {c["text"] for c in json.load(open(os.path.join(TESTS, "cases.json")))}
    cases = []
    for kind in plan:
        for _ in range(500):
            made = MAKERS[kind](w, rng)
            if made and made[1] not in seen:
                break
        else:
            raise SystemExit(f"could not make a {kind} case")
        s, t, expect = made
        seen.add(t)
        cases.append({"id": f"H-{len(cases) + 1:03d}", "category": kind, "source": s, "text": t, "expect": expect})
    with open(HOLDOUT, "w", encoding="utf-8") as handle:
        handle.write('{"_note": "HELD OUT. Written after the reader and the model prompt were made general. Do not '
                     'tune the reader or the prompt on these. Answer keys come from real scenarios in the tables.",\n'
                     ' "cases": [\n' + ",\n".join("  " + json.dumps(c, ensure_ascii=False) for c in cases) + "\n]}\n")
    given = json.load(open(os.path.join(TESTS, "given_cases.json"), encoding="utf-8"))["cases"]
    graphs = {
        "_note": "Expected graph per case: the answer key traced through the company tables (tests/run_cases.py Truth).",
        "holdout": {c["id"]: expected_graph(w.truth, c["expect"]) for c in cases},
        "given": {c["id"]: expected_graph(w.truth, c["expect"]) for c in given},
    }
    with open(GRAPHS, "w", encoding="utf-8") as handle:
        json.dump(graphs, handle, indent=1)
        handle.write("\n")
    print(f"{len(cases)} held-out cases -> {HOLDOUT}")
    for k in MIX:
        print(f"  {k:15} {sum(c['category'] == k for c in cases)}")
    print(f"expected graphs for {len(graphs['holdout'])} held-out + {len(graphs['given'])} given cases -> {GRAPHS}")


if __name__ == "__main__":
    main()
