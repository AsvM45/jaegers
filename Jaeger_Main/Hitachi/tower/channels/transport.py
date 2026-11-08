"""HTTP and OAuth plumbing shared by every channel. Standard library only.

Every connector receives a Transport, so tests can swap in a fake one and nothing reaches
the network.
"""

from __future__ import annotations

import json
import os
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any


class ChannelError(Exception):
    """A channel call failed: bad credentials, HTTP error, or a provider-level error."""


class Transport:
    """Thin urllib wrapper. request() returns parsed JSON (or text) and raises ChannelError."""

    # retries=2 means up to three attempts in all, with backoff of 1 s, then 2 s.
    def __init__(self, timeout: float = 20.0, retries: int = 2):
        self.timeout = timeout
        self.retries = retries

    def request(self, method: str, url: str, *, headers: dict | None = None, json_body: Any = None,
                form: dict | None = None, raw: bytes | None = None) -> Any:
        """Send one request. Give at most one body: json_body, form (URL-encoded) or raw bytes.

        Retries 429 and 5xx (honouring Retry-After) and network errors; any other 4xx fails at
        once. An empty response is {}; a non-JSON body (Slack webhooks answer "ok") is text.
        """
        headers = dict(headers or {})
        data = raw
        if json_body is not None:
            data = json.dumps(json_body).encode("utf-8")
            headers.setdefault("Content-Type", "application/json")
        elif form is not None:
            data = urllib.parse.urlencode(form).encode("utf-8")
            headers.setdefault("Content-Type", "application/x-www-form-urlencoded")
        headers.setdefault("User-Agent", "wacky-wheels-control-tower/1.0")
        last = None
        for attempt in range(self.retries + 1):
            req = urllib.request.Request(url, data=data, headers=headers, method=method)
            try:
                with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                    body = resp.read()
                    if not body:
                        return {}
                    try:
                        return json.loads(body)
                    except ValueError:
                        return body.decode("utf-8", "replace")
            except urllib.error.HTTPError as exc:
                detail = exc.read().decode("utf-8", "replace")[:500]
                last = ChannelError(f"{method} {_redact(url)} -> HTTP {exc.code}: {detail}")
                # Retry only throttling and server errors; a 4xx is our fault and will not improve.
                if exc.code not in (429, 500, 502, 503, 504):
                    raise last from None
                wait = float(exc.headers.get("Retry-After") or 2 ** attempt)
            except (urllib.error.URLError, TimeoutError, OSError) as exc:
                last = ChannelError(f"{method} {_redact(url)} failed: {exc}")
                wait = 2 ** attempt
            if attempt < self.retries:
                time.sleep(min(wait, 10))
        raise last


def _redact(url: str) -> str:
    """Webhook URLs carry their secret in the path; never print them whole."""
    parts = urllib.parse.urlsplit(url)
    path = parts.path if len(parts.path) < 24 else parts.path[:16] + "…"
    return f"{parts.scheme}://{parts.netloc}{path}"


def env(name: str | None, required: bool = True) -> str | None:
    """Read a secret from the environment by the variable name given in the config."""
    if not name:
        if required:
            raise ChannelError("config is missing the name of the environment variable for a secret")
        return None
    value = os.environ.get(name)
    if required and not value:
        raise ChannelError(f"environment variable {name} is not set")
    return value


def load_dotenv(path: str) -> None:
    """Load KEY=VALUE lines into os.environ without overriding variables already set."""
    if not os.path.isfile(path):
        return
    with open(path, encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


class _TokenCache:
    """One OAuth access token, refreshed a minute before it expires. Thread-safe."""

    def __init__(self):
        self._token = None
        self._expires = 0.0
        self._lock = threading.Lock()

    # fetch() returns (token, lifetime in seconds) and is called only when a refresh is due.
    def get(self, fetch) -> str:
        with self._lock:
            if self._token is None or time.time() > self._expires - 60:
                token, ttl = fetch()
                self._token, self._expires = token, time.time() + ttl
            return self._token


class GoogleAuth:
    """OAuth 2.0 refresh-token flow for Gmail (installed app or web client)."""

    TOKEN_URL = "https://oauth2.googleapis.com/token"

    def __init__(self, transport: Transport, client_id: str, client_secret: str, refresh_token: str):
        self.transport, self.client_id, self.client_secret, self.refresh_token = (
            transport, client_id, client_secret, refresh_token)
        self._cache = _TokenCache()

    @classmethod
    def from_config(cls, transport: Transport, cfg: dict) -> "GoogleAuth":
        """Build from a source/sink config; each *_env key names the variable holding the secret."""
        return cls(transport, env(cfg.get("client_id_env", "GOOGLE_CLIENT_ID")),
                   env(cfg.get("client_secret_env", "GOOGLE_CLIENT_SECRET")),
                   env(cfg.get("refresh_token_env", "GOOGLE_REFRESH_TOKEN")))

    def token(self) -> str:
        """A valid access token, refreshing it through the refresh token when needed."""
        def fetch():
            res = self.transport.request("POST", self.TOKEN_URL, form={
                "client_id": self.client_id, "client_secret": self.client_secret,
                "refresh_token": self.refresh_token, "grant_type": "refresh_token"})
            if not isinstance(res, dict) or "access_token" not in res:
                raise ChannelError(f"Google token refresh failed: {res}")
            return res["access_token"], float(res.get("expires_in", 3600))
        return self._cache.get(fetch)

    def headers(self) -> dict:
        return {"Authorization": f"Bearer {self.token()}"}


class MicrosoftAuth:
    """Entra ID (Azure AD) client-credentials flow for Microsoft Graph: Outlook mail and Teams."""

    def __init__(self, transport: Transport, tenant_id: str, client_id: str, client_secret: str):
        self.transport, self.tenant_id, self.client_id, self.client_secret = (
            transport, tenant_id, client_id, client_secret)
        self._cache = _TokenCache()

    @classmethod
    def from_config(cls, transport: Transport, cfg: dict) -> "MicrosoftAuth":
        """Build from a source/sink config; each *_env key names the variable holding the secret."""
        return cls(transport, env(cfg.get("tenant_id_env", "MS_TENANT_ID")),
                   env(cfg.get("client_id_env", "MS_CLIENT_ID")),
                   env(cfg.get("client_secret_env", "MS_CLIENT_SECRET")))

    def token(self) -> str:
        """An app-only Graph token. Client credentials have no refresh token; just ask again."""
        def fetch():
            url = f"https://login.microsoftonline.com/{self.tenant_id}/oauth2/v2.0/token"
            res = self.transport.request("POST", url, form={
                "client_id": self.client_id, "client_secret": self.client_secret,
                "scope": "https://graph.microsoft.com/.default", "grant_type": "client_credentials"})
            if not isinstance(res, dict) or "access_token" not in res:
                raise ChannelError(f"Microsoft token request failed: {res}")
            return res["access_token"], float(res.get("expires_in", 3600))
        return self._cache.get(fetch)

    def headers(self) -> dict:
        return {"Authorization": f"Bearer {self.token()}"}


GRAPH = "https://graph.microsoft.com/v1.0"
