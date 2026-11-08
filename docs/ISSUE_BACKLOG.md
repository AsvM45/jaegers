# Issue-ready backlog (not posted to GitHub)

These are proposed independent issues; none is claimed created remotely. Prefix with `HE-V5` and apply after Astra plan review.

| ID | P | Title | File scope | Acceptance |
|---|---|---|---|---|
| HE-V5-01 | P0 | Verify HEAD and frozen champion | read-only `jaegers_entry`, source scorer | Actual local commit, status, deterministic config, evidence record |
| HE-V5-02 | P0 | Reproduce reported 55.12 validation claim | `jaegers_entry/`, checker | Exact current validation score+4 condition ratios, command, CPU time, split provenance |
| HE-V5-03 | P0 | Fix/prove stacker historical signal availability | `jaeger_model.py`, tests | historical rows cannot see unsupported query-time signal; targeted fixture and matched-score comparison |
| HE-V5-04 | P0 | Document validation-target-derived size constants | model audit, potential new estimator | split-exposure log; independent train-only ablation and legal use distinguished |
| HE-V5-05 | P0 | Pin offline dependencies and update README | entry `requirements.txt`, README | Python3.13/Linux reproducible NumPy + sklearn pins verified; no stale 'no training' claim |
| HE-V5-06 | P0 | Official CSV/ZIP final-byte reproduction | entry, builder, outputs | frozen artifacts; exact IDs; 1e-8 normalized numeric parity; sizes; hashes |
| HE-V5-07 | P0 | Resolve organizer version / submission receipt | docs + human organizer communication | current 60/40 vs older 80/20 resolved or explicitly BLOCKED; actual form receipt saved |
| HE-V5-08 | P1 | Episode-grouped evaluation harness | experiments, tests | fixed folds, no episode overlap, Brier vs official target-scored separation |
| HE-V5-09 | P1 | Honest historical as-of dataset builder | new module + tests | tick<t, missingness, no past signal copies, correct sibling cutoff |
| HE-V5-10 | P1 | Test episode-specific adaptation vs champion | new model adapter | same held-out episode splits and loss metrics, no query answer access |
| HE-V5-11 | P1 | Pseudo-supervised global model comparator | new model adapter | meaningful five-class outputs, paired group scores, no future features |
| HE-V5-12 | P1 | Ablation suite for stack/size/peer/short-prior | configs + runner | one-factor tests; score shifts per condition and runtime |
| HE-V5-13 | P1 | Immutable trial registry and bounded scheduler | `experiments/` + tests | resume after interruption, failure states, SHA lineage, no same-id overwrite |
| HE-V5-14 | P2 | Feature interactions, boosting, ARIMA challenger | optional model modules | feature provenance, probability simplex, measured improvement, time budget |
| HE-V5-15 | P2 | Databricks sponsor evidence | Databricks notebook scripts | bronze/silver/gold Delta, local parity, true MLflow run, value demonstrated |
| HE-V5-16 | P0 at round-two release | Adaptation migration and preflight | separate adaptation artifacts | new data hashes, fresh test IDs, cold ZIP, receipt before 11 AM |

**Strongest current rejected alternative to model rewrite:** Preserve the existing 73-expert/size/stack candidate; rewriting around an old pooled baseline would discard demonstrated development progress and increase release risk. Main scientific uncertainty is validation-target exposure and history-signal semantics, not lack of candidate complexity.
