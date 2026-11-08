"""Small shared provenance helpers. No third-party imports needed for freezing."""
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import time
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parents[1]


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def digest(value):
    return hashlib.sha256(value if isinstance(value, bytes) else canonical(value).encode()).hexdigest()


def file_hash(path):
    return digest(Path(path).read_bytes())


def tree_hashes(path):
    path = Path(path)
    return {p.relative_to(path).as_posix(): file_hash(p) for p in sorted(path.rglob("*"))
            if p.is_file() and "__pycache__" not in p.parts and p.suffix != ".pyc"}


def now():
    return datetime.now(timezone.utc).isoformat()


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
    # OneDrive/Windows readers can briefly deny a rename even after our file is
    # closed. Keep atomic replacement; retry boundedly rather than writing in place.
    for attempt in range(10):
        try:
            os.replace(temporary, path)
            break
        except PermissionError:
            if attempt == 9:
                raise
            time.sleep(min(.05 * 2**attempt, .5))


def git(*args):
    return subprocess.check_output(["git", *args], cwd=REPO, text=True).strip()


def environment():
    packages = {}
    for name in ("numpy", "scipy", "scikit-learn", "joblib", "threadpoolctl", "psutil",
                 "optuna", "xgboost", "lightgbm", "statsmodels", "hmmlearn"):
        try:
            packages[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            packages[name] = None
    return {"python": platform.python_version(), "executable": sys.executable,
            "platform": platform.platform(), "machine": platform.machine(),
            "processor": platform.processor(), "packages": packages,
            "numeric_environment": {name: os.environ.get(name) for name in (
                "NPY_DISABLE_CPU_FEATURES", "OPENBLAS_CORETYPE", "MKL_CBWR",
                "MKL_ENABLE_INSTRUCTIONS", "BLIS_ARCH_TYPE", "OMP_DYNAMIC",
                "MKL_DYNAMIC", "PYTHONHASHSEED", "OMP_NUM_THREADS",
                "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS")}}


def require_python():
    if sys.version_info[:2] != (3, 13):
        raise RuntimeError(f"Research requires CPython 3.13; got {sys.version} at {sys.executable}")


def limit_threads():
    for name in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
        os.environ[name] = "2"
