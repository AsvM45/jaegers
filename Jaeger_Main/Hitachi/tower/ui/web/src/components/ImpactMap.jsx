// The impact map: every plant, supplier and dealer on a US map. Each plant shows its status (running,
// down, or affected by a delay or hold). The event just handled lights up the supplier and dealers it
// touched, and its plant pulses twice. No lines are drawn between places.
import { useEffect, useMemo, useRef, useState } from "react";
import { Icon } from "../lib/icons.jsx";
import { geoAlbers, geoPath } from "d3-geo";
import { feature, mesh } from "topojson-client";
import us from "us-atlas/states-albers-10m.json";
import { getJSON, useData } from "../lib/data.jsx";
import { useTipProps } from "../lib/ui.jsx";
import { KIND_LABEL, fmt } from "../lib/constants.js";
import { tr } from "../lib/i18n.js";

// The us-atlas file is already projected (Albers USA, scale 1300, 975 x 610); points use the same projection.
const project = geoAlbers().scale(1300).translate([487.5, 305]);
const drawn = geoPath();
const STATES = drawn(feature(us, us.objects.states));
const BORDERS = drawn(mesh(us, us.objects.states, (a, b) => a !== b));
const OUTLINE = drawn(mesh(us, us.objects.nation));
const MAX_DEALER_ROUTES = 14;
// The map's own coordinates (the viewBox), and how far it zooms in.
const VB = { x: -10, y: 0, w: 985, h: 650 };
const MAX_ZOOM = 8;
const clampView = ({ k, tx, ty }) => {
  k = Math.min(MAX_ZOOM, Math.max(1, k));
  // Keep the map filling the frame: never pan past its edges.
  const minX = (VB.x + VB.w) * (1 - k), maxX = VB.x * (1 - k), minY = (VB.y + VB.h) * (1 - k), maxY = VB.y * (1 - k);
  return { k, tx: Math.min(maxX, Math.max(minX, tx)), ty: Math.min(maxY, Math.max(minY, ty)) };
};
const FIT = { k: 1, tx: 0, ty: 0 };
const STATUS = {
  running: ["Running", "var(--good)"],
  affected: ["Affected", "var(--warn)"],
  down: ["Down", "var(--bad)"],
};


export function ImpactMap({ focusId }) {
  const d = useData();
  const tipProps = useTipProps();
  const [places, setPlaces] = useState(null);
  useEffect(() => { getJSON("/api/network_map", null).then(setPlaces); }, []);

  // Zoom and pan: buttons, pinch or Cmd/Ctrl + scroll toward the cursor, drag to move, double-click to zoom in.
  // A plain scroll still scrolls the page.
  const [view, setView] = useState(FIT);
  const svgRef = useRef(null), drag = useRef(null);
  const toMap = (clientX, clientY) => {
    const svg = svgRef.current;
    const pt = svg.createSVGPoint(); pt.x = clientX; pt.y = clientY;
    return pt.matrixTransform(svg.getScreenCTM().inverse());
  };
  const zoomAt = (factor, at) => setView((v) => {
    const c = at || { x: VB.x + VB.w / 2, y: VB.y + VB.h / 2 };
    const k = Math.min(MAX_ZOOM, Math.max(1, v.k * factor));
    return clampView({ k, tx: c.x - (c.x - v.tx) * (k / v.k), ty: c.y - (c.y - v.ty) * (k / v.k) });
  });
  useEffect(() => {
    const svg = svgRef.current;
    if (!svg) return undefined;
    const onWheel = (e) => {
      if (!e.ctrlKey && !e.metaKey) return;   // pinch on a trackpad arrives as Ctrl + wheel
      e.preventDefault();
      zoomAt(Math.exp(-e.deltaY * 0.01), toMap(e.clientX, e.clientY));
    };
    svg.addEventListener("wheel", onWheel, { passive: false });
    return () => svg.removeEventListener("wheel", onWheel);
  }, [places]); // eslint-disable-line react-hooks/exhaustive-deps
  const onDown = (e) => {
    if (view.k === 1 || e.button !== 0) return;
    drag.current = { x: e.clientX, y: e.clientY, v: view, per: VB.w / svgRef.current.clientWidth };
    svgRef.current.setPointerCapture(e.pointerId);
  };
  const onMove = (e) => {
    const g = drag.current;
    if (!g) return;
    setView(clampView({ k: g.v.k, tx: g.v.tx + (e.clientX - g.x) * g.per, ty: g.v.ty + (e.clientY - g.y) * g.per }));
  };
  const onUp = () => { drag.current = null; };

  const at = useMemo(() => {
    const out = {};
    for (const kind of ["plants", "suppliers", "dealers"]) {
      for (const p of places?.[kind] || []) {
        const xy = project([p.lon, p.lat]);
        if (xy) out[p.id] = { ...p, kind, x: xy[0], y: xy[1] };
      }
    }
    return out;
  }, [places]);

  // Each plant's status across the feed: down if an outage names it, affected if a delay or hold does.
  const status = useMemo(() => {
    const s = {};
    for (const t of d.traces) {
      for (const i of t.incidents || []) {
        if (!i.plant_id) continue;
        if (i.kind === "plant_outage") s[i.plant_id] = "down";
        else if ((i.kind === "supplier_delay" || i.kind === "quality_hold") && s[i.plant_id] !== "down") s[i.plant_id] = "affected";
      }
    }
    return s;
  }, [d.traces]);

  // The routes of the focused event (the one just handled).
  const focus = d.traceById[focusId];
  const routes = useMemo(() => {
    if (!focus) return [];
    const out = [], seen = new Set();
    const add = (a, b, kind) => {
      const k = `${a}>${b}`;
      if (a !== b && at[a] && at[b] && !seen.has(k)) { seen.add(k); out.push({ a, b, kind }); }
    };
    const real = (focus.incidents || []).filter((i) => i.plant_id);
    for (const i of real) if (i.supplier_id) add(i.supplier_id, i.plant_id, "supply");
    const rows = (d.byEvent[focus.event_id] || []).filter((r) => r.ok);
    for (const r of rows) if (r.tool === "mes.transfer" && r.args?.to_plant_id) for (const i of real) add(i.plant_id, r.args.to_plant_id, "transfer");
    const dealers = [...new Set(rows.filter((r) => ["dealer.notify", "dealer.stop_sale"].includes(r.tool)).map((r) => r.args?.dealer_id).filter(Boolean))];
    const from = real[0]?.plant_id;
    for (const dl of dealers.slice(0, MAX_DEALER_ROUTES)) if (from) add(from, dl, "dealer");
    return { list: out, dealers: dealers.length, plants: [...new Set(real.map((i) => i.plant_id))] };
  }, [focus, at, d.byEvent]);

  if (!places) return <div className="map-wrap"><div className="empty">{tr("Loading the map…")}</div></div>;
  const pts = Object.values(at);
  // A plant with another plant just to its right puts its name on the left, so names never run together.
  const plantPts = pts.filter((p) => p.kind === "plants");
  const leftLabel = new Set(plantPts.filter((p) => plantPts.some((q) => q !== p && q.x > p.x && q.x - p.x < 110 && Math.abs(q.y - p.y) < 22)).map((p) => p.id));
  const routeList = routes.list || [];
  const lit = new Set(routeList.flatMap((r) => [r.a, r.b]));
  const kinds = (focus?.incidents || []).map((i) => KIND_LABEL[i.kind]).filter(Boolean);
  const s = 1 / view.k;   // markers and labels keep their size on screen at any zoom

  return (
    <div className="map-wrap">
      <div className="map-zoom" role="group" aria-label={tr("Zoom the map")}>
        <button type="button" onClick={() => zoomAt(1.6)} disabled={view.k >= MAX_ZOOM} aria-label={tr("Zoom in")} title={tr("Zoom in")}><Icon name="plus" /></button>
        <button type="button" onClick={() => zoomAt(1 / 1.6)} disabled={view.k <= 1} aria-label={tr("Zoom out")} title={tr("Zoom out")}><Icon name="minus" /></button>
        <button type="button" onClick={() => setView(FIT)} disabled={view.k <= 1} aria-label={tr("Show the whole map")} title={tr("Show the whole map")}><Icon name="refresh" /></button>
      </div>
      <svg ref={svgRef} viewBox={`${VB.x} ${VB.y} ${VB.w} ${VB.h}`} className={`impact-map${view.k > 1 ? " zoomed" : ""}`} role="img"
        aria-label={tr("Map of the company's plants, suppliers and dealers")}
        onPointerDown={onDown} onPointerMove={onMove} onPointerUp={onUp} onPointerCancel={onUp}
        onDoubleClick={(e) => zoomAt(1.8, toMap(e.clientX, e.clientY))}>
        <g transform={`translate(${view.tx} ${view.ty}) scale(${view.k})`}>
        <path d={STATES} className="map-land" />
        <path d={BORDERS} className="map-borders" />
        <path d={OUTLINE} className="map-outline" />
        {pts.filter((p) => p.kind === "dealers").map((p) => (
          <circle key={p.id} cx={p.x} cy={p.y} r={(lit.has(p.id) ? 3.6 : 2.4) * s} className={`map-dealer${lit.has(p.id) ? " on" : ""}`}
            {...tipProps(`${p.name} · ${p.city}`)} />
        ))}
        {pts.filter((p) => p.kind === "suppliers").map((p) => (
          <rect key={p.id} x={p.x - 3.2 * s} y={p.y - 3.2 * s} width={6.4 * s} height={6.4 * s} transform={`rotate(45 ${p.x} ${p.y})`}
            className={`map-supplier${lit.has(p.id) ? " on" : ""}`} {...tipProps(`${p.name} · ${tr("supplier")} · ${p.city}`)} />
        ))}
        {pts.filter((p) => p.kind === "plants").map((p) => {
          const st = status[p.id] || "running";
          const isFocus = (routes.plants || []).includes(p.id);
          return (
            <g key={p.id} {...tipProps(`${p.name} · ${tr(STATUS[st][0])}`)}>
              {isFocus && <circle key={`pulse-${focusId}`} cx={p.x} cy={p.y} r={9 * s} className="map-pulse" style={{ stroke: STATUS[st][1] }} />}
              <circle cx={p.x} cy={p.y} r={9 * s} className="map-plant-ring" style={{ stroke: STATUS[st][1] }} />
              <circle cx={p.x} cy={p.y} r={4.5 * s} className="map-plant" style={{ fill: STATUS[st][1] }} />
              <text x={leftLabel.has(p.id) ? p.x - 12 * s : p.x + 12 * s} y={p.y + 4 * s} textAnchor={leftLabel.has(p.id) ? "end" : "start"}
                className="map-label" style={{ fontSize: 12 * s, strokeWidth: 3 * s }}>{p.name.replace(/^Wacky Wheels /, "")}</text>
            </g>
          );
        })}
        </g>
      </svg>
      <div className="map-foot">
        <div className="legend">
          {Object.values(STATUS).map(([label, color]) => <span key={label}><i style={{ background: color, borderRadius: "50%" }} />{tr(label)}</span>)}
          <span><i className="lg-supplier" />{tr("Supplier")}</span>
          <span><i className="lg-dealer" />{tr("Dealer")}</span>
        </div>
        <span className="note">
          {view.k > 1 ? tr("Drag to move · pinch or ⌘ + scroll to zoom") : focus ? tr("{id}: {kinds} · {dealers} dealers notified", { id: focus.event_id, kinds: kinds.join(" + ") || tr("no action"), dealers: fmt(routes.dealers || 0) })
            : tr("Places light up as events are handled.")}
        </span>
      </div>
    </div>
  );
}
