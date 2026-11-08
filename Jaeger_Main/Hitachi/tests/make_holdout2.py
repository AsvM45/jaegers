"""Write the second held-out set, tests/holdout2_cases.json (H2-001..H2-100), and add its expected
graphs to tests/expected_graphs.json under "holdout2".

    python tests/make_holdout2.py       # run once; stored, not regenerated per run

Why a second set: the first held-out set (tests/holdout_cases.json) was used to diagnose the
reader's failures, so it is no longer blind. This one was written after those fixes, with new
phrasing, sources and connectors, and nothing may be tuned on it. Like the first, every case comes
from a real scenario in the tables, so its answer key is computed by code, and some forms are hard
on purpose ("First ... Second ...", "A) ... B)").
"""

from __future__ import annotations

import json
import os
import random
import sys
from datetime import date

HITACHI = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TESTS = os.path.join(HITACHI, "tests")
for p in (HITACHI, TESTS):
    if p not in sys.path:
        sys.path.insert(0, p)

from enterprise import date_to_idx  # noqa: E402
from make_cases import World  # noqa: E402
from make_holdout import GRAPHS, day, expected_graph, part_words, plant_words, say, sup_words  # noqa: E402

OUT = os.path.join(TESTS, "holdout2_cases.json")
SEED = 4242
MIX = {"supplier_delay": 22, "plant_outage": 20, "quality_hold": 18, "noise": 14, "unconfirmed": 12, "compound": 14}

NOISE = [
    ("internal memo", "Reminder: submit March expense reports through the finance portal."),
    ("internal memo", "Town hall slides are posted on the intranet."),
    ("news wire", "Heavy rain expected in Seattle, WA through Wednesday."),
    ("dealer email", "Dealer {city} asks for the updated accessory price sheets."),
    ("internal memo", "Please welcome our new CFO, who starts on Monday."),
    ("internal memo", "Fire drill at the {plant_city} office building Thursday at 10 am. Plan to be outside for 15 minutes."),
    ("teams message", "Lunch and learn on EV battery chemistry in the big conference room today."),
    ("internal memo", "Parking permits must be renewed by the end of the month."),
    ("news wire", "A car magazine review praises the ride quality of our Summit model."),
    ("dealer email", "Dealer {city} reports record showroom traffic this weekend."),
    ("internal memo", "The holiday schedule for next year has been posted."),
    ("teams message", "Reminder to fill out the employee engagement survey."),
]
RUMORS = [
    ("teams message", "Gossip says {sup} is in financial trouble; could affect supply. Nothing confirmed."),
    ("voicemail", "Hearing {plant} might go down for maintenance soon, no dates."),
    ("email", "A driver mentioned possible delays at the border. Unverified."),
    ("teams message", "Somebody thinks the latest {part_name} batch could be defective; no lot or dates."),
    ("teams message", "Possible labor action at {plant}? Not confirmed."),
    ("teams message", "rumor: chip shortage coming, no idea when"),
    ("email", "Unclear reports that a supplier may miss deliveries next month."),
    ("voicemail", "Could be a problem with paint supply, no details yet."),
]
OUTAGE_CAUSES = ["a transformer fire", "a cyberattack on the line controllers", "a boiler failure",
                 "an ammonia leak", "ice damage to the roof", "a conveyor motor burnout"]
DELAY_CAUSES = ["a customs hold", "a derailment", "a machine breakdown at their site", "a raw-material shortage",
                "a missed vessel", "a strike at their warehouse"]
DEFECTS = ["intermittent shorts", "seal leaks", "a mislabeled part number", "brittle plastic clips",
           "excess solder", "wrong thread pitch"]


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
        ("teams message", f"Heads-up: {sup} says the {part} bound for {plant} slid from {was} to {now}."),
        ("email", f"Inbound {part} ({sup}) to {plant}: original delivery {was}; now arriving {now} because of {why}."),
        ("plant alert", f"{plant} receiving: the {part} truck from {sup} won't show {was}. Carrier now quoting {now}."),
        ("email", f"Per {sup}, {part} for {plant} got pushed out a few days: {was} -> {now}."),
        ("supplier portal", f"{sup} missed the {was} delivery of {part} to {plant}. Revised date: {now}."),
        ("supplier portal", f"Update on {sid} ({part}): no longer {was}, expect {now}. Destination {plant}. Shipper {sup}."),
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
        texts = [("plant alert", f"{plant}: no builds {a} ({why}), resuming the next working day."),
                 ("teams message", f"{plant} is idle on {a} because of {why}.")]
    else:
        texts = [("plant alert", f"{plant} is idle {a} to {b} due to {why}."),
                 ("email", f"Heads up: we're losing {plant} for {a} through {b} ({why})."),
                 ("voicemail", f"{plant} production halted from {a} after {why}; restart planned {back}."),
                 ("plant alert", f"Emergency: {why} at {plant}. Assembly paused {a} through {b}.")]
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
        texts = [("quality report", f"QA hold: lot {lid} ({part} from {sup}) used at {plant}, builds {a} to {b}. Issue: {defect}."),
                 ("email", f"Please quarantine {lid}: {defect} in {part}. {plant} builds {a} through {b}.")]
    else:
        texts = [("quality report", f"Field reports of {defect} traced to {part} from {sup} at {plant}; affected build "
                                    f"window {a} to {b}."),
                 ("email", f"{sup} issued a defect notice for {part} supplied to {plant}, production dates {a} through {b}: {defect}.")]
    s, t = rng.choice(texts)
    return s, t, {"incidents": [{"kind": "quality_hold", "lots": [lid]}], "escalate": False}


def noise(w, rng):
    s, t = rng.choice(NOISE)
    return s, t.format(city=rng.choice(w.dealers)["city"].split(",")[0],
                       plant_city=w.plants[rng.choice(sorted(w.plants))]["city"].split(",")[0]), \
        {"incidents": [], "escalate": False}


def rumor(w, rng):
    s, t = rng.choice(RUMORS)
    return s, t.format(sup=w.suppliers[rng.choice(sorted(w.suppliers))]["name"],
                       plant=plant_words(w, rng, rng.choice(sorted(w.plants))),
                       part_name=w.parts[rng.choice(sorted(w.parts))]["name"]), {"incidents": [], "escalate": True}


def compound(w, rng):
    pair = rng.choice([("plant_outage", "supplier_delay"), ("supplier_delay", "noise"), ("quality_hold", "unconfirmed"),
                       ("supplier_delay", "quality_hold"), ("noise", "plant_outage"), ("plant_outage", "plant_outage")])
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
    low = t2[0].lower() + t2[1:]
    style = rng.choice(["paren", "bare", "separately", "also", "first_second", "letters"])
    text = {"paren": f"Shift report. (1) {t1} (2) {t2}", "bare": f"Two notes: 1) {t1} 2) {t2}",
            "separately": f"{t1} Separately, {low}", "also": f"{t1} Also, {low}",
            "first_second": f"First, {t1[0].lower() + t1[1:]} Second, {low}", "letters": f"A) {t1} B) {t2}"}[style]
    return "shift report", text, {"incidents": incs, "escalate": any(e["escalate"] for _s, _t, e in parts)}


MAKERS = {"supplier_delay": supplier_delay, "plant_outage": plant_outage, "quality_hold": quality_hold,
          "noise": noise, "unconfirmed": rumor, "compound": compound}


def main() -> None:
    w, rng = World(), random.Random(SEED)
    plan = [k for k, n in MIX.items() for _ in range(n)]
    rng.shuffle(plan)
    seen = {c["text"] for c in json.load(open(os.path.join(TESTS, "cases.json")))}
    seen |= {c["text"] for c in json.load(open(os.path.join(TESTS, "holdout_cases.json")))["cases"]}
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
        cases.append({"id": f"H2-{len(cases) + 1:03d}", "category": kind, "source": s, "text": t, "expect": expect})
    with open(OUT, "w", encoding="utf-8") as handle:
        handle.write('{"_note": "HELD OUT (second set). Written after the fixes made from the first held-out set. Do not '
                     'tune the reader or the prompt on these.",\n "cases": [\n'
                     + ",\n".join("  " + json.dumps(c, ensure_ascii=False) for c in cases) + "\n]}\n")
    graphs = json.load(open(GRAPHS))
    graphs["holdout2"] = {c["id"]: expected_graph(w.truth, c["expect"]) for c in cases}
    with open(GRAPHS, "w", encoding="utf-8") as handle:
        json.dump(graphs, handle, indent=1)
        handle.write("\n")
    print(f"{len(cases)} cases -> {OUT}; expected graphs added under 'holdout2'")
    for k in MIX:
        print(f"  {k:15} {sum(c['category'] == k for c in cases)}")


if __name__ == "__main__":
    main()
