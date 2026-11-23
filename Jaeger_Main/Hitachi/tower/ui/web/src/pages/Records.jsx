// #/records  The company's tables, read-only: what a visitor needs to write their own test messages
// (a supplier and shipment for a delay, a plant for an outage, a lot for a quality hold). The server
// pages and searches the rows (GET /api/records/<table>), since the largest tables have thousands.
import { useEffect, useState } from "react";
import { getJSON } from "../lib/data.jsx";
import { useUi } from "../lib/ui.jsx";
import { fmt } from "../lib/constants.js";
import { CardHead } from "../components/common.jsx";
import { Pager, TABLE_SIZES } from "../components/Pager.jsx";
import { Icon } from "../lib/icons.jsx";
import { Page } from "./Page.jsx";
import { tr, trx } from "../lib/i18n.js";

// Built when the page renders, so it is in the language chosen in Settings.
const TABLES = () => ({
  suppliers: [tr("Suppliers"), tr("Who ships each part. A supplier delay names one.")],
  inbound_shipments: [tr("Inbound shipments"), tr("Parts on their way to each plant. A late shipment is a supplier delay.")],
  part_lots: [tr("Part lots"), tr("Batches of a part built into vehicles. A defective lot is a quality hold.")],
  plants: [tr("Plants"), tr("Where the vehicles are built. A plant that stops is a plant outage.")],
  parts: [tr("Parts"), tr("The parts the models are built from.")],
  dealers: [tr("Dealers"), tr("The dealers that sell the vehicles and are told about delays.")],
  production_orders: [tr("Production orders"), tr("Vehicles scheduled to be built, by plant and day.")],
  customer_orders: [tr("Customer orders"), tr("Vehicles customers have ordered, with the date promised to them.")],
  finished_vehicles: [tr("Finished vehicles"), tr("Vehicles already built, by VIN.")],
  customers: [tr("Customers"), tr("Customers and their tier. Platinum and Gold customers get loaners first.")],
});

const COLUMNS = () => ({
  supplier_id: tr("Supplier"), name: tr("Name"), city: tr("City"), plant_id: tr("Plant"), slots_per_day: tr("Slots per day"),
  part_id: tr("Part"), category: tr("Category"), shipment_id: tr("Shipment"), eta_date: tr("ETA"), covers_days: tr("Days covered"),
  lot_id: tr("Lot"), first_build_date: tr("First build"), last_build_date: tr("Last build"), dealer_id: tr("Dealer"),
  region: tr("Region"), transit_days: tr("Transit days"), production_order_id: tr("Production order"), build_date: tr("Build date"),
  model: tr("Model"), units: tr("Units"), customer_order_id: tr("Customer order"), customer_id: tr("Customer"),
  promised_date: tr("Promised date"), vin: tr("VIN"), status: tr("Status"), tier: tr("Tier"),
});
// Columns that hold a record's id: shown in the code font, since that is how a message names them.
const ID_COLUMN = /(_id|^vin)$/;

function RecordTable({ table, title, hint }) {
  const { ui, set } = useUi();
  const [q, setQ] = useState("");
  const [query, setQuery] = useState("");
  const [data, setData] = useState(null);
  const size = TABLE_SIZES.includes(ui.recPageSize) ? ui.recPageSize : 25;
  const pageNo = ui.recPage || 0;
  // Search after a short pause in typing, from the first page.
  useEffect(() => {
    const t = setTimeout(() => { setQuery(q); set({ recPage: 0 }); }, 250);
    return () => clearTimeout(t);
  }, [q]); // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => {
    let live = true;
    const url = `/api/records/${table}?q=${encodeURIComponent(query)}&offset=${pageNo * size}&limit=${size}`;
    getJSON(url, null).then((res) => { if (live) setData(res); });
    return () => { live = false; };
  }, [table, query, pageNo, size]);

  const cols = COLUMNS();
  const total = data?.total || 0;
  const pg = {
    total, size, page: pageNo, pages: Math.max(1, Math.ceil(total / size)), sizes: TABLE_SIZES,
    setSize: (s) => set({ recPageSize: s, recPage: 0 }), setPage: (p) => set({ recPage: p }),
  };
  return (
    <div className="card">
      <CardHead title={title} sub={hint}>
        <div className="controls">
          <label className="rec-search">
            <Icon name="search" />
            <input value={q} onChange={(e) => setQ(e.target.value)} placeholder={tr("Search this table")} aria-label={tr("Search this table")} />
          </label>
        </div>
      </CardHead>
      <div className="scroll-x"><table>
        <thead><tr>{(data?.columns || []).map((c) => <th key={c}>{cols[c] || c}</th>)}</tr></thead>
        <tbody>
          {(data?.rows || []).map((row, i) => (
            <tr key={`${pageNo}-${i}`}>
              {row.map((cell, j) => {
                const id = ID_COLUMN.test(data.columns[j]);
                return <td key={j} className={id ? "mono" : ""}>{id && j === 0 ? <b>{cell}</b> : cell}</td>;
              })}
            </tr>
          ))}
          {data && !data.rows.length && <tr><td colSpan={data.columns.length || 1} className="empty">{tr("No rows match.")}</td></tr>}
          {!data && <tr><td className="empty">{tr("Loading…")}</td></tr>}
        </tbody>
      </table></div>
      <Pager pg={pg} />
    </div>
  );
}

export default function Records() {
  const { ui, set } = useUi();
  const [list, setList] = useState([]);
  useEffect(() => { getJSON("/api/records", []).then((r) => setList(Array.isArray(r) ? r : [])); }, []);
  const names = TABLES();
  const tab = names[ui.recTab] ? ui.recTab : "suppliers";
  const count = Object.fromEntries(list.map((t) => [t.id, t.rows]));
  return (
    <Page title={tr("Company records")}
      subtitle={<span>{trx("The company's tables, read-only. Name records from here in a message on {add} to test the tower.",
        { add: <a className="link" href="#/add">{tr("Add events")}</a> })}</span>}>
      <div className="rec-tabs" role="tablist" aria-label={tr("Table")}>
        {Object.entries(names).map(([id, [label]]) => (
          <button key={id} type="button" role="tab" aria-selected={tab === id} className={tab === id ? "on" : ""}
            onClick={() => set({ recTab: id, recPage: 0 })}>
            {label}{count[id] != null && <span className="ev-n">{fmt(count[id])}</span>}
          </button>
        ))}
      </div>
      <div style={{ marginTop: 16 }}>
        <RecordTable key={tab} table={tab} title={names[tab][0]} hint={names[tab][1]} />
      </div>
    </Page>
  );
}
