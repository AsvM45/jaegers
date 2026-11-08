"""Small local LLM event reader (default Qwen3 0.6B), served by Ollama.

The model reads one message section and returns its incident kind plus the
exact phrases that name the plant, part, supplier, lot, shipment, and the two
dates. It never returns ids or computed dates: plain code resolves the
phrases through aliases.csv and the working-day calendar, and rejects any
phrase that does not appear verbatim in the text.

Setup:  ollama pull qwen3:0.6b   (Ollama must be running on localhost:11434)
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request

# Qwen3 0.6B (752M parameters, 4-bit, 522 MB): the smallest model that gets 14/16 incident kinds
# right, at ~3 s per call. Bigger models (Llama 3.2 1B, Qwen3 1.7B) pass more readings but give
# the same actions, because code verifies every reading. Override with TOWER_LLM_MODEL.
MODEL = os.environ.get("TOWER_LLM_MODEL", "qwen3:0.6b")
OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434")

KINDS = ("supplier_delay", "plant_outage", "quality_hold", "unconfirmed", "noise")
FIELDS = ("plant", "part", "supplier", "lot_id", "shipment_id", "start_date", "end_date")

# JSON schema passed to Ollama's 'format' option: the model must answer with exactly these keys,
# and 'kind' must be one of KINDS.
_SCHEMA = {
    "type": "object",
    "properties": {
        "kind": {"type": "string", "enum": list(KINDS)},
        **{name: {"type": "string"} for name in FIELDS},
        "reason": {"type": "string"},
    },
    "required": ["kind", *FIELDS, "reason"],
}

# Instructions for the model. It only labels the message and copies phrases; ids and dates are
# worked out by code.
_SYSTEM = """You read operations messages for Wacky Wheels Co., a carmaker with plants, parts suppliers and dealers.
Classify the message as exactly one kind:
- supplier_delay: a confirmed shipment of a part will arrive later than planned.
- plant_outage: a plant cannot build for a stated range of days.
- quality_hold: a part or lot is defective for vehicles built in a stated date range.
- unconfirmed: a rumor or vague report with no confirmed details or dates.
- noise: anything not about operations (brochures, prices, far-away weather).
Wording cues: "we're dark", "power failure", "lost production", "outage" mean plant_outage.
"waiting on", "can't make it", "new ETA", "delayed", "will now arrive" mean supplier_delay.
"quality alert", "faulty", "contamination", "suspect" mean quality_hold.
"rumor", "not confirmed", "someone mentioned" mean unconfirmed.

Then copy phrases from the message. Copy them EXACTLY as written. Never invent, translate or compute a value.
Use "" when the message does not say it.
- plant: words naming the plant (city, state or id).
- part: words naming the part.
- supplier: words naming the supplier.
- lot_id: a lot id such as LOT-0123.
- shipment_id: a shipment id such as SH-0123.
- start_date: supplier_delay = the original arrival date; plant_outage = the first day down; quality_hold = the first build date.
- end_date: supplier_delay = the new arrival date; plant_outage = the last day down; quality_hold = the last build date.
- reason: one short sentence on why you chose the kind.
Answer with JSON only."""

# One worked example (few-shot). The names are invented; if the model copies them into a real
# answer, the 'phrase must be in the message' check rejects them.
_EXAMPLE_IN = (
    "Heads up from Acme: the brake kits for Denver were due Tuesday Mar 9 "
    "but the truck broke down, new ETA next Thursday."
)
_EXAMPLE_OUT = {
    "kind": "supplier_delay",
    "plant": "Denver",
    "part": "brake kits",
    "supplier": "Acme",
    "lot_id": "",
    "shipment_id": "",
    "start_date": "Tuesday Mar 9",
    "end_date": "next Thursday",
    "reason": "A supplier says a part shipment will arrive late with an old and a new date.",
}


class LLMUnavailable(RuntimeError):
    """Ollama is not reachable or the model is not pulled."""


class LLMReader:
    """Thin client for one structured extraction per message section."""

    def __init__(self, model: str = MODEL, url: str = OLLAMA_URL, timeout: float = 60.0):
        self.model = model
        self.url = url.rstrip("/")
        self.timeout = timeout
        self.calls = 0

    # One HTTP call to the local Ollama server per message section. Temperature 0 and a fixed seed
    # give the same answer every run.
    def extract(self, section: str) -> dict:
        """Ask the model for kind + phrases. Returns every key as a stripped string ("" if absent).

        Raises LLMUnavailable when Ollama cannot be reached, and ValueError when the answer is
        not usable JSON. The caller (understand.py) treats both as "use the rule reader".
        """
        payload = {
            "model": self.model,
            "stream": False,
            "format": _SCHEMA,
            "options": {"temperature": 0, "seed": 7},
            "messages": [
                {"role": "system", "content": _SYSTEM},
                {"role": "user", "content": _EXAMPLE_IN},
                {"role": "assistant", "content": json.dumps(_EXAMPLE_OUT)},
                {"role": "user", "content": section},
            ],
        }
        if self.model.startswith("qwen3"):
            payload["think"] = False  # Qwen3 thinks by default; extraction does not need it.
        request = urllib.request.Request(
            f"{self.url}/api/chat",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                body = json.loads(response.read().decode("utf-8"))
        except (urllib.error.URLError, TimeoutError, ConnectionError) as exc:
            raise LLMUnavailable(f"Ollama at {self.url} with {self.model}: {exc}") from exc
        self.calls += 1
        # The schema constrains the format, but a small model can still break it; check anyway.
        content = body.get("message", {}).get("content", "")
        try:
            out = json.loads(content)
        except json.JSONDecodeError as exc:
            raise ValueError(f"model returned non-JSON: {content[:200]!r}") from exc
        if out.get("kind") not in KINDS:
            raise ValueError(f"model returned unknown kind {out.get('kind')!r}")
        return {key: str(out.get(key) or "").strip() for key in ("kind", *FIELDS, "reason")}
