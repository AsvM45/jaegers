"""SQLite trial identities and append-only attempts. One coordinator per registry."""
from contextlib import contextmanager
import json
import os
from pathlib import Path
import sqlite3
import psutil
from .common import canonical, digest, now, tree_hashes, write_json


def export_snapshot(rows, out):
    """Versioned, self-contained dashboard data; never opens/writes the source DB."""
    path = Path(out) / "registry.json"
    previous = json.loads(path.read_text()) if path.exists() else {}
    if previous and (not isinstance(previous, dict) or previous.get("schema") != "jaegers.experiment_registry" or previous.get("schema_version") != 1):
        raise ValueError("Unsupported prior export schema; use a new destination")
    sealed = {r["trial_id"]: r for r in previous.get("trials", [])}
    records = []
    for row in rows:
        config, identity = json.loads(row["config"]), json.loads(row["identity"])
        artifact = Path(row["artifact"]) if row.get("artifact") else None
        result_path = artifact / "result.json" if artifact else None
        result = json.loads(result_path.read_text()) if result_path and result_path.exists() else {}
        if row["status"] == "SUCCEEDED" and not result:
            raise ValueError(f"Completed trial lacks result evidence: {row['id']}")
        if result and result.get("evaluation_source") != "sampled_outcome_group_cv":
            raise ValueError("Core registry export requires explicit sampled_outcome_group_cv provenance")
        terminal = row["status"] not in ("PENDING", "RUNNING")
        hashes = tree_hashes(artifact) if terminal and artifact and artifact.exists() else None
        old = sealed.get(row["id"])
        if old and old.get("artifact_sha256") is not None and old["attempt"] == row["attempt"] and old["artifact_sha256"] != hashes:
            raise ValueError(f"Sealed trial artifact bytes changed: {row['id']}")
        metrics = result if row["status"] == "SUCCEEDED" else {}
        records.append({
            "trial_id": row["id"], "study_name": row["study"],
            "family": config.get("family", "unknown"), "status": row["status"],
            "attempt": row["attempt"], "created_at": row["created_at"],
            "finished_at": row["finished_at"], "wall_seconds": row["wall_seconds"],
            "provenance": "TRAIN_GROUP_CV", "evaluation_source": result.get("evaluation_source"),
            "official_points": None, "mean_brier": metrics.get("mean_brier"),
            "condition_losses": None, "sampled_brier_by_condition": metrics.get("by_condition"),
            "per_episode_errors": metrics.get("per_episode"),
            "episode_conditions": metrics.get("episode_conditions"),
            "calibration_bins": metrics.get("calibration"),
            "hyperparameters": config, "source_commit": identity.get("head", ""),
            "error_message": row["error"], "is_synthetic": False,
            "artifact_path": None, "artifact_sha256": hashes,
            "identity": identity, "result": result,
        })
    content = {"schema": "jaegers.experiment_registry", "schema_version": 1, "trials": records}
    content["content_sha256"] = digest(content)
    write_json(path, content)
    return content


class Registry:
    def __init__(self, root):
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self.path = self.root / "registry.sqlite"
        with self.connect() as db:
            db.executescript('''
              PRAGMA journal_mode=WAL;
              CREATE TABLE IF NOT EXISTS trials (
                id TEXT PRIMARY KEY, study TEXT NOT NULL, config TEXT NOT NULL,
                identity TEXT NOT NULL, status TEXT NOT NULL, attempt INTEGER NOT NULL DEFAULT 0,
                artifact TEXT, mean_brier REAL, wall_seconds REAL, error TEXT,
                created_at TEXT NOT NULL, finished_at TEXT);
              CREATE TABLE IF NOT EXISTS attempts (
                trial_id TEXT NOT NULL, attempt INTEGER NOT NULL, artifact TEXT NOT NULL,
                status TEXT NOT NULL, started_at TEXT NOT NULL, finished_at TEXT, error TEXT,
                PRIMARY KEY(trial_id,attempt));
              CREATE TABLE IF NOT EXISTS coordinator (id INTEGER PRIMARY KEY, pid INTEGER, birth REAL);
              CREATE TABLE IF NOT EXISTS study_trials (study TEXT NOT NULL, trial_id TEXT NOT NULL,
                PRIMARY KEY(study,trial_id));
            ''')

    def connect(self):
        return sqlite3.connect(self.path, timeout=30)

    @contextmanager
    def coordinator(self):
        pid = os.getpid()
        birth = psutil.Process(pid).create_time()
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT pid,birth FROM coordinator WHERE id=1").fetchone()
            if row:
                try:
                    active = psutil.Process(row[0]).create_time() == row[1]
                except psutil.Error:
                    active = False
                if active:
                    raise RuntimeError("A live sweep already owns this registry")
            db.execute("INSERT OR REPLACE INTO coordinator VALUES (1,?,?)", (pid,birth))
        try:
            yield self
        finally:
            with self.connect() as db:
                db.execute("DELETE FROM coordinator WHERE id=1 AND pid=? AND birth=?", (pid,birth))

    def register(self, study, config, identity):
        # A docs-only team commit must not rerun identical numerical work. HEAD is
        # retained as provenance; actual numerical source hashes remain in the key.
        numerical_identity={k:v for k,v in identity.items() if k != "head"}
        if "champion_sha256" in numerical_identity:
            numerical_identity["champion_sha256"]={k:v for k,v in numerical_identity["champion_sha256"].items()
                                                  if k.endswith(".py") or k == "params.json"}
        trial_id = digest({"config":config, "identity":numerical_identity})
        with self.connect() as db:
            db.execute("INSERT OR IGNORE INTO trials (id,study,config,identity,status,created_at) VALUES (?,?,?,?,?,?)",
                       (trial_id,study,canonical(config),canonical(identity),"PENDING",now()))
            db.execute("INSERT OR IGNORE INTO study_trials VALUES (?,?)",(study,trial_id))
        return trial_id

    def start(self, trial_id, retry_failed=False):
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            status, attempt = db.execute("SELECT status,attempt FROM trials WHERE id=?", (trial_id,)).fetchone()
            if status == "SUCCEEDED" or (status in ("FAILED","TIMEOUT","MEMORY_LIMIT") and not retry_failed):
                return None
            if status == "RUNNING":
                db.execute("UPDATE attempts SET status='INTERRUPTED',finished_at=?,error=? WHERE trial_id=? AND attempt=?",
                           (now(),"Previous coordinator exited before finalization",trial_id,attempt))
            attempt += 1
            artifact = self.root / "trials" / trial_id / f"attempt-{attempt:04d}"
            artifact.mkdir(parents=True, exist_ok=False)
            db.execute("INSERT INTO attempts VALUES (?,?,?,?,?,?,?)", (trial_id,attempt,str(artifact),"RUNNING",now(),None,None))
            db.execute("UPDATE trials SET status='RUNNING',attempt=?,artifact=?,error=NULL WHERE id=?", (attempt,str(artifact),trial_id))
        return artifact

    def finish(self, trial_id, status, result=None, error=None, wall_seconds=None):
        with self.connect() as db:
            db.execute("UPDATE trials SET status=?,mean_brier=?,wall_seconds=?,error=?,finished_at=? WHERE id=?",
                       (status,(result or {}).get("mean_brier"),wall_seconds,error,now(),trial_id))
            db.execute("UPDATE attempts SET status=?,finished_at=?,error=? WHERE trial_id=? AND attempt=(SELECT attempt FROM trials WHERE id=?)",
                       (status,now(),error,trial_id,trial_id))

    def rows(self):
        with self.connect() as db:
            db.row_factory = sqlite3.Row
            return [dict(r) for r in db.execute("SELECT * FROM trials ORDER BY created_at,id")]

    def export(self):
        rows = self.rows()
        write_json(self.root / "registry.json", rows)
        export_snapshot(rows, self.root / "exports/v1")
        return rows


if __name__ == "__main__":
    import argparse
    from .report import read_rows
    parser = argparse.ArgumentParser(description="Export an existing registry read-only for portable dashboard use")
    parser.add_argument("--root", required=True, help="Existing directory containing registry.sqlite")
    parser.add_argument("--out", required=True, help="Destination folder; never the source registry directory")
    args = parser.parse_args()
    if Path(args.root).resolve() == Path(args.out).resolve():
        parser.error("Export destination must differ from source registry directory")
    snapshot = export_snapshot(read_rows(args.root), args.out)
    print(json.dumps({"schema_version": snapshot["schema_version"], "trials": len(snapshot["trials"]),
                      "content_sha256": snapshot["content_sha256"]}))
