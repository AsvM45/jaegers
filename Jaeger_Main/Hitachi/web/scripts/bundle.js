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
const run = process.env.TOWER_RUN_DIR || path.join('runs', 'run1');

const files = [
  'tower/ui/index.html',
  'runs/tests/viewer_data.json',
  ...['events.json', 'traces.json', 'action_log.jsonl', 'outbox.jsonl'].map((f) => path.join(run, f)),
];
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
