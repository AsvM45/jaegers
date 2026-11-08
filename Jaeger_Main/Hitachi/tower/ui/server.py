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
    GET /api/domains
    GET /api/ontology.mmd
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

from tower.domains import payload as domain_payload

INDEX = os.path.join(HERE, "index.html")
ONTOLOGY_MMD = os.path.join(HERE, "..", "ontology.mmd")
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
_ontology_bytes = None
_ontology_lock = threading.Lock()
_file_cache: dict[str, tuple[tuple[int, int], bytes]] = {}
_file_cache_lock = threading.Lock()


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


def cached_bytes(path: str, encode) -> bytes | None:
    """Encoded file bytes. A new mtime or size rebuilds them."""
    try:
        stat = os.stat(path)
    except OSError:
        return None
    token = (stat.st_mtime_ns, stat.st_size)
    with _file_cache_lock:
        hit = _file_cache.get(path)
        if hit is not None and hit[0] == token:
            return hit[1]
    body = encode(path)
    with _file_cache_lock:
        _file_cache[path] = (token, body)
    return body


def json_file_bytes(path: str, reader) -> bytes:
    body = cached_bytes(path, lambda name: json.dumps(reader(name), ensure_ascii=False).encode("utf-8"))
    if body is None:
        raise FileNotFoundError(path)
    return body


def ontology_payload():
    global _ontology
    if _ontology is not None:
        return _ontology
    with _ontology_lock:
        if _ontology is None:
            from tower.graph import WorldGraph

            graph = WorldGraph()
            export = graph.ontology_export()
            _ontology = {
                "counts": export["counts"],
                "relationships": list(RELATIONSHIPS),
                "nodes": export["nodes"],
                "edges": export["edges"],
                "chains": export["chains"],
            }
        return _ontology


def ontology_bytes() -> bytes:
    global _ontology_bytes
    if _ontology_bytes is not None:
        return _ontology_bytes
    with _ontology_lock:
        if _ontology_bytes is None:
            _ontology_bytes = json.dumps(ontology_payload(), ensure_ascii=False).encode("utf-8")
        return _ontology_bytes


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        path = urllib.parse.urlsplit(self.path).path
        if path != "/":
            path = path.rstrip("/") or "/"
        try:
            if path == "/":
                page = cached_bytes(INDEX, lambda name: open(name, "rb").read())
                if page is None:
                    raise FileNotFoundError(INDEX)
                return self._bytes(page, "text/html; charset=utf-8")
            if path == "/api/events":
                return self._bytes(json_file_bytes(EVENTS, read_json), "application/json; charset=utf-8")
            if path == "/api/ontology":
                return self._bytes(ontology_bytes(), "application/json; charset=utf-8")
            if path == "/api/traces":
                return self._bytes(json_file_bytes(TRACES, read_json), "application/json; charset=utf-8")
            if path == "/api/log":
                return self._bytes(json_file_bytes(LOG, read_jsonl), "application/json; charset=utf-8")
            if path == "/api/domains":
                return self._json(domain_payload())
            if path == "/api/ontology.mmd":
                body = cached_bytes(ONTOLOGY_MMD, lambda name: open(name, "rb").read())
                if body is None:
                    raise FileNotFoundError(ONTOLOGY_MMD)
                return self._bytes(body, "text/plain; charset=utf-8")
        except FileNotFoundError as exc:
            return self._json({"error": "missing file", "detail": str(exc)}, 500)
        except json.JSONDecodeError as exc:
            return self._json({"error": "invalid json", "detail": str(exc)}, 500)
        except OSError as exc:
            return self._json({"error": "read failed", "detail": str(exc)}, 500)
        self._json({"error": "not found"}, 404)

    def _bytes(self, body: bytes, content_type: str, code: int = 200):
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _json(self, payload, code=200):
        self._bytes(
            json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            "application/json; charset=utf-8",
            code,
        )

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
