"""Prove an unchanged study resumes without changing completed trial artifacts."""
import argparse
import json
from pathlib import Path
from .common import tree_hashes, write_json
from .registry import Registry
from .sweep import sweep


def check(spec,data,root,out):
    registry=Registry(root)
    before={r["id"]:r for r in registry.rows()}
    hashes={key:tree_hashes(row["artifact"]) for key,row in before.items() if row["status"] == "SUCCEEDED"}
    result=sweep(spec,data,root)
    after={r["id"]:r for r in registry.rows()}
    if before != after:
        raise AssertionError("Resume changed trial records or created new identities; inspect source/data/env changes")
    for key,expected in hashes.items():
        if tree_hashes(after[key]["artifact"]) != expected:
            raise AssertionError(f"Resume changed completed artifacts: {key}")
    evidence={"status":"PASSED","preserved_trials":len(hashes),"no_new_trials":True,
              "no_attempt_changes":True,"artifact_bytes_unchanged":True,"sweep":result}
    if Path(out).exists():
        raise FileExistsError("Refusing to overwrite resume evidence")
    write_json(out,evidence)
    print(json.dumps(evidence),flush=True)
    return evidence


if __name__ == "__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--study",required=True); p.add_argument("--data",required=True)
    p.add_argument("--registry",required=True); p.add_argument("--out",required=True)
    a=p.parse_args()
    check(json.loads(Path(a.study).read_text()),a.data,a.registry,a.out)
