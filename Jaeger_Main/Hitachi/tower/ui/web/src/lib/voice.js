// Voice input: record the microphone in the page, show a live waveform, then transcribe the
// recording on this machine (POST /api/voice/transcribe, whisper.cpp). No audio leaves the laptop.
//
// Asking for the microphone (getUserMedia) is what makes Safari, Chrome and the desktop app show
// their permission prompt. If access was refused before, the browser will not ask again by itself,
// so the error says where to turn it back on.
import { useCallback, useEffect, useRef, useState } from "react";
import { tr } from "./i18n.js";

const RATE = 16000;          // what Whisper expects
const BARS = 96;             // waveform bars on screen
const MAX_SECONDS = 180;     // stop on its own after three minutes

export const MIC_SETTINGS = "x-apple.systempreferences:com.apple.preference.security?Privacy_Microphone";

function micProblem(err) {
  const name = err?.name || "";
  const mac = /Mac/.test(navigator.platform || navigator.userAgent);
  if (name === "NotAllowedError" || name === "SecurityError") {
    return {
      blocked: true,
      text: window.towerDesktop
        ? tr("The desktop app isn't allowed to use the microphone. Turn it on in System Settings → Privacy & Security → Microphone, then try again.")
        : mac
          ? tr("Microphone access is blocked for this page. Allow it from the address bar (the camera/microphone icon, or Safari → Settings for This Website), and make sure your browser is on in System Settings → Privacy & Security → Microphone.")
          : tr("Microphone access is blocked for this page. Allow it from the address bar (the camera/microphone icon)."),
    };
  }
  if (name === "NotFoundError" || name === "OverconstrainedError") return { text: tr("No microphone was found.") };
  if (name === "NotReadableError") return { text: tr("The microphone is in use by another app.") };
  if (!navigator.mediaDevices?.getUserMedia) return { text: tr("This browser can't record audio here. Open the dashboard at http://127.0.0.1 in Safari or Chrome.") };
  return { text: tr("The microphone could not start ({reason}).", { reason: name || String(err) }) };
}

// Float32 chunks at the device rate -> 16 kHz mono 16-bit WAV.
export function toWav(chunks, inRate) {
  let length = 0;
  for (const c of chunks) length += c.length;
  const input = new Float32Array(length);
  let at = 0;
  for (const c of chunks) { input.set(c, at); at += c.length; }
  const ratio = inRate / RATE;
  const out = new Int16Array(Math.floor(input.length / ratio));
  for (let i = 0; i < out.length; i += 1) {
    const from = Math.floor(i * ratio), to = Math.min(input.length, Math.floor((i + 1) * ratio));
    let sum = 0;
    for (let j = from; j < to; j += 1) sum += input[j];
    const v = Math.max(-1, Math.min(1, sum / Math.max(1, to - from)));
    out[i] = v < 0 ? v * 0x8000 : v * 0x7fff;
  }
  const buf = new ArrayBuffer(44 + out.length * 2), view = new DataView(buf);
  const str = (o, s) => { for (let i = 0; i < s.length; i += 1) view.setUint8(o + i, s.charCodeAt(i)); };
  str(0, "RIFF"); view.setUint32(4, 36 + out.length * 2, true); str(8, "WAVE"); str(12, "fmt ");
  view.setUint32(16, 16, true); view.setUint16(20, 1, true); view.setUint16(22, 1, true);
  view.setUint32(24, RATE, true); view.setUint32(28, RATE * 2, true); view.setUint16(32, 2, true);
  view.setUint16(34, 16, true); str(36, "data"); view.setUint32(40, out.length * 2, true);
  new Int16Array(buf, 44).set(out);
  return new Blob([buf], { type: "audio/wav" });
}

// state: "idle" | "asking" (waiting on the permission prompt) | "recording" | "transcribing"
export function useVoice({ lang = "en", onText, onProblem }) {
  const [state, setState] = useState("idle");
  const [levels, setLevels] = useState(() => Array(BARS).fill(0));
  const [seconds, setSeconds] = useState(0);
  const [blocked, setBlocked] = useState(false);
  const [engine, setEngine] = useState(null);   // GET /api/voice: ready, problem, model
  const rec = useRef(null);

  useEffect(() => {
    let live = true;
    fetch(`/api/voice?lang=${encodeURIComponent(lang)}`, { cache: "no-store" })
      .then((r) => (r.ok ? r.json() : null)).then((d) => { if (live) setEngine(d); })
      .catch(() => { if (live) setEngine(null); });
    return () => { live = false; };
  }, [lang]);

  const release = useCallback(() => {
    const r = rec.current;
    if (!r) return;
    clearInterval(r.timer);
    r.stream.getTracks().forEach((t) => t.stop());
    r.ctx.close().catch(() => {});
    rec.current = null;
  }, []);

  useEffect(() => release, [release]);

  const finish = useCallback(async (keep) => {
    const r = rec.current;
    if (!r) return;
    const chunks = r.chunks, rate = r.ctx.sampleRate;
    release();
    setLevels(Array(BARS).fill(0));
    if (!keep) { setState("idle"); return; }
    if (!chunks.length) { setState("idle"); onProblem(tr("Nothing was recorded.")); return; }
    setState("transcribing");
    try {
      const res = await fetch(`/api/voice/transcribe?lang=${encodeURIComponent(lang)}`, {
        method: "POST", headers: { "Content-Type": "audio/wav" }, body: toWav(chunks, rate),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) onProblem(data.error || tr("Transcription failed."));
      else if (!data.text) onProblem(tr("Didn't catch any words. Try again a little closer to the microphone."));
      else onText(data.text);
    } catch {
      onProblem(tr("Could not reach the dashboard server to transcribe."));
    } finally {
      setState("idle");
    }
  }, [lang, onProblem, onText, release]);

  const start = useCallback(async () => {
    if (rec.current || state !== "idle") return;
    if (engine && !engine.ready) { onProblem(engine.problem); return; }
    if (!navigator.mediaDevices?.getUserMedia) { onProblem(micProblem({}).text); return; }
    // The audio context must start inside the click. After the permission prompt the click no
    // longer counts as a user gesture, and the browser would keep the context paused (silence).
    const Ctx = window.AudioContext || window.webkitAudioContext;
    const ctx = new Ctx();
    ctx.resume().catch(() => {});
    setState("asking");
    let stream;
    try {
      stream = await navigator.mediaDevices.getUserMedia({
        audio: { channelCount: 1, echoCancellation: true, noiseSuppression: true, autoGainControl: true },
      });
    } catch (err) {
      ctx.close().catch(() => {});
      const p = micProblem(err);
      setBlocked(!!p.blocked);
      setState("idle");
      onProblem(p.text);
      return;
    }
    setBlocked(false);
    if (ctx.state !== "running") await ctx.resume().catch(() => {});
    const source = ctx.createMediaStreamSource(stream);
    const analyser = ctx.createAnalyser();
    analyser.fftSize = 1024;
    // ScriptProcessor is old but works in every browser this runs in, without a worklet file.
    const tap = ctx.createScriptProcessor(4096, 1, 1);
    const mute = ctx.createGain();
    mute.gain.value = 0;
    const chunks = [];
    tap.onaudioprocess = (e) => chunks.push(new Float32Array(e.inputBuffer.getChannelData(0)));
    source.connect(analyser);
    source.connect(tap);
    tap.connect(mute);
    mute.connect(ctx.destination);
    const frame = new Float32Array(analyser.fftSize);
    const t0 = Date.now();
    const timer = setInterval(() => {
      analyser.getFloatTimeDomainData(frame);
      let sum = 0;
      for (let i = 0; i < frame.length; i += 1) sum += frame[i] * frame[i];
      const level = Math.min(1, Math.sqrt(Math.sqrt(sum / frame.length)) * 2.2);
      setLevels((l) => [...l.slice(1), level]);
      const s = Math.floor((Date.now() - t0) / 1000);
      setSeconds(s);
      if (s >= MAX_SECONDS) finish(true);
    }, 70);
    rec.current = { stream, ctx, chunks, timer };
    setSeconds(0);
    setState("recording");
  }, [engine, finish, onProblem, state]);

  return {
    state, levels, seconds, blocked, engine,
    start, stop: () => finish(true), cancel: () => finish(false),
  };
}

export const clock = (s) => `${Math.floor(s / 60)}:${String(s % 60).padStart(2, "0")}`;
