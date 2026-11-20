// Per-viewer settings: theme, text size, motion, language, formats, time zone and voice language.
// Kept in this browser's localStorage; the page works the same when storage is unavailable.
import { Fragment, createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { setClock, setNumberLocale } from "./constants.js";
import { LANGUAGES, msg, setLanguage, systemLanguage } from "./i18n.js";

export const DEFAULTS = {
  theme: "system",        // system (Default: follows this computer) | dark | light
  textSize: "default",    // small | default | large | xlarge
  motion: "full",         // full | reduce
  language: "auto",       // auto (this computer's, when the dashboard has it) or a code in LANGUAGES
  locale: "auto",         // auto (match the language) or a BCP 47 tag: dates and numbers
  timeZone: "auto",       // auto (this computer) or an IANA zone: run and test times
  clock: "12",            // 12 (normal, 7:17 PM) | 24 (military, 19:17)
  voiceLang: "en",        // the language Whisper listens for
};


const KEY = "tower.settings.v1";

function load() {
  try {
    const saved = JSON.parse(localStorage.getItem(KEY) || "{}");
    const out = { ...DEFAULTS, ...(saved && typeof saved === "object" ? saved : {}) };
    // Before there was a Language setting, Formats was the only language choice: carry it over.
    if (!("language" in (saved || {})) && out.locale !== "auto") {
      const code = out.locale.split("-")[0];
      if (LANGUAGES.some(([c]) => c === code)) { out.language = code; out.locale = "auto"; }
    }
    return out;
  } catch {
    return { ...DEFAULTS };
  }
}

function save(value) {
  try { localStorage.setItem(KEY, JSON.stringify(value)); } catch { /* private window: settings last this visit */ }
}

const systemDark = () => !window.matchMedia || window.matchMedia("(prefers-color-scheme: dark)").matches;

const Ctx = createContext(null);

export function SettingsProvider({ children }) {
  const [settings, setSettings] = useState(load);
  const [dark, setDark] = useState(systemDark);

  useEffect(() => {
    const mq = window.matchMedia?.("(prefers-color-scheme: dark)");
    if (!mq) return undefined;
    const on = () => setDark(mq.matches);
    mq.addEventListener("change", on);
    return () => mq.removeEventListener("change", on);
  }, []);

  const theme = settings.theme === "system" ? (dark ? "dark" : "light") : settings.theme;
  const uiLang = settings.language === "auto" ? systemLanguage() : settings.language;
  setLanguage(uiLang); // before children render, so t() uses it on this pass
  const matched = settings.language === "auto" ? undefined : LANGUAGES.find(([c]) => c === uiLang)?.[3];
  // Dates and numbers always follow the language.
  const locale = matched;
  const clock = settings.clock === "24" ? "24" : "12";
  setClock(clock === "12");
  const timeZone = settings.timeZone === "auto" ? undefined : settings.timeZone;
  setNumberLocale(locale); // before children render, so fmt() uses it on this pass

  useEffect(() => {
    const root = document.documentElement;
    root.dataset.theme = theme;
    root.dataset.size = settings.textSize;
    root.dataset.motion = settings.motion;
    root.lang = uiLang;
  }, [theme, settings.textSize, settings.motion, uiLang]);

  const update = useCallback((patch) => setSettings((s) => { const next = { ...s, ...patch }; save(next); return next; }), []);
  const reset = useCallback(() => { save(DEFAULTS); setSettings({ ...DEFAULTS }); }, []);

  // "2026-11-08 10:14:21" (this computer's clock, as the server writes it) -> the chosen zone and format.
  const formatTime = useCallback((value) => {
    if (!value) return "";
    const m = String(value).match(/^(\d{4})-(\d{2})-(\d{2})[ T](\d{2}):(\d{2})(?::(\d{2}))?/);
    if (!m) return String(value);
    const d = new Date(+m[1], +m[2] - 1, +m[3], +m[4], +m[5], +(m[6] || 0));
    try {
      return new Intl.DateTimeFormat(locale, {
        timeZone, year: "numeric", month: "short", day: "numeric", hour: clock === "12" ? "numeric" : "2-digit", minute: "2-digit", hour12: clock === "12",
        ...(m[6] ? { second: "2-digit" } : {}), timeZoneName: timeZone ? "short" : undefined,
      }).format(d);
    } catch {
      return String(value);
    }
  }, [locale, timeZone, clock]);

  const value = useMemo(() => ({ settings, theme, language: uiLang, locale, clock, update, reset, formatTime }),
    [settings, theme, uiLang, locale, clock, update, reset, formatTime]);
  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

// A new language or number format redraws the pages, so every label (including the ones read from
// constants) comes out in it. It sits inside the UI and data providers: filters, the selected event
// and the loaded data stay, and nothing is fetched again.
export function Redraw({ children }) {
  const { language, locale, clock } = useContext(Ctx);
  return <Fragment key={`${language}|${locale || ""}|${clock}`}>{children}</Fragment>;
}

export const useSettings = () => useContext(Ctx);
