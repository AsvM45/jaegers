"""Wacky Wheels control tower page. Standard library only.

From the Hitachi directory:

    python -m tower.ui.server
    python tower/ui/server.py

Listens on http://127.0.0.1:8080

    GET /                     the dashboard (the React build in tower/ui/dist; dashboard.html if not built)
    GET /assets/...           the React build's scripts and styles
    GET /api/events
    GET /api/ontology
    GET /api/traces
    GET /api/log
    GET /api/outbox     messages dispatched to Slack, Teams, Gmail, Outlook... for the run
    GET /api/channels   which channels are configured (names and kinds only, never secrets)
    GET /api/ontology_export   node and edge types for the ontology diagram
    GET /runs/<...>.md         a Markdown report the test runs wrote (download from the Tests page)
    GET /api/logs[?name=...]   saved start.py output (runs/logs/), list or one file
    GET /api/domains           the domain map (tower/domains.py): which part of the tower owns which fact
    GET /api/ontology.mmd      the ontology as a Mermaid diagram (tower/ontology.mmd)
    GET /api/agents            the coordinator and the three specialist agents (role, tools, rules)
    GET /api/test_reports      expected vs actual outcome for every test case, per reader
    GET /api/revision          a token that changes when the run or the saved results change
    GET /api/events/chat       the event-add transcript
    POST /api/events/chat      read one chat message and add it to the feed
    GET /api/events/run        the event run in progress (or the last one)
    GET /api/events/run/stream the same run as a server-sent event stream
    POST /api/events/run       walk the feed and report each event as it finishes
    POST /api/events/run/stop  stop that walk
    GET /api/run               the test grade in progress (or the last one), one snapshot
    GET /api/run/stream        the same grade as a server-sent event stream
    POST /api/run              start a grade: {"reader":"rules"|"llm"|"both","suites":["given",...]}
    POST /api/run/stop         stop the grade that is going
    GET /api/knowledge_graph?view=network|schema|event&event=E-01[&run=given/rules]
                               {nodes, links} for the orb graph
    GET /orb/...               the orb graph viewer (orb-graph/public), embedded on the Ontology page
    DELETE /api/test_reports/<suite>/<reader>   delete one report folder under runs/
"""

from __future__ import annotations

import json
import os
import socket
import sys
import threading
import time
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

HERE = os.path.dirname(os.path.abspath(__file__))
HITACHI = os.path.abspath(os.path.join(HERE, "..", ".."))
if HITACHI not in sys.path:
    sys.path.insert(0, HITACHI)

DASHBOARD = os.path.join(HERE, "dashboard.html")
# The React dashboard (tower/ui/web), built with `npm run build` into tower/ui/dist.
DIST = os.path.join(HERE, "dist")
ONTOLOGY_JSON = os.path.join(HITACHI, "runs", "ontology", "ontology.json")
ORB_ROOT = os.path.join(HITACHI, "orb-graph", "public")
ONTOLOGY_MMD = os.path.join(HITACHI, "tower", "ontology.mmd")
STATIC_TYPES = {
    ".html": "text/html; charset=utf-8", ".js": "text/javascript; charset=utf-8",
    ".css": "text/css; charset=utf-8", ".json": "application/json", ".svg": "image/svg+xml",
    ".png": "image/png", ".ico": "image/x-icon", ".woff2": "font/woff2", ".md": "text/markdown; charset=utf-8",
}
# Test-suite run folders the knowledge graph may read traces from (suite id -> runs/ subfolder).
SUITE_RUNS = {"given": "given"}
EVENTS = os.path.join(HITACHI, "Data", "hack_the_highway_package", "data", "events.json")
# TOWER_RUN_DIR=runs/live shows the live channel feed instead of the batch run.
RUN_DIR = os.path.join(HITACHI, os.environ.get("TOWER_RUN_DIR", os.path.join("runs", "run1")))
TRACES = os.path.join(RUN_DIR, "traces.json")
LOG = os.path.join(RUN_DIR, "action_log.jsonl")
OUTBOX = os.path.join(RUN_DIR, "outbox.jsonl")
if os.path.isfile(os.path.join(RUN_DIR, "events.json")):
    EVENTS = os.path.join(RUN_DIR, "events.json")
HOST = "127.0.0.1"
PORT = 8080

# The three citation chains WorldGraph builds. Counts come from the tables.
RELATIONSHIPS = [
    "Shipment to dealer: shipment, part, model through the bill of materials, plant, production order, customer order, dealer and customer.",
    "Plant to dealer: plant, production order, customer order, dealer and customer.",
    "Lot to dealer or customer: lot, production order, vehicle, then the dealer, or the dealer and customer when the vehicle is sold.",
]

_ontology = None
_ontology_lock = threading.Lock()


class NotFound(Exception):
    """The URL named something this server does not have. That is a 404, not a failed read."""


class TowerServer(ThreadingHTTPServer):
    """Bind without a reverse-DNS lookup, which can stall on some networks."""

    def server_bind(self):
        # Set what TCPServer.server_bind would have, so a restart can rebind a port in TIME_WAIT.
        if self.allow_reuse_address:
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.bind(self.server_address)
        # Port 0 is assigned by the OS. getsockname() is the port that actually listened.
        self.server_address = self.socket.getsockname()
        host, port = self.server_address[:2]
        self.server_name = host
        self.server_port = port


def read_json(path):
    """Load a JSON file. Errors propagate; do_GET turns them into a 500 with a reason."""
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def read_jsonl(path):
    """Load a JSON-lines file. A bad line becomes an error row, so one broken line in the
    action log does not hide the rest of the audit trail."""
    rows = []
    with open(path, encoding="utf-8") as handle:
        for number, line in enumerate(handle, 1):
            text = line.strip()
            if not text:
                continue
            try:
                rows.append(json.loads(text))
            except json.JSONDecodeError:
                rows.append({"error": "invalid json", "line": number, "text": text})
    return rows


# Built once and cached; loading the graph reads about 17,000 CSV rows.
def ontology_payload():
    """Record counts and relationship chains for the header panel, cached after the first call."""
    global _ontology
    # Double-checked locking: the server is threaded, and two first requests must not both load
    # the graph.
    if _ontology is not None:
        return _ontology
    with _ontology_lock:
        if _ontology is None:
            from tower.graph import WorldGraph

            _ontology = {
                "counts": WorldGraph().counts(),
                "relationships": list(RELATIONSHIPS),
            }
        return _ontology


def ontology_export():
    """The exported ontology from runs/ontology/, or a fresh build if it has not been exported."""
    if os.path.isfile(ONTOLOGY_JSON):
        return read_json(ONTOLOGY_JSON)
    from tower.ontology import build

    return build()


def knowledge_payload(query):
    """Orb-graph data for ?view=network|schema|event. An event reads the tower run's traces, or a
    test report's with run=<suite>/<reader>."""
    from tower.ui import knowledge

    view = (query.get("view") or ["network"])[0]
    if view == "schema":
        return knowledge.schema(ontology_export())
    if view == "event":
        event_id = (query.get("event") or [""])[0]
        traces = TRACES
        run = (query.get("run") or [""])[0]
        if run:
            suite, _, reader = run.partition("/")
            parent = os.path.join(HITACHI, "runs", SUITE_RUNS.get(suite, ""))
            if suite not in SUITE_RUNS or not os.path.isdir(parent) or reader not in os.listdir(parent):
                raise NotFound(f"no test run {run}")
            traces = os.path.join(parent, reader, "traces.json")
        return knowledge.event(traces, event_id)
    return knowledge.network()


LOG_DIR = os.path.join(HITACHI, "runs", "logs")


def logs_payload(name: str | None):
    """The saved start.py outputs (runs/logs/*.log), newest first; with name, that file's text."""
    files = sorted((f for f in os.listdir(LOG_DIR) if f.endswith(".log")), reverse=True) if os.path.isdir(LOG_DIR) else []
    if name:
        if name not in files:
            raise NotFound(name)
        with open(os.path.join(LOG_DIR, name), encoding="utf-8", errors="replace") as handle:
            return {"name": name, "text": handle.read()[-400_000:]}
    return [{"name": f, "size": os.path.getsize(os.path.join(LOG_DIR, f)),
             "updated": time.strftime("%Y-%m-%d %H:%M", time.localtime(os.path.getmtime(os.path.join(LOG_DIR, f))))}
            for f in files]


def revision_payload():
    """Changes when the run files or any saved test result change. Stat calls only, no report build."""
    from tower.ui import reports

    from tower.ui import event_desk

    stamps = [reports.revision()]
    for path in (TRACES, LOG, OUTBOX, EVENTS, ONTOLOGY_JSON, *event_desk.stamp_paths()):
        if os.path.isfile(path):
            st = os.stat(path)
            stamps.append(f"{os.path.basename(path)}:{st.st_mtime_ns}:{st.st_size}")
    return {"rev": "|".join(stamps)}


def channels_payload():
    """Which channel sources, sinks and routes are configured. Names and kinds only, never secrets."""
    from tower.channels.config import ChannelConfig

    cfg = ChannelConfig.load()
    return {
        "configured": cfg.path is not None,
        "sources": {name: c.get("kind") for name, c in cfg.sources.items()},
        "sinks": {name: c.get("kind") for name, c in cfg.sinks.items()},
        "routes": {name: r["sinks"] for name, r in cfg.routes.items()},
    }


# Read-only JSON API over the run output. dashboard.html fetches these endpoints and renders the event
# feed, graph paths, actions and audit trail.
class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        """Route a GET. Missing run files return [] (the tower has not run yet), not an error."""
        # Ignore any query string, and treat "/api/log/" the same as "/api/log".
        split = urllib.parse.urlsplit(self.path)
        path = split.path
        query = urllib.parse.parse_qs(split.query)
        if path != "/":
            path = path.rstrip("/") or "/"
        try:
            if path == "/":
                built = os.path.join(DIST, "index.html")
                return self._file(built if os.path.isfile(built) else DASHBOARD, "text/html; charset=utf-8")
            if split.path.startswith("/assets/"):
                return self._static(os.path.join(DIST, "assets"), urllib.parse.unquote(split.path[len("/assets/"):]))
            if split.path == "/orb":
                return self._redirect("/orb/")
            if split.path.startswith("/orb/"):
                return self._static(ORB_ROOT, urllib.parse.unquote(split.path[len("/orb/"):]) or "index.html")
            if path == "/api/events":
                from tower.ui import event_desk

                official = read_json(EVENTS)
                extra = event_desk.saved_events()
                have = {e.get("event_id") for e in official if isinstance(e, dict)}
                return self._json(official + [e for e in extra if e.get("event_id") not in have])
            if path == "/api/ontology":
                return self._json(ontology_payload())
            if path == "/api/traces":
                from tower.ui import event_desk

                base = read_json(TRACES) if os.path.isfile(TRACES) else []
                have = {t.get("event_id") for t in base if isinstance(t, dict)}
                return self._json(base + [t for t in event_desk.saved_traces() if t.get("event_id") not in have])
            if path == "/api/log":
                from tower.ui import event_desk

                base = read_jsonl(LOG) if os.path.isfile(LOG) else []
                return self._json(base + event_desk.saved_log())
            if path == "/api/outbox":
                return self._json(read_jsonl(OUTBOX) if os.path.isfile(OUTBOX) else [])
            if path == "/api/channels":
                return self._json(channels_payload())
            if path == "/api/ontology_export":
                return self._json(ontology_export())
            if split.path.startswith("/runs/") and split.path.endswith(".md"):
                return self._static(os.path.join(HITACHI, "runs"), urllib.parse.unquote(split.path[len("/runs/"):]))
            if path == "/api/logs":
                return self._json(logs_payload((query.get("name") or [None])[0]))
            if path == "/api/domains":
                from tower.domains import payload as domain_payload

                return self._json(domain_payload())
            if path == "/api/ontology.mmd":
                return self._file(ONTOLOGY_MMD, "text/plain; charset=utf-8")
            if path == "/api/agents":
                from tower.agents.roster import roster

                return self._json(roster())
            if path == "/api/knowledge_graph":
                return self._json(knowledge_payload(query))
            if path == "/api/test_reports":
                from tower.ui import reports

                return self._json(reports.payload())
            if path == "/api/revision":
                return self._json(revision_payload())
            if path == "/api/events/chat":
                from tower.ui import event_desk

                return self._json({"messages": event_desk.messages()})
            if path == "/api/events/run":
                from tower.ui import event_desk

                return self._json(event_desk.status())
            if path == "/api/events/run/stream":
                return self._stream_events()
            if path == "/api/run":
                from tower.ui import runner

                return self._json(runner.status())
            if path == "/api/run/stream":
                return self._stream_run()
        except NotFound as exc:
            return self._json({"error": "not found", "detail": str(exc)}, 404)
        except FileNotFoundError as exc:
            return self._json({"error": "missing file", "detail": str(exc)}, 500)
        except json.JSONDecodeError as exc:
            return self._json({"error": "invalid json", "detail": str(exc)}, 500)
        except OSError as exc:
            return self._json({"error": "read failed", "detail": str(exc)}, 500)
        except UnicodeError as exc:
            return self._json({"error": "bad encoding", "detail": str(exc)}, 500)
        self._json({"error": "not found"}, 404)

    def _local(self) -> bool:
        """True when the browser asked this process by name. Blocks a DNS-rebinding page."""
        host = (self.headers.get("Host") or "").split(":")[0]
        return host in ("127.0.0.1", "localhost")

    def do_POST(self):
        """POST starts a test grade, an event run, or one chat event. Same-host only."""
        if not self._local():
            return self._json({"error": "forbidden"}, 403)
        path = urllib.parse.urlsplit(self.path).path.rstrip("/") or "/"
        allowed = ("/api/run", "/api/run/stop", "/api/events/run", "/api/events/run/stop", "/api/events/chat")
        if path not in allowed:
            return self._json({"error": "not found"}, 404)
        from tower.ui import event_desk, runner

        if path == "/api/run/stop":
            return self._json(runner.stop())
        if path == "/api/events/run/stop":
            return self._json(event_desk.stop())
        try:
            length = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            return self._json({"error": "bad request"}, 400)
        if length > 8000:
            return self._json({"error": "bad request"}, 400)
        raw = self.rfile.read(length) if length else b"{}"
        try:
            body = json.loads(raw.decode("utf-8") or "{}")
        except (UnicodeDecodeError, json.JSONDecodeError):
            return self._json({"error": "invalid json"}, 400)
        if not isinstance(body, dict):
            return self._json({"error": "invalid json"}, 400)
        if path == "/api/events/chat":
            return self._add_event(body)
        if path == "/api/events/run":
            result = event_desk.start()
            if result.get("error"):
                return self._json(result, 409)
            return self._json(result)
        try:
            result = runner.start(body.get("reader") or "rules", body.get("suites"))
        except ValueError as exc:
            return self._json({"error": str(exc)}, 400)
        except OSError as exc:
            return self._json({"error": "could not start", "detail": str(exc)}, 500)
        if result.get("error"):
            return self._json(result, 409)
        return self._json(result)

    def do_DELETE(self):
        """DELETE /api/test_reports/<suite>/<reader> removes that report's folder under runs/.

        Only same-host requests are accepted: the Host header must be this server, which blocks
        DNS-rebinding pages, and browsers will not send a cross-site DELETE without a CORS
        preflight, which this server never answers.
        """
        if not self._local():
            return self._json({"error": "forbidden"}, 403)
        parts = [urllib.parse.unquote(p) for p in urllib.parse.urlsplit(self.path).path.strip("/").split("/")]
        if len(parts) != 4 or parts[:2] != ["api", "test_reports"]:
            return self._json({"error": "not found"}, 404)
        from tower.ui import reports

        try:
            removed = reports.delete(parts[2], parts[3])
        except OSError as exc:
            return self._json({"error": "delete failed", "detail": str(exc)}, 500)
        if not removed:
            return self._json({"error": "no such report"}, 404)
        return self._json({"deleted": f"{parts[2]}/{parts[3]}"})

    def _add_event(self, body: dict):
        """Read one chat message and keep it as an event. The 15 given events are not rewritten."""
        from tower.ui import event_desk

        try:
            saved = event_desk.add_message(body.get("text"))
        except ValueError as exc:
            return self._json({"error": str(exc)}, 400)
        except OSError as exc:
            return self._json({"error": "could not save", "detail": str(exc)}, 500)
        return self._json(saved)

    def _stream(self, follow):
        """Server-sent events. One chunk per update, plus a snapshot on connect."""
        self.protocol_version = "HTTP/1.1"
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Connection", "close")
        self.send_header("Transfer-Encoding", "chunked")
        self.end_headers()

        def send(event: str, data: dict) -> None:
            raw = f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n".encode("utf-8")
            self.wfile.write(f"{len(raw):x}\r\n".encode("ascii") + raw + b"\r\n")
            self.wfile.flush()

        try:
            for event, data in follow():
                send(event, data)
        except (BrokenPipeError, ConnectionAbortedError, ConnectionResetError, TimeoutError, OSError):
            return
        except Exception as exc:  # noqa: BLE001 - keep one dropped client from taking down the server
            print(f"event stream ended: {exc}", file=sys.stderr, flush=True)
            return
        finally:
            self.close_connection = True

    def _stream_events(self):
        from tower.ui import event_desk

        return self._stream(event_desk.follow)

    def _stream_run(self):
        """Server-sent events for the live grade. One event per case, plus a snapshot on connect."""
        from tower.ui import runner

        return self._stream(runner.follow)

    def _static(self, root, rel):
        """Serve a file under root; anything that resolves outside it is a 404."""
        root = os.path.realpath(root)
        full = os.path.realpath(os.path.join(root, rel))
        if not full.startswith(root + os.sep) or not os.path.isfile(full):
            return self._json({"error": "not found"}, 404)
        ext = os.path.splitext(full)[1].lower()
        return self._file(full, STATIC_TYPES.get(ext, "application/octet-stream"))

    def _redirect(self, location):
        self.send_response(301)
        self.send_header("Location", location)
        self.send_header("Content-Length", "0")
        self.end_headers()

    def _file(self, path, content_type):
        """Serve a static file. no-store, so Refresh always shows the latest run."""
        with open(path, "rb") as handle:
            body = handle.read()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _json(self, payload, code=200):
        """Send a JSON response. ensure_ascii=False keeps names and dashes readable."""
        try:
            body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        except UnicodeEncodeError:
            body = json.dumps(payload).encode("ascii")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt, *args):
        """Silence the per-request access log; each page load makes several API calls."""
        return


def main():
    """Serve until Ctrl-C. Bound to 127.0.0.1 only: the page is for this laptop.

    The Electron shell (desktop/) passes --port so it can open the window on a free port.
    """
    import argparse

    ap = argparse.ArgumentParser(description="Serve the control tower dashboard on 127.0.0.1.")
    ap.add_argument("--port", type=int, default=PORT, help="port (default 8080)")
    cli = ap.parse_args()
    try:
        server = TowerServer((HOST, cli.port), Handler)
    except OSError as exc:
        print(f"could not bind {HOST}:{cli.port}: {exc}", file=sys.stderr, flush=True)
        raise SystemExit(1) from exc
    print(f"http://{HOST}:{server.server_port}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        try:
            from tower.ui import event_desk, runner

            runner.stop()
            event_desk.stop()
        except Exception:  # noqa: BLE001 - shutting down anyway
            pass
        server.server_close()


if __name__ == "__main__":
    main()
