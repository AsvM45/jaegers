"""Cold Linux reproduction with disabled network and read-only entry/data mounts."""
import argparse
from pathlib import Path
import sys
import json
import subprocess
from .common import ROOT, require_python
from .process import run
from .release import verify, record_failure


def offline(release, data, prediction_python=None):
    require_python()
    release, data = Path(release).resolve(), Path(data).resolve()
    attempt = 1
    while (release / "offline" / f"attempt-{attempt:04d}").exists():
        attempt += 1
    attempt_root = release / "offline" / f"attempt-{attempt:04d}"
    attempt_root.mkdir(parents=True,exist_ok=False)
    output = attempt_root / "output"
    output.mkdir(exist_ok=False)
    executable = Path(prediction_python or sys.executable).absolute()
    runtime=json.loads(subprocess.check_output([str(executable),"-c",
        "import json,sys; print(json.dumps({'base':sys.base_prefix,'prefix':sys.prefix,'version':list(sys.version_info[:2])}))"],text=True))
    if runtime["version"] != [3,13]:
        raise ValueError("Prediction interpreter must be Python 3.13")
    base = Path(runtime["base"]).resolve()
    venv = Path(runtime["prefix"]).resolve()
    command = ["bwrap", "--unshare-all", "--die-with-parent", "--new-session"]
    for path in ("/usr", "/lib", "/lib64", "/etc"):
        if Path(path).exists():
            command += ["--ro-bind", path, path]
    command += ["--proc", "/proc", "--dev", "/dev", "--tmpfs", "/tmp"]
    for path in (base, venv):
        command += ["--ro-bind", str(path), str(path)]
    command += ["--ro-bind", str(release / "extracted"), "/submission",
                "--ro-bind", str(data), "/data", "--bind", str(output), "/output",
                "--ro-bind", str(ROOT / "tools/offline_runner.py"), "/runner.py",
                "--setenv", "TMP", "/tmp", "--setenv", "TEMP", "/tmp", "--setenv", "TMPDIR", "/tmp",
                "--setenv", "PATH", str(venv / "bin")+":/usr/bin:/bin",
                "--chdir", "/submission", str(executable), "/runner.py"]
    try:
        run(command, ROOT, attempt_root / "process", timeout=1800)
        if sum(p.stat().st_size for p in output.rglob("*") if p.is_file()) > 32*1024**2:
            raise ValueError("Output scratch limit exceeded")
        result = verify(release, output / "submission.csv", output / "environment.json")
    except Exception as exc:
        record_failure(release, attempt_root, exc)
        raise
    print(result["status"], result["parity"], flush=True)
    return result


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--release", required=True)
    p.add_argument("--data", default=str(ROOT / "public"))
    p.add_argument("--prediction-python",help="Separate runtime-only Python; controller dependencies remain outside sandbox")
    args = p.parse_args()
    offline(args.release, args.data,args.prediction_python)
