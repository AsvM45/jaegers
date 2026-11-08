# Wacky Wheels control tower

A local operations control tower for Wacky Wheels Co., a just-in-time automaker. One coordinating agent and three specialists read an event feed, trace each incident through the company knowledge graph, and apply the policy handbook through the enterprise tools. Noise is left alone. Unconfirmed reports go to a human.

The feed is Monday 8 March 2027. Everything runs on a laptop: Python standard library, optional [Ollama](https://ollama.com) for the reader, and a dashboard on `http://127.0.0.1:8080`.

## Quick start

From this folder (`Jaeger_Main/Hitachi`):

```bash
python start.py
```

That runs the tower on the 15 given events, the test suites, and the ontology export, then opens the dashboard. If Ollama is running with `qwen3:0.6b` pulled, the LLM reader is used and every reading is checked by the rule reader. Otherwise the rule reader runs alone.

```bash
python start.py --rules          # rule reader only, about 5 seconds
python start.py --serve-only     # dashboard on the results already on disk
python start.py --no-browser     # do not open a tab
python start.py --port 9000
python start.py --model-test     # also score the LLM reader on its own
```

Python 3.10 or newer. No pip packages.

## Run it in pieces

```bash
ollama pull qwen3:0.6b && ollama serve          # optional
python -m tower.run --notify dry-run            # runs/run1/  (Overview, Event feed)
python tests/run_given.py                       # runs/given/
python tests/run_cases.py                       # runs/tests/  (100 generated cases)
python -m tower.ontology                        # runs/ontology/
python -m tower.ui.server                       # http://127.0.0.1:8080
```

`--reader` on the test scripts is `rules`, `llm`, or `both`. Another model: `TOWER_LLM_MODEL=qwen3:1.7b`.

A live channel feed (Gmail, Outlook, Slack, Teams, and outbound notices) is documented in [tower/channels/README.md](tower/channels/README.md).

## Dashboard

| Page | What it shows |
|---|---|
| Overview | Events, tool calls, escalations, test pass rate, the agent team |
| Event feed | How each message was read, the graph path, and every tool call |
| Tests | Pass rate by suite and case, expected versus actual |
| Knowledge graph | Company records and the paths an event traced |
| Logs | `start.py` output, the action log, and test history |
| Guide | How to run the tower and what each page reads |

The chip beside search shows the reader and how fresh the data is.

Rebuild the React UI after changing `tower/ui/web`:

```bash
cd tower/ui/web && npm install && npm run build
```

`npm run dev` hot-reloads on port 5173 and proxies `/api` to the Python server (`python start.py --serve-only`). `cd desktop && npm start` opens the same dashboard in Electron.

## How a message is handled

1. **Read.** Qwen3 0.6B (or the rule reader) turns the text into incidents. Quoted phrases must appear in the message. A failed check falls back to the rules, and the trace says why.
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
tests/                 given, generated, held-out, stress, and accuracy suites
Data/                  events, handbook, and company tables
runs/                  traces, action logs, and reports
```

Company tables, `policy_handbook.md`, and `enterprise.py` are the source of truth. Event ids are never an answer key.
