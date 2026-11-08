# HE-85 finite experiment preflight

Implementation base: `dea93882c236ee791c38eb07d16e841ff2f9b7f9`.
This change adds only `research/plan_he85.py`, its acceptance tests, and this report.
It does not execute experiments, change a model, or produce competition scores.

## Existing implementation inspected

`research/sweep.py` already owns grid/random/Optuna dispatch, source snapshots,
grouped folds, worker limits and registry reuse. Its `candidates()` materializes
the Cartesian product before the scheduling cap. `research/registry.py` already
retains attempts and supports immutable versioned exports. `research/process.py`
already records process status, wall time and peak RSS. These modules are unchanged.

## Contract and scope

`preflight(grammar)` accepts schema `jaegers.finite_plan`, version 1. Required
fields are `name`, `provenance`, `evaluation`, `features`, `families`, `seeds`,
and `resources`. The executable example schema is `grammar()` in
`tests/test_he85_plan_budget.py`; its hashes/episodes are explicitly **synthetic
test fixtures**, not measured research provenance.

- Provenance requires main/adaptation round, season, and SHA-256 digests for
  source, data, features and runtime policy.
- Evaluation requires train-only `sampled_outcome_group_cv`, a whole-episode
  fold mapping, its matching canonical digest, and explicit public-validation
  exposure. Public validation cannot be labeled unseen. Official points stay null.
- Features declare availability and dependencies, required and optional groups,
  and optional mutually exclusive sets. A model supplies an allowed group set.
  Query-only signal is rejected for this historical-supervision planning contract.
- Each family has named variants, prerequisite groups, exactly one transform
  choice per variant, config fragments and finite scalar parameter axes.
  `when` conditions reference parent parameter choices; the DAG is sorted
  deterministically and cycles/unknown parents are rejected. Inactive axes
  contribute one absent value, rather than a duplicate Cartesian dimension.
- Equivalent variants/transforms are deduplicated by numerical config; aliases
  are retained in branch evidence. Candidate IDs bind config, declared provenance,
  evaluation and resource policy. They are **planning IDs**, not registry trial IDs.
- The normalized plan digest and JSON report are independent of axis ordering.

The default enumeration cap is 100,000 branches. Independent feature toggles are
counted symbolically beyond this cap: **20 optional toggles = 1,048,576 masks**
when a required base group keeps every mask nonempty. Constrained spaces above
the cap are `BLOCKED_SPACE`: the raw count is an upper bound and exact constrained
count is null. No sampled/truncated count is presented as exact. Reduce the
preregistered axes to export. The planner deliberately does not solve arbitrary
large constraint-counting problems or implement covering-array/Optuna execution.

`runner_spec(report)` recompiles and checks the report, accepts only READY plans,
and exports at most `max_trials` existing-runner candidates. It does not import
the scheduler or start workers. Config fragment conflicts fail instead of silently
overriding values. The runner remains authoritative for numerical trial identity.
Before separately invoking the runner, callers must verify the declared hashes
and regenerated folds against actual inputs; a supplied hash is not proof of
the bytes it describes. The planner does not certify arbitrary plugin semantics.

## Resource preflight

The adapter matches the existing grid runner: one or two workers, two aggregate
CPUs (`2 // workers` per worker), and 8 GiB per worker. It validates positive,
finite caps and rejects overflow-sized trial requests. The table includes requested
trials, bounded planned trials, per-trial and study wall policy, concurrent memory,
serial trial seconds and approximate maximum worker CPU seconds.

All resource figures are **policy estimates**, excluding coordinator overhead,
feature-cache construction, staging and cleanup. They are not measured consumption
or a guarantee about total elapsed time. Setup may consume time before dispatch.

## Reproduce locally

From repository root, with CPython 3.13:

```powershell
python -m venv .venv
.venv/Scripts/python.exe -m pip install -r Jaeger_Main/House_Edge/requirements-analytics.txt
cd Jaeger_Main/House_Edge
../../.venv/Scripts/python.exe -m pytest tests/test_he85_plan_budget.py -q
```

Generate a labeled test-fixture grammar locally (no actual trial launch):

```powershell
../../.venv/Scripts/python.exe -c "import runpy,json,pathlib; p=pathlib.Path('research_runs/he85_fixture'); p.mkdir(parents=True,exist_ok=True); g=runpy.run_path('tests/test_he85_plan_budget.py')['grammar'](); (p/'grammar.json').write_text(json.dumps(g))"
../../.venv/Scripts/python.exe -m research.plan_he85 --grammar research_runs/he85_fixture/grammar.json --runner-spec research_runs/he85_fixture/study.json --out research_runs/he85_fixture/report.json
```

Observed environment: Windows 11 build 26300, AMD64 Family 25 Model 117, 16 logical
CPUs, CPython **3.13.2**; isolated venv, repository-pinned NumPy 2.5.4,
scikit-learn 1.9.1, pytest 9.2.0, psutil 7.2.2, pandas 3.1.1, Plotly 7.1.0,
Streamlit 1.67.0. No global PATH change.

Observed initial focused validation: **39 passed in 1.04s**, followed by an
additional regression for input/output path collision and Windows UTF-8 report
export. The tests exercise exact
counting, deterministic reports/IDs, conditional parameters, aliases,
dependencies/exclusions/prerequisites, query-signal rejection, million-mask guard,
zero/nonfinite/overflow caps, missing or mismatched hashes/folds, invalid exposure,
config conflicts, capped runner compatibility and CLI no-execution behavior.

Initial root regression: 138 passed, one pre-existing calibration plotting test
failed because the fresh analytics environment lacked Matplotlib. This is an
environment prerequisite, not a planner source change; the Databricks CI installs
its plotting dependency separately. After installation, **139 root tests passed
in 28.36s**. The full House Edge suite passed **262 tests plus five subtests in
144.86s**, with one pre-existing negative-control `log1p` warning. The added CLI
regression is checked separately after that run. Final results are recorded in the PR.

No validation/test target was scored in this issue; no champion promotion or
submission artifact change occurred. Independent review is required for integration.
