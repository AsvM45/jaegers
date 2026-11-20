// Paging for the Event Center's lists: show 5, 25, 50 or all events, with previous / next pages.
// The page size and page are shared by the Feed list and the Results table.
import { useEffect } from "react";
import { useUi } from "../lib/ui.jsx";
import { Toggle } from "./common.jsx";
import { fmt } from "../lib/constants.js";
import { tr } from "../lib/i18n.js";

const SIZES = [5, 25, 50, 0];   // 0 = all

export function usePage(list, selId) {
  const { ui, set } = useUi();
  const size = SIZES.includes(ui.evPageSize) ? ui.evPageSize : 5;
  const pages = size ? Math.max(1, Math.ceil(list.length / size)) : 1;
  const page = Math.min(Math.max(0, ui.evPage || 0), pages - 1);
  // An event picked from elsewhere (Overview, search, a chart) opens on the page that holds it.
  useEffect(() => {
    if (!size || !selId) return;
    const i = list.findIndex((t) => t.event_id === selId);
    if (i >= 0 && Math.floor(i / size) !== page) set({ evPage: Math.floor(i / size) });
  }, [selId]); // eslint-disable-line react-hooks/exhaustive-deps
  return {
    shown: size ? list.slice(page * size, page * size + size) : list,
    size, page, pages, total: list.length,
    setSize: (s) => set({ evPageSize: s, evPage: 0 }),
    setPage: (p) => set({ evPage: p }),
  };
}

export function Pager({ pg }) {
  if (!pg.total) return null;
  const from = pg.size ? pg.page * pg.size + 1 : 1;
  const to = pg.size ? Math.min(pg.total, from + pg.size - 1) : pg.total;
  return (
    <div className="pager">
      <span className="note">{tr("Show")}</span>
      <Toggle value={String(pg.size)} onChange={(v) => pg.setSize(Number(v))} aria-label={tr("Events per page")}
        options={SIZES.map((n) => [String(n), n ? fmt(n) : tr("All")])} />
      {pg.pages > 1 && (
        <div className="pager-nav">
          <button type="button" className="btn" disabled={pg.page === 0} onClick={() => pg.setPage(pg.page - 1)} aria-label={tr("Previous page")}>‹</button>
          <span className="note">{tr("{from}–{to} of {total}", { from: fmt(from), to: fmt(to), total: fmt(pg.total) })}</span>
          <button type="button" className="btn" disabled={pg.page >= pg.pages - 1} onClick={() => pg.setPage(pg.page + 1)} aria-label={tr("Next page")}>›</button>
        </div>
      )}
    </div>
  );
}
