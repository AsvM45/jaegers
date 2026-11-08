# Start here: JAEGERS Codex/Astra v5

Work in `Jaeger_Main/House_Edge`. **First action is native `/plan` mode**, paste `.codex/tasks/00-astra-plan-only.md` (from House Edge CWD `../../.codex/tasks/00-astra-plan-only.md`). Read your actual checkout and team changes; DO NOT IMPLEMENT ANYTHING in the plan-only pass.

- Latest *audited public* HEAD b78abe75 (claimed 55.12/60 public validation); it may already be stale. Local dirty tree overrides snapshot.
- Core source: `jaegers_entry/` and existing official kit/checker. Don't replace current model with starter baseline.
- P0 blockers: historical stacker query-time `signal` used in older pseudo-training rows, validation-target-derived `SIZE_REGIMES`, missing NumPy+sklearn dependency pins, stale README, unverified official checker/cold ZIP/reproduction/receipt, 60/40 versus older 80/20 guide conflict.
- Plan phase gates: `../../docs/PLAN_GATES.md`; issue candidates `../../docs/ISSUE_BACKLOG.md`; validation contract `../../docs/VALIDATION_PROTOCOL.md`; detailed spec `../../docs/ENGINEERING_SPEC.md` (read only relevant sections).
- Native skills are at repo root `.agents/skills/`. Prefer task-matched skill on demand; avoid loading 500KB conversation exports into every coding prompt.
- Never commit, push, submit, overwrite teammates, publish credentials, or claim a hidden score without explicit authorization/evidence.
