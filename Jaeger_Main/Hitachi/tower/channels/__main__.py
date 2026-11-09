"""Channel commands. Run from the Hitachi directory.

    python -m tower.channels check                       # config problems and missing secrets
    python -m tower.channels test --sink slack_ops       # send one test message through a sink
    python -m tower.channels pull  [--out runs/live/events.json]
    python -m tower.channels notify [--run runs/run1] [--mode dry-run|send]
    python -m tower.channels watch [--interval 60] [--reader rules|llm] [--mode dry-run|send] [--once]

`watch` is the live control tower: poll every enabled source, run each new message through the
same coordinator as the batch run, append to runs/live/{traces.json, action_log.jsonl}, and
dispatch what was done. The batch run in runs/run1 is never touched.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time

_HITACHI = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _HITACHI not in sys.path:
    sys.path.insert(0, _HITACHI)

from tower.channels.config import ChannelConfig  # noqa: E402
from tower.channels.dispatch import Dispatcher, build_messages, notify_run, summarize, write_outbox  # noqa: E402
from tower.channels.inbound import SOURCES  # noqa: E402
from tower.channels.outbound import SINKS, Message  # noqa: E402
from tower.channels.transport import ChannelError, Transport  # noqa: E402

DATA = os.path.join(_HITACHI, "Data", "hack_the_highway_package", "data")
LIVE = os.path.join(_HITACHI, "runs", "live")


# Every environment variable a source or sink config refers to (keys ending in _env).
def _env_names(cfg: dict) -> list[str]:
    return [v for k, v in cfg.items() if k.endswith("_env") and isinstance(v, str)]


def cmd_check(config: ChannelConfig, _args) -> int:
    """Print what is enabled and which secrets are missing. Exit 1 if the config has problems."""
    print(f"config: {config.path or '(none — copy tower/channels/channels.example.json to channels.json)'}")
    for title, table in (("sources", config.sources), ("sinks", config.sinks)):
        print(f"\n{title}:")
        if not table:
            print("  (none enabled)")
        for name, cfg in table.items():
            missing = [n for n in _env_names(cfg) if not os.environ.get(n)]
            state = "ready" if not missing else "missing env " + ", ".join(missing)
            print(f"  {name:22} {cfg.get('kind', '?'):12} {state}")
    print("\nroutes:")
    for route, value in config.routes.items():
        print(f"  {route:12} -> {', '.join(value['sinks']) or '(no sinks)'}")
    print(f"\nsafety: {json.dumps(config.safety)}")
    print("contacts: " + ", ".join(f"{k}={len(v)}" for k, v in config.contacts.items() if not k.startswith("_")))
    problems = config.problems()
    for p in problems:
        print(f"PROBLEM: {p}")
    return 1 if problems else 0


def cmd_test(config: ChannelConfig, args) -> int:
    """Send one fixed test message through one sink. Bypasses dispatch, so no ledger or cap."""
    if args.sink not in config.sinks:
        print(f"unknown or disabled sink {args.sink!r}; enabled: {', '.join(config.sinks) or 'none'}")
        return 2
    cfg = config.sinks[args.sink]
    msg = Message(route="ops", event_id="TEST", subject="Control tower connectivity test",
                  text="If you can read this, the control tower can reach this channel.",
                  to=args.to or list(config.safety.get("redirect_to") or cfg.get("to", [])),
                  facts={"Sink": args.sink, "Kind": cfg.get("kind")})
    try:
        print(json.dumps(SINKS[cfg["kind"]](args.sink, cfg, Transport()).send(msg)))
    except ChannelError as exc:
        print(f"FAILED: {exc}")
        return 1
    return 0


def pull(config: ChannelConfig, transport: Transport) -> tuple[list[dict], dict]:
    """Fetch from every enabled source. Returns (events, {event_id: source object})."""
    # One failing source is reported and skipped; the others still poll.
    events, owners = [], {}
    for name, cfg in config.sources.items():
        try:
            source = SOURCES[cfg["kind"]](name, cfg, transport)
            got = source.fetch()
        except (ChannelError, KeyError) as exc:
            print(f"  {name}: {exc}", file=sys.stderr)
            continue
        print(f"  {name}: {len(got)} message(s)")
        for event in got:
            owners[event["event_id"]] = source
        events.extend(got)
    events.sort(key=lambda e: e["received_at"])
    return events, owners


# A JSON file's content, or default when the file does not exist yet.
def _read_json(path, default):
    if os.path.isfile(path):
        with open(path, encoding="utf-8") as handle:
            return json.load(handle)
    return default


def _append_json(path, item):
    """Read the list, add one item, write to a temp file and rename, so a crash never leaves
    a truncated audit file."""
    rows = _read_json(path, []) + [item]
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as handle:
        json.dump(rows, handle, indent=2)
    os.replace(tmp, path)


def cmd_pull(config: ChannelConfig, args) -> int:
    """Fetch once and merge new events into a feed file that tower.run --events can process."""
    events, _ = pull(config, Transport())
    existing = _read_json(args.out, [])
    known = {e["event_id"] for e in existing}
    new = [e for e in events if e["event_id"] not in known]
    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as handle:
        json.dump(existing + new, handle, indent=2)
    print(f"{len(new)} new event(s) -> {args.out}  (run them: python -m tower.run --events {args.out} --out runs/live)")
    return 0


def cmd_notify(config: ChannelConfig, args) -> int:
    """Dispatch an existing run directory. Exit 1 if any delivery failed."""
    records = notify_run(args.run, DATA, args.mode, config)
    print(f"{args.mode}: {summarize(records)} -> {os.path.join(args.run, 'outbox.jsonl')}")
    return 1 if any(r["status"] == "failed" for r in records) else 0


def cmd_watch(config: ChannelConfig, args) -> int:
    """The live loop. Each new event: act, persist the audit files, notify, then acknowledge."""
    from enterprise import Enterprise, ToolError
    from tower.agents.coordinator import handle_event
    from tower.graph import WorldGraph
    from tower.run import _CallLog, _require_model

    if not config.sources:
        print("no sources enabled in channels.json; nothing to watch")
        return 2
    llm = None
    if args.reader == "llm":
        from tower.agents.llm_reader import MODEL, OLLAMA_URL, LLMReader
        _require_model(MODEL, OLLAMA_URL)
        llm = LLMReader()
    # Loaded once for the whole session. Enterprise keeps a separate world per event id, so
    # live events never affect each other, the same as in a batch run.
    graph = WorldGraph()
    enterprise = Enterprise(graph.data_dir)
    transport = Transport()
    dispatcher = Dispatcher(config, args.mode, transport, ledger_path=os.path.join(LIVE, "channels_sent.json"))
    os.makedirs(LIVE, exist_ok=True)
    paths = {k: os.path.join(LIVE, f) for k, f in
             (("events", "events.json"), ("traces", "traces.json"), ("log", "action_log.jsonl"), ("outbox", "outbox.jsonl"))}
    seen = {e["event_id"] for e in _read_json(paths["events"], [])}
    print(f"watching {', '.join(config.sources)} every {args.interval}s · reader={args.reader} · mode={args.mode}")
    while True:
        events, owners = pull(config, transport)
        new = [e for e in events if e["event_id"] not in seen]
        for event in new:
            records: list[dict] = []
            trace = handle_event(graph, _CallLog(enterprise, records), event, llm).to_dict()
            seen.add(event["event_id"])
            # Persist before notifying, so a crash never loses the audit trail of an action taken.
            _append_json(paths["events"], event)
            _append_json(paths["traces"], trace)
            with open(paths["log"], "a", encoding="utf-8") as h:
                h.writelines(json.dumps(r) + "\n" for r in records)
            out = dispatcher.dispatch(build_messages([trace], records, DATA, bool(config.safety.get("notify_noise"))))
            write_outbox(paths["outbox"], out, append=True)
            print(f"  {event['event_id']} [{event['channel']['kind']}] {trace['classification']}: "
                  f"{len(records)} call(s); notify {summarize(out)}")
            # Acknowledge last (mark read, react 👀), so a crash before this point leaves the
            # message unacknowledged at the provider.
            try:
                owners[event["event_id"]].acknowledge(event)
            except (ChannelError, ToolError) as exc:
                print(f"  ack failed for {event['event_id']}: {exc}", file=sys.stderr)
        if args.once:
            return 0
        time.sleep(args.interval)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="python -m tower.channels", description=__doc__.splitlines()[0])
    parser.add_argument("--config", help="channels.json path (default $TOWER_CHANNELS_CONFIG or tower/channels/channels.json)")
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("check")
    t = sub.add_parser("test")
    t.add_argument("--sink", required=True)
    t.add_argument("--to", nargs="*", help="addresses for an email sink")
    p = sub.add_parser("pull")
    p.add_argument("--out", default=os.path.join(LIVE, "inbox_events.json"))
    n = sub.add_parser("notify")
    n.add_argument("--run", default=os.path.join(_HITACHI, "runs", "run1"))
    n.add_argument("--mode", choices=("dry-run", "send"), default="dry-run")
    w = sub.add_parser("watch")
    w.add_argument("--interval", type=float, default=60)
    w.add_argument("--reader", choices=("llm", "rules"), default="rules")
    w.add_argument("--mode", choices=("dry-run", "send"), default="dry-run")
    w.add_argument("--once", action="store_true", help="poll once and exit")
    args = parser.parse_args(argv)
    config = ChannelConfig.load(args.config)
    return {"check": cmd_check, "test": cmd_test, "pull": cmd_pull, "notify": cmd_notify, "watch": cmd_watch}[args.cmd](config, args)


if __name__ == "__main__":
    sys.exit(main())
