"""The test summary as a PDF, built from the same results as the Tests page. Standard library only.

    GET /api/summary.pdf                   (the Tests page's Download PDF)
    python -m tower.ui.summary_pdf out.pdf

A small PDF writer: US Letter pages, the built-in Helvetica fonts, wrapped text, tables and bars.
The report is in English (the built-in PDF fonts have no Japanese, Chinese, Korean or Hindi glyphs).
"""

from __future__ import annotations

import sys
import time
import zlib

from tower.ui import reports

W, H = 612, 792            # US Letter, points
M = 48                     # margin
INK, SUB, MUTED = (0.08, 0.10, 0.20), (0.27, 0.31, 0.42), (0.45, 0.49, 0.60)
LINE, BAND = (0.86, 0.88, 0.93), (0.95, 0.96, 0.99)
ACCENT, GOOD, BAD, WARN = (0.0, 0.38, 0.84), (0.05, 0.55, 0.25), (0.78, 0.18, 0.18), (0.80, 0.52, 0.0)
CAT_NAME = {"supplier_delay": "Supplier delay", "plant_outage": "Plant outage", "quality_hold": "Quality hold",
            "unconfirmed": "Unconfirmed", "compound": "Compound", "noise": "Noise"}

# Advance widths (1/1000 em) for ASCII 32..126, from the Helvetica and Helvetica-Bold AFM files.
_REG = [278, 278, 355, 556, 556, 889, 667, 191, 333, 333, 389, 584, 278, 333, 278, 278] + [556] * 10 + [
    278, 278, 584, 584, 584, 556, 1015, 667, 667, 722, 722, 667, 611, 778, 722, 278, 500, 667, 556, 833, 722,
    778, 667, 778, 722, 667, 611, 722, 667, 944, 667, 667, 611, 278, 278, 278, 469, 556, 333, 556, 556, 500,
    556, 556, 278, 556, 556, 222, 222, 500, 222, 833, 556, 556, 556, 556, 333, 500, 278, 556, 500, 722, 500,
    500, 500, 334, 260, 334, 584]
_BOLD = [278, 333, 474, 556, 556, 889, 722, 238, 333, 333, 389, 584, 278, 333, 278, 278] + [556] * 10 + [
    333, 333, 584, 584, 584, 611, 975, 722, 722, 722, 722, 667, 611, 778, 722, 278, 556, 722, 611, 833, 722,
    778, 667, 778, 722, 667, 611, 722, 667, 944, 667, 667, 611, 333, 278, 333, 584, 556, 333, 556, 611, 556,
    611, 556, 333, 611, 611, 278, 278, 556, 278, 889, 611, 611, 611, 611, 389, 556, 333, 611, 556, 778, 556,
    556, 500, 389, 280, 389, 584]
# The few non-ASCII characters the report uses, in WinAnsiEncoding, with their width.
_EXTRA = {"—": (0x97, 1000), "–": (0x96, 556), "·": (0xB7, 278), "•": (0x95, 350), "’": (0x92, 222),
          "“": (0x93, 333), "”": (0x94, 333), "…": (0x85, 1000), "é": (0xE9, 556), "×": (0xD7, 584)}
_SWAP = {"→": "->", "←": "<-", "✓": "+", "✗": "x", "≥": ">=", "≤": "<="}


def _clean(text) -> str:
    out = []
    for ch in str(text):
        ch = _SWAP.get(ch, ch)
        out.append(ch if (" " <= ch <= "~") or ch in _EXTRA or len(ch) > 1 else "?")
    return "".join(out)


def width(text: str, size: float, bold: bool = False) -> float:
    table = _BOLD if bold else _REG
    total = 0
    for ch in _clean(text):
        total += _EXTRA[ch][1] if ch in _EXTRA else table[ord(ch) - 32] if " " <= ch <= "~" else 556
    return total * size / 1000


def wrap(text: str, size: float, max_w: float, bold: bool = False) -> list[str]:
    lines, line = [], ""
    for word in _clean(text).split():
        trial = f"{line} {word}" if line else word
        if width(trial, size, bold) <= max_w:
            line = trial
            continue
        if line:
            lines.append(line)
        while width(word, size, bold) > max_w:          # a very long token (an id list): hard-break it
            cut = len(word)
            while cut > 1 and width(word[:cut], size, bold) > max_w:
                cut -= 1
            lines.append(word[:cut])
            word = word[cut:]
        line = word
    if line:
        lines.append(line)
    return lines or [""]


def _pdf_string(text: str) -> bytes:
    raw = bytearray()
    for ch in _clean(text):
        raw += bytes([_EXTRA[ch][0]]) if ch in _EXTRA else ch.encode("latin-1")
    return b"(" + bytes(raw).replace(b"\\", b"\\\\").replace(b"(", b"\\(").replace(b")", b"\\)") + b")"


class Doc:
    """Pages of drawing commands, top-left coordinates, with a cursor y for flowing content."""

    def __init__(self, title: str):
        self.title, self.pages, self.ops, self.y = title, [], None, 0
        self.new_page()

    def new_page(self):
        self.ops = []
        self.pages.append(self.ops)
        self.y = M

    def need(self, h: float):
        if self.y + h > H - M - 20:
            self.new_page()

    def _rgb(self, rgb, stroke=False):
        return f"{rgb[0]:.3f} {rgb[1]:.3f} {rgb[2]:.3f} {'RG' if stroke else 'rg'}"

    def text(self, x, y, s, size=10, bold=False, rgb=INK):
        self.ops.append(f"BT /{'F2' if bold else 'F1'} {size} Tf {self._rgb(rgb)} {x:.2f} {H - y - size * 0.8:.2f} Td ".encode()
                        + _pdf_string(s) + b" Tj ET")

    def rect(self, x, y, w, h, rgb):
        self.ops.append(f"{self._rgb(rgb)} {x:.2f} {H - y - h:.2f} {w:.2f} {h:.2f} re f".encode())

    def hline(self, x, y, w, rgb=LINE, lw=0.6):
        self.ops.append(f"{self._rgb(rgb, True)} {lw} w {x:.2f} {H - y:.2f} m {x + w:.2f} {H - y:.2f} l S".encode())

    def para(self, s, size=10, bold=False, rgb=SUB, x=M, w=W - 2 * M, gap=4):
        lead = size * 1.38
        for line in wrap(s, size, w, bold):
            self.need(lead)
            self.text(x, self.y, line, size, bold, rgb)
            self.y += lead
        self.y += gap

    def heading(self, s, size=14):
        self.need(size * 3)
        self.y += 6
        self.text(M, self.y, s, size, True, INK)
        self.y += size * 1.5

    def table(self, cols, rows, size=9):
        """cols: [(title, width, align)]; rows: lists of cells. A cell may be (text, rgb)."""
        pad, lead = 5, size * 1.35
        def draw_row(cells, bold, fill=None):
            wrapped = [wrap(c[0] if isinstance(c, tuple) else c, size, cw - 2 * pad, bold) for c, (_, cw, _) in zip(cells, cols)]
            h = max(len(w) for w in wrapped) * lead + 2 * pad
            self.need(h)
            if fill:
                self.rect(M, self.y, sum(c[1] for c in cols), h, fill)
            x = M
            for cell, lines, (_, cw, align) in zip(cells, wrapped, cols):
                rgb = cell[1] if isinstance(cell, tuple) else (INK if bold else SUB)
                for k, line in enumerate(lines):
                    tx = x + cw - pad - width(line, size, bold) if align == "r" else x + pad
                    self.text(tx, self.y + pad + k * lead, line, size, bold, rgb)
                x += cw
            self.y += h
            self.hline(M, self.y, sum(c[1] for c in cols))
        draw_row([c[0] for c in cols], True, BAND)
        for row in rows:
            draw_row(row, False)
        self.y += 10

    def bytes(self) -> bytes:
        """Serialise: catalog, page tree, two fonts, then a page and a content stream per page."""
        total = len(self.pages)
        objs = [b"<< /Type /Catalog /Pages 2 0 R >>", None,
                b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>",
                b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold /Encoding /WinAnsiEncoding >>"]
        kids = []
        for n, ops in enumerate(self.pages, 1):
            foot = [f"0.45 0.49 0.60 rg BT /F1 8 Tf {M} 28 Td ".encode() + _pdf_string(f"{self.title} · page {n} of {total}") + b" Tj ET"]
            stream = zlib.compress(b"\n".join(ops + foot))
            objs.append(b"<< /Length %d /Filter /FlateDecode >>\nstream\n" % len(stream) + stream + b"\nendstream")
            content_id = len(objs)
            objs.append(f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {W} {H}] /Contents {content_id} 0 R "
                        f"/Resources << /Font << /F1 3 0 R /F2 4 0 R >> >> >>".encode())
            kids.append(f"{len(objs)} 0 R")
        objs[1] = f"<< /Type /Pages /Kids [{' '.join(kids)}] /Count {total} >>".encode()
        objs.append(b"<< /Title " + _pdf_string(self.title) + b" /Producer (Wacky Wheels control tower) >>")
        out, offsets = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n"), []
        for i, body in enumerate(objs, 1):
            offsets.append(len(out))
            out += f"{i} 0 obj\n".encode() + body + b"\nendobj\n"
        xref = len(out)
        out += f"xref\n0 {len(objs) + 1}\n0000000000 65535 f \n".encode()
        out += b"".join(f"{o:010d} 00000 n \n".encode() for o in offsets)
        out += f"trailer\n<< /Size {len(objs) + 1} /Root 1 0 R /Info {len(objs)} 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode()
        return bytes(out)


def _pct(n, total):
    return f"{round(100 * n / total)}%" if total else "—"


def _rate_rgb(n, total):
    if not total:
        return MUTED
    return GOOD if n == total else WARN if n / total >= 0.8 else BAD


def build(data: dict | None = None) -> bytes:
    data = data or reports.payload()
    sets = [(s, r) for s in data["suites"] for r in s["readers"]]
    doc = Doc("Control tower test summary")

    # Title band.
    doc.rect(0, 0, W, 112, (0.04, 0.07, 0.20))
    doc.rect(0, 112, W, 3, ACCENT)
    doc.text(M, 34, "WACKY WHEELS · CONTROL TOWER", 9, True, (0.62, 0.70, 0.88))
    doc.text(M, 52, "Test summary", 24, True, (1, 1, 1))
    doc.text(M, 84, f"Written {time.strftime('%A %d %B %Y, %H:%M')} from the saved results", 10, False, (0.78, 0.82, 0.92))
    doc.y = 140

    # Headline numbers: the newest saved run of each set (as on the Tests page), summed across sets.
    newest = {}
    for s, r in sets:
        if s["id"] not in newest or (r.get("updated") or "") > (newest[s["id"]].get("updated") or ""):
            newest[s["id"]] = r
    passed, total = sum(r["passed"] for r in newest.values()), sum(r["total"] for r in newest.values())
    tiles = [("Cases passed, newest runs", f"{passed} / {total}" if total else "—"), ("Pass rate", _pct(passed, total)),
             ("Test sets", str(len({s['id'] for s, _ in sets}))), ("Readers", str(len({r['label'] for _, r in sets})))]
    tw = (W - 2 * M - 3 * 12) / 4
    for i, (label, value) in enumerate(tiles):
        x = M + i * (tw + 12)
        doc.rect(x, doc.y, tw, 58, BAND)
        doc.text(x + 12, doc.y + 12, label.upper(), 7.5, True, MUTED)
        doc.text(x + 12, doc.y + 28, value, 18, True, _rate_rgb(passed, total) if label == "Pass rate" else INK)
    doc.y += 76

    doc.para("Each test's expected output is its answer key traced through the company tables, independently of the "
             "tower's own graph code. The grader also replays every action in the enterprise simulator and checks it "
             "against the policy handbook. A case passes only when the tower's actions match the answer key exactly.")

    if not sets:
        doc.heading("No results yet")
        doc.para("Run the tests, then download this summary again.")
        return doc.bytes()

    doc.heading("Every test set and reader")
    doc.table([("Test set", 108, "l"), ("Reader", 74, "l"), ("Saved", 82, "l"), ("Incident type", 56, "r"),
               ("Records and dates", 62, "r"), ("Full output", 52, "r"), ("Passed", 82, "r")],
              [[s["title"], r["label"], r.get("updated") or "—",
                f"{r['scores']['kinds_ok']}/{r['total']}", f"{r['scores']['fields_ok']}/{r['total']}",
                f"{r['scores']['output_ok']}/{r['total']}",
                (f"{r['passed']}/{r['total']} · {_pct(r['passed'], r['total'])}", _rate_rgb(r["passed"], r["total"]))]
               for s, r in sets])
    doc.para("Test sets: " + "; ".join(f"{s['title']}: {s['subtitle']}" for s in data["suites"]) + ".", size=8.5, rgb=MUTED)

    for s, r in sets:
        doc.new_page()
        doc.heading(f"{s['title']} · {r['label']}", 16)
        doc.para(f"{r['passed']} of {r['total']} cases passed ({_pct(r['passed'], r['total'])}). Saved {r.get('updated') or 'at an unknown time'}.")
        cats = r.get("by_category") or {}
        if cats:
            doc.heading("By kind of message", 11)
            bar_x, bar_w = M + 250, W - 2 * M - 250
            for cat, v in sorted(cats.items(), key=lambda kv: list(CAT_NAME).index(kv[0]) if kv[0] in CAT_NAME else 99):
                doc.need(22)
                doc.text(M, doc.y + 3, CAT_NAME.get(cat, cat), 9.5, False, INK)
                doc.text(M + 150, doc.y + 3, f"{v['passed']} / {v['total']}", 9.5, True, _rate_rgb(v["passed"], v["total"]))
                doc.rect(bar_x, doc.y + 4, bar_w, 8, BAND)
                if v["total"]:
                    doc.rect(bar_x, doc.y + 4, bar_w * v["passed"] / v["total"], 8, _rate_rgb(v["passed"], v["total"]))
                doc.y += 20
            doc.y += 8
        failed = [c for c in r.get("cases", []) if c.get("verdict") != "PASS"]
        doc.heading(f"Failed cases ({len(failed)})" if failed else "Failed cases", 11)
        if not failed:
            doc.para("None: every case matched its expected output.", rgb=GOOD)
        for c in failed:
            doc.need(48)
            doc.hline(M, doc.y, W - 2 * M)
            doc.y += 7
            doc.text(M, doc.y, f"{c['id']} · {CAT_NAME.get(c.get('category'), c.get('category') or '')}", 10, True, INK)
            doc.text(W - M - width(f"read as {c.get('classification') or '—'}", 8.5), doc.y + 1,
                     f"read as {c.get('classification') or '—'}", 8.5, False, MUTED)
            doc.y += 15
            doc.para(f"“{c.get('text', '').strip()}”", size=8.5, rgb=SUB, gap=2)
            fails = c.get("fails") or c.get("score", {}).get("mismatches") or []
            for f in fails[:4]:
                doc.para(f"• {f}", size=8.5, rgb=BAD, x=M + 8, w=W - 2 * M - 8, gap=0)
            if len(fails) > 4:
                doc.para(f"…and {len(fails) - 4} more differences.", size=8.5, rgb=MUTED, x=M + 8, w=W - 2 * M - 8, gap=0)
            doc.y += 6

    for m in data.get("model_eval") or []:
        doc.new_page()
        doc.heading("The AI model on its own (no rule check)", 16)
        doc.para(f"Run {m['run']}. The model reads each message; the tower only looks up the records "
                 "and dates it named, and the reading is compared with the expected outcome.")
        doc.table([("Set", 180, "l"), ("Incident type", 112, "r"), ("Records and dates", 112, "r"), ("Full output", 112, "r")],
                  [[name, f"{x['kinds_ok']}/{x['total']}", f"{x['fields_ok']}/{x['total']}",
                    (f"{x['output_ok']}/{x['total']}", _rate_rgb(x["output_ok"], x["total"]))] for name, x in m["suites"].items()])
    return doc.bytes()


def filename() -> str:
    return f"control-tower-test-summary-{time.strftime('%Y-%m-%d')}.pdf"


if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else filename()
    with open(out, "wb") as handle:
        handle.write(build())
    print(out)
