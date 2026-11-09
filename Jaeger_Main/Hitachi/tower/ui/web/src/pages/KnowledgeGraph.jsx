import { memo } from "react";
import { KIND_LABEL, fmt, kindWords } from "../lib/constants.js";
import { useData } from "../lib/data.jsx";
import { useUi } from "../lib/ui.jsx";
import { CardHead, Toggle } from "../components/common.jsx";
import { Page } from "./Page.jsx";

function orbSrc(orb) {
  const p = new URLSearchParams({ view: orb.view });
  if (orb.view === "event") { p.set("event", orb.event || ""); if (orb.run) p.set("run", orb.run); }
  return `/orb/?embed=1&bg=0b1437&data=${encodeURIComponent(`/api/knowledge_graph?${p}`)}`;
}

// Only reloads when its src changes, so typing in search or refreshing data leaves the graph alone.
const OrbFrame = memo(function OrbFrame({ src }) {
  return <iframe title="Orb knowledge graph" src={src}
    style={{ width: "100%", height: "min(72vh,720px)", border: 0, borderRadius: 14, display: "block", background: "#0b1437" }} />;
});

export default function KnowledgeGraph() {
  const d = useData();
  const { ui, set } = useUi();
  const o = d.onto;
  const withPaths = d.traces.filter((t) => (t.results || []).some((r) => (r.graph_paths || []).length));
  const orb = { ...ui.orb };
  if (orb.view === "event" && !orb.event) orb.event = withPaths[0]?.event_id || null;
  const runNote = orb.view === "event" && orb.run ? ` from test report ${orb.run}` : "";
  const subs = {
    network: "Every supplier, part, model, plant and dealer, and how they connect. Orders, customers and vehicles are left out: 17,000 records is too many orbs.",
    schema: "The ontology: one orb per node type, one link per edge type.",
    event: `The records the agents traced for ${orb.event || "an event"}${runNote}.`,
  };
  const src = orbSrc(orb);
  const subtitle = <>
    <span><b>{fmt(o?.nodes?.length || 0)}</b> node types</span><span><b>{fmt(o?.edges?.length || 0)}</b> edge types</span><span>from the company tables</span>
  </>;
  const extraOption = orb.run && !withPaths.some((t) => t.event_id === orb.event);

  return (
    <Page title="Knowledge graph" subtitle={subtitle}>
      <div className="card">
        <CardHead title="Knowledge graph" sub={`${subs[orb.view]} Drag an orb, click to focus its links, scroll to zoom. Click a type in the legend to hide it.`}>
          <div className="controls">
            <Toggle value={orb.view} options={[["network", "Network"], ["schema", "Schema"], ["event", "Event"]]}
              onChange={(v) => set((s) => ({ orb: { ...s.orb, view: v, run: v === "event" ? s.orb.run : "" } }))} />
            {orb.view === "event" && (
              <select className="chip-btn" aria-label="Event" value={extraOption ? "__run" : orb.event || ""}
                onChange={(e) => set((s) => ({ orb: { ...s.orb, event: e.target.value, run: "" } }))}>
                {extraOption && <option value="__run">{orb.event}</option>}
                {withPaths.map((t) => <option key={t.event_id} value={t.event_id}>{t.event_id} · {kindWords(t)}</option>)}
              </select>
            )}
            <a className="chip-btn" href={src} target="_blank" rel="noopener">Full screen ↗</a>
          </div>
        </CardHead>
        <OrbFrame src={src} />
      </div>

      {o ? (
        <div className="grid g-chart" style={{ marginTop: 20 }}>
          <div className="card">
            <CardHead title="Edge types" sub={`${o.nodes.length} node types, ${o.edges.length} edge types. Read as "from — relation → to".`} />
            <div className="scroll-x"><table>
              <thead><tr><th>From</th><th>Relation</th><th>To</th><th className="num">Links</th></tr></thead>
              <tbody>{o.edges.map((e, k) => <tr key={k}><td>{e.from}</td><td><b>{e.relation}</b></td><td>{e.to}</td><td className="num">{fmt(e.count)}</td></tr>)}</tbody>
            </table></div>
          </div>
          <div className="card">
            <CardHead title="Traversals the agents use" sub="The evidence chains shown on each event" />
            <div className="grid" style={{ gap: 12 }}>
              {Object.entries(o.traversals || {}).map(([k, v]) => (
                <div className="inc" key={k}><b>{KIND_LABEL[k] || k.replace(/_/g, " ")}</b><div className="note" style={{ color: "var(--text-2)" }}>{v}</div></div>
              ))}
            </div>
          </div>
        </div>
      ) : <div className="card empty" style={{ marginTop: 20 }}>No ontology export yet. Run <span className="mono">python -m tower.ontology</span>.</div>}
    </Page>
  );
}
