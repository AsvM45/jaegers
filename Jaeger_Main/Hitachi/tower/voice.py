"""Local voice input: speech to text with whisper.cpp, on this machine. Standard library only.

    python -m tower.voice setup                 # check whisper-cli, download the English model (148 MB)
    python -m tower.voice setup --multilingual  # also the model for other languages (148 MB)
    python -m tower.voice status
    python -m tower.voice transcribe note.wav [--lang en]

whisper-cli comes from whisper.cpp (macOS: brew install whisper-cpp). The dashboard records the
microphone in the page and posts 16 kHz mono WAV to POST /api/voice/transcribe; no audio leaves
the laptop. Whisper is told the company's plant, supplier and part names, so it spells them the
way the tables do.

Overrides: TOWER_WHISPER_CLI (the binary), TOWER_WHISPER_DIR (where models live).
"""

from __future__ import annotations

import csv
import os
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import urllib.request

HITACHI = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODEL_DIR = os.environ.get("TOWER_WHISPER_DIR", os.path.join(HITACHI, "models", "whisper"))
MODELS = {"en": "ggml-base.en.bin", "multi": "ggml-base.bin"}
URL = "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/{}"
MAX_WAV = 8 * 1024 * 1024  # about four minutes of 16 kHz mono 16-bit audio
LANGUAGES = {"en": "English", "es": "Spanish", "fr": "French", "de": "German", "pt": "Portuguese",
             "ja": "Japanese", "zh": "Chinese", "ko": "Korean", "hi": "Hindi"}
_lock = threading.Lock()
_vocab: str | None = None
_warmed: set[str] = set()


def cli() -> str | None:
    return os.environ.get("TOWER_WHISPER_CLI") or shutil.which("whisper-cli")


def _model(lang: str) -> str | None:
    """The model file for a language: the English-only model for English when present."""
    picks = [MODELS["en"], MODELS["multi"]] if lang == "en" else [MODELS["multi"]]
    for name in picks:
        path = os.path.join(MODEL_DIR, name)
        if os.path.isfile(path) and os.path.getsize(path) > 1_000_000:
            return path
    return None


def status(lang: str = "en") -> dict:
    """What the dashboard needs to show the microphone button, or say how to set it up."""
    binary, model = cli(), _model(lang)
    problem, fix = "", ""
    if not binary:
        problem = "Voice input is not set up on this computer."
        fix = "brew install whisper-cpp"
    elif not model:
        problem = "The voice model for this language is not on this computer yet."
        fix = "python -m tower.voice setup" + ("" if lang == "en" else " --multilingual")
    if not problem and lang not in _warmed:
        # The first whisper run on a machine compiles its GPU kernels (about 20 s); do it now, in the
        # background, so the first real recording comes back in about a second.
        _warmed.add(lang)
        threading.Thread(target=_warm, args=(lang,), name="voice-warm", daemon=True).start()
    return {"ready": not problem, "problem": problem, "fix": fix, "engine": "whisper.cpp",
            "model": os.path.basename(model) if model else None, "languages": LANGUAGES}


def _silence(seconds: float = 1.0, rate: int = 16000) -> bytes:
    import struct

    data = b"\x00\x00" * int(seconds * rate)
    return (b"RIFF" + struct.pack("<I", 36 + len(data)) + b"WAVEfmt " + struct.pack("<IHHIIHH", 16, 1, 1, rate, rate * 2, 2, 16)
            + b"data" + struct.pack("<I", len(data)) + data)


def _warm(lang: str) -> None:
    try:
        transcribe(_silence(), lang, gate=False)
    except (RuntimeError, ValueError, OSError):
        _warmed.discard(lang)


def _vocabulary() -> str:
    """Names Whisper should expect, from the company tables, as its initial prompt."""
    global _vocab
    if _vocab is None:
        data = os.path.join(HITACHI, "Data", "hack_the_highway_package", "data")
        words: list[str] = []
        for name, column in (("plants", "city"), ("suppliers", "name"), ("parts", "name")):
            try:
                with open(os.path.join(data, f"{name}.csv"), encoding="utf-8") as handle:
                    words += [row[column].split(",")[0] for row in csv.DictReader(handle)]
            except (OSError, KeyError):
                continue
        _vocab = "Wacky Wheels operations. " + ", ".join(dict.fromkeys(words))[:700] + ". Shipment SH-0182, lot LOT-0191."
    return _vocab


# Whisper's markers for silence and noise, which are not words anyone said.
_NOISE = re.compile(r"\[[^\]]*\]|\((?:silence|music|noise|blank[^)]*)\)", re.I)


def _loudness(wav: bytes) -> float:
    """RMS of a 16-bit PCM WAV, 0..1. Whisper invents words ("you", "thank you") for silence, so a
    recording this quiet is treated as saying nothing."""
    import array
    import math

    at = wav.find(b"data", 12)
    pcm = array.array("h")
    pcm.frombytes(wav[at + 8: at + 8 + ((len(wav) - at - 8) // 2) * 2] if at > 0 else b"")
    if sys.byteorder == "big":
        pcm.byteswap()
    if not pcm:
        return 0.0
    return math.sqrt(sum(x * x for x in pcm[::4]) / len(pcm[::4])) / 32768


QUIET = 0.004  # about -48 dBFS: room noise, not speech


def transcribe(wav: bytes, lang: str = "en", gate: bool = True) -> str:
    """Text of a WAV recording ("" when it is silent). Raises ValueError for bad input,
    RuntimeError when whisper is not set up or fails."""
    if not wav.startswith(b"RIFF") or wav[8:12] != b"WAVE":
        raise ValueError("expected a WAV recording")
    if len(wav) > MAX_WAV:
        raise ValueError("the recording is too long (about four minutes at most)")
    lang = lang if lang in LANGUAGES else "en"
    if gate and _loudness(wav) < QUIET:
        return ""
    ready = status(lang)
    if not ready["ready"]:
        raise RuntimeError(ready["problem"])
    with _lock, tempfile.TemporaryDirectory() as tmp:
        audio, out = os.path.join(tmp, "audio.wav"), os.path.join(tmp, "text")
        with open(audio, "wb") as handle:
            handle.write(wav)
        command = [cli(), "-m", _model(lang), "-f", audio, "-l", lang, "-nt", "-np", "-otxt", "-of", out,
                   "--prompt", _vocabulary() if lang == "en" else ""]
        try:
            done = subprocess.run(command, capture_output=True, text=True, timeout=120)
        except subprocess.TimeoutExpired as exc:
            raise RuntimeError("transcription took too long") from exc
        if done.returncode != 0 or not os.path.exists(out + ".txt"):
            raise RuntimeError(f"whisper-cli failed: {(done.stderr or done.stdout).strip()[-300:]}")
        with open(out + ".txt", encoding="utf-8") as handle:
            text = handle.read()
    return re.sub(r"\s+", " ", _NOISE.sub(" ", text)).strip()


def setup(multilingual: bool = False) -> int:
    if not cli():
        print("whisper-cli was not found. Install whisper.cpp first (macOS: brew install whisper-cpp).")
        return 1
    print(f"whisper-cli: {cli()}")
    os.makedirs(MODEL_DIR, exist_ok=True)
    for key in ("en", "multi") if multilingual else ("en",):
        name = MODELS[key]
        path = os.path.join(MODEL_DIR, name)
        if os.path.isfile(path) and os.path.getsize(path) > 1_000_000:
            print(f"{name}: already downloaded")
            continue
        print(f"Downloading {name} (about 148 MB) to {MODEL_DIR} ...")
        part = path + ".part"
        with urllib.request.urlopen(URL.format(name), timeout=60) as response, open(part, "wb") as handle:
            shutil.copyfileobj(response, handle, 1 << 20)
        os.replace(part, path)
        print(f"{name}: done")
    state = status()
    print("Voice is ready." if state["ready"] else f"{state['problem']} Fix: {state['fix']}")
    return 0


if __name__ == "__main__":
    args = sys.argv[1:]
    if args[:1] == ["setup"]:
        sys.exit(setup("--multilingual" in args))
    if args[:1] == ["transcribe"] and len(args) >= 2:
        lang = args[args.index("--lang") + 1] if "--lang" in args else "en"
        with open(args[1], "rb") as wav:
            print(transcribe(wav.read(), lang))
        sys.exit(0)
    print(status())
