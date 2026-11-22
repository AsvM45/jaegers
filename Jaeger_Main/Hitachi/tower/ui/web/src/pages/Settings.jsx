import { useEffect, useMemo, useState } from "react";
import { Icon } from "../lib/icons.jsx";
import { useSettings } from "../lib/settings.jsx";
import { fmt } from "../lib/constants.js";
import { MIC_SETTINGS } from "../lib/voice.js";
import { CardHead, Toggle } from "../components/common.jsx";
import { Select } from "../components/Select.jsx";
import { Page } from "./Page.jsx";
import { LANGUAGES, msg, systemLanguage, tr } from "../lib/i18n.js";

const HERE_ZONE = Intl.DateTimeFormat().resolvedOptions().timeZone;
const ZONES = (() => {
  try { return Intl.supportedValuesOf("timeZone"); } catch { return [HERE_ZONE, "UTC"]; }
})();
// "GMT-6" for a zone right now, shown beside its name and searchable.
function offset(zone) {
  try {
    return new Intl.DateTimeFormat("en-US", { timeZone: zone, timeZoneName: "shortOffset" })
      .formatToParts(new Date()).find((p) => p.type === "timeZoneName")?.value || "";
  } catch { return ""; }
}
// Voice languages: the native name, with the English name beside it.
const NATIVE = { en: "English", es: "Español", fr: "Français", de: "Deutsch", pt: "Português", ja: "日本語", zh: "中文", ko: "한국어", hi: "हिन्दी" };

function Row({ label, hint, children }) {
  return (
    <div className="set-row">
      <div className="set-label"><b>{label}</b>{hint && <span>{hint}</span>}</div>
      <div className="set-control">{children}</div>
    </div>
  );
}

// Microphone permission as the browser reports it, plus a one-click check that asks for it.
function Microphone() {
  const [state, setState] = useState("unknown");
  const [note, setNote] = useState("");

  useEffect(() => {
    let status;
    const on = () => setState(status.state);
    navigator.permissions?.query({ name: "microphone" }).then((s) => { status = s; on(); s.addEventListener("change", on); })
      .catch(() => {});
    return () => status?.removeEventListener("change", on);
  }, []);

  const check = async () => {
    setNote("");
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const name = stream.getAudioTracks()[0]?.label;
      stream.getTracks().forEach((t) => t.stop());
      setState("granted");
      setNote(name ? tr("Working: {name}", { name: name }) : "Working.");
    } catch (err) {
      setState(err?.name === "NotAllowedError" ? "denied" : state);
      setNote(err?.name === "NotAllowedError"
        ? "Blocked. Allow the microphone for this page in the browser (address bar, or Safari → Settings for This Website), and for the browser or app in System Settings → Privacy & Security → Microphone."
        : err?.name === "NotFoundError" ? "No microphone was found." : tr("Could not open the microphone ({err}).", { err: err?.name || err }));
    }
  };

  const word = { granted: ["ok", msg("Allowed"), "good"], denied: ["x", msg("Blocked"), "bad"], prompt: ["alert", msg("Will ask when you record"), "warn"] }[state];
  return (
    <>
      <div className="set-inline">
        {word ? <span className={`set-pill ${word[2]}`}><Icon name={word[0]} />{tr(word[1])}</span> : <span className="set-pill">{tr("Not checked")}</span>}
        <button type="button" className="btn" onClick={check}><Icon name="mic" />{tr("Check microphone")}</button>
        {state === "denied" && (
          <button type="button" className="btn" onClick={() => (window.towerDesktop?.openMicSettings ? window.towerDesktop.openMicSettings() : (window.location.href = MIC_SETTINGS))}>{tr("Open microphone settings")}</button>
        )}
      </div>
      {note && <p className="set-note">{note}</p>}
    </>
  );
}

export default function Settings() {
  const { settings, update, reset, formatTime } = useSettings();
  const [voice, setVoice] = useState(null);

  useEffect(() => {
    fetch(`/api/voice?lang=${encodeURIComponent(settings.voiceLang)}`, { cache: "no-store" })
      .then((r) => (r.ok ? r.json() : null)).then(setVoice).catch(() => setVoice(null));
  }, [settings.voiceLang]);

  const zones = useMemo(() => [
    ["auto", tr("Default"), `${HERE_ZONE.replace(/_/g, " ")} · ${offset(HERE_ZONE)}`],
    ...ZONES.map((z) => [z, z.replace(/_/g, " ").replace(/\//g, " / "), offset(z)]),
  ], []);
  const now = new Date();
  const sample = `${formatTime(`${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}-${String(now.getDate()).padStart(2, "0")} ${String(now.getHours()).padStart(2, "0")}:${String(now.getMinutes()).padStart(2, "0")}`)} · ${fmt(1234567.5)}`;
  const languages = Object.entries(voice?.languages || { en: "English" })
    .map(([code, english]) => [code, NATIVE[code] || english, NATIVE[code] && NATIVE[code] !== english ? english : ""]);

  return (
    <Page title={tr("Settings")} subtitle={<span>{tr("Saved in this browser, for you only")}</span>}>
      <div className="set-page">
        <div className="card">
          <CardHead title={tr("Appearance")} />
          <Row label={tr("Theme")}>
            <Toggle value={settings.theme} onChange={(v) => update({ theme: v })}
              options={[["dark", tr("Dark")], ["light", tr("Light")]]} />
          </Row>
          <Row label={tr("Text size")}>
            <Toggle value={settings.textSize} onChange={(v) => update({ textSize: v })} options={[["small", tr("Small")], ["default", tr("Default")], ["large", tr("Large")], ["xlarge", tr("Extra large")]]} />
          </Row>
          <Row label={tr("Motion")} hint={tr("Reduced turns off count-ups, chart draw-ins and hover lifts.")}>
            <Toggle value={settings.motion} onChange={(v) => update({ motion: v })} options={[["full", tr("Full")], ["reduce", tr("Reduced")]]} />
          </Row>
        </div>

        <div className="card">
          <CardHead title={tr("Language and region")} />
          <Row label={tr("Language")} hint={tr("The dashboard's labels and help. Event messages and the tower's reasoning stay as they were written.")}>
            <Select label={tr("Language")} value={settings.language} onChange={(v) => update({ language: v })}
              options={[["auto", tr("Default"), LANGUAGES.find(([c]) => c === systemLanguage())?.[1]],
                ...LANGUAGES.map(([code, name, english]) => [code, name, english])]} />
          </Row>
          <Row label={tr("Time")} hint={tr("Dates and numbers follow the language.")}>
            <Toggle value={settings.clock === "24" ? "24" : "12"} onChange={(v) => update({ clock: v })}
              options={[["12", tr("12-hour")], ["24", tr("24-hour (military)")]]} />
          </Row>
          <Row label={tr("Time zone")} hint={tr("For run and test times. Event times stay as each message gave them.")}>
            <Select label={tr("Time zone")} value={settings.timeZone} onChange={(v) => update({ timeZone: v })} options={zones} />
          </Row>
          <Row label={tr("Preview")}><span className="mono">{sample}</span></Row>
        </div>

        <div className="card">
          <CardHead title={tr("Voice")} sub={tr("Recorded in the page and turned into text on this computer. No audio leaves the laptop.")} />
          <Row label={tr("Microphone")}><Microphone /></Row>
          <Row label={tr("Listen for")} hint={settings.voiceLang !== "en" ? tr("Other languages use the multilingual model.") : tr("English uses the English-only model, which is more accurate.")}>
            <Select label={tr("Voice language")} value={settings.voiceLang} onChange={(v) => update({ voiceLang: v })} options={languages} />
          </Row>
          <Row label={tr("Speech engine")}>
            {voice?.ready
              ? <span className="set-pill good"><Icon name="ok" />{tr("Ready · {model}", { model: /\.en\b/.test(voice.model || "") ? tr("English model") : tr("Multilingual model") })}</span>
              : <span className="set-pill bad"><Icon name="alert" />{voice?.problem || "The dashboard server did not answer."}</span>}
          </Row>
        </div>

        <div className="set-foot">
          <button type="button" className="btn" onClick={reset}><Icon name="refresh" />{tr("Reset to defaults")}</button>
        </div>
      </div>
    </Page>
  );
}
