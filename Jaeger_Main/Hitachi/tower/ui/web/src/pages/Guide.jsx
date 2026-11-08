// The platform guide: what the tower does, what each page is for, the words it uses, and how to run it.
import { useState } from "react";
import { Icon } from "../lib/icons.jsx";
import { useData } from "../lib/data.jsx";
import { useUi } from "../lib/ui.jsx";
import { CardHead, KindTag, Mono, Toggle } from "../components/common.jsx";
import { Page } from "./Page.jsx";

const FLOW = [
  { icon: "mail", t: "Message arrives", p: "A supplier email, plant alert, dealer note or rumor lands in the event feed." },
  { icon: "cpu", t: "Read", p: "The LLM reads it and explains its reasoning; the rule reader checks the reading against the company tables." },
  { icon: "graph", t: "Trace", p: "Agents follow the knowledge graph from the part, plant or lot to every order, dealer and vehicle affected." },
  { icon: "wrench", t: "Act", p: "Specialist agents plan tool calls; the coordinator checks each one against the handbook, then runs it." },
  { icon: "alert", t: "Escalate", p: "Rumors and anything that can't be confirmed go to a human. Nothing is changed for them." },
];

const TOUR = [
  { id: "overview", icon: "home", t: "Overview", p: "The state of the run at a glance.",
    points: ["Headline counts: events, tool calls, escalations, test pass rate", "Agent team and what each agent may do", "Tool calls per event; click a bar to open that event"] },
  { id: "events", icon: "feed", t: "Event feed", p: "Every message and exactly what the tower did about it.",
    points: ["How it was read, with the model's reasoning", "Agent handoffs and graph paths", "Every tool call with its reason and result"] },
  { id: "tests", icon: "check", t: "Tests", p: "How well the tower predicts, scored against answer keys.",
    points: ["Pass rate by test set and by kind of message", "Drill in: all sets → one set → one case", "Each case: input, expected output, actual output"] },
  { id: "ontology", icon: "graph", t: "Knowledge graph", p: "The company's records and how they connect.",
    points: ["Network, schema, or one event's traced records", "Drag, click to focus, scroll to zoom", "Edge types and the traversals agents use"] },
  { id: "logs", icon: "doc", t: "Logs", p: "The raw record behind every page.",
    points: ["Console output of each start.py run", "Every tool call, filterable by event or failure", "History of every test run"] },
];

const TERMS = [
  { term: <KindTag kind="supplier_delay" />, d: "A part or shipment will arrive late. Production orders that need it are moved." },
  { term: <KindTag kind="plant_outage" />, d: "A plant can't build for some days. Its orders move to the earliest feasible slot." },
  { term: <KindTag kind="quality_hold" />, d: "A lot is defective. The lot is held, unsold vehicles stop sale, owners are told." },
  { term: <KindTag kind="unconfirmed" />, d: "Hearsay or a report that can't be checked. Escalated to a human; nothing changes." },
  { term: <KindTag kind="noise" />, d: "Not operational (a brochure question, a thank-you). No action." },
  { term: <b>Reader</b>, d: "What turned the message into incidents: the model (checked by rules) or the rules alone." },
  { term: <b>Expected output</b>, d: "A test case's answer key traced through the company tables: what a correct tower would change." },
  { term: <b>Held-out sets</b>, d: "Test cases never used to tune the reader, so their score shows how well it generalizes." },
];

const RUN = {
  quick: [
    { c: "python start.py", d: "Run the tower, every test set and the ontology export, then open the dashboard." },
    { c: "python start.py --rules", d: "The same, with the rule reader only (no Ollama needed)." },
    { c: "python start.py --serve-only", d: "Just open the dashboard on the results already on disk." },
  ],
  steps: [
    { c: "ollama pull qwen2.5:0.5b && ollama serve", d: "Optional: the local LLM reader, the smallest that passes the 15 events. Pick another with TOWER_LLM_MODEL." },
    { c: "python -m tower.run --notify dry-run", d: "Run the tower on the 15 events (writes runs/run1/)." },
    { c: "python tests/run_given.py", d: "Grade the 15 given events." },
    { c: "python tests/run_cases.py", d: "Run the 100 generated cases (--reader rules | llm | both)." },
    { c: "python tests/run_model.py", d: "Score the model on its own against the held-out sets." },
    { c: "python -m tower.ontology", d: "Export the ontology for the Knowledge graph page." },
    { c: "python -m tower.ui.server", d: "Serve this dashboard at http://127.0.0.1:8080." },
  ],
  dev: [
    { c: "cd tower/ui/web && npm install && npm run build", d: "Rebuild the dashboard after changing its React source." },
    { c: "cd tower/ui/web && npm run dev", d: "Hot reload on :5173 (keep the Python server running for the data)." },
  ],
};

const SOURCES = [
  ["Overview, Event feed", "runs/run1/"],
  ["Tests", "runs/given, tests, holdout, holdout2"],
  ["Answer keys", "tests/*.json"],
  ["Knowledge graph", "Data/…/data/*.csv, runs/ontology/"],
  ["Logs", "runs/logs/, runs/test_log.jsonl"],
  ["Notifications", "runs/run1/outbox.jsonl"],
];

function Command({ c, d }) {
  const { toast } = useUi();
  const copy = async () => {
    try { await navigator.clipboard.writeText(c); toast("Copied"); } catch { toast("Copy failed; select the text instead"); }
  };
  return (
    <div className="gcmd">
      <div className="gcmd-line">
        <code>{c}</code>
        <button className="btn copy" onClick={copy} title="Copy command"><Icon name="copy" />Copy</button>
      </div>
      <p>{d}</p>
    </div>
  );
}

export default function Guide() {
  const d = useData();
  const [runTab, setRunTab] = useState("quick");
  return (
    <Page title="Guide" subtitle={<><span>What the control tower does and how to use each page</span><span>Start with <b>python start.py</b></span></>}>
      <div className="card">
        <CardHead title="What the control tower does"
          sub="Wacky Wheels builds just in time, so one late part or idle plant ripples into orders, dealers and customers. The tower reads every incoming message, works out what it affects, and fixes it with the enterprise tools, following the policy handbook." />
        <ol className="flow">
          {FLOW.map((f, i) => (
            <li key={f.t} className="panel">
              <div className="flow-head"><span className="badge-ico"><Icon name={f.icon} /></span><span className="note">Step {i + 1}</span></div>
              <b>{f.t}</b>
              <p>{f.p}</p>
            </li>
          ))}
        </ol>
      </div>

      <div className="card" style={{ marginTop: 20 }}>
        <CardHead title="The pages" sub="Click a card to open the page." />
        <div className="tour">
          {TOUR.map((p) => (
            <a key={p.id} href={`#/${p.id}`} className="panel tour-card">
              <div className="flow-head"><span className="badge-ico"><Icon name={p.icon} /></span><b>{p.t}</b></div>
              <p>{p.p}</p>
              <ul>{p.points.map((x) => <li key={x}>{x}</li>)}</ul>
              <span className="go-link">Open {p.t} →</span>
            </a>
          ))}
          <div className="panel tour-card tips">
            <div className="flow-head"><span className="badge-ico"><Icon name="bolt" /></span><b>Tips</b></div>
            <ul>
              <li>Press <kbd>/</kbd> to search events or test cases; <kbd>Esc</kbd> clears it.</li>
              <li>The live chip shows the reader and when this page last loaded. It reloads on its own when the run or the test results change.</li>
              <li>On a test set, <b>Delete run</b> removes that result for good (it asks first).</li>
              {d.model && <li>This run was read by <b>{d.model}</b> with the rule check.</li>}
            </ul>
          </div>
        </div>
      </div>

      <div className="grid g-guide" style={{ marginTop: 20 }}>
        <div className="card">
          <CardHead title="Run it" sub="From the Jaeger_Main/Hitachi folder. Python 3.10+ and the standard library are all the tower needs.">
            <Toggle value={runTab} options={[["quick", "Quick start"], ["steps", "Step by step"], ["dev", "Dashboard dev"]]} onChange={setRunTab} />
          </CardHead>
          <div className="gcmds">{RUN[runTab].map((x) => <Command key={x.c} {...x} />)}</div>
        </div>
        <div className="card">
          <CardHead title="Key terms" sub="The words the dashboard uses" />
          <dl className="gloss">
            {TERMS.map((x, i) => <div key={i}><dt>{x.term}</dt><dd>{x.d}</dd></div>)}
          </dl>
          <div className="section-title">Where each page's data lives</div>
          <dl className="gloss compact">
            {SOURCES.map(([p, s]) => <div key={p}><dt><b>{p}</b></dt><dd><Mono>{s}</Mono></dd></div>)}
          </dl>
        </div>
      </div>
    </Page>
  );
}
