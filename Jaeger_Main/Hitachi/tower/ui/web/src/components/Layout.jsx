import { Fragment, useEffect, useRef, useState } from "react";
import { Icon } from "../lib/icons.jsx";
import { useData } from "../lib/data.jsx";
import { useUi } from "../lib/ui.jsx";
import { Search } from "./Search.jsx";

const NAV = [
  ["overview", "home", "Overview"], ["events", "feed", "Event feed"], ["tests", "check", "Tests"],
  ["ontology", "graph", "Knowledge graph"], ["logs", "doc", "Logs"],
];

export function Sidebar({ page }) {
  const link = ([id, ic, label]) => (
    <a key={id} href={`#/${id}`} className={page === id ? "on" : ""}><span className="ico"><Icon name={ic} /></span>{label}</a>
  );
  return (
    <aside className="side">
      <div className="brand">
        <div className="brand-mark">W</div>
        <div className="brand-name">WACKY WHEELS<span>CONTROL TOWER</span></div>
      </div>
      <nav className="nav">{NAV.map(link)}</nav>
      <div className="nav-label">HELP</div>
      <nav className="nav">{link(["guide", "book", "Guide"])}</nav>
    </aside>
  );
}

function agoText(ms) {
  const secs = Math.round(ms / 1000);
  return secs < 10 ? "just now" : secs < 60 ? `${secs}s ago` : secs < 3600 ? `${Math.floor(secs / 60)}m ago` : `${Math.floor(secs / 3600)}h ago`;
}

function LiveChip() {
  const d = useData();
  const [, tick] = useState(0);
  useEffect(() => { const t = setInterval(() => tick((n) => n + 1), 15000); return () => clearInterval(t); }, []);
  if (!d.loadedAt) return <div className="live"><span className="pulse" /><span>Loading…</span></div>;
  const age = Date.now() - d.loadedAt;
  const cls = !d.traces.length ? "down" : age > 600000 ? "stale" : "";
  return (
    <div className={`live ${cls}`} title="Reader model and when the data was last loaded">
      <span className="pulse" />
      <span>{d.traces.length ? <><b>{d.model || "rule reader"}</b> · updated {agoText(age)}</> : "No run loaded"}</span>
    </div>
  );
}

// title, and either a trail ([[label, href|null], ...]) or a subtitle (node) under it.
export function Topbar({ title, trail, subtitle }) {
  const { set } = useUi();
  const q = useRef(null);
  const [scrolled, setScrolled] = useState(false);

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 8);
    // "/" jumps to search from anywhere; Esc clears it.
    const onKey = (e) => {
      const typing = /^(INPUT|TEXTAREA|SELECT)$/.test(document.activeElement?.tagName || "");
      if (e.key === "/" && !typing) { e.preventDefault(); q.current?.focus(); }
      if (e.key === "Escape" && document.activeElement === q.current) { set({ q: "" }); q.current.blur(); }
    };
    window.addEventListener("scroll", onScroll, { passive: true });
    document.addEventListener("keydown", onKey);
    return () => { window.removeEventListener("scroll", onScroll); document.removeEventListener("keydown", onKey); };
  }, [set]);

  return (
    <header className={`topbar${scrolled ? " scrolled" : ""}`}>
      <div className="tb-left">
        {trail && (
          <nav className="trail" aria-label="Breadcrumb">
            {trail.map(([label, href], i) => (
              <Fragment key={i}>
                {i > 0 && <span className="sep">›</span>}
                {href ? <a href={href}>{label}</a> : <span>{label}</span>}
              </Fragment>
            ))}
          </nav>
        )}
        <h1>{title}</h1>
        {!trail && <div className="tb-sub">{subtitle}</div>}
      </div>
      <div className="tb-right">
        <LiveChip />
        <Search ref={q} />
      </div>
    </header>
  );
}
