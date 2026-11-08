---
name: jaegers-antigravity-review
description: "Perform an independent, read-only adversarial code review of the House Edge statistical pipeline, temporal leakage, model provenance, release verification and experiment claims without modifying Codex-owned files."
---

# Antigravity: independent verification

## Inputs
- The actual local Git branch/HEAD, `AGENTS.md`, nested House Edge `AGENTS.md`, `docs/CURRENT_STATE.md`, `docs/VALIDATION_PROTOCOL.md`, current GitHub issue and recent diffs.
- Targeted skills: `jaegers-leakage-audit`, `jaegers-evaluation`, `jaegers-release-preflight`.

## Procedure
1. Define the precise statement to verify and its evidence level: source inspection, executed local test, cold Linux packaging, authorized organizer acknowledgment, or hidden score (unavailable).
2. Audit feature lineage, exact tick cutoffs, missing ticks, sibling-machine cutoff, episode-group folds, query-time signal in historical rows, validation-target-derived constants, output simplex, dependency pins and offline runner.
3. Add **isolated new tests** only if delegated; never edit original `jaegers_entry/`, common `research/` implementation files, `docs/CURRENT_STATE.md`, or release outputs without coordination.
4. Report findings by severity with reproducible minimal fixtures, exact paths/lines, affected metrics and a proposed fix assigned to its file owner.
5. Preserve negative results and uncertainty; don't treat a locally reported validation score as independently verified merely because it is documented.

## Handoff
Comment on the assigned issue or provide a concise review artifact. Stop at the file ownership boundary and request integration via a PR. The reviewer must not promote or submit a model.
