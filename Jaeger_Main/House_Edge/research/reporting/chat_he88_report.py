"""Export local, standalone quantitative research evidence without publishing it."""
import argparse
from collections import defaultdict
import csv
import html
import io
import json
from pathlib import Path

from ..analysis.chat_he88_evidence import audit_registry, calibration, comparison, context_key, load_export, trial_rows
from ..common import digest, file_hash, write_json


def export_report(registry_json, out, baseline_id=None, audit_root=None):
    from dashboard.he88_views import build_figures
    trials = load_export(registry_json)
    rows = trial_rows(trials)
    out = Path(out)
    if out.exists():
        raise FileExistsError("Use a new report destination to preserve earlier evidence")
    groups = defaultdict(list)
    for trial in trials:
        try:
            groups[context_key(trial)].append(trial)
        except ValueError:
            groups["incomplete_context"].append(trial)
    comparisons, diagnostic = [], {}
    baseline = next((t for t in trials if t["trial_id"] == baseline_id), None)
    if baseline_id and baseline is None:
        raise ValueError("Unknown baseline ID")
    for trial in trials:
        if trial["status"] == "SUCCEEDED":
            diagnostic[trial["trial_id"]] = calibration(trial)
            if baseline is not None and trial["trial_id"] != baseline_id:
                try:
                    comparisons.append(comparison(trial, baseline))
                except ValueError as exc:
                    comparisons.append({"candidate_id": trial["trial_id"], "baseline_id": baseline_id, "blocker": str(exc)})
    payload = {"schema": "jaegers.he88_comparison_report", "schema_version": 1,
               "input_content_sha256": json.loads(Path(registry_json).read_text())["content_sha256"],
               "reporting_source_sha256": {"reporter": file_hash(__file__),
                   "reader": file_hash(Path(__file__).parents[1]/"analysis/chat_he88_evidence.py"),
                   "views": file_hash(build_figures.__code__.co_filename)},
               "metric_source": "sampled_outcome_group_cv", "official_points": None,
               "trials": rows, "comparisons": comparisons, "diagnostics": diagnostic,
               "attempt_audit": audit_registry(audit_root) if audit_root else None,
               "limitations": ["Development-informed design; exploratory unadjusted intervals and multiple-comparison selection effects.",
                   "Trial wall time includes training/evaluation/setup; inference latency is unmeasured.",
                   "Raw feature distributions are unavailable; feature drift is unmeasured.",
                   "Public validation, MLflow and hidden-test metrics are outside this train-only report."]}
    payload["content_sha256"] = digest(payload)
    charts, includes_js = [], True
    for context, group in sorted(groups.items()):
        charts.append("<h2>Context " + html.escape(context[:16]) + "</h2>")
        if context == "incomplete_context":
            charts.append("<p>Missing comparison provenance; scored ranking unavailable.</p>")
            continue
        figures, blockers = build_figures(group, baseline_id=baseline_id)
        for name, figure in figures.items():
            charts.append(figure.to_html(full_html=False, include_plotlyjs=includes_js,
                                         div_id="he88-"+context[:12]+"-"+name))
            includes_js = False
        charts.extend("<p>"+html.escape(b)+"</p>" for b in blockers)
    fields = list(rows[0]) if rows else ["trial_id", "status", "mean_brier"]
    csv_text = io.StringIO()
    writer = csv.DictWriter(csv_text, fieldnames=fields, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    table_fields = ["trial_id", "family", "status", "mean_brier", "wall_seconds", "groups", "attempt"]
    table = "<table><thead><tr>" + "".join("<th>"+html.escape(f)+"</th>" for f in table_fields) + "</tr></thead><tbody>"
    for row in rows:
        table += "<tr>" + "".join("<td>"+html.escape(str(row.get(f) if row.get(f) is not None else "unavailable"))+"</td>" for f in table_fields) + "</tr>"
    table += "</tbody></table>"
    page = """<!doctype html><html><head><meta charset="utf-8"><title>House Edge research evidence</title>
<style>body{font-family:system-ui;margin:32px auto;max-width:1250px;padding:0 24px;color:#13263c;background:#f5f8fc}
h1{margin-bottom:8px}p{line-height:1.6}table{border-collapse:collapse;width:100%;font-size:13px;background:white}td,th{padding:10px;border-bottom:1px solid #d8e1ec;text-align:left;overflow-wrap:anywhere}td:first-child{max-width:130px}.plotly-graph-div{margin-top:24px}</style></head><body>
<h1>House Edge research evidence</h1><p>Train-only episode-grouped sampled Brier. Public validation remains development-exposed; hidden test quality is unavailable.</p>"""
    page += "<p>Input digest: "+html.escape(payload["input_content_sha256"])+"</p>"+table+"".join(charts)
    page += "<h2>Interpretation limits</h2><ul>"+"".join("<li>"+html.escape(x)+"</li>" for x in payload["limitations"])+"</ul></body></html>"
    # All validation occurs before creating outputs; prior reports are preserved.
    out.mkdir(parents=True, exist_ok=False)
    write_json(out/"comparison.json", payload)
    (out/"comparison.csv").write_text(csv_text.getvalue(), encoding="utf-8")
    (out/"index.html").write_text(page, encoding="utf-8")
    lines = ["# HE-88 local research evidence", "", "Metric: train-only grouped sampled-label Brier; no official points.", "",
             "| Family | Status | Brier | Trial wall seconds |", "|---|---|---:|---:|"]
    lines += [f"| {r['family']} | {r['status']} | {r['mean_brier']} | {r['wall_seconds']} |" for r in rows]
    lines += ["", "Input content SHA-256: "+payload["input_content_sha256"], "", *payload["limitations"]]
    (out/"report.md").write_text("\n".join(lines)+"\n", encoding="utf-8")
    return payload


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--registry", required=True, help="Portable v1 registry.json")
    parser.add_argument("--out", required=True)
    parser.add_argument("--baseline")
    parser.add_argument("--audit-root", help="Optional original single-host registry for all-attempt audit")
    args = parser.parse_args(argv)
    result = export_report(args.registry, args.out, args.baseline, args.audit_root)
    print(json.dumps({"content_sha256": result["content_sha256"], "trials": len(result["trials"]), "out": args.out}))


if __name__ == "__main__":
    main()
