// #/tests                         charts across every set and the run log
// #/tests/<suite>/<reader>        one test set: its charts, then filters and cases beside the chosen case
// #/tests/<suite>/<reader>/<id>   the same, with that case chosen
import { Fragment, useEffect, useRef, useState } from "react";
import { Icon } from "../lib/icons.jsx";
import { CAT_NAME, CAT_ORDER, KIND_LABEL, TOOL_WORD, fmt, passColor, pctOf, plain, readerName, sameSet } from "../lib/constants.js";
import { newestBySuite, useData } from "../lib/data.jsx";
import { go, useUi } from "../lib/ui.jsx";
import { CardHead, KindTag, Mono, Status, Time, Toggle } from "../components/common.jsx";
import { FailurePie, PassBars, PassFailPie, catRows } from "../components/charts.jsx";
import { Page } from "./Page.jsx";
import { tr, trx } from "../lib/i18n.js";
import { ResetButton } from "../components/ResetButton.jsx";

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

export function incLine(i) {
  const d = (s) => (s || "").slice(5);
  if (i.kind === "plant_outage") return `${KIND_LABEL[i.kind]} ${i.plant_id || "?"} ${d(i.outage_start)}→${d(i.outage_end)}`;
  if (i.kind === "supplier_delay") return `${KIND_LABEL[i.kind]} ${i.part_id || "?"} @ ${i.plant_id || "?"} ${d(i.blocked_from)}→${d(i.blocked_until)}`;
  if (i.kind === "quality_hold") return `${KIND_LABEL[i.kind]} ${(i.lots || []).join(", ") || i.lot_id || i.part_id || ""}`.trim();
  return KIND_LABEL[i.kind] || i.kind;
}
export function outcomeBits(o) {
  const bits = [];
  const n = (k) => o[k]?.length || 0;
  if (n("moved")) bits.push(tr(n("moved") > 1 ? "{n} orders moved" : "{n} order moved", { n: n("moved") }));
  if (n("dealers")) bits.push(tr("{dealers} dealers notified", { dealers: n("dealers") }));
  if (n("loaners")) bits.push(tr("{loaners} loaners", { loaners: n("loaners") }));
  if (n("lots")) bits.push(tr(n("lots") > 1 ? "{n} lots held" : "{n} lot held", { n: n("lots") }));
  if (n("stop_sale_vins")) bits.push(tr("{stop_sale_vins} stop-sale", { stop_sale_vins: n("stop_sale_vins") }));
  if (n("owners")) bits.push(tr("{owners} owners notified", { owners: n("owners") }));
  if (o.escalate) bits.push("escalated to a human");
  return bits;
}
function outcomeHead(o) {
  const incs = (o.incidents || []).map(incLine);
  return incs.length ? incs.join(" + ") : o.escalate ? tr("Escalate only") : tr("No action");
}
export function OutcomeLine({ o }) {
  return <><div style={{ fontWeight: 600 }}>{outcomeHead(o)}</div><div className="note">{outcomeBits(o).join(" · ") || "no calls"}</div></>;
}

function useTestsSubtitle() {
  const d = useData();
  const score = newestBySuite(d.reports);
  const who = score.labels.length === 1 ? score.labels[0] : score.labels.length > 1 ? "newest reader per set" : "";
  return <>
    <span>{trx("{n} test cases", { n: <b>{fmt(score.total)}</b> })}</span>
    <span>{who ? trx("{who} · saved {when}", { who: <b>{who}</b>, when: score.updated }) : tr("No results yet")}</span>
    <span>{trx("{n} of {m} cases passed", { n: <b>{fmt(score.passed)}</b>, m: <b>{fmt(score.total)}</b> })}</span>
  </>;
}

function scoreCopy(sets) {
  const groups = new Map();
  for (const { suite, reader } of sets) {
    const names = groups.get(reader.label) || [];
    names.push(suite.title);
    groups.set(reader.label, names);
  }
  if (groups.size <= 1) {
    const label = [...groups.keys()][0] || "rules";
    return { title: tr("Latest results · {label}", { label: label }), sub: tr("Newest saved run of every set, all read by the {label}. A case passes when the tower's actions match the answer key and the simulator's handbook checks.", { label: label.toLowerCase() }) };
  }
  const bits = [...groups].map(([label, names]) => names.length === 1 ? `${label} on ${names[0]}` : tr("{label} on {names} sets", { label: label, names: names.length }));
  return { title: "Latest results", sub: tr("Newest saved run of each set: {bits}. A later run of one set does not replace the others.", { bits: bits.join("; ") }) };
}

/* ---- level 1: every set ---- */
function AllSets() {
  const d = useData();
  const subtitle = useTestsSubtitle();
  const score = newestBySuite(d.reports);
  const roll = readerRollup(d.reports).sort((a, b) => b.total - a.total || b.updated.localeCompare(a.updated));
  const [historyId, setHistoryId] = useState(null);
  const sets = score.sets.map(({ suite, reader }) => ({ s: suite, r: reader }));
  const { passed, total } = score;
  const byCat = {};
  for (const { r } of sets) for (const [k, v] of Object.entries(r.by_category)) {
    byCat[k] ||= { passed: 0, total: 0 };
    byCat[k].passed += v.passed; byCat[k].total += v.total;
  }
  const log = d.reports.log || [];
  const copy = scoreCopy(score.sets);
  return (
    <Page title={tr("Tests")} subtitle={subtitle}>
      <div className="card">
        <CardHead title={copy.title} sub={copy.sub}>
          <div className="controls"><ResetButton kind="tests" /></div>
        </CardHead>
        <div className="grid g-charts">
          <div className="panel"><h4>{tr("Pass / fail · {n} of {m} cases", { n: passed, m: total })}</h4><PassFailPie passed={passed} total={total} /></div>
          <div className="panel"><h4>{tr("Where the failures are")}</h4><FailurePie byCat={byCat} /></div>
          <div className="panel"><h4>{tr("By test set · click to open")}</h4>
            <PassBars rows={sets.map(({ s, r }) => ({ label: `${s.title} · ${r.label}`, passed: r.passed, total: r.total, href: `#/tests/${s.id}/${r.id}` }))} /></div>
        </div>
        <div className="panel" style={{ marginTop: 16 }}><h4>{tr("By category")}</h4><PassBars rows={catRows(byCat)} /></div>
      </div>

      <SummaryDownload runs={(d.reports.suites || []).reduce((n, s) => n + s.readers.length, 0)} />

      {roll.length > 0 && (
        <div className="card" style={{ marginTop: 20 }}>
          <CardHead title={tr("By reader")} sub={tr("Every set that reader has saved. The score above keeps only the newest run of each set. Open a row to see that reader's sets.")} />
          <div className="scroll-x"><table>
            <thead><tr><th>{tr("Reader")}</th><th>{tr("Saved")}</th><th>{tr("Test sets")}</th><th className="num">{tr("Result")}</th></tr></thead>
            <tbody>
              {roll.map((row) => {
                const open = historyId === row.id;
                const pct = pctOf(row.passed, row.total);
                const histLog = (d.reports.log || []).filter((e) => e.reader === row.id);
                return (
                  <Fragment key={row.id}>
                    <tr className="click" onClick={() => setHistoryId(open ? null : row.id)}>
                      <td><b>{readerName(row.id)}</b></td>
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
        <CardHead title={tr("Run history")} sub={tr("Every saved run, newest first.")} />
        <div className="scroll-x"><table>
          <thead><tr><th>{tr("When")}</th><th>{tr("Test set")}</th><th>{tr("Reader")}</th><th>{tr("Result")}</th><th className="num">{tr("Passed")}</th></tr></thead>
          <tbody>
            {log.map((e, k) => {
              const s = d.suiteById(e.suite), open = s && readerOf(s, e.reader);
              const pct = pctOf(e.passed, e.total);
              return (
                <tr key={k} className={open ? "click" : ""} onClick={open ? () => go(`#/tests/${e.suite}/${e.reader}`) : undefined}>
                  <td className="mono"><Time value={e.time} /></td><td><b>{s?.title || e.suite}</b></td><td>{readerName(e.reader)}</td>
                  <td style={{ minWidth: 160 }}><div className="meter"><i style={{ width: `${pct}%`, background: passColor(pct) }} /></div></td>
                  <td className="num"><b>{e.passed}/{e.total}</b> <span className="note">{pct}%</span></td>
                </tr>
              );
            })}
            {!log.length && <tr><td colSpan={5} className="empty">{tr("No runs logged yet.")}</td></tr>}
          </tbody>
        </table></div>
      </div>
    </Page>
  );
}

/* ---- level 2: one set ---- */
function TestSet({ sid, rid, cid }) {
  const d = useData();
  const { ui, set, toast } = useUi();
  // The chosen case. A case link (#/tests/<set>/<reader>/<case>) opens with that case chosen; picking
  // another updates the link without reloading the page.
  const [picked, setPicked] = useState(cid || null);
  const listRef = useRef(null);
  const pick = (id) => {
    setPicked(id);
    history.replaceState(null, "", `#/tests/${sid}/${rid}/${encodeURIComponent(id)}`);
  };
  useEffect(() => {
    const box = listRef.current, item = box?.querySelector(`[data-ev="${CSS.escape(picked || "")}"]`);
    if (!item) return;
    const b = box.getBoundingClientRect(), r = item.getBoundingClientRect();
    if (r.top < b.top || r.bottom > b.bottom) box.scrollTop += r.top - b.top - 8;
  }, [picked]);
  const suite = d.suiteById(sid), reader = readerOf(suite, rid);
  const latest = [...(suite?.readers || [])].sort((a, b) => (b.updated || "").localeCompare(a.updated || ""))[0];
  const historical = latest && reader && reader.id !== latest.id;
  if (!reader) return (
    <Page title={tr("Tests")} trail={[["Tests", "#/tests"], [sid, null]]}>
      <div className="card empty">{tr("That test set has no results for this reader.")}{" "}<a href="#/tests" style={{ color: "var(--accent-2)" }}>{tr("Back to all tests")}</a></div>
    </Page>
  );
  const f = ui.caseFilter;
  const q = ui.q.trim().toLowerCase();
  const cases = reader.cases.filter((c) => (f.verdict === "all" || (f.verdict === "pass") === (c.verdict === "PASS"))
    && (f.cat === "all" || c.category === f.cat) && (!q || `${c.id} ${c.text}`.toLowerCase().includes(q)));
  const cats = CAT_ORDER.filter((k) => reader.by_category[k]);
  const confirm = ui.confirmDelete === `${sid}/${rid}`;
  const setFilter = (patch) => set((s) => ({ caseFilter: { ...s.caseFilter, ...patch } }));
  // Counts for each option are taken with the other filter applied, so they add up to what you'd see.
  const byVerdict = (v) => (c) => v === "all" || (v === "pass") === (c.verdict === "PASS");
  const byCat = (k) => (c) => k === "all" || c.category === k;
  const searched = reader.cases.filter((c) => !q || `${c.id} ${c.text}`.toLowerCase().includes(q));
  const nVerdict = (v) => searched.filter(byCat(f.cat)).filter(byVerdict(v)).length;
  const nCat = (k) => searched.filter(byVerdict(f.verdict)).filter(byCat(k)).length;
  const label = (word, n) => <>{word} <span className="ev-n">{n}</span></>;
  const selIdx = Math.max(0, cases.findIndex((c) => c.id === picked));
  const sel = cases[selIdx];
  const selId = sel?.id;

  const del = async () => {
    try {
      const res = await fetch(`/api/test_reports/${encodeURIComponent(sid)}/${encodeURIComponent(rid)}`, { method: "DELETE" });
      const body = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(body.error || `HTTP ${res.status}`);
      toast(tr("Deleted {sid}/{rid}", { sid: sid, rid: rid }));
      go("#/tests");
    } catch (e) { toast(tr("Could not delete: {message}", { message: e.message })); }
    set({ confirmDelete: null });
    await d.reload();
  };

  return (
    <Page title={`${suite.title} · ${readerName(reader.id)}`} trail={[["Tests", "#/tests"], [suite.title, null]]}>
      {historical && <p className="note" style={{ margin: "0 0 12px" }}>Older run of this set, saved {reader.updated}. The current score uses {latest.label}, saved {latest.updated}. <a href={`#/tests/${sid}/${latest.id}`} style={{ color: "var(--accent-2)" }}>{tr("Open the current run")}</a></p>}
      <div className="card">
        <CardHead title={tr("{title} · {id}", { title: suite.title, id: readerName(reader.id) })} sub={`${suite.subtitle}. Run ${reader.updated}.`}>
          <div className="controls">
            <a className="btn" href="#/tests">{tr("← All tests")}</a>
            {reader.report_md && <a className="btn" href={`/${reader.report_md}`} download><Icon name="doc" />{tr("Download report")}</a>}
            {d.online ? null : confirm ? <>
              <button className="btn danger solid" onClick={del}><Icon name="trash" />{tr("Delete for good")}</button>
              <button className="btn" onClick={() => set({ confirmDelete: null })}>{tr("Cancel")}</button>
            </> : <button className="btn danger" onClick={() => set({ confirmDelete: `${sid}/${rid}` })}><Icon name="trash" />{tr("Delete run")}</button>}
          </div>
        </CardHead>
        <div className="grid g-charts">
          <div className="panel"><h4>{tr("Pass / fail · {n} of {m} cases", { n: reader.passed, m: reader.total })}</h4><PassFailPie passed={reader.passed} total={reader.total} /></div>
          <div className="panel"><h4>{tr("Where the failures are")}</h4><FailurePie byCat={reader.by_category} /></div>
          <div className="panel"><h4>{tr("By category")}</h4><PassBars rows={catRows(reader.by_category)} /></div>
        </div>
      </div>

      {/* Filters and the case list on the left, the chosen case on the right, like the Event Center's feed. */}
      <div className="ev-layout" style={{ marginTop: 20 }}>
        <div className="ev-side">
          <div className="ev-filters panel">
            <div className="ev-flabel">{tr("Result")}</div>
            <Toggle value={f.verdict} onChange={(v) => setFilter({ verdict: v })} options={[
              ["all", label(tr("All"), nVerdict("all"))], ["pass", label(tr("Passed"), nVerdict("pass"))], ["fail", label(tr("Failed"), nVerdict("fail"))]]} />
            <div className="ev-flabel">{tr("Kind of message")}</div>
            <div className="ev-kinds">
              {[["all", tr("All kinds")], ...cats.map((k) => [k, CAT_NAME[k]])].map(([k, word]) => (
                <button key={k} type="button" className={`ev-kind${f.cat === k ? " on" : ""}${k !== "all" ? ` k-${k}` : ""}`}
                  onClick={() => setFilter({ cat: k })} disabled={k !== "all" && !nCat(k)}>{label(word, nCat(k))}</button>
              ))}
            </div>
            <div className="ev-showing">{trx("Showing {n} of {m}", { n: <b>{cases.length}</b>, m: reader.total })}{q && <> · {tr("matching “{q}”", { q: ui.q.trim() })}</>}
              {(f.verdict !== "all" || f.cat !== "all" || q) && <button type="button" className="link-btn" onClick={() => set({ q: "", caseFilter: { verdict: "all", cat: "all" } })}>{tr("Clear")}</button>}
            </div>
          </div>
          {!cases.length ? <div className="panel empty">{tr("No cases match these filters.")}</div> : (
            <div className="ev-list" ref={listRef}>
              {cases.map((c) => (
                <div key={c.id} data-ev={c.id} className={`ev-item ${c.id === selId ? "on" : ""}`} onClick={() => pick(c.id)}>
                  <div className="row1"><b>{c.id}</b><Status kind={c.verdict === "PASS" ? "pass" : "fail"} /></div>
                  <div><KindTag kind={c.category} /></div>
                  <div className="txt">{c.text}</div>
                  {c.verdict !== "PASS" && (c.score?.mismatches?.[0] || c.fails?.[0]) && <div className="note case-why">{c.score?.mismatches?.[0] || c.fails[0]}</div>}
                </div>
              ))}
            </div>
          )}
        </div>
        {sel ? <div className="card"><CaseDetail c={sel} reader={reader} prev={cases[selIdx - 1]} next={cases[selIdx + 1]} onPick={pick} /></div>
          : <div className="card empty">{tr("Pick a case, or clear the filters.")}</div>}
      </div>
    </Page>
  );
}

/* ---- level 3: one case ---- */
export function Reading({ incidents, escalate, reasoning = [] }) {
  const why = reasoning.length > 0 && <>
    <div className="section-title" style={{ margin: "12px 0 6px" }}>{tr("The model's reasoning")}</div>
    {reasoning.map((r, k) => <div className="reasoning" style={{ marginBottom: 6 }} key={k}><Icon name="cpu" /><span>{r}</span></div>)}
  </>;
  if (!incidents.length) return <>
    <p className="note" style={{ margin: 0 }}>{escalate ? tr("Read as unconfirmed: escalate to a human, change nothing.") : tr("Read as noise: no action.")}</p>{why}
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

export function Effects({ o, actual }) {
  return (
    <dl className="kv" style={{ marginTop: 10 }}>
      <dt>{tr("Escalate")}</dt><dd>{o.escalate ? "yes" : "no"}</dd>
      {EFFECTS.map(([l, k]) => <Fragment key={k}><dt>{l}</dt><dd>{(o[k] || []).length}</dd></Fragment>)}
      {actual && <>
        <dt>{tr("Tool calls")}</dt><dd>{fmt(o.calls)} ({o.failed} failed)</dd>
        <dt>{tr("By tool")}</dt><dd>{Object.entries(o.by_tool || {}).map(([t, n]) => `${TOOL_WORD[t] || t} ${n}`).join(" · ") || "none"}</dd>
      </>}
    </dl>
  );
}

export function Cell({ v }) {
  if (!Array.isArray(v)) return v;
  if (!v.length) return <span className="na">0</span>;
  return <><b>{v.length}</b>{v.length <= 10 ? <div className="ids">{v.join(", ")}</div>
    : <details><summary>{tr("show ids")}</summary><div className="ids">{v.join(", ")}</div></details>}</>;
}

// One case: verdict, input, expected and actual output, the differences, and effect by effect.
function CaseDetail({ c, reader, prev, next, onPick }) {
  const pass = c.verdict === "PASS";
  const mism = c.score?.mismatches || [];
  const diffs = [...mism, ...c.fails.filter(() => !mism.length)];
  const E = c.expected, A = c.actual;
  const rows = [["Escalate to a human", E.escalate ? "yes" : "no", A.escalate ? "yes" : "no", E.escalate === A.escalate],
    ...[["Orders moved", "moved"], ["Dealers notified", "dealers"], ["Loaners assigned", "loaners"], ["Lots held", "lots"],
      ["Stop-sale vehicles", "stop_sale_vins"], ["Owners notified", "owners"]].map(([l, k]) => [l, E[k] || [], A[k] || [], sameSet(E[k] || [], A[k] || [])])];
  return (
    <>
      <div className="card-head">
        <div><h3>{c.id} · {CAT_NAME[c.category] || c.category}</h3><p className="sub">{readerName(reader.id)} · {tr("run {when}", { when: reader.updated })}</p></div>
        <div className="controls">
          {prev && <button type="button" className="btn" onClick={() => onPick(prev.id)}>‹ {prev.id}</button>}
          {next && <button type="button" className="btn" onClick={() => onPick(next.id)}>{next.id} ›</button>}
        </div>
      </div>
      <div className={`panel verdict ${pass ? "pass" : "fail"}`} style={{ marginBottom: 16 }}>
        <span className="big-verdict"><Icon name={pass ? "ok" : "x"} />{pass ? tr("Passed") : tr("Failed")}</span>
        <span className="note">{pass ? tr("The actual output matches the expected output, and every action passed the simulator's handbook checks.")
          : tr(diffs.length === 1 ? "{n} difference from the expected output." : "{n} differences from the expected output.", { n: diffs.length })}</span>
      </div>
      <div className="io">
        <div className="panel"><h4><span className="n">1</span>{tr("Input")} · {c.source || tr("message")}</h4><pre className="msg">{c.text}</pre>
          {c.edge && <p className="note" style={{ margin: "10px 0 0" }}>{tr("Edge case: {edge}", { edge: plain(c.edge) })}</p>}</div>
        <div className="panel"><h4><span className="n">2</span>{tr("Expected output")}</h4>
          <Reading incidents={E.incidents || []} escalate={E.escalate} /><Effects o={E} />
          <p className="note" style={{ margin: "10px 0 0" }}>{tr("The answer key traced through the company graph.")}</p></div>
        <div className="panel"><h4><span className="n">3</span>{tr("Actual output")}</h4>
          <Reading incidents={A.incidents || []} escalate={A.escalate} reasoning={A.reasoning || []} /><Effects o={A} actual />
          {c.summary && <p className="note" style={{ margin: "10px 0 0", color: "var(--text-2)" }}>{c.summary}</p>}</div>
      </div>
      {(diffs.length > 0 || c.warnings.length > 0) && <>
        <div className="section-title">{tr("Differences")}</div>
        <ul className="fails">
          {diffs.map((x, k) => <li className="f" key={`f${k}`}>✗ {x}</li>)}
          {c.warnings.map((w, k) => <li className="w" key={`w${k}`}>⚠ {w}</li>)}
        </ul>
      </>}
      <div className="section-title">{tr("Effect by effect")}</div>
      <div className="cmp">
        <div className="h">{tr("Effect")}</div><div className="h">{tr("Expected")}</div><div className="h">{tr("Actual")}</div><div className="h">{tr("Match")}</div>
        {rows.map(([l, e, a, ok]) => (
          <Fragment key={l}>
            <div className="lbl">{tr(l)}</div><div><Cell v={e} /></div><div><Cell v={a} /></div>
            <div className={ok ? "ok" : "no"}>{ok ? `✓ ${tr("yes")}` : `✗ ${tr("no")}`}</div>
          </Fragment>
        ))}
      </div>
    </>
  );
}

// The test summary as a PDF, built by the server from the same results this page shows.
function SummaryDownload({ runs }) {
  const { toast } = useUi();
  const [busy, setBusy] = useState(false);
  const download = async () => {
    setBusy(true);
    try {
      const res = await fetch("/api/summary.pdf", { cache: "no-store" });
      if (!res.ok) throw new Error(String(res.status));
      const name = (res.headers.get("Content-Disposition") || "").match(/filename="([^"]+)"/)?.[1] || "test-summary.pdf";
      const url = URL.createObjectURL(await res.blob());
      const a = Object.assign(document.createElement("a"), { href: url, download: name });
      document.body.appendChild(a);
      a.click();
      a.remove();
      setTimeout(() => URL.revokeObjectURL(url), 2000);
    } catch {
      toast(tr("Could not build the summary PDF"));
    } finally {
      setBusy(false);
    }
  };
  return (
    <div className="card dl-card">
      <div className="dl-doc" aria-hidden="true"><Icon name="doc" /><span>PDF</span></div> {/* i18n-ignore: a file format */}
      <div className="dl-body">
        <h3>{tr("Test summary report")}</h3>
        <p className="sub">{tr("A printable report of these results: the score of every test set and reader, results by kind of message, and every failed case with what differed. Written in English.")}</p>
        <ul className="dl-points">
          <li><Icon name="ok" />{tr(runs === 1 ? "Scores for 1 saved run" : "Scores for {n} saved runs", { n: runs })}</li>
          <li><Icon name="ok" />{tr("Failed cases, with the differences")}</li>
          <li><Icon name="ok" />{tr("Built from the newest saved results")}</li>
        </ul>
      </div>
      <button type="button" className="btn primary dl-btn" onClick={download} disabled={busy}>
        {busy ? <><span className="spin"><Icon name="refresh" /></span>{tr("Preparing…")}</> : <><Icon name="download" />{tr("Download PDF")}</>}
      </button>
    </div>
  );
}

export default function Tests() {
  const d = useData();
  const { segs } = useUi();
  const subtitle = useTestsSubtitle();
  if (!d.reports?.suites?.some((s) => s.readers.length)) return (
    <Page title={tr("Tests")} subtitle={subtitle}>
      <div className="card empty">
        {d.loadedAt ? tr("No test results yet.") : tr("Loading…")}
        {d.loadedAt && <div className="controls" style={{ justifyContent: "center", marginTop: 12 }}><ResetButton kind="tests" /></div>}
      </div>
    </Page>
  );
  if (segs[1] && segs[2]) return <TestSet sid={segs[1]} rid={segs[2]} cid={segs[3] ? decodeURIComponent(segs[3]) : null} />;
  return <AllSets />;
}
