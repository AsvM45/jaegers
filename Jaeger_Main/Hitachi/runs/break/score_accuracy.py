"""Score the breaker list against the rule reader. Prints misses only."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from tower.graph import WorldGraph
from tower.agents.understand import understand

KIND = {
    "noise": "noise",
    "unconfirmed": "unconfirmed",
    "plant_outage": "plant_outage",
    "supplier_delay": "supplier_delay",
    "quality_hold": "quality_hold",
}
graph = WorldGraph()
rows = json.loads(Path("runs/break/accuracy.json").read_text(encoding="utf-8"))
bad = 0
for row in rows:
    got = [i.kind for i in understand(graph, row["text"])]
    want = row["expected_kind"]
    if want in ("noise", "unconfirmed"):
        ok = got == [want]
    elif "+" in want:
        ok = got == want.split("+")
    else:
        ok = want in got and all(k != "noise" for k in got)
    if not ok:
        bad += 1
        print("MISS", want, "got", got)
        print("   ", row["text"])
print(f"{len(rows) - bad}/{len(rows)} matched")
