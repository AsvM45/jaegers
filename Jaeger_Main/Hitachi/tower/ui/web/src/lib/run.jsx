// The live event run, shared by the Overview hero, the live activity ticker and the Event Center timeline.
// Polls the run every half second while it is going (every 3 s otherwise) and reloads the page data as
// each event lands, so the map, charts and feed fill in live.
import { useEffect, useRef, useState } from "react";
import { getJSON, useData } from "./data.jsx";

export function useEventRun() {
  const { reload } = useData();
  const [job, setJob] = useState(null);
  const started = useRef(null);
  const timer = useRef(null);

  const pull = async () => {
    clearTimeout(timer.current);
    const next = await getJSON("/api/events/run", null);
    if (next) setJob(next);
    timer.current = setTimeout(pull, next?.running ? 500 : 3000);
  };
  useEffect(() => { pull(); return () => clearTimeout(timer.current); }, []); // eslint-disable-line react-hooks/exhaustive-deps

  // Each finished event changes the data on every page: reload it.
  const progress = job ? `${job.running}:${job.done}` : "";
  useEffect(() => { if (progress) reload(); }, [progress]); // eslint-disable-line react-hooks/exhaustive-deps

  // How long the run has taken, for "15 events in 24 s".
  if (job?.running && !started.current) started.current = Date.now();
  if (job && !job.running && started.current && !job.elapsed) job.elapsed = Math.round((Date.now() - started.current) / 1000);

  const start = async () => {
    started.current = Date.now();
    try {
      const res = await fetch("/api/events/run", { method: "POST", headers: { "Content-Type": "application/json" }, body: "{}" });
      if (!res.ok) return (await res.json().catch(() => ({}))).error || "Could not start the run";
    } catch {
      return "Could not start the run";
    }
    pull();
    return null;
  };
  return { job, start };
}
