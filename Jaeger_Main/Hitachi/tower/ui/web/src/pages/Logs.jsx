import { useEffect, useState } from "react";
import { Icon } from "../lib/icons.jsx";
import { CAT_NAME, TOOL_WORD, argText, fmt, readerName } from "../lib/constants.js";
import { getJSON, useData } from "../lib/data.jsx";
import { useUi } from "../lib/ui.jsx";
import { CardHead, Mono, Status, Toggle } from "../components/common.jsx";
import { Page } from "./Page.jsx";

function OutputLogs() {
  const { ui, set } = useUi();
  const d = useData();
  const [files, setFiles] = useState(null);
  const [text, setText] = useState("");
  useEffect(() => { getJSON("/api/logs", []).then(setFiles); }, [d.loadedAt]);
  const name = files?.some((f) => f.name === ui.logFile) ? ui.logFile : files?.[0]?.name;
  useEffect(() => {
    if (!name) return;
    let live = true;
    getJSON(`/api/logs?name=${encodeURIComponent(name)}`, { text: "" }).then((doc) => { if (live) setText(doc.text); });
    return () => { live = false; };
  }, [name, d.loadedAt]);

  if (!files) return <div className="card empty">Loading…</div>;
  if (!files.length) return <div className="card empty">No saved output yet. Every <Mono>python start.py</Mono> run saves its output to <Mono>runs/logs/</Mono>.</div>;
  return (
    <div className="wr-layout">
      <div className="wr-list">
        {files.map((f) => (
          <div key={f.name} className={`wr-item ${f.name === name ? "on" : ""}`} onClick={() => set({ logFile: f.name })}>
            <b>{f.updated}</b><span className="mono note">{f.name}</span>
          </div>
        ))}
      </div>
      <div className="card">
        <CardHead title={name} sub={<>Everything <Mono>python start.py</Mono> printed in that run.</>}>
          <a className="btn" href={`data:text/plain;charset=utf-8,${encodeURIComponent(text)}`} download={name}><Icon name="doc" />Download</a>
        </CardHead>
        <pre className="console">{text}</pre>
      </div>
    </div>
  );
}

function CallLog() {
  const d = useData();
  const { ui, set } = useUi();
  const indexed = d.log.map((r, i) => ({ r, n: i + 1 }));
  const rows = indexed.filter(({ r }) => (!ui.callEvent || r.event_id === ui.callEvent) && (!ui.callFailed || !r.ok));
  const events = [...new Set(d.log.map((r) => r.event_id))];
  return (
    <div className="card">
      <CardHead title="Tool-call log · runs/run1/action_log.jsonl"
        sub={`Every call the tower made to the enterprise tools, in order: ${fmt(d.log.length)} calls, ${d.log.filter((r) => !r.ok).length} failed.`}>
        <div className="controls">
          <select className="chip-btn" value={ui.callEvent} onChange={(e) => set({ callEvent: e.target.value })}>
            <option value="">All events</option>
            {events.map((e) => <option key={e} value={e}>{e}</option>)}
          </select>
          <Toggle value={ui.callFailed ? "1" : "0"} options={[["0", "All"], ["1", "Failed only"]]} onChange={(v) => set({ callFailed: v === "1" })} />
        </div>
      </CardHead>
      <div className="scroll-x"><table>
        <thead><tr><th className="num">#</th><th>Event</th><th>Tool</th><th>Arguments</th><th>Result</th></tr></thead>
        <tbody>{rows.slice(0, 1000).map(({ r, n }) => (
          <tr key={n}>
            <td className="num note">{n}</td><td><b>{r.event_id}</b></td>
            <td>{TOOL_WORD[r.tool] || r.tool}<div className="note mono">{r.tool}</div></td>
            <td className="mono" style={{ maxWidth: 520 }}>{argText(r.args)}</td>
            <td><Status kind={r.ok ? "ok" : "fail"} /></td>
          </tr>
        ))}</tbody>
      </table></div>
      {rows.length > 1000 && <p className="note">Showing the first 1,000 of {fmt(rows.length)}.</p>}
    </div>
  );
}

function History() {
  const d = useData();
  const log = d.reports?.log || [];
  return (
    <div className="card">
      <CardHead title="Test run history · runs/test_log.jsonl" sub="One line per test set per run, newest first." />
      <div className="scroll-x"><table>
        <thead><tr><th>When</th><th>Test set</th><th>Reader</th><th className="num">Passed</th><th>By category</th></tr></thead>
        <tbody>{log.map((e, k) => (
          <tr key={k}>
            <td className="mono">{e.time}</td><td>{d.suiteById(e.suite)?.title || e.suite}</td><td>{readerName(e.reader)}</td>
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
  const tab = ui.logTab || "output";
  return (
    <Page title="Logs" subtitle={<span>Run output, every tool call, and the test-run history</span>}>
      <div className="tabs-row">
        <Toggle value={tab} options={[["output", "Run output"], ["calls", "Tool-call log"], ["history", "Test run history"]]} onChange={(v) => set({ logTab: v })} />
      </div>
      <div style={{ marginTop: 16 }}>
        {tab === "calls" ? <CallLog /> : tab === "history" ? <History /> : <OutputLogs />}
      </div>
    </Page>
  );
}
