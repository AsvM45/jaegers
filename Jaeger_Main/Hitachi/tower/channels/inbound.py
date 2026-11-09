"""Inbound sources: read messages from Gmail, Outlook, Slack, Teams or any IMAP mailbox and turn
them into control-tower events.

An event has the same keys as events.json (event_id, received_at, source, text) plus a
"channel" block that records where it came from. The tower reads only the text, so a Slack
message and a supplier email go through the same pipeline.

Loop guard: anything the tower itself posted carries TOWER_MARKER, and bot posts are skipped,
so the tower's own notices never come back as new events.
"""

from __future__ import annotations

import base64
import email
import email.policy
import html
import imaplib
import re
import urllib.parse
from datetime import datetime, timezone

from tower.channels.transport import (GRAPH, ChannelError, GoogleAuth, MicrosoftAuth, Transport,
                                      env)

TOWER_MARKER = "[control-tower]"


def html_to_text(markup: str) -> str:
    """Rough HTML to plain text for email and Teams bodies. Block tags become line breaks.

    The reader needs words and dates, not layout, so a regex is enough; nothing here is
    rendered back as HTML.
    """
    text = re.sub(r"(?is)<(script|style).*?</\1>", " ", markup or "")
    text = re.sub(r"(?i)<br\s*/?>|</p>|</div>|</li>", "\n", text)
    text = re.sub(r"<[^>]+>", "", text)
    text = html.unescape(text).replace("\xa0", " ").replace("\u200b", "")
    return re.sub(r"[ \t]+", " ", re.sub(r"\n\s*\n+", "\n\n", text)).strip()


# Timestamps are converted to this machine's local time. The reader ignores received_at, so this
# only affects how the UI orders and shows events.
def _iso_local(dt: datetime) -> str:
    """events.json uses naive local ISO timestamps to the second."""
    if dt.tzinfo is not None:
        dt = dt.astimezone().replace(tzinfo=None)
    return dt.replace(microsecond=0).isoformat()


def _parse_iso(text: str) -> datetime:
    # Graph sends "2027-03-08T07:17:00.1234567Z": seven fractional digits and a Z.
    cleaned = re.sub(r"(\.\d{6})\d+", r"\1", text.replace("Z", "+00:00"))
    return datetime.fromisoformat(cleaned)


def _mail_text(subject: str, sender: str, body: str) -> str:
    # Same layout as the supplier emails in events.json, so the reader sees a familiar shape.
    return f"Subject: {subject}\nFrom: {sender}\n\n{body.strip()}"


def _event(prefix: str, ref: str, received: datetime, source: str, text: str, kind: str, **extra) -> dict:
    """Build one event. The id is the provider prefix plus the last 16 alphanumerics of the
    provider's message id: stable across polls (for dedup) and short enough to read in the UI."""
    safe = re.sub(r"[^A-Za-z0-9]", "", ref)[-16:] or "0"
    return {
        "event_id": f"{prefix}-{safe}",
        "received_at": _iso_local(received),
        "source": source,
        "text": text,
        "channel": {"kind": kind, "ref": ref, **extra},
    }


class Source:
    """Base class. Subclasses set kind and default_label and implement fetch().

    cfg is the source's block from channels.json. limit caps how many messages one poll reads;
    source_label is the "source" field on each event (the feed uses "supplier email", "ops chat").
    """

    kind = "source"

    def __init__(self, name: str, cfg: dict, transport: Transport):
        self.name, self.cfg, self.transport = name, cfg, transport
        self.limit = int(cfg.get("limit", 25))
        self.source_label = cfg.get("source_label", self.default_label)

    default_label = "message"

    def fetch(self) -> list[dict]:
        """Return new messages as events. Raises ChannelError when the provider call fails."""
        raise NotImplementedError

    def acknowledge(self, event: dict) -> None:
        """Mark a message as handled at the provider, when the config asks for it."""

    # Empty messages and the tower's own posts are never turned into events.
    @staticmethod
    def _skip(text: str) -> bool:
        return not text.strip() or TOWER_MARKER in text


# ---------------------------------------------------------------- Gmail (Gmail REST API)
class GmailSource(Source):
    """Scopes: gmail.readonly (or gmail.modify when mark_read is true)."""

    kind = "gmail"
    default_label = "supplier email"
    API = "https://gmail.googleapis.com/gmail/v1/users/me"

    def __init__(self, name, cfg, transport):
        super().__init__(name, cfg, transport)
        self.auth = GoogleAuth.from_config(transport, cfg)
        self.query = cfg.get("query", "is:unread newer_than:2d")

    def fetch(self):
        # Gmail lists ids only; each message needs a second call for headers and body.
        q = urllib.parse.urlencode({"q": self.query, "maxResults": self.limit})
        listing = self.transport.request("GET", f"{self.API}/messages?{q}", headers=self.auth.headers())
        events = []
        for stub in listing.get("messages", []) or []:
            msg = self.transport.request("GET", f"{self.API}/messages/{stub['id']}?format=full",
                                         headers=self.auth.headers())
            hdrs = {h["name"].lower(): h["value"] for h in msg.get("payload", {}).get("headers", [])}
            body = self._body(msg.get("payload", {})) or msg.get("snippet", "")
            text = _mail_text(hdrs.get("subject", ""), hdrs.get("from", ""), body)
            if self._skip(text):
                continue
            received = datetime.fromtimestamp(int(msg.get("internalDate", 0)) / 1000)
            events.append(_event("GMAIL", msg["id"], received, self.source_label, text, self.kind,
                                 source_name=self.name, sender=hdrs.get("from", ""),
                                 thread=msg.get("threadId")))
        return events

    def _body(self, part: dict) -> str:
        """Depth-first search of the MIME tree for text/plain, falling back to text/html.

        Gmail bodies are base64url without padding, so the padding is added back first.
        """
        mime = part.get("mimeType", "")
        data = part.get("body", {}).get("data")
        if data and mime in ("text/plain", "text/html"):
            raw = base64.urlsafe_b64decode(data + "=" * (-len(data) % 4)).decode("utf-8", "replace")
            return raw if mime == "text/plain" else html_to_text(raw)
        subs = part.get("parts", []) or []
        for want in ("text/plain", "text/html"):
            for sub in subs:
                if sub.get("mimeType") == want or sub.get("mimeType", "").startswith("multipart/"):
                    found = self._body(sub)
                    if found:
                        return found
        return ""

    def acknowledge(self, event):
        if self.cfg.get("mark_read"):
            self.transport.request("POST", f"{self.API}/messages/{event['channel']['ref']}/modify",
                                   headers=self.auth.headers(), json_body={"removeLabelIds": ["UNREAD"]})


# ---------------------------------------------------------------- Outlook / Exchange Online (Graph)
class OutlookSource(Source):
    """Application permission Mail.Read (Mail.ReadWrite when mark_read is true), scoped with an
    Exchange application access policy to the one ops mailbox."""

    kind = "outlook"
    default_label = "supplier email"

    def __init__(self, name, cfg, transport):
        super().__init__(name, cfg, transport)
        self.auth = MicrosoftAuth.from_config(transport, cfg)
        self.mailbox = cfg.get("mailbox") or env(cfg.get("mailbox_env", "OUTLOOK_MAILBOX"))
        self.folder = cfg.get("folder", "inbox")

    def fetch(self):
        # The Prefer header asks Graph for a text body; html_to_text covers servers that ignore it.
        params = {"$top": self.limit, "$orderby": "receivedDateTime desc",
                  "$select": "id,subject,from,receivedDateTime,body,conversationId"}
        if self.cfg.get("unread_only", True):
            params["$filter"] = "isRead eq false"
        url = (f"{GRAPH}/users/{urllib.parse.quote(self.mailbox)}/mailFolders/{self.folder}/messages?"
               + urllib.parse.urlencode(params))
        headers = {**self.auth.headers(), "Prefer": 'outlook.body-content-type="text"'}
        events = []
        for msg in self.transport.request("GET", url, headers=headers).get("value", []):
            sender = (msg.get("from") or {}).get("emailAddress", {}).get("address", "")
            body = msg.get("body", {})
            content = body.get("content", "")
            if body.get("contentType") == "html":
                content = html_to_text(content)
            text = _mail_text(msg.get("subject", ""), sender, content)
            if self._skip(text):
                continue
            events.append(_event("OUTLOOK", msg["id"], _parse_iso(msg["receivedDateTime"]), self.source_label,
                                 text, self.kind, source_name=self.name, sender=sender,
                                 thread=msg.get("conversationId")))
        return events

    def acknowledge(self, event):
        if self.cfg.get("mark_read"):
            url = f"{GRAPH}/users/{urllib.parse.quote(self.mailbox)}/messages/{event['channel']['ref']}"
            self.transport.request("PATCH", url, headers=self.auth.headers(), json_body={"isRead": True})


# ---------------------------------------------------------------- Slack (Web API)
class SlackSource(Source):
    """Bot token scopes: channels:history (groups:history for private channels)."""

    kind = "slack"
    default_label = "ops chat"

    def __init__(self, name, cfg, transport):
        super().__init__(name, cfg, transport)
        self.token = env(cfg.get("token_env", "SLACK_BOT_TOKEN"))
        self.channel = cfg["channel_id"]
        self.oldest = cfg.get("oldest")

    def fetch(self):
        params = {"channel": self.channel, "limit": self.limit}
        if self.oldest:
            params["oldest"] = self.oldest
        # Slack answers HTTP 200 even on errors; the real status is the "ok" field.
        res = self.transport.request("GET", "https://slack.com/api/conversations.history?" + urllib.parse.urlencode(params),
                                     headers={"Authorization": f"Bearer {self.token}"})
        if not res.get("ok"):
            raise ChannelError(f"Slack conversations.history: {res.get('error')}")
        events = []
        for msg in res.get("messages", []):
            # Keep human posts only: no bots (including the tower), joins, edits or topic changes.
            if msg.get("bot_id") or msg.get("subtype") not in (None, "thread_broadcast", "file_share"):
                continue
            text = msg.get("text", "")
            if self._skip(text):
                continue
            received = datetime.fromtimestamp(float(msg["ts"]))
            events.append(_event("SLACK", msg["ts"], received, self.source_label, text, self.kind,
                                 source_name=self.name, channel_id=self.channel, user=msg.get("user")))
        return events

    def acknowledge(self, event):
        if self.cfg.get("react"):
            self.transport.request("POST", "https://slack.com/api/reactions.add",
                                   headers={"Authorization": f"Bearer {self.token}"},
                                   json_body={"channel": self.channel, "timestamp": event["channel"]["ref"],
                                              "name": self.cfg["react"]})


# ---------------------------------------------------------------- Microsoft Teams channel (Graph)
class TeamsSource(Source):
    """Application permission ChannelMessage.Read.All (a protected API; request access from
    Microsoft), or a resource-specific consent grant on the one team."""

    kind = "teams"
    default_label = "ops chat"

    def __init__(self, name, cfg, transport):
        super().__init__(name, cfg, transport)
        self.auth = MicrosoftAuth.from_config(transport, cfg)
        self.team, self.channel = cfg["team_id"], cfg["channel_id"]

    def fetch(self):
        # Top-level channel posts only; replies in threads are not read. Graph caps $top at 50.
        url = f"{GRAPH}/teams/{self.team}/channels/{urllib.parse.quote(self.channel)}/messages?$top={min(self.limit, 50)}"
        events = []
        for msg in self.transport.request("GET", url, headers=self.auth.headers()).get("value", []):
            if msg.get("messageType") != "message" or msg.get("deletedDateTime"):
                continue
            if (msg.get("from") or {}).get("application"):
                continue  # posted by a bot or webhook, including the tower itself
            body = msg.get("body", {})
            text = body.get("content", "")
            if body.get("contentType") == "html":
                text = html_to_text(text)
            if msg.get("subject"):
                text = f"{msg['subject']}\n{text}"
            if self._skip(text):
                continue
            user = ((msg.get("from") or {}).get("user") or {}).get("displayName")
            events.append(_event("TEAMS", msg["id"], _parse_iso(msg["createdDateTime"]), self.source_label,
                                 text, self.kind, source_name=self.name, user=user))
        return events


# ---------------------------------------------------------------- Any IMAP mailbox
class ImapSource(Source):
    """Generic IMAP over TLS: Gmail/Outlook app passwords, Yahoo, Fastmail, on-prem Exchange."""

    kind = "imap"
    default_label = "supplier email"

    def __init__(self, name, cfg, transport):
        super().__init__(name, cfg, transport)
        self.host, self.port = cfg["host"], int(cfg.get("port", 993))
        self.user = cfg.get("user") or env(cfg.get("user_env", "IMAP_USER"))
        self.password = env(cfg.get("password_env", "IMAP_PASSWORD"))
        self.folder = cfg.get("folder", "INBOX")
        self.search = cfg.get("search", "UNSEEN")

    def fetch(self):
        events = []
        try:
            with imaplib.IMAP4_SSL(self.host, self.port) as box:
                box.login(self.user, self.password)
                # Read-only unless mark_read is set, and BODY.PEEK below, so polling never marks
                # mail as read behind the user's back.
                box.select(self.folder, readonly=not self.cfg.get("mark_read"))
                _typ, data = box.uid("search", None, self.search)
                uids = (data[0] or b"").split()[-self.limit:]
                for uid in uids:
                    part = "(RFC822)" if self.cfg.get("mark_read") else "(BODY.PEEK[])"
                    _typ, fetched = box.uid("fetch", uid, part)
                    raw = next((item[1] for item in fetched if isinstance(item, tuple)), None)
                    if raw is None:
                        continue
                    events.extend(self._parse(uid.decode(), raw))
        except (imaplib.IMAP4.error, OSError) as exc:
            raise ChannelError(f"IMAP {self.host}: {exc}") from None
        return events

    def _parse(self, uid: str, raw: bytes) -> list[dict]:
        """One raw RFC 822 message -> [event], or [] when it should be skipped."""
        msg = email.message_from_bytes(raw, policy=email.policy.default)
        body_part = msg.get_body(preferencelist=("plain", "html"))
        body = body_part.get_content() if body_part else ""
        if body_part is not None and body_part.get_content_subtype() == "html":
            body = html_to_text(body)
        text = _mail_text(str(msg.get("subject", "")), str(msg.get("from", "")), body)
        if self._skip(text):
            return []
        try:
            received = email.utils.parsedate_to_datetime(msg.get("date"))
        except (TypeError, ValueError):
            received = datetime.now(timezone.utc)
        ref = str(msg.get("message-id") or uid)
        return [_event("IMAP", ref, received, self.source_label, text, self.kind,
                       source_name=self.name, sender=str(msg.get("from", "")))]


# kind in channels.json -> class.
SOURCES = {cls.kind: cls for cls in (GmailSource, OutlookSource, SlackSource, TeamsSource, ImapSource)}
