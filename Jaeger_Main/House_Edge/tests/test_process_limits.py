import json
import sys
import pytest
from research.process import run


def test_timeout_terminates_worker_and_preserves_logs(tmp_path):
    out=tmp_path/"timeout"
    with pytest.raises(RuntimeError,match="TIMEOUT"):
        run([sys.executable,"-c","import time; time.sleep(10)"],tmp_path,out,timeout=.2,cpus=1)
    record=json.loads((out/"process.json").read_text())
    assert record["status"] == "TIMEOUT"
    assert record["returncode"] != 0
    assert (out/"stdout.log").exists() and (out/"stderr.log").exists()


def test_parallel_worker_slots_use_distinct_cpu_affinities(tmp_path):
    import psutil
    if not hasattr(psutil.Process(),"cpu_affinity") or len(psutil.Process().cpu_affinity()) < 2:
        pytest.skip("Two CPU-affinity slots unavailable")
    a=run([sys.executable,"-c","print('a')"],tmp_path,tmp_path/"a",cpus=1,slot=0)
    b=run([sys.executable,"-c","print('b')"],tmp_path,tmp_path/"b",cpus=1,slot=1)
    assert set(a["cpu_affinity"]).isdisjoint(b["cpu_affinity"])
