# Contributing to JAEGERS

This repository is a public research/competition project. Contributions require source-backed claims and review, not only plausible AI-generated code.

1. Read [README](README.md), [`AGENTS.md`](AGENTS.md), the relevant nested `AGENTS.md`, [collaboration protocol](docs/AGENT_COLLABORATION_PROTOCOL.md), and [status](docs/CURRENT_STATE.md).
2. Choose one [unclaimed issue](https://github.com/AsvM45/jaegers/issues) with an explicit acceptance contract. Post a named `jaegers-claim:v1` comment, exclusive writable paths and handoff responsibility. For concurrent edits use an independent physical Git worktree or a GitHub-hosted cloud sandbox.
3. Start a uniquely named `agent/<name-issue>` or `human/<name-issue>` branch from current `main`. Never force-push or reset somebody else's worktree. Do not resurrect already-integrated branch history into redundant PRs.
4. Keep source changes limited to the issue's claimed paths. Coordinate interfaces and data schemas before touching common research modules.
5. Run exact unit/contract/smoke tests. Record actual commands, environment, source/data hashes, negative outcomes, approximate run time, and evaluation provenance (public validation vs grouped training vs no hidden score). Reproducibility and absence of future-feature leakage matter as much as a score.
6. Open a [pull request](https://github.com/AsvM45/jaegers/pulls) using the repository template with **one canonical** `Issue: #NN` line, exact branch and agent, nonempty tests and handoff; wait for a passing trusted ownership gate and applicable component checks.
7. Review changed paths and request human non-author approval where available. A green path-filtered workflow can be a SKIP, not evidence that tests ran. No agent self-merge, unattended production promotion, organizer upload or cloud spend.
8. Keep Git-ignored experiment evidence until acceptance and recoverability are verified. Branch cleanup follows [Codex's read-only inventory](docs/ops/BRANCH_CONSOLIDATION_AUDIT.md); this is not a license to delete uninspected worktrees.

## Development commands

House Edge (Python 3.13):

```bash
cd Jaeger_Main/House_Edge
python -m pip install -r requirements-research.txt
python -m pytest tests/test_release_smoke.py tests/test_temporal.py -q
python scripts/smoke_release.py --self-test
```

The full [CI and release runbook](docs/runbooks/CI_AND_RELEASE.md) describes the new offline component checks. The Hitachi `tower/` test suite lives on its separate `hitachi` branch. Do not claim its source is already on `main`.

## Security, attribution and license

Do not post private organizer submissions, receipts/tokens, hidden labels, signed agreements or user files to the repository. See [SECURITY](SECURITY.md). The repository currently has no agreed open-source license: **public visibility is not automatic permission to redistribute or relicense others' contributions**. Verify that the Hack the Highway and House Edge starter materials can be shared before changing licensing.

## GitHub cloud agents

For Copilot cloud agent and custom JAEGERS reviewer setup, see [Agents and worktrees](docs/agents/GITHUB_AGENTS_AND_WORKTREES.md). A local Cursor/Grok/Claude session does not automatically appear in GitHub's Agents tab.
