# JAEGERS source migration audit — updated 2026-11-08

## Decision

GitHub `main` is the intended versioned knowledge base; active docs are `docs/research/`, `docs/architecture/`, `docs/science/`, `docs/runbooks/`, `docs/agents/`. A dated ChatGPT continuity source points to these. Wiki pages are source-controlled in `docs/wiki/`; a published separate Wiki was **not verified**. GitHub Projects is enabled but a live board and API write support were not verified.

## Shared Drive source disposition

- The original Warehouse Experiment Factory v7 and Human Guide texts were read completely from connected Drive and integrated conceptually into live research/design docs. Their complete recovered text is preserved in [the dated source archive](README.md), distinct from current implementation.
- The Nov 7 architecture/code PDF is **obsolete as a current-state report**. Useful model/system concepts are captured in [architecture](../../architecture/SYSTEM_OVERVIEW.md), [science](../../science/EVALUATION_AND_PROVENANCE.md) and [experiment design](../../research/EXPERIMENT_FACTORY_v7.md). Do not blindly publish the old text extract.
- The personal math/stats PDF is **explicitly excluded** from GitHub, GitHub Wiki, and this ChatGPT source package. Its previous staging in an unmerged PR branch must not enter main/history.
- Google Drive originals remain unchanged as backups; nothing automatically archives or deletes them.

## ChatGPT project source set

The project view reported 23 files, including duplicated enormous conversation exports (~548KB and ~61KB), a dated coordination handoff, original organizer guides/kits, and 13 screenshots. The two long exports and Nov 7 handoff are historical-only; screenshots usually don't belong in default agent context. Retain the official House Edge ZIP + participant DOCX as a paired primary-source conflict, retain Hitachi challenge pack only when needed, and import the compact `JAEGERS_PROJECT_CONTEXT_2026-11-08.md` as primary continuity.

## Evidence and privacy

Source conflicts (technical kit 60/40 vs older participant DOCX 80/20; main/adaptation schedule vs wider Devpost) remain explicit until organizer decision. Development-exposed public score is not hidden performance. Local artifacts/receipts are not in Git. Mock Databricks tests are not a workspace run. The public GitHub repository should never receive private organizer tokens, hidden labels, personal conversations, NDA documents or a personal study guide.

## Integration and retirement gates

1. Confirm no personal guide text appears in the final Git tree/merge diff.
2. Ensure original v7 and human Markdown source strings preserve retrieved text and current docs incorporate their engineering concepts rather than merely archiving them.
3. Validate links and governance CI; check main readback and current HEAD.
4. Only then set Drive folder to archival-only from the team's process. Retain backups until human decides deletion.
5. Update the ChatGPT Project source list manually with the provided ZIP; no GitHub action alters that source list.
