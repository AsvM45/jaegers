import { Fragment, useEffect, useLayoutEffect, useRef } from "react";
import { Icon } from "../lib/icons.jsx";
import { KIND_LABEL, TOOL_WORD, argText, fmt, kindWords, kindsOf, readerName, typeWords, when } from "../lib/constants.js";
import { useData } from "../lib/data.jsx";
import { useUi } from "../lib/ui.jsx";
import { KindTag, Status, Toggle } from "../components/common.jsx";
import { Page } from "./Page.jsx";
import { useFilteredTraces } from "./Overview.jsx";
import { EventResults } from "./EventResults.jsx";
import { Pager, usePage } from "../components/Pager.jsx";
import { EventEscalations, escalationOf } from "./EventEscalations.jsx";
import { exportEvents } from "../lib/exportEvents.js";
import { tr, trx } from "../lib/i18n.js";
import { ExportMenu } from "../components/ExportMenu.jsx";

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
            {NODE_TYPES.test(type) ? <span className="node"><small>{typeWords(type)}</small>{rest}</span> : <span className="note">{s}</span>}
          </Fragment>
        );
      })}
    </div>
  );
}

const FIELD_KEYS = ["plant_id", "part_id", "supplier_id", "shipment_id", "lot_id", "blocked_from", "blocked_until", "outage_start", "outage_end", "build_start", "build_end"];
const FIELD_LABEL = {
  plant_id: "plant id", part_id: "part id", supplier_id: "supplier id", shipment_id: "shipment id", lot_id: "lot id",
  blocked_from: "blocked from", blocked_until: "blocked until", outage_start: "outage start", outage_end: "outage end",
  build_start: "build start", build_end: "build end",
};

function IncidentCard({ i }) {
  const fields = FIELD_KEYS.filter((k) => i[k]);
  return (
    <div className="inc">
      <div style={{ display: "flex", justifyContent: "space-between", gap: 10, alignItems: "center" }}>
        <KindTag kind={i.kind} /><span className="tag">{tr("read by {reader}", { reader: i.reader || readerName("rules") })}</span>
      </div>
      <div>{i.summary}</div>
      {fields.length > 0 && <div className="fields">{fields.map((k) => <span className="field" key={k}><span>{tr(FIELD_LABEL[k])}</span>{i[k]}</span>)}</div>}
      {i.model_reason && <div className="reasoning"><Icon name="cpu" /><span>{i.model_reason}</span></div>}
      <details>
        <summary>{tr("Reasoning trace ({n} steps)", { n: (i.evidence || []).length })}</summary>
        <ul>{(i.evidence || []).map((e, k) => <li key={k}>{e}</li>)}</ul>
      </details>
    </div>
  );
}

function Handoffs({ t }) {
  const d = useData();
  const hs = t.handoffs || [];
  if (!hs.length) return <p className="note">{tr("No handoffs recorded for this event.")}</p>;
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
        <div><h3>{t.event_id} · {kindWords(t)}</h3><p className="sub">{t.source} · {tr("received {when}", { when: when(t.received_at) })}</p></div>
        <Status kind={o} />
      </div>
      <p className="quote">{t.text}</p>

      <div className="section-title">{tr("Summary")}</div>
      <div className="summary-box">{t.summary}</div>
      <p className="note" style={{ marginTop: 10 }}>{tr("Guardrail:")} {t.guardrail}</p>

      <div className="section-title">{tr("1 · Understanding")}</div>
      <div className="grid" style={{ gap: 12 }}>{(t.incidents || []).map((i, k) => <IncidentCard key={k} i={i} />)}</div>

      <div className="section-title">{tr("Agent handoffs")}</div>
      <Handoffs t={t} />

      <div className="section-title" style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 10 }}>
        <span>{tr(paths.length === 1 ? "2 · Graph path ({n})" : "2 · Graph paths ({n})", { n: fmt(paths.length) })}</span>
        {paths.length > 0 && (
          <a className="btn" style={{ textTransform: "none", letterSpacing: 0 }} href="#/ontology"
            onClick={() => set({ orb: { view: "event", event: t.event_id, run: "" } })}><Icon name="graph" />{tr("View in orb graph")}</a>
        )}
      </div>
      {paths.length ? <>
        <div>{paths.slice(0, 6).map((p, k) => <GraphPath key={k} p={p} />)}</div>
        {paths.length > 6 && <details><summary>{tr("Show all {n} paths", { n: fmt(paths.length) })}</summary>{paths.slice(6).map((p, k) => <GraphPath key={k} p={p} />)}</details>}
      </> : <p className="note">{tr("No graph traversal: nothing operational to trace.")}</p>}

      <div className="section-title">{tr(rows.length === 1 ? "3 · Actions ({n} call, {f} failed)" : "3 · Actions ({n} calls, {f} failed)", { n: fmt(rows.length), f: rows.filter((r) => !r.ok).length })}</div>
      {calls.length ? Object.entries(grouped).map(([tool, items]) => (
        <details key={tool} open={items.length <= 3} style={{ marginBottom: 8 }}>
          <summary>{TOOL_WORD[tool] || tool} · {items.length}{items[0].c.agent ? ` · by ${d.agentName(items[0].c.agent)}` : ""}</summary>
          <div className="scroll-x"><table>
            <thead><tr><th>{tr("Arguments")}</th><th>{tr("Why")}</th><th>{tr("Result")}</th></tr></thead>
            <tbody>{items.map(({ c, ok }, k) => (
              <tr key={k}><td className="mono">{argText(c.args)}</td><td style={{ color: "var(--text-2)" }}>{c.reason}</td><td><Status kind={ok ? "ok" : "fail"} /></td></tr>
            ))}</tbody>
          </table></div>
        </details>
      )) : <p className="note">No tool calls. {o === "none" ? "Noise writes nothing." : ""}</p>}

      <div className="section-title">{tr("4 · Notifications ({n})", { n: fmt(notes.length) })}</div>
      {notes.length ? <>
        <div className="scroll-x"><table>
          <thead><tr><th>{tr("Channel")}</th><th>{tr("To")}</th><th>{tr("Subject")}</th><th>{tr("Status")}</th></tr></thead>
          <tbody>{notes.slice(0, 40).map((n, k) => (
            <tr key={k}>
              <td><b>{n.route}</b><div className="note">{n.sink}</div></td>
              <td className="mono">{n.recipient_id || (n.to || []).join(", ") || "—"}</td>
              <td style={{ color: "var(--text-2)" }}>{n.subject || ""}</td>
              <td><span className="tag">{String(n.status || "").replace("_", "-")}</span></td>
            </tr>
          ))}</tbody>
        </table></div>
        {notes.length > 40 && <p className="note">{notes.length - 40} more not shown.</p>}
      </> : <p className="note">{d.outbox.length
        ? tr("No channel messages for this event.") : tr("No channel messages for this event.")}</p>}

    </>
  );
}

export default function Events() {
  const d = useData();
  const { ui, set, toast, visit } = useUi();
  const searched = useFilteredTraces();
  const f = ui.evFilter;
  const setF = (patch) => set((s) => ({ evFilter: { ...s.evFilter, ...patch }, evPage: 0 }));
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
  const pg = usePage(list, sel);
  // Keep the selected event visible inside the list when it is picked (search, chart, table, list).
  // Only the list moves, at once, and only when the selection changes: new events landing in the
  // feed never scroll anything, and the page itself is never scrolled.
  const listRef = useRef(null);
  useEffect(() => {
    const box = listRef.current, item = box?.querySelector(`[data-ev="${sel}"]`);
    if (!item) return;
    const b = box.getBoundingClientRect(), r = item.getBoundingClientRect();
    if (r.top < b.top || r.bottom > b.bottom) box.scrollTop += r.top - b.top - 8;
  }, [sel]); // eslint-disable-line react-hooks/exhaustive-deps
  const subtitle = <><span>{trx("{n} events", { n: <b>{fmt(d.traces.length)}</b> })}</span><span>{trx("Selected {id}", { id: <b>{sel || "—"}</b> })}</span></>;
  // Every visit lands on Results. A link to one event (Overview, search, Event add) opens that event there.
  // A redraw (language change) keeps the tab and the open event.
  useLayoutEffect(() => {
    set((s) => (s.openEvent ? { evView: "results", resultOpen: true, sel: s.openEvent, openEvent: null, evVisit: visit }
      : s.evVisit === visit ? {} : { evView: "results", resultOpen: false, evVisit: visit }));
  }, [set, visit]);
  const view = ["feed", "escalated"].includes(ui.evView) ? ui.evView : "results";
  const nEscalated = d.traces.filter((t) => escalationOf(d, t)).length;
  // What the export covers: the events the search and filters show, and a note saying which ones.
  const scope = [f.outcome !== "all" && `outcome ${({ acted: "acted", esc: "escalated", none: "no action" })[f.outcome]}`,
    f.kind !== "all" && `type ${KIND_LABEL[f.kind] || f.kind}`, ui.q.trim() && `search "${ui.q.trim()}"`].filter(Boolean).join(", ");
  const doExport = (format) => {
    if (!list.length) { toast(tr("No events to export.")); return; }
    const n = exportEvents(d, list, format, scope);
    toast(tr(n === 1 ? "Exported {n} event" : "Exported {n} events", { n }));
  };
  const tabs = d.traces.length > 0 && (
    <div className="ev-tabs">
      <Toggle value={view} onChange={(v) => set({ evView: v, resultOpen: false })}
        options={[["results", tr("Results")], ["feed", tr("Feed")],
          ["escalated", <>{tr("Escalated")} <span className="ev-n">{nEscalated}</span></>]]} aria-label={tr("Event center view")} />
      <span className="note">{view === "results" ? tr("What the tower did with each event. Not graded.")
        : view === "escalated" ? tr("Events handed to a person, why, and what they need to answer.")
        : tr("Every event as it came in, with its reasoning, graph paths and actions.")}</span>
      <div className="ev-export" role="group" aria-label={tr("Export event history")}>
        <ExportMenu label={scope ? tr("Export {n} shown", { n: list.length }) : tr("Export all {n}", { n: list.length })}
          disabled={!list.length} onPick={doExport} options={[
            ["log", tr("Readable log (.log)"), tr("Readable log: one block per event with every tool call")],
            ["csv", tr("Spreadsheet (.csv)"), tr("One row per event, for Excel or Sheets")],
            ["json", tr("Data (.json)"), tr("Every field and tool call, for other tools")],
          ]} />
      </div>
    </div>
  );
  return (
    <Page title={tr("Event center")} subtitle={subtitle}>
      {tabs}
      {!d.traces.length ? <div className="card empty">{d.loadedAt ? trx("No events yet. Go to {add} to send one, or to run the 15 given events.", { add: <a className="link" href="#/add">{tr("Add events")}</a> }) : "Loading…"}</div> : view === "results" ? <EventResults list={list} /> : view === "escalated" ? <EventEscalations list={list} /> : (
        <div className="ev-layout">
          <div className="ev-side">
          <div className="ev-filters panel">
            <div className="ev-flabel">{tr("Outcome")}</div>
            <Toggle value={f.outcome} onChange={(v) => setF({ outcome: v })} options={[
              ["all", label(tr("All"), nOutcome("all"))], ["acted", label(tr("Acted"), nOutcome("acted"))],
              ["esc", label(tr("Escalated"), nOutcome("esc"))], ["none", label(tr("No action"), nOutcome("none"))]]} />
            <div className="ev-flabel">{tr("Incident type")}</div>
            <div className="ev-kinds">
              {[["all", tr("All types")], ...kinds.map((k) => [k, KIND_LABEL[k]])].map(([k, word]) => (
                <button key={k} className={`ev-kind${f.kind === k ? " on" : ""}${k !== "all" ? ` k-${k}` : ""}`}
                  onClick={() => setF({ kind: k })} disabled={k !== "all" && !nKind(k)}>{label(word, nKind(k))}</button>
              ))}
            </div>
            <div className="ev-showing">{trx("Showing {n} of {m}", { n: <b>{list.length}</b>, m: d.traces.length })}{ui.q.trim() && <> · {tr("matching “{q}”", { q: ui.q.trim() })}</>}
              {(filtered || ui.q.trim()) && <button className="link-btn" onClick={() => set({ q: "", evFilter: { outcome: "all", kind: "all" } })}>{tr("Clear")}</button>}
            </div>
          </div>
          {!list.length ? <div className="panel empty">{tr("No events match these filters.")}</div> : (
          <>
          <div className="ev-list" ref={listRef}>
            {pg.shown.map((e) => (
              <div key={e.event_id} data-ev={e.event_id} className={`ev-item ${e.event_id === sel ? "on" : ""}`} onClick={() => set({ sel: e.event_id })}>
                <div className="row1"><b>{e.event_id}</b><Status kind={d.outcome(e.event_id)} /></div>
                <div>{kindsOf(e).map((k, i) => <KindTag key={i} kind={k} />)}</div>
                <div className="txt">{e.text}</div>
              </div>
            ))}
          </div>
          <Pager pg={pg} />
          </>)}
          </div>
          {sel ? <div className="card"><EventDetail t={d.traceById[sel]} /></div>
               : <div className="card empty">{tr("Pick an event, or clear the filters.")}</div>}
        </div>
      )}
    </Page>
  );
}

