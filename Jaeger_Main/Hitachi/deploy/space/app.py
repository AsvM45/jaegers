"""Hugging Face Space entry point (Gradio SDK; CPU basic or ZeroGPU hardware): the control tower with the AI model.

The Space runs `python app.py`. This loads Qwen3 1.7B from Hugging Face into a local stand-in for
Ollama (deploy/space/local_model.py), then starts the tower's own dashboard server on port 7860.
No Gradio page is used; the Space only needs something answering on 7860.
"""

import os
import runpy
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "deploy", "space"))

os.environ.setdefault("TOWER_PUBLIC", "1")
os.environ.setdefault("TOWER_WORKSPACES", "1")   # each visitor gets their own events (tower/ui/event_desk.py)
# Online, the feed and the demo have 6 given events, one of each kind; the other 9 stay in the files, unshown.
os.environ.setdefault("TOWER_DEMO_EVENTS", "E-01,E-02,E-03,E-04,E-05,E-09")
os.environ.setdefault("TOWER_LLM_MODEL", "qwen3:1.7b")
os.environ.setdefault("TOWER_TOOL_MODEL", "qwen3:1.7b")
os.environ.setdefault("TOWER_RUN_PARALLEL", "1")   # two free CPUs: one event at a time is as fast
os.environ.setdefault("OLLAMA_URL", "http://127.0.0.1:11434")

import local_model  # noqa: E402

# On ZeroGPU hardware the Space checks that the app has a GPU function before it starts. The model runs
# on the Space's CPU (always available, no daily GPU quota), so this one is never called.
try:
    import spaces

    @spaces.GPU
    def _unused_gpu_slot():
        return None

    # The Space learns about GPU functions when a Gradio page starts. No Gradio page starts here (the
    # tower serves its own dashboard), so send that startup report directly.
    from spaces.zero.lifecycle import zerogpu_mode_enabled, zerogpu_startup
    if zerogpu_mode_enabled():
        zerogpu_startup()
        print("ZeroGPU startup reported", flush=True)
except ImportError:
    pass

t0 = time.time()
print("loading the AI model…", flush=True)
local_model.load()
local_model.serve()
print(f"AI model ready after {time.time() - t0:.0f}s", flush=True)

sys.argv = ["tower.ui.server", "--host", "0.0.0.0", "--port", os.environ.get("PORT", "7860")]
runpy.run_module("tower.ui.server", run_name="__main__")
