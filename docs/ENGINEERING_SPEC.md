# House Edge engineering reference

This file describes design constraints, not evidence of implemented capabilities.
Live measurements belong in [CURRENT_STATE.md](CURRENT_STATE.md), active ownership
and acceptance in [GitHub #18](https://github.com/AsvM45/jaegers/issues/18), evaluation
rules in [VALIDATION_PROTOCOL.md](VALIDATION_PROTOCOL.md), and exact APIs in
[CONTRACTS.md](../Jaeger_Main/House_Edge/research/CONTRACTS.md).
The superseded v5 snapshot/specification remains in Git history.

## Authority and boundaries

- Current source and the supplied organizer kit determine executable behavior.
  Inspect HEAD and dirty files before edits; distinguish a code commit from a frozen
  model implementation and from actual generated/reproduced artifacts.
- Work only on House Edge. Preserve the champion; do not modify Hitachi, overwrite
  teammate work, expose credentials, spend money, push, or submit without authorization.
- CPython 3.13 is the supported project/release runtime. Pin tested dependencies;
  record OS, patch version and actual numerical behavior. Cross-platform equality
  is a measured requirement, not something implied by a fixed random seed.
- Competition inference is offline and independent of Databricks, dashboards,
  experiment registries, APIs and search services.

## Release integrity before breadth

Freeze source/config/data/scorer hashes; independently generate validation and test
predictions; use the supplied official checker. Package with the organizer builder,
extract fresh, run the declared command under Linux/offline/read-only constraints,
and compare actual normalized CSV values within 1e-8. Preserve failed attempts.
Record exact bytes, sizes, hashes, environment, timing and resource measurements.

The kit requires 2 CPUs, 16 GiB, 30 minutes, CSV <=10 MB and ZIP <=100 MB. Local
checks, offline verification, human receipt and organizer acceptance are distinct
statuses. Never skip a status or automatically replace a submitted artifact.

## Scientific evaluation

Use the dedicated validation protocol. Core distinctions:

- Historical example at t: label is observed payout(t), features only use outcomes <t.
- Query signal is query-only unless historical availability is separately established.
- Missing exact ticks remain unknown; sibling observations obey the same cutoff.
- Whole episodes are the independent outer fold unit. Preprocessing, global priors,
  calibration and learned gating stay within fitting episodes.
- Train one-hot Brier, public true-vector competition points, and test-format checks
  are different evidence sources. Public validation already informed model design and
  constants; do not describe a new slice of it as a pristine sealed audit.
- Estimate uncertainty with paired episode-level comparisons, stratified by condition.
  Apply the same local adaptation to held-out episodes that inference will apply.

## Experiment execution

Trial identities include configuration, numerical source/plugin hashes, data, fold
manifest, seed and environment. Git HEAD is recorded as provenance; docs-only commits
must not invalidate otherwise identical numerical work. Each worker imports its own
frozen source copy. A single coordinator owns each registry; parallel workers write
separate attempt directories. Keep failures and interrupted attempts; resume never
rewrites completed trial artifacts.

Start with real smoke studies and prove resume/retry/resource controls. Screen a
structured search space, investigate failures, then expand promising model/feature
families. Distinct scientific hypotheses matter more than repeated run counts.
Keep main/adaptation datasets, registries, references and release artifacts separate.

## Specialist extensions

Use the agreed fit/predict/serialization and feature contracts rather than duplicate
core functionality. Statistical, supervised, temporal and ensemble agents may add
models and configs on their own branches; all outputs remain full five-category
probabilities. Feature interactions declare dependencies. Current signal may be used
for query-supervised models without inventing historical signal rows.

Analytics reads real registry artifacts and exposes provenance, paired episode
losses, condition behavior, calibration, rare payouts, ablations, uncertainty and
failures. Missing metrics stay missing. No dashboard may invent hidden-test results.

Databricks work requires available authorized access, real Delta/PySpark/MLflow runs,
local parity and a documented analytical contribution. Keep cloud dependencies out
of submitted inference. Defer it when release integrity or deadlines are threatened.
