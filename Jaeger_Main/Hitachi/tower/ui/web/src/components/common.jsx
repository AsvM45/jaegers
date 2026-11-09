import { useEffect, useRef, useState } from "react";
import { Icon } from "../lib/icons.jsx";
import { fmt, KIND_LABEL } from "../lib/constants.js";

const STATUS = {
  pass: ["pass", "ok", "Passed"], fail: ["fail", "x", "Failed"], ok: ["pass", "ok", "OK"],
  acted: ["pass", "ok", "Acted"], esc: ["esc", "alert", "Escalated"], none: ["none", "minus", "No action"],
};
export function Status({ kind }) {
  const [cls, ic, word] = STATUS[kind];
  return <span className={`status ${cls}`}><Icon name={ic} />{word}</span>;
}

export function KindTag({ kind }) {
  return <span className={`tag k-${kind}`}>{KIND_LABEL[kind] || kind}</span>;
}

// A segmented toggle. options: [[value, label], ...]
export function Toggle({ value, options, onChange, ...rest }) {
  return (
    <div className="toggle" role="tablist" {...rest}>
      {options.map(([v, label]) => (
        <button key={v} className={v === value ? "on" : ""} onClick={() => onChange(v)}>{label}</button>
      ))}
    </div>
  );
}

// A number that rises from 0 to its value over ~0.8 s when it first appears.
export function CountUp({ value }) {
  const reduce = typeof matchMedia !== "undefined" && matchMedia("(prefers-reduced-motion: reduce)").matches;
  const [shown, setShown] = useState(reduce ? value : 0);
  const from = useRef(reduce ? value : 0);
  useEffect(() => {
    if (reduce) { setShown(value); return; }
    const start = from.current, t0 = performance.now(), dur = 800;
    let raf;
    const step = (now) => {
      const k = Math.min(1, (now - t0) / dur);
      const v = Math.round(start + (value - start) * (1 - Math.pow(1 - k, 3)));
      from.current = v;
      setShown(v);
      if (k < 1) raf = requestAnimationFrame(step);
    };
    raf = requestAnimationFrame(step);
    return () => cancelAnimationFrame(raf);
  }, [value, reduce]);
  return <span>{fmt(shown)}</span>;
}

// value: a number (counts up) or a string such as "12 / 15" (the leading number counts up).
export function StatCard({ label, value, delta, trend, icon }) {
  const dcls = ["up", "down", "warn"].includes(trend) ? trend : "flat";
  const arr = trend === "up" ? "▲" : trend === "down" ? "▼" : "";
  let body = value;
  const m = typeof value === "number" ? [null, String(value), ""] : String(value).match(/^([\d,]+)(.*)$/);
  if (m) body = <><CountUp value={Number(m[1].replace(/,/g, ""))} />{m[2]}</>;
  return (
    <div className="card stat">
      <div className="stat-body">
        <div className="k">{label}</div>
        <div className="v">{body}</div>
        {delta && <div className={`delta ${dcls}`}>{arr && <span className="arr">{arr}</span>}<span className="txt">{delta}</span></div>}
      </div>
      <div className="badge-ico"><Icon name={icon} /></div>
    </div>
  );
}

export function CardHead({ title, sub, children }) {
  return (
    <div className="card-head">
      <div><h3>{title}</h3>{sub && <p className="sub">{sub}</p>}</div>
      {children}
    </div>
  );
}

export const Mono = ({ children }) => <span className="mono">{children}</span>;
