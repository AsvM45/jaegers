"""Write a blind test set: code picks real scenarios, a large local model writes the messages.

    python tests/make_blind.py                    # 40 cases -> tests/blind_cases.json
    python tests/make_blind.py --n 100 --out tests/blind2_cases.json --seed 2

Why this split: the answer key must be exact, so code picks every scenario from the company tables
(a real shipment and its due date, a real plant and days, a lot whose part, plant and build window
match only that lot) and decides how each fact is written ("next Tuesday", "the 24th", a nickname,
a one-letter typo). The writer model (TOWER_WRITER_MODEL, default qwen3:8b) only turns those facts
into a message a person would send. A message that drops a required phrase is rejected and
rewritten. Rumors and noise are included, some naming a plant, and compound messages join two.

The file is BLIND: nobody tunes the reader or the prompts on it. Score it with
    python tests/run_model.py --suite blind
"""

from __future__ import annotations

import argparse
import json
import os
import random
import sys
import urllib.request
from datetime import date, timedelta

HITACHI = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HITACHI)

from tower.calendar_util import TODAY, is_working_day  # noqa: E402
from tower.graph import WorldGraph  # noqa: E402

WRITER = os.environ.get("TOWER_WRITER_MODEL", "qwen3:8b")
OLLAMA = os.environ.get("OLLAMA_URL", "http://localhost:11434")
WEEKDAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September",
          "October", "November", "December"]


def ordinal(n: int) -> str:
    return f"{n}{'th' if 11 <= n % 100 <= 13 else {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th')}"


def phrase_for(day: date, rng: random.Random, allow_relative: bool = True) -> str:
    """How a person might write this date, relative to TODAY (Mon 8 March 2027)."""
    styles = ["iso", "month_day", "slash", "weekday_month", "day_only"]
    delta = (day - TODAY).days
    if allow_relative and 7 <= delta <= 13:
        styles += ["relative", "relative"]
    style = rng.choice(styles)
    if style == "iso":
        return day.isoformat()
    if style == "month_day":
        return f"{MONTHS[day.month - 1]} {ordinal(day.day)}"
    if style == "slash":
        return f"{day.month}/{day.day}"
    if style == "weekday_month":
        return f"{WEEKDAYS[day.weekday()]} {MONTHS[day.month - 1][:3]} {day.day}"
    if style == "day_only":
        return f"the {ordinal(day.day)}"
    # relative: "next Tuesday" from Monday 8 March is Tuesday 16 March (the following week's day)
    return f"next {WEEKDAYS[day.weekday()]}"


def working_days(start: date, end: date) -> list[date]:
    out, d = [], start
    while d <= end:
        if is_working_day(d):
            out.append(d)
        d += timedelta(days=1)
    return out


def typo(word: str, rng: random.Random) -> str:
    """One edit (drop or swap a letter), as the reader's typo matching allows."""
    i = rng.randrange(1, len(word) - 2)
    return word[:i] + word[i + 1:] if rng.random() < 0.5 else word[:i] + word[i + 1] + word[i] + word[i + 2:]


class Names:
    def __init__(self, graph: WorldGraph, rng: random.Random):
        self.g, self.rng = graph, rng
        self.aliases: dict[tuple[str, str], list[str]] = {}
        for alias, (etype, eid) in graph._alias_map.items():
            self.aliases.setdefault((etype, eid), []).append(alias)

    def plant(self, pid: str, messy: bool) -> str:
        city = self.g.plants[pid]["city"]
        options = [self.g.plants[pid]["name"], city, f"the {city} plant"]
        if messy and len(city) >= 6 and city.isalpha():
            options = [typo(city, self.rng), f"the {typo(city, self.rng)} plant"]
        return self.rng.choice(options)

    def supplier(self, sid: str, messy: bool) -> str:
        name = self.g.suppliers[sid]["name"]
        short = name.split()[0]
        if messy and len(short) >= 6 and short.isalpha():
            return typo(short, self.rng)
        return self.rng.choice([name, short, sid])

    def part(self, part_id: str) -> str:
        names = [a for a in self.aliases.get(("part", part_id), []) if not a.isupper()]
        return self.rng.choice([self.g.parts[part_id]["name"], part_id, *names[:3]])


def scenario_delay(g, names, rng, messy):
    window = [s for s in g.shipments.values() if "2027-03-09" <= s["eta_date"] <= "2027-04-02"
              and is_working_day(date.fromisoformat(s["eta_date"]))]
    s = rng.choice(window)
    due = date.fromisoformat(s["eta_date"])
    new = rng.choice(working_days(due + timedelta(days=1), due + timedelta(days=6)))
    facts = {"supplier": names.supplier(s["supplier_id"], messy), "part": names.part(s["part_id"]),
             "plant": names.plant(s["plant_id"], messy), "original date": phrase_for(due, rng),
             "new date": phrase_for(new, rng)}
    if rng.random() < 0.25:
        facts = {"shipment": s["shipment_id"], "new date": facts["new date"],
                 **({"original date": facts["original date"]} if rng.random() < 0.5 else {})}
    incident = {"kind": "supplier_delay", "supplier_id": s["supplier_id"], "part_id": s["part_id"],
                "plant_id": s["plant_id"], "blocked_from": due.isoformat(), "blocked_until": new.isoformat()}
    return facts, "a supplier's delivery of a part is late: it was due on the original date and now arrives on the new date", incident


def scenario_outage(g, names, rng, messy):
    pid = rng.choice(sorted(g.plants))
    days = working_days(TODAY + timedelta(days=1), date(2027, 4, 2))
    start = rng.choice(days[:-4])
    span = working_days(start, start + timedelta(days=6))[: rng.randint(1, 4)]
    end = span[-1]
    facts = {"plant": names.plant(pid, messy), "first day down": phrase_for(start, rng)}
    situation = "a plant cannot build cars for some days (pick a believable cause)"
    if rng.random() < 0.3:
        restart = working_days(end + timedelta(days=1), end + timedelta(days=5))[0]
        facts["day production restarts"] = phrase_for(restart, rng)
        situation += "; say it is down from the first day and production restarts on the restart day"
    else:
        facts["last day down"] = phrase_for(end, rng)
    incident = {"kind": "plant_outage", "plant_id": pid, "outage_start": start.isoformat(), "outage_end": end.isoformat()}
    return facts, situation, incident


def scenario_quality(g, names, rng, messy):
    lots = [l for l in g.lots.values() if "2027-02-20" <= l["first_build_date"] <= "2027-03-08"]
    lot = rng.choice(lots)
    defect = rng.choice(["cracked housings", "bad solder joints", "loose connectors", "porosity in the castings",
                         "wrong thread pitch", "seal leaks", "a software checksum error"])
    if rng.random() < 0.4:
        facts = {"lot": lot["lot_id"], "defect": defect}
    else:
        only = g.find_lots(lot["supplier_id"], lot["part_id"], lot["plant_id"], lot["first_build_date"], lot["last_build_date"])
        if len(only) != 1:
            return scenario_quality(g, names, rng, messy)
        facts = {"supplier": names.supplier(lot["supplier_id"], messy), "part": names.part(lot["part_id"]),
                 "plant": names.plant(lot["plant_id"], messy), "defect": defect,
                 "first build date": phrase_for(date.fromisoformat(lot["first_build_date"]), rng, allow_relative=False),
                 "last build date": phrase_for(date.fromisoformat(lot["last_build_date"]), rng, allow_relative=False)}
    incident = {"kind": "quality_hold", "lots": [lot["lot_id"]]}
    return facts, "parts are defective; vehicles built with them must be held (a quality bulletin or defect notice)", incident


RUMOR_TOPICS = ["a seat supplier might be having money trouble", "a chip shortage could be coming",
                "a trucking strike may hit deliveries soon", "a plant might shut down for a while",
                "a batch of parts may be bad, nobody knows which", "a supplier may miss deliveries next month"]
NOISE_TOPICS = ["the cafeteria menu change at the {plant}", "a parking lot repaving at the {plant}",
                "a dealer asking for the new brochure PDF", "a reminder to submit expense reports",
                "weather far away with no effect on us", "a team volunteering day", "a plant tour request at the {plant}"]


def write(facts: dict, situation: str, rng: random.Random, kind: str, tries: int = 4) -> str | None:
    must = [v for k, v in facts.items() if k != "defect"]
    for attempt in range(tries):
        lines = "\n".join(f"- {k}: {v}" for k, v in facts.items())
        prompt = (
            "Write one short, realistic message (1 to 3 sentences) that a supplier, plant manager or coworker "
            "would send to the operations team of the carmaker Wacky Wheels. Sound like a real person: casual "
            "or terse, no greeting line, no signature.\n"
            f"What it is about: {situation}.\n"
            + (f"Facts. Use each value EXACTLY as written, word for word:\n{lines}\n" if facts else "")
            + ("Do not mention any other dates, plants, parts, suppliers, lots or shipments.\n" if kind != "noise" else "")
            + "Reply with the message only."
        )
        payload = {"model": WRITER, "stream": False, "think": False,
                   "options": {"temperature": 0.8, "seed": rng.randrange(10**6)},
                   "messages": [{"role": "user", "content": prompt}]}
        req = urllib.request.Request(f"{OLLAMA}/api/chat", json.dumps(payload).encode(), {"Content-Type": "application/json"})
        text = json.load(urllib.request.urlopen(req, timeout=300))["message"]["content"].strip().strip('"')
        if all(v.casefold() in text.casefold() for v in must):
            return text
    return None


def make_case(g, names, rng, kind, idx):
    messy = rng.random() < 0.5
    if kind in ("supplier_delay", "plant_outage", "quality_hold"):
        facts, situation, incident = {"supplier_delay": scenario_delay, "plant_outage": scenario_outage,
                                      "quality_hold": scenario_quality}[kind](g, names, rng, messy)
        text = write(facts, situation, rng, kind)
        return text and {"text": text, "expect": {"incidents": [incident], "escalate": False}, "edge": "messy" if messy else ""}
    if kind == "unconfirmed":
        text = write({}, "an unconfirmed rumor or hearsay: " + rng.choice(RUMOR_TOPICS) +
                     ". No specific plant, part, lot, shipment or date; make it clear nothing is confirmed", rng, kind)
        return text and {"text": text, "expect": {"incidents": [], "escalate": True}, "edge": "rumor"}
    plant = g.plants[rng.choice(sorted(g.plants))]["city"]
    topic = rng.choice(NOISE_TOPICS).format(plant=f"{plant} plant")
    text = write({}, "something unrelated to late deliveries, plants being down, or defective parts: " + topic, rng, "noise")
    return text and {"text": text, "expect": {"incidents": [], "escalate": False}, "edge": "names a plant" if "plant" in topic else ""}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=40)
    ap.add_argument("--out", default=os.path.join(HITACHI, "tests", "blind_cases.json"))
    ap.add_argument("--seed", type=int, default=1)
    cli = ap.parse_args()
    rng = random.Random(cli.seed)
    g = WorldGraph()
    names = Names(g, rng)
    # Harder mix: compound and messy messages weigh more than in the docx's six test cases.
    share = {"supplier_delay": 0.175, "plant_outage": 0.175, "quality_hold": 0.175, "unconfirmed": 0.125,
             "noise": 0.10, "compound": 0.25}
    plan = [k for k, f in share.items() for _ in range(round(f * cli.n))][: cli.n]
    rng.shuffle(plan)
    cases = []
    for i, kind in enumerate(plan, 1):
        case = None
        while case is None:
            if kind == "compound":
                a, b = rng.sample(["supplier_delay", "plant_outage", "quality_hold", "quality_hold", "unconfirmed", "noise"], 2)
                one, two = make_case(g, names, rng, a, i), make_case(g, names, rng, b, i)
                if one and two:
                    joint = rng.choice(["Two things: (1) {a} (2) {b}", "Morning digest. 1) {a} 2) {b}",
                                        "{a} Also, {b}", "First, {a} Second, {b}"])
                    case = {"text": joint.format(a=one["text"], b=two["text"]),
                            "expect": {"incidents": one["expect"]["incidents"] + two["expect"]["incidents"],
                                       "escalate": one["expect"]["escalate"] or two["expect"]["escalate"]},
                            "edge": f"compound {a}+{b}"}
            else:
                case = make_case(g, names, rng, kind, i)
        cases.append({"id": f"B-{i:03d}", "category": kind, "source": "blind", **case})
        print(f"{i}/{len(plan)} {kind}", flush=True)
    json.dump({"_note": f"BLIND. Written by {WRITER} from scenarios code picked in the tables (seed {cli.seed}). "
                        "Do not read these messages or tune the reader or prompts on them.", "cases": cases},
              open(cli.out, "w"), indent=1)
    print("wrote", cli.out)


if __name__ == "__main__":
    main()
