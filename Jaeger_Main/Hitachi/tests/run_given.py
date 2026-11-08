"""Grade the 15 given events (data/events.json) against the docx test cases TC1-TC6.

    python tests/run_given.py                  # both readers
    python tests/run_given.py --reader rules   # deterministic reader only

Expected answers are in tests/given_cases.json. They were written by reading each
message by hand and looking ids up in the CSVs; the tower never reads that file.
Effects are graded by tests/run_cases.py's grader, which works from the CSVs, not
from tower/graph.py. On top of that, this script checks the evidence the docx asks
for per test case (graph path shape, reasons, three kinds of action).

Output: runs/given/<reader>/ and runs/given/REPORT.md
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
HITACHI = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, HITACHI)

import run_cases as rc  # noqa: E402
from tower.graph import WorldGraph  # noqa: E402

OUT = os.path.join(HITACHI, "runs", "given")
REAL = {"supplier_delay", "plant_outage", "quality_hold"}

# What each docx test case is about, and the graph-path evidence it requires.
TC = {
    "TC1": ("Supplier Delay", "Shipment → Part → Model (BOM) → ProductionOrder → CustomerOrder → Dealer / Customer"),
    "TC2": ("Plant Outage", "Plant → ProductionOrder → CustomerOrder → Dealer / Customer"),
    "TC3": ("Quality Hold", "Lot → ProductionOrder → Vehicle → Dealer / Customer"),
    "TC4": ("Noise", "the reason the event was judged not relevant"),
    "TC5": ("Compound Incident", "one graph path per incident"),
    "TC6": ("Unconfirmed Report", "the reason the report was not actionable"),
}


def load_cases():
    events = {e["event_id"]: e for e in json.load(open(os.path.join(rc.DATA, "events.json")))}
    data = json.load(open(os.path.join(HERE, "given_cases.json")))
    cases = data["cases"] if isinstance(data, dict) else data
    for case in cases:
        case["text"] = events[case["id"]]["text"]
        case["source"] = events[case["id"]]["source"]
    return cases


def _paths(trace):
    return [p for r in trace.get("results", []) for p in r.get("graph_paths", [])]


def _starts(paths, word):
    return [p for p in paths if p and p[0].startswith(word)]


def _chain(path, *words):
    """True when the path's elements start with these words, in this order."""
    it = iter(path)
    return all(any(step.startswith(w) for step in it) for w in words)


def evidence_checks(case, trace, rows):
    """The docx's 'Evidence Required' and completeness rules for one event. Returns (ok, note) pairs."""
    tc = case["tc"]
    paths = _paths(trace)
    writes = [r for r in rows if r["ok"] and r["tool"] in rc.WRITE_TOOLS]
    kinds = {r["tool"] for r in writes}
    checks = [("summary and reason recorded", bool(trace.get("summary")))]
    checks.append(("no failed tool calls", all(r["ok"] for r in rows)))
    if tc == "TC1":
        full = [p for p in paths if _chain(p, "Shipment", "Part", "Model", "ProductionOrder", "CustomerOrder", "Dealer")]
        checks.append(("graph path starts at the Shipment", bool(full)))
        if not full:
            part = [p for p in paths if _chain(p, "Part", "Model", "ProductionOrder", "CustomerOrder", "Dealer")]
            checks.append(("fallback path Part → … → Dealer / Customer", bool(part)))
    if tc in ("TC2", "TC5"):
        checks.append(("outage path Plant → PO → CO → Dealer / Customer",
                       any(_chain(p, "Plant", "ProductionOrder", "CustomerOrder", "Dealer") for p in paths)))
    if tc == "TC5":
        checks.append(("delay path for the second incident",
                       any(_chain(p, "ProductionOrder", "CustomerOrder", "Dealer") and p[0].split()[0] in ("Shipment", "Part")
                           for p in paths)))
    if tc == "TC3":
        checks.append(("lot path Lot → PO → Vehicle → Dealer / Customer",
                       any(_chain(p, "Lot", "ProductionOrder", "Vehicle", "Dealer") for p in paths)))
    if tc in ("TC1", "TC2", "TC3", "TC5"):
        checks.append((f"≥3 kinds of action (rule 9): {len(kinds)}", len(kinds) >= 3))
    if tc == "TC4":
        checks.append(("no calls at all", not rows))
    if tc == "TC6":
        tools = [r["tool"] for r in rows]
        reason = next((r["args"].get("reason") for r in rows if r["tool"] == "escalate"), "")
        checks.append(("escalate only, no writes", tools == ["escalate"]))
        checks.append(("escalation gives a reason", bool(reason)))
    return checks


def write_report(all_results, cases, traces_by_reader, rows_by_reader):
    names = list(all_results)
    lines = [
        "# Given test cases — the 15 events in `data/events.json`",
        "",
        "Each event is graded twice:",
        "",
        "1. **Effects**: the action log is compared with hand-written expected answers "
        "(`tests/given_cases.json`) by the independent CSV grader in `tests/run_cases.py`. "
        "It checks the right orders moved and no others, slots after the disruption, transfers only when "
        "the home plant is full, one notice per dealer with exactly its orders, loaners by tier, priority "
        "and pool, the lots held, stop-sale VINs and owners notified.",
        "2. **Evidence**: the graph path, reasons and action kinds the docx asks for per test case.",
        "",
        "## Summary by docx test case",
        "",
        "| Test case | Events | " + " | ".join(f"{n}: effects" for n in names) + " | Evidence | Required evidence |",
        "|---|---|" + "---|" * len(names) + "---|---|",
    ]
    for tc, (title, needed) in TC.items():
        ids = [c["id"] for c in cases if c["tc"] == tc]
        cells = []
        for n in names:
            res = [r for r in all_results[n] if r["id"] in ids]
            cells.append(f"{sum(r['verdict'] == 'PASS' for r in res)}/{len(res)}")
        ev_ok = all(ok for c in cases if c["tc"] == tc
                    for _, ok in evidence_checks(c, traces_by_reader[names[0]][c["id"]], rows_by_reader[names[0]][c["id"]]))
        lines.append(f"| {tc} {title} | {', '.join(ids)} | " + " | ".join(cells) + f" | {'✅' if ev_ok else '⚠'} | {needed} |")
    lines.append("")
    for n in names:
        p = sum(r["verdict"] == "PASS" for r in all_results[n])
        calls = sum(len(v) for v in rows_by_reader[n].values())
        failed = sum(not r["ok"] for v in rows_by_reader[n].values() for r in v)
        lines.append(f"- **{n}**: {p}/{len(cases)} events pass on effects · {calls} tool calls · {failed} failed")
    lines.append("")

    for n in names:
        lines += [f"## Details — {n} reader", ""]
        for case, r in zip(cases, all_results[n]):
            trace = traces_by_reader[n][case["id"]]
            rows = rows_by_reader[n][case["id"]]
            lines.append(f"### {case['id']} — {case['tc']} {TC[case['tc']][0]} — {r['verdict']}")
            lines.append(f"> {case['text']}")
            lines.append("")
            lines.append(f"- **Read as:** `{r['classification']}` (reader: {', '.join(map(str, r['readers']))})")
            for inc in trace.get("incidents", []):
                fields = {k: v for k, v in inc.items() if v and k not in ("summary", "evidence", "reader", "kind")}
                lines.append(f"  - {inc['kind']}: `{json.dumps(fields)}`")
            want = case["expect"]["incidents"]
            lines.append(f"- **Expected:** {json.dumps(want) if want else 'no incident'}; "
                         f"escalate={str(case['expect']['escalate']).lower()}")
            counts = Counter(row["tool"] for row in rows)
            lines.append(f"- **Calls:** {dict(counts) if counts else 'none'}")
            for x in r["fails"]:
                lines.append(f"- ❌ {x}")
            for x in r["warnings"]:
                lines.append(f"- ⚠ {x}")
            for label, ok in evidence_checks(case, trace, rows):
                lines.append(f"- {'✅' if ok else '⚠'} {label}")
            paths = _paths(trace)
            if paths:
                lines.append(f"- **Graph path (1 of {len(paths)}):** {' → '.join(paths[0])}")
            lines.append(f"- **Summary:** {trace.get('summary')}")
            lines.append("")
    path = os.path.join(OUT, "REPORT.md")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    return path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--reader", choices=("rules", "llm", "both"), default="both")
    args = ap.parse_args()
    rc.OUT = OUT  # rc.run writes each reader's log, traces and results under runs/given/
    cases = load_cases()
    truth, graph = rc.Truth(), WorldGraph()
    from tower.agents.llm_reader import MODEL

    readers = ["rules", "llm"] if args.reader == "both" else [args.reader]
    all_results, traces_by_reader, rows_by_reader = {}, {}, {}
    for reader in readers:
        name = "rules" if reader == "rules" else MODEL
        all_results[name] = rc.run(reader, cases, truth, graph)
        folder = os.path.join(OUT, "rules" if reader == "rules" else "llm_" + MODEL.replace(":", "_"))
        traces_by_reader[name] = {t["event_id"]: t for t in json.load(open(os.path.join(folder, "traces.json")))}
        rows = {c["id"]: [] for c in cases}
        for line in open(os.path.join(folder, "action_log.jsonl")):
            row = json.loads(line)
            rows[row["event_id"]].append(row)
        rows_by_reader[name] = rows
    print("report:", write_report(all_results, cases, traces_by_reader, rows_by_reader))


if __name__ == "__main__":
    main()
