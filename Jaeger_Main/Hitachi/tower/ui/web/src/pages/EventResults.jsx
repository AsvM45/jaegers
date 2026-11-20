// The Results tab of the Event center: the Tests layout for the events in the feed, with no grading.
// Charts across the feed, a table of every event, and one event's input, reading and actions.
import { Fragment } from "react";
import { CAT_COLOR, CAT_NAME, CAT_ORDER, GROUPS, KIND_LABEL, TOOL_WORD, WRITE_TOOLS, clockTime, fmt, kindsOf } from "../lib/constants.js";
import { useData } from "../lib/data.jsx";
import { useUi } from "../lib/ui.jsx";
import { useState } from "react";
import { CardHead, KindTag, Status, Toggle } from "../components/common.jsx";
import { Pie, StackBars } from "../components/charts.jsx";
import { Pager, usePage } from "../components/Pager.jsx";
import { Cell, Effects, OutcomeLine, Reading } from "./Tests.jsx";
import { tr } from "../lib/i18n.js";

const REAL = new Set(["supplier_delay", "plant_outage", "quality_hold"]);
const FIELDS = ["plant_id", "part_id", "supplier_id", "shipment_id", "lot_id", "blocked_from", "blocked_until",
  "outage_start", "outage_end", "build_start", "build_end"];
const OUTCOME_PARTS = [["acted", "Acted", "var(--good)"], ["esc", "Escalated", "var(--warn)"], ["none", "No action", "#6b7894"]];

// One category per event, the way the test sets label cases: two real incidents make a compound.
export function categoryOf(t) {
  const kinds = kindsOf(t);
  const real = kinds.filter((k) => REAL.has(k));
  if (real.length > 1) return "compound";
  return real[0] || (kinds.includes("unconfirmed") ? "unconfirmed" : "noise");
}

// What the tower did for one event, in the same shape as a test case's actual output.
export function eventOutcome(t, rows) {
  const ok = rows.filter((r) => r.ok);
  const ids = (tools, key) => [...new Set(ok.filter((r) => tools.includes(r.tool) && r.args?.[key]).map((r) => r.args[key]))].sort();
  const byTool = {};
  for (const r of rows) byTool[r.tool] = (byTool[r.tool] || 0) + 1;
  return {
    incidents: (t.incidents || []).filter((i) => REAL.has(i.kind))
      .map((i) => Object.fromEntries([["kind", i.kind], ...FIELDS.filter((k) => i[k]).map((k) => [k, i[k]])])),
    reasoning: (t.incidents || []).map((i) => i.model_reason).filter(Boolean),
    escalate: ok.some((r) => r.tool === "escalate"),
    moved: ids(["mes.reschedule", "mes.transfer"], "production_order_id"),
    dealers: ids(["dealer.notify"], "dealer_id"),
    loaners: ids(["crm.assign_loaner"], "customer_order_id"),
    lots: ids(["quality.hold_lot"], "lot_id"),
    stop_sale_vins: [...new Set(ok.filter((r) => r.tool === "dealer.stop_sale").flatMap((r) => r.args?.vins || []))].sort(),
    owners: ids(["crm.notify_customer"], "customer_id"),
    calls: rows.length,
    failed: rows.filter((r) => !r.ok).length,
    by_tool: byTool,
  };
}

function ToolBars({ counts }) {
  const tools = Object.entries(counts).filter(([t]) => WRITE_TOOLS.has(t) || t === "escalate").sort((a, b) => b[1] - a[1]);
  if (!tools.length) return <div className="empty">{tr("No tool calls yet.")}</div>;
  const max = Math.max(1, ...tools.map(([, n]) => n));
  return (
    <div className="bars">
      {tools.map(([t, n]) => (
        <div className="hbar" key={t}>
          <div className="lab"><span>{TOOL_WORD[t] || t}</span><b>{fmt(n)}</b></div>
          <div className="track"><div className="fill" style={{ width: `${(n / max) * 100}%` }} /></div>
        </div>
      ))}
    </div>
  );
}

// ---- Events over time: events (or tool calls) per time bucket, split by outcome, type or kind of action.
const STEPS = [[15, "15 minutes"], [30, "30 minutes"], [60, "hour"], [180, "3 hours"], [1440, "day"], [10080, "week"]];
const stamp = (s) => { const t = Date.parse(String(s || "").replace(" ", "T")); return Number.isNaN(t) ? null : t; };
// Calendar buckets: a day starts at midnight, a week on Monday, a month on the 1st (local clock: received
// times carry no zone).
function startOf(t, unit) {
  const d = new Date(t);
  d.setHours(0, 0, 0, 0);
  if (unit === "week") d.setDate(d.getDate() - ((d.getDay() + 6) % 7));
  if (unit === "month") d.setDate(1);
  return d.getTime();
}
function nextOf(t, unit) {
  const d = new Date(t);
  if (unit === "day") d.setDate(d.getDate() + 1);
  else if (unit === "week") d.setDate(d.getDate() + 7);
  else d.setMonth(d.getMonth() + 1);
  return d.getTime();
}
// The bars: unit "time" picks the smallest clock step that keeps the chart under about 24 bars;
// "day", "week" and "month" follow the calendar. Returns each bar's start and end.
function bucketsFor(times, unit) {
  const lo = Math.min(...times), hi = Math.max(...times);
  const starts = [];
  let word, kind;
  if (unit === "time") {
    const span = (hi - lo) / 60000;
    const [mins, w] = STEPS.find(([m]) => span / m <= 24) || STEPS[STEPS.length - 1];
    const size = mins * 60000;
    if (mins >= 1440) return bucketsFor(times, mins >= 10080 ? "week" : "day");
    for (let t = Math.floor(lo / size) * size; t <= hi; t += size) starts.push(t);
    word = w; kind = "clock";
  } else {
    for (let t = startOf(lo, unit); t <= hi; t = nextOf(t, unit)) starts.push(t);
    word = unit; kind = unit;
  }
  const ends = starts.map((t, i) => starts[i + 1] ?? (kind === "clock" ? t + (starts[1] - starts[0] || 3600000) : nextOf(t, kind)));
  return { starts, ends, word, kind };
}
function bucketLabel(t, kind) {
  const d = new Date(t);
  if (kind === "clock") return clockTime(t);
  if (kind === "month") return d.toLocaleDateString(undefined, { month: "short", year: "numeric" });
  const day = d.toLocaleDateString(undefined, { month: "short", day: "numeric" });
  return kind === "week" ? tr("Week of {date}", { date: day }) : day;
}

function TimeChart({ list }) {
  const d = useData();
  const { set } = useUi();
  const [measure, setMeasure] = useState("events");
  const [split, setSplit] = useState("outcome");
  const [unit, setUnit] = useState("time");
  const dated = list.map((t) => ({ t, at: stamp(t.received_at) })).filter((x) => x.at != null);
  if (!dated.length) return null;
  const b = bucketsFor(dated.map((x) => x.at), unit);
  const series = measure === "calls" ? GROUPS.map((g) => ({ key: g.id, label: g.label, color: g.color }))
    : split === "type" ? CAT_ORDER.map((k) => ({ key: k, label: CAT_NAME[k], color: CAT_COLOR[k] }))
    : OUTCOME_PARTS.map(([k, label, color]) => ({ key: k, label: tr(label), color }));
  const rows = b.starts.map((at, i) => ({ id: String(i), at, vals: series.map(() => 0), total: 0, events: [] }));
  for (const { t, at } of dated) {
    let i = b.starts.length - 1;
    while (i > 0 && b.starts[i] > at) i -= 1;
    const row = rows[i];
    row.events.push(t.event_id);
    if (measure === "calls") {
      for (const r of d.byEvent[t.event_id] || []) {
        const gi = GROUPS.findIndex((g) => g.tools.includes(r.tool));
        if (gi >= 0) { row.vals[gi] += 1; row.total += 1; }
      }
    } else {
      const key = split === "type" ? categoryOf(t) : d.outcome(t.event_id);
      const si = series.findIndex((s) => s.key === key);
      if (si >= 0) { row.vals[si] += 1; row.total += 1; }
    }
  }
  for (const r of rows) r.label = bucketLabel(r.at, b.kind);
  const busiest = rows.reduce((a, r) => (r.total > a.total ? r : a), rows[0]);
  const total = rows.reduce((a, r) => a + r.total, 0);
  const unitWord = measure === "calls" ? tr("tool calls") : tr("events");
  const first = rows[0].label;
  const last = b.kind === "clock" ? bucketLabel(b.ends[b.ends.length - 1] - 60000, "clock") : rows[rows.length - 1].label;
  return (
    <div className="card" style={{ marginBottom: 20 }}>
      <CardHead title={measure === "calls" ? tr("Actions over time") : tr("Events over time")}
        sub={rows.length === 1
          ? tr("{total} {unit} in {when}. Click the bar to open its first event.", { total: fmt(total), unit: unitWord, when: first })
          : tr("{total} {unit} from {first} to {last}, per {step}. Busiest: {when} with {n}. Click a bar to open its first event.", {
            total: fmt(total), unit: unitWord, first, last, step: tr(b.word), when: busiest.label, n: fmt(busiest.total) })}>
        <div className="controls">
          <Toggle value={unit} onChange={setUnit} aria-label={tr("Group by")}
            options={[["time", tr("Time")], ["day", tr("Day")], ["week", tr("Week")], ["month", tr("Month")]]} />
          <Toggle value={measure} onChange={setMeasure} options={[["events", tr("Events")], ["calls", tr("Tool calls")]]} />
          {measure === "events" && <Toggle value={split} onChange={setSplit} options={[["outcome", tr("By outcome")], ["type", tr("By type")]]} />}
        </div>
      </CardHead>
      <StackBars data={rows} series={series} unit={unitWord} height={220}
        ariaLabel={tr("Stacked bar chart of {unit} per {step}", { unit: unitWord, step: tr(b.word) })}
        onPick={(row) => set({ sel: row.events[0], resultOpen: true })} />
    </div>
  );
}

function ResultsList({ list }) {
  const d = useData();
  const { ui, set } = useUi();
  const all = d.traces;
  const f = ui.evFilter;
  const setF = (patch) => set((s) => ({ evFilter: { ...s.evFilter, ...patch }, evPage: 0 }));
  const pg = usePage(list, ui.sel);
  const kinds = Object.keys(KIND_LABEL).filter((k) => all.some((t) => kindsOf(t).includes(k)));
  const byOutcome = Object.fromEntries(OUTCOME_PARTS.map(([k]) => [k, 0]));
  const byCat = {};
  const tools = {};
  for (const t of all) {
    byOutcome[d.outcome(t.event_id)] += 1;
    const c = categoryOf(t);
    byCat[c] = (byCat[c] || 0) + 1;
    for (const r of d.byEvent[t.event_id] || []) tools[r.tool] = (tools[r.tool] || 0) + 1;
  }
  const calls = Object.values(tools).reduce((a, n) => a + n, 0);
  const catParts = CAT_ORDER.filter((k) => byCat[k]).map((k) => ({ label: CAT_NAME[k], value: byCat[k], color: CAT_COLOR[k] }));
  return (
    <>
      <TimeChart list={list} />
      <div className="card">
        <CardHead title={tr("Results · {n} events", { n: fmt(all.length) })}
          sub={tr("What the tower did with each event in the feed. Feed events have no answer key, so nothing here is graded.")} />
        <div className="grid g-charts">
          <div className="panel"><h4>{tr("Outcome")}</h4>
            <Pie caption={tr("events")} center={fmt(all.length)}
              parts={OUTCOME_PARTS.map(([k, label, color]) => ({ label: tr(label), value: byOutcome[k], color }))} /></div>
          <div className="panel"><h4>{tr("By incident type")}</h4>
            <Pie caption={tr("events")} center={fmt(all.length)} parts={catParts} /></div>
          <div className="panel"><h4>{tr("Actions · {n} tool calls", { n: fmt(calls) })}</h4><ToolBars counts={tools} /></div>
        </div>
      </div>

      <div className="card" style={{ marginTop: 20 }}>
        <CardHead title={tr("Events ({n} of {m})", { n: list.length, m: all.length })}
          sub={tr("Click an event to see its input, how it was read and what the tower did.")}>
          <div className="controls">
            <Toggle value={f.outcome} onChange={(v) => setF({ outcome: v })}
              options={[["all", tr("All")], ...OUTCOME_PARTS.map(([k, label]) => [k, tr(label)])]} />
            <Toggle value={f.kind} onChange={(v) => setF({ kind: v })}
              options={[["all", tr("All types")], ...kinds.map((k) => [k, KIND_LABEL[k]])]} />
          </div>
        </CardHead>
        <div className="scroll-x"><table>
          <thead><tr><th>{tr("Event")}</th><th>{tr("Input")}</th><th>{tr("What the tower did")}</th><th className="num">{tr("Calls")}</th><th>{tr("Outcome")}</th></tr></thead>
          <tbody>
            {pg.shown.map((t) => {
              const rows = d.byEvent[t.event_id] || [];
              return (
                <tr key={t.event_id} className="click" onClick={() => set({ sel: t.event_id, resultOpen: true })}>
                  <td><b>{t.event_id}</b><div style={{ marginTop: 4 }}><KindTag kind={categoryOf(t)} /></div></td>
                  <td><div className="clip">{t.text}</div></td>
                  <td><OutcomeLine o={eventOutcome(t, rows)} /></td>
                  <td className="num">{fmt(rows.length)}</td>
                  <td><Status kind={d.outcome(t.event_id)} /></td>
                </tr>
              );
            })}
            {!list.length && <tr><td colSpan={5} className="empty">{tr("No events match these filters.")}</td></tr>}
          </tbody>
        </table></div>
        <Pager pg={pg} />
      </div>
    </>
  );
}

const EFFECT_ROWS = [["Orders moved", "moved"], ["Dealers notified", "dealers"], ["Loaners assigned", "loaners"],
  ["Lots held", "lots"], ["Stop-sale vehicles", "stop_sale_vins"], ["Owners notified", "owners"]];

function ResultCase({ list, id }) {
  const d = useData();
  const { set } = useUi();
  const idx = list.findIndex((t) => t.event_id === id);
  const t = d.traceById[id];
  const back = <button className="btn" onClick={() => set({ resultOpen: false })}>← {tr("All results")}</button>;
  if (!t) return <div className="card empty">{tr("Event not found.")} {back}</div>;
  const prev = idx > 0 ? list[idx - 1] : null, next = idx >= 0 ? list[idx + 1] : null;
  const A = eventOutcome(t, d.byEvent[t.event_id] || []);
  return (
    <div className="card">
      <div className="card-head">
        <div className="controls">
          {back}
          {prev && <button className="btn" onClick={() => set({ sel: prev.event_id })}>‹ {prev.event_id}</button>}
          {next && <button className="btn" onClick={() => set({ sel: next.event_id })}>{next.event_id} ›</button>}
          <button className="btn" onClick={() => set({ evView: "feed" })}>{tr("Open in feed")}</button>
        </div>
        <Status kind={d.outcome(t.event_id)} />
      </div>
      <h3 style={{ margin: "0 0 14px" }}>{t.event_id} · {CAT_NAME[categoryOf(t)]}</h3>
      <div className="io">
        <div className="panel"><h4><span className="n">1</span>{tr("Input")} · {t.source || tr("message")}</h4><pre className="msg">{t.text}</pre></div>
        <div className="panel"><h4><span className="n">2</span>{tr("How it was read")}</h4>
          <Reading incidents={A.incidents} escalate={A.escalate} reasoning={A.reasoning} /></div>
        <div className="panel"><h4><span className="n">3</span>{tr("What the tower did")}</h4>
          <Effects o={A} actual />
          {t.summary && <p className="note" style={{ margin: "10px 0 0", color: "var(--text-2)" }}>{t.summary}</p>}</div>
      </div>
      <div className="section-title">{tr("Effect by effect")}</div>
      <div className="cmp cmp2">
        <div className="h">{tr("Effect")}</div><div className="h">{tr("Done")}</div>
        <div className="lbl">{tr("Escalate to a human")}</div><div>{A.escalate ? tr("yes") : tr("no")}</div>
        {EFFECT_ROWS.map(([l, k]) => (
          <Fragment key={k}><div className="lbl">{tr(l)}</div><div><Cell v={A[k]} /></div></Fragment>
        ))}
      </div>
    </div>
  );
}

export function EventResults({ list }) {
  const { ui } = useUi();
  if (ui.resultOpen && ui.sel) return <ResultCase list={list} id={ui.sel} />;
  return <ResultsList list={list} />;
}
