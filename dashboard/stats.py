"""Statistical computation engine for JAEGERS experiment analysis.

Provides:
- Condition-stratified paired episode bootstrapping with 95% confidence intervals.
- Multi-class calibration curves, ECE, MCE, and Brier decomposition across 5 payout classes.
- Rare payout (20x) tail diagnostics: realized MAE, 80% CI width, calibration correlation, ratio.
- Component ablation analysis with waterfall sequencing and significance labeling.
- Hyperparameter and Optuna sweep analysis: trajectories, correlations, parallel coordinates.
- Hypothesis verification engine against observed evidence.
"""

from __future__ import annotations

import math
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union

import numpy as np

from .schema import (
    AblationAnalysisResult,
    AblationItem,
    CalibrationBin,
    CalibrationReport,
    ComponentAblation,
    HyperparameterSweepAnalysis,
    HypothesisRecord,
    HypothesisVerificationResult,
    PairedBootstrapResult,
    RarePayoutDiagnostic,
    TrialRecord,
)

PAYOUT_CLASSES = (0, 1, 2, 5, 20)


def paired_episode_bootstrap(
    candidate_errors: Dict[str, float],
    baseline_errors: Dict[str, float],
    episode_conditions: Dict[str, str],
    n_resamples: int = 2000,
    seed: int = 0,
    strict_episodes: bool = False,
) -> PairedBootstrapResult:
    """Compute condition-stratified bootstrap resampling over shared held-out episodes.

    Computes 95% CI [q0.025, q0.975], mean delta, per-condition deltas,
    P(Delta < 0), and supported_improvement (q0.975 < 0).

    Args:
        candidate_errors: Mapping of episode_id to candidate error/loss.
        baseline_errors: Mapping of episode_id to baseline error/loss.
        episode_conditions: Mapping of episode_id to contest condition name.
        n_resamples: Number of bootstrap draws (default 2000).
        seed: Random seed for deterministic reproducibility.
        strict_episodes: If True, raises ValueError if episode sets are not identical.

    Returns:
        PairedBootstrapResult with bootstrap statistics.
    """
    if not candidate_errors or not baseline_errors:
        raise ValueError("Episode error dictionaries must not be empty.")

    cand_eps = set(candidate_errors.keys())
    base_eps = set(baseline_errors.keys())

    if strict_episodes and cand_eps != base_eps:
        raise ValueError(
            f"Paired comparison requires identical held-out episodes. "
            f"Candidate has {len(cand_eps)}, baseline has {len(base_eps)}."
        )

    shared_eps = sorted(cand_eps.intersection(base_eps))
    if not shared_eps:
        raise ValueError("No shared held-out episodes found between candidate and baseline.")

    diffs = {ep: float(candidate_errors[ep] - baseline_errors[ep]) for ep in shared_eps}

    # Handle N = 1 edge case: single episode cannot compute statistical variance
    if len(shared_eps) == 1:
        single_ep = shared_eps[0]
        delta = diffs[single_ep]
        cond = episode_conditions.get(single_ep, "unknown")
        return PairedBootstrapResult(
            mean_delta=delta,
            ci95_low=delta,
            ci95_high=delta,
            p_improvement=1.0 if delta < 0 else 0.0,
            supported_improvement=False,
            n_episodes=1,
            n_resamples=n_resamples,
            seed=seed,
            by_condition_delta={cond: delta},
            episode_deltas=diffs,
        )

    # Condition-stratified bootstrap resampling
    groups = sorted(set(episode_conditions.get(ep, "unknown") for ep in shared_eps))
    by_cond: Dict[str, float] = {}
    means: List[float] = []
    rng = np.random.default_rng(seed)
    draws = np.zeros(n_resamples)

    for c in groups:
        vals = np.array(
            [diffs[ep] for ep in shared_eps if episode_conditions.get(ep, "unknown") == c],
            dtype=float,
        )
        if len(vals) == 0:
            continue
        c_mean = float(vals.mean())
        by_cond[c] = c_mean
        means.append(c_mean)
        if len(vals) >= 2:
            draws += rng.choice(vals, size=(n_resamples, len(vals)), replace=True).mean(axis=1) / len(groups)
        else:
            draws += vals[0] / len(groups)

    mean_delta = float(np.mean(means)) if means else 0.0
    ci95 = np.quantile(draws, [0.025, 0.975]).tolist() if len(draws) > 0 else [mean_delta, mean_delta]
    p_imp = float((draws < 0).mean()) if len(draws) > 0 else 0.5
    supported = bool(ci95[1] < 0)

    return PairedBootstrapResult(
        mean_delta=mean_delta,
        ci95_low=float(ci95[0]),
        ci95_high=float(ci95[1]),
        p_improvement=p_imp,
        supported_improvement=supported,
        n_episodes=len(shared_eps),
        n_resamples=n_resamples,
        seed=seed,
        by_condition_delta=by_cond,
        episode_deltas=diffs,
    )


def calculate_calibration_curve(
    probabilities: Union[np.ndarray, Sequence[Sequence[float]]],
    labels: Union[np.ndarray, Sequence[int]],
    n_bins: int = 10,
    conditions: Optional[Sequence[str]] = None,
    payout_classes: Tuple[int, ...] = PAYOUT_CLASSES,
) -> CalibrationReport:
    """Calculate multi-class calibration curves, ECE, MCE, and Brier decomposition.

    Evaluates calibration across 10 probability bins for each payout class
    (0x, 1x, 2x, 5x, 20x).

    Args:
        probabilities: Array-like of shape (N, K) containing predicted probabilities.
        labels: Array-like of shape (N,) containing class indices (0..4) or payout values.
        n_bins: Number of probability bins (default 10).
        conditions: Optional sequence of condition labels per query.
        payout_classes: Payout class labels tuple (default 0, 1, 2, 5, 20).

    Returns:
        CalibrationReport containing bins, ECE, MCE, and Brier decomposition.
    """
    probs = np.asarray(probabilities, dtype=float)
    if probs.ndim != 2:
        raise ValueError(f"Probabilities must be 2D array of shape (N, K), got shape {probs.shape}")

    n_samples, n_classes = probs.shape
    if n_samples == 0:
        raise ValueError("Cannot calculate calibration curve on empty sample set.")
    if n_classes != len(payout_classes):
        raise ValueError(
            f"Expected {len(payout_classes)} classes ({payout_classes}), got {n_classes} columns."
        )

    # Normalize row probabilities if slight floating point drift
    row_sums = probs.sum(axis=1, keepdims=True)
    row_sums = np.where(row_sums == 0, 1.0, row_sums)
    probs = probs / row_sums

    # Convert labels: handle if labels are payout values (e.g. [0, 1, 2, 5, 20]) vs indices (0..4)
    raw_labels = np.asarray(labels)
    if raw_labels.ndim != 1 or len(raw_labels) != n_samples:
        raise ValueError(f"Labels must be 1D array of length {n_samples}, got shape {raw_labels.shape}")

    # Map payout values to class indices if needed
    payout_to_idx = {p: i for i, p in enumerate(payout_classes)}
    if any(val in (5, 20) for val in raw_labels) or set(raw_labels).issubset(set(payout_classes)):
        label_indices = np.array([payout_to_idx.get(val, int(val)) for val in raw_labels], dtype=int)
    else:
        label_indices = raw_labels.astype(int)

    # Multi-class one-hot encoding
    y_onehot = np.eye(n_classes)[label_indices]

    # Multi-class Brier score decomposition by class
    squared_errors = (probs - y_onehot) ** 2
    overall_brier = float(squared_errors.sum(axis=1).mean())
    class_brier = {
        payout_classes[k]: float(squared_errors[:, k].mean()) for k in range(n_classes)
    }

    # Brier by condition if provided
    by_condition_brier: Dict[str, float] = {}
    if conditions is not None and len(conditions) == n_samples:
        cond_array = np.asarray(conditions)
        for c in sorted(set(cond_array)):
            mask = cond_array == c
            if mask.any():
                by_condition_brier[str(c)] = float(squared_errors[mask].sum(axis=1).mean())

    # Calibration bins and errors per class
    calibration_bins: List[CalibrationBin] = []
    ece_by_class: Dict[int, float] = {}
    mce_by_class: Dict[int, float] = {}

    for k in range(n_classes):
        p_class = probs[:, k]
        payout_val = payout_classes[k]
        ece_k = 0.0
        mce_k = 0.0

        for b in range(n_bins):
            lower = b / n_bins
            upper = (b + 1) / n_bins
            if b == n_bins - 1:
                bin_mask = (p_class >= lower) & (p_class <= upper)
            else:
                bin_mask = (p_class >= lower) & (p_class < upper)

            count = int(bin_mask.sum())
            if count > 0:
                pred_mean = float(p_class[bin_mask].mean())
                obs_freq = float((label_indices[bin_mask] == k).mean())
                gap = abs(pred_mean - obs_freq)
                ece_k += (count / n_samples) * gap
                if gap > mce_k:
                    mce_k = gap
            else:
                pred_mean = (lower + upper) / 2.0
                obs_freq = 0.0

            calibration_bins.append(
                CalibrationBin(
                    payout_class=payout_val,
                    bin_index=b,
                    bin_range=(lower, upper),
                    sample_count=count,
                    mean_predicted=pred_mean,
                    observed_frequency=obs_freq,
                )
            )

        ece_by_class[payout_val] = float(ece_k)
        mce_by_class[payout_val] = float(mce_k)

    overall_ece = float(np.mean(list(ece_by_class.values())))
    overall_mce = float(np.max(list(mce_by_class.values())))

    return CalibrationReport(
        bins=calibration_bins,
        ece_by_class=ece_by_class,
        mce_by_class=mce_by_class,
        overall_ece=overall_ece,
        overall_mce=overall_mce,
        class_brier=class_brier,
        by_condition_brier=by_condition_brier,
        overall_brier=overall_brier,
    )


def decompose_brier_score(
    probabilities: Union[np.ndarray, Sequence[Sequence[float]]],
    labels: Union[np.ndarray, Sequence[int]],
    n_bins: int = 10,
) -> Dict[str, float]:
    """Decompose Brier score into Murphy (1973) components: Reliability, Resolution, Uncertainty.

    Brier = Reliability - Resolution + Uncertainty.

    Returns:
        Dictionary with overall_brier, reliability, resolution, uncertainty.
    """
    probs = np.asarray(probabilities, dtype=float)
    n_samples, n_classes = probs.shape
    raw_labels = np.asarray(labels, dtype=int)
    y_onehot = np.eye(n_classes)[raw_labels]

    overall_brier = float(((probs - y_onehot) ** 2).sum(axis=1).mean())

    # Overall base rates
    base_rates = y_onehot.mean(axis=0)
    uncertainty = float(np.sum(base_rates * (1.0 - base_rates)))

    reliability = 0.0
    resolution = 0.0

    for k in range(n_classes):
        p_k = probs[:, k]
        y_k = y_onehot[:, k]
        base_k = base_rates[k]

        for b in range(n_bins):
            lower = b / n_bins
            upper = (b + 1) / n_bins
            if b == n_bins - 1:
                mask = (p_k >= lower) & (p_k <= upper)
            else:
                mask = (p_k >= lower) & (p_k < upper)

            cnt = int(mask.sum())
            if cnt > 0:
                p_bar = float(p_k[mask].mean())
                y_bar = float(y_k[mask].mean())
                weight = cnt / n_samples
                reliability += weight * ((p_bar - y_bar) ** 2)
                resolution += weight * ((y_bar - base_k) ** 2)

    return {
        "overall_brier": overall_brier,
        "reliability": float(reliability),
        "resolution": float(resolution),
        "uncertainty": float(uncertainty),
    }


def analyze_rare_payout_tail(
    probabilities: Union[np.ndarray, Sequence[Sequence[float]]],
    labels: Union[np.ndarray, Sequence[int]],
    payouts: Tuple[int, ...] = PAYOUT_CLASSES,
    rare_class_idx: int = 4,
) -> RarePayoutDiagnostic:
    """Analyze tail risk diagnostics for the rare jackpot class (20x).

    Computes:
    - Realized payout MAE: mean |expected_forecast - realized_payout|.
    - 80% CI width: mean(q0.90 - q0.10) over prediction distributions.
    - Calibration correlation: correlation between predicted rare probability and rare event.
    - Under/over-prediction ratio: mean_predicted / true_frequency.
    - Overall Brier component for rare class.

    Args:
        probabilities: Array-like of shape (N, 5).
        labels: Array-like of shape (N,) with class indices or payout values.
        payouts: Tuple of payout amounts (0, 1, 2, 5, 20).
        rare_class_idx: Index of rare class (default 4 for 20x).

    Returns:
        RarePayoutDiagnostic instance.
    """
    probs = np.asarray(probabilities, dtype=float)
    n_samples, n_classes = probs.shape
    if n_samples == 0:
        raise ValueError("Cannot analyze rare payout tail on empty dataset.")

    # Normalize row sums
    row_sums = probs.sum(axis=1, keepdims=True)
    row_sums = np.where(row_sums == 0, 1.0, row_sums)
    probs = probs / row_sums

    raw_labels = np.asarray(labels)
    # Map to integer class indices if payouts passed
    payout_to_idx = {p: i for i, p in enumerate(payouts)}
    if any(val in (5, 20) for val in raw_labels) or set(raw_labels).issubset(set(payouts)):
        label_indices = np.array([payout_to_idx.get(val, int(val)) for val in raw_labels], dtype=int)
    else:
        label_indices = raw_labels.astype(int)

    payout_vals = np.array(payouts, dtype=float)
    realized_payouts = payout_vals[label_indices]

    # Expected payout forecast: E[Y] = sum(p_k * payout_k)
    expected_payouts = np.dot(probs, payout_vals)
    realized_mae = float(np.mean(np.abs(expected_payouts - realized_payouts)))

    # 80% CI width: q0.90 - q0.10 from cumulative payout distribution
    ci_widths: List[float] = []
    cum_probs = np.cumsum(probs, axis=1)
    for i in range(n_samples):
        c = cum_probs[i]
        # Quantile 0.10
        idx_low = int(np.searchsorted(c, 0.10, side="left"))
        q_low = payout_vals[min(idx_low, n_classes - 1)]
        # Quantile 0.90
        idx_high = int(np.searchsorted(c, 0.90, side="left"))
        q_high = payout_vals[min(idx_high, n_classes - 1)]
        ci_widths.append(float(q_high - q_low))

    mean_ci80_width = float(np.mean(ci_widths))

    # Rare class diagnostics
    rare_probs = probs[:, rare_class_idx]
    rare_indicator = (label_indices == rare_class_idx).astype(float)

    mean_pred_rare = float(np.mean(rare_probs))
    true_freq_rare = float(np.mean(rare_indicator))

    # Under/over prediction ratio
    if true_freq_rare > 0:
        ratio = float(mean_pred_rare / true_freq_rare)
    else:
        ratio = 1.0 if mean_pred_rare == 0 else 999.0

    # Calibration correlation
    if np.std(rare_probs) > 1e-12 and np.std(rare_indicator) > 1e-12:
        corr_matrix = np.corrcoef(rare_probs, rare_indicator)
        calib_corr = float(corr_matrix[0, 1])
    else:
        calib_corr = 0.0

    overall_brier_comp = float(np.mean((rare_probs - rare_indicator) ** 2))

    return RarePayoutDiagnostic(
        payout_class=payouts[rare_class_idx],
        overall_brier_component=overall_brier_comp,
        mean_predicted_prob=mean_pred_rare,
        true_frequency=true_freq_rare,
        calibration_correlation=calib_corr,
        under_over_prediction_ratio=ratio,
        mae=realized_mae,
        ci80_width=mean_ci80_width,
    )


def analyze_component_ablations(
    ablations: Union[Sequence[ComponentAblation], Sequence[Dict[str, Any]]],
    baseline_points: float = 55.121615,
    baseline_brier: Optional[float] = None,
    significance_threshold: float = 0.05,
) -> AblationAnalysisResult:
    """Analyze pre-registered component ablations with waterfall sequencing and significance labeling.

    Args:
        ablations: List of ComponentAblation dataclasses or dict equivalents.
        baseline_points: Official points of baseline champion (default 55.121615).
        baseline_brier: Optional baseline Brier score for relative delta.
        significance_threshold: Threshold for statistical significance.

    Returns:
        AblationAnalysisResult with ranked items, waterfall steps, and key components.
    """
    items: List[AblationItem] = []

    for a in ablations:
        if isinstance(a, ComponentAblation):
            name = a.variant_name
            comp = a.removed_component
            hyp = a.hypothesis
            pts = a.official_points
            delta = a.official_points_delta
            ci95 = a.ci95_points
            brier_delta = a.train_brier_delta
            ci95_brier = a.ci95_brier
            supported = a.supported
            direction = a.direction
        else:
            name = str(a.get("variant_name", a.get("name", "")))
            comp = str(a.get("removed_component", a.get("component", "")))
            hyp = str(a.get("hypothesis", ""))
            pts = float(a.get("official_points", 0.0))
            delta = float(a.get("official_points_delta", pts - baseline_points))
            ci_raw = a.get("ci95_points", (delta, delta))
            ci95 = (float(ci_raw[0]), float(ci_raw[1]))
            brier_delta = a.get("train_brier_delta")
            ci95_brier = a.get("ci95_brier")
            supported = bool(a.get("supported", False))
            direction = str(a.get("direction", "worse"))

        pct_delta = float((delta / baseline_points) * 100.0) if baseline_points != 0 else 0.0

        # Significance determination
        if ci95[1] < 0:
            status = "SUPPORTED_DEGRADATION"
            sup = True
            dir_str = "worse"
        elif ci95[0] > 0:
            status = "SUPPORTED_IMPROVEMENT"
            sup = True
            dir_str = "better"
        elif abs(delta) < significance_threshold:
            status = "NEGLIGIBLE"
            sup = False
            dir_str = "neutral"
        else:
            status = "INCONCLUSIVE"
            sup = False
            dir_str = "worse" if delta < 0 else "better"

        items.append(
            AblationItem(
                variant_name=name,
                removed_component=comp,
                hypothesis=hyp,
                official_points=pts,
                delta_points=delta,
                pct_delta_points=pct_delta,
                ci95_points=ci95,
                train_brier_delta=brier_delta,
                ci95_brier=ci95_brier,
                status=status,
                supported=sup,
                direction=dir_str,
            )
        )

    # Sort items by degradation severity (most negative delta first)
    ranked = sorted(items, key=lambda x: x.delta_points)

    # Waterfall ordering
    waterfall_steps: List[Dict[str, Any]] = [
        {
            "step": "Baseline Champion",
            "component": "Full Model",
            "delta": 0.0,
            "running_total": baseline_points,
            "type": "base",
        }
    ]

    for item in ranked:
        waterfall_steps.append(
            {
                "step": f"Remove {item.removed_component}",
                "component": item.removed_component,
                "delta": item.delta_points,
                "running_total": item.official_points,
                "type": "relative",
            }
        )

    max_impact = ranked[0].removed_component if ranked else "none"
    min_impact = sorted(items, key=lambda x: abs(x.delta_points))[0].removed_component if items else "none"
    n_supported_deg = sum(1 for x in items if x.status == "SUPPORTED_DEGRADATION")

    return AblationAnalysisResult(
        ranked_ablations=ranked,
        waterfall_steps=waterfall_steps,
        max_impact_component=max_impact,
        min_impact_component=min_impact,
        supported_degradations_count=n_supported_deg,
    )


def analyze_hyperparameter_sweep(
    trials: Union[Sequence[TrialRecord], Sequence[Dict[str, Any]]],
    metric_key: str = "mean_brier",
    maximize: bool = False,
) -> HyperparameterSweepAnalysis:
    """Analyze hyperparameter optimization sweep trajectories and parameter correlations.

    Computes:
    - Optimization trajectory (trial-by-trial metric and running best).
    - Correlation between numeric hyperparameters and the optimization metric.
    - Parameter importance ranking.
    - Parallel coordinates visualization format.

    Args:
        trials: Sequence of TrialRecords or dictionaries.
        metric_key: Objective metric key to optimize (default "mean_brier").
        maximize: If True, higher is better; if False, lower is better.

    Returns:
        HyperparameterSweepAnalysis instance.
    """
    valid_trials: List[Dict[str, Any]] = []

    for idx, t in enumerate(trials):
        if isinstance(t, TrialRecord):
            tid = t.trial_id
            created = t.created_at or str(idx)
            val = getattr(t, metric_key, None)
            params = dict(t.hyperparameters)
        else:
            tid = str(t.get("trial_id", t.get("id", f"trial_{idx}")))
            created = str(t.get("created_at", idx))
            val = t.get(metric_key)
            params = dict(t.get("hyperparameters", t.get("config", {})))

        if val is not None and math.isfinite(float(val)):
            valid_trials.append(
                {
                    "trial_id": tid,
                    "created_at": created,
                    "metric": float(val),
                    "params": params,
                }
            )

    if not valid_trials:
        return HyperparameterSweepAnalysis(
            trajectory=[],
            param_correlations={},
            param_importance_rank=[],
            parallel_coords_data={"dimensions": [], "metrics": []},
            best_trial_id="",
            best_metric_value=0.0,
        )

    # Sort trials chronologically
    valid_trials.sort(key=lambda x: x["created_at"])

    # Compute trajectory
    trajectory: List[Dict[str, Any]] = []
    best_val = -float("inf") if maximize else float("inf")
    best_tid = ""

    for step, item in enumerate(valid_trials):
        m = item["metric"]
        if maximize:
            if m > best_val:
                best_val = m
                best_tid = item["trial_id"]
        else:
            if m < best_val:
                best_val = m
                best_tid = item["trial_id"]

        trajectory.append(
            {
                "step": step + 1,
                "trial_id": item["trial_id"],
                "metric": m,
                "running_best": best_val,
                "params": item["params"],
            }
        )

    # Identify numeric hyperparameters
    all_numeric_params: Dict[str, List[float]] = {}
    metric_values = [item["metric"] for item in valid_trials]

    for item in valid_trials:
        for p_name, p_val in item["params"].items():
            if isinstance(p_val, (int, float)) and not isinstance(p_val, bool) and math.isfinite(p_val):
                if p_name not in all_numeric_params:
                    all_numeric_params[p_name] = []

    # Populate vectors for params present in all or most trials
    correlations: Dict[str, float] = {}
    for p_name in list(all_numeric_params.keys()):
        p_vec = []
        m_vec = []
        for item in valid_trials:
            if p_name in item["params"]:
                pv = item["params"][p_name]
                if isinstance(pv, (int, float)) and not isinstance(pv, bool) and math.isfinite(pv):
                    p_vec.append(float(pv))
                    m_vec.append(item["metric"])

        if len(p_vec) >= 3 and np.std(p_vec) > 1e-12 and np.std(m_vec) > 1e-12:
            r = float(np.corrcoef(p_vec, m_vec)[0, 1])
            correlations[p_name] = r

    # Parameter importance rank by absolute correlation
    importance_rank = sorted(
        [(k, abs(v)) for k, v in correlations.items()], key=lambda x: x[1], reverse=True
    )

    # Parallel coordinates preparation
    dimensions: List[Dict[str, Any]] = []
    for p_name in correlations.keys():
        vals = [
            float(item["params"].get(p_name, np.nan))
            for item in valid_trials
            if p_name in item["params"]
        ]
        if vals:
            dimensions.append(
                {
                    "name": p_name,
                    "min": float(min(vals)),
                    "max": float(max(vals)),
                    "values": vals,
                }
            )

    parallel_data = {
        "dimensions": dimensions,
        "metrics": metric_values,
        "trial_ids": [item["trial_id"] for item in valid_trials],
    }

    return HyperparameterSweepAnalysis(
        trajectory=trajectory,
        param_correlations=correlations,
        param_importance_rank=importance_rank,
        parallel_coords_data=parallel_data,
        best_trial_id=best_tid,
        best_metric_value=best_val,
    )


def verify_hypothesis(
    hypothesis: Union[HypothesisRecord, Dict[str, Any]],
    observed_points_diff: Optional[float] = None,
    observed_brier_diff: Optional[float] = None,
    ci95_points: Optional[Tuple[float, float]] = None,
    ci95_brier: Optional[Tuple[float, float]] = None,
    significance_alpha: float = 0.05,
) -> HypothesisVerificationResult:
    """Evaluate formal hypothesis against observed points / Brier diff.

    Assigns status: CONFIRMED, REFUTED, or INCONCLUSIVE.
    Assigns decision: PROMOTE, REJECT, MAINTAIN_BASELINE, or NO_PROMOTION.

    Args:
        hypothesis: HypothesisRecord or dictionary defining hypothesis.
        observed_points_diff: Candidate points minus baseline points (or ablation points minus champ).
        observed_brier_diff: Candidate Brier minus baseline Brier.
        ci95_points: 95% confidence interval for points delta.
        ci95_brier: 95% confidence interval for Brier delta.
        significance_alpha: Alpha level (default 0.05).

    Returns:
        HypothesisVerificationResult instance.
    """
    if isinstance(hypothesis, HypothesisRecord):
        h_id = hypothesis.id
        stmt = hypothesis.statement
        exp_dir = hypothesis.expected_direction.lower()
        if observed_points_diff is None:
            observed_points_diff = hypothesis.observed_points_diff
        if observed_brier_diff is None:
            observed_brier_diff = hypothesis.observed_brier_diff
    else:
        h_id = str(hypothesis.get("id", "H-000"))
        stmt = str(hypothesis.get("statement", ""))
        exp_dir = str(hypothesis.get("expected_direction", "worse")).lower()
        if observed_points_diff is None:
            observed_points_diff = hypothesis.get("observed_points_diff")
        if observed_brier_diff is None:
            observed_brier_diff = hypothesis.get("observed_brier_diff")

    # Evaluate using points delta if available
    if observed_points_diff is not None:
        diff = float(observed_points_diff)
        ci = ci95_points

        if exp_dir in ("worse", "degradation", "negative"):
            # Expected removing component will hurt performance (delta < 0)
            if ci is not None:
                if ci[1] < 0:
                    status = "CONFIRMED"
                    decision = "MAINTAIN_BASELINE"
                    explanation = (
                        f"Statistically supported degradation (Δ = {diff:.4f}, 95% CI [{ci[0]:.4f}, {ci[1]:.4f}]). "
                        f"Component verified as essential to model performance."
                    )
                elif ci[0] > 0:
                    status = "REFUTED"
                    decision = "FURTHER_STUDY"
                    explanation = (
                        f"Unexpected statistically significant improvement upon component removal "
                        f"(Δ = {diff:.4f}, 95% CI [{ci[0]:.4f}, {ci[1]:.4f}])."
                    )
                else:
                    status = "INCONCLUSIVE"
                    decision = "NO_PROMOTION"
                    explanation = (
                        f"Degradation is not statistically significant (95% CI spans zero: [{ci[0]:.4f}, {ci[1]:.4f}])."
                    )
            else:
                if diff < -0.05:
                    status = "CONFIRMED"
                    decision = "MAINTAIN_BASELINE"
                    explanation = f"Observed degradation (Δ = {diff:.4f}) aligns with hypothesis."
                elif diff > 0.05:
                    status = "REFUTED"
                    decision = "FURTHER_STUDY"
                    explanation = f"Observed unexpected improvement (Δ = {diff:.4f})."
                else:
                    status = "INCONCLUSIVE"
                    decision = "NO_PROMOTION"
                    explanation = f"Observed difference is within noise threshold (Δ = {diff:.4f})."

            return HypothesisVerificationResult(
                hypothesis_id=h_id,
                statement=stmt,
                expected_direction=exp_dir,
                status=status,
                observed_diff=diff,
                ci95=ci,
                decision=decision,
                explanation=explanation,
            )

        elif exp_dir in ("better", "improvement", "positive"):
            # Expected improvement (delta > 0)
            if ci is not None:
                if ci[0] > 0:
                    status = "CONFIRMED"
                    decision = "PROMOTE"
                    explanation = (
                        f"Statistically supported improvement (Δ = {diff:.4f}, 95% CI [{ci[0]:.4f}, {ci[1]:.4f}]). "
                        f"Promotion is recommended."
                    )
                elif ci[1] < 0:
                    status = "REFUTED"
                    decision = "REJECT"
                    explanation = (
                        f"Significant degradation observed (Δ = {diff:.4f}, 95% CI [{ci[0]:.4f}, {ci[1]:.4f}])."
                    )
                else:
                    status = "INCONCLUSIVE"
                    decision = "NO_PROMOTION"
                    explanation = "Improvement is not statistically significant (95% CI spans zero)."
            else:
                if diff > 0.05:
                    status = "CONFIRMED"
                    decision = "PROMOTE"
                    explanation = f"Observed improvement (Δ = {diff:.4f})."
                elif diff < -0.05:
                    status = "REFUTED"
                    decision = "REJECT"
                    explanation = f"Observed degradation (Δ = {diff:.4f})."
                else:
                    status = "INCONCLUSIVE"
                    decision = "NO_PROMOTION"
                    explanation = f"Observed difference is within noise threshold (Δ = {diff:.4f})."

            return HypothesisVerificationResult(
                hypothesis_id=h_id,
                statement=stmt,
                expected_direction=exp_dir,
                status=status,
                observed_diff=diff,
                ci95=ci,
                decision=decision,
                explanation=explanation,
            )

    # Evaluate using Brier diff if points not available (lower Brier is better!)
    if observed_brier_diff is not None:
        diff = float(observed_brier_diff)
        ci = ci95_brier

        if exp_dir in ("worse", "degradation", "negative"):
            # Removing component increases Brier error (delta > 0)
            if ci is not None:
                if ci[0] > 0:
                    status = "CONFIRMED"
                    decision = "MAINTAIN_BASELINE"
                    explanation = f"Statistically supported Brier loss increase (Δ = {diff:.6f}, 95% CI [{ci[0]:.6f}, {ci[1]:.6f}])."
                elif ci[1] < 0:
                    status = "REFUTED"
                    decision = "FURTHER_STUDY"
                    explanation = f"Unexpected Brier reduction upon removal (Δ = {diff:.6f}, 95% CI [{ci[0]:.6f}, {ci[1]:.6f}])."
                else:
                    status = "INCONCLUSIVE"
                    decision = "NO_PROMOTION"
                    explanation = "Brier difference is not statistically significant (95% CI spans zero)."
            else:
                status = "CONFIRMED" if diff > 0.0005 else ("REFUTED" if diff < -0.0005 else "INCONCLUSIVE")
                decision = "MAINTAIN_BASELINE" if status == "CONFIRMED" else "NO_PROMOTION"
                explanation = f"Point estimate Brier delta = {diff:.6f}."

            return HypothesisVerificationResult(
                hypothesis_id=h_id,
                statement=stmt,
                expected_direction=exp_dir,
                status=status,
                observed_diff=diff,
                ci95=ci,
                decision=decision,
                explanation=explanation,
            )

        elif exp_dir in ("better", "improvement", "positive"):
            # Improvement decreases Brier error (delta < 0)
            if ci is not None:
                if ci[1] < 0:
                    status = "CONFIRMED"
                    decision = "PROMOTE"
                    explanation = f"Statistically supported Brier improvement (Δ = {diff:.6f}, 95% CI [{ci[0]:.6f}, {ci[1]:.6f}])."
                elif ci[0] > 0:
                    status = "REFUTED"
                    decision = "REJECT"
                    explanation = f"Significant Brier degradation observed (Δ = {diff:.6f}, 95% CI [{ci[0]:.6f}, {ci[1]:.6f}])."
                else:
                    status = "INCONCLUSIVE"
                    decision = "NO_PROMOTION"
                    explanation = "Brier improvement is not statistically significant (95% CI spans zero)."
            else:
                status = "CONFIRMED" if diff < -0.0005 else ("REFUTED" if diff > 0.0005 else "INCONCLUSIVE")
                decision = "PROMOTE" if status == "CONFIRMED" else "NO_PROMOTION"
                explanation = f"Point estimate Brier delta = {diff:.6f}."

            return HypothesisVerificationResult(
                hypothesis_id=h_id,
                statement=stmt,
                expected_direction=exp_dir,
                status=status,
                observed_diff=diff,
                ci95=ci,
                decision=decision,
                explanation=explanation,
            )

    return HypothesisVerificationResult(
        hypothesis_id=h_id,
        statement=stmt,
        expected_direction=exp_dir,
        status="INCONCLUSIVE",
        observed_diff=None,
        ci95=None,
        decision="NO_PROMOTION",
        explanation="No empirical points or Brier difference evidence provided for verification.",
    )
