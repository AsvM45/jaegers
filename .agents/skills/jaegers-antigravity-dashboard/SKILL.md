---
name: jaegers-antigravity-dashboard
description: "Build or audit the JAEGERS House Edge experiment analytics dashboard, read-only run ingestion, paired model comparisons, hypothesis reporting, calibration, feature ablations and error analysis. Use on GitHub issue #13."
---

# Antigravity: House Edge analytics dashboard

## Prerequisites
1. Read `AGENTS.md`, `Jaeger_Main/House_Edge/AGENTS.md`, `docs/VALIDATION_PROTOCOL.md`, and issues #13 and #18. Inspect latest source before relying on names. Work on a dedicated branch/worktree.
2. Reuse `research/metrics.py` and the trial registry/schema exposed by Codex when available; avoid changing their implementations. Get an agreed contract for trial metadata, metrics, per-episode errors, feature toggles and prediction IDs.
3. Follow the existing `jaegers-evaluation` and `jaegers-experiment-factory` skills where relevant.

## Execute in bounded milestones
1. Implement a *read-only* ingestion adapter in `dashboard/` handling empty registry, successful/failed trials, missing fields, and schema version changes. Include small explicitly labeled **synthetic demo fixtures**, never advertised as real competition evidence.
2. Build a Streamlit + Plotly UI (or equally lightweight proven stack) with: model run table, provenance filters, per-condition loss ratios when true vectors exist, grouped sampled-label Brier, paired episode differences/uncertainty, calibration, rare-payout errors, feature ablation comparisons, hyperparameter relationships, runtime and failure diagnostics.
3. Explicitly separate metric provenance (`train_group_cv`, `public_validation_true_targets`, `test_format_only`); never infer a hidden-test score or show a 0–100 diagnostic as official 60-point score.
4. Add deterministic unit tests for data ingestion and metric separation, smoke test startup and view with real registry when it exists; document exact startup command and screenshots if possible.
5. Write a compact issue update with changed paths, actual test commands, results, blockers and next request for the registry owner.

## Completion
A user can browse genuine experiment history once runs exist, filter candidates and inspect supported claims without any changes to the original champion, submission artifacts or Codex's research modules. If no real runs exist, show *no runs yet* and maintain separate demonstration mode.
