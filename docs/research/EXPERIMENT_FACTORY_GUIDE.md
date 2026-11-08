# Human guide — What the JAEGERS experiment factory does

**Fresh public-safe guide derived from the latest House Edge architecture discussions and recent Library guide title. NOT a verbatim import of the Library artifact** (its complete bytes were unavailable via the Library connection). Current implemented status always comes from code, issue #8 and actual test runs.

## The goal

Replace ad hoc hand-tuned models with a reproducible research engine. It should answer questions like:

- Does adding information from sibling machines help specifically in `shared_change`, or does it also harm `stable`?
- Does a hierarchical Dirichlet prior beat frequency/shrinkage in `short_history`?
- How much of JAEGERS 55.12/60 development score comes from its stacking layer, payout-size regimes, or lag experts?
- Are two top models making complementary prediction errors and worth blending?
- Which feature groups, hyperparameters, training modes and interaction combinations improve **same-episode-fold**, properly sourced loss?

## What one experiment contains

A **trial** specifies the data snapshot, episode fold manifest, legal as-of feature groups, model, training mode, hyperparameters, seed and maximum runtime. The runner constructs training/evaluation input, fits the model, produces five payout probabilities, checks for future leakage/simplex, computes the **appropriate** metric, stores hashes/results/negative findings, and makes them queryable by a dashboard. Failures are recorded; they are not silently deleted. A dashboard can filter by condition, model family, features, runtime, seed and training provenance.

The experiment scheduler should avoid factorial explosions. Start with simple baselines, single feature ablations, selected pair interactions, several model families, then tune promising families with Optuna/random search. Always cap workers, attempts and wall time. An analysis dashboard is **read-only** to the trial registry.

## The tools and roles

- **Python 3.13 + NumPy + scikit-learn**: existing baseline and core probability modeling.
- **Pandas / DuckDB / Parquet**: optional convenient local queryable features and run history.
- **Optuna**: bounded conditional hyperparameter/feature search (not an evaluator or warehouse).
- **SQLite/atomic JSONL + immutable files**: local trial queue, run state and evidence; multi-host version might move to PostgreSQL.
- **pytest**: as-of, ID/normalization, scorer/adapter tests.
- **Streamlit + Plotly**: optional user-facing local research dashboard.
- **Delta Lake / PySpark / Databricks + MLflow**: optional sponsor-compliant lakehouse and experiment mirror; NOT required for offline competition runner.

**Agents:** CHAT builds common experiment API; Claude independently audits correctness; Cursor builds quality gate and later supervised ML; Grok owns new statistical challengers; Antigravity builds the reader/dashboard and later Databricks where approved. See owner map.

## Before trusting a score

Is it train sampled-label Brier, public validation true-probability competition points, or test format-only? Was a training row built using a historical signal never actually observed? Were the eight machines in an episode kept together in holdouts? Was public validation previously used in design? Was the ZIP independently reproduced? **55.12/60 public validation is a development result, not the hidden score.**

## How to begin

Use the task issue/PR and exact runnable commands reported by the owner. Do not treat a mock dashboard, plan or configuration file as proof that large sweeps ran. For a fresh experiment: state a hypothesis, pick a legal feature/model delta, run a small pilot with the same episode folds, compare paired per-episode loss, record negative results and decide whether a bigger sweep is justified.
