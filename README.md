# JAEGERS — TAMU Datathon 2026

Probabilistic forecasting, experiment engineering, and agentic operations developed for TAMU Datathon 2026. This public repository includes two distinct challenge areas:

| Project | Source | Scope |
| --- | --- | --- |
| **House Edge** | [`Jaeger_Main/House_Edge/`](Jaeger_Main/House_Edge/) | Five-class payout-probability forecasting, reproducible statistical evaluation, offline release engineering, research experiments and monitoring |
| **Hack the Highway / Hitachi** | [`Jaeger_Main/Hitachi/`](Jaeger_Main/Hitachi/) | An independent challenge project. The full `tower/` implementation and adversarial tests currently live on the separate [`hitachi` branch](https://github.com/AsvM45/jaegers/tree/hitachi/Jaeger_Main/Hitachi) |

**Status is evidence-specific.** The House Edge model's approximately **55.12/60 is public development validation**, **not** hidden-test points or an organizer receipt. The separately frozen Linux candidate was tested under a pinned CPU policy. Whether the organizers accepted any entry must be established from an actual receipt; see [release status](docs/CURRENT_STATE.md). The historical pseudo-example feature-compliance witness reports **NOT_CERTIFIED**, not a passing organizer ruling.

## Read first

For an up-to-date synthesized continuity source for new ChatGPT sessions, start at [the canonical JAEGERS project source](docs/JAEGERS_PROJECT_CONTEXT_2026-11-08.md). The complete Nov 7 Drive experiment-factory research has been reconciled into [current technical design](docs/research/EXPERIMENT_FACTORY_v7.md) and [plain-English guide](docs/research/EXPERIMENT_FACTORY_GUIDE.md); historical originals are archived separately, and private/personal materials are excluded. GitHub Wiki and Projects are enabled at the repository level but live publication/board configuration is not confirmed.



| Need | Canonical source |
| --- | --- |
| Current evidence, integrated work and unknowns | [Verified status](docs/CURRENT_STATE.md) and [issue #18](https://github.com/AsvM45/jaegers/issues/18) |
| System architecture and source directories | [Architecture overview](docs/architecture/SYSTEM_OVERVIEW.md) |
| Evaluation, calibration and statistical pitfalls | [Scientific validation and provenance](docs/science/EVALUATION_AND_PROVENANCE.md) |
| Setup, offline tests, packaging and operations | [CI and release runbook](docs/runbooks/CI_AND_RELEASE.md) |
| AI agents, physical worktrees, GitHub Agents tab | [Agents and worktrees](docs/agents/GITHUB_AGENTS_AND_WORKTREES.md) |
| Contributor scope and pull-request checklist | [Contributing](CONTRIBUTING.md) and [governance runbook](docs/ops/PR_GOVERNANCE_RUNBOOK.md) |
| Security and responsible disclosure | [Security policy](SECURITY.md) |
| Long-form engineering design (historical snapshot) | [Engineering specification v5](docs/ENGINEERING_SPEC.md) |
| Platform decisions and optional GitHub features | [ADR-0001](docs/adr/0001-github-engineering-features.md) |
| Wiki-style navigation | [`docs/wiki/Home.md`](docs/wiki/Home.md) |

The definitive **task contract** lives in its GitHub issue; the definitive **code state** lives in its branch or merged commit. The dated documents are not proof that an agent is running. Check [Issues](https://github.com/AsvM45/jaegers/issues), [Pull requests](https://github.com/AsvM45/jaegers/pulls), and [Actions](https://github.com/AsvM45/jaegers/actions).

## Getting started locally

Read [`AGENT_START_HERE.md`](AGENT_START_HERE.md), root [`AGENTS.md`](AGENTS.md), and [House Edge `AGENTS.md`](Jaeger_Main/House_Edge/AGENTS.md) before any automated modification. Some older startup text is a historical handoff; the latest issue claim and current code supersede dated task assignments.

House Edge commands (from its directory, after Python 3.13 and dependencies are set up):

```bash
cd Jaeger_Main/House_Edge
python -m pip install -r requirements-research.txt
python -m pytest tests/test_release_smoke.py tests/test_temporal.py -q
python scripts/smoke_release.py --self-test
```

The repo-root component CI and experiment architecture are documented in [the runbook](docs/runbooks/CI_AND_RELEASE.md). The Hitachi branch has its own source and tests; do not assume those tests run on `main`.

## Collaboration and repository policy

Agents use **one claimed issue**, **one exclusive write scope**, **one branch**, and a **separate physical checkout or GitHub-hosted cloud sandbox**. All changes arrive through reviewable PRs. Claims, handoffs and limitations are recorded on the issue. GitHub's Agents tab manages GitHub-hosted Copilot/agent-app sessions; it does **not** monitor local Grok, Claude, Cursor or Antigravity processes.

**Public repository warning:** Do not commit organizer tokens, private receipts, hidden labels, credentials, private conversations, unpublished participant data, or generated run directories. Public visibility is not a software license; licensing remains a maintainer/coauthor decision.

_Source-of-truth policy: current code + official organizer kit + current issue/PR evidence > current docs > older handoffs and chat exports._
