# JAEGERS House Edge | Verified public remote snapshot

**Public GitHub:** https://github.com/AsvM45/jaegers. **Inspected default branch:** `main`. **HEAD:** `b78abe75db15688e652b30b9d5388a151f2b7acd`. **Observed pushed_at:** 2026-11-07 22:45:19 UTC = 4:45:19 PM Central. **Snapshot is not attestation of a local dirty tree or later pushes.**

| Evidence | Status / provenance |
|---|---|
| Public repository, five commits, one visible main branch | VERIFIED via GitHub connector (at inspection) |
| GitHub issues and pull requests | None returned at inspection; not proof local task list absent |
| Latest commit title | `Made improvement to score 55.12/60` - **CLAIM**, unverified score |
| Prior changes | `322121a` reported 54.99/60; `1c69ba9` reported 51.55/60. Do not interpret relative performance as independently rerun |
| Current forecaster | `Jaeger_Main/House_Edge/jaegers_entry/jaeger_model.py`, `params.json`, `predict.py` |
| New stacker | `fit_stacker` uses `sklearn.ensemble.HistGradientBoostingClassifier`, trained on earlier observed payouts; enabled by `params.json:stack=true` |
| Additional current model behavior | Size-context experts enabled; `prior_short=0.85`; `lam_s=0.995`, `beta_s=2`, `lam_sll=0.99`, `ep_weight_s=1` |
| Data contracts + organizer checker | Present in `Jaeger_Main/House_Edge/`; original kit says main 60/adaptation 40 |
| Historical signal contamination | **P0 suspect**: `stack_features()` uses current query signal during historical `collect=True` rows; exact historical signal(t) not provided |
| Validation-target-derived constants | **P0 provenance**: `SIZE_REGIMES` comment says read from validation true targets; public validation score is development/selection not pristine independent audit |
| Dependencies | No tracked `jaegers_entry/requirements.txt`; current model imports NumPy AND scikit-learn when stack enabled |
| Submission README | Outdated (states no training, NumPy-only runtime, prior validation ~51.1) despite current train-time stacker |
| GitHub CI / dedicated tests | No `.github/workflows/` or dedicated `tests/` folder in inspected tree; no status checks reported by connector |
| Code ZIP, generated CSV, cold offline reproduction, form receipt | **NOT VERIFIED** in this remote inspection; teammates may have local files |
| Sponsor Databricks pipeline | Not found in public tree at snapshot; do not assert it is implemented |

**Current top concern:** Reproduce current candidate locally, audit signal provenance and validation exposure, pin packages, and ensure exact final main submission before building experiment factory. Code-reading is not a runtime test. Remote HEAD can advance at any moment.
