"""Run tests/cases.json through the control tower and grade the result.

    python tests/run_cases.py                  # both readers
    python tests/run_cases.py --reader rules   # deterministic reader only

The grader computes expected effects straight from the CSVs and the handbook
rules, from hand-written ground truth in cases.json. It does not use
tower/graph.py, so it is an independent check of the tower's own queries.
Output goes to runs/tests/<reader>/ plus runs/tests/REPORT.md.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
import time
from collections import defaultdict
from datetime import date, timedelta

HITACHI = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HITACHI)

from enterprise import LAST_IDX, Enterprise, ToolError, date_to_idx, idx_to_date  # noqa: E402
from tower.agents.coordinator import handle_event  # noqa: E402
from tower.graph import WorldGraph  # noqa: E402

DATA = os.path.join(HITACHI, "Data", "hack_the_highway_package", "data")
OUT = os.path.join(HITACHI, "runs", "tests")
CASES_NAME = "cases.json"
WRITE_TOOLS = {"mes.reschedule", "mes.transfer", "dealer.notify", "dealer.stop_sale",
               "crm.assign_loaner", "crm.notify_customer", "quality.hold_lot"}
SUPPLY_TOOLS = {"mes.reschedule", "mes.transfer", "dealer.notify", "crm.assign_loaner"}
QUALITY_TOOLS = {"quality.hold_lot", "dealer.stop_sale", "crm.notify_customer"}
# Loaner priority rank; tiers not listed here (Standard) get no loaner at all.
TIER = {"Platinum": 0, "Gold": 1}


def rd(name):
    """One company CSV as a list of row dicts."""
    with open(os.path.join(DATA, name), newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


class Truth:
    """The company tables, read independently of tower/graph.py."""

    def __init__(self):
        self.orders = {r["production_order_id"]: r for r in rd("production_orders.csv")}
        self.plant_models = defaultdict(set)
        for r in rd("plant_models.csv"):
            self.plant_models[r["plant_id"]].add(r["model"])
        self.slots = {r["plant_id"]: int(r["slots_per_day"]) for r in rd("plants.csv")}
        self.models_using = defaultdict(set)
        for r in rd("bom.csv"):
            self.models_using[r["part_id"]].add(r["model"])
        self.cos_by_po = defaultdict(list)
        self.cos = {}
        for r in rd("customer_orders.csv"):
            self.cos_by_po[r["production_order_id"]].append(r)
            self.cos[r["customer_order_id"]] = r
        self.customers = {r["customer_id"]: r for r in rd("customers.csv")}
        self.pool = {r["dealer_id"]: int(r["loaners_available"]) for r in rd("loaners.csv")}
        self.lots = {r["lot_id"]: r for r in rd("part_lots.csv")}
        self.vehicles = rd("finished_vehicles.csv")

    def idx(self, iso):
        """ISO date -> working-day index (enterprise.py's own mapping)."""
        return date_to_idx(date.fromisoformat(iso))

    def affected(self, inc):
        """{po: earliest allowed index} for one supply incident."""
        if inc["kind"] == "supplier_delay":
            lo, hi = self.idx(inc["blocked_from"]), self.idx(inc["blocked_until"])
            models = self.models_using[inc["part_id"]]
            return {po: hi for po, o in self.orders.items()
                    if o["plant_id"] == inc["plant_id"] and o["model"] in models
                    and lo <= self.idx(o["build_date"]) < hi and self.idx(o["build_date"]) >= 0}
        # Indexes count working days only, so hi + 1 is the next working day: the restart day.
        lo, hi = self.idx(inc["outage_start"]), self.idx(inc["outage_end"])
        return {po: hi + 1 for po, o in self.orders.items()
                if o["plant_id"] == inc["plant_id"] and lo <= self.idx(o["build_date"]) <= hi
                and self.idx(o["build_date"]) >= 0}

    def lot_vehicles(self, lot_id):
        """Rule 6: vehicles at the lot's plant, in its build dates, on models that use its part."""
        lot = self.lots[lot_id]
        models = self.models_using[lot["part_id"]]
        return [v for v in self.vehicles if v["plant_id"] == lot["plant_id"] and v["model"] in models
                and lot["first_build_date"] <= v["build_date"] <= lot["last_build_date"]]


def expected_effects(truth, case):
    """What the handbook says must happen for one case, from its hand-written incidents.

    Returns earliest allowed day per production order, dealer -> order ids to notify, loaner
    order ids, lots, dealer -> VINs to stop, and owners to contact. Exact dates are not fixed
    here; grade() checks them against the free slots instead.
    """
    inc_list = case["expect"]["incidents"]
    earliest = {}
    for inc in inc_list:
        if inc["kind"] in ("supplier_delay", "plant_outage"):
            for po, e in truth.affected(inc).items():
                earliest[po] = max(earliest.get(po, 0), e)
    cos = [co for po in earliest for co in truth.cos_by_po[po]]
    notify = defaultdict(set)
    for co in cos:
        notify[co["dealer_id"]].add(co["customer_order_id"])
    # Loaners: per dealer, sort eligible orders by (tier rank, promised date, id) and take as
    # many as the pool holds.
    entitled = defaultdict(list)
    for co in cos:
        tier = truth.customers[co["customer_id"]]["tier"]
        if tier in TIER:
            entitled[co["dealer_id"]].append((TIER[tier], co["promised_date"], co["customer_order_id"]))
    loaners = set()
    for dealer, rows in entitled.items():
        loaners.update(r[2] for r in sorted(rows)[: truth.pool[dealer]])
    lots, stop, owners = set(), defaultdict(set), set()
    for inc in inc_list:
        if inc["kind"] == "quality_hold":
            for lot in inc["lots"]:
                lots.add(lot)
                for v in truth.lot_vehicles(lot):
                    if v["status"] == "in_stock":
                        stop[v["dealer_id"]].add(v["vin"])
                    elif v["status"] == "sold" and v["customer_id"]:
                        owners.add(v["customer_id"])
    return {"earliest": earliest, "notify": dict(notify), "loaners": loaners,
            "lots": lots, "stop": dict(stop), "owners": owners}


class Logged:
    """Enterprise wrapper that records every call, including the error text of a failed one."""

    def __init__(self, enterprise):
        self.enterprise, self.records = enterprise, []

    def call(self, event_id, tool, args):
        # Append before calling, so a failing call is still in the log, marked ok=False.
        row = {"event_id": event_id, "tool": tool, "args": args, "ok": True}
        self.records.append(row)
        try:
            return self.enterprise.call(event_id, tool, args)
        except ToolError as exc:
            row["ok"], row["error"] = False, str(exc)
            raise


def grade(truth, case, rows, trace, state):
    """Return (verdict, fails, warnings, stats).

    A fail is a handbook violation; a warning is legal but worth a look (a failed call, a later
    slot than needed). state is the enterprise's end state for the case, used for slot checks.
    """
    fails, warns = [], []
    exp = expected_effects(truth, case)
    tools = [r["tool"] for r in rows]
    writes = [r for r in rows if r["tool"] in WRITE_TOOLS and r["ok"]]
    failed = [r for r in rows if not r["ok"]]
    if failed:
        warns.append(f"{len(failed)} failed call(s): " + "; ".join(
            f"{r['tool']} -> {r.get('error')}" for r in failed[:3]))

    # Classification and fields.
    got_inc = [i for i in trace["incidents"] if i["kind"] in ("supplier_delay", "plant_outage", "quality_hold")]
    want_inc = case["expect"]["incidents"]
    got_kinds = sorted(i["kind"] for i in got_inc)
    want_kinds = sorted(i["kind"] for i in want_inc)
    if got_kinds != want_kinds:
        fails.append(f"incident kinds {got_kinds or ['none']} expected {want_kinds or ['none']}")
    else:
        for want in want_inc:
            if want["kind"] == "quality_hold":
                continue
            # Several incidents of one kind (a compound case): compare with the closest one.
            cands = [g for g in got_inc if g["kind"] == want["kind"]]
            best = min(cands, key=lambda g: sum(g.get(k) != v for k, v in want.items()))
            diffs = [f"{k}={best.get(k)} (expected {v})" for k, v in want.items() if k != "kind" and best.get(k) != v]
            if diffs:
                fails.append(f"{want['kind']} fields: " + ", ".join(diffs))

    # Escalation.
    escalated = "escalate" in tools
    if case["expect"]["escalate"] and not escalated:
        fails.append("expected an escalate, none made")
    if not case["expect"]["escalate"] and escalated:
        fails.append("escalated although the event is actionable / noise")

    # Noise and unconfirmed cases stop here: any write at all is a fail.
    if not want_inc:
        if writes:
            fails.append(f"{len(writes)} write call(s) on a non-actionable event: {sorted(set(r['tool'] for r in writes))}")
        stats = {"writes": len(writes), "calls": len(rows)}
        return ("PASS" if not fails else "FAIL"), fails, warns, stats

    # Production orders.
    moved = {}
    for r in rows:
        if r["ok"] and r["tool"] in ("mes.reschedule", "mes.transfer"):
            moved[r["args"]["production_order_id"]] = r
    want_po = set(exp["earliest"])
    extra, missing = sorted(set(moved) - want_po), sorted(want_po - set(moved))
    if extra:
        fails.append(f"{len(extra)} unaffected PO(s) moved: {extra[:5]}")
    if missing:
        fails.append(f"{len(missing)} affected PO(s) not moved: {missing[:5]}")
    n_res = n_tr = 0
    for po, r in moved.items():
        if po not in want_po:
            continue
        home = truth.orders[po]["plant_id"]
        model = truth.orders[po]["model"]
        new_idx = truth.idx(r["args"]["new_date"])
        e = exp["earliest"][po]
        if r["tool"] == "mes.reschedule":
            n_res += 1
            if new_idx < e:
                fails.append(f"{po} rescheduled to {r['args']['new_date']}, before the disruption ends")
            # Only a warning: a slot that is free in the end state may have been taken by an earlier
            # order when this one was placed.
            free_earlier = [i for i in range(e, new_idx) if len(state["slots"][(home, i)]) < truth.slots[home]]
            if free_earlier:
                warns.append(f"{po} rescheduled to {r['args']['new_date']} though {home} still has a free slot on "
                             f"{idx_to_date(free_earlier[0])}")
        else:
            n_tr += 1
            dest = r["args"]["to_plant_id"]
            if model not in truth.plant_models[dest]:
                fails.append(f"{po} transferred to {dest}, which does not build {model}")
            # Rule 3: a transfer is allowed only when the home plant has no free day left. This uses
            # the end state, so a slot freed later in the same event also counts against it.
            home_free = [i for i in range(e, LAST_IDX + 1) if len(state["slots"][(home, i)]) < truth.slots[home]]
            if home_free:
                fails.append(f"{po} transferred but {home} has a free slot on {idx_to_date(home_free[0])} (end state)")

    # Dealers.
    notices = defaultdict(list)
    for r in rows:
        if r["ok"] and r["tool"] == "dealer.notify":
            notices[r["args"]["dealer_id"]].append(set(r["args"]["customer_order_ids"]))
    for d, lists in notices.items():
        if len(lists) > 1:
            fails.append(f"dealer {d} notified {len(lists)} times")
    if set(notices) != set(exp["notify"]):
        fails.append(f"dealer set: extra {sorted(set(notices) - set(exp['notify']))[:5]}, "
                     f"missing {sorted(set(exp['notify']) - set(notices))[:5]}")
    for d in sorted(set(notices) & set(exp["notify"])):  # sorted: same report every run
        got = set().union(*notices[d])
        if got != exp["notify"][d]:
            fails.append(f"dealer {d} order list: extra {sorted(got - exp['notify'][d])[:3]}, "
                         f"missing {sorted(exp['notify'][d] - got)[:3]}")

    # Loaners.
    got_loan = {r["args"]["customer_order_id"] for r in rows if r["ok"] and r["tool"] == "crm.assign_loaner"}
    if got_loan != exp["loaners"]:
        fails.append(f"loaners: extra {sorted(got_loan - exp['loaners'])[:5]}, "
                     f"missing {sorted(exp['loaners'] - got_loan)[:5]}")

    # Quality.
    got_lots = {r["args"]["lot_id"] for r in rows if r["ok"] and r["tool"] == "quality.hold_lot"}
    if got_lots != exp["lots"]:
        fails.append(f"lots held {sorted(got_lots)} expected {sorted(exp['lots'])}")
    stops = defaultdict(set)
    for r in rows:
        if r["ok"] and r["tool"] == "dealer.stop_sale":
            stops[r["args"]["dealer_id"]].update(r["args"]["vins"])
    if stops != exp["stop"]:
        got_v = set().union(*stops.values()) if stops else set()
        want_v = set().union(*exp["stop"].values()) if exp["stop"] else set()
        fails.append(f"stop-sale VINs: got {len(got_v)} expected {len(want_v)} "
                     f"(extra {sorted(got_v - want_v)[:3]}, missing {sorted(want_v - got_v)[:3]})")
    owners = {r["args"]["customer_id"] for r in rows if r["ok"] and r["tool"] == "crm.notify_customer"}
    if owners != exp["owners"]:
        fails.append(f"owners notified: got {len(owners)} expected {len(exp['owners'])} "
                     f"(extra {sorted(owners - exp['owners'])[:3]}, missing {sorted(exp['owners'] - owners)[:3]})")

    # Rule 9 (completeness) is a warning only: a tiny incident can legitimately need fewer kinds.
    kinds = {r["tool"] for r in writes}
    if len(kinds) < 3:
        warns.append(f"only {len(kinds)} kind(s) of write action (handbook rule 9 wants 3)")

    stats = {"writes": len(writes), "calls": len(rows), "moved": len(moved), "rescheduled": n_res,
             "transferred": n_tr, "expected_moves": len(want_po), "dealers": len(notices),
             "loaners": len(got_loan), "lots": sorted(got_lots), "stop_sale_vins": sum(len(v) for v in stops.values()),
             "owners": len(owners)}
    return ("PASS" if not fails else "FAIL"), fails, warns, stats


def run(reader_name, cases, truth, graph):
    """Run every case through handle_event with one reader, grade it, and save the run files.

    One Enterprise serves all cases; it keeps a separate world per event id, and the case id
    is the event id.
    """
    llm = None
    if reader_name == "llm":
        from tower.agents.llm_reader import LLMReader
        llm = LLMReader()
    enterprise = Enterprise(DATA)
    logged = Logged(enterprise)
    results, traces = [], []
    for case in cases:
        event = {"event_id": case["id"], "received_at": "2027-03-08T08:00:00",
                 "source": case["source"], "text": case["text"]}
        # This case's calls are the log rows added from here on.
        start = len(logged.records)
        t0 = time.time()
        try:
            trace = handle_event(graph, logged, event, llm).to_dict()
            crash = None
        except Exception as exc:  # report crashes as failures, keep going
            trace = {"event_id": case["id"], "incidents": [], "summary": "", "classification": "CRASH"}
            crash = f"{type(exc).__name__}: {exc}"
        rows = logged.records[start:]
        verdict, fails, warns, stats = grade(truth, case, rows, trace, enterprise.state(case["id"]))
        if crash:
            verdict, fails = "FAIL", [f"crashed: {crash}"] + fails
        traces.append(trace)
        results.append({
            "id": case["id"], "category": case["category"], "edge": case.get("edge"),
            "verdict": verdict, "fails": fails, "warnings": warns, "stats": stats,
            "classification": trace.get("classification"),
            "readers": [i.get("reader") for i in trace.get("incidents", [])],
            "parsed": [{k: v for k, v in i.items() if v and k not in ("summary", "evidence")}
                       for i in trace.get("incidents", [])],
            "summary": trace.get("summary"), "seconds": round(time.time() - t0, 1),
        })
        print(f"[{reader_name}] {case['id']} {verdict:4} {case['category']:15} {trace.get('classification')}")
    out = os.path.join(OUT, reader_name if llm is None else "llm_" + llm.model.replace(":", "_"))
    os.makedirs(out, exist_ok=True)
    with open(os.path.join(out, "action_log.jsonl"), "w") as f:
        for r in logged.records:
            f.write(json.dumps(r) + "\n")
    json.dump(traces, open(os.path.join(out, "traces.json"), "w"), indent=2)
    json.dump(results, open(os.path.join(out, "results.json"), "w"), indent=2)
    log_run(os.path.basename(OUT), os.path.basename(out), results)
    return results


# runs/ folder -> the dashboard's suite id.
SUITE_OF_FOLDER = {"given": "given", "tests": "generated", "holdout": "holdout", "holdout2": "holdout2",
                    "stress": "stress", "accuracy": "accuracy"}


def log_run(folder, reader, results):
    """Append one line per test run to runs/test_log.jsonl: the history the dashboard's run log shows."""
    by_cat = defaultdict(lambda: [0, 0])
    for r in results:
        by_cat[r["category"]][0] += r["verdict"] == "PASS"
        by_cat[r["category"]][1] += 1
    entry = {"time": time.strftime("%Y-%m-%d %H:%M:%S"), "suite": SUITE_OF_FOLDER.get(folder, folder),
             "folder": folder, "reader": reader, "passed": sum(r["verdict"] == "PASS" for r in results),
             "total": len(results), "by_category": dict(by_cat)}
    with open(os.path.join(HITACHI, "runs", "test_log.jsonl"), "a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry) + "\n")


def report(all_results, cases):
    """Write runs/tests/REPORT.md: a pass/fail table per reader, then details per case."""
    title = {"cases.json": "generated tests", "holdout_cases.json": "held-out tests, set 1",
             "holdout2_cases.json": "held-out tests, set 2",
             "stress_cases.json": "stress tests",
             "accuracy_cases.json": "accuracy paraphrases"}.get(CASES_NAME, CASES_NAME)
    lines = [f"# Hitachi control tower — {title}", "",
             f"{len(cases)} cases from `tests/{CASES_NAME}`, graded by `tests/run_cases.py` against "
             "expected effects computed from the CSVs (not from tower/graph.py).", ""]
    names = list(all_results)
    lines.append("| Case | Category | " + " | ".join(names) + " | Edge case? |")
    lines.append("|---|---|" + "---|" * len(names) + "---|")
    for i, case in enumerate(cases):
        cells = []
        for n in names:
            r = all_results[n][i]
            cells.append(r["verdict"] + (" ⚠" if r["warnings"] else ""))
        lines.append(f"| {case['id']} | {case['category']} | " + " | ".join(cells) + f" | {'yes' if case.get('edge') else ''} |")
    lines.append("")
    for n in names:
        p = sum(r["verdict"] == "PASS" for r in all_results[n])
        lines.append(f"**{n}**: {p}/{len(cases)} pass")
    lines.append("")
    for n in names:
        lines += [f"## Details — {n} reader", ""]
        for r, case in zip(all_results[n], cases):
            lines.append(f"### {r['id']} — {r['category']} — {r['verdict']}")
            lines.append(f"> {case['text']}".replace("\n", " "))
            if r["edge"]:
                lines.append(f"- Edge: {r['edge']}")
            lines.append(f"- Read as: `{r['classification']}` (reader: {', '.join(map(str, r['readers']))})")
            lines.append(f"- Stats: {json.dumps(r['stats'])}")
            for x in r["fails"]:
                lines.append(f"- FAIL: {x}")
            for x in r["warnings"]:
                lines.append(f"- warn: {x}")
            lines.append("")
    path = os.path.join(OUT, "REPORT.md")
    open(path, "w", encoding="utf-8").write("\n".join(lines) + "\n")
    return path


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--reader", choices=("rules", "llm", "both"), default="both")
    ap.add_argument("--cases", default=os.path.join(HITACHI, "tests", "cases.json"),
                    help="cases file (default tests/cases.json; tests/holdout_cases.json for the held-out set)")
    ap.add_argument("--out", help="output folder (default runs/tests)")
    args = ap.parse_args()
    if args.out:
        OUT = os.path.abspath(args.out)
    CASES_NAME = os.path.basename(args.cases)
    data = json.load(open(args.cases))
    cases = data["cases"] if isinstance(data, dict) else data
    truth, graph = Truth(), WorldGraph()
    readers = ["rules", "llm"] if args.reader == "both" else [args.reader]
    from tower.agents.llm_reader import MODEL
    all_results = {(n if n == "rules" else MODEL): run(n, cases, truth, graph) for n in readers}
    print("report:", report(all_results, cases))
