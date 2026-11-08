"""HE-06 adaptation-round orchestrator: verify kit -> fallback forecasts -> official checks -> CSV+ZIP -> cold rerun.

Run from Jaeger_Main/House_Edge (on Linux/WSL for the real release, see README.md here):

    python adaptation/run_adaptation.py --kit <adaptation_kit>/public --main public \
        --out research_runs/adaptation --expect-round adaptation \
        --env NPY_DISABLE_CPU_FEATURES=<policy>

Nothing is uploaded. The protected champion `jaegers_entry/` is copied, never edited. The champion refits its
expert prior and gradient-boosted stacker on whatever kit is mounted at `--data`/train, so the fallback adapts to
the new round's training machines automatically.

Outputs under --out: kit_report.json, validation/, test/, test_repeat/, release/{submission.csv, code.zip, source/},
cold/, manifest.json. Every step writes its evidence before the next one starts; a failure stops the run.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import platform
import re
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

HE = Path(__file__).resolve().parents[1]
PAYOUTS = {"0", "1", "2", "5", "20"}
ROUND_POINTS = {"main": 60, "adaptation": 40}
TOLERANCE = 1e-8


# --------------------------------------------------------------------------- helpers

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def tree_sha(folder):
    folder = Path(folder)
    return {p.relative_to(folder).as_posix(): sha(p) for p in sorted(folder.rglob("*")) if p.is_file()}


def rows(path):
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def write_json(path, value):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def read_csv_probs(path):
    return {r["query_id"]: [float(r[c]) for c in ("p_0", "p_1", "p_2", "p_5", "p_20")] for r in rows(path)}


def max_normalized_diff(a, b):
    pa, pb = read_csv_probs(a), read_csv_probs(b)
    if pa.keys() != pb.keys():
        raise ValueError("query IDs differ between the two CSVs")
    worst = 0.0
    for k in pa:
        sa, sb = sum(pa[k]), sum(pb[k])
        worst = max(worst, max(abs(x / sa - y / sb) for x, y in zip(pa[k], pb[k])))
    return worst


def run(cmd, cwd, env_extra, log_dir):
    log_dir.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ, **env_extra)
    p = subprocess.run([str(c) for c in cmd], cwd=cwd, env=env, capture_output=True, text=True)
    (log_dir / "stdout.log").write_text(p.stdout, encoding="utf-8")
    (log_dir / "stderr.log").write_text(p.stderr, encoding="utf-8")
    if p.returncode != 0:
        raise RuntimeError(f"command failed ({p.returncode}): {cmd}\n{p.stderr[-2000:]}")
    return p.stdout


# --------------------------------------------------------------------------- 1. kit verification

def verify_kit(kit, main=None, expect_round="adaptation"):
    kit = Path(kit)
    meta = json.loads((kit / "metadata.json").read_text(encoding="utf-8"))
    problems = []
    if meta.get("round") != expect_round:
        problems.append(f"metadata round is {meta.get('round')!r}, expected {expect_round!r}")
    if meta.get("max_points") != ROUND_POINTS.get(expect_round):
        problems.append(f"max_points is {meta.get('max_points')!r}, expected {ROUND_POINTS.get(expect_round)}")
    if not re.fullmatch(r"[0-9a-f]{24}", str(meta.get("season_id", ""))):
        problems.append("season_id is not a 24-hex id")
    needed = ["train/queries.csv", "train/history.csv", "validation/queries.csv", "validation/history.csv",
              "validation/targets.csv", "validation/reference.csv", "validation/conditions.csv",
              "test/queries.csv", "test/history.csv"]
    missing = [n for n in needed if not (kit / n).exists()]
    problems += [f"missing {n}" for n in missing]
    report = {"kit": str(kit), "metadata": meta, "missing": missing}
    if not missing:
        ids = {}
        for split in ("train", "validation", "test"):
            q = rows(kit / split / "queries.csv")
            qids = [r["query_id"] for r in q]
            if len(qids) != len(set(qids)):
                problems.append(f"duplicate query_id in {split}")
            ids[split] = set(qids)
            cut = {(r["episode_id"], r["machine_id"]): int(r["cutoff"]) for r in q}
            late, bad_payout = 0, 0
            for h in rows(kit / split / "history.csv"):
                key = (h["episode_id"], h["machine_id"])
                if key in cut and int(h["tick"]) >= cut[key]:
                    late += 1
                if h["payout"] not in PAYOUTS:
                    bad_payout += 1
            if late:
                problems.append(f"{split}: {late} history rows at/after cutoff")
            if bad_payout:
                problems.append(f"{split}: {bad_payout} history rows with unknown payout")
            report[f"{split}_queries"] = len(qids)
        if (kit / "test" / "targets.csv").exists() or (kit / "test" / "labels.csv").exists():
            problems.append("test truth file present in kit: refuse to proceed")
        if main is not None:
            main_ids = set()
            for split in ("train", "validation", "test"):
                p = Path(main) / split / "queries.csv"
                if p.exists():
                    main_ids |= {r["query_id"] for r in rows(p)}
            overlap = sorted((ids["train"] | ids["validation"] | ids["test"]) & main_ids)
            report["overlap_with_main"] = len(overlap)
            if overlap and expect_round == "adaptation":
                problems.append(f"{len(overlap)} query IDs overlap the main round, e.g. {overlap[:3]}")
            main_meta = Path(main) / "metadata.json"
            if main_meta.exists() and expect_round == "adaptation":
                if json.loads(main_meta.read_text(encoding="utf-8")).get("season_id") == meta.get("season_id"):
                    report["note_same_season_as_main"] = True
    report["sha256"] = tree_sha(kit)
    report["problems"] = problems
    report["ok"] = not problems
    return report


# --------------------------------------------------------------------------- 2-5. forecasts, checks, package, cold rerun

def checker_for(kit):
    """Prefer the kit's own check_submission.py (it carries that round's scorer); fall back to the repo's."""
    own = Path(kit).parent / "check_submission.py"
    return own if own.exists() else HE / "check_submission.py"


def predict(entry, kit, split, out_csv, env_extra, log_dir):
    run([sys.executable, Path(entry) / "predict.py", "--data", kit, "--split", split, "--out", out_csv],
        cwd=entry, env_extra=env_extra, log_dir=log_dir)


def check(kit, csv_path, split, log_dir):
    chk = checker_for(kit)
    out = run([sys.executable, chk, csv_path, "--data", kit, "--split", split], cwd=chk.parent, env_extra={}, log_dir=log_dir)
    result = {"checker": str(chk), "checker_sha256": sha(chk), "stdout": out.strip()}
    m = re.search(r"Validation points: ([0-9.]+) / ([0-9]+)", out)
    if m:
        result["points"], result["max_points"] = float(m.group(1)), int(m.group(2))
    if "VALID FORMAT" not in out:
        raise RuntimeError(f"checker did not report VALID FORMAT for {csv_path}")
    return result


def reproduce_command(env_extra):
    base = ["python", "predict.py", "--data", "/data", "--out", "/output/submission.csv"]
    return (["env"] + [f"{k}={v}" for k, v in sorted(env_extra.items())] + base) if env_extra else base


def stage_source(entry, dest, meta, env_extra):
    shutil.copytree(entry, dest, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    shutil.copyfile(HE / "requirements-runtime.txt", dest / "requirements.txt")
    cmd = reproduce_command(env_extra)
    (dest / "reproduce.json").write_text(json.dumps({"image": "python", "command": cmd}, indent=2) + "\n", encoding="utf-8")
    (dest / "README.md").write_text(
        f"# JAEGERS House Edge - {meta['round']} round\n\n"
        f"- Team: JAEGERS\n- Round: {meta['round']} ({meta.get('max_points')} points)\n- Season ID: {meta['season_id']}\n"
        f"- Environment: `python` image, CPython 3.13, exact pins in requirements.txt\n\n"
        f"## Recreate the forecast\n\nFrom the ZIP root:\n\n```sh\n{' '.join(cmd)}\n```\n\n"
        "The command reads `/data/train` (fits the expert prior and the gradient-boosted win stacker on this round's\n"
        "training machines) and `/data/test`, and writes all test queries to `/output/submission.csv`. No saved model\n"
        "files, no network, no randomness (fixed settings, random_state=0). Main-round data is not used.\n"
        + (f"Environment variables in the command pin NumPy CPU dispatch so Linux reruns are byte-identical.\n" if env_extra else "")
        + "\nModel: unchanged JAEGERS main-round champion (73 lag-context experts, peer evidence, size experts,\n"
          "HistGradientBoosting stacker), refit on the adaptation kit's train split.\n", encoding="utf-8")


def package(source, zip_path):
    sys.path.insert(0, str(HE))
    from slot_forecasting.submission_contract import package_code
    return package_code(source, zip_path)


def cold_rerun(zip_path, kit, workdir, log_dir):
    workdir = Path(workdir)
    sub, out = workdir / "submission", workdir / "output"
    sub.mkdir(parents=True); out.mkdir(parents=True)
    with zipfile.ZipFile(zip_path) as z:
        z.extractall(sub)
    if not (sub / "README.md").exists() or not (sub / "reproduce.json").exists():
        raise RuntimeError("ZIP root must contain README.md and reproduce.json")
    cmd = json.loads((sub / "reproduce.json").read_text(encoding="utf-8"))["command"]
    env_extra = {}
    if cmd and cmd[0] == "env":
        i = 1
        while i < len(cmd) and "=" in cmd[i]:
            k, v = cmd[i].split("=", 1); env_extra[k] = v; i += 1
        cmd = cmd[i:]
    cmd = [sys.executable if c == "python" else str(kit) if c == "/data" else str(out / "submission.csv")
           if c == "/output/submission.csv" else c for c in cmd]
    run(cmd, cwd=sub, env_extra=env_extra, log_dir=log_dir)
    return out / "submission.csv"


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--kit", required=True, help="the round's public/ folder (metadata.json, train/, validation/, test/)")
    ap.add_argument("--main", default=str(HE / "public"), help="main-round public/ folder, for ID disjointness")
    ap.add_argument("--out", required=True)
    ap.add_argument("--entry", default=str(HE / "jaegers_entry"))
    ap.add_argument("--expect-round", default="adaptation", choices=sorted(ROUND_POINTS))
    ap.add_argument("--env", action="append", default=[], help="KEY=VALUE pinned into the run and reproduce.json")
    a = ap.parse_args(argv)
    kit, out, entry = Path(a.kit).resolve(), Path(a.out).resolve(), Path(a.entry).resolve()
    env_extra = dict(e.split("=", 1) for e in a.env)
    out.mkdir(parents=True, exist_ok=False)
    manifest = {"status": "RUNNING", "python": sys.version, "platform": platform.platform(), "env_pinned": env_extra,
                "entry_sha256": tree_sha(entry)}
    write_json(out / "manifest.json", manifest)

    kit_report = verify_kit(kit, a.main, a.expect_round)
    write_json(out / "kit_report.json", kit_report)
    if not kit_report["ok"]:
        manifest.update(status="BLOCKED_KIT", problems=kit_report["problems"]); write_json(out / "manifest.json", manifest)
        print("KIT CHECK FAILED:", *kit_report["problems"], sep="\n  ")
        return 2
    meta = kit_report["metadata"]

    predict(entry, kit, "validation", out / "validation.csv", env_extra, out / "logs/validation")
    manifest["validation"] = check(kit, out / "validation.csv", "validation", out / "logs/validation_check")
    predict(entry, kit, "test", out / "test.csv", env_extra, out / "logs/test")
    predict(entry, kit, "test", out / "test_repeat.csv", env_extra, out / "logs/test_repeat")
    manifest["test_check"] = check(kit, out / "test.csv", "test", out / "logs/test_check")
    manifest["repeat_max_diff"] = max_normalized_diff(out / "test.csv", out / "test_repeat.csv")
    if manifest["repeat_max_diff"] > TOLERANCE:
        raise RuntimeError(f"test forecasts are not deterministic: {manifest['repeat_max_diff']}")
    write_json(out / "manifest.json", manifest)

    rel = out / "release"
    rel.mkdir()
    shutil.copyfile(out / "test.csv", rel / "submission.csv")
    stage_source(entry, rel / "source", meta, env_extra)
    package(rel / "source", rel / "code.zip")
    cold_csv = cold_rerun(rel / "code.zip", kit, out / "cold", out / "logs/cold")
    manifest["cold_max_diff"] = max_normalized_diff(rel / "submission.csv", cold_csv)
    if manifest["cold_max_diff"] > TOLERANCE:
        raise RuntimeError(f"cold rerun differs from submission.csv: {manifest['cold_max_diff']}")
    manifest.update(status="READY_FOR_HUMAN_REVIEW", round=meta["round"], season_id=meta["season_id"],
                    submission_sha256=sha(rel / "submission.csv"), submission_bytes=(rel / "submission.csv").stat().st_size,
                    code_zip_sha256=sha(rel / "code.zip"), code_zip_bytes=(rel / "code.zip").stat().st_size,
                    test_queries=kit_report["test_queries"], uploaded=False)
    write_json(out / "manifest.json", manifest)
    print(json.dumps({k: manifest[k] for k in ("status", "round", "season_id", "submission_sha256", "code_zip_sha256",
                                                "repeat_max_diff", "cold_max_diff")}, indent=2))
    if "points" in manifest["validation"]:
        print(f"validation: {manifest['validation']['points']} / {manifest['validation']['max_points']} (development-exposed)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
