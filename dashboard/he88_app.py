"""Read-only HE-88 research evidence viewer.

From repo root: python -m streamlit run dashboard/he88_app.py --server.address 127.0.0.1
"""
from pathlib import Path
import json
import os
import sqlite3
import sys

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

import pandas as pd
import streamlit as st

from dashboard.he88_views import build_figures, filter_trials
from Jaeger_Main.House_Edge.research.analysis.chat_he88_evidence import (
    CONDITIONS, audit_registry, calibration, load_export, trial_rows,
)
from Jaeger_Main.House_Edge.research.common import digest


def main():
    st.set_page_config(page_title="House Edge · Research evidence", layout="wide")
    st.title("House Edge research evidence")
    st.caption("Train-only episode-grouped sampled Brier · five payout classes · local read-only evidence")
    default = os.environ.get("JAEGERS_HE88_REGISTRY", str(REPO/"Jaeger_Main/House_Edge/research_runs/he88_acceptance/exports/v1/registry.json"))
    source = st.sidebar.text_input("Portable registry JSON", default)
    if not Path(source).is_file():
        st.info("No registry export at this path. Select an existing v1 portable export to inspect real runs.")
        return
    try:
        trials = load_export(source)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        st.error("Evidence unavailable: " + str(exc))
        return
    if not trials:
        st.info("No runs yet in this registry.")
        return
    rows = trial_rows(trials)
    contexts = sorted({r["context"] for r in rows if r["context"]})
    filters = {}
    if contexts:
        selected_context = st.sidebar.selectbox("Comparable data / fold / runtime context", contexts,
                                               format_func=lambda s: s[:16])
        filters["context"] = [selected_context]
    else:
        st.warning("Comparison context is incomplete. Inspect provenance before interpreting scores.")
    for label, key in (("Family", "family"), ("Outcome", "status"), ("Source", "source_sha256"),
                       ("Dataset", "data_sha256"), ("Feature source", "feature_sha256"), ("Fold manifest", "split_sha256")):
        choices = sorted({r[key] for r in rows if r.get(key) is not None})
        filters[key] = st.sidebar.multiselect(label, choices, format_func=lambda s: str(s)[:32])
    groups = sorted({g for t in trials for g in t.get("hyperparameters", {}).get("groups", [])})
    required = st.sidebar.multiselect("Required feature groups", groups)
    param_text = st.sidebar.text_input("Hyperparameter text")
    selected = filter_trials(trials, filters, required, param_text)
    if not selected:
        st.info("No runs match these filters.")
        return
    frame = pd.DataFrame(trial_rows(selected))
    total, success, failures = st.columns(3)
    total.metric("Selected trials", len(selected))
    success.metric("Succeeded", int((frame.status == "SUCCEEDED").sum()))
    failures.metric("Failed / interrupted", int(frame.status.isin(["FAILED", "TIMEOUT", "MEMORY_LIMIT", "INTERRUPTED", "CANCELLED"]).sum()))
    st.dataframe(frame, hide_index=True)
    if any(t.get("result", {}).get("historical_signal_policy") == "unsupported_copied_signal" for t in selected):
        st.warning("The frozen champion anchor retains the documented historical copied-signal caveat. This view grants no promotion or compliance certification.")
    if frame.warning.notna().any():
        st.warning("Some runs have incomplete comparison provenance and cannot be ranked together.")
    successful = [t for t in selected if t["status"] == "SUCCEEDED"]
    ids = [t["trial_id"] for t in successful]
    names = {t["trial_id"]: t["family"] + " · " + t["trial_id"][:12] for t in successful}
    baseline = st.selectbox("Paired baseline", ids, format_func=names.get) if ids else None
    diagnostic = st.selectbox("Calibration and probability diagnostics", ids, format_func=names.get) if ids else None
    parameters = sorted({k for t in successful for k, v in t["hyperparameters"].get("params", {}).items() if type(v) in (int, float)})
    parameter = st.selectbox("Parameter association", parameters) if parameters else "C"
    try:
        figures, blockers = build_figures(selected, baseline, diagnostic, parameter)
    except ValueError as exc:
        st.error(str(exc))
        figures, blockers = {}, []
    tabs = st.tabs(["Performance and cost", "Paired uncertainty", "Features and parameters", "Calibration", "Provenance and audit"])
    slots = {"status": 0, "trajectory": 0, "pareto": 0, "conditions": 0, "paired_ci": 1,
             "ablations": 2, "parameters": 2, "calibration": 3, "probability_diagnostics": 3, "condition_residuals": 3}
    for name, figure in figures.items():
        with tabs[slots[name]]:
            st.plotly_chart(figure, width="stretch", key="he88-"+name)
    with tabs[0]:
        condition = st.selectbox("Condition detail", list(CONDITIONS))
        st.dataframe(pd.DataFrame([{"trial_id": t["trial_id"], "condition": condition,
            "sampled_brier": t["result"]["by_condition"][condition]} for t in successful]), hide_index=True)
        st.caption("Wall time measures the complete trial, including fitting and evaluation. Inference latency is unmeasured.")
    with tabs[1]:
        st.caption("Whole episodes are resampled within conditions. Intervals are exploratory and unadjusted for multiple comparisons.")
        for blocker in blockers:
            st.info(blocker)
    with tabs[2]:
        st.caption("Feature membership and parameter scatter show observed associations. Controlled comparisons require matched settings. Raw feature distributions are unavailable for drift estimation.")
    with tabs[3]:
        if diagnostic:
            cal = calibration(next(t for t in successful if t["trial_id"] == diagnostic))
            st.dataframe(pd.DataFrame(cal["classes"]), hide_index=True)
            st.json({"rare_20": cal["rare_20"], "mean_class_ece": cal["mean_class_ece"]})
            st.caption(cal["warning"])
    with tabs[4]:
        st.caption("Public validation remains development-exposed; these sampled-label metrics carry no official points. Hidden-test quality is unavailable.")
        st.dataframe(frame[["trial_id", "round", "season_id", "source_commit", "source_sha256", "data_sha256", "split_sha256", "feature_sha256", "metric_source"]], hide_index=True)
        audit_root = st.text_input("Original local registry directory for attempt audit (optional)")
        if st.button("Read attempt history") and audit_root:
            try:
                audit = audit_registry(audit_root)
                st.json({k: v for k, v in audit.items() if k != "attempts"})
                st.dataframe(pd.DataFrame(audit["attempts"]), hide_index=True)
            except (OSError, ValueError, sqlite3.Error) as exc:
                st.error(str(exc))
    payload = {"schema": "jaegers.he88_filtered_summary", "schema_version": 1, "trials": trial_rows(selected)}
    payload["content_sha256"] = digest(payload)
    st.download_button("Download filtered CSV", frame.to_csv(index=False), file_name="he88_filtered_summary.csv", mime="text/csv")
    st.download_button("Download filtered JSON", json.dumps(payload, sort_keys=True, indent=2), file_name="he88_filtered_summary.json", mime="application/json")


if __name__ == "__main__":
    main()
