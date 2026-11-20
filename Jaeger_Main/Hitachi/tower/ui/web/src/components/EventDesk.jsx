// The Add events page: a chat where each message becomes an event the tower reads (EventChat),
// and the event run that walks the feed (EventRun).
import { useCallback, useEffect, useRef, useState } from "react";
import { Icon } from "../lib/icons.jsx";
import { useData } from "../lib/data.jsx";
import { go, useUi } from "../lib/ui.jsx";
import { MIC_SETTINGS, clock, useVoice } from "../lib/voice.js";
import { useSettings } from "../lib/settings.jsx";
import { ACCEPT, AttachError, readAttachment } from "../lib/attach.js";
import { CardHead } from "./common.jsx";
import { RESET_EVENT, ResetButton } from "./ResetButton.jsx";
import { msg, tr } from "../lib/i18n.js";

const EMPTY = { seq: 0, running: false, current: null, done: 0, total: 0, error: null, events: [] };
const MAX = 4000;

// Starters fill the box with a message built from real records, so each one reads as its kind.
// The labels are translated when shown; the sample messages stay English, like real ops traffic.
const STARTERS = [
  [msg("Supplier delay"), "Shipment SH-0310 of airbag modules for Greensboro was due Monday Mar 15 and will now arrive Thursday Mar 18. Reason: a customs hold."],
  [msg("Plant outage"), "Greensboro plant update: a power failure. We're dark from Tuesday Mar 23 through Wednesday Mar 24; the line restarts the following working day."],
  [msg("Quality hold"), "Quality alert: lot LOT-0247 of 60 kWh battery packs installed at Huntsville on vehicles built 2027-03-02 to 2027-03-03 failed a cell inspection. Hold the lot."],
  [msg("Rumor"), "Someone at the supplier day said a brake supplier might be running behind. Nothing confirmed, no dates."],
];

export function EventChat() {
  const { reload } = useData();
  const { toast, set } = useUi();
  const [chat, setChat] = useState([]);
  // Reset events clears the chat history on the server; clear this copy of it too.
  useEffect(() => {
    const on = (e) => { if (e.detail?.kind === "events") setChat([]); };
    window.addEventListener(RESET_EVENT, on);
    return () => window.removeEventListener(RESET_EVENT, on);
  }, []);
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const [waited, setWaited] = useState(0);
  const log = useRef(null);
  const box = useRef(null);
  const file = useRef(null);
  const { settings } = useSettings();
  const [note, setNote] = useState(null);   // a voice problem, shown under the box
  const heard = useCallback((words) => {
    setNote(null);
    setText((prev) => `${prev.trim() ? `${prev.trimEnd()} ` : ""}${words}`.slice(0, MAX));
    box.current?.focus();
  }, []);
  const problem = useCallback((message) => setNote({ text: message }), []);
  const voice = useVoice({ lang: settings.voiceLang, onText: heard, onProblem: problem });
  const recording = voice.state === "recording", transcribing = voice.state === "transcribing";
  const voiceBusy = voice.state !== "idle";

  // While recording: Esc cancels, Enter stops and transcribes.
  useEffect(() => {
    if (!recording) return undefined;
    const on = (e) => {
      if (e.key === "Escape") { e.preventDefault(); voice.cancel(); }
      if (e.key === "Enter") { e.preventDefault(); voice.stop(); }
    };
    document.addEventListener("keydown", on);
    return () => document.removeEventListener("keydown", on);
  }, [recording, voice]);

  const micSettings = () => {
    if (window.towerDesktop?.openMicSettings) window.towerDesktop.openMicSettings();
    else window.location.href = MIC_SETTINGS;
  };

  useEffect(() => {
    (async () => {
      try {
        const res = await fetch("/api/events/chat", { cache: "no-store" });
        if (res.ok) setChat((await res.json()).messages || []);
      } catch { /* the transcript stays empty */ }
    })();
  }, []);
  useEffect(() => {
    const el = log.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [chat, busy]);
  // The box grows with its text, up to the CSS max-height (Safari has no field-sizing).
  useEffect(() => {
    const el = box.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = `${el.scrollHeight}px`;
  }, [text]);
  // Seconds since the message was sent, for the thinking bubble.
  useEffect(() => {
    if (!busy) { setWaited(0); return undefined; }
    const t0 = Date.now();
    const timer = setInterval(() => setWaited(Math.floor((Date.now() - t0) / 1000)), 1000);
    return () => clearInterval(timer);
  }, [busy]);

  const open = (id) => { set({ sel: id, openEvent: id }); go("#/events"); };

  const fill = (value) => { setText(value); box.current?.focus(); };

  const attach = async (e) => {
    const f = e.target.files?.[0];
    e.target.value = "";
    if (!f) return;
    try {
      const texts = await readAttachment(f);
      if (texts.length > 1) { setNote({ text: tr("{name} has {texts} events.", { name: f.name, texts: texts.length }), batch: texts }); return; }
      if (texts[0].length > MAX) toast(tr("{name} is long; only the first {MAX} characters were added", { name: f.name, MAX: MAX.toLocaleString() }));
      setNote(null);
      fill(texts[0].slice(0, MAX));
    } catch (err) {
      setNote({ text: err instanceof AttachError ? err.message : tr("Could not read {name}.", { name: f.name }) });
    }
  };

  // One message to the tower. Returns true when it was added to the feed.
  const post = async (message) => {
    setChat((rows) => [...rows, { role: "user", text: message }]);
    try {
      const res = await fetch("/api/events/chat", {
        method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ text: message }),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        toast(data.error || "Could not add that event");
        setChat((rows) => rows.slice(0, -1));
        return false;
      }
      setChat((rows) => [...rows, { role: "tower", text: data.reply, event_id: data.event.event_id }]);
      set({ sel: data.event.event_id });
      return true;
    } catch {
      toast(tr("Could not add that event"));
      setChat((rows) => rows.slice(0, -1));
      return false;
    }
  };

  const send = async () => {
    const message = text.trim();
    if (!message || busy || voiceBusy) return;
    setBusy(true);
    setText("");
    try {
      if (!(await post(message))) setText(message);
      else await reload();
    } finally {
      setBusy(false);
    }
  };

  // A JSON file with several events: add them one after another, in order.
  const sendAll = async (texts) => {
    setNote(null);
    setBusy(true);
    let added = 0;
    try {
      for (const t of texts) {
        if (!(await post(t.slice(0, MAX)))) break;
        added += 1;
      }
      await reload();
      toast(tr("Added {added} of {texts} events", { added: added, texts: texts.length }));
    } finally {
      setBusy(false);
    }
  };

  const fresh = !chat.length && !busy;

  return (
    <section className="ask">
      {fresh ? (
        <div className="ask-hero">
          <div className="ask-orb" aria-hidden="true"><Icon name="cpu" /></div>
          <h2>{tr("What happened in operations?")}</h2>
          <p>{tr("Paste a supplier email, plant alert, quality bulletin or chat message. The tower reads it, traces the records it touches and acts, or asks a person when it isn't sure.")}</p>
        </div>
      ) : (
        <div className="ask-log" ref={log} aria-live="polite">
          {chat.map((m, i) => (
            <div className={`desk-bubble ${m.role === "user" ? "user" : "tower"}`} key={i}>
              {m.text}
              {m.event_id && <button type="button" onClick={() => open(m.event_id)}>Open {m.event_id} in the feed</button>}
            </div>
          ))}
          {busy && (
            <div className="desk-bubble tower thinking" role="status">
              <span className="dots" aria-hidden="true"><i /><i /><i /></span>
              <span>Thinking{waited ? ` · ${waited}s` : ""}</span>
              <small>{tr("Reading the message, checking it against the company records, then acting. This usually takes 10–20 seconds.")}</small>
            </div>
          )}
        </div>
      )}

      <form className={`ask-box${recording ? " recording" : ""}`} onSubmit={(e) => { e.preventDefault(); send(); }}>
        {voiceBusy && voice.state !== "asking" ? (
          <div className="ask-rec" role="status" aria-live="polite">
            <button type="button" className="ask-round" onClick={voice.cancel} disabled={transcribing} aria-label={tr("Cancel recording")}>
              <Icon name="x" />
            </button>
            <div className={`ask-wave${transcribing ? " still" : ""}`} aria-hidden="true">
              {voice.levels.map((l, i) => <i key={i} style={{ height: `${Math.max(8, Math.round(l * 100))}%` }} />)}
            </div>
            <span className="ask-clock">{transcribing ? "Transcribing…" : clock(voice.seconds)}</span>
            <button type="button" className="ask-send" onClick={voice.stop} disabled={transcribing} aria-label={tr("Stop and transcribe")}>
              {transcribing ? <span className="spin"><Icon name="refresh" /></span> : <Icon name="ok" />}
            </button>
          </div>
        ) : (
          <div className="ask-input">
            <span className="ask-spark" aria-hidden="true"><Icon name="spark" /></span>
            <textarea ref={box} rows={2} value={text} maxLength={MAX} aria-label={tr("Message to add as an event")}
              placeholder={tr("Describe the event, or paste the message")}
              onChange={(e) => setText(e.target.value)}
              onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); send(); } }} />
            <button type="submit" className="ask-send" disabled={busy || !text.trim()} aria-label={tr("Send")}>
              {busy ? <span className="spin"><Icon name="refresh" /></span> : <Icon name="up" />}
            </button>
          </div>
        )}
        <div className="ask-tools">
          <button type="button" className="ask-tool" onClick={() => file.current?.click()} disabled={busy || voiceBusy}>
            <Icon name="clip" />{tr("Attach")}</button>
          <input ref={file} type="file" hidden accept={ACCEPT} onChange={attach} />
          <span className="ask-sep" aria-hidden="true" />
          <button type="button" className={`ask-tool${voiceBusy ? " on" : ""}`} onClick={voice.start}
            disabled={busy || voiceBusy} title={voice.engine?.ready === false ? voice.engine.problem : tr("Dictate the message")}>
            <Icon name="mic" />{voice.state === "asking" ? tr("Allow the microphone…") : tr("Voice")}
          </button>
          <span className="ask-hint">
            {voiceBusy
              ? tr("Listening on this computer · Esc cancels · Enter stops")
              : text.length > MAX - 400 ? `${text.length.toLocaleString()} / ${MAX.toLocaleString()}` : tr("Enter to send · Shift+Enter for a new line")}
          </span>
        </div>
      </form>
      {note && (
        <div className="ask-note" role="alert">
          <Icon name="alert" />
          <span>{note.text}</span>
          {voice.blocked && <button type="button" className="btn" onClick={micSettings}>{tr("Open microphone settings")}</button>}
          {note.batch && <>
            <button type="button" className="btn primary" onClick={() => sendAll(note.batch)}>Add all {note.batch.length}</button>
            <button type="button" className="btn" onClick={() => { fill(note.batch[0].slice(0, MAX)); setNote(null); }}>{tr("Edit the first")}</button>
          </>}
          <button type="button" className="ask-x" onClick={() => setNote(null)} aria-label={tr("Dismiss")}><Icon name="x" /></button>
        </div>
      )}

      {fresh && (
        <div className="ask-starters">
          <div className="ask-label">{tr("SOME EXAMPLES TO START WITH")}</div>
          <div className="ask-chips">
            {STARTERS.map(([label, value]) => (
              <button type="button" key={label} className="ask-chip" onClick={() => fill(value)}>
                <Icon name={{ "Supplier delay": "mail", "Plant outage": "wrench", "Quality hold": "shield", Rumor: "alert" }[label]} />{tr(label)}
              </button>
            ))}
          </div>
        </div>
      )}
    </section>
  );
}

export function EventRun() {
  const { reload } = useData();
  const { toast } = useUi();
  const [job, setJob] = useState(null);
  const [stopping, setStopping] = useState(false);
  const seq = useRef(-1);
  const accept = useCallback((data) => {
    if (!data || typeof data.seq !== "number" || data.seq <= seq.current) return;
    seq.current = data.seq;
    setJob(data);
    if (!data.running) setStopping(false);
  }, []);

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
  }, [accept]);

  // Event run writes each finished event into the feed: refresh the page data as it lands, and
  // once when a run starts (the feed is cleared) and ends.
  const progress = job ? `${job.running}:${job.done}` : "";
  useEffect(() => { if (progress) reload(); }, [progress]); // eslint-disable-line react-hooks/exhaustive-deps

  const run = async () => {
    try {
      const res = await fetch("/api/events/run", { method: "POST", headers: { "Content-Type": "application/json" }, body: "{}" });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) toast(data.error || "Could not start the event run");
    } catch {
      toast(tr("Could not start the event run"));
    }
  };

  // The button answers at once; the server ends the run in the same request and the reply is applied
  // directly, so nothing waits for the event the model is still reading.
  const halt = async () => {
    setStopping(true);
    try {
      const res = await fetch("/api/events/run/stop", { method: "POST", headers: { "Content-Type": "application/json" }, body: "{}" });
      if (res.ok) accept(await res.json());
      else { setStopping(false); toast(tr("Could not stop the event run")); }
    } catch {
      setStopping(false);
      toast(tr("Could not stop the event run"));
    }
  };

  const shown = job || EMPTY;
  const width = shown.total ? Math.round((shown.done / shown.total) * 100) : 0;
  const blurb = shown.running
    ? (shown.current
      ? tr("Reading {feed}. {done} of {total} finished.", { feed: shown.current, done: shown.done, total: shown.total })
      : tr("Reading the feed. {done} of {total} finished.", { done: shown.done, total: shown.total }))
    : shown.events.length
      ? (shown.error === "Stopped" ? tr("Stopped after {done} of {total} events.", { done: shown.done, total: shown.total })
        : shown.error ? tr("Stopped. {error}.", { error: shown.error }) : tr("Finished. {done} events.", { done: shown.done }))
      : tr("Walks the 15 given events, then any event from the chat, and shows each one as it finishes. The saved run of the 15 stays as it is.");

  return (
    <div className="card desk-card">
      <CardHead title={tr("Event run")} sub={blurb}>
        <div className="desk-actions">
          {shown.running
            ? <button type="button" className="btn danger" onClick={halt} disabled={stopping}>{stopping ? tr("Stopping…") : <><Icon name="stop" />{tr("Stop")}</>}</button>
            : <button type="button" className="btn primary" onClick={run}><Icon name="play" />{tr("Run events")}</button>}
          {!!shown.events.length && !shown.running && <a className="btn" href="#/events">{tr("Open the feed")}</a>}
          <ResetButton kind="events" />
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
    </div>
  );
}
