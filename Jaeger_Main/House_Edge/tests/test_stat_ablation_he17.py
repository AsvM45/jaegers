"""HE-17 harness tests: config validity, isolation of module patches, trial IDs, bootstrap sanity.

Run from Jaeger_Main/House_Edge:  python -m pytest tests/test_stat_ablation_he17.py -q
"""
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pytest

HE = Path(__file__).resolve().parents[1]
if str(HE) not in sys.path:
    sys.path.insert(0, str(HE))

from research.analysis import stat_ablation_he17 as H  # noqa: E402

CONFIG = json.loads(H.CONFIG.read_text())
KNOWN_KEYS = {"params", "drop_stack_cols", "experts", "size_regimes", "shuffle_stack_labels"}


def test_config_is_well_formed():
    names = [v["name"] for v in CONFIG["variants"]]
    assert len(names) == len(set(names)) and CONFIG["baseline"] in names
    assert len(names) - 1 >= 8, "issue asks for eight or more controlled ablations"
    for v in CONFIG["variants"]:
        assert set(v["change"]) <= KNOWN_KEYS, v["name"]
        assert v.get("hypothesis"), v["name"]
    assert any("NEGATIVE CONTROL" in v["hypothesis"] for v in CONFIG["variants"])


def test_param_references_resolve():
    base = json.loads(H.PARAMS.read_text())
    p = H.resolve_params(base, {"params": {"lam_short": "=lam", "prior_short": "=prior", "gamma": 0.0}})
    assert p["lam_short"] == base["lam"] and p["prior_short"] == base["prior"] and p["gamma"] == 0.0
    assert base["lam_short"] != base["lam"], "fixture assumption: champion uses a distinct short-history lam"


def test_expert_filters_and_isolation():
    before = hashlib.sha256(H.CHAMPION.read_bytes()).hexdigest()
    single = H.apply_module_changes(H.fresh_core("t1"), {"experts": "single_lag_only"})
    binary = H.apply_module_changes(H.fresh_core("t2"), {"experts": "binary_only"})
    untouched = H.fresh_core("t3")
    assert len(untouched.EXPERTS) == 73
    assert len(single.EXPERTS) == 1 + 2 * 8 and all(e[1] == 0 for e in single.EXPERTS)
    assert len(binary.EXPERTS) == 1 + 8 + 28 and all(e[2] in (1, 2) for e in binary.EXPERTS)
    regimes = H.apply_module_changes(H.fresh_core("t4"), {"size_regimes": {"steady": [[1, 1, 1, 1], [2, 1, 1, 0]]}})
    np.testing.assert_allclose(regimes.SIZE_REGIMES["steady"].sum(axis=1), 1.0)
    assert not np.allclose(untouched.SIZE_REGIMES["steady"], regimes.SIZE_REGIMES["steady"])
    assert hashlib.sha256(H.CHAMPION.read_bytes()).hexdigest() == before


def test_unknown_expert_filter_rejected():
    with pytest.raises(ValueError):
        H.apply_module_changes(H.fresh_core("t5"), {"experts": "nope"})


def test_trial_ids_deterministic_and_distinct():
    ids = [H.trial_id(v) for v in CONFIG["variants"]]
    assert ids == [H.trial_id(v) for v in CONFIG["variants"]]
    assert len(set(ids)) == len(ids)


def test_bootstrap_identity_and_sign():
    keys = [f"{c}|e{i}" for c in ("drift", "stable") for i in range(6)]
    rng = np.random.default_rng(0)
    base = {k: float(rng.uniform(0.1, 0.2)) for k in keys}
    ref = {k: 0.3 for k in keys}
    same = H.bootstrap_A(base, dict(base), ref, reps=200)
    assert same["diff"] == 0 and same["ci95"] == [0.0, 0.0]
    better = H.bootstrap_A(base, {k: v * 0.5 for k, v in base.items()}, ref, reps=200)
    assert better["diff"] > 0 and better["ci95"][0] > 0
    worse_b = H.bootstrap_B(base, {k: v + 0.01 for k, v in base.items()}, reps=200)
    assert worse_b["diff"] == pytest.approx(0.01) and worse_b["ci95"][0] > 0
