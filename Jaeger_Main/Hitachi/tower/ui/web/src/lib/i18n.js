// Dashboard language. tr("English text", { n: 3 }) returns the text in the language chosen in
// Settings, or the English when a string has no translation yet. Keys are the English strings
// themselves, so a page reads naturally in the source. {name} in a string is filled from vars.
//
// What the tower itself writes (event messages, summaries, reasons, tool results) is data and stays
// as written; only the dashboard's own words are translated. Translations live in src/locales/.
import { Fragment, createElement } from "react";
import de from "../locales/de.json";
import es from "../locales/es.json";
import fr from "../locales/fr.json";
import hi from "../locales/hi.json";
import ja from "../locales/ja.json";
import ko from "../locales/ko.json";
import pt from "../locales/pt.json";
import zh from "../locales/zh.json";

const DICTS = { de, es, fr, hi, ja, ko, pt, zh };

// [code, name in that language, English name, the date and number format it implies]
export const LANGUAGES = [
  ["en", "English", "", "en-US"], ["ja", "日本語", "Japanese", "ja-JP"], ["es", "Español", "Spanish", "es-ES"],
  ["fr", "Français", "French", "fr-FR"], ["de", "Deutsch", "German", "de-DE"], ["pt", "Português", "Portuguese", "pt-BR"],
  ["zh", "中文 (简体)", "Chinese, Simplified", "zh-CN"], ["ko", "한국어", "Korean", "ko-KR"], ["hi", "हिन्दी", "Hindi", "hi-IN"],
];

let current = "en";
let dict = null;

// The language this computer prefers, when the dashboard has it; otherwise English.
export function systemLanguage() {
  const base = (navigator.language || "en").split("-")[0];
  return DICTS[base] ? base : "en";
}

// Called by the settings provider before the app renders.
export function setLanguage(code) {
  current = DICTS[code] ? code : "en";
  dict = DICTS[current] || null;
}

export const language = () => current;

// A heading in Title Case, in English only (other languages keep their own capitalisation):
// "What the control tower does" -> "What the Control Tower Does", "Tool-call log" -> "Tool-Call Log".
const MINOR = new Set(["a", "an", "the", "and", "or", "nor", "but", "of", "to", "in", "on", "at", "by", "for", "from", "with", "as", "per", "vs", "via"]);
export function titleCase(text) {
  if (current !== "en" || typeof text !== "string") return text;
  const words = text.split(" ");
  return words.map((w, i) => {
    if (i > 0 && i < words.length - 1 && MINOR.has(w.toLowerCase())) return w.toLowerCase();
    return w.replace(/^([("'“]?)(\p{Ll})/u, (m, p, c) => p + c.toUpperCase()).replace(/-(\p{Ll})/gu, (m, c) => "-" + c.toUpperCase());
  }).join(" ");
}

export function tr(text, vars) {
  let out = (dict && dict[text]) || text;
  if (vars) out = out.replace(/\{(\w+)\}/g, (m, k) => (k in vars ? String(vars[k]) : m));
  return out;
}

// Marks a string to be translated later, where it is shown with tr(variable). It returns the string
// unchanged; it exists so the key list (and a reader) can see which strings are interface text.
export const msg = (text) => text;

// A sentence with markup inside: trx("{n} events, {m} acted on", { n: <b>3</b>, m: <b>2</b> }).
// The whole sentence is translated, so each language puts the bold numbers where its grammar needs.
export function trx(text, parts) {
  return tr(text).split(/(\{\w+\})/).filter(Boolean).map((piece, i) => {
    const key = piece.match(/^\{(\w+)\}$/)?.[1];
    return createElement(Fragment, { key: i }, key && key in parts ? parts[key] : piece);
  });
}

// A table of labels whose values are translated when read: KIND_LABEL.noise -> tr("Noise").
export function translated(table) {
  return new Proxy(table, { get: (obj, key) => (typeof obj[key] === "string" ? tr(obj[key]) : obj[key]) });
}
