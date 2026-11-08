# Submission files — start here

**Team-reported operational deadline: Sunday, November 8, 2026, 10:30 AM Central.** The released `RULES.md` still says **main closes Saturday Nov 7, 9 PM**, and **adaptation closes Sunday Nov 8, 11 AM**. **Which form the revised 10:30 time applies to is not independently verified.** Check official organizer announcement/Form immediately before treating main as open. The public Datathon-wide schedule does not supersede challenge-specific rules.

## Actual submission pair (local files, NOT checked into GitHub)

From the **original repository checkout**:

```text
Jaeger_Main/House_Edge/research_runs/REVIEW_MAIN_9PM/
    submission.csv       SHA256 b718f2d5e14a5a508d3c6c3658259042228a7a4d38e0221513e46e5590d9babf
    code.zip             SHA256 9a8a9e0e18a8d21d30474b3e007156c1f19be4f693dd3b2235019be830d3001f
```

**Do not search GitHub for these binaries:** `research_runs/` is intentionally gitignored. The model source/reconstruction inputs are tracked in `jaegers_entry/`; package builder in `research/release.py`; checker `check_submission.py`. A released code ZIP root must include `README.md`, `reproduce.json`, `requirements.txt`.

```powershell
# From original jaegers root:
$folder = "Jaeger_Main\House_Edge\research_runs\REVIEW_MAIN_9PM"
Get-FileHash "$folder\submission.csv" -Algorithm SHA256
Get-FileHash "$folder\code.zip" -Algorithm SHA256
python Jaeger_Main\House_Edge\check_submission.py "$folder\submission.csv" --data Jaeger_Main\House_Edge\public --split test
```

Last report: 1,536 complete query IDs, correct simplex/format, **55.090815/60 exposed public validation**, and two exact cold Linux reproductions under CPU policies on the **same physical machine**. Cross-host parity, strict historical as-of interpretation and actual organizer acceptance remain unverified. Do not mix with earlier **failed** Windows/default Linux packages.

Only an authorized **human** may choose/upload/replace CSV+ZIP and retain the Google Form receipt. No GitHub push, PR merge or CI run is a submission.

## Work while submission is pending

- Human #5: deadline/form confirmation and final upload.
- Cursor [#46](https://github.com/AsvM45/jaegers/issues/46): separately owned **read-only portability and frozen pair witness**; no overwrite or recomputation of submission.
- CHAT #8: continue bounded portable experiment registry export; separate release artifacts remain frozen.
- Other agents: keep their existing issue claims/worktrees; no new simultaneous agent on a claimed issue.

For full decision, caveats, precise paths, tests and workstream priorities, read [docs/DEADLINE_1030_HANDOFF.md](../../docs/DEADLINE_1030_HANDOFF.md) and [issue #18](https://github.com/AsvM45/jaegers/issues/18). The source challenge rules remain at `RULES.md` without edits.
