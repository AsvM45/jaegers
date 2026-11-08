"""HE-15 temporal challenger tests (fixed seeds, synthetic fixtures).

Run from Jaeger_Main/House_Edge:  python -m pytest tests/test_stat_temporal_models.py -q
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

from research.challengers import stat_temporal_models as T  # noqa: E402

FAST = {"restarts": 1, "iters": 8}


def fixture(episodes=3, machines=6, cutoff=90, seed=0, kind="random"):
    rng = random.Random(seed)
    queries, history, labels = [], defaultdict(dict), {}
    for e in range(episodes):
        c = cutoff + 7 * e
        for m in range(machines):
            q = dict(query_id=f"e{e}m{m}", episode_id=f"e{e}", machine_id=f"m{m}",
                     machine_type=T.TYPES[m % 3], signal="0", cutoff=str(c))
            queries.append(q)
            state = 0
            for t in range(c + 1):
                if kind == "regimes":   # sticky hidden regime: mostly losses vs mostly 5x/20x wins
                    if rng.random() < 0.03:
                        state = 1 - state
                    y = rng.choice((0, 0, 0, 1)) if state == 0 else rng.choice((5, 20, 5, 0))
                elif kind == "alternate":
                    y = 0 if t % 2 == 0 else 2
                else:
                    y = rng.choice((0, 0, 0, 1, 1, 2, 5, 20))
                if t < c:
                    if rng.random() < 0.15 and t < c - 3:
                        continue
                    history[(q["episode_id"], q["machine_id"])][t] = y
                else:
                    labels[q["query_id"]] = T.PAYOUTS.index(y)
    return queries, history, labels


def model(name):
    return T.factory({"model": name, "params": FAST if name != "stat_temporal_ar1" else {}})


@pytest.fixture(params=sorted(T.MODELS))
def name(request):
    return request.param


def test_contract_simplex_ids_and_determinism(name):
    q, h, l = fixture()
    a = model(name).fit(q, h, l).predict_proba(q, h)
    b = model(name).fit(q, h, l).predict_proba(q, h)
    assert set(a) == {x["query_id"] for x in q}
    assert all(np.allclose(a[k], b[k]) for k in a)


def test_future_ticks_ignored(name):
    q, h, l = fixture()
    m = model(name).fit(q, h, l)
    base = m.predict_proba(q, h)
    h2 = deepcopy(h)
    for x in q:
        c = int(x["cutoff"])
        for t in range(c, c + 9):
            h2[(x["episode_id"], x["machine_id"])][t] = 20
    after = m.predict_proba(q, h2)
    assert max(float(np.abs(np.subtract(base[k], after[k])).max()) for k in base) == 0.0


def test_other_episode_isolated(name):
    q, h, l = fixture()
    m = model(name).fit(q, h, l)
    base = m.predict_proba(q, h)
    h2 = deepcopy(h)
    for (ep, _), r in h2.items():
        if ep == "e2":
            for t in r:
                r[t] = 20
    after = m.predict_proba(q, h2)
    e0 = [x["query_id"] for x in q if x["episode_id"] == "e0"]
    assert max(float(np.abs(np.subtract(base[k], after[k])).max()) for k in e0) == 0.0


def test_missing_tick_is_not_zero(name):
    q, h, l = fixture(seed=3)
    m = model(name).fit(q, h, l)
    x = q[0]; key = (x["episode_id"], x["machine_id"]); c = int(x["cutoff"])
    hm = deepcopy(h); hm[key].pop(c - 1, None)
    hz = deepcopy(h); hz[key][c - 1] = 0
    a, b = m.predict_proba(q, hm)[x["query_id"]], m.predict_proba(q, hz)[x["query_id"]]
    assert float(np.abs(np.subtract(a, b)).max()) > 0


def test_baum_welch_loglik_never_decreases():
    q, h, _ = fixture(kind="regimes", seed=5)
    O, lens = T.sequences(q, h, "payout")
    rng_hist = []
    for iters in range(1, 9):
        rng_hist.append(T.baum_welch(O, lens, 2, 5, iters=iters, seed=0, tol=0)["loglik"])
    assert all(b >= a - 1e-6 for a, b in zip(rng_hist, rng_hist[1:]))


def test_hmm_recovers_two_separated_regimes():
    q, h, _ = fixture(kind="regimes", seed=7, episodes=4)
    O, lens = T.sequences(q, h, "payout")
    fit = T.best_of_restarts(O, lens, 2, 5, restarts=3, iters=30)[0]
    p0 = sorted(fit["B"][:, 0])                    # P(0x) per state
    assert p0[0] < 0.4 and p0[1] > 0.6, fit["B"]   # one loss-heavy state, one win-heavy state
    assert np.all(np.diag(fit["A"]) > 0.8)          # sticky regimes


def test_hmm_filter_tracks_current_regime():
    q, h, l = fixture(kind="regimes", seed=11, episodes=4)
    m = T.TemporalHMM(restarts=2, iters=25).fit(q, h, l)
    x = q[0]; key = (x["episode_id"], x["machine_id"]); c = int(x["cutoff"])
    hl = deepcopy(h); hw = deepcopy(h)
    for t in range(c - 15, c):
        hl[key][t] = 0; hw[key][t] = 20
    assert m.predict_proba(q, hw)[x["query_id"]][4] > m.predict_proba(q, hl)[x["query_id"]][4] + 0.1


def test_factorized_win_matches_lag_mixture():
    q, h, l = fixture(seed=2)
    m = model("stat_temporal_factorized").fit(q, h, l)
    p = m.predict_proba(q, h)
    lag = m.win.predict(q, h)
    assert all(abs(p[k][0] - lag[k][0]) < 1e-9 for k in p)


def test_ar1_learns_negative_autocorrelation():
    q, h, l = fixture(kind="alternate", seed=1)
    m = T.TemporalAR1().fit(q, h, l)
    assert all(m.phi[ty][0] < -0.5 for ty in T.TYPES)


def test_unknown_model_rejected():
    with pytest.raises(ValueError):
        T.factory({"model": "nope"})


def test_factory_imports_inside_registry_snapshot_layout(tmp_path):
    """Registry workers run from a frozen snapshot (no research/analysis, no research/configs)."""
    snap = tmp_path / "source"
    (snap / "research").mkdir(parents=True)
    for f in (HE / "research").glob("*.py"):
        shutil.copyfile(f, snap / "research" / f.name)
    for d in ("jaegers_entry", "slot_forecasting", "research/models", "research/features",
              "research/challengers", "research/extensions"):
        shutil.copytree(HE / d, snap / d, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    code = ("import json,sys; from research import worker; "
            "print(type(worker.model_for(json.loads(sys.argv[1]),None)).__name__)")
    cfg = {"family": "stat_temporal_hmm", "factory": "research.challengers.stat_temporal_models:factory",
           "model": "stat_temporal_hmm", "supervision": "query"}
    out = subprocess.run([sys.executable, "-B", "-c", code, json.dumps(cfg)], cwd=snap, capture_output=True, text=True)
    assert out.returncode == 0, out.stderr[-1500:]
    assert out.stdout.strip() == "TemporalHMM"
