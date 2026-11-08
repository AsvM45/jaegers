"""HE-03 follow-up: causal stacker challenger tests.

Run from Jaeger_Main/House_Edge:  python -m pytest tests/test_agent_qa_causal_stacker.py -q
"""
import json
import random
import shutil
import subprocess
import sys
from collections import defaultdict
from copy import deepcopy
from pathlib import Path

import numpy as np
import pytest

HE = Path(__file__).resolve().parents[1]
if str(HE) not in sys.path:
    sys.path.insert(0, str(HE))

from research.challengers import qa_causal_stacker as Q  # noqa: E402

P = json.loads((HE / "jaegers_entry/params.json").read_text())


def fixture(cutoff=160, episodes=4, machines=4, seed=0):
    rng = random.Random(seed)
    queries, history, labels = [], defaultdict(dict), {}
    for e in range(episodes):
        c = cutoff + 6 * e
        for m in range(machines):
            q = dict(query_id=f"e{e}m{m}", episode_id=f"e{e}", machine_id=f"m{m}",
                     machine_type=("steady", "balanced", "jackpot")[m % 3], signal=str(m % 3 - 1), cutoff=str(c))
            queries.append(q)
            prev = [0] * 8
            for t in range(c + 1):
                win = rng.random() < (0.7 if (prev[1] > 0) != (prev[4] > 0) else 0.25)
                y = rng.choice((1, 1, 2, 5, 20)) if win else 0
                prev = [y] + prev[:-1]
                if t < c:
                    history[(q["episode_id"], q["machine_id"])][t] = y
                else:
                    labels[q["query_id"]] = Q.PAYOUTS.index(y)
    return queries, history, labels


def test_core_parity_with_champion_on_real_subset():
    q, h = Q.C.read_split(str(HE / "public/train"))
    sub = q[:64]
    a, b = Q.C.predict(sub, h, P), Q.core_predict(sub, h, P)
    assert max(float(np.abs(np.subtract(a[k], b[k])).max()) for k in a) == 0.0
    _, Xa, ya = Q.C.predict(sub, h, P, collect=True)
    _, Xb, yb = Q.core_predict(sub, h, P, collect=True)
    assert np.array_equal(Xa, Xb) and np.array_equal(ya, yb)


def _rows_before(q, h, t_max, **kw):
    """Historical stacker rows produced at ticks < t_max (seen >= 20), via a cutoff-limited copy."""
    _, X, _ = Q.core_predict(q, h, P, collect=True, **kw)
    return X


def test_running_regime_removes_final_coverage_leak():
    """Deleting late ticks must not change earlier historical rows (the audit's coverage fixture)."""
    q, h, _ = fixture(cutoff=160, episodes=2)
    cut = deepcopy(h)
    for rows in cut.values():
        for t in range(60, 166):
            rows.pop(t, None)
    # champion: total coverage drops below 100 -> lam_short/prior_short -> early rows change
    _, Xa, _ = Q.core_predict(q, h, P, collect=True)
    _, Xb, _ = Q.core_predict(q, cut, P, collect=True)
    n_early = len(Xb)  # every row of the truncated run lies before tick 60
    assert not np.allclose(Xa[:n_early], Xb)
    # causal: identical early rows
    _, Xc, _ = Q.core_predict(q, h, P, collect=True, running_regime=True)
    _, Xd, _ = Q.core_predict(q, cut, P, collect=True, running_regime=True)
    np.testing.assert_array_equal(Xc[:n_early], Xd)


def test_running_regime_matches_champion_rule_at_cutoff_for_short_histories():
    q, h, _ = fixture(cutoff=80, episodes=2)  # every machine has < 100 spins: regime identical all along
    a, b = Q.core_predict(q, h, P), Q.core_predict(q, h, P, running_regime=True)
    assert max(float(np.abs(np.subtract(a[k], b[k])).max()) for k in a) == 0.0


def test_crossfit_prior_rows_ignore_own_group_history():
    q, h, l = fixture(episodes=4)
    g = Q.episode_groups(q)
    _, LL = Q.core_predict(q, h, P, return_ll=True)
    rows_a = {k: Q.logprior_from_ll(LL[g != k]) for k in np.unique(g)}
    h2 = deepcopy(h)
    for (ep, _m), r in h2.items():
        if ep == "e0":
            for t in r:
                r[t] = 20 if r[t] == 0 else 0
    _, LL2 = Q.core_predict(q, h2, P, return_ll=True)
    k0 = g[[i for i, x in enumerate(q) if x["episode_id"] == "e0"][0]]
    np.testing.assert_array_equal(rows_a[k0], Q.logprior_from_ll(LL2[g != k0]))


def test_signal_dropped_from_stacker_and_used_only_in_query_head():
    q, h, l = fixture(episodes=3)
    m = Q.factory({"variant": "causal_all"}).fit(q, h, l)
    assert Q.SIGNAL_COL not in m.cols and m.head is not None
    flipped = [dict(x, signal="1" if x["signal"] != "1" else "-1") for x in q]
    m2 = Q.factory({"variant": "causal_all_nohead"}).fit(q, h, l)
    a, b = m2.predict_proba(q, h), m2.predict_proba(flipped, h)
    assert max(float(np.abs(np.subtract(a[k], b[k])).max()) for k in a) == 0.0  # no signal anywhere
    c, d = m.predict_proba(q, h), m.predict_proba(flipped, h)
    assert max(float(np.abs(np.subtract(c[k], d[k])).max()) for k in c) > 0.0    # head uses query signal


@pytest.mark.parametrize("variant", sorted(Q.VARIANTS))
def test_variants_contract_and_future_ticks(variant):
    q, h, l = fixture(episodes=3)
    m = Q.factory({"variant": variant}).fit(q, h, l)
    base = m.predict_proba(q, h)
    h2 = deepcopy(h)
    for x in q:
        c = int(x["cutoff"])
        for t in range(c, c + 6):
            h2[(x["episode_id"], x["machine_id"])][t] = 20
    assert max(float(np.abs(np.subtract(base[k], m.predict_proba(q, h2)[k])).max()) for k in base) == 0.0


def test_unknown_variant_rejected():
    with pytest.raises(ValueError):
        Q.factory({"variant": "nope"})


def test_factory_imports_inside_registry_snapshot_layout(tmp_path):
    snap = tmp_path / "source"
    (snap / "research").mkdir(parents=True)
    for f in (HE / "research").glob("*.py"):
        shutil.copyfile(f, snap / "research" / f.name)
    for d in ("jaegers_entry", "slot_forecasting", "research/models", "research/features",
              "research/challengers", "research/extensions"):
        shutil.copytree(HE / d, snap / d, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    code = ("import json,sys; from research import worker; "
            "print(type(worker.model_for(json.loads(sys.argv[1]),None)).__name__)")
    cfg = {"family": "qa_causal_all", "factory": "research.challengers.qa_causal_stacker:factory",
           "variant": "causal_all", "supervision": "query"}
    out = subprocess.run([sys.executable, "-B", "-c", code, json.dumps(cfg)], cwd=snap, capture_output=True, text=True)
    assert out.returncode == 0, out.stderr[-1500:]
    assert out.stdout.strip() == "CausalStacker"
