import { Icon } from "../lib/icons.jsx";
import { AGENT_ICON, GROUPS, TOOL_WORD, WRITE_TOOLS, fmt, kindWords, kindsOf, pctOf, plain, when } from "../lib/constants.js";
import { useData } from "../lib/data.jsx";
import { go, useTipProps, useUi } from "../lib/ui.jsx";
import { CardHead, CountUp, KindTag, StatCard, Status, Toggle } from "../components/common.jsx";
import { ImpactMap } from "../components/ImpactMap.jsx";
import { LiveTicker } from "../components/LiveRun.jsx";
import { useEventRun } from "../lib/run.jsx";
import { CallsChart, KindBars } from "../components/charts.jsx";
import { Page } from "./Page.jsx";
import { tr, trx } from "../lib/i18n.js";

export function useFilteredTraces() {
  const d = useData();
  const { ui } = useUi();
  const q = ui.q.trim().toLowerCase();
  if (!q) return d.traces;
  return d.traces.filter((t) => `${t.event_id} ${t.text} ${t.classification}`.toLowerCase().includes(q));
}

export function AgentCard({ a }) {
  return (
    <div className="agent panel">
      <div className={`who ${a.id === "coordinator" ? "coord" : ""}`}>
        <span className="badge-ico"><Icon name={AGENT_ICON[a.id] || "cpu"} /></span>
        <div><b>{a.title}</b><div className="note">{tr(a.handbook_rules.includes(",") ? "Handbook rules {rules}" : "Handbook rule {rules}", { rules: a.handbook_rules })}</div></div>
      </div>
      <p>{a.responsibility}</p>
      <div className="note">{tr("Takes {what}", { what: a.takes })}</div>
      <div className="tools">{a.tools.map((t) => <span className="tag" key={t}>{TOOL_WORD[t] || plain(t)}</span>)}</div>
    </div>
  );
}

function TimelineItem({ t }) {
  const d = useData();
  const o = d.outcome(t.event_id);
  const rows = d.byEvent[t.event_id] || [];
  const ic = o === "acted" ? "wrench" : o === "esc" ? "alert" : "minus";
  const color = o === "acted" ? "var(--good-text)" : o === "esc" ? "var(--warn)" : "var(--muted)";
  const writes = rows.filter((r) => r.ok && WRITE_TOOLS.has(r.tool)).length;
  const what = o === "acted" ? tr("{writes} changes made", { writes: writes }) : o === "esc" ? tr("Handed to a human") : tr("No action needed");
  return (
    <div className="tl">
      <div className="ico" style={{ color }}><Icon name={ic} /></div>
      <div><b>{t.event_id} · {what}</b><div className="when">{when(t.received_at)} · {kindWords(t)}</div></div>
    </div>
  );
}

function CallsTable({ data }) {
  return (
    <div className="scroll-x"><table>
      <thead><tr><th>{tr("Event")}</th>{GROUPS.map((g) => <th className="num" key={g.id}>{g.label}</th>)}<th className="num">{tr("Total")}</th></tr></thead>
      <tbody>{data.map((r) => <tr key={r.id}><td>{r.id}</td>{r.vals.map((v, i) => <td className="num" key={i}>{v}</td>)}<td className="num"><b>{r.total}</b></td></tr>)}</tbody>
    </table></div>
  );
}

// Customer promise impact: each customer order behind a moved build, its new build date against the
// date the customer was promised. Built by the server from the action log and the company records.
const BANDS = [
  ["on_track", "On track", "var(--good)", "Still built at least 2 days before the promised date"],
  ["tight", "Tight", "var(--warn)", "Built 0 to 1 day before the promised date"],
  ["late", "Late", "var(--bad)", "Built after the promised date"],
];
function PromiseCard({ p }) {
  const tipProps = useTipProps();
  const { set } = useUi();
  const total = p?.orders || 0;
  return (
    <div className="card promise">
      <CardHead title={tr("Customer promise impact")}
        sub={total ? tr("{orders} customer orders sit behind the {builds} builds the tower moved. Each new build date is checked against the date the customer was promised.", { orders: fmt(total), builds: fmt(p.builds_moved) })
          : tr("When the tower moves a build, each customer order behind it is checked against its promised date.")} />
      {!total ? <div className="empty">{tr("No customer orders affected yet.")}</div> : <>
        <div className="pr-head">
          <div><div className="pr-big">{fmt(p.bands.late)}</div><div className="note">{tr("orders now late")}</div></div>
          <div><div className="pr-big">{fmt(p.avg_delay_days)}<small>{tr(" days")}</small></div><div className="note">{tr("average build delay")}</div></div>
          <div><div className="pr-big">{fmt(p.max_days_late)}<small>{tr(" days")}</small></div><div className="note">{tr("latest past promise")}</div></div>
        </div>
        <div className="pr-bar" role="img" aria-label={BANDS.map(([k, l]) => `${tr(l)} ${p.bands[k]}`).join(", ")}>
          {BANDS.map(([k, label, color, hint]) => p.bands[k] > 0 && (
            <span key={k} style={{ flex: p.bands[k], background: color }} {...tipProps(`${tr(label)}: ${fmt(p.bands[k])} · ${tr(hint)}`)} />
          ))}
        </div>
        <div className="pr-legend">
          {BANDS.map(([k, label, color, hint]) => (
            <div key={k} title={tr(hint)}><i style={{ background: color }} /><span>{tr(label)}</span><b>{fmt(p.bands[k])}</b>
              <span className="note">{tr("{n} priority", { n: fmt(p.priority[k]) })}</span></div>
          ))}
        </div>
        <div className="pr-cover">
          <Icon name={p.late_priority && p.late_priority_with_loaner === p.late_priority ? "ok" : "alert"} />
          <span>{p.late_priority
            ? tr("{n} of {m} late Platinum and Gold customers have a loaner", { n: fmt(p.late_priority_with_loaner), m: fmt(p.late_priority) })
            : tr("No Platinum or Gold customer is late")}</span>
        </div>
        {p.most_at_risk.length > 0 && <>
          <div className="section-title" style={{ margin: "14px 0 6px" }}>{tr("Most at risk")}</div>
          <div className="pr-list">
            {p.most_at_risk.map((o) => (
              <button type="button" key={o.customer_order_id} className="pr-row" onClick={() => { set({ sel: o.event_id, openEvent: o.event_id }); go("#/events"); }}
                title={tr("Open {id} in the Event Center", { id: o.event_id })}>
                <b>{o.customer_order_id}</b><span className={`tier t-${o.tier.toLowerCase()}`}>{tr(o.tier)}</span>
                <span className="note">{o.model} · {o.dealer_id}</span>
                <span className="late">{tr(o.days_late === 1 ? "{n} day late" : "{n} days late", { n: o.days_late })}</span>
                <span className={o.loaner ? "ok" : "bad"}>{o.loaner ? tr("Loaner") : tr("No loaner")}</span>
              </button>
            ))}
          </div>
        </>}
      </>}
    </div>
  );
}

// The first thing a visitor sees: what this is, how well it works (from the saved test runs), and a
// button that plays the given events through the real tower, live. Online the numbers come only from
// the visitor's own test run of the demo events ("—" until they run one).
function Hero({ run }) {
  const d = useData();
  const { toast } = useUi();
  const job = run.job;
  const reader = (sid, label) => d.suiteById(sid)?.readers.find((r) => r.label === label);
  const blind = reader("blind100", tr("AI model")), rules = reader("blind100", tr("Rule reader")), given = reader("given", tr("AI model"));
  // Online the demo has a short set of the given events: count only their test results.
  const demoCases = d.demoSize && given?.cases ? given.cases.filter((c) => d.demoIds.includes(c.id)) : null;
  const tested = demoCases ? { passed: demoCases.filter((c) => c.verdict === "PASS").length, total: demoCases.length } : given;
  const pct = (r) => (r && r.total ? Math.round((r.passed / r.total) * 100) : null);
  const now = job?.current ? String(job.current) : "";
  const runDemo = async () => { const err = await run.start(); if (err) toast(err); };
  return (
    <section className="card hero2">
      <div className="hero2-bg" aria-hidden="true" />
      <div className="hero2-main">
        <div className="hero2-kicker">
          <span className={`live-dot${job?.running ? " on" : ""}`} />
          {job?.running ? tr("Live · {done} of {total} events · reading {now}", { done: fmt(job.done), total: fmt(job.total), now: now || "…" })
            : tr("Operations control tower · Hitachi Hack the Highway")}
        </div>
        <h1>{tr("Wacky Wheels Control Tower")}</h1>
        <p>{tr("An AI model reads every supplier, plant and dealer message. Code checks each reading against the company records, then agents reschedule production, notify dealers and assign loaners. Anything unclear goes to a person.")}</p>
        <div className="hero2-actions">
          <button type="button" className="btn primary hero2-run" onClick={runDemo} disabled={job?.running}>
            {job?.running ? <><span className="spin-dot" aria-hidden="true" />{tr("Running the demo")}</> : <><Icon name="play" />{tr("Run the demo")}</>}
          </button>
          <a className="btn" href="#/events">{tr("Open the Event Center")}</a>
          <span className="note">{d.demoSize ? tr("Plays {n} of the given events through the tower, live, one of each kind.", { n: fmt(d.demoSize) }) : tr("Plays the 15 given events through the tower, live.")}</span>
        </div>
        {job?.running && <div className="run-meter hero2-meter" aria-hidden="true"><span style={{ width: `${job.total ? (job.done / job.total) * 100 : 0}%` }} /></div>}
      </div>
      <div className="hero2-metrics">
        {!d.online && <div className="metric">
          <div className="metric-v">{pct(blind) != null ? <><CountUp value={pct(blind)} />%</> : "—"}</div>
          <div className="metric-k">{tr("accuracy on {n} unseen messages", { n: fmt(blind?.total || 100) })}</div>
          {pct(rules) != null && <div className="metric-s">{tr("vs {n}% rule-based", { n: pct(rules) })}</div>}
        </div>}
        <div className="metric">
          <div className="metric-v">{tested ? <><CountUp value={tested.passed} />/{tested.total}</> : "—"}</div>
          <div className="metric-k">{d.demoSize ? tr("demo events passed their tests") : tr("required test events passed")}</div>
        </div>
        <div className="metric">
          {d.online ? <>
            <div className="metric-v">{given?.avg_seconds ? `${given.avg_seconds} s` : "—"}</div>
            <div className="metric-k">{tr("per event, in your test run")}</div>
          </> : <>
            <div className="metric-v">{blind?.avg_seconds ? `${blind.avg_seconds} s` : "—"}</div>
            <div className="metric-k">{tr("per event, on a local 1.7B model")}</div>
          </>}
        </div>
      </div>
    </section>
  );
}

export default function Overview() {
  const d = useData();
  const { ui, set } = useUi();
  const traces = d.traces;
  const calls = d.log.length;
  const failed = d.log.filter((r) => !r.ok).length;
  const escal = d.log.filter((r) => r.tool === "escalate").length;
  const count = (o) => traces.filter((t) => d.outcome(t.event_id) === o).length;
  const acted = count("acted");
  const incidents = traces.flatMap((t) => t.incidents || []);
  const filtered = useFilteredTraces();
  const run = useEventRun();
  // The map follows the event just handled: the newest in a run, otherwise the newest real incident.
  const lastRun = run.job?.events?.[run.job.events.length - 1]?.id;
  const lastReal = [...traces].reverse().find((t) => (t.incidents || []).some((i) => i.plant_id))?.event_id;
  const focusId = (lastRun && d.traceById[lastRun] ? lastRun : null) || lastReal;
  const open = (id) => { set({ sel: id, openEvent: id }); go("#/events"); };
  const chartData = traces.map((t) => {
    const rows = d.byEvent[t.event_id] || [];
    const vals = GROUPS.map((g) => rows.filter((r) => g.tools.includes(r.tool)).length);
    return { id: t.event_id, vals, total: vals.reduce((a, b) => a + b, 0) };
  });

  const subtitle = <>
    <span><Icon name="check" />{tr("Monday 8 March 2027")}</span>
    <span>{trx("{n} events, {m} acted on", { n: <b>{fmt(traces.length)}</b>, m: <b>{fmt(acted)}</b> })}</span>
    <span>{trx("{n} tool calls", { n: <b>{fmt(calls)}</b> })}</span>
    <span className={failed ? "bad" : "ok"}>{trx("{n} failed", { n: <b>{fmt(failed)}</b> })}</span>
  </>;

  return (
    <Page title={tr("Overview")} subtitle={subtitle}>
      <Hero run={run} />

      <div className="grid g3" style={{ marginTop: 20 }}>
        <StatCard label={tr("Events handled")} value={traces.length} delta={tr("{acted} acted on", { acted: acted })} trend="up" icon="feed" />
        <StatCard label={tr("Tool calls")} value={calls} delta={failed ? tr("{failed} failed", { failed: failed }) : tr("None failed")} trend={failed ? "down" : "up"} icon="bolt" />
        <StatCard label={tr("Escalated to a human")} value={escal} delta={tr("Rumors & unclear reports")} trend="flat" icon="alert" />
      </div>

      <div className="grid g-map" style={{ marginTop: 20 }}>
        <div className="card">
          <CardHead title={tr("Impact map")} sub={tr("Plants, suppliers and dealers. Each plant shows its status; the event just handled lights up the places it touched.")} />
          <ImpactMap focusId={focusId} />
        </div>
        <LiveTicker job={run.job} />
      </div>

      <div className="grid g-hero two" style={{ marginTop: 20 }}>
        <PromiseCard p={d.promise} />
        <div className="card">
          <CardHead title={tr("What the messages were")} sub={tr("Incidents by type (a compound message counts each part)")} />
          <KindBars incidents={incidents} />
        </div>
      </div>

      {d.agents.length > 0 && (
        <div className="card" style={{ marginTop: 20 }}>
          <CardHead title={tr("Agent team")} sub={tr("One coordinator and three specialists. Specialists plan; the coordinator checks every planned call against the agent's tools, then runs it.")} />
          <div className="grid g-agents">{d.agents.map((a) => <AgentCard key={a.id} a={a} />)}</div>
        </div>
      )}

      <div className="grid" style={{ marginTop: 20 }}>
        <div className="card">
          <CardHead title={tr("Tool calls per event")} sub={tr("{calls} calls across {traces} events, grouped by job", { calls: fmt(calls), traces: traces.length })}>
            <Toggle value={ui.chartView} options={[["chart", tr("Chart")], ["table", tr("Table")]]} onChange={(v) => set({ chartView: v })} />
          </CardHead>
          <div className="legend" style={{ marginBottom: 10 }}>{GROUPS.map((g) => <span key={g.id}><i style={{ background: g.color }} />{g.label}</span>)}</div>
          {ui.chartView === "table" ? <CallsTable data={chartData} /> : <CallsChart data={chartData} onPick={open} />}
        </div>
      </div>

      <div className="grid g-table" style={{ marginTop: 20 }}>
        <div className="card">
          <CardHead title={tr("Events")} sub={tr("{acted} acted on · {esc} escalated · {none} left alone", { acted: acted, esc: count("esc"), none: count("none") })}>
            <a className="chip-btn" href="#/events">{tr("View all")}</a>
          </CardHead>
          <div className="scroll-x"><table>
            <thead><tr><th>{tr("Event")}</th><th>{tr("Message")}</th><th>{tr("Read as")}</th><th className="num">{tr("Calls")}</th><th>{tr("Outcome")}</th></tr></thead>
            <tbody>{filtered.map((t) => (
              <tr className="click" key={t.event_id} onClick={() => open(t.event_id)}>
                <td><b>{t.event_id}</b><div className="note">{t.source}</div></td>
                <td><div className="clip">{t.text}</div></td>
                <td>{kindsOf(t).map((k, i) => <KindTag key={i} kind={k} />)}</td>
                <td className="num">{fmt((d.byEvent[t.event_id] || []).length)}</td>
                <td><Status kind={d.outcome(t.event_id)} /></td>
              </tr>
            ))}</tbody>
          </table></div>
        </div>
        <div className="card">
          <CardHead title={tr("Audit trail")} sub={tr("What the tower did, event by event")} />
          <div className="timeline">{traces.map((t) => <TimelineItem key={t.event_id} t={t} />)}</div>
        </div>
      </div>
    </Page>
  );
}
