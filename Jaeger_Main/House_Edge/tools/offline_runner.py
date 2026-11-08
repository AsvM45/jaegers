"""Runs inside Bubblewrap; not included in the submitted entry."""
import errno
import json
import os
from pathlib import Path
import resource
import socket
import subprocess
import sys
import time
import importlib.metadata

started = time.monotonic()
resource.setrlimit(resource.RLIMIT_AS, (16 * 1024**3, 16 * 1024**3))
resource.setrlimit(resource.RLIMIT_FSIZE, (32 * 1024**2, 32 * 1024**2))


def readonly(path):
    try:
        fd = os.open(path, os.O_WRONLY)
    except OSError as exc:
        return exc.errno in (errno.EROFS, errno.EACCES)
    else:
        os.close(fd)
        return False


sock = socket.socket()
sock.settimeout(1)
network_error = sock.connect_ex(("1.1.1.1", 443))
sock.close()
evidence = {
    "python": sys.version, "python_313": sys.version_info[:2] == (3, 13),
    "network_disabled": network_error in (errno.ENETUNREACH, errno.EHOSTUNREACH),
    "network_probe_errno": network_error,
    "submission_read_only": readonly("/submission/predict.py"),
    "data_read_only": readonly("/data/metadata.json"),
    "cpu_affinity": sorted(os.sched_getaffinity(0)),
    "cpu_limit_enforced": len(os.sched_getaffinity(0)) <= 2,
    "memory_limit_enforced": resource.getrlimit(resource.RLIMIT_AS)[0] == 16*1024**3,
    "time_limit_enforced": True,
    "installed_distributions":{d.metadata["Name"]:d.version for d in importlib.metadata.distributions()},
    "numpy_disabled_cpu_features":os.environ.get("NPY_DISABLE_CPU_FEATURES", ""),
}
if not all(evidence[k] for k in ("python_313", "network_disabled", "submission_read_only", "data_read_only", "cpu_limit_enforced", "memory_limit_enforced")):
    raise RuntimeError(f"Sandbox preflight failed: {evidence}")
config = json.loads(Path("/submission/reproduce.json").read_text())
if config["image"] != "python":
    raise ValueError("Unsupported reproduction environment")
result = subprocess.run(config["command"], cwd="/submission", timeout=1790)
scratch_bytes = sum(p.stat().st_size for p in Path("/tmp").rglob("*") if p.is_file())
if scratch_bytes > 128*1024**2:
    raise RuntimeError("Scratch usage exceeded 128 MiB")
evidence.update(status="SUCCEEDED" if result.returncode == 0 else "FAILED", returncode=result.returncode,
                scratch_bytes_after_run=scratch_bytes, scratch_limit_hard_enforced=False,
                wall_seconds=time.monotonic()-started,
                peak_child_rss_mib=resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss/1024)
Path("/output/environment.json").write_text(json.dumps(evidence, indent=2)+"\n")
raise SystemExit(result.returncode)
