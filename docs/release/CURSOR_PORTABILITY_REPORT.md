# Cursor portability report — issue #46

**Recommendation: `VERIFIED WITH LIMITATIONS`**

The frozen House Edge pair in the original local checkout is structurally valid against the organizer submission contract and the released main-test query IDs. This is a packaging and portability witness. It is not an organizer receipt, a hidden-test score, or a second-machine reproduction.

`SECOND_HOST_NOT_TESTED`

`REPRODUCTION_NOT_RERUN`

No organizer receipt was found in the repository docs, issue #5, or issue #18. Nothing was uploaded.

## Scope

| Item | Value |
| --- | --- |
| Issue | #46 |
| Claim | https://github.com/AsvM45/jaegers/issues/46#issuecomment-6717061405 |
| Agent | Cursor Grok agent for issue #46 (`cursor-he46`) |
| Branch | `agent/cursor-he46-portability` |
| Worktree | `C:\Users\asvat\OneDrive\Documents\GitHub\Datathon2026\jaegers-he46-portability` |
| Base | `origin/main` at `f77c112ba15e562a21e7be74dcf1feada581c238` |
| Writable files | `Jaeger_Main/House_Edge/tools/cursor_portability_probe.py`, `Jaeger_Main/House_Edge/tests/test_cursor_portability_probe.py`, `docs/release/CURSOR_PORTABILITY_REPORT.md` |

The probe reads `submission.csv` and `code.zip` and inspects the ZIP in memory. It does not extract into the submission directory, does not open those artifacts for writing, and does not run `predict.py`.

## Frozen artifact provenance

Original checkout, gitignored `research_runs` directory. Both files stayed `ReadOnly`. SHA-256 and size were recorded before the unit tests, after the probe, and again with `Get-FileHash`. They did not change.

| File | Absolute path | Bytes | SHA-256 | mtime (UTC) |
| --- | --- | ---: | --- | --- |
| `submission.csv` | `C:\Users\asvat\OneDrive\Documents\GitHub\Datathon2026\jaegers\Jaeger_Main\House_Edge\research_runs\REVIEW_MAIN_9PM\submission.csv` | 195579 | `b718f2d5e14a5a508d3c6c3658259042228a7a4d38e0221513e46e5590d9babf` | 2026-11-08T02:35:33.581801+00:00 |
| `code.zip` | `C:\Users\asvat\OneDrive\Documents\GitHub\Datathon2026\jaegers\Jaeger_Main\House_Edge\research_runs\REVIEW_MAIN_9PM\code.zip` | 8263 | `9a8a9e0e18a8d21d30474b3e007156c1f19be4f693dd3b2235019be830d3001f` | 2026-11-08T02:35:33.595901+00:00 |

These match the hashes recorded in `docs/CURRENT_STATE.md` and issue #5. The artifacts were not regenerated.

Released test queries used by the probe:

`Jaeger_Main/House_Edge/public/test/queries.csv` in this worktree.

- 1536 unique IDs, same order as the original checkout's copy.
- Git blob in both checkouts: `970142d6901a7dcea9b96e4c26e4741981ba08f1`.
- On-disk bytes differ only by CRLF. Worktree SHA-256 `3d8065626e161fd3e7b988b735583a23d4c989eb64c8ae90f200b726c02e42b9` (LF, 123518 bytes). Original checkout SHA-256 `f299006b964df3aab11075975a940490013022ef666bc4f9f2b6e8b8c0b4969f` (CRLF, 125055 bytes). Newline-normalized bytes are equal, and the query-id set matches the frozen CSV exactly.

## Commands and results

From `C:\Users\asvat\OneDrive\Documents\GitHub\Datathon2026\jaegers-he46-portability`:

```text
python -m unittest Jaeger_Main/House_Edge/tests/test_cursor_portability_probe.py -v
```

Result: **15 tests, 0 failures, 0 errors, OK in 1.774s.** pytest is not installed in this interpreter (`Python 3.13.2`); the suite is `unittest`.

Covered failures: bad header, wrong row count, duplicate IDs, non-numeric probabilities, negative values, values above 1, NaN, Inf, rows that do not sum to 1, missing CSV, missing ZIP, missing ZIP members, unpinned and `>=` requirements, missing local entrypoint files, empty README, wrong output path, incorrect hashes, unsafe archive names (`../evil.txt`, `/tmp/evil.txt`, `C:/evil.txt`, `..\evil.txt`, `foo/../../evil.txt`), a raw ZIP member containing a null byte, a symlink member, a truncated ZIP, a corrupted ZIP, a garbled CSV, a member-count cap, and a refusal to write JSON into the artifact directory.

Read-only probe, exit code 0, every required check `PASS`:

```text
python Jaeger_Main/House_Edge/tools/cursor_portability_probe.py --csv C:\Users\asvat\OneDrive\Documents\GitHub\Datathon2026\jaegers\Jaeger_Main\House_Edge\research_runs\REVIEW_MAIN_9PM\submission.csv --zip C:\Users\asvat\OneDrive\Documents\GitHub\Datathon2026\jaegers\Jaeger_Main\House_Edge\research_runs\REVIEW_MAIN_9PM\code.zip
```

Observed summary: `STRUCTURAL: PASS`, `not_passed: none`, normalization tolerance `1e-06`, reproduction tolerance `1e-08`, and the tokens `REPRODUCTION_NOT_RERUN` and `SECOND_HOST_NOT_TESTED`.

The same CSV also passed the organizer CLI, which is a thin wrapper over `slot_forecasting.io.read_submission`. Working directory does not matter because `PYTHONPATH` pointed at `Jaeger_Main/House_Edge`:

```text
python Jaeger_Main/House_Edge/check_submission.py <frozen submission.csv> --data Jaeger_Main/House_Edge/public --split test
```

Observed output:

```text
VALID FORMAT: 1536 queries | main | test
Season: 5fffdc4d0c700bbf61c3f911
SHA-256: b718f2d5e14a5a508d3c6c3658259042228a7a4d38e0221513e46e5590d9babf
Test answers are private; this check does not calculate your event score.
Local check only. Nothing was uploaded. Acceptance and code reproduction are separate.
```

Exit code 0. That checker does not score hidden test answers.

### Frozen ZIP contract that passed

Root members: `README.md` (1147 bytes), `reproduce.json`, `requirements.txt`, `predict.py`, `jaeger_model.py`, `params.json`. Six members, 20330 uncompressed bytes, `zipfile.testzip` clean.

Declared command:

```text
env NPY_DISABLE_CPU_FEATURES=X86_V3,X86_V4,AVX512_ICL,AVX512_SPR OPENBLAS_CORETYPE=Nehalem OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 python predict.py --data /data --out /output/submission.csv
```

`reproduce.json` has exactly `image` = `python` and that command array. Exact pins: `numpy==2.5.4`, `scikit-learn==1.9.1`, `scipy==1.18.1`, `joblib==1.6.0`, `threadpoolctl==3.8.0`, `cloudpickle==3.1.2`, `narwhals==2.28.0`. The entrypoint references `jaeger_model.py` and `params.json`, and both are in the archive. Upload sizes are within the RULES.md caps (CSV 10,000,000 bytes, ZIP 100,000,000 bytes; MB means 1,000,000 bytes).

## Interfaces reused and reimplemented

Reused, and still checked independently:

- `slot_forecasting.io.read_queries`
- `slot_forecasting.io.read_submission` (the validator behind `check_submission.py`)
- `slot_forecasting.submission_contract.inspect_archive`
- `slot_forecasting.submission_contract.safe_name`
- `slot_forecasting.schema.SUBMISSION_COLUMNS`
- `slot_forecasting.schema.SUM_TOLERANCE` (`1e-6`)

Reimplemented beside those calls: SHA-256 and size identity, CSV header/row/duplicate/finite/range/sum checks, `zipfile.testzip`, unsafe path checks (absolute, `..`, backslash, drive prefix, null byte, device names, symlink mode), member-count and uncompressed-size caps, `requirements.txt` exact `==` pins, and the static entrypoint file check.

Judgment calls:

- A row passes the sum check when `abs(sum - 1) <= 1e-6`. RULES.md and `SUM_TOLERANCE` use `1e-6`. The reproduction comparison tolerance is a different number, `1e-8`, and applies after normalization to a rerun. This probe does not rerun inference, so it records `1e-8` and does not loosen the `1e-6` row check to hide a bad simplex.
- Dependency lines must be exact `==` pins. A bare name or `>=` fails. An empty requirements file would pass only if the README states "Python standard library only". The frozen file has seven exact pins.
- Archive expansion is skipped when the central directory declares more than 5,000 members or more than 512 MiB uncompressed (`submission_contract` caps). Inspection stays in memory.
- The entrypoint scan reads the declared `.py` file and requires local `import` / quoted `.py` / `.json` names to exist in the ZIP. It does not execute them.
- If size and SHA-256 stay the same, an mtime-only touch does not fail the unchanged check. In this run, size, SHA-256, and mtime were all unchanged.

## Environment and reproduction

Witness machine: hostname `dauntless`, `Windows-11-10.0.26300-SP0`, CPython `3.13.2 (MSC v.1942 64 bit AMD64)`.

`SECOND_HOST_NOT_TESTED`. WSL reports `Ubuntu-22.04` stopped on this same PC. That is not a second physical host, and it was not started. An SSH config exists on this account; no host was contacted. No cloud VM was started and no money was spent.

`REPRODUCTION_NOT_RERUN`. The frozen command writes `/output/submission.csv`. Running it here would be a same-machine Windows execution, which earlier release evidence already showed can move probabilities by much more than `1e-8`, and it would not satisfy the cross-host question. The structural checks were completed instead. The frozen files were left untouched.

Prior release evidence, quoted from the local read-only `verification.json` beside the frozen pair and from issue #5, says two cold Linux Python 3.13 runs on one x86-64 host, under two CPU policies, reproduced all 1,536 queries with identical CSV bytes and maximum normalized difference 0. The recorded platform string in that file is `Linux-6.6.87.2-microsoft-standard-WSL2-x86_64-with-glibc2.35`. This report does not relabel that WSL2 run as independent hardware. Public development validation recorded there is `55.09081500826751/60`. Hard aggregate scratch-quota enforcement was already reported as unavailable. Earlier Windows and default-Linux CPU-dispatch packages failed portability (maximum differences about 0.1069 and 0.0903) and are a different pair.

## Public validation is not hidden-test performance

A passing package check shows that the CSV matches the released test-query IDs and the probability contract, and that the ZIP satisfies the offline layout. `check_submission.py --split test` states that test answers are private and that the check does not calculate the event score. The public validation number above used development-exposed targets. It is not a hidden-test score, a leaderboard position, or an acceptance decision.

## As-of and historical-signal limits

A packaging checker cannot settle feature timing. Documented concerns, unchanged by this witness:

- Issue #5 and `docs/CURRENT_STATE.md`: historical stacker rows have been described as using final-cutoff query signal, final history coverage, and an expert prior that can see later observations relative to the historical example. `RULES.md` requires strict as-of features for historical training rows too. The audit calls this train/serve skew, and it distinguishes that from hidden test-answer leakage. Historical per-tick `signal(t)` is not separately released. Query-time signal at the cutoff is allowed. Compliance is unresolved until an organizer clarification.
- `SIZE_REGIMES` and parameter selection used public validation targets. That is allowed development selection in the released kit, and it means 55.09 is development-exposed.
- The frozen README itself says historical query-signal availability remains unresolved and that size regimes and parameter selection used public validation targets.

## Deadline

The team operational target is Sunday, November 8, 2026, 10:30 AM Central. It is user-confirmed in `docs/DEADLINE_1030_HANDOFF.md` and `docs/CURRENT_STATE.md`. Released `Jaeger_Main/House_Edge/RULES.md` still says the main round closes Saturday, November 7, 2026, at 9:00 PM Central, and adaptation closes Sunday, November 8, 2026, at 11:00 AM Central. This repository does not contain an organizer announcement that extends the main deadline or that says which form 10:30 AM covers. Those clocks are not reconciled here.

## What the human release lead does next

1. On issue #5, confirm with the current organizer Form or announcement whether the main round is still open and whether 10:30 AM Central applies to that form. If the main form is closed, this pair does not become eligible because the team target is later.
2. If the correct form is open, upload only this matched pair (`submission.csv` and `code.zip` with the hashes above). Do not mix in the earlier Windows or default-dispatch packages, and do not regenerate the files.
3. Keep the Form receipt privately. A green probe, a green checker, and this report are not that receipt.
4. Treat historical-signal / as-of compliance and single-host CPU pinning as open limitations when describing the entry. This witness does not clear them.
