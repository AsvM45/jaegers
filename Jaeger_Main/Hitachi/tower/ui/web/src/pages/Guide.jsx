import { Icon } from "../lib/icons.jsx";
import { useUi } from "../lib/ui.jsx";
import { CardHead, Mono } from "../components/common.jsx";
import { Page } from "./Page.jsx";

const GUIDE = [
  { t: "The one command", p: "Runs the tower, the test suites and the ontology export, then opens this dashboard. It uses the LLM reader when Ollama is running with the model pulled, and the rule reader otherwise. --rules skips the LLM reader; --serve-only just opens the dashboard on the results already on disk.",
    c: ["python start.py", "python start.py --rules", "python start.py --serve-only"] },
  { t: "Or step by step: open a terminal in the Hitachi folder", p: "Every command below runs from here. Python 3.10+ and the standard library are all the tower needs.",
    c: ["cd Jaeger_Main/Hitachi"] },
  { t: "Optional: start the local LLM reader", p: "The tower reads messages with Qwen3 through Ollama and checks every reading with the rule reader. Skip this step to use the rule reader alone (--reader rules). Pick another model with TOWER_LLM_MODEL.",
    c: ["ollama pull qwen3:0.6b", "ollama serve"] },
  { t: "Run the control tower on the 15 events", p: "Writes runs/run1/traces.json and action_log.jsonl, which feed the Overview and Event feed pages. Add --notify dry-run to fill the Notifications section.",
    c: ["python -m tower.run", "python -m tower.run --reader rules --notify dry-run"] },
  { t: "Run the tests", p: "Each run writes one report per reader under runs/given/ or runs/tests/, which shows on the Tests page. --reader takes rules, llm or both (the default).",
    c: ["python tests/run_given.py", "python tests/run_cases.py", "TOWER_LLM_MODEL=qwen3:1.7b python tests/run_cases.py --reader llm"] },
  { t: "How good is the model itself", p: "Scores the LLM reader on its own (no rule check) on the 100 held-out cases and the 15 given events, against the expected graphs in tests/expected_graphs.json. About 3 seconds per message with qwen3:0.6b. Set TOWER_LLM_MODEL to test another model.",
    c: ["python tests/run_model.py", "TOWER_LLM_MODEL=qwen3:1.7b python tests/run_model.py", "python tests/run_cases.py --cases tests/holdout_cases.json --out runs/holdout"] },
  { t: "Test cases", p: "100 generated cases: 25 hand-made edge cases and 75 written once from real records by tests/make_cases.py, each with its answer key. Each answer key is traced through the company graph to the expected output, and every run compares the reader's predictions with it: incident type, records and dates, full output.",
    c: ["python tests/make_cases.py"] },
  { t: "Export the ontology", p: "Writes runs/ontology/ontology.json for the edge tables on the Knowledge graph page. The orb graph itself reads the CSVs directly.",
    c: ["python -m tower.ontology"] },
  { t: "Start this dashboard", p: "Then open http://127.0.0.1:8080 and press Refresh after any run. The page is a React app in tower/ui/web; after changing it, rebuild with npm run build (or use npm run dev for hot reload on :5173).",
    c: ["python -m tower.ui.server", "cd tower/ui/web && npm install && npm run build", "cd tower/ui/web && npm run dev"] },
];

const SOURCES = [
  ["Overview, Event feed", "runs/run1/"],
  ["Tests", "runs/given, tests, holdout, holdout2 (+ tests/*.json)"],
  ["Logs", "runs/logs/*.log, runs/run1/action_log.jsonl, runs/test_log.jsonl"],
  ["Prediction scores", "tests/*.json (answer keys) + the graph"],
  ["Knowledge graph", "Data/…/data/*.csv runs/ontology/"],
  ["Notifications", "runs/run1/outbox.jsonl"],
];

export default function Guide() {
  const { toast } = useUi();
  const copy = async (c) => {
    try { await navigator.clipboard.writeText(c); toast("Copied"); } catch { toast("Copy failed; select the text instead"); }
  };
  return (
    <Page title="How to run" subtitle={<span>From the Jaeger_Main/Hitachi folder: <b>python start.py</b></span>}>
      <div className="grid g-chart">
        <div className="card">
          <CardHead title="How to run" sub="From the Jaeger_Main/Hitachi folder. Step 1 does everything; the rest are the same work one piece at a time." />
          <div className="steps">
            {GUIDE.map((g, i) => (
              <div className="step" key={g.t}>
                <div className="n">{i + 1}</div>
                <div>
                  <h4>{g.t}</h4><p>{g.p}</p>
                  {g.c.map((c) => <div className="cmd" key={c}><code>{c}</code><button className="btn copy" onClick={() => copy(c)}><Icon name="copy" />Copy</button></div>)}
                </div>
              </div>
            ))}
          </div>
        </div>
        <div className="card">
          <CardHead title="What each page reads" sub="Files on disk, so a re-run shows after Refresh" />
          <div className="scroll-x"><table>
            <thead><tr><th>Page</th><th>Source</th></tr></thead>
            <tbody>{SOURCES.map(([p, s]) => <tr key={p}><td><b>{p}</b></td><td className="mono">{s}</td></tr>)}</tbody>
          </table></div>
          <div className="section-title">Deleting a report</div>
          <p className="note" style={{ lineHeight: 1.6 }}>On a test set's page, Delete run removes that reader's folder, for example <Mono>runs/tests/llm_qwen3_1.7b/</Mono>. It asks once to confirm and cannot be undone. Re-run the suite to get it back.</p>
        </div>
      </div>
    </Page>
  );
}
