"""Reproduce control-tower crashes and path escapes. Does not delete real suites.

Writes nothing outside this temp tree and runs/break/. Never calls reports.delete
with a real suite id.
"""

from __future__ import annotations

import io
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import traceback
import urllib.error
import urllib.request

HITACHI = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if HITACHI not in sys.path:
    sys.path.insert(0, HITACHI)

os.chdir(HITACHI)

PROTECTED = ("given", "holdout", "holdout2", "stress", "tests", "accuracy", "run1")
REAL_SUITE_IDS = ("given", "holdout", "holdout2", "generated", "stress", "accuracy")
OUTAGE = (
    "Power failure at Jackson from 2027-03-16 through 2027-03-18. "
    "Production is stopped."
)
FINDINGS: list[dict] = []


def snap() -> dict:
    runs = os.path.join(HITACHI, "runs")
    out = {}
    for name in PROTECTED:
        path = os.path.join(runs, name)
        out[name] = sorted(os.listdir(path)) if os.path.isdir(path) else None
    return out


def record(name: str, ok: bool, detail: str) -> None:
    FINDINGS.append({"name": name, "ok": ok, "detail": detail})
    print(f"[{'ok' if ok else 'FAIL'}] {name}: {detail}", flush=True)


def fetch(port: int, path: str, method: str = "GET", headers: dict | None = None):
    req = urllib.request.Request(
        f"http://127.0.0.1:{port}{path}",
        method=method,
        headers=headers or {},
    )
    try:
        with urllib.request.urlopen(req, timeout=8) as res:
            return res.status, res.read(4000)
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read(4000)
    except Exception as exc:  # noqa: BLE001 - the probe records client-side failures
        return type(exc).__name__, str(exc).encode("utf-8", "replace")


class Sink:
    """Stand-in for BaseHTTPRequestHandler header machinery."""

    def __init__(self) -> None:
        self.status = None
        self.wfile = io.BytesIO()

    def send_response(self, code, message=None):
        self.status = code

    def send_header(self, key, value):
        return None

    def end_headers(self):
        return None


def call_static(root: str, rel: str):
    from tower.ui.server import Handler

    handler = Handler.__new__(Handler)
    sink = Sink()
    handler.wfile = sink.wfile
    handler.send_response = sink.send_response
    handler.send_header = sink.send_header
    handler.end_headers = sink.end_headers
    try:
        handler._static(root, rel)
    except Exception as exc:  # noqa: BLE001
        return "raise", type(exc).__name__, str(exc)
    body = sink.wfile.getvalue()
    return sink.status, body


def call_get(path: str):
    from tower.ui.server import Handler

    handler = Handler.__new__(Handler)
    sink = Sink()
    handler.path = path
    handler.wfile = sink.wfile
    handler.send_response = sink.send_response
    handler.send_header = sink.send_header
    handler.end_headers = sink.end_headers
    handler.headers = {}
    try:
        handler.do_GET()
    except Exception as exc:  # noqa: BLE001
        return "raise", type(exc).__name__ + ": " + str(exc)
    body = sink.wfile.getvalue()
    return sink.status, body[:300]


def junction(link: str, target: str) -> str | None:
    if os.path.lexists(link):
        os.rmdir(link)
    result = subprocess.run(
        ["cmd", "/c", "mklink", "/J", link, target],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return (result.stdout + result.stderr).strip()
    return None


def test_static_and_delete(before: dict) -> None:
    from tower.ui import reports

    base = tempfile.mkdtemp(prefix="ww-break-")
    try:
        root = os.path.join(base, "root")
        outside = os.path.join(base, "outside")
        os.makedirs(root)
        os.makedirs(os.path.join(outside, "sub"))
        secret = os.path.join(outside, "sub", "secret.md")
        with open(secret, "w", encoding="utf-8") as handle:
            handle.write("SECRET-MARKER")
        with open(os.path.join(root, "ok.md"), "w", encoding="utf-8") as handle:
            handle.write("INSIDE-OK")
        link = os.path.join(root, "link")
        err = junction(link, outside)
        if err:
            record("static junction setup", False, err)
        else:
            status, body = call_static(root, "ok.md")
            record(
                "static inside file",
                status == 200 and b"INSIDE-OK" in body,
                f"status={status} body={body[:80]!r}",
            )
            status, body = call_static(root, os.path.join("..", "outside", "sub", "secret.md"))
            leaked = isinstance(body, (bytes, bytearray)) and b"SECRET-MARKER" in body
            record(
                "static dotdot",
                status == 404 and not leaked,
                f"status={status} leaked={leaked} body={body[:80]!r}",
            )
            status, body = call_static(root, os.path.join("link", "sub", "secret.md"))
            leaked = isinstance(body, (bytes, bytearray)) and b"SECRET-MARKER" in body
            record(
                "static junction",
                status == 404 and not leaked,
                f"status={status} leaked={leaked} body={body[:120]!r}",
            )
            abs_rel = secret
            status, body = call_static(root, abs_rel)
            leaked = isinstance(body, (bytes, bytearray)) and b"SECRET-MARKER" in body
            record(
                "static absolute rel",
                (status == 404 or status == "raise") and not leaked,
                f"status={status} leaked={leaked} body={str(body)[:120]!r}",
            )

        status, info = call_get("/runs/foo%00.md")
        record("GET runs null byte", status == 404, f"{status} {info}")
        with open(os.path.join(root, "note.md"), "w", encoding="utf-8") as handle:
            handle.write("NOTE-MARKER")
        for rel in ("note\x00.md", "note.md\x00.md", "note.md\x00"):
            status, body = call_static(root, rel)
            leaked = isinstance(body, (bytes, bytearray)) and b"NOTE-MARKER" in body
            record(
                f"static nul rel {rel!r}",
                not leaked,
                f"status={status} leaked={leaked} body={str(body)[:120]!r}",
            )

        # Path arguments against the real function. Reader ids are not directory names.
        outside_before = snap()
        if outside_before != before:
            record("snapshot drifted before delete probes", False, "protected listdir changed")
        probes = [
            ("given", ".."),
            ("given", "../.."),
            ("given", "..\\..\\..\\Windows"),
            ("given", "reader/../../outside"),
            ("given", "C:\\Windows"),
            ("given", "\\Windows\\System32"),
            ("given", ""),
            ("given", "."),
            ("given", "\x00"),
            ("given", "no-such\x00reader"),
            ("given", "A" * 20000),
            ("../given", "whatever"),
            ("given/../given", "whatever"),
            ("", ""),
            ("generated", "..\\..\\secret"),
        ]
        for suite_id, reader_id in probes:
            if suite_id in REAL_SUITE_IDS:
                parent_name = next(
                    s["runs"] for s in reports.SUITES if s["id"] == suite_id
                )
                parent = os.path.join(reports.RUNS, parent_name)
                if os.path.isdir(parent) and reader_id in os.listdir(parent):
                    record("refused live reader", False, f"would have deleted {suite_id}/{reader_id}")
                    continue
            removed = reports.delete(suite_id, reader_id)
            record(
                f"delete {suite_id!r} {reader_id[:40]!r}",
                removed is False,
                f"returned {removed!r}",
            )
        after_live = snap()
        record(
            "protected dirs after live delete probes",
            after_live == before,
            "unchanged" if after_live == before else "LISTDIR CHANGED",
        )

        # Temp suite only. Monkeypatch stays inside this process.
        suite_dir = os.path.join(base, "runs", "suite")
        keep = os.path.join(suite_dir, "keep")
        os.makedirs(keep)
        with open(os.path.join(keep, "marker.txt"), "w", encoding="utf-8") as handle:
            handle.write("keep")
        precious = os.path.join(outside, "precious.txt")
        with open(precious, "w", encoding="utf-8") as handle:
            handle.write("precious")
        suite_link = os.path.join(suite_dir, "link")
        err = junction(suite_link, outside)
        old_runs, old_suites = reports.RUNS, reports.SUITES
        reports.RUNS = os.path.join(base, "runs")
        reports.SUITES = [{
            "id": "zzbreak",
            "title": "temp",
            "subtitle": "temp",
            "cases": "nope.json",
            "runs": "suite",
        }]
        try:
            if err:
                record("delete junction setup", False, err)
            else:
                parent = os.path.realpath(suite_dir)
                target = os.path.realpath(suite_link)
                record(
                    "delete junction realpath",
                    True,
                    f"parent={parent} target={target} dirname_eq={os.path.dirname(target) == parent}",
                )
                removed = reports.delete("zzbreak", "link")
                precious_ok = os.path.isfile(precious)
                outside_ok = os.path.isdir(outside)
                record(
                    "delete junction does not escape",
                    removed is False and precious_ok and outside_ok,
                    f"returned {removed!r} precious={precious_ok} outside={outside_ok}",
                )
            removed = reports.delete("zzbreak", "keep")
            keep_gone = not os.path.exists(keep)
            record(
                "delete temp reader still works",
                removed is True and keep_gone and os.path.isfile(precious),
                f"returned {removed!r} keep_gone={keep_gone}",
            )
            for reader_id in ("..", "..\\..\\outside", "C:\\Windows", "keep\\..\\..\\outside", "\x00"):
                removed = reports.delete("zzbreak", reader_id)
                record(
                    f"temp delete {reader_id!r}",
                    removed is False and os.path.isfile(precious),
                    f"returned {removed!r} precious={os.path.isfile(precious)}",
                )
        finally:
            reports.RUNS, reports.SUITES = old_runs, old_suites
    finally:
        shutil.rmtree(base, ignore_errors=True)


def test_http(before: dict) -> None:
    from tower.ui import server as srv

    bad_json = os.path.join(tempfile.mkdtemp(prefix="ww-break-http-"), "bad.json")
    try:
        with open(bad_json, "wb") as handle:
            handle.write(b"\xff\xfe not utf-8")
        old_events = srv.EVENTS
        srv.EVENTS = bad_json
        try:
            status, body = call_get("/api/events")
        finally:
            srv.EVENTS = old_events
        record("GET events invalid utf-8", status == "raise", f"{status} {body}")

        surrogate_path = bad_json + ".surrogate.json"
        with open(surrogate_path, "w", encoding="utf-8") as handle:
            handle.write('[{"event_id": "E", "text": "\\ud800"}]')
        old_traces = srv.TRACES
        srv.TRACES = surrogate_path
        try:
            status, body = call_get("/api/traces")
        finally:
            srv.TRACES = old_traces
        record("GET traces lone surrogate", status == "raise", f"{status} {body}")

        httpd = srv.TowerServer(("127.0.0.1", 0), srv.Handler)
        advertised = httpd.server_address
        bound = httpd.socket.getsockname()
        record(
            "bind port 0 address",
            True,
            f"server_address={advertised} getsockname={bound} server_port={httpd.server_port}",
        )
        port = bound[1]
        thread = threading.Thread(target=httpd.serve_forever, daemon=True)
        thread.start()
        try:
            status, body = fetch(advertised[1], "/no-such")
            record("HTTP connect advertised port", True, f"{status} {body[:120]!r}")
            status, body = fetch(port, "/runs/foo%00.md")
            record("HTTP runs null byte", status == 404, f"{status} {body[:180]!r}")
            status, body = fetch(port, "/no-such")
            record("HTTP server still up", status == 404, f"{status} {body[:80]!r}")
            status, body = fetch(
                port,
                "/api/test_reports/given/..%2F..%2F..%2FWindows",
                method="DELETE",
                headers={"Host": "127.0.0.1"},
            )
            record("HTTP delete traversal", status == 404, f"{status} {body[:160]!r}")
            status, body = fetch(
                port,
                "/api/test_reports/zzbreak/nope",
                method="DELETE",
                headers={"Host": "evil.example"},
            )
            record("HTTP delete foreign host", status == 403, f"{status} {body[:120]!r}")
            srv.EVENTS = bad_json
            status, body = fetch(port, "/api/events")
            record("HTTP events invalid utf-8", True, f"{status} {body[:220]!r}")
            srv.EVENTS = old_events
            srv.TRACES = surrogate_path
            status, body = fetch(port, "/api/traces")
            record("HTTP traces lone surrogate", True, f"{status} {body[:220]!r}")
            srv.TRACES = old_traces
            status, body = fetch(port, "/no-such")
            record("HTTP server after unicode errors", status == 404, f"{status} {body[:80]!r}")
        finally:
            srv.EVENTS = old_events
            srv.TRACES = old_traces
            httpd.shutdown()
            httpd.server_close()
        record("protected dirs after http", snap() == before, "compared to start")
    finally:
        shutil.rmtree(os.path.dirname(bad_json), ignore_errors=True)


def test_allow_url() -> None:
    main = os.path.join(HITACHI, "desktop", "main.js")
    source = open(main, encoding="utf-8").read()
    start = source.find("function allowUrl")
    end = source.find("function createWindow")
    fn = source[start:end].strip()
    script = (
        "const origin = 'http://127.0.0.1:8080';\n"
        + fn
        + "\nconst urls = [\n"
        "  'http://127.0.0.1:8080/',\n"
        "  'http://127.0.0.1:8080/api/events',\n"
        "  'http://127.0.0.1:80800/',\n"
        "  'http://127.0.0.1:8080.example/',\n"
        "  'http://127.0.0.1:8080@evil.example/',\n"
        "  'file:///C:/Windows/win.ini',\n"
        "  'https://evil.example/',\n"
        "];\n"
        "for (const u of urls) console.log(JSON.stringify({u, allow: allowUrl(u)}));\n"
    )
    node = shutil.which("node")
    if not node:
        record("allowUrl", False, "node not on PATH")
        return
    result = subprocess.run([node, "-e", script], capture_output=True, text=True, timeout=20)
    record(
        "allowUrl",
        result.returncode == 0,
        (result.stdout or result.stderr).strip(),
    )


def test_reader() -> None:
    from tower.agents.coordinator import handle_event
    from tower.agents.understand import understand
    from tower.graph import WorldGraph

    print("loading graph...", flush=True)
    started = time.perf_counter()
    graph = WorldGraph()
    print(f"graph loaded in {time.perf_counter() - started:.1f}s", flush=True)

    class Rec:
        def __init__(self) -> None:
            self.calls = []

        def call(self, event_id, tool, args):
            self.calls.append((tool, dict(args)))
            return {}

    def run_case(label: str, text: str) -> None:
        t0 = time.perf_counter()
        try:
            incidents = understand(graph, text)
            kinds = [item.kind for item in incidents]
            box = Rec()
            event = {
                "event_id": "break-" + label,
                "source": "break",
                "received_at": "2027-03-08T08:00:00",
                "text": text,
            }
            trace = handle_event(graph, box, event)
            elapsed = time.perf_counter() - t0
            tools = [call.tool for call in trace.calls]
            record(
                "reader " + label,
                True,
                f"{elapsed:.2f}s kinds={kinds} tools={tools} n={len(text)}",
            )
        except Exception as exc:  # noqa: BLE001
            elapsed = time.perf_counter() - t0
            record(
                "reader " + label,
                False,
                f"{elapsed:.2f}s {type(exc).__name__}: {exc}\n{traceback.format_exc(limit=6)}",
            )

    hidden = (
        "Power fail\x00ure at Jackson from 2027-03-16 through 2027-03-18. "
        "Production is stop\x00ped."
    )
    run_case("empty", "")
    run_case("whitespace", " \n\t ")
    run_case("null", "\x00")
    run_case("null20k", "\x00" * 20000)
    run_case("chars20k", "x" * 20000)
    run_case("outage", OUTAGE)
    run_case("outage-nul-inside-words", hidden)
    run_case(
        "outage-soh-inside-words",
        "Power fail\x01ure at Jackson from 2027-03-16 through 2027-03-18. "
        "Production is stop\x01ped.",
    )
    run_case("outage-leading-nul", "\x00" + OUTAGE)
    run_case("surrogate", "\ud800")
    run_case("outage-surrogate", OUTAGE + "\ud800")


def main() -> None:
    before = snap()
    print("protected snapshot taken", flush=True)
    test_static_and_delete(before)
    test_http(before)
    test_allow_url()
    test_reader()
    after = snap()
    record("protected dirs at end", after == before, "unchanged" if after == before else "CHANGED")
    failed = [item for item in FINDINGS if not item["ok"]]
    print(f"DONE {len(FINDINGS)} checks, {len(failed)} failed", flush=True)


if __name__ == "__main__":
    main()
