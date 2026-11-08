import { Icon } from "../lib/icons.jsx";
import { AGENT_ICON, GROUPS, WRITE_TOOLS, fmt, kindWords, kindsOf, pctOf, when } from "../lib/constants.js";
import { useData } from "../lib/data.jsx";
import { go, useUi } from "../lib/ui.jsx";
import { CardHead, KindTag, StatCard, Status, Toggle } from "../components/common.jsx";
import { CallsChart, Gauge, KindBars, Ring } from "../components/charts.jsx";
import { Page } from "./Page.jsx";

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
        <div><b>{a.title}</b><div className="note">Handbook rule{a.handbook_rules.includes(",") ? "s" : ""} {a.handbook_rules}</div></div>
      </div>
      <p>{a.responsibility}</p>
      <div className="note">Takes {a.takes}</div>
      <div className="tools">{a.tools.map((t) => <span className="tag" key={t}>{t}</span>)}</div>
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
  const what = o === "acted" ? `${writes} changes made` : o === "esc" ? "Handed to a human" : "No action needed";
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
      <thead><tr><th>Event</th>{GROUPS.map((g) => <th className="num" key={g.id}>{g.label}</th>)}<th className="num">Total</th></tr></thead>
      <tbody>{data.map((r) => <tr key={r.id}><td>{r.id}</td>{r.vals.map((v, i) => <td className="num" key={i}>{v}</td>)}<td className="num"><b>{r.total}</b></td></tr>)}</tbody>
    </table></div>
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
  const { passed, total } = d.testTotals;
  const pct = pctOf(passed, total);
  const incidents = traces.flatMap((t) => t.incidents || []);
  const viaModel = incidents.filter((i) => i.reader && i.reader !== "rules").length;
  const overLists = incidents.filter((i) => (i.evidence || []).some((e) => String(e).startsWith("rule word lists read"))).length;
  const filtered = useFilteredTraces();
  const open = (id) => { set({ sel: id }); go("#/events"); };
  const chartData = traces.map((t) => {
    const rows = d.byEvent[t.event_id] || [];
    const vals = GROUPS.map((g) => rows.filter((r) => g.tools.includes(r.tool)).length);
    return { id: t.event_id, vals, total: vals.reduce((a, b) => a + b, 0) };
  });

  const subtitle = <>
    <span><Icon name="check" />Monday 8 March 2027</span>
    <span><b>{fmt(traces.length)}</b> events, <b>{fmt(acted)}</b> acted on</span>
    <span><b>{fmt(calls)}</b> tool calls</span>
    <span className={failed ? "bad" : "ok"}><b>{fmt(failed)}</b> failed</span>
  </>;

  return (
    <Page title="Overview" subtitle={subtitle} showRefresh={false}>
      <div className="grid g4">
        <StatCard label="Events handled" value={traces.length} delta={`${acted} acted on`} trend="up" icon="feed" />
        <StatCard label="Tool calls" value={calls} delta={failed ? `${failed} failed` : "None failed"} trend={failed ? "down" : "up"} icon="bolt" />
        <StatCard label="Escalated to a human" value={escal} delta="Rumors & unclear reports" trend="flat" icon="alert" />
        <StatCard label="Test cases passed" value={total ? `${passed} / ${total}` : "—"} delta={total ? `${pct}% pass rate` : "No reports yet"}
          trend={total ? (pct === 100 ? "up" : pct >= 80 ? "warn" : "down") : "flat"} icon="shield" />
      </div>

      <div className="grid g-hero" style={{ marginTop: 20 }}>
        <div className="card hero">
          <div>
            <div className="k">Operations control tower · Monday 8 March 2027</div>
            <h2>Wacky Wheels Co.</h2>
            <p>Every message is read, traced through the knowledge graph, and fixed with the enterprise tools, following the policy handbook. Unclear reports go to a human.</p>
            <div className="model-pill"><span className="dot" />{d.model ? `Reader: ${d.model} + rule check` : "Reader: rules only"}</div>
          </div>
          <a className="go" href="#/events">Open the event feed →</a>
        </div>

        <div className="card">
          <CardHead title="Test pass rate" sub={`All test suites, ${d.model || "rules"} reader`} />
          <div className="gauge-wrap">
            <Gauge pct={pct} />
            <div className="gauge-cap"><b>{fmt(passed)}</b> of {fmt(total)} test cases passed</div>
            <a className="btn" href="#/tests" style={{ marginTop: 8 }}>Open the tests →</a>
          </div>
        </div>

        <div className="card">
          <CardHead title="Who read the messages" sub={`Which reader's interpretation the tower acted on, across ${fmt(traces.length)} events`} />
          <div className="reader">
            <Ring frac={incidents.length ? viaModel / incidents.length : 0} label={`${pctOf(viaModel, incidents.length)}%`} caption="model" />
            <div className="mini">
              <div className="tile" title="Incidents where the model's checked reading was used"><div className="k">Model</div><div className="v">{viaModel}<small> of {incidents.length}</small></div></div>
              <div className="tile" title="Incidents where the rule reader's reading was used"><div className="k">Rules</div><div className="v">{incidents.length - viaModel}</div></div>
              <div className="tile" title="Incidents the model caught that the word lists missed"><div className="k">Model only</div><div className="v">{overLists}</div></div>
            </div>
          </div>
        </div>
      </div>

      {d.agents.length > 0 && (
        <div className="card" style={{ marginTop: 20 }}>
          <CardHead title="Agent team" sub="One coordinator and three specialists. Specialists plan; the coordinator checks every planned call against the agent's tools, then runs it." />
          <div className="grid g-agents">{d.agents.map((a) => <AgentCard key={a.id} a={a} />)}</div>
        </div>
      )}

      <div className="grid g-chart" style={{ marginTop: 20 }}>
        <div className="card">
          <CardHead title="Tool calls per event" sub={`${fmt(calls)} calls across ${traces.length} events, grouped by job`}>
            <Toggle value={ui.chartView} options={[["chart", "Chart"], ["table", "Table"]]} onChange={(v) => set({ chartView: v })} />
          </CardHead>
          <div className="legend" style={{ marginBottom: 10 }}>{GROUPS.map((g) => <span key={g.id}><i style={{ background: g.color }} />{g.label}</span>)}</div>
          {ui.chartView === "table" ? <CallsTable data={chartData} /> : <CallsChart data={chartData} onPick={open} />}
        </div>
        <div className="card">
          <CardHead title="What the messages were" sub="Incidents by type (a compound message counts each part)" />
          <KindBars incidents={incidents} />
        </div>
      </div>

      <div className="grid g-table" style={{ marginTop: 20 }}>
        <div className="card">
          <CardHead title="Events" sub={`${acted} acted on · ${count("esc")} escalated · ${count("none")} left alone`}>
            <a className="chip-btn" href="#/events">View all</a>
          </CardHead>
          <div className="scroll-x"><table>
            <thead><tr><th>Event</th><th>Message</th><th>Read as</th><th className="num">Calls</th><th>Outcome</th></tr></thead>
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
          <CardHead title="Audit trail" sub="What the tower did, event by event" />
          <div className="timeline">{traces.map((t) => <TimelineItem key={t.event_id} t={t} />)}</div>
        </div>
      </div>
    </Page>
  );
}
