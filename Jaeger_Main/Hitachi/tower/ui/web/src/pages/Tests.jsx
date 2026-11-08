// #/tests                         charts across every set and the run log
// #/tests/<suite>/<reader>        one test set: its charts and its cases
// #/tests/<suite>/<reader>/<id>   one test case: input, expected output, actual output
import { Fragment, useState } from "react";
import { Icon } from "../lib/icons.jsx";
import { CAT_NAME, CAT_ORDER, KIND_LABEL, TOOL_WORD, fmt, passColor, pctOf, readerName, sameSet } from "../lib/constants.js";
import { useData } from "../lib/data.jsx";
import { go, useUi } from "../lib/ui.jsx";
import { CardHead, KindTag, Mono, Status, Toggle } from "../components/common.jsx";
import { FailurePie, PassBars, PassFailPie, catRows } from "../components/charts.jsx";
import { Page } from "./Page.jsx";

const readerOf = (suite, id) => suite?.readers.find((r) => r.id === id);

// One row per saved reader: the newest `updated` stamp wins, then the score across every set it has.
function readerRollup(reports) {
  const byId = new Map();
  for (const suite of reports?.suites || []) {
    for (const reader of suite.readers) {
      const row = byId.get(reader.id) || { id: reader.id, updated: "", passed: 0, total: 0, sets: [] };
      if ((reader.updated || "") > row.updated) row.updated = reader.updated;
      row.passed += reader.passed;
      row.total += reader.total;
      row.sets.push({ suite, reader });
      byId.set(reader.id, row);
    }
  }
  return [...byId.values()].sort((a, b) => b.updated.localeCompare(a.updated) || a.id.localeCompare(b.id));
}

function incLine(i) {
  const d = (s) => (s || "").slice(5);
  if (i.kind === "plant_outage") return `${KIND_LABEL[i.kind]} ${i.plant_id || "?"} ${d(i.outage_start)}→${d(i.outage_end)}`;
  if (i.kind === "supplier_delay") return `${KIND_LABEL[i.kind]} ${i.part_id || "?"} @ ${i.plant_id || "?"} ${d(i.blocked_from)}→${d(i.blocked_until)}`;
  if (i.kind === "quality_hold") return `${KIND_LABEL[i.kind]} ${(i.lots || []).join(", ") || i.lot_id || i.part_id || ""}`.trim();
  return KIND_LABEL[i.kind] || i.kind;
}
function outcomeBits(o) {
  const bits = [];
  const n = (k) => o[k]?.length || 0;
  if (n("moved")) bits.push(`${n("moved")} order${n("moved") > 1 ? "s" : ""} moved`);
  if (n("dealers")) bits.push(`${n("dealers")} dealers notified`);
  if (n("loaners")) bits.push(`${n("loaners")} loaners`);
  if (n("lots")) bits.push(`${n("lots")} lot${n("lots") > 1 ? "s" : ""} held`);
  if (n("stop_sale_vins")) bits.push(`${n("stop_sale_vins")} stop-sale`);
  if (n("owners")) bits.push(`${n("owners")} owners notified`);
  if (o.escalate) bits.push("escalated to a human");
  return bits;
}
function outcomeHead(o) {
  const incs = (o.incidents || []).map(incLine);
  return incs.length ? incs.join(" + ") : o.escalate ? "Escalate only" : "No action";
}
function OutcomeLine({ o }) {
  return <><div style={{ fontWeight: 600 }}>{outcomeHead(o)}</div><div className="note">{outcomeBits(o).join(" · ") || "no calls"}</div></>;
}

function useTestsSubtitle() {
  const d = useData();
  const current = readerRollup(d.reports)[0];
  const sets = current ? current.sets.length : 0;
  return <>
    <span><b>{fmt(sets)}</b> test sets</span>
    <span>{current ? <><b>{readerName(current.id)}</b> · saved {current.updated}</> : "No results yet"}</span>
    <span><b>{fmt(current?.passed || 0)}</b> of <b>{fmt(current?.total || 0)}</b> cases passed</span>
  </>;
}

/* ---- level 1: every set ---- */
function AllSets() {
  const d = useData();
  const subtitle = useTestsSubtitle();
  const roll = readerRollup(d.reports);
  const current = roll[0];
  const rid = current.id;
  const [historyId, setHistoryId] = useState(null);
  const sets = current.sets.map(({ suite, reader }) => ({ s: suite, r: reader }));
  const passed = sets.reduce((a, x) => a + x.r.passed, 0), total = sets.reduce((a, x) => a + x.r.total, 0);
  const byCat = {};
  for (const { r } of sets) for (const [k, v] of Object.entries(r.by_category)) {
    byCat[k] ||= { passed: 0, total: 0 };
    byCat[k].passed += v.passed; byCat[k].total += v.total;
  }
  const log = (d.reports.log || []).filter((e) => e.reader === rid);
  const older = roll.slice(1);
  return (
    <Page title="Tests" subtitle={subtitle}>
      <div className="card">
        <CardHead title={`Latest results · ${readerName(rid)} reader`}
          sub={`Saved ${current.updated}. This score is only the newest reader. Each case passes when the tower's actions match the answer key and the simulator's handbook checks.`}>
          <div className="controls">
            <a className="btn" href="/runs/TEST_SUMMARY.md" download><Icon name="doc" />Summary .md</a>
          </div>
        </CardHead>
        <div className="grid g-charts">
          <div className="panel"><h4>Pass / fail · {passed} of {total} cases</h4><PassFailPie passed={passed} total={total} /></div>
          <div className="panel"><h4>Where the failures are</h4><FailurePie byCat={byCat} /></div>
          <div className="panel"><h4>By test set · click to open</h4>
            <PassBars rows={sets.map(({ s, r }) => ({ label: s.title, passed: r.passed, total: r.total, href: `#/tests/${s.id}/${r.id}` }))} /></div>
        </div>
        <div className="panel" style={{ marginTop: 16 }}><h4>By category</h4><PassBars rows={catRows(byCat)} /></div>
      </div>

      {older.length > 0 && (
        <div className="card" style={{ marginTop: 20 }}>
          <CardHead title="History" sub="Earlier readers, kept as a record. They are not part of the score above. Open a row to see that saved run." />
          <div className="scroll-x"><table>
            <thead><tr><th>Reader</th><th>Saved</th><th>Test sets</th><th className="num">Result</th></tr></thead>
            <tbody>
              {older.map((row) => {
                const open = historyId === row.id;
                const pct = pctOf(row.passed, row.total);
                const histLog = (d.reports.log || []).filter((e) => e.reader === row.id);
                return (
                  <Fragment key={row.id}>
                    <tr className="click" onClick={() => setHistoryId(open ? null : row.id)}>
                      <td><span className="tag">Historical</span> <b style={{ marginLeft: 8 }}>{readerName(row.id)}</b></td>
                      <td className="mono">{row.updated}</td>
                      <td>{row.sets.length}</td>
                      <td className="num"><b>{row.passed}/{row.total}</b> <span className="note">{pct}%</span></td>
                    </tr>
                    {open && (
                      <tr>
                        <td colSpan={4}>
                          <PassBars rows={row.sets.map(({ suite, reader }) => ({
                            label: suite.title, passed: reader.passed, total: reader.total,
                            href: `#/tests/${suite.id}/${reader.id}`,
                          }))} />
                          {histLog.length > 0 && <p className="note" style={{ margin: "12px 0 0" }}>{histLog.length} saved run{histLog.length === 1 ? "" : "s"} for this reader, from {histLog[histLog.length - 1].time} to {histLog[0].time}. Click a set above to open one.</p>}
                        </td>
                      </tr>
                    )}
                  </Fragment>
                );
              })}
            </tbody>
          </table></div>
        </div>
      )}

      <div className="card" style={{ marginTop: 20 }}>
        <CardHead title="Run history" sub={`Each time the ${readerName(rid)} reader was run, newest first.`} />
        <div className="scroll-x"><table>
          <thead><tr><th>When</th><th>Test set</th><th>Reader</th><th>Result</th><th className="num">Passed</th></tr></thead>
          <tbody>
            {log.map((e, k) => {
              const s = d.suiteById(e.suite), open = s && readerOf(s, e.reader);
              const pct = pctOf(e.passed, e.total);
              return (
                <tr key={k} className={open ? "click" : ""} onClick={open ? () => go(`#/tests/${e.suite}/${e.reader}`) : undefined}>
                  <td className="mono">{e.time}</td><td><b>{s?.title || e.suite}</b></td><td>{readerName(e.reader)}</td>
                  <td style={{ minWidth: 160 }}><div className="meter"><i style={{ width: `${pct}%`, background: passColor(pct) }} /></div></td>
                  <td className="num"><b>{e.passed}/{e.total}</b> <span className="note">{pct}%</span></td>
                </tr>
              );
            })}
            {!log.length && <tr><td colSpan={5} className="empty">No runs logged yet.</td></tr>}
          </tbody>
        </table></div>
      </div>
    </Page>
  );
}

/* ---- level 2: one set ---- */
function TestSet({ sid, rid }) {
  const d = useData();
  const { ui, set, toast } = useUi();
  const suite = d.suiteById(sid), reader = readerOf(suite, rid);
  const latest = readerRollup(d.reports)[0];
  const historical = latest && reader && reader.id !== latest.id;
  if (!reader) return (
    <Page title="Tests" trail={[["Tests", "#/tests"], [sid, null]]}>
      <div className="card empty">That test set has no results for this reader. <a href="#/tests" style={{ color: "var(--accent-2)" }}>Back to all tests</a></div>
    </Page>
  );
  const f = ui.caseFilter;
  const q = ui.q.trim().toLowerCase();
  const cases = reader.cases.filter((c) => (f.verdict === "all" || (f.verdict === "pass") === (c.verdict === "PASS"))
    && (f.cat === "all" || c.category === f.cat) && (!q || `${c.id} ${c.text}`.toLowerCase().includes(q)));
  const cats = CAT_ORDER.filter((k) => reader.by_category[k]);
  const confirm = ui.confirmDelete === `${sid}/${rid}`;
  const setFilter = (patch) => set((s) => ({ caseFilter: { ...s.caseFilter, ...patch } }));

  const del = async () => {
    try {
      const res = await fetch(`/api/test_reports/${encodeURIComponent(sid)}/${encodeURIComponent(rid)}`, { method: "DELETE" });
      const body = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(body.error || `HTTP ${res.status}`);
      toast(`Deleted ${sid}/${rid}`);
      go("#/tests");
    } catch (e) { toast(`Could not delete: ${e.message}`); }
    set({ confirmDelete: null });
    await d.reload();
  };

  return (
    <Page title={`${suite.title} · ${readerName(reader.id)}`} trail={[["Tests", "#/tests"], [suite.title, null]]}>
      {historical && <p className="note" style={{ margin: "0 0 12px" }}>Historical record, saved {reader.updated}. The current score uses {readerName(latest.id)}, saved {latest.updated}. <a href="#/tests" style={{ color: "var(--accent-2)" }}>Back to latest</a></p>}
      <div className="card">
        <CardHead title={`${suite.title} · ${readerName(reader.id)} reader`} sub={`${suite.subtitle}. Run ${reader.updated}.`}>
          <div className="controls">
            <a className="btn" href="#/tests">← All tests</a>
            {reader.report_md && <a className="btn" href={`/${reader.report_md}`} download><Icon name="doc" />Report .md</a>}
            {confirm ? <>
              <button className="btn danger solid" onClick={del}><Icon name="trash" />Delete for good</button>
              <button className="btn" onClick={() => set({ confirmDelete: null })}>Cancel</button>
            </> : <button className="btn danger" onClick={() => set({ confirmDelete: `${sid}/${rid}` })}><Icon name="trash" />Delete run</button>}
          </div>
        </CardHead>
        <div className="grid g-charts">
          <div className="panel"><h4>Pass / fail · {reader.passed} of {reader.total} cases</h4><PassFailPie passed={reader.passed} total={reader.total} /></div>
          <div className="panel"><h4>Where the failures are</h4><FailurePie byCat={reader.by_category} /></div>
          <div className="panel"><h4>By category</h4><PassBars rows={catRows(reader.by_category)} /></div>
        </div>
      </div>

      <div className="card" style={{ marginTop: 20 }}>
        <CardHead title={`Test cases (${cases.length} of ${reader.total})`} sub="Click a case to see its input, expected output and actual output.">
          <div className="controls">
            <Toggle value={f.verdict} options={[["all", "All"], ["pass", "Passed"], ["fail", "Failed"]]} onChange={(v) => setFilter({ verdict: v })} />
            <Toggle value={f.cat} options={[["all", "All kinds"], ...cats.map((k) => [k, CAT_NAME[k]])]} onChange={(v) => setFilter({ cat: v })} />
          </div>
        </CardHead>
        <div className="scroll-x"><table>
          <thead><tr><th>Case</th><th>Input</th><th>Expected output</th><th>Actual output</th><th>Result</th></tr></thead>
          <tbody>
            {cases.map((c) => (
              <tr key={c.id} className="click" onClick={() => go(`#/tests/${sid}/${rid}/${encodeURIComponent(c.id)}`)}>
                <td><b>{c.id}</b><div style={{ marginTop: 4 }}><KindTag kind={c.category} /></div></td>
                <td><div className="clip">{c.text}</div></td>
                <td><OutcomeLine o={c.expected} /></td><td><OutcomeLine o={c.actual} /></td>
                <td><Status kind={c.verdict === "PASS" ? "pass" : "fail"} /></td>
              </tr>
            ))}
            {!cases.length && <tr><td colSpan={5} className="empty">No cases match.</td></tr>}
          </tbody>
        </table></div>
      </div>
    </Page>
  );
}

/* ---- level 3: one case ---- */
function Reading({ incidents, escalate, reasoning = [] }) {
  const why = reasoning.length > 0 && <>
    <div className="section-title" style={{ margin: "12px 0 6px" }}>The model's reasoning</div>
    {reasoning.map((r, k) => <div className="reasoning" style={{ marginBottom: 6 }} key={k}><Icon name="cpu" /><span>{r}</span></div>)}
  </>;
  if (!incidents.length) return <>
    <p className="note" style={{ margin: 0 }}>{escalate ? "Read as unconfirmed: escalate to a human, change nothing." : "Read as noise: no action."}</p>{why}
  </>;
  return <>
    {incidents.map((i, k) => {
      const fields = Object.entries(i).filter(([key, v]) => !["kind", "model_reason", "evidence", "summary"].includes(key) && v && (!Array.isArray(v) || v.length));
      return (
        <div className="inc" style={{ marginBottom: 8 }} key={k}>
          <div><KindTag kind={i.kind} /></div>
          {fields.length > 0 && <div className="fields">{fields.map(([key, v]) => <span className="field" key={key}><span>{key.replace(/_/g, " ")}</span>{Array.isArray(v) ? v.join(", ") : String(v)}</span>)}</div>}
        </div>
      );
    })}
    {why}
  </>;
}

const EFFECTS = [["Orders moved", "moved"], ["Dealers notified", "dealers"], ["Loaners", "loaners"], ["Lots held", "lots"],
  ["Stop-sale vehicles", "stop_sale_vins"], ["Owners notified", "owners"]];

function Effects({ o, actual }) {
  return (
    <dl className="kv" style={{ marginTop: 10 }}>
      <dt>Escalate</dt><dd>{o.escalate ? "yes" : "no"}</dd>
      {EFFECTS.map(([l, k]) => <Fragment key={k}><dt>{l}</dt><dd>{(o[k] || []).length}</dd></Fragment>)}
      {actual && <>
        <dt>Tool calls</dt><dd>{fmt(o.calls)} ({o.failed} failed)</dd>
        <dt>By tool</dt><dd>{Object.entries(o.by_tool || {}).map(([t, n]) => `${TOOL_WORD[t] || t} ${n}`).join(" · ") || "none"}</dd>
      </>}
    </dl>
  );
}

function Cell({ v }) {
  if (!Array.isArray(v)) return v;
  if (!v.length) return <span className="na">0</span>;
  return <><b>{v.length}</b>{v.length <= 10 ? <div className="ids">{v.join(", ")}</div>
    : <details><summary>show ids</summary><div className="ids">{v.join(", ")}</div></details>}</>;
}

function TestCase({ sid, rid, cid }) {
  const d = useData();
  const suite = d.suiteById(sid), reader = readerOf(suite, rid);
  const idx = reader ? reader.cases.findIndex((c) => c.id === cid) : -1;
  const base = `#/tests/${sid}/${rid}`;
  if (idx < 0) return (
    <Page title="Tests" trail={[["Tests", "#/tests"], [suite?.title || sid, base], [cid, null]]}>
      <div className="card empty">Case not found. <a href={base} style={{ color: "var(--accent-2)" }}>Back to the set</a></div>
    </Page>
  );
  const c = reader.cases[idx], prev = reader.cases[idx - 1], next = reader.cases[idx + 1];
  const pass = c.verdict === "PASS";
  const mism = c.score?.mismatches || [];
  const diffs = [...mism, ...c.fails.filter(() => !mism.length)];
  const E = c.expected, A = c.actual;
  const rows = [["Escalate to a human", E.escalate ? "yes" : "no", A.escalate ? "yes" : "no", E.escalate === A.escalate],
    ...[["Orders moved", "moved"], ["Dealers notified", "dealers"], ["Loaners assigned", "loaners"], ["Lots held", "lots"],
      ["Stop-sale vehicles", "stop_sale_vins"], ["Owners notified", "owners"]].map(([l, k]) => [l, E[k] || [], A[k] || [], sameSet(E[k] || [], A[k] || [])])];
  return (
    <Page title={`${c.id} · ${CAT_NAME[c.category] || c.category}`} trail={[["Tests", "#/tests"], [suite.title, base], [c.id, null]]}>
      <div className="card">
        <div className="card-head">
          <div className="controls">
            <a className="btn" href={base}>← {suite.title}</a>
            {prev && <a className="btn" href={`${base}/${encodeURIComponent(prev.id)}`}>‹ {prev.id}</a>}
            {next && <a className="btn" href={`${base}/${encodeURIComponent(next.id)}`}>{next.id} ›</a>}
          </div>
          <span className="note">{readerName(reader.id)} reader · run {reader.updated}</span>
        </div>
        <div className={`panel verdict ${pass ? "pass" : "fail"}`} style={{ marginBottom: 16 }}>
          <span className="big-verdict"><Icon name={pass ? "ok" : "x"} />{pass ? "Passed" : "Failed"}</span>
          <span className="note">{pass ? "The actual output matches the expected output, and every action passed the simulator's handbook checks."
            : `${diffs.length} difference${diffs.length === 1 ? "" : "s"} from the expected output.`}</span>
        </div>
        <div className="io">
          <div className="panel"><h4><span className="n">1</span>Input · {c.source || "message"}</h4><pre className="msg">{c.text}</pre>
            {c.edge && <p className="note" style={{ margin: "10px 0 0" }}>Edge case: {c.edge}</p>}</div>
          <div className="panel"><h4><span className="n">2</span>Expected output</h4>
            <Reading incidents={E.incidents || []} escalate={E.escalate} /><Effects o={E} />
            <p className="note" style={{ margin: "10px 0 0" }}>The answer key traced through the company graph.</p></div>
          <div className="panel"><h4><span className="n">3</span>Actual output</h4>
            <Reading incidents={A.incidents || []} escalate={A.escalate} reasoning={A.reasoning || []} /><Effects o={A} actual />
            {c.summary && <p className="note" style={{ margin: "10px 0 0", color: "var(--text-2)" }}>{c.summary}</p>}</div>
        </div>
        {(diffs.length > 0 || c.warnings.length > 0) && <>
          <div className="section-title">Differences</div>
          <ul className="fails">
            {diffs.map((x, k) => <li className="f" key={`f${k}`}>✗ {x}</li>)}
            {c.warnings.map((w, k) => <li className="w" key={`w${k}`}>⚠ {w}</li>)}
          </ul>
        </>}
        <div className="section-title">Effect by effect</div>
        <div className="cmp">
          <div className="h">Effect</div><div className="h">Expected</div><div className="h">Actual</div><div className="h">Match</div>
          {rows.map(([l, e, a, ok]) => (
            <Fragment key={l}>
              <div className="lbl">{l}</div><div><Cell v={e} /></div><div><Cell v={a} /></div>
              <div className={ok ? "ok" : "no"}>{ok ? "✓ yes" : "✗ no"}</div>
            </Fragment>
          ))}
        </div>
      </div>
    </Page>
  );
}

export default function Tests() {
  const d = useData();
  const { segs } = useUi();
  const subtitle = useTestsSubtitle();
  if (!d.reports?.suites?.some((s) => s.readers.length)) return (
    <Page title="Tests" subtitle={subtitle}>
      <div className="card empty">{d.loadedAt ? <>No test results yet. Run <Mono>python start.py</Mono>.</> : "Loading…"}</div>
    </Page>
  );
  if (segs[1] && segs[2]) return segs[3]
    ? <TestCase sid={segs[1]} rid={segs[2]} cid={decodeURIComponent(segs[3])} />
    : <TestSet sid={segs[1]} rid={segs[2]} />;
  return <AllSets />;
}
