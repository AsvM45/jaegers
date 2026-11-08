# Branch consolidation: non-destructive preflight

Issue: [#65](https://github.com/AsvM45/jaegers/issues/65). Owner: `codex-branch-consolidation`.
Snapshot: **2026-11-08T07:46:45.062400+00:00**; canonical main **`ef43c0e43aa77f3d9cea0dbec0f4dcf9b1114a91`**.
Status: **READY FOR HUMAN REVIEW; no branches or worktrees retired**. This is an inventory and a proposed retirement manifest, not approval to execute it. Issue #66 has not been started.

## Verified result

- Full refreshed paginated GitHub snapshot: **37 remote branches, 41 PRs**, zero open PRs before this audit PR, 69 issue/PR rows and 155 issue comments. Raw snapshots and a separate bare graph agree on every branch SHA. The earlier preserved snapshot had #61/#67 open; their lifecycle changed during this audit as described below.
- History classes: **30 exact-head matches to merged PRs**, five ancestors (including protected main and agy), two unique/unmerged tips (hitachi and Claude's original adaptation branch). Matching PR merge commits were also checked reachable from main. Grok's squash-merged takeover has exact-head PR evidence without graph ancestry.
- Operational classes: **16 MERGED_EXACT_HEAD + 3 ANCESTOR_NO_UNIQUE_COMMITS = 19 review candidates; 14 KEEP_ACTIVE; 4 BLOCKED**. **Zero branches are retirement-ready**: no per-branch owner sign-offs have been collected.
- Ten physical checkouts in three Git repositories were inspected, not merely the six entries in the primary repository's worktree registry. No teammate checkout had tracked modifications or untracked nonignored files at scan time; ignored evidence is present. Only this Codex checkout had its expected new audit tooling. A later HEAD/status recheck of all nine other checkouts matched the snapshot.
- No local branch contained commits absent from all refs in the remote graph snapshot. Local ref differences are recorded below; clean status and zero local-only commits do not prove agent inactivity.
- **4,533 research-run files / 145,697,907 bytes** were preserved, plus two loose AGY-side experiment/test files. Verified private archive: **4,535 files / 145,716,874 source bytes**. All archived members were read back and SHA-256 checked, with zero source changes observed during copying. Three complete local-ref Git bundles passed `git bundle verify`.
- No deletion, worktree removal, force push, reset, clean, merge, model/source change, adaptation change, Databricks action or organizer action was performed. The audit publication itself adds one protected `agent/codex-branch-consolidation` remote ref after this 37-branch baseline; its delivery SHA is available in the PR.

## Classification and limits

`MERGED_EXACT_HEAD` means a GitHub PR into this repository's main was merged, the PR's recorded head SHA exactly equals the branch SHA, and its merge commit is reachable from the snapshot main. It does **not** require graph ancestry: squash-merged tips can legitimately remain ahead. No new merge is needed for these branches.

`ANCESTOR_NO_UNIQUE_COMMITS` requires the actual tip to be an ancestor of main with zero ahead commits. `UNIQUE_UNMERGED` is a history fact and is never retirement evidence. `KEEP_ACTIVE` includes explicit user protections and unresolved claim markers on open issues; it does not assert that each old claim is a running process. `BLOCKED` identifies otherwise integrated branches still checked out with ignored evidence. `UNKNOWN/LOCAL_ONLY` is reserved for missing/uninspectable refs or commits absent from the remote graph; none was observed other than this newly created, deliberately protected local audit branch name before publication.

The eight historical claim markers on still-open #18 remain conservative holds until their owners/coordinator explicitly resolve them: governance collaboration, hub, single-digit fix, live-base fix, context mirrors, bootlinks, Cursor ensemble and deadline/cursor docs. Closed issue claims alone are not treated as active, but every local checkout and its ignored files is still protected.

Scope is the supplied workspace and all worktrees registered by its discovered repositories. Dependency/cache trees (`.runtime`, `.venv`, caches, node_modules), symlinks and the private bare graph are not searched as independent agent repositories. The first discovery attempt encountered uv cache `.git` sentinel files; the final pass excludes `.runtime` from repository discovery and completed with zero errors. Ignored cache paths remain recorded but are not backed up as experiment evidence. The ignored nested `.chat-he08` container is inspected as its own worktree. There is no claim to have inspected other computers, undiscovered external clones, a private organizer receipt that was not present, or live process ownership.

## Exact remote retirement manifest

Ahead/behind counts are relative to the full main SHA above. `REVIEW` means history/local preflight passed, **not deletion approval**; owner confirmation and a fresh live SHA/PR/claim/worktree check remain mandatory. `HOLD claim` means unresolved marker; `HOLD worktree` includes local ignored evidence. Both adaptation refs, hitachi, main, agy and the AGY Databricks lane are explicit holds.

| Branch | Exact remote tip SHA | Ahead / behind main | Merged exact-head PR(s) | Classification / proposed action |
| --- | --- | ---: | --- | --- |
| `agent/antigravity-he13-dashboard` | `701ee2ae296033f24bd25f980c83fb1e2166c7a6` | 4 / 148 | [45](https://github.com/AsvM45/jaegers/pull/45) | BLOCKED; HOLD worktree/evidence |
| `agent/antigravity-he14-databricks` | `27e6a866e49f3c7b7dacb6a672b5a2c1f11e34ad` | 0 / 13 | [60](https://github.com/AsvM45/jaegers/pull/60) | KEEP_ACTIVE; HOLD explicit protection, claim, worktree/evidence |
| `agent/chat-he08-completion` | `0ede25413a826c9c5d87c9ffa312517cef1520d2` | 0 / 25 | [47](https://github.com/AsvM45/jaegers/pull/47) | MERGED_EXACT_HEAD; REVIEW only |
| `agent/chat-he08-core` | `d916bad9357b282766c1f27cfc57a0a9db1ebf1d` | 0 / 140 | [34](https://github.com/AsvM45/jaegers/pull/34) | MERGED_EXACT_HEAD; REVIEW only |
| `agent/chat-house-edge-finalize` | `59dd2b6000986c5675691b096c962c934d521bb7` | 0 / 34 | [44](https://github.com/AsvM45/jaegers/pull/44) | MERGED_EXACT_HEAD; REVIEW only |
| `agent/chat-runtime-screen` | `1972120a1be55bf2e700148510f583d53c524e1c` | 0 / 20 | [53](https://github.com/AsvM45/jaegers/pull/53) | BLOCKED; HOLD worktree/evidence |
| `agent/chatgpt-he18-bootlinks` | `421d6e59b650c65a9b38901775cfedc56f49b3b6` | 0 / 165 | [32](https://github.com/AsvM45/jaegers/pull/32) | KEEP_ACTIVE; HOLD claim |
| `agent/chatgpt-he18-context-mirrors` | `e12e00bc67025eed437eea5b10810796c44373fb` | 0 / 162 | [31](https://github.com/AsvM45/jaegers/pull/31) | KEEP_ACTIVE; HOLD claim |
| `agent/chatgpt-he18-deadline-cursor` | `b120c67606bb7eca7ea3c9d508e17d153bc37e1e` | 12 / 32 | [48](https://github.com/AsvM45/jaegers/pull/48) | KEEP_ACTIVE; HOLD claim |
| `agent/chatgpt-he18-hub` | `518a9099d29b3944a01866753f93808a92f37bef` | 0 / 133 | [26](https://github.com/AsvM45/jaegers/pull/26) | KEEP_ACTIVE; HOLD claim |
| `agent/claude-c-2-qa-tests` | `3e323292d23ed145ee38ee7ccc0ae68e8f0a2b4f` | 0 / 174 | [43](https://github.com/AsvM45/jaegers/pull/43) | MERGED_EXACT_HEAD; REVIEW only |
| `agent/claude-c-7-feature-contract` | `c0c4f20f3cd2b125e606eff6462c5fbd8ee4b307` | 0 / 174 | [42](https://github.com/AsvM45/jaegers/pull/42) | MERGED_EXACT_HEAD; REVIEW only |
| `agent/claude-d-17-ablation` | `e53beb01a25e52ed0dcf6ba5634183843e3a4982` | 0 / 173 | [40](https://github.com/AsvM45/jaegers/pull/40) | MERGED_EXACT_HEAD; REVIEW only |
| `agent/claude-he03-signal-audit` | `d0fcfb66081c23a11f6324b14e086d20bdab01a6` | 0 / 174 | [38](https://github.com/AsvM45/jaegers/pull/38) | MERGED_EXACT_HEAD; REVIEW only |
| `agent/claude-qa-he03-causal-stacker` | `59c8e5196dd4a9af8ae7baf49ceb12362ec02e94` | 0 / 20 | [56](https://github.com/AsvM45/jaegers/pull/56), [63](https://github.com/AsvM45/jaegers/pull/63) | MERGED_EXACT_HEAD; REVIEW only |
| `agent/claude-release-he06-adaptation` | `9c77b580ea2a7650e9050c1e3aa3198df04642c0` | 1 / 22 | — | KEEP_ACTIVE; HOLD explicit protection, claim |
| `agent/claude-stats-he09-challengers` | `6906701e00285f17f2f9b17d98f9f36f8c751d62` | 0 / 166 | [28](https://github.com/AsvM45/jaegers/pull/28) | MERGED_EXACT_HEAD; REVIEW only |
| `agent/claude-stats-he09-registry` | `a639d872cd7259375a692f3f7c1f93ec7ad1eef5` | 0 / 31 | [49](https://github.com/AsvM45/jaegers/pull/49) | MERGED_EXACT_HEAD; REVIEW only |
| `agent/claude-stats-he15-temporal` | `cce96a891d643b35bf1c67e32cb0eb9a89d494eb` | 0 / 18 | [52](https://github.com/AsvM45/jaegers/pull/52), [62](https://github.com/AsvM45/jaegers/pull/62) | MERGED_EXACT_HEAD; REVIEW only |
| `agent/claude-stats-he17-registry` | `d4409476ef0a334e1504f8c484d3a3601dbc369a` | 0 / 23 | [50](https://github.com/AsvM45/jaegers/pull/50) | MERGED_EXACT_HEAD; REVIEW only |
| `agent/claude-stats-structural-stack` | `d425c3f484400c86d123767eade08b7d47c82dc3` | 0 / 14 | [59](https://github.com/AsvM45/jaegers/pull/59), [64](https://github.com/AsvM45/jaegers/pull/64) | MERGED_EXACT_HEAD; REVIEW only |
| `agent/cursor-he10-ml` | `a7296be8f1c4e0f2b2ba74b53aff569433388f20` | 0 / 170 | [36](https://github.com/AsvM45/jaegers/pull/36) | MERGED_EXACT_HEAD; REVIEW only |
| `agent/cursor-he11-temporal` | `88735be2dc0d2798ffc98cc9395aa2ec3ec21b11` | 0 / 168 | [39](https://github.com/AsvM45/jaegers/pull/39) | MERGED_EXACT_HEAD; REVIEW only |
| `agent/cursor-he12-ensemble` | `1819ef476ded05f3a7b660ce69fe0c4cbecc01fc` | 0 / 168 | [35](https://github.com/AsvM45/jaegers/pull/35) | KEEP_ACTIVE; HOLD claim |
| `agent/cursor-he16-ci` | `27d2bffdebf62962e60d03eb75f186115a7c1dc0` | 0 / 174 | [41](https://github.com/AsvM45/jaegers/pull/41) | MERGED_EXACT_HEAD; REVIEW only |
| `agent/cursor-he46-portability` | `97bdf4bf2961dcb4e5bd10125809da467083e592` | 1 / 22 | [54](https://github.com/AsvM45/jaegers/pull/54) | BLOCKED; HOLD worktree/evidence |
| `agent/governance-he18-collaboration` | `ac3b6608f8677e0ae0a3a02aa00830cf5b2afcfb` | 0 / 171 | [23](https://github.com/AsvM45/jaegers/pull/23) | KEEP_ACTIVE; HOLD claim |
| `agent/governance-he18-live-base-handoff-fix` | `722b886ec27c41a90150b9ad3d21c99121a30902` | 0 / 170 | [30](https://github.com/AsvM45/jaegers/pull/30) | KEEP_ACTIVE; HOLD claim |
| `agent/governance-he18-single-digit-fix` | `02b6da1767969b8bff46b194018bb7ff4e5b0483` | 0 / 172 | [29](https://github.com/AsvM45/jaegers/pull/29) | KEEP_ACTIVE; HOLD claim |
| `agent/grok-he06-adaptation-takeover` | `456ff33425374b750cb7d0c8bd647834e4ff58ac` | 3 / 1 | [67](https://github.com/AsvM45/jaegers/pull/67) | KEEP_ACTIVE; HOLD explicit protection, claim, worktree/evidence |
| `agent/grok-he55-asof-witness` | `3ff81a70a858028189ec78b9205d7a015f63894f` | 1 / 16 | [57](https://github.com/AsvM45/jaegers/pull/57) | BLOCKED; HOLD worktree/evidence |
| `agy` | `27ef059c01ba01c06d26c86ca98d6ac52e2ea3b9` | 0 / 173 | — | KEEP_ACTIVE; HOLD explicit protection, worktree/evidence, local tip differs |
| `chat/house-edge-release-research-core` | `f7bdfaef58adf0c6e8b1309ae9e28f2e0017f0bb` | 0 / 174 | — | ANCESTOR_NO_UNIQUE_COMMITS; REVIEW only |
| `docs/autonomous-agents-operating-system` | `9a42f0602b986140f13402c9c0ce83aa5929f1fe` | 0 / 138 | — | ANCESTOR_NO_UNIQUE_COMMITS; REVIEW only |
| `docs/five-agent-github-hub-v2` | `bb7cb1d360bc94dd9fc4b29ede27dbc93b7085ca` | 0 / 174 | — | ANCESTOR_NO_UNIQUE_COMMITS; REVIEW only |
| `hitachi` | `6d988f535f9d6e1bba1f57f0a56b5b367400e612` | 2 / 178 | — | KEEP_ACTIVE; HOLD explicit protection |
| `main` | `ef43c0e43aa77f3d9cea0dbec0f4dcf9b1114a91` | 0 / 0 | — | KEEP_ACTIVE; HOLD explicit protection, worktree/evidence, local tip differs |

The 19 REVIEW rows form the complete proposed first review batch; the remaining 18 remote refs are excluded. No ref is silently omitted. `docs/autonomous-agents-operating-system` had an older closed/unmerged PR #25, so its evidence is ancestry/zero unique commits, not a merged-PR claim.

## Physical worktrees and local refs

Paths below are relative to the workspace parent of this repository. All existing ignored contents and source files remain in place. The primary registry and AGY clone's registry are distinct; the Grok clone has its own main checkout.

| Checkout | Branch | Actual HEAD | Tracked/untracked status | Ignored research-run files / bytes |
| --- | --- | --- | --- | ---: |
| `anti_gravity/jaegers` | `agy` | `26f23435175ea71e1cb6217d15d67614e6d87792` | Clean; ignored evidence separately inspected | 0 / 0 |
| `anti_gravity/jaegers-agy-he13` | `agent/antigravity-he13-dashboard` | `701ee2ae296033f24bd25f980c83fb1e2166c7a6` | Clean; ignored evidence separately inspected | 0 / 0 |
| `anti_gravity/jaegers-agy-he14` | `agent/antigravity-he14-databricks` | `27e6a866e49f3c7b7dacb6a672b5a2c1f11e34ad` | Clean; ignored evidence separately inspected | 0 / 0 |
| `grok/jaegers` | `main` | `fc7054e016dd15c38b825252e5c76b2991584c1e` | Clean; ignored evidence separately inspected | 0 / 0 |
| `jaegers` | `main` | `0492d434501a5e73d3e99fb7ce9f7ee7bd59f581` | Clean; ignored evidence separately inspected | 1,027 / 60,719,064 |
| `jaegers/.chat-he08` | `agent/chat-runtime-screen` | `1972120a1be55bf2e700148510f583d53c524e1c` | Clean; ignored evidence separately inspected | 3,506 / 84,978,843 |
| `jaegers-codex-branch-consolidation` | `agent/codex-branch-consolidation` | `0492d434501a5e73d3e99fb7ce9f7ee7bd59f581` | Expected new audit files (own worktree) | 0 / 0 |
| `jaegers-he06-adaptation-takeover` | `agent/grok-he06-adaptation-takeover` | `456ff33425374b750cb7d0c8bd647834e4ff58ac` | Clean; ignored evidence separately inspected | 0 / 0 |
| `jaegers-he46-portability` | `agent/cursor-he46-portability` | `97bdf4bf2961dcb4e5bd10125809da467083e592` | Clean; ignored evidence separately inspected | 0 / 0 |
| `jaegers-he55-asof-witness` | `agent/grok-he55-asof-witness` | `3ff81a70a858028189ec78b9205d7a015f63894f` | Clean; ignored evidence separately inspected | 0 / 0 |

There were no observed concurrent HEAD/status changes during either scan or the later nine-checkout recheck. This is a point-in-time observation, not permission to interrupt an agent.

Local heads were enumerated in each common Git directory, including branches not currently checked out. All were reachable in the captured remote graph. Important local/remote differences:

- AGY clone `agy` and its local `main`: `26f23435175ea71e1cb6217d15d67614e6d87792`; remote agy is `27ef059c01ba01c06d26c86ca98d6ac52e2ea3b9`. Neither local ref is updated by this audit.
- Grok clone local `main`: `fc7054e016dd15c38b825252e5c76b2991584c1e`; current remote main is newer. It remains untouched.
- The primary clone has ten local branch names: eight existing feature refs match their remote tips; local `main` and the new audit branch initially remain at `0492d434501a5e73d3e99fb7ce9f7ee7bd59f581`, while remote main advanced to `ef43c0e43aa77f3d9cea0dbec0f4dcf9b1114a91`. No existing checkout or local main ref was advanced by Codex. The new audit branch is explicitly protected; all nonchecked-out local feature refs are retained.
- `agent/antigravity-he13-dashboard`, `agent/cursor-he46-portability`, `agent/grok-he55-asof-witness` and `agent/chat-runtime-screen` have merged exact-head evidence but remain BLOCKED because their physical worktrees and ignored evidence still exist. A remote-merged head can be nonancestral after squash; no forced local branch deletion is proposed.

AGY is actively working on #14; its merged PR #60 does not end that assignment. At the initial snapshot Claude's #61 and Grok's #67 were both open and overlapping. A fresh live recheck caught changes by the release owners: #61 closed without merge at `2026-11-08T07:38:58Z`; #67 squash-merged at `2026-11-08T07:42:21Z`, moving main from `0492d434501a5e73d3e99fb7ce9f7ee7bd59f581` to `ef43c0e43aa77f3d9cea0dbec0f4dcf9b1114a91`. Both adaptation branch heads remained unchanged. The report/manifest was refreshed against that new main, retaining the earlier raw snapshot for provenance. Issue #6's [release-owner update](https://github.com/AsvM45/jaegers/issues/6#issuecomment-6718866611) still says BLOCKED_KIT_MISSING and no new artifact pair or receipt. **Both branches remain protected regardless of PR closure.** Codex did not close, merge, update or edit either PR/branch or their worktrees.

## Zero-diff duplicate merges #62–64

The Git trees of each merge and its first parent are identical. `git diff --name-only <merge>^1 <merge>` produced zero paths for all three. Earlier delivery PRs had already integrated the work; creating further consolidation PRs from these tips would add no source value.

| PR | Exact head SHA | Merge SHA | Prior delivery | Changed files against first parent |
| --- | --- | --- | --- | ---: |
| [#62](https://github.com/AsvM45/jaegers/pull/62) | `cce96a891d643b35bf1c67e32cb0eb9a89d494eb` | `e8800586d68694dcca42109c29c4128f16e46d28` | #52 | 0 |
| [#63](https://github.com/AsvM45/jaegers/pull/63) | `59c8e5196dd4a9af8ae7baf49ceb12362ec02e94` | `450ce4daf73fb9005b7ad3c84d2a497dad742199` | #56 | 0 |
| [#64](https://github.com/AsvM45/jaegers/pull/64) | `d425c3f484400c86d123767eade08b7d47c82dc3` | `0492d434501a5e73d3e99fb7ce9f7ee7bd59f581` | #59 | 0 |

Shared tree SHA for all six tree checks: `2c153a4cab57fdb20214cd780d55ff4220a62f9e`. The GitHub issue reports ownership-gate failures on these merges; this audit independently verified their zero-diff property, not rerun historical CI. Main history is preserved as recorded.

## Private evidence preservation and recovery

All evidence stays outside tracked source in `../codex-branch-audit-private-20261108/`. No raw run contents, private receipt contents, local file inventory, databases, credentials or bundle bytes are added to GitHub. This is an additive backup on the same machine/OneDrive volume, **not an independent offsite backup or a transactionally consistent backup of a running database**. Every source remains untouched; worktrees remain blocked until their owners confirm inactivity and backup suitability.

- `local-evidence-verified.zip`: 147,632,566 bytes; SHA-256 `4c03ba0d7e558fbb5f35e0896a716daaf0e2c018e857e7d6f41014bd1bf4b9d7`. All 4,533 inventoried research-run files and two loose AGY-side files are present; archived bytes were independently read back and hashed. Cache files are excluded. An earlier incomplete private ZIP from a directory-entry handling error is not the verified backup and must not be used for recovery.
- `preservation.json`: private per-member source path, byte size, SHA-256 and copy-stability record. Original sources are not removed or made writable.
- `latest/graph.git`: separate complete refreshed remote object/ref snapshot at the manifest SHAs; the initial `graph.git` is also retained. Neither is a worktree used by any agent.
- Three local-ref bundles, each verified:
  - `anti_gravity-jaegers.bundle`: 3,956,096 bytes; SHA-256 `239db4b6e661bbff163f2b1634eded41e49e08bb0db3fa0140d509bf1fbcd52e`.
  - `grok-jaegers.bundle`: 3,375,182 bytes; SHA-256 `b18847f5be55ed95787eb426899f7089338ca3df9387550280b9e38aeb066de1`.
  - `jaegers.bundle`: 3,379,877 bytes; SHA-256 `28f4348fb8d8e72be2e235073c2ff1f5d89567b2fa53eec917b328684ce7abae`.

The original frozen main pair was hashed directly and agrees with the backed-up members:

| Existing path under `jaegers/Jaeger_Main/House_Edge/research_runs/` | Bytes | SHA-256 |
| --- | ---: | --- |
| `REVIEW_MAIN_9PM/submission.csv` | 195,579 | `b718f2d5e14a5a508d3c6c3658259042228a7a4d38e0221513e46e5590d9babf` |
| `REVIEW_MAIN_9PM/code.zip` | 8,263 | `9a8a9e0e18a8d21d30474b3e007156c1f19be4f693dd3b2235019be830d3001f` |

Recovery, only if a future reviewed retirement needs reversal:

1. Check that the branch name and 40-character tip match this manifest, and verify the chosen bundle/archive hashes. Work in a **new recovery checkout**, never an active agent checkout.
2. Inspect the private remote snapshot with `git -C <private-graph.git> cat-file -e <exact-tip>^{commit}` and `git -C <private-graph.git> show --no-patch <exact-tip>`. For a local ref absent from that snapshot, run `git -C <new-recovery-repo> bundle verify <matching.bundle>` and fetch the preserved branch from that bundle into a new recovery branch.
3. Restore files from the ZIP to a new destination, then compare every restored byte length/SHA-256 with private `preservation.json`. Do not overwrite live worktrees. An SQLite/live-output snapshot may require owner review before use.
4. A remote branch can be recreated from the preserved object using the exact `SHA:refs/heads/name` refspec, only after confirming the remote ref is currently absent and obtaining the same human/owner authorization. Never force-update an existing ref. Retain all private backups through review and any eventual retirement verification.

## Reproduce the read-only audit

Use a fresh **private directory outside all tracked checkouts**. The following PowerShell collection uses GitHub CLI authentication already configured locally; no token is printed or copied. Do not overwrite the preserved baseline snapshot. Record the actual repository URL and use a new directory for each attempt.

```powershell
$auditPrivate = Join-Path $env:TEMP ('jaegers-branch-audit-' + [guid]::NewGuid())
New-Item -ItemType Directory -Path $auditPrivate | Out-Null
$auditEndpoints = [ordered]@{
  branches = 'branches?per_page=100'
  pulls = 'pulls?state=all&per_page=100'
  issues = 'issues?state=all&per_page=100'
  comments = 'issues/comments?per_page=100'
}
foreach ($entry in $auditEndpoints.GetEnumerator()) {
  $auditJson = gh api --paginate --slurp "repos/AsvM45/jaegers/$($entry.Value)"
  if ($LASTEXITCODE -ne 0) { throw "Snapshot failed: $($entry.Key)" }
  [IO.File]::WriteAllText((Join-Path $auditPrivate ($entry.Key + '.json')),
    ($auditJson -join "`n"), [Text.UTF8Encoding]::new($false))
}
git clone --bare https://github.com/AsvM45/jaegers.git (Join-Path $auditPrivate 'graph.git')
if ($LASTEXITCODE -ne 0) { throw 'Graph snapshot failed' }
# Run from THIS dedicated audit worktree; '..' is the workspace search root.
python -X utf8 -B tools/audit_branch_retirement.py `
  --graph (Join-Path $auditPrivate 'graph.git') --workspace .. `
  --github-snapshot $auditPrivate |
  Set-Content -Encoding utf8 (Join-Path $auditPrivate 'audit.json')
if ($LASTEXITCODE -ne 0) { throw 'Audit blocked; inspect private errors' }
```

The tool has **no apply/delete mode** and performs no network calls. It uses `GIT_OPTIONAL_LOCKS=0`, removes inherited Git routing variables, and supplies per-process `safe.directory` only; it does not edit global Git config, indexes, refs or source. Its stdout is **private** because exact local filenames/statuses are included. Cache paths are recorded without opening/statting each dependency; noncache and research evidence receive file metadata. A remote-ref mismatch against the bare graph fails closed; refresh the private snapshot instead of trusting a mixed-time inventory. Other local inspection/discovery errors produce exit 2 and block retirement candidates. Changing claims or dirty files also block the affected refs.

The audit is point-in-time and cannot lock other agents' work. It hashes frozen artifacts, inventories other ignored files by metadata and records changed-during-scan status; the separate preservation pass verifies actual archived bytes. No snapshot is permanent deletion consent.

Observed dry-run summary:

```text
remote_branch_count=37; pr_count=41; physical_checkouts=10; repositories=3
history: MERGED_EXACT_HEAD=30 ANCESTOR_NO_UNIQUE_COMMITS=5 UNIQUE_UNMERGED=2
operational: MERGED_EXACT_HEAD=16 ANCESTOR_NO_UNIQUE_COMMITS=3 KEEP_ACTIVE=14 BLOCKED=4
review_candidates=19; retirement_ready_count=0; retired=[]
discovery_errors=[]; checkout_errors=0
zero_diff_merge_changed_files: #62=0 #63=0 #64=0
frozen_pair_hashes=matched; private_archive_members_verified=4535; unstable_copies=0
local_ref_bundles_verified=3; teammate_HEAD_status_recheck=9/9 unchanged
```

Private raw input snapshot SHA-256 hashes (do not publish their raw contents):

| Snapshot | SHA-256 |
| --- | --- |
| `branches.json` | `db723ab171f3f64432296befea706f43e723c48abbb995fddd026c65ceec3ba9` |
| `pulls.json` | `3d422bddfd1523778a5e23c891583dbfe6ec5eb70d40e7a66c785f47dcf35e1e` |
| `issues.json` | `06e506682d2137157d61bba683d8f840cfbec62bcdfea72f35a1361e22d469ed` |
| `comments.json` | `c66e1d47843a68294aed14ecb7881c847e2b2034aaf76cc396e97ccf6c4882a9` |

## Validation and remaining approval

- Real full-graph/checkouts dry run completed without discovery/checkout errors. Frozen hashes, exact-head/main-reachability checks, and zero-diff trees were actually measured.
- Ten focused audit regression/adversarial checks passed: squash/nonancestor acceptance, postmerge tip changes, closed-unmerged PR rejection, wrong target rejection, ancestor classification, strict standalone handoff/closed-issue handling, snapshot shape, ref-race fail-closed, absent apply mode and local-only commit detection. The private harness is preserved as `verify_audit.py` (outside the issue's two-file tracked scope); command: `python -X utf8 -B ../codex-branch-audit-private-20261108/verify_audit.py`.
- Existing governance suite: `python -X utf8 -B -m unittest discover -s tests -p test_agent_collaboration_policy.py -v` — **10 passed**. `git diff --check` passed. Local Python is **3.12.9**; no Python 3.13 execution is claimed locally. The normal PR workflow runs governance under 3.13.
- Scope is only this new report and `tools/audit_branch_retirement.py`. No runtime/model tests are needed for unchanged runtime; CI and the ownership/overlap gate must still be reviewed on the actual PR.

Before any retirement: human reviewer accepts this preflight; the relevant owner confirms each branch is inactive; any checked-out branch remains excluded until the owner separately clears/removes its clean worktree and confirms evidence backup; all open PR/claim holds are resolved; refresh remote refs, PRs, claims, local statuses and exact SHAs immediately before each small batch. If anything changes or remains ambiguous, keep the branch. There is no blanket approval for the 19 REVIEW rows, no planned forced local deletion, and no automatic main merge.

Retirements actually performed: **none**. Required next action: independent human review of this issue-linked audit PR. Keep #65 open through review/handoff and any separately authorized later retirement; do not claim #66. After review, post the accepted preflight/holds to #18 as required by #65.
