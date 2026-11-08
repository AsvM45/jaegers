"""HE-06 adaptation orchestrator: kit verification and packaging helpers (fast; no full forecasts).

Run from Jaeger_Main/House_Edge:  python -m pytest tests/test_adaptation_release.py -q
The full pipeline is exercised by `python adaptation/run_adaptation.py --kit public --expect-round main ...`.
"""
import csv
import json
import shutil
import sys
from pathlib import Path

import pytest

HE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HE / "adaptation"))
import run_adaptation as RA  # noqa: E402

PUB = HE / "public"


def small_kit(tmp_path, round_name="adaptation", points=40, season="a" * 24, prefix="adapt"):
    """Copy two episodes per split from the main kit, re-ID them, and set metadata."""
    kit = tmp_path / "kit"
    for split in ("train", "validation", "test"):
        (kit / split).mkdir(parents=True)
        q = RA.rows(PUB / split / "queries.csv")
        keep = sorted({r["episode_id"] for r in q})[:2]
        for name in sorted(p.name for p in (PUB / split).iterdir()):
            src = RA.rows(PUB / split / name)
            out = [r for r in src if r.get("episode_id", None) in keep or
                   ("episode_id" not in r and r["query_id"].rsplit("-m", 1)[0] in keep)]
            for r in out:
                for k in ("query_id", "episode_id"):
                    if k in r:
                        r[k] = r[k].replace("main-", prefix + "-")
            with open(kit / split / name, "w", newline="", encoding="utf-8") as f:
                w = csv.DictWriter(f, fieldnames=src[0].keys()); w.writeheader(); w.writerows(out)
    meta = json.loads((PUB / "metadata.json").read_text())
    meta.update(round=round_name, max_points=points, season_id=season)
    (kit / "metadata.json").write_text(json.dumps(meta))
    return kit


def test_main_kit_passes_as_main_round():
    rep = RA.verify_kit(PUB, PUB, "main")
    assert rep["ok"], rep["problems"]
    assert rep["test_queries"] == 1536


def test_main_kit_is_rejected_as_adaptation():
    rep = RA.verify_kit(PUB, PUB, "adaptation")
    assert not rep["ok"]
    text = " ".join(rep["problems"])
    assert "round" in text and "max_points" in text and "overlap" in text


def test_valid_adaptation_kit_passes(tmp_path):
    kit = small_kit(tmp_path)
    rep = RA.verify_kit(kit, PUB, "adaptation")
    assert rep["ok"], rep["problems"]
    assert rep["overlap_with_main"] == 0


def test_future_tick_bad_payout_and_test_truth_are_flagged(tmp_path):
    kit = small_kit(tmp_path)
    h = RA.rows(kit / "train" / "history.csv"); q = RA.rows(kit / "train" / "queries.csv")
    first = q[0]
    h.append({"episode_id": first["episode_id"], "machine_id": first["machine_id"], "tick": first["cutoff"], "payout": "7"})
    with open(kit / "train" / "history.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=h[0].keys()); w.writeheader(); w.writerows(h)
    shutil.copyfile(kit / "validation" / "targets.csv", kit / "test" / "targets.csv")
    text = " ".join(RA.verify_kit(kit, PUB, "adaptation")["problems"])
    assert "at/after cutoff" in text and "unknown payout" in text and "test truth" in text


def test_missing_file_blocks(tmp_path):
    kit = small_kit(tmp_path)
    (kit / "validation" / "reference.csv").unlink()
    rep = RA.verify_kit(kit, PUB, "adaptation")
    assert not rep["ok"] and "validation/reference.csv" in rep["missing"]


def test_reproduce_command_pins_env_and_cold_parser_reads_it(tmp_path):
    assert RA.reproduce_command({}) == ["python", "predict.py", "--data", "/data", "--out", "/output/submission.csv"]
    cmd = RA.reproduce_command({"NPY_DISABLE_CPU_FEATURES": "AVX512F"})
    assert cmd[:2] == ["env", "NPY_DISABLE_CPU_FEATURES=AVX512F"] and cmd[2:4] == ["python", "predict.py"]


def test_staged_source_and_zip_are_valid(tmp_path):
    meta = {"round": "adaptation", "max_points": 40, "season_id": "a" * 24}
    src = tmp_path / "source"
    RA.stage_source(HE / "jaegers_entry", src, meta, {"NPY_DISABLE_CPU_FEATURES": "X"})
    assert (src / "README.md").read_text().startswith("# JAEGERS House Edge - adaptation round")
    assert json.loads((src / "reproduce.json").read_text())["command"][0] == "env"
    assert (src / "requirements.txt").read_text() == (HE / "requirements-runtime.txt").read_text()
    assert (src / "jaeger_model.py").read_bytes() == (HE / "jaegers_entry" / "jaeger_model.py").read_bytes()
    zp = RA.package(src, tmp_path / "code.zip")
    import zipfile
    names = zipfile.ZipFile(zp).namelist()
    assert {"README.md", "reproduce.json", "predict.py", "jaeger_model.py", "params.json", "requirements.txt"} <= set(names)


def test_max_normalized_diff(tmp_path):
    a, b = tmp_path / "a.csv", tmp_path / "b.csv"
    for p, v in ((a, "0.2"), (b, "0.2")):
        p.write_text("query_id,p_0,p_1,p_2,p_5,p_20\nq1," + ",".join([v] * 5) + "\n")
    assert RA.max_normalized_diff(a, b) == 0.0
    b.write_text("query_id,p_0,p_1,p_2,p_5,p_20\nq1,0.3,0.2,0.2,0.2,0.1\n")
    assert RA.max_normalized_diff(a, b) == pytest.approx(0.1)
    b.write_text("query_id,p_0,p_1,p_2,p_5,p_20\nq2,0.2,0.2,0.2,0.2,0.2\n")
    with pytest.raises(ValueError):
        RA.max_normalized_diff(a, b)
