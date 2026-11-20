// Export the Event center's events (whatever the search and filters show) as a text log, CSV or JSON.
// Everything is built in the browser from data the page already has: traces, the action log, the outbox.
import { KIND_LABEL, kindWords } from "./constants.js";
import { categoryOf, eventOutcome } from "../pages/EventResults.jsx";

const OUTCOME_WORD = { acted: "Acted", esc: "Escalated", none: "No action" };
const FIELDS = ["plant_id", "part_id", "supplier_id", "shipment_id", "lot_id", "blocked_from", "blocked_until",
  "outage_start", "outage_end", "build_start", "build_end"];

// One plain record per event: the message, how it was read, every tool call with its result, and the effects.
function record(d, t) {
  const rows = d.byEvent[t.event_id] || [];
  const effects = eventOutcome(t, rows);
  const calls = (t.calls || []).map((c, i) => ({
    tool: c.tool, args: c.args || {}, reason: c.reason || "", agent: c.agent ? d.agentName(c.agent) : "",
    ok: rows[i] ? !!rows[i].ok : true,
  }));
  return {
    event_id: t.event_id,
    received_at: t.received_at || "",
    source: t.source || "",
    message: t.text || "",
    type: categoryOf(t),
    read_as: kindWords(t),
    outcome: OUTCOME_WORD[d.outcome(t.event_id)] || d.outcome(t.event_id),
    incidents: (t.incidents || []).map((i) => ({
      kind: i.kind, reader: i.reader || "rules",
      ...Object.fromEntries(FIELDS.filter((k) => i[k]).map((k) => [k, i[k]])),
      ...(i.model_reason ? { reason: i.model_reason } : {}),
      ...(i.question ? { question: i.question } : {}),
    })),
    effects: {
      escalated: effects.escalate, orders_moved: effects.moved.length, dealers_notified: effects.dealers.length,
      loaners: effects.loaners.length, lots_held: effects.lots.length, stop_sale_vehicles: effects.stop_sale_vins.length,
      owners_notified: effects.owners.length,
    },
    tool_calls: calls.length,
    failed_calls: calls.filter((c) => !c.ok).length,
    calls,
    notifications: d.outbox.filter((n) => n && n.event_id === t.event_id).length,
    summary: t.summary || "",
    guardrail: t.guardrail || "",
  };
}

const plural = (n, word) => `${n} ${word}${n === 1 ? "" : "s"}`;
const argLine = (args) => Object.entries(args).map(([k, v]) => `${k}=${Array.isArray(v) ? `[${v.join(",")}]` : v}`).join(" ");

function toLog(records, header) {
  const out = [...header.map((h) => `# ${h}`), ""];
  for (const r of records) {
    out.push(`==== ${r.event_id} · ${r.received_at.replace("T", " ")} · ${r.source}`);
    out.push(`Outcome: ${r.outcome} · ${r.read_as || KIND_LABEL[r.type] || r.type}`);
    out.push(`Message: ${r.message}`);
    out.push("Read as:");
    for (const i of r.incidents) {
      const fields = FIELDS.filter((k) => i[k]).map((k) => `${k}=${i[k]}`).join(" ");
      out.push(`  - ${i.kind} (read by ${i.reader})${fields ? ` ${fields}` : ""}`);
      if (i.reason) out.push(`    Reason: ${i.reason}`);
      if (i.question) out.push(`    Question: ${i.question}`);
    }
    if (!r.incidents.length) out.push("  - nothing");
    out.push(`Actions (${plural(r.tool_calls, "call")}, ${r.failed_calls} failed):`);
    for (const c of r.calls) {
      out.push(`  [${c.ok ? "ok" : "FAILED"}] ${c.tool} ${argLine(c.args)}`.trimEnd());
      if (c.reason || c.agent) out.push(`         ${[c.agent, c.reason].filter(Boolean).join(": ")}`);
    }
    if (!r.calls.length) out.push("  - none");
    const e = r.effects;
    out.push(`Effects: ${e.orders_moved} orders moved, ${e.dealers_notified} dealers notified, ${e.loaners} loaners, `
      + `${e.lots_held} lots held, ${e.stop_sale_vehicles} stop-sale vehicles, ${e.owners_notified} owners notified`
      + `${e.escalated ? ", escalated to a human" : ""}; ${plural(r.notifications, "channel message")}`);
    out.push(`Summary: ${r.summary}`);
    out.push("");
  }
  return out.join("\n");
}

// A cell that starts with = + - @ is quoted with a leading apostrophe, so a spreadsheet never runs it as a formula.
function cell(v) {
  let s = v == null ? "" : String(v);
  if (/^[=+\-@\t\r]/.test(s)) s = `'${s}`;
  return /[",\n\r]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
}

const CSV_COLUMNS = [
  ["event_id", (r) => r.event_id], ["received_at", (r) => r.received_at], ["source", (r) => r.source],
  ["type", (r) => r.type], ["read_as", (r) => r.read_as], ["outcome", (r) => r.outcome],
  ["readers", (r) => [...new Set(r.incidents.map((i) => i.reader))].join(" ")],
  ["escalated", (r) => (r.effects.escalated ? "yes" : "no")], ["orders_moved", (r) => r.effects.orders_moved],
  ["dealers_notified", (r) => r.effects.dealers_notified], ["loaners", (r) => r.effects.loaners],
  ["lots_held", (r) => r.effects.lots_held], ["stop_sale_vehicles", (r) => r.effects.stop_sale_vehicles],
  ["owners_notified", (r) => r.effects.owners_notified], ["tool_calls", (r) => r.tool_calls],
  ["failed_calls", (r) => r.failed_calls], ["notifications", (r) => r.notifications],
  ["message", (r) => r.message], ["summary", (r) => r.summary],
];

function toCsv(records) {
  const lines = [CSV_COLUMNS.map(([name]) => name).join(",")];
  for (const r of records) lines.push(CSV_COLUMNS.map(([, get]) => cell(get(r))).join(","));
  return lines.join("\r\n") + "\r\n";
}

const FORMATS = {
  log: { ext: "log", type: "text/plain;charset=utf-8" },
  csv: { ext: "csv", type: "text/csv;charset=utf-8" },
  json: { ext: "json", type: "application/json;charset=utf-8" },
};

// Build the file for these events and hand it to the browser (a save dialog in the desktop app).
export function exportEvents(d, list, format, scope) {
  const records = list.map((t) => record(d, t));
  const stamp = new Date();
  const pad = (n) => String(n).padStart(2, "0");
  const tag = `${stamp.getFullYear()}${pad(stamp.getMonth() + 1)}${pad(stamp.getDate())}-${pad(stamp.getHours())}${pad(stamp.getMinutes())}`;
  const header = [
    "Wacky Wheels Control Tower · event history",
    `Exported ${stamp.toLocaleString()} · ${records.length} of ${d.traces.length} events${scope ? ` · ${scope}` : ""}`,
  ];
  const body = format === "csv" ? "﻿" + toCsv(records)
    : format === "json" ? JSON.stringify({ exported_at: stamp.toISOString(), scope: scope || "all events", count: records.length, events: records }, null, 2) + "\n"
    : toLog(records, header);
  const { ext, type } = FORMATS[format];
  const url = URL.createObjectURL(new Blob([body], { type }));
  const a = Object.assign(document.createElement("a"), { href: url, download: `event-history-${tag}${scope ? "-filtered" : ""}.${ext}` });
  document.body.appendChild(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
  return records.length;
}
