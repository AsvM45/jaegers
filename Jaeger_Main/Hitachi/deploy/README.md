# Deploying the control tower

Two ways to put the dashboard online. Both are free.

| | Hugging Face Spaces (recommended) | Render |
|---|---|---|
| AI model | Yes: Qwen3 1.7B runs inside the Space (llama.cpp) | No: rule reader only (72/100 on the blind set, against 92/100 with the model) |
| Speed | About 10–20 s per event on the free CPU | Fast pages; every event read by rules |
| Sleeps | After 48 h without visitors; wakes in about 1–2 minutes | After 15 min without visitors; wakes in about a minute |
| Data | Each visitor has their own events (a browser cookie names the workspace); all reset when the Space restarts or redeploys | Resets on every deploy or restart |

Visitors are asked for a password when `TOWER_PASSWORD` is set (any user name works).

On the Space (`TOWER_WORKSPACES=1`), each visitor starts fresh: no events handled and no tests run.
They can run the demo, add events, run the tests (the demo events, graded with the AI model) and reset
either, without affecting anyone else. One test run goes at a time; a second visitor is asked to try
again in a minute. A closed tab's workspace is deleted about 10 minutes later. The blind test sets, the
saved runs and the logs on this computer are not pushed to the Space and never shown there.

## Hugging Face Spaces

1. Make a free account at huggingface.co.
2. Create an access token with **write** permission: huggingface.co/settings/tokens.
3. Create a Space: huggingface.co/new-space. Pick a name, **Gradio** as the SDK (Docker needs paid
   hardware), the **Blank** template, the free **CPU basic** hardware (or **ZeroGPU** if that is the
   only free choice: the model runs on its CPU and uses no GPU quota), and Public or Private.
   The app does not use a Gradio page; the Space only runs `app.py`, which starts the dashboard.
4. In the Space, open **Settings → Variables and secrets** and add a **secret** named `TOWER_PASSWORD`
   with the password you will share, and a **secret** named `GROQ_API_KEY` with your Groq key
   (console.groq.com → API Keys). With the key, events are read by Groq in a second or two, spread over
   several Groq models; the Space's own model answers whenever Groq is busy or unreachable. Without
   it, the Space's own model reads everything (slower: minutes per demo).
5. From this folder (`Jaeger_Main/Hitachi`), push the app:

   ```sh
   deploy/push_to_space.sh https://huggingface.co/spaces/<your-user>/<space-name>
   ```

   It builds the dashboard on your computer first (Node is needed), then pushes. When git asks, the user
   name is your Hugging Face user name and the password is the token from step 2.
6. The Space installs its packages (a few minutes the first time), then downloads the model from Hugging
   Face and loads it (under a minute). Watch the **Logs** tab; it is ready when it shows
   `AI model ready` and then `http://0.0.0.0:7860  (password required)`.
7. Share the direct link, `https://<your-user>-<space-name>.hf.space`, and the password. The direct link
   works better than the Space page, which shows the app inside a frame.

To update the deployed app later, run step 5 again.

## Render

1. Commit and push this repository to GitHub (it includes `render.yaml` at the top level).
2. In Render: **New → Blueprint**, pick the repository. It reads `render.yaml` and creates the service.
3. When asked, set `TOWER_PASSWORD`.
4. Render builds `Dockerfile.render` and gives you a `https://<name>.onrender.com` link.

To use the AI model from Render, set `OLLAMA_URL` to an Ollama server reachable from the internet.

## Settings

| Variable | What it does | Default in the images |
|---|---|---|
| `TOWER_PASSWORD` | Password every visitor must enter | none (open) |
| `PORT` | Port the dashboard listens on | 7860 (Render sets its own) |
| `TOWER_HOST` | Address the dashboard listens on | 0.0.0.0 |
| `TOWER_PUBLIC` | Accept actions from the public address | 1 |
| `RUN_OLLAMA` | Start Ollama inside a Docker image | 1 (Dockerfile), 0 (Render) |
| `GROQ_API_KEY` | Groq key: read events with Groq first (Space secret) | none |
| `GROQ_MODELS` | Groq models to spread calls over, comma-separated | openai/gpt-oss-20b, qwen/qwen3.8-27b |
| `TOWER_DEMO_EVENTS` | The given events the feed shows and Run the demo reads; the rest stay in the files, unshown | E-01,E-02,E-03,E-04,E-05,E-09 on the Space; all on a laptop |
| `OLLAMA_URL` | Where the AI model is | http://localhost:11434 (the Space runs its own there) |

On a laptop nothing changes: `python start.py` and the desktop app still serve on 127.0.0.1 only.
