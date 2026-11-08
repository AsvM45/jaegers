"""Wacky Wheels control tower page. Standard library only.

From the Hitachi directory:

    python -m tower.ui.server
    python tower/ui/server.py

Listens on http://127.0.0.1:8080

    GET /
    GET /api/events
    GET /api/ontology
    GET /api/traces
    GET /api/log
    GET /api/outbox     messages dispatched to Slack, Teams, Gmail, Outlook... for the run
    GET /api/channels   which channels are configured (names and kinds only, never secrets)
"""

from __future__ import annotations

import json
import os
import sys
import threading
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

HERE = os.path.dirname(os.path.abspath(__file__))
HITACHI = os.path.abspath(os.path.join(HERE, "..", ".."))
if HITACHI not in sys.path:
    sys.path.insert(0, HITACHI)

INDEX = os.path.join(HERE, "index.html")
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


# Read-only JSON API over the run output. index.html fetches these endpoints and renders the event
# feed, graph paths, actions and audit trail.
class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        """Route a GET. Missing run files return [] (the tower has not run yet), not an error."""
        # Ignore any query string, and treat "/api/log/" the same as "/api/log".
        path = urllib.parse.urlsplit(self.path).path
        if path != "/":
            path = path.rstrip("/") or "/"
        try:
            if path == "/":
                return self._file(INDEX, "text/html; charset=utf-8")
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
        except FileNotFoundError as exc:
            return self._json({"error": "missing file", "detail": str(exc)}, 500)
        except json.JSONDecodeError as exc:
            return self._json({"error": "invalid json", "detail": str(exc)}, 500)
        except OSError as exc:
            return self._json({"error": "read failed", "detail": str(exc)}, 500)
        self._json({"error": "not found"}, 404)

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
