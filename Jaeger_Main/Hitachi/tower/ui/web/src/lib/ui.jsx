// UI state that outlives a page (filters, selections, search), the hash route, the hover tip and toasts.
import { createContext, useCallback, useContext, useEffect, useRef, useState } from "react";

const INITIAL = {
  q: "", sel: null, evFilter: { outcome: "all", kind: "all" },
  testReader: null, logFilter: "reader", caseFilter: { verdict: "all", cat: "all" },
  logTab: "output", logFile: null, callEvent: "", callFailed: false,
  chartView: "chart", confirmDelete: null,
  orb: { view: "network", event: null, run: "" },
};

const UiCtx = createContext(null);

function readHash() { return location.hash.replace(/^#\/?/, "").split("?")[0].split("/"); }

export function UiProvider({ children }) {
  const [ui, setState] = useState(INITIAL);
  const set = useCallback((patch) => setState((s) => ({ ...s, ...(typeof patch === "function" ? patch(s) : patch) })), []);

  const [segs, setSegs] = useState(readHash);
  useEffect(() => {
    const on = () => {
      const s = readHash();
      // Old links: #/reports and #/writeups are now the Tests page.
      if (s[0] === "reports" || s[0] === "writeups") { location.replace("#/tests"); return; }
      setSegs(s);
    };
    window.addEventListener("hashchange", on);
    return () => window.removeEventListener("hashchange", on);
  }, []);

  // Toast
  const [toastMsg, setToastMsg] = useState({ text: "", on: false });
  const timer = useRef();
  const toast = useCallback((text) => {
    setToastMsg({ text, on: true });
    clearTimeout(timer.current);
    timer.current = setTimeout(() => setToastMsg((t) => ({ ...t, on: false })), 3200);
  }, []);

  // Hover tip: any element calls tip.show(event, content) / tip.hide().
  const [tipState, setTip] = useState({ on: false, x: 0, y: 0, content: null });
  const tip = useRef({
    show: (e, content) => setTip({ on: true, x: e.pageX, y: e.pageY, content }),
    hide: () => setTip((t) => ({ ...t, on: false })),
  }).current;

  return (
    <UiCtx.Provider value={{ ui, set, segs, toast, tip }}>
      {children}
      <div className={`tip${tipState.on ? " on" : ""}`} style={{ left: tipState.x, top: tipState.y }}>{tipState.content}</div>
      <div className={`toast${toastMsg.on ? " on" : ""}`} role="status" aria-live="polite">{toastMsg.text}</div>
    </UiCtx.Provider>
  );
}

export const useUi = () => useContext(UiCtx);
export const go = (hash) => { location.hash = hash; };

// Props that show a plain-text tip on hover.
export function useTipProps() {
  const { tip } = useUi();
  return (text) => ({ onMouseMove: (e) => tip.show(e, <b>{text}</b>), onMouseLeave: tip.hide });
}
