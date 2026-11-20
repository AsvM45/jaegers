import { Select } from "../components/Select.jsx";
import { CAT_NAME, TOOL_WORD, argText, fmt, plain } from "../lib/constants.js";
import { useData } from "../lib/data.jsx";
import { useUi } from "../lib/ui.jsx";
import { CardHead, Status, Time, Toggle } from "../components/common.jsx";
import { Page } from "./Page.jsx";
import { tr } from "../lib/i18n.js";

function CallLog() {
  const d = useData();
  const { ui, set } = useUi();
  const indexed = d.log.map((r, i) => ({ r, n: i + 1 }));
  const rows = indexed.filter(({ r }) => (!ui.callEvent || r.event_id === ui.callEvent) && (!ui.callFailed || !r.ok));
  const events = [...new Set(d.log.map((r) => r.event_id))];
  return (
    <div className="card">
      <CardHead title={tr("Tool-call log")}
        sub={tr("Every call the tower made to the enterprise tools, in order: {log} calls, {ok} failed.", { log: fmt(d.log.length), ok: d.log.filter((r) => !r.ok).length })}>
        <div className="controls">
          <Select size="sm" label={tr("Event")} width={170} value={ui.callEvent} onChange={(v) => set({ callEvent: v })}
            options={[["", tr("All events")], ...events.map((e) => [e, e])]} />
          <Toggle value={ui.callFailed ? "1" : "0"} options={[["0", tr("All")], ["1", tr("Failed only")]]} onChange={(v) => set({ callFailed: v === "1" })} />
        </div>
      </CardHead>
      <div className="scroll-x"><table>
        <thead><tr><th className="num">#</th><th>{tr("Event")}</th><th>{tr("Tool")}</th><th>{tr("Arguments")}</th><th>{tr("Result")}</th></tr></thead>
        <tbody>
          {rows.slice(0, 1000).map(({ r, n }) => (
            <tr key={n}>
              <td className="num note">{n}</td><td><b>{r.event_id}</b></td>
              <td>{TOOL_WORD[r.tool] || plain(r.tool)}</td>
              <td className="mono" style={{ maxWidth: 520 }}>{argText(r.args)}</td>
              <td><Status kind={r.ok ? "ok" : "fail"} /></td>
            </tr>
          ))}
          {!rows.length && <tr><td colSpan={5} className="empty">{ui.callFailed ? tr("No failed calls.") : tr("No calls match.")}</td></tr>}
        </tbody>
      </table></div>
      {rows.length > 1000 && <p className="note">Showing the first 1,000 of {fmt(rows.length)}.</p>}
    </div>
  );
}

// Every message the tower sent to dealers and owners, across all events (each event shows only its own).
function Notifications() {
  const d = useData();
  const { ui, set } = useUi();
  const all = d.outbox.filter(Boolean);
  const rows = all.filter((n) => !ui.noteEvent || n.event_id === ui.noteEvent);
  const events = [...new Set(all.map((n) => n.event_id))];
  const byRoute = {};
  for (const n of all) byRoute[n.route || "—"] = (byRoute[n.route || "—"] || 0) + 1;
  return (
    <div className="card">
      <CardHead title={tr("Notifications")}
        sub={tr("Every message the tower sent to dealers and owners: {n} messages. {routes}", { n: fmt(all.length),
          routes: Object.entries(byRoute).map(([r, n]) => `${r} ${fmt(n)}`).join(" · ") })}>
        <div className="controls">
          <Select size="sm" label={tr("Event")} width={170} value={ui.noteEvent || ""} onChange={(v) => set({ noteEvent: v })}
            options={[["", tr("All events")], ...events.map((e) => [e, e])]} />
        </div>
      </CardHead>
      <div className="scroll-x"><table>
        <thead><tr><th>{tr("Event")}</th><th>{tr("Channel")}</th><th>{tr("To")}</th><th>{tr("Subject")}</th><th>{tr("Status")}</th></tr></thead>
        <tbody>
          {rows.slice(0, 1000).map((n, k) => (
            <tr key={k}>
              <td><b>{n.event_id}</b></td><td><b>{n.route}</b><div className="note">{n.sink}</div></td>
              <td>{n.recipient_id || (n.to || []).join(", ") || "—"}</td>
              <td style={{ color: "var(--text-2)" }}>{n.subject || ""}</td>
              <td><span className="tag">{String(n.status || "").replace(/_/g, " ")}</span></td>
            </tr>
          ))}
          {!rows.length && <tr><td colSpan={5} className="empty">{tr("No notifications yet.")}</td></tr>}
        </tbody>
      </table></div>
      {rows.length > 1000 && <p className="note">{tr("Showing the first 1,000 of {n}.", { n: fmt(rows.length) })}</p>}
    </div>
  );
}

// Every task one agent handed another, across all events, with what came back.
function Handoffs() {
  const d = useData();
  const { ui, set } = useUi();
  const all = d.traces.flatMap((t) => (t.handoffs || []).map((h) => ({ ...h, event_id: t.event_id })));
  const rows = all.filter((h) => !ui.handEvent || h.event_id === ui.handEvent);
  const refused = all.reduce((a, h) => a + (h.refused?.length || 0), 0);
  return (
    <div className="card">
      <CardHead title={tr("Agent handoffs")}
        sub={tr("Every task the coordinator gave a specialist, and what it returned: {n} handoffs, {r} planned calls refused.", { n: fmt(all.length), r: fmt(refused) })}>
        <div className="controls">
          <Select size="sm" label={tr("Event")} width={170} value={ui.handEvent || ""} onChange={(v) => set({ handEvent: v })}
            options={[["", tr("All events")], ...d.traces.map((t) => [t.event_id, t.event_id])]} />
        </div>
      </CardHead>
      <div className="scroll-x"><table>
        <thead><tr><th>{tr("Event")}</th><th>{tr("From → to")}</th><th>{tr("Task")}</th><th>{tr("Returned")}</th></tr></thead>
        <tbody>
          {rows.map((h, k) => (
            <tr key={k}>
              <td><b>{h.event_id}</b></td>
              <td style={{ whiteSpace: "nowrap" }}>{d.agentName(h.from)} → {d.agentName(h.to)}</td>
              <td style={{ color: "var(--text-2)" }}>{h.task}</td>
              <td>{h.returned}{h.accepted != null && <div className="note">{tr("{n} accepted", { n: h.accepted })}{h.refused?.length ? ` · ${tr("{n} refused", { n: h.refused.length })}` : ""}</div>}</td>
            </tr>
          ))}
          {!rows.length && <tr><td colSpan={4} className="empty">{tr("No handoffs yet.")}</td></tr>}
        </tbody>
      </table></div>
    </div>
  );
}

function History() {
  const d = useData();
  const log = d.reports?.log || [];
  return (
    <div className="card">
      <CardHead title={tr("Test run history")} sub={tr("One line per test set per run, newest first.")} />
      <div className="scroll-x"><table>
        <thead><tr><th>{tr("When")}</th><th>{tr("Test set")}</th><th className="num">{tr("Passed")}</th><th>{tr("By category")}</th></tr></thead>
        <tbody>{log.map((e, k) => (
          <tr key={k}>
            <td className="mono"><Time value={e.time} /></td><td>{d.suiteById(e.suite)?.title || e.suite}</td>
            <td className="num"><b>{e.passed}/{e.total}</b></td>
            <td className="note">{Object.entries(e.by_category || {}).map(([c, v]) => `${CAT_NAME[c] || c} ${v[0]}/${v[1]}`).join(" · ")}</td>
          </tr>
        ))}</tbody>
      </table></div>
    </div>
  );
}

export default function Logs() {
  const { ui, set } = useUi();
  const tab = ["calls", "notes", "handoffs", "history"].includes(ui.logTab) ? ui.logTab : "calls";
  return (
    <Page title={tr("Logs")} subtitle={<span>{tr("Every tool call, notification and agent handoff, and the test-run history")}</span>}>
      <div className="tabs-row">
        <Toggle value={tab} onChange={(v) => set({ logTab: v })} options={[["calls", tr("Tool-call log")], ["notes", tr("Notifications")],
          ["handoffs", tr("Agent handoffs")], ["history", tr("Test run history")]]} />
      </div>
      <div style={{ marginTop: 16 }}>
        {tab === "notes" ? <Notifications /> : tab === "handoffs" ? <Handoffs /> : tab === "history" ? <History /> : <CallLog />}
      </div>
    </Page>
  );
}
