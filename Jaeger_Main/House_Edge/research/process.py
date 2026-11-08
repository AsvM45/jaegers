"""Supervised subprocesses: bounded CPU, memory and wall time, durable evidence."""
import os
from pathlib import Path
import subprocess
import time
import psutil
from .common import now, write_json


def run(command, cwd, out, timeout=1800, memory_gib=16, cpus=2, env=None, slot=0):
    out = Path(out)
    out.mkdir(parents=True, exist_ok=False)
    record = {"command": [str(x) for x in command], "cwd": str(cwd), "started_at": now(),
              "timeout_seconds": timeout, "memory_limit_gib": memory_gib, "cpus": cpus,
              "status": "RUNNING"}
    write_json(out / "process.json", record)
    child_env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
    scratch = out.resolve() / "tmp"
    scratch.mkdir()
    child_env.update(TMP=str(scratch), TEMP=str(scratch), TMPDIR=str(scratch))
    for key in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
        child_env[key] = str(cpus)
    child_env.update(env or {})
    start = time.perf_counter()
    peak = 0
    status = None
    with (out / "stdout.log").open("w", encoding="utf-8") as stdout, (out / "stderr.log").open("w", encoding="utf-8") as stderr:
        proc = subprocess.Popen(record["command"], cwd=cwd, env=child_env, stdout=stdout, stderr=stderr)
        monitored = psutil.Process(proc.pid)
        try:
            allowed = monitored.cpu_affinity()
            selected = allowed[slot*cpus:slot*cpus+cpus]
            if not selected:
                raise ValueError("Requested CPU slot exceeds available CPUs")
            monitored.cpu_affinity(selected)
            record["cpu_affinity"] = selected
        except (AttributeError, psutil.Error):
            record["cpu_affinity"] = None
        try:
            while proc.poll() is None:
                try:
                    tree = [monitored, *monitored.children(recursive=True)]
                    rss = sum(p.memory_info().rss for p in tree if p.is_running())
                    peak = max(peak, rss)
                except psutil.Error:
                    pass
                elapsed = time.perf_counter() - start
                if elapsed > timeout:
                    status = "TIMEOUT"
                    break
                if peak > memory_gib * 1024**3:
                    status = "MEMORY_LIMIT"
                    break
                time.sleep(0.1)
        finally:
            if proc.poll() is None:
                for child in monitored.children(recursive=True):
                    try:
                        child.kill()
                    except psutil.Error:
                        pass
                proc.kill()
            proc.wait()
    record.update(status=status or ("SUCCEEDED" if proc.returncode == 0 else "FAILED"),
                  returncode=proc.returncode, finished_at=now(),
                  wall_seconds=time.perf_counter() - start, peak_rss_mib=peak / 1024**2)
    write_json(out / "process.json", record)
    if record["status"] != "SUCCEEDED":
        raise RuntimeError(f"{record['status']}: {command}; see {out}")
    return record
