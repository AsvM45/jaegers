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
    GET /api/promise           customer promise impact: moved builds against each customer's promised date
    GET /api/network_map       plants, suppliers and dealers with their locations, for the Overview map
    GET /api/test_reports      expected vs actual outcome for every test case, per reader
    GET /api/records           the company tables visitors can read (tower/ui/records.py)
    GET /api/records/<table>?q=&offset=&limit=   one page of a table, searched
    GET /api/revision          a token that changes when the run or the saved results change
    GET /api/events/chat       the event-add transcript
    POST /api/events/chat      read one chat message and add it to the feed
    GET /api/events/run        the event run in progress (or the last one)
    GET /api/events/run/stream the same run as a server-sent event stream
    POST /api/events/run       walk the feed and report each event as it finishes
    POST /api/events/run/stop  stop that walk
    GET /api/reset             whether each kind (events, tests) has data and a reset that Undo can restore
    POST /api/reset            {"kind":"events"|"tests","confirm":"RESET"}: back the data up to runs/.reset/, then clear it
    POST /api/reset/undo       {"kind":...}: put the newest reset backup back
    GET /api/summary.pdf       the test summary as a PDF (tower/ui/summary_pdf.py), downloaded from the Tests page
    GET /api/voice[?lang=en]   whether local voice input (whisper.cpp) is ready, or how to set it up
    POST /api/voice/transcribe?lang=en   a WAV recording -> {"text": ...}, transcribed on this machine
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
import re
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
    ".html": "text/html; charset=utf-8", ".js": "text/javascript; charset=utf-8", ".mjs": "text/javascript; charset=utf-8",
    ".css": "text/css; charset=utf-8", ".json": "application/json", ".svg": "image/svg+xml",
    ".png": "image/png", ".ico": "image/x-icon", ".woff2": "font/woff2", ".md": "text/markdown; charset=utf-8",
}
EVENTS = os.path.join(HITACHI, "Data", "hack_the_highway_package", "data", "events.json")
# TOWER_RUN_DIR=runs/live shows the live channel feed instead of the batch run.
RUN_DIR = os.path.join(HITACHI, os.environ.get("TOWER_RUN_DIR", os.path.join("runs", "run1")))
TRACES = os.path.join(RUN_DIR, "traces.json")
LOG = os.path.join(RUN_DIR, "action_log.jsonl")
OUTBOX = os.path.join(RUN_DIR, "outbox.jsonl")
if os.path.isfile(os.path.join(RUN_DIR, "events.json")):
    EVENTS = os.path.join(RUN_DIR, "events.json")
# On this laptop: 127.0.0.1:8080. Deployed (Hugging Face Spaces, Render): TOWER_HOST=0.0.0.0 and the
# host's PORT. TOWER_PUBLIC=1 accepts actions from the public address (the password guards them instead),
# and TOWER_PASSWORD, when set, asks every visitor for it (any user name).
HOST = os.environ.get("TOWER_HOST", "127.0.0.1")
PORT = int(os.environ.get("PORT", "8080"))
PUBLIC = os.environ.get("TOWER_PUBLIC", "") == "1"
PASSWORD = os.environ.get("TOWER_PASSWORD", "")

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

    # Python's default backlog is 5 pending connections. A page that opens several graphs at once asks for
    # dozens of files together; past 5 the OS drops the connection and the browser retries 1, 3, 7 s later,
    # so a graph could take 20 s or never load. 128 keeps every request moving.
    request_queue_size = 128
    daemon_threads = True

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


def knowledge_payload(query, desk):
    """Orb-graph data for ?view=network|schema|event. An event reads the tower run's traces, or a
    test report's with run=<suite>/<reader>."""
    from tower.ui import knowledge

    view = (query.get("view") or ["network"])[0]
    if view == "schema":
        return knowledge.schema(ontology_export())
    if view == "event":
        event_id = (query.get("event") or [""])[0]
        traces = desk.feed_traces
        run = (query.get("run") or [""])[0]
        if run:
            from tower.ui import reports

            suite, _, reader = run.partition("/")
            known = {s["id"]: s["runs"] for s in reports.SUITES}
            parent = os.path.join(desk.tests_dir, known.get(suite, ""))
            if suite not in known or not os.path.isdir(parent) or reader not in os.listdir(parent):
                raise NotFound(f"no test run {run}")
            traces = os.path.join(parent, reader, "traces.json")
        if run:
            return knowledge.event(traces, event_id)
        return knowledge.event(traces, event_id, desk.saved_traces())
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


def revision_payload(desk):
    """Changes when the run files or any saved test result change. Stat calls only, no report build."""
    from tower.ui import reports

    stamps = [reports.revision(desk.tests_dir)]
    for path in (desk.feed_traces, desk.feed_log, desk.feed_outbox, EVENTS, ONTOLOGY_JSON, *desk.stamp_paths()):
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
WS_COOKIE = "tower_ws"
_WS_ID = re.compile(r"^[A-Za-z0-9_-]{16,64}$")


class Handler(BaseHTTPRequestHandler):
    _new_ws: str | None = None

    def _desk(self, write: bool = False):
        """This visitor's event desk. Online (TOWER_WORKSPACES=1) each browser has its own workspace,
        named by a random id in a cookie the server sets on the first visit; on a laptop, the one desk.
        A first visit (no cookie yet) reads the shared demo data; the workspace is made on disk the
        first time the visitor's browser comes back with the cookie, or changes something."""
        from tower.ui import event_desk

        if not event_desk.WORKSPACES:
            return event_desk.DEFAULT
        wid = None
        for part in (self.headers.get("Cookie") or "").split(";"):
            name, _, value = part.strip().partition("=")
            if name == WS_COOKIE and _WS_ID.match(value):
                wid = value
        if wid is None:
            import secrets

            wid = self._new_ws or secrets.token_urlsafe(18)
            self._new_ws = wid
            if not write:
                return event_desk.BLANK
        return event_desk.get(wid)

    def end_headers(self):
        if self._new_ws:
            # Online, Hugging Face shows the app in a frame on huggingface.co, another site: a Lax cookie
            # is never sent there, so each action would start a new, empty workspace. SameSite=None
            # lets the frame keep it; Partitioned keeps it working where third-party cookies are blocked
            # (it is kept for this site-in-that-site only). The cookie only names a sandbox workspace.
            same_site = "None; Secure; Partitioned" if PUBLIC else "Lax"
            self.send_header("Set-Cookie", f"{WS_COOKIE}={self._new_ws}; Path=/; Max-Age=2592000; HttpOnly; SameSite={same_site}")
        super().end_headers()

    def _allowed(self) -> bool:
        """With TOWER_PASSWORD set, every request needs it (HTTP Basic, any user name). The health
        check stays open so the host can tell the server is up. Sends the 401 itself."""
        if not PASSWORD or urllib.parse.urlsplit(self.path).path == "/healthz":
            return True
        import base64
        import hmac

        header = self.headers.get("Authorization") or ""
        if header.startswith("Basic "):
            try:
                given = base64.b64decode(header[6:]).decode("utf-8", "replace").split(":", 1)[-1]
            except ValueError:
                given = ""
            if hmac.compare_digest(given.encode(), PASSWORD.encode()):
                return True
        body = b"Password required"
        self.send_response(401)
        self.send_header("WWW-Authenticate", 'Basic realm="Control Tower", charset="UTF-8"')
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)
        return False

    def do_GET(self):
        """Route a GET. Missing run files return [] (the tower has not run yet), not an error."""
        if not self._allowed():
            return
        if urllib.parse.urlsplit(self.path).path == "/healthz":
            return self._json({"ok": True})
        # Ignore any query string, and treat "/api/log/" the same as "/api/log".
        split = urllib.parse.urlsplit(self.path)
        path = split.path
        query = urllib.parse.parse_qs(split.query)
        if path != "/":
            path = path.rstrip("/") or "/"
        desk = self._desk()
        try:
            if path == "/api/mode":
                from tower.ui import event_desk

                # Online, each visitor has a workspace of their own: events and test runs.
                return self._json({"workspaces": event_desk.WORKSPACES, "demo": sorted(event_desk.DEMO_EVENTS)})
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

                official = [e for e in read_json(EVENTS) if not isinstance(e, dict) or event_desk.shown(e.get("event_id", ""))]
                extra = desk.saved_events()
                have = {e.get("event_id") for e in official if isinstance(e, dict)}
                return self._json(official + [e for e in extra if e.get("event_id") not in have])
            if path == "/api/ontology":
                return self._json(ontology_payload())
            if path == "/api/traces":
                base = read_json(desk.feed_traces) if os.path.isfile(desk.feed_traces) else []
                have = {t.get("event_id") for t in base if isinstance(t, dict)}
                return self._json(base + [t for t in desk.saved_traces() if t.get("event_id") not in have])
            if path == "/api/log":
                base = read_jsonl(desk.feed_log) if os.path.isfile(desk.feed_log) else []
                return self._json(base + desk.saved_log())
            if path == "/api/network_map":
                from tower.ui import geo

                return self._json(geo.payload())
            if path == "/api/promise":
                from tower.ui import promise

                base = read_jsonl(desk.feed_log) if os.path.isfile(desk.feed_log) else []
                return self._json(promise.payload(base + desk.saved_log()))
            if path == "/api/outbox":
                return self._json(read_jsonl(desk.feed_outbox) if os.path.isfile(desk.feed_outbox) else [])
            if path == "/api/channels":
                return self._json(channels_payload())
            if path == "/api/ontology_export":
                return self._json(ontology_export())
            if split.path.startswith("/runs/") and split.path.endswith(".md"):
                return self._static(desk.tests_dir, urllib.parse.unquote(split.path[len("/runs/"):]))
            if path == "/api/logs":
                from tower.ui import event_desk

                # The saved start.py outputs are this laptop's; online there are none.
                name = (query.get("name") or [None])[0]
                if event_desk.WORKSPACES:
                    if name:
                        raise NotFound(name)
                    return self._json([])
                return self._json(logs_payload(name))
            if path == "/api/domains":
                from tower.domains import payload as domain_payload

                return self._json(domain_payload())
            if path == "/api/ontology.mmd":
                return self._file(ONTOLOGY_MMD, "text/plain; charset=utf-8")
            if path == "/api/reset":
                from tower.ui import reset

                return self._json(reset.status(desk))
            if path == "/api/summary.pdf":
                from tower.ui import summary_pdf

                from tower.ui import reports

                body = summary_pdf.build(reports.payload(desk.tests_dir))
                self.send_response(200)
                self.send_header("Content-Type", "application/pdf")
                self.send_header("Content-Disposition", f'attachment; filename="{summary_pdf.filename()}"')
                self.send_header("Content-Length", str(len(body)))
                self.send_header("Cache-Control", "no-store")
                self.end_headers()
                self.wfile.write(body)
                return None
            if path == "/api/voice":
                from tower import voice

                return self._json(voice.status((query.get("lang") or ["en"])[0]))
            if path == "/api/agents":
                from tower.agents.roster import roster

                return self._json(roster())
            if path == "/api/records" or path.startswith("/api/records/"):
                from tower.ui import records

                if path == "/api/records":
                    return self._json(records.tables())
                def num(name, default):
                    try:
                        return int((query.get(name) or [default])[0])
                    except ValueError:
                        return default
                try:
                    return self._json(records.page(urllib.parse.unquote(path[len("/api/records/"):]),
                                                   (query.get("q") or [""])[0], num("offset", 0), num("limit", 25)))
                except KeyError as exc:
                    raise NotFound(f"no table {exc}") from exc
            if path == "/api/knowledge_graph":
                return self._json(knowledge_payload(query, desk))
            if path == "/api/test_reports":
                from tower.ui import reports

                return self._json(reports.payload(desk.tests_dir))
            if path == "/api/revision":
                return self._json(revision_payload(desk))
            if path == "/api/events/chat":
                return self._json({"messages": desk.messages()})
            if path == "/api/events/run":
                return self._json(desk.status())
            if path == "/api/events/run/stream":
                return self._stream_events()
            if path == "/api/run":
                from tower.ui import runner

                return self._json(runner.status(desk.tests_dir))
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
        """True when the browser asked this process by name. Blocks a DNS-rebinding page.
        Deployed (TOWER_PUBLIC=1) the public address is the name, so actions come from anywhere and
        the password guards them."""
        if PUBLIC:
            return True
        host = (self.headers.get("Host") or "").split(":")[0]
        return host in ("127.0.0.1", "localhost")

    def do_POST(self):
        """POST starts a test grade, an event run, or one chat event. Same-host only."""
        if not self._allowed():
            return
        if not self._local():
            return self._json({"error": "forbidden"}, 403)
        path = urllib.parse.urlsplit(self.path).path.rstrip("/") or "/"
        allowed = ("/api/run", "/api/run/stop", "/api/events/run", "/api/events/run/stop", "/api/events/chat",
                   "/api/voice/transcribe", "/api/reset", "/api/reset/undo")
        if path not in allowed:
            return self._json({"error": "not found"}, 404)
        if path == "/api/voice/transcribe":
            return self._transcribe()
        from tower.ui import event_desk, runner

        desk = self._desk(write=True)
        if path == "/api/run/stop":
            return self._json(runner.stop(desk.tests_dir))
        if path == "/api/events/run/stop":
            return self._json(desk.stop())
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
        if path in ("/api/reset", "/api/reset/undo"):
            from tower.ui import reset

            kind = str(body.get("kind") or "")
            try:
                if path == "/api/reset":
                    return self._json(reset.reset(kind, str(body.get("confirm") or ""), desk))
                return self._json(reset.undo(kind, desk))
            except ValueError as exc:
                return self._json({"error": str(exc)}, 400)
            except OSError as exc:
                return self._json({"error": "could not move the files", "detail": str(exc)}, 500)
        if path == "/api/events/chat":
            return self._add_event(body, desk)
        if path == "/api/events/run":
            result = desk.start()
            if result.get("error"):
                return self._json(result, 409)
            return self._json(result)
        try:
            result = runner.start(body.get("reader") or "rules", body.get("suites"), desk.tests_dir)
        except ValueError as exc:
            return self._json({"error": str(exc)}, 400)
        except OSError as exc:
            return self._json({"error": "could not start", "detail": str(exc)}, 500)
        if result.get("error"):
            return self._json(result, 409)
        return self._json(result)

    def _transcribe(self):
        """POST /api/voice/transcribe?lang=en with a WAV body: {"text": ...} from local Whisper."""
        from tower import voice

        try:
            length = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            return self._json({"error": "bad request"}, 400)
        if not 0 < length <= voice.MAX_WAV:
            return self._json({"error": "the recording is empty or too long"}, 400)
        lang = (urllib.parse.parse_qs(urllib.parse.urlsplit(self.path).query).get("lang") or ["en"])[0]
        try:
            return self._json({"text": voice.transcribe(self.rfile.read(length), lang)})
        except ValueError as exc:
            return self._json({"error": str(exc)}, 400)
        except RuntimeError as exc:
            return self._json({"error": str(exc)}, 503)

    def do_DELETE(self):
        """DELETE /api/test_reports/<suite>/<reader> removes that report's folder under runs/.

        Only same-host requests are accepted: the Host header must be this server, which blocks
        DNS-rebinding pages, and browsers will not send a cross-site DELETE without a CORS
        preflight, which this server never answers.
        """
        if not self._allowed():
            return
        if not self._local():
            return self._json({"error": "forbidden"}, 403)
        from tower.ui import event_desk

        desk = self._desk(write=True)
        parts = [urllib.parse.unquote(p) for p in urllib.parse.urlsplit(self.path).path.strip("/").split("/")]
        if len(parts) != 4 or parts[:2] != ["api", "test_reports"]:
            return self._json({"error": "not found"}, 404)
        from tower.ui import reports

        try:
            removed = reports.delete(parts[2], parts[3], desk.tests_dir)
        except OSError as exc:
            return self._json({"error": "delete failed", "detail": str(exc)}, 500)
        if not removed:
            return self._json({"error": "no such report"}, 404)
        return self._json({"deleted": f"{parts[2]}/{parts[3]}"})

    def _add_event(self, body: dict, desk):
        """Read one chat message and keep it as an event. The 15 given events are not rewritten."""
        try:
            saved = desk.add_message(body.get("text"))
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
        return self._stream(self._desk().follow)

    def _stream_run(self):
        """Server-sent events for the live grade. One event per case, plus a snapshot on connect."""
        from tower.ui import runner

        root = self._desk().tests_dir
        return self._stream(lambda: runner.follow(root))

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
        """Serve a static file. no-store, so Refresh always shows the latest run, except the graph's
        3D library (orb-graph/public/vendor), which never changes: the browser keeps it, so each graph
        does not download it again."""
        with open(path, "rb") as handle:
            body = handle.read()
        vendor = os.sep + "vendor" + os.sep in path
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "public, max-age=86400, immutable" if vendor else "no-store")
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

    ap = argparse.ArgumentParser(description="Serve the control tower dashboard (127.0.0.1 unless TOWER_HOST says otherwise).")
    ap.add_argument("--port", type=int, default=PORT, help="port (default 8080, or $PORT)")
    ap.add_argument("--host", default=HOST, help="address to listen on (default 127.0.0.1, or $TOWER_HOST)")
    cli = ap.parse_args()
    try:
        server = TowerServer((cli.host, cli.port), Handler)
    except OSError as exc:
        print(f"could not bind {cli.host}:{cli.port}: {exc}", file=sys.stderr, flush=True)
        raise SystemExit(1) from exc
    print(f"http://{cli.host}:{server.server_port}" + ("  (password required)" if PASSWORD else ""), flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        try:
            from tower.ui import event_desk, runner

            runner.stop()
            event_desk.stop_all()
        except Exception:  # noqa: BLE001 - shutting down anyway
            pass
        server.server_close()


if __name__ == "__main__":
    main()
