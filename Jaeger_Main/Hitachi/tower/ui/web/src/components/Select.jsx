// A dropdown that matches the dashboard: a clear button, a solid list with a check on the current
// choice, keyboard support, and a search box. Typing while it is closed opens it and searches.
//
//   <Select label="Time zone" value={v} onChange={setV} options={[[value, label, hint?], ...]} />
import { useEffect, useId, useMemo, useRef, useState } from "react";
import { Icon } from "../lib/icons.jsx";
import { tr } from "../lib/i18n.js";

export function Select({ value, onChange, options, label, size = "md", searchable = true, placeholder = "Choose…", width }) {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [active, setActive] = useState(0);
  const [up, setUp] = useState(false);
  const wrap = useRef(null), button = useRef(null), list = useRef(null), search = useRef(null);
  const id = useId();
  const canSearch = searchable;

  const shown = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return options;
    // Best first: a word of the name starts with the text, then the name contains it, then the hint or value.
    const rank = ([v, text, hint]) => {
      const name = String(text).toLowerCase();
      if (name.split(/[\s/(),·-]+/).some((w) => w.startsWith(q))) return 0;
      if (name.includes(q)) return 1;
      return `${hint || ""} ${v}`.toLowerCase().includes(q) ? 2 : -1;
    };
    return options.map((o, i) => [rank(o), i, o]).filter(([r]) => r >= 0)
      .sort((x, y) => x[0] - y[0] || x[1] - y[1]).map(([, , o]) => o);
  }, [options, query]);
  const current = options.find(([v]) => v === value);

  const show = (typed = "") => {
    const b = button.current.getBoundingClientRect();
    setUp(window.innerHeight - b.bottom < 340 && b.top > window.innerHeight - b.bottom);
    setQuery(canSearch ? typed : "");
    setActive(typed ? 0 : Math.max(0, options.findIndex(([v]) => v === value)));
    setOpen(true);
  };
  const close = (focus = true) => { setOpen(false); if (focus) button.current?.focus(); };
  const pick = (v) => { if (v !== value) onChange(v); close(); };

  // Close on a click outside; focus the search box (or the list) when it opens.
  useEffect(() => {
    if (!open) return undefined;
    const away = (e) => { if (!wrap.current?.contains(e.target)) close(false); };
    document.addEventListener("pointerdown", away);
    (canSearch ? search.current : list.current)?.focus();
    return () => document.removeEventListener("pointerdown", away);
  }, [open]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    if (open) list.current?.querySelector(`[data-i="${active}"]`)?.scrollIntoView({ block: "nearest" });
  }, [active, open, shown]);

  const typed = useRef({ text: "", at: 0 });
  const onKey = (e) => {
    if (e.key === "ArrowDown") { e.preventDefault(); setActive((a) => Math.min(shown.length - 1, a + 1)); }
    else if (e.key === "ArrowUp") { e.preventDefault(); setActive((a) => Math.max(0, a - 1)); }
    else if (e.key === "Home") { e.preventDefault(); setActive(0); }
    else if (e.key === "End") { e.preventDefault(); setActive(shown.length - 1); }
    else if (e.key === "Enter") { e.preventDefault(); if (shown[active]) pick(shown[active][0]); }
    else if (e.key === "Escape") { e.preventDefault(); close(); }
    else if (e.key === "Tab") close(false);
    else if (!canSearch && e.key.length === 1) {
      // Type-ahead: jump to the first option starting with what was typed.
      const now = Date.now();
      typed.current = { text: (now - typed.current.at < 700 ? typed.current.text : "") + e.key.toLowerCase(), at: now };
      const i = shown.findIndex(([, text]) => String(text).toLowerCase().startsWith(typed.current.text));
      if (i >= 0) setActive(i);
    }
  };

  return (
    <div className={`sel sel-${size}${open ? " open" : ""}`} ref={wrap} style={width ? { width } : undefined}>
      <button type="button" ref={button} className="sel-btn" aria-haspopup="listbox" aria-expanded={open}
        aria-label={label ? `${label}: ${current ? current[1] : placeholder}` : undefined}
        onClick={() => (open ? close() : show())}
        onKeyDown={(e) => {
          if (["ArrowDown", "ArrowUp", "Enter", " "].includes(e.key)) { e.preventDefault(); show(); }
          else if (canSearch && e.key.length === 1 && !e.metaKey && !e.ctrlKey && !e.altKey) { e.preventDefault(); show(e.key); }
        }}>
        <span className="sel-value">{current ? current[1] : <span className="sel-ph">{placeholder}</span>}</span>
        {current?.[2] && size === "md" && <span className="sel-hint">{current[2]}</span>}
        <span className="sel-chev" aria-hidden="true"><Icon name="chevron" /></span>
      </button>
      {open && (
        <div className={`sel-pop${up ? " up" : ""}`} onKeyDown={onKey}>
          {canSearch && (
            <div className="sel-search">
              <Icon name="search" />
              <input ref={search} value={query} onChange={(e) => { setQuery(e.target.value); setActive(0); }} placeholder={tr("Search")}
                aria-label={tr("Search {options}", { options: label || "options" })} aria-controls={id}
                aria-activedescendant={shown[active] ? `${id}-${active}` : undefined} />
            </div>
          )}
          <div className="sel-list" role="listbox" id={id} ref={list} tabIndex={-1} aria-label={label}
            aria-activedescendant={shown[active] ? `${id}-${active}` : undefined}>
            {!shown.length && <div className="sel-empty">{tr("No matches")}</div>}
            {shown.map(([v, text, hint], i) => (
              <div key={v} id={`${id}-${i}`} data-i={i} role="option" aria-selected={v === value}
                className={`sel-opt${i === active ? " active" : ""}${v === value ? " on" : ""}`}
                onPointerMove={() => setActive(i)} onClick={() => pick(v)}>
                <span className="sel-check" aria-hidden="true">{v === value && <Icon name="ok" />}</span>
                <span className="sel-text">{text}</span>
                {hint && <span className="sel-hint">{hint}</span>}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
