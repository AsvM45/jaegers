"""One command: run the control tower and both test suites, then open the dashboard.

    python start.py                # everything, then http://127.0.0.1:8080 opens in the browser
    python start.py --rules        # skip the LLM reader even if Ollama is running (fast, ~5 seconds)
    python start.py --serve-only   # just open the dashboard on the results already on disk
    python start.py --model-test   # also score the LLM reader on its own (held-out + given, ~6 min)
    python start.py --no-browser   # don't open a browser tab
    python start.py --port 9000

Works from any directory. Steps, in order:

    1. Check for Ollama and the reader model (TOWER_LLM_MODEL, default qwen3:0.6b). If it is not
       running or the model is not pulled, every step uses the rule reader instead, so the reports
       never show rule-reader results under an LLM name.
    2. python -m tower.run --notify dry-run --overwrite  -> runs/run1/  (Overview, Event feed)
    3. python tests/run_given.py                -> runs/given/       (Test reports, given suite)
    4. python tests/run_cases.py                -> runs/tests/       (Test reports, generated suite)
       python tests/run_cases.py --cases tests/holdout_cases.json --out runs/holdout   (held-out suite)
       python tests/run_model.py                -> runs/model/       (only with --model-test)
    5. python -m tower.ontology                 -> runs/ontology/    (Knowledge graph tables)
    6. Serve tower/ui/dashboard.html and open it.

A failed step is reported and the rest still run, so the dashboard always opens.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import threading
import time
import urllib.request
import webbrowser

HITACHI = os.path.dirname(os.path.abspath(__file__))
if HITACHI not in sys.path:
    sys.path.insert(0, HITACHI)

MODEL = os.environ.get("TOWER_LLM_MODEL", "qwen3:0.6b")
OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434").rstrip("/")


def ollama_has_model() -> tuple[bool, str]:
    """(usable, reason). Usable means Ollama answers and MODEL is pulled."""
    try:
        with urllib.request.urlopen(f"{OLLAMA_URL}/api/tags", timeout=2) as response:
            names = {m.get("name") for m in json.load(response).get("models", [])}
    except Exception:  # noqa: BLE001 - any failure means "not available"
        return False, f"Ollama is not running at {OLLAMA_URL} (start it with: ollama serve)"
    if MODEL not in names and f"{MODEL}:latest" not in names:
        return False, f"model {MODEL} is not pulled (run: ollama pull {MODEL})"
    return True, f"Ollama is running with {MODEL}"


class _Tee:
    """Write to the terminal and to the run's log file (runs/logs/), which the dashboard's Logs page shows."""

    def __init__(self, *streams):
        self.streams = streams

    def write(self, text):
        for stream in self.streams:
            stream.write(text)
            stream.flush()
        return len(text)

    def flush(self):
        for stream in self.streams:
            stream.flush()


def step(label: str, args: list[str]) -> bool:
    """Run one step from the Hitachi folder, streaming its output. True if it exited 0."""
    print(f"\n▶ {label}\n  $ {' '.join(['python', *args])}", flush=True)
    started = time.time()
    proc = subprocess.Popen([sys.executable, "-u", *args], cwd=HITACHI, stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT, text=True, bufsize=1)
    for line in proc.stdout:  # pass each line through, so it lands in the log file too
        print(line, end="")
    code = proc.wait()
    took = time.time() - started
    print(f"  {'✓ done' if code == 0 else f'✗ failed (exit {code})'} in {took:.1f}s", flush=True)
    return code == 0


def bind_server(server, start: int):
    """A TowerServer on the first port from start upward that binds."""
    for port in range(start, start + 20):
        try:
            return server.TowerServer(("127.0.0.1", port), server.Handler), port
        except OSError:
            continue
    raise SystemExit(f"No free port between {start} and {start + 19}.")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--rules", action="store_true", help="use the rule reader only, even if Ollama is running")
    ap.add_argument("--serve-only", action="store_true", help="skip the runs and open the dashboard")
    ap.add_argument("--no-browser", action="store_true", help="don't open a browser tab")
    ap.add_argument("--model-test", action="store_true",
                    help="also score the LLM reader on its own against the expected graphs (needs Ollama)")
    ap.add_argument("--port", type=int, default=8080, help="dashboard port (default 8080, or the next free one)")
    cli = ap.parse_args()
    sys.stdout.reconfigure(line_buffering=True)  # progress shows even when piped to a file
    if not cli.serve_only:
        logs = os.path.join(HITACHI, "runs", "logs")
        os.makedirs(logs, exist_ok=True)
        log_path = os.path.join(logs, time.strftime("start_%Y-%m-%d_%H-%M-%S.log"))
        sys.stdout = _Tee(sys.__stdout__, open(log_path, "w", encoding="utf-8"))
        print(f"python start.py {' '.join(sys.argv[1:])}   (log: runs/logs/{os.path.basename(log_path)})")

    failed = []
    if not cli.serve_only:
        if cli.rules:
            use_llm, why = False, "--rules given"
        else:
            use_llm, why = ollama_has_model()
        print(f"Reader: {'LLM ' + MODEL + ' + rule check' if use_llm else 'rules only'} ({why})")
        tower_reader = "llm" if use_llm else "rules"
        test_reader = "both" if use_llm else "rules"
        if use_llm:
            print("The LLM steps take a few minutes. Use --rules for a run in seconds.")

        steps = [
            ("Control tower on the 15 events", ["-m", "tower.run", "--reader", tower_reader, "--notify", "dry-run",
                                                "--overwrite"]),
            ("Given tests (docx TC1–TC6)", ["tests/run_given.py", "--reader", test_reader]),
            ("Generated tests (100 cases)", ["tests/run_cases.py", "--reader", test_reader]),
            ("Held-out tests, set 1 (100 cases)", ["tests/run_cases.py", "--reader", test_reader,
                                                  "--cases", "tests/holdout_cases.json", "--out", "runs/holdout"]),
            ("Held-out tests, set 2 (100 cases)", ["tests/run_cases.py", "--reader", test_reader,
                                                  "--cases", "tests/holdout2_cases.json", "--out", "runs/holdout2"]),
            ("Ontology export", ["-m", "tower.ontology"]),
        ]
        if cli.model_test:
            if use_llm:
                steps.append(("The model on its own vs the expected graphs", ["tests/run_model.py"]))
            else:
                print("--model-test skipped: it needs Ollama with the model pulled.")
        for label, args in steps:
            if not step(label, args):
                failed.append(label)

    if not cli.serve_only:
        try:
            from tower.ui import reports
            print(f"\nSummary -> {reports.write_summary()}")
        except Exception as exc:  # noqa: BLE001  the dashboard still opens
            print(f"\nCould not write runs/TEST_SUMMARY.md: {exc}")

    from tower.ui import server  # imported late: it reads TOWER_RUN_DIR at import time

    httpd, port = bind_server(server, cli.port)
    url = f"http://127.0.0.1:{port}"
    print("\n" + "─" * 60)
    if failed:
        print("Failed steps (the dashboard shows the last good results for these):")
        for label in failed:
            print(f"  ✗ {label}")
    print(f"Dashboard: {url}    (Ctrl-C to stop)")
    if not cli.no_browser:
        threading.Timer(0.5, webbrowser.open, args=(url,)).start()
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
    finally:
        httpd.server_close()


if __name__ == "__main__":
    main()
