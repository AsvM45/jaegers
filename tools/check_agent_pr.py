#!/usr/bin/env python3
"""Read-only GitHub PR collaboration gate. Run trusted base-branch copy only."""
import fnmatch, json, os, re, sys
from pathlib import Path
from urllib.request import Request, urlopen

BRANCH = re.compile(r"^(agent|human)/[a-z0-9][a-z0-9-]{2,90}$")
CLAIM = re.compile(r"(?m)^[ \t]*<!--[ \t]*jaegers-claim:v1\s+agent=([a-z0-9-]+)\s+branch=([a-z0-9/-]+)\s+paths=([a-zA-Z0-9_.*\-/|]+)\s*-->[ \t]*$", re.I)
HANDOFF = re.compile(r"(?m)^[ \t]*<!--[ \t]*jaegers-handoff:v1[ \t]+branch=([a-z0-9/-]+)[ \t]*-->[ \t]*$", re.I)
FIELDS = ("Agent-ID", "Issue", "Worktree", "Tests", "Handoff")

def metadata(body):
    return {k: (m.group(1).strip() if (m := re.search(r"^" + k + r":\s*(.+)$", body or "", re.M | re.I)) else "") for k in FIELDS}

def latest_claim(comments, branch):
    active = None
    for comment in comments:
        body = comment.get("body") or ""
        if any(m.group(1) == branch for m in HANDOFF.finditer(body)):
            active = None
        for m in CLAIM.finditer(body):
            if m.group(2) == branch:
                active = {"agent": m.group(1), "paths": m.group(3).split("|")}
    return active

def covered(path, pattern):
    return path.startswith(pattern) if pattern.endswith("/") else fnmatch.fnmatchcase(path, pattern)

def check(event, paths, comments, other_pr_paths, merged_prs=(), head_ancestor=False):
    pr = event["pull_request"]; branch = pr["head"]["ref"]; fields = metadata(pr.get("body") or "")
    errors = []
    if not BRANCH.fullmatch(branch): errors.append("Branch must be agent/<slug> or human/<slug>")
    if not paths: errors.append("No files changed")
    # Existing PRs #19-#22 existed before this workflow and are exempt from new claim metadata.
    if int(pr["number"]) > 22:
        for k in FIELDS:
            if k != "Issue" and len(fields[k]) < 3:
                errors.append("Missing PR field: " + k)
        issue = re.fullmatch(r"#([1-9][0-9]*)", fields["Issue"])
        if not issue: errors.append("Issue must be #NN")
        claim = latest_claim(comments, branch)
        if not claim: errors.append("Missing named issue claim for this branch")
        else:
            if claim["agent"] != fields["Agent-ID"]: errors.append("Agent-ID does not match issue claim")
            missing = [p for p in paths if not any(covered(p, pattern) for pattern in claim["paths"])]
            if missing: errors.append("Files outside claimed write scope: " + ", ".join(missing))
        if any(p.startswith(("Jaeger_Main/House_Edge/jaegers_entry/", "Jaeger_Main/House_Edge/slot_forecasting/")) for p in paths):
            if fields["Agent-ID"] not in ("chat", "codex", "release"):
                errors.append("Champion/organizer source changes require release integrator plus human review")
    for other, their_paths in other_pr_paths.items():
        collision = sorted(set(paths) & set(their_paths))
        if collision: errors.append(f"Overlapping open PR #{other}: " + ", ".join(collision))
    if int(pr["number"]) > 22:
        head_sha = pr.get("head", {}).get("sha")
        if head_sha:
            duplicates = sorted({int(p["number"]) for p in merged_prs
                                 if p.get("merged_at") and p.get("head", {}).get("sha") == head_sha
                                 and int(p["number"]) != int(pr["number"])})
            if duplicates:
                errors.append("Head SHA was already integrated by merged PR(s): "
                              + ", ".join("#" + str(n) for n in duplicates))
        if head_ancestor:
            errors.append("PR head is already an ancestor of main; no new commits to integrate")
        if len(re.findall(r"(?mi)^Issue:\s*#[1-9][0-9]*\s*$", pr.get("body") or "")) != 1:
            errors.append("Exactly one canonical Issue: #NN line is required")
    return errors

def get_json(url, token):
    req = Request(url, headers={"Authorization": "Bearer " + token, "Accept": "application/vnd.github+json", "User-Agent": "jaegers-pr-check", "X-GitHub-Api-Version": "2022-11-28"})
    with urlopen(req, timeout=20) as resp: return json.load(resp)

def pages(url, token):
    out=[]
    for page in range(1,22):
        batch=get_json(url + ("&" if "?" in url else "?") + f"per_page=100&page={page}", token)
        if not isinstance(batch,list): raise ValueError("Unexpected API response: "+url)
        out += batch
        if len(out)>2000: raise ValueError("API pagination limit exceeded")
        if len(batch)<100: return out
    raise ValueError("API page limit exceeded")

def main():
    token=os.environ["GITHUB_TOKEN"]; repo=os.environ["GITHUB_REPOSITORY"]
    event=json.loads(Path(os.environ["GITHUB_EVENT_PATH"]).read_text())
    pr=event["pull_request"]; number=pr["number"]; root="https://api.github.com/repos/"+repo
    live = get_json(f"{root}/pulls/{number}", token)
    if live["head"]["sha"] != pr["head"]["sha"]:
        print("BLOCKED: PR head moved since this event; rerun checks on latest push")
        return 1
    paths=[x["filename"] for x in pages(f"{root}/pulls/{number}/files",token)]
    issue=re.fullmatch(r"#([1-9][0-9]*)",metadata(pr.get("body") or "")["Issue"])
    comments=pages(f"{root}/issues/{issue.group(1)}/comments",token) if issue else []
    others={}
    for p in pages(f"{root}/pulls?state=open",token):
        if p["number"]!=number:
            others[p["number"]]=[x["filename"] for x in pages(f"{root}/pulls/{p['number']}/files",token)]
    merged = pages(f"{root}/pulls?state=closed", token)
    ancestor = False
    head_sha, base_sha = pr["head"].get("sha"), pr["base"].get("sha")
    if head_sha and base_sha:
        comparison = get_json(f"{root}/compare/{head_sha}...{base_sha}", token)
        ancestor = (comparison.get("status") in ("ahead", "identical")
                    and comparison.get("behind_by", 0) == 0)
    errors=check(event,paths,comments,others,merged_prs=merged,head_ancestor=ancestor)
    for err in errors: print("FAIL:",err)
    print("AGENT COLLABORATION:", "BLOCKED" if errors else "PASS", "PR",number,"changed",len(paths))
    return 1 if errors else 0

if __name__=="__main__":
    try: sys.exit(main())
    except Exception as error:
        print("BLOCKED:",repr(error),file=sys.stderr)
        sys.exit(2)
