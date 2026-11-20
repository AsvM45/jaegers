# Wacky Wheels control tower

A local operations control tower for Wacky Wheels Co., a just-in-time automaker. One coordinating agent and three specialists read an event feed, trace each incident through the company knowledge graph, and apply the policy handbook through the enterprise tools. Noise is left alone. Unconfirmed reports go to a human.

The feed is Monday 8 March 2027. Everything runs on a laptop: Python standard library, optional [Ollama](https://ollama.com) for the reader, and a dashboard on `http://127.0.0.1:8080`.

## Quick start

From this folder (`Jaeger_Main/Hitachi`):

```bash
python start.py
```

That runs the tower on the 15 given events, grades them, runs the failure checks, and exports the ontology, then opens the dashboard. If Ollama is running with `qwen3:1.7b` pulled, the model reads every message and code checks each reading against the tables; gaps are looked up, and anything still missing is escalated with a question. Otherwise the rule reader runs as the backup.

```bash
python start.py --rules          # rule reader only, about 5 seconds
python start.py --serve-only     # dashboard on the results already on disk
python start.py --no-browser     # do not open a tab
python start.py --port 9000
```

Python 3.10 or newer. No pip packages.

## Run it in pieces

```bash
ollama pull qwen3:1.7b && ollama serve          # optional: the reader and lookup model
python -m tower.run --notify dry-run            # runs/run1/  (Overview, Event center)
python tests/run_given.py                       # runs/given/  (the 15 given events)
python tests/test_failures.py                   # failed calls, missing info, model down (19 checks, no network)
python -m tower.ontology                        # runs/ontology/
python -m tower.ui.server                       # http://127.0.0.1:8080
```

`--reader` on `tests/run_given.py` is `rules`, `llm`, or `both`. Another model: `TOWER_LLM_MODEL=qwen3:8b`.

**Voice input (optional).** The Add events page can take a spoken message. It records in the page and transcribes on this laptop with Whisper; no audio leaves the machine.

```bash
brew install whisper-cpp          # macOS; elsewhere, build whisper.cpp and put whisper-cli on PATH
python -m tower.voice setup       # downloads the English model (148 MB) into models/whisper/
python -m tower.voice setup --multilingual   # only for voice languages other than English
```

The browser asks for the microphone the first time you press Voice. Settings shows whether it is allowed and whether the speech engine is ready.

A live channel feed (Gmail, Outlook, Slack, Teams, and outbound notices) is documented in [tower/channels/README.md](tower/channels/README.md).

## Dashboard

| Page | What it shows |
|---|---|
| Overview | Events, tool calls, escalations, test pass rate, the agent team |
| Event center | Opens on Results: charts and a table of what the tower did with each event (not graded). The Feed tab shows how each message was read, the graph path, and every tool call. Event run walks the feed live. Event add chats a new message into the feed. |
| Tests | The 15 given events: expected versus actual. Run tests grades them and shows each one as it finishes. |
| Knowledge graph | Company records and the paths an event traced |
| Logs | `start.py` output, the action log, and test history |
| Guide | How to run the tower and what each page reads |
| Settings | Theme (dark, light, system), text size, motion, formats, time zone, voice language, microphone check |

The chip beside search shows the reader and when the page last loaded the run. It reloads on its own when those files change.

**Languages.** Settings → Language translates the dashboard into English, 日本語, Español, Français, Deutsch, Português, 中文, 한국어 or हिन्दी. Event messages and the tower's reasoning stay as written. When you add UI text, wrap it in `tr("…")` and keep the translations in step:

```bash
cd tower/ui/web
npm run i18n          # what is not wrapped, missing or unused (also runs before every build)
npm run i18n:fill     # translate the missing strings with local Ollama (qwen3:8b); review the result
```

Rebuild the React UI after changing `tower/ui/web`:

```bash
cd tower/ui/web && npm install && npm run build
```

`npm run dev` hot-reloads on port 5173 and proxies `/api` to the Python server (`python start.py --serve-only`). `cd desktop && npm install && npm start` opens the same dashboard in Electron (it starts its own server with `python3`).

## How a message is handled

1. **Read.** Qwen2.5 0.5B (or the rule reader) turns the text into incidents. Quoted phrases must appear in the message. A checked reading is used only when it matches the rule reader; otherwise the rules decide, and the trace says why.
2. **Hand off.** Supply Chain Planner owns delays, outages, and slots. Quality Containment owns lots, stop-sale, and owner notices. Dealer and Customer Care owns one notice per dealer and loaners.
3. **Check.** The coordinator drops any planned call outside that agent's tools, then runs the rest. Only affected records change. A failed write is logged, not retried.
4. **Record.** `runs/run1/action_log.jsonl` and `traces.json` feed the dashboard.

Design notes: [DESIGN.md](DESIGN.md) and [DESIGN_CARD.md](DESIGN_CARD.md). The build log is [tower/PROGRESS.md](tower/PROGRESS.md).

## Layout

```
enterprise.py          company tools (in process)
enterprise_server.py   the same tools over HTTP (GET /events, POST /act)
start.py               one command: run, test, serve
tower/agents/          coordinator, reader, three specialists
tower/graph.py         knowledge graph over the company CSVs
tower/channels/        inbound mail and chat, outbound notices
tower/ui/              dashboard (React source in web/, served from dist/)
tests/                 the 15 given events graded against TC1–TC6 (run_given.py)
Data/                  events, handbook, and company tables
runs/                  traces, action logs, and reports
```

Company tables, `policy_handbook.md`, and `enterprise.py` are the source of truth. Event ids are never an answer key.
