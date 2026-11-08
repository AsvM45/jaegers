"""HE-15 follow-up blend tests.  Run from Jaeger_Main/House_Edge:
    python -m pytest tests/test_stat_temporal_blend.py -q
"""
import json
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest

HE = Path(__file__).resolve().parents[1]
if str(HE) not in sys.path:
    sys.path.insert(0, str(HE))

from research.challengers import stat_temporal_blend as B  # noqa: E402


def test_swap_size_keeps_champion_loss_probability_and_simplex():
    champ = np.array([[0.6, 0.2, 0.1, 0.07, 0.03], [0.1, 0.3, 0.3, 0.2, 0.1]])
    size = np.array([[0.25, 0.25, 0.25, 0.25], [2.0, 1.0, 1.0, 0.0]])  # unnormalised on purpose
    p = B.swap_size(champ, size)
    np.testing.assert_allclose(p[:, 0], champ[:, 0])
    np.testing.assert_allclose(p.sum(1), 1.0)
    np.testing.assert_allclose(p[1, 1:] / p[1, 1:].sum(), [0.5, 0.25, 0.25, 0.0])


def test_blend_endpoints():
    a = {"q": np.array([0.5, 0.2, 0.1, 0.1, 0.1])}; b = {"q": np.array([0.2, 0.2, 0.2, 0.2, 0.2])}
    np.testing.assert_allclose(B.blend(a, b, 1.0)["q"], a["q"])
    np.testing.assert_allclose(B.blend(a, b, 0.0)["q"], b["q"])
    np.testing.assert_allclose(B.blend(a, b, 0.5)["q"].sum(), 1.0)


def test_best_weight_finds_the_better_model():
    labels = {f"q{i}": 0 for i in range(20)}
    good = {k: np.array([0.9, 0.025, 0.025, 0.025, 0.025]) for k in labels}
    bad = {k: np.array([0.2, 0.2, 0.2, 0.2, 0.2]) for k in labels}
    assert B.best_weight(good, bad, list(labels), labels)[0] == 1.0
    assert B.best_weight(bad, good, list(labels), labels)[0] == 0.0


def test_nested_oof_never_uses_the_held_out_fold():
    """Fold 0 rewards model b, folds 1-3 reward model a: fold 0's weight must still be 1.0 (a)."""
    labels, folds, a, b = {}, {}, {}, {}
    for f in range(4):
        for i in range(10):
            k = f"f{f}q{i}"
            folds[k] = f
            labels[k] = 0 if f else 4
            a[k] = np.array([0.9, 0.025, 0.025, 0.025, 0.025])
            b[k] = np.array([0.025, 0.025, 0.025, 0.025, 0.9])
    _, weights = B.nested_oof(a, b, folds, labels)
    assert weights[0] == 1.0
    assert all(0.0 <= w <= 1.0 for w in weights.values())


def test_factory_only_builds_size_swap():
    assert isinstance(B.factory({"model": "size_swap"}), B.SizeSwapModel)
    with pytest.raises(ValueError):
        B.factory({"model": "blend_linear"})


def test_blend_factory_imports_inside_registry_snapshot_layout(tmp_path):
    snap = tmp_path / "source"
    (snap / "research").mkdir(parents=True)
    for f in (HE / "research").glob("*.py"):
        shutil.copyfile(f, snap / "research" / f.name)
    for d in ("jaegers_entry", "slot_forecasting", "research/models", "research/features",
              "research/challengers", "research/extensions"):
        shutil.copytree(HE / d, snap / d, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    code = ("import json,sys; from research import worker; "
            "print(type(worker.model_for(json.loads(sys.argv[1]),None)).__name__)")
    cfg = {"family": "stat_temporal_size_swap", "factory": "research.challengers.stat_temporal_blend:factory",
           "model": "size_swap", "supervision": "query"}
    out = subprocess.run([sys.executable, "-B", "-c", code, json.dumps(cfg)], cwd=snap, capture_output=True, text=True)
    assert out.returncode == 0, out.stderr[-1500:]
    assert out.stdout.strip() == "SizeSwapModel"
