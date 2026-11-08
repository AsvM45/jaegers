"""Tiny synthetic fixtures: training lineage, never competition measurements."""
import importlib.util
import json
from pathlib import Path

import pytest

path = Path(__file__).resolve().parents[1]/"adaptation/combined_rounds.py"
spec = importlib.util.spec_from_file_location("combined_rounds", path)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def kit(root, round_name):
    root.mkdir()
    (root/"metadata.json").write_text(json.dumps({"round": round_name, "max_points": 20 if round_name == "adaptation" else 60, "season_id": "same"}))
    for split in ("train", "validation", "test"):
        folder = root/split
        folder.mkdir()
        ep = round_name+"-"+split
        (folder/"queries.csv").write_text("query_id,episode_id,machine_id,machine_type,signal,cutoff\n"+f"{ep}-q,{ep},m0,steady,1,10\n")
        (folder/"history.csv").write_text("episode_id,machine_id,tick,payout\n"+f"{ep},m0,9,2\n")
    return root


def test_pool_contains_only_allowed_released_histories(tmp_path, monkeypatch):
    adapt, main = kit(tmp_path/"adapt", "adaptation"), kit(tmp_path/"main", "main")
    reads = []
    original = module.read_rows
    def observe(path):
        reads.append(Path(path))
        return original(path)
    monkeypatch.setattr(module, "read_rows", observe)
    queries, history, manifest = module.pool_training(adapt, main, ["train", "test"])
    assert len(queries) == len(history) == 3
    assert [m["source"] for m in manifest] == ["adaptation/train", "main/train", "main/test"]
    assert not any(p.name in {"labels.csv", "targets.csv", "conditions.csv"} for p in reads)
    assert adapt/"test/history.csv" not in reads and adapt/"validation/history.csv" not in reads
    assert not any(q["episode_id"] in {"adaptation-test", "adaptation-validation"} for q in queries)
    assert len(module.pool_training(adapt)[0]) == 1


@pytest.mark.parametrize("splits", [["validation"], ["train", "train"], ["test", "validation"]])
def test_invalid_training_splits_are_rejected(tmp_path, splits):
    with pytest.raises(ValueError, match="splits"):
        module.pool_training(kit(tmp_path/"adapt", "adaptation"), kit(tmp_path/"main", "main"), splits)


def test_main_round_and_season_must_match(tmp_path):
    adapt, main = kit(tmp_path/"adapt", "adaptation"), kit(tmp_path/"main", "main")
    (main/"metadata.json").write_text(json.dumps({"round": "main", "season_id": "different"}))
    with pytest.raises(ValueError, match="season"):
        module.pool_training(adapt, main, ["train"])
    with pytest.raises(ValueError, match="required"):
        module.pool_training(adapt, None, ["train"])


@pytest.mark.parametrize("row", ["adaptation-train,m0,10,2\n", "adaptation-train,m0,9,7\n", "other,m0,9,2\n", "adaptation-train,m0,-1,2\n"])
def test_invalid_or_future_training_history_is_rejected(tmp_path, row):
    adapt = kit(tmp_path/"adapt", "adaptation")
    (adapt/"train/history.csv").write_text("episode_id,machine_id,tick,payout\n"+row)
    with pytest.raises(ValueError, match="history"):
        module.pool_training(adapt)


def test_duplicate_ticks_and_heldout_episodes_are_rejected(tmp_path):
    adapt = kit(tmp_path/"adapt", "adaptation")
    history = adapt/"train/history.csv"
    history.write_text(history.read_text()+"adaptation-train,m0,9,2\n")
    with pytest.raises(ValueError, match="Duplicate history"):
        module.pool_training(adapt)
    (adapt/"train/queries.csv").write_text((adapt/"test/queries.csv").read_text())
    with pytest.raises(ValueError, match="held-out"):
        module.pool_training(adapt)


def test_new_round_point_scale_is_explicit(tmp_path):
    adapt = kit(tmp_path/"adapt", "adaptation")
    (adapt/"metadata.json").write_text(json.dumps({"round": "adaptation", "max_points": 40}))
    with pytest.raises(ValueError, match="max_points=20"):
        module.pool_training(adapt)
