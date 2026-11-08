// Wacky Wheels control tower — Node web server. No dependencies; Node 18+.
//
//   npm start                      # http://localhost:8080
//   PORT=3000 npm start
//
// Pages
//   GET /            control-tower view (tower/ui/index.html)
//   GET /tests       generated test-case viewer (web/public/tests.html)
//
// JSON API (same shapes as tower/ui/server.py)
//   GET /api/events  /api/traces  /api/log  /api/outbox  /api/ontology  /api/channels
//   GET /api/tests   test results built by tests/build_viewer.py (runs/tests/viewer_data.json)
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

// A run directory may carry its own events.json (the live channel feed); otherwise use the package's.
const eventsPath = () => {
  const own = path.join(RUN_DIR, 'events.json');
  return fs.existsSync(own) ? own : path.join(DATA_DIR, 'events.json');
};

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
  '/api/events': (req, res) => json(req, res, readJson(eventsPath())),
  '/api/traces': (req, res) => {
    const f = path.join(RUN_DIR, 'traces.json');
    json(req, res, fs.existsSync(f) ? readJson(f) : []);
  },
  '/api/log': (req, res) => json(req, res, readJsonl(path.join(RUN_DIR, 'action_log.jsonl'))),
  '/api/outbox': (req, res) => json(req, res, readJsonl(path.join(RUN_DIR, 'outbox.jsonl'))),
  '/api/ontology': (req, res) => json(req, res, ontologyPayload()),
  '/api/channels': (req, res) => json(req, res, channelsPayload()),
  '/api/tests': (req, res) => {
    if (!fs.existsSync(TESTS_DATA)) {
      return json(req, res, { error: 'no test results', detail: 'Run python3 tests/run_cases.py (or tests/build_viewer.py).' }, 404);
    }
    send(req, res, 200, 'application/json; charset=utf-8', fs.readFileSync(TESTS_DATA));
  },
};

const server = http.createServer((req, res) => {
  if (req.method !== 'GET' && req.method !== 'HEAD') return json(req, res, { error: 'method not allowed' }, 405);
  let pathname = new URL(req.url, 'http://x').pathname;
  if (pathname !== '/') pathname = pathname.replace(/\/+$/, '') || '/';
  const handler = ROUTES_GET[pathname];
  if (!handler) return json(req, res, { error: 'not found' }, 404);
  try {
    handler(req, res);
  } catch (err) {
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
