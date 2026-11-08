# JAEGERS House Edge ? live implementation state

Updated: 2026-11-08T00:13:40.023005+00:00

## Working baseline

- HEAD: `b78abe75db15688e652b30b9d5388a151f2b7acd`; current main after the user's pull.
- Original `jaegers_entry` model and parameters unchanged. Frozen source/data/scorer hashes:
  `Jaeger_Main/House_Edge/research_runs/champion-b78abe75/manifest.json` (ignored local artifact).
- Project runtime: CPython 3.13.18, workspace-local Windows environment. Runtime pins:
  `requirements-runtime.txt`; dev pins: `requirements-research.txt` in House Edge.
- Independently observed official public development validation: **55.121615/60**.
  Condition ratios: stable 0.067316, short_history 0.116980, drift 0.092323,
  shared_change 0.077390. Detailed evidence: `research_runs/reproduction-b78abe75/`.
- Repeat validation and test-format evidence are being finalized. Test truth is private.

## Milestones

1. Source freeze and Python 3.13 setup COMPLETE.
2. Baseline reproduction RUNNING; first validation agrees with the commit's rounded claim.
3. Initial temporal audit: **5 tests passed** (`tests/test_temporal.py`).
   Executed fixtures confirm query-time signal in old training rows and end-of-history
   coverage affecting historical smoothing. Champion preserved; separate causal adapter
   removes signal and uses fixed, predeclared smoothing to remove this coverage dependence.
4. Linux provisioning RUNNING in existing Ubuntu 22.04 WSL. No cloud resources used.

## Scientific and release limitations

- SIZE_REGIMES and model selection used public validation targets. This is a
  development-exposed score, not pristine independent generalization evidence.
- Historical signal availability unresolved; no clean leakage claim for champion.
- Offline package parity, final artifact hashes, and organizer receipt not yet verified.
- Kit says main 60/adaptation 40, main cutoff Nov 7 21:00 Central and adaptation cutoff
  Nov 8 11:00 Central. Separate older 80/20 guide conflict remains unresolved.
  No new organizer announcement has been verified in this session.
- Databricks workspace/access not established. Do not claim cloud integration.

## Next actions

Finish baseline repeated/test checks; build and cold-verify a frozen release; then run
causal candidates and grouped-CV smoke/resume checks before broader studies. All trials
must retain failure records, data/source/environment identities and metric provenance.
See `VALIDATION_PROTOCOL.md` for scoring/split rules and `ISSUE_BACKLOG.md` for backlog.
No commit, push, upload, cloud spend, or Hitachi change authorized or performed.
