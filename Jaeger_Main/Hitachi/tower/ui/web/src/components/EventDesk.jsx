// Event run walks the feed. Event add is a chat: each message becomes an event the tower reads.
import { useEffect, useRef, useState } from "react";
import { Icon } from "../lib/icons.jsx";
import { useData } from "../lib/data.jsx";
import { useUi } from "../lib/ui.jsx";
import { CardHead } from "./common.jsx";

const EMPTY = { seq: 0, running: false, current: null, done: 0, total: 0, error: null, events: [] };

export function EventDesk() {
  const { reload } = useData();
  const { toast, set } = useUi();
  const [job, setJob] = useState(null);
  const [open, setOpen] = useState(false);
  const [chat, setChat] = useState([]);
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const [waited, setWaited] = useState(0);
  const seq = useRef(-1);
  const log = useRef(null);

  const accept = (data) => {
    if (!data || typeof data.seq !== "number" || data.seq <= seq.current) return;
    seq.current = data.seq;
    setJob(data);
  };

  useEffect(() => {
    let stop = false;
    const pull = async () => {
      try {
        const res = await fetch("/api/events/run", { cache: "no-store" });
        if (!stop && res.ok) accept(await res.json());
      } catch { /* the next poll retries */ }
    };
    pull();
    const timer = setInterval(pull, 400);
    return () => { stop = true; clearInterval(timer); };
  }, []);

  const loadChat = async () => {
    try {
      const res = await fetch("/api/events/chat", { cache: "no-store" });
      if (res.ok) setChat((await res.json()).messages || []);
    } catch { /* the transcript stays as it was */ }
  };

  useEffect(() => { loadChat(); }, []);
  // Event run writes each finished event into the feed: refresh the page data as it lands, and
  // once when a run starts (the feed is cleared) and ends.
  const progress = job ? `${job.running}:${job.done}` : "";
  useEffect(() => { if (progress) reload(); }, [progress]); // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => {
    const box = log.current;
    if (box) box.scrollTop = box.scrollHeight;
  }, [chat, open, busy]);
  // Seconds since the message was sent, for the thinking bubble.
  useEffect(() => {
    if (!busy) { setWaited(0); return undefined; }
    const t0 = Date.now();
    const timer = setInterval(() => setWaited(Math.floor((Date.now() - t0) / 1000)), 1000);
    return () => clearInterval(timer);
  }, [busy]);

  const run = async () => {
    try {
      const res = await fetch("/api/events/run", { method: "POST", headers: { "Content-Type": "application/json" }, body: "{}" });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) toast(data.error || "Could not start the event run");
    } catch {
      toast("Could not start the event run");
    }
  };

  const halt = async () => {
    try { await fetch("/api/events/run/stop", { method: "POST", headers: { "Content-Type": "application/json" }, body: "{}" }); }
    catch { /* the run notices the next check */ }
  };

  const send = async () => {
    const message = text.trim();
    if (!message || busy) return;
    setBusy(true);
    setText("");
    setChat((rows) => [...rows, { role: "user", text: message }]);
    try {
      const res = await fetch("/api/events/chat", {
        method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ text: message }),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        toast(data.error || "Could not add that event");
        setText(message);
        setChat((rows) => rows.slice(0, -1));
        return;
      }
      setChat((rows) => [...rows, { role: "tower", text: data.reply, event_id: data.event.event_id }]);
      await reload();
      set({ sel: data.event.event_id });
    } catch {
      toast("Could not add that event");
      setText(message);
    } finally {
      setBusy(false);
    }
  };

  const shown = job || EMPTY;
  const width = shown.total ? Math.round((shown.done / shown.total) * 100) : 0;
  const blurb = shown.running
    ? `Reading ${shown.current || "the feed"}. ${shown.done} of ${shown.total} finished.`
    : shown.events.length
      ? (shown.error ? `Stopped. ${shown.error}.` : `Finished. ${shown.done} events.`)
      : "Walks the 15 given events, then any event from this chat, and shows each one as it finishes. The saved run of the 15 stays as it is.";

  return (
    <div className="card desk-card">
      <CardHead title="Events" sub={blurb}>
        <div className="desk-actions">
          {shown.running
            ? <button type="button" className="btn danger" onClick={halt}>Stop</button>
            : <button type="button" className="btn primary" onClick={run}><Icon name="play" />Event run</button>}
          <button type="button" className="btn" onClick={() => setOpen((v) => !v)}>{open ? "Close chat" : "Event add"}</button>
        </div>
      </CardHead>
      {!!shown.events.length && (
        <div className="desk-run">
          <div className="desk-meter" aria-hidden="true"><span style={{ width: `${width}%` }} /></div>
          <div className="desk-feed">
            {shown.events.map((ev) => (
              <div className="desk-ev" key={ev.id}>
                <b>{ev.id}</b>
                <span className="out">{ev.outcome}</span>
                <span className="sum">{ev.classification} · {ev.summary}</span>
              </div>
            ))}
          </div>
        </div>
      )}
      {open && (
        <div className="desk-chat">
          <div className="desk-log" ref={log}>
            {!chat.length && <div className="desk-bubble tower">Send a supplier email, a plant alert, or an ops note. I will read it and add it to the feed.</div>}
            {chat.map((m, i) => (
              <div className={`desk-bubble ${m.role === "user" ? "user" : "tower"}`} key={i}>
                {m.text}
                {m.event_id && <button type="button" onClick={() => set({ sel: m.event_id })}>Open {m.event_id}</button>}
              </div>
            ))}
            {busy && (
              <div className="desk-bubble tower thinking" role="status" aria-live="polite">
                <span className="dots" aria-hidden="true"><i /><i /><i /></span>
                <span>Thinking{waited ? ` · ${waited}s` : ""}</span>
                <small>Reading the message, checking it against the company records, then acting. This usually takes 10–20 seconds.</small>
              </div>
            )}
          </div>
          <form className="desk-compose" onSubmit={(e) => { e.preventDefault(); send(); }}>
            <textarea rows={2} value={text} maxLength={4000} placeholder="Type a message to add as an event"
              onChange={(e) => setText(e.target.value)}
              onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); send(); } }} />
            <button type="submit" className="btn primary" disabled={busy || !text.trim()}>{busy ? <><span className="spin"><Icon name="refresh" /></span>Thinking</> : "Send"}</button>
          </form>
        </div>
      )}
    </div>
  );
}
