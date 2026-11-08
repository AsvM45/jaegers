# Channels: Gmail, Outlook, Slack, Teams and more

The tower reads incidents from where people actually write them, and tells people what it did.
Standard library only, like the rest of the tower.

```
 Gmail ─┐                                                   ┌─ Slack (webhook or bot)
 Outlook┤   inbound.py      coordinator (unchanged)        ├─ Microsoft Teams (Workflows webhook)
 Slack ─┼─► events ──────►  understand → graph → act  ──►   ├─ PagerDuty (escalations)
 Teams ─┤   (same shape as   traces.json + action_log      ├─ Outlook / Gmail / SMTP (dealers, customers)
 IMAP ──┘    events.json)              │                    ├─ Google Chat
                                       └──► dispatch.py ───►└─ Webhook (ServiceNow, Jira, Zapier, n8n)
```

Dispatch reads the finished run and never calls Enterprise, so **`action_log.jsonl` is byte-identical
with channels on or off** (checked by `tests/test_channels.py`).

## Quick start

```bash
cd Jaeger_Main/Hitachi
cp tower/channels/channels.example.json tower/channels/channels.json   # gitignored
cp tower/channels/contacts.example.json tower/channels/contacts.json   # gitignored
# put secrets in Hitachi/.env (gitignored), e.g. SLACK_OPS_WEBHOOK_URL=https://hooks.slack.com/...
python -m tower.channels check                         # what's configured, which secrets are missing
python -m tower.channels test --sink slack_ops         # one test message

python -m tower.run --reader rules --notify dry-run    # batch run + outbox.jsonl, sends nothing
python -m tower.run --reader rules --notify send       # ...and actually deliver
python -m tower.channels notify --run runs/run1 --mode send   # deliver an existing run

python -m tower.channels watch --interval 60 --mode send      # live: poll, act, notify
TOWER_RUN_DIR=runs/live python -m tower.ui.server              # control tower over the live feed
```

## Routes

| Route | What | Default sinks |
|---|---|---|
| `escalations` | every `escalate` call: the human-in-the-loop hand-off, with the original message | Slack, Teams, PagerDuty |
| `ops` | one summary per real incident (noise only if `safety.notify_noise`) | Slack, Teams |
| `dealers` | one message per dealer per event: delayed orders and stop-sale VINs | Outlook |
| `customers` | one per contacted owner/buyer | Outlook |

## Guardrails

1. Only calls the enterprise **accepted** (`ok: true`) produce a message. If a trace and the log disagree, that event sends no dealer or customer mail.
2. `dry-run` writes `outbox.jsonl` and sends nothing. The UI shows it under **Notifications**.
3. `safety.redirect_to` sends every email to a test inbox. It is on in the example config.
4. Without a redirect, email goes only to ids in `contacts.json`. The company tables have no addresses, so nothing is guessed.
5. `safety.max_messages` (default 200) caps one dispatch. Escalations go first, then ops, then dealers, then customers, so bulk mail never crowds out a page.
6. `channels_sent.json` records every delivered key, so a re-run never sends a message twice. PagerDuty also dedups on the event id.
7. Loop guard: every outbound post carries `[control-tower]`. Inbound skips it, along with bot and app posts.
8. A failing sink is recorded as `failed` and the other sinks still deliver.
9. Secrets never sit in config files. Each config entry names the environment variable that holds its secret (`*_env`).

## Provider setup

**Slack.** For posting, create an app with an incoming webhook and set `SLACK_OPS_WEBHOOK_URL`. Bot posting (`chat:write`) is also supported. For reading, use a bot token (`SLACK_BOT_TOKEN`) with `channels:history` (and `groups:history` for private channels). Add `reactions:write` if you set `"react"`. Invite the bot to the channel.

**Microsoft Teams.** For posting, open the channel's **Workflows** menu and choose "Post to a channel when a webhook request is received". Set `TEAMS_WEBHOOK_URL`. Graph cannot post channel messages with application permissions, so the webhook is the supported path. For reading, register an Entra app (`MS_TENANT_ID`, `MS_CLIENT_ID`, `MS_CLIENT_SECRET`) with `ChannelMessage.Read.All`, or use resource-specific consent on the one team.

**Outlook / Exchange Online.** Use the same Entra app with the application permissions `Mail.Read` (`Mail.ReadWrite` if `mark_read`) and `Mail.Send`. Restrict it to the tower mailbox with `New-ApplicationAccessPolicy`.

**Gmail.** Create an OAuth client in Google Cloud and enable the Gmail API. Get a refresh token with the scopes `gmail.readonly` (or `gmail.modify` if `mark_read`) and `gmail.send`. Set `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET` and `GOOGLE_REFRESH_TOKEN`. A Gmail filter that labels ops mail `control-tower` matches the example `query`.

**IMAP / SMTP.** Any provider works: Gmail or Outlook app passwords, SES, SendGrid, Mailgun or on-prem. Configure `host`/`port` plus the `*_env` credentials.

**PagerDuty.** Create an Events API v2 integration on a service and set `PAGERDUTY_ROUTING_KEY`.

**Google Chat.** Use a space webhook: set `GOOGLE_CHAT_WEBHOOK_URL`.

**Webhook (ServiceNow, Jira, Zapier, n8n).** Each message is POSTed as JSON. With `secret_env`, the request also carries `X-Tower-Signature: sha256=HMAC(secret, "<X-Tower-Timestamp>.<body>")`.

## Live events and the simulation calendar

Live messages go through the same reader, which resolves relative dates ("next Friday") against the simulation's today, 2027-03-08 (`tower/calendar_util.py`). Live events get ids like `SLACK-…`, `GMAIL-…` or `OUTLOOK-…` and are kept in `runs/live/`, apart from the scored `runs/run1`.

## Tests

```bash
python tests/test_channels.py     # 23 tests, no network
```
