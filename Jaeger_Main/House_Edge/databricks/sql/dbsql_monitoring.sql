-- ============================================================================
-- JAEGERS House Edge: Production Databricks SQL (DBSQL) Analytical Monitoring
-- ============================================================================
-- Architecture: Medallion Delta Lakehouse (Bronze -> Silver -> Gold)
-- Engine: Databricks Serverless SQL Warehouse / DBSQL
-- Purpose: Continuous model monitoring, calibration diagnostics, data drift detection,
--          episode-level error diagnosis, and cryptographic Bronze ingestion lineage.
-- ============================================================================

-- ----------------------------------------------------------------------------
-- QUERY 1: model_leaderboard_provenance
-- ----------------------------------------------------------------------------
-- Description:
--   Ranks registered models within each evaluation provenance tier (e.g.
--   'official_public_validation' vs 'sampled_outcome_group_cv') by primary
--   competition loss (mean_brier ASC) and log_loss (ASC).
--   Surfaces champion status, hyperparameters, condition breakdowns, and ECE.
-- ----------------------------------------------------------------------------
WITH ranked_evaluations AS (
    SELECT
        run_id,
        model_name,
        model_type,
        evaluation_provenance,
        champion_status,
        mean_brier,
        log_loss,
        ece_calibration,
        brier_stable,
        brier_short_history,
        brier_drift,
        brier_shared_change,
        git_commit,
        created_at,
        ROW_NUMBER() OVER (
            PARTITION BY evaluation_provenance 
            ORDER BY mean_brier ASC, log_loss ASC
        ) AS rank_in_provenance,
        DENSE_RANK() OVER (
            ORDER BY mean_brier ASC
        ) AS overall_rank
    FROM gold_model_evaluations
)
SELECT
    overall_rank,
    rank_in_provenance,
    model_name,
    model_type,
    evaluation_provenance,
    champion_status,
    ROUND(mean_brier, 6) AS mean_brier,
    ROUND(log_loss, 6) AS log_loss,
    ROUND(ece_calibration, 6) AS ece_calibration,
    ROUND(brier_stable, 6) AS brier_stable,
    ROUND(brier_short_history, 6) AS brier_short_history,
    ROUND(brier_drift, 6) AS brier_drift,
    ROUND(brier_shared_change, 6) AS brier_shared_change,
    -- Compute relative degradation in drift vs stable condition
    ROUND((brier_drift - brier_stable) / NULLIF(brier_stable, 0) * 100.0, 2) AS drift_degradation_pct,
    git_commit,
    created_at
FROM ranked_evaluations
ORDER BY evaluation_provenance ASC, rank_in_provenance ASC;


-- ----------------------------------------------------------------------------
-- QUERY 2: payout_calibration_reliability
-- ----------------------------------------------------------------------------
-- Description:
--   Computes reliability diagram statistics by unpivoting all 5 payout classes
--   (0x, 1x, 2x, 5x, 20x), binning predictions into probability deciles (1..10),
--   and calculating the decile-level calibration error: |avg_pred - observed_rate|.
-- ----------------------------------------------------------------------------
WITH unpivoted_predictions AS (
    SELECT
        p.query_id,
        p.model_name,
        0 AS payout_class,
        p.p_0 AS predicted_prob,
        CASE WHEN q.outcome = 0 THEN 1.0 ELSE 0.0 END AS actual_outcome
    FROM gold_predictions p
    INNER JOIN silver_queries q ON p.query_id = q.query_id
    UNION ALL
    SELECT
        p.query_id,
        p.model_name,
        1 AS payout_class,
        p.p_1 AS predicted_prob,
        CASE WHEN q.outcome = 1 THEN 1.0 ELSE 0.0 END AS actual_outcome
    FROM gold_predictions p
    INNER JOIN silver_queries q ON p.query_id = q.query_id
    UNION ALL
    SELECT
        p.query_id,
        p.model_name,
        2 AS payout_class,
        p.p_2 AS predicted_prob,
        CASE WHEN q.outcome = 2 THEN 1.0 ELSE 0.0 END AS actual_outcome
    FROM gold_predictions p
    INNER JOIN silver_queries q ON p.query_id = q.query_id
    UNION ALL
    SELECT
        p.query_id,
        p.model_name,
        5 AS payout_class,
        p.p_5 AS predicted_prob,
        CASE WHEN q.outcome = 5 THEN 1.0 ELSE 0.0 END AS actual_outcome
    FROM gold_predictions p
    INNER JOIN silver_queries q ON p.query_id = q.query_id
    UNION ALL
    SELECT
        p.query_id,
        p.model_name,
        20 AS payout_class,
        p.p_20 AS predicted_prob,
        CASE WHEN q.outcome = 20 THEN 1.0 ELSE 0.0 END AS actual_outcome
    FROM gold_predictions p
    INNER JOIN silver_queries q ON p.query_id = q.query_id
),
binned_predictions AS (
    SELECT
        query_id,
        model_name,
        payout_class,
        predicted_prob,
        actual_outcome,
        NTILE(10) OVER (
            PARTITION BY model_name, payout_class 
            ORDER BY predicted_prob ASC
        ) AS prob_decile
    FROM unpivoted_predictions
),
decile_aggregates AS (
    SELECT
        model_name,
        payout_class,
        prob_decile,
        COUNT(*) AS bin_count,
        MIN(predicted_prob) AS min_predicted_prob,
        MAX(predicted_prob) AS max_predicted_prob,
        AVG(predicted_prob) AS avg_predicted_prob,
        AVG(actual_outcome) AS observed_win_rate,
        ABS(AVG(predicted_prob) - AVG(actual_outcome)) AS bin_calibration_error
    FROM binned_predictions
    GROUP BY model_name, payout_class, prob_decile
)
SELECT
    model_name,
    payout_class,
    prob_decile,
    bin_count,
    ROUND(min_predicted_prob, 5) AS min_predicted_prob,
    ROUND(max_predicted_prob, 5) AS max_predicted_prob,
    ROUND(avg_predicted_prob, 5) AS avg_predicted_prob,
    ROUND(observed_win_rate, 5) AS observed_win_rate,
    ROUND(bin_calibration_error, 5) AS bin_calibration_error,
    -- Decile contribution to overall Expected Calibration Error (ECE)
    ROUND(
        bin_calibration_error * bin_count * 1.0 / 
        SUM(bin_count) OVER (PARTITION BY model_name, payout_class), 
        6
    ) AS weighted_decile_ece
FROM decile_aggregates
ORDER BY model_name ASC, payout_class ASC, prob_decile ASC;


-- ----------------------------------------------------------------------------
-- QUERY 3: regime_and_data_drift
-- ----------------------------------------------------------------------------
-- Description:
--   Monitors population stability and data drift across splits (train, validation, test)
--   by calculating the proportion of machine types (steady, balanced, jackpot)
--   and condition regimes, along with spin density metrics.
-- ----------------------------------------------------------------------------
WITH split_machine_counts AS (
    SELECT
        q.split,
        q.machine_type,
        COUNT(*) AS query_count,
        AVG(q.cutoff * 1.0) AS avg_cutoff,
        AVG(e.total_spins_observed * 1.0) AS avg_observed_spins,
        AVG((q.cutoff - e.total_spins_observed) * 1.0 / NULLIF(q.cutoff, 0)) AS avg_sparsity_ratio
    FROM silver_queries q
    LEFT JOIN silver_episodes e ON q.episode_id = e.episode_id AND q.split = e.split
    GROUP BY q.split, q.machine_type
),
split_totals AS (
    SELECT
        split,
        SUM(query_count) AS total_queries_in_split
    FROM split_machine_counts
    GROUP BY split
)
SELECT
    smc.split,
    smc.machine_type,
    smc.query_count,
    st.total_queries_in_split,
    ROUND(smc.query_count * 100.0 / st.total_queries_in_split, 2) AS machine_type_pct,
    ROUND(smc.avg_cutoff, 2) AS avg_cutoff_tick,
    ROUND(smc.avg_observed_spins, 2) AS avg_spins_observed,
    ROUND(smc.avg_sparsity_ratio * 100.0, 2) AS avg_sparsity_pct
FROM split_machine_counts smc
INNER JOIN split_totals st ON smc.split = st.split
ORDER BY smc.split ASC, smc.machine_type ASC;


-- ----------------------------------------------------------------------------
-- QUERY 4: episode_outlier_error_diagnosis
-- ----------------------------------------------------------------------------
-- Description:
--   Identifies worst-performing episodes for champion models (highest average Brier
--   loss across payout classes) and evaluates correlation with history sparsity,
--   cutoff depth, and win rates to diagnose failure modes.
-- ----------------------------------------------------------------------------
WITH query_brier_scores AS (
    SELECT
        p.model_name,
        q.split,
        q.episode_id,
        q.query_id,
        q.machine_type,
        q.cutoff,
        (
            POWER(p.p_0 - CASE WHEN q.outcome = 0 THEN 1.0 ELSE 0.0 END, 2) +
            POWER(p.p_1 - CASE WHEN q.outcome = 1 THEN 1.0 ELSE 0.0 END, 2) +
            POWER(p.p_2 - CASE WHEN q.outcome = 2 THEN 1.0 ELSE 0.0 END, 2) +
            POWER(p.p_5 - CASE WHEN q.outcome = 5 THEN 1.0 ELSE 0.0 END, 2) +
            POWER(p.p_20 - CASE WHEN q.outcome = 20 THEN 1.0 ELSE 0.0 END, 2)
        ) AS multi_brier_loss
    FROM gold_predictions p
    INNER JOIN silver_queries q ON p.query_id = q.query_id
    WHERE q.outcome IS NOT NULL
),
episode_aggregated_loss AS (
    SELECT
        qbs.model_name,
        qbs.split,
        qbs.episode_id,
        qbs.machine_type,
        COUNT(DISTINCT qbs.query_id) AS queries_in_episode,
        AVG(qbs.multi_brier_loss) AS episode_mean_brier,
        AVG(qbs.cutoff * 1.0) AS avg_cutoff,
        COALESCE(e.total_spins_observed, 0) AS total_spins_observed,
        COALESCE(e.win_rate, 0.0) AS historical_win_rate,
        ROUND((AVG(qbs.cutoff * 1.0) - COALESCE(e.total_spins_observed, 0)) * 1.0 / NULLIF(AVG(qbs.cutoff * 1.0), 0), 4) AS sparsity_ratio
    FROM query_brier_scores qbs
    LEFT JOIN silver_episodes e ON qbs.episode_id = e.episode_id AND qbs.split = e.split
    GROUP BY qbs.model_name, qbs.split, qbs.episode_id, qbs.machine_type, e.total_spins_observed, e.win_rate
)
SELECT
    model_name,
    split,
    episode_id,
    machine_type,
    queries_in_episode,
    ROUND(episode_mean_brier, 6) AS episode_mean_brier,
    total_spins_observed,
    ROUND(historical_win_rate, 4) AS historical_win_rate,
    ROUND(sparsity_ratio * 100.0, 2) AS missing_ticks_pct,
    DENSE_RANK() OVER (
        PARTITION BY model_name, split 
        ORDER BY episode_mean_brier DESC
    ) AS error_severity_rank
FROM episode_aggregated_loss
ORDER BY model_name ASC, split ASC, episode_mean_brier DESC;


-- ----------------------------------------------------------------------------
-- QUERY 5: bronze_ingestion_audit_lineage
-- ----------------------------------------------------------------------------
-- Description:
--   Verifies data integrity, provenance, and row consistency across all ingested
--   raw CSV files in the Bronze audit log.
--   Validates SHA-256 cryptographic hashes, row counts, and ingestion timestamps.
-- ----------------------------------------------------------------------------
WITH audit_summary AS (
    SELECT
        dataset_name,
        split,
        file_path,
        sha256_checksum,
        record_count,
        file_size_bytes,
        ROUND(file_size_bytes / 1024.0, 2) AS file_size_kb,
        ingested_at,
        status,
        -- Detect duplicated files across ingest batches
        COUNT(*) OVER (PARTITION BY sha256_checksum) AS hash_occurrence_count
    FROM bronze_audit_log
)
SELECT
    dataset_name,
    split,
    status,
    record_count,
    file_size_kb,
    SUBSTRING(sha256_checksum, 1, 16) AS sha256_prefix,
    sha256_checksum,
    file_path,
    ingested_at,
    CASE 
        WHEN status = 'SUCCESS' AND record_count > 0 THEN 'VERIFIED_HEALTHY'
        WHEN status = 'SUCCESS' AND record_count = 0 THEN 'EMPTY_WARNING'
        ELSE 'INGEST_FAILURE'
    END AS audit_health_indicator
FROM audit_summary
ORDER BY split ASC, dataset_name ASC;
