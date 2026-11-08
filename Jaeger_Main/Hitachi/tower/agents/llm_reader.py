"""Small local LLM event reader (default Qwen2.5 0.5B), served by Ollama.

The model reads one message section and returns its incident kind plus the
exact phrases that name the plant, part, supplier, lot, shipment, and the two
dates. It never returns ids or computed dates: plain code resolves the
phrases through aliases.csv and the working-day calendar, and rejects any
phrase that does not appear verbatim in the text.

Setup:  ollama pull qwen2.5:0.5b   (Ollama must be running on localhost:11434)
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request

# Qwen2.5 0.5B (494M parameters, 397 MB on disk): the smallest model that still passes the 15
# given events. On its own it fills few fields, so a checked reading is used only when it matches
# the rule reader; otherwise the rules decide. Override with TOWER_LLM_MODEL.
MODEL = os.environ.get("TOWER_LLM_MODEL", "qwen3:1.7b")
OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434")
# The model that investigates with lookup tools when a reading has gaps. Tool calling is harder
# than reading, so it is a step up from the reader; it only runs on the few sections that need it.
TOOL_MODEL = os.environ.get("TOWER_TOOL_MODEL", "qwen3:1.7b")
MAX_LOOKUPS = 6

_INVESTIGATE_SYSTEM = """You help read an operations message for Wacky Wheels Co., a carmaker.
The message was read as a {kind}, but something it needs is missing or unclear: {problem}.
Use the tools to find the missing records or dates in the company tables. Search names with search_records
when a name is unfamiliar or misspelled, then use lookup with the ids it returns. Use as few calls as you can.
When you have what is needed, or the tables cannot settle it, stop calling tools and say in one sentence what you found."""

KINDS = ("supplier_delay", "plant_outage", "quality_hold", "unconfirmed", "noise")
FIELDS = ("plant", "part", "supplier", "lot_id", "shipment_id", "start_date", "end_date")

# JSON schema passed to Ollama's 'format' option: the model must answer with exactly these keys,
# and 'kind' must be one of KINDS.
# "reason" comes first and must be a real sentence: the model explains what the message says and
# why, before it labels it (the docx asks for a reason behind every decision).
_SCHEMA = {
    "type": "object",
    "properties": {
        "reason": {"type": "string", "minLength": 25},
        "kind": {"type": "string", "enum": list(KINDS)},
        **{name: {"type": "string"} for name in FIELDS},
    },
    "required": ["reason", "kind", *FIELDS],
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
How each kind is usually worded:
- plant_outage: a plant or line is down, dark, offline, halted, shut down or cannot build; an outage or power failure.
- supplier_delay: a delivery is late, delayed, slipping or postponed; a new or revised ETA or arrival date.
- quality_hold: parts are defective, faulty, contaminated, cracked or out of spec; a lot to hold or a recall.
- unconfirmed: hearsay or hedging (heard, might, apparently, rumor, not confirmed) about a possible problem.

Then copy phrases from the message. Copy names EXACTLY as written. Never invent a name, id or date.
Use "" when the message does not say it.
- plant: words naming the plant (city, state or id).
- part: words naming the part.
- supplier: words naming the supplier.
- lot_id: a lot id such as LOT-0123.
- shipment_id: a shipment id such as SH-0123.
- start_date: supplier_delay = the original arrival date; plant_outage = the first day down; quality_hold = the first build date.
- end_date: supplier_delay = the new arrival date; plant_outage = the last day down, or the day work resumes if that is all it says; quality_hold = the last build date.
Copy each date as written. A day written without a month ("the 24th") may be given with its month ("March 24").
- reason (answer this first): one or two sentences saying what the message reports and why that makes it this kind, or why it is noise or unconfirmed.
Answer with JSON only."""

# One worked example (few-shot). The names are invented; if the model copies them into a real
# answer, the 'phrase must be in the message' check rejects them.
_EXAMPLE_IN = (
    "Heads up from Acme: the brake kits for Denver were due Tuesday Mar 9 "
    "but the truck broke down, new ETA next Thursday."
)
_EXAMPLE_OUT = {
    "reason": "A supplier says a part shipment will arrive late, with the original and the new date, so it is a supplier delay.",
    "kind": "supplier_delay",
    "plant": "Denver",
    "part": "brake kits",
    "supplier": "Acme",
    "lot_id": "",
    "shipment_id": "",
    "start_date": "Tuesday Mar 9",
    "end_date": "next Thursday",
}


# --- Two-step reading -------------------------------------------------------------------------
# Step 1 asks only what kind of event a section is and why. Step 2 (real incidents only) asks for
# the records and dates that kind needs, as a choice among candidates code found in the message
# and the tables: the answer format only allows those options, so the model cannot invent a name,
# an id or a date, and it never has to spell a date or an id itself.

_CLASSIFY_SYSTEM = """You read operations messages for Wacky Wheels Co., a carmaker with plants, parts suppliers and dealers.
Decide what the message reports, by its meaning (people word things in many different ways):
- supplier_delay: a delivery of parts will arrive later than planned (a new date replaces the planned one).
- plant_outage: a plant cannot build for some days (any cause).
- quality_hold: parts, a part lot or the vehicles built with them over some dates are defective or suspect and must be held.
- unconfirmed: a possible problem that nobody has confirmed (hearsay, guesses, vague reports without specifics).
- noise: not about the company's deliveries, plants or part quality (announcements, questions, news elsewhere).
First write the reason: one or two sentences on what the message says and why that makes it this kind.
Answer with JSON only."""

# The same definitions plus the phrasing hints the one-step prompt already had (written before the
# held-out sets, and unchanged so those sets stay unbiased). They are hints to the model about
# meaning, not a word list: nothing in code matches them.
_CLASSIFY_HINTS = """
Examples of how each kind may be phrased (there are many other ways):
- plant_outage: a plant or line is down, dark, offline, halted, shut down or cannot build; an outage or power failure.
- supplier_delay: a delivery is late, delayed, slipping or postponed; a new or revised ETA or arrival date.
- quality_hold: parts are defective, faulty, contaminated, cracked or out of spec; a lot to hold or a recall.
- unconfirmed: hearsay or hedging (heard, might, apparently, rumor, not confirmed) about a possible problem.
"""
if os.environ.get("TOWER_CLASSIFY_HINTS", "1") == "1":
    _CLASSIFY_SYSTEM = _CLASSIFY_SYSTEM.replace("First write the reason", _CLASSIFY_HINTS.strip() + "\nFirst write the reason")

_CLASSIFY_SCHEMA = {
    "type": "object",
    "properties": {
        "reason": {"type": "string", "minLength": 25},
        "kind": {"type": "string", "enum": list(KINDS)},
    },
    "required": ["reason", "kind"],
}

# Step 2: the roles each kind needs, with what each role means. The keys are the JSON fields.
ROLES = {
    "supplier_delay": {
        "shipment": ("shipment", "the shipment that is late"),
        "supplier": ("supplier", "the supplier sending the parts"),
        "part": ("part", "the part being delivered"),
        "plant": ("plant", "the plant receiving the parts"),
        "original_date": ("date", "the date the delivery was originally due"),
        "new_date": ("date", "the new date the delivery will arrive"),
    },
    "plant_outage": {
        "plant": ("plant", "the plant that cannot build"),
        "first_day": ("date", "the first day the plant cannot build"),
        "last_day_down": ("date", "the last day the plant cannot build, if the message gives it"),
        "restart_day": ("date", "the day the plant builds again, only if the message gives a date for it"),
    },
    "quality_hold": {
        "lot": ("lot", "the defective part lot, if one is named"),
        "part": ("part", "the defective part"),
        "supplier": ("supplier", "the supplier of the defective part"),
        "plant": ("plant", "the plant that built with the part"),
        "first_build_date": ("date", "the first build date affected"),
        "last_build_date": ("date", "the last build date affected"),
    },
}

_FILL_SYSTEM = """You read operations messages for Wacky Wheels Co. You are told what kind of event the message reports.
For each field, pick the option id that the message means, using the descriptions. The options were found in the message and the company records.
Answer none when the message does not say it. Never pick an option just because it is listed.
Answer with JSON only."""


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
    def extract(self, section: str, previous: dict | None = None, problem: str | None = None) -> dict:
        """Ask the model for kind + phrases. Returns every key as a stripped string ("" if absent).

        With previous and problem, this is the one retry: the model sees its last answer and why it
        failed the checks ("end_date 'March 25th' is not a date in the message") and answers again.

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
        if previous is not None:
            payload["messages"] += [
                {"role": "assistant", "content": json.dumps(previous)},
                {"role": "user", "content": (
                    f"That answer does not check out: {problem}. Read the message again and answer with "
                    "corrected JSON. Copy names and dates from the message; never invent one.")},
            ]
        return self._post(payload, check_kind=True, keys=("kind", *FIELDS, "reason"))

    def classify(self, section: str) -> dict:
        """Step 1: {"kind", "reason"} for one message section."""
        payload = {
            "model": self.model, "stream": False, "format": _CLASSIFY_SCHEMA,
            "options": {"temperature": 0, "seed": 7},
            "messages": [{"role": "system", "content": _CLASSIFY_SYSTEM}, {"role": "user", "content": section}],
        }
        return self._post(payload, check_kind=True, keys=("kind", "reason"))

    def investigate(self, section: str, kind: str, problem: str, lookups, max_calls: int = MAX_LOOKUPS) -> str:
        """Let the model call the lookup tools (tower.agents.lookup_tools) to fill a gap. Runs at most
        max_calls tool calls; returns the model's one-line finding. Records and dates the tools
        returned are kept on `lookups` for the next fill."""
        from tower.agents.lookup_tools import SCHEMAS

        messages = [
            {"role": "system", "content": _INVESTIGATE_SYSTEM.format(kind=kind.replace("_", " "), problem=problem)},
            {"role": "user", "content": section},
        ]
        used = 0
        while True:
            payload = {"model": self.model, "stream": False, "messages": messages,
                       "options": {"temperature": 0, "seed": 7}}
            if used < max_calls:
                payload["tools"] = SCHEMAS
            reply = self._chat(payload)
            calls = reply.get("tool_calls") or []
            if not calls or used >= max_calls:
                return (reply.get("content") or "").strip()
            messages.append(reply)
            for call in calls[: max_calls - used]:
                fn = call.get("function", {})
                args = fn.get("arguments") or {}
                if isinstance(args, str):
                    try:
                        args = json.loads(args)
                    except json.JSONDecodeError:
                        args = {}
                messages.append({"role": "tool", "content": lookups.call(fn.get("name", ""), args)})
                used += 1

    def _chat(self, payload: dict) -> dict:
        """One raw /api/chat call; returns the reply message."""
        if self.model.startswith("qwen3"):
            payload["think"] = False
        request = urllib.request.Request(f"{self.url}/api/chat", data=json.dumps(payload).encode("utf-8"),
                                         headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                body = json.loads(response.read().decode("utf-8"))
        except (urllib.error.URLError, TimeoutError, ConnectionError) as exc:
            raise LLMUnavailable(f"Ollama at {self.url} with {self.model}: {exc}") from exc
        self.calls += 1
        return body.get("message", {})

    def fill(self, section: str, kind: str, options: dict[str, list[tuple[str, str]]],
             previous: dict | None = None, problem: str | None = None, findings: str = "") -> dict:
        """Step 2: pick the records and dates a `kind` needs. options maps a role type ("plant",
        "part", "supplier", "lot", "shipment", "date") to the labels code found. The answer
        format only allows those labels or "". With previous/problem, this is the one retry."""
        roles = ROLES[kind]
        props = {name: {"type": "string", "enum": [*(v for v, _ in options.get(rtype, [])), "none"]}
                 for name, (rtype, _) in roles.items()}
        required = list(roles)
        schema = {"type": "object", "properties": props, "required": required}
        lines = [f"Kind of event: {kind}.", "",
                 "Fields (answer each with an option id, or none when the message does not say it):"]
        for name, (rtype, meaning) in roles.items():
            shown = [label for _, label in options.get(rtype, [])]
            lines.append(f"- {name}: {meaning}. Options: " + ("; ".join(shown) if shown else "none"))
        if findings:
            lines += ["", "What a lookup in the company tables found: " + findings]
        lines += ["", "Message:", section]
        messages = [{"role": "system", "content": _FILL_SYSTEM}, {"role": "user", "content": "\n".join(lines)}]
        if previous is not None:
            messages += [
                {"role": "assistant", "content": json.dumps(previous)},
                {"role": "user", "content": f"That answer does not check out: {problem}. Read the message again and answer again."},
            ]
        payload = {"model": self.model, "stream": False, "format": schema,
                   "options": {"temperature": 0, "seed": 7}, "messages": messages}
        out = self._post(payload, check_kind=False, keys=tuple(required))
        return {k: ("" if v == "none" else v) for k, v in out.items()}

    def _post(self, payload: dict, check_kind: bool, keys: tuple[str, ...]) -> dict:
        """One call to Ollama; returns the answer's keys as stripped strings ("" if absent)."""
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
        if check_kind and out.get("kind") not in KINDS:
            raise ValueError(f"model returned unknown kind {out.get('kind')!r}")
        return {key: str(out.get(key) or "").strip() for key in keys}
