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

Independent integration review found that the initial all-attempt audit checked
successful result-file existence without validating its contents. The correction
reconstructs successful results from their per-query/fold evidence, checks their
configuration and current SQLite score, and verifies terminal artifact bytes
against the existing content-sealed portable export. Invalid JSON, changed metrics,
changed OOF bytes, changed configuration, changed SQLite scores and invalid export
seals are regression cases. The audit never repairs or reseals source artifacts.
Historical or unexported attempts without an available seal are explicitly marked
UNAVAILABLE with warnings and coverage counts. `ok` means no detected errors,
not proof that all historical attempts have byte-level seals.

### Grok research-result interface

The completed #87 report has aggregate episode errors and declared module/data/
protocol hashes rather than portable per-query registry records. The additive
`dashboard/he88_research_sources.py` reader checks those bytes against the
inspected checkout, verifies train query/episode coverage, fold digest, four
condition aggregates and mean score, and exposes a separate source-checked summary
panel. Missing raw probabilities and full dependency/runtime lineage remain
explicit limitations. Cross-source ranking, reconstructed class calibration and
registry Pareto comparisons stay unavailable for these aggregate records.

The UI now has a sixth **Research summaries** tab, which also works when no local
registry exists. It provides candidate and condition charts, retained negative
results and a separate JSON export. The offline report accepts optional
`--external-report <HE87 checkout>/research/reports/grok_he87_results.json`, adds
the two source-checked summary charts and separate `external_summary.csv`/JSON,
and hashes the adapter source. It does not modify Grok's files or relabel these
summaries as full registry trials. The existing ten full-evidence charts remain.

Actual adapter check against Grok source `a301483bb975888bd39bee7b17ca2d1d7c040b3b`:
**34 candidate summaries / 96 episodes / 768 queries**, content digest
`2494eb7d345fdb3b8a57d7e45f05f812845ed248aca2668200c76b75f26341a4`.
The independent integration review also reproduced all 34 Brier scores and all
episode errors exactly in **273.2914s** at that source. No public validation peeks.
Adapter + dashboard tests: **19 passed in 7.85s**. Final broader regression counts
and final pushed SHA are recorded on PR #92.

## Reproduce

Use CPython 3.13 and a fresh isolated environment at repository root:

```powershell
python -m venv .venv
.venv/Scripts/python.exe -m pip install -r Jaeger_Main/House_Edge/requirements-analytics.txt
.venv/Scripts/python.exe -m pip install matplotlib==3.10.8
.venv/Scripts/python.exe -m pytest tests/test_dashboard_he88_views.py -q
cd Jaeger_Main/House_Edge
../../.venv/Scripts/python.exe -m pytest tests/test_chat_he88_evidence.py tests/test_chat_he88_study.py -q
$env:OMP_NUM_THREADS='2'; $env:OPENBLAS_NUM_THREADS='2'; $env:MKL_NUM_THREADS='2'; $env:NUMEXPR_NUM_THREADS='2'
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

Complete local regressions after the reader hardening: **257 House Edge tests +
five subtests passed in 124.07s**, with the existing deliberate negative-control
`log1p` warning; **146 root tests passed in 32.52s**. Subsequent additive resource
columns, reporter-byte provenance and seed/cost filters passed **39 relevant tests
in 8.32s** (plus the two unchanged preregistration tests in the full run).

The existing runner requires the House Edge package root for its absolute
`slot_forecasting` imports. An initial root-package invocation failed before any
trial dispatch; rerunning the documented command from House Edge succeeded.

### Actual bounded platform run, 2026-11-08 12:07–12:09 UTC

Experiment source: **`3a3df6831aaf5aca27181bd875c8afef8b5d6b42`**, clean before
dispatch, CPython 3.13.2 / Windows 11 build 26300 / AMD64, fixed seed 0,
96 training episodes, 768 query labels, four grouped folds. All six trials
succeeded in **102.8471 seconds** total scheduling wall time. Source snapshots,
process logs, OOF probabilities, outcome diagnostics and unsuccessful feature
variants remain in ignored local `research_runs/he88_acceptance/`.

| Configuration | Grouped sampled Brier ↓ | Trial wall seconds |
|---|---:|---:|
| Frozen champion anchor, existing historical-signal caveat | 0.3622911451 | 78.2140 |
| Frequency, strength 20 / decay 1 | 0.5705298414 | 1.5231 |
| Frequency, strength 10 / decay .97 / peer .1 | 0.5662851961 | 1.8645 |
| Query logistic: type/windows/missingness, C=.1 | 0.5717537803 | 5.3687 |
| Same logistic plus lags | 0.6030834403 | 5.5849 |
| Same logistic plus lags and peers | 0.6084001037 | 6.1923 |

Relative to the frequency-prior baseline, decay/peer delta is **−0.00424465**,
95% paired whole-episode interval **[−0.01328735, 0.00430544]** (2,000 resamples,
seed 0). The interval includes zero. Logistic plus lags has delta **0.03255360**,
interval **[0.01638916, 0.04878997]**. These are exploratory development-informed
sampled-label results, not official validation points or hidden quality. The
champion anchor's numerical advantage does not resolve its documented historical
information-availability caveat or authorize promotion.

There are only **12 observed 20x labels** in these 768 held-out query predictions.
The report exposes that count, predicted/observed rates, class Brier and classwise
reliability/ECE instead of implying high-precision rare-event conclusions.

Preregistration digest:
`e6af5f1c67cbdf126829e7df6e56aa22f22d2a4229df98aef0d9e32d7b6bf29e`.
Train-files digest:
`a2e485240a36961d85aee6b4c310c4bffabc91cbc78729a7490cb43f4cbb64eb`.
Episode manifest digest:
`84f2aa3282c5dc8f394bdd06179f0adac2ec3865804dda99285d1b5c7e4ccc0e`.
Initial report content digest:
`3654988908444bd7f3be9b9d031c79bfc49fb257bee529e1841ba06d49b81fe1`.

An immediate identical resume finished in **0.9465 seconds**, created no new
attempts and preserved **all 324 attempt artifact files byte-for-byte**. The
read-only audit reported six attempts and zero findings. Later additive reader
hardening changes analysis-source provenance; use a fresh destination for a new
preregistration, or the original source commit to replay the original wrapper.

Streamlit AppTest against the genuine export rendered **6 selected / 6 succeeded /
0 failed**, five tabs and no exceptions. Browser visual inspection was blocked by
an unavailable browser-access host. A standalone Matplotlib summary PNG was
rendered and visually checked: error bars, labels, units and caveat are legible.
The offline Plotly HTML, CSV, JSON, Markdown and PNG remain local ignored artifacts;
they are not published competition data.

Self-review added malformed-object validation and an explicit error for invalid
input shapes. Focused validation after those changes: **41 passed in 11.10s**.

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
