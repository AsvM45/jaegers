import { memo, useCallback, useEffect, useRef, useState } from "react";
import { Loader } from "../components/Loading.jsx";
import { Select } from "../components/Select.jsx";
import { KIND_LABEL, fmt, kindWords, relationWords, typeWords } from "../lib/constants.js";
import { useData } from "../lib/data.jsx";
import { useUi } from "../lib/ui.jsx";
import { CardHead, Toggle } from "../components/common.jsx";
import { Page } from "./Page.jsx";
import { tr, trx } from "../lib/i18n.js";

const VIEWS = ["network", "schema", "event"];

// rev changes when the feed gains events, so an event view refreshes as events arrive.
function orbSrc(orb, rev) {
  const p = new URLSearchParams({ view: orb.view });
  if (orb.view === "event") { p.set("event", orb.event || "all"); if (orb.run) p.set("run", orb.run); p.set("rev", rev); }
  return `/orb/?embed=1&bg=0b1437&data=${encodeURIComponent(`/api/knowledge_graph?${p}`)}`;
}

// Only reloads when its src changes, so typing in search or refreshing data leaves the graph alone.
// The orb page posts {source: "orb", type: "ready" | "error"} when its layout is done. A new view shows
// a loader until then (and gives up waiting after 20 s, in case a message is lost). A refresh of the
// same view (new events landed) loads behind the current graph and swaps in when ready: no flash.
// shown: this view is the one on screen. Hidden views stay loaded (switching back is instant) but are told
// to stop drawing, as is any graph scrolled out of sight. onReady: the newest graph finished its layout.
const OrbFrame = memo(function OrbFrame({ src, view, shown = true, onReady }) {
  const [frames, setFrames] = useState([{ src, view, state: "loading" }]);
  const refs = useRef({});
  useEffect(() => {
    setFrames((fs) => {
      const live = fs[fs.length - 1];
      if (live.src === src) return fs;
      // Same view with more data: keep the shown graph until the new one is ready.
      const keep = live.view === view && live.state === "ready" ? [live] : [];
      return [...keep, { src, view, state: "loading" }];
    });
  }, [src, view]);
  useEffect(() => {
    const on = (e) => {
      if (e.data?.source !== "orb") return;
      const hit = Object.entries(refs.current).find(([, el]) => el?.contentWindow === e.source)?.[0];
      if (!hit) return;
      setFrames((fs) => {
        const next = fs.map((f) => (f.src === hit ? { ...f, state: e.data.type === "error" ? "error" : "ready" } : f));
        const newest = next[next.length - 1];
        return newest.state === "loading" ? next : [newest];   // the new graph is up: drop the old one
      });
    };
    window.addEventListener("message", on);
    return () => window.removeEventListener("message", on);
  }, []);
  useEffect(() => {
    const timer = setTimeout(() => setFrames((fs) => [{ ...fs[fs.length - 1], state: "ready" }]), 20000);
    return () => clearTimeout(timer);
  }, [src]);
  // Tell each graph how much of its bottom is hidden below the window, so its zoom buttons stay on
  // screen (bottom-right of what you can see) while the graph is taller than the window.
  const wrap = useRef(null);
  const shownRef = useRef(shown);
  shownRef.current = shown;
  const sendRef = useRef(() => {});
  useEffect(() => {
    let raf = 0, onScreen = true;
    const send = () => {
      raf = 0;
      const box = wrap.current?.getBoundingClientRect();
      if (!box) return;
      const bottom = Math.max(0, box.bottom - window.innerHeight);
      const on = shownRef.current && onScreen;
      for (const el of Object.values(refs.current)) {
        try {
          el?.contentWindow?.postMessage({ source: "dashboard", type: "inset", bottom }, location.origin);
          el?.contentWindow?.postMessage({ source: "dashboard", type: "active", on }, location.origin);
        } catch { /* frame gone */ }
      }
    };
    sendRef.current = send;
    // Stop drawing while the graph is scrolled out of sight.
    const seen = new IntersectionObserver(([entry]) => { onScreen = entry.isIntersecting; send(); });
    if (wrap.current) seen.observe(wrap.current);
    const soon = () => { if (!raf) raf = requestAnimationFrame(send); };
    window.addEventListener("scroll", soon, { passive: true });
    window.addEventListener("resize", soon);
    soon();
    const timer = setInterval(send, 1000);   // a new frame finishing its load also needs the number
    return () => { seen.disconnect(); window.removeEventListener("scroll", soon); window.removeEventListener("resize", soon); clearInterval(timer); if (raf) cancelAnimationFrame(raf); };
  }, []);
  useEffect(() => { sendRef.current(); }, [shown]);
  const newest = frames[frames.length - 1];
  useEffect(() => { if (newest.state !== "loading") onReady?.(); }, [newest.state]); // eslint-disable-line react-hooks/exhaustive-deps
  const covering = newest.state === "loading" && frames.length === 1;
  return (
    <div ref={wrap} className={`orb-wrap ${covering ? "loading" : newest.state}${shown ? "" : " orb-hidden"}`} aria-hidden={!shown}>
      {frames.map((f, i) => (
        <iframe key={f.src} ref={(el) => { refs.current[f.src] = el; }} title={tr("Orb knowledge graph")} src={f.src}
          onLoad={() => sendRef.current()} tabIndex={shown ? 0 : -1}
          className={i < frames.length - 1 || f.state === "ready" || covering ? "" : "orb-next"} />
      ))}
      {covering && (
        <div className="orb-cover">
          <Loader title={tr("Loading the knowledge graph")} detail={tr("Placing every record and the links between them…")} />
        </div>
      )}
    </div>
  );
});

export default function KnowledgeGraph() {
  const d = useData();
  const { ui, set } = useUi();
  const o = d.onto;
  const withPaths = d.traces.filter((t) => (t.results || []).some((r) => (r.graph_paths || []).length));
  const orb = { ...ui.orb };
  // Event view: every event's records by default; it grows as events arrive.
  if (orb.view === "event" && !orb.event) orb.event = "all";
  const rev = `${d.traces.length}:${withPaths.length}`;
  const runNote = orb.view === "event" && orb.run ? tr(" from test report {run}", { run: orb.run }) : "";
  const subs = {
    network: "Every supplier, part, model, plant and dealer, and how they connect. Orders, customers and vehicles are left out: 17,000 records is too many orbs.",
    schema: "The ontology: one orb per node type, one link per edge type.",
    event: orb.event === "all" ? tr("The records the agents traced for every event in the feed. New events appear as they arrive.")
      : tr("The records the agents traced for {event}{runNote}.", { event: orb.event, runNote: runNote }),
  };
  const src = orbSrc(orb, rev);
  // Each view's graph stays loaded once opened, so switching between them is instant. Once the first
  // view is ready, the other two load quietly behind it.
  const [warm, setWarm] = useState(false);
  const opened = useRef(new Set());
  const warmUp = useCallback(() => setWarm(true), []);
  const subtitle = <>
    <span>{trx("{n} node types", { n: <b>{fmt(o?.nodes?.length || 0)}</b> })}</span><span>{trx("{n} edge types", { n: <b>{fmt(o?.edges?.length || 0)}</b> })}</span><span>{tr("from the company tables")}</span>
  </>;
  const extraOption = orb.run && !withPaths.some((t) => t.event_id === orb.event);

  return (
    <Page title={tr("Knowledge graph")} subtitle={subtitle}>
      <div className="card">
        <CardHead title={tr("Knowledge graph")} sub={tr("{view} Drag an orb, click to focus its links, scroll to zoom. Click a type in the legend to hide it.", { view: subs[orb.view] })}>
          <div className="controls">
            <Toggle value={orb.view} options={[["network", tr("Network")], ["schema", tr("Schema")], ["event", tr("Event")]]}
              onChange={(v) => set((s) => ({ orb: { ...s.orb, view: v, run: v === "event" ? s.orb.run : "" } }))} />
            {orb.view === "event" && (
              <Select size="sm" label={tr("Event")} width={260} value={extraOption ? "__run" : orb.event || ""} placeholder={tr("Choose an event")}
                onChange={(v) => set((s) => ({ orb: { ...s.orb, event: v, run: "" } }))}
                options={[["all", tr("All events"), withPaths.length ? tr(withPaths.length === 1 ? "{n} event" : "{n} events", { n: withPaths.length }) : ""],
                  ...(extraOption ? [["__run", orb.event]] : []), ...withPaths.map((t) => [t.event_id, t.event_id, kindWords(t)])]} />
            )}
            <a className="chip-btn" href={src} target="_blank" rel="noopener">{tr("Full screen ↗")}</a>
          </div>
        </CardHead>
        <div className="orb-stack">
          {VIEWS.filter((v) => v === orb.view || warm || opened.current.has(v)).map((v) => {
            opened.current.add(v);
            const o = v === orb.view ? orb : v === "event" ? { view: "event", event: ui.orb.event || "all", run: ui.orb.run } : { view: v };
            return <OrbFrame key={v} src={v === orb.view ? src : orbSrc(o, rev)} view={`${v}:${o.event || ""}:${o.run || ""}`}
              shown={v === orb.view} onReady={v === orb.view ? warmUp : undefined} />;
          })}
        </div>
      </div>

      {o ? (
        <div className="grid g-chart" style={{ marginTop: 20 }}>
          <div className="card">
            <CardHead title={tr("Edge types")} sub={tr("{nodes} node types, {edges} edge types. Read as \"from — relation → to\".", { nodes: o.nodes.length, edges: o.edges.length })} />
            <div className="scroll-x"><table>
              <thead><tr><th>{tr("From")}</th><th>{tr("Relation")}</th><th>{tr("To")}</th><th className="num">{tr("Links")}</th></tr></thead>
              <tbody>{o.edges.map((e, k) => <tr key={k}><td>{typeWords(e.from)}</td><td><b>{relationWords(e.relation)}</b></td><td>{typeWords(e.to)}</td><td className="num">{fmt(e.count)}</td></tr>)}</tbody>
            </table></div>
          </div>
          <div className="card">
            <CardHead title={tr("Traversals the agents use")} sub={tr("The evidence chains shown on each event")} />
            <div className="grid" style={{ gap: 12 }}>
              {Object.entries(o.traversals || {}).map(([k, v]) => (
                <div className="inc" key={k}><b>{KIND_LABEL[k] || k.replace(/_/g, " ")}</b><div className="note" style={{ color: "var(--text-2)" }}>{v}</div></div>
              ))}
            </div>
          </div>
        </div>
      ) : <div className="card empty" style={{ marginTop: 20 }}>{tr("The record types are not available yet.")}</div>}
    </Page>
  );
}
