// Loads the run and test results from the Python server and shares them with every page.
import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { WRITE_TOOLS, plain, readerName } from "./constants.js";
import { tr } from "./i18n.js";
import { useSettings } from "./settings.jsx";

export async function getJSON(url, fallback) {
  try {
    const r = await fetch(url, { cache: "no-store" });
    if (!r.ok) return fallback;
    return await r.json();
  } catch {
    return fallback;
  }
}

const EMPTY = { events: [], traces: [], log: [], outbox: [], onto: null, reports: null, agents: [], promise: null, online: false, demoIds: [], demoSize: 0, loadedAt: null, failed: false };

// Newest saved run of each suite. A later run of one small set must not replace the score for the rest.
export function newestBySuite(reports) {
  const sets = [];
  for (const suite of reports?.suites || []) {
    const reader = [...suite.readers].sort((a, b) => (b.updated || "").localeCompare(a.updated || "") || a.id.localeCompare(b.id))[0];
    if (reader) sets.push({ suite, reader });
  }
  const passed = sets.reduce((a, x) => a + x.reader.passed, 0);
  const total = sets.reduce((a, x) => a + x.reader.total, 0);
  const labels = [...new Set(sets.map((x) => x.reader.label))];
  const updated = sets.reduce((a, x) => ((x.reader.updated || "") > a ? x.reader.updated : a), "");
  return { sets, passed, total, labels, updated };
}

// Names and descriptions the server sends for the agent team and the test sets are interface text:
// translate them here, once. Event text, summaries and reasons stay as the tower wrote them.
function localize(raw) {
  const agents = raw.agents.map((a) => ({ ...a, title: tr(a.title), responsibility: plain(tr(a.responsibility)), takes: plain(tr(a.takes)) }));
  const reports = raw.reports && {
    ...raw.reports, suites: (raw.reports.suites || []).map((s) => ({
      ...s, title: tr(s.title), subtitle: tr(s.subtitle),
      readers: (s.readers || []).map((r) => ({ ...r, label: readerName(r.id), cases: (r.cases || []).map(plainCase) })),
    })),
  };
  // Escalation reasons in the tool-call log, in plain words and without model names.
  const log = raw.log.map((r) => (r.tool === "escalate" && r.args?.reason ? { ...r, args: { ...r.args, reason: plain(r.args.reason) } } : r));
  return { ...raw, agents, reports, log, traces: raw.traces.map(plainTrace), onto: plainOnto(raw.onto) };
}

// The tower's own wording (summaries, reasons, evidence, handoffs, grader notes) in plain words, so no page
// shows a field name, tool id or function. Event messages, record ids and tool arguments are left as they are.
const plainAll = (list) => (Array.isArray(list) ? list.map(plain) : list);
function plainTrace(t) {
  return {
    ...t, summary: plain(t.summary), guardrail: plain(t.guardrail),
    incidents: (t.incidents || []).map((i) => ({ ...i, reader: readerName(i.reader), summary: plain(i.summary), model_reason: plain(i.model_reason),
      question: plain(i.question), evidence: plainAll(i.evidence) })),
    handoffs: (t.handoffs || []).map((h) => ({ ...h, task: plain(h.task), returned: plain(h.returned) })),
    calls: (t.calls || []).map((c) => ({ ...c, reason: plain(c.reason), args: c.tool === "escalate" && c.args ? { ...c.args, reason: plain(c.args.reason) } : c.args })),
  };
}
function plainCase(c) {
  return {
    ...c, summary: plain(c.summary), fails: plainAll(c.fails || []), warnings: plainAll(c.warnings || []),
    score: c.score && { ...c.score, mismatches: plainAll(c.score.mismatches || []) },
    actual: c.actual && { ...c.actual, reasoning: plainAll(c.actual.reasoning || []) },
  };
}
function plainOnto(o) {
  if (!o) return o;
  return { ...o, traversals: Object.fromEntries(Object.entries(o.traversals || {}).map(([k, v]) => [k, plain(v)])) };
}

function derive(source) {
  const raw = localize(source);
  const byEvent = {};
  for (const row of raw.log) (byEvent[row.event_id] ||= []).push(row);
  const traceById = Object.fromEntries(raw.traces.map((t) => [t.event_id, t]));
  const agentById = Object.fromEntries(raw.agents.map((a) => [a.id, a]));
  const outcome = (eventId) => {
    const rows = byEvent[eventId] || [];
    if (rows.some((r) => r.ok && WRITE_TOOLS.has(r.tool))) return "acted";
    if (rows.some((r) => r.tool === "escalate")) return "esc";
    return "none";
  };
  let model = null;
  outer: for (const t of raw.traces) for (const i of t.incidents || []) if (i.reader && i.reader !== readerName("rules")) { model = i.reader; break outer; }
  const agentName = (id) => agentById[id]?.title || ({ reader: tr("Reader (LLM + rules)"), enterprise: tr("Enterprise tools") })[id] || id;
  const suites = raw.reports?.suites || [];
  const suiteById = (id) => suites.find((s) => s.id === id);
  const score = newestBySuite(raw.reports);
  return {
    ...raw, byEvent, traceById, agentById, outcome, model, agentName, suiteById,
    testTotals: { passed: score.passed, total: score.total, labels: score.labels, updated: score.updated },
  };
}

const DataCtx = createContext(null);
// The newest load, outside React: a redraw (a new language) starts from it instead of an empty page.
let lastRaw = EMPTY;

export function DataProvider({ children }) {
  const [raw, setRaw] = useState(() => lastRaw);
  const [busy, setBusy] = useState(false);

  const reload = useCallback(async () => {
    setBusy(true);
    // The two core feeds: if either cannot be reached, the pages show a "couldn't load" banner with a retry.
    let failed = false;
    const core = (url, fallback) => fetch(url, { cache: "no-store" })
      .then((r) => (r.ok ? r.json() : Promise.reject()))
      .catch(() => { failed = true; return fallback; });
    const [events, traces, log, onto, reports, outbox, agents, promise, mode] = await Promise.all([
      getJSON("/api/events", []), core("/api/traces", []), getJSON("/api/log", []),
      getJSON("/api/ontology_export", null), core("/api/test_reports", null), getJSON("/api/outbox", []),
      getJSON("/api/agents", []), getJSON("/api/promise", null), getJSON("/api/mode", null),
    ]);
    // online: the shared online version, where each visitor has their own events and the tests are read-only.
    const online = !!mode?.workspaces;
    // demoIds: the given events Run the demo reads online (a short set); empty means all of them.
    const demoIds = Array.isArray(mode?.demo) ? mode.demo : [];
    const demoSize = demoIds.length;
    lastRaw = { events, traces, log, onto, reports, outbox, agents, promise, online, demoIds, demoSize, loadedAt: Date.now(), failed };
    setRaw(lastRaw);
    setBusy(false);
    return { events: traces.length, calls: log.length };
  }, []);

  useEffect(() => { reload(); }, [reload]);
  // Reload only when the run or the saved results change, so an open tab cannot keep an old score.
  useEffect(() => {
    let seen = null;
    let stop = false;
    const tick = async () => {
      const cur = await getJSON("/api/revision", null);
      if (stop || !cur || !cur.rev) return;
      if (seen === null) seen = cur.rev;
      else if (cur.rev !== seen) { seen = cur.rev; reload(); }
    };
    const timer = setInterval(tick, 3000);
    tick();
    return () => { stop = true; clearInterval(timer); };
  }, [reload]);
  const { language, locale } = useSettings();
  const value = useMemo(() => ({ ...derive(raw), busy, reload }), [raw, busy, reload, language, locale]); // eslint-disable-line react-hooks/exhaustive-deps
  return <DataCtx.Provider value={value}>{children}</DataCtx.Provider>;
}

export const useData = () => useContext(DataCtx);
