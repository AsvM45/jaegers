// The Escalated tab of the Event Center: every event the tower handed to a person, why, and what it
// needs to go ahead. Built from the traces and the action log the page already has.
import { Icon } from "../lib/icons.jsx";
import { KIND_LABEL, fmt, plain, when } from "../lib/constants.js";
import { useData } from "../lib/data.jsx";
import { useUi } from "../lib/ui.jsx";
import { CardHead, KindTag, Status } from "../components/common.jsx";
import { tr } from "../lib/i18n.js";

const REAL = new Set(["supplier_delay", "plant_outage", "quality_hold"]);
const FIELDS = [["plant_id", "Plant"], ["part_id", "Part"], ["supplier_id", "Supplier"], ["shipment_id", "Shipment"],
  ["lot_id", "Lot"], ["blocked_from", "Blocked from"], ["blocked_until", "Blocked until"], ["outage_start", "Down from"],
  ["outage_end", "Down until"], ["build_start", "Built from"], ["build_end", "Built until"]];

// Why an event went to a person, in one of four plain groups.
const WHY = [
  ["unconfirmed", "Unconfirmed report", "A rumor or report that can't be checked. Nothing was changed.", "var(--s4)"],
  ["details", "Missing details", "A real problem, but the message left out something the tower needs.", "var(--s2)"],
  ["failed", "Actions refused", "The tower planned actions, but the company systems refused every one.", "var(--bad)"],
  ["other", "Needs a person", "The tower could not settle the reading on its own.", "#6b7894"],
];

export function escalationOf(d, t) {
  const rows = d.byEvent[t.event_id] || [];
  const esc = rows.filter((r) => r.tool === "escalate");
  if (!esc.length) return null;
  const incidents = t.incidents || [];
  const questions = [...new Set(incidents.map((i) => i.question).filter(Boolean))];
  const writes = rows.filter((r) => r.tool !== "escalate");
  const why = incidents.some((i) => i.kind === "unconfirmed") && !questions.length ? "unconfirmed"
    : questions.length ? "details"
    : writes.length && writes.every((r) => !r.ok) ? "failed" : "other";
  return {
    why, questions,
    reasons: [...new Set(esc.map((r) => plain(r.args?.reason || "")).filter(Boolean))],
    understood: incidents.filter((i) => REAL.has(i.kind)),
    acted: writes.some((r) => r.ok),
  };
}

function Understood({ incidents }) {
  if (!incidents.length) return <p className="note" style={{ margin: 0 }}>{tr("Nothing it could act on.")}</p>;
  return incidents.map((i, k) => {
    const fields = FIELDS.filter(([key]) => i[key]);
    return (
      <div className="esc-inc" key={k}>
        <KindTag kind={i.kind} />
        {fields.length > 0 && <div className="fields">{fields.map(([key, label]) => <span className="field" key={key}><span>{tr(label)}</span>{i[key]}</span>)}</div>}
      </div>
    );
  });
}

export function EventEscalations({ list }) {
  const d = useData();
  const { set } = useUi();
  const all = d.traces.map((t) => ({ t, e: escalationOf(d, t) })).filter((x) => x.e);
  const shown = list.map((t) => ({ t, e: escalationOf(d, t) })).filter((x) => x.e);
  const byWhy = Object.fromEntries(WHY.map(([k]) => [k, all.filter((x) => x.e.why === k).length]));
  const waiting = all.filter((x) => x.e.questions.length).length;
  const partial = all.filter((x) => x.e.acted).length;
  const max = Math.max(1, ...Object.values(byWhy));
  const open = (id) => set({ sel: id, evView: "feed" });

  if (!all.length) return (
    <div className="card empty">
      <Icon name="ok" /> {tr("Nothing has been escalated. Rumors, unclear reports and anything the tower can't settle will appear here for a person to review.")}
    </div>
  );
  return (
    <>
      <div className="card">
        <CardHead title={tr("Escalated to a person · {n} events", { n: fmt(all.length) })}
          sub={tr("Events the tower would not act on alone. Each one says why, and what a person needs to confirm or supply.")} />
        <div className="grid g-charts">
          <div className="panel esc-stats">
            <div><div className="esc-big">{fmt(all.length)}<small> / {fmt(d.traces.length)}</small></div><div className="note">{tr("events escalated")}</div></div>
            <div><div className="esc-big">{fmt(waiting)}</div><div className="note">{tr("waiting on missing details")}</div></div>
            <div><div className="esc-big">{fmt(partial)}</div><div className="note">{tr("partly handled already")}</div></div>
          </div>
          <div className="panel"><h4>{tr("Why they were escalated")}</h4>
            <div className="bars">
              {WHY.map(([k, label, hint, color]) => (
                <div className="hbar" key={k} title={tr(hint)}>
                  <div className="lab"><span>{tr(label)}</span><b>{fmt(byWhy[k])}</b></div>
                  <div className="track"><div className="fill" style={{ width: `${(byWhy[k] / max) * 100}%`, background: color }} /></div>
                </div>
              ))}
            </div>
          </div>
          <div className="panel"><h4>{tr("What each group means")}</h4>
            <dl className="esc-key">{WHY.map(([k, label, hint]) => <div key={k}><dt>{tr(label)}</dt><dd>{tr(hint)}</dd></div>)}</dl>
          </div>
        </div>
      </div>

      <div className="card" style={{ marginTop: 20 }}>
        <CardHead title={tr("For review ({n} of {m})", { n: shown.length, m: all.length })}
          sub={tr("Newest last, as they arrived. Open one to see its full reading, graph paths and actions.")} />
        {!shown.length ? <div className="empty">{tr("No escalated events match these filters.")}</div> : (
          <div className="esc-list">
            {shown.map(({ t, e }) => {
              const group = WHY.find(([k]) => k === e.why);
              return (
                <article className="esc-card panel" key={t.event_id} style={{ "--c": group[3] }}>
                  <header>
                    <div><b>{t.event_id}</b><span className="note">{t.source} · {tr("received {when}", { when: when(t.received_at) })}</span></div>
                    <div className="esc-tags"><span className="esc-why">{tr(group[1])}</span><Status kind={e.acted ? "acted" : "esc"} /></div>
                  </header>
                  <p className="quote">{t.text}</p>
                  <div className="esc-grid">
                    <div><div className="section-title">{tr("Why it was escalated")}</div>
                      {e.reasons.length ? e.reasons.map((r, k) => <p key={k} className="esc-reason">{r}</p>) : <p className="note">{plain(t.summary)}</p>}</div>
                    <div><div className="section-title">{tr("What a person needs to answer")}</div>
                      {e.questions.length ? <ul className="esc-q">{e.questions.map((q, k) => <li key={k}>{q}</li>)}</ul>
                        : <p className="note" style={{ margin: 0 }}>{e.why === "unconfirmed" ? tr("Is this real? Confirm it with the source before anything changes.") : tr("Review the reading and decide what to do.")}</p>}</div>
                    <div><div className="section-title">{tr("What the tower understood")}</div><Understood incidents={e.understood} /></div>
                  </div>
                  <footer><button type="button" className="btn" onClick={() => open(t.event_id)}><Icon name="feed" />{tr("Open in Feed")}</button>
                    {e.understood.length > 0 && <span className="note">{e.understood.map((i) => KIND_LABEL[i.kind]).join(" + ")}</span>}</footer>
                </article>
              );
            })}
          </div>
        )}
      </div>
    </>
  );
}
