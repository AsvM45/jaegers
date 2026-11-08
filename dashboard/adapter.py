"""Production-grade read-only ExperimentStore for JAEGERS dashboard.

Supports SQLite (?mode=ro), JSON directories, static audit reports,
clean empty-directory handling, and fallback demonstration fixtures.
"""

from __future__ import annotations

import csv
import json
import logging
import sqlite3
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np

from .fixtures import DEMO_REGISTRY_PATH, METADATA_PATH
from .provenance import (
    calculate_official_points,
    validate_comparison_compatibility,
)
from .schema import (
    AttemptRecord,
    CalibrationBin,
    ComponentAblation,
    ConditionLosses,
    ExecutionLog,
    FeatureImportanceRecord,
    HypothesisRecord,
    PairedComparison,
    ProvenanceType,
    RarePayoutDiagnostic,
    TrialDetail,
    TrialRecord,
)

logger = logging.getLogger(__name__)


class ExperimentStore(ABC):
    """Abstract base class for experiment history stores."""

    @abstractmethod
    def list_trials(
        self,
        study: Optional[str] = None,
        provenance: Optional[ProvenanceType] = None,
        status: Optional[str] = None,
    ) -> List[TrialRecord]:
        """List summary records matching optional filters."""

    @abstractmethod
    def get_trial(self, trial_id: str) -> Optional[TrialDetail]:
        """Get complete trial details including out-of-fold data and artifacts."""

    @abstractmethod
    def get_champion(self) -> Optional[TrialRecord]:
        """Retrieve baseline champion record if present."""

    @abstractmethod
    def list_hypotheses(self) -> List[HypothesisRecord]:
        """List pre-registered hypotheses and their validation status."""

    @abstractmethod
    def list_ablations(self) -> List[ComponentAblation]:
        """List component ablation benchmarks."""

    @abstractmethod
    def get_calibration_bins(self, trial_id: Optional[str] = None) -> List[CalibrationBin]:
        """Get 5-class probability calibration bins."""

    @abstractmethod
    def get_rare_payout_diagnostic(self, trial_id: Optional[str] = None) -> Optional[RarePayoutDiagnostic]:
        """Get diagnostic metrics for the rare 20x jackpot class."""

    @abstractmethod
    def get_execution_logs(self) -> List[ExecutionLog]:
        """List execution telemetry and failure logs."""

    @property
    @abstractmethod
    def is_demo_mode(self) -> bool:
        """Flag indicating if data is synthetic demonstration fixture."""

    @abstractmethod
    def has_runs(self) -> bool:
        """Return True if store contains at least one trial record."""

    def get_paired_comparison(
        self, candidate_id: str, baseline_id: str, bootstrap: int = 2000, seed: int = 0
    ) -> Optional[PairedComparison]:
        """Compute paired statistical comparison between candidate and baseline."""
        c_detail = self.get_trial(candidate_id)
        b_detail = self.get_trial(baseline_id)
        if not c_detail or not b_detail:
            return None

        c_rec = c_detail.record
        b_rec = b_detail.record

        valid, _ = validate_comparison_compatibility(c_rec, b_rec)
        if not valid:
            return None

        # Case 1: Per-episode errors available (compute paired bootstrap)
        if c_rec.per_episode_errors and b_rec.per_episode_errors and b_rec.episode_conditions:
            from .stats import paired_episode_bootstrap

            try:
                boot_res = paired_episode_bootstrap(
                    candidate_errors=c_rec.per_episode_errors,
                    baseline_errors=b_rec.per_episode_errors,
                    episode_conditions=b_rec.episode_conditions,
                    n_resamples=bootstrap,
                    seed=seed,
                )
                return PairedComparison(
                    candidate_id=candidate_id,
                    baseline_id=baseline_id,
                    provenance=c_rec.provenance,
                    mean_delta=boot_res.mean_delta,
                    ci95_low=boot_res.ci95_low,
                    ci95_high=boot_res.ci95_high,
                    p_improvement=boot_res.p_improvement,
                    supported_improvement=boot_res.supported_improvement,
                    n_episodes=boot_res.n_episodes,
                    bootstrap_iterations=boot_res.n_resamples,
                    episode_deltas=boot_res.episode_deltas,
                    by_condition_delta=boot_res.by_condition_delta,
                )
            except ValueError:
                return None

        # Case 2: Aggregate official points delta
        if c_rec.official_points is not None and b_rec.official_points is not None:
            delta = c_rec.official_points - b_rec.official_points
            by_cond = {}
            if c_rec.condition_losses and b_rec.condition_losses:
                c_d = c_rec.condition_losses.as_dict()
                b_d = b_rec.condition_losses.as_dict()
                for k in c_d:
                    by_cond[k] = c_d[k] - b_d[k]

            return PairedComparison(
                candidate_id=candidate_id,
                baseline_id=baseline_id,
                provenance=c_rec.provenance,
                mean_delta=delta,
                ci95_low=delta,
                ci95_high=delta,
                p_improvement=1.0 if delta > 0 else 0.0,
                supported_improvement=bool(delta > 0),
                n_episodes=0,
                bootstrap_iterations=0,
                episode_deltas={},
                by_condition_delta=by_cond,
            )

        return None


from contextlib import contextmanager


@contextmanager
def _sqlite_connect_ro(path: Path):
    """Connect to SQLite database strictly in read-only URI mode and close on exit."""
    clean_path = path.resolve().as_posix()
    uri = f"file:{clean_path}?mode=ro"
    conn = sqlite3.connect(uri, uri=True, timeout=30.0)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


class SQLiteStore(ExperimentStore):
    """Production read-only SQLite trial registry store."""

    def __init__(self, db_path: Union[str, Path]):
        self.db_path = Path(db_path).resolve()
        self._cached_trials: Optional[Dict[str, TrialRecord]] = None
        self._cached_details: Dict[str, TrialDetail] = {}

    @property
    def is_demo_mode(self) -> bool:
        return False

    def has_runs(self) -> bool:
        if not self.db_path.exists():
            return False
        try:
            with _sqlite_connect_ro(self.db_path) as db:
                cur = db.cursor()
                cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='trials'")
                if not cur.fetchone():
                    return False
                cur.execute("SELECT COUNT(*) FROM trials")
                count = cur.fetchone()[0]
                return count > 0
        except (sqlite3.Error, OSError) as e:
            logger.warning("Error checking runs in SQLite %s: %s", self.db_path, e)
            return False

    def _load_trial_records(self) -> Dict[str, TrialRecord]:
        if self._cached_trials is not None:
            return self._cached_trials

        records: Dict[str, TrialRecord] = {}
        if not self.db_path.exists():
            self._cached_trials = records
            return records

        try:
            with _sqlite_connect_ro(self.db_path) as db:
                cur = db.cursor()
                cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='trials'")
                if not cur.fetchone():
                    self._cached_trials = records
                    return records

                query = (
                    "SELECT id, study, config, identity, status, attempt, artifact, "
                    "mean_brier, wall_seconds, error, created_at, finished_at FROM trials"
                )
                cur.execute(query)
                rows = cur.fetchall()

                for row in rows:
                    t_id = str(row["id"])
                    study = str(row["study"])
                    status = str(row["status"]).upper()
                    cfg_raw = row["config"]
                    config = json.loads(cfg_raw) if isinstance(cfg_raw, str) else dict(cfg_raw or {})
                    identity = str(row["identity"] or "jaeger")
                    attempt = int(row["attempt"] or 0)
                    artifact = str(row["artifact"] or "")
                    mean_brier = float(row["mean_brier"]) if row["mean_brier"] is not None else None
                    wall_sec = float(row["wall_seconds"] or 0.0)
                    error = row["error"]
                    created_at = str(row["created_at"] or "")
                    finished_at = row["finished_at"]

                    # Check attempt directory for result.json
                    cond_losses = None
                    per_ep = None
                    ep_conds = None
                    feat_imp = None
                    cal_bins = None
                    provenance = ProvenanceType.TRAIN_GROUP_CV
                    official_points = None

                    artifact_dir = self.db_path.parent / artifact if artifact else None
                    if artifact_dir and artifact_dir.exists():
                        res_file = artifact_dir / "result.json"
                        if res_file.exists():
                            try:
                                with open(res_file, "r", encoding="utf-8") as f:
                                    res_data = json.load(f)
                                by_c = res_data.get("by_condition")
                                if isinstance(by_c, dict) and len(by_c) >= 4:
                                    cond_losses = ConditionLosses.from_dict(by_c)
                                    if res_data.get("evaluation_source") == "public_validation":
                                        provenance = ProvenanceType.PUBLIC_VALIDATION
                                        official_points = calculate_official_points(cond_losses)
                                per_ep = res_data.get("per_episode")
                                ep_conds = res_data.get("episode_conditions")
                                feat_imp = res_data.get("importance")
                                cal_bins = res_data.get("calibration")
                                if res_data.get("mean_brier") is not None:
                                    mean_brier = float(res_data["mean_brier"])
                            except (json.JSONDecodeError, OSError):
                                pass

                    rec = TrialRecord(
                        trial_id=t_id,
                        study_name=study,
                        family=identity,
                        status=status,
                        provenance=provenance,
                        is_champion=bool("champion" in t_id or "champion" in study),
                        source_commit=str(config.get("git_sha", "")),
                        wall_seconds=wall_sec,
                        created_at=created_at,
                        finished_at=finished_at,
                        official_points=official_points,
                        mean_brier=mean_brier,
                        condition_losses=cond_losses,
                        per_episode_errors=per_ep,
                        episode_conditions=ep_conds,
                        hyperparameters=config,
                        feature_importance=feat_imp,
                        calibration_bins=cal_bins,
                        error_message=error,
                        is_synthetic=False,
                        attempt=attempt,
                        artifact_path=artifact,
                    )
                    records[t_id] = rec
        except (sqlite3.Error, OSError) as e:
            logger.warning("SQLite query failure in %s: %s", self.db_path, e)

        self._cached_trials = records
        return records

    def list_trials(
        self,
        study: Optional[str] = None,
        provenance: Optional[ProvenanceType] = None,
        status: Optional[str] = None,
    ) -> List[TrialRecord]:
        records = list(self._load_trial_records().values())
        if study:
            records = [r for r in records if r.study_name == study]
        if provenance:
            records = [r for r in records if r.provenance == provenance]
        if status:
            records = [r for r in records if r.status == status.upper()]
        return records

    def get_trial(self, trial_id: str) -> Optional[TrialDetail]:
        if trial_id in self._cached_details:
            return self._cached_details[trial_id]

        recs = self._load_trial_records()
        if trial_id not in recs:
            return None
        rec = recs[trial_id]

        oof_data = None
        per_query = None
        folds = None
        logs = None

        if rec.artifact_path:
            artifact_dir = self.db_path.parent / rec.artifact_path
            if artifact_dir.exists():
                oof_csv = artifact_dir / "oof.csv"
                if oof_csv.exists():
                    try:
                        with open(oof_csv, "r", encoding="utf-8") as f:
                            reader = csv.DictReader(f)
                            oof_data = list(reader)
                    except OSError:
                        pass

                res_json = artifact_dir / "result.json"
                if res_json.exists():
                    try:
                        with open(res_json, "r", encoding="utf-8") as f:
                            res_dict = json.load(f)
                            per_query = res_dict.get("per_query")
                            folds = res_dict.get("folds")
                    except (json.JSONDecodeError, OSError):
                        pass

        detail = TrialDetail(
            record=rec,
            oof_predictions=oof_data,
            per_query_metrics=per_query,
            folds=folds,
            raw_config=rec.hyperparameters,
            process_evidence=None,
            logs=logs,
        )
        self._cached_details[trial_id] = detail
        return detail

    def get_champion(self) -> Optional[TrialRecord]:
        for r in self.list_trials():
            if r.is_champion:
                return r
        return None

    def list_hypotheses(self) -> List[HypothesisRecord]:
        return []

    def list_ablations(self) -> List[ComponentAblation]:
        return []

    def get_calibration_bins(self, trial_id: Optional[str] = None) -> List[CalibrationBin]:
        t = self.get_trial(trial_id) if trial_id else (self.get_champion() or (self.list_trials()[0] if self.has_runs() else None))
        if t and t.record.calibration_bins:
            res = []
            for item in t.record.calibration_bins:
                b = item.get("bin", 0)
                res.append(
                    CalibrationBin(
                        payout_class=item.get("class", 0),
                        bin_index=b,
                        bin_range=(b / 10.0, (b + 1) / 10.0),
                        sample_count=item.get("count", 0),
                        mean_predicted=item.get("predicted", 0.0),
                        observed_frequency=item.get("observed", 0.0),
                    )
                )
            return res
        return []

    def get_rare_payout_diagnostic(self, trial_id: Optional[str] = None) -> Optional[RarePayoutDiagnostic]:
        return None

    def get_execution_logs(self) -> List[ExecutionLog]:
        logs = []
        try:
            with _sqlite_connect_ro(self.db_path) as db:
                cur = db.cursor()
                cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='attempts'")
                if cur.fetchone():
                    cur.execute("SELECT trial_id, attempt, artifact, status, error FROM attempts")
                    for row in cur.fetchall():
                        logs.append(
                            ExecutionLog(
                                trial_id=str(row["trial_id"]),
                                attempt=int(row["attempt"]),
                                status=str(row["status"]).upper(),
                                wall_seconds=0.0,
                                error_message=row["error"],
                            )
                        )
        except (sqlite3.Error, OSError):
            pass
        return logs


class DirectoryStore(ExperimentStore):
    """File-system reader for JSON registries, attempt directories, or static results."""

    def __init__(self, dir_path: Union[str, Path]):
        self.dir_path = Path(dir_path).resolve()
        self._cached_trials: Optional[Dict[str, TrialRecord]] = None
        self._cached_details: Dict[str, TrialDetail] = {}

    @property
    def is_demo_mode(self) -> bool:
        return False

    def has_runs(self) -> bool:
        if not self.dir_path.exists():
            return False
        return len(self._load_trial_records()) > 0

    def _load_trial_records(self) -> Dict[str, TrialRecord]:
        if self._cached_trials is not None:
            return self._cached_trials

        records: Dict[str, TrialRecord] = {}
        if not self.dir_path.exists():
            self._cached_trials = records
            return records

        # 1. Check for single registry.json file
        reg_file = self.dir_path / "registry.json"
        if reg_file.exists():
            try:
                with open(reg_file, "r", encoding="utf-8") as f:
                    content = json.load(f)
                    trials_list = content.get("trials", content) if isinstance(content, dict) else content
                    if isinstance(trials_list, list):
                        for t in trials_list:
                            rec = TrialRecord.from_dict(t)
                            records[rec.trial_id] = rec
            except (json.JSONDecodeError, OSError) as e:
                logger.warning("Error reading registry.json in %s: %s", self.dir_path, e)

        # 2. Check for trial directories under self.dir_path / "trials" or directly in self.dir_path
        scan_dir = self.dir_path / "trials" if (self.dir_path / "trials").exists() else self.dir_path
        if scan_dir.is_dir():
            try:
                for entry in scan_dir.iterdir():
                    if entry.is_dir() and entry.name not in (".git", "fixtures"):
                        t_id = entry.name
                        # Search for attempt subfolders or direct result.json
                        res_file = entry / "result.json"
                        req_file = entry / "request.json"
                        fail_file = entry / "failure.json"

                        # If not at top level, check attempt-XXXX subdirs
                        if not res_file.exists() and not fail_file.exists():
                            attempts = sorted(entry.glob("attempt-*"))
                            if attempts:
                                latest_att = attempts[-1]
                                res_file = latest_att / "result.json"
                                req_file = latest_att / "request.json"
                                fail_file = latest_att / "failure.json"

                        status = "RUNNING"
                        error_msg = None
                        config: Dict[str, Any] = {}
                        mean_brier = None
                        cond_losses = None
                        per_ep = None
                        ep_conds = None
                        wall_sec = 0.0

                        if fail_file.exists():
                            status = "FAILED"
                            try:
                                with open(fail_file, "r", encoding="utf-8") as f:
                                    fail_data = json.load(f)
                                error_msg = fail_data.get("message", fail_data.get("traceback"))
                                if "timeout" in str(error_msg).lower():
                                    status = "TIMEOUT"
                                elif "memory" in str(error_msg).lower():
                                    status = "MEMORY_LIMIT"
                            except (json.JSONDecodeError, OSError):
                                pass

                        if req_file.exists():
                            try:
                                with open(req_file, "r", encoding="utf-8") as f:
                                    req_data = json.load(f)
                                config = req_data.get("config", {})
                            except (json.JSONDecodeError, OSError):
                                pass

                        if res_file.exists():
                            status = "SUCCEEDED"
                            try:
                                with open(res_file, "r", encoding="utf-8") as f:
                                    res_data = json.load(f)
                                mean_brier = res_data.get("mean_brier")
                                wall_sec = float(res_data.get("wall_seconds", 0.0) or 0.0)
                                by_c = res_data.get("by_condition")
                                if isinstance(by_c, dict) and len(by_c) >= 4:
                                    cond_losses = ConditionLosses.from_dict(by_c)
                                per_ep = res_data.get("per_episode")
                                ep_conds = res_data.get("episode_conditions")
                            except (json.JSONDecodeError, OSError):
                                status = "CORRUPTED"
                                error_msg = "Corrupted or partially written result.json"

                        if res_file.exists() or fail_file.exists() or req_file.exists():
                            provenance = ProvenanceType.TRAIN_GROUP_CV
                            official_points = None
                            if cond_losses:
                                provenance = ProvenanceType.PUBLIC_VALIDATION
                                official_points = calculate_official_points(cond_losses)

                            records[t_id] = TrialRecord(
                                trial_id=t_id,
                                study_name="directory_scan",
                                family=str(config.get("family", "jaeger")),
                                status=status,
                                provenance=provenance,
                                is_champion=bool("champion" in t_id),
                                wall_seconds=wall_sec,
                                official_points=official_points,
                                mean_brier=mean_brier,
                                condition_losses=cond_losses,
                                per_episode_errors=per_ep,
                                episode_conditions=ep_conds,
                                hyperparameters=config,
                                error_message=error_msg,
                                is_synthetic=False,
                            )
            except OSError as e:
                logger.warning("Error scanning directory %s: %s", self.dir_path, e)

        self._cached_trials = records
        return records

    def list_trials(
        self,
        study: Optional[str] = None,
        provenance: Optional[ProvenanceType] = None,
        status: Optional[str] = None,
    ) -> List[TrialRecord]:
        records = list(self._load_trial_records().values())
        if study:
            records = [r for r in records if r.study_name == study]
        if provenance:
            records = [r for r in records if r.provenance == provenance]
        if status:
            records = [r for r in records if r.status == status.upper()]
        return records

    def get_trial(self, trial_id: str) -> Optional[TrialDetail]:
        if trial_id in self._cached_details:
            return self._cached_details[trial_id]
        recs = self._load_trial_records()
        if trial_id not in recs:
            return None
        detail = TrialDetail(record=recs[trial_id])
        self._cached_details[trial_id] = detail
        return detail

    def get_champion(self) -> Optional[TrialRecord]:
        for r in self.list_trials():
            if r.is_champion:
                return r
        return None

    def list_hypotheses(self) -> List[HypothesisRecord]:
        return []

    def list_ablations(self) -> List[ComponentAblation]:
        return []

    def get_calibration_bins(self, trial_id: Optional[str] = None) -> List[CalibrationBin]:
        return []

    def get_rare_payout_diagnostic(self, trial_id: Optional[str] = None) -> Optional[RarePayoutDiagnostic]:
        return None

    def get_execution_logs(self) -> List[ExecutionLog]:
        logs = []
        for r in self.list_trials():
            if r.status in ("FAILED", "TIMEOUT", "MEMORY_LIMIT", "CORRUPTED"):
                logs.append(
                    ExecutionLog(
                        trial_id=r.trial_id,
                        attempt=r.attempt,
                        status=r.status,
                        wall_seconds=r.wall_seconds,
                        error_message=r.error_message,
                    )
                )
        return logs


class SyntheticDemoStore(ExperimentStore):
    """Fallback demonstration store providing complete, rich fixtures."""

    def __init__(self, fixture_path: Optional[Union[str, Path]] = None):
        self.fixture_path = Path(fixture_path or DEMO_REGISTRY_PATH).resolve()
        self._trials: Dict[str, TrialRecord] = {}
        self._ablations: List[ComponentAblation] = []
        self._hypotheses: List[HypothesisRecord] = []
        self._calibration: List[CalibrationBin] = []
        self._rare_20x: Optional[RarePayoutDiagnostic] = None
        self._execution_logs: List[ExecutionLog] = []
        self._load_fixtures()

    @property
    def is_demo_mode(self) -> bool:
        return True

    def has_runs(self) -> bool:
        return len(self._trials) > 0

    def _load_fixtures(self) -> None:
        if not self.fixture_path.exists():
            logger.error("Demo fixture not found at %s", self.fixture_path)
            return

        with open(self.fixture_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        # Trials
        for t_dict in data.get("trials", []):
            rec = TrialRecord.from_dict(t_dict)
            self._trials[rec.trial_id] = rec

        # Ablations
        for ab in data.get("ablations", []):
            self._ablations.append(
                ComponentAblation(
                    variant_name=ab["variant_name"],
                    removed_component=ab["removed_component"],
                    hypothesis=ab["hypothesis"],
                    official_points=float(ab["official_points"]),
                    official_points_delta=float(ab["official_points_delta"]),
                    ci95_points=tuple(ab["ci95_points"]),  # type: ignore
                    train_brier_delta=ab.get("train_brier_delta"),
                    ci95_brier=tuple(ab["ci95_brier"]) if ab.get("ci95_brier") else None,  # type: ignore
                    condition_loss_ratios=ab.get("condition_loss_ratios"),
                    supported=bool(ab.get("supported", False)),
                    direction=ab.get("direction", "worse"),
                )
            )

        # Hypotheses
        for h in data.get("hypotheses", []):
            self._hypotheses.append(
                HypothesisRecord(
                    id=h["id"],
                    preregistered_timestamp=h["preregistered_timestamp"],
                    component=h["component"],
                    statement=h["statement"],
                    expected_direction=h["expected_direction"],
                    observed_points_diff=h.get("observed_points_diff"),
                    observed_brier_diff=h.get("observed_brier_diff"),
                    verdict=h.get("verdict", "Awaiting Trial Run"),
                    decision=h.get("decision", "NO_PROMOTION"),
                    linked_trial_id=h.get("linked_trial_id"),
                )
            )

        # Calibration
        for c in data.get("calibration", []):
            self._calibration.append(
                CalibrationBin(
                    payout_class=int(c["class"]),
                    bin_index=int(c["bin"]),
                    bin_range=tuple(c["bin_range"]),  # type: ignore
                    sample_count=int(c["sample_count"]),
                    mean_predicted=float(c["mean_predicted"]),
                    observed_frequency=float(c["observed_frequency"]),
                )
            )

        # Rare 20x
        r20 = data.get("rare_payout_20x")
        if r20:
            self._rare_20x = RarePayoutDiagnostic(
                payout_class=r20.get("payout_class", 20),
                overall_brier_component=float(r20.get("overall_brier_component", 0.0)),
                mean_predicted_prob=float(r20.get("mean_predicted_prob", 0.0)),
                true_frequency=float(r20.get("true_frequency", 0.0147)),
                calibration_correlation=float(r20.get("calibration_correlation", 0.0)),
                under_over_prediction_ratio=float(r20.get("under_over_prediction_ratio", 1.0)),
                mae=r20.get("mae"),
                ci80_width=r20.get("ci80_width"),
            )

        # Execution Logs
        for el in data.get("execution_logs", []):
            self._execution_logs.append(
                ExecutionLog(
                    trial_id=el["trial_id"],
                    attempt=el.get("attempt", 1),
                    status=el.get("status", "UNKNOWN"),
                    wall_seconds=float(el.get("wall_seconds", 0.0)),
                    memory_peak_gib=el.get("memory_peak_gib"),
                    cpu_threads=el.get("cpu_threads", 1),
                    error_category=el.get("error_category"),
                    error_message=el.get("error_message"),
                    traceback=el.get("traceback"),
                    stdout_snippet=el.get("stdout_snippet"),
                    stderr_snippet=el.get("stderr_snippet"),
                )
            )

    def list_trials(
        self,
        study: Optional[str] = None,
        provenance: Optional[ProvenanceType] = None,
        status: Optional[str] = None,
    ) -> List[TrialRecord]:
        records = list(self._trials.values())
        if study:
            records = [r for r in records if r.study_name == study]
        if provenance:
            records = [r for r in records if r.provenance == provenance]
        if status:
            records = [r for r in records if r.status == status.upper()]
        return records

    def get_trial(self, trial_id: str) -> Optional[TrialDetail]:
        if trial_id not in self._trials:
            return None
        rec = self._trials[trial_id]
        return TrialDetail(
            record=rec,
            oof_predictions=None,
            per_query_metrics=None,
            folds=None,
            raw_config=rec.hyperparameters,
            process_evidence=None,
            logs=None,
        )

    def get_champion(self) -> Optional[TrialRecord]:
        for r in self._trials.values():
            if r.is_champion:
                return r
        return self._trials.get("champion-b78abe75")

    def list_hypotheses(self) -> List[HypothesisRecord]:
        return list(self._hypotheses)

    def list_ablations(self) -> List[ComponentAblation]:
        return list(self._ablations)

    def get_calibration_bins(self, trial_id: Optional[str] = None) -> List[CalibrationBin]:
        return list(self._calibration)

    def get_rare_payout_diagnostic(self, trial_id: Optional[str] = None) -> Optional[RarePayoutDiagnostic]:
        return self._rare_20x

    def get_execution_logs(self) -> List[ExecutionLog]:
        return list(self._execution_logs)


def get_experiment_store(
    source_path: Optional[Union[str, Path]] = None,
    force_demo: bool = False,
) -> ExperimentStore:
    """Factory creating appropriate ExperimentStore with automatic fallback.

    Search sequence:
    1. If force_demo is True -> SyntheticDemoStore
    2. If source_path specified:
       - SQLite file -> SQLiteStore
       - Directory containing registry.sqlite -> SQLiteStore
       - Directory with files -> DirectoryStore
       - Empty directory -> DirectoryStore (returns empty list cleanly)
    3. Canonical repository paths:
       - research_runs/main/registry.sqlite
       - Jaeger_Main/House_Edge/research_runs/main/registry.sqlite
    4. Fallback -> SyntheticDemoStore
    """
    if force_demo:
        return SyntheticDemoStore()

    if source_path:
        p = Path(source_path).resolve()
        if p.is_file():
            if p.suffix in (".sqlite", ".db"):
                store = SQLiteStore(p)
                if store.has_runs():
                    return store
        elif p.is_dir():
            sqlite_in_dir = p / "registry.sqlite"
            if sqlite_in_dir.is_file():
                store = SQLiteStore(sqlite_in_dir)
                if store.has_runs():
                    return store
            dir_store = DirectoryStore(p)
            # If the user explicitly provided this directory, return it even if empty
            return dir_store

    # Check canonical locations in repo
    candidates = [
        Path("research_runs/main/registry.sqlite"),
        Path("Jaeger_Main/House_Edge/research_runs/main/registry.sqlite"),
    ]
    for c in candidates:
        if c.is_file():
            s = SQLiteStore(c)
            if s.has_runs():
                return s

    # Fallback to rich demonstration fixture
    return SyntheticDemoStore()
