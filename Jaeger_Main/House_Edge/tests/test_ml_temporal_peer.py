"""HE-11 leakage tests and same-fold peer/drift comparison."""
from copy import deepcopy
import numpy as np

from research.challengers.temporal_peer import exact_window, observed, run_screen, sibling_labels
from research.models import PAYOUTS


def synthetic():
    queries, history, labels, condition_map = [], {}, {}, {}
    for condition_index, condition in enumerate(("stable", "short_history", "drift", "shared_change")):
        for episode_index in range(4):
            episode = f"{condition}_{episode_index}"
            for machine_index, machine_type in enumerate(("steady", "balanced")):
                query_id = f"{episode}_{machine_index}"
                machine = f"m{machine_index}"
                cutoff = 16
                queries.append({
                    "query_id": query_id, "episode_id": episode, "machine_id": machine,
                    "machine_type": machine_type, "signal": "0", "cutoff": str(cutoff),
                })
                history[(episode, machine)] = {
                    tick: PAYOUTS[(tick + machine_index + condition_index) % 5] for tick in range(cutoff)
                }
                labels[query_id] = (cutoff + machine_index) % 5
                condition_map[query_id] = condition
    return queries, history, labels, condition_map


def test_siblings_ignore_future_ticks_other_episodes_and_signal():
    queries, history, _, _ = synthetic()
    query = queries[0]
    cutoff = int(query["cutoff"])
    baseline = sibling_labels(history, query["episode_id"], query["machine_id"], cutoff, "all", 8)
    leaked = deepcopy(history)
    leaked[(query["episode_id"], "m1")][cutoff] = 20
    leaked[("other", "m9")] = {tick: 20 for tick in range(cutoff + 2)}
    assert sibling_labels(leaked, query["episode_id"], query["machine_id"], cutoff, "all", 8) == baseline
    changed = dict(query, signal="1")
    assert observed(history, changed["episode_id"], changed["machine_id"], cutoff) == observed(
        history, query["episode_id"], query["machine_id"], cutoff
    )


def test_missing_exact_tick_is_not_a_zero_payout():
    ticks = [0, 1, 2, 3, 4, 5, 7]
    labels = [PAYOUTS.index(0 if tick % 2 == 0 else 1) for tick in ticks]
    window = exact_window(ticks, labels, cutoff=8, width=2)
    assert 6 not in ticks
    assert window == [labels[-1]]
    assert PAYOUTS.index(0) not in window or ticks[-1] % 2 == 0


def test_exact_window_differs_from_most_recent_rows():
    queries, history, _, _ = synthetic()
    query = queries[0]
    history[(query["episode_id"], query["machine_id"])].pop(14)
    ticks, labels = observed(history, query["episode_id"], query["machine_id"], 16)
    exact = exact_window(ticks, labels, 16, 8)
    recent = labels[-8:]
    assert len(exact) == 7
    assert len(recent) == 8
    assert exact != recent


def test_same_fold_variants_and_simplex(tmp_path):
    del tmp_path
    queries, history, labels, condition_map = synthetic()
    config = {
        "seed": 0, "fold_count": 4, "holdout_fold": 0, "prior": 0.5, "window": 8, "baseline": "no_peer",
        "variants": ["no_peer", "peer", "drift", "peer_drift", "global", "local"],
        "hypotheses": {"peer": "siblings help"},
    }
    report = run_screen(queries, history, labels, condition_map, config)
    assert report["official_points"] is None
    assert report["status"] == "MEASURED_NOT_PROMOTED"
    assert set(report["variants"]) == set(config["variants"])
    episodes = [set(report["variants"][name]["per_episode"]) for name in config["variants"]]
    assert all(group == episodes[0] for group in episodes)
    for variant in report["variants"].values():
        assert 0 <= variant["mean_brier"] <= 2
        for row in variant["class_brier"]:
            assert np.isfinite(row)
