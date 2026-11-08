"""Evaluation provenance rules, formulas, and compatibility validation."""

from __future__ import annotations

from typing import Any, Dict, Optional, Tuple

from .schema import ConditionLosses, ProvenanceType, TrialRecord


PROVENANCE_METADATA: Dict[ProvenanceType, Dict[str, Any]] = {
    ProvenanceType.PUBLIC_VALIDATION: {
        "display_name": "Public Validation (Development-Exposed)",
        "badge": "[DEV-EXPOSED]",
        "color": "#3b82f6",  # blue
        "formula": r"\text{Points} = \frac{60}{1 + R}, \quad R = \frac{1}{4} \sum_{c \in \text{conditions}} \frac{E_c}{\max(B_c, 10^{-9})}",
        "description": (
            "Normalized 4-condition points (0-60 scale) evaluated on public validation queries. "
            "Because model hyper-parameters and stacking rules were tuned against this set during development, "
            "it is development-exposed and MUST NOT be cited as unbiased test accuracy."
        ),
        "scored": True,
        "is_synthetic": False,
        "points_scale": 60.0,
    },
    ProvenanceType.TRAIN_GROUP_CV: {
        "display_name": "Train Grouped-CV (Sampled Brier)",
        "badge": "[TRAIN-GROUP-CV]",
        "color": "#10b981",  # green
        "formula": r"\text{Mean Brier} = \frac{1}{4} \sum_{c \in \text{conditions}} \text{Brier}_c, \quad \text{Brier} = \frac{1}{N} \sum_{i=1}^N \|p_i - y_i\|_2^2",
        "description": (
            "4-fold whole-episode grouped cross-validation evaluated on discrete sampled outcomes. "
            "Official competition points are strictly NOT available for this provenance. "
            "Lower Brier indicates superior probabilistic forecast."
        ),
        "scored": False,
        "is_synthetic": False,
        "points_scale": None,
    },
    ProvenanceType.VAL_TO_TRAIN: {
        "display_name": "Reverse Split (Validation to Train)",
        "badge": "[VAL-TO-TRAIN]",
        "color": "#8b5cf6",  # purple
        "formula": r"\text{Reverse Brier} = \frac{1}{4} \sum_{c} \text{Brier}_c(\text{model fit on val, tested on train})",
        "description": (
            "Reverse cross-check model fitted on validation and evaluated on train episodes. "
            "Used to detect structural distribution shift or severe overfit to training noise."
        ),
        "scored": False,
        "is_synthetic": False,
        "points_scale": None,
    },
    ProvenanceType.TEST_FORMAT_CHECK: {
        "display_name": "Public Test Format Check (Unscored)",
        "badge": "[FORMAT-ONLY]",
        "color": "#6b7280",  # gray
        "formula": r"\text{N/A (Hidden targets unavailable)}",
        "description": (
            "Verification of submission format on the 1,536 public test queries (checks columns, non-negative "
            "probabilities, row sums to 1.0 within 1e-6). Hidden test ground truth is strictly withheld and "
            "CANNOT be scored. No numeric score is permitted."
        ),
        "scored": False,
        "is_synthetic": False,
        "points_scale": None,
    },
    ProvenanceType.DEMO_SYNTHETIC: {
        "display_name": "Demonstration Only (Synthetic Fixture)",
        "badge": "[DEMO-SYNTHETIC]",
        "color": "#f59e0b",  # amber
        "formula": r"\text{Simulated / Demo-Only Fixture}",
        "description": (
            "Simulated data fixtures generated strictly for UI development, component testing, and offline verification. "
            "These numbers are synthetic and MUST NEVER be reported as real experimental findings or competition evidence."
        ),
        "scored": True,
        "is_synthetic": True,
        "points_scale": 60.0,
    },
}


def get_provenance_meta(provenance: ProvenanceType) -> Dict[str, Any]:
    """Retrieve metadata, formula explanation, and badge styling for a provenance type."""
    if not isinstance(provenance, ProvenanceType):
        provenance = ProvenanceType.from_str(str(provenance))
    return PROVENANCE_METADATA.get(provenance, PROVENANCE_METADATA[ProvenanceType.TRAIN_GROUP_CV])


def get_provenance_badge(provenance: ProvenanceType) -> str:
    """Retrieve text badge string for display in UI or tables."""
    return get_provenance_meta(provenance)["badge"]


def calculate_official_points(condition_losses: ConditionLosses, max_points: float = 60.0) -> float:
    """Compute official technical points from condition losses using contest formula: max_points / (1 + R)."""
    r = condition_losses.mean_ratio
    return max_points / (1.0 + r)


def validate_comparison_compatibility(candidate: TrialRecord, baseline: TrialRecord) -> Tuple[bool, Optional[str]]:
    """Verify that candidate and baseline can be scientifically compared without invalid cross-provenance confounding.

    Returns:
        (True, None) if comparison is valid.
        (False, reason_string) if comparison is invalid or blocked.
    """
    if candidate.trial_id == baseline.trial_id:
        return False, "Cannot compare a trial to itself."

    # 1. Enforce strict provenance equality
    if candidate.provenance != baseline.provenance:
        c_badge = get_provenance_badge(candidate.provenance)
        b_badge = get_provenance_badge(baseline.provenance)
        return (
            False,
            f"Comparison Blocker: Incompatible evaluation provenance ({candidate.provenance.value} {c_badge} "
            f"vs {baseline.provenance.value} {b_badge}). Cross-provenance comparisons are invalid.",
        )

    # 2. Block comparisons on unscored test format check
    if candidate.provenance == ProvenanceType.TEST_FORMAT_CHECK:
        return (
            False,
            "Comparison Blocker: TEST_FORMAT_CHECK runs have no ground truth labels and cannot be scored or compared.",
        )

    # 3. If per-episode errors exist, verify they share held-out episodes
    if candidate.per_episode_errors and baseline.per_episode_errors:
        cand_eps = set(candidate.per_episode_errors.keys())
        base_eps = set(baseline.per_episode_errors.keys())
        shared = cand_eps.intersection(base_eps)
        if not shared:
            return (
                False,
                f"Comparison Blocker: Trials have completely disjoint held-out episodes "
                f"({len(cand_eps)} candidate vs {len(base_eps)} baseline, 0 shared).",
            )
        if cand_eps != base_eps:
            return (
                False,
                f"Comparison Blocker: Trials have differing held-out episode sets "
                f"({len(cand_eps)} candidate vs {len(base_eps)} baseline, {len(shared)} shared). "
                f"Paired episode bootstrap requires identical test folds.",
            )

    # 4. Check episode condition mapping consistency
    if candidate.episode_conditions and baseline.episode_conditions:
        cand_conds = candidate.episode_conditions
        base_conds = baseline.episode_conditions
        common_eps = set(cand_conds.keys()).intersection(base_conds.keys())
        for ep in common_eps:
            if cand_conds[ep] != base_conds[ep]:
                return (
                    False,
                    f"Comparison Blocker: Episode '{ep}' has conflicting condition mapping "
                    f"('{cand_conds[ep]}' in candidate vs '{base_conds[ep]}' in baseline).",
                )

    return True, None


def is_comparable(candidate: TrialRecord, baseline: TrialRecord) -> bool:
    """Convenience boolean check for comparison compatibility."""
    valid, _ = validate_comparison_compatibility(candidate, baseline)
    return valid
