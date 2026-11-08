# Plan gates | time-critical order

The first Codex/Astra session **must be PLAN MODE ONLY** and produce a reviewable implementation proposal. Do not write code in that session.

| Phase | Priority | Definition of done | Do not proceed if |
|---|---|---|---|
| 0: local state | P0 | Actual checkout HEAD/status, dependencies, file inventory, current champion recorded | Dirty teammate work might be overwritten |
| 1: release rescue | P0 | Candidate's validation score independently rerun, test IDs checked, requirements verified, code ZIP extracted/cold rerun match actual CSV, hashes documented | Any reproduction mismatch, scorer ambiguity, package missing dependency |
| 2: leakage/exposure | P0 | Historical signal availability documented, no-signal/ablation planned and tested; SIZE_REGIMES validation exposure properly labeled | Future signal being silently used in pseudo training; score reported as independent |
| 3: focused science | P1 | Train episode-grouped baseline vs at least one as-of historical learner or local adaptation challenger, with paired errors, sources, timing | Main submission deadline or regression risk |
| 4: experiment factory | P1 after core release | Immutable bounded sweeps, resumes, output hashes, config/feature flags, at least 3 smoke trials and provenance | No reliable scorer, no split manifest, critical cutoff imminent |
| 5: feature/model zoo | P2 | Add statistical family only with honest benefit and runtime, ARIMA/SARIMA not default | Unmeasured benefit, explosion of 2^feature subsets |
| 6: Databricks | P2 | Real Delta/PySpark table + local parity + MLflow evidence with a meaningful decision contribution | Risk to main / adaptation submissions |
| 7: adaptation | P0 when new kit available | Fresh round ID/version, rebuilt CSV/ZIP, reproduced and human-submitted with receipt | Accidentally reusing main IDs or assuming same priors/conditions |

**Time checks**: published kit says main Saturday Nov 7 21:00 Central, adaptation opens then and closes Sunday Nov 8 11:00 Central. General Devpost sponsor metadata has previously listed Sunday 10:30 Central; reconfirm. If now close to any cutoff, skip P1/P2 rather than endanger P0.

Four owners: A release/CI/registry; B validation and leakage; C temporal/pseudo-example challenger; D experiment orchestration + Databricks after release. Avoid simultaneous edits to `jaegers_entry/`; use feature branches or files with distinct ownership when human authorizes Git operations.

**Release status vocabulary:** `REMOTE_INSPECTED` < `LOCAL_REPRODUCED` < `OFFLINE_PACKAGE_VERIFIED` < `HUMAN_SUBMITTED` < `ORGANIZER_ACCEPTED`. Do not skip steps or assert acceptance from checker output.
