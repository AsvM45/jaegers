"""Turn the tower's traces into messages and deliver them through the configured routes.

Routes:
    ops          one summary per real incident event (and, if enabled, per noise event)
    escalations  every `escalate` call: the human-in-the-loop hand-off
    dealers      one message per dealer per event: delayed orders and stop-sale VINs
    customers    one message per contacted owner/buyer

Guardrails, in order:
    1. Only calls the enterprise accepted (ok=true in action_log.jsonl) produce a message.
    2. mode "dry-run" (the default) writes outbox.jsonl and sends nothing.
    3. safety.redirect_to replaces every email address (contact or not), for demos and testing.
    4. Without a redirect, email sinks send only to addresses in the contacts file; no guessing.
    5. safety.max_messages caps one dispatch; the rest are recorded as skipped.
    6. A ledger of sent keys makes re-runs idempotent: nothing is delivered twice.
Dispatch never calls Enterprise and never writes action_log.jsonl.
"""

from __future__ import annotations

import csv
import json
import os
import time
from collections import defaultdict
from datetime import datetime

from tower.channels.config import ChannelConfig
from tower.channels.outbound import SINKS, Message
from tower.channels.transport import ChannelError, Transport

MODES = ("off", "dry-run", "send")
_PRIORITY = {"escalations": 0, "ops": 1, "dealers": 2, "customers": 3}


# ---------------------------------------------------------------- traces -> messages
def _pair_ok(traces: list[dict], log: list[dict]) -> dict[str, list[tuple[dict, bool | None]]]:
    """Attach ok/failed to each traced call. The coordinator logs calls in the order it traces
    them, so the i-th log line of an event is the i-th call. A count mismatch makes every
    call of that event unknown (None), which blocks per-recipient sends for it."""
    by_event = defaultdict(list)
    for line in log:
        by_event[line.get("event_id")].append(line)
    paired = {}
    for trace in traces:
        calls = trace.get("calls", [])
        lines = by_event.get(trace["event_id"], [])
        same = len(lines) == len(calls) and all(l.get("tool") == c.get("tool") for l, c in zip(lines, calls))
        paired[trace["event_id"]] = [(c, bool(l.get("ok")) if same else None) for c, l in
                                     zip(calls, lines if same else [{}] * len(calls))]
    return paired


def _names(data_dir: str, filename: str, key: str) -> dict[str, str]:
    """id -> display name from one company CSV. Read directly; the full graph is not needed."""
    path = os.path.join(data_dir, filename)
    if not os.path.isfile(path):
        return {}
    with open(path, newline="", encoding="utf-8") as handle:
        return {row[key]: row.get("name", "") for row in csv.DictReader(handle)}


def build_messages(traces: list[dict], log: list[dict], data_dir: str, include_noise: bool = False) -> list[Message]:
    """Turn traces (plus the log's ok flags) into Messages for the four routes, in event order."""
    dealers = _names(data_dir, "dealers.csv", "dealer_id")
    customers = _names(data_dir, "customers.csv", "customer_id")
    paired = _pair_ok(traces, log)
    out: list[Message] = []
    for trace in traces:
        eid = trace["event_id"]
        calls = paired.get(eid, [])
        accepted = [c for c, ok in calls if ok]
        failed = [c for c, ok in calls if ok is False]
        kinds = trace.get("classification", "")
        real = any(k in kinds for k in ("supplier_delay", "plant_outage", "quality_hold"))
        base_facts = {"Event": eid, "Source": trace.get("source", ""), "Received": trace.get("received_at", ""),
                      "Classification": kinds.replace("+", " + ")}

        for call, ok in calls:
            # Escalations go out even when the ok flag is unknown (None): telling a human about
            # an unclear report is always safe, unlike messaging a dealer or customer.
            if call["tool"] == "escalate" and ok is not False:
                out.append(Message(
                    route="escalations", event_id=eid, severity="warning",
                    subject=f"Needs a human: {eid} ({kinds.replace('_', ' ')})",
                    text=f"{call['args'].get('reason', '')}\n\nOriginal message:\n> {trace.get('text', '')[:1500]}",
                    facts=base_facts))

        if real or (include_noise and kinds):
            counts = defaultdict(int)
            for call in accepted:
                if call["tool"] != "escalate":
                    counts[call["tool"]] += 1
            facts = {**base_facts, **{tool: n for tool, n in counts.items()}}
            if failed:
                facts["Failed calls"] = len(failed)
            out.append(Message(
                route="ops", event_id=eid,
                severity="critical" if failed or not counts and real else ("warning" if real else "info"),
                subject=f"{eid}: {kinds.replace('_', ' ').replace('+', ' + ')}",
                text=trace.get("summary", ""), facts=facts))

        # Per-dealer: delayed customer orders and stop-sale VINs, one message per dealer.
        per_dealer: dict[str, dict] = defaultdict(lambda: {"orders": [], "vins": [], "notes": []})
        for call in accepted:
            args = call.get("args", {})
            if call["tool"] == "dealer.notify":
                d = per_dealer[args["dealer_id"]]
                d["orders"] += args.get("customer_order_ids", [])
                d["notes"].append(args.get("message", ""))
            elif call["tool"] == "dealer.stop_sale":
                per_dealer[args["dealer_id"]]["vins"] += args.get("vins", [])
        for dealer_id, d in sorted(per_dealer.items()):
            parts = [n for n in d["notes"] if n]
            if d["orders"]:
                parts.append("Delayed customer orders: " + ", ".join(d["orders"]))
            if d["vins"]:
                parts.append("STOP SALE: do not sell or deliver these vehicles: " + ", ".join(d["vins"]))
            out.append(Message(
                route="dealers", event_id=eid, severity="critical" if d["vins"] else "warning",
                subject=("Stop sale" if d["vins"] else "Order delay") + f" notice for {dealers.get(dealer_id) or dealer_id}",
                text="\n\n".join(parts), recipient_id=dealer_id, recipient_name=dealers.get(dealer_id),
                facts={"Event": eid, "Dealer": dealer_id, "Orders": len(d["orders"]), "Vehicles": len(d["vins"])}))

        for call in accepted:
            if call["tool"] == "crm.notify_customer":
                cid = call["args"]["customer_id"]
                out.append(Message(
                    route="customers", event_id=eid, severity="warning",
                    subject="An important notice about your Wacky Wheels vehicle",
                    text=call["args"].get("message", ""), recipient_id=cid, recipient_name=customers.get(cid),
                    facts={"Event": eid, "Customer": cid}))
    return out


# ---------------------------------------------------------------- delivery
class Dispatcher:
    """Deliver Messages through the routes in a ChannelConfig, applying the guardrails above.

    Sinks are built lazily, so dry-run never reads a secret. clock and sleep are injectable
    for tests of the throttle.
    """

    def __init__(self, config: ChannelConfig, mode: str = "dry-run", transport: Transport | None = None,
                 ledger_path: str | None = None, clock=time.time, sleep=time.sleep):
        if mode not in MODES:
            raise ValueError(f"mode must be one of {MODES}")
        self.config, self.mode = config, mode
        self.transport = transport or Transport()
        self.ledger_path = ledger_path
        self.sent = self._load_ledger()
        self._sinks: dict[str, object] = {}
        self._last_send: dict[str, float] = {}
        self.clock, self.sleep = clock, sleep

    # The ledger is a JSON list of "event|route|recipient|sink" keys already delivered.
    def _load_ledger(self) -> set[str]:
        if self.ledger_path and os.path.isfile(self.ledger_path):
            with open(self.ledger_path, encoding="utf-8") as handle:
                return set(json.load(handle))
        return set()

    def _save_ledger(self):
        """Persist the ledger. Only send mode delivers anything, so only it writes the file."""
        if self.ledger_path and self.mode == "send":
            os.makedirs(os.path.dirname(self.ledger_path), exist_ok=True)
            with open(self.ledger_path, "w", encoding="utf-8") as handle:
                json.dump(sorted(self.sent), handle, indent=0)

    def _sink(self, name: str):
        """Return the named sink, building it on first use. Config errors raise ChannelError."""
        if name not in self._sinks:
            cfg = self.config.sinks.get(name)
            if cfg is None:
                raise ChannelError(f"route names sink {name!r}, which is not defined under 'sinks'")
            cls = SINKS.get(cfg.get("kind"))
            if cls is None:
                raise ChannelError(f"sink {name!r} has unknown kind {cfg.get('kind')!r}; known: {sorted(SINKS)}")
            self._sinks[name] = cls(name, cfg, self.transport)
        return self._sinks[name]

    def _addresses(self, msg: Message, sink_cfg: dict) -> list[str]:
        """Email addresses for a message: contacts.<route>[recipient_id] for per-recipient routes,
        else the sink's fixed "to" list."""
        if msg.recipient_id:
            book = self.config.contacts.get(msg.route, {})
            found = book.get(msg.recipient_id) or []
            return [found] if isinstance(found, str) else list(found)
        return list(sink_cfg.get("to", []))

    def dispatch(self, messages: list[Message]) -> list[dict]:
        """Deliver (or, in dry-run, record) every message on every sink of its route.

        Returns one outbox record per (message, sink), whatever happened: sent, dry_run,
        failed, skipped or unrouted. A sink failure never stops the other deliveries.
        """
        if self.mode == "off":
            return []
        records, delivered = [], 0
        cap = int(self.config.safety.get("max_messages", 200))
        redirect = self.config.safety.get("redirect_to") or []
        stamp = datetime.now().replace(microsecond=0).isoformat()
        # Human hand-offs and ops summaries first, so bulk dealer/customer mail can never use up
        # max_messages before an escalation goes out. sorted() keeps event order within a route.
        for msg in sorted(messages, key=lambda m: _PRIORITY.get(m.route, 9)):
            route = self.config.routes.get(msg.route, {"sinks": []})
            if not route["sinks"]:
                records.append(self._record(stamp, msg, "-", [], "unrouted", f"no sinks on route {msg.route!r}"))
                continue
            for sink_name in route["sinks"]:
                sink_cfg = self.config.sinks.get(sink_name, {})
                email_like = SINKS.get(sink_cfg.get("kind")) and SINKS[sink_cfg["kind"]].needs_address
                to = self._addresses(msg, sink_cfg) if email_like else []
                note = ""
                if email_like and redirect:
                    # Demo/test mode: everything goes to the redirect inbox, contact or not.
                    note = "redirected" if to else "redirected (no contact on file)"
                    to = list(redirect)
                elif email_like and not to:
                    records.append(self._record(stamp, msg, sink_name, [], "skipped", "no contact on file"))
                    continue
                key = f"{msg.event_id}|{msg.route}|{msg.recipient_id or ''}|{sink_name}"
                if key in self.sent:
                    records.append(self._record(stamp, msg, sink_name, to, "skipped", "already sent (ledger)"))
                    continue
                if delivered >= cap:
                    records.append(self._record(stamp, msg, sink_name, to, "skipped", f"max_messages={cap} reached"))
                    continue
                delivered += 1
                if self.mode == "dry-run":
                    records.append(self._record(stamp, msg, sink_name, to, "dry_run", note))
                    continue
                try:
                    self._throttle(sink_name, sink_cfg)
                    msg.to = to
                    result = self._sink(sink_name).send(msg)
                    self.sent.add(key)
                    records.append(self._record(stamp, msg, sink_name, to, "sent", json.dumps(result)[:300]))
                except ChannelError as exc:
                    records.append(self._record(stamp, msg, sink_name, to, "failed", str(exc)[:500]))
        self._save_ledger()
        return records

    def _throttle(self, sink_name: str, sink_cfg: dict):
        """Wait so posts to one sink are at least min_interval_s apart (Slack allows ~1/s)."""
        gap = float(sink_cfg.get("min_interval_s", 0))
        if gap:
            wait = self._last_send.get(sink_name, 0) + gap - self.clock()
            if wait > 0:
                self.sleep(wait)
        self._last_send[sink_name] = self.clock()

    # One outbox.jsonl line. The UI's Notifications section renders these fields.
    def _record(self, stamp, msg: Message, sink: str, to: list[str], status: str, detail: str) -> dict:
        return {"at": stamp, "mode": self.mode, "event_id": msg.event_id, "route": msg.route, "sink": sink,
                "severity": msg.severity, "recipient_id": msg.recipient_id, "to": to,
                "subject": msg.subject, "text": msg.text[:2000], "status": status, "detail": detail}


# Batch runs rewrite the outbox; the live watcher appends one event at a time.
def write_outbox(path: str, records: list[dict], append: bool = False) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "a" if append else "w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")


def notify_run(run_dir: str, data_dir: str, mode: str = "dry-run", config: ChannelConfig | None = None,
               transport: Transport | None = None) -> list[dict]:
    """Read traces.json + action_log.jsonl from a run directory and dispatch them."""
    config = config or ChannelConfig.load()
    with open(os.path.join(run_dir, "traces.json"), encoding="utf-8") as handle:
        traces = json.load(handle)
    log = []
    with open(os.path.join(run_dir, "action_log.jsonl"), encoding="utf-8") as handle:
        log = [json.loads(line) for line in handle if line.strip()]
    messages = build_messages(traces, log, data_dir, include_noise=bool(config.safety.get("notify_noise")))
    dispatcher = Dispatcher(config, mode, transport, ledger_path=os.path.join(run_dir, "channels_sent.json"))
    records = dispatcher.dispatch(messages)
    if mode != "off":
        write_outbox(os.path.join(run_dir, "outbox.jsonl"), records)
    return records


# One-line status for the terminal, e.g. "26 dry_run, 610 skipped".
def summarize(records: list[dict]) -> str:
    by = defaultdict(int)
    for r in records:
        by[r["status"]] += 1
    return ", ".join(f"{n} {status}" for status, n in sorted(by.items())) or "nothing to dispatch"
