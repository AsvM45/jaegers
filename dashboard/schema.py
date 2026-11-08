"""Clean, frozen domain data contracts and provenance definitions for JAEGERS dashboard."""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


class ProvenanceType(str, Enum):
    """Evaluation provenance categories with strict separation semantics."""

    PUBLIC_VALIDATION = "PUBLIC_VALIDATION"  # 4-condition normalized points (0-60)
    TRAIN_GROUP_CV = "TRAIN_GROUP_CV"        # 4-fold whole-episode sampled Brier (no official points)
    VAL_TO_TRAIN = "VAL_TO_TRAIN"            # Reverse split observed Brier
    TEST_FORMAT_CHECK = "TEST_FORMAT_CHECK"  # Public test format check only (unscored)
    DEMO_SYNTHETIC = "DEMO_SYNTHETIC"        # Explicit synthetic demonstration fixture

    @classmethod
    def from_str(cls, val: str) -> ProvenanceType:
        """Parse string to ProvenanceType, handling aliases and case insensitivity."""
        if isinstance(val, cls):
            return val
        s = str(val).strip().upper()
        mapping = {
            "PUBLIC_VALIDATION": cls.PUBLIC_VALIDATION,
            "PUBLIC_VALIDATION_DEVELOPMENT_EXPOSED": cls.PUBLIC_VALIDATION,
            "DEV_EXPOSED": cls.PUBLIC_VALIDATION,
            "TRAIN_GROUP_CV": cls.TRAIN_GROUP_CV,
            "SAMPLED_OUTCOME_GROUP_CV": cls.TRAIN_GROUP_CV,
            "GROUP_CV": cls.TRAIN_GROUP_CV,
            "VAL_TO_TRAIN": cls.VAL_TO_TRAIN,
            "REVERSE_SPLIT": cls.VAL_TO_TRAIN,
            "TEST_FORMAT_CHECK": cls.TEST_FORMAT_CHECK,
            "PUBLIC_TEST_FORMAT_CHECK": cls.TEST_FORMAT_CHECK,
            "TEST_CHECK": cls.TEST_FORMAT_CHECK,
            "DEMO_SYNTHETIC": cls.DEMO_SYNTHETIC,
            "SYNTHETIC_DEMO": cls.DEMO_SYNTHETIC,
            "DEMO": cls.DEMO_SYNTHETIC,
        }
        if s in mapping:
            return mapping[s]
        try:
            return cls(s)
        except ValueError:
            return cls.TRAIN_GROUP_CV


@dataclass(frozen=True)
class ConditionLosses:
    """Loss ratios across the 4 contest conditions."""

    stable: float
    short_history: float
    drift: float
    shared_change: float

    @property
    def mean_ratio(self) -> float:
        """Unweighted mean loss ratio R = 1/4 * sum(loss_ratios)."""
        return (self.stable + self.short_history + self.drift + self.shared_change) / 4.0

    @property
    def points_60(self) -> float:
        """Official validation technical points = 60 / (1 + R)."""
        return 60.0 / (1.0 + self.mean_ratio)

    @property
    def points_70(self) -> float:
        """Contest technical points = 70 / (1 + R)."""
        return 70.0 / (1.0 + self.mean_ratio)

    def as_dict(self) -> Dict[str, float]:
        """Convert condition losses to dictionary mapping."""
        return {
            "stable": self.stable,
            "short_history": self.short_history,
            "drift": self.drift,
            "shared_change": self.shared_change,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> ConditionLosses:
        """Create from dictionary with flexible keys."""
        return cls(
            stable=float(data.get("stable", 0.0)),
            short_history=float(data.get("short_history", 0.0)),
            drift=float(data.get("drift", 0.0)),
            shared_change=float(data.get("shared_change", 0.0)),
        )


@dataclass(frozen=True)
class TrialRecord:
    """Summary record of an experimental trial for leaderboard and indexing."""

    trial_id: str
    study_name: str
    family: str
    status: str
    provenance: ProvenanceType
    is_champion: bool = False
    source_commit: str = ""
    wall_seconds: float = 0.0
    created_at: str = ""
    finished_at: Optional[str] = None
    official_points: Optional[float] = None
    mean_brier: Optional[float] = None
    condition_losses: Optional[ConditionLosses] = None
    per_episode_errors: Optional[Dict[str, float]] = None
    episode_conditions: Optional[Dict[str, str]] = None
    hyperparameters: Dict[str, Any] = field(default_factory=dict)
    feature_importance: Optional[Dict[str, float]] = None
    calibration_bins: Optional[List[Dict[str, Any]]] = None
    error_message: Optional[str] = None
    is_synthetic: bool = False
    attempt: int = 0
    artifact_path: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Serialize record to dict."""
        res = asdict(self)
        res["provenance"] = self.provenance.value
        if self.condition_losses:
            res["condition_losses"] = self.condition_losses.as_dict()
        return res

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> TrialRecord:
        """Construct record from dict with robust conversions."""
        raw_losses = data.get("condition_losses")
        cond_losses = None
        if raw_losses:
            if isinstance(raw_losses, ConditionLosses):
                cond_losses = raw_losses
            elif isinstance(raw_losses, dict):
                cond_losses = ConditionLosses.from_dict(raw_losses)

        provenance = ProvenanceType.from_str(data.get("provenance", "TRAIN_GROUP_CV"))
        is_syn = bool(data.get("is_synthetic", False) or provenance == ProvenanceType.DEMO_SYNTHETIC)

        return cls(
            trial_id=str(data.get("trial_id", data.get("id", ""))),
            study_name=str(data.get("study_name", data.get("study", "default"))),
            family=str(data.get("family", "jaeger")),
            status=str(data.get("status", "UNKNOWN")).upper(),
            provenance=provenance,
            is_champion=bool(data.get("is_champion", False)),
            source_commit=str(data.get("source_commit", data.get("source_digest", ""))),
            wall_seconds=float(data.get("wall_seconds", 0.0) or 0.0),
            created_at=str(data.get("created_at", "")),
            finished_at=data.get("finished_at"),
            official_points=float(data["official_points"]) if data.get("official_points") is not None else None,
            mean_brier=float(data["mean_brier"]) if data.get("mean_brier") is not None else None,
            condition_losses=cond_losses,
            per_episode_errors=data.get("per_episode_errors"),
            episode_conditions=data.get("episode_conditions"),
            hyperparameters=dict(data.get("hyperparameters", data.get("config", {}))),
            feature_importance=data.get("feature_importance"),
            calibration_bins=data.get("calibration_bins"),
            error_message=data.get("error_message", data.get("error")),
            is_synthetic=is_syn,
            attempt=int(data.get("attempt", 0) or 0),
            artifact_path=data.get("artifact_path", data.get("artifact")),
        )


@dataclass(frozen=True)
class TrialDetail:
    """Full detail of a trial including out-of-fold predictions and process evidence."""

    record: TrialRecord
    oof_predictions: Optional[List[Dict[str, Any]]] = None
    per_query_metrics: Optional[List[Dict[str, Any]]] = None
    folds: Optional[List[Dict[str, Any]]] = None
    raw_config: Optional[Dict[str, Any]] = None
    process_evidence: Optional[Dict[str, Any]] = None
    logs: Optional[str] = None


@dataclass(frozen=True)
class AttemptRecord:
    """Execution attempt metadata from sweep worker."""

    trial_id: str
    attempt: int
    artifact: str
    status: str
    started_at: str
    finished_at: Optional[str] = None
    error: Optional[str] = None


@dataclass(frozen=True)
class CalibrationBin:
    """Probability calibration bin for reliability diagram."""

    payout_class: int
    bin_index: int
    bin_range: Tuple[float, float]
    sample_count: int
    mean_predicted: float
    observed_frequency: float


@dataclass(frozen=True)
class RarePayoutDiagnostic:
    """Specific diagnostic metrics for rare jackpot class (20x)."""

    payout_class: int = 20
    overall_brier_component: float = 0.0
    mean_predicted_prob: float = 0.0
    true_frequency: float = 0.0147
    calibration_correlation: float = 0.0
    under_over_prediction_ratio: float = 1.0
    mae: Optional[float] = None
    ci80_width: Optional[float] = None


@dataclass(frozen=True)
class FeatureImportanceRecord:
    """Feature importance ranking and family classification."""

    feature_name: str
    feature_group: str
    importance_score: float
    rank: int


@dataclass(frozen=True)
class ComponentAblation:
    """Component ablation study result (HE-17 specification)."""

    variant_name: str
    removed_component: str
    hypothesis: str
    official_points: float
    official_points_delta: float
    ci95_points: Tuple[float, float]
    train_brier_delta: Optional[float] = None
    ci95_brier: Optional[Tuple[float, float]] = None
    condition_loss_ratios: Optional[Dict[str, float]] = None
    supported: bool = False
    direction: str = "worse"


@dataclass(frozen=True)
class HypothesisRecord:
    """Pre-registered hypothesis tracking record."""

    id: str
    preregistered_timestamp: str
    component: str
    statement: str
    expected_direction: str
    observed_points_diff: Optional[float] = None
    observed_brier_diff: Optional[float] = None
    verdict: str = "Awaiting Trial Run"
    decision: str = "NO_PROMOTION"
    linked_trial_id: Optional[str] = None


@dataclass(frozen=True)
class PairedComparison:
    """Paired episode statistical difference analysis between candidate and baseline."""

    candidate_id: str
    baseline_id: str
    provenance: ProvenanceType
    mean_delta: float
    ci95_low: float
    ci95_high: float
    p_improvement: float
    supported_improvement: bool
    n_episodes: int
    bootstrap_iterations: int
    episode_deltas: Dict[str, float] = field(default_factory=dict)
    by_condition_delta: Dict[str, float] = field(default_factory=dict)


@dataclass(frozen=True)
class ExecutionLog:
    """Process execution log and error telemetry for failed/interrupted trials."""

    trial_id: str
    attempt: int
    status: str
    wall_seconds: float
    memory_peak_gib: Optional[float] = None
    cpu_threads: int = 1
    error_category: Optional[str] = None
    error_message: Optional[str] = None
    traceback: Optional[str] = None
    stdout_snippet: Optional[str] = None
    stderr_snippet: Optional[str] = None


@dataclass(frozen=True)
class PairedBootstrapResult:
    """Statistical outcome of condition-stratified paired episode bootstrap."""

    mean_delta: float
    ci95_low: float
    ci95_high: float
    p_improvement: float
    supported_improvement: bool
    n_episodes: int
    n_resamples: int
    seed: int
    by_condition_delta: Dict[str, float] = field(default_factory=dict)
    episode_deltas: Dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class CalibrationReport:
    """Multi-class calibration and Brier decomposition report."""

    bins: List[CalibrationBin]
    ece_by_class: Dict[int, float]
    mce_by_class: Dict[int, float]
    overall_ece: float
    overall_mce: float
    class_brier: Dict[int, float]
    by_condition_brier: Dict[str, float]
    overall_brier: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "bins": [asdict(b) for b in self.bins],
            "ece_by_class": self.ece_by_class,
            "mce_by_class": self.mce_by_class,
            "overall_ece": self.overall_ece,
            "overall_mce": self.overall_mce,
            "class_brier": self.class_brier,
            "by_condition_brier": self.by_condition_brier,
            "overall_brier": self.overall_brier,
        }


@dataclass(frozen=True)
class AblationItem:
    """Processed component ablation metrics."""

    variant_name: str
    removed_component: str
    hypothesis: str
    official_points: float
    delta_points: float
    pct_delta_points: float
    ci95_points: Tuple[float, float]
    train_brier_delta: Optional[float] = None
    ci95_brier: Optional[Tuple[float, float]] = None
    status: str = "INCONCLUSIVE"
    supported: bool = False
    direction: str = "worse"


@dataclass(frozen=True)
class AblationAnalysisResult:
    """Waterfall and ranking analysis of component ablations."""

    ranked_ablations: List[AblationItem]
    waterfall_steps: List[Dict[str, Any]]
    max_impact_component: str
    min_impact_component: str
    supported_degradations_count: int

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ranked_ablations": [asdict(a) for a in self.ranked_ablations],
            "waterfall_steps": self.waterfall_steps,
            "max_impact_component": self.max_impact_component,
            "min_impact_component": self.min_impact_component,
            "supported_degradations_count": self.supported_degradations_count,
        }


@dataclass(frozen=True)
class HyperparameterSweepAnalysis:
    """Analysis of hyperparameter search trajectory and parameter correlations."""

    trajectory: List[Dict[str, Any]]
    param_correlations: Dict[str, float]
    param_importance_rank: List[Tuple[str, float]]
    parallel_coords_data: Dict[str, Any]
    best_trial_id: str
    best_metric_value: float

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class HypothesisVerificationResult:
    """Formal hypothesis evaluation outcome."""

    hypothesis_id: str
    statement: str
    expected_direction: str
    status: str  # "CONFIRMED", "REFUTED", "INCONCLUSIVE"
    observed_diff: Optional[float]
    ci95: Optional[Tuple[float, float]]
    decision: str
    explanation: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

