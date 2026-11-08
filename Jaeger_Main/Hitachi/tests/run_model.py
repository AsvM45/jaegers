"""How good is the model itself? Score the LLM reader alone against the expected graphs.

    python tests/run_model.py                                  # qwen3:0.6b on held-out + given
    TOWER_LLM_MODEL=qwen3:1.7b python tests/run_model.py       # another model
    python tests/run_model.py --suite holdout --limit 10       # a quick look

In the tower, the model's reading is only used when the rule reader agrees with it, so the tower's
scores cannot show how good the model is. This runner takes the rule reader out:

1. The model reads each message section (numbered "(1) (2)" items are split, as in the tower)
   and returns its kind and the words it saw for the plant, part, supplier, lot and dates.
2. Code only looks those words up in the tables (tower.agents.understand.checked_model_reading):
   no rule reader, no fallback, no veto. A reading that fails gets one retry with the reason. A reading whose words are not in the message or do not
   resolve to a record would be escalated, so it counts as "unconfirmed".
3. The model's incidents are traced through the company graph (tests/run_cases.py), exactly
   like the answer keys were for tests/expected_graphs.json, and the two graphs are compared.

Per case: incident type right, records and dates right, full output right (every production
order, dealer, loaner, lot, stop-sale vehicle and owner). Written to runs/model/<model>/.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from collections import defaultdict

HITACHI = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TESTS = os.path.join(HITACHI, "tests")
for p in (HITACHI, TESTS):
    if p not in sys.path:
        sys.path.insert(0, p)

import run_cases as rc  # noqa: E402
from tower.agents import understand  # noqa: E402
from tower.agents.llm_reader import MODEL, LLMReader, LLMUnavailable  # noqa: E402
from tower.agents.quality import _select_lots  # noqa: E402
from tower.graph import WorldGraph  # noqa: E402

GRAPHS = os.path.join(TESTS, "expected_graphs.json")
SUITES = {"holdout2": "holdout2_cases.json", "holdout": "holdout_cases.json", "given": "given_cases.json"}
EFFECTS = [("Production orders moved", "production_orders"), ("Dealers notified", "dealers_notified"),
           ("Loaners", "loaners"), ("Lots held", "lots"), ("Stop-sale vehicles", "stop_sale_vins"),
           ("Owners notified", "owners_notified")]
KEYS = {"supplier_delay": ("plant_id", "part_id", "blocked_from", "blocked_until"),
        "plant_outage": ("plant_id", "outage_start", "outage_end")}


def _cases(name: str) -> list[dict]:
    data = json.load(open(os.path.join(TESTS, SUITES[name]), encoding="utf-8"))
    return data["cases"] if isinstance(data, dict) else data


def _texts() -> dict:
    return {e["event_id"]: e["text"] for e in json.load(open(os.path.join(rc.DATA, "events.json")))}


def model_reading(graph, llm, text: str) -> tuple[list[dict], list[dict]]:
    """The model's incidents for one message, in answer-key format, and what it said per incident.

    This is exactly the tower's reading (tower.agents.understand with the model): step 1 the model
    names the kind and why, step 2 it picks records and dates from candidates found in the tables,
    and code checks the picks. No word lists take part. If the model gives no usable answer the
    tower would fall back to the rule reader; here that counts as unconfirmed, so the score is the
    model's alone."""
    incidents, said = [], []
    for inc in understand.understand(graph, text, llm=llm):
        entry = {"kind": inc.kind, "reader": inc.reader, "summary": inc.summary, "evidence": inc.evidence[:6]}
        if inc.reader == "rules":
            incidents.append({"kind": "unconfirmed", "why": "model gave no usable answer"})
        elif inc.kind in ("noise", "unconfirmed"):
            incidents.append({"kind": inc.kind})
        elif inc.kind == "supplier_delay":
            incidents.append({"kind": inc.kind, "supplier_id": inc.supplier_id, "part_id": inc.part_id,
                              "plant_id": inc.plant_id, "blocked_from": inc.blocked_from,
                              "blocked_until": inc.blocked_until})
        elif inc.kind == "plant_outage":
            incidents.append({"kind": inc.kind, "plant_id": inc.plant_id, "outage_start": inc.outage_start,
                              "outage_end": inc.outage_end})
        else:
            lots, note = _select_lots(graph, inc)
            if lots:
                incidents.append({"kind": inc.kind, "lots": sorted(l["lot_id"] for l in lots)})
            else:
                entry["problem"] = note
                incidents.append({"kind": "unconfirmed", "why": note})
        said.append(entry)
    return incidents, said


def predicted_graph(truth, incidents: list[dict]) -> dict:
    """The model's incidents traced through the company graph, like the answer keys were."""
    real = [{k: v for k, v in i.items() if k != "why"} for i in incidents if i["kind"] in KEYS or i["kind"] == "quality_hold"]
    eff = rc.expected_effects(truth, {"expect": {"incidents": real, "escalate": False}})
    return {
        "incidents": real,
        "escalate": any(i["kind"] == "unconfirmed" for i in incidents),
        "production_orders": sorted(eff["earliest"]),
        "dealers_notified": sorted(eff["notify"]),
        "loaners": sorted(eff["loaners"]),
        "lots": sorted(eff["lots"]),
        "stop_sale_vins": sorted(v for vins in eff["stop"].values() for v in vins),
        "owners_notified": sorted(eff["owners"]),
    }


def score(expected: dict, got: dict) -> dict:
    kinds = lambda g: sorted(i["kind"] for i in g["incidents"])  # noqa: E731
    kinds_ok = kinds(expected) == kinds(got) and expected["escalate"] == got["escalate"]
    fields_ok = kinds_ok
    misses = []
    if not kinds_ok:
        misses.append(f"Type: expected {', '.join(kinds(expected)) or 'none'}{' + escalate' if expected['escalate'] else ''}; "
                      f"model read {', '.join(kinds(got)) or 'none'}{' + escalate' if got['escalate'] else ''}.")
    else:
        for w in expected["incidents"]:
            keys = KEYS.get(w["kind"])
            same = [g for g in got["incidents"] if g["kind"] == w["kind"]]
            ok = (any(all(g.get(k) == w[k] for k in keys) for g in same) if keys
                  else any(set(w["lots"]) <= set(g.get("lots", [])) for g in same))
            if not ok:
                fields_ok = False
                want = ", ".join(f"{k} {w[k]}" for k in keys) if keys else "lot " + ", ".join(w["lots"])
                read = "; ".join(", ".join(f"{k} {g.get(k)}" for k in keys) if keys else "lots " + ", ".join(g.get("lots", []))
                                 for g in same)
                misses.append(f"{w['kind']}: expected {want}; model read {read}.")
    output_ok = kinds_ok
    for label, key in EFFECTS:
        e, a = set(expected[key]), set(got[key])
        if e != a:
            output_ok = False
            misses.append(f"{label}: expected {len(e)}, model's reading gives {len(a)} "
                          f"({len(e - a)} missing, {len(a - e)} extra).")
    return {"kinds_ok": kinds_ok, "fields_ok": fields_ok, "output_ok": output_ok, "mismatches": misses}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--suite", choices=("all", *SUITES), default="all")
    ap.add_argument("--limit", type=int, help="only the first N cases of each suite")
    ap.add_argument("--tag", default="", help="suffix for the output folder, to keep experiments apart")
    cli = ap.parse_args()
    graphs = json.load(open(GRAPHS))
    truth, graph, llm, texts = rc.Truth(), WorldGraph(), LLMReader(), _texts()
    rows = []
    for suite in (SUITES if cli.suite == "all" else [cli.suite]):
        for case in _cases(suite)[: cli.limit]:
            text = case.get("text") or texts[case["id"]]
            t0 = time.time()
            incidents, said = model_reading(graph, llm, text)
            got = predicted_graph(truth, incidents)
            sc = score(graphs[suite][case["id"]], got)
            rows.append({"suite": suite, "id": case["id"], "category": case.get("category"), "text": text,
                         "expected": {k: graphs[suite][case["id"]][k] for k in ("incidents", "escalate")},
                         "predicted": {k: got[k] for k in ("incidents", "escalate")}, "model_said": said,
                         **sc, "seconds": round(time.time() - t0, 1)})
            mark = "OK  " if sc["output_ok"] else "MISS"
            print(f"[{llm.model}] {suite:7} {case['id']:6} {mark} {case.get('category', ''):15} "
                  f"{'' if sc['output_ok'] else sc['mismatches'][0][:90]}", flush=True)
    out = os.path.join(HITACHI, "runs", "model", llm.model.replace(":", "_") + (f"_{cli.tag}" if cli.tag else ""))
    os.makedirs(out, exist_ok=True)
    summary = {"model": llm.model, "run": time.strftime("%Y-%m-%d %H:%M"), "suites": {}}
    for suite in dict.fromkeys(r["suite"] for r in rows):
        rs = [r for r in rows if r["suite"] == suite]
        by_kind = defaultdict(lambda: {"total": 0, "kinds_ok": 0, "fields_ok": 0, "output_ok": 0})
        for r in rs:
            for k in ("total", "kinds_ok", "fields_ok", "output_ok"):
                by_kind[r["category"]][k] += 1 if k == "total" else r[k]
        summary["suites"][suite] = {"total": len(rs), **{k: sum(r[k] for r in rs) for k in ("kinds_ok", "fields_ok", "output_ok")},
                                    "seconds": round(sum(r["seconds"] for r in rs), 1), "by_kind": dict(by_kind)}
    json.dump(rows, open(os.path.join(out, "results.json"), "w"), indent=1)
    json.dump(summary, open(os.path.join(out, "summary.json"), "w"), indent=1)
    with open(os.path.join(HITACHI, "runs", "test_log.jsonl"), "a", encoding="utf-8") as handle:
        for suite, s in summary["suites"].items():
            handle.write(json.dumps({"time": time.strftime("%Y-%m-%d %H:%M:%S"), "suite": suite, "folder": "model",
                                     "reader": f"{llm.model} alone", "passed": s["output_ok"], "total": s["total"],
                                     "by_category": {k: [v["output_ok"], v["total"]] for k, v in s["by_kind"].items()}})
                         + "\n")
    print(f"\n{llm.model} on its own (no rule check), vs the expected graphs:")
    for suite, s in summary["suites"].items():
        n = s["total"]
        print(f"  {suite:8} type {s['kinds_ok']}/{n}   records+dates {s['fields_ok']}/{n}   full output {s['output_ok']}/{n}")
        for kind, k in sorted(s["by_kind"].items()):
            print(f"      {kind:15} {k['output_ok']}/{k['total']}")
    print(f"-> {out}")


if __name__ == "__main__":
    main()
