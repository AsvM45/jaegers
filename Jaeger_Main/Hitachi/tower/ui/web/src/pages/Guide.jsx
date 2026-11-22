// The platform guide: what the tower does, what each page is for, how to use it, and the words it uses.
import { Icon } from "../lib/icons.jsx";
import { useData } from "../lib/data.jsx";
import { CardHead, KindTag } from "../components/common.jsx";
import { Page } from "./Page.jsx";
import { titleCase, tr, trx } from "../lib/i18n.js";

// Built when the page renders, so it is in the language chosen in Settings.
const FLOW = () => [
  { icon: "mail", t: tr("Message arrives"), p: tr("A supplier email, plant alert, dealer note or rumor lands in the event feed.") },
  { icon: "cpu", t: tr("Read"), p: tr("The LLM reads it and explains its reasoning; the rule reader checks the reading against the company tables.") },
  { icon: "graph", t: tr("Trace"), p: tr("Agents follow the knowledge graph from the part, plant or lot to every order, dealer and vehicle affected.") },
  { icon: "wrench", t: tr("Act"), p: tr("Specialist agents plan tool calls; the coordinator checks each one against the handbook, then runs it.") },
  { icon: "alert", t: tr("Escalate"), p: tr("Rumors and anything that can't be confirmed go to a human. Nothing is changed for them.") },
];

// Built when the page renders, so it is in the language chosen in Settings. demo: online, the number of
// demo events (the short set the online version uses); 0 on a laptop.
const TOUR = (demo) => [
  { id: "overview", icon: "home", t: tr("Overview"), p: tr("The state of the run at a glance."),
    points: [tr("Headline counts: events, tool calls, escalations, test pass rate"), tr("Agent team and what each agent may do"), tr("Tool calls per event; click a bar to open that event")] },
  { id: "events", icon: "feed", t: tr("Event center"), p: tr("Every message and exactly what the tower did about it."),
    points: [tr("Every event, filterable by outcome and incident type"), tr("How it was read and the graph path it traced"), tr("Every tool call and the audit trail")] },
  { id: "add", icon: "plus", t: tr("Add events"), p: tr("Give the tower a new message, or run the whole feed."),
    points: [tr("Type, paste, attach a file, or dictate by voice (Safari or Chrome)"), tr("The tower reads it, acts or escalates, and adds it to the feed"), demo ? tr("Run events walks the {n} demo events", { n: demo }) : tr("Run events walks the 15 given events and the chat's events")] },
  { id: "tests", icon: "check", t: tr("Tests"), p: tr("How well the tower predicts, scored against answer keys."),
    points: [demo ? tr("Run tests and watch each of the {n} demo events pass or fail as it finishes", { n: demo }) : tr("Run tests and watch each of the 15 given events pass or fail as it finishes"), tr("Pass rate by kind of message"), tr("Open one event: input, expected output, actual output")] },
  { id: "ontology", icon: "graph", t: tr("Knowledge graph"), p: tr("The company's records and how they connect."),
    points: [tr("Network, schema, or one event's traced records"), tr("Drag, click to focus, scroll to zoom"), tr("Edge types and the traversals agents use")] },
  { id: "logs", icon: "doc", t: tr("Logs"), p: tr("The raw record behind every page."),
    points: [tr("Every tool call, filterable by event or failure"), tr("Every notification and agent handoff, across all events"), tr("History of every test run")] },
];

// Built when the page renders, so it is in the language chosen in Settings.
const TERMS = () => [
  { term: <KindTag kind="supplier_delay" />, d: tr("A part or shipment will arrive late. Production orders that need it are moved.") },
  { term: <KindTag kind="plant_outage" />, d: tr("A plant can't build for some days. Its orders move to the earliest feasible slot.") },
  { term: <KindTag kind="quality_hold" />, d: tr("A lot is defective. The lot is held, unsold vehicles stop sale, owners are told.") },
  { term: <KindTag kind="unconfirmed" />, d: tr("Hearsay or a report that can't be checked. Escalated to a human; nothing changes.") },
  { term: <KindTag kind="noise" />, d: tr("Not operational (a brochure question, a thank-you). No action.") },
  { term: <b>{titleCase(tr("Reader"))}</b>, d: tr("What turned the message into incidents: the model (checked by rules) or the rules alone.") },
  { term: <b>{titleCase(tr("Expected output"))}</b>, d: tr("A test case's answer key traced through the company tables: what a correct tower would change.") },
];

// Built when the page renders, so it is in the language chosen in Settings.
const USE = (demo) => [
  { icon: "plus", t: tr("Give it events"), p: demo ? tr("On Add Events, type or paste a message, attach a file, or dictate it. Run Events plays the {n} demo events in as if they were arriving live.", { n: demo })
    : tr("On Add Events, type or paste a message, attach a file, or dictate it. Run Events plays the 15 given events in as if they were arriving live.") },
  { icon: "feed", t: tr("See what it did"), p: tr("The Event Center opens on Results: what the tower did with each event. Switch to Feed for how each message was read and every action taken.") },
  { icon: "doc", t: tr("Export the history"), p: tr("From the Event Center, download the events shown as a readable log, a spreadsheet, or a full data file.") },
  { icon: "check", t: tr("Check the scores"), p: demo ? tr("Tests compares the tower's actions with answer keys, case by case, for the demo events.")
    : tr("Tests compares the tower's actions with answer keys, case by case, for the given events and the blind set.") },
  { icon: "graph", t: tr("Explore the records"), p: tr("The Knowledge Graph shows the company's records and the paths the agents follow from a problem to the people it affects.") },
  { icon: "wrench", t: tr("Make it yours"), p: tr("Settings sets the theme, language, number format, time zone and voice input.") },
];

// Built when the page renders, so it is in the language chosen in Settings.
const SOURCES = (demo) => [
  [tr("Overview, Event center"), tr("The events in the feed and every action the tower took")],
  [tr("Tests"), tr("Saved test runs, scored against answer keys")],
  [tr("Answer keys"), demo ? tr("Written by hand for each demo event") : tr("Written by hand for the 15 given events; built from the company records for the blind set")],
  [tr("Knowledge graph"), tr("The company records: plants, parts, suppliers, orders, dealers, vehicles and owners")],
  [tr("Logs"), tr("Every tool call, notification and agent handoff, and the test history")],
  [tr("Notifications"), tr("The messages sent to dealers and owners for each event")],
];

export default function Guide() {
  const d = useData();
  return (
    <Page title={titleCase(tr("Guide"))} subtitle={<><span>{tr("What the control tower does and how to use each page")}</span><span>{trx("Start on {page}", { page: <a className="link" href="#/add">{titleCase(tr("Add events"))}</a> })}</span></>}>
      <div className="card">
        <CardHead title={titleCase(tr("What the control tower does"))}
          sub={tr("Wacky Wheels builds just in time, so one late part or idle plant ripples into orders, dealers and customers. The tower reads every incoming message, works out what it affects, and fixes it with the enterprise tools, following the policy handbook.")} />
        <ol className="flow">
          {FLOW().map((f, i) => (
            <li key={f.t} className="panel">
              <div className="flow-head"><span className="badge-ico"><Icon name={f.icon} /></span><span className="note">{tr("Step {n}", { n: i + 1 })}</span></div>
              <b>{titleCase(f.t)}</b>
              <p>{f.p}</p>
            </li>
          ))}
        </ol>
      </div>

      <div className="card" style={{ marginTop: 20 }}>
        <CardHead title={titleCase(tr("The pages"))} sub={tr("Click a card to open the page.")} />
        <div className="tour">
          {TOUR(d.demoSize).map((p) => (
            <a key={p.id} href={`#/${p.id}`} className="panel tour-card">
              <div className="flow-head"><span className="badge-ico"><Icon name={p.icon} /></span><b>{titleCase(p.t)}</b></div>
              <p>{p.p}</p>
              <ul>{p.points.map((x) => <li key={x}>{x}</li>)}</ul>
              <span className="go-link">{tr("Open {page} →", { page: titleCase(p.t) })}</span>
            </a>
          ))}
          <div className="panel tour-card tips">
            <div className="flow-head"><span className="badge-ico"><Icon name="bolt" /></span><b>{titleCase(tr("Tips"))}</b></div>
            <ul>
              <li>{trx("Press {slash} to search events or test cases; {esc} clears it.", { slash: <kbd>/</kbd>, esc: <kbd>Esc</kbd> })}</li>
              <li>{tr("The live chip shows the reader and when this page last loaded. It reloads on its own when the run or the test results change.")}</li>
              <li>{trx("On a test set, {delete} removes that result for good (it asks first).", { delete: <b>{tr("Delete run")}</b> })}</li>
              {d.model && <li>{tr("This run was read by the AI model, checked by the rule reader.")}</li>}
            </ul>
          </div>
        </div>
      </div>

      <div className="grid g-guide" style={{ marginTop: 20 }}>
        <div className="card">
          <CardHead title={titleCase(tr("Using the dashboard"))} sub={tr("Everything happens in the app; there is nothing to install or type.")} />
          <ol className="guse">
            {USE(d.demoSize).map((x) => (
              <li key={x.t}><span className="badge-ico"><Icon name={x.icon} /></span><div><b>{titleCase(x.t)}</b><p>{x.p}</p></div></li>
            ))}
          </ol>
        </div>
        <div className="card">
          <CardHead title={titleCase(tr("Key terms"))} sub={tr("The words the dashboard uses")} />
          <dl className="gloss">
            {TERMS().map((x, i) => <div key={i}><dt>{x.term}</dt><dd>{x.d}</dd></div>)}
          </dl>
          <div className="section-title">{tr("Where each page's data lives")}</div>
          <dl className="gloss compact">
            {SOURCES(d.demoSize).map(([p, s]) => <div key={p}><dt><b>{titleCase(p)}</b></dt><dd>{s}</dd></div>)}
          </dl>
        </div>
      </div>
    </Page>
  );
}
