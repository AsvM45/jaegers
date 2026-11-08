// The title-bar search: filters the lists on the page and shows matching events and test cases
// underneath, from any page. "/" focuses it, arrows move, Enter opens, Esc clears.
import { forwardRef, useMemo, useState } from "react";
import { Icon } from "../lib/icons.jsx";
import { readerName } from "../lib/constants.js";
import { useData } from "../lib/data.jsx";
import { go, useUi } from "../lib/ui.jsx";
import { KindTag, Status } from "./common.jsx";

const MAX_EVENTS = 6, MAX_CASES = 8;

function useResults(q) {
  const d = useData();
  return useMemo(() => {
    if (!q) return { events: [], cases: [], more: 0 };
    const hit = (s) => s.toLowerCase().includes(q);
    const events = d.traces.filter((t) => hit(`${t.event_id} ${t.text} ${t.source || ""}`)).map((t) => ({
      key: `e:${t.event_id}`, kind: "event", id: t.event_id, text: t.text, tag: t.incidents?.[0]?.kind, status: d.outcome(t.event_id),
    }));
    // One row per case per test set, from the set's first reader (the case text is the same for every reader).
    const cases = [];
    for (const s of d.reports?.suites || []) {
      const r = s.readers[0];
      for (const c of r?.cases || []) if (hit(`${c.id} ${c.text}`)) cases.push({
        key: `c:${s.id}:${c.id}`, kind: "case", id: c.id, text: c.text, tag: c.category, set: s.title,
        href: `#/tests/${s.id}/${r.id}/${encodeURIComponent(c.id)}`, reader: readerName(r.id), pass: c.verdict === "PASS",
      });
    }
    return {
      events: events.slice(0, MAX_EVENTS), cases: cases.slice(0, MAX_CASES),
      more: Math.max(0, events.length - MAX_EVENTS) + Math.max(0, cases.length - MAX_CASES),
    };
  }, [d, q]);
}

// Bold the matched part of a line of text.
function Mark({ text, q }) {
  const s = String(text || ""), i = s.toLowerCase().indexOf(q);
  if (i < 0) return s;
  const start = Math.max(0, i - 40);
  return <>{start ? "…" : ""}{s.slice(start, i)}<mark>{s.slice(i, i + q.length)}</mark>{s.slice(i + q.length)}</>;
}

export const Search = forwardRef(function Search(_, ref) {
  const { ui, set } = useUi();
  const [open, setOpen] = useState(false);
  const [active, setActive] = useState(0);
  const q = ui.q.trim().toLowerCase();
  const { events, cases, more } = useResults(q);
  const rows = [...events, ...cases];

  const pick = (row) => {
    if (row.kind === "event") { set({ q: "", sel: row.id }); go("#/events"); }
    else { set({ q: "" }); go(row.href); }
    setOpen(false);
    ref.current?.blur();
  };
  const onKey = (e) => {
    if (e.key === "ArrowDown") { e.preventDefault(); setActive((a) => Math.min(rows.length - 1, a + 1)); }
    if (e.key === "ArrowUp") { e.preventDefault(); setActive((a) => Math.max(0, a - 1)); }
    if (e.key === "Enter" && rows[active]) { e.preventDefault(); pick(rows[active]); }
  };
  const row = (r, i) => (
    <button key={r.key} className={`sr-row${i === active ? " on" : ""}`} onMouseEnter={() => setActive(i)}
      onMouseDown={(e) => e.preventDefault()} onClick={() => pick(r)}>
      <div className="sr-top">
        <b>{r.id}</b>{r.tag && <KindTag kind={r.tag} />}
        <span className="sr-right">{r.kind === "event" ? <Status kind={r.status} /> : <Status kind={r.pass ? "pass" : "fail"} />}</span>
      </div>
      {r.set && <div className="note">{r.set} · {r.reader}</div>}
      <div className="sr-text"><Mark text={r.text} q={q} /></div>
    </button>
  );

  return (
    <div className="search-wrap">
      <label className="search">
        <Icon name="search" />
        <input ref={ref} placeholder="Search events or tests" autoComplete="off" value={ui.q}
          onChange={(e) => { set({ q: e.target.value }); setActive(0); setOpen(true); }}
          onFocus={() => setOpen(true)} onBlur={() => setOpen(false)} onKeyDown={onKey} />
        <kbd>/</kbd>
      </label>
      {open && q && (
        <div className="sresults" role="listbox">
          {!rows.length && <div className="sr-empty">No events or test cases match “{ui.q.trim()}”.</div>}
          {events.length > 0 && <div className="sr-head">Events</div>}
          {events.map((r, i) => row(r, i))}
          {cases.length > 0 && <div className="sr-head">Test cases</div>}
          {cases.map((r, i) => row(r, events.length + i))}
          {more > 0 && <div className="sr-foot">{more} more. Keep typing to narrow it down.</div>}
        </div>
      )}
    </div>
  );
});
