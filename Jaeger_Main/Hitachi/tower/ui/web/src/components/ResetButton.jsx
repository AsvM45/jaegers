// Reset events / Reset tests: clears one kind of data after the person types RESET, and offers Undo.
// The server moves the data to runs/.reset/ (tower/ui/reset.py), so a reset can always be undone.
import { useCallback, useEffect, useRef, useState } from "react";
import { Icon } from "../lib/icons.jsx";
import { msg, tr } from "../lib/i18n.js";
import { useData } from "../lib/data.jsx";
import { useUi } from "../lib/ui.jsx";

const WORD = "RESET";

// What each reset clears and what it leaves alone; English keys, translated when shown.
const COPY = {
  events: {
    button: msg("Reset events"),
    title: msg("Reset all event data?"),
    clears: [msg("Every event in the Event feed and on Overview, with its tool calls and notifications"),
      msg("Events added on Add events, and the chat history"), msg("The tool-call log and notifications on the Logs page")],
    keeps: msg("Test results, the frozen submission, the company data and your settings are not touched."),
    done: msg("Event data cleared. Run events rebuilds the feed."),
  },
  tests: {
    button: msg("Reset tests"),
    title: msg("Reset all test results?"),
    clears: [msg("Every saved test run and its results, for every test set and reader"), msg("The run history and the summary report")],
    keeps: msg("Events, the frozen submission, the test cases and your settings are not touched."),
    done: msg("Test results cleared. Run tests grades them again."),
  },
};

// Other parts of the page (the chat transcript, a selected event) listen for this and reload.
export const RESET_EVENT = "tower:reset";

export function ResetButton({ kind, disabled }) {
  const { reload } = useData();
  const { toast, set } = useUi();
  const [state, setState] = useState(null);     // GET /api/reset for this kind: has_data, undo, at
  const [open, setOpen] = useState(false);
  const [typed, setTyped] = useState("");
  const [busy, setBusy] = useState(false);
  const input = useRef(null);
  const copy = COPY[kind];

  const refresh = useCallback(async () => {
    try {
      const res = await fetch("/api/reset", { cache: "no-store" });
      if (res.ok) setState((await res.json())[kind]);
    } catch { /* the buttons stay as they were */ }
  }, [kind]);

  useEffect(() => { refresh(); }, [refresh]);
  useEffect(() => {
    const on = () => refresh();
    window.addEventListener(RESET_EVENT, on);
    return () => window.removeEventListener(RESET_EVENT, on);
  }, [refresh]);
  useEffect(() => {
    if (!open) return undefined;
    setTyped("");
    setTimeout(() => input.current?.focus(), 0);
    const onKey = (e) => { if (e.key === "Escape" && !busy) setOpen(false); };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [open, busy]);

  const call = async (path, body, success) => {
    setBusy(true);
    try {
      const res = await fetch(path, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) { toast(data.error || tr("Could not reset")); return; }
      setOpen(false);
      if (kind === "events") set({ sel: null });
      window.dispatchEvent(new CustomEvent(RESET_EVENT, { detail: { kind } }));
      await reload();
      toast(success);
    } catch {
      toast(tr("Could not reach the dashboard server"));
    } finally {
      setBusy(false);
      refresh();
    }
  };

  const reset = () => call("/api/reset", { kind, confirm: typed.trim() }, tr(copy.done));
  const undo = () => call("/api/reset/undo", { kind }, tr("Reset undone. The data is back."));
  const ready = typed.trim() === WORD;

  return (
    <>
      {state?.undo && !state.has_data && (
        <button type="button" className="btn" onClick={undo} disabled={busy || disabled}
          title={tr("Put back the data cleared at {when}", { when: state.at })}>
          <Icon name="refresh" />{tr("Undo reset")}
        </button>
      )}
      <button type="button" className="btn danger" onClick={() => setOpen(true)} disabled={busy || disabled || state?.has_data === false}
        title={state?.has_data === false ? tr("Nothing to reset") : undefined}>
        <Icon name="trash" />{tr(copy.button)}
      </button>
      {open && (
        <div className="modal-back" onMouseDown={(e) => { if (e.target === e.currentTarget && !busy) setOpen(false); }}>
          <div className="modal" role="dialog" aria-modal="true" aria-labelledby={`reset-${kind}`}>
            <div className="modal-icon" aria-hidden="true"><Icon name="alert" /></div>
            <h3 id={`reset-${kind}`}>{tr(copy.title)}</h3>
            <p className="sub">{tr("This clears:")}</p>
            <ul className="modal-list">{copy.clears.map((line) => <li key={line}>{tr(line)}</li>)}</ul>
            <p className="note">{tr(copy.keeps)} {tr("A copy is kept, and Undo reset puts it back.")}</p>
            <form onSubmit={(e) => { e.preventDefault(); if (ready && !busy) reset(); }}>
              <label className="modal-label" htmlFor={`reset-${kind}-word`}>{tr("Type {word} to confirm", { word: WORD })}</label>
              <input id={`reset-${kind}-word`} ref={input} className="modal-input" value={typed} autoComplete="off" spellCheck={false}
                onChange={(e) => setTyped(e.target.value.toUpperCase())} placeholder={WORD} aria-invalid={!!typed && !ready} />
              <div className="modal-actions">
                <button type="button" className="btn" onClick={() => setOpen(false)} disabled={busy}>{tr("Cancel")}</button>
                <button type="submit" className="btn danger solid" disabled={!ready || busy}>
                  {busy ? <><span className="spin"><Icon name="refresh" /></span>{tr("Resetting…")}</> : <><Icon name="trash" />{tr(copy.button)}</>}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </>
  );
}
