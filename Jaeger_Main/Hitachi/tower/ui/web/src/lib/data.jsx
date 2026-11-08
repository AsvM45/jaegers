// Loads the run and test results from the Python server and shares them with every page.
import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { WRITE_TOOLS } from "./constants.js";

export async function getJSON(url, fallback) {
  try {
    const r = await fetch(url, { cache: "no-store" });
    if (!r.ok) return fallback;
    return await r.json();
  } catch {
    return fallback;
  }
}

const EMPTY = { events: [], traces: [], log: [], outbox: [], onto: null, reports: null, agents: [], loadedAt: null };

function derive(raw) {
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
  outer: for (const t of raw.traces) for (const i of t.incidents || []) if (i.reader && i.reader !== "rules") { model = i.reader; break outer; }
  const agentName = (id) => agentById[id]?.title || ({ reader: "Reader (LLM + rules)", enterprise: "Enterprise tools" })[id] || id;
  const suites = raw.reports?.suites || [];
  const suiteById = (id) => suites.find((s) => s.id === id);
  const defaultReader = (suite) => {
    const newest = [...suite.readers].sort((a, b) => (b.updated || "").localeCompare(a.updated || ""))[0];
    return newest?.label;
  };
  let passed = 0, total = 0;
  for (const s of suites) {
    const r = s.readers.find((x) => x.label === defaultReader(s));
    if (r) { passed += r.passed; total += r.total; }
  }
  return { ...raw, byEvent, traceById, agentById, outcome, model, agentName, suiteById, testTotals: { passed, total } };
}

const DataCtx = createContext(null);

export function DataProvider({ children }) {
  const [raw, setRaw] = useState(EMPTY);
  const [busy, setBusy] = useState(false);

  const reload = useCallback(async () => {
    setBusy(true);
    const [events, traces, log, onto, reports, outbox, agents] = await Promise.all([
      getJSON("/api/events", []), getJSON("/api/traces", []), getJSON("/api/log", []),
      getJSON("/api/ontology_export", null), getJSON("/api/test_reports", null), getJSON("/api/outbox", []),
      getJSON("/api/agents", []),
    ]);
    setRaw({ events, traces, log, onto, reports, outbox, agents, loadedAt: Date.now() });
    setBusy(false);
    return { events: traces.length, calls: log.length };
  }, []);

  useEffect(() => { reload(); }, [reload]);
  const value = useMemo(() => ({ ...derive(raw), busy, reload }), [raw, busy, reload]);
  return <DataCtx.Provider value={value}>{children}</DataCtx.Provider>;
}

export const useData = () => useContext(DataCtx);
