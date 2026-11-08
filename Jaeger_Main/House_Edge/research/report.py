"""Read-only status and provenance-aware paired comparisons from real trial artifacts."""
import argparse
from collections import Counter
import json
from pathlib import Path
import sqlite3
from .common import canonical, digest, now, write_json
from .metrics import paired


def read_rows(root):
    path=Path(root).resolve()/"registry.sqlite"
    with sqlite3.connect(path.as_uri()+"?mode=ro",uri=True) as db:
        db.row_factory=sqlite3.Row
        return [dict(row) for row in db.execute("SELECT * FROM trials ORDER BY created_at,id")]


def evaluation_key(row):
    identity=json.loads(row["identity"])
    return digest({key:identity.get(key) for key in ("train_sha256","metadata_sha256","split_manifest_sha256","environment")})


def report(root,out,baseline=None):
    root,out=Path(root).resolve(),Path(out).resolve()
    out.mkdir(parents=True,exist_ok=False)
    rows=read_rows(root)
    succeeded=[r for r in rows if r["status"] == "SUCCEEDED"]
    baseline_row=None
    if baseline:
        selected=[r for r in succeeded if r["id"].startswith(baseline)]
        if len(selected) != 1:
            raise ValueError("Baseline must uniquely identify one completed trial")
        baseline_row=selected[0]
    comparisons=[]
    baseline_result=json.loads((Path(baseline_row["artifact"])/"result.json").read_text()) if baseline_row else None
    for row in sorted(succeeded,key=lambda r:r["mean_brier"]):
        config=json.loads(row["config"])
        result=json.loads((Path(row["artifact"])/"result.json").read_text())
        entry={"id":row["id"],"study":row["study"],"family":config["family"],"config":config,
               "mean_brier":result["mean_brier"],"by_condition":result["by_condition"],
               "log_loss":result["log_loss"],"wall_seconds":row["wall_seconds"],
               "validation_target_exposure":result["validation_target_exposure"],
               "evaluation_source":result["evaluation_source"],"evaluation_key":evaluation_key(row),
               "source_digest":digest(json.loads(row["identity"])["source_sha256"]),
               "official_points":None,"paired":None}
        if baseline_row:
            if evaluation_key(row) == evaluation_key(baseline_row):
                entry["paired"]=paired(result,baseline_result)
            else:
                entry["comparison_blocker"]="Different data, folds or runtime provenance"
        comparisons.append(entry)
    summary={"created_at":now(),"statuses":dict(Counter(r["status"] for r in rows)),
             "completed_runs":len(succeeded),"distinct_completed_configs":len({r["config"] for r in succeeded}),
             "completed_families":sorted({json.loads(r["config"])["family"] for r in succeeded}),
             "baseline":baseline_row["id"] if baseline_row else None,"comparisons":comparisons,
             "failures":[{"id":r["id"],"status":r["status"],"error":r["error"],"artifact":r["artifact"]}
                         for r in rows if r["status"] not in ("SUCCEEDED","PENDING","RUNNING")]}
    write_json(out/"report.json",summary)
    lines=["# House Edge experiment evidence", "", f"Generated {summary['created_at']}.", "",
           f"Completed runs: {len(succeeded)}; distinct configurations: {summary['distinct_completed_configs']}.",
           "Repeated source versions are separate runs, not additional scientific hypotheses.", "",
           "These are sampled-label episode-grouped Brier losses, not official competition points.","",
           "| Trial | Family | Brier ↓ | Seconds | Validation-target exposure |",
           "| --- | --- | ---: | ---: | --- |"]
    for r in comparisons:
        lines.append(f"| {r['id'][:12]} | {r['family']} | {r['mean_brier']:.6f} | {r['wall_seconds']:.2f} | {r['validation_target_exposure']} |")
    lines += ["", "## Condition diagnostics", "", "| Trial | stable | short_history | drift | shared_change |", "| --- | ---: | ---: | ---: | ---: |"]
    for r in comparisons:
        values=" | ".join(f"{r['by_condition'][c]:.6f}" for c in ("stable","short_history","drift","shared_change"))
        lines.append(f"| {r['id'][:12]} | {values} |")
    if baseline_row:
        lines += ["", "## Paired episode differences", "", "Negative values favor the candidate. Bootstrap resamples whole episodes within conditions.", ""]
        for r in comparisons:
            p=r["paired"]
            lines.append(f"- {r['id'][:12]}: delta {p['mean_delta_brier']:.6f}; 95% interval {p['ci95']}." if p else
                         f"- {r['id'][:12]}: comparison unavailable ({r['comparison_blocker']}).")
    lines += ["", "## Failures", ""]
    lines += [f"- {r['id'][:12]}: {r['status']}; inspect recorded attempt logs." for r in summary["failures"]] or ["None recorded."]
    (out/"report.md").write_text("\n".join(lines)+"\n",encoding="utf-8")
    print(json.dumps({k:v for k,v in summary.items() if k not in ("comparisons","failures")}),flush=True)
    return summary


if __name__ == "__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--registry",required=True)
    p.add_argument("--out",required=True)
    p.add_argument("--baseline")
    a=p.parse_args()
    report(a.registry,a.out,a.baseline)
