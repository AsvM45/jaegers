# HE-88 research platform and HE-89 integration evidence

Owner-directed engineering window began 2026-11-08 11:37 UTC. This is a narrow
House Edge research extension; organizer artifacts and Hitachi remain outside scope.
Implementation base: `dea93882c236ee791c38eb07d16e841ff2f9b7f9`.

## Additive implementation

- `research/analysis/chat_he88_evidence.py`: verifies the portable v1 content seal,
  reconstructs the existing sampled Brier metric from five-class per-query records,
  validates whole-episode OOF membership and split digest, blocks incompatible
  comparisons, computes class calibration/20x diagnostics using existing metrics,
  and audits all durable attempts read-only from a consistent SQLite snapshot.
- `research/analysis/chat_he88_study.py`: preregisters one fixed six-trial platform
  acceptance benchmark and calls the existing sweep only with `--execute`.
- `research/reporting/chat_he88_report.py`: writes a new local report directory
  with offline interactive HTML, CSV, sealed JSON and Markdown. Existing outputs
  are preserved. Distinct contexts get separate chart sections.
- `dashboard/he88_views.py` / `dashboard/he88_app.py`: additive read-only UI, with
  filters for family, outcome, feature groups, hyperparameter text, context and
  source/data/feature/fold hashes. Ten quantitative views cover outcome counts,
  performance over time, trial-cost Pareto frontier, condition errors, feature
  membership, parameter association, paired episode intervals, class reliability,
  probability diagnostics and condition calibration residuals.

Existing registry/sweep/worker/metrics/feature/model/dashboard files are unchanged.
No second trial queue or multi-host SQLite lease is introduced. Existing core
tests cover cache invalidation, retry/crash recovery and immutable source staging;
the new reader surfaces incomplete or conflicting evidence instead of repairing it.

## Reproduce

Use CPython 3.13 and a fresh isolated environment at repository root:

```powershell
python -m venv .venv
.venv/Scripts/python.exe -m pip install -r Jaeger_Main/House_Edge/requirements-analytics.txt
.venv/Scripts/python.exe -m pip install matplotlib==3.10.8
.venv/Scripts/python.exe -m pytest tests/test_dashboard_he88_views.py -q
cd Jaeger_Main/House_Edge
../../.venv/Scripts/python.exe -m pytest tests/test_chat_he88_evidence.py tests/test_chat_he88_study.py -q
../../.venv/Scripts/python.exe -m research.analysis.chat_he88_study --out research_runs/he88_acceptance
../../.venv/Scripts/python.exe -m research.analysis.chat_he88_study --out research_runs/he88_acceptance --execute
cd ../..
.venv/Scripts/python.exe -m Jaeger_Main.House_Edge.research.reporting.chat_he88_report --registry Jaeger_Main/House_Edge/research_runs/he88_acceptance/exports/v1/registry.json --out Jaeger_Main/House_Edge/research_runs/he88_report --audit-root Jaeger_Main/House_Edge/research_runs/he88_acceptance
$env:JAEGERS_HE88_REGISTRY = (Resolve-Path Jaeger_Main/House_Edge/research_runs/he88_acceptance/exports/v1/registry.json).Path
.venv/Scripts/python.exe -m streamlit run dashboard/he88_app.py --server.address 127.0.0.1 --server.headless true --browser.gatherUsageStats false
```

Preparation records actual train/source/feature/scorer/runtime hashes and all 96
train episode fold assignments. Execution is capped at six trials, one two-CPU
worker, 240 seconds per trial, 900 seconds scheduling wall time and 8 GiB worker
memory. Setup/cleanup are extra. Repeating an identical preregistration resumes
through the existing registry; changed input/source policy requires a new directory.

The six configurations are the frozen unmodified champion anchor, two existing
frequency configurations, and three query-supervised logistic feature sets at a
fixed C/seed. This is a platform acceptance check, not Grok's wider model-search
campaign. The champion's historical copied-signal caveat remains visible. No
public validation targets are evaluated or described as unseen here.

## Validation and interpretation

Initial focused acceptance: **33 passed in 6.94s** (before adding the Streamlit
startup/render check). Final source SHAs, actual measured runs and final test
counts are recorded in the issue-linked PR and subsequent evidence below.

Comparisons require matching round, season, raw train files, metadata, split
manifest, scorer and numerical runtime policy, plus identical query labels and
episode/condition membership. Different source versions remain visible. Missing
provenance blocks ranking. Failed/interrupted trials keep null scores. Unknown
schema/provenance and synthetic records are rejected in this real-evidence view;
the existing demonstration dashboard remains separate.

Intervals resample whole episodes within conditions and remain exploratory,
unadjusted for multiple comparisons. ECE uses sampled class outcomes and fixed
bins; low rare-event counts limit interpretation. Recorded wall time measures
complete training/evaluation trials, not inference latency. Raw feature-distribution
drift cannot be estimated from prediction-only exports. No hidden score, official
train-CV points, universal hardware parity, or champion promotion is claimed.

## Integration queue at implementation start

This inventory is observational. Final #89 inspection must refresh every SHA,
claim, review, file list, check and branch relation before any merge.

| Candidate | Observed source | Initial disposition |
|---|---|---|
| PR #83 governance | `1639f39387e2621ff760b43519592afe3921197b` | Green checks; independent security review pending |
| PR #79 full regression CI | `e0478b3ffb4f41b60c1144320a83749f665642c6` | Green checks; independent review pending |
| PR #90 AGY #14 | initially `f5d08a6`, advanced to `0443f133ddd1eeaf46274b67178effb60ce74766` | Source moving; review final pushed SHA and live claims |
| Grok #87 | No PR observed yet | Await actual final handoff; do not infer background progress |
| PR #91 planner #85 | `f5010a84ea91278ca35e633e2acdcaea2b37187c` | Green checks; independent review requested |
| #88 additive platform | Current claimed branch | Implement/test, then freeze and publish scoped PR |
| Copilot PR #81 | `b8c955ded79b153cda237fb666b8497c2a7088c1` | Draft; inspect real diff and workflow approval gate |

No historical branch is eligible merely because it exists. Branch-retirement
issue #65 remains read-only and no refs are deleted. Final integration uses
GitHub's normal PR workflow, serial regression and exact source SHA verification.
An absent independent approval is `BLOCKED_REVIEW`; unresolved conflicts are
`BLOCKED_CONFLICT`. Required protections are never bypassed.
