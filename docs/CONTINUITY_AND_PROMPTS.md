# Codex continuity, context efficiency and local execution

## Never load entire transcript by default
Use the 1-page `AGENTS.md` chain, `docs/CURRENT_STATE.md` for latest verified snapshot, one relevant skill, and the single task file. The deep spec is reference-only; read sections on demand. The two user conversation exports are in the package's `reference_inputs/`, **outside** `repo_overlay/` intentionally to avoid context bloat.

## Astra plan-only sequence
1. Install overlay dry-run and apply only if no collision; start `codex` from `Jaeger_Main/House_Edge/`.
2. Use native `/plan` mode, paste `.codex/tasks/00-astra-plan-only.md` as the single task. The first pass is read-only: no file writes, dependency install, commits, prompts to implement.
3. Review plan for actual local HEAD, uncommitted teammate changes, official release blockers, owner isolation, time left, and tasks with acceptance.
4. Once approved, switch to implementation mode and give **one** `tasks/01-...` work unit at a time; require status/commands/checks. Do not re-paste huge conversation exports.

## Trial record needed for reproducibility
Each trial gets: unique content-derived ID, exact code SHA or dirty-tree digest, resolved config and feature flags, raw data hashes, fold ID manifest, sample source (real historical vs query labels vs true validation), validation-target exposure yes/no, current signal historical availability, trained artifact, output SHA, per-condition error if available, paired episode deltas, run status/error, CPU/wall and versions. Store append-only artifacts; coordinate writers using one registry owner.

## Session restart note template
`Current branch/HEAD: ...; dirty paths: ...; approved phase: ...; completed test command and result: ...; champion source/config/score provenance: ...; accepted main submission receipt and hashes (if any): ...; next bounded task: ...; blockers: ...`.

## Best prompt for *implementation* (only after plan approved)
`Implement only HE-V5-XX from ../../docs/ISSUE_BACKLOG.md on my approved local working tree. Confirm HEAD/status, follow applicable AGENTS and the relevant skill, preserve current JAEGERS entry and Hitachi, add the smallest tested change, run exact affected checks, record metrics with source/exposure, then STOP. No push/submit/commit.`
