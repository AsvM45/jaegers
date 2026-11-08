"""Legality and plumbing tests for the HE-87 campaign. Synthetic data only."""
import json
from pathlib import Path

import numpy as np

from research.challengers.grok_he87_experiment import run_campaign, write_reports
from research.challengers.grok_he87_features import GROUP_ORDER, build_bundle, build_index, leakage_controls, row_parts
from research.challengers.grok_he87_models import (
    EXPERT_ORDER,
    apply_softmax_gate,
    fit_cell_gate,
    fit_experts,
    fit_softmax_gate,
    fit_static_weights,
    predict_experts,
    project_simplex,
)

PAYOUTS = (0, 1, 2, 5, 20)
ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = ROOT / "research" / "configs" / "grok_he87_protocol.json"


def synthetic():
    queries, history, labels, condition_map = [], {}, {}, {}
    conditions = ("stable", "short_history", "drift", "shared_change")
    types = ("steady", "balanced", "jackpot")
    for condition_index, condition in enumerate(conditions):
        for episode_index in range(4):
            episode = f"{condition}_{episode_index}"
            for machine_index in range(2):
                query_id = f"{episode}_m{machine_index}"
                machine = f"m{machine_index}"
                cutoff = 18
                queries.append({
                    "query_id": query_id,
                    "episode_id": episode,
                    "machine_id": machine,
                    "machine_type": types[(condition_index + machine_index) % 3],
                    "signal": str((machine_index % 3) - 1),
                    "cutoff": str(cutoff),
                })
                rows = {}
                for tick in range(cutoff):
                    if tick == 3 and machine_index == 0:
                        continue
                    rows[tick] = PAYOUTS[(tick + condition_index + machine_index) % 5]
                history[(episode, machine)] = rows
                last_tick = max(rows)
                labels[query_id] = PAYOUTS.index(rows[last_tick])
                condition_map[query_id] = condition
    return queries, history, labels, condition_map


def tiny_config():
    return {
        "seed": 0,
        "fold_count": 4,
        "bootstrap": 200,
        "public_validation_peeks": 0,
        "feature_baseline": ["type", "exact_lags"],
        "feature_groups": ["sparse", "discounted", "sibling", "transitions", "entropy", "changepoint", "win_size", "rarity20", "interactions"],
        "logistic_C": 1.0,
        "logistic_max_iter": 60,
        "logistic_C_grid": [1.0],
        "elastic_net": {"C": 1.0, "l1_ratio": 0.5, "max_iter": 40},
        "extra_trees": {"trees": 4, "depth": 3, "leaf": 1},
        "hist_boost": {"iters": 3, "lr": 0.1, "leaves": 4, "l2": 1.0},
        "run_extra_trees": True,
        "run_hist_boost": True,
        "dirichlet_strength": 10.0,
        "dirichlet_decay": 0.97,
        "short_strength": 5.0,
        "short_window": 8,
        "markov_alpha": 1.0,
        "factorized_strength": 10.0,
        "factorized_decay": 0.97,
        "peer_kappa": 4.0,
        "drift_tau": 0.25,
        "dirichlet_grid": {"strength": [10.0], "decay": [0.97]},
        "peer_kappa_grid": [4.0],
        "drift_tau_grid": [0.25],
        "moe_experts": ["dirichlet_long", "dirichlet_short", "markov_exact_lag1", "factorized_size", "peer_shrink"],
        "regime_thresholds": {"short_n": 8, "sparse_coverage": 0.5, "volatile_l1": 0.3, "shared_l1": 0.3},
        "regime_min_count": 100,
        "inner_folds": 3,
        "references": ["frequency"],
        "gate_steps": 20,
        "gate_lr": 0.1,
    }


def test_missing_exact_lag_is_not_encoded_as_zero():
    query = {
        "query_id": "q", "episode_id": "e", "machine_id": "a", "machine_type": "steady",
        "signal": "0", "cutoff": "4",
    }
    history = {("e", "a"): {1: 20}, ("e", "b"): {1: 0}}
    parts, names, _, _, _, _ = row_parts(query, build_index(history))
    lag_names = names["exact_lags"]
    lag = parts["exact_lags"]
    assert lag[lag_names.index("exact_lags/lag1_missing")] == 1.0
    assert lag[lag_names.index("exact_lags/lag1_c0")] == 0.0
    assert lag[lag_names.index("exact_lags/lag2_missing")] == 1.0
    assert lag[lag_names.index("exact_lags/lag3_missing")] == 0.0
    assert lag[lag_names.index("exact_lags/lag3_c4")] == 1.0
    assert lag[lag_names.index("exact_lags/lag3_c0")] == 0.0


def test_leakage_controls_hold_on_synthetic_histories():
    queries, history, _, _ = synthetic()
    controls = leakage_controls(queries, history)
    assert controls["signal_inert"] is True
    assert controls["future_tick_inert"] is True
    assert controls["peer_cutoff_excluded"] is True
    assert controls["other_episode_inert"] is True
    assert controls["signal_block_changes_when_requested"] is True


def test_experts_ignore_test_labels_and_future_payouts():
    queries, history, labels, _ = synthetic()
    index = build_index(history)
    settings = {
        "dirichlet_strength": 10.0, "dirichlet_decay": 0.97, "short_strength": 5.0, "short_window": 8,
        "markov_alpha": 1.0, "factorized_strength": 10.0, "factorized_decay": 0.97, "peer_kappa": 4.0,
        "drift_tau": 0.25,
    }
    state = fit_experts(queries[:8], labels, index)
    original = predict_experts(queries[8:12], index, state, settings)
    changed_labels = dict(labels)
    for query in queries[8:12]:
        changed_labels[query["query_id"]] = (changed_labels[query["query_id"]] + 1) % 5
    refit = fit_experts(queries[:8], changed_labels, index)
    assert np.allclose(original, predict_experts(queries[8:12], index, refit, settings))
    probe = queries[8]
    mutated = {key: dict(rows) for key, rows in history.items()}
    mutated[(probe["episode_id"], probe["machine_id"])][int(probe["cutoff"])] = 20
    future = predict_experts([probe], build_index(mutated), state, settings)
    assert np.allclose(future, predict_experts([probe], index, state, settings))
    assert original.shape[1] == len(EXPERT_ORDER)
    assert np.allclose(original.sum(axis=2), 1.0)


def test_exact_lag_markov_differs_from_last_observed_when_lag_is_missing():
    query = {
        "query_id": "q", "episode_id": "e", "machine_id": "a", "machine_type": "steady",
        "signal": "0", "cutoff": "5",
    }
    history = {("e", "a"): {1: 20}}
    state = {
        "prior": {machine_type: np.full(5, 0.2) for machine_type in ("steady", "balanced", "jackpot")},
        "exact": {machine_type: np.zeros((6, 5)) for machine_type in ("steady", "balanced", "jackpot")},
        "last": {machine_type: np.zeros((6, 5)) for machine_type in ("steady", "balanced", "jackpot")},
    }
    state["exact"]["steady"][5, 1] = 30.0
    state["last"]["steady"][4, 0] = 30.0
    settings = {
        "dirichlet_strength": 1.0, "dirichlet_decay": 1.0, "short_strength": 1.0, "short_window": 4,
        "markov_alpha": 1.0, "factorized_strength": 1.0, "factorized_decay": 1.0, "peer_kappa": 1.0,
        "drift_tau": 2.0,
    }
    cube = predict_experts([query], build_index(history), state, settings)
    exact = cube[0, EXPERT_ORDER.index("markov_exact_lag1")]
    last = cube[0, EXPERT_ORDER.index("markov_last_observed")]
    assert exact[1] > exact[0]
    assert last[0] > last[1]


def test_static_and_regime_gates_recover_a_separated_problem():
    count = 40
    predictions = np.zeros((count, 2, 5))
    labels = np.zeros(count, dtype=int)
    predictions[:, 0, 0] = 1.0
    predictions[:, 1, 1] = 1.0
    labels[20:] = 1
    weights = fit_static_weights(predictions[:20], labels[:20], steps=80, lr=0.3)
    assert abs(weights.sum() - 1.0) < 1e-8
    assert weights[0] > 0.9
    covariates = np.zeros((count, 1))
    covariates[:20, 0] = 1.0
    gate = fit_softmax_gate(predictions, covariates, labels, steps=150, lr=0.6, l2=0.0)
    _, mixing = apply_softmax_gate(predictions, covariates, gate)
    assert mixing[:20, 0].mean() > 0.7
    assert mixing[20:, 1].mean() > 0.7
    hard = np.zeros((20, 4))
    hard[10:, 0] = 1.0
    separated = np.zeros((20, 2, 5))
    separated[:, 0, 0] = 1.0
    separated[:, 1, 1] = 1.0
    cell_labels = np.array([0] * 10 + [1] * 10)
    cells = fit_cell_gate(separated, hard, cell_labels, np.array([0.5, 0.5]), min_count=5)
    assert cells["choices"]["0"]["mode"] == "expert"
    assert cells["choices"]["0"]["expert"] == 0
    assert cells["choices"]["1"]["expert"] == 1
    backed_off = fit_cell_gate(separated, hard, cell_labels, np.array([0.5, 0.5]), min_count=100)
    assert backed_off["choices"]["0"]["mode"] == "static"


def test_simplex_projection_stays_nonnegative_and_normalized():
    even = project_simplex(np.full(5, 0.2))
    assert np.allclose(even, np.full(5, 0.2))
    projected = project_simplex(np.array([2.0, -1.0, 0.0]))
    assert np.all(projected >= -1e-12)
    assert abs(projected.sum() - 1.0) < 1e-8


def test_synthetic_campaign_records_negative_control_and_writes_reports(tmp_path):
    queries, history, labels, condition_map = synthetic()
    result = run_campaign(queries, history, labels, condition_map, tiny_config())
    assert result["public_validation_peeks"] == 0
    assert result["validation_files_opened"] is False
    assert result["official_points"] is None
    names = {row["name"] for row in result["candidates"]}
    assert "frequency_default" in names
    assert "moe_static" in names
    assert "logistic_label_permutation" in names
    assert "jaeger_frozen_params" not in names
    by_name = {row["name"]: row for row in result["candidates"]}
    assert by_name["logistic_label_permutation"]["mean_brier"] > by_name["logistic_full"]["mean_brier"]
    assert result["leakage_controls"]["signal_inert"] is True
    assert result["feature_ranking"]
    assert result["mixture"]["diversity"]["outer_test_error_correlation"]
    repeated = run_campaign(queries, history, labels, condition_map, tiny_config())
    assert repeated["fold_manifest_sha256"] == result["fold_manifest_sha256"]
    assert repeated["best_observed_mean_brier"] == result["best_observed_mean_brier"]
    write_reports(tmp_path, result)
    payload = json.loads((tmp_path / "grok_he87_results.json").read_text(encoding="utf-8"))
    assert payload["status"] == "MEASURED_NOT_PROMOTED"
    report = (tmp_path / "grok_he87_report.md").read_text(encoding="utf-8")
    assert "MEASURED_NOT_PROMOTED" in report
    assert "Public-validation peeks: 0" in report


def test_protocol_is_closed_at_zero_validation_peeks():
    protocol = json.loads(PROTOCOL.read_text(encoding="utf-8"))
    assert protocol["public_validation_peeks"] == 0
    assert set(protocol["feature_baseline"] + protocol["feature_groups"]) <= set(GROUP_ORDER)
    assert set(protocol["moe_experts"]) <= set(EXPERT_ORDER)
    assert "jaeger" in protocol["references"]
    bundle_groups = build_bundle([], {}, groups=tuple(GROUP_ORDER))
    assert bundle_groups["X"].shape == (0, 0)
