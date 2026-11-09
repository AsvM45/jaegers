// SVG charts, no libraries. Arcs and bars draw in once when they first appear.
import { useEffect, useRef, useState } from "react";
import { Icon } from "../lib/icons.jsx";
import { CAT_COLOR, CAT_NAME, CAT_ORDER, GROUPS, KIND_LABEL, fmt, niceStep, passColor, pctOf } from "../lib/constants.js";
import { go, useTipProps, useUi } from "../lib/ui.jsx";

export function Gauge({ pct }) {
  // A half ring with the percentage inside it; nothing overlaps the arc.
  const r = 80, len = Math.PI * r;
  const filled = (Math.max(0, Math.min(100, pct)) / 100) * len;
  return (
    <svg viewBox="0 0 200 118" width="240" role="img" aria-label={`${pct}% of test cases passed`}>
      <path d="M20 100 A80 80 0 0 1 180 100" fill="none" stroke="rgba(255,255,255,.08)" strokeWidth="14" strokeLinecap="round" />
      <path d="M20 100 A80 80 0 0 1 180 100" fill="none" stroke={passColor(pct)} strokeWidth="14" strokeLinecap="round"
        className="draw" strokeDasharray={len} style={{ "--len": len, "--off": len - filled }} />
      <text x="100" y="86" textAnchor="middle" fill="#fff" fontSize="34" fontWeight="800">{pct}%</text>
      <text x="100" y="106" textAnchor="middle" fill="var(--muted)" fontSize="11">passed</text>
      <text x="20" y="117" textAnchor="middle" fill="var(--muted)" fontSize="9">0%</text>
      <text x="180" y="117" textAnchor="middle" fill="var(--muted)" fontSize="9">100%</text>
    </svg>
  );
}

export function Ring({ frac, label, caption }) {
  const r = 52, c = 2 * Math.PI * r, f = Math.max(0, Math.min(1, frac)) * c;
  return (
    <svg viewBox="0 0 140 140" width="140" role="img" aria-label={`${label} ${caption}`}>
      <circle cx="70" cy="70" r={r} fill="none" stroke="rgba(255,255,255,.08)" strokeWidth="10" />
      <circle cx="70" cy="70" r={r} fill="none" stroke="var(--s3)" strokeWidth="10" strokeLinecap="round"
        className="draw" strokeDasharray={c} style={{ "--len": c, "--off": c - f }} transform="rotate(-90 70 70)" />
      <text x="70" y="64" textAnchor="middle" className="ring-center">{caption}</text>
      <text x="70" y="88" textAnchor="middle" fill="#fff" fontSize="24" fontWeight="800">{label}</text>
    </svg>
  );
}

function arcPath(cx, cy, r0, r1, a0, a1) {
  const p = (r, a) => [cx + r * Math.sin(a), cy - r * Math.cos(a)];
  const large = a1 - a0 > Math.PI ? 1 : 0;
  const [x0, y0] = p(r1, a0), [x1, y1] = p(r1, a1), [x2, y2] = p(r0, a1), [x3, y3] = p(r0, a0);
  return `M${x0} ${y0} A${r1} ${r1} 0 ${large} 1 ${x1} ${y1} L${x2} ${y2} A${r0} ${r0} 0 ${large} 0 ${x3} ${y3} Z`;
}

// A donut: one slice per part, 2px gaps, the headline in the middle, and a legend with the counts.
export function Pie({ parts, center, caption }) {
  const tipProps = useTipProps();
  const total = parts.reduce((a, p) => a + p.value, 0);
  if (!total) return <div className="empty">Nothing to show yet.</div>;
  const shown = parts.filter((p) => p.value > 0);
  let a = 0;
  const slices = shown.map((p) => {
    const span = (p.value / total) * Math.PI * 2;
    const gap = shown.length > 1 ? 0.025 : 0;
    const a0 = a, a1 = a + span - gap;
    a += span;
    if (span >= Math.PI * 2 - 0.001)
      return <circle key={p.label} cx="80" cy="80" r="62" fill="none" stroke={p.color} strokeWidth="28" {...tipProps(`${p.label}: ${p.value} of ${total}`)} />;
    return <path key={p.label} d={arcPath(80, 80, 48, 76, a0, Math.max(a1, a0 + 0.01))} fill={p.color}
      {...tipProps(`${p.label}: ${p.value} of ${total} (${pctOf(p.value, total)}%)`)} />;
  });
  return (
    <div className="pie">
      <svg viewBox="0 0 160 160" width="168" height="168" role="img" aria-label={caption}>
        {slices}
        <text x="80" y="78" textAnchor="middle" className="pie-big">{center}</text>
        <text x="80" y="98" textAnchor="middle" className="pie-small">{caption}</text>
      </svg>
      <div className="pie-legend">
        {parts.map((p) => (
          <div key={p.label}><i style={{ background: p.color }} />{p.icon ? <Icon name={p.icon} /> : <span />}<span>{p.label}</span><b>{fmt(p.value)}</b></div>
        ))}
      </div>
    </div>
  );
}

export function PassFailPie({ passed, total, caption = "passed" }) {
  return <Pie caption={caption} center={total ? `${pctOf(passed, total)}%` : "—"} parts={[
    { label: "Passed", value: passed, color: "var(--good)", icon: "ok" },
    { label: "Failed", value: total - passed, color: "var(--bad)", icon: "x" },
  ]} />;
}

export function FailurePie({ byCat }) {
  const parts = CAT_ORDER.map((k) => ({ label: CAT_NAME[k], value: byCat[k] ? byCat[k].total - byCat[k].passed : 0, color: CAT_COLOR[k] }))
    .filter((p) => p.value > 0);
  const n = parts.reduce((a, p) => a + p.value, 0);
  if (!n) return <div className="empty" style={{ padding: 20 }}><Icon name="ok" /> No failures.</div>;
  return <Pie parts={parts} center={String(n)} caption={n === 1 ? "failure" : "failures"} />;
}

export function catRows(byCat) {
  return CAT_ORDER.filter((k) => byCat[k]).map((k) => ({ label: CAT_NAME[k] || k, swatch: CAT_COLOR[k], ...byCat[k] }))
    .concat(Object.keys(byCat).filter((k) => !CAT_ORDER.includes(k)).map((k) => ({ label: k, ...byCat[k] })));
}

// One row per item: a passed segment and a failed segment, each row its own whole so pass rates line up.
export function PassBars({ rows }) {
  const tipProps = useTipProps();
  if (!rows.length) return <div className="empty">Nothing to show yet.</div>;
  return (
    <div className="pbars">
      {rows.map((r) => {
        const pw = r.total ? (r.passed / r.total) * 100 : 0, fw = r.total ? 100 - pw : 0;
        return (
          <div key={r.label} className="pbar" onClick={r.href ? () => go(r.href) : undefined} data-href={r.href ? "" : undefined}
            {...tipProps(`${r.label}: ${r.passed} passed, ${r.total - r.passed} failed`)}>
            <div className="lab">
              <span>{r.swatch && <i style={{ background: r.swatch }} />}{r.label}</span>
              <b>{r.passed}/{r.total} <span className="note">{pctOf(r.passed, r.total)}%</span></b>
            </div>
            <div className="track">
              {pw > 0 && <div className="seg ok" style={{ width: `${pw}%` }} />}
              {fw > 0 && <div className="seg no" style={{ width: `${fw}%` }} />}
            </div>
          </div>
        );
      })}
      <div className="legend" style={{ marginTop: 4 }}>
        <span><i style={{ background: "var(--good)" }} />Passed</span><span><i style={{ background: "var(--bad)" }} />Failed</span>
      </div>
    </div>
  );
}

export function KindBars({ incidents }) {
  const counts = {};
  for (const i of incidents) counts[i.kind] = (counts[i.kind] || 0) + 1;
  const max = Math.max(1, ...Object.values(counts));
  return (
    <div className="bars">
      {["supplier_delay", "plant_outage", "quality_hold", "unconfirmed", "noise"].map((k) => (
        <div className="hbar" key={k}>
          <div className="lab"><span>{KIND_LABEL[k]}</span><b>{counts[k] || 0}</b></div>
          <div className="track"><div className="fill" style={{ width: `${((counts[k] || 0) / max) * 100}%` }} /></div>
        </div>
      ))}
    </div>
  );
}

function roundTopRect(x, y, w, h, r) {
  return `M${x} ${y + h} V${y + r} Q${x} ${y} ${x + r} ${y} H${x + w - r} Q${x + w} ${y} ${x + w} ${y + r} V${y + h} Z`;
}

function useWidth(ref) {
  const [w, setW] = useState(0);
  useEffect(() => {
    if (!ref.current) return;
    const ro = new ResizeObserver(([e]) => setW(Math.round(e.contentRect.width)));
    ro.observe(ref.current);
    return () => ro.disconnect();
  }, [ref]);
  return w;
}

/* Stacked bar chart: one bar per event, segments by tool group, 2px gaps, 4px rounded top. */
export function CallsChart({ data, onPick }) {
  const host = useRef(null);
  const width = useWidth(host);
  const { tip } = useUi();
  const [hover, setHover] = useState(-1);
  if (!data.length) return <div className="chart" ref={host}><div className="empty">No run yet. Run python -m tower.run.</div></div>;
  const W = Math.max(320, width), H = 260, pad = { l: 36, r: 8, t: 8, b: 26 };
  const max = Math.max(1, ...data.map((d) => d.total));
  const step = niceStep(max), top = Math.ceil(max / step) * step;
  const iw = W - pad.l - pad.r, ih = H - pad.t - pad.b;
  const slot = iw / data.length, bw = Math.min(26, slot * 0.55);
  const y = (v) => pad.t + ih - (v / top) * ih;
  const ticks = [];
  for (let v = 0; v <= top; v += step) ticks.push(v);
  const showTip = (e, d) => tip.show(e, <>
    <b>{d.id} · {d.total} calls</b>
    {d.total ? GROUPS.map((g, gi) => d.vals[gi] ? <div className="row" key={g.id}><span><i style={{ background: g.color }} />{g.label}</span><span>{d.vals[gi]}</span></div> : null) : "No calls"}
  </>);
  return (
    <div className="chart" ref={host}>
      {width > 0 && (
        <svg viewBox={`0 0 ${W} ${H}`} height={H} role="img" aria-label="Stacked bar chart of tool calls per event">
          <g className="axis">
            {ticks.map((v) => <g key={v}><line className="grid-line" x1={pad.l} x2={W - pad.r} y1={y(v)} y2={y(v)} /><text x={pad.l - 8} y={y(v) + 3} textAnchor="end">{v}</text></g>)}
            {data.map((d, i) => <text key={d.id} x={pad.l + slot * i + slot / 2} y={H - 8} textAnchor="middle">{d.id.replace("E-", "")}</text>)}
          </g>
          {data.map((d, i) => {
            const x = pad.l + slot * i + (slot - bw) / 2;
            const segs = d.vals.map((v, gi) => ({ v, gi })).filter((s) => s.v > 0);
            let acc = 0;
            return (
              <g key={d.id}>
                {segs.map((s, si) => {
                  const y0 = y(acc), y1 = y(acc + s.v);
                  acc += s.v;
                  const h = Math.max(1, y0 - y1 - (si > 0 ? 2 : 0)); // 2px surface gap between stacked segments
                  const isTop = si === segs.length - 1;
                  return <path key={s.gi} className="bar" style={{ animationDelay: `${i * 35}ms` }}
                    d={roundTopRect(x, y1, bw, h, isTop ? Math.min(4, h / 2, bw / 2) : 0)} fill={GROUPS[s.gi].color} />;
                })}
                <rect x={pad.l + slot * i} y={pad.t} width={slot} height={ih} className="hit"
                  fill={hover === i ? "rgba(255,255,255,.04)" : "transparent"}
                  onMouseMove={(e) => { setHover(i); showTip(e, d); }}
                  onMouseLeave={() => { setHover(-1); tip.hide(); }}
                  onClick={() => { tip.hide(); onPick(d.id); }} />
              </g>
            );
          })}
        </svg>
      )}
    </div>
  );
}
