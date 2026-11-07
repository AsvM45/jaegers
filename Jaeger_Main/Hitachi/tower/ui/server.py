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
TRACES = os.path.join(HITACHI, "runs", "run1", "traces.json")
LOG = os.path.join(HITACHI, "runs", "run1", "action_log.jsonl")
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
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def read_jsonl(path):
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


def ontology_payload():
    global _ontology
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


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
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
        except FileNotFoundError as exc:
            return self._json({"error": "missing file", "detail": str(exc)}, 500)
        except json.JSONDecodeError as exc:
            return self._json({"error": "invalid json", "detail": str(exc)}, 500)
        except OSError as exc:
            return self._json({"error": "read failed", "detail": str(exc)}, 500)
        self._json({"error": "not found"}, 404)

    def _file(self, path, content_type):
        with open(path, "rb") as handle:
            body = handle.read()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _json(self, payload, code=200):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt, *args):
        return


def main():
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
