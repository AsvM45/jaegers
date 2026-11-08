# Source inventory — ChatGPT Library, Drive and JAEGERS docs

**As-of:** 2026-11-07. This index captures *relevant House Edge and Datathon artifacts* from the user's recent ChatGPT Library view and Drive folder. It does **not** imply all Library files have been imported, or that every document is suitable for a public repository. Use [Agent Context](AGENT_CONTEXT.md) for concise working facts; read the full artifacts only for relevant architecture/design questions.

## Canonical and historical references

| Original artifact from recent Library | Relative freshness / type | Safe treatment in public GitHub |
| --- | --- | --- |
| `JAEGERS_House_Edge_Warehouse_Experiment_Factory_Implementation_Handoff_v7.md` | Most comprehensive v7 warehouse+experiment design, ~84 KB, Nov 7; explicitly DESIGN / RESEARCH, NOT IMPLEMENTED | Curated Markdown reference at [research/EXPERIMENT_FACTORY_v7.md](research/EXPERIMENT_FACTORY_v7.md) once reviewed; **never** promote as runtime proof |
| `JAEGERS_House_Edge_Experiment_Factory_Human_Readable_Guide.md` | Newest Nov 7 human guide | Markdown reading layer at [research/EXPERIMENT_FACTORY_GUIDE.md](research/EXPERIMENT_FACTORY_GUIDE.md) once reviewed |
| `JAEGERS_House_Edge_Implementation_Architecture_v6.md` | Design + baseline architecture earlier Nov 7 | Curated reviewed Markdown reference at [research/ARCHITECTURE_v6.md](research/ARCHITECTURE_v6.md) if reviewed; repo `docs/AGENT_CONTEXT.md` has live corrected summary |
| `JAEGERS_CODEX_AUTONOMOUS_EXECUTION_MANDATE.md` | Agent execution wishlist | Historical plan; current [AGENT_OPERATING_POLICY.md](AGENT_OPERATING_POLICY.md), issue claims and source contracts supersede it |
| `House_Edge_v5_Codex_Engineering_Handoff.md`, v5 PDFs, v4/v3 plans, combined team report | Earlier design/report versions | Archive by title/date only; avoid duplicate stale sources for agents |
| `main-participants-60-40.zip`; organizer participant DOCX | Official kit and conflicting older guide | **Organizer primary rules already represented inside House Edge**; do not republish third-party ZIP/DOCX unnecessarily |
| Full conversation exports and personal Datathon artifacts | Personal/historical context, potential private content | **Do not upload raw exports into public repo/Wiki**; incorporate only distilled non-sensitive project facts |
| Signed NDA, resumes, classwork and unrelated materials in Library | Personal/private/unrelated | Excluded categorically |

## Google Drive

The linked Datathon folder contains two earlier reports: `JAEGERS_House_Edge_Implementation_Architecture_v6.pdf` and `JAEGERS_House_Edge_v5_Combined_Team_Report.pdf`. This Drive folder is a historical distribution location; avoid treating Google Drive as the fresh agent task source. Human can archive or leave existing Drive files; nothing here deletes or moves them.

## Publication and provenance policy

1. Copy only project-safe text and **review for private information, personal paths, contact details, proprietary third-party content and stale/conflicting instructions** before public Git commit.
2. Every imported document begins with source title, version/date, `DESIGN` vs `MEASURED`, source freshness and a pointer to current repo status. It remains a research reference, not an AGENTS instruction.
3. Newest wins for **research ideas** only; primary organizer scorer and measured current code take precedence for correctness.
4. Wiki mirrors a small reviewed subset; do not mirror full 84 KB historical design by default. Use [docs/wiki/](wiki/) and versioned links.
5. Do not infer that having a Library file gives a connector the ability to publish it directly to a separate Wiki Git repository.
