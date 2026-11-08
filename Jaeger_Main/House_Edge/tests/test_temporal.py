from collections import defaultdict
from copy import deepcopy
import numpy as np
import pytest
from research.adapters import core_module, JaegerModel, validate_predictions


def fixture(cutoff=64):
    queries, history = [], defaultdict(dict)
    for e in range(2):
        for m in range(3):
            q = dict(query_id=f"q{e}_{m}", episode_id=f"e{e}", machine_id=f"m{m}",
                     machine_type="steady", signal=str(m-1), cutoff=str(cutoff))
            queries.append(q)
            for t in range(cutoff):
                history[(q["episode_id"], q["machine_id"])][t] = (0, 1, 2, 5, 20)[(t*7+m+e)%5]
    return queries, history


def test_cutoff_future_and_sibling_mutations():
    q, h = fixture()
    core = core_module()
    baseline = core.predict(q, h)
    changed = deepcopy(h)
    for rows in changed.values():
        rows[64] = 20
        rows[65] = 0
    assert core.predict(q, changed) == baseline


def test_order_and_episode_isolation():
    q, h = fixture()
    core = core_module()
    baseline = core.predict(q, h)
    reordered = core.predict(list(reversed(q)), h)
    for key in baseline:
        np.testing.assert_allclose(baseline[key], reordered[key], atol=1e-14)
    changed = deepcopy(h)
    for key, rows in changed.items():
        if key[0] == "e1":
            for tick in rows:
                rows[tick] = 0
    prediction = core.predict(q, changed)
    for row in q[:3]:
        np.testing.assert_array_equal(baseline[row["query_id"]], prediction[row["query_id"]])


def test_historical_signal_finding_and_physical_removal():
    q, h = fixture()
    other = [dict(row, signal="9") for row in q]
    core = core_module()
    _, X, y = core.predict(q, h, collect=True)
    _, X2, y2 = core.predict(other, h, collect=True)
    assert np.any(X[:, 13] != X2[:, 13])  # executed evidence of copied query-time signal
    keep = [i for i in range(1, X.shape[1]) if i != 13]
    np.testing.assert_array_equal(X[:, keep], X2[:, keep])
    np.testing.assert_array_equal(y, y2)


def test_final_history_coverage_leaks_into_old_features():
    q, h = fixture(cutoff=128)
    changed = deepcopy(h)
    for rows in changed.values():
        for t in range(70, 128):
            del rows[t]
    core = core_module()
    _, X, _ = core.predict(q, h, collect=True)
    _, X2, _ = core.predict(q, changed, collect=True)
    assert not np.allclose(X[:60], X2[:60])
    params = {"lam": .95, "lam_short": .95, "prior": .35, "prior_short": .35}
    _, X, _ = core.predict(q, h, params, collect=True)
    _, X2, _ = core.predict(q, changed, params, collect=True)
    np.testing.assert_array_equal(X[:60], X2[:60])


def test_probability_contract_and_determinism():
    q, h = fixture()
    prediction = core_module().predict(q, h)
    validate_predictions(prediction, q)
    assert prediction == core_module().predict(q, h)
    prediction[q[0]["query_id"]] = [float("nan")]*5
    with pytest.raises(ValueError):
        validate_predictions(prediction, q)
