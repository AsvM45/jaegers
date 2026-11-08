"""Wacky Wheels control tower page. Standard library only.

From the Hitachi directory:

    python -m tower.ui.server
    python tower/ui/server.py

Listens on http://127.0.0.1:8080

    GET /                     the dashboard (dashboard.html)
    GET /api/events
    GET /api/ontology
    GET /api/traces
    GET /api/log
    GET /api/outbox     messages dispatched to Slack, Teams, Gmail, Outlook... for the run
    GET /api/channels   which channels are configured (names and kinds only, never secrets)
    GET /api/ontology_export   node and edge types for the ontology diagram
    GET /runs/<...>.md         a Markdown report the test runs wrote (download from the Tests page)
    GET /api/logs[?name=...]   saved start.py output (runs/logs/), list or one file
    GET /api/agents            the coordinator and the three specialist agents (role, tools, rules)
    GET /api/test_reports      expected vs actual outcome for every test case, per reader
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
ONTOLOGY_JSON = os.path.join(HITACHI, "runs", "ontology", "ontology.json")
ORB_ROOT = os.path.join(HITACHI, "orb-graph", "public")
STATIC_TYPES = {
    ".html": "text/html; charset=utf-8", ".js": "text/javascript; charset=utf-8",
    ".css": "text/css; charset=utf-8", ".json": "application/json", ".svg": "image/svg+xml",
    ".png": "image/png", ".md": "text/markdown; charset=utf-8",
}
# Test-suite run folders the knowledge graph may read traces from (suite id -> runs/ subfolder).
SUITE_RUNS = {"given": "given", "generated": "tests", "holdout": "holdout", "holdout2": "holdout2"}
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


class TowerServer(ThreadingHTTPServer):
    """Bind without a reverse-DNS lookup, which can stall on some networks."""

    def server_bind(self):
        # Set what TCPServer.server_bind would have, so a restart can rebind a port in TIME_WAIT.
        if self.allow_reuse_address:
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.bind(self.server_address)
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
                raise FileNotFoundError(f"no test run {run}")
            traces = os.path.join(parent, reader, "traces.json")
        return knowledge.event(traces, event_id)
    return knowledge.network()


LOG_DIR = os.path.join(HITACHI, "runs", "logs")


def logs_payload(name: str | None):
    """The saved start.py outputs (runs/logs/*.log), newest first; with name, that file's text."""
    files = sorted((f for f in os.listdir(LOG_DIR) if f.endswith(".log")), reverse=True) if os.path.isdir(LOG_DIR) else []
    if name:
        if name not in files:
            raise FileNotFoundError(name)
        with open(os.path.join(LOG_DIR, name), encoding="utf-8", errors="replace") as handle:
            return {"name": name, "text": handle.read()[-400_000:]}
    return [{"name": f, "size": os.path.getsize(os.path.join(LOG_DIR, f)),
             "updated": time.strftime("%Y-%m-%d %H:%M", time.localtime(os.path.getmtime(os.path.join(LOG_DIR, f))))}
            for f in files]


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
                return self._file(DASHBOARD, "text/html; charset=utf-8")
            if split.path == "/orb":
                return self._redirect("/orb/")
            if split.path.startswith("/orb/"):
                return self._static(ORB_ROOT, urllib.parse.unquote(split.path[len("/orb/"):]) or "index.html")
            if path == "/api/events":
                return self._json(read_json(EVENTS))
            if path == "/api/ontology":
                return self._json(ontology_payload())
            if path == "/api/traces":
                return self._json(read_json(TRACES) if os.path.isfile(TRACES) else [])
            if path == "/api/log":
                return self._json(read_jsonl(LOG) if os.path.isfile(LOG) else [])
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
            if path == "/api/agents":
                from tower.agents.roster import roster

                return self._json(roster())
            if path == "/api/knowledge_graph":
                return self._json(knowledge_payload(query))
            if path == "/api/test_reports":
                from tower.ui import reports

                return self._json(reports.payload())
        except FileNotFoundError as exc:
            return self._json({"error": "missing file", "detail": str(exc)}, 500)
        except json.JSONDecodeError as exc:
            return self._json({"error": "invalid json", "detail": str(exc)}, 500)
        except OSError as exc:
            return self._json({"error": "read failed", "detail": str(exc)}, 500)
        self._json({"error": "not found"}, 404)

    def do_DELETE(self):
        """DELETE /api/test_reports/<suite>/<reader> removes that report's folder under runs/.

        Only same-host requests are accepted: the Host header must be this server, which blocks
        DNS-rebinding pages, and browsers will not send a cross-site DELETE without a CORS
        preflight, which this server never answers.
        """
        host = (self.headers.get("Host") or "").split(":")[0]
        if host not in ("127.0.0.1", "localhost"):
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
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
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
    """Serve until Ctrl-C. Bound to 127.0.0.1 only: the page is for this laptop."""
    server = TowerServer((HOST, PORT), Handler)
    print(f"http://{HOST}:{PORT}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
