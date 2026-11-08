# Validation protocol | House Edge main and adaptation

## Exact objective and diagnostic trap
Target = five probabilities ordered 0,1,2,5,20. For each query q, `L_q = sum_k (pred[q,k] - true[q,k])**2`. Average machine errors within episode, then episodes within each of `stable`, `short_history`, `drift`, `shared_change`; divide each condition by its separate frozen reference error. `R = mean_c(E_c/max(B_c,1e-9))`. The supplied main kit gives `points = 60/(1+R)`; round two `40/(1+R)`. The older DOCX says 80/20. Ask organizers; do not infer.

`slot_forecasting/scoring.py:score_predictions` computes a separate `100*(1-loss/2)` diagnostic. **Never report this as official technical main points**. Official public validation: `python check_submission.py <predicted_validation.csv> --split validation` or `rounds.score_round`.

## Five distinct evaluation contexts
A. Train episodes: fit global model, group split by episode; if using historical as-of pseudo-examples, label observed past payout at t and use features strictly before t. Evaluate sampled-label Brier (proper in expectation, noisy), not official `points`.
B. Auxiliary within-episode temporal folds: forward-chaining / rolling origin to probe drift; not evidence of transfer between episodes.
C. Public validation: exact true-probability targets available. Useful for limited model selection, but some current model constants derive from those targets. Mark prior exposure; report a development score, not unbiased independent validation.
D. Public test: actual main submission queries/histories already provided; hidden true next-spin probabilities and condition labels absent. Can generate predicted CSV and format check only; may adapt to observed test history using predeclared as-of procedure.
E. Hidden organizer: official score computed after upload on same test queries using undisclosed truths; never simulated or claimed from GitHub logs.

## Coverage and feature assertions
- Every query exactly once; 8 machines per episode; shared cutoff; missing ticks remain unknown.
- Every source outcome used for a query or pseudo-row satisfies `source_tick < target_tick`, including sibling machines.
- Do not propagate final `signal` to earlier pseudo-examples. Test source provenance of machine type, too.
- Do not use true validation condition labels in a predictor when hidden test lacks condition tags. A learned gate must use only observable episode features.
- Group outer folds by episode. Store split-ID manifest SHA and per-episode losses for paired comparison.
- Never reuse formerly seen validation targets as a fresh sealed audit, and never confuse validation score with hidden-test score.

## Suggested adversarial fixtures
- Mutation at tick c and c+1 must not alter prediction at c.
- Remove tick c-2; lag-2 becomes missing, not last observed value.
- Reorder CSV rows and episodes; outputs must map by query_id and be stable.
- Change a sibling observation at c; no feature/prediction change at c.
- Two episodes sharing `m000` suffix must not share state.
- Change query-time signal while generating historical stack rows; assert it is either absent from historical features or explicitly justified as known historically.
- Zero expected score from test checker; it only validates shape/IDs.
- Remove either NumPy or sklearn from fresh env to prove ZIP provisioning is necessary and present.
