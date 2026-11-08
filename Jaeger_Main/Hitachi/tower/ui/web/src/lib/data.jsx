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
  const score = newestBySuite(raw.reports);
  return {
    ...raw, byEvent, traceById, agentById, outcome, model, agentName, suiteById,
    testTotals: { passed: score.passed, total: score.total, labels: score.labels, updated: score.updated },
  };
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
    const timer = setInterval(tick, 15000);
    tick();
    return () => { stop = true; clearInterval(timer); };
  }, [reload]);
  const value = useMemo(() => ({ ...derive(raw), busy, reload }), [raw, busy, reload]);
  return <DataCtx.Provider value={value}>{children}</DataCtx.Provider>;
}

export const useData = () => useContext(DataCtx);
