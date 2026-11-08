# JAEGERS House Edge — The Human-Readable Plan

*A plain-English explanation of the v7 warehouse-backed experiment-factory design. This is a proposal, not an implemented or tested system.*

## The big idea

We want to turn model research from “someone changes some Python, runs it, and reports a score” into an **experiment factory**.

The factory would know what data we have, what features can legally be computed, what models we can train, which settings each model supports, how much computing we can spend, and how to compare results fairly. We could then describe a research question—such as “try different lag structures, with and without cross-machine information, across our Bayesian and tree-based models”—and have the system generate, execute, record, and compare the valid experiments.

**The warehouse stores reliable, reusable data. The experiment engine decides what to try and runs it. The evaluation system determines what genuinely worked.** These are three distinct responsibilities.

Databricks can make the data and results shareable and auditable. But our models must continue to work without Databricks, including in the competition’s offline submission environment.

## What makes House Edge an interesting problem?

For each slot-machine query, we predict five probabilities: payout of 0×, 1×, 2×, 5×, or 20×. The predictions must add to 100%.

We receive prior observations for a machine and, sometimes, useful information from other machines in the same eight-machine episode. Some histories have gaps; the gaps are *unknown spins*, not losses. Machines may change behavior, and relationships among machines can change too.

We are not merely predicting whether the next spin wins or what the average payout might be. We are estimating the **entire probability distribution of the next spin**.

The existing JAEGERS approach already combines 73 lag-pattern experts, recency weighting, same-episode information, payout-size modeling, and a gradient-boosted stacker. A GitHub commit claims **55.12 out of 60 on public validation**. This is a commit-message claim, not an independently reproduced result or a hidden-test score. The reviewed repository had also advanced to a later infrastructure commit.

We should protect that existing model rather than replace it simply because a new technique sounds sophisticated.

## What the system would do in practice

Imagine requesting:

> Test Bayesian lag models, small gradient-boosted trees, and hidden-state models. Try using the last 8 spins versus longer histories. Turn sibling-machine features on and off. Try three smoothing strengths, two drift-detection methods, and several calibration options. Tell me what improved the score, on which machine conditions, at what runtime, and whether the improvement holds up across episodes.

A proper system would:

1. **Locate the exact dataset version** and verify its original files.
2. **Build reusable features** such as recent win rates, exact lag patterns, missing-data indicators, and prior payouts from sibling machines.
3. **Generate candidate configurations** from registered models, features, and settings.
4. **Reject invalid combinations**, such as a historical model that uses signal information only available at the final query.
5. **Estimate and cap the number of experiments** before launching an expensive search.
6. **Run the experiments**, retry recoverable failures, and reuse cached work where legitimate.
7. **Evaluate consistently** on entire held-out episodes, not randomly separated machines from the same episode.
8. **Save everything**: input data version, code revision, feature choices, hyperparameters, predictions, per-condition errors, runtime, logs, and trained artifacts.
9. **Compare against the existing champion** with identical evaluation rules.
10. **Promote a candidate only after checks** for validity, reproducibility, and performance.

The outcome is not just “Model X scored better.” We want to know **why it appears better, how trustworthy that conclusion is, how expensive it was, and how to reproduce it**.

## The warehouse: three layers of data

Think of the warehouse as a well-organized scientific lab notebook.

### Bronze: keep the originals

Store the original released CSVs, their checksums, and information about the challenge round and data split. Do not silently overwrite them. This gives us a way to prove exactly which source data produced a result.

### Silver: make the data reliable

Convert the raw inputs into validated episode, machine, spin, and query records. Check for duplicate IDs, invalid payouts, inconsistent cutoffs, broken joins, and future observations that should not be visible.

A crucial rule is that the models may use **only observations from strictly before the spin they are predicting**. This includes observations from sibling machines.

### Gold: make useful, reusable model inputs

Prepare features such as:

- Recent counts and percentages of each payout.
- Exponentially weighted win rates that emphasize recent observations.
- Exact payout values at lags 1 through 8.
- Explicit flags for missing ticks.
- Runs, transitions, and combinations of past outcomes.
- Signals of drift or abrupt changes.
- Summaries of other machines in the same episode.
- Estimated probability distributions and confidence measures from simpler models.

Gold should include both features for actual query cutoffs and carefully constructed *historical training examples*. They are different because the final query may include an input signal that was not recorded at earlier historical ticks.

Building features once and reusing them across many models saves repeated computation. Every cached feature set must be tied to its input data, code version, and precise construction rules.

## How we get more training examples without inventing data

Suppose a machine was observed at ticks 10, 11, 13, and 15.

To create an example for tick 13, we can use the observations at 10 and 11 as its historical inputs and use the **actual observed payout at tick 13** as its label. We cannot use the observation at 15, and we must not pretend that missing tick 12 was a zero payout.

Doing this across many histories creates additional real observed training examples. It does **not** mean we have more independent episodes, and one observed payout is not the same as knowing the true five-category probability distribution.

That distinction must carry through the entire evaluation pipeline.

## The model library: what we want to try

The platform should start with the current JAEGERS champion and simple baselines, then expand into research families:

**Probability estimation and Bayes:** smoothed frequency models, Beta-Binomial and Dirichlet-Multinomial models, hierarchical Bayes, and Bayesian model averaging.

**Lag-pattern and mechanism discovery:** first- and higher-order Markov models, variable-length contexts, suffix trees, context-tree weighting, sparse lag interactions, Boolean/XOR-like rules, and Bayesian selection of lag structures.

**Changes over time:** exponential forgetting, sliding windows, CUSUM/Page-Hinkley change detectors, Bayesian online changepoint detection, hidden Markov models, and hidden semi-Markov models.

**Relationships among machines:** lagged peer features, hierarchical episode effects, shared latent factors, small multivariate hidden-state models, and cross-machine changepoint methods.

**Payout-size behavior:** learning whether the four winning-payout probabilities reflect a few recurring underlying regimes, mixtures of probability vectors, low-rank structure, or state transitions.

**General machine learning:** logistic regression, generalized additive models, random forests, extra trees, gradient boosting, XGBoost/CatBoost/LightGBM where warranted, and small neural sequence models as later experiments.

**Combining and calibrating forecasts:** weighted mixtures, out-of-fold stacking, temperature/Dirichlet calibration, Bayesian averaging, and conservative blending toward reliable priors.

Statistical tests—autocorrelation, mutual information, runs tests, likelihood comparisons, bootstraps, and changepoint diagnostics—also belong in the research toolkit. They help us discover or reject hypotheses even when they are not forecasting models themselves.

Every model is an **experiment to evaluate**, not an assumed upgrade.

## How “test every combination” actually works

We would register features, models, and options in machine-readable definitions. Each experiment is a combination of:

- A specific dataset and evaluation split.
- A method of creating training labels.
- One or more feature groups.
- One prediction model.
- That model’s hyperparameters.
- An optional episode-specific adaptation method.
- An optional calibration or ensemble method.
- A random seed and a computing budget.

A **parameter** is usually a value the model learns from data, such as a regression coefficient. A **hyperparameter** is a setting that controls learning or model structure, such as tree depth, prior strength, or number of hidden states. A feature is an input variable, such as the payout at lag 2. We need to track all three, but search generally operates over model families, feature choices, and hyperparameters.

We can enumerate every legal combination in a **finite, explicitly defined search space**. But searching every possible model or every real-valued hyperparameter is impossible.

Even 20 yes/no feature switches create over one million possible feature subsets. Multiply those by models, training modes, settings, and evaluation folds and the number can grow into hundreds of millions.

The answer is a layered search strategy:

1. **Small exhaustive studies** when the total number of valid combinations is manageable.
2. **Ablation tests** that remove one feature or model component at a time, revealing what it contributes.
3. **Pairwise coverage** that deliberately tests important pairs of decisions without running every full combination.
4. **Random or Bayesian/Optuna search** for large conditional hyperparameter spaces.
5. **Focused higher-order tests** only when the evidence suggests useful interactions.
6. **Careful final comparisons** of a few strong, different models or ensembles.

Before running anything, the planner should say how many combinations exist, how many are invalid or duplicates, and the estimated cost based on actual measurements from small trials.

The goal is **comprehensive coverage and systematic learning**, not wasting money to claim we executed every conceivable configuration.

## How we avoid fooling ourselves

This is the most important part of the architecture.

The competition evaluates predicted five-category probabilities. On public validation, it compares our probability vector with a true probability vector supplied by the organizer, aggregates squared error by episode and condition, and normalizes against a reference forecaster.

But the original training labels and historical spins are *sampled outcomes*. They support probability learning, but they do not reveal the true latent probability vectors. The same metric cannot be computed directly from them.

There are also four machine conditions: stable, short history, drift, and shared change. Good average performance can hide a failure in one condition, so we should show results separately.

The system should:

- Hold out **whole episodes**, not individual machines within episodes.
- Keep every input chronologically earlier than the target spin.
- Keep final-query signals out of earlier training rows unless genuine historical signals exist.
- Never give a training model public validation true targets by accident.
- Distinguish public validation development scores from independent evidence.
- Record how often validation information influenced a model’s design.
- Compare new models to the champion on the *same episodes*.
- Save per-episode differences and test whether apparent improvements are widespread or driven by a few lucky cases.
- Reject models that cannot output five valid probabilities or cannot be rerun.

Two concrete issues in the reviewed current model deserve special attention. The historical stacker appears to reuse final-query signal during earlier training examples even though historical signals were not supplied. The existing payout-size regime constants were reportedly derived from public validation targets. Neither observation alone proves a competition violation, but both affect how we should evaluate claims of generalization. The first needs an as-of audit; the second needs transparent evaluation-exposure labels and train-only challengers.

## The experiment runner and result history

We need an experiment ledger, not a folder full of ambiguously named CSVs.

Every trial gets a unique ID based on its full definition: dataset versions, code version, features, model, settings, evaluation split, and random seed. A trial should save its predicted probabilities, scores, per-condition and per-episode errors, training time, memory use, software environment, and logs.

If we try an identical experiment again, the system should recognize that and reuse its completed artifacts **only after verifying the saved hashes**. If a worker crashes, the trial should remain visible and be retryable rather than disappear or silently count as a bad model.

Initially, a single local coordinator can manage this. If we later run jobs across teammates’ computers, we can move to a stronger shared queue with worker leases and heartbeats. Databricks jobs may execute batches, while MLflow shows and compares runs; neither should replace the canonical experiment ledger.

## Why Databricks is worth using—and what it will not do

Databricks can provide a convincing, working data-engineering layer for the sponsor challenge:

1. Upload permitted raw sources into Bronze Delta tables.
2. Validate and standardize them into Silver.
3. Build leakage-safe reusable features in Gold using SQL or PySpark.
4. Demonstrate that Databricks features match local Python features on the same examples.
5. Run at least one genuine model comparison and record its parameters, metrics, and artifacts in MLflow.
6. Show the lineage and operational value: which source files and transformations produced which result, what data checks caught, and how teammates can reuse the results.

What we should **not** claim is that Spark makes our tiny forecasting dataset faster by default, or that Databricks Free Edition offers unlimited parallel training. The free platform has meaningful quotas. Local CPU execution is initially the more sensible way to fit many small models.

Most importantly, the competition’s final predictor needs to be a **self-contained offline Python program**. It must not call Databricks, MLflow, or an internet API to make a prediction.

## What we should build first

The original v7 document proposes a staged build, not a large one-shot rewrite.

**First: protect the existing submission.** Inspect actual local code and dependencies, independently reproduce its claimed validation score, audit information leakage, build a valid CSV and code ZIP, and prove the ZIP can reproduce the CSV offline. The repository’s instructions currently require a plan-only first engineering session and human approval before edits.

**Second: build a tiny complete factory.** One versioned source snapshot; one validated feature family; one historical-as-of feature example; fixed episode-grouped splits; two model adapters (current champion and a simple Bayesian categorical baseline); three actual trials; one consistent result report.

**Third: make research cheap and repeatable.** Add cached Parquet features, a model/feature registry, automatic experiment enumeration, stable trial IDs, retries, and per-episode comparison reports.

**Fourth: add intelligent search and new science.** Start with champion ablations and targeted lag-rule, changepoint, cross-machine, and payout-mixture models. Add pairwise coverage and Optuna when the basic engine is correct.

**Fifth: integrate Databricks and scale deliberately.** Implement the Bronze/Silver/Gold mirror, verify feature parity, add MLflow tracking, and run a bounded job batch. Add shared database coordination only when multiple remote workers genuinely need it.

## Suggested division of work for four people

- **Release and integration:** current champion, scorer, dependencies, offline submission, hashes, and final package.
- **Statistical correctness:** historical as-of construction, leakage tests, grouped splits, and honest score comparisons.
- **Experiment engine:** model adapters, feature/model registry, trial planner, search methods, and execution queue.
- **Data and Databricks:** source manifests, validated tables, cached features, SQL/PySpark parity, and MLflow integration.

They should work in separate branches or worktrees and avoid simultaneously editing the existing model’s central files.

## How we know this project is successful

The first milestone is not “we tried a thousand models.” It is:

> Given a frozen dataset, a feature definition, and a model search specification, the system can generate valid trials, run them, score them honestly, save every artifact, and reproduce the best result on demand.

Later success means it can repeat this process across dozens of model families and thousands of carefully selected configurations without losing track of which results are trustworthy.

**Bottom line:** build the infrastructure to make every *well-defined* combination testable, but use scientific judgment to choose which ones deserve computation. The warehouse makes inputs reliable. The compiler and scheduler make experimentation scalable. The evaluator makes the conclusions credible. The frozen offline runner turns the research into a valid competition submission.
