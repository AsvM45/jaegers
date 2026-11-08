// Copy everything the web app reads into web/data/, so the web/ folder can be deployed on its own.
//
//   npm run bundle
//
// Re-run after a new tower run or test run. Channel config is deliberately not copied.

'use strict';

const fs = require('node:fs');
const path = require('node:path');

const WEB = path.join(__dirname, '..');
const SRC = path.join(WEB, '..');
const DEST = path.join(WEB, 'data');

const files = ['tower/ui/index.html', 'runs/tests/viewer_data.json', 'tests/cases.json'];
// Every report folder under runs/ (two levels deep), so the Reports page works after deploy.
const RUN_FILES = ['events.json', 'traces.json', 'action_log.jsonl', 'outbox.jsonl', 'report_meta.json', 'results.json'];
const walk = (rel, depth) => {
  const abs = path.join(SRC, rel);
  if (!fs.existsSync(abs)) return;
  RUN_FILES.forEach((f) => { if (fs.existsSync(path.join(abs, f))) files.push(path.join(rel, f)); });
  if (depth < 2) fs.readdirSync(abs, { withFileTypes: true }).filter((e) => e.isDirectory()).forEach((e) => walk(path.join(rel, e.name), depth + 1));
};
walk('runs', 0);
const dataDir = 'Data/hack_the_highway_package/data';
for (const f of fs.readdirSync(path.join(SRC, dataDir))) {
  if (f.endsWith('.csv') || f === 'events.json') files.push(path.join(dataDir, f));
}

fs.rmSync(DEST, { recursive: true, force: true });
let copied = 0, bytes = 0;
for (const rel of files) {
  const from = path.join(SRC, rel);
  if (!fs.existsSync(from)) { console.log(`skip     ${rel} (not found)`); continue; }
  const to = path.join(DEST, rel);
  fs.mkdirSync(path.dirname(to), { recursive: true });
  fs.copyFileSync(from, to);
  copied++; bytes += fs.statSync(to).size;
}
console.log(`bundled  ${copied} files, ${(bytes / 1e6).toFixed(1)} MB -> ${path.relative(process.cwd(), DEST) || DEST}`);
