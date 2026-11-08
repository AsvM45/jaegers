"""Communication channels for the control tower: Gmail, Outlook, Slack, Microsoft Teams, IMAP/SMTP,
PagerDuty, Google Chat and generic webhooks.

Inbound sources turn messages into events of the same shape as events.json. Outbound sinks deliver
what the tower decided (escalations, dealer notices, customer notices, event summaries) to people.

Nothing here calls Enterprise or touches action_log.jsonl. Dispatch runs after the tower has acted
and reads only the traces, so the scored log is identical with channels on or off.
Standard library only. Secrets come from environment variables, never from the config file.
"""
