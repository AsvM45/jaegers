#!/usr/bin/env python3
"""No-network Markdown link checker for canonical JAEGERS documentation.

Historical archived docs are intentionally excluded from the default path list.
Cannot verify external web URLs, dynamic GitHub anchors or published Wiki pages.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import re
import sys
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[1]

CANONICAL = (
    "README.md",
    "CONTRIBUTING.md",
    "SECURITY.md",
    "docs/CURRENT_STATE.md",
    "docs/architecture/SYSTEM_OVERVIEW.md",
    "docs/science/EVALUATION_AND_PROVENANCE.md",
    "docs/runbooks/CI_AND_RELEASE.md",
    "docs/agents/GITHUB_AGENTS_AND_WORKTREES.md",
    "docs/adr/0001-github-engineering-features.md",
    "docs/wiki/Home.md",
    "docs/wiki/_Sidebar.md",
    "docs/ops/PR_GOVERNANCE_RUNBOOK.md",
    "docs/ops/BRANCH_CONSOLIDATION_AUDIT.md",
)
LINK = re.compile(r"(?<!!)\[[^\]]+\]\(([^)]+)\)")


def local_links(source: Path):
    """Yield href and resolved path for direct Markdown file links."""
    data = source.read_text(encoding="utf-8-sig")
    fenced = False
    for line in data.splitlines():
        if line.lstrip().startswith(("~~~", "```")):
            fenced = not fenced
            continue
        if fenced:
            continue
        for match in LINK.finditer(line):
            raw = match.group(1).strip()
            if raw.startswith("<") and ">" in raw:
                raw = raw[1:raw.index(">")]
            else:
                raw = raw.split(" ", 1)[0]
            if (not raw or raw.startswith("#") or raw.startswith("/")
                    or re.match(r"^[A-Za-z][A-Za-z0-9+.-]*:", raw)):
                continue
            filepart = unquote(raw.split("#", 1)[0].split("?", 1)[0])
            if filepart:
                yield raw, (source.parent / filepart).resolve()


def check(paths=CANONICAL, root=ROOT):
    errors = []
    root = root.resolve()
    for name in paths:
        path = (root / name).resolve()
        if not path.is_file():
            errors.append(f"{name}: page missing")
            continue
        if root not in path.parents and path != root:
            errors.append(f"{name}: page outside repository")
            continue
        for link, dest in local_links(path):
            if root not in dest.parents and dest != root:
                errors.append(f"{name}: link escapes repository: {link}")
            elif not dest.exists():
                errors.append(f"{name}: missing target: {link}")
    return errors


def self_test():
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "home.md").write_text("[Existing](x.md) [Remote](https://example.com/a) "
                                      "[Same](#anchor)\n", encoding="utf-8")
        (root / "x.md").write_text("# Found\n", encoding="utf-8")
        assert check(("home.md",), root) == [], "valid references should pass"
        (root / "x.md").unlink()
        failed = check(("home.md",), root)
        assert len(failed) == 1 and "missing target" in failed[0], failed
    print("DOCS CHECKER SELF-TEST: PASS")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("files", nargs="*", help="Repo-relative Markdown pages; default is canonical index")
    args = parser.parse_args()
    if args.self_test:
        self_test()
    errors = check(tuple(args.files) if args.files else CANONICAL)
    for error in errors:
        print("DOCS LINK FAIL:", error, file=sys.stderr)
    if errors:
        print(f"DOCS LINK CHECK FAILED: {len(errors)} missing/unsafe references")
        return 1
    print(f"DOCS LINK CHECK PASS: {len(args.files) if args.files else len(CANONICAL)} pages")
    return 0


if __name__ == "__main__":
    sys.exit(main())
