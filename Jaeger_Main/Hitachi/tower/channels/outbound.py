"""Outbound sinks: deliver a tower Message to Slack, Microsoft Teams, Gmail, Outlook, SMTP,
PagerDuty, Google Chat or any JSON webhook (ServiceNow, Jira Automation, Zapier, n8n...).

A sink only formats and sends. Who gets what, dry-run, redirects and rate limits are decided
in dispatch.py.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import smtplib
import ssl
import time
import urllib.parse
from dataclasses import asdict, dataclass, field
from email.message import EmailMessage
from email.utils import formataddr

from tower.channels.inbound import TOWER_MARKER
from tower.channels.transport import GRAPH, ChannelError, GoogleAuth, MicrosoftAuth, Transport, env

SEVERITY_COLOR = {"info": "#2E7D32", "warning": "#F9A825", "critical": "#C62828"}


@dataclass
class Message:
    """One thing the tower wants a person to know."""

    route: str            # ops | escalations | dealers | customers
    event_id: str
    subject: str
    text: str
    severity: str = "info"            # info | warning | critical
    recipient_id: str | None = None   # dealer_id / customer_id for per-recipient routes
    recipient_name: str | None = None
    to: list[str] = field(default_factory=list)  # resolved addresses (email sinks)
    facts: dict = field(default_factory=dict)

    def to_dict(self):
        return asdict(self)

    # Every outbound post ends with this. The marker is what stops the tower reading its own posts.
    def footer(self) -> str:
        return f"{TOWER_MARKER} event {self.event_id} · Wacky Wheels control tower"


class Sink:
    """Base class. send() delivers one Message and returns a small result dict, or raises ChannelError."""

    kind = "sink"
    needs_address = False  # email sinks need Message.to or a configured "to"

    def __init__(self, name: str, cfg: dict, transport: Transport):
        self.name, self.cfg, self.transport = name, cfg, transport

    def send(self, msg: Message) -> dict:
        raise NotImplementedError

    def _addresses(self, msg: Message) -> list[str]:
        """Resolved recipients from dispatch, else the sink's fixed "to" list. Never empty."""
        to = list(msg.to) or list(self.cfg.get("to", []))
        if not to:
            raise ChannelError(f"{self.name}: no recipient address for {msg.recipient_id or msg.route}")
        return to


# ---------------------------------------------------------------- Slack
class SlackSink(Sink):
    """Either an incoming webhook (webhook_env) or a bot token with chat:write (token_env + channel_id)."""

    kind = "slack"

    def send(self, msg):
        # Block Kit layout; the slices keep within Slack's per-block text limits (150 / 3000).
        blocks = [
            {"type": "header", "text": {"type": "plain_text", "text": msg.subject[:150]}},
            {"type": "section", "text": {"type": "mrkdwn", "text": msg.text[:2900]}},
        ]
        if msg.facts:
            blocks.append({"type": "section", "fields": [
                {"type": "mrkdwn", "text": f"*{k}*\n{v}"} for k, v in list(msg.facts.items())[:10]]})
        blocks.append({"type": "context", "elements": [{"type": "mrkdwn", "text": msg.footer()}]})
        # "text" is the fallback for notifications and screen readers, which do not show blocks.
        payload = {"text": f"{msg.subject} {TOWER_MARKER}", "blocks": blocks}
        if self.cfg.get("webhook_env"):
            res = self.transport.request("POST", env(self.cfg["webhook_env"]), json_body=payload)
            return {"ok": True, "detail": res if isinstance(res, str) else "posted"}
        payload["channel"] = self.cfg["channel_id"]
        res = self.transport.request("POST", "https://slack.com/api/chat.postMessage", json_body=payload,
                                     headers={"Authorization": f"Bearer {env(self.cfg.get('token_env', 'SLACK_BOT_TOKEN'))}"})
        if not res.get("ok"):
            raise ChannelError(f"Slack chat.postMessage: {res.get('error')}")
        return {"ok": True, "ts": res.get("ts")}


# ---------------------------------------------------------------- Microsoft Teams
class TeamsSink(Sink):
    """Teams Workflows webhook ("Post to a channel when a webhook request is received").
    Graph cannot post channel messages with application permissions, so the webhook is the
    supported path for an unattended service."""

    kind = "teams"

    def send(self, msg):
        # An Adaptive Card wrapped in the message envelope that Teams Workflows expect.
        body = [
            {"type": "TextBlock", "size": "Large", "weight": "Bolder", "wrap": True, "text": msg.subject,
             "color": {"critical": "Attention", "warning": "Warning"}.get(msg.severity, "Default")},
            {"type": "TextBlock", "wrap": True, "text": msg.text[:4000]},
        ]
        if msg.facts:
            body.append({"type": "FactSet", "facts": [{"title": str(k), "value": str(v)}
                                                       for k, v in list(msg.facts.items())[:12]]})
        body.append({"type": "TextBlock", "isSubtle": True, "size": "Small", "wrap": True, "text": msg.footer()})
        card = {"$schema": "http://adaptivecards.io/schemas/adaptive-card.json", "type": "AdaptiveCard",
                "version": "1.4", "body": body}
        payload = {"type": "message", "attachments": [
            {"contentType": "application/vnd.microsoft.card.adaptive", "contentUrl": None, "content": card}]}
        self.transport.request("POST", env(self.cfg.get("webhook_env", "TEAMS_WEBHOOK_URL")), json_body=payload)
        return {"ok": True}


# ---------------------------------------------------------------- Email (shared MIME builder)
def _mime(msg: Message, sender: str, to: list[str]) -> EmailMessage:
    """Plain-text email for the Gmail and SMTP sinks. X-Tower-Event lets mail rules filter replies."""
    mail = EmailMessage()
    mail["Subject"] = msg.subject
    mail["From"] = sender
    mail["To"] = ", ".join(to)
    mail["X-Tower-Event"] = msg.event_id
    lines = [msg.text, ""]
    lines += [f"{k}: {v}" for k, v in msg.facts.items()]
    lines += ["", "--", msg.footer()]
    mail.set_content("\n".join(lines))
    return mail


class GmailSink(Sink):
    """Gmail API users.messages.send. Scope: gmail.send."""

    kind = "gmail"
    needs_address = True

    def __init__(self, name, cfg, transport):
        super().__init__(name, cfg, transport)
        self.auth = GoogleAuth.from_config(transport, cfg)

    def send(self, msg):
        # Gmail takes the whole RFC 822 message base64url-encoded; "me" is the authorised account.
        sender = self.cfg.get("from", "me")
        raw = base64.urlsafe_b64encode(_mime(msg, sender, self._addresses(msg)).as_bytes()).decode()
        res = self.transport.request("POST", "https://gmail.googleapis.com/gmail/v1/users/me/messages/send",
                                     headers=self.auth.headers(), json_body={"raw": raw})
        return {"ok": True, "id": res.get("id") if isinstance(res, dict) else None}


class OutlookSink(Sink):
    """Graph users/{mailbox}/sendMail. Application permission: Mail.Send (limit it to the
    tower mailbox with an Exchange application access policy)."""

    kind = "outlook"
    needs_address = True

    def __init__(self, name, cfg, transport):
        super().__init__(name, cfg, transport)
        self.auth = MicrosoftAuth.from_config(transport, cfg)
        self.mailbox = cfg.get("mailbox") or env(cfg.get("mailbox_env", "OUTLOOK_MAILBOX"))

    def send(self, msg):
        content = "\n".join([msg.text, ""] + [f"{k}: {v}" for k, v in msg.facts.items()] + ["", "--", msg.footer()])
        payload = {"message": {
            "subject": msg.subject,
            "body": {"contentType": "Text", "content": content},
            "toRecipients": [{"emailAddress": {"address": a}} for a in self._addresses(msg)],
            "internetMessageHeaders": [{"name": "X-Tower-Event", "value": msg.event_id}],
        }, "saveToSentItems": True}
        self.transport.request("POST", f"{GRAPH}/users/{urllib.parse.quote(self.mailbox)}/sendMail",
                               headers=self.auth.headers(), json_body=payload)
        return {"ok": True}


class SmtpSink(Sink):
    """Any SMTP relay: Gmail/Outlook app passwords, SendGrid, Amazon SES, Mailgun, on-prem."""

    kind = "smtp"
    needs_address = True

    def send(self, msg):
        host, port = self.cfg["host"], int(self.cfg.get("port", 587))
        user = self.cfg.get("user") or env(self.cfg.get("user_env"), required=False)
        password = env(self.cfg.get("password_env"), required=False)
        sender = self.cfg.get("from") or user
        mail = _mime(msg, formataddr((self.cfg.get("from_name", "Control Tower"), sender)), self._addresses(msg))
        # Port 465 (or ssl: true) is TLS from the start; anything else upgrades with STARTTLS.
        # Either way the server certificate is verified.
        try:
            ctx = ssl.create_default_context()
            if self.cfg.get("ssl") or port == 465:
                server = smtplib.SMTP_SSL(host, port, context=ctx, timeout=20)
            else:
                server = smtplib.SMTP(host, port, timeout=20)
                server.starttls(context=ctx)
            with server:
                if user and password:
                    server.login(user, password)
                server.send_message(mail)
        except (smtplib.SMTPException, OSError) as exc:
            raise ChannelError(f"SMTP {host}: {exc}") from None
        return {"ok": True}


# ---------------------------------------------------------------- PagerDuty (human-in-the-loop paging)
class PagerDutySink(Sink):
    """Events API v2. dedup_key is the event id, so re-running the tower never double-pages."""

    kind = "pagerduty"

    def send(self, msg):
        payload = {
            "routing_key": env(self.cfg.get("routing_key_env", "PAGERDUTY_ROUTING_KEY")),
            "event_action": "trigger",
            "dedup_key": f"tower-{msg.event_id}",
            "payload": {"summary": msg.subject[:1024], "source": "wacky-wheels-control-tower",
                        "severity": {"critical": "critical", "warning": "warning"}.get(msg.severity, "info"),
                        "custom_details": {"text": msg.text, **msg.facts}},
        }
        res = self.transport.request("POST", "https://events.pagerduty.com/v2/enqueue", json_body=payload)
        return {"ok": True, "dedup_key": res.get("dedup_key") if isinstance(res, dict) else None}


# ---------------------------------------------------------------- Google Chat space webhook
class GoogleChatSink(Sink):
    kind = "google_chat"

    def send(self, msg):
        text = f"*{msg.subject}*\n{msg.text}\n" + "".join(f"\n• {k}: {v}" for k, v in msg.facts.items())
        self.transport.request("POST", env(self.cfg.get("webhook_env", "GOOGLE_CHAT_WEBHOOK_URL")),
                               json_body={"text": f"{text}\n_{msg.footer()}_"})
        return {"ok": True}


# ---------------------------------------------------------------- Generic JSON webhook
class WebhookSink(Sink):
    """POST the Message as JSON. With secret_env set, adds X-Tower-Signature: sha256=<hmac>
    over "<timestamp>.<body>" so the receiver can verify it."""

    kind = "webhook"

    def send(self, msg):
        body = json.dumps({"tower": "wacky-wheels", **msg.to_dict()}).encode("utf-8")
        headers = {"Content-Type": "application/json", **self.cfg.get("headers", {})}
        if self.cfg.get("secret_env"):
            stamp = str(int(time.time()))
            sig = hmac.new(env(self.cfg["secret_env"]).encode(), f"{stamp}.".encode() + body, hashlib.sha256)
            headers.update({"X-Tower-Timestamp": stamp, "X-Tower-Signature": f"sha256={sig.hexdigest()}"})
        url = self.cfg.get("url") or env(self.cfg.get("url_env", "TOWER_WEBHOOK_URL"))
        self.transport.request("POST", url, headers=headers, raw=body)
        return {"ok": True}


# kind in channels.json -> class.
SINKS = {cls.kind: cls for cls in (SlackSink, TeamsSink, GmailSink, OutlookSink, SmtpSink,
                                   PagerDutySink, GoogleChatSink, WebhookSink)}
