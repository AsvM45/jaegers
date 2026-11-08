// Wacky Wheels control tower — Node web server. No dependencies; Node 18+.
//
//   npm start                      # http://localhost:8080
//   PORT=3000 npm start
//
// Pages
//   GET /            control-tower view (tower/ui/index.html)
//   GET /tests       generated test-case viewer (web/public/tests.html)
//
// JSON API (same shapes as tower/ui/server.py; the run endpoints also take ?run=<report id>)
//   GET /api/events  /api/traces  /api/log  /api/outbox  /api/ontology  /api/channels
//   GET /api/reports                every run folder under runs/ with summary stats
//   GET /api/testcases?run=tests/x  test cases with expected outcome + graded result (test reports only)
//   POST /api/reports/meta          {run, title?, notes?, starred?}
//   POST /api/reports/delete        {run}  move to runs/.trash (restorable)
//   POST /api/reports/restore       {key}  move back out of the trash
//   POST /api/reports/purge         {key}  delete a trashed report for good
//   (all POSTs are refused when TOWER_READONLY=1)
//   GET /api/tests   test results built by tests/build_viewer.py (runs/tests/viewer_data.json)
//   GET /vendor/three/...           local three.js for the 3D knowledge network
//   GET /healthz
//
// Data root: $TOWER_ROOT, else web/data/ when `npm run bundle` has filled it, else the
// Hitachi folder this file lives in. $TOWER_RUN_DIR (relative to the root) picks the run
// shown at / and defaults to runs/run1, as in the Python server.

'use strict';

const fs = require('node:fs');
const path = require('node:path');
const http = require('node:http');
const zlib = require('node:zlib');

const WEB = __dirname;
const BUNDLED = path.join(WEB, 'data');
// Prefer the live Hitachi folder; fall back to the bundled snapshot only when web/ was deployed alone.
const LIVE = path.join(WEB, '..');
const ROOT = path.resolve(
  process.env.TOWER_ROOT ||
  (fs.existsSync(path.join(LIVE, 'tower', 'ui', 'index.html')) ? LIVE : BUNDLED)
);
const DATA_DIR = path.join(ROOT, 'Data', 'hack_the_highway_package', 'data');
const RUN_DIR = path.resolve(ROOT, process.env.TOWER_RUN_DIR || path.join('runs', 'run1'));
const TESTS_DATA = path.join(ROOT, 'runs', 'tests', 'viewer_data.json');
const TOWER_INDEX = path.join(ROOT, 'tower', 'ui', 'index.html');
const TESTS_INDEX = path.join(WEB, 'public', 'tests.html');
const CHANNELS = process.env.TOWER_CHANNELS_CONFIG || path.join(ROOT, 'tower', 'channels', 'channels.json');
const PORT = Number(process.env.PORT) || 8080;
const HOST = process.env.HOST || '0.0.0.0';

const RUNS_ROOT = path.join(ROOT, 'runs');
const READONLY = /^(1|true|yes)$/i.test(process.env.TOWER_READONLY || '');

const RELATIONSHIPS = [
  'Shipment to dealer: shipment, part, model through the bill of materials, plant, production order, customer order, dealer and customer.',
  'Plant to dealer: plant, production order, customer order, dealer and customer.',
  'Lot to dealer or customer: lot, production order, vehicle, then the dealer, or the dealer and customer when the vehicle is sold.',
];
const ROUTES = ['ops', 'escalations', 'dealers', 'customers'];

// ---------- readers ----------

const readJson = (file) => JSON.parse(fs.readFileSync(file, 'utf8'));

function readJsonl(file) {
  if (!fs.existsSync(file)) return [];
  const rows = [];
  fs.readFileSync(file, 'utf8').split(/\r?\n/).forEach((line, i) => {
    const text = line.trim();
    if (!text) return;
    try { rows.push(JSON.parse(text)); } catch { rows.push({ error: 'invalid json', line: i + 1, text }); }
  });
  return rows;
}

// Minimal RFC 4180 CSV parser (quoted fields, escaped quotes, CRLF).
function readCsv(file) {
  const text = fs.readFileSync(file, 'utf8');
  const rows = [];
  let row = [], field = '', quoted = false;
  for (let i = 0; i < text.length; i++) {
    const c = text[i];
    if (quoted) {
      if (c === '"' && text[i + 1] === '"') { field += '"'; i++; }
      else if (c === '"') quoted = false;
      else field += c;
    } else if (c === '"') quoted = true;
    else if (c === ',') { row.push(field); field = ''; }
    else if (c === '\n' || c === '\r') {
      if (c === '\r' && text[i + 1] === '\n') i++;
      row.push(field); field = '';
      if (row.length > 1 || row[0] !== '') rows.push(row);
      row = [];
    } else field += c;
  }
  if (field !== '' || row.length) { row.push(field); rows.push(row); }
  const [head, ...body] = rows;
  return body.map((r) => Object.fromEntries(head.map((h, k) => [h, r[k] ?? ''])));
}

// ---------- reports (one per run folder) ----------

// Every folder under runs/ (two levels deep) holding traces.json or action_log.jsonl is a report.
// Ids are posix paths relative to runs/, e.g. "run1" or "tests/rules".
function discoverReports() {
  const found = [];
  const visit = (dir, depth) => {
    let entries = [];
    try { entries = fs.readdirSync(dir, { withFileTypes: true }); } catch { return; }
    if (entries.some((e) => e.isFile() && (e.name === 'traces.json' || e.name === 'action_log.jsonl'))) {
      found.push({ id: path.relative(RUNS_ROOT, dir).split(path.sep).join('/'), dir });
    }
    if (depth < 2) entries.filter((e) => e.isDirectory() && !e.name.startsWith('.')).forEach((e) => visit(path.join(dir, e.name), depth + 1));
  };
  visit(RUNS_ROOT, 0);
  return found.filter((r) => r.id).sort((a, b) => a.id.localeCompare(b.id));
}
const DEFAULT_REPORT = path.relative(RUNS_ROOT, RUN_DIR).split(path.sep).join('/');

// Resolve ?run= to a known report folder; anything not discovered is refused (no path traversal).
function runDir(req) {
  const want = new URL(req.url, 'http://x').searchParams.get('run');
  if (!want) return RUN_DIR;
  const hit = discoverReports().find((r) => r.id === want);
  if (!hit) { const e = new Error(`unknown report ${want}`); e.status = 404; throw e; }
  return hit.dir;
}

// A run folder may carry its own events.json (the live channel feed). Otherwise use the package
// feed, unless the run traced events the package does not have (a test run): then rebuild the feed
// from the traces themselves.
function eventsFor(dir) {
  const own = path.join(dir, 'events.json');
  if (fs.existsSync(own)) return readJson(own);
  const pkg = readJson(path.join(DATA_DIR, 'events.json'));
  const tracesFile = path.join(dir, 'traces.json');
  if (!fs.existsSync(tracesFile)) return pkg;
  const traces = readJson(tracesFile);
  const known = new Set(pkg.map((e) => e.event_id));
  if (traces.every((t) => known.has(t.event_id))) return pkg;
  return traces.map((t) => ({ event_id: t.event_id, received_at: t.received_at, source: t.source, text: t.text }));
}

const REAL = new Set(['supplier_delay', 'plant_outage', 'quality_hold']);
const WRITE_TOOLS = new Set(['mes.reschedule', 'mes.transfer', 'dealer.notify', 'dealer.stop_sale',
  'crm.assign_loaner', 'crm.notify_customer', 'quality.hold_lot']);

function readMeta(dir) {
  const f = path.join(dir, 'report_meta.json');
  try { return fs.existsSync(f) ? readJson(f) : {}; } catch { return {}; }
}

function reportSummary({ id, dir }) {
  const tracesFile = path.join(dir, 'traces.json'), logFile = path.join(dir, 'action_log.jsonl');
  const traces = fs.existsSync(tracesFile) ? readJson(tracesFile) : [];
  const log = readJsonl(logFile);
  const events = eventsFor(dir);
  const kinds = {};
  let incidents = 0;
  traces.forEach((t) => (t.incidents || []).forEach((i) => {
    kinds[i.kind] = (kinds[i.kind] || 0) + 1;
    if (REAL.has(i.kind)) incidents++;
  }));
  const mtimes = [tracesFile, logFile].filter((f) => fs.existsSync(f)).map((f) => fs.statSync(f).mtimeMs);
  const meta = readMeta(dir);
  return {
    id,
    kind: id.startsWith('tests/') ? 'test' : 'run',
    is_default: id === DEFAULT_REPORT,
    title: meta.title || '',
    notes: meta.notes || '',
    starred: !!meta.starred,
    modified: mtimes.length ? new Date(Math.max(...mtimes)).toISOString() : null,
    events: events.length,
    traced: traces.length,
    incidents,
    kinds,
    calls: log.length,
    writes: log.filter((r) => r.ok !== false && WRITE_TOOLS.has(r.tool)).length,
    failed: log.filter((r) => r.ok === false).length,
    escalations: log.filter((r) => r.tool === 'escalate').length,
  };
}

function readBody(req, limit = 16 * 1024) {
  return new Promise((resolve, reject) => {
    let size = 0; const chunks = [];
    req.on('data', (c) => { size += c.length; if (size > limit) { reject(Object.assign(new Error('body too large'), { status: 413 })); req.destroy(); } else chunks.push(c); });
    req.on('end', () => { try { resolve(JSON.parse(Buffer.concat(chunks).toString('utf8') || '{}')); } catch { reject(Object.assign(new Error('invalid json body'), { status: 400 })); } });
    req.on('error', reject);
  });
}

// POST /api/reports/meta {run, title?, notes?, starred?} -> runs/<run>/report_meta.json
async function saveMeta(req, res) {
  if (READONLY) return json(req, res, { error: 'read-only server (TOWER_READONLY is set)' }, 403);
  const body = await readBody(req);
  const hit = discoverReports().find((r) => r.id === body.run);
  if (!hit) return json(req, res, { error: 'unknown report' }, 404);
  const meta = readMeta(hit.dir);
  if (typeof body.title === 'string') meta.title = body.title.trim().slice(0, 120);
  if (typeof body.notes === 'string') meta.notes = body.notes.slice(0, 4000);
  if (typeof body.starred === 'boolean') meta.starred = body.starred;
  meta.updated_at = new Date().toISOString();
  fs.writeFileSync(path.join(hit.dir, 'report_meta.json'), JSON.stringify(meta, null, 2) + '\n');
  json(req, res, reportSummary(hit));
}

// ---------- deleting reports: a recoverable trash under runs/.trash ----------

const TRASH = path.join(RUNS_ROOT, '.trash');

function listTrash() {
  let entries = [];
  try { entries = fs.readdirSync(TRASH, { withFileTypes: true }); } catch { return []; }
  return entries.filter((e) => e.isDirectory()).map((e) => {
    let info = {};
    try { info = readJson(path.join(TRASH, e.name, '.trashinfo.json')); } catch { /* unknown origin */ }
    return { key: e.name, id: info.id || e.name, deleted_at: info.deleted_at || null };
  }).sort((a, b) => String(b.deleted_at).localeCompare(String(a.deleted_at)));
}
const trashEntry = (key) => listTrash().find((t) => t.key === key);
const refuse = (status, message) => Object.assign(new Error(message), { status });

// POST /api/reports/delete {run} -> moves runs/<run> to runs/.trash/<name> (restorable)
async function deleteReport(req, res) {
  if (READONLY) throw refuse(403, 'read-only server (TOWER_READONLY is set)');
  const body = await readBody(req);
  const hit = discoverReports().find((r) => r.id === body.run);
  if (!hit) throw refuse(404, 'unknown report');
  if (hit.id === DEFAULT_REPORT) throw refuse(409, 'The server default report cannot be deleted. Point TOWER_RUN_DIR at another run first.');
  fs.mkdirSync(TRASH, { recursive: true });
  const key = `${hit.id.replace(/\//g, '__')}--${Date.now()}`;
  fs.renameSync(hit.dir, path.join(TRASH, key));
  fs.writeFileSync(path.join(TRASH, key, '.trashinfo.json'), JSON.stringify({ id: hit.id, deleted_at: new Date().toISOString() }, null, 2) + '\n');
  json(req, res, { ok: true, trashed: key });
}

// POST /api/reports/restore {key} -> moves it back to runs/<original id>
async function restoreReport(req, res) {
  if (READONLY) throw refuse(403, 'read-only server (TOWER_READONLY is set)');
  const body = await readBody(req);
  const entry = trashEntry(body.key);
  if (!entry) throw refuse(404, 'not in trash');
  const target = path.resolve(RUNS_ROOT, entry.id);
  if (!target.startsWith(RUNS_ROOT + path.sep)) throw refuse(400, 'bad report id');
  if (fs.existsSync(target)) throw refuse(409, `runs/${entry.id} already exists; move it away first`);
  fs.mkdirSync(path.dirname(target), { recursive: true });
  fs.renameSync(path.join(TRASH, entry.key), target);
  fs.rmSync(path.join(target, '.trashinfo.json'), { force: true });
  json(req, res, { ok: true, restored: entry.id });
}

// POST /api/reports/purge {key} -> permanently removes one trashed report
async function purgeReport(req, res) {
  if (READONLY) throw refuse(403, 'read-only server (TOWER_READONLY is set)');
  const body = await readBody(req);
  const entry = trashEntry(body.key);
  if (!entry) throw refuse(404, 'not in trash');
  fs.rmSync(path.join(TRASH, entry.key), { recursive: true, force: true });
  json(req, res, { ok: true, purged: entry.key });
}

// ---------- payloads ----------

// Same numbers as tower.graph.WorldGraph.counts(); built once, ~17,000 rows.
let ontology = null;
function ontologyPayload() {
  if (ontology) return ontology;
  const t = (name) => readCsv(path.join(DATA_DIR, name));
  const plants = t('plants.csv'), suppliers = t('suppliers.csv'), parts = t('parts.csv'), models = t('models.csv');
  const dealers = t('dealers.csv'), shipments = t('inbound_shipments.csv'), lots = t('part_lots.csv');
  const bom = new Set(t('bom.csv').map((r) => `${r.model}|${r.part_id}`));
  // Alias keys are case-folded and the first registration wins, so the count is unique keys.
  const aliases = new Set();
  const add = (s) => aliases.add(String(s).toLowerCase());
  const aliasRows = t('aliases.csv');
  aliasRows.forEach((r) => add(r.alias));
  // "the Texas plant" is also registered as "Texas plant".
  aliasRows.forEach((r) => { if (r.alias.toLowerCase().startsWith('the ')) add(r.alias.slice(4)); });
  plants.forEach((r) => { add(r.plant_id); add(r.name); });
  suppliers.forEach((r) => { add(r.supplier_id); add(r.name); });
  parts.forEach((r) => { add(r.part_id); add(r.name); });
  models.forEach((r) => add(r.model));
  shipments.forEach((r) => add(r.shipment_id));
  lots.forEach((r) => add(r.lot_id));
  dealers.forEach((r) => { add(r.dealer_id); add(r.name); });
  ontology = {
    counts: {
      plants: plants.length, suppliers: suppliers.length, parts: parts.length, models: models.length,
      bom_edges: bom.size, shipments: shipments.length, lots: lots.length,
      production_orders: t('production_orders.csv').length, customer_orders: t('customer_orders.csv').length,
      customers: t('customers.csv').length, dealers: dealers.length, vehicles: t('finished_vehicles.csv').length,
      aliases: aliases.size,
    },
    relationships: RELATIONSHIPS,
    // Plant list for the dashboard's plant-network map (same shape as tower/ui/server.py).
    plants: plants.map((p) => ({ plant_id: p.plant_id, name: p.name, city: p.city, slots_per_day: Number(p.slots_per_day) })),
  };
  return ontology;
}

// Names and kinds only — never secrets (matches tower/channels/config.py filtering).
function channelsPayload() {
  if (!fs.existsSync(CHANNELS)) {
    return { configured: false, sources: {}, sinks: {}, routes: Object.fromEntries(ROUTES.map((r) => [r, []])) };
  }
  const raw = readJson(CHANNELS);
  const enabled = (obj) => Object.fromEntries(Object.entries(obj || {}).filter(([, v]) => v.enabled !== false));
  const sources = enabled(raw.sources), sinks = enabled(raw.sinks);
  const routes = {};
  for (const name of ROUTES) {
    const v = (raw.routes || {})[name] || [];
    routes[name] = (Array.isArray(v) ? v : v.sinks || []).filter((s) => s in sinks);
  }
  const kinds = (obj) => Object.fromEntries(Object.entries(obj).map(([k, v]) => [k, v.kind ?? null]));
  return { configured: true, sources: kinds(sources), sinks: kinds(sinks), routes };
}

// ---------- http ----------

function send(req, res, code, type, body) {
  const headers = { 'Content-Type': type, 'Cache-Control': 'no-store', 'X-Content-Type-Options': 'nosniff' };
  let buf = Buffer.isBuffer(body) ? body : Buffer.from(body);
  if (buf.length > 1024 && /\bgzip\b/.test(req.headers['accept-encoding'] || '')) {
    buf = zlib.gzipSync(buf);
    headers['Content-Encoding'] = 'gzip';
    headers.Vary = 'Accept-Encoding';
  }
  headers['Content-Length'] = buf.length;
  res.writeHead(code, headers);
  res.end(req.method === 'HEAD' ? undefined : buf);
}
const json = (req, res, payload, code = 200) =>
  send(req, res, code, 'application/json; charset=utf-8', JSON.stringify(payload));
const page = (req, res, file) => send(req, res, 200, 'text/html; charset=utf-8', fs.readFileSync(file));

const ROUTES_GET = {
  '/': (req, res) => page(req, res, TOWER_INDEX),
  '/tests': (req, res) => page(req, res, TESTS_INDEX),
  '/healthz': (req, res) => json(req, res, { ok: true, root: path.relative(WEB, ROOT) || '.' }),
  '/api/events': (req, res) => json(req, res, eventsFor(runDir(req))),
  '/api/traces': (req, res) => {
    const f = path.join(runDir(req), 'traces.json');
    json(req, res, fs.existsSync(f) ? readJson(f) : []);
  },
  '/api/log': (req, res) => json(req, res, readJsonl(path.join(runDir(req), 'action_log.jsonl'))),
  '/api/outbox': (req, res) => json(req, res, readJsonl(path.join(runDir(req), 'outbox.jsonl'))),
  // Test-run reports only: each case's definition (tests/cases.json) joined with its graded result.
  '/api/testcases': (req, res) => {
    const resultsFile = path.join(runDir(req), 'results.json');
    const casesFile = path.join(ROOT, 'tests', 'cases.json');
    if (!fs.existsSync(resultsFile) || !fs.existsSync(casesFile)) return json(req, res, { error: 'not a test report' }, 404);
    const results = new Map(readJson(resultsFile).map((r) => [r.id, r]));
    json(req, res, readJson(casesFile).map((c) => ({ ...c, result: results.get(c.id) || null })));
  },
  '/api/reports': (req, res) => json(req, res, {
    default: DEFAULT_REPORT, readonly: READONLY, reports: discoverReports().map(reportSummary), trash: listTrash(),
  }),
  '/api/ontology': (req, res) => json(req, res, ontologyPayload()),
  '/api/channels': (req, res) => json(req, res, channelsPayload()),
  '/api/tests': (req, res) => {
    if (!fs.existsSync(TESTS_DATA)) {
      return json(req, res, { error: 'no test results', detail: 'Run python3 tests/run_cases.py (or tests/build_viewer.py).' }, 404);
    }
    send(req, res, 200, 'application/json; charset=utf-8', fs.readFileSync(TESTS_DATA));
  },
};

// Local copy of three.js (npm dependency) for the 3D knowledge network, so the page works offline.
// Only .js files under build/ and examples/jsm/ are served.
const THREE_DIR = path.join(WEB, 'node_modules', 'three');
function serveVendor(req, res, pathname) {
  const rel = decodeURIComponent(pathname.slice('/vendor/three/'.length));
  const abs = path.resolve(THREE_DIR, rel);
  const okRoot = [path.join(THREE_DIR, 'build') + path.sep, path.join(THREE_DIR, 'examples', 'jsm') + path.sep].some((r) => abs.startsWith(r));
  if (!okRoot || !abs.endsWith('.js') || !fs.existsSync(abs)) return json(req, res, { error: 'not found' }, 404);
  let buf = fs.readFileSync(abs);
  const headers = { 'Content-Type': 'text/javascript; charset=utf-8', 'Cache-Control': 'public, max-age=86400', 'X-Content-Type-Options': 'nosniff' };
  if (/\bgzip\b/.test(req.headers['accept-encoding'] || '')) { buf = zlib.gzipSync(buf); headers['Content-Encoding'] = 'gzip'; headers.Vary = 'Accept-Encoding'; }
  headers['Content-Length'] = buf.length;
  res.writeHead(200, headers);
  res.end(req.method === 'HEAD' ? undefined : buf);
}

const ROUTES_POST = {
  '/api/reports/meta': saveMeta,
  '/api/reports/delete': deleteReport,
  '/api/reports/restore': restoreReport,
  '/api/reports/purge': purgeReport,
};

const server = http.createServer(async (req, res) => {
  let pathname = new URL(req.url, 'http://x').pathname;
  if (pathname !== '/') pathname = pathname.replace(/\/+$/, '') || '/';
  if ((req.method === 'GET' || req.method === 'HEAD') && pathname.startsWith('/vendor/three/')) return serveVendor(req, res, pathname);
  const table = req.method === 'POST' ? ROUTES_POST : (req.method === 'GET' || req.method === 'HEAD') ? ROUTES_GET : null;
  if (!table) return json(req, res, { error: 'method not allowed' }, 405);
  const handler = table[pathname];
  if (!handler) return json(req, res, { error: 'not found' }, 404);
  try {
    await handler(req, res);
  } catch (err) {
    if (err.status) return json(req, res, { error: err.message }, err.status);
    if (err.code === 'ENOENT') return json(req, res, { error: 'missing file', detail: err.message }, 500);
    if (err instanceof SyntaxError) return json(req, res, { error: 'invalid json', detail: err.message }, 500);
    json(req, res, { error: 'read failed', detail: err.message }, 500);
  }
});

if (require.main === module) {
  server.on('error', (err) => {
    if (err.code === 'EADDRINUSE') {
      console.error(`Port ${PORT} is already in use. Stop the other server (lsof -i :${PORT}) or run with PORT=3000 npm start.`);
      process.exit(1);
    }
    throw err;
  });
  server.listen(PORT, HOST, () => {
    const shown = HOST === '0.0.0.0' ? 'localhost' : HOST;
    console.log(`Control tower  http://${shown}:${PORT}/`);
    console.log(`Test viewer    http://${shown}:${PORT}/tests`);
    console.log(`Data root      ${ROOT}`);
  });
  const stop = () => server.close(() => process.exit(0));
  process.on('SIGTERM', stop);
  process.on('SIGINT', stop);
}

module.exports = { server };
