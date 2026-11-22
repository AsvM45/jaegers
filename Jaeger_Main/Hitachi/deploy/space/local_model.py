"""A stand-in for Ollama on hosts that cannot run it (a free Hugging Face Space).

Runs Qwen3 1.7B (the same Q4_K_M build Ollama serves as qwen3:1.7b) in-process with llama.cpp and
answers the two Ollama calls the tower makes, so the tower's code does not change. With GROQ_API_KEY
set, each call goes to Groq first (groq_client.py) and this model answers only when Groq cannot:

    GET  /api/tags   the model list (the tower checks the model is there)
    POST /api/chat   one chat turn: messages, an optional JSON schema ("format") the answer must
                     follow, optional tools, options temperature / seed / num_predict, think false

    python deploy/space/local_model.py           listens on 127.0.0.1:11434 (LOCAL_MODEL_PORT)
"""

from __future__ import annotations

import json
import os
import re
import threading
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

REPO = os.environ.get("LOCAL_MODEL_REPO", "unsloth/Qwen3-1.7B-GGUF")
FILE = os.environ.get("LOCAL_MODEL_FILE", "Qwen3-1.7B-Q4_K_M.gguf")
NAME = os.environ.get("TOWER_LLM_MODEL", "qwen3:1.7b")   # the name the tower asks for
CTX = int(os.environ.get("LOCAL_MODEL_CTX", "8192"))
PORT = int(os.environ.get("LOCAL_MODEL_PORT", "11434"))

_llm = None
_template = None
_lock = threading.Lock()   # one generation at a time: llama.cpp's model object is not thread-safe
_TOOL_CALL = re.compile(r"<tool_call>\s*(\{.*?\})\s*</tool_call>", re.S)
_THINK = re.compile(r"<think>.*?</think>\s*", re.S)


def load(path: str | None = None) -> None:
    """Download the model from Hugging Face (cached after the first time) and load it."""
    global _llm, _template
    from llama_cpp import Llama
    import jinja2

    if path is None:
        from huggingface_hub import hf_hub_download
        path = hf_hub_download(REPO, FILE)
    _llm = Llama(model_path=path, n_ctx=CTX, n_threads=os.cpu_count() or 2, n_gpu_layers=-1, verbose=False)
    # The model's own chat template, rendered with thinking off (as Ollama does with think: false).
    source = _llm.metadata["tokenizer.chat_template"]
    env = jinja2.Environment(loader=jinja2.BaseLoader(), trim_blocks=True, lstrip_blocks=True)
    env.globals["raise_exception"] = lambda msg: (_ for _ in ()).throw(ValueError(msg))
    _template = env.from_string(source)


def _prompt(messages: list[dict], tools: list | None) -> str:
    msgs = []
    for m in messages:
        m = dict(m)
        if m.get("tool_calls"):
            # Ollama sends arguments as objects; the template accepts objects or strings.
            m["tool_calls"] = [{"type": "function", "function": c.get("function", c)} for c in m["tool_calls"]]
        m.setdefault("content", "")
        msgs.append(m)
    return _template.render(messages=msgs, tools=tools or None, add_generation_prompt=True, enable_thinking=False)


def chat(body: dict) -> dict:
    """One /api/chat request -> Ollama's reply shape. Groq first when a key is set (fast), then the
    model on this machine. Without a local model loaded (GROQ_ONLY=1, for tests), Groq or an error."""
    import groq_client

    if groq_client.enabled():
        while True:
            try:
                return groq_client.answer(body)
            except groq_client.GroqBusy:
                if _llm is not None:
                    break
                # Groq only (tests): wait for a model's allowance instead of failing the reading.
                import time
                time.sleep(min(90.0, groq_client.next_free() + 0.5))
    return _local_chat(body)


def _local_chat(body: dict) -> dict:
    from llama_cpp.llama_grammar import LlamaGrammar

    opts = body.get("options") or {}
    tools = body.get("tools")
    prompt = _prompt(body.get("messages") or [], tools)
    fmt = body.get("format")
    grammar = None
    if isinstance(fmt, dict):
        grammar = LlamaGrammar.from_json_schema(json.dumps(fmt), verbose=False)
    elif fmt == "json":
        grammar = LlamaGrammar.from_json_schema(json.dumps({"type": "object"}), verbose=False)
    with _lock:
        out = _llm.create_completion(
            prompt, grammar=grammar, max_tokens=int(opts.get("num_predict") or 1024),
            temperature=float(opts.get("temperature", 0)), seed=int(opts.get("seed", 7)),
            stop=["<|im_end|>", "<|endoftext|>"],
        )
    text = _THINK.sub("", out["choices"][0]["text"]).strip()
    message = {"role": "assistant", "content": text}
    if tools:
        calls = []
        # The tags are special tokens that llama.cpp may leave out of the text: then each call is a
        # bare {"name", "arguments"} object on its own line.
        found = _TOOL_CALL.findall(text) or [ln for ln in text.splitlines() if ln.strip().startswith("{") and '"name"' in ln]
        for raw in found:
            try:
                call = json.loads(raw)
            except json.JSONDecodeError:
                continue
            args = call.get("arguments") or {}
            if isinstance(args, str):
                try:
                    args = json.loads(args)
                except json.JSONDecodeError:
                    args = {}
            calls.append({"id": uuid.uuid4().hex[:8], "function": {"name": call.get("name", ""), "arguments": args}})
        if calls:
            message = {"role": "assistant", "content": "", "tool_calls": calls}
    return {"model": body.get("model", NAME), "message": message, "done": True}


class _Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):   # quiet: the tower logs what matters
        pass

    def _send(self, code: int, obj: dict) -> None:
        data = json.dumps(obj).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        if self.path.startswith("/api/tags"):
            return self._send(200, {"models": [{"name": NAME, "model": NAME}]})
        self._send(404, {"error": "not found"})

    def do_POST(self):
        if not self.path.startswith("/api/chat"):
            return self._send(404, {"error": "not found"})
        try:
            body = json.loads(self.rfile.read(int(self.headers.get("Content-Length") or 0)) or b"{}")
            self._send(200, chat(body))
        except Exception as exc:   # report it; the tower treats a failed call as a failed reading
            self._send(500, {"error": str(exc)})


def serve(host: str = "127.0.0.1", port: int = PORT) -> ThreadingHTTPServer:
    """Start answering in a background thread; returns the server."""
    server = ThreadingHTTPServer((host, port), _Handler)
    server.daemon_threads = True
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server


if __name__ == "__main__":
    import sys
    if os.environ.get("GROQ_ONLY") != "1":
        load(sys.argv[1] if len(sys.argv) > 1 else None)
    serve()
    print(f"model ready on http://127.0.0.1:{PORT} as {NAME}", flush=True)
    threading.Event().wait()
