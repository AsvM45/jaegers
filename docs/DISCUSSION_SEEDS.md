# Discussion seeds — publish only when GitHub Discussions is enabled

**Repo setting at last check:** Discussions disabled. These are curated starter prompts for a **human maintainer**, not live Discussion posts. Once enabled, use category `Research hypotheses` / `Architecture RFCs` / `Decisions`.

## Discussion 1 — Does sibling history matter differently across conditions?
Hypothesis: same-episode sibling outcomes strictly before t improve `shared_change` without harming `stable`, or reveal opposite machine responses. Proposed test: same-fold peer on/off ablation, paired per-episode squared-error/Brier with correct target provenance. Implementation linked issue #11 after claim.

## Discussion 2 — Which data truly belongs in a historical training row?
Historical signal(t) is not separately released. Claude #3/PR #19 identifies train/serve information skew in the champion's stacker; test-time query signal itself is permitted. Debate explicit signal policies, any organizer clarifications, and correct original vs no-signal/causal alternatives. Decision affects #3/#8, not a license to change the champion.

## Discussion 3 — How broad should automated hyperparameter/feature search be?
Select staged ablation → pairwise covering → model-family screening → bounded Optuna finalists. Discuss budget, multiple comparisons, repeated public validation exposure and a predeclared stopping criterion. Link #8 registry, #9 Bayesian and #10 supervised models.

## Discussion 4 — Databricks: value beyond Spark for tiny datasets
Evaluate reproducibility/lineage, Delta Bronze/Silver/Gold parity, MLflow trial tracking and team insight. Require actual workspace evidence and no cloud inference dependency; cloud spend needs permission. Link #14.

## Discussion 5 — Post-datathon open-source research directions
Reproducible synthetic probabilistic forecasting, causal as-of validation, challenge transfer, data/feature compiler reuse. Separate post-event ambitions from hard deadline claims. No organizer/private content uploaded.

## Discussion template

```
Hypothesis or decision:
Known evidence (linked, sourced):
What is uncertain:
Proposed falsifiable experiment:
Budget and data availability:
Potential source/validation leakage:
What decision will results unlock:
Related Issue/PR:
```
