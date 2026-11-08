"""Preregistration uses real released train bytes, without dispatching test trials."""
from copy import deepcopy
import json
from pathlib import Path
import sys

import pytest

REPO = Path(__file__).resolve().parents[3]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from Jaeger_Main.House_Edge.research.analysis import chat_he88_study as study
from Jaeger_Main.House_Edge.research.common import ROOT, digest


def test_fixed_platform_study_is_finite_and_has_no_validation_selection():
    spec = study.study_spec()
    assert len(spec["candidates"]) == spec["budget"]["trials"] == 6
    assert spec["budget"]["workers"] == 1
    assert spec["budget"]["seconds"] == 900
    assert spec["budget"]["trial_seconds"] == 240
    assert spec["candidates"][0] == {"family": "jaeger", "causal": False, "seed": 0}
    assert all("current_signal" not in c.get("groups", []) for c in spec["candidates"])


def test_prepare_is_idempotent_and_bound_to_actual_episode_manifest(tmp_path, monkeypatch):
    def no_dispatch(*args, **kwargs):
        raise AssertionError("prepare must not dispatch trials")
    monkeypatch.setattr(study, "sweep", no_dispatch)
    prereg = study.prepare(ROOT/"public", tmp_path)
    assert prereg == study.prepare(ROOT/"public", tmp_path)
    assert len(prereg["folds"]) == 96
    assert set(prereg["folds"].values()) == {0, 1, 2, 3}
    assert prereg["identity"]["split_manifest_sha256"] == digest(prereg["folds"])
    assert prereg["identity"]["train_sha256"]["queries.csv"]
    assert prereg["official_points"] is None
    assert sorted(p.name for p in tmp_path.iterdir()) == ["he88_preregistration.json"]
    path = tmp_path/"he88_preregistration.json"
    stored = json.loads(path.read_text())
    stored["spec"]["budget"]["trials"] = 999
    path.write_text(json.dumps(stored))
    with pytest.raises(ValueError, match="conflicts"):
        study.prepare(ROOT/"public", tmp_path)
