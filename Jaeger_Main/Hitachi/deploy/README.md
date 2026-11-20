# Deploying the control tower

Two ways to put the dashboard online. Both are free.

| | Hugging Face Spaces (recommended) | Render |
|---|---|---|
| AI model | Yes: Ollama with qwen3:1.7b runs inside the container | No: rule reader only (72/100 on the blind set, against 92/100 with the model) |
| Speed | About 10–20 s per event on the free CPU | Fast pages; every event read by rules |
| Sleeps | After 48 h without visitors; wakes in about a minute | After 15 min without visitors; wakes in about a minute |
| Data | Resets when the Space restarts or redeploys | Resets on every deploy or restart |

Visitors are asked for a password when `TOWER_PASSWORD` is set (any user name works).

## Hugging Face Spaces

1. Make a free account at huggingface.co.
2. Create an access token with **write** permission: huggingface.co/settings/tokens.
3. Create a Space: huggingface.co/new-space. Pick a name, **Docker** as the SDK, the **Blank** template,
   the free **CPU basic** hardware, and Public or Private.
4. In the Space, open **Settings → Variables and secrets** and add a **secret** named `TOWER_PASSWORD`
   with the password you will share.
5. From this folder (`Jaeger_Main/Hitachi`), push the app:

   ```sh
   deploy/push_to_space.sh https://huggingface.co/spaces/<your-user>/<space-name>
   ```

   When git asks, the user name is your Hugging Face user name and the password is the token from step 2.
6. The Space builds (about 10 minutes the first time: it installs Ollama and the model). Watch the
   **Logs** tab; it is ready when it shows `http://0.0.0.0:7860  (password required)`.
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
| `RUN_OLLAMA` | Start Ollama inside the container | 1 (Spaces), 0 (Render) |
| `OLLAMA_URL` | Where the AI model is | http://localhost:11434 |

On a laptop nothing changes: `python start.py` and the desktop app still serve on 127.0.0.1 only.
