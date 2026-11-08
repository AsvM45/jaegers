# HE-06 adaptation round runbook

Issue: AsvM45/jaegers#6 (agent `claude-release`). Round two: **40 points**, kit opened Sat Nov 7 21:00 CT,
closes **Sun Nov 8 11:00 CT** per `RULES.md` (the team's working cutoff in `docs/CURRENT_STATE.md` is 10:30 CT;
the human release lead confirms the real one on #5). Nothing here uploads anything.

## Fallback strategy

The unchanged champion (`jaegers_entry/`, protected) refits its expert prior and gradient-boosted stacker on the
mounted kit's `train/` at prediction time, so it adapts to the new round's training machines with no code change.
That is the fallback. Bounded refits (e.g. re-estimated size regimes or forgetting rate, see #9/#17) are considered
only after the fallback package passes every check below, and only if they beat it on adaptation validation.

## Steps (Linux/WSL, CPython 3.13, exact pins)

The organizers rerun on Linux. CHAT measured Windows vs Linux forecasts differing by 0.107 and Linux default vs
pinned CPU dispatch by 0.090, far above the 1e-8 tolerance. So the **released CSV must be produced on Linux with the
same pinned NumPy CPU policy that `reproduce.json` declares**. Use the policy from the verified main-round package
(`research_runs/REVIEW_MAIN_9PM/code.zip`, file `reproduce.json`, on the release machine).

```sh
# 1. unpack the kit next to the repo; KIT points at its public/ folder (metadata.json, train/, validation/, test/)
# 2. environment: CPython 3.13 + requirements-runtime.txt (numpy 2.5.4, scikit-learn 1.9.1, ...)
python3.13 -m venv .venv-linux && .venv-linux/bin/pip install -r requirements-runtime.txt
# 3. one command: kit checks -> validation score -> test CSV twice -> CSV+ZIP -> cold rerun from the ZIP
.venv-linux/bin/python adaptation/run_adaptation.py --kit "$KIT" --main public \
    --out research_runs/adaptation --expect-round adaptation --env NPY_DISABLE_CPU_FEATURES=<policy from main package>
```

The run stops at the first failure and records evidence under `--out`:

| check | evidence |
|---|---|
| `round == adaptation`, `max_points == 40`, season id, all files present, no test truth files | `kit_report.json` |
| query IDs disjoint from main; no history tick at/after cutoff; payouts in {0,1,2,5,20} | `kit_report.json` |
| adaptation validation scored with **the kit's own** `check_submission.py` | `manifest.json` `validation` |
| test CSV format check (all IDs, simplex) | `manifest.json` `test_check` |
| two test runs identical (max normalized diff <= 1e-8) | `manifest.json` `repeat_max_diff` |
| ZIP built with the kit's `package_code`; root has README.md + reproduce.json | `release/code.zip` |
| cold rerun of the ZIP's own `reproduce.json` equals `submission.csv` within 1e-8 | `manifest.json` `cold_max_diff` |

Status `READY_FOR_HUMAN_REVIEW` means: upload `release/submission.csv` + `release/code.zip` together (matched by
`submission_sha256` / `code_zip_sha256` in `manifest.json`) through the **adaptation** Google Form. Main-round
artifacts are separate and untouched.

## Human release checklist (#5)

- [ ] Confirm the operative adaptation deadline and Form (11:00 CT kit vs 10:30 CT team note).
- [ ] `manifest.json` status is `READY_FOR_HUMAN_REVIEW`, round `adaptation`, 40 points, expected season id.
- [ ] Hashes of the two files you upload equal the manifest values.
- [ ] Upload both files in one Form response; keep the confirmation privately (not on GitHub).

## Dry run evidence (main kit, Windows, logic only; not a release)

`python adaptation/run_adaptation.py --kit public --main public --out <tmp> --expect-round main` on Windows 11,
CPython 3.13.5: status READY_FOR_HUMAN_REVIEW, validation 55.121615/60 (matches the known Windows score), test CSV
sha256 `82b3203e...` (matches the earlier Windows rerun), repeat diff 0.0, cold-rerun diff 0.0.
