# CI, local verification, and release runbook

**Scope:** source-backed instructions for JAEGERS. **Status:** runnable commands are separate from verified completion. Always check [current state](../CURRENT_STATE.md), the official organizer kit, GitHub Actions and the relevant issue/PR before submitting.

## Supported local House Edge test path

Start in `Jaeger_Main/House_Edge`, using Python 3.13. The repository provides Windows and Linux helper scripts in `tools/`.

```bash
cd Jaeger_Main/House_Edge
python -m pip install -r requirements-research.txt
python -m pytest tests/test_release_smoke.py tests/test_temporal.py -q
python scripts/smoke_release.py --self-test
```

For broader optional modeling families, use their explicit per-family requirements rather than adding unpinned dependencies to the competition runtime. `requirements-runtime.txt` is the smaller pinned offline inference layer; `requirements-research.txt` adds Optuna, process utilities and tests. Inspect [`RESEARCH.md`](../../Jaeger_Main/House_Edge/RESEARCH.md) and the model-specific run commands before running heavy experiments.

## GitHub Actions inventory

| Workflow (source path) | When | What is actually checked |
| --- | --- | --- |
| [`agent-collaboration.yml`](../../.github/workflows/agent-collaboration.yml) | Every PR event | PR issue/claim ownership, changed-file allowlist, conflicting open PR paths, duplicate prior merged branch heads, ancestor-only branches and governance regression tests |
| [`house-edge-ci.yml`](../../.github/workflows/house-edge-ci.yml) | House Edge paths + manual | Pinned Python 3.13 research environment, two focused release/temporal tests, smoke release command |
| [`databricks-offline-ci.yml`](../../.github/workflows/databricks-offline-ci.yml) | Databricks subtree/tests + manual | 49 observed offline/mock unit, feature parity, MLflow and SQL tests. **Not real cloud execution.** |
| [`hitachi-ci.yml`](../../.github/workflows/hitachi-ci.yml) | Hitachi paths + manual | Executes `tower/tests/test_*.py` if checked-out branch contains it; otherwise explicitly SKIPs. A workflow success with SKIP does not mean tower tests passed. |
| [`docs-checks.yml`](../../.github/workflows/docs-checks.yml) | Documentation paths + manual | Internal-link smoke and source Markdown inventory. Intended to guard new canonical docs without automatically rewriting historical archived material. |

**CI is not enforcement until ruleset settings actually require it.** Prefer one always-on trusted governance job as a required status check; path-filtered checks can be skipped and remain pending on unrelated PRs. See [governance runbook](../ops/PR_GOVERNANCE_RUNBOOK.md).

## Frozen main entry: exact pair, never mixed

The recorded original checkout stores frozen `research_runs/REVIEW_MAIN_9PM/submission.csv` and `code.zip` outside tracked Git. Their reported hashes, sizes, runtime history and limitations are in [CURRENT_STATE.md](../CURRENT_STATE.md). A filename containing `9PM` does not establish the actual current organizer deadline.

**Release gate:** verify authorized round, participant registration, official current `RULES.md`, kit hashes/version, target query IDs, CSV shape and probability sums, ZIP manifest and dependency pins; run two cold offline Linux reproductions with the correct CPU dispatch policy; retain identical output hashes and max difference within organizer tolerance; human authorizes actual submission and stores the private receipt. Reproducing on one host is not universal hardware portability.

Commands supported by [`RESEARCH.md`](../../Jaeger_Main/House_Edge/RESEARCH.md) use new output directories and refuse overwrite:

```bash
cd Jaeger_Main/House_Edge
python -B -m research.freeze --data public --out research_runs/new-freeze
python -B -m research.reproduce --entry research_runs/new-freeze/entry --data public --out research_runs/new-repro
```

These are **examples** to execute after dependencies/kit availability. Do not replace the already frozen candidate by running them. The organizer hidden test score cannot be computed from released test inputs.

## Adaptation is a distinct release

Read [the actual adaptation status](../../Jaeger_Main/House_Edge/adaptation/RELEASE_STATUS.md), [orchestrator README](../../Jaeger_Main/House_Edge/adaptation/README.md) and current issue [#6](https://github.com/AsvM45/jaegers/issues/6). The merged orchestrator refuses the original `round: main` kit when expecting `round: adaptation`. At the last verified source checkpoint the new kit is **not available**: no validated adaptation forecast, matched CSV+ZIP or organizer receipt exists. Do not submit the main pair to adaptation or fabricate a new kit.

The event-wide Devpost deadline is not an extension of a distinct challenge form. House Edge main and adaptation deadlines/point allocation have conflicting older sources. Verify the live organizer channel and document the authoritative link privately.

## Hitachi branch testing

Full `tower/` source and adversarial tests are currently on [`hitachi`](https://github.com/AsvM45/jaegers/tree/hitachi/Jaeger_Main/Hitachi). From that branch, after checking requirements and test expectations:

```bash
cd Jaeger_Main/Hitachi
python -m unittest discover -s tower/tests -p 'test_*.py' -v
```

No Hitachi success on the separate branch may be inferred from a SKIP on `main`. Merge work only after an owned issue/PR, source review and genuine tests.

## Evidence and rollback

- Record Git commit, Python version, OS, dependency versions, data SHA, evaluation split, commands, wall time, and error logs for every experiment.
- Use the current separate branch/worktree per active agent; stop after red ownership/CI. Do not force-push, reset, clean or delete another agent's checkout.
- Before branch retirement, consult [Codex's audit](../ops/BRANCH_CONSOLIDATION_AUDIT.md), preserve ignored run directories and get owner sign-offs. That audit authorizes **zero deletions**.
- Do not publish private receipts, organizer tokens, hidden labels or raw personal data in GitHub issues or Actions artifacts.
- Do not equate an imported historical report with current successful execution. Only actual current commands and immutable evidence support a status change.
