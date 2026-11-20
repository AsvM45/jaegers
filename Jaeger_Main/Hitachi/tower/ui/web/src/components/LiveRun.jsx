// Live activity while events are handled. LiveTicker (Overview): the newest events first, with the ones
// being read now. RunTimeline (Event Center): each event's steps, received -> read -> traced -> acted.
import { Icon } from "../lib/icons.jsx";
import { KIND_LABEL, fmt, kindsOf } from "../lib/constants.js";
import { useData } from "../lib/data.jsx";
import { useUi, go } from "../lib/ui.jsx";
import { CardHead, Status } from "./common.jsx";
import { tr } from "../lib/i18n.js";

// The run reports "acted", "escalated" or "no action"; the status badge says "acted", "esc" or "none".
const OUTCOME = { acted: "acted", escalated: "esc", "no action": "none" };
const reading = (job) => (job?.current ? String(job.current).split(", ").filter(Boolean) : []);

function runLine(job) {
  if (!job) return tr("Waiting for events.");
  if (job.running) return tr("{done} of {total} events handled", { done: fmt(job.done), total: fmt(job.total) });
  if (job.error) return tr("Stopped after {done} of {total} events.", { done: fmt(job.done), total: fmt(job.total) });
  if (job.done) return job.elapsed ? tr("Last run: {n} events in {s} s", { n: fmt(job.done), s: fmt(job.elapsed) }) : tr("Last run: {n} events", { n: fmt(job.done) });
  return tr("No run yet. Run the demo, or add an event.");
}

export function LiveTicker({ job }) {
  const { set } = useUi();
  const now = reading(job);
  const rows = [...(job?.events || [])].reverse().slice(0, 7);
  const open = (id) => { set({ sel: id, openEvent: id }); go("#/events"); };
  return (
    <div className="card live-card">
      <CardHead title={<span className="live-title"><span className={`live-dot${job?.running ? " on" : ""}`} />{tr("Live activity")}</span>}
        sub={runLine(job)} />
      {job?.running && <div className="run-meter" aria-hidden="true"><span style={{ width: `${job.total ? (job.done / job.total) * 100 : 0}%` }} /></div>}
      <ol className="ticker">
        {now.map((id) => (
          <li key={`r-${id}`} className="tick reading">
            <span className="spin-dot" aria-hidden="true" /><b>{id}</b><span className="note">{tr("Reading the message…")}</span>
          </li>
        ))}
        {rows.map((e) => (
          <li key={e.id} className="tick" onClick={() => open(e.id)}>
            <Status kind={OUTCOME[e.outcome] || e.outcome} /><b>{e.id}</b><span className="tick-sum">{e.summary}</span>
          </li>
        ))}
        {!now.length && !rows.length && <li className="tick empty-tick">{tr("Events appear here as the tower handles them.")}</li>}
      </ol>
    </div>
  );
}

// One event's steps, from what the tower recorded for it.
function steps(d, id, state) {
  if (state === "queued") return [["wait", tr("Waiting")]];
  if (state === "reading") return [["ok", tr("Received")], ["now", tr("Reading the message")]];
  const t = d.traceById[id];
  const rows = d.byEvent[id] || [];
  const kinds = t ? kindsOf(t).map((k) => KIND_LABEL[k]).filter(Boolean) : [];
  const paths = t ? (t.results || []).reduce((a, r) => a + (r.graph_paths || []).length, 0) : 0;
  const writes = rows.filter((r) => r.ok && r.tool !== "escalate").length;
  const escalated = rows.some((r) => r.tool === "escalate");
  return [
    ["ok", tr("Received")],
    ["ok", tr("Read as {kinds}", { kinds: kinds.join(" + ") || tr("noise") })],
    ["ok", paths ? tr("Traced {n} paths", { n: fmt(paths) }) : tr("Nothing to trace")],
    ["ok", writes ? tr("Took {n} actions", { n: fmt(writes) }) : escalated ? tr("Sent to a person") : tr("No action needed")],
  ];
}

export function RunTimeline({ job }) {
  const d = useData();
  const { set } = useUi();
  if (!job || (!job.running && !job.events?.length)) return null;
  const now = reading(job);
  const done = job.events || [];
  // The events of this run in order: finished, being read, then a few still waiting.
  const ids = (job.running ? [...done.map((e) => e.id), ...now] : done.map((e) => e.id)).slice(-6);
  const state = (id) => (now.includes(id) ? "reading" : done.some((e) => e.id === id) ? "done" : "queued");
  const rows = (
    <div className="rt-rows">
      {ids.map((id) => (
        <div key={id} className={`rt-row ${state(id)}`} onClick={() => set({ sel: id, evView: "feed" })}>
          <b className="rt-id">{id}</b>
          <ol className="rt-steps">
            {steps(d, id, state(id)).map(([s, label], k) => (
              <li key={`${id}-${k}-${s}`} className={`rt-step ${s}`} style={{ animationDelay: `${k * 90}ms` }}>
                {s === "ok" ? <Icon name="ok" /> : s === "now" ? <span className="spin-dot" aria-hidden="true" /> : <span className="rt-wait" />}
                <span>{label}</span>
              </li>
            ))}
          </ol>
        </div>
      ))}
    </div>
  );
  // While a run is going: open, step by step. Afterwards: one line that opens to the same steps.
  if (!job.running) return (
    <details className="card run-timeline run-done">
      <summary><span className="live-dot" /><b>{tr("Last run")}</b><span className="note">{runLine(job).replace(/^Last run: /, "")}</span>
        <span className="rt-open note">{tr("Show steps")}</span></summary>
      {rows}
    </details>
  );
  return (
    <div className="card run-timeline">
      <CardHead title={<span className="live-title"><span className="live-dot on" />{tr("Live run")}</span>} sub={runLine(job)} />
      <div className="run-meter" aria-hidden="true"><span style={{ width: `${job.total ? (job.done / job.total) * 100 : 0}%` }} /></div>
      {rows}
    </div>
  );
}
