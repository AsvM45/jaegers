"""Load channels.json (sources, sinks, routes, safety) and contacts.json.

Lookup order for the config file:
    1. $TOWER_CHANNELS_CONFIG
    2. tower/channels/channels.json   (gitignored; copy channels.example.json)
With no file the tower still runs: every route is empty and dispatch records "unrouted".

Secrets are never stored in these files. A config names the environment variable that holds
each secret (token_env, webhook_env, client_secret_env...). Hitachi/.env is loaded if present.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field

from tower.channels.transport import load_dotenv

HERE = os.path.dirname(os.path.abspath(__file__))
HITACHI = os.path.abspath(os.path.join(HERE, "..", ".."))
DEFAULT_CONFIG = os.path.join(HERE, "channels.json")
DEFAULT_CONTACTS = os.path.join(HERE, "contacts.json")
ROUTES = ("ops", "escalations", "dealers", "customers")


@dataclass
class ChannelConfig:
    """Parsed channels.json. Disabled entries are dropped while loading, so the rest of the
    code sees only what is switched on."""

    sources: dict[str, dict] = field(default_factory=dict)
    sinks: dict[str, dict] = field(default_factory=dict)
    routes: dict[str, dict] = field(default_factory=dict)
    contacts: dict[str, dict] = field(default_factory=dict)
    safety: dict = field(default_factory=dict)
    path: str | None = None

    @classmethod
    def load(cls, path: str | None = None) -> "ChannelConfig":
        """Load Hitachi/.env, then the config file. A missing file gives an empty, safe config."""
        load_dotenv(os.path.join(HITACHI, ".env"))
        path = path or os.environ.get("TOWER_CHANNELS_CONFIG") or DEFAULT_CONFIG
        if not os.path.isfile(path):
            return cls(routes={r: {"sinks": []} for r in ROUTES}, safety=_SAFE_DEFAULTS.copy())
        with open(path, encoding="utf-8") as handle:
            raw = json.load(handle)
        return cls.from_dict(raw, base_dir=os.path.dirname(os.path.abspath(path)), path=path)

    @classmethod
    def from_dict(cls, raw: dict, base_dir: str = HERE, path: str | None = None) -> "ChannelConfig":
        """Normalise a raw config. Routes may be a list of sink names or {"sinks": [...]}.
        contacts may be inline, or a path relative to the config file."""
        routes = {}
        for name in ROUTES:
            value = raw.get("routes", {}).get(name, [])
            routes[name] = {"sinks": list(value)} if isinstance(value, list) else {"sinks": list(value.get("sinks", []))}
        contacts = raw.get("contacts", {})
        if isinstance(contacts, str):
            contacts_path = contacts if os.path.isabs(contacts) else os.path.join(base_dir, contacts)
            contacts = {}
            if os.path.isfile(contacts_path):
                with open(contacts_path, encoding="utf-8") as handle:
                    contacts = json.load(handle)
        cfg = cls(
            sources={k: v for k, v in raw.get("sources", {}).items() if v.get("enabled", True)},
            sinks={k: v for k, v in raw.get("sinks", {}).items() if v.get("enabled", True)},
            routes=routes, contacts=contacts, safety={**_SAFE_DEFAULTS, **raw.get("safety", {})}, path=path)
        # A route that names a disabled sink just drops it.
        for route in cfg.routes.values():
            route["sinks"] = [s for s in route["sinks"] if s in cfg.sinks]
        return cfg

    def problems(self) -> list[str]:
        """Static checks for `python -m tower.channels check`."""
        from tower.channels.inbound import SOURCES
        from tower.channels.outbound import SINKS

        found = []
        for name, cfg in self.sources.items():
            if cfg.get("kind") not in SOURCES:
                found.append(f"source {name}: unknown kind {cfg.get('kind')!r} (known: {', '.join(sorted(SOURCES))})")
        for name, cfg in self.sinks.items():
            if cfg.get("kind") not in SINKS:
                found.append(f"sink {name}: unknown kind {cfg.get('kind')!r} (known: {', '.join(sorted(SINKS))})")
        for route in ("dealers", "customers"):
            email_sinks = [s for s in self.routes[route]["sinks"]
                           if SINKS.get(self.sinks[s].get("kind")) and SINKS[self.sinks[s]["kind"]].needs_address]
            if email_sinks and not self.contacts.get(route) and not self.safety.get("redirect_to"):
                found.append(f"route {route}: email sinks {email_sinks} but no contacts.{route} — every message will be skipped")
        return found


# Used when the config omits safety settings: cap at 200, no redirect, quiet on noise.
_SAFE_DEFAULTS = {"max_messages": 200, "redirect_to": [], "notify_noise": False}
