# Control tower web app (Node.js)

One Node server, Node 18+. Its only dependency is `three` (served locally at `/vendor/three/` for the 3D knowledge network, so nothing loads from a CDN).

| Path | What |
|---|---|
| `/` | Control-tower view (`tower/ui/index.html`) |
| `/tests` | Test-case viewer (`web/public/tests.html`) |
| `/api/events`, `/api/traces`, `/api/log`, `/api/outbox`, `/api/ontology`, `/api/channels` | Same JSON as `tower/ui/server.py` |
| `/api/reports` | Every run folder under `runs/` (a "report") with summary stats; the run endpoints take `?run=<id>` |
| `POST /api/reports/meta` | Save a report's title, notes and star (`runs/<id>/report_meta.json`) |
| `POST /api/reports/delete`, `/restore`, `/purge` | Move a report to `runs/.trash/`, bring it back, or erase it from the trash |
| `/api/testcases?run=tests/<x>` | Test cases with their expected outcome and graded result |
| `/api/tests` | Test results (`runs/tests/viewer_data.json`) |
| `/healthz` | Health check |

## Run locally

```bash
cd Jaeger_Main/Hitachi/web
npm install               # once: installs three.js
npm start                 # http://localhost:8080  (PORT=3000 npm start for another port)
```

The data comes from the Python side. Refresh it there, then reload the page:

```bash
python3 -m tower.run --reader rules     # control-tower run   -> runs/run1/
python3 tests/run_cases.py              # test cases + viewer -> runs/tests/
```

## Deploy (any Node host: Render, Railway, Heroku-style, a VM)

- **Root directory:** `Jaeger_Main/Hitachi/web`
- **Build command:** `npm install` (nothing to install, but hosts expect it)
- **Start command:** `npm start`
- The server listens on `$PORT` and `0.0.0.0`.

If the host only receives the `web/` folder (zip upload, `scp`), run `npm run bundle` first.
That copies the CSVs, the run, the tower page and the test results into `web/data/`, and the
server uses `web/data/` whenever it exists. Re-run it after every new run.

`runs/tests/` must be present (committed, or bundled) for `/tests` to show results.

## Settings

| Variable | Default | Meaning |
|---|---|---|
| `PORT` | `8080` | Listen port |
| `HOST` | `0.0.0.0` | Listen address (`127.0.0.1` for local-only) |
| `TOWER_ROOT` | `..` (the Hitachi folder), else `web/data` when `web/` is deployed alone | Folder holding `Data/`, `runs/`, `tower/` |
| `TOWER_RUN_DIR` | `runs/run1` | Run shown at `/`, relative to the root (e.g. `runs/live`) |
| `TOWER_READONLY` | off | `1` blocks editing and deleting reports (use for public deploys) |
| `TOWER_CHANNELS_CONFIG` | `tower/channels/channels.json` | Channel config; only names and kinds are exposed |
