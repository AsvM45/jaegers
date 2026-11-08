# Architecture — JAEGERS

**Verification anchor:** source tree and merged commit `9eec670c8bd3b1fcdcc67f7d376cbf316dd639a8`, Nov 8 2026. Modules evolve; verify imports and interfaces before implementation. See [current state](../CURRENT_STATE.md) and [House Edge contracts](../../Jaeger_Main/House_Edge/research/CONTRACTS.md).

## Monorepo boundaries

```text
Jaeger_Main/
  House_Edge/
    public/                  organizer-released inputs; only licensed/public-safe data
    jaegers_entry/           protected champion predictor and parameters
    research/                episode-grouped evaluation, model adapters,
                             feature API, challengers, registry and trial reports
    adaptation/              distinct round-two orchestration and blocker report
    scripts/                 smoke and reproduction helpers
    tools/                   packaging/environment verification
    dashboard/               read-only analysis of versioned registry results
    databricks/              sponsor-specific ETL / feature parity / MLflow bundle
    tests/                   cutoff, release, adversarial and component tests
  Hitachi/
    Data/                    challenge input package and enterprise source
    enterprise.py
    enterprise_server.py
    # expanded tower/ architecture is on the separate 'hitachi' branch
docs/                        canonical source-backed project knowledge
.github/workflows/            pull-request gate and bounded component CI
tools/                        root repository governance and audit scripts
```

The House Edge inference runtime is **offline CPU Python**, separate from research orchestration and any optional cloud sponsors. The GitHub repository is public; personal organizer tokens, receipts, private resources and Git-ignored experiment outputs do not belong in its history.

## House Edge learning and inference

```mermaid
flowchart TD
    A[Organizer public train] --> B[Immutable loader and source manifest]
    V[Public validation] --> C[Development-only evaluation]
    B --> D[As-of feature calculation]
    D --> E[73-expert and stacker champion]
    D --> F[Isolated challenger families]
    E --> G[Episode-grouped folds and provenance]
    F --> G
    G --> H[Versioned trial registry and results]
    H --> I[Read-only analytics dashboard]
    E --> J[Offline code ZIP and CSV]
    T[Test queries and earlier history] --> J
    J --> K[Human organizer submission and receipt]
    V --> C
    G --> C
```

**Statistical target:** one five-class probability vector `[p_0,p_1,p_2,p_5,p_20]` per query, where output values are finite/nonnegative and sum to 1. There are eight related machines per episode, and only history with `tick < cutoff` may enter a prediction, including sibling machines. Machine identities and absolute tick values do not persist across episodes. Missing history ticks are *missing*, not 0× payouts.

**Model implementation:** `jaegers_entry/` is a protected frozen champion. `research/adapters.py`, `research/feature_api.py`, `research/dataset.py`, `research/metrics.py`, `research/worker.py`, `research/registry.py` and `research/challengers/` provide evaluation tooling and experimental models. Use actual [integration contracts](../../Jaeger_Main/House_Edge/research/CONTRACTS.md) before touching interfaces; it is not safe to extrapolate signatures from old examples.

**Scientific limitations:** Real next-spin probability targets are public in validation but hidden in test, so *public scores are repeatedly development-exposed*. An independent historical-feature witness identified post-t dependence in pseudo-training rows; see [the `NOT_CERTIFIED` report](../release/GROK_HISTORICAL_FEATURE_COMPLIANCE.md). Do not call this hidden-test leakage or assert organizer legality without a ruling.

## Release and adaptation isolation

The main candidate is a **paired** `submission.csv` and `code.zip`, locally Git-ignored with hashes recorded in [CURRENT_STATE](../CURRENT_STATE.md). The organizer sandbox is CPU/offline; cold reproduction must use the matching runtime and numerical tolerance. Never mix a Windows CSV with a Linux ZIP merely because the Python source matches: CPU dispatch differences were measured.

Round-two adaptation uses the **different** data kit, season metadata and query IDs. Its `adaptation/run_adaptation.py` rejects main-round metadata. The merged [adaptation status](../../Jaeger_Main/House_Edge/adaptation/RELEASE_STATUS.md) says `BLOCKED_KIT_MISSING`, with no independently verified adaptation submission.

## Sponsors and visibility boundaries

The `databricks/` subtree contains a Bronze/Silver/Gold, Spark-style feature and MLflow proof-of-concept; offline/mock CI tests are not equivalent to actual workspace execution. The `dashboard/` package reads exported trial records without rewriting them. The Hitachi `tower/` component is maintained on a distinct development branch and must be integrated/reviewed separately.

## Operational ownership

One issue per agent, explicit claim, exclusive writable paths, own physical checkout/cloud sandbox, and independent PR review. [Governance runbook](../ops/PR_GOVERNANCE_RUNBOOK.md) and [agent guide](../agents/GITHUB_AGENTS_AND_WORKTREES.md) document the execution contract. GitHub Actions verifies some conditions; no automation proves local process ownership or an organizer receipt.
