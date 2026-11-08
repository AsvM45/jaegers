import { useLayoutEffect } from "react";
import { PAGES } from "./lib/constants.js";
import { useUi } from "./lib/ui.jsx";
import { Sidebar } from "./components/Layout.jsx";
import Overview from "./pages/Overview.jsx";
import Events from "./pages/Events.jsx";
import Tests from "./pages/Tests.jsx";
import KnowledgeGraph from "./pages/KnowledgeGraph.jsx";
import Logs from "./pages/Logs.jsx";
import Guide from "./pages/Guide.jsx";

const VIEWS = { overview: Overview, events: Events, tests: Tests, ontology: KnowledgeGraph, logs: Logs, guide: Guide };

export default function App() {
  const { segs } = useUi();
  const page = PAGES[segs[0]] ? segs[0] : "overview";
  const View = VIEWS[page];
  const key = segs.join("/");
  useLayoutEffect(() => { window.scrollTo(0, 0); }, [key]);
  return (
    <div className="app">
      <Sidebar page={page} />
      {/* key: a new page (or test set / case) mounts fresh, so count-up and draw-in play on arrival only */}
      <main className="main" key={key}><View /></main>
    </div>
  );
}
