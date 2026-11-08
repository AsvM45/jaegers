"""Cold Linux reproduction with disabled network and read-only entry/data mounts."""
import argparse
from pathlib import Path
import sys
from .common import ROOT, require_python
from .process import run
from .release import verify


def offline(release, data):
    require_python()
    release, data = Path(release).resolve(), Path(data).resolve()
    output = release / "linux_output"
    output.mkdir(exist_ok=False)
    executable = Path(sys.executable).absolute()
    base = Path(sys.base_prefix).resolve()
    venv = Path(sys.prefix).resolve()
    command = ["bwrap", "--unshare-all", "--die-with-parent", "--new-session"]
    for path in ("/usr", "/lib", "/lib64", "/etc"):
        if Path(path).exists():
            command += ["--ro-bind", path, path]
    command += ["--proc", "/proc", "--dev", "/dev", "--size", "134217728", "--tmpfs", "/tmp"]
    for path in (base, venv):
        command += ["--ro-bind", str(path), str(path)]
    command += ["--ro-bind", str(release / "extracted"), "/submission",
                "--ro-bind", str(data), "/data", "--bind", str(output), "/output",
                "--ro-bind", str(ROOT / "tools/offline_runner.py"), "/runner.py",
                "--setenv", "PATH", str(venv / "bin")+":/usr/bin:/bin",
                "--chdir", "/submission", str(executable), "/runner.py"]
    run(command, ROOT, release / "linux_sandbox", timeout=1800)
    if sum(p.stat().st_size for p in output.rglob("*") if p.is_file()) > 32*1024**2:
        raise ValueError("Output scratch limit exceeded")
    result = verify(release, output / "submission.csv", output / "environment.json")
    print(result["status"], result["parity"], flush=True)
    return result


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--release", required=True)
    p.add_argument("--data", default=str(ROOT / "public"))
    args = p.parse_args()
    offline(args.release, args.data)
