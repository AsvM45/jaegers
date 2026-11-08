# JAEGERS House Edge ? current release and research state

Updated: 2026-11-08T02:37:04.002516+00:00

## Main-round deadline and upload candidate

Main closes November 7, 2026 at **21:00 America/Chicago** (November 8, 03:00 UTC), per the kit and human deadline confirmation. No organizer upload or receipt is recorded by CHAT.

Human review/upload folder in the original checkout:
`Jaeger_Main/House_Edge/research_runs/REVIEW_MAIN_9PM/`.
Upload the matched `submission.csv` and `code.zip` only after human release review.

| Artifact | SHA-256 | Bytes |
|---|---|---:|
| submission.csv | b718f2d5e14a5a508d3c6c3658259042228a7a4d38e0221513e46e5590d9babf | 195579 |
| code.zip | 9a8a9e0e18a8d21d30474b3e007156c1f19be4f693dd3b2235019be830d3001f | 8263 |

This candidate keeps the original champion model, predictor and parameters unchanged and pins the Linux NumPy/OpenBLAS CPU policy in `reproduce.json`. Two cold Linux x86-64 Python 3.13.18 runs, using only the seven runtime distributions, disabled network, read-only code/data, two CPUs and 16 GiB memory limits, reproduced **all 1,536 queries with identical CSV bytes and maximum probability difference 0**. The two incoming CPU policies were tested on one physical host; universal hardware/build portability is not claimed. Hard aggregate scratch quota enforcement remains unavailable.

Candidate provenance and both attempts: `.chat-he08/Jaeger_Main/House_Edge/research_runs/baseline-cpu-candidate/`. The review folder is a checksum-verified copy; CSV/ZIP are read-only. No challenger promotion is implied.

## Verified scores and failed hypotheses

All scores below use the official organizer checker on **development-exposed public validation**, not hidden test.

| Configuration/runtime | Main points / 60 | Release interpretation |
|---|---:|---|
| Original champion, Windows | 55.1216153061 | Independently reproduced; failed Linux parity |
| Original champion, Linux default CPU | 55.1458245393 | Same-environment parity passed; changed-CPU parity failed |
| Same champion, explicit Linux CPU policy | 55.0908150083 | Matched upload candidate; both cold parity checks passed |

The Windows/Linux mismatch was 0.1068863090; disabling optional NumPy CPU dispatch changed the original Linux forecasts by 0.0903333471, above the required 1e-8 tolerance. Preserve those failed packages as evidence and do not mix their files with the candidate pair. The original Linux verification pointer is FAILED. Stable expert-weight sorting did not fix platform differences and was rejected. Release tooling now invalidates stale success after a recorded failure.

## Integrated implementation and tests

- Core PR #34 merged at `940dfbf0c9efd31eb565aec5af4319e507518603`. Model, audit, QA, feature, ML, temporal, ensemble and CI branches are integrated. Remaining historical documentation/governance tips are consolidated without reverting newer content. Hitachi is unchanged.
- Python 3.13 setup, frozen source/data manifests, official reproduction/checking, ZIP staging, offline verification, grouped/as-of datasets, switchable features, serialization, deterministic/source-isolated trials, grid/random/Optuna searches, bounded processes, SQLite attempts/leases, resume proofs, OOF/calibration/paired reports are implemented.
- Compatibility packages `research.models` and `research.features` re-export existing implementations from `adapters.py` and `feature_api.py`.
- Latest combined dashboard/governance/House Edge suite: **207 passed** in 73.88 seconds; one warning comes from the deliberate leaky-extension negative control. Core GitHub ownership and House Edge CI passed; HE-08 completion checks are recorded in PR #47.
- #1 champion preservation/reproduction and #4 local offline release gate are complete and closed. Human submission/receipt remains separate in #5.
- Version-1 portable trial exports preserve the legacy JSON/SQLite interfaces, include metric/source/data/fold provenance and terminal artifact hashes, and reject changed sealed evidence. The actual dashboard reader loaded all **12 canonical trials / three families / 96 episodes each**. Streamlit AppTest completed on that real export with **zero application exceptions**; this is an initial rendering smoke, not verification of every interactive analysis flow. Evidence: `.chat-he08/Jaeger_Main/House_Edge/research_runs/analytics/`.
- External setup/usage guide: [RESEARCH.md](../Jaeger_Main/House_Edge/RESEARCH.md). API contract: [CONTRACTS.md](../Jaeger_Main/House_Edge/research/CONTRACTS.md).

## Research evidence and remaining work

The canonical CHAT registry has **12 completed distinct configurations across three families**, four no-rewrite resume proofs, and a retained champion decision. Grouped sampled-label Brier: champion 0.3622911451 versus best screened challenger 0.5662851961; paired delta +0.2039940510, 95% episode-bootstrap interval [0.1851518350, 0.2231266999], 96 episodes. This is not official true-vector validation loss. Peer study reports are under `research/reports/` and `research/configs/`; their runs are not counted again here.

HE-08 completion regression: three current-source smoke configurations succeeded in 41.46 seconds. Replay took 0.96 seconds and preserved all three trial identities, attempt numbers and artifact bytes. These repeat configurations do not increase scientific diversity. Evidence: `.chat-he08/Jaeger_Main/House_Edge/research_runs/he08-completion-smoke/resume-proof.json`.

Historical pseudo-row signal/final-history construction remains an audit finding; SIZE_REGIMES and selection used public validation targets. Human release review must account for these caveats. No hidden-test performance or organizer acceptance is knowable locally.

Broad 100+ experimentation, complete interactive-dashboard acceptance, cloud integration and adaptation release are **not declared complete**. Initial real-data dashboard rendering is verified above; Databricks access is not established. Adaptation uses a separate released kit, history, registry and package; kit deadline is November 8 at 11:00 Central. Release selection/upload/receipt and organizer announcements remain human-owned #5; #18 holds coordination.
