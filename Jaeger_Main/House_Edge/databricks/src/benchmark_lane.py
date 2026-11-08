"""Governed Model Benchmark Lane for JAEGERS House Edge (Issue #86)

Provides read-only ingestion, normalization, provenance isolation, paired bootstrap
CI95 gating, rare 20x payout calibration auditing, and Delta/MLflow persistence across
all House Edge model families and ablation studies without modifying offline competition
inference code or research artifacts.

Core Governance Rules:
1. Strict Provenance Isolation:
   Never conflate scores across incompatible evaluation tiers:
   - `sampled_outcome_group_cv`: 5-fold grouped cross-validation on `train` against
     realized discrete spin outcomes (`outcome in {0, 1, 2, 5, 20}`, mean Brier ~0.362).
   - `official_public_validation`: Public validation evaluation against true 5-element
     payout probability vectors (`p_0..p_20`, mean Brier ~0.0566, official points ~55.12).
   - `dev_exposed_public_validation_sampled_outcome`: Public validation queries evaluated
     against realized discrete outcomes (`outcome in {0, 1, 2, 5, 20}`, mean Brier ~0.550).
2. Read-Only Research Ingestion:
   Reads frozen JSON reports from `Jaeger_Main/House_Edge/research/{reports,audits,configs}/`
   without mutating any source files.
3. Serverless Startup Safety:
   Resolves module paths without relying on `__file__` so the script executes cleanly
   inside Databricks Serverless `exec(compile(...))` wrappers.
"""

from __future__ import annotations

import argparse
import dataclasses
import hashlib
import inspect
import json
import logging
import math
import os
import sys
import types
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np
import pandas as pd


def _resolve_src_dir() -> str:
    """Resolves `databricks/src` directory safely even when `__file__` is undefined."""
    g = globals()
    for var_name in ("__file__", "filename"):
        cand = g.get(var_name)
        if isinstance(cand, str) and cand and not cand.startswith("<"):
            return os.path.dirname(os.path.abspath(cand))
    frame = inspect.currentframe()
    try:
        while frame is not None:
            co_file = frame.f_code.co_filename
            if isinstance(co_file, str) and co_file and not co_file.startswith("<"):
                cand_dir = os.path.dirname(os.path.abspath(co_file))
                if os.path.isfile(os.path.join(cand_dir, "session.py")):
                    return cand_dir
            frame = frame.f_back
    finally:
        del frame
    if sys.argv and sys.argv[0] and not sys.argv[0].startswith("-"):
        cand_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
        if os.path.isdir(cand_dir):
            return cand_dir
    cwd = os.getcwd()
    for rel in ("", "src", os.path.join("Jaeger_Main", "House_Edge", "databricks", "src")):
        cand = os.path.abspath(os.path.join(cwd, rel))
        if os.path.isfile(os.path.join(cand, "session.py")):
            return cand
    return cwd


_SRC_DIR = _resolve_src_dir()
if _SRC_DIR not in sys.path:
    sys.path.insert(0, _SRC_DIR)

if __name__ not in sys.modules:
    _mod = types.ModuleType(__name__)
    _mod.__dict__.update(globals())
    sys.modules[__name__] = _mod

try:
    from .session import get_mlflow, get_spark_session
except (ImportError, ValueError):
    from session import get_mlflow, get_spark_session

logger = logging.getLogger("jaegers.databricks.benchmark_lane")

VALID_PROVENANCE_TIERS = (
    "sampled_outcome_group_cv",
    "official_public_validation",
    "dev_exposed_public_validation_sampled_outcome",
)

LIVE_SERVERLESS_EVALUATIONS: List[Dict[str, Any]] = [
    {
        "study_name": "databricks_serverless_job_888066060424343",
        "model_name": "empirical_bayes_k50",
        "model_family": "dirichlet_empirical_bayes_baseline",
        "feature_groups": "canonical_471_gold_features",
        "hyperparams": {"smoothing_k": 50.0, "prior": "train_machine_type", "eval_queries": 768},
        "seed": 42,
        "fold_scheme": "public_train_to_validation_split",
        "evaluation_provenance": "dev_exposed_public_validation_sampled_outcome",
        "split": "public_validation",
        "primary_metric_name": "sampled_brier",
        "primary_metric_value": 0.550339,
        "mean_brier": 0.550339,
        "official_points": None,
        "log_loss": 1.158627,
        "ece_calibration": 0.025798,
        "brier_stable": 0.542758,
        "brier_short_history": 0.608005,
        "brier_drift": 0.491081,
        "brier_shared_change": 0.559513,
        "class_brier_0": 0.242310,
        "class_brier_1": 0.168420,
        "class_brier_2": 0.089150,
        "class_brier_5": 0.038120,
        "class_brier_20": 0.012339,
        "mean_pred_p20": 0.011850,
        "mean_target_p20": 0.011719,
        "corr_p20": 0.114200,
        "validation_target_exposure": False,
        "historical_signal_policy": "strict_tick_lt_cutoff_gold_features",
        "wall_seconds": 30.892,
        "source_artifact": "workspace.house_edge.gold_model_evaluations#run=8f04cbec276044c9a99ae5c3569d227d",
    },
    {
        "study_name": "databricks_serverless_job_888066060424343",
        "model_name": "regime_dirichlet_k35",
        "model_family": "dirichlet_empirical_bayes_baseline",
        "feature_groups": "canonical_471_gold_features",
        "hyperparams": {"smoothing_k": 35.0, "prior": "train_machine_type", "eval_queries": 768},
        "seed": 42,
        "fold_scheme": "public_train_to_validation_split",
        "evaluation_provenance": "dev_exposed_public_validation_sampled_outcome",
        "split": "public_validation",
        "primary_metric_name": "sampled_brier",
        "primary_metric_value": 0.550469,
        "mean_brier": 0.550469,
        "official_points": None,
        "log_loss": 1.158805,
        "ece_calibration": 0.025219,
        "brier_stable": 0.543083,
        "brier_short_history": 0.607855,
        "brier_drift": 0.491477,
        "brier_shared_change": 0.559460,
        "class_brier_0": 0.242410,
        "class_brier_1": 0.168490,
        "class_brier_2": 0.089190,
        "class_brier_5": 0.038140,
        "class_brier_20": 0.012239,
        "mean_pred_p20": 0.011910,
        "mean_target_p20": 0.011719,
        "corr_p20": 0.113800,
        "validation_target_exposure": False,
        "historical_signal_policy": "strict_tick_lt_cutoff_gold_features",
        "wall_seconds": 30.892,
        "source_artifact": "workspace.house_edge.gold_model_evaluations#run=8ae86a39ba9448e29c67d5c8a8398be5",
    },
    {
        "study_name": "databricks_serverless_job_888066060424343",
        "model_name": "uncalibrated_empirical_k1",
        "model_family": "uncalibrated_empirical_frequency",
        "feature_groups": "canonical_471_gold_features",
        "hyperparams": {"smoothing_k": 1.0, "prior": "train_machine_type", "eval_queries": 768},
        "seed": 42,
        "fold_scheme": "public_train_to_validation_split",
        "evaluation_provenance": "dev_exposed_public_validation_sampled_outcome",
        "split": "public_validation",
        "primary_metric_name": "sampled_brier",
        "primary_metric_value": 0.556865,
        "mean_brier": 0.556865,
        "official_points": None,
        "log_loss": 1.186259,
        "ece_calibration": 0.029445,
        "brier_stable": 0.553599,
        "brier_short_history": 0.609493,
        "brier_drift": 0.499838,
        "brier_shared_change": 0.564532,
        "class_brier_0": 0.245120,
        "class_brier_1": 0.170310,
        "class_brier_2": 0.090120,
        "class_brier_5": 0.038650,
        "class_brier_20": 0.012665,
        "mean_pred_p20": 0.012410,
        "mean_target_p20": 0.011719,
        "corr_p20": 0.098500,
        "validation_target_exposure": False,
        "historical_signal_policy": "strict_tick_lt_cutoff_gold_features",
        "wall_seconds": 30.892,
        "source_artifact": "workspace.house_edge.gold_model_evaluations#run=21c2911be6ff4e38a21a0174c40b0910",
    },
]


@dataclass(frozen=True)
class BenchmarkTrialRecord:
    """Normalized governed model benchmark trial record."""

    trial_id: str
    study_name: str
    model_name: str
    model_family: str
    feature_groups: str
    hyperparams_json: str
    seed: int
    fold_scheme: str
    evaluation_provenance: str
    split: str
    primary_metric_name: str
    primary_metric_value: float
    mean_brier: float
    official_points: Optional[float]
    log_loss: Optional[float]
    ece_calibration: Optional[float]
    brier_stable: Optional[float]
    brier_short_history: Optional[float]
    brier_drift: Optional[float]
    brier_shared_change: Optional[float]
    class_brier_0: Optional[float]
    class_brier_1: Optional[float]
    class_brier_2: Optional[float]
    class_brier_5: Optional[float]
    class_brier_20: Optional[float]
    mean_pred_p20: Optional[float]
    mean_target_p20: Optional[float]
    corr_p20: Optional[float]
    validation_target_exposure: bool
    historical_signal_policy: str
    wall_seconds: float
    source_artifact: str
    config_sha256: str


@dataclass(frozen=True)
class PairedComparisonRecord:
    """Normalized paired bootstrap hypothesis comparison record."""

    comparison_id: str
    study_name: str
    candidate_model: str
    reference_model: str
    evaluation_provenance: str
    metric_type: str
    mean_delta: float
    ci95_low: float
    ci95_high: float
    episodes: int
    bootstrap_samples: int
    supported_improvement: bool
    direction: str
    source_artifact: str


@dataclass(frozen=True)
class EpisodeDiagnosticRecord:
    """Normalized episode-level loss diagnostic record."""

    study_name: str
    model_name: str
    evaluation_provenance: str
    split: str
    episode_id: str
    condition: str
    episode_loss: float
    source_artifact: str


def resolve_research_dir(explicit_dir: Optional[str] = None) -> str:
    """Resolves `Jaeger_Main/House_Edge/research` directory without mutating it."""
    if explicit_dir and os.path.isdir(explicit_dir):
        return os.path.abspath(explicit_dir)
    repo_root = os.path.abspath(os.path.join(_SRC_DIR, "..", "..", "..", ".."))
    cand = os.path.join(repo_root, "Jaeger_Main", "House_Edge", "research")
    if os.path.isdir(cand):
        return cand
    alt = os.path.abspath(os.path.join(_SRC_DIR, "..", "..", "research"))
    if os.path.isdir(alt):
        return alt
    raise FileNotFoundError(f"Could not locate House Edge research directory from {_SRC_DIR}")


def _compute_config_sha256(
    study_name: str,
    model_name: str,
    model_family: str,
    feature_groups: str,
    hyperparams_json: str,
    seed: int,
    evaluation_provenance: str,
) -> str:
    payload = json.dumps(
        {
            "study_name": study_name,
            "model_name": model_name,
            "model_family": model_family,
            "feature_groups": feature_groups,
            "hyperparams_json": hyperparams_json,
            "seed": int(seed),
            "evaluation_provenance": evaluation_provenance,
        },
        sort_keys=True,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _safe_float(val: Any) -> Optional[float]:
    if val is None:
        return None
    try:
        f = float(val)
        return None if math.isnan(f) else f
    except (TypeError, ValueError):
        return None


def _build_trial_record(
    *,
    study_name: str,
    model_name: str,
    model_family: str,
    feature_groups: str,
    hyperparams: Dict[str, Any],
    seed: int,
    fold_scheme: str,
    evaluation_provenance: str,
    split: str,
    primary_metric_name: str,
    primary_metric_value: float,
    mean_brier: float,
    official_points: Optional[float],
    log_loss: Optional[float],
    ece_calibration: Optional[float],
    condition_losses: Optional[Dict[str, Any]],
    class_brier: Optional[Dict[str, Any]],
    rare_20: Optional[Dict[str, Any]],
    validation_target_exposure: bool,
    historical_signal_policy: str,
    wall_seconds: float,
    source_artifact: str,
) -> BenchmarkTrialRecord:
    if evaluation_provenance not in VALID_PROVENANCE_TIERS:
        raise ValueError(
            f"Unsupported evaluation_provenance '{evaluation_provenance}'. "
            f"Expected one of {VALID_PROVENANCE_TIERS}"
        )
    hyperparams_json = json.dumps(hyperparams or {}, sort_keys=True)
    config_sha = _compute_config_sha256(
        study_name=study_name,
        model_name=model_name,
        model_family=model_family,
        feature_groups=feature_groups,
        hyperparams_json=hyperparams_json,
        seed=seed,
        evaluation_provenance=evaluation_provenance,
    )
    cond = condition_losses or {}
    cb = class_brier or {}
    r20 = rare_20 or {}
    return BenchmarkTrialRecord(
        trial_id=config_sha[:16],
        study_name=study_name,
        model_name=model_name,
        model_family=model_family,
        feature_groups=feature_groups,
        hyperparams_json=hyperparams_json,
        seed=int(seed),
        fold_scheme=fold_scheme,
        evaluation_provenance=evaluation_provenance,
        split=split,
        primary_metric_name=primary_metric_name,
        primary_metric_value=float(primary_metric_value),
        mean_brier=float(mean_brier),
        official_points=_safe_float(official_points),
        log_loss=_safe_float(log_loss),
        ece_calibration=_safe_float(ece_calibration),
        brier_stable=_safe_float(cond.get("stable")),
        brier_short_history=_safe_float(cond.get("short_history")),
        brier_drift=_safe_float(cond.get("drift")),
        brier_shared_change=_safe_float(cond.get("shared_change")),
        class_brier_0=_safe_float(cb.get("0")),
        class_brier_1=_safe_float(cb.get("1")),
        class_brier_2=_safe_float(cb.get("2")),
        class_brier_5=_safe_float(cb.get("5")),
        class_brier_20=_safe_float(cb.get("20")),
        mean_pred_p20=_safe_float(r20.get("mean_pred_p20")),
        mean_target_p20=_safe_float(r20.get("mean_target_p20")),
        corr_p20=_safe_float(r20.get("corr_p20")),
        validation_target_exposure=bool(validation_target_exposure),
        historical_signal_policy=str(historical_signal_policy),
        wall_seconds=float(wall_seconds or 0.0),
        source_artifact=source_artifact,
        config_sha256=config_sha,
    )


def _mean_from_ratios(ratios: Optional[Dict[str, Any]]) -> float:
    if not isinstance(ratios, dict) or not ratios:
        return 0.0
    vals = [float(v) for v in ratios.values() if v is not None]
    return float(sum(vals) / len(vals)) if vals else 0.0


def _ingest_registry_style_artifact(
    data: Dict[str, Any],
    study_name: str,
    rel_path: str,
    default_family: str,
) -> Tuple[List[BenchmarkTrialRecord], List[PairedComparisonRecord], List[EpisodeDiagnosticRecord]]:
    trials: List[BenchmarkTrialRecord] = []
    comparisons: List[PairedComparisonRecord] = []
    episodes_out: List[EpisodeDiagnosticRecord] = []

    # 1. `trials` dictionary format (`stat_ablation_he17_registry_results.json`, `stat_he09_registry_results.json`,
    #    `stat_temporal_registry_results.json`, `audits/qa_causal_stacker_registry.json`)
    if isinstance(data.get("trials"), dict):
        provenance = "sampled_outcome_group_cv"
        for model_name, t_obj in data["trials"].items():
            if not isinstance(t_obj, dict):
                continue
            flags = t_obj.get("flags") or {}
            # Legacy `jaeger` / `champion` uses in-sample stacker target exposure on train CV folds
            default_exposed = model_name in ("jaeger", "champion")
            val_exp = bool(
                t_obj.get(
                    "validation_target_exposure",
                    flags.get("validation_target_exposure", default_exposed),
                )
            )
            hist_pol = str(
                t_obj.get(
                    "historical_signal_policy",
                    flags.get("historical_signal_policy", "strict_tick_lt_cutoff"),
                )
            )
            mean_brier = float(t_obj.get("mean_brier", 0.0))
            wall_s = float(t_obj.get("wall_seconds", 0.0))
            trials.append(
                _build_trial_record(
                    study_name=study_name,
                    model_name=str(model_name),
                    model_family=default_family,
                    feature_groups=f"{study_name}:{model_name}",
                    hyperparams={"study": study_name, "trial_name": model_name},
                    seed=0,
                    fold_scheme="grouped_episode_cv_4fold",
                    evaluation_provenance=provenance,
                    split="train_oof_cv",
                    primary_metric_name="sampled_brier",
                    primary_metric_value=mean_brier,
                    mean_brier=mean_brier,
                    official_points=None,
                    log_loss=_safe_float(t_obj.get("log_loss")),
                    ece_calibration=_safe_float(t_obj.get("ece")),
                    condition_losses=t_obj.get("by_condition"),
                    class_brier=_class_brier_from_seq_or_dict(t_obj.get("class_brier")),
                    rare_20=t_obj.get("calibration_20x") or t_obj.get("rare_20"),
                    validation_target_exposure=val_exp,
                    historical_signal_policy=hist_pol,
                    wall_seconds=wall_s,
                    source_artifact=rel_path,
                )
            )
            for key, val in t_obj.items():
                if key.startswith("vs_") and isinstance(val, dict) and "ci95" in val:
                    ref_name = key[len("vs_") :]
                    ci = val.get("ci95", [0.0, 0.0])
                    comp_id = hashlib.sha256(
                        f"{study_name}:{model_name}:{ref_name}:{provenance}".encode("utf-8")
                    ).hexdigest()[:16]
                    comparisons.append(
                        PairedComparisonRecord(
                            comparison_id=comp_id,
                            study_name=study_name,
                            candidate_model=str(model_name),
                            reference_model=ref_name,
                            evaluation_provenance=provenance,
                            metric_type="delta_brier",
                            mean_delta=float(val.get("mean_delta_brier", 0.0)),
                            ci95_low=float(ci[0]),
                            ci95_high=float(ci[1]),
                            episodes=int(val.get("episodes", 96)),
                            bootstrap_samples=int(val.get("bootstrap", 4000)),
                            supported_improvement=bool(val.get("supported_improvement", float(ci[1]) < 0.0)),
                            direction="lower_is_better",
                            source_artifact=rel_path,
                        )
                    )
        return trials, comparisons, episodes_out

    # 2. `summary` + `raw` format (`stat_ablation_he17_results.json`)
    if isinstance(data.get("summary"), list):
        for item in data["summary"]:
            if not isinstance(item, dict):
                continue
            model_name = str(item.get("name", "unknown"))
            n_exp = int(item.get("n_experts", 73))
            wall_s = float(item.get("seconds_total", 0.0))
            val_exp = model_name != "train_size_regimes"

            # Official public validation record (A_points & A_ratios)
            if "A_points" in item:
                pts = float(item["A_points"])
                a_ratios = item.get("A_ratios") or {}
                approx_brier = _mean_from_ratios(a_ratios)
                trials.append(
                    _build_trial_record(
                        study_name=study_name,
                        model_name=model_name,
                        model_family=default_family,
                        feature_groups=f"n_experts={n_exp}:{model_name}",
                        hyperparams={"n_experts": n_exp, "ablation": model_name},
                        seed=0,
                        fold_scheme="public_train_to_validation_split",
                        evaluation_provenance="official_public_validation",
                        split="public_validation",
                        primary_metric_name="official_points",
                        primary_metric_value=pts,
                        mean_brier=approx_brier,
                        official_points=pts,
                        log_loss=None,
                        ece_calibration=None,
                        condition_losses=a_ratios,
                        class_brier=None,
                        rare_20=None,
                        validation_target_exposure=False,
                        historical_signal_policy="strict_tick_lt_cutoff",
                        wall_seconds=wall_s,
                        source_artifact=rel_path,
                    )
                )
                if isinstance(item.get("A_vs_champion"), dict):
                    ac = item["A_vs_champion"]
                    ci = ac.get("ci95", [0.0, 0.0])
                    comp_id = hashlib.sha256(
                        f"{study_name}:{model_name}:champion:official_public_validation".encode("utf-8")
                    ).hexdigest()[:16]
                    comparisons.append(
                        PairedComparisonRecord(
                            comparison_id=comp_id,
                            study_name=study_name,
                            candidate_model=model_name,
                            reference_model="champion",
                            evaluation_provenance="official_public_validation",
                            metric_type="delta_official_points",
                            mean_delta=float(ac.get("diff", 0.0)),
                            ci95_low=float(ci[0]),
                            ci95_high=float(ci[1]),
                            episodes=96,
                            bootstrap_samples=4000,
                            supported_improvement=bool(float(ci[0]) > 0.0),
                            direction="higher_is_better",
                            source_artifact=rel_path,
                        )
                    )

            # Sampled outcome group CV record (B_mean_brier)
            if "B_mean_brier" in item:
                b_brier = float(item["B_mean_brier"])
                trials.append(
                    _build_trial_record(
                        study_name=f"{study_name}_cv_pair",
                        model_name=model_name,
                        model_family=default_family,
                        feature_groups=f"n_experts={n_exp}:{model_name}",
                        hyperparams={"n_experts": n_exp, "ablation": model_name},
                        seed=0,
                        fold_scheme="grouped_episode_cv_4fold",
                        evaluation_provenance="sampled_outcome_group_cv",
                        split="train_oof_cv",
                        primary_metric_name="sampled_brier",
                        primary_metric_value=b_brier,
                        mean_brier=b_brier,
                        official_points=None,
                        log_loss=None,
                        ece_calibration=None,
                        condition_losses=None,
                        class_brier=None,
                        rare_20=None,
                        validation_target_exposure=val_exp,
                        historical_signal_policy="strict_tick_lt_cutoff",
                        wall_seconds=wall_s,
                        source_artifact=rel_path,
                    )
                )
                if isinstance(item.get("B_vs_champion"), dict):
                    bc = item["B_vs_champion"]
                    ci = bc.get("ci95", [0.0, 0.0])
                    comp_id = hashlib.sha256(
                        f"{study_name}:{model_name}:champion:sampled_outcome_group_cv".encode("utf-8")
                    ).hexdigest()[:16]
                    comparisons.append(
                        PairedComparisonRecord(
                            comparison_id=comp_id,
                            study_name=f"{study_name}_cv_pair",
                            candidate_model=model_name,
                            reference_model="champion",
                            evaluation_provenance="sampled_outcome_group_cv",
                            metric_type="delta_brier",
                            mean_delta=float(bc.get("diff", 0.0)),
                            ci95_low=float(ci[0]),
                            ci95_high=float(ci[1]),
                            episodes=96,
                            bootstrap_samples=4000,
                            supported_improvement=bool(float(ci[1]) < 0.0),
                            direction="lower_is_better",
                            source_artifact=rel_path,
                        )
                    )

        for raw_item in data.get("raw", []):
            if not isinstance(raw_item, dict):
                continue
            m_name = str(raw_item.get("name", "unknown"))
            for cond_ep, loss_val in (raw_item.get("A_episode") or {}).items():
                parts = str(cond_ep).split("|", 1)
                cond_str = parts[0] if len(parts) == 2 else "unknown"
                ep_str = parts[1] if len(parts) == 2 else str(cond_ep)
                episodes_out.append(
                    EpisodeDiagnosticRecord(
                        study_name=study_name,
                        model_name=m_name,
                        evaluation_provenance="official_public_validation",
                        split="public_validation",
                        episode_id=ep_str,
                        condition=cond_str,
                        episode_loss=float(loss_val),
                        source_artifact=rel_path,
                    )
                )
        return trials, comparisons, episodes_out

    # 3. `R_nested_oof` + `A_official_validation` format (`stat_temporal_blend_results.json`)
    if "R_nested_oof" in data or "A_official_validation" in data:
        oof = data.get("R_nested_oof") or {}
        grid = oof.get("grid_oof_brier") or {}
        for weight_str, b_val in grid.items():
            w_float = float(weight_str)
            m_name = f"blend_champion_w{weight_str}"
            trials.append(
                _build_trial_record(
                    study_name=study_name,
                    model_name=m_name,
                    model_family=default_family,
                    feature_groups="champion_plus_factorized_temporal_expert",
                    hyperparams={"weight_on_champion": w_float},
                    seed=0,
                    fold_scheme="nested_grouped_episode_cv_4fold",
                    evaluation_provenance="sampled_outcome_group_cv",
                    split="train_oof_cv",
                    primary_metric_name="sampled_brier",
                    primary_metric_value=float(b_val),
                    mean_brier=float(b_val),
                    official_points=None,
                    log_loss=None,
                    ece_calibration=None,
                    condition_losses=None,
                    class_brier=None,
                    rare_20=None,
                    validation_target_exposure=bool(w_float > 0.0),
                    historical_signal_policy="unsupported_copied_signal" if w_float > 0.0 else "strict_tick_lt_cutoff",
                    wall_seconds=0.0,
                    source_artifact=rel_path,
                )
            )
        a_off = data.get("A_official_validation") or {}
        for m_name, m_obj in a_off.items():
            if not isinstance(m_obj, dict) or "official_points" not in m_obj:
                continue
            pts = float(m_obj["official_points"])
            l_ratios = m_obj.get("loss_ratios") or {}
            trials.append(
                _build_trial_record(
                    study_name=study_name,
                    model_name=str(m_name),
                    model_family=default_family,
                    feature_groups="champion_plus_factorized_temporal_expert",
                    hyperparams={"model": m_name},
                    seed=0,
                    fold_scheme="public_train_to_validation_split",
                    evaluation_provenance="official_public_validation",
                    split="public_validation",
                    primary_metric_name="official_points",
                    primary_metric_value=pts,
                    mean_brier=_mean_from_ratios(l_ratios),
                    official_points=pts,
                    log_loss=None,
                    ece_calibration=None,
                    condition_losses=l_ratios,
                    class_brier=None,
                    rare_20=m_obj.get("calibration_20x"),
                    validation_target_exposure=False,
                    historical_signal_policy="strict_tick_lt_cutoff",
                    wall_seconds=float(m_obj.get("seconds", 0.0)),
                    source_artifact=rel_path,
                )
            )
        return trials, comparisons, episodes_out

    # 4. Top-level model dict with `official_points` (`stat_temporal_official.json`, `qa_causal_stacker_official.json`)
    for m_name, m_obj in data.items():
        if not isinstance(m_obj, dict) or "official_points" not in m_obj:
            continue
        pts = float(m_obj["official_points"])
        l_ratios = m_obj.get("loss_ratios") or {}
        trials.append(
            _build_trial_record(
                study_name=study_name,
                model_name=str(m_name),
                model_family=default_family,
                feature_groups=f"{study_name}:{m_name}",
                hyperparams={"K": m_obj.get("K"), "study": study_name},
                seed=0,
                fold_scheme="public_train_to_validation_split",
                evaluation_provenance="official_public_validation",
                split="public_validation",
                primary_metric_name="official_points",
                primary_metric_value=pts,
                mean_brier=_mean_from_ratios(l_ratios),
                official_points=pts,
                log_loss=None,
                ece_calibration=None,
                condition_losses=l_ratios,
                class_brier=None,
                rare_20=m_obj.get("calibration_20x"),
                validation_target_exposure=False,
                historical_signal_policy="strict_tick_lt_cutoff",
                wall_seconds=float(m_obj.get("seconds", 0.0)),
                source_artifact=rel_path,
            )
        )
        if isinstance(m_obj.get("vs_champion_points"), dict):
            vc = m_obj["vs_champion_points"]
            ci = vc.get("ci95", [0.0, 0.0])
            comp_id = hashlib.sha256(
                f"{study_name}:{m_name}:champion:official_public_validation".encode("utf-8")
            ).hexdigest()[:16]
            comparisons.append(
                PairedComparisonRecord(
                    comparison_id=comp_id,
                    study_name=study_name,
                    candidate_model=str(m_name),
                    reference_model="champion",
                    evaluation_provenance="official_public_validation",
                    metric_type="delta_official_points",
                    mean_delta=float(vc.get("diff", 0.0)),
                    ci95_low=float(ci[0]),
                    ci95_high=float(ci[1]),
                    episodes=96,
                    bootstrap_samples=4000,
                    supported_improvement=bool(float(ci[0]) > 0.0),
                    direction="higher_is_better",
                    source_artifact=rel_path,
                )
            )

    return trials, comparisons, episodes_out


def _class_brier_from_seq_or_dict(raw_cb: Any) -> Dict[str, Optional[float]]:
    if isinstance(raw_cb, dict):
        return {k: _safe_float(raw_cb.get(k)) for k in ("0", "1", "2", "5", "20")}
    if isinstance(raw_cb, (list, tuple)) and len(raw_cb) == 5:
        keys = ("0", "1", "2", "5", "20")
        return {k: _safe_float(v) for k, v in zip(keys, raw_cb)}
    return {}


def _ingest_special_research_artifact(
    data: Dict[str, Any],
    study_name: str,
    rel_path: str,
    default_family: str,
) -> Tuple[List[BenchmarkTrialRecord], List[PairedComparisonRecord], List[EpisodeDiagnosticRecord]]:
    """Ingests specialized research artifacts (`stat_ensemble_result.json`,
    `stat_structural_walkforward_results.json`, `configs/ml/screen_result.json`,
    `configs/ml/temporal_screen_result.json`).
    """
    trials: List[BenchmarkTrialRecord] = []
    comparisons: List[PairedComparisonRecord] = []
    episodes_out: List[EpisodeDiagnosticRecord] = []

    provenance = str(data.get("evaluation_source", "sampled_outcome_group_cv"))
    val_exp = bool(data.get("validation_target_exposure", False))

    # Case A: stat_ensemble_result.json (`models` dict + `versus_baseline` dict)
    if isinstance(data.get("models"), dict):
        for model_name, m_obj in data["models"].items():
            if not isinstance(m_obj, dict):
                continue
            mean_brier = float(m_obj.get("mean_brier", 0.0))
            trials.append(
                _build_trial_record(
                    study_name=study_name,
                    model_name=str(model_name),
                    model_family=default_family,
                    feature_groups="oof_candidate_probability_streams",
                    hyperparams={"study": study_name, "variant": model_name},
                    seed=0,
                    fold_scheme="grouped_episode_cv_4fold",
                    evaluation_provenance=provenance,
                    split="train_oof_cv",
                    primary_metric_name="sampled_brier",
                    primary_metric_value=mean_brier,
                    mean_brier=mean_brier,
                    official_points=_safe_float(m_obj.get("official_points")),
                    log_loss=_safe_float(m_obj.get("log_loss")),
                    ece_calibration=_safe_float(m_obj.get("ece")),
                    condition_losses=m_obj.get("by_condition"),
                    class_brier=_class_brier_from_seq_or_dict(m_obj.get("class_brier")),
                    rare_20=None,
                    validation_target_exposure=val_exp,
                    historical_signal_policy="strict_tick_lt_cutoff",
                    wall_seconds=float(m_obj.get("predict_seconds", 0.0)),
                    source_artifact=rel_path,
                )
            )
            for ep_id, loss_val in (m_obj.get("per_episode") or {}).items():
                episodes_out.append(
                    EpisodeDiagnosticRecord(
                        study_name=study_name,
                        model_name=str(model_name),
                        evaluation_provenance=provenance,
                        split="train_oof_cv",
                        episode_id=str(ep_id),
                        condition="aggregate_episode",
                        episode_loss=float(loss_val),
                        source_artifact=rel_path,
                    )
                )
        for cand, c_obj in (data.get("versus_baseline") or {}).items():
            if not isinstance(c_obj, dict):
                continue
            ci = c_obj.get("ci95", [0.0, 0.0])
            comp_id = hashlib.sha256(
                f"{study_name}:{cand}:no_peer:{provenance}".encode("utf-8")
            ).hexdigest()[:16]
            comparisons.append(
                PairedComparisonRecord(
                    comparison_id=comp_id,
                    study_name=study_name,
                    candidate_model=str(cand),
                    reference_model="no_peer",
                    evaluation_provenance=provenance,
                    metric_type="delta_brier",
                    mean_delta=float(c_obj.get("mean_delta_brier", 0.0)),
                    ci95_low=float(ci[0]),
                    ci95_high=float(ci[1]),
                    episodes=int(c_obj.get("episodes", 96)),
                    bootstrap_samples=int(c_obj.get("bootstrap", 2000)),
                    supported_improvement=bool(c_obj.get("supported_improvement", False)),
                    direction="lower_is_better",
                    source_artifact=rel_path,
                )
            )

    # Case B: configs/ml/temporal_screen_result.json (`variants` dict + `versus_no_peer` dict)
    elif isinstance(data.get("variants"), dict):
        for var_name, v_obj in data["variants"].items():
            if not isinstance(v_obj, dict):
                continue
            mean_brier = float(v_obj.get("mean_brier", 0.0))
            trials.append(
                _build_trial_record(
                    study_name=study_name,
                    model_name=str(var_name),
                    model_family=default_family,
                    feature_groups=f"temporal_variant:{var_name}",
                    hyperparams={"study": study_name, "variant": var_name},
                    seed=0,
                    fold_scheme="grouped_episode_holdout_fold0",
                    evaluation_provenance=provenance,
                    split="train_oof_cv",
                    primary_metric_name="sampled_brier",
                    primary_metric_value=mean_brier,
                    mean_brier=mean_brier,
                    official_points=_safe_float(v_obj.get("official_points")),
                    log_loss=_safe_float(v_obj.get("log_loss")),
                    ece_calibration=_safe_float(v_obj.get("ece")),
                    condition_losses=v_obj.get("by_condition"),
                    class_brier=_class_brier_from_seq_or_dict(v_obj.get("class_brier")),
                    rare_20=None,
                    validation_target_exposure=val_exp,
                    historical_signal_policy="strict_tick_lt_cutoff",
                    wall_seconds=float(v_obj.get("predict_seconds", 0.0)),
                    source_artifact=rel_path,
                )
            )
            for ep_id, loss_val in (v_obj.get("per_episode") or {}).items():
                episodes_out.append(
                    EpisodeDiagnosticRecord(
                        study_name=study_name,
                        model_name=str(var_name),
                        evaluation_provenance=provenance,
                        split="train_oof_cv",
                        episode_id=str(ep_id),
                        condition="aggregate_episode",
                        episode_loss=float(loss_val),
                        source_artifact=rel_path,
                    )
                )
        for cand, c_obj in (data.get("versus_no_peer") or {}).items():
            if not isinstance(c_obj, dict):
                continue
            ci = c_obj.get("ci95", [0.0, 0.0])
            comp_id = hashlib.sha256(
                f"{study_name}:{cand}:no_peer:{provenance}".encode("utf-8")
            ).hexdigest()[:16]
            comparisons.append(
                PairedComparisonRecord(
                    comparison_id=comp_id,
                    study_name=study_name,
                    candidate_model=str(cand),
                    reference_model="no_peer",
                    evaluation_provenance=provenance,
                    metric_type="delta_brier",
                    mean_delta=float(c_obj.get("mean_delta_brier", 0.0)),
                    ci95_low=float(ci[0]),
                    ci95_high=float(ci[1]),
                    episodes=int(c_obj.get("episodes", 24)),
                    bootstrap_samples=int(c_obj.get("bootstrap", 2000)),
                    supported_improvement=bool(c_obj.get("supported_improvement", False)),
                    direction="lower_is_better",
                    source_artifact=rel_path,
                )
            )
        if isinstance(data.get("local_minus_global"), dict):
            c_obj = data["local_minus_global"]
            ci = c_obj.get("ci95", [0.0, 0.0])
            comp_id = hashlib.sha256(
                f"{study_name}:local:global:{provenance}".encode("utf-8")
            ).hexdigest()[:16]
            comparisons.append(
                PairedComparisonRecord(
                    comparison_id=comp_id,
                    study_name=study_name,
                    candidate_model="local",
                    reference_model="global",
                    evaluation_provenance=provenance,
                    metric_type="delta_brier",
                    mean_delta=float(c_obj.get("mean_delta_brier", 0.0)),
                    ci95_low=float(ci[0]),
                    ci95_high=float(ci[1]),
                    episodes=int(c_obj.get("episodes", 24)),
                    bootstrap_samples=int(c_obj.get("bootstrap", 2000)),
                    supported_improvement=bool(c_obj.get("supported_improvement", False)),
                    direction="lower_is_better",
                    source_artifact=rel_path,
                )
            )

    # Case C: configs/ml/screen_result.json (`families` dict)
    elif isinstance(data.get("families"), dict):
        for fam_name, fam_obj in data["families"].items():
            if not isinstance(fam_obj, dict):
                continue
            for sup_mode in ("historical_supervision", "query_supervision"):
                s_obj = fam_obj.get(sup_mode)
                if not isinstance(s_obj, dict):
                    continue
                model_name = f"{fam_name}__{sup_mode}"
                mean_brier = float(s_obj.get("mean_brier", 0.0))
                trials.append(
                    _build_trial_record(
                        study_name=study_name,
                        model_name=model_name,
                        model_family=str(fam_name),
                        feature_groups=f"ml_screen:{sup_mode}",
                        hyperparams={"family": fam_name, "supervision": sup_mode},
                        seed=0,
                        fold_scheme="grouped_episode_holdout_fold0",
                        evaluation_provenance=provenance,
                        split="train_oof_cv",
                        primary_metric_name="sampled_brier",
                        primary_metric_value=mean_brier,
                        mean_brier=mean_brier,
                        official_points=_safe_float(s_obj.get("official_points")),
                        log_loss=_safe_float(s_obj.get("log_loss")),
                        ece_calibration=_safe_float(s_obj.get("ece")),
                        condition_losses=s_obj.get("by_condition"),
                        class_brier=_class_brier_from_seq_or_dict(s_obj.get("class_brier")),
                        rare_20=None,
                        validation_target_exposure=val_exp,
                        historical_signal_policy="strict_tick_lt_cutoff",
                        wall_seconds=float(s_obj.get("fit_seconds", 0.0)),
                        source_artifact=rel_path,
                    )
                )
            if isinstance(fam_obj.get("query_minus_historical"), dict):
                c_obj = fam_obj["query_minus_historical"]
                ci = c_obj.get("ci95", [0.0, 0.0])
                comp_id = hashlib.sha256(
                    f"{study_name}:{fam_name}_query:{fam_name}_hist:{provenance}".encode("utf-8")
                ).hexdigest()[:16]
                comparisons.append(
                    PairedComparisonRecord(
                        comparison_id=comp_id,
                        study_name=study_name,
                        candidate_model=f"{fam_name}__query_supervision",
                        reference_model=f"{fam_name}__historical_supervision",
                        evaluation_provenance=provenance,
                        metric_type="delta_brier",
                        mean_delta=float(c_obj.get("mean_delta_brier", 0.0)),
                        ci95_low=float(ci[0]),
                        ci95_high=float(ci[1]),
                        episodes=int(c_obj.get("episodes", 24)),
                        bootstrap_samples=int(c_obj.get("bootstrap", 2000)),
                        supported_improvement=bool(c_obj.get("supported_improvement", False)),
                        direction="lower_is_better",
                        source_artifact=rel_path,
                    )
                )
        if isinstance(data.get("hist_boost_minus_logistic_query"), dict):
            c_obj = data["hist_boost_minus_logistic_query"]
            ci = c_obj.get("ci95", [0.0, 0.0])
            comp_id = hashlib.sha256(
                f"{study_name}:hist_boost_query:logistic_query:{provenance}".encode("utf-8")
            ).hexdigest()[:16]
            comparisons.append(
                PairedComparisonRecord(
                    comparison_id=comp_id,
                    study_name=study_name,
                    candidate_model="hist_boost__query_supervision",
                    reference_model="logistic__query_supervision",
                    evaluation_provenance=provenance,
                    metric_type="delta_brier",
                    mean_delta=float(c_obj.get("mean_delta_brier", 0.0)),
                    ci95_low=float(ci[0]),
                    ci95_high=float(ci[1]),
                    episodes=int(c_obj.get("episodes", 24)),
                    bootstrap_samples=int(c_obj.get("bootstrap", 2000)),
                    supported_improvement=bool(c_obj.get("supported_improvement", False)),
                    direction="lower_is_better",
                    source_artifact=rel_path,
                )
            )

    # Case D: reports/stat_structural_walkforward_results.json (`champion_mean` vs `stack_swm_mean`)
    elif "champion_mean" in data and "stack_swm_mean" in data:
        champ_brier = float(data["champion_mean"])
        swm_brier = float(data["stack_swm_mean"])
        for m_name, b_val in (("champion_walkforward_ref", champ_brier), ("stack_swm_walkforward", swm_brier)):
            trials.append(
                _build_trial_record(
                    study_name=study_name,
                    model_name=m_name,
                    model_family=default_family,
                    feature_groups="structural_walkforward_40j",
                    hyperparams={"n_scored": data.get("n_scored", 30720), "J": data.get("J", 40)},
                    seed=42,
                    fold_scheme="walkforward_30720_spins_96_episodes",
                    evaluation_provenance="sampled_outcome_group_cv",
                    split="train_oof_cv",
                    primary_metric_name="sampled_brier",
                    primary_metric_value=b_val,
                    mean_brier=b_val,
                    official_points=None,
                    log_loss=None,
                    ece_calibration=None,
                    condition_losses=None,
                    class_brier=None,
                    rare_20=None,
                    validation_target_exposure=False,
                    historical_signal_policy="strict_tick_lt_cutoff",
                    wall_seconds=0.0,
                    source_artifact=rel_path,
                )
            )
        all_ci = data.get("ALL", [0.0, 0.0, 0.0])
        comp_id = hashlib.sha256(
            f"{study_name}:stack_swm_walkforward:champion_walkforward_ref".encode("utf-8")
        ).hexdigest()[:16]
        comparisons.append(
            PairedComparisonRecord(
                comparison_id=comp_id,
                study_name=study_name,
                candidate_model="stack_swm_walkforward",
                reference_model="champion_walkforward_ref",
                evaluation_provenance="sampled_outcome_group_cv",
                metric_type="delta_brier",
                mean_delta=float(all_ci[0]),
                ci95_low=float(all_ci[1]),
                ci95_high=float(all_ci[2]),
                episodes=int(data.get("episodes", 96)),
                bootstrap_samples=2000,
                supported_improvement=bool(float(all_ci[2]) < 0.0),
                direction="lower_is_better",
                source_artifact=rel_path,
            )
        )

    return trials, comparisons, episodes_out


def ingest_repository_benchmarks(
    research_dir: Optional[str] = None,
    include_live_serverless: bool = True,
) -> Dict[str, pd.DataFrame]:
    """Reads all frozen House Edge research benchmark JSONs and returns normalized DataFrames.

    Never modifies any file in `research/`.
    Returns dictionary with keys:
      - `registry`: DataFrame of `BenchmarkTrialRecord`
      - `comparisons`: DataFrame of `PairedComparisonRecord`
      - `episodes`: DataFrame of `EpisodeDiagnosticRecord`
    """
    base_dir = resolve_research_dir(research_dir)
    all_trials: List[BenchmarkTrialRecord] = []
    all_comparisons: List[PairedComparisonRecord] = []
    all_episodes: List[EpisodeDiagnosticRecord] = []

    single_provenance_specs = [
        ("reports/stat_ablation_he17_registry_results.json", "he17_feature_ablation_cv", "jaeger_regime_mixture"),
        ("reports/stat_ablation_he17_results.json", "he17_feature_ablation_official", "jaeger_regime_mixture"),
        ("reports/stat_he09_registry_results.json", "he09_prior_hierarchy_ablation", "jaeger_regime_mixture"),
        ("reports/stat_temporal_registry_results.json", "he_temporal_expert_cv", "temporal_expert_mixture"),
        ("reports/stat_temporal_official.json", "he_temporal_expert_official", "temporal_expert_mixture"),
        ("reports/stat_temporal_blend_results.json", "he_temporal_blend_sweep", "legacy_temporal_blend"),
        ("audits/qa_causal_stacker_registry.json", "qa_causal_stacker_audit_cv", "causal_oof_stacker"),
        ("audits/qa_causal_stacker_official.json", "qa_causal_stacker_audit_official", "causal_oof_stacker"),
    ]

    for rel_path, study_name, default_family in single_provenance_specs:
        abs_path = os.path.join(base_dir, *rel_path.split("/"))
        if not os.path.isfile(abs_path):
            continue
        with open(abs_path, "r", encoding="utf-8") as f:
            payload = json.load(f)
        t_list, c_list, e_list = _ingest_registry_style_artifact(
            payload, study_name=study_name, rel_path=rel_path, default_family=default_family
        )
        all_trials.extend(t_list)
        all_comparisons.extend(c_list)
        all_episodes.extend(e_list)

    special_specs = [
        ("reports/stat_ensemble_result.json", "he_seed_ensemble_study", "seed_ensemble"),
        ("reports/stat_structural_walkforward_results.json", "he_structural_walkforward", "structural_sequential"),
        ("configs/ml/screen_result.json", "he_ml_family_screen", "ml_challenger_screen"),
        ("configs/ml/temporal_screen_result.json", "he_temporal_ml_screen", "temporal_ml_screen"),
    ]

    for rel_path, study_name, default_family in special_specs:
        abs_path = os.path.join(base_dir, *rel_path.split("/"))
        if not os.path.isfile(abs_path):
            continue
        with open(abs_path, "r", encoding="utf-8") as f:
            payload = json.load(f)
        t_list, c_list, e_list = _ingest_special_research_artifact(
            payload, study_name=study_name, rel_path=rel_path, default_family=default_family
        )
        all_trials.extend(t_list)
        all_comparisons.extend(c_list)
        all_episodes.extend(e_list)

    if include_live_serverless:
        for item in LIVE_SERVERLESS_EVALUATIONS:
            all_trials.append(
                _build_trial_record(
                    study_name=item["study_name"],
                    model_name=item["model_name"],
                    model_family=item["model_family"],
                    feature_groups=item["feature_groups"],
                    hyperparams=item["hyperparams"],
                    seed=item["seed"],
                    fold_scheme=item["fold_scheme"],
                    evaluation_provenance=item["evaluation_provenance"],
                    split=item["split"],
                    primary_metric_name=item["primary_metric_name"],
                    primary_metric_value=item["primary_metric_value"],
                    mean_brier=item["mean_brier"],
                    official_points=item["official_points"],
                    log_loss=item["log_loss"],
                    ece_calibration=item["ece_calibration"],
                    condition_losses={
                        "stable": item["brier_stable"],
                        "short_history": item["brier_short_history"],
                        "drift": item["brier_drift"],
                        "shared_change": item["brier_shared_change"],
                    },
                    class_brier={
                        "0": item["class_brier_0"],
                        "1": item["class_brier_1"],
                        "2": item["class_brier_2"],
                        "5": item["class_brier_5"],
                        "20": item["class_brier_20"],
                    },
                    rare_20={
                        "mean_pred_p20": item["mean_pred_p20"],
                        "mean_target_p20": item["mean_target_p20"],
                        "corr_p20": item["corr_p20"],
                    },
                    validation_target_exposure=item["validation_target_exposure"],
                    historical_signal_policy=item["historical_signal_policy"],
                    wall_seconds=item["wall_seconds"],
                    source_artifact=item["source_artifact"],
                )
            )

    df_registry = pd.DataFrame([dataclasses.asdict(t) for t in all_trials])
    df_comparisons = pd.DataFrame([dataclasses.asdict(c) for c in all_comparisons])
    df_episodes = pd.DataFrame([dataclasses.asdict(e) for e in all_episodes])
    return {
        "registry": df_registry,
        "comparisons": df_comparisons,
        "episodes": df_episodes,
    }


def rank_models_within_provenance(
    df_registry: pd.DataFrame,
    evaluation_provenance: str,
    exclude_target_exposed: bool = True,
) -> pd.DataFrame:
    """Ranks models strictly within a single homogeneous `evaluation_provenance` tier.

    Raises ValueError if `evaluation_provenance` is missing or if `df_registry` contains
    mixed provenance tiers without filtering.
    """
    if not evaluation_provenance or evaluation_provenance not in VALID_PROVENANCE_TIERS:
        raise ValueError(
            f"Must specify a single valid evaluation_provenance in {VALID_PROVENANCE_TIERS} "
            f"to rank models safely; got '{evaluation_provenance}'."
        )
    subset = df_registry[df_registry["evaluation_provenance"] == evaluation_provenance].copy()
    if exclude_target_exposed and "validation_target_exposure" in subset.columns:
        subset = subset[~subset["validation_target_exposure"].astype(bool)].copy()

    if len(subset) == 0:
        subset["rank_in_provenance"] = pd.Series(dtype=int)
        return subset

    # Check homogeneity
    distinct_prov = subset["evaluation_provenance"].unique()
    if len(distinct_prov) != 1:
        raise ValueError(f"Mixed evaluation_provenance detected: {distinct_prov}")

    subset = subset.sort_values(
        by=["mean_brier", "log_loss", "wall_seconds"],
        ascending=[True, True, True],
        na_position="last",
    ).reset_index(drop=True)
    subset["rank_in_provenance"] = np.arange(1, len(subset) + 1)
    return subset


def assert_single_provenance_comparison(df: pd.DataFrame) -> str:
    """Guardrail verifying that a comparison DataFrame does not mix evaluation provenance tiers."""
    if "evaluation_provenance" not in df.columns:
        raise ValueError("DataFrame missing required 'evaluation_provenance' column.")
    tiers = sorted(df["evaluation_provenance"].dropna().unique().tolist())
    if len(tiers) > 1:
        raise ValueError(
            f"Cross-provenance comparison is forbidden! Found multiple tiers: {tiers}. "
            "Partition or filter by `evaluation_provenance` before comparing metrics."
        )
    return tiers[0] if tiers else ""


def materialize_benchmark_tables(
    spark: Any,
    catalog: str = "workspace",
    schema: str = "house_edge",
    research_dir: Optional[str] = None,
    include_live_serverless: bool = True,
) -> Dict[str, int]:
    """Materializes governed benchmark tables into Delta / Spark catalog:
      - `gold_benchmark_registry`
      - `gold_benchmark_paired_comparisons`
      - `gold_benchmark_episode_diagnostics`
    """
    bundle = ingest_repository_benchmarks(
        research_dir=research_dir,
        include_live_serverless=include_live_serverless,
    )
    df_reg = bundle["registry"]
    df_comp = bundle["comparisons"]
    df_ep = bundle["episodes"]

    prefix = f"{catalog}.{schema}." if catalog and schema else ""
    reg_table = f"{prefix}gold_benchmark_registry"
    comp_table = f"{prefix}gold_benchmark_paired_comparisons"
    ep_table = f"{prefix}gold_benchmark_episode_diagnostics"

    sdf_reg = spark.createDataFrame(df_reg)
    sdf_reg.write.format("delta").mode("overwrite").saveAsTable(reg_table)

    sdf_comp = spark.createDataFrame(df_comp)
    sdf_comp.write.format("delta").mode("overwrite").saveAsTable(comp_table)

    sdf_ep = spark.createDataFrame(df_ep)
    sdf_ep.write.format("delta").mode("overwrite").saveAsTable(ep_table)

    return {
        "gold_benchmark_registry": len(df_reg),
        "gold_benchmark_paired_comparisons": len(df_comp),
        "gold_benchmark_episode_diagnostics": len(df_ep),
    }


def log_benchmark_study_to_mlflow(
    df_registry: pd.DataFrame,
    study_name: Optional[str] = None,
    experiment_name: str = "/Shared/jaegers_house_edge_experiments",
    force_mock: bool = False,
) -> List[str]:
    """Logs normalized benchmark trials to MLflow with full provenance and leakage tags."""
    mlflow = get_mlflow(force_mock=force_mock)
    mlflow.set_experiment(experiment_name)

    subset = df_registry if not study_name else df_registry[df_registry["study_name"] == study_name]
    logged_run_ids: List[str] = []

    for _, row in subset.iterrows():
        run_name = f"{row['study_name']}__{row['model_name']}__{row['evaluation_provenance']}"
        with mlflow.start_run(run_name=run_name) as run:
            mlflow.log_params(
                {
                    "study_name": str(row["study_name"]),
                    "model_name": str(row["model_name"]),
                    "model_family": str(row["model_family"]),
                    "feature_groups": str(row["feature_groups"])[:250],
                    "seed": int(row["seed"]),
                    "fold_scheme": str(row["fold_scheme"]),
                    "config_sha256": str(row["config_sha256"]),
                }
            )
            mlflow.set_tags(
                {
                    "evaluation_provenance": str(row["evaluation_provenance"]),
                    "split": str(row["split"]),
                    "validation_target_exposure": str(bool(row["validation_target_exposure"])),
                    "historical_signal_policy": str(row["historical_signal_policy"]),
                    "source_artifact": str(row["source_artifact"]),
                }
            )
            metrics_to_log: Dict[str, float] = {
                "mean_brier": float(row["mean_brier"]),
                "primary_metric_value": float(row["primary_metric_value"]),
                "wall_seconds": float(row["wall_seconds"]),
            }
            for col_name in (
                "official_points",
                "log_loss",
                "ece_calibration",
                "brier_stable",
                "brier_short_history",
                "brier_drift",
                "brier_shared_change",
                "class_brier_0",
                "class_brier_1",
                "class_brier_2",
                "class_brier_5",
                "class_brier_20",
                "mean_pred_p20",
                "mean_target_p20",
                "corr_p20",
            ):
                val = row.get(col_name)
                if val is not None and not pd.isna(val):
                    metrics_to_log[col_name] = float(val)
            mlflow.log_metrics(metrics_to_log)
            logged_run_ids.append(run.info.run_id)

    return logged_run_ids


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="JAEGERS House Edge Governed Benchmark Lane")
    parser.add_argument("--catalog", type=str, default="workspace")
    parser.add_argument("--schema", type=str, default="house_edge")
    parser.add_argument("--research-dir", type=str, default=None)
    parser.add_argument("--experiment-name", type=str, default="/Shared/jaegers_house_edge_experiments")
    parser.add_argument("--force-mock", action="store_true", default=False)
    return parser.parse_args(argv)


def main(argv: Optional[Sequence[str]] = None) -> Dict[str, int]:
    args = parse_args(argv)
    spark = get_spark_session(
        app_name="jaegers_house_edge_benchmark_lane",
        catalog=args.catalog,
        schema=args.schema,
        force_mock=args.force_mock,
    )
    counts = materialize_benchmark_tables(
        spark=spark,
        catalog=args.catalog,
        schema=args.schema,
        research_dir=args.research_dir,
    )
    logger.info("Materialized governed benchmark tables: %s", counts)
    return counts


if __name__ == "__main__":
    main()
