"""Bounded HE-87 campaign: same episode folds, lawful features, mixtures, negative results.

Scores are sampled-outcome Brier on held-out train queries. They are not official
round points. This module never reads public validation or test targets.
"""
from __future__ import annotations

import argparse
import json
import os
import time
import tracemalloc
from pathlib import Path

os.environ.setdefault("OMP_NUM_THREADS", "2")
os.environ.setdefault("OPENBLAS_NUM_THREADS", "2")
os.environ.setdefault("MKL_NUM_THREADS", "2")
os.environ.setdefault("NUMEXPR_NUM_THREADS", "2")

import numpy as np

from research.adapters import FrequencyModel, core_module
from research.challengers.grok_he87_features import (
    GROUP_ORDER,
    TYPES,
    build_bundle,
    columns_for,
    leakage_controls,
)
from research.challengers.grok_he87_models import (
    EXPERT_ORDER,
    aligned_proba,
    apply_cell_gate,
    apply_softmax_gate,
    apply_temperature_bias,
    error_correlation,
    fit_cell_gate,
    fit_experts,
    fit_softmax_gate,
    fit_static_weights,
    fit_temperature_bias,
    make_extra_trees,
    make_hist_boost,
    make_logistic,
    predict_dirichlet_grid,
    predict_drift_tau,
    predict_experts,
    predict_peer_kappa,
)
from research.common import digest, environment, file_hash, require_python, write_json
from research.dataset import conditions as read_conditions
from research.dataset import episode_folds, read_labels
from research.metrics import diagnostics, paired

HERE = Path(__file__).resolve()
HOUSE = HERE.parents[2]
DEFAULT_CONFIG = HOUSE / "research" / "configs" / "grok_he87_protocol.json"
DEFAULT_OUT = HOUSE / "research" / "reports"


def expert_settings(config):
    return {
        "dirichlet_strength": float(config["dirichlet_strength"]),
        "dirichlet_decay": float(config["dirichlet_decay"]),
        "short_strength": float(config["short_strength"]),
        "short_window": int(config["short_window"]),
        "markov_alpha": float(config["markov_alpha"]),
        "factorized_strength": float(config["factorized_strength"]),
        "factorized_decay": float(config["factorized_decay"]),
        "peer_kappa": float(config["peer_kappa"]),
        "drift_tau": float(config["drift_tau"]),
    }


def json_ready(value):
    if isinstance(value, dict):
        return {str(key): json_ready(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_ready(item) for item in value]
    if isinstance(value, np.ndarray):
        return json_ready(value.tolist())
    if isinstance(value, np.floating):
        return float(value)
    if isinstance(value, np.integer):
        return int(value)
    if isinstance(value, np.bool_):
        return bool(value)
    return value


def expected_calibration_error(predicted, observed, bins=10):
    predicted = np.asarray(predicted, dtype=np.float64)
    observed = np.asarray(observed, dtype=np.float64)
    total = 0.0
    table = []
    count = len(predicted)
    for bin_id in range(bins):
        lo = bin_id / bins
        hi = (bin_id + 1) / bins
        if bin_id + 1 < bins:
            mask = (predicted >= lo) & (predicted < hi)
        else:
            mask = (predicted >= lo) & (predicted <= 1.0)
        if not np.any(mask):
            continue
        pred_mean = float(predicted[mask].mean())
        obs_mean = float(observed[mask].mean())
        weight = float(mask.sum() / count)
        total += weight * abs(pred_mean - obs_mean)
        table.append({"bin": bin_id, "count": int(mask.sum()), "predicted": pred_mean, "observed": obs_mean})
    return float(total), table


def fold_scores(per_episode, episode_conditions, folds):
    scores = {}
    for fold in sorted(set(folds.values())):
        episodes = [episode for episode, assigned in folds.items() if assigned == fold]
        by_condition = {}
        for episode in episodes:
            by_condition.setdefault(episode_conditions[episode], []).append(per_episode[episode])
        scores[str(fold)] = float(np.mean([float(np.mean(values)) for values in by_condition.values()]))
    return scores


def summarize_matrix(name, probabilities, queries, labels, condition_map, folds, seconds, facts=None):
    probabilities = np.asarray(probabilities, dtype=np.float64)
    if probabilities.shape != (len(queries), 5):
        raise ValueError(f"{name} predictions have shape {probabilities.shape}")
    if not np.isfinite(probabilities).all():
        raise ValueError(f"{name} predictions are not finite")
    mapping = {query["query_id"]: probabilities[index] for index, query in enumerate(queries)}
    report = diagnostics(mapping, queries, labels, condition_map)
    y = np.array([labels[query["query_id"]] for query in queries], dtype=int)
    ece, table = expected_calibration_error(probabilities[:, 4], y == 4)
    summary = {
        "name": name,
        "evaluation_source": "sampled_outcome_group_cv",
        "official_points": None,
        "mean_brier": report["mean_brier"],
        "by_condition": report["by_condition"],
        "log_loss": report["log_loss"],
        "class_brier": [float(value) for value in report["class_brier"]],
        "class_counts": [int(value) for value in report["class_counts"]],
        "class_20_mean_prediction": float(probabilities[:, 4].mean()),
        "class_20_observed_rate": float(np.mean(y == 4)),
        "class_20_ece": ece,
        "class_20_reliability": table,
        "per_episode": report["per_episode"],
        "episode_conditions": report["episode_conditions"],
        "fit_seconds": float(seconds),
        "fold_brier": fold_scores(report["per_episode"], report["episode_conditions"], folds),
    }
    if facts is not None:
        summary["query_stratified_brier"] = stratified_brier(probabilities, y, facts)
    return summary


def stratified_brier(probabilities, y, facts):
    losses = np.sum((probabilities - np.eye(5)[y]) ** 2, axis=1)
    buckets = {"short_<8": [], "mid_8_31": [], "long_>=32": [], "lag1_known": [], "lag1_missing": []}
    by_type = {machine_type: [] for machine_type in TYPES}
    for index, fact in enumerate(facts):
        by_type[fact["machine_type"]].append(float(losses[index]))
        if fact["n_obs"] < 8:
            buckets["short_<8"].append(float(losses[index]))
        elif fact["n_obs"] < 32:
            buckets["mid_8_31"].append(float(losses[index]))
        else:
            buckets["long_>=32"].append(float(losses[index]))
        buckets["lag1_known" if fact["lag1_known"] else "lag1_missing"].append(float(losses[index]))

    def mean(values):
        return None if not values else float(np.mean(values))

    return {
        "definition": "mean query-level sampled Brier, not the episode-then-condition average",
        "by_machine_type": {key: mean(value) for key, value in by_type.items()},
        "by_history": {key: mean(value) for key, value in buckets.items()},
    }


def wins_losses(candidate, baseline):
    wins = losses = ties = 0
    for episode, baseline_loss in baseline["per_episode"].items():
        delta = candidate["per_episode"][episode] - baseline_loss
        if delta < -1e-12:
            wins += 1
        elif delta > 1e-12:
            losses += 1
        else:
            ties += 1
    return {"episodes_better": wins, "episodes_worse": losses, "ties": ties}


def compare(candidate, baseline, bootstrap, seed):
    report = paired(candidate, baseline, bootstrap=bootstrap, seed=seed)
    report.update(wins_losses(candidate, baseline))
    report["baseline"] = baseline["name"]
    report["candidate"] = candidate["name"]
    return report


def oof_sklearn(factory, features, y, episodes, folds):
    predictions = np.zeros((len(y), 5), dtype=np.float64)
    seconds = 0.0
    models = []
    import warnings
    from sklearn.exceptions import ConvergenceWarning

    warnings_seen = 0
    for fold in sorted(set(folds.values())):
        test = np.array([folds[episode] == fold for episode in episodes])
        if test.all() or not test.any():
            raise ValueError("Fold split is empty")
        model = factory()
        started = time.perf_counter()
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always", ConvergenceWarning)
            model.fit(features[~test], y[~test])
            warnings_seen += sum(1 for item in caught if issubclass(item.category, ConvergenceWarning))
        seconds += time.perf_counter() - started
        predictions[test] = aligned_proba(model, features[test])
        models.append((fold, model))
    return predictions, seconds, models, warnings_seen


def group_importance(models, names, slices):
    totals = {group: [] for group in slices}
    for _, model in models:
        estimator = model
        if hasattr(model, "named_steps"):
            estimator = model.named_steps["logisticregression"]
        if hasattr(estimator, "coef_"):
            score = np.abs(estimator.coef_).mean(axis=0)
        elif hasattr(estimator, "feature_importances_"):
            score = np.asarray(estimator.feature_importances_, dtype=np.float64)
        else:
            return {}
        for group, indexes in slices.items():
            totals[group].append(float(np.mean(score[indexes])))
    return {group: float(np.mean(values)) for group, values in totals.items() if values}


def oof_reference(factory, queries, history, labels, folds):
    predictions = {}
    started = time.perf_counter()
    for fold in sorted(set(folds.values())):
        hold = {episode for episode, assigned in folds.items() if assigned == fold}
        fit_queries = [query for query in queries if query["episode_id"] not in hold]
        hold_queries = [query for query in queries if query["episode_id"] in hold]
        fit_episodes = {query["episode_id"] for query in fit_queries}
        hold_episodes = {query["episode_id"] for query in hold_queries}
        fit_history = {key: value for key, value in history.items() if key[0] in fit_episodes}
        hold_history = {key: value for key, value in history.items() if key[0] in hold_episodes}
        model = factory()
        fit_labels = {query["query_id"]: labels[query["query_id"]] for query in fit_queries}
        model.fit(fit_queries, fit_history, fit_labels)
        predictions.update(model.predict_proba(hold_queries, hold_history))
    matrix = np.vstack([np.asarray(predictions[query["query_id"]], dtype=np.float64) for query in queries])
    return matrix, time.perf_counter() - started


def coverage_facts(facts):
    count = max(len(facts), 1)
    return {
        "queries": len(facts),
        "mean_observed_ticks": float(np.mean([fact["n_obs"] for fact in facts])) if facts else 0.0,
        "fraction_lag1_known": float(np.mean([fact["lag1_known"] for fact in facts])) if facts else 0.0,
        "fraction_seen_20": float(np.mean([fact["seen_20"] for fact in facts])) if facts else 0.0,
        "fraction_with_peer_observations": float(np.mean([fact["peer_mass"] > 0 for fact in facts])) if facts else 0.0,
        "fraction_short_history": float(np.mean([fact["n_obs"] < 8 for fact in facts])) if facts else 0.0,
        "denominator": count,
    }


def compact_slices(groups, bundle):
    slices = {}
    cursor = 0
    for group in groups:
        width = len(bundle["slices"][group])
        slices[group] = list(range(cursor, cursor + width))
        cursor += width
    return slices


def run_campaign(queries, history, labels, condition_map, config):
    if int(config.get("public_validation_peeks", 0)) != 0:
        raise ValueError("This campaign is preregistered at zero public-validation peeks")
    started = time.perf_counter()
    tracemalloc.start()
    try:
        return _execute(queries, history, labels, condition_map, config, started)
    finally:
        if tracemalloc.is_tracing():
            tracemalloc.stop()


def _execute(queries, history, labels, condition_map, config, started):
    keys = [(query["episode_id"], query["machine_id"]) for query in queries]
    if len(keys) != len(set(keys)):
        raise ValueError("Expected one query per episode machine")
    for key in keys:
        if key not in history:
            raise ValueError(f"Missing history for {key}")
    folds = episode_folds(queries, condition_map, int(config["fold_count"]))
    bundle = build_bundle(queries, history, groups=GROUP_ORDER, thresholds=config["regime_thresholds"])
    controls = leakage_controls(queries, history, thresholds=config["regime_thresholds"])
    if not all(controls[key] for key in ("signal_inert", "future_tick_inert", "peer_cutoff_excluded", "other_episode_inert")):
        raise RuntimeError(f"Leakage controls failed: {controls}")
    y = np.array([labels[query["query_id"]] for query in queries], dtype=int)
    episodes = [query["episode_id"] for query in queries]
    settings = expert_settings(config)
    seed = int(config["seed"])
    candidates = []
    sensitivities = []
    negative = []

    def add_candidate(name, probabilities, seconds):
        summary = summarize_matrix(name, probabilities, queries, labels, condition_map, folds, seconds, bundle["facts"])
        candidates.append(summary)
        return summary

    baseline_groups = list(config["feature_baseline"])
    addon_groups = list(config["feature_groups"])
    full_groups = baseline_groups + [group for group in addon_groups if group not in baseline_groups]
    baseline_x = bundle["X"][:, columns_for(bundle, baseline_groups)]
    full_x = bundle["X"][:, columns_for(bundle, full_groups)]

    def logistic_factory(C=None, elastic=False):
        value = float(config["logistic_C"] if C is None else C)
        return lambda: make_logistic(value, seed, elastic=elastic, max_iter=int(config["logistic_max_iter"]))

    base_pred, base_seconds, _, base_warnings = oof_sklearn(logistic_factory(), baseline_x, y, episodes, folds)
    baseline = add_candidate("logistic_type_exact_lags", base_pred, base_seconds)
    one_factor = []
    for group in addon_groups:
        columns = columns_for(bundle, baseline_groups + [group])
        pred, seconds, _, warnings_seen = oof_sklearn(logistic_factory(), bundle["X"][:, columns], y, episodes, folds)
        summary = add_candidate(f"logistic_base_plus_{group}", pred, seconds)
        one_factor.append({
            "group": group,
            "mean_brier": summary["mean_brier"],
            "delta_brier_vs_baseline": summary["mean_brier"] - baseline["mean_brier"],
            "by_condition": summary["by_condition"],
            "fit_seconds": summary["fit_seconds"],
            "convergence_warnings": warnings_seen,
            "legality": "past ticks only; group does not read query signal",
        })
    one_factor_sorted = sorted(one_factor, key=lambda row: row["delta_brier_vs_baseline"])
    pair_rows = []
    top_groups = [row["group"] for row in one_factor_sorted[:3]]
    for left_index, left in enumerate(top_groups):
        for right in top_groups[left_index + 1:]:
            columns = columns_for(bundle, baseline_groups + [left, right])
            pred, seconds, _, _ = oof_sklearn(logistic_factory(), bundle["X"][:, columns], y, episodes, folds)
            summary = add_candidate(f"logistic_base_plus_{left}_and_{right}", pred, seconds)
            left_delta = next(row["delta_brier_vs_baseline"] for row in one_factor if row["group"] == left)
            right_delta = next(row["delta_brier_vs_baseline"] for row in one_factor if row["group"] == right)
            interaction = (summary["mean_brier"] - baseline["mean_brier"]) - left_delta - right_delta
            pair_rows.append({
                "groups": [left, right],
                "mean_brier": summary["mean_brier"],
                "delta_brier_vs_baseline": summary["mean_brier"] - baseline["mean_brier"],
                "interaction_beyond_main_effects": interaction,
                "fit_seconds": summary["fit_seconds"],
                "selection": "pair chosen from the three best one-factor groups on this same CV; exploratory, not a fresh test",
            })

    full_pred, full_seconds, full_models, full_warnings = oof_sklearn(logistic_factory(), full_x, y, episodes, folds)
    full_summary = add_candidate("logistic_full", full_pred, full_seconds)
    signal_x = np.hstack([full_x, bundle["signal"]])
    signal_pred, signal_seconds, _, _ = oof_sklearn(logistic_factory(), signal_x, y, episodes, folds)
    signal_summary = add_candidate("logistic_full_plus_own_query_signal", signal_pred, signal_seconds)
    elastic_pred, elastic_seconds, _, elastic_warnings = oof_sklearn(
        lambda: make_logistic(float(config["elastic_net"]["C"]), seed, elastic=True, max_iter=int(config["elastic_net"]["max_iter"])),
        full_x, y, episodes, folds,
    )
    add_candidate("elastic_net_full", elastic_pred, elastic_seconds)
    if config.get("run_extra_trees", True):
        trees = config["extra_trees"]
        tree_pred, tree_seconds, tree_models, _ = oof_sklearn(
            lambda: make_extra_trees(trees["trees"], trees["depth"], trees["leaf"], seed),
            full_x, y, episodes, folds,
        )
        add_candidate("extra_trees_full", tree_pred, tree_seconds)
        tree_importance = group_importance(tree_models, bundle["names"], compact_slices(full_groups, bundle))
    else:
        tree_importance = {}
    if config.get("run_hist_boost", True):
        boost = config["hist_boost"]
        boost_pred, boost_seconds, _, _ = oof_sklearn(
            lambda: make_hist_boost(boost["iters"], boost["lr"], boost["leaves"], boost["l2"], seed),
            full_x, y, episodes, folds,
        )
        add_candidate("hist_boost_full", boost_pred, boost_seconds)

    for C in config["logistic_C_grid"]:
        pred, seconds, _, warnings_seen = oof_sklearn(logistic_factory(C), full_x, y, episodes, folds)
        summary = summarize_matrix(f"logistic_full_C_{C}", pred, queries, labels, condition_map, folds, seconds, bundle["facts"])
        sensitivities.append({"family": "logistic_full", "C": float(C), "convergence_warnings": warnings_seen, **_public_summary(summary)})

    permuted = np.zeros_like(full_pred)
    permute_seconds = 0.0
    rng = np.random.default_rng(seed + 17)
    for fold in sorted(set(folds.values())):
        test = np.array([folds[episode] == fold for episode in episodes])
        shuffled = y.copy()
        train_ids = np.flatnonzero(~test)
        shuffled[train_ids] = rng.permutation(shuffled[train_ids])
        model = make_logistic(float(config["logistic_C"]), seed, max_iter=int(config["logistic_max_iter"]))
        tick = time.perf_counter()
        model.fit(full_x[~test], shuffled[~test])
        permute_seconds += time.perf_counter() - tick
        permuted[test] = aligned_proba(model, full_x[test])
    permutation = add_candidate("logistic_label_permutation", permuted, permute_seconds)
    negative.append({
        "name": "logistic_label_permutation",
        "result": "kept",
        "mean_brier": permutation["mean_brier"],
        "reason": "Training labels were permuted inside each fit fold. A score near the full logistic model would indicate leakage.",
    })

    primary = np.zeros((len(queries), len(EXPERT_ORDER), 5), dtype=np.float64)
    expert_seconds = 0.0
    fold_states = []
    for fold in sorted(set(folds.values())):
        test_index = [index for index, episode in enumerate(episodes) if folds[episode] == fold]
        train_queries = [queries[index] for index, episode in enumerate(episodes) if folds[episode] != fold]
        test_queries = [queries[index] for index in test_index]
        tick = time.perf_counter()
        state = fit_experts(train_queries, labels, bundle["index"])
        cube = predict_experts(test_queries, bundle["index"], state, settings)
        expert_seconds += time.perf_counter() - tick
        primary[test_index] = cube
        fold_states.append({
            "fold": fold,
            "test_index": test_index,
            "train_queries": train_queries,
            "test_queries": test_queries,
            "state": state,
        })
    per_expert_seconds = expert_seconds / len(EXPERT_ORDER)
    expert_summaries = {}
    for expert_index, name in enumerate(EXPERT_ORDER):
        expert_summaries[name] = add_candidate(name, primary[:, expert_index, :], per_expert_seconds)

    for strength in config["dirichlet_grid"]["strength"]:
        for decay in config["dirichlet_grid"]["decay"]:
            grid = np.zeros((len(queries), 5), dtype=np.float64)
            tick = time.perf_counter()
            for cached in fold_states:
                grid[cached["test_index"]] = predict_dirichlet_grid(
                    cached["test_queries"], bundle["index"], cached["state"], float(strength), float(decay)
                )
            seconds = time.perf_counter() - tick
            summary = summarize_matrix(
                f"dirichlet_s{strength}_d{decay}", grid, queries, labels, condition_map, folds, seconds, bundle["facts"]
            )
            sensitivities.append({
                "family": "dirichlet", "strength": float(strength), "decay": float(decay), **_public_summary(summary)
            })
    for kappa in config["peer_kappa_grid"]:
        grid = np.zeros((len(queries), 5), dtype=np.float64)
        tick = time.perf_counter()
        for cached in fold_states:
            grid[cached["test_index"]] = predict_peer_kappa(
                cached["test_queries"], bundle["index"], cached["state"], settings, float(kappa)
            )
        summary = summarize_matrix(f"peer_kappa_{kappa}", grid, queries, labels, condition_map, folds, time.perf_counter() - tick, bundle["facts"])
        sensitivities.append({"family": "peer_shrink", "kappa": float(kappa), **_public_summary(summary)})
    for tau in config["drift_tau_grid"]:
        grid = np.zeros((len(queries), 5), dtype=np.float64)
        tick = time.perf_counter()
        for cached in fold_states:
            grid[cached["test_index"]] = predict_drift_tau(
                cached["test_queries"], bundle["index"], cached["state"], settings, float(tau)
            )
        summary = summarize_matrix(f"drift_tau_{tau}", grid, queries, labels, condition_map, folds, time.perf_counter() - tick, bundle["facts"])
        sensitivities.append({"family": "drift_switch", "tau": float(tau), **_public_summary(summary)})

    moe_names = list(config["moe_experts"])
    moe_columns = [EXPERT_ORDER.index(name) for name in moe_names]
    static_oof = np.zeros((len(queries), 5), dtype=np.float64)
    regime_oof = np.zeros((len(queries), 5), dtype=np.float64)
    cell_oof = np.zeros((len(queries), 5), dtype=np.float64)
    calibrated_oof = np.zeros((len(queries), 5), dtype=np.float64)
    gate_records = []
    inner_cubes = []
    inner_labels = []
    moe_seconds = 0.0
    for cached in fold_states:
        train_ids = [index for index in range(len(queries)) if index not in set(cached["test_index"])]
        train_queries = [queries[index] for index in train_ids]
        inner = episode_folds(train_queries, condition_map, int(config["inner_folds"]))
        parts, part_y, part_z, part_hard = [], [], [], []
        tick = time.perf_counter()
        for inner_fold in sorted(set(inner.values())):
            val_episodes = {episode for episode, assigned in inner.items() if assigned == inner_fold}
            fit_queries = [query for query in train_queries if query["episode_id"] not in val_episodes]
            val_queries = [query for query in train_queries if query["episode_id"] in val_episodes]
            state = fit_experts(fit_queries, labels, bundle["index"])
            cube = predict_experts(val_queries, bundle["index"], state, settings)[:, moe_columns]
            parts.append(cube)
            part_y.append(np.array([labels[query["query_id"]] for query in val_queries], dtype=int))
            positions = [next(index for index, query in enumerate(queries) if query["query_id"] == item["query_id"]) for item in val_queries]
            part_z.append(bundle["regime_z"][positions])
            part_hard.append(bundle["regime_hard"][positions])
        inner_p = np.vstack(parts)
        inner_y = np.concatenate(part_y)
        inner_z = np.vstack(part_z)
        inner_hard = np.vstack(part_hard)
        weights = fit_static_weights(inner_p, inner_y, steps=int(config["gate_steps"]), lr=float(config["gate_lr"]))
        softmax = fit_softmax_gate(inner_p, inner_z, inner_y, steps=int(config["gate_steps"]), lr=float(config["gate_lr"]))
        mixture = np.einsum("e,nek->nk", weights, inner_p)
        calibration = fit_temperature_bias(mixture, inner_y)
        cells = fit_cell_gate(inner_p, inner_hard, inner_y, weights, int(config["regime_min_count"]))
        test_cube = primary[cached["test_index"]][:, moe_columns]
        test_z = bundle["regime_z"][cached["test_index"]]
        test_hard = bundle["regime_hard"][cached["test_index"]]
        static = np.einsum("e,nek->nk", weights, test_cube)
        regime, mixing = apply_softmax_gate(test_cube, test_z, softmax)
        cell = apply_cell_gate(test_cube, test_hard, cells)
        calibrated = apply_temperature_bias(static, calibration["temperature"], calibration["bias20"])
        static_oof[cached["test_index"]] = static
        regime_oof[cached["test_index"]] = regime
        cell_oof[cached["test_index"]] = cell
        calibrated_oof[cached["test_index"]] = calibrated
        moe_seconds += time.perf_counter() - tick
        gate_records.append({
            "fold": int(cached["fold"]),
            "static_weights": {name: float(weights[index]) for index, name in enumerate(moe_names)},
            "mean_softmax_gate_on_test": {name: float(mixing[:, index].mean()) for index, name in enumerate(moe_names)},
            "calibration": calibration,
            "cell_choices": cells["choices"],
        })
        inner_cubes.append(inner_p)
        inner_labels.append(inner_y)
    shared_moe_seconds = moe_seconds / max(len(fold_states), 1)
    static_summary = add_candidate("moe_static", static_oof, shared_moe_seconds)
    regime_summary = add_candidate("moe_regime_softmax", regime_oof, shared_moe_seconds)
    cell_summary = add_candidate("moe_regime_cells", cell_oof, shared_moe_seconds)
    calibrated_summary = add_candidate("moe_static_calibrated", calibrated_oof, shared_moe_seconds)
    if calibrated_summary["mean_brier"] > static_summary["mean_brier"]:
        negative.append({
            "name": "moe_static_calibrated",
            "result": "kept",
            "mean_brier": calibrated_summary["mean_brier"],
            "reason": "Inner-OOF temperature and 20x logit bias did not reduce outer-fold sampled Brier versus the uncalibrated static mixture.",
        })

    reference_notes = []
    reference_seconds = {}
    if "frequency" in config["references"]:
        freq_pred, freq_seconds = oof_reference(FrequencyModel, queries, history, labels, folds)
        add_candidate("frequency_default", freq_pred, freq_seconds)
        reference_seconds["frequency_default"] = freq_seconds
        reference_notes.append("frequency_default is the repository FrequencyModel with default strength 20, decay 1, peer 0.")
    champion_error = None
    if any(name in config["references"] for name in ("jaeger", "jaeger_causal")):
        try:
            from research.adapters import JaegerModel

            params = json.loads((HOUSE / "jaegers_entry" / "params.json").read_text(encoding="utf-8"))
            if "jaeger" in config["references"]:
                pred, seconds = oof_reference(lambda: JaegerModel(params, causal=False), queries, history, labels, folds)
                add_candidate("jaeger_frozen_params", pred, seconds)
                reference_seconds["jaeger_frozen_params"] = seconds
            if "jaeger_causal" in config["references"]:
                pred, seconds = oof_reference(lambda: JaegerModel(params, causal=True), queries, history, labels, folds)
                add_candidate("jaeger_causal_adapter", pred, seconds)
                reference_seconds["jaeger_causal_adapter"] = seconds
            reference_notes.append(
                "Frozen jaegers_entry/params.json is development-exposed from earlier public-validation work. "
                "This run did not open validation labels. jaeger_causal_adapter sets short-history lambda and prior "
                "equal to the long values and drops stacker column 13; it does not remove every champion as-of caveat."
            )
        except Exception as exc:
            champion_error = repr(exc)
            negative.append({"name": "jaeger_reference", "result": "failed", "reason": champion_error})

    by_name = {row["name"]: row for row in candidates}
    anchor_name = "frequency_default" if "frequency_default" in by_name else "type_prior_only"
    anchor = by_name[anchor_name]
    comparisons = [compare(row, anchor, int(config["bootstrap"]), seed) for row in candidates if row["name"] != anchor_name]
    if "jaeger_frozen_params" in by_name:
        for name in ("moe_static", "moe_regime_softmax", "markov_exact_lag1", "factorized_size", "logistic_full"):
            if name in by_name:
                comparisons.append(compare(by_name[name], by_name["jaeger_frozen_params"], int(config["bootstrap"]), seed))
    moe_vs_experts = []
    for name in moe_names:
        moe_vs_experts.append(compare(by_name["moe_static"], by_name[name], int(config["bootstrap"]), seed))

    inner_joined = np.vstack(inner_cubes) if inner_cubes else np.zeros((0, len(moe_names), 5))
    inner_y = np.concatenate(inner_labels) if inner_labels else np.zeros(0, dtype=int)
    outer_moe = primary[:, moe_columns]
    diversity = {
        "experts": moe_names,
        "outer_test_error_correlation": error_correlation(outer_moe, y),
        "inner_oof_error_correlation": error_correlation(inner_joined, inner_y) if len(inner_y) else None,
        "mean_static_weights": _mean_weight_record(gate_records, "static_weights", moe_names),
        "effective_static_experts": _effective_experts(_mean_weight_record(gate_records, "static_weights", moe_names)),
    }
    logistic_importance = group_importance(full_models, bundle["names"], compact_slices(full_groups, bundle))
    ranking = []
    for row in one_factor_sorted:
        ranking.append({
            "group": row["group"],
            "one_factor_delta_brier": row["delta_brier_vs_baseline"],
            "mean_abs_logistic_coefficient": logistic_importance.get(row["group"]),
            "mean_extra_trees_importance": tree_importance.get(row["group"]),
            "helps_sampled_brier": row["delta_brier_vs_baseline"] < 0,
        })
    for group in baseline_groups:
        ranking.append({
            "group": group,
            "one_factor_delta_brier": None,
            "mean_abs_logistic_coefficient": logistic_importance.get(group),
            "mean_extra_trees_importance": tree_importance.get(group),
            "helps_sampled_brier": None,
            "role": "included in the ablation baseline, so it has no one-factor delta",
        })

    best_name = min(candidates, key=lambda row: row["mean_brier"])["name"]
    peak = tracemalloc.get_traced_memory()[1]
    result = {
        "status": "MEASURED_NOT_PROMOTED",
        "evaluation_source": "sampled_outcome_group_cv",
        "official_points": None,
        "public_validation_peeks": 0,
        "validation_files_opened": False,
        "supervision": "one labeled row per train query; features and count experts use ticks < cutoff only",
        "signal_policy": "default matrix ignores signal; logistic_full_plus_own_query_signal uses that query's own signal and never copies it onto another tick",
        "machine_type_assumption": "machine_type is intrinsic static metadata",
        "fold_algorithm": "research.dataset.episode_folds, condition-stratified, digest order, index modulo fold_count",
        "fold_count": int(config["fold_count"]),
        "fold_manifest_sha256": digest(folds),
        "folds": folds,
        "n_queries": len(queries),
        "n_episodes": len(set(episodes)),
        "class_counts": [int(value) for value in np.bincount(y, minlength=5)],
        "leakage_controls": controls,
        "feature_coverage": coverage_facts(bundle["facts"]),
        "feature_ranking": ranking,
        "one_factor": one_factor_sorted,
        "pairwise": pair_rows,
        "sensitivities": sensitivities,
        "mixture": {
            "experts": moe_names,
            "gates": gate_records,
            "diversity": diversity,
            "vs_member_experts": moe_vs_experts,
            "static_mean_brier": static_summary["mean_brier"],
            "regime_softmax_mean_brier": regime_summary["mean_brier"],
            "regime_cells_mean_brier": cell_summary["mean_brier"],
            "calibrated_mean_brier": calibrated_summary["mean_brier"],
            "own_signal_delta_vs_logistic_full": signal_summary["mean_brier"] - full_summary["mean_brier"],
        },
        "comparisons_vs_anchor": comparisons,
        "anchor": anchor_name,
        "candidates": [_public_summary(row) for row in candidates],
        "best_observed_name": best_name,
        "best_observed_mean_brier": by_name[best_name]["mean_brier"],
        "negative_results": negative,
        "reference_notes": reference_notes,
        "reference_seconds": reference_seconds,
        "champion_error": champion_error,
        "logistic_convergence_warnings": {"baseline": base_warnings, "full": full_warnings, "elastic_net": elastic_warnings},
        "cited_prior_not_rerun": [
            {"study": "chat_runtime_screen", "point": "35 configurations, 13 families; jaeger mean Brier 0.361702, best non-jaeger stat_markov 0.417735, extra_trees 0.535957"},
            {"study": "HE-09", "point": "Dirichlet, decay BMA and Markov were not promoted; Markov was the strongest of the three"},
            {"study": "HE-15", "point": "stat_temporal_hmm sampled Brier 0.5544 and was not rerun; factorized size improved 20x calibration but stayed below the champion"},
        ],
        "wall_seconds": time.perf_counter() - started,
        "tracemalloc_peak_bytes": int(peak),
        "selection_note": "Primary hyperparameters are the protocol values. Grids and the top-three pairwise follow-up are sensitivity checks on the same folds, not a held-out confirmation and not a public-validation search.",
    }
    return json_ready(result)


def _mean_weight_record(records, key, names):
    if not records:
        return {name: None for name in names}
    return {name: float(np.mean([record[key][name] for record in records])) for name in names}


def _effective_experts(weights):
    values = np.array([value for value in weights.values() if value is not None], dtype=np.float64)
    if len(values) == 0 or np.sum(values ** 2) <= 0:
        return None
    return float(1.0 / np.sum(values ** 2))


def _public_summary(summary):
    keep = (
        "name", "evaluation_source", "official_points", "mean_brier", "by_condition", "log_loss",
        "class_brier", "class_counts", "class_20_mean_prediction", "class_20_observed_rate",
        "class_20_ece", "class_20_reliability", "per_episode", "episode_conditions", "fit_seconds",
        "fold_brier", "query_stratified_brier",
    )
    return {key: summary[key] for key in keep if key in summary}


def _reading(result):
    by_name = {row["name"]: row for row in result["candidates"]}
    lines = []
    champion = by_name.get("jaeger_frozen_params")
    factorized = by_name.get("factorized_size")
    if champion is not None:
        lines.append(
            "The frozen champion reference is included for comparison. Its parameter file already carries older public-validation exposure. This run did not open validation files."
        )
    if champion is not None and factorized is not None:
        lines.append(
            f"Point estimates: champion {champion['mean_brier']:.6f}, "
            f"factorized size {factorized['mean_brier']:.6f}, "
            f"static mixture {result['mixture']['static_mean_brier']:.6f}."
        )
    causal = by_name.get("jaeger_causal_adapter")
    if causal is not None:
        lines.append(f"Causal adapter mean Brier: {causal['mean_brier']:.6f}.")
    coverage = result.get("feature_coverage") or {}
    if coverage.get("fraction_short_history") == 0:
        lines.append(
            "No train query has fewer than 8 observed ticks, so the preregistered short-count regime bit does not fire on this split. "
            f"Mean observed ticks: {coverage.get('mean_observed_ticks')}. Exact lag 1 is known for fraction {coverage.get('fraction_lag1_known')}."
        )
    helped = [row["group"] for row in result["feature_ranking"] if row.get("helps_sampled_brier")]
    hurt = [row["group"] for row in result["feature_ranking"] if row.get("helps_sampled_brier") is False]
    lines.append(f"Logistic one-factor groups that reduced Brier: {helped or ['none']}. Groups that increased it: {hurt}.")
    versus_factorized = next((row for row in result["mixture"]["vs_member_experts"] if row["baseline"] == "factorized_size"), None)
    if versus_factorized is not None:
        lo, hi = versus_factorized["ci95"]
        lines.append(
            f"Static mixture minus factorized size: {versus_factorized['mean_delta_brier']:.6f} "
            f"with 95% interval [{lo:.6f}, {hi:.6f}]."
        )
    correlation = (result.get("mixture") or {}).get("diversity", {}).get("outer_test_error_correlation")
    if correlation and len(correlation) > 1:
        off_diagonal = [correlation[i][j] for i in range(len(correlation)) for j in range(i + 1, len(correlation))]
        lines.append(
            f"Outer-test pairwise error correlations among mixture members range from {min(off_diagonal):.3f} to {max(off_diagonal):.3f}."
        )
    static = by_name.get("moe_static")
    calibrated = by_name.get("moe_static_calibrated")
    if static is not None and calibrated is not None:
        lines.append(
            f"Calibrated static mixture Brier {calibrated['mean_brier']:.6f} versus uncalibrated {static['mean_brier']:.6f}; "
            f"20x ECE {calibrated['class_20_ece']:.4f} versus {static['class_20_ece']:.4f}."
        )
    grid = [row for row in result["sensitivities"] if row.get("family") == "dirichlet"]
    if grid:
        best = min(grid, key=lambda row: row["mean_brier"])
        lines.append(
            f"Dirichlet sensitivity minimum on these same folds is strength {best['strength']} and decay {best['decay']} "
            f"at Brier {best['mean_brier']:.6f}. That grid point was not the preregistered primary and is not a second test."
        )
    if result.get("fold_manifest_sha256") == "84f2aa3282c5dc8f394bdd06179f0adac2ec3865804dda99285d1b5c7e4ccc0e":
        lines.append("Fold manifest SHA-256 matches the published 35-configuration screen split.")
    warnings = result.get("logistic_convergence_warnings") or {}
    if warnings.get("elastic_net"):
        lines.append(
            f"Elastic-net fits emitted {warnings['elastic_net']} convergence warnings. Its score is a completed but unconverged trial."
        )
    lines.append(
        "The one-step exact-lag and last-observed Markov tables in this campaign are not the HE-09 multi-lag mixture."
    )
    return lines


def render_markdown(result):
    lines = [
        "# HE-87 feature, model-family and mixture results",
        "",
        "Status: MEASURED_NOT_PROMOTED. No champion was replaced and no organizer file was written.",
        "",
        "## Evaluation",
        "",
        f"- Source: sampled-outcome episode-grouped CV. Official points: none. Public-validation peeks: {result['public_validation_peeks']}.",
        f"- Folds: {result['fold_count']} via `{result['fold_algorithm']}`.",
        f"- Fold manifest SHA-256: `{result['fold_manifest_sha256']}`.",
        f"- Queries: {result['n_queries']}. Episodes: {result['n_episodes']}. Class counts [0,1,2,5,20]: {result['class_counts']}.",
        f"- Supervision: {result['supervision']}.",
        f"- Signal: {result['signal_policy']}.",
        f"- Wall seconds: {result['wall_seconds']:.3f}. Tracemalloc peak bytes: {result['tracemalloc_peak_bytes']}.",
        f"- {result['selection_note']}",
        "",
        "## Measured reading",
        "",
    ]
    lines.extend(f"- {line}" for line in _reading(result))
    lines.extend(["", "## Leakage controls", ""])
    for key, value in result["leakage_controls"].items():
        lines.append(f"- {key}: {value}")
    lines.extend(["", "## Candidates", "", "| Candidate | Mean Brier | Log loss | 20x predicted | 20x ECE | Fit seconds | Fold SD |", "|---|---:|---:|---:|---:|---:|---:|"])
    ordered = sorted(result["candidates"], key=lambda row: row["mean_brier"])
    for row in ordered:
        fold_values = list(row["fold_brier"].values())
        fold_sd = float(np.std(fold_values))
        lines.append(
            f"| {row['name']} | {row['mean_brier']:.6f} | {row['log_loss']:.6f} | {row['class_20_mean_prediction']:.4f} | {row['class_20_ece']:.4f} | {row['fit_seconds']:.3f} | {fold_sd:.6f} |"
        )
    lines.extend(["", f"Lowest observed mean Brier in this run: `{result['best_observed_name']}` at {result['best_observed_mean_brier']:.6f}.", "", "## Paired comparisons versus the anchor", "", f"Anchor: `{result['anchor']}`. Negative delta means the candidate has lower Brier.", "", "| Candidate | Delta Brier | 95% CI | Episodes better | Episodes worse | Supported improvement |", "|---|---:|---|---:|---:|---|"])
    for row in result["comparisons_vs_anchor"]:
        if row["baseline"] != result["anchor"]:
            continue
        lo, hi = row["ci95"]
        lines.append(
            f"| {row['candidate']} | {row['mean_delta_brier']:.6f} | [{lo:.6f}, {hi:.6f}] | {row['episodes_better']} | {row['episodes_worse']} | {row['supported_improvement']} |"
        )
    lines.extend(["", "## Feature ranking", "", "One-factor delta is added-group Brier minus type+exact-lag logistic Brier. Negative means the group helped. Baseline groups have no one-factor delta.", "", "| Group | One-factor delta | Mean abs logistic coef | ExtraTrees importance | Helps |", "|---|---:|---:|---:|---|"])
    for row in result["feature_ranking"]:
        delta = "" if row["one_factor_delta_brier"] is None else f"{row['one_factor_delta_brier']:.6f}"
        coef = "" if row["mean_abs_logistic_coefficient"] is None else f"{row['mean_abs_logistic_coefficient']:.6f}"
        trees = "" if row["mean_extra_trees_importance"] is None else f"{row['mean_extra_trees_importance']:.6f}"
        lines.append(f"| {row['group']} | {delta} | {coef} | {trees} | {row['helps_sampled_brier']} |")
    lines.extend(["", "## Pairwise follow-up", "", "Interaction beyond main effects is `B(base+a+b) - B(base) - (B(base+a)-B(base)) - (B(base+b)-B(base))`. Negative means the pair beat the sum of the one-factor gains.", ""])
    if not result["pairwise"]:
        lines.append("No pair was run.")
    for row in result["pairwise"]:
        lines.append(
            f"- {row['groups'][0]} + {row['groups'][1]}: Brier {row['mean_brier']:.6f}, delta {row['delta_brier_vs_baseline']:.6f}, interaction {row['interaction_beyond_main_effects']:.6f}."
        )
    lines.extend(["", "## Mixture of experts", "", f"- Members: {', '.join(result['mixture']['experts'])}.", f"- Static Brier {result['mixture']['static_mean_brier']:.6f}; regime softmax {result['mixture']['regime_softmax_mean_brier']:.6f}; regime cells {result['mixture']['regime_cells_mean_brier']:.6f}; calibrated static {result['mixture']['calibrated_mean_brier']:.6f}.", f"- Mean static weights: {result['mixture']['diversity']['mean_static_weights']}.", f"- Effective static experts (1/sum w^2): {result['mixture']['diversity']['effective_static_experts']}.", f"- Own-query-signal delta versus full logistic: {result['mixture']['own_signal_delta_vs_logistic_full']:.6f}.", "", "Outer-test error correlation of the mixture members:", ""])
    corr = result["mixture"]["diversity"]["outer_test_error_correlation"]
    if corr:
        lines.append("| | " + " | ".join(result["mixture"]["experts"]) + " |")
        lines.append("|---|" + "|".join(["---:" for _ in result["mixture"]["experts"]]) + "|")
        for name, row in zip(result["mixture"]["experts"], corr):
            lines.append("| " + name + " | " + " | ".join(f"{value:.3f}" for value in row) + " |")
    lines.extend(["", "## Condition-specific sampled Brier for the best observed row", ""])
    best = next(row for row in result["candidates"] if row["name"] == result["best_observed_name"])
    for condition, value in best["by_condition"].items():
        lines.append(f"- {condition}: {value:.6f}")
    if best.get("query_stratified_brier"):
        lines.extend(["", "Query-level strata for that same row:", ""])
        for key, value in best["query_stratified_brier"]["by_machine_type"].items():
            lines.append(f"- type {key}: {value:.6f}")
        for key, value in best["query_stratified_brier"]["by_history"].items():
            shown = "n/a" if value is None else f"{value:.6f}"
            lines.append(f"- history {key}: {shown}")
    lines.extend(["", "## Hyperparameter checks", ""])
    for row in result["sensitivities"]:
        shown = {key: value for key, value in row.items() if key in ("family", "C", "strength", "decay", "kappa", "tau", "mean_brier", "fit_seconds", "convergence_warnings", "class_20_ece")}
        lines.append(f"- {json.dumps(shown, sort_keys=True)}")
    lines.extend(["", "## Negative results kept", ""])
    for row in result["negative_results"]:
        lines.append(f"- {row['name']}: {row['reason']}")
    lines.extend(["", "## Prior studies cited, not rerun", ""])
    for row in result["cited_prior_not_rerun"]:
        lines.append(f"- {row['study']}: {row['point']}")
    if result.get("champion_error"):
        lines.extend(["", "## Champion reference error", "", f"`{result['champion_error']}`"])
    for note in result["reference_notes"]:
        lines.append(f"- Note: {note}")
    lines.extend([
        "",
        "## Commands",
        "",
        "From `Jaeger_Main/House_Edge`:",
        "",
        "```",
        "py -3.13 -m pytest tests/test_grok_he87_research.py -q",
        "py -3.13 -m research.challengers.grok_he87_experiment --config research/configs/grok_he87_protocol.json --out-dir research/reports",
        "```",
        "",
        "Resume without the frozen champion reference:",
        "",
        "```",
        "py -3.13 -m research.challengers.grok_he87_experiment --config research/configs/grok_he87_protocol.json --out-dir research/reports --skip-champion",
        "```",
        "",
    ])
    return "\n".join(lines) + "\n"


def write_reports(directory, result):
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    payload = json_ready(result)
    write_json(directory / "grok_he87_results.json", payload)
    (directory / "grok_he87_report.md").write_text(render_markdown(payload), encoding="utf-8")
    return payload


def load_public_train(data):
    folder = Path(data) / "train"
    queries, history = core_module().read_split(str(folder))
    labels = read_labels(folder)
    condition_map = read_conditions(folder)
    hashes = {name: file_hash(folder / name) for name in ("queries.csv", "history.csv", "labels.csv", "conditions.csv")}
    return queries, history, labels, condition_map, hashes


def main(argv=None):
    require_python()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, default=HOUSE / "public")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--skip-champion", action="store_true")
    args = parser.parse_args(argv)
    config = json.loads(Path(args.config).read_text(encoding="utf-8"))
    if args.skip_champion:
        config["references"] = [name for name in config["references"] if name not in ("jaeger", "jaeger_causal")]
    queries, history, labels, condition_map, data_hashes = load_public_train(args.data)
    result = run_campaign(queries, history, labels, condition_map, config)
    result["protocol_sha256"] = file_hash(args.config)
    result["data_sha256"] = data_hashes
    result["source_sha256"] = {
        "features": file_hash(HERE.with_name("grok_he87_features.py")),
        "models": file_hash(HERE.with_name("grok_he87_models.py")),
        "experiment": file_hash(HERE),
    }
    result["environment"] = environment()
    result["command"] = "py -3.13 -m research.challengers.grok_he87_experiment --config research/configs/grok_he87_protocol.json --out-dir research/reports"
    if args.skip_champion:
        result["command"] += " --skip-champion"
    write_reports(args.out_dir, result)
    print(json.dumps({
        "status": result["status"],
        "best_observed_name": result["best_observed_name"],
        "best_observed_mean_brier": result["best_observed_mean_brier"],
        "public_validation_peeks": result["public_validation_peeks"],
        "wall_seconds": result["wall_seconds"],
        "champion_error": result["champion_error"],
    }, sort_keys=True))


if __name__ == "__main__":
    main()
