"""HE-10 adapter contract tests. Synthetic only; the train screen is a separate command."""
from copy import deepcopy
import numpy as np
import pytest

from research.challengers.ml_screen import historical_matrix, run_screen
from research.features import FeatureComputer
from research.learners import HistoricalModel
from research.models import PAYOUTS


def synthetic():
    queries, history, labels, condition_map = [], {}, {}, {}
    for condition_index, condition in enumerate(("stable", "short_history", "drift", "shared_change")):
        for episode_index in range(4):
            episode = f"{condition}_{episode_index}"
            for machine_index in range(2):
                query_id = f"{episode}_{machine_index}"
                machine = f"m{machine_index}"
                cutoff = 16
                queries.append({
                    "query_id": query_id,
                    "episode_id": episode,
                    "machine_id": machine,
                    "machine_type": "steady",
                    "signal": str((machine_index + episode_index) % 3 - 1),
                    "cutoff": str(cutoff),
                })
                history[(episode, machine)] = {tick: PAYOUTS[(tick + machine_index + condition_index) % 5] for tick in range(cutoff)}
                labels[query_id] = (cutoff + machine_index) % 5
                condition_map[query_id] = condition
    return queries, history, labels, condition_map


def test_missing_training_class_stays_inside_five_simplex():
    queries, history, labels, _ = synthetic()
    labels = {key: index % 3 for index, key in enumerate(labels)}
    model = HistoricalModel("logistic", ["type", "lags", "missingness"], supervision="query", seed=0)
    model.fit(queries, history, labels)
    predictions = model.predict_proba(queries[:4], history)
    for row in predictions.values():
        values = np.asarray(row, dtype=float)
        assert values.shape == (5,)
        assert abs(values.sum() - 1) < 1e-6
        # Temperature scaling clips exact zeros to 1e-9 before renormalizing.
        assert values[3] < 1e-6 and values[4] < 1e-6


def test_same_seed_is_deterministic():
    queries, history, labels, _ = synthetic()
    groups = ["type", "lags", "missingness"]
    first = HistoricalModel("hist_boost", groups, {"iters": 5}, supervision="query", seed=0)
    second = HistoricalModel("hist_boost", groups, {"iters": 5}, supervision="query", seed=0)
    first.fit(queries, history, labels)
    second.fit(queries, history, labels)
    a = first.predict_proba(queries[:3], history)
    b = second.predict_proba(queries[:3], history)
    for key in a:
        np.testing.assert_allclose(a[key], b[key], atol=1e-12)


def test_historical_features_ignore_signal_and_future_ticks():
    queries, history, _, _ = synthetic()
    groups = ("lags", "missingness")
    features, labels, _, _ = historical_matrix(queries[:2], history, groups, stride=4, max_rows=2)
    assert set(labels).issubset(set(range(5)))
    assert len(features) == 4
    query = queries[0]
    computer = FeatureComputer(history)
    baseline = computer.row(query, groups)[0]
    leaked = deepcopy(history)
    leaked[(query["episode_id"], query["machine_id"])][int(query["cutoff"])] = 20
    assert np.array_equal(baseline, FeatureComputer(leaked).row(query, groups)[0])
    with pytest.raises(ValueError, match="query-time signal"):
        historical_matrix(queries[:1], history, ("lags", "current_signal"), 4, 1)


def test_two_families_share_one_fold_manifest(tmp_path):
    queries, history, labels, condition_map = synthetic()
    config = {
        "seed": 0,
        "fold_count": 4,
        "holdout_fold": 0,
        "query_groups": ["type", "lags", "missingness", "current_signal"],
        "historical_groups": ["type", "lags", "missingness"],
        "historical_stride": 4,
        "historical_max_rows": 2,
        "families": {"logistic": {"C": 1.0}, "hist_boost": {"iters": 5, "lr": 0.1, "leaves": 4, "l2": 1.0}},
    }
    report = run_screen(queries, history, labels, condition_map, config, tmp_path / "cache")
    assert report["official_points"] is None
    assert report["status"] == "MEASURED_NOT_PROMOTED"
    assert set(report["families"]) == {"logistic", "hist_boost"}
    logistic_episodes = set(report["families"]["logistic"]["query_supervision"]["per_episode"])
    boost_episodes = set(report["families"]["hist_boost"]["query_supervision"]["per_episode"])
    assert logistic_episodes == boost_episodes
    assert report["n_holdout_queries"] > 0
    for family in report["families"].values():
        for mode in ("query_supervision", "historical_supervision"):
            assert 0 <= family[mode]["mean_brier"] <= 2
