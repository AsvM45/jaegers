// Labels, colors and pure helpers shared by every page. Label tables translate when read (lib/i18n.js).
import { tr, translated } from "./i18n.js";

// The number format follows Settings (lib/settings.jsx sets it before each render).
let numberLocale;
export const setNumberLocale = (locale) => { numberLocale = locale; };
export const fmt = (n) => Number(n || 0).toLocaleString(numberLocale);

export const KIND_LABEL = translated({
  supplier_delay: "Supplier delay", plant_outage: "Plant outage", quality_hold: "Quality hold",
  unconfirmed: "Unconfirmed", noise: "Noise",
});

/* Tool groups for the calls chart: one hue per job, fixed order. */
const GROUP_LIST = [
  { id: "prod", label: "Production moves", color: "var(--s1)", tools: ["mes.reschedule", "mes.transfer"] },
  { id: "dealer", label: "Dealer notices & stop-sales", color: "var(--s2)", tools: ["dealer.notify", "dealer.stop_sale"] },
  { id: "cust", label: "Loaners & owner notices", color: "var(--s3)", tools: ["crm.assign_loaner", "crm.notify_customer"] },
  { id: "lot", label: "Lot holds", color: "var(--s4)", tools: ["quality.hold_lot"] },
  { id: "esc", label: "Escalations", color: "var(--s5)", tools: ["escalate"] },
];
export const GROUPS = GROUP_LIST.map((g) => ({ ...g, get label() { return tr(g.label); } }));

export const TOOL_WORD = translated({
  "mes.reschedule": "Reschedule", "mes.transfer": "Transfer", "dealer.notify": "Dealer notice",
  "dealer.stop_sale": "Stop sale", "crm.assign_loaner": "Loaner", "crm.notify_customer": "Owner notice",
  "quality.hold_lot": "Lot hold", escalate: "Escalate",
});
export const WRITE_TOOLS = new Set(Object.keys(TOOL_WORD).filter((t) => t !== "escalate"));

export const CAT_ORDER = ["supplier_delay", "plant_outage", "quality_hold", "unconfirmed", "compound", "noise"];
export const CAT_COLOR = {
  supplier_delay: "var(--s1)", plant_outage: "var(--s2)", quality_hold: "var(--s3)",
  unconfirmed: "var(--s4)", compound: "var(--s5)", noise: "#6b7894",
};
export const CAT_NAME = translated({ ...KIND_LABEL, compound: "Compound" });

export const PAGES = translated({
  overview: "Overview", events: "Event center", add: "Add events", tests: "Tests", ontology: "Knowledge graph", records: "Company records", logs: "Logs", guide: "Guide", settings: "Settings",
});

export const AGENT_ICON = { coordinator: "cpu", supply_chain: "wrench", quality: "shield", dealer_customer: "mail" };

export const passColor = (pct) => (pct === 100 ? "var(--good)" : pct >= 80 ? "var(--warn)" : "var(--bad)");
export const pctOf = (n, total) => (total ? Math.round((n / total) * 100) : 0);
export const kindsOf = (t) => (t.incidents || []).map((i) => i.kind);
export const kindWords = (t) => kindsOf(t).map((k) => KIND_LABEL[k]).join(" + ");
// The clock follows Settings → Time (12-hour or 24-hour); set before each render, like the number format.
let clock12 = true;
export const setClock = (twelve) => { clock12 = twelve; };
export const isClock12 = () => clock12;
// An event's received time, "2027-03-08T07:17:00" -> "Mar 8, 2027, 7:17 AM" (or "07:17" on a 24-hour clock).
export function when(s) {
  const m = String(s || "").match(/^(\d{4})-(\d{2})-(\d{2})[ T](\d{2}):(\d{2})/);
  if (!m) return String(s || "");
  const d = new Date(+m[1], +m[2] - 1, +m[3], +m[4], +m[5]);
  try {
    return new Intl.DateTimeFormat(numberLocale, { year: "numeric", month: "short", day: "numeric", hour: "numeric", minute: "2-digit", hour12: clock12 }).format(d);
  } catch { return String(s).replace("T", " "); }
}
// A clock time alone: "7:17 AM" or "07:17".
export function clockTime(t) {
  try { return new Date(t).toLocaleTimeString(numberLocale, { hour: clock12 ? "numeric" : "2-digit", minute: "2-digit", hour12: clock12 }); }
  catch { return ""; }
}

// A field name in words: "production_order_id" -> "production order", "new_date" -> "new date".
const FIELD_SPECIAL = { vins: "vehicles", vin: "vehicle", po: "production order", eta: "arrival" };
export const fieldWords = (k) => FIELD_SPECIAL[k] || String(k).replace(/_id$/, "").replace(/_/g, " ");

// A tool call's arguments in words: "production order PO-0316 · new date 2027-03-19".
export function argText(args) {
  return Object.entries(args || {}).map(([k, v]) => {
    if (Array.isArray(v)) return `${fieldWords(k)} ${v.length > 4 ? v.slice(0, 4).join(", ") + ` … +${v.length - 4}` : v.join(", ")}`;
    const s = String(v);
    return `${fieldWords(k)} ${s.length > 60 ? s.slice(0, 57) + "…" : s}`;
  }).join(" · ");
}

// A record type in words: "ProductionOrder" -> "Production order".
export const typeWords = (t) => String(t || "").replace(/([a-z])([A-Z])/g, "$1 $2").replace(/ ([A-Z])(?=[a-z])/g, (m, c) => ` ${c.toLowerCase()}`);

// A relation in words: "SCHEDULED_AT" -> "scheduled at", "USED_IN (BOM)" -> "used in (BOM)".
export const relationWords = (r) => String(r || "").replace(/\b[A-Z]+(?:_[A-Z]+)*\b(?! *\))/g, (w) => w.toLowerCase().replace(/_/g, " "));

// Text the tower wrote, in plain words: tool ids, field names and record types become words.
// "supplier_delay" -> "supplier delay", "mes.reschedule" -> "reschedule", "find_shipments(" -> "find shipments (",
// 'original_date="2027-03-15"' -> 'original date "2027-03-15"', "ProductionOrder" -> "Production order".
// Record ids (PO-0316, P_TX, SH-0190) and quoted message text are left as they are.
// Model names (qwen3:1.7b, llama3.2:1b, ...) never show: a leading "qwen3:1.7b: " is dropped, any other
// mention becomes "the AI model".
const MODEL_NAME = /\b(?:qwen|llama|gemma|mistral|phi|deepseek|granite|smollm)[\w.-]*(?::[\w.-]+)?/gi;
export function hideModel(text) {
  if (typeof text !== "string" || !text) return text;
  return text.replace(new RegExp(`^\\s*${MODEL_NAME.source}:\\s*`, "i"), "").replace(MODEL_NAME, tr("the AI model"));
}
export function plain(text) {
  if (typeof text !== "string" || !text) return text;
  return hideModel(text)
    .replace(/\b(?:mes|crm|dealer|quality)\.[a-z_]+\b/g, (t) => (TOOL_WORD[t] || t.split(".")[1].replace(/_/g, " ")).toLowerCase())
    .replace(/\b(Shipment|Part|Model|Plant|ProductionOrder|CustomerOrder|Dealer|Customer|Lot|Supplier|Vehicle)\.([a-z_]+)\b/g, (m, t, f) => `${typeWords(t).toLowerCase()} ${fieldWords(f)}`)
    .replace(/\b(ProductionOrder|CustomerOrder)\b/g, (t) => typeWords(t))
    .replace(/\b[a-z][a-z0-9]*(?:_[a-z0-9]+)+\b/g, (w) => w.replace(/_/g, " "))
    .replace(/\b([a-z]+)\(/g, "$1 (")
    .replace(/\b([a-z][a-z]*)=(?=["\w[])/g, "$1 ")
    .replace(/\b[A-Z]{2,}(?:_[A-Z]+)+\b/g, (w) => w.toLowerCase().replace(/_/g, " "))
    .replace(/([a-z])\+([a-z])/g, "$1 + $2");
}

export function sameSet(a, b) {
  if (a.length !== b.length) return false;
  const s = new Set(a);
  return b.every((x) => s.has(x));
}

// Which reader read a message, in words: never a model name. "llm_qwen3_1.7b" or "qwen3:1.7b" -> "AI model".
export function readerName(id) {
  if (!id || id === "rules") return tr("Rule reader");
  return tr("AI model");
}

export function niceStep(max) {
  const raw = max / 4, p = Math.pow(10, Math.floor(Math.log10(raw)));
  const n = raw / p;
  return (n <= 1 ? 1 : n <= 2 ? 2 : n <= 5 ? 5 : 10) * p;
}
