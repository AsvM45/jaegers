-- ============================================================================
-- JAEGERS House Edge: Governed Model Benchmark Lane SQL Analytics (Issue #86)
-- ============================================================================
-- Architecture: Medallion Delta Lakehouse (Gold Benchmark Governance Tables)
-- Tables:
--   - gold_benchmark_registry
--   - gold_benchmark_paired_comparisons
--   - gold_benchmark_episode_diagnostics
-- Purpose:
--   1. Strict provenance-partitioned model ranking (never conflating
--      `sampled_outcome_group_cv`, `official_public_validation`, and
--      `dev_exposed_public_validation_sampled_outcome`).
--   2. Paired bootstrap 95% confidence interval hypothesis promotion gating.
--   3. Rare 20x jackpot payout calibration and 5-class Brier decomposition.
--   4. Condition-regime (`stable`, `short_history`, `drift`, `shared_change`)
--      loss ratios and relative degradation auditing.
--   5. Validation target exposure (`validation_target_exposure`) leakage flags
--      and runtime Pareto efficiency analysis.
-- ============================================================================

-- ----------------------------------------------------------------------------
-- QUERY 1: provenance_partitioned_model_leaderboard
-- ----------------------------------------------------------------------------
-- Description:
--   Ranks clean (non-target-exposed) candidate models strictly within each
--   `evaluation_provenance` tier by `mean_brier ASC` and `log_loss ASC`.
--   Prevents cross-provenance score conflation.
-- ----------------------------------------------------------------------------
WITH clean_trials AS (
    SELECT
        trial_id,
        study_name,
        model_name,
        model_family,
        feature_groups,
        seed,
        fold_scheme,
        evaluation_provenance,
        split,
        primary_metric_name,
        primary_metric_value,
        mean_brier,
        official_points,
        log_loss,
        ece_calibration,
        validation_target_exposure,
        historical_signal_policy,
        wall_seconds,
        config_sha256,
        ROW_NUMBER() OVER (
            PARTITION BY evaluation_provenance
            ORDER BY mean_brier ASC, log_loss ASC, wall_seconds ASC
        ) AS rank_within_provenance,
        MIN(mean_brier) OVER (
            PARTITION BY evaluation_provenance
        ) AS best_brier_in_provenance
    FROM gold_benchmark_registry
    WHERE validation_target_exposure = 0 OR validation_target_exposure IS FALSE
)
SELECT
    evaluation_provenance,
    rank_within_provenance,
    study_name,
    model_name,
    model_family,
    fold_scheme,
    split,
    ROUND(mean_brier, 6) AS mean_brier,
    ROUND(mean_brier - best_brier_in_provenance, 6) AS delta_vs_provenance_best_brier,
    ROUND(official_points, 4) AS official_points,
    ROUND(log_loss, 6) AS log_loss,
    ROUND(ece_calibration, 6) AS ece_calibration,
    historical_signal_policy,
    ROUND(wall_seconds, 3) AS wall_seconds,
    SUBSTRING(config_sha256, 1, 12) AS config_hash_prefix
FROM clean_trials
ORDER BY evaluation_provenance ASC, rank_within_provenance ASC;


-- ----------------------------------------------------------------------------
-- QUERY 2: paired_hypothesis_ci95_promotion_gate
-- ----------------------------------------------------------------------------
-- Description:
--   Evaluates paired bootstrap comparisons (`gold_benchmark_paired_comparisons`)
--   and classifies each candidate hypothesis into `PROMOTE_SUPPORTED`,
--   `REJECT_SIGNIFICANT_REGRESSION`, or `INCONCLUSIVE_CI_SPANNING_ZERO`.
-- ----------------------------------------------------------------------------
WITH gated_comparisons AS (
    SELECT
        comparison_id,
        study_name,
        candidate_model,
        reference_model,
        evaluation_provenance,
        metric_type,
        mean_delta,
        ci95_low,
        ci95_high,
        episodes,
        bootstrap_samples,
        supported_improvement,
        direction,
        CASE
            WHEN direction = 'lower_is_better' AND ci95_high < 0.0 THEN 'PROMOTE_SUPPORTED'
            WHEN direction = 'higher_is_better' AND ci95_low > 0.0 THEN 'PROMOTE_SUPPORTED'
            WHEN direction = 'lower_is_better' AND ci95_low > 0.0 THEN 'REJECT_SIGNIFICANT_REGRESSION'
            WHEN direction = 'higher_is_better' AND ci95_high < 0.0 THEN 'REJECT_SIGNIFICANT_REGRESSION'
            ELSE 'INCONCLUSIVE_CI_SPANNING_ZERO'
        END AS promotion_decision,
        ABS(ci95_high - ci95_low) AS ci95_width
    FROM gold_benchmark_paired_comparisons
)
SELECT
    evaluation_provenance,
    study_name,
    candidate_model,
    reference_model,
    metric_type,
    promotion_decision,
    ROUND(mean_delta, 6) AS mean_delta,
    ROUND(ci95_low, 6) AS ci95_low,
    ROUND(ci95_high, 6) AS ci95_high,
    ROUND(ci95_width, 6) AS ci95_width,
    episodes,
    bootstrap_samples
FROM gated_comparisons
ORDER BY evaluation_provenance ASC, study_name ASC, mean_delta ASC;


-- ----------------------------------------------------------------------------
-- QUERY 3: rare_20x_payout_and_class_brier_audit
-- ----------------------------------------------------------------------------
-- Description:
--   Decomposes multi-class Brier loss across all 5 payout classes (`0x`, `1x`,
--   `2x`, `5x`, `20x`) and audits rare `20x` jackpot calibration bias
--   (`mean_pred_p20 - mean_target_p20`) and correlation (`corr_p20`).
-- ----------------------------------------------------------------------------
WITH class_decomposition AS (
    SELECT
        evaluation_provenance,
        study_name,
        model_name,
        model_family,
        mean_brier,
        class_brier_0,
        class_brier_1,
        class_brier_2,
        class_brier_5,
        class_brier_20,
        mean_pred_p20,
        mean_target_p20,
        (mean_pred_p20 - mean_target_p20) AS rare_20x_prob_bias,
        corr_p20,
        ROW_NUMBER() OVER (
            PARTITION BY evaluation_provenance
            ORDER BY corr_p20 DESC, class_brier_20 ASC
        ) AS rare_20x_rank
    FROM gold_benchmark_registry
    WHERE class_brier_20 IS NOT NULL
      AND mean_pred_p20 IS NOT NULL
)
SELECT
    evaluation_provenance,
    rare_20x_rank,
    study_name,
    model_name,
    model_family,
    ROUND(mean_brier, 6) AS mean_brier,
    ROUND(class_brier_0, 6) AS class_brier_0,
    ROUND(class_brier_1, 6) AS class_brier_1,
    ROUND(class_brier_2, 6) AS class_brier_2,
    ROUND(class_brier_5, 6) AS class_brier_5,
    ROUND(class_brier_20, 6) AS class_brier_20,
    ROUND(mean_pred_p20, 6) AS mean_pred_p20,
    ROUND(mean_target_p20, 6) AS mean_target_p20,
    ROUND(rare_20x_prob_bias, 6) AS rare_20x_prob_bias,
    ROUND(corr_p20, 6) AS corr_p20
FROM class_decomposition
ORDER BY evaluation_provenance ASC, rare_20x_rank ASC;


-- ----------------------------------------------------------------------------
-- QUERY 4: condition_regime_degradation_matrix
-- ----------------------------------------------------------------------------
-- Description:
--   Analyzes model robustness across the 4 structural episode conditions
--   (`stable`, `short_history`, `drift`, `shared_change`) and computes relative
--   loss ratios against the `stable` baseline within each provenance tier.
-- ----------------------------------------------------------------------------
WITH condition_ratios AS (
    SELECT
        evaluation_provenance,
        study_name,
        model_name,
        model_family,
        mean_brier,
        brier_stable,
        brier_short_history,
        brier_drift,
        brier_shared_change,
        brier_short_history / NULLIF(brier_stable, 0.0) AS short_history_to_stable_ratio,
        brier_drift / NULLIF(brier_stable, 0.0) AS drift_to_stable_ratio,
        brier_shared_change / NULLIF(brier_stable, 0.0) AS shared_change_to_stable_ratio
    FROM gold_benchmark_registry
    WHERE brier_stable IS NOT NULL
)
SELECT
    evaluation_provenance,
    study_name,
    model_name,
    model_family,
    ROUND(mean_brier, 6) AS mean_brier,
    ROUND(brier_stable, 6) AS brier_stable,
    ROUND(brier_short_history, 6) AS brier_short_history,
    ROUND(brier_drift, 6) AS brier_drift,
    ROUND(brier_shared_change, 6) AS brier_shared_change,
    ROUND(short_history_to_stable_ratio, 4) AS short_history_loss_ratio,
    ROUND(drift_to_stable_ratio, 4) AS drift_loss_ratio,
    ROUND(shared_change_to_stable_ratio, 4) AS shared_change_loss_ratio
FROM condition_ratios
ORDER BY evaluation_provenance ASC, mean_brier ASC;


-- ----------------------------------------------------------------------------
-- QUERY 5: leakage_exposure_and_runtime_pareto
-- ----------------------------------------------------------------------------
-- Description:
--   Audits `validation_target_exposure` and `historical_signal_policy` across
--   all registered benchmark runs and computes runtime efficiency (`wall_seconds`)
--   relative to predictive accuracy within each provenance tier.
-- ----------------------------------------------------------------------------
WITH governance_audit AS (
    SELECT
        evaluation_provenance,
        study_name,
        model_name,
        model_family,
        validation_target_exposure,
        historical_signal_policy,
        mean_brier,
        official_points,
        wall_seconds,
        CASE
            WHEN validation_target_exposure = 1 OR validation_target_exposure IS TRUE
                THEN 'DISQUALIFIED_IN_SAMPLE_STACKER_EXPOSURE'
            WHEN historical_signal_policy LIKE '%leaked%'
                THEN 'DISQUALIFIED_TEMPORAL_SIGNAL_LEAKAGE'
            ELSE 'GOVERNANCE_COMPLIANT'
        END AS governance_status,
        RANK() OVER (
            PARTITION BY evaluation_provenance
            ORDER BY wall_seconds ASC, mean_brier ASC
        ) AS runtime_efficiency_rank
    FROM gold_benchmark_registry
)
SELECT
    evaluation_provenance,
    governance_status,
    study_name,
    model_name,
    model_family,
    historical_signal_policy,
    ROUND(mean_brier, 6) AS mean_brier,
    ROUND(official_points, 4) AS official_points,
    ROUND(wall_seconds, 3) AS wall_seconds,
    runtime_efficiency_rank
FROM governance_audit
ORDER BY evaluation_provenance ASC, governance_status ASC, mean_brier ASC;
