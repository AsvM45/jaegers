#!/usr/bin/env python3
"""Read-only issue #65 preflight. JSON stdout contains PRIVATE local filenames.

Supply a separate bare graph copy and four complete `gh api --paginate --slurp`
snapshots: branches.json, pulls.json (state=all), issues.json (state=all), and
comments.json (issues/comments). This tool has no retirement/apply mode, performs
no network calls, and never updates refs, indexes, files, or worktrees. Redirect
stdout outside every tracked checkout. Snapshot evidence is not deletion consent.
"""

import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import stat as filemode
import subprocess
import sys


PROTECTED = {
    "main", "hitachi", "agy", "agent/antigravity-he14-databricks",
    "agent/claude-release-he06-adaptation", "agent/grok-he06-adaptation-takeover",
    "agent/codex-branch-consolidation",
}
CLAIM = re.compile(
    r"<!--\s*jaegers-claim:v1\s+agent=([a-z0-9-]+)\s+"
    r"branch=([a-z0-9/-]+)\s+paths=([a-zA-Z0-9_.*\-/|]+)\s*-->", re.I
)
HANDOFF = re.compile(
    r"(?m)^[ \t]*<!--[ \t]*jaegers-handoff:v1[ \t]+"
    r"branch=([a-z0-9/-]+)[ \t]*-->[ \t]*$", re.I
)
SKIP = {".git", ".venv", "venv", "node_modules", "__pycache__",
        "research_runs", ".runtime", ".pytest_cache", ".mypy_cache", "graph.git"}
CACHES = {".runtime", ".venv", "venv", "node_modules", "__pycache__",
          ".pytest_cache", ".mypy_cache"}


def git(repo, *args, accepted=(0,)):
    """An explicit per-process ownership exception; never alter global config."""
    repo = Path(repo).resolve()
    env = dict(os.environ, GIT_OPTIONAL_LOCKS="0", GIT_TERMINAL_PROMPT="0")
    # Do not let inherited Git routing silently inspect a different checkout.
    for name in ("GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE", "GIT_COMMON_DIR"):
        env.pop(name, None)
    result = subprocess.run(
        ["git", "--no-optional-locks", "-c", f"safe.directory={repo.as_posix()}",
         "-C", str(repo), *args], env=env, capture_output=True,
        encoding="utf-8", errors="replace", timeout=120,
    )
    if result.returncode not in accepted:
        raise RuntimeError(f"git {args[0]} failed ({result.returncode}): "
                           + result.stderr.strip())
    return result.stdout


def digest(path):
    hasher = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            hasher.update(block)
    return hasher.hexdigest()


def load_pages(folder, name):
    value = json.loads((folder / (name + ".json")).read_text(encoding="utf-8-sig"))
    if not isinstance(value, list) or any(not isinstance(p, list) for p in value):
        raise ValueError(name + " must be complete --paginate --slurp page arrays")
    return [row for page in value for row in page]


def discover(workspace):
    """Find checkouts, including distinct clones; do not traverse symlinks."""
    checkouts, errors = set(), []
    def onerror(error):
        errors.append(str(error))
    for base, dirs, files in os.walk(workspace, followlinks=False, onerror=onerror):
        path = Path(base)
        if ".git" in dirs or ".git" in files:
            checkouts.add(path.resolve())
        dirs[:] = sorted(d for d in dirs if d not in SKIP
                         and not (path / d).is_symlink())
    for checkout in sorted(checkouts):
        try:
            for line in git(checkout, "worktree", "list", "--porcelain").splitlines():
                if line.startswith("worktree "):
                    checkouts.add(Path(line[9:]).resolve())
        except (RuntimeError, OSError) as error:
            errors.append(str(error))
    return sorted(checkouts), errors


def inventory_checkout(path, remote_reachable):
    """Keep exact statuses private; metadata only for untracked/ignored files."""
    record = {"path": str(path), "errors": []}
    try:
        record["head"] = git(path, "rev-parse", "HEAD").strip()
        record["branch"] = git(path, "symbolic-ref", "--quiet", "--short", "HEAD",
                               accepted=(0, 1)).strip() or None
        record["common_dir"] = git(path, "rev-parse", "--path-format=absolute",
                                   "--git-common-dir").strip()
        before = git(path, "status", "--porcelain=v1", "-z", "--untracked-files=all")
        ignored = git(path, "status", "--porcelain=v1", "-z", "--ignored",
                      "--untracked-files=all")
        record["status_z"] = before
        record["ignored_status_z"] = ignored
        record["dirty"] = bool(before)
        files = set()
        for args in (("ls-files", "--others", "--exclude-standard", "-z"),
                     ("ls-files", "--others", "--ignored", "--exclude-standard", "-z")):
            files.update(filter(None, git(path, *args).split("\0")))
        metadata, cache_paths, buckets = [], [], Counter()
        for name in sorted(files):
            parts = Path(name).parts
            if "research_runs" not in parts and CACHES.intersection(parts):
                cache_paths.append(name)
                continue
            source = path / name
            try:
                stat = source.lstat()
                directory = filemode.S_ISDIR(stat.st_mode)
                metadata.append({"path": name, "bytes": stat.st_size,
                                 "mtime_ns": stat.st_mtime_ns,
                                 "symlink": filemode.S_ISLNK(stat.st_mode), "directory": directory})
                bucket = "research_runs" if "research_runs" in parts else "other"
                if directory:
                    buckets[bucket + "_directories"] += 1
                else:
                    buckets[bucket + "_files"] += 1
                    buckets[bucket + "_bytes"] += stat.st_size
            except OSError as error:
                record["errors"].append(str(error))
        record["local_files"] = metadata
        record["dependency_cache_paths"] = cache_paths
        record["dependency_cache_entries"] = len(cache_paths)
        record["local_file_totals"] = dict(buckets)
        record["local_branches"] = []
        for line in git(path, "for-each-ref", "--format=%(refname:short) %(objectname)",
                        "refs/heads").splitlines():
            branch, sha = line.split()
            local_commits = set(git(path, "rev-list", sha).splitlines())
            unique = len(local_commits - remote_reachable)
            record["local_branches"].append({"branch": branch, "sha": sha,
                                              "commits_not_on_any_remote": unique})
        after = git(path, "status", "--porcelain=v1", "-z", "--untracked-files=all")
        record["changed_during_scan"] = (before != after or record["head"] !=
                                           git(path, "rev-parse", "HEAD").strip())
    except (RuntimeError, OSError, ValueError, subprocess.TimeoutExpired) as error:
        record["errors"].append(str(error))
    return record


def active_claims(issues, comments):
    """Open-issue markers only, strict standalone handoff, chronological replay."""
    open_numbers = {i["number"] for i in issues
                    if i["state"] == "open" and "pull_request" not in i}
    claims = {}
    for comment in sorted(comments, key=lambda c: c["id"]):
        number = int(comment["issue_url"].rsplit("/", 1)[-1])
        if number not in open_numbers:
            continue
        body = comment.get("body") or ""
        for match in HANDOFF.finditer(body):
            claims.pop((number, match[1]), None)
        for match in CLAIM.finditer(body):
            claims[number, match[2]] = {"issue": number, "agent": match[1],
                                        "branch": match[2], "url": comment["html_url"]}
    return list(claims.values())


def history_class(sha, branch, pulls, ancestor, ahead):
    matches = [p for p in pulls if p.get("merged_at") and
               p["base"]["ref"] == "main" and p["base"]["repo"]["full_name"] ==
               "AsvM45/jaegers" and p["head"]["ref"] == branch and p["head"]["sha"] == sha]
    if matches:
        return "MERGED_EXACT_HEAD", matches
    if ancestor and ahead == 0:
        return "ANCESTOR_NO_UNIQUE_COMMITS", []
    return "UNIQUE_UNMERGED", []


def run(graph, workspace, folder):
    branches, pulls, issues, comments = [load_pages(folder, n) for n in
                                         ("branches", "pulls", "issues", "comments")]
    refs = {b["name"]: b["commit"]["sha"] for b in branches}
    if len(refs) != len(branches) or "main" not in refs:
        raise ValueError("Duplicate branch names or missing main in snapshot")
    graph_refs = dict(line.split() for line in git(
        graph, "for-each-ref", "--format=%(refname:short) %(objectname)", "refs/heads").splitlines())
    if refs != graph_refs:
        raise ValueError("Remote JSON/graph refs differ; refresh BOTH private snapshots")
    main = refs["main"]
    paths, errors = discover(workspace)
    remote_reachable = set(git(graph, "rev-list", "--all").splitlines())
    worktrees = [inventory_checkout(p, remote_reachable) for p in paths]
    claims = active_claims(issues, comments)
    open_prs = [p for p in pulls if p["state"] == "open"]
    manifest = []
    for branch, sha in sorted(refs.items()):
        behind, ahead = map(int, git(graph, "rev-list", "--left-right", "--count",
                                     main + "..." + sha).split())
        ancestor = git(graph, "merge-base", main, sha).strip() == sha
        category, matches = history_class(sha, branch, pulls, ancestor, ahead)
        # A merged PR must itself be reachable from this main snapshot.
        integrated = [p for p in matches if git(graph, "merge-base", main,
                      p["merge_commit_sha"]).strip() == p["merge_commit_sha"]]
        if matches and len(integrated) != len(matches):
            category = "BLOCKED"
        uses = [w for w in worktrees if w.get("branch") == branch]
        locals_ = [dict(local, path=w["path"]) for w in worktrees
                   for local in w.get("local_branches", []) if local["branch"] == branch]
        active = [c for c in claims if c["branch"] == branch]
        prs = [p["number"] for p in open_prs if p["head"]["ref"] == branch
               or p["base"]["ref"] == branch]
        blockers = []
        if branch in PROTECTED: blockers.append("EXPLICITLY_PROTECTED")
        if prs: blockers.append("OPEN_PR")
        if active: blockers.append("OPEN_ISSUE_CLAIM")
        if uses: blockers.append("CHECKED_OUT")
        if any(w.get("dirty") for w in uses): blockers.append("DIRTY_WORKTREE")
        if any(w.get("local_files") for w in uses): blockers.append("LOCAL_IGNORED_OR_UNTRACKED_EVIDENCE")
        if any(w.get("changed_during_scan") for w in uses): blockers.append("CONCURRENT_CHANGE")
        if any(l["commits_not_on_any_remote"] is None or
               l["commits_not_on_any_remote"] > 0 for l in locals_):
            blockers.append("LOCAL_ONLY_COMMITS_OR_UNKNOWN")
        if any(l["sha"] != sha for l in locals_): blockers.append("LOCAL_TIP_DIFFERS")
        if errors or any(w["errors"] for w in worktrees): blockers.append("INCOMPLETE_LOCAL_INVENTORY")
        if category in ("UNIQUE_UNMERGED", "BLOCKED"): blockers.append(category)
        classification = ("KEEP_ACTIVE" if branch in PROTECTED or prs or active else
                          "BLOCKED" if blockers else category)
        manifest.append({"branch": branch, "sha": sha, "ahead_main": ahead,
            "behind_main": behind, "ancestor_main": ancestor, "history_class": category,
            "classification": classification,
            "merged_exact_prs": [p["number"] for p in integrated], "open_prs": prs,
            "claims": active, "worktrees": [w["path"] for w in uses],
            "local_refs": locals_, "blockers": blockers,
            "history_candidate": category in ("MERGED_EXACT_HEAD", "ANCESTOR_NO_UNIQUE_COMMITS"),
            "review_candidate": not blockers,
            "retirement_ready": False, "action": "KEEP; owner/human confirmation required"})
    duplicates = []
    for number in (62, 63, 64):
        pr = next(p for p in pulls if p["number"] == number)
        merge = pr["merge_commit_sha"]
        changed = git(graph, "diff", "--name-only", merge + "^1", merge).splitlines()
        duplicates.append({"pr": number, "head_sha": pr["head"]["sha"],
            "merge_sha": merge, "merged_at": pr["merged_at"], "changed_paths": changed,
            "tree": git(graph, "rev-parse", merge + "^{tree}").strip(),
            "first_parent_tree": git(graph, "rev-parse", merge + "^1^{tree}").strip()})
    frozen = []
    for w in worktrees:
        for name in ("submission.csv", "code.zip"):
            path = Path(w["path"]) / "Jaeger_Main/House_Edge/research_runs/REVIEW_MAIN_9PM" / name
            if path.is_file():
                frozen.append({"path": str(path), "bytes": path.stat().st_size,
                               "sha256": digest(path)})
    return {"schema": "jaegers-branch-audit:v1", "mode": "READ_ONLY_DRY_RUN",
        "generated_utc": datetime.now(timezone.utc).isoformat(), "main_sha": main,
        "snapshot_hashes": {n: digest(folder / (n + ".json")) for n in
                            ("branches", "pulls", "issues", "comments")},
        "remote_branch_count": len(refs), "pr_count": len(pulls),
        "open_prs": [{"number": p["number"], "head": p["head"]["ref"],
                       "sha": p["head"]["sha"]} for p in open_prs],
        "active_claims": claims, "discovery_errors": errors, "worktrees": worktrees,
        "branches": manifest, "zero_diff_merges": duplicates, "frozen_artifacts": frozen,
        "counts": dict(Counter(b["classification"] for b in manifest)),
        "retired": [], "retirement_ready_count": 0,
        "limitations": ["Snapshots race active development; refresh before any action.",
                        "Discovery covers this workspace and registered worktrees only.",
                        "Metadata inventory is not a backup or proof of agent inactivity.",
                        "No owner sign-offs are inferred; no destructive commands exist."]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--graph", type=Path, required=True, help="Separate bare graph snapshot")
    parser.add_argument("--workspace", type=Path, required=True, help="Local checkout search root")
    parser.add_argument("--github-snapshot", type=Path, required=True)
    args = parser.parse_args()
    try:
        result = run(args.graph.resolve(), args.workspace.resolve(), args.github_snapshot.resolve())
        print(json.dumps(result, indent=2, ensure_ascii=True))
        return 2 if result["discovery_errors"] or any(w["errors"] for w in result["worktrees"]) else 0
    except (RuntimeError, OSError, ValueError, KeyError, StopIteration, subprocess.TimeoutExpired) as error:
        print("BLOCKED: " + str(error), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
