"""HE-09 unit tests for the statistical challengers (fixed seeds, synthetic fixtures).

Run from Jaeger_Main/House_Edge:  python -m pytest tests/test_stat_he09_models.py -q
"""
import random
import sys
from collections import defaultdict
from copy import deepcopy
from pathlib import Path

import numpy as np
import pytest

HE = Path(__file__).resolve().parents[1]
if str(HE) not in sys.path:
    sys.path.insert(0, str(HE))

from research.challengers import stat_he09_models as SM  # noqa: E402

PAYOUTS = SM.PAYOUTS


def fixture(episodes=3, machines=4, cutoff=80, seed=0, pattern=None):
    """Synthetic episodes; cutoffs differ by episode so the future-tick test is not masked."""
    rng = random.Random(seed)
    queries, history, labels = [], defaultdict(dict), {}
    for e in range(episodes):
        c = cutoff + 8 * e
        for m in range(machines):
            q = dict(query_id=f"e{e}m{m}", episode_id=f"e{e}", machine_id=f"m{m}",
                     machine_type=SM.TYPES[m % 3], signal=str(m % 3 - 1), cutoff=str(c))
            queries.append(q)
            for t in range(c + 1):
                if pattern == "alternate":
                    y = 0 if t % 2 == 0 else 2
                elif pattern == "switch":
                    y = 0 if t < c - 15 else 20
                else:
                    y = rng.choice((0, 0, 0, 1, 1, 2, 5, 20))
                if t < c:
                    if rng.random() < 0.15 and t < c - 3:
                        continue
                    history[(q["episode_id"], q["machine_id"])][t] = y
                else:
                    labels[q["query_id"]] = PAYOUTS.index(y)
    return queries, history, labels


@pytest.fixture(params=sorted(SM.MODELS))
def name(request):
    return request.param


def fitted(name, q, h, l):
    return SM.MODELS[name]().fit(q, h, l)


def test_contract_simplex_and_ids(name):
    q, h, l = fixture()
    pred = fitted(name, q, h, l).predict(q, h)
    assert set(pred) == {x["query_id"] for x in q}
    for v in pred.values():
        p = np.asarray(v)
        assert p.shape == (5,) and np.isfinite(p).all() and (p > 0).all() and abs(p.sum() - 1) < 1e-9


def test_future_ticks_ignored(name):
    q, h, l = fixture()
    model = fitted(name, q, h, l)
    base = model.predict(q, h)
    h2 = deepcopy(h)
    for x in q:
        c = int(x["cutoff"])
        for t in range(c, c + 10):
            h2[(x["episode_id"], x["machine_id"])][t] = 20
    after = model.predict(q, h2)
    assert max(np.abs(np.subtract(base[k], after[k])).max() for k in base) == 0.0


def test_other_episode_isolated(name):
    q, h, l = fixture()
    model = fitted(name, q, h, l)
    base = model.predict(q, h)
    h2 = deepcopy(h)
    for (ep, m), r in h2.items():
        if ep == "e2":
            for t in r:
                r[t] = 20
    after = model.predict(q, h2)
    e0 = [x["query_id"] for x in q if x["episode_id"] == "e0"]
    assert max(np.abs(np.subtract(base[k], after[k])).max() for k in e0) == 0.0


def test_missing_tick_is_not_zero(name):
    q, h, l = fixture(seed=4)
    model = fitted(name, q, h, l)
    x = q[0]; key = (x["episode_id"], x["machine_id"]); c = int(x["cutoff"])
    h_missing = deepcopy(h); h_missing[key].pop(c - 1, None)
    h_zero = deepcopy(h); h_zero[key][c - 1] = 0
    a = model.predict(q, h_missing)[x["query_id"]]
    b = model.predict(q, h_zero)[x["query_id"]]
    assert np.abs(np.subtract(a, b)).max() > 0


def test_signal_is_query_prior_only(name):
    q, h, l = fixture()
    model = fitted(name, q, h, l)
    flipped = [dict(x, signal="1" if x["signal"] != "1" else "-1") for x in q]
    a = model.predict(q, h); b = model.predict(flipped, h)
    if name == "stat_markov":  # no signal input at all
        assert max(np.abs(np.subtract(a[k], b[k])).max() for k in a) == 0.0
    else:
        assert max(np.abs(np.subtract(a[k], b[k])).max() for k in a) > 0.0


def test_dirichlet_posterior_matches_hand_calculation():
    q, h, l = fixture()
    model = SM.DirichletModel().fit(q, h, l)
    model.decay, model.s_short, model.s_long = 1.0, 5.0, 5.0
    x = q[0]
    _, ys = SM.past(h, x)
    expect = (5.0 * model.prior(x) + np.bincount(ys, minlength=5)) / (5.0 + len(ys))
    np.testing.assert_allclose(model.predict([x], h)[x["query_id"]], expect / expect.sum(), atol=1e-12)


def test_markov_learns_lag_structure():
    q, h, l = fixture(pattern="alternate", seed=1)
    model = SM.MarkovMixture().fit(q, h, l)
    pred = model.predict(q, h)
    for x in q:
        truth = l[x["query_id"]]
        assert pred[x["query_id"]][truth] > 0.6, (x["query_id"], pred[x["query_id"]])


def test_decay_bma_adapts_to_switch_faster_than_no_decay():
    q, h, l = fixture(pattern="switch", seed=2)
    bma = SM.DecayBMA().fit(q, h, l)
    slow = SM.DirichletModel().fit(q, h, l); slow.decay, slow.s_short, slow.s_long = 1.0, bma.s, bma.s
    pb, ps = bma.predict(q, h), slow.predict(q, h)
    assert np.mean([pb[x["query_id"]][4] for x in q]) > np.mean([ps[x["query_id"]][4] for x in q]) + 0.2


def test_fit_is_deterministic(name):
    q, h, l = fixture()
    a = fitted(name, q, h, l).predict(q, h)
    b = fitted(name, q, h, l).predict(q, h)
    assert a == b


def test_type_signal_prior_uses_only_fit_labels():
    q, h, l = fixture()
    p1 = SM.TypeSignalPrior().fit(q, h, l)
    l2 = {k: 4 for k in l}  # every label 20x
    p2 = SM.TypeSignalPrior().fit(q, h, l2)
    x = q[0]
    assert p2(x)[4] > p1(x)[4]
    np.testing.assert_allclose(p1.type_mean[x["machine_type"]], p2.type_mean[x["machine_type"]])
