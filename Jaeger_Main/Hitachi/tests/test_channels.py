"""Tests for tower/channels. No network: every connector gets a FakeTransport.

    python -m unittest tests.test_channels -v      (from the Hitachi directory)
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import sys
import tempfile
import unittest

HITACHI = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HITACHI)

from tower.channels.config import ChannelConfig  # noqa: E402
from tower.channels.dispatch import Dispatcher, build_messages, notify_run  # noqa: E402
from tower.channels.inbound import TOWER_MARKER, GmailSource, OutlookSource, SlackSource, TeamsSource  # noqa: E402
from tower.channels.outbound import (GmailSink, Message, OutlookSink, PagerDutySink, SlackSink,  # noqa: E402
                                     TeamsSink, WebhookSink)
from tower.channels.transport import ChannelError  # noqa: E402

DATA = os.path.join(HITACHI, "Data", "hack_the_highway_package", "data")
RUN1 = os.path.join(HITACHI, "runs", "run1")


class FakeTransport:
    """Answers by URL substring; records every request."""

    def __init__(self, routes=None):
        self.routes = routes or {}
        self.calls = []

    def request(self, method, url, *, headers=None, json_body=None, form=None, raw=None):
        self.calls.append({"method": method, "url": url, "headers": headers or {}, "json": json_body,
                           "form": form, "raw": raw})
        if "oauth2" in url or "/token" in url:
            return {"access_token": "tok", "expires_in": 3600}
        for key, value in self.routes.items():
            if key in url:
                if isinstance(value, Exception):
                    raise value
                return value(url) if callable(value) else value
        return {"ok": True}


ENV = {"GOOGLE_CLIENT_ID": "id", "GOOGLE_CLIENT_SECRET": "s", "GOOGLE_REFRESH_TOKEN": "r",
       "MS_TENANT_ID": "t", "MS_CLIENT_ID": "id", "MS_CLIENT_SECRET": "s", "SLACK_BOT_TOKEN": "xoxb",
       "SLACK_OPS_WEBHOOK_URL": "https://hooks.slack.com/services/T/B/X",
       "TEAMS_WEBHOOK_URL": "https://prod.westus.logic.azure.com/workflows/abc",
       "PAGERDUTY_ROUTING_KEY": "rk", "TOWER_WEBHOOK_URL": "https://hooks.example/tower", "TOWER_WEBHOOK_SECRET": "shh"}


# Fake secrets: connectors read them at construction, and FakeTransport never sends them anywhere.
def setUpModule():
    os.environ.update(ENV)


def _read(path, mode="r"):
    with open(path, mode) as handle:
        return handle.read()


# Gmail-style base64url without padding.
def b64(text):
    return base64.urlsafe_b64encode(text.encode()).decode().rstrip("=")


class InboundTests(unittest.TestCase):
    """Each source turns provider JSON into events and skips what it must skip."""

    def test_gmail_multipart_to_event(self):
        msg = {"id": "18f2a9c0ffee", "threadId": "t1", "internalDate": "1804406220000", "payload": {
            "mimeType": "multipart/alternative",
            "headers": [{"name": "Subject", "value": "Shipment SH-0182 delayed"},
                        {"name": "From", "value": "dispatch@orbit.example"}],
            "parts": [{"mimeType": "text/html", "body": {"data": b64("<p>ignored html</p>")}},
                      {"mimeType": "text/plain", "body": {"data": b64("SH-0182 now arrives 2027-03-18.")}}]}}
        t = FakeTransport({"/messages?": {"messages": [{"id": "18f2a9c0ffee"}]}, "/messages/18f2a9c0ffee": msg})
        [event] = GmailSource("g", {}, t).fetch()
        self.assertEqual(event["event_id"], "GMAIL-18f2a9c0ffee")
        self.assertEqual(event["source"], "supplier email")
        self.assertEqual(event["text"], "Subject: Shipment SH-0182 delayed\nFrom: dispatch@orbit.example\n\n"
                                        "SH-0182 now arrives 2027-03-18.")
        self.assertEqual(set(event), {"event_id", "received_at", "source", "text", "channel"})

    def test_outlook_graph_message(self):
        t = FakeTransport({"/messages?": {"value": [{
            "id": "AAMkAD=1", "subject": "Plant alert", "receivedDateTime": "2027-03-08T09:16:00.1234567Z",
            "from": {"emailAddress": {"address": "ops@ww.example"}},
            "body": {"contentType": "html", "content": "<div>Lexington&nbsp;down</div><br>Mar 24-25"}}]}})
        [event] = OutlookSource("o", {"mailbox": "tower@ww.example"}, t).fetch()
        self.assertIn("Lexington down", event["text"])
        self.assertIn("Mar 24-25", event["text"])
        self.assertIn("/users/tower%40ww.example/mailFolders/inbox/messages", t.calls[-1]["url"])
        self.assertIn("isRead+eq+false", t.calls[-1]["url"])

    def test_slack_skips_bots_joins_and_own_posts(self):
        t = FakeTransport({"conversations.history": {"ok": True, "messages": [
            {"ts": "1804400000.000100", "user": "U1", "text": "Huntsville line is waiting on battery packs"},
            {"ts": "1804400001.000100", "bot_id": "B1", "text": "bot chatter"},
            {"ts": "1804400002.000100", "subtype": "channel_join", "text": "joined"},
            {"ts": "1804400003.000100", "user": "U2", "text": f"E-01 summary {TOWER_MARKER}"}]}})
        events = SlackSource("s", {"channel_id": "C1"}, t).fetch()
        self.assertEqual([e["text"] for e in events], ["Huntsville line is waiting on battery packs"])
        self.assertEqual(events[0]["source"], "ops chat")

    def test_slack_api_error_raises(self):
        t = FakeTransport({"conversations.history": {"ok": False, "error": "not_in_channel"}})
        with self.assertRaises(ChannelError):
            SlackSource("s", {"channel_id": "C1"}, t).fetch()

    def test_teams_strips_html_and_skips_apps(self):
        t = FakeTransport({"/channels/": {"value": [
            {"id": "1", "messageType": "message", "createdDateTime": "2027-03-08T10:07:00Z",
             "from": {"user": {"displayName": "Floor lead"}}, "body": {"contentType": "html",
             "content": "<p>Jackson update: a power failure.</p>"}},
            {"id": "2", "messageType": "message", "createdDateTime": "2027-03-08T10:08:00Z",
             "from": {"application": {"displayName": "Workflows"}}, "body": {"content": "tower post"}},
            {"id": "3", "messageType": "systemEventMessage", "createdDateTime": "2027-03-08T10:09:00Z",
             "body": {"content": ""}}]}})
        events = TeamsSource("t", {"team_id": "T", "channel_id": "19:x@thread.tacv2"}, t).fetch()
        self.assertEqual([e["text"] for e in events], ["Jackson update: a power failure."])


class SinkTests(unittest.TestCase):
    """Each sink builds the payload its provider expects."""

    msg = Message(route="escalations", event_id="E-02", subject="Needs a human", text="Rumor", severity="warning",
                  facts={"Event": "E-02"}, to=["qa@ww.example"])

    def test_slack_webhook_blocks_carry_marker(self):
        t = FakeTransport({"hooks.slack.com": "ok"})
        SlackSink("s", {"webhook_env": "SLACK_OPS_WEBHOOK_URL"}, t).send(self.msg)
        body = t.calls[0]["json"]
        self.assertIn(TOWER_MARKER, body["text"])
        self.assertEqual(body["blocks"][0]["type"], "header")

    def test_slack_bot_error(self):
        t = FakeTransport({"chat.postMessage": {"ok": False, "error": "channel_not_found"}})
        with self.assertRaises(ChannelError):
            SlackSink("s", {"channel_id": "C1"}, t).send(self.msg)

    def test_teams_adaptive_card(self):
        t = FakeTransport()
        TeamsSink("t", {}, t).send(self.msg)
        att = t.calls[0]["json"]["attachments"][0]
        self.assertEqual(att["contentType"], "application/vnd.microsoft.card.adaptive")
        self.assertEqual(att["content"]["body"][0]["color"], "Warning")

    def test_outlook_sendmail(self):
        t = FakeTransport()
        OutlookSink("o", {"mailbox": "tower@ww.example"}, t).send(self.msg)
        call = t.calls[-1]
        self.assertTrue(call["url"].endswith("/users/tower%40ww.example/sendMail"))
        self.assertEqual(call["json"]["message"]["toRecipients"], [{"emailAddress": {"address": "qa@ww.example"}}])

    def test_gmail_raw_mime(self):
        t = FakeTransport({"messages/send": {"id": "abc"}})
        GmailSink("g", {}, t).send(self.msg)
        raw = base64.urlsafe_b64decode(t.calls[-1]["json"]["raw"]).decode()
        self.assertIn("To: qa@ww.example", raw)
        self.assertIn("X-Tower-Event: E-02", raw)

    def test_email_without_recipient_fails(self):
        msg = Message(route="dealers", event_id="E-1", subject="s", text="t", recipient_id="D01")
        with self.assertRaises(ChannelError):
            OutlookSink("o", {"mailbox": "m@x"}, FakeTransport()).send(msg)

    def test_pagerduty_dedup_on_event(self):
        t = FakeTransport({"events.pagerduty.com": {"status": "success", "dedup_key": "tower-E-02"}})
        PagerDutySink("p", {}, t).send(self.msg)
        self.assertEqual(t.calls[0]["json"]["dedup_key"], "tower-E-02")
        self.assertEqual(t.calls[0]["json"]["payload"]["severity"], "warning")

    def test_webhook_hmac_signature_verifies(self):
        t = FakeTransport()
        WebhookSink("w", {"secret_env": "TOWER_WEBHOOK_SECRET"}, t).send(self.msg)
        call = t.calls[0]
        stamp = call["headers"]["X-Tower-Timestamp"]
        want = hmac.new(b"shh", f"{stamp}.".encode() + call["raw"], hashlib.sha256).hexdigest()
        self.assertEqual(call["headers"]["X-Tower-Signature"], f"sha256={want}")


# A small routing config for the dispatch tests: Slack + PagerDuty for people, Outlook for mail.
def _config(**overrides):
    raw = {
        "sinks": {"slack_ops": {"kind": "slack", "webhook_env": "SLACK_OPS_WEBHOOK_URL"},
                  "pd": {"kind": "pagerduty"},
                  "mail": {"kind": "outlook", "mailbox": "tower@ww.example"}},
        "routes": {"ops": ["slack_ops"], "escalations": ["slack_ops", "pd"], "dealers": ["mail"], "customers": ["mail"]},
        "contacts": {"dealers": {"D01": "d01@ww.example"}},
        "safety": {"redirect_to": []},
    }
    for key, value in overrides.items():
        raw[key] = value
    return ChannelConfig.from_dict(raw)


# Three hand-made events: noise, a rumor (escalated), and an outage whose second dealer notice
# was rejected by the enterprise.
TRACES = [
    {"event_id": "N-1", "classification": "noise", "source": "news wire", "received_at": "", "text": "brochure",
     "summary": "noise", "calls": []},
    {"event_id": "U-1", "classification": "unconfirmed", "source": "ops chat", "received_at": "", "text": "rumor",
     "summary": "rumor", "calls": [{"tool": "escalate", "args": {"reason": "no dates"}}]},
    {"event_id": "R-1", "classification": "plant_outage", "source": "plant alert", "received_at": "", "text": "dark",
     "summary": "outage", "calls": [
         {"tool": "mes.reschedule", "args": {"production_order_id": "PO1", "new_date": "2027-03-29"}},
         {"tool": "dealer.notify", "args": {"dealer_id": "D01", "customer_order_ids": ["CO1"], "message": "late"}},
         {"tool": "dealer.notify", "args": {"dealer_id": "D02", "customer_order_ids": ["CO2"], "message": "late"}},
         {"tool": "crm.notify_customer", "args": {"customer_id": "C0001", "message": "sorry"}}]},
]
LOG = [{"event_id": "U-1", "tool": "escalate", "ok": True},
       {"event_id": "R-1", "tool": "mes.reschedule", "ok": True},
       {"event_id": "R-1", "tool": "dealer.notify", "ok": True},
       {"event_id": "R-1", "tool": "dealer.notify", "ok": False},   # rejected: must not be announced
       {"event_id": "R-1", "tool": "crm.notify_customer", "ok": True}]


class DispatchTests(unittest.TestCase):
    """The guardrails in dispatch.py, one test each."""

    def test_messages_follow_accepted_calls_only(self):
        msgs = build_messages(TRACES, LOG, DATA)
        by_route = {}
        for m in msgs:
            by_route.setdefault(m.route, []).append(m)
        self.assertNotIn("N-1", {m.event_id for m in msgs}, "noise must not notify anyone")
        self.assertEqual([m.event_id for m in by_route["escalations"]], ["U-1"])
        self.assertEqual([m.recipient_id for m in by_route["dealers"]], ["D01"], "D02's notify was rejected")
        self.assertEqual(by_route["ops"][0].severity, "critical", "a failed call raises severity")
        self.assertEqual(by_route["dealers"][0].recipient_name, "Lone Star Wacky Wheels")

    def test_log_mismatch_blocks_per_recipient_sends(self):
        msgs = build_messages(TRACES[2:], LOG[1:3], DATA)  # one line short
        self.assertFalse([m for m in msgs if m.route in ("dealers", "customers")])

    def test_dry_run_sends_nothing(self):
        t = FakeTransport()
        records = Dispatcher(_config(), "dry-run", t).dispatch(build_messages(TRACES, LOG, DATA))
        self.assertEqual(t.calls, [])
        statuses = {(r["route"], r["status"], r["detail"]) for r in records}
        self.assertIn(("dealers", "dry_run", ""), statuses)
        self.assertIn(("customers", "skipped", "no contact on file"), statuses)

    def test_redirect_overrides_addresses(self):
        cfg = _config(safety={"redirect_to": ["qa@ww.example"]})
        t = FakeTransport()
        records = Dispatcher(cfg, "send", t).dispatch(build_messages(TRACES, LOG, DATA))
        mails = [c for c in t.calls if c["url"].endswith("/sendMail")]
        self.assertTrue(mails)
        for call in mails:
            self.assertEqual(call["json"]["message"]["toRecipients"], [{"emailAddress": {"address": "qa@ww.example"}}])
        self.assertFalse([r for r in records if r["status"] == "failed"])

    def test_cap_and_ledger_idempotency(self):
        with tempfile.TemporaryDirectory() as tmp:
            ledger = os.path.join(tmp, "sent.json")
            msgs = build_messages(TRACES, LOG, DATA)
            first = Dispatcher(_config(safety={"max_messages": 2}), "send", FakeTransport(), ledger).dispatch(msgs)
            self.assertEqual(sum(r["status"] == "sent" for r in first), 2)
            self.assertTrue(any("max_messages" in r["detail"] for r in first))
            t = FakeTransport()
            second = Dispatcher(_config(), "send", t, ledger).dispatch(build_messages(TRACES, LOG, DATA))
            self.assertEqual(sum(r["detail"] == "already sent (ledger)" for r in second), 2)

    def test_cap_never_starves_escalations(self):
        many = [{"event_id": f"Q-{i}", "classification": "quality_hold", "source": "", "received_at": "",
                 "text": "", "summary": "", "calls": [{"tool": "crm.notify_customer",
                                                       "args": {"customer_id": "C0001", "message": "m"}}]}
                for i in range(10)]
        log = [{"event_id": t["event_id"], "tool": "crm.notify_customer", "ok": True} for t in many]
        msgs = build_messages(many + TRACES[1:2], log + LOG[:1], DATA)
        cfg = _config(safety={"max_messages": 3, "redirect_to": ["qa@ww.example"]})
        records = Dispatcher(cfg, "dry-run", FakeTransport()).dispatch(msgs)
        esc = [r for r in records if r["route"] == "escalations"]
        self.assertEqual({r["status"] for r in esc}, {"dry_run"})

    def test_sink_failure_is_recorded_not_raised(self):
        t = FakeTransport({"hooks.slack.com": ChannelError("HTTP 404")})
        records = Dispatcher(_config(), "send", t).dispatch(build_messages(TRACES, LOG, DATA))
        self.assertTrue(any(r["sink"] == "slack_ops" and r["status"] == "failed" for r in records))
        self.assertTrue(any(r["sink"] == "pd" and r["status"] == "sent" for r in records))

    def test_no_config_is_unrouted(self):
        records = Dispatcher(ChannelConfig.from_dict({}), "dry-run", FakeTransport()).dispatch(
            build_messages(TRACES, LOG, DATA))
        self.assertTrue(records)
        self.assertEqual({r["status"] for r in records}, {"unrouted"})

    @unittest.skipUnless(os.path.isfile(os.path.join(RUN1, "traces.json")), "no runs/run1")
    def test_real_run_pairs_cleanly_and_does_not_touch_log(self):
        log_path = os.path.join(RUN1, "action_log.jsonl")
        before = _read(log_path, "rb")
        with tempfile.TemporaryDirectory() as tmp:
            for name in ("traces.json", "action_log.jsonl"):
                with open(os.path.join(RUN1, name), "rb") as src, open(os.path.join(tmp, name), "wb") as dst:
                    dst.write(src.read())
            records = notify_run(tmp, DATA, "dry-run", _config(safety={"max_messages": 100000}))
        self.assertEqual(_read(log_path, "rb"), before)
        traces = json.loads(_read(os.path.join(RUN1, "traces.json")))
        log = [json.loads(line) for line in _read(log_path).splitlines() if line.strip()]
        escalates = sum(1 for line in log if line["tool"] == "escalate" and line["ok"])
        self.assertEqual(sum(r["route"] == "escalations" for r in records) // 2, escalates)  # two sinks
        noise = {t["event_id"] for t in traces if t["classification"] == "noise"}
        self.assertFalse(noise & {r["event_id"] for r in records})
        dealer_pairs = {(l["event_id"], l["args"]["dealer_id"]) for l in log
                        if l["ok"] and l["tool"] in ("dealer.notify", "dealer.stop_sale")}
        self.assertEqual(sum(r["route"] == "dealers" for r in records), len(dealer_pairs))


class EndToEndTests(unittest.TestCase):
    """A message arriving through Slack takes exactly the same actions as the same text in events.json."""

    def test_slack_message_matches_feed_event(self):
        from enterprise import Enterprise
        from tower.agents.coordinator import handle_event
        from tower.graph import WorldGraph
        from tower.run import _CallLog

        feed = {e["event_id"]: e for e in json.loads(_read(os.path.join(DATA, "events.json")))}
        reference = feed["E-10"]
        t = FakeTransport({"conversations.history": {"ok": True, "messages": [
            {"ts": "1804406000.000200", "user": "U9", "text": reference["text"]}]}})
        [live] = SlackSource("s", {"channel_id": "C1"}, t).fetch()

        graph = WorldGraph()
        ent = Enterprise(graph.data_dir)
        a, b = [], []
        handle_event(graph, _CallLog(ent, a), reference, None)
        handle_event(graph, _CallLog(ent, b), live, None)
        strip = lambda rows: [(r["tool"], json.dumps(r["args"], sort_keys=True), r["ok"]) for r in rows]
        self.assertTrue(a)
        self.assertEqual(strip(a), strip(b))


if __name__ == "__main__":
    unittest.main()
