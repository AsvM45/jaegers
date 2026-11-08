// Live grade. POST /api/run starts the same suites start.py runs; the stream draws each case as it finishes.
import { useEffect, useRef, useState } from "react";
import { Icon } from "../lib/icons.jsx";
import { useData } from "../lib/data.jsx";
import { useUi } from "../lib/ui.jsx";
import { CardHead } from "./common.jsx";

const EMPTY = {
  seq: 0, running: false, reader: null, model: "", ollama: false, why: "",
  passed: 0, failed: 0, total: 0, ok: null, error: null, tail: [], suites: [],
};

function tally(job) {
  const passed = job.suites.reduce((a, s) => a + s.passed, 0);
  const failed = job.suites.reduce((a, s) => a + s.failed, 0);
  return { ...job, passed, failed };
}

export function reduceRun(job, ev) {
  if (!ev || ev.type === "ping") return job;
  if (ev.type === "reset") return ev.job || job;
  const base = job || EMPTY;
  if (ev.type === "log") return { ...base, tail: [...(base.tail || []), ev.text].slice(-12) };
  if (ev.type === "suite") {
    const suites = base.suites.map((s) => (s.id === ev.id
      ? { ...s, status: ev.status, total: ev.total ?? s.total, passed: ev.passed ?? s.passed, failed: ev.failed ?? s.failed }
      : s));
    return tally({ ...base, suites });
  }
  if (ev.type === "case") {
    const suites = base.suites.map((s) => (s.id === ev.suite
      ? { ...s, passed: ev.passed, failed: ev.failed, cases: [...s.cases, ev.case] }
      : s));
    return tally({ ...base, suites });
  }
  if (ev.type === "done") {
    return {
      ...base, running: false, ok: ev.ok, error: ev.error,
      passed: ev.passed ?? base.passed, failed: ev.failed ?? base.failed, total: ev.total ?? base.total,
    };
  }
  return base;
}

function folderFor(label) {
  return label === "rules" ? "rules" : `llm_${(label || "").replace(":", "_")}`;
}

function blurb(job, mode) {
  if (job?.running) {
    const seen = job.passed + job.failed;
    const who = job.reader === "rules" ? "rule reader" : `${job.model} + rule check`;
    return `Running with the ${who}. ${seen} of ${job.total} cases finished.`;
  }
  if (job?.suites?.length) {
    if (job.ok) return `Finished. ${job.passed} passed${job.failed ? `, ${job.failed} failed` : ""}.`;
    return job.error ? `Stopped. ${job.error}.` : `Finished with ${job.failed} failed.`;
  }
  if (mode === "both") return "Grades the 15 given events with the model, then checks every reading against the rules. Each case shows up when it finishes.";
  return "Grades the 15 given events with the rule reader. Each case shows up as soon as it finishes. This does not re-run the event feed.";
}

export function RunTests() {
  const { reload } = useData();
  const { toast } = useUi();
  const [job, setJob] = useState(null);
  const [mode, setMode] = useState("rules");
  const seq = useRef(-1);
  const sawRun = useRef(false);
  const feed = useRef(null);
  const stick = useRef(true);

  const accept = (data) => {
    if (!data || typeof data.seq !== "number" || data.seq <= seq.current) return;
    seq.current = data.seq;
    setJob(data);
  };

  useEffect(() => {
    let stop = false;
    const es = new EventSource("/api/run/stream");
    es.addEventListener("state", (e) => { if (!stop) accept(JSON.parse(e.data)); });
    es.addEventListener("update", (e) => {
      if (stop) return;
      const ev = JSON.parse(e.data);
      if (typeof ev.seq === "number" && ev.seq <= seq.current) return;
      if (typeof ev.seq === "number") seq.current = ev.seq;
      setJob((cur) => reduceRun(cur, ev));
    });
    const poll = setInterval(async () => {
      if (stop) return;
      try {
        const res = await fetch("/api/run", { cache: "no-store" });
        if (res.ok) accept(await res.json());
      } catch { /* the stream is the live path; the next poll retries */ }
    }, 1000);
    return () => { stop = true; clearInterval(poll); es.close(); };
  }, []);

  useEffect(() => {
    if (!job) return;
    if (job.running) sawRun.current = true;
    else if (sawRun.current) { sawRun.current = false; reload(); }
  }, [job, job?.running, reload]);

  const seen = (job?.passed || 0) + (job?.failed || 0);
  useEffect(() => {
    const el = feed.current;
    if (el && stick.current) el.scrollTop = el.scrollHeight;
  }, [seen]);

  const start = async () => {
    const body = mode === "both" ? { reader: "both", suites: ["given"] } : { reader: "rules" };
    try {
      const res = await fetch("/api/run", {
        method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) toast(data.error || "Could not start the run");
    } catch {
      toast("Could not start the run");
    }
  };

  const stop = async () => {
    try {
      const res = await fetch("/api/run/stop", { method: "POST" });
      if (!res.ok) toast("Could not stop the run");
    } catch {
      toast("Could not stop the run");
    }
  };

  const running = !!job?.running;
  const pct = job?.total ? Math.min(100, Math.round((100 * seen) / job.total)) : 0;
  const bar = job?.failed ? "var(--bad)" : running ? "var(--accent)" : "var(--good)";
  const rows = [];
  for (const suite of job?.suites || []) {
    suite.cases.forEach((c, i) => rows.push({ ...c, suite, key: `${suite.id}-${c.reader}-${c.id}-${i}` }));
  }
  const last = rows.length - 1;

  return (
    <div className="card run-card">
      <CardHead title="Run tests" sub={blurb(job, mode)}>
        <div className="controls">
          <div className="toggle" role="group" aria-label="What to run">
            <button type="button" className={mode === "rules" ? "on" : ""} disabled={running} onClick={() => setMode("rules")}>Rules</button>
            <button type="button" className={mode === "both" ? "on" : ""} disabled={running || !job?.ollama}
              title={job && !job.ollama ? job.why : "Grade the 15 given events with the model and the rule check"}
              onClick={() => setMode("both")}>Model + rules</button>
          </div>
          <button type="button" className="btn primary" disabled={running} onClick={start}>
            <Icon name="play" />{running ? "Running" : "Run tests"}
          </button>
          {running && <button type="button" className="btn" onClick={stop}><Icon name="x" />Stop</button>}
        </div>
      </CardHead>

      {!!job?.suites?.length && (
        <>
          <div className="run-top">
            <div className="run-count"><b>{seen}</b><span> / {job.total}</span></div>
            <div className="run-meter" aria-hidden="true"><i style={{ width: `${pct}%`, background: bar }} /></div>
            <div className={`run-flag ${job.failed ? "bad" : running ? "go" : "ok"}`}>
              {running ? "Live" : job.failed ? `${job.failed} failed` : "Passed"}
            </div>
          </div>
          <div className="run-suites">
            {job.suites.map((s) => (
              <div key={s.id} className={`run-suite ${s.status}`}>
                {s.status === "running" && <span className="pulse" />}
                <b>{s.title}</b>
                <span>{s.passed + s.failed}/{s.total}</span>
              </div>
            ))}
          </div>
          <div className="run-feed" ref={feed} onScroll={(e) => {
            const el = e.currentTarget;
            stick.current = el.scrollHeight - el.scrollTop - el.clientHeight < 48;
          }}>
            {rows.map((c, i) => {
              const open = c.suite.status === "done" || c.suite.status === "failed";
              const href = `#/tests/${c.suite.id}/${folderFor(c.reader)}/${c.id}`;
              return (
                <div key={c.key} className={`run-case ${c.verdict === "PASS" ? "pass" : "fail"}${i === last ? " latest" : ""}`}>
                  <span className="mark">{c.verdict === "PASS" ? "PASS" : "FAIL"}</span>
                  {open ? <a href={href}>{c.id}</a> : <b>{c.id}</b>}
                  <span className="who">{c.reader}</span>
                  <span className="cat">{c.category}</span>
                  <span className="set">{c.suite.title}</span>
                </div>
              );
            })}
            {!rows.length && <div className="run-wait">Starting the grader…</div>}
          </div>
          {running && !!job.tail?.length && <pre className="run-tail">{job.tail[job.tail.length - 1]}</pre>}
        </>
      )}
    </div>
  );
}
