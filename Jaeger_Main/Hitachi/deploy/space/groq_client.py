"""Groq as the fast reader for the online Space: one Ollama /api/chat request -> Groq's chat API.

local_model.py calls answer(body) first when GROQ_API_KEY is set. Calls are spread over several
Groq models (each has its own free per-minute and per-day allowance). A model that answers "too
many requests" rests for as long as Groq asks; one that fails rests 30 s. When every model is
resting, answer() raises GroqBusy and the Space's own model answers instead.

    GROQ_API_KEY   the key (a Space secret; never in the repo)
    GROQ_MODELS    comma-separated model ids, tried in turn (default below)
"""

from __future__ import annotations

import copy
import itertools
import json
import os
import threading
import time
import urllib.error
import urllib.request

URL = os.environ.get("GROQ_URL", "https://api.groq.com/openai/v1/chat/completions")
KEY = os.environ.get("GROQ_API_KEY", "").strip()
MODELS = [m.strip() for m in os.environ.get(
    "GROQ_MODELS", "openai/gpt-oss-20b,qwen/qwen3.8-27b").split(",") if m.strip()]
TIMEOUT = float(os.environ.get("GROQ_TIMEOUT", "30"))

_lock = threading.Lock()
_rest_until: dict[str, float] = {}
_no_strict: set[str] = set()          # models that refused a strict JSON schema: use JSON object mode
_turn = itertools.count()
stats = {"groq": 0, "busy": 0, "errors": 0}


class GroqBusy(RuntimeError):
    """No Groq model can answer right now."""


def enabled() -> bool:
    return bool(KEY and MODELS)


def _strict(schema: dict) -> dict:
    """Groq's strict mode wants every field required and no extra fields; minLength is dropped."""
    out = copy.deepcopy(schema)

    def walk(node):
        if isinstance(node, dict):
            node.pop("minLength", None)
            if node.get("type") == "object" and isinstance(node.get("properties"), dict):
                node["required"] = list(node["properties"])
                node["additionalProperties"] = False
            for v in node.values():
                walk(v)
        elif isinstance(node, list):
            for v in node:
                walk(v)

    walk(out)
    return out


def _messages(body: dict, schema_hint: str | None) -> list[dict]:
    """Ollama messages -> OpenAI messages (tool calls carry ids; tool replies name the call)."""
    out, pending = [], []
    for m in body.get("messages") or []:
        role = m.get("role")
        if role == "assistant" and m.get("tool_calls"):
            calls = []
            for i, c in enumerate(m["tool_calls"]):
                fn = c.get("function", c)
                cid = c.get("id") or f"call_{len(out)}_{i}"
                args = fn.get("arguments")
                calls.append({"id": cid, "type": "function",
                              "function": {"name": fn.get("name", ""), "arguments": args if isinstance(args, str) else json.dumps(args or {})}})
            pending = [c["id"] for c in calls]
            out.append({"role": "assistant", "content": m.get("content") or "", "tool_calls": calls})
        elif role == "tool":
            out.append({"role": "tool", "content": m.get("content") or "", "tool_call_id": pending.pop(0) if pending else "call_0"})
        else:
            out.append({"role": role or "user", "content": m.get("content") or ""})
    if schema_hint:
        note = "Answer with one JSON object that matches this JSON schema exactly:\n" + schema_hint
        if out and out[0]["role"] == "system":
            out[0] = {**out[0], "content": out[0]["content"] + "\n\n" + note}
        else:
            out.insert(0, {"role": "system", "content": note})
    return out


def _request(model: str, body: dict) -> dict:
    opts = body.get("options") or {}
    fmt = body.get("format")
    strict = isinstance(fmt, dict) and model not in _no_strict
    payload = {
        "model": model,
        "messages": _messages(body, json.dumps(fmt) if isinstance(fmt, dict) and not strict else None),
        "temperature": float(opts.get("temperature", 0)),
        "seed": int(opts.get("seed", 7)),
    }
    limit = int(opts.get("num_predict") or 1024)
    if model.startswith("openai/gpt-oss"):
        payload["reasoning_effort"] = "low"
        payload["include_reasoning"] = False
        limit = max(limit, 1024)   # its (hidden) reasoning counts toward the limit
    elif model.startswith("qwen/"):
        payload["reasoning_effort"] = "none"
    payload["max_completion_tokens"] = limit
    if body.get("tools"):
        payload["tools"] = body["tools"]
    if strict:
        payload["response_format"] = {"type": "json_schema", "json_schema": {"name": "answer", "schema": _strict(fmt), "strict": True}}
    elif fmt:
        payload["response_format"] = {"type": "json_object"}
    req = urllib.request.Request(URL, data=json.dumps(payload).encode("utf-8"), headers={
        "Content-Type": "application/json", "Authorization": f"Bearer {KEY}", "User-Agent": "control-tower"})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as res:
        return json.loads(res.read().decode("utf-8"))


def _reply(data: dict, model: str) -> dict:
    msg = (data.get("choices") or [{}])[0].get("message") or {}
    message = {"role": "assistant", "content": (msg.get("content") or "").strip()}
    calls = []
    for c in msg.get("tool_calls") or []:
        fn = c.get("function") or {}
        args = fn.get("arguments") or "{}"
        try:
            args = json.loads(args) if isinstance(args, str) else args
        except json.JSONDecodeError:
            args = {}
        calls.append({"id": c.get("id"), "function": {"name": fn.get("name", ""), "arguments": args}})
    if calls:
        message = {"role": "assistant", "content": "", "tool_calls": calls}
    return {"model": model, "message": message, "done": True}


def _rest(model: str, seconds: float) -> None:
    with _lock:
        _rest_until[model] = max(_rest_until.get(model, 0), time.time() + seconds)


def next_free() -> float:
    """Seconds until some model stops resting (0 if one is free now)."""
    with _lock:
        return max(0.0, min(_rest_until.get(m, 0) for m in MODELS) - time.time())


def answer(body: dict) -> dict:
    """Answer with the next Groq model that is not resting. Raises GroqBusy when none can."""
    start = next(_turn)
    order = [MODELS[(start + i) % len(MODELS)] for i in range(len(MODELS))]
    for model in order:
        with _lock:
            if _rest_until.get(model, 0) > time.time():
                continue
        for attempt in range(2):
            try:
                data = _request(model, body)
                stats["groq"] += 1
                return _reply(data, model)
            except urllib.error.HTTPError as exc:
                detail = exc.read().decode("utf-8", "replace")[:300]
                if exc.code == 429:
                    wait = float(exc.headers.get("retry-after") or 20)
                    _rest(model, min(wait, 3600))
                    break
                if exc.code == 400 and isinstance(body.get("format"), dict) and model not in _no_strict and attempt == 0:
                    _no_strict.add(model)          # try again without the strict schema
                    continue
                stats["errors"] += 1
                print(f"groq {model}: HTTP {exc.code} {detail}", flush=True)
                _rest(model, 30)
                break
            except (urllib.error.URLError, TimeoutError, ConnectionError, json.JSONDecodeError) as exc:
                stats["errors"] += 1
                print(f"groq {model}: {exc}", flush=True)
                _rest(model, 30)
                break
    stats["busy"] += 1
    raise GroqBusy("every Groq model is resting")
