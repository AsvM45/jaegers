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

// Shown only when the data can't be reached; otherwise the dashboard says nothing about loading.
export function LoadBanner() {
  const d = useData();
  if (!d.failed) return null;
  return (
    <div className="load-banner" role="status">
      <span>Couldn't load the latest data. Some pages may be empty.</span>
      <button className="btn" onClick={d.reload} disabled={d.busy}>{d.busy ? "Retrying…" : "Retry"}</button>
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
        <Search ref={q} />
      </div>
    </header>
  );
}
