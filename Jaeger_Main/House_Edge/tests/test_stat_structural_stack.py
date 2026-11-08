"""Issue #58: structural XOR/XNOR stacker features. Run from Jaeger_Main/House_Edge:
    python -m pytest tests/test_stat_structural_stack.py -q
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

from research.challengers import stat_structural_stack as SS  # noqa: E402

P = json.loads((HE / "jaegers_entry/params.json").read_text())


def fixture(episodes=4, machines=4, cutoff=150, seed=0, rule=(1, 3, "xor")):
    """Machines follow a fixed XOR/XNOR rule at a lag pair with p_on 0.92 / p_off 0.08."""
    rng = random.Random(seed)
    queries, history, labels = [], defaultdict(dict), {}
    for e in range(episodes):
        c = cutoff + 5 * e
        for m in range(machines):
            q = dict(query_id=f"e{e}m{m}", episode_id=f"e{e}", machine_id=f"m{m}",
                     machine_type=("steady", "balanced", "jackpot")[m % 3], signal=str(m % 3 - 1), cutoff=str(c))
            queries.append(q)
            w = {}
            for t in range(c + 1):
                a, b, kind = rule
                if t >= b:
                    same = w[t - a] == w[t - b]
                    on = same if kind == "xnor" else not same
                    win = rng.random() < (0.92 if on else 0.08)
                else:
                    win = rng.random() < 0.4
                w[t] = int(win)
                y = rng.choice((1, 1, 2, 5, 20)) if win else 0
                if t < c:
                    history[(q["episode_id"], q["machine_id"])][t] = y
                else:
                    labels[q["query_id"]] = SS.PAYOUTS.index(y)
    return queries, history, labels


def test_core_parity_with_champion_on_real_subset():
    q, h = SS.C.read_split(str(HE / "public/train"))
    sub = q[:64]
    a, b = SS.C.predict(sub, h, P), SS.core_predict(sub, h, P)
    assert max(float(np.abs(np.subtract(a[k], b[k])).max()) for k in a) == 0.0
    _, Xa, ya = SS.C.predict(sub, h, P, collect=True)
    _, Xb, yb = SS.core_predict(sub, h, P, collect=True)
    assert np.array_equal(Xa, Xb) and np.array_equal(ya, yb)


def test_model_without_extra_equals_champion():
    from research.adapters import JaegerModel
    q, h, l = fixture(episodes=3)
    a = JaegerModel(P).fit(q, h, l).predict_proba(q, h)
    b = SS.StructuralStack(use_extra=False).fit(q, h, l).predict_proba(q, h)
    assert max(float(np.abs(np.subtract(a[k], b[k])).max()) for k in a) == 0.0


def test_rule_features_are_as_of():
    q, h, l = fixture()
    m = SS.SWM().fit(q, h, l)
    base = SS.swm_features(q, h, m)
    t0 = 100
    h2 = deepcopy(h)
    for r in h2.values():
        for t in list(r):
            if t >= t0:
                r[t] = 20 if r[t] == 0 else 0
    after = SS.swm_features(q, h2, m)
    np.testing.assert_array_equal(base[:, :t0 + 1], after[:, :t0 + 1])   # features at tick t use ticks < t only
    assert not np.array_equal(base[:, t0 + 2:], after[:, t0 + 2:])


def test_rule_model_identifies_the_true_rule():
    q, h, l = fixture(rule=(2, 5, "xnor"), seed=3)
    m = SS.SWM().fit(q, h, l)
    true_k = SS.HYPS.index((2, 5, "xnor"))
    for x in q:
        _, _, post = SS.run_machine(*SS._series(h, x), m.p_on, m.p_off, m.lam, prior=m.prior)
        assert post.argmax() == true_k and post[true_k] > 0.9
    assert m.p_on > 0.8 and m.p_off < 0.2


def test_missing_lags_abstain_to_null_rate():
    w = {0: 1, 10: 0, 20: 1}                  # no lag pair ever observed
    LL, pw, post = SS.run_machine(w, 30, 0.9, 0.1, 1.0)
    assert np.allclose(LL[:SS.NULL], LL[SS.NULL])   # every rule abstained -> same likelihood as null
    assert 0 < pw < 1


def test_model_contract_future_ticks_and_episode_isolation():
    q, h, l = fixture(episodes=3)
    m = SS.StructuralStack().fit(q, h, l)
    base = m.predict_proba(q, h)
    h2 = deepcopy(h)
    for x in q:
        c = int(x["cutoff"])
        for t in range(c, c + 6):
            h2[(x["episode_id"], x["machine_id"])][t] = 20
    assert max(float(np.abs(np.subtract(base[k], m.predict_proba(q, h2)[k])).max()) for k in base) == 0.0
    h3 = deepcopy(h)
    for (ep, _), r in h3.items():
        if ep == "e2":
            for t in r:
                r[t] = 0
    after = m.predict_proba(q, h3)
    e0 = [x["query_id"] for x in q if x["episode_id"] == "e0"]
    assert max(float(np.abs(np.subtract(base[k], after[k])).max()) for k in e0) == 0.0


def test_factory_imports_inside_registry_snapshot_layout(tmp_path):
    snap = tmp_path / "s"
    (snap / "research").mkdir(parents=True)
    for f in (HE / "research").glob("*.py"):
        shutil.copyfile(f, snap / "research" / f.name)
    for d in ("jaegers_entry", "slot_forecasting", "research/models", "research/features",
              "research/challengers", "research/extensions"):
        shutil.copytree(HE / d, snap / d, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    code = ("import json,sys; from research import worker; "
            "print(type(worker.model_for(json.loads(sys.argv[1]),None)).__name__)")
    cfg = {"family": "stat_structural_stack", "factory": "research.challengers.stat_structural_stack:factory",
           "supervision": "query"}
    out = subprocess.run([sys.executable, "-B", "-c", code, json.dumps(cfg)], cwd=snap, capture_output=True, text=True)
    assert out.returncode == 0, out.stderr[-1500:]
    assert out.stdout.strip() == "StructuralStack"
