import collections
import json
import sys

def load(path):
    rows = [json.loads(line) for line in open(path, encoding="utf-8") if line.strip()]
    return rows

def key(row):
    return (row["event_id"], row["tool"], json.dumps(row["args"], sort_keys=True))

old = load(sys.argv[1])
new = load(sys.argv[2])
print("old", len(old), "new", len(new))
print("failed old", sum(not r["ok"] for r in old), "failed new", sum(not r["ok"] for r in new))
by_event = collections.defaultdict(lambda: [collections.Counter(), collections.Counter()])
for r in old:
    by_event[r["event_id"]][0][key(r)] += 1
for r in new:
    by_event[r["event_id"]][1][key(r)] += 1
for event in sorted(by_event):
    a, b = by_event[event]
    tools_a = collections.Counter(k[1] for k in a.elements())
    tools_b = collections.Counter(k[1] for k in b.elements())
    gone = a - b
    added = b - a
    flag = "" if not gone and not added else "  CHANGED"
    print(event, dict(tools_b), flag)
    for k in list(gone)[:8]:
        print("   -", k[1], k[2][:160])
    for k in list(added)[:8]:
        print("   +", k[1], k[2][:160])
    if len(gone) > 8 or len(added) > 8:
        print("   ...", len(gone), "removed,", len(added), "added")
