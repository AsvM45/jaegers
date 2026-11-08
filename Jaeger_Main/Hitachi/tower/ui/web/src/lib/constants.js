// Labels, colors and pure helpers shared by every page.

export const fmt = (n) => Number(n || 0).toLocaleString("en-US");

export const KIND_LABEL = {
  supplier_delay: "Supplier delay", plant_outage: "Plant outage", quality_hold: "Quality hold",
  unconfirmed: "Unconfirmed", noise: "Noise",
};

/* Tool groups for the calls chart: one hue per job, fixed order. */
export const GROUPS = [
  { id: "prod", label: "Production moves", color: "var(--s1)", tools: ["mes.reschedule", "mes.transfer"] },
  { id: "dealer", label: "Dealer notices & stop-sales", color: "var(--s2)", tools: ["dealer.notify", "dealer.stop_sale"] },
  { id: "cust", label: "Loaners & owner notices", color: "var(--s3)", tools: ["crm.assign_loaner", "crm.notify_customer"] },
  { id: "lot", label: "Lot holds", color: "var(--s4)", tools: ["quality.hold_lot"] },
  { id: "esc", label: "Escalations", color: "var(--s5)", tools: ["escalate"] },
];

export const TOOL_WORD = {
  "mes.reschedule": "Reschedule", "mes.transfer": "Transfer", "dealer.notify": "Dealer notice",
  "dealer.stop_sale": "Stop sale", "crm.assign_loaner": "Loaner", "crm.notify_customer": "Owner notice",
  "quality.hold_lot": "Lot hold", escalate: "Escalate",
};
export const WRITE_TOOLS = new Set(Object.keys(TOOL_WORD).filter((t) => t !== "escalate"));

export const CAT_ORDER = ["supplier_delay", "plant_outage", "quality_hold", "unconfirmed", "compound", "noise"];
export const CAT_COLOR = {
  supplier_delay: "var(--s1)", plant_outage: "var(--s2)", quality_hold: "var(--s3)",
  unconfirmed: "var(--s4)", compound: "var(--s5)", noise: "#6b7894",
};
export const CAT_NAME = { ...KIND_LABEL, compound: "Compound" };

export const PAGES = {
  overview: "Overview", events: "Event feed", tests: "Tests", ontology: "Knowledge graph", logs: "Logs", guide: "Guide",
};

export const AGENT_ICON = { coordinator: "cpu", supply_chain: "wrench", quality: "shield", dealer_customer: "mail" };

export const passColor = (pct) => (pct === 100 ? "var(--good)" : pct >= 80 ? "var(--warn)" : "var(--bad)");
export const pctOf = (n, total) => (total ? Math.round((n / total) * 100) : 0);
export const kindsOf = (t) => (t.incidents || []).map((i) => i.kind);
export const kindWords = (t) => kindsOf(t).map((k) => KIND_LABEL[k]).join(" + ");
export const when = (s) => (s || "").replace("T", " ");

export function argText(args) {
  return Object.entries(args || {}).map(([k, v]) => {
    if (Array.isArray(v)) return `${k}=[${v.length > 4 ? v.slice(0, 4).join(", ") + ` … +${v.length - 4}` : v.join(", ")}]`;
    const s = String(v);
    return `${k}=${s.length > 60 ? s.slice(0, 57) + "…" : s}`;
  }).join("  ");
}

export function sameSet(a, b) {
  if (a.length !== b.length) return false;
  const s = new Set(a);
  return b.every((x) => s.has(x));
}

export function readerName(id) { return id.startsWith("llm_") ? id.slice(4).replace("_", ":") : id; }

export function niceStep(max) {
  const raw = max / 4, p = Math.pow(10, Math.floor(Math.log10(raw)));
  const n = raw / p;
  return (n <= 1 ? 1 : n <= 2 ? 2 : n <= 5 ? 5 : 10) * p;
}
