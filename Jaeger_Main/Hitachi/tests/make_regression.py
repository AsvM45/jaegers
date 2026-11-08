"""Add two regression cases for every holdout case the rule reader missed.

Each pair keeps the original answer key and says it two ways: a reschedule / quarantine /
"we're losing" wording, and a "won't show" / "QA hold" / "closed" wording. Compounds and rumors
are separate sections, so a second fact cannot swallow the first.
"""

from __future__ import annotations

import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
HITACHI = os.path.dirname(HERE)
sys.path.insert(0, HITACHI)
sys.path.insert(0, HERE)

from make_holdout import expected_graph  # noqa: E402
from run_cases import Truth  # noqa: E402

RUMOR = "Unclear reports that a supplier may miss deliveries next month."
LABELS = ("First", "Second", "Third")


def _fail_ids(dump: str) -> dict[str, list[str]]:
    current = None
    found = {"holdout": [], "holdout2": []}
    for line in open(dump, encoding="utf-8"):
        if line.startswith("holdout2 "):
            current = "holdout2"
        elif line.startswith("holdout "):
            current = "holdout"
        elif line.startswith("H2-") or line.startswith("H-"):
            found[current].append(line.split()[0])
    return found


def _quality_bits(graph, lots: list[str]) -> tuple[str, str, str, str, str]:
    lot = graph.lots[lots[0]]
    return lots[0], lot["part_id"], lot["supplier_id"], lot["plant_id"], lot["first_build_date"], lot["last_build_date"]


def _one(graph, inc: dict, variant: int) -> str:
    kind = inc["kind"]
    if kind == "supplier_delay":
        sup, part, plant = inc["supplier_id"], inc["part_id"], inc["plant_id"]
        start, end = inc["blocked_from"], inc["blocked_until"]
        if variant == 0:
            return (f"Voicemail from {sup}: the {part} order headed to {plant} is rescheduled "
                    f"from {start} to {end}.")
        return (f"{plant} receiving: the {part} truck from {sup} won't show {start}. "
                f"Carrier now quoting {end}.")
    if kind == "plant_outage":
        plant, start, end = inc["plant_id"], inc["outage_start"], inc["outage_end"]
        if variant == 0:
            return f"Heads up: we're losing {plant} for {start} through {end} (a boiler failure)."
        return f"{plant} closed {start} - {end} (a chemical spill)."
    lot, part, sup, plant, start, end = _quality_bits(graph, inc["lots"])
    if variant == 0:
        return (f"Please quarantine {lot}: seal leaks in {part}. {plant} builds {start} through {end}.")
    return (f"QA hold: lot {lot} ({part} from {sup}) used at {plant}, builds {start} to {end}. "
            f"Issue: brittle plastic clips.")


def _join(parts: list[str], variant: int) -> str:
    if len(parts) == 1:
        return parts[0]
    if variant == 0:
        return " ".join(f"({index}) {part}" for index, part in enumerate(parts, start=1))
    return " ".join(f"{LABELS[index]}, {part}" for index, part in enumerate(parts))


def _paraphrase(graph, case: dict, variant: int) -> str:
    expect = case["expect"]
    parts = [_one(graph, inc, variant) for inc in expect["incidents"]]
    if expect["escalate"]:
        parts.append(RUMOR)
    if not parts:
        return RUMOR if variant == 0 else (
            "Heard a supplier may miss a delivery sometime soon. Not confirmed."
        )
    return _join(parts, variant)


def _write_cases(path: str, data: dict) -> None:
    """One case per line, matching tests/make_holdout.py."""
    note = json.dumps(data["_note"], ensure_ascii=False)
    body = ",\n".join("  " + json.dumps(case, ensure_ascii=False) for case in data["cases"])
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        handle.write('{"_note": ' + note + ',\n "cases": [\n' + body + "\n]}\n")


def _append(path: str, suite: str, cases: list[dict], graphs: dict, truth) -> None:
    data = json.load(open(path, encoding="utf-8"))
    data["cases"].extend(cases)
    _write_cases(path, data)
    bucket = graphs.setdefault(suite, {})
    for case in cases:
        bucket[case["id"]] = expected_graph(truth, case["expect"])


def main() -> None:
    dump = os.path.join(HITACHI, "runs", "_fail_dump.txt")
    failed = _fail_ids(dump)
    truth = Truth()
    graphs = json.load(open(os.path.join(HERE, "expected_graphs.json"), encoding="utf-8"))
    added = False
    for suite, filename, prefix in (
        ("holdout", "holdout_cases.json", "H"),
        ("holdout2", "holdout2_cases.json", "H2"),
    ):
        path = os.path.join(HERE, filename)
        data = json.load(open(path, encoding="utf-8"))
        if any(case["id"].endswith("-101") or case["id"] == f"{prefix}-101" for case in data["cases"]):
            print(f"{suite}: regression cases already present")
            _write_cases(path, data)
            continue
        by_id = {case["id"]: case for case in data["cases"]}
        made = []
        number = 101
        for old_id in failed[suite]:
            case = by_id[old_id]
            for variant in (0, 1):
                made.append({
                    "id": f"{prefix}-{number}",
                    "category": case["category"],
                    "source": "regression",
                    "text": _paraphrase(truth, case, variant),
                    "expect": case["expect"],
                    "edge": f"regression of {old_id}",
                })
                number += 1
        _append(path, suite, made, graphs, truth)
        added = True
        print(f"{suite}: added {len(made)} cases ({prefix}-101..{prefix}-{number - 1})")
    if not added:
        return
    with open(os.path.join(HERE, "expected_graphs.json"), "w", encoding="utf-8") as handle:
        json.dump(graphs, handle, indent=1)
        handle.write("\n")


if __name__ == "__main__":
    main()
