# House Edge integration contracts

Execution owner of the integration core: **CHAT**, active editing issue #8.
Issue #1/#4 prerequisites are READY FOR REVIEW, not closed before integration.
Active branch: `agent/chat-he08-core`; separate physical worktree: `.chat-he08/`.
The shared GitHub assignee does not identify an agent. Read the explicit claim on #18.

## Model adapters

New model implementations belong in `research/models/<family>.py` or the existing
specialist `research/challengers/` namespace; do not create a
second flat `research/models.py`. The integration-owned existing-model adapters live
in `research/adapters.py`. Public interface:

`research.models` re-exports these adapters for existing consumers, while remaining
a package for specialist modules. The implementations live only in `adapters.py`.

```python
model.fit(queries, history, labels)  # returns self
predictions = model.predict_proba(queries, history)
model.save(path)
restored = Serializable.load(path)
```

- Queries: list of CSV-shaped dictionaries with string query_id, episode_id,
  machine_id, machine_type, signal, cutoff. IDs are metadata, not predictors.
- History: mapping `(episode_id, machine_id)` to `{integer_tick: payout}`.
  Payouts are the actual values 0, 1, 2, 5, 20. Missing ticks are absent.
- Labels passed by the CV runner: mapping query_id to **class index 0–4** in that
  payout order. Historical cache y also uses class indices. This differs from raw
  organizer labels, which contain payout values.
- Predictions: mapping every requested query_id exactly once to a finite,
  nonnegative length-five vector summing to one. Use `validate_predictions`.
- Fit sees only fitting episodes. Prediction may adapt to held-out episode history
  strictly before its cutoff, never query outcomes. Serialization is for trusted local
  artifacts; submitted code can deterministically retrain instead.
- Register a factory via `factory: research.models.module:function` or
  `factory: research.challengers.module:function` in trial configuration. It accepts
  `(config, cache_path)` and returns the model; specialist wrappers convert their
  internal schema to this shared raw-query/history/class-index contract. Coordinate
  changed contracts with CHAT; do not independently rewrite worker/registry files.

## Features and as-of supervision

The provisional integration bridge is `research/feature_api.py`; specialist features
may live under `research/features/` without a module-name collision. Coordinate API
changes with #7 and #8 before changing the bridge or `research/dataset.py`.

`FeatureComputer(history).row(query, groups)` returns `(float32_vector, column_names)`.
Columns use `group/name_index` identifiers. Source identities/snapshots also cover
specialist `research/extensions/` and `research/challengers/` files, and feature cache
keys include feature extension/plugin and reader hashes. Adding those source files
does not itself register new groups or integrate an unreviewed specialist model.
`validate_groups` checks interaction
dependencies and rejects query-only signal for historical training. All outcomes,
including peers, must have tick < target tick. Machine type is treated as intrinsic
static metadata; that assumption is recorded. Do not copy final signal into old rows.

The cache stores numeric/string arrays only (`allow_pickle=False`), source/input
digests, feature columns, row kinds, episodes and ticks. Cache identities must change
when feature logic or source data change. Missingness is explicit, never payout zero.

## Evaluation and trial registry

The runner uses four deterministic, condition-stratified whole-episode folds on
`public/train`. Historical fit rows and held-out query labels cannot share episodes.
Preprocessing and calibration fit inside the outer fold. Public validation is a
separate explicitly invoked development-scoring step; test checks have no score.

SQLite: `research_runs/<round>/registry.sqlite`. Tables:

- `trials`: id, study, config (JSON), identity (JSON), status, attempt, artifact,
  mean_brier, wall_seconds, error, created_at, finished_at.
- `attempts`: trial_id, attempt, artifact, status, started_at, finished_at, error.
- `coordinator`: a live-process lease; one writer/scheduler per registry.
- `study_trials`: many-to-many study membership without duplicate numerical trials.

Trial ID hashes canonical configuration plus source, data, fold and environment
identity. Completed trials are reused; interrupted attempts get a new directory.
Git HEAD and entry README/dependency text are retained as provenance but do not
invalidate an otherwise identical numerical trial. Worker source snapshots and
model/parameter bytes remain part of the identity. A specialist factory named
`research.models.module:factory` accepts `(config, cache_path)` and returns the model.
Old attempt evidence is retained. Failed trials retry only with `--retry-failed`.
Grid/random/Optuna studies use the same registry and supervised process path.

Each attempt contains request.json, process logs/resource evidence, result.json and
OOF CSV, or failure.json, plus its immutable source copy and source-manifest.json.
Results include mean_brier, by_condition, per_episode, episode_conditions, per_query,
calibration, class errors, feature importance where
available, fold membership, metric source and validation-exposure flags.

Dashboard agents should read SQLite in read-only mode, or read `registry.json` plus
referenced result.json files. Do not write the registry or load model pickles for UI.
Missing metrics stay missing; never render a sampled-label Brier value as official
points, or a format-checked test CSV as a scored test result.

## Release boundaries

Only CHAT edits shared release tooling while #4 is claimed. Frozen artifacts are in
ignored `research_runs/`; no teammate modifies them. Packaging uses the organizer's
builder/inspector and exact runtime pins. No push or submission occurs automatically.
Human release coordination is #5; independent QA/audit remain #2 and #3.
