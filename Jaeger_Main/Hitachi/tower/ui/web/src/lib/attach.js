// Read an attached file into event messages. Everything happens in the page; nothing is uploaded
// until the message is sent like a typed one.
//
//   .txt .md .log   the text as it is
//   .pdf            the text of every page (pdf.js, loaded only when a PDF is attached)
//   .eml            a saved email: Subject, From and the plain-text body, like events.json's email events
//   .json           one event ({"text": ...}, or a string), or several ([...] or {"events": [...]})

import { tr } from "./i18n.js";

export const ACCEPT = ".txt,.pdf,.json,.eml,.md,.log,text/plain,application/pdf,application/json,message/rfc822";
const KINDS = { txt: "text", md: "text", log: "text", pdf: "pdf", json: "json", eml: "eml" };
const MAX_BYTES = 10 * 1024 * 1024;

export class AttachError extends Error {}

export async function readAttachment(file) {
  const ext = (file.name.split(".").pop() || "").toLowerCase();
  const kind = KINDS[ext];
  if (!kind) throw new AttachError(tr("{file}: only .txt, .pdf, .json, .eml, .md and .log files can be attached.", { file: file.name }));
  if (file.size > MAX_BYTES) throw new AttachError(tr("{file} is larger than 10 MB.", { file: file.name }));
  if (!file.size) throw new AttachError(tr("{file} is empty.", { file: file.name }));
  let texts;
  if (kind === "pdf") texts = [await pdfText(file)];
  else if (kind === "eml") texts = [emailText(await file.text())];
  else if (kind === "json") texts = jsonEvents(await file.text(), file.name);
  else texts = [await file.text()];
  texts = texts.map((t) => tidy(t)).filter(Boolean);
  if (!texts.length) {
    throw new AttachError(kind === "pdf"
      ? tr("{file} has no text to read (it may be a scanned image). Paste the text instead.", { file: file.name })
      : tr("{file} has no message text in it.", { file: file.name }));
  }
  return texts;
}

const tidy = (t) => String(t || "").replace(/\r\n?/g, "\n").replace(/[ \t]{2,}/g, " ").replace(/[ \t]+\n/g, "\n").replace(/\n{3,}/g, "\n\n").trim();

async function pdfText(file) {
  const pdfjs = await import("pdfjs-dist");
  const worker = await import("pdfjs-dist/build/pdf.worker.min.mjs?url");
  pdfjs.GlobalWorkerOptions.workerSrc = worker.default;
  let doc;
  try {
    doc = await pdfjs.getDocument({ data: new Uint8Array(await file.arrayBuffer()) }).promise;
  } catch (err) {
    throw new AttachError(err?.name === "PasswordException"
      ? tr("{file} could not be opened as a PDF (it is password protected).", { file: file.name })
      : tr("{file} could not be opened as a PDF.", { file: file.name }));
  }
  const pages = [];
  for (let n = 1; n <= Math.min(doc.numPages, 30); n += 1) {
    const content = await (await doc.getPage(n)).getTextContent();
    let line = "";
    // pdf.js gives spaces as their own items, so items join with nothing; a line break is hasEOL.
    for (const item of content.items) line += (item.str || "") + (item.hasEOL ? "\n" : "");
    pages.push(line);
  }
  return pages.join("\n\n");
}

function jsonEvents(raw, name) {
  let data;
  try { data = JSON.parse(raw); } catch { throw new AttachError(tr("{file} is not valid JSON.", { file: name })); }
  const list = Array.isArray(data) ? data : Array.isArray(data?.events) ? data.events : [data];
  return list.map((item) => {
    if (typeof item === "string") return item;
    if (!item || typeof item !== "object") return "";
    const body = item.text ?? item.body ?? item.message ?? item.content ?? "";
    return item.subject && !String(body).startsWith("Subject:") ? `Subject: ${item.subject}\n\n${body}` : body;
  });
}

// ---- email (.eml) ----

function decodeWords(s) {
  // =?utf-8?B?...?= and =?utf-8?Q?...?= in headers
  return s.replace(/=\?([^?]+)\?([bq])\?([^?]*)\?=/gi, (_, charset, enc, data) => {
    try {
      const bytes = enc.toLowerCase() === "b"
        ? Uint8Array.from(atob(data), (c) => c.charCodeAt(0))
        : qpBytes(data.replace(/_/g, " "));
      return new TextDecoder(charset).decode(bytes);
    } catch { return data; }
  });
}

function qpBytes(s) {
  const clean = s.replace(/=\r?\n/g, "");
  const out = [];
  for (let i = 0; i < clean.length; i += 1) {
    if (clean[i] === "=" && /^[0-9a-f]{2}$/i.test(clean.slice(i + 1, i + 3))) { out.push(parseInt(clean.slice(i + 1, i + 3), 16)); i += 2; }
    else out.push(clean.charCodeAt(i) & 0xff);
  }
  return new Uint8Array(out);
}

function splitPart(raw) {
  const at = raw.search(/\r?\n\r?\n/);
  const head = at < 0 ? raw : raw.slice(0, at), body = at < 0 ? "" : raw.slice(at).replace(/^\r?\n\r?\n/, "");
  const headers = {};
  for (const line of head.replace(/\r?\n[ \t]+/g, " ").split(/\r?\n/)) {
    const m = line.match(/^([\w-]+):\s*(.*)$/);
    if (m) headers[m[1].toLowerCase()] = m[2];
  }
  return { headers, body };
}

function partText({ headers, body }) {
  const type = (headers["content-type"] || "text/plain").toLowerCase();
  const boundary = (headers["content-type"] || "").match(/boundary="?([^";]+)"?/i)?.[1];
  if (type.startsWith("multipart/") && boundary) {
    const parts = body.split(`--${boundary}`).slice(1).filter((p) => !p.startsWith("--")).map(splitPart);
    const plain = parts.find((p) => (p.headers["content-type"] || "text/plain").toLowerCase().startsWith("text/plain"));
    const pick = plain || parts.find((p) => /^(text\/html|multipart\/)/i.test(p.headers["content-type"] || ""));
    return pick ? partText(pick) : "";
  }
  const charset = type.match(/charset="?([^";]+)"?/)?.[1] || "utf-8";
  const enc = (headers["content-transfer-encoding"] || "").toLowerCase();
  let text = body;
  try {
    if (enc === "base64") text = new TextDecoder(charset).decode(Uint8Array.from(atob(body.replace(/\s+/g, "")), (c) => c.charCodeAt(0)));
    else if (enc === "quoted-printable") text = new TextDecoder(charset).decode(qpBytes(body));
  } catch { /* keep the raw body */ }
  if (type.startsWith("text/html")) text = new DOMParser().parseFromString(text, "text/html").body.textContent || "";
  return text;
}

function emailText(raw) {
  const top = splitPart(raw);
  const lines = [];
  if (top.headers.subject) lines.push(`Subject: ${decodeWords(top.headers.subject)}`);
  if (top.headers.from) lines.push(`From: ${decodeWords(top.headers.from)}`);
  return `${lines.join("\n")}${lines.length ? "\n\n" : ""}${partText(top)}`;
}
