#!/usr/bin/env node
// Keeps the dashboard's translations (src/locales/*.json) in step with its source.
//
//   npm run i18n            report: text not wrapped in tr(), strings a language is missing, unused ones
//   npm run i18n:fill       translate the missing strings with the local Ollama model, then report
//   npm run i18n:prune      also drop translations no source string uses any more
//
// `npm run build` runs the report first (warnings only; the build never fails on it).
//
// The English strings are the keys. They are found in the source: the string literals in the first
// argument of tr(), trx() and msg(), the values of translated({...}) tables, the incident field
// labels, and the agent and test-set text the Python server sends (tower/agents/roster.py and
// tower/ui/reports.py). Adding a component means: wrap its words in tr("...") (or trx() for a
// sentence with markup, msg() for a string translated later), then run npm run i18n:fill.
//
// Fill uses Ollama on this machine (no cloud): TOWER_I18N_MODEL, default qwen3:8b, at OLLAMA_URL.
// Every answer is checked: it must keep exactly the {placeholders} of the English, or it is dropped
// and reported. Review machine translations before a demo; a person's fix in the JSON is kept.
import { execFileSync } from "node:child_process";
import { readFileSync, readdirSync, statSync, writeFileSync } from "node:fs";
import { dirname, join, relative } from "node:path";
import { fileURLToPath } from "node:url";

const WEB = join(dirname(fileURLToPath(import.meta.url)), "..");
const SRC = join(WEB, "src");
const LOCALES = join(SRC, "locales");
const HITACHI = join(WEB, "..", "..", "..");
const NAMES = { de: "German", es: "Spanish", fr: "French", hi: "Hindi", ja: "Japanese", ko: "Korean", pt: "Portuguese (Brazil)", zh: "Simplified Chinese" };
const MODEL = process.env.TOWER_I18N_MODEL || "qwen3:8b";
const OLLAMA = process.env.OLLAMA_URL || "http://localhost:11434";

const files = (dir) => readdirSync(dir).flatMap((f) => {
  const p = join(dir, f);
  if (statSync(p).isDirectory()) return f === "locales" ? [] : files(p);
  return /\.(jsx?|mjs)$/.test(f) ? [p] : [];
});

// The first argument of a call starting at index i (just after the opening parenthesis).
function firstArg(s, i) {
  let depth = 0, quote = null;
  for (let j = i; j < s.length; j += 1) {
    const c = s[j];
    if (quote) { if (c === "\\") j += 1; else if (c === quote) quote = null; continue; }
    if (c === '"' || c === "'" || c === "`") quote = c;
    else if ("([{".includes(c)) depth += 1;
    else if (")]}".includes(c)) { if (depth === 0) return s.slice(i, j); depth -= 1; }
    else if (c === "," && depth === 0) return s.slice(i, j);
  }
  return s.slice(i);
}

const literals = (code) => [...code.matchAll(/"((?:[^"\\]|\\.)*)"/g)].map((m) => JSON.parse(`"${m[1]}"`));

function sourceKeys() {
  const keys = [];
  for (const p of files(SRC)) {
    if (p.endsWith("i18n.js")) continue;
    const s = readFileSync(p, "utf8");
    for (const m of s.matchAll(/\b(?:trx?|msg)\(/g)) keys.push(...literals(firstArg(s, m.index + m[0].length)));
    for (const m of s.matchAll(/translated\(\{([\s\S]*?)\}\)/g)) keys.push(...[...m[1].matchAll(/:\s*"([^"]+)"/g)].map((x) => x[1]));
    for (const m of s.matchAll(/\blabel: "([^"]+)"/g)) if (p.endsWith("constants.js")) keys.push(m[1]);
    const fields = s.match(/const FIELD_LABEL = \{([\s\S]*?)\};/);
    if (fields) keys.push(...[...fields[1].matchAll(/:\s*"([^"]+)"/g)].map((x) => x[1]));
  }
  return keys;
}

// Interface text the Python side sends: agent titles and duties, test-set names.
function serverKeys() {
  const script = [
    "import json, sys; sys.path.insert(0, '.')",
    "from tower.agents.roster import roster",
    "from tower.ui import reports",
    "out = []",
    "for a in roster(): out += [a['title'], a['responsibility'], a['takes']]",
    "for s in reports.SUITES: out += [s['title'], s.get('subtitle', '')]",
    "print(json.dumps(out))",
  ].join("\n");
  try {
    return JSON.parse(execFileSync("python3", ["-c", script], { cwd: HITACHI, encoding: "utf8", stdio: ["ignore", "pipe", "ignore"] }));
  } catch {
    console.warn("i18n: could not read the server's agent and test-set text (python3 tower.agents.roster); skipping it.");
    return [];
  }
}

// Words in JSX that look like interface text but are not passed through tr(). Lines with
// "i18n-ignore" are skipped; so are commands, paths and ids.
const CODEY = /^(python3?|npm|npx|cd |ollama|brew|git |TOWER_|http)|^[\w.\-]*[/._][\w./\-]*$|^[\W\d_]+$/;
function unwrapped() {
  const found = [];
  for (const p of files(SRC)) {
    if (!p.endsWith(".jsx")) continue;
    const lines = readFileSync(p, "utf8").split("\n");
    lines.forEach((line, n) => {
      if (line.includes("i18n-ignore") || /^\s*(\/\/|\*|import )/.test(line)) return;
      for (const m of line.matchAll(/(?<![=\-])>([^<>{}]*[A-Za-z]{3,}[^<>{}]*)<(?=[/A-Za-z])/g)) {
        const text = m[1].trim();
        const before = line.slice(0, m.index + 1);
        if (/<kbd[^>]*>$/.test(before) || /^,?\s*\w+:$/.test(text)) continue; // a key name; an object key in trx(...)
        if (text && !CODEY.test(text) && !/(=>|&&|\|\||==)/.test(text)) found.push(`${relative(WEB, p)}:${n + 1}  ${text.slice(0, 70)}`);
      }
      for (const m of line.matchAll(/\b(placeholder|title|aria-label|label|sub|subtitle|hint)="([A-Z][^"]*[a-z]{2,}[^"]*)"/g)) {
        if (!CODEY.test(m[2])) found.push(`${relative(WEB, p)}:${n + 1}  ${m[1]}="${m[2].slice(0, 60)}"`);
      }
    });
  }
  return found;
}

const placeholders = (s) => (s.match(/\{\w+\}/g) || []).sort().join(" ");
// The text a reader sees as prose: no {placeholders}, no menu paths like "System Settings → Privacy",
// nothing in parentheses (where English menu and product names are kept on purpose).
const plainText = (s) => s.replace(/\{\w+\}/g, "").replace(/\([^)]*\)/g, "").replace(/[A-Za-z][\w&' ]*(\s*→\s*[A-Za-z][\w&' ]*)+/g, "");
const load = (lang) => JSON.parse(readFileSync(join(LOCALES, `${lang}.json`), "utf8"));
const save = (lang, dict) => writeFileSync(join(LOCALES, `${lang}.json`),
  JSON.stringify(Object.fromEntries(Object.entries(dict).sort(([a], [b]) => (a < b ? -1 : 1))), null, 0).replace(/^\{/, "{\n").replace(/","/g, '",\n"').replace(/\}$/, "\n}\n"));

async function translate(lang, strings) {
  const out = {};
  for (let i = 0; i < strings.length; i += 25) {
    const batch = strings.slice(i, i + 25);
    const items = Object.fromEntries(batch.map((s, k) => [String(k), s]));
    const props = Object.fromEntries(batch.map((_, k) => [String(k), { type: "string" }]));
    const body = {
      model: MODEL, stream: false, think: false, options: { temperature: 0 },
      format: { type: "object", properties: props, required: Object.keys(props) },
      messages: [
        { role: "system", content: `You translate the interface of an automotive operations dashboard ("control tower") from English to ${NAMES[lang]}. Write natural, concise UI text. Keep every {placeholder} exactly as written. Keep product names (Wacky Wheels, Whisper, Ollama), commands, file names, ids like P_TX or supplier_delay, keyboard keys and symbols (→ ↗ ·) unchanged. Answer with JSON: the same keys, each value the translation.` },
        { role: "user", content: JSON.stringify(items) },
      ],
    };
    const res = await fetch(`${OLLAMA}/api/chat`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
    if (!res.ok) throw new Error(`Ollama answered ${res.status}. Is ${MODEL} pulled? (ollama pull ${MODEL})`);
    const answer = JSON.parse((await res.json()).message?.content || "{}");
    batch.forEach((s, k) => {
      const t = typeof answer[k] === "string" ? answer[k].trim() : "";
      if (t && placeholders(t) === placeholders(s)) out[s] = t;
      else console.warn(`  ${lang}: dropped a translation that changed the placeholders: ${s}`);
    });
  }
  return out;
}

async function main() {
  const mode = process.argv[2] || "check";
  const keys = [...new Set([...sourceKeys(), ...serverKeys()].filter((k) => /[A-Za-z]/.test(k) && k.trim()))];
  const langs = readdirSync(LOCALES).filter((f) => f.endsWith(".json")).map((f) => f.slice(0, -5)).sort();
  let problems = 0;

  const loose = unwrapped();
  if (loose.length) {
    problems += loose.length;
    console.warn(`i18n: ${loose.length} piece(s) of interface text are not wrapped in tr() (add "i18n-ignore" on the line if it is code):`);
    for (const l of loose) console.warn(`  ${l}`);
  }

  for (const lang of langs) {
    let dict = load(lang);
    let missing = keys.filter((k) => !dict[k]);
    if (mode === "fill" && missing.length) {
      console.log(`i18n: translating ${missing.length} string(s) into ${NAMES[lang] || lang} with ${MODEL}…`);
      dict = { ...dict, ...(await translate(lang, missing)) };
      save(lang, dict);
      missing = keys.filter((k) => !dict[k]);
    }
    const unused = Object.keys(dict).filter((k) => !keys.includes(k));
    if (mode === "prune" && unused.length) {
      for (const k of unused) delete dict[k];
      save(lang, dict);
    }
    const wrong = keys.filter((k) => dict[k] && placeholders(dict[k]) !== placeholders(k));
    // Scripts that are not Latin: an English function word left in the text is a sign of a half
    // translation (a model fill does this most often). Flag it for a person to look at.
    const english = ["ja", "zh", "ko", "hi"].includes(lang)
      ? keys.filter((k) => dict[k] && /(^|[^A-Za-z])(of|the|and|with|from|for)([^A-Za-z]|$)/.test(plainText(dict[k])))
      : [];
    problems += english.length;
    for (const k of english.slice(0, 8)) console.log(`    still has English words: ${dict[k].slice(0, 90)}`);
    if (missing.length || wrong.length) problems += missing.length + wrong.length;
    console.log(`i18n: ${lang} ${keys.length - missing.length}/${keys.length}` +
      (missing.length ? `, missing ${missing.length}` : "") + (wrong.length ? `, ${wrong.length} with wrong placeholders` : "") +
      (unused.length && mode !== "prune" ? `, ${unused.length} unused` : ""));
    for (const k of missing.slice(0, 8)) console.log(`    missing: ${k.slice(0, 90)}`);
    for (const k of wrong.slice(0, 8)) console.log(`    placeholders differ: ${k.slice(0, 90)}`);
  }
  if (problems && mode === "check") console.log("i18n: run `npm run i18n:fill` to translate what is missing.");
  if (process.argv.includes("--strict") && problems) process.exit(1);
}

main().catch((err) => { console.error(`i18n: ${err.message}`); process.exit(mode() === "check" ? 0 : 1); });
function mode() { return process.argv[2] || "check"; }
