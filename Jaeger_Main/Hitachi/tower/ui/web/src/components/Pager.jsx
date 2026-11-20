// Paging for long lists, with previous / next pages. Tables (the Logs) use the usual 10 / 25 / 50 / 100;
// the Event Center's event cards are taller, so they use 5 / 10 / 25 / 50 / All.
// Each list has its own name (id), so it keeps its own page size and page: the Event Center's Feed list
// and Results table share "ev"; each Logs tab has its own.
import { useEffect } from "react";
import { useUi } from "../lib/ui.jsx";
import { Toggle } from "./common.jsx";
import { fmt } from "../lib/constants.js";
import { tr } from "../lib/i18n.js";

export const TABLE_SIZES = [10, 25, 50, 100];
export const CARD_SIZES = [5, 10, 25, 50, 0];   // 0 = all

// list: the rows. selId: an event id that must be on the shown page (Event Center only).
export function usePage(list, selId, { id = "ev", initial = 5, sizes = CARD_SIZES } = {}) {
  const { ui, set } = useUi();
  const sizeKey = `${id}PageSize`, pageKey = `${id}Page`;
  const size = sizes.includes(ui[sizeKey]) ? ui[sizeKey] : initial;
  const pages = size ? Math.max(1, Math.ceil(list.length / size)) : 1;
  const page = Math.min(Math.max(0, ui[pageKey] || 0), pages - 1);
  // An event picked from elsewhere (Overview, search, a chart) opens on the page that holds it.
  useEffect(() => {
    if (!size || !selId) return;
    const i = list.findIndex((t) => t.event_id === selId);
    if (i >= 0 && Math.floor(i / size) !== page) set({ [pageKey]: Math.floor(i / size) });
  }, [selId]); // eslint-disable-line react-hooks/exhaustive-deps
  return {
    shown: size ? list.slice(page * size, page * size + size) : list,
    size, page, pages, sizes, total: list.length,
    setSize: (s) => set({ [sizeKey]: s, [pageKey]: 0 }),
    setPage: (p) => set({ [pageKey]: p }),
    reset: () => set({ [pageKey]: 0 }),
  };
}

export function Pager({ pg, label }) {
  if (!pg.total) return null;
  const from = pg.size ? pg.page * pg.size + 1 : 1;
  const to = pg.size ? Math.min(pg.total, from + pg.size - 1) : pg.total;
  return (
    <div className="pager">
      <span className="note">{tr("Show")}</span>
      <Toggle value={String(pg.size)} onChange={(v) => pg.setSize(Number(v))} aria-label={label || tr("Rows per page")}
        options={pg.sizes.map((n) => [String(n), n ? fmt(n) : tr("All")])} />
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
