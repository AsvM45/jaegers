"""Test reports for the dashboard: expected outcome, actual outcome and verdict for every case.

Two suites, each with one folder per reader under runs/:

    given      tests/given_cases.json  +  runs/given/<reader>/   (python tests/run_given.py)
    generated  tests/cases.json        +  runs/tests/<reader>/   (python tests/run_cases.py)

Expected output: each case's answer key ("expect" in the cases file) traced through the company
graph by tests/run_cases.py (CSV-based, independent of tower/graph.py) to every production order,
dealer, loaner, lot, vehicle and owner it touches. Actual output: that reader's action_log.jsonl.

Two scores per case:
  prediction   how well the reader predicted: incident type, records and dates, and the full
               output (every affected record), by comparing the two graphs' outputs in code.
  verdict      the grader's own (results.json), which also replays the actions in the enterprise
               simulator and checks them against the handbook: free slots, transfers, loaner
               priority, one notice per dealer, no failed calls.
Built on request and cached until any input file changes.
"""

from __future__ import annotations

import json
import os
import shutil
import sys
import threading
import time
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
HITACHI = os.path.abspath(os.path.join(HERE, "..", ".."))
TESTS = os.path.join(HITACHI, "tests")
RUNS = os.path.join(HITACHI, "runs")

SUITES = [
    {"id": "given", "title": "Given tests", "subtitle": "The 15 events in events.json, graded against docx TC1–TC6",
     "cases": "given_cases.json", "runs": "given"},
    {"id": "holdout2", "title": "Held-out tests (set 2)", "subtitle": "100 fresh messages, written after the fixes; never tuned on (tests/make_holdout2.py)",
     "cases": "holdout2_cases.json", "runs": "holdout2"},
    {"id": "holdout", "title": "Held-out tests (set 1)", "subtitle": "100 messages; used to diagnose the reader, so no longer blind (tests/make_holdout.py)",
     "cases": "holdout_cases.json", "runs": "holdout"},
    {"id": "generated", "title": "Generated tests", "subtitle": "100 messages: 25 hand-made edge cases + 75 from real records (tests/make_cases.py)",
     "cases": "cases.json", "runs": "tests"},
    {"id": "stress", "title": "Stress tests", "subtitle": "149 messages: 74 normal, 45 edge cases, 30 overload (tests/make_stress.py)",
     "cases": "stress_cases.json", "runs": "stress"},
]

_cache: dict = {"key": None, "data": None}
_lock = threading.Lock()


def _inputs() -> list[str]:
    """Every file the report depends on, for cache invalidation."""
    paths = []
    for suite in SUITES:
        paths.append(os.path.join(TESTS, suite["cases"]))
        folder = os.path.join(RUNS, suite["runs"])
        if os.path.isdir(folder):
            for name in sorted(os.listdir(folder)):
                for f in ("results.json", "action_log.jsonl"):
                    p = os.path.join(folder, name, f)
                    if os.path.isfile(p):
                        paths.append(p)
    return paths


MODEL_RUNS = os.path.join(RUNS, "model")


def _model_files() -> list[str]:
    if not os.path.isdir(MODEL_RUNS):
        return []
    return [os.path.join(MODEL_RUNS, d, f) for d in sorted(os.listdir(MODEL_RUNS))
            for f in ("summary.json", "results.json") if os.path.isfile(os.path.join(MODEL_RUNS, d, f))]


def model_eval() -> list[dict]:
    """tests/run_model.py results: each model on its own, scored against the expected graphs."""
    out = []
    for d in sorted(os.listdir(MODEL_RUNS)) if os.path.isdir(MODEL_RUNS) else []:
        s_path, r_path = os.path.join(MODEL_RUNS, d, "summary.json"), os.path.join(MODEL_RUNS, d, "results.json")
        if not os.path.isfile(s_path):
            continue
        with open(s_path, encoding="utf-8") as handle:
            summary = json.load(handle)
        misses = []
        if os.path.isfile(r_path):
            with open(r_path, encoding="utf-8") as handle:
                misses = [{k: r[k] for k in ("suite", "id", "category", "text", "mismatches", "expected", "predicted")}
                          for r in json.load(handle) if not r["output_ok"]]
        out.append(summary | {"id": d, "misses": misses})
    return out


def _key() -> tuple:
    return tuple((p, os.path.getmtime(p)) for p in _inputs() + _model_files() + [LOG] if os.path.exists(p))


def _load_cases(name: str) -> list[dict]:
    path = os.path.join(TESTS, name)
    if not os.path.isfile(path):
        return []
    with open(path, encoding="utf-8") as handle:
        data = json.load(handle)
    return data["cases"] if isinstance(data, dict) else data


def _label(folder_name: str) -> str:
    """'rules' stays; 'llm_qwen3_0.6b' becomes 'qwen3:0.6b'."""
    if folder_name.startswith("llm_"):
        return folder_name[4:].replace("_", ":", 1)
    return folder_name


def expected_outcome(rc, truth, case: dict) -> dict:
    exp = rc.expected_effects(truth, case)
    return {
        "incidents": case["expect"]["incidents"],
        "escalate": case["expect"]["escalate"],
        "moved": sorted(exp["earliest"]),
        "dealers": sorted(exp["notify"]),
        "loaners": sorted(exp["loaners"]),
        "lots": sorted(exp["lots"]),
        "stop_sale_vins": sorted(v for vins in exp["stop"].values() for v in vins),
        "owners": sorted(exp["owners"]),
    }


def actual_outcome(rows: list[dict], result: dict) -> dict:
    ok = [r for r in rows if r.get("ok")]

    def ids(tools, key):
        return sorted({r["args"][key] for r in ok if r["tool"] in tools and key in r["args"]})

    return {
        "incidents": [{k: v for k, v in inc.items() if k not in ("reader", "model_reason")} for inc in result.get("parsed", [])
                      if inc.get("kind") in ("supplier_delay", "plant_outage", "quality_hold")],
        # The model's explanation of every section it read, including noise and rumors.
        "reasoning": [inc["model_reason"] for inc in result.get("parsed", []) if inc.get("model_reason")],
        "escalate": any(r["tool"] == "escalate" for r in ok),
        "moved": ids(("mes.reschedule", "mes.transfer"), "production_order_id"),
        "transfers": sum(r["tool"] == "mes.transfer" for r in ok),
        "dealers": ids(("dealer.notify",), "dealer_id"),
        "loaners": ids(("crm.assign_loaner",), "customer_order_id"),
        "lots": ids(("quality.hold_lot",), "lot_id"),
        "stop_sale_vins": sorted({v for r in ok if r["tool"] == "dealer.stop_sale" for v in r["args"].get("vins", [])}),
        "owners": ids(("crm.notify_customer",), "customer_id"),
        "calls": len(rows),
        "failed": sum(not r.get("ok") for r in rows),
        "by_tool": dict(Counter(r["tool"] for r in rows)),
    }


# Output effects compared between expected and actual, with their labels.
EFFECTS = [("Orders moved", "moved"), ("Dealers notified", "dealers"), ("Loaners", "loaners"),
           ("Lots held", "lots"), ("Stop-sale vehicles", "stop_sale_vins"), ("Owners notified", "owners")]
# The fields that make a supply incident's prediction right. A quality hold is judged by its lots.
_KEYS = {"supplier_delay": ("plant_id", "part_id", "blocked_from", "blocked_until"),
         "plant_outage": ("plant_id", "outage_start", "outage_end")}


def _ids(items: list[str]) -> str:
    return ", ".join(items[:4]) + (" …" if len(items) > 4 else "")


def score_case(expected: dict, actual: dict) -> dict:
    """How well one prediction matches the expected output: kinds, records and dates, full output."""
    kinds_ok = (sorted(i["kind"] for i in expected["incidents"]) == sorted(i["kind"] for i in actual["incidents"])
                and expected["escalate"] == actual["escalate"])
    fields_ok = kinds_ok
    mismatches = []
    if not kinds_ok:
        mismatches.append(f"Incident type: expected {', '.join(sorted(i['kind'] for i in expected['incidents'])) or 'none'}"
                          f"{' + escalate' if expected['escalate'] else ''}; predicted "
                          f"{', '.join(sorted(i['kind'] for i in actual['incidents'])) or 'none'}"
                          f"{' + escalate' if actual['escalate'] else ''}.")
    else:
        for w in expected["incidents"]:
            keys = _KEYS.get(w["kind"])
            got = [g for g in actual["incidents"] if g["kind"] == w["kind"]]
            if keys and not any(all(g.get(k) == w[k] for k in keys) for g in got):
                fields_ok = False
                mismatches.append(f"{w['kind']}: expected " + ", ".join(f"{k} {w[k]}" for k in keys) + "; predicted "
                                  + "; ".join(", ".join(f"{k} {g.get(k)}" for k in keys) for g in got) + ".")
            elif not keys and not set(w.get("lots", [])) <= set(actual["lots"]):
                fields_ok = False
                mismatches.append(f"quality_hold: expected lot {', '.join(w.get('lots', []))}; held "
                                  f"{', '.join(actual['lots']) or 'none'}.")
    for label, key in EFFECTS:
        e, a = set(expected[key]), set(actual[key])
        if e != a:
            miss, extra = sorted(e - a), sorted(a - e)
            bits = ([f"{len(miss)} missing ({_ids(miss)})"] if miss else []) + \
                   ([f"{len(extra)} extra ({_ids(extra)})"] if extra else [])
            mismatches.append(f"{label}: expected {len(e)}, did {len(a)}: {'; '.join(bits)}.")
    return {"kinds_ok": kinds_ok, "fields_ok": fields_ok, "output_ok": not any(
                m.split(":")[0] in {lab for lab, _k in EFFECTS} for m in mismatches) and kinds_ok,
            "mismatches": mismatches}


def build() -> dict:
    if TESTS not in sys.path:
        sys.path.insert(0, TESTS)
    import run_cases as rc  # the independent grader

    truth = rc.Truth()
    with open(os.path.join(rc.DATA, "events.json"), encoding="utf-8") as handle:
        event_text = {e["event_id"]: e for e in json.load(handle)}

    suites = []
    for suite in SUITES:
        cases = _load_cases(suite["cases"])
        folder = os.path.join(RUNS, suite["runs"])
        readers = []
        for name in sorted(os.listdir(folder)) if os.path.isdir(folder) else []:
            res_path = os.path.join(folder, name, "results.json")
            if not os.path.isfile(res_path):
                continue
            with open(res_path, encoding="utf-8") as handle:
                results = {r["id"]: r for r in json.load(handle)}
            rows = defaultdict(list)
            log_path = os.path.join(folder, name, "action_log.jsonl")
            if os.path.isfile(log_path):
                with open(log_path, encoding="utf-8") as handle:
                    for line in handle:
                        if line.strip():
                            row = json.loads(line)
                            rows[row["event_id"]].append(row)
            items = []
            for case in cases:
                result = results.get(case["id"])
                if result is None:
                    continue
                event = event_text.get(case["id"], {})
                items.append({
                    "id": case["id"],
                    "category": case.get("category"),
                    "tc": case.get("tc"),
                    "edge": case.get("edge"),
                    "source": case.get("source") or event.get("source"),
                    "text": case.get("text") or event.get("text", ""),
                    "verdict": result["verdict"],
                    "fails": result.get("fails", []),
                    "warnings": result.get("warnings", []),
                    "classification": result.get("classification"),
                    "readers": result.get("readers", []),
                    "summary": result.get("summary"),
                    "expected": expected_outcome(rc, truth, case),
                    "actual": actual_outcome(rows[case["id"]], result),
                })
                items[-1]["score"] = score_case(items[-1]["expected"], items[-1]["actual"])
            readers.append({
                "id": name,
                "label": _label(name),
                "kind": "llm" if name.startswith("llm_") else "rules",
                "updated": time.strftime("%Y-%m-%d %H:%M", time.localtime(os.path.getmtime(res_path))),
                "passed": sum(i["verdict"] == "PASS" for i in items),
                "total": len(items),
                "scores": {k: sum(i["score"][k] for i in items) for k in ("kinds_ok", "fields_ok", "output_ok")}
                          | {"total": len(items)},
                "by_category": _by_category(items),
                "report_md": f"runs/{suite['runs']}/REPORT.md" if os.path.isfile(os.path.join(folder, "REPORT.md")) else None,
                "cases": items,
            })
        suites.append({k: suite[k] for k in ("id", "title", "subtitle")} | {"readers": readers})
    return {"suites": suites, "system_prompt": _system_prompt(), "model_eval": model_eval(), "log": run_log(suites)}


def _by_category(items: list[dict]) -> dict:
    out: dict = {}
    for i in items:
        c = out.setdefault(i["category"] or "other", {"passed": 0, "total": 0})
        c["passed"] += i["verdict"] == "PASS"
        c["total"] += 1
    return out


LOG = os.path.join(RUNS, "test_log.jsonl")


def run_log(suites: list[dict]) -> list[dict]:
    """Every test run, newest first, from runs/test_log.jsonl. Runs from before the log existed
    appear once each, dated by their results file."""
    rows = []
    if os.path.isfile(LOG):
        with open(LOG, encoding="utf-8") as handle:
            for line in handle:
                if line.strip():
                    try:
                        rows.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
    logged = {(r["suite"], r["reader"]) for r in rows}
    for s in suites:
        for r in s["readers"]:
            if (s["id"], r["id"]) not in logged:
                rows.append({"time": r["updated"] + ":00", "suite": s["id"], "reader": r["id"],
                             "passed": r["passed"], "total": r["total"],
                             "by_category": {k: [v["passed"], v["total"]] for k, v in r["by_category"].items()}})
    rows.sort(key=lambda r: r["time"], reverse=True)
    return rows[:300]


def _system_prompt() -> str | None:
    """The instructions the LLM reader sends ahead of each message. The rule reader has none."""
    if HITACHI not in sys.path:
        sys.path.insert(0, HITACHI)
    try:
        from tower.agents import llm_reader
    except Exception:  # noqa: BLE001 - the dashboard still works without the LLM module
        return None
    return getattr(llm_reader, "_SYSTEM", None)


def delete(suite_id: str, reader_id: str) -> bool:
    """Delete one report: the runs/<suite>/<reader>/ folder (results, traces, action log).

    Both names must match an existing suite and an existing folder inside it, so a crafted
    request cannot reach anything outside runs/. Returns False when there is nothing to delete.
    """
    suite = next((s for s in SUITES if s["id"] == suite_id), None)
    if suite is None:
        return False
    parent = os.path.realpath(os.path.join(RUNS, suite["runs"]))
    if not os.path.isdir(parent) or reader_id not in os.listdir(parent):
        return False
    target = os.path.realpath(os.path.join(parent, reader_id))
    if os.path.dirname(target) != parent or not os.path.isdir(target):
        return False
    shutil.rmtree(target)
    with _lock:
        _cache["key"] = None
    return True


def payload() -> dict:
    """Cached build; rebuilt when a cases file, results.json or action log changes."""
    key = _key()
    with _lock:
        if _cache["key"] != key:
            _cache["data"] = build()
            _cache["key"] = key
        return _cache["data"]


def write_summary(path: str = os.path.join(RUNS, "TEST_SUMMARY.md")) -> str:
    """Write runs/TEST_SUMMARY.md from the current results, so it never goes stale."""
    data = payload()
    lines = ["# Control tower — test summary", "",
             f"Written {time.strftime('%Y-%m-%d %H:%M')} from the saved results by `tower/ui/reports.py`. "
             "Each test's expected output is its answer key traced through the company graph (`tests/run_cases.py`, "
             "independent of `tower/graph.py`); the grader also replays every action in the enterprise simulator "
             "and checks it against the handbook.", "",
             "## The tower, per suite and reader", "",
             "| Suite | Reader | Incident type | Records and dates | Full output | Grader | Report |",
             "|---|---|---|---|---|---|---|"]
    for suite in data["suites"]:
        folder = next(s["runs"] for s in SUITES if s["id"] == suite["id"])
        for reader in suite["readers"]:
            sc, n = reader["scores"], reader["total"]
            lines.append(f"| {suite['title']} | {reader['label']} | {sc['kinds_ok']}/{n} | {sc['fields_ok']}/{n} | "
                         f"{sc['output_ok']}/{n} | {reader['passed']}/{n} | [{folder}/REPORT.md]({folder}/REPORT.md) |")
    lines += ["", "Suites: " + "; ".join(f"**{s['title']}**: {s['subtitle']}" for s in SUITES) + ".", ""]
    for m in data["model_eval"]:
        lines += [f"## {m['model']} on its own (no rule check)", "",
                  f"Run {m['run']} with `tests/run_model.py`: the model reads each message, code only looks up the "
                  "records and dates it named (one retry with feedback when they do not check out), and the reading "
                  "is traced through the graph and compared with the expected graph.", "",
                  "| Set | Incident type | Records and dates | Full output |", "|---|---|---|---|"]
        for name, x in m["suites"].items():
            n = x["total"]
            lines.append(f"| {name} | {x['kinds_ok']}/{n} | {x['fields_ok']}/{n} | {x['output_ok']}/{n} |")
        lines.append("")
    with open(path, "w", encoding="utf-8") as handle:
        handle.write("\n".join(lines) + "\n")
    return path


if __name__ == "__main__":
    if "--write-summary" in sys.argv:
        print("summary ->", write_summary())
    # How well each reader predicts, per suite.
    data = payload()
    print(f"{'suite':9} {'reader':12} {'type':>8} {'records+dates':>14} {'full output':>12} {'grader':>8}")
    for suite in data["suites"]:
        for reader in suite["readers"]:
            sc, n = reader["scores"], reader["total"]
            print(f"{suite['id']:9} {reader['label']:12} {sc['kinds_ok']:>4}/{n:<3} {sc['fields_ok']:>9}/{n:<4} "
                  f"{sc['output_ok']:>7}/{n:<4} {reader['passed']:>4}/{n}")
