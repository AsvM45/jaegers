# JAEGERS House Edge research core

Reproduce the existing five-category probabilistic forecaster, run controlled
episode-grouped experiments, and prepare offline competition artifacts without
replacing the frozen champion. This is the integration core of an expanding research
platform; specialist model studies, dashboard, CI and Databricks have separate owners.

See [current measured results](../../docs/CURRENT_STATE.md) and the
[coordination board](https://github.com/AsvM45/jaegers/issues/18) for execution status.
This guide describes supported commands, not a claim that every planned study is done.

## Python 3.13 setup

Run from `Jaeger_Main/House_Edge`. On Windows:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File tools/setup_windows.ps1
.venv/Scripts/python.exe --version
```

The script installs workspace-local uv/CPython 3.13.18, creates `.venv`, and installs
the pinned core dependencies. Repeated cached setup can use `-Offline`. It does not
change PATH or register a new global Python installation.

For Linux, `bash tools/setup_linux.sh` provisions a separate runtime and
`bash tools/run_linux.sh <python arguments>` invokes it. WSL setup keeps binaries in
`/var/tmp/jaegers-house-edge-runtime` because the OneDrive mount rejected installation
renames. Override `JAEGERS_LINUX_RUNTIME` to choose another isolated runtime directory.

Dependency layers:

- `requirements-runtime.txt`: competition NumPy/scikit-learn stack only.
- `requirements-research.txt`: runtime plus Optuna, process monitoring and tests.
- `requirements-models.txt`: optional statistical/boosting libraries for specialists.
- `requirements-analytics.txt`: optional Streamlit/Plotly/Pandas for the analytics owner.

## Protect and reproduce a champion

Use fresh output paths; freezing and packaging refuse to overwrite existing artifacts.

```powershell
.venv/Scripts/python.exe -B -m research.freeze --data public --out research_runs/my-champion
.venv/Scripts/python.exe -B -m research.reproduce --entry research_runs/my-champion/entry --data public --out research_runs/my-reproduction
```

The second command runs validation twice and test once, executes the official checker
on each saved CSV, and records commands, package versions, hashes, timing and memory.
Test checking provides no event score. Public validation is development-exposed.

**Generate release reference predictions under Linux.** Matching package versions did
not make Windows and Linux predictions equal. A fixed seed is insufficient evidence
of portability. Preserve failed parity checks and compare actual normalized vectors.

Stage the exact CSV/source pair, then cold-verify it with Bubblewrap on Linux:

```text
python -B -m research.release --entry research_runs/my-champion/entry --data public --predictions research_runs/my-linux-reproduction/test.csv --out research_runs/releases/my-release
bash tools/verify_linux.sh --release research_runs/releases/my-release --data public
```

Verification disables networking, mounts entry/data read-only, limits CPU/memory/time,
and requires probability agreement <=1e-8. It records actual scratch/output use;
the installed older Bubblewrap does not hard-enforce an aggregate scratch quota.
The organizer builder/inspector remains authoritative for archive structure. A verified
local package is neither a submission receipt nor organizer acceptance.

## Run and resume experiments

```powershell
.venv/Scripts/python.exe -B -m research.sweep --study studies/smoke.json --data public --out research_runs/main
.venv/Scripts/python.exe -B -m research.resume_check --study studies/smoke.json --data public --registry research_runs/main --out research_runs/main/resume-proof.json
.venv/Scripts/python.exe -B -m research.sweep --study studies/random_smoke.json --data public --out research_runs/main
.venv/Scripts/python.exe -B -m research.sweep --study studies/optuna_smoke.json --data public --out research_runs/main
```

Studies declare candidates or parameter spaces, a fixed seed, whole-episode folds,
worker count, total wall budget, trial count and per-trial timeout. At most two CPU
slots execute concurrently. Optuna uses its own persistent sampler/study database;
trial execution and provenance use the common registry. Retry recorded failures only
with `--retry-failed`; interruption creates a new attempt without erasing old evidence.

Every worker imports a hashed source snapshot, so concurrent edits cannot silently
change an in-flight trial. IDs reflect numerical source/config/data/fold/environment
identity. Git revision and entry documentation are recorded without causing duplicate
numerical trials when only documentation changes. Numerical code/data/env changes
create a new identity rather than masquerading as a resumed run.

## Compare actual evidence

```powershell
.venv/Scripts/python.exe -B -m research.report --registry research_runs/main --out research_runs/reports/comparison-001
```

Add `--baseline <unique-trial-id-prefix>` for paired, condition-stratified episode
bootstrap differences. Reports contain condition losses, calibration/error provenance,
source identities, runtime and failures. Incompatible data/fold/runtime contexts are
not silently paired. Repeated source versions are reported separately from distinct
configurations; run count is not scientific diversity.

The coordinator evaluates sampled query outcomes from training episodes. It does not
score test truth or repeatedly tune on public true-probability validation. Official
points require a separate, explicitly recorded public-validation check.

## Extend without duplicating the core

Read [CONTRACTS.md](research/CONTRACTS.md) before implementing a model, feature provider
or dashboard. Existing adapters reuse JAEGERS; new families belong in `research/models/`
and may register a `research.models.module:factory` that accepts `(config, cache_path)`
and returns a compatible model. Coordinate worker-factory edits with the integration owner.

Feature groups declare interaction dependencies. Historical rows use strictly earlier
own-machine and sibling outcomes; missing ticks remain unknown. Query-only signal is
not invented for historical rows. Preprocessing/calibration fit within episode folds.
The current champion's validation-derived constants and historical signal use remain
explicit audit findings, not claims of pristine evaluation or a proven rules violation.

Dashboard readers should use SQLite read-only or exported JSON/result artifacts. Final
prediction code never depends on the registry, dashboard, Databricks or network access.
Main/adaptation use separate dataset manifests, registries and release directories.

## Tests and collaboration

```powershell
.venv/Scripts/python.exe -B -m pytest tests -q --basetemp=research_runs/pytest-fresh-run
```

Choose a fresh temporary directory for each invocation. Tests exercise temporal
availability, exact missing lags, episode isolation, score anchors, serialization,
source snapshots, atomic writes, retry/resume and resource controls.

Claim a GitHub issue with an explicit agent name and use a dedicated branch/worktree.
The shared GitHub account does not identify an execution owner. Keep generated runs,
models and releases out of Git. Do not edit Hitachi, upload entries, incur cloud costs
or merge another agent's work without the appropriate authorization.
