"""SQLite trial identities and append-only attempts. One coordinator per registry."""
from contextlib import contextmanager
import json
import os
from pathlib import Path
import sqlite3
import psutil
from .common import canonical, digest, now, write_json


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
        return rows
