import { Fragment, useEffect, useRef } from "react";
import { Icon } from "../lib/icons.jsx";
import { KIND_LABEL, TOOL_WORD, argText, fmt, kindWords, kindsOf, when } from "../lib/constants.js";
import { useData } from "../lib/data.jsx";
import { useUi } from "../lib/ui.jsx";
import { KindTag, Mono, Status, Toggle } from "../components/common.jsx";
import { Page } from "./Page.jsx";
import { useFilteredTraces } from "./Overview.jsx";

const NODE_TYPES = /^(Shipment|Part|Model|Plant|ProductionOrder|CustomerOrder|Dealer|Customer|Lot|Supplier|Vehicle)$/;

function GraphPath({ p }) {
  return (
    <div className="path">
      {p.map((step, k) => {
        const s = String(step), sp = s.indexOf(" ");
        const type = sp > 0 ? s.slice(0, sp) : "", rest = sp > 0 ? s.slice(sp + 1) : s;
        return (
          <Fragment key={k}>
            {k > 0 && <span className="arrow">→</span>}
            {NODE_TYPES.test(type) ? <span className="node"><small>{type}</small>{rest}</span> : <span className="note">{s}</span>}
          </Fragment>
        );
      })}
    </div>
  );
}

const FIELD_KEYS = ["plant_id", "part_id", "supplier_id", "shipment_id", "lot_id", "blocked_from", "blocked_until", "outage_start", "outage_end", "build_start", "build_end"];

function IncidentCard({ i }) {
  const fields = FIELD_KEYS.filter((k) => i[k]);
  return (
    <div className="inc">
      <div style={{ display: "flex", justifyContent: "space-between", gap: 10, alignItems: "center" }}>
        <KindTag kind={i.kind} /><span className="tag">read by {i.reader || "rules"}</span>
      </div>
      <div>{i.summary}</div>
      {fields.length > 0 && <div className="fields">{fields.map((k) => <span className="field" key={k}><span>{k.replace(/_/g, " ")}</span>{i[k]}</span>)}</div>}
      {i.model_reason && <div className="reasoning"><Icon name="cpu" /><span>{i.model_reason}</span></div>}
      <details>
        <summary>Reasoning trace ({(i.evidence || []).length} steps)</summary>
        <ul>{(i.evidence || []).map((e, k) => <li key={k}>{e}</li>)}</ul>
      </details>
    </div>
  );
}

function Handoffs({ t }) {
  const d = useData();
  const hs = t.handoffs || [];
  if (!hs.length) return <p className="note">This run predates agent handoffs. Re-run with <Mono>python start.py</Mono>.</p>;
  return (
    <div>
      {hs.map((h, k) => (
        <div className="hand" key={k}>
          <div className="route">{d.agentName(h.from)}<span className="arrow">→</span>{d.agentName(h.to)}</div>
          <div className="task">{h.task}</div>
          <div className="ret">
            {h.returned}
            {h.accepted != null && <> · <b>{h.accepted} accepted</b></>}
            {h.refused?.length > 0 && <> · <span className="bad">{h.refused.length} refused ({h.refused.join(", ")})</span></>}
          </div>
        </div>
      ))}
    </div>
  );
}

function EventDetail({ t }) {
  const d = useData();
  const { set } = useUi();
  const rows = d.byEvent[t.event_id] || [];
  const paths = (t.results || []).flatMap((r) => r.graph_paths || []);
  const calls = t.calls || [];
  const notes = d.outbox.filter((n) => n && n.event_id === t.event_id);
  const grouped = {};
  calls.forEach((c, i) => { (grouped[c.tool] ||= []).push({ c, ok: rows[i] ? rows[i].ok : true }); });
  const o = d.outcome(t.event_id);
  return (
    <>
      <div className="card-head">
        <div><h3>{t.event_id} · {kindWords(t)}</h3><p className="sub">{t.source} · received {when(t.received_at)}</p></div>
        <Status kind={o} />
      </div>
      <p className="quote">{t.text}</p>

      <div className="section-title">Summary</div>
      <div className="summary-box">{t.summary}</div>
      <p className="note" style={{ marginTop: 10 }}>Guardrail: {t.guardrail}</p>

      <div className="section-title">1 · Understanding</div>
      <div className="grid" style={{ gap: 12 }}>{(t.incidents || []).map((i, k) => <IncidentCard key={k} i={i} />)}</div>

      <div className="section-title">Agent handoffs</div>
      <Handoffs t={t} />

      <div className="section-title" style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 10 }}>
        <span>2 · Graph path{paths.length === 1 ? "" : "s"} ({fmt(paths.length)})</span>
        {paths.length > 0 && (
          <a className="btn" style={{ textTransform: "none", letterSpacing: 0 }} href="#/ontology"
            onClick={() => set({ orb: { view: "event", event: t.event_id, run: "" } })}><Icon name="graph" />View in orb graph</a>
        )}
      </div>
      {paths.length ? <>
        <div>{paths.slice(0, 6).map((p, k) => <GraphPath key={k} p={p} />)}</div>
        {paths.length > 6 && <details><summary>Show all {fmt(paths.length)} paths</summary>{paths.slice(6).map((p, k) => <GraphPath key={k} p={p} />)}</details>}
      </> : <p className="note">No graph traversal: nothing operational to trace.</p>}

      <div className="section-title">3 · Actions ({fmt(rows.length)} call{rows.length === 1 ? "" : "s"}, {rows.filter((r) => !r.ok).length} failed)</div>
      {calls.length ? Object.entries(grouped).map(([tool, items]) => (
        <details key={tool} open={items.length <= 3} style={{ marginBottom: 8 }}>
          <summary>{TOOL_WORD[tool] || tool} · {items.length}{items[0].c.agent ? ` · by ${d.agentName(items[0].c.agent)}` : ""}</summary>
          <div className="scroll-x"><table>
            <thead><tr><th>Arguments</th><th>Why</th><th>Result</th></tr></thead>
            <tbody>{items.map(({ c, ok }, k) => (
              <tr key={k}><td className="mono">{argText(c.args)}</td><td style={{ color: "var(--text-2)" }}>{c.reason}</td><td><Status kind={ok ? "ok" : "fail"} /></td></tr>
            ))}</tbody>
          </table></div>
        </details>
      )) : <p className="note">No tool calls. {o === "none" ? "Noise writes nothing." : ""}</p>}

      <div className="section-title">4 · Notifications ({fmt(notes.length)})</div>
      {notes.length ? <>
        <div className="scroll-x"><table>
          <thead><tr><th>Channel</th><th>To</th><th>Subject</th><th>Status</th></tr></thead>
          <tbody>{notes.slice(0, 40).map((n, k) => (
            <tr key={k}>
              <td><b>{n.route}</b><div className="note">{n.sink}</div></td>
              <td className="mono">{n.recipient_id || (n.to || []).join(", ") || "—"}</td>
              <td style={{ color: "var(--text-2)" }}>{n.subject || ""}</td>
              <td><span className="tag">{String(n.status || "").replace("_", "-")}</span></td>
            </tr>
          ))}</tbody>
        </table></div>
        {notes.length > 40 && <p className="note">{notes.length - 40} more in outbox.jsonl.</p>}
      </> : <p className="note">No channel messages. Run the tower with <Mono>--notify dry-run</Mono> to see what Slack, Teams and email would get.</p>}

    </>
  );
}

export default function Events() {
  const d = useData();
  const { ui, set } = useUi();
  const searched = useFilteredTraces();
  const f = ui.evFilter;
  const setF = (patch) => set((s) => ({ evFilter: { ...s.evFilter, ...patch } }));
  // Counts for each option are taken with the other filter applied, so they add up to what you'd see.
  const byOutcome = (o) => (t) => o === "all" || d.outcome(t.event_id) === o;
  const byKind = (k) => (t) => k === "all" || kindsOf(t).includes(k);
  const list = searched.filter(byOutcome(f.outcome)).filter(byKind(f.kind));
  const nOutcome = (o) => searched.filter(byKind(f.kind)).filter(byOutcome(o)).length;
  const nKind = (k) => searched.filter(byOutcome(f.outcome)).filter(byKind(k)).length;
  const kinds = Object.keys(KIND_LABEL).filter((k) => d.traces.some((t) => kindsOf(t).includes(k)));
  const filtered = f.outcome !== "all" || f.kind !== "all";
  const label = (word, n) => <>{word} <span className="ev-n">{n}</span></>;
  const sel = list.some((t) => t.event_id === ui.sel) ? ui.sel : list[0]?.event_id;
  // Keep the selected event visible in the list, however it was chosen (search, chart, table, list).
  const listRef = useRef(null), first = useRef(true);
  useEffect(() => {
    const box = listRef.current, item = box?.querySelector(`[data-ev="${sel}"]`);
    if (!item) return;
    const b = box.getBoundingClientRect(), r = item.getBoundingClientRect();
    if (r.top < b.top || r.bottom > b.bottom) {
      box.scrollTo({ top: box.scrollTop + r.top - b.top - 8, behavior: first.current ? "auto" : "smooth" });
    }
    if (!first.current && window.scrollY > 0) window.scrollTo({ top: 0, behavior: "smooth" });
    first.current = false;
  }, [sel, list.length]);
  const subtitle = <><span><b>{fmt(d.traces.length)}</b> events</span><span>Selected <b>{sel || "—"}</b></span></>;
  return (
    <Page title="Event feed" subtitle={subtitle}>
      {!d.traces.length ? <div className="card empty">{d.loadedAt ? "No events yet. Run python start.py." : "Loading…"}</div> : (
        <div className="ev-layout">
          <div className="ev-side">
          <div className="ev-filters panel">
            <div className="ev-flabel">Outcome</div>
            <Toggle value={f.outcome} onChange={(v) => setF({ outcome: v })} options={[
              ["all", label("All", nOutcome("all"))], ["acted", label("Acted", nOutcome("acted"))],
              ["esc", label("Escalated", nOutcome("esc"))], ["none", label("No action", nOutcome("none"))]]} />
            <div className="ev-flabel">Incident type</div>
            <div className="ev-kinds">
              {[["all", "All types"], ...kinds.map((k) => [k, KIND_LABEL[k]])].map(([k, word]) => (
                <button key={k} className={`ev-kind${f.kind === k ? " on" : ""}${k !== "all" ? ` k-${k}` : ""}`}
                  onClick={() => setF({ kind: k })} disabled={k !== "all" && !nKind(k)}>{label(word, nKind(k))}</button>
              ))}
            </div>
            <div className="ev-showing">
              Showing <b>{list.length}</b> of {d.traces.length}{ui.q.trim() && <> · matching “{ui.q.trim()}”</>}
              {(filtered || ui.q.trim()) && <button className="link-btn" onClick={() => set({ q: "", evFilter: { outcome: "all", kind: "all" } })}>Clear</button>}
            </div>
          </div>
          {!list.length ? <div className="panel empty">No events match these filters.</div> : (
          <div className="ev-list" ref={listRef}>
            {list.map((e) => (
              <div key={e.event_id} data-ev={e.event_id} className={`ev-item ${e.event_id === sel ? "on" : ""}`} onClick={() => set({ sel: e.event_id })}>
                <div className="row1"><b>{e.event_id}</b><Status kind={d.outcome(e.event_id)} /></div>
                <div>{kindsOf(e).map((k, i) => <KindTag key={i} kind={k} />)}</div>
                <div className="txt">{e.text}</div>
              </div>
            ))}
          </div>)}
          </div>
          {sel ? <div className="card"><EventDetail t={d.traceById[sel]} /></div>
               : <div className="card empty">Pick an event, or clear the filters.</div>}
        </div>
      )}
    </Page>
  );
}

