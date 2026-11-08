# Control tower reliability

Probed with `runs/break/probe_reliability.py`. Real suite folders were not deleted. `runs/given`, `runs/holdout`, `runs/holdout2`, `runs/stress`, `runs/tests`, `runs/accuracy`, and `runs/run1` had the same directory listing at the end as at the start.

## Bugs

### 1. A control character inside a word drops a real outage

- **File:** `tower/agents/understand.py`
- **Function:** `_prepare` (called by `understand`, then `handle_event` in `tower/agents/coordinator.py`)
- **Severity:** high
- **What happens:** `_prepare` strips zero-width characters so they cannot hide a phrase, and it leaves NUL and other non-whitespace controls in place. A control byte in the middle of an operative word breaks the match. The section becomes `noise`, and the coordinator writes nothing.

Clean sentence, rule reader, fake enterprise (calls are accepted by the gateway, not executed against live data):

`Power failure at Jackson from 2027-03-16 through 2027-03-18. Production is stopped.`

Result: one `plant_outage`, then `mes.reschedule`, `dealer.notify`, and `crm.assign_loaner`.

Same sentence with U+0000 inside `failure` and `stopped` (`fail\x00ure`, `stop\x00ped`):

Result: `noise`, no tool calls.

Same sentence with U+0001 in those two words: `noise`, no tool calls.

A leading NUL, 20,000 NULs alone, an empty string, and 20,000 `x`s do not crash. Empty text and the long strings stay `noise` and write nothing. A trailing lone surrogate on the clean outage still classifies as `plant_outage`.

- **Fix:** In `_prepare`, delete non-whitespace controls (at least U+0000–U+0008, U+000E–U+001F, and U+007F) the same way `_ZERO_WIDTH` deletes zero-width characters, before the phrase scan. Keep tab, newline, and carriage return so list splitting still sees line breaks. The clean sentence is unchanged. The hidden sentence reads as the outage again.

### 2. A bad Unicode payload closes the HTTP request

- **File:** `tower/ui/server.py`
- **Functions:** `read_json`, `Handler.do_GET`, `Handler._json`
- **Severity:** medium
- **What happens:** `do_GET` turns `FileNotFoundError`, `json.JSONDecodeError`, and `OSError` into a JSON 500. `UnicodeDecodeError` and `UnicodeEncodeError` are not caught. The process stays up; that request never sends a response.

Invalid UTF-8 (`b"\xff\xfe..."`) pointed at by `EVENTS`, then `GET /api/events`: `read_json` raises `UnicodeDecodeError`. Over HTTP the client sees `RemoteDisconnected` (no status line). The server log is the traceback from `do_GET` line 219.

A traces file whose JSON contains the escape `\ud800`, then `GET /api/traces`: `json.load` succeeds and `Handler._json` raises `UnicodeEncodeError` on `json.dumps(..., ensure_ascii=False).encode("utf-8")`. Same dropped connection, traceback at `_json`.

A later `GET /no-such` still returns 404, so the process did not die.

- **Fix:** Catch `UnicodeError` in `do_GET` and return the same JSON 500 used for `OSError`. In `_json`, if `encode("utf-8")` raises `UnicodeEncodeError`, send `json.dumps(payload).encode("ascii")` so names stay readable for normal text and a lone surrogate is escaped instead of killing the response. Do not change incident classification.

### 3. The desktop navigation check allows other origins

- **File:** `desktop/main.js`
- **Function:** `allowUrl`
- **Severity:** medium
- **What happens:** `will-navigate` and `setWindowOpenHandler` allow a URL when it starts with `file:` or with `origin`. `origin` is `http://127.0.0.1:<port>` with no trailing delimiter. Node, running the function copied from this file with `origin = "http://127.0.0.1:8080"`, returned:

| URL | allowed |
| --- | --- |
| `http://127.0.0.1:8080/` and `http://127.0.0.1:8080/api/events` | yes |
| `http://127.0.0.1:80800/` | yes (different port) |
| `http://127.0.0.1:8080.example/` | yes |
| `http://127.0.0.1:8080@evil.example/` | yes |
| `file:///C:/Windows/win.ini` | yes |
| `https://evil.example/` | no |

- **Fix:** Parse with `new URL`. Allow `file:` only when the path is `boot.html`. Allow `http:` only when protocol, hostname, and port all equal `origin`. That still loads the boot page and the local dashboard.

### 4. Port 0 is advertised as port 0

- **File:** `tower/ui/server.py`
- **Function:** `TowerServer.server_bind` (`main` prints `cli.port`, which has the same problem)
- **Severity:** low
- **What happens:** `server_bind` binds the socket and then copies `self.server_address` without `getsockname()`. For `TowerServer(("127.0.0.1", 0), Handler)` the probe saw `server_address == ('127.0.0.1', 0)` and `server_port == 0`, while `getsockname()` was `('127.0.0.1', 56856)`. Connecting to the advertised port fails with `WinError 10049`. Connecting to the real port works. The desktop shell passes a concrete port from `freePort()`, so this does not break that launch path. `python -m tower.ui.server --port 0` prints `http://127.0.0.1:0`.

- **Fix:** After `bind`, set `self.server_address = self.socket.getsockname()` and print `server.server_port`.

## Guards that held

- **Empty text, whitespace, 20,000 `x`s, 20,000 NULs:** `understand` / `handle_event` return `noise` and make no tool calls. No crash. The 20,000-NUL case finished in under a second.
- **`reports.delete`:** `..`, absolute paths (`C:\Windows`, `\Windows\System32`), an empty reader, `.`, NUL, and a 20,000-character name return `False` for real suite ids. A junction inside a temporary suite whose target was outside that suite resolved outside the parent (`dirname` did not match), `delete` returned `False`, and the outside file was still there. Deleting a real child of that temporary suite still removed only that child. `DELETE /api/test_reports/given/..%2F..%2F..%2FWindows` with `Host: 127.0.0.1` returned 404 `no such report`. `Host: evil.example` returned 403.
- **`Handler._static`:** A file inside the root is served. `..`, an absolute path, a directory junction that points outside the root, and a relative path containing NUL return 404 and do not return the outside file.
