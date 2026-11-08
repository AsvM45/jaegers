# Staged JAEGERS Wiki (not yet published)

These Markdown pages are **Git-reviewed drafts** for the separate GitHub Wiki repository. The canonical versioned technical docs remain in `docs/`; the Wiki is a readable mirror after human approval.

**GitHub repository settings observed:** Wiki feature enabled, Discussions disabled; the available GitHub connector can update the main repo but **cannot push to the separate `jaegers.wiki.git` repository**. Nothing under `docs/wiki/` is automatically a live Wiki page.

## Publish safely

1. Review and merge this docs PR (human approval).
2. Create the first page via the repository Wiki UI if none exists.
3. Locally clone `https://github.com/AsvM45/jaegers.wiki.git`.
4. Copy vetted Markdown pages from `docs/wiki/` to wiki root; ensure relative links and page names remain valid.
5. Human-reviewed commit/push to Wiki repository, or copy manually through UI. Never auto-sync raw Library files, private receipts, signed NDAs, credentials or full chats.
6. Link Wiki pages back to the canonical GitHub `docs/` files/commit.
