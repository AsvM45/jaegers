"""HE-12 gating, simplex, and out-of-fold ensemble tests."""
import inspect

import numpy as np

from research.challengers.stat_ensemble import gate_member, mixture, run_screen, temper
from research.models import PAYOUTS


def synthetic():
    queries, history, labels, condition_map = [], {}, {}, {}
    for condition_index, condition in enumerate(("stable", "short_history", "drift", "shared_change")):
        for episode_index in range(4):
            episode = f"{condition}_{episode_index}"
            for machine_index in range(2):
                query_id = f"{episode}_{machine_index}"
                machine = f"m{machine_index}"
                cutoff = 12
                queries.append({
                    "query_id": query_id, "episode_id": episode, "machine_id": machine,
                    "machine_type": "steady", "signal": "0", "cutoff": str(cutoff),
                })
                history[(episode, machine)] = {tick: PAYOUTS[(tick + machine_index + condition_index) % 5] for tick in range(cutoff)}
                labels[query_id] = (cutoff + machine_index) % 5
                condition_map[query_id] = condition
    return queries, history, labels, condition_map


def test_gate_uses_history_length_not_condition_labels():
    assert "condition" not in inspect.signature(gate_member).parameters
    assert gate_member(3, 8) == "no_peer"
    assert gate_member(8, 8) == "ensemble"


def test_future_tick_does_not_change_mixture():
    queries, history, _, _ = synthetic()
    query = queries[0]
    before, count = mixture(query, history, {"prior": 0.5, "window": 8}, "no_peer")
    history[(query["episode_id"], query["machine_id"])][int(query["cutoff"])] = 20
    after, after_count = mixture(query, history, {"prior": 0.5, "window": 8}, "no_peer")
    assert count == after_count
    np.testing.assert_allclose(before, after)


def test_temperature_one_preserves_a_simplex():
    rows = np.array([[0.4, 0.3, 0.2, 0.05, 0.05]])
    adjusted = temper(rows, 1)
    np.testing.assert_allclose(adjusted.sum(axis=1), 1)
    assert np.all(adjusted >= 0)


def test_oof_ensemble_covers_every_query():
    queries, history, labels, condition_map = synthetic()
    config = {
        "seed": 0, "fold_count": 4, "prior": 0.5, "window": 4, "short_history_max": 8, "baseline": "no_peer",
        "temperatures": [1.0, 2.0],
        "learners": [{
            "family": "logistic", "params": {"C": 1.0},
            "groups": ["type", "lags", "missingness"],
        }],
    }
    report = run_screen(queries, history, labels, condition_map, config)
    assert report["official_points"] is None
    assert report["included_issue9_forecasts"] is False
    assert report["condition_labels_used_as_inputs"] is False
    assert report["n_queries"] == len(queries)
    for name in ("no_peer", "drift", "logistic", "ensemble", "gated"):
        assert report["models"][name]["per_episode"]
        assert 0 <= report["models"][name]["mean_brier"] <= 2
