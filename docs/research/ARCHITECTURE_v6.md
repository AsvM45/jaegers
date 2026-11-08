# House Edge architecture v6 — curated historical reference

**Status:** concise public-safe synopsis of the earlier ChatGPT Library `JAEGERS_House_Edge_Implementation_Architecture_v6.md`, not its complete original bytes. Design ideas are historical; the current repo owns implementation truth. Main source of current state: [AGENT_CONTEXT](../AGENT_CONTEXT.md) and [#18](https://github.com/AsvM45/jaegers/issues/18).

## Current/previous implementation

Existing original champion `jaegers_entry/` includes 73 lag-context experts over history, a win/no-win estimator plus conditional positive-size distribution and size experts, within-episode sibling evidence, and a scikit-learn histogram-gradient-boosted stacker. Its committed old README is stale. Original source intended to be preserved while developing challengers in isolated research modules.

Released main data: train (96 episodes), validation (96 with true target probabilities), test (192 with only queries/history); eight machines per episode; outputs five-class vector for payouts 0,1,2,5,20. Official points score equal-weight four-condition normalized true-vector errors, not a generic 0–100 scoring diagnostic.

## Four architecture layers

1. **Data and causality** — strict tick<cutoff, exact-lag missingness, all siblings' earlier rows only, episode-disjoint CV, no past signal(t) leakage.
2. **Forecasting** — preserved expert-mixture champion alongside Bayesian, tabular supervised, temporal and ensemble challenger adapters. Five-simplex output contract for each.
3. **Experiment factory** — shared feature registry, immutable source/fold/model/config identity, bounded trial queue, official/sampled score separation, paired per-episode diagnostics, output hashes and failures.
4. **Release and analysis** — ZIP+CSV offline reproduction (2CPU/16GiB/30m), human submission approval and separate adaptation round; optional Streamlit/Plotly dashboards and Databricks Delta/PySpark/MLflow mirror.

## Stage gates

Priority: protect champion and ensure correct organizer submission first; validate leakage concerns; implement honest grouped experimental runner and real smoke tests; add diverse feature/model trials; build dashboard/Databricks only when they cannot jeopardize submission. No large rewrite required to start measuring challenger performance.

## Reference

Full original v6 Markdown/PDF exists in ChatGPT Library and a PDF is in the linked team Drive; was not directly exportable as an authorized raw file into this GitHub session. This synopsis is for agents who need a brief architecture, not an exact historical reproduction.
