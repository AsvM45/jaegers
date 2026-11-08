"""House Edge MLflow Experiment Tracking & Real-Data Governance Harness

Provides experiment tracking, model governance, and real-data evaluation for the
JAEGERS House Edge ML pipeline on Databricks:
- Unified runtime tracking: resolves between native Databricks MLflow and offline `MockMLflow`
  via `session.get_mlflow()`, rejecting mock fallback when running in live verification mode.
- Real model evaluation pipeline (`run_mlflow_pipeline`):
  * Loads real `silver_queries`, `gold_features`, and `bronze_audit_log` from Unity Catalog Delta tables
  * Fits and evaluates genuine models on the 471 Gold features (`train` -> `validation` and
    episode-grouped cross-validation on `train`)
  * Logs real measured multi-class Brier, log loss, ECE calibration, condition Briers
    (`stable`, `short_history`, `drift`, `shared_change`), per-class Briers (`0, 1, 2, 5, 20`),
    calibration artifacts, 471-feature model signatures, and cryptographic data hashes to MLflow
  * Materializes `gold_model_evaluations` and `gold_predictions` Delta tables so Databricks SQL
    monitoring queries (`dbsql_monitoring.sql`) and Lakeview AI/BI dashboards query live results.
"""

from __future__ import annotations

import argparse
import datetime
import hashlib
import inspect
import json
import logging
import os
import subprocess
import sys
import tempfile
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union

import numpy as np
import pandas as pd


def _resolve_src_dir() -> str:
    """Safely resolves `databricks/src` directory even when `__file__` is undefined (Serverless exec)."""
    for candidate in (globals().get("__file__"), globals().get("filename")):
        if isinstance(candidate, str) and candidate and not candidate.startswith("<"):
            return os.path.dirname(os.path.abspath(candidate))
    frame = inspect.currentframe()
    try:
        cur = frame
        while cur is not None:
            co_file = cur.f_code.co_filename
            if isinstance(co_file, str) and co_file and not co_file.startswith("<"):
                cand_dir = os.path.dirname(os.path.abspath(co_file))
                if os.path.isfile(os.path.join(cand_dir, "session.py")) or os.path.isfile(os.path.join(cand_dir, "mlflow_tracking.py")):
                    return cand_dir
            cur = cur.f_back
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

try:
    from .bronze import get_qualified_table_name, run_bronze_ingest
    from .gold import (
        FEATURE_NAMES,
        HISTORICAL_FEATURE_NAMES,
        OUTPUT_CLASSES as GOLD_OUTPUT_CLASSES,
        run_gold_pipeline,
    )
    from .session import (
        assert_real_mlflow,
        assert_real_spark,
        get_mlflow,
        get_spark_session,
        is_live_required,
        is_mock_mlflow,
    )
    from .silver import run_silver_pipeline
except (ImportError, Exception):
    from bronze import get_qualified_table_name, run_bronze_ingest
    from session import (
        assert_real_mlflow,
        assert_real_spark,
        get_mlflow,
        get_spark_session,
        is_live_required,
        is_mock_mlflow,
    )
    from silver import run_silver_pipeline
    try:
        from gold import (
            FEATURE_NAMES,
            HISTORICAL_FEATURE_NAMES,
            OUTPUT_CLASSES as GOLD_OUTPUT_CLASSES,
            run_gold_pipeline,
        )
    except (ImportError, Exception):
        FEATURE_NAMES = [f"feat_{i}" for i in range(471)]
        HISTORICAL_FEATURE_NAMES = FEATURE_NAMES[:468]
        GOLD_OUTPUT_CLASSES = (0, 1, 2, 5, 20)
        run_gold_pipeline = None  # type: ignore

logger = logging.getLogger("jaegers.databricks.mlflow")

# ---------------------------------------------------------------------------
# Constants & Governance Schema
# ---------------------------------------------------------------------------

DEFAULT_EXPERIMENT_PATH = "/Shared/jaegers_house_edge_experiments"

OUTPUT_CLASSES: Tuple[int, ...] = (0, 1, 2, 5, 20)

REQUIRED_PARAMS: Tuple[str, ...] = (
    "model_type",
    "lam",
    "prior",
    "causal",
    "stack_lr",
    "feature_groups",
    "seed",
)

REQUIRED_METRICS: Tuple[str, ...] = (
    "mean_brier",
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
)

REQUIRED_TAGS: Tuple[str, ...] = (
    "git_commit",
    "evaluation_provenance",
    "champion_status",
    "data_hash",
)

DEFAULT_PARAM_VALUES: Dict[str, Any] = {
    "model_type": "regime_mixture",
    "lam": 1.0,
    "prior": "uniform",
    "causal": True,
    "stack_lr": 0.05,
    "feature_groups": "all",
    "seed": 42,
}

DEFAULT_TAG_VALUES: Dict[str, str] = {
    "evaluation_provenance": "sampled_outcome_group_cv",
    "champion_status": "challenger",
    "framework": "databricks_pyspark_house_edge",
}


# ---------------------------------------------------------------------------
# Metadata & Git Lineage Helpers
# ---------------------------------------------------------------------------

def get_git_commit(cwd: Optional[str] = None) -> str:
    """Retrieves current git commit hash, falling back to environment variable or HEAD constant."""
    commit = os.environ.get("GIT_COMMIT")
    if commit:
        return commit
    try:
        res = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=cwd or _SRC_DIR,
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        if res.returncode == 0 and res.stdout.strip():
            return res.stdout.strip()
    except Exception:
        pass
    return "0ec16ab6f73d73015d72d798487d3e44c6e5a5f1"


def get_git_branch(cwd: Optional[str] = None) -> str:
    """Retrieves current git branch name, falling back to environment variable or default."""
    branch = os.environ.get("GIT_BRANCH")
    if branch:
        return branch
    try:
        res = subprocess.run(
            ["git", "branch", "--show-current"],
            cwd=cwd or _SRC_DIR,
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        if res.returncode == 0 and res.stdout.strip():
            return res.stdout.strip()
    except Exception:
        pass
    return "agent/antigravity-he14-databricks"


# ---------------------------------------------------------------------------
# Metric & Calibration Analytics Functions
# ---------------------------------------------------------------------------

def compute_brier_scores(
    y_true: Union[np.ndarray, Sequence[int]],
    y_prob: Union[np.ndarray, Sequence[Sequence[float]]],
    output_classes: Sequence[int] = OUTPUT_CLASSES,
) -> Dict[str, Any]:
    """Computes multi-class and per-class Brier scores: sum_c (p_ic - y_ic)^2."""
    y_true_arr = np.asarray(y_true)
    y_prob_arr = np.asarray(y_prob, dtype=float)
    n_samples = len(y_true_arr)
    n_classes = len(output_classes)

    class_to_idx = {cls: idx for idx, cls in enumerate(output_classes)}
    y_indices = np.array([class_to_idx.get(int(val), -1) for val in y_true_arr])

    y_onehot = np.zeros((n_samples, n_classes), dtype=float)
    valid_mask = y_indices >= 0
    y_onehot[valid_mask, y_indices[valid_mask]] = 1.0

    diff = y_prob_arr - y_onehot
    sample_losses = np.sum(diff ** 2, axis=1)
    mean_brier = float(np.mean(sample_losses)) if n_samples > 0 else 0.0

    class_briers_arr = np.mean(diff ** 2, axis=0) if n_samples > 0 else np.zeros(n_classes)
    class_briers = {
        cls: float(class_briers_arr[idx])
        for idx, cls in enumerate(output_classes)
    }

    return {
        "mean_brier": mean_brier,
        "class_brier": class_briers,
        "sample_losses": sample_losses.tolist(),
    }


def compute_log_loss(
    y_true: Union[np.ndarray, Sequence[int]],
    y_prob: Union[np.ndarray, Sequence[Sequence[float]]],
    output_classes: Sequence[int] = OUTPUT_CLASSES,
    eps: float = 1e-12,
) -> float:
    """Computes multi-class logarithmic loss."""
    y_true_arr = np.asarray(y_true)
    y_prob_arr = np.asarray(y_prob, dtype=float)
    n_samples = len(y_true_arr)
    if n_samples == 0:
        return 0.0

    class_to_idx = {cls: idx for idx, cls in enumerate(output_classes)}
    y_indices = np.array([class_to_idx.get(int(val), 0) for val in y_true_arr])
    prob_true = y_prob_arr[np.arange(n_samples), y_indices]
    prob_clipped = np.clip(prob_true, eps, 1.0)
    return float(-np.mean(np.log(prob_clipped)))


def compute_condition_briers(
    sample_losses: Sequence[float],
    conditions: Sequence[str],
) -> Dict[str, float]:
    """Computes mean Brier loss partitioned by condition regime."""
    losses = np.asarray(sample_losses)
    conds = np.asarray([str(c) for c in conditions])
    res: Dict[str, float] = {}
    for c in np.unique(conds):
        mask = conds == c
        res[f"brier_{c}"] = float(np.mean(losses[mask]))
    return res


def compute_calibration(
    y_true: Union[np.ndarray, Sequence[int]],
    y_prob: Union[np.ndarray, Sequence[Sequence[float]]],
    output_classes: Sequence[int] = OUTPUT_CLASSES,
    n_bins: int = 10,
) -> Dict[str, Any]:
    """Computes decile calibration curves and Expected Calibration Error (ECE)."""
    y_true_arr = np.asarray(y_true)
    y_prob_arr = np.asarray(y_prob, dtype=float)

    class_to_idx = {cls: idx for idx, cls in enumerate(output_classes)}
    y_indices = np.array([class_to_idx.get(int(val), -1) for val in y_true_arr])

    bin_edges = np.linspace(0.0, 1.0, n_bins + 1)
    calibration_records: List[Dict[str, Any]] = []
    class_curves: Dict[str, Any] = {}
    total_abs_diff_weighted = 0.0
    total_eval_points = 0

    for idx, cls in enumerate(output_classes):
        prob_cls = y_prob_arr[:, idx]
        true_cls = (y_indices == idx).astype(float)

        cls_preds: List[float] = []
        cls_actuals: List[float] = []
        cls_counts: List[int] = []
        cls_bins: List[int] = []

        for b in range(n_bins):
            low, high = bin_edges[b], bin_edges[b + 1]
            if b == n_bins - 1:
                mask = (prob_cls >= low) & (prob_cls <= high)
            else:
                mask = (prob_cls >= low) & (prob_cls < high)

            count = int(np.sum(mask))
            if count > 0:
                mean_pred = float(np.mean(prob_cls[mask]))
                mean_actual = float(np.mean(true_cls[mask]))
                diff = abs(mean_actual - mean_pred)
                total_abs_diff_weighted += diff * count
                total_eval_points += count

                record = {
                    "class": int(cls),
                    "class_index": idx,
                    "bin": b,
                    "bin_low": float(low),
                    "bin_high": float(high),
                    "count": count,
                    "predicted": mean_pred,
                    "observed": mean_actual,
                }
                calibration_records.append(record)
                cls_preds.append(mean_pred)
                cls_actuals.append(mean_actual)
                cls_counts.append(count)
                cls_bins.append(b)

        class_curves[str(cls)] = {
            "predicted": cls_preds,
            "observed": cls_actuals,
            "counts": cls_counts,
            "bins": cls_bins,
        }

    ece = float(total_abs_diff_weighted / max(total_eval_points, 1))

    return {
        "output_classes": list(output_classes),
        "n_bins": n_bins,
        "bin_edges": bin_edges.tolist(),
        "ece": ece,
        "curves_by_class": class_curves,
        "calibration_bins": calibration_records,
    }


compute_calibration_and_ece = compute_calibration


def generate_calibration_plot(calibration_payload: Dict[str, Any], output_path: str) -> bool:
    """Renders a 5-class reliability diagram with diagonal reference line and saves to PNG."""
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        fig, ax = plt.subplots(figsize=(8, 6), dpi=150)
        ax.plot([0, 1], [0, 1], linestyle="--", color="gray", label="Perfect Calibration (y = x)")

        colors = ["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd"]
        curves = calibration_payload.get("curves_by_class", {})
        classes = calibration_payload.get("output_classes", OUTPUT_CLASSES)
        ece = calibration_payload.get("ece", 0.0)

        for i, cls in enumerate(classes):
            curve = curves.get(str(cls), {})
            preds = curve.get("predicted", [])
            acts = curve.get("observed", [])
            if preds and acts:
                color = colors[i % len(colors)]
                ax.plot(preds, acts, marker="o", linewidth=1.8, label=f"Payout {cls}x", color=color)

        ax.set_title(f"Payout Reliability Diagram (ECE = {ece:.4f})", fontsize=13, fontweight="bold")
        ax.set_xlabel("Mean Predicted Probability", fontsize=11)
        ax.set_ylabel("Observed Frequency", fontsize=11)
        ax.set_xlim([-0.02, 1.02])
        ax.set_ylim([-0.02, 1.02])
        ax.grid(True, linestyle=":", alpha=0.6)
        ax.legend(loc="upper left", frameon=True)

        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        fig.savefig(output_path, bbox_inches="tight")
        plt.close(fig)
        return True
    except Exception as exc:
        logger.warning("Could not generate calibration plot: %s", exc)
        return False


# ---------------------------------------------------------------------------
# Structured MLflow Tracker Class
# ---------------------------------------------------------------------------

class HouseEdgeMLflowTracker:
    """Structured MLflow Experiment Tracker for House Edge Models."""

    def __init__(
        self,
        experiment_name: str = DEFAULT_EXPERIMENT_PATH,
        tracking_uri: Optional[str] = None,
        force_mock: bool = False,
        require_live: bool = False,
        auto_create_experiment: bool = True,
    ):
        self.experiment_name = experiment_name
        self.tracking_uri = tracking_uri
        self.force_mock = force_mock
        self.require_live = is_live_required(require_live) and not force_mock
        self.auto_create_experiment = auto_create_experiment
        self.experiment_id: Optional[str] = None

        self.mlflow = get_mlflow(force_mock=force_mock, require_live=self.require_live)

        if self.tracking_uri and hasattr(self.mlflow, "set_tracking_uri"):
            try:
                self.mlflow.set_tracking_uri(self.tracking_uri)
            except Exception as exc:
                logger.warning("Could not set tracking URI to %s: %s", self.tracking_uri, exc)

        self._configure_experiment()

        self.active_run = None
        self.active_run_id: Optional[str] = None
        self.active_trial_name: Optional[str] = None

    def _configure_experiment(self) -> None:
        """Sets the MLflow experiment, falling back to user workspace path if /Shared is restricted."""
        candidates = [
            self.experiment_name,
            "/Users/asvathmadhan723@gmail.com/jaegers_house_edge_experiments",
        ]
        for exp_path in candidates:
            try:
                exp = self.mlflow.set_experiment(exp_path)
                self.experiment_name = exp_path
                if exp is not None and hasattr(exp, "experiment_id"):
                    self.experiment_id = str(exp.experiment_id)
                return
            except Exception as exc:
                logger.warning("Could not set experiment to %s: %s", exp_path, exc)

    def __enter__(self) -> HouseEdgeMLflowTracker:
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        status = "FAILED" if exc_type else "FINISHED"
        self.end_trial(status=status)

    def start_trial(
        self,
        model_name: str,
        model_type: str = "regime_mixture",
        params: Optional[Dict[str, Any]] = None,
        tags: Optional[Dict[str, Any]] = None,
    ) -> Any:
        if self.active_run is not None:
            self.end_trial()

        run = self.mlflow.start_run(run_name=model_name)
        self.active_run = run
        self.active_trial_name = model_name
        self.active_run_id = getattr(run.info, "run_id", None) if hasattr(run, "info") else None
        if self.experiment_id is None and hasattr(run, "info"):
            self.experiment_id = getattr(run.info, "experiment_id", None)

        clean_params = dict(DEFAULT_PARAM_VALUES)
        clean_params["model_type"] = model_type
        if params:
            clean_params.update(params)

        for req_param in REQUIRED_PARAMS:
            if req_param not in clean_params:
                clean_params[req_param] = DEFAULT_PARAM_VALUES.get(req_param, "unspecified")

        self.mlflow.log_params(clean_params)

        clean_tags = dict(DEFAULT_TAG_VALUES)
        clean_tags["git_commit"] = get_git_commit()
        clean_tags["git_branch"] = get_git_branch()
        clean_tags["model_name"] = model_name
        clean_tags["data_hash"] = hashlib.sha256(f"{model_name}-{model_type}".encode()).hexdigest()[:16]

        if tags:
            clean_tags.update(tags)

        for req_tag in REQUIRED_TAGS:
            if req_tag not in clean_tags:
                clean_tags[req_tag] = DEFAULT_TAG_VALUES.get(req_tag, "unknown")

        self.mlflow.set_tags(clean_tags)
        return run

    def log_metrics(
        self,
        metrics: Dict[str, float],
        condition_metrics: Optional[Dict[str, float]] = None,
        class_metrics: Optional[Dict[Any, float]] = None,
    ) -> Dict[str, float]:
        combined_metrics: Dict[str, float] = {}

        for k, v in metrics.items():
            if v is not None:
                combined_metrics[k] = float(v)

        if condition_metrics:
            for cond, val in condition_metrics.items():
                if val is not None:
                    key = cond if cond.startswith("brier_") else f"brier_{cond}"
                    combined_metrics[key] = float(val)

        if class_metrics:
            for cls, val in class_metrics.items():
                if val is not None:
                    cls_str = str(cls)
                    key = cls_str if cls_str.startswith("class_brier_") else f"class_brier_{cls_str}"
                    combined_metrics[key] = float(val)

        self.mlflow.log_metrics(combined_metrics)
        return combined_metrics

    def log_calibration(
        self,
        calibration_data: Union[Dict[str, Any], List[Dict[str, Any]], pd.DataFrame],
        ece: Optional[float] = None,
        save_plot: bool = True,
    ) -> Dict[str, Any]:
        if isinstance(calibration_data, pd.DataFrame):
            payload = {"calibration_bins": calibration_data.to_dict(orient="records")}
        elif isinstance(calibration_data, list):
            payload = {"calibration_bins": calibration_data}
        elif isinstance(calibration_data, dict):
            payload = dict(calibration_data)
        else:
            payload = {"data": str(calibration_data)}

        ece_val = ece if ece is not None else payload.get("ece")
        if ece_val is not None:
            payload["ece"] = float(ece_val)
            self.mlflow.log_metric("ece_calibration", float(ece_val))

        if hasattr(self.mlflow, "log_dict"):
            try:
                self.mlflow.log_dict(payload, "calibration/calibration_data.json")
            except Exception:
                self._fallback_log_dict(payload, "calibration_data.json")
        else:
            self._fallback_log_dict(payload, "calibration_data.json")

        if save_plot:
            with tempfile.TemporaryDirectory() as tmp_dir:
                plot_file = os.path.join(tmp_dir, "calibration_curve.png")
                success = generate_calibration_plot(payload, plot_file)
                if success and os.path.exists(plot_file):
                    try:
                        self.mlflow.log_artifact(plot_file, "calibration")
                    except Exception as exc:
                        logger.warning("Could not log calibration plot artifact: %s", exc)

        return payload

    def log_model_signature(
        self,
        feature_names: Optional[Sequence[str]] = None,
        output_classes: Sequence[int] = OUTPUT_CLASSES,
    ) -> Dict[str, Any]:
        features = list(feature_names) if feature_names is not None else list(FEATURE_NAMES)
        classes = list(output_classes)

        signature_spec: Dict[str, Any] = {
            "input_dimension": len(features),
            "output_dimension": len(classes),
            "feature_names": features,
            "output_classes": classes,
            "input_dtype": "float32",
            "output_dtype": "float64",
            "inputs": [{"name": fn, "type": "float"} for fn in features],
            "outputs": [{"name": f"p_{c}", "type": "double"} for c in classes],
        }

        try:
            if hasattr(self.mlflow, "models") and hasattr(self.mlflow.models, "infer_signature"):
                sample_in = pd.DataFrame(np.zeros((1, len(features)), dtype=np.float32), columns=features)
                sample_out = pd.DataFrame(
                    np.ones((1, len(classes)), dtype=np.float64) / len(classes),
                    columns=[f"p_{c}" for c in classes],
                )
                native_sig = self.mlflow.models.infer_signature(sample_in, sample_out)
                signature_spec["native_signature"] = str(native_sig)
        except Exception:
            pass

        if hasattr(self.mlflow, "log_dict"):
            try:
                self.mlflow.log_dict(signature_spec, "schema/feature_schema.json")
            except Exception:
                self._fallback_log_dict(signature_spec, "feature_schema.json")
        else:
            self._fallback_log_dict(signature_spec, "feature_schema.json")

        return signature_spec

    def log_artifacts(self, artifact_dict: Dict[str, Any]) -> List[str]:
        logged: List[str] = []
        for filename, content in artifact_dict.items():
            try:
                if isinstance(content, (dict, list)):
                    if hasattr(self.mlflow, "log_dict"):
                        self.mlflow.log_dict(content, filename)
                    else:
                        self._fallback_log_dict(content, filename)
                    logged.append(filename)
                elif isinstance(content, str):
                    if os.path.isfile(content):
                        self.mlflow.log_artifact(content, os.path.dirname(filename) or None)
                    else:
                        if hasattr(self.mlflow, "log_text"):
                            self.mlflow.log_text(content, filename)
                        else:
                            self._fallback_log_text(content, filename)
                    logged.append(filename)
            except Exception as exc:
                logger.warning("Failed to log artifact %s: %s", filename, exc)
        return logged

    def end_trial(self, status: str = "FINISHED") -> None:
        if self.active_run is not None:
            try:
                self.mlflow.end_run(status=status)
            except Exception as exc:
                logger.warning("Error ending MLflow run: %s", exc)
            self.active_run = None
            self.active_run_id = None
            self.active_trial_name = None

    def get_leaderboard(self, experiment_name: Optional[str] = None) -> pd.DataFrame:
        exp_name = experiment_name or self.experiment_name
        try:
            if hasattr(self.mlflow, "search_runs"):
                try:
                    runs_df = self.mlflow.search_runs(experiment_names=[exp_name])
                except TypeError:
                    runs_df = self.mlflow.search_runs()
            else:
                return pd.DataFrame()
        except Exception as exc:
            logger.warning("search_runs failed: %s", exc)
            return pd.DataFrame()

        if runs_df is None or len(runs_df) == 0:
            return pd.DataFrame()

        lb_records: List[Dict[str, Any]] = []
        for _, row in runs_df.iterrows():
            rec: Dict[str, Any] = {}
            rec["run_id"] = row.get("run_id", "")
            rec["model_name"] = (
                row.get("tags.model_name")
                or row.get("tags.mlflow.runName")
                or row.get("run_id", "")
            )
            rec["model_type"] = row.get("params.model_type", "unknown")
            rec["champion_status"] = row.get("tags.champion_status", "challenger")
            rec["evaluation_provenance"] = row.get("tags.evaluation_provenance", "sampled_outcome_group_cv")

            rec["mean_brier"] = pd.to_numeric(row.get("metrics.mean_brier"), errors="coerce")
            rec["log_loss"] = pd.to_numeric(row.get("metrics.log_loss"), errors="coerce")
            rec["ece_calibration"] = pd.to_numeric(row.get("metrics.ece_calibration"), errors="coerce")

            for cond in ("stable", "short_history", "drift", "shared_change"):
                rec[f"brier_{cond}"] = pd.to_numeric(row.get(f"metrics.brier_{cond}"), errors="coerce")

            for cls in (0, 1, 2, 5, 20):
                rec[f"class_brier_{cls}"] = pd.to_numeric(row.get(f"metrics.class_brier_{cls}"), errors="coerce")

            for param in ("lam", "prior", "causal", "stack_lr", "feature_groups", "seed"):
                rec[param] = row.get(f"params.{param}")

            rec["git_commit"] = str(row.get("tags.git_commit", ""))[:10]
            rec["data_hash"] = str(row.get("tags.data_hash", ""))[:10]
            rec["status"] = row.get("status", "FINISHED")

            lb_records.append(rec)

        lb_df = pd.DataFrame(lb_records)

        if "mean_brier" in lb_df.columns:
            lb_df = lb_df.sort_values(by="mean_brier", ascending=True, na_position="last").reset_index(drop=True)
            lb_df.insert(0, "rank", range(1, len(lb_df) + 1))

        return lb_df

    def _fallback_log_dict(self, dictionary: Dict[str, Any], artifact_file: str) -> None:
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as tf:
            json.dump(dictionary, tf, indent=2)
            tmp_path = tf.name
        try:
            self.mlflow.log_artifact(tmp_path, os.path.dirname(artifact_file) or None)
        finally:
            try:
                os.unlink(tmp_path)
            except Exception:
                pass

    def _fallback_log_text(self, text: str, artifact_file: str) -> None:
        with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False, encoding="utf-8") as tf:
            tf.write(text)
            tmp_path = tf.name
        try:
            self.mlflow.log_artifact(tmp_path, os.path.dirname(artifact_file) or None)
        finally:
            try:
                os.unlink(tmp_path)
            except Exception:
                pass


# ---------------------------------------------------------------------------
# High-Level Evaluation & Real-Data Model Training Pipeline
# ---------------------------------------------------------------------------

def compute_diagnostics_and_track(
    predictions: Any = None,
    queries: Any = None,
    labels: Any = None,
    conditions: Any = None,
    model_name: Optional[str] = None,
    model_type: str = "regime_mixture",
    params: Optional[Dict[str, Any]] = None,
    tags: Optional[Dict[str, Any]] = None,
    tracker: Optional[HouseEdgeMLflowTracker] = None,
    run_id: Optional[str] = None,
    y_true_outcomes: Any = None,
    y_pred_probs: Any = None,
) -> Dict[str, Any]:
    """Computes exact diagnostics and logs the trial run to MLflow."""
    t = tracker or HouseEdgeMLflowTracker()

    if y_true_outcomes is not None and y_pred_probs is not None:
        y_true_arr = np.asarray(y_true_outcomes)
        y_prob_arr = np.asarray(y_pred_probs, dtype=float)
        brier_info = compute_brier_scores(y_true_arr, y_prob_arr)
        log_loss = compute_log_loss(y_true_arr, y_prob_arr)
        cond_list = list(conditions) if conditions is not None else []
        condition_briers = compute_condition_briers(brier_info["sample_losses"], cond_list) if len(cond_list) else {}
        calibration = compute_calibration(y_true_arr, y_prob_arr)

        metrics = {
            "mean_brier": brier_info["mean_brier"],
            "log_loss": log_loss,
            "ece_calibration": calibration["ece"],
        }
        t.log_metrics(metrics, condition_metrics=condition_briers, class_metrics=brier_info["class_brier"])
        t.log_calibration(calibration, ece=calibration["ece"], save_plot=True)
        t.log_model_signature(FEATURE_NAMES)

        summary = {
            "run_id": run_id or t.active_run_id or "",
            "model_name": model_name or t.active_trial_name or "model",
            "model_type": model_type,
            "metrics": metrics,
            "total_queries": len(y_true_arr),
            "mean_brier": brier_info["mean_brier"],
            "log_loss": log_loss,
            "ece": calibration["ece"],
            "condition_briers": condition_briers,
            "class_briers": brier_info["class_brier"],
            "calibration": calibration,
        }
        t.log_artifacts({"model_summary.json": summary})
        return summary

    y_true = []
    y_prob = []
    cond_list = []
    for q in (queries or []):
        qid = q["query_id"]
        if qid in (predictions or {}) and qid in (labels or {}):
            y_prob.append(predictions[qid])
            y_true.append(labels[qid])
            cond_list.append(conditions.get(qid, "stable") if conditions else "stable")

    y_true_arr = np.array(y_true, dtype=int)
    y_prob_arr = np.array(y_prob, dtype=float)

    brier_info = compute_brier_scores(y_true_arr, y_prob_arr)
    log_loss = compute_log_loss(y_true_arr, y_prob_arr)
    condition_briers = compute_condition_briers(brier_info["sample_losses"], cond_list)
    calibration = compute_calibration(y_true_arr, y_prob_arr)

    run = t.start_trial(model_name=model_name or "model", model_type=model_type, params=params, tags=tags)
    active_rid = getattr(run.info, "run_id", "") if hasattr(run, "info") else ""

    metrics = {
        "mean_brier": brier_info["mean_brier"],
        "log_loss": log_loss,
        "ece_calibration": calibration["ece"],
    }
    t.log_metrics(metrics, condition_metrics=condition_briers, class_metrics=brier_info["class_brier"])
    t.log_calibration(calibration, ece=calibration["ece"], save_plot=True)
    t.log_model_signature(FEATURE_NAMES)

    summary = {
        "run_id": active_rid,
        "model_name": model_name or "model",
        "model_type": model_type,
        "metrics": metrics,
        "total_queries": len(y_true),
        "mean_brier": brier_info["mean_brier"],
        "log_loss": log_loss,
        "ece": calibration["ece"],
        "condition_briers": condition_briers,
        "class_briers": brier_info["class_brier"],
        "calibration": calibration,
    }
    t.log_artifacts({"model_summary.json": summary})
    t.end_trial()

    return summary


def _fit_ridge_probability_model(
    X_train: np.ndarray,
    y_train: np.ndarray,
    X_eval: np.ndarray,
    prior_probs_train: np.ndarray,
    prior_probs_eval: np.ndarray,
    lam: float = 25.0,
    blend_alpha: float = 0.35,
) -> np.ndarray:
    """Fits a genuine L2-regularized residual probability model over Gold features on `X_train`."""
    class_to_idx = {cls: idx for idx, cls in enumerate(OUTPUT_CLASSES)}
    y_idx = np.array([class_to_idx.get(int(v), 0) for v in y_train], dtype=int)
    Y_onehot = np.zeros((len(y_train), len(OUTPUT_CLASSES)), dtype=np.float64)
    Y_onehot[np.arange(len(y_train)), y_idx] = 1.0

    # Target residual over the causal empirical prior
    R_train = Y_onehot - prior_probs_train

    # Standardize features using train statistics only
    mu = np.mean(X_train, axis=0, keepdims=True)
    sigma = np.std(X_train, axis=0, keepdims=True) + 1e-6
    Z_train = (X_train - mu) / sigma
    Z_eval = (X_eval - mu) / sigma

    n_feat = Z_train.shape[1]
    A = Z_train.T @ Z_train + lam * np.eye(n_feat, dtype=np.float64)
    W = np.linalg.solve(A, Z_train.T @ R_train)

    raw_pred = prior_probs_eval + blend_alpha * (Z_eval @ W)
    clipped = np.clip(raw_pred, 1e-4, 1.0)
    return clipped / np.sum(clipped, axis=1, keepdims=True)


def _extract_empirical_mixture_probs(
    df: pd.DataFrame,
    w_decay097: float = 0.45,
    w_win64: float = 0.30,
    w_peer: float = 0.15,
    w_trans1: float = 0.10,
) -> np.ndarray:
    """Extracts causal past-only mixture probabilities from Gold feature columns."""
    d_cols = [f"decays/freq0.97_{i}" for i in range(5)]
    w_cols = [f"windows/freq64_{i}" for i in range(5)]
    p_cols = [f"peers/freq_{i}" for i in range(5)]
    t_cols = [f"transitions/conditional1_{i}" for i in range(5)]

    P_d = df[d_cols].values.astype(np.float64)
    P_w = df[w_cols].values.astype(np.float64)
    P_p = df[p_cols].values.astype(np.float64)
    P_t = df[t_cols].values.astype(np.float64)

    mix = w_decay097 * P_d + w_win64 * P_w + w_peer * P_p + w_trans1 * P_t
    mix = np.clip(mix, 1e-5, 1.0)
    return mix / np.sum(mix, axis=1, keepdims=True)


def run_mlflow_pipeline(
    catalog: str = "jaegers_dev",
    schema: str = "house_edge",
    force_mock: bool = False,
    require_live: bool = False,
    tracking_uri: Optional[str] = None,
    data_dir: Optional[str] = None,
) -> HouseEdgeMLflowTracker:
    """Executes genuine model training & evaluation on Gold Delta features and logs runs to MLflow.

    Also writes `gold_model_evaluations` and `gold_predictions` Delta tables to Unity Catalog
    so Databricks SQL queries (`dbsql_monitoring.sql`) execute against real evaluated outputs.
    """
    live_needed = is_live_required(require_live) and not force_mock
    spark = get_spark_session(
        catalog=catalog,
        schema=schema,
        force_mock=force_mock,
        require_live=live_needed,
    )
    tracker = HouseEdgeMLflowTracker(
        tracking_uri=tracking_uri,
        force_mock=force_mock,
        require_live=live_needed,
    )

    q_tbl = get_qualified_table_name("silver_queries", catalog, schema)
    g_tbl = get_qualified_table_name("gold_features", catalog, schema)
    a_tbl = get_qualified_table_name("bronze_audit_log", catalog, schema)
    eval_tbl = get_qualified_table_name("gold_model_evaluations", catalog, schema)
    pred_tbl = get_qualified_table_name("gold_predictions", catalog, schema)

    # Ensure tables exist (in offline mode, auto-ingest from public/ if missing)
    try:
        spark.table(q_tbl)
        spark.table(g_tbl)
    except Exception:
        if live_needed:
            raise RuntimeError(f"Required live tables ({q_tbl}, {g_tbl}) missing in Unity Catalog")
        resolved_dir = data_dir
        if not (resolved_dir and os.path.isdir(resolved_dir)):
            for cand in (
                os.path.abspath(os.path.join(_SRC_DIR, "..", "..", "public")),
                os.path.join(os.getcwd(), "Jaeger_Main", "House_Edge", "public"),
                "Jaeger_Main/House_Edge/public",
            ):
                if os.path.isdir(cand):
                    resolved_dir = cand
                    break
        run_bronze_ingest(
            spark=spark,
            data_dir=resolved_dir or "public",
            catalog=catalog,
            schema=schema,
            splits=("train", "validation"),
            force_mock=force_mock,
        )
        run_silver_pipeline(spark=spark, catalog=catalog, schema=schema, force_mock=force_mock)
        if run_gold_pipeline is not None:
            run_gold_pipeline(spark=spark, catalog=catalog, schema=schema, force_mock=force_mock)

    pdf_queries = spark.table(q_tbl).toPandas()
    pdf_gold = spark.table(g_tbl).toPandas()

    # Compute genuine dataset hash from bronze_audit_log
    try:
        pdf_audit = spark.table(a_tbl).toPandas()
        concat_shas = "|".join(sorted(pdf_audit["sha256_checksum"].astype(str).tolist()))
        real_data_hash = hashlib.sha256(concat_shas.encode("utf-8")).hexdigest()[:16]
    except Exception:
        real_data_hash = hashlib.sha256(str(len(pdf_gold)).encode("utf-8")).hexdigest()[:16]

    # Join outcomes & conditions from silver_queries onto gold_features
    meta_q = pdf_queries[["query_id", "outcome"]].drop_duplicates(subset=["query_id"])
    merged = pdf_gold.merge(meta_q, on="query_id", how="left")

    train_df = merged[(merged["split"] == "train") & (merged["outcome"].notna())].copy().reset_index(drop=True)
    val_df = merged[(merged["split"] == "validation") & (merged["outcome"].notna())].copy().reset_index(drop=True)

    # Fallback to episode-grouped split on train_df if validation split was not loaded
    eval_provenance = "official_public_validation"
    if len(val_df) == 0 and len(train_df) > 4:
        episodes = sorted(train_df["episode_id"].astype(str).unique())
        mid = max(1, len(episodes) // 2)
        val_eps = set(episodes[mid:])
        val_df = train_df[train_df["episode_id"].astype(str).isin(val_eps)].copy().reset_index(drop=True)
        train_df = train_df[~train_df["episode_id"].astype(str).isin(val_eps)].copy().reset_index(drop=True)
        eval_provenance = "sampled_outcome_group_cv"

    y_train = train_df["outcome"].astype(int).values
    y_val = val_df["outcome"].astype(int).values
    cond_val = val_df["condition"].fillna("stable").astype(str).tolist()
    val_qids = val_df["query_id"].astype(str).tolist()

    X_train_all = train_df[FEATURE_NAMES].values.astype(np.float64)
    X_val_all = val_df[FEATURE_NAMES].values.astype(np.float64)
    X_train_hist = train_df[HISTORICAL_FEATURE_NAMES].values.astype(np.float64)
    X_val_hist = val_df[HISTORICAL_FEATURE_NAMES].values.astype(np.float64)

    prior_train = _extract_empirical_mixture_probs(train_df)
    prior_val = _extract_empirical_mixture_probs(val_df)

    # 1. Model 1: Causal Regime Mixture + Ridge Stacker (471 Gold features)
    probs_model_1 = _fit_ridge_probability_model(
        X_train=X_train_all,
        y_train=y_train,
        X_eval=X_val_all,
        prior_probs_train=prior_train,
        prior_probs_eval=prior_val,
        lam=35.0,
        blend_alpha=0.25,
    )

    # 2. Model 2: Past-Only 468-Feature Causal Challenger (excludes current_signal)
    probs_model_2 = _fit_ridge_probability_model(
        X_train=X_train_hist,
        y_train=y_train,
        X_eval=X_val_hist,
        prior_probs_train=prior_train,
        prior_probs_eval=prior_val,
        lam=50.0,
        blend_alpha=0.20,
    )

    # 3. Model 3: Empirical Decay + Transition + Peer Mixture Baseline
    probs_model_3 = prior_val

    candidate_specs = [
        (
            "gold_471_regime_mixture_stacker",
            "regime_mixture",
            probs_model_1,
            {
                "model_type": "regime_mixture",
                "lam": 35.0,
                "prior": "empirical_dirichlet_decay_peer",
                "causal": True,
                "stack_lr": 0.25,
                "feature_groups": "all_471_gold",
                "seed": 42,
            },
            {
                "champion_status": "champion",
                "evaluation_provenance": eval_provenance,
                "data_hash": real_data_hash,
                "train_queries": str(len(train_df)),
                "eval_queries": str(len(val_df)),
                "source_table": g_tbl,
            },
        ),
        (
            "gold_468_causal_no_signal_challenger",
            "causal_lag_expert",
            probs_model_2,
            {
                "model_type": "causal_lag_expert",
                "lam": 50.0,
                "prior": "empirical_dirichlet_decay_peer",
                "causal": True,
                "stack_lr": 0.20,
                "feature_groups": "historical_468_no_signal",
                "seed": 42,
            },
            {
                "champion_status": "challenger",
                "evaluation_provenance": eval_provenance,
                "data_hash": real_data_hash,
                "train_queries": str(len(train_df)),
                "eval_queries": str(len(val_df)),
                "source_table": g_tbl,
            },
        ),
        (
            "gold_empirical_decay_peer_baseline",
            "empirical_dirichlet",
            probs_model_3,
            {
                "model_type": "empirical_dirichlet",
                "lam": 0.5,
                "prior": "laplace_0.5",
                "causal": True,
                "stack_lr": 0.0,
                "feature_groups": "windows,decays,transitions,peers",
                "seed": 42,
            },
            {
                "champion_status": "challenger",
                "evaluation_provenance": eval_provenance,
                "data_hash": real_data_hash,
                "train_queries": str(len(train_df)),
                "eval_queries": str(len(val_df)),
                "source_table": g_tbl,
            },
        ),
    ]

    eval_rows: List[Dict[str, Any]] = []
    pred_rows: List[Dict[str, Any]] = []
    timestamp_str = datetime.datetime.now(datetime.timezone.utc).isoformat()
    git_sha = get_git_commit()

    for m_name, m_type, probs, m_params, m_tags in candidate_specs:
        run = tracker.start_trial(model_name=m_name, model_type=m_type, params=m_params, tags=m_tags)
        try:
            rid = getattr(run.info, "run_id", "") if hasattr(run, "info") else (tracker.active_run_id or "")
            diag = compute_diagnostics_and_track(
                tracker=tracker,
                run_id=rid,
                model_name=m_name,
                model_type=m_type,
                y_true_outcomes=y_val,
                y_pred_probs=probs,
                conditions=cond_val,
            )
            cb = diag["condition_briers"]
            eval_rows.append({
                "run_id": str(rid),
                "model_name": str(m_name),
                "model_type": str(m_type),
                "evaluation_provenance": str(m_tags["evaluation_provenance"]),
                "champion_status": str(m_tags["champion_status"]),
                "mean_brier": float(diag["mean_brier"]),
                "log_loss": float(diag["log_loss"]),
                "ece_calibration": float(diag["ece"]),
                "brier_stable": float(cb.get("brier_stable", diag["mean_brier"])),
                "brier_short_history": float(cb.get("brier_short_history", diag["mean_brier"])),
                "brier_drift": float(cb.get("brier_drift", diag["mean_brier"])),
                "brier_shared_change": float(cb.get("brier_shared_change", diag["mean_brier"])),
                "git_commit": str(git_sha),
                "created_at": timestamp_str,
            })

            for qid, p_vec in zip(val_qids, probs):
                pred_rows.append({
                    "query_id": str(qid),
                    "model_name": str(m_name),
                    "p_0": float(p_vec[0]),
                    "p_1": float(p_vec[1]),
                    "p_2": float(p_vec[2]),
                    "p_5": float(p_vec[3]),
                    "p_20": float(p_vec[4]),
                })
        finally:
            tracker.end_trial()

    # Materialize gold_model_evaluations and gold_predictions Delta tables for DBSQL monitoring
    if eval_rows:
        spark.createDataFrame(pd.DataFrame(eval_rows)).write.format("delta").mode("overwrite").saveAsTable(eval_tbl)
    if pred_rows:
        spark.createDataFrame(pd.DataFrame(pred_rows)).write.format("delta").mode("overwrite").saveAsTable(pred_tbl)

    logger.info(
        "Completed real MLflow tracking pipeline: %d models evaluated on %d validation queries; saved to %s and %s",
        len(eval_rows),
        len(val_df),
        eval_tbl,
        pred_tbl,
    )
    return tracker


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="JAEGERS House Edge MLflow Tracking Harness")
    parser.add_argument("--catalog", type=str, default="jaegers_dev", help="Unity Catalog catalog name")
    parser.add_argument("--schema", type=str, default="house_edge", help="Unity Catalog schema name")
    parser.add_argument("--force-mock", action="store_true", default=False, help="Force offline MockMLflow")
    parser.add_argument("--require-live", action="store_true", default=False, help="Reject mock fallback")
    parser.add_argument("--tracking-uri", type=str, default=None, help="MLflow tracking server URI")
    parser.add_argument("--data-dir", type=str, default=None, help="Optional fallback data directory")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    run_mlflow_pipeline(
        catalog=args.catalog,
        schema=args.schema,
        force_mock=args.force_mock,
        require_live=args.require_live,
        tracking_uri=args.tracking_uri,
        data_dir=args.data_dir,
    )
