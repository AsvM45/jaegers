import { useLayoutEffect } from "react";
import { PAGES } from "./lib/constants.js";
import { useUi } from "./lib/ui.jsx";
import { Sidebar } from "./components/Layout.jsx";
import { PageSkeleton } from "./components/Loading.jsx";
import { useData } from "./lib/data.jsx";
import Overview from "./pages/Overview.jsx";
import Events from "./pages/Events.jsx";
import AddEvents from "./pages/AddEvents.jsx";
import Tests from "./pages/Tests.jsx";
import KnowledgeGraph from "./pages/KnowledgeGraph.jsx";
import Logs from "./pages/Logs.jsx";
import Records from "./pages/Records.jsx";
import Guide from "./pages/Guide.jsx";
import Settings from "./pages/Settings.jsx";

const VIEWS = { overview: Overview, events: Events, add: AddEvents, tests: Tests, ontology: KnowledgeGraph, records: Records, logs: Logs, guide: Guide, settings: Settings };

// The page the window last showed, kept outside React so a redraw does not reset it.
const shown = { key: null };

export default function App() {
  const { segs } = useUi();
  const page = PAGES[segs[0]] ? segs[0] : "overview";
  const View = VIEWS[page];
  const key = segs.join("/");
  const { visit } = useUi();
  const { loadedAt, failed } = useData();
  const loaded = !!loadedAt || failed || ["settings", "guide", "add"].includes(page); // these pages do not need the data
  // Top of the page on a move to another page only. A redraw (language change) keeps your place.
  useLayoutEffect(() => {
    if (shown.key !== key) window.scrollTo(0, 0);
    shown.key = key;
  }, [key, visit]);
  return (
    <div className="app">
      <Sidebar page={page} />
      {/* key: a new page (or test set / case) mounts fresh, so count-up and draw-in play on arrival only */}
      <main className="main" key={key}>{loaded ? <View /> : <PageSkeleton />}</main>
    </div>
  );
}
