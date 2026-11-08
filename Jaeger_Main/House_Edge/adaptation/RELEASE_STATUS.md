# HE-06 adaptation release status

**Status: `BLOCKED_KIT_MISSING`**

Agent: `grok-he06`  
Branch: `agent/grok-he06-adaptation-takeover`  
Worktree: `C:\Users\asvat\OneDrive\Documents\GitHub\Datathon2026\jaegers-he06-adaptation-takeover`  
Issue: https://github.com/AsvM45/jaegers/issues/6  
Claim: https://github.com/AsvM45/jaegers/issues/6#issuecomment-6718627255

No adaptation submission CSV or ZIP was produced. Nothing was uploaded. This is not organizer acceptance.

## Remote state

Fetched with `git fetch --all --prune --tags` before the branch was created, and the tips had not moved:

| Ref | SHA |
|---|---|
| `origin/main` | `0492d434501a5e73d3e99fb7ce9f7ee7bd59f581` |
| `origin/agent/claude-release-he06-adaptation` | `9c77b580ea2a7650e9050c1e3aa3198df04642c0` |

Claude's branch was 1 commit ahead of the merge-base and 21 commits behind `origin/main`. This branch was created from that Claude tip, then `origin/main` was merged with no conflicts. The merge kept Claude's three adaptation files and took main's version of every other file. Claude's branch was not pushed or rewritten.

Inherited files, not rewritten:

- `Jaeger_Main/House_Edge/adaptation/run_adaptation.py`
- `Jaeger_Main/House_Edge/adaptation/README.md` (status line and the four CPU pins read from the frozen ZIP)
- `Jaeger_Main/House_Edge/tests/test_adaptation_release.py`

Open PR #61 (`agent/claude-release-he06-adaptation`) already changes the same three inherited paths. The collaboration checker compares exact filenames across open PRs, so this branch's PR is expected to collide with #61. Claude's PR was not closed.

## Kit

**Not found.** Every `metadata.json` under `Datathon2026`, `Downloads`, `Desktop`, and `Documents` (depth 6) that declared a `round` field said `round: main`. WSL `/home` had no House Edge kit. The repo copy `Jaeger_Main/House_Edge/public/metadata.json` is the main round:

- `round`: `main`
- `max_points`: `60`
- `season_id`: `5fffdc4d0c700bbf61c3f911`
- `suite_version`: `experimentation-suite-v3`

`adaptation/run_adaptation.py` rejects that tree when `--expect-round adaptation` because the round, point total, and query IDs are the main round. It was not used as the adaptation kit.

The orchestrator requires a separate organizer `public/` directory with:

- `metadata.json` where `round` is `adaptation`, `max_points` is `40`, and `season_id` is 24 hex characters
- `train/queries.csv`, `train/history.csv`
- `validation/queries.csv`, `validation/history.csv`, `validation/targets.csv`, `validation/reference.csv`, `validation/conditions.csv`
- `test/queries.csv`, `test/history.csv`
- no `test/targets.csv` and no `test/labels.csv`
- the kit's own `check_submission.py` beside that `public/` folder (the repo checker is only a fallback)

`RULES.md` says the second kit opens Saturday, November 7, 2026 at 9:00 PM Central and contains training data, validation answers, and test histories. It also says each round has its own Google Form and that form links will be announced. No adaptation form URL was independently verified in this pass. Obtain the kit from the organizer channel that published the round-two files. Do not reuse `Jaeger_Main/House_Edge/public`.

Because the kit is absent there is no adaptation validation score, no adaptation query-id coverage check, no repeat diff, and no cold-run diff.

## Environment

| Item | Observed |
|---|---|
| Windows CPython | 3.13.2 (`py -3.13`) |
| Installed on that interpreter | numpy 2.2.6, pytest 9.2.0; `joblib` and `scikit-learn` are not installed |
| WSL | Ubuntu 22.04, CPython 3.10.12 only; `python3.13` is not installed |
| Runtime pins the release needs | `requirements-runtime.txt` (numpy 2.5.4, scikit-learn 1.9.1, joblib 1.6.0) |

A Windows run is not an adaptation release. Prior measurements cited in the runbook put Windows-versus-Linux forecast differences around 0.107 and unpinned-versus-pinned Linux CPU dispatch around 0.090, both far above the 1e-8 tolerance.

CPU policy read from the frozen main ZIP member `reproduce.json` (read-only):

```text
NPY_DISABLE_CPU_FEATURES=X86_V3,X86_V4,AVX512_ICL,AVX512_SPR
OPENBLAS_CORETYPE=Nehalem
OMP_NUM_THREADS=2
OPENBLAS_NUM_THREADS=2
```

Command to run only after the real kit is mounted and Linux CPython 3.13 with `requirements-runtime.txt` exists. Run from `Jaeger_Main/House_Edge`. This command was not executed, because both the kit and that Linux interpreter are missing:

```sh
.venv-linux/bin/python adaptation/run_adaptation.py --kit "$KIT" --main public \
    --out research_runs/adaptation --expect-round adaptation \
    --env NPY_DISABLE_CPU_FEATURES=X86_V3,X86_V4,AVX512_ICL,AVX512_SPR \
    --env OPENBLAS_CORETYPE=Nehalem \
    --env OMP_NUM_THREADS=2 \
    --env OPENBLAS_NUM_THREADS=2
```

`$KIT` must be the adaptation kit's `public/` directory. `--out` must be a new directory. The run writes `kit_report.json`, validation and test forecasts, `release/submission.csv`, `release/code.zip`, and `manifest.json`. Success is `manifest.json` status `READY_FOR_HUMAN_REVIEW` with `repeat_max_diff` and `cold_max_diff` at most 1e-8.

## Artifacts

| Artifact | Path | SHA-256 |
|---|---|---|
| Adaptation `submission.csv` | not produced | n/a |
| Adaptation `code.zip` | not produced | n/a |
| Frozen main `submission.csv` | `C:\Users\asvat\OneDrive\Documents\GitHub\Datathon2026\jaegers\Jaeger_Main\House_Edge\research_runs\REVIEW_MAIN_9PM\submission.csv` | `b718f2d5e14a5a508d3c6c3658259042228a7a4d38e0221513e46e5590d9babf` (195,579 bytes) |
| Frozen main `code.zip` | `C:\Users\asvat\OneDrive\Documents\GitHub\Datathon2026\jaegers\Jaeger_Main\House_Edge\research_runs\REVIEW_MAIN_9PM\code.zip` | `9a8a9e0e18a8d21d30474b3e007156c1f19be4f693dd3b2235019be830d3001f` (8,263 bytes) |

The frozen pair lives only in the original checkout. It is gitignored and is not in this worktree. It was hashed by reading the bytes before this report and again after the report file existed. Both SHA-256 values still match the table. It was not extracted onto itself, regenerated, or replaced. ZIP members seen: `README.md`, `jaeger_model.py`, `params.json`, `predict.py`, `reproduce.json`, `requirements.txt`.

## Tests

Focused adaptation tests, from `Jaeger_Main/House_Edge`, Windows CPython 3.13.2:

```text
py -3.13 -m pytest tests/test_adaptation_release.py -q --tb=short
8 passed in 22.60s
```

Exit code 0. Those tests check the real main kit as a main round (1,536 test queries), reject that same kit as adaptation, accept a re-identified two-episode fixture, and flag late ticks, unknown payouts, hidden-test labels, and a missing validation file. They also check env pinning, ZIP root members, and normalized probability diffs. They do not score an adaptation round.

Collecting the rest of `Jaeger_Main/House_Edge/tests` in this interpreter stopped with 16 collection errors, all `ModuleNotFoundError: No module named 'joblib'`. `scikit-learn` is also absent. Claude's earlier "148 passed" result was not reproduced here and is not claimed. The global interpreter was not given a new research stack, because that would not supply the missing kit or a Linux 3.13 runtime.

## Deadlines and form

These are different channels. This report does not invent an extension.

- House Edge `RULES.md`: adaptation closes **Sunday, November 8, 2026 at 11:00 AM Central**. Scoring for that round is 40 points. The Google Form link is described as announced by the organizers and was not verified here.
- Issue #5 records the TAMU Datathon Devpost cutoff as **Sunday, November 8, 2026 at 10:30 AM Central** (`2026-11-08T16:30:00Z`). That overall Devpost clock does not by itself move the House Edge adaptation form.

## Compliance risks

- Shipping the main-round CSV/ZIP, or a Windows forecast of the main kit, as the adaptation entry would be the wrong round, the wrong point scale, and the wrong query IDs.
- Producing the adaptation CSV on Windows, or on Linux without the four CPU pins above, can miss the 1e-8 repeatability tolerance.
- A challenger must not replace the unchanged champion until it has an adaptation validation score, a cold ZIP reproduction, and explicit human approval. No challenger was trained.
- Open PR #61 overlaps this branch's inherited paths. Merging both would be a duplicate release path. The human chooses which PR to keep.
- Main-round eligibility after Saturday 9:00 PM Central is a separate #5 question. This report does not reopen it.

## What the human release lead does

1. Download the organizer adaptation kit. Do not substitute `Jaeger_Main/House_Edge/public`.
2. Use Linux CPython 3.13 and `requirements-runtime.txt`. This machine's WSL is 3.10.12, so the release command cannot be finished here until that runtime exists.
3. Run the command in the runbook. Require every adaptation query id once, five finite nonnegative normalized probabilities, two forecasts within 1e-8, and a cold offline ZIP that matches the CSV. Record both SHA-256 values from `manifest.json`.
4. Confirm the adaptation form and whether 10:30 AM or 11:00 AM Central is the clock that actually accepts the House Edge files.
5. Upload only the new adaptation CSV and ZIP. Keep the receipt private. Leave `REVIEW_MAIN_9PM/submission.csv` and `code.zip` untouched.
6. Review this PR. Do not treat a passing unit test or a GitHub merge as an organizer submission. If the collaboration check fails only because PR #61 touches the same adaptation paths, resolve that overlap by choosing one open PR. Do not force-push Claude's branch.
