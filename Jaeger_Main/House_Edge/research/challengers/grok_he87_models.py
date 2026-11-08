"""Count experts, linear/tree adapters, and out-of-fold mixtures for HE-87.

Fit tables use only the episodes passed to ``fit_experts``. Prediction reads ticks
strictly before each query cutoff. Hidden condition labels are not an input.
"""
from __future__ import annotations

import os

os.environ.setdefault("OMP_NUM_THREADS", "2")
os.environ.setdefault("OPENBLAS_NUM_THREADS", "2")
os.environ.setdefault("MKL_NUM_THREADS", "2")
os.environ.setdefault("NUMEXPR_NUM_THREADS", "2")

import numpy as np

from research.challengers.grok_he87_features import TYPES, past_until

EXPERT_ORDER = (
    "dirichlet_long",
    "dirichlet_short",
    "markov_exact_lag1",
    "markov_last_observed",
    "factorized_size",
    "peer_shrink",
    "drift_switch",
    "type_prior_only",
)


def project_simplex(vector):
    values = np.asarray(vector, dtype=np.float64)
    if values.ndim != 1:
        raise ValueError("Simplex projection expects a vector")
    ordered = np.sort(values)[::-1]
    cumulative = np.cumsum(ordered)
    ranks = np.arange(1, len(values) + 1)
    support = np.nonzero(ordered * ranks > (cumulative - 1))[0]
    rho = int(support[-1])
    theta = (cumulative[rho] - 1.0) / (rho + 1.0)
    projected = np.maximum(values - theta, 0.0)
    total = projected.sum()
    if total <= 0:
        return np.full(len(values), 1.0 / len(values))
    return projected / total


def _as_simplex(matrix):
    out = np.asarray(matrix, dtype=np.float64)
    out = np.clip(out, 0.0, None)
    totals = out.sum(axis=1, keepdims=True)
    if np.any(totals <= 0):
        raise ValueError("Probability row has no mass")
    return out / totals


def fit_static_weights(predictions, labels, steps=200, lr=0.08):
    """Minimize mean sampled Brier over a convex combination. ``predictions`` is (n, experts, 5)."""
    cube = np.asarray(predictions, dtype=np.float64)
    target = np.eye(5)[np.asarray(labels, dtype=int)]
    experts = cube.shape[1]
    weights = np.full(experts, 1.0 / experts)
    scale = max(len(labels), 1)
    for _ in range(int(steps)):
        mixture = np.einsum("e,nek->nk", weights, cube)
        residual = 2.0 * (mixture - target) / scale
        gradient = np.einsum("nek,nk->e", cube, residual)
        weights = project_simplex(weights - lr * gradient)
    return weights


def fit_softmax_gate(predictions, covariates, labels, steps=120, lr=0.4, l2=1e-3):
    cube = np.asarray(predictions, dtype=np.float64)
    raw = np.asarray(covariates, dtype=np.float64)
    mean = raw.mean(axis=0)
    std = raw.std(axis=0)
    std = np.where(std < 1e-6, 1.0, std)
    scaled = (raw - mean) / std
    target = np.eye(5)[np.asarray(labels, dtype=int)]
    experts = cube.shape[1]
    bias = np.zeros(experts)
    weights = np.zeros((scaled.shape[1], experts))
    scale = max(len(labels), 1)
    for _ in range(int(steps)):
        logits = bias + scaled @ weights
        logits -= logits.max(axis=1, keepdims=True)
        gate = np.exp(logits)
        gate /= gate.sum(axis=1, keepdims=True)
        mixture = np.einsum("ne,nek->nk", gate, cube)
        residual = 2.0 * (mixture - target) / scale
        mixture_grad = np.einsum("nek,nk->ne", cube, residual)
        dotted = np.sum(gate * mixture_grad, axis=1, keepdims=True)
        logit_grad = gate * (mixture_grad - dotted)
        bias -= lr * logit_grad.sum(axis=0)
        weights -= lr * (scaled.T @ logit_grad + l2 * weights)
    return {"bias": bias, "weights": weights, "mean": mean, "std": std}


def apply_softmax_gate(predictions, covariates, gate):
    cube = np.asarray(predictions, dtype=np.float64)
    scaled = (np.asarray(covariates, dtype=np.float64) - gate["mean"]) / gate["std"]
    logits = gate["bias"] + scaled @ gate["weights"]
    logits -= logits.max(axis=1, keepdims=True)
    mixing = np.exp(logits)
    mixing /= mixing.sum(axis=1, keepdims=True)
    mixture = np.einsum("ne,nek->nk", mixing, cube)
    return _as_simplex(mixture), mixing


def fit_cell_gate(predictions, hard, labels, static_weights, min_count):
    cube = np.asarray(predictions, dtype=np.float64)
    target = np.eye(5)[np.asarray(labels, dtype=int)]
    losses = np.sum((cube - target[:, None, :]) ** 2, axis=2)
    ids = cell_ids(hard)
    choices = {}
    for cell in range(16):
        mask = ids == cell
        count = int(mask.sum())
        if count < int(min_count):
            choices[str(cell)] = {"mode": "static", "n": count}
            continue
        means = losses[mask].mean(axis=0)
        choices[str(cell)] = {
            "mode": "expert",
            "expert": int(np.argmin(means)),
            "n": count,
            "mean_brier": [float(value) for value in means],
        }
    return {"choices": choices, "static_weights": np.asarray(static_weights, dtype=np.float64), "min_count": int(min_count)}


def apply_cell_gate(predictions, hard, cell_gate):
    cube = np.asarray(predictions, dtype=np.float64)
    ids = cell_ids(hard)
    mixed = np.einsum("e,nek->nk", cell_gate["static_weights"], cube)
    for row, cell in enumerate(ids):
        choice = cell_gate["choices"][str(int(cell))]
        if choice["mode"] == "expert":
            mixed[row] = cube[row, choice["expert"]]
    return _as_simplex(mixed)


def cell_ids(hard):
    bits = np.asarray(hard, dtype=np.int64)
    return bits[:, 0] + 2 * bits[:, 1] + 4 * bits[:, 2] + 8 * bits[:, 3]


def apply_temperature_bias(probabilities, temperature, bias20):
    logits = np.log(np.clip(probabilities, 1e-12, 1.0)) / float(temperature)
    logits = np.array(logits, copy=True)
    logits[:, 4] += float(bias20)
    logits -= logits.max(axis=1, keepdims=True)
    scaled = np.exp(logits)
    return _as_simplex(scaled)


def fit_temperature_bias(probabilities, labels):
    target = np.eye(5)[np.asarray(labels, dtype=int)]
    best = {"temperature": 1.0, "bias20": 0.0, "mean_brier": None}
    for temperature in (0.75, 1.0, 1.25, 1.5, 2.0, 3.0):
        for bias20 in (-0.75, -0.25, 0.0, 0.25, 0.75):
            mixed = apply_temperature_bias(probabilities, temperature, bias20)
            score = float(np.mean(np.sum((mixed - target) ** 2, axis=1)))
            if best["mean_brier"] is None or score < best["mean_brier"]:
                best = {"temperature": temperature, "bias20": bias20, "mean_brier": score}
    return best


def _normalize(counts):
    counts = np.asarray(counts, dtype=np.float64)
    total = counts.sum()
    if total <= 0:
        return np.full(5, 0.2)
    return counts / total


def fit_experts(queries, labels, index):
    priors = {machine_type: np.ones(5, dtype=np.float64) for machine_type in TYPES}
    exact = {machine_type: np.zeros((6, 5), dtype=np.float64) for machine_type in TYPES}
    last = {machine_type: np.zeros((6, 5), dtype=np.float64) for machine_type in TYPES}
    for query in queries:
        machine_type = query["machine_type"]
        cutoff = int(query["cutoff"])
        ticks, observed = past_until(*index["series"][(query["episode_id"], query["machine_id"])], cutoff)
        if len(observed):
            priors[machine_type] += np.bincount(observed, minlength=5)
        lookup = {int(tick): int(label) for tick, label in zip(ticks, observed)}
        for tick, label in lookup.items():
            context = lookup.get(tick - 1, 5)
            exact[machine_type][context, label] += 1.0
        if len(observed) == 0:
            last[machine_type][5, labels[query["query_id"]]] += 1.0
        else:
            for nxt, label in enumerate(observed[1:], start=1):
                last[machine_type][int(observed[nxt - 1]), int(label)] += 1.0
            last[machine_type][int(observed[-1]), labels[query["query_id"]]] += 1.0
        exact_context = lookup.get(cutoff - 1, 5)
        exact[machine_type][exact_context, labels[query["query_id"]]] += 1.0
    return {
        "prior": {key: _normalize(value) for key, value in priors.items()},
        "exact": exact,
        "last": last,
    }


def _dirichlet(prior, ticks, labels, cutoff, strength, decay, window):
    counts = float(strength) * prior
    if len(labels) == 0:
        return _normalize(counts)
    chosen_ticks, chosen = ticks, labels
    if window is not None:
        mask = ticks >= int(cutoff) - int(window)
        chosen_ticks, chosen = ticks[mask], labels[mask]
    if len(chosen) == 0:
        return _normalize(counts)
    if decay is None or float(decay) == 1.0:
        counts = counts + np.bincount(chosen, minlength=5)
    else:
        weights = np.power(float(decay), (int(cutoff) - 1 - chosen_ticks).astype(np.float64))
        counts = counts + np.bincount(chosen, weights=weights, minlength=5)
    return _normalize(counts)


def _markov(table, prior, context, alpha):
    counts = table[int(context)] + float(alpha) * prior
    return _normalize(counts)


def _factorized(prior, ticks, labels, cutoff, strength, decay):
    discounted = _dirichlet(prior, ticks, labels, cutoff, strength, decay, None)
    # Convert the smoothed class distribution back to a zero-vs-size factorization
    # by rebuilding counts from the same weights.
    counts = float(strength) * prior
    if len(labels):
        weights = np.power(float(decay), (int(cutoff) - 1 - ticks).astype(np.float64))
        counts = counts + np.bincount(labels, weights=weights, minlength=5)
    p0 = counts[0] / counts.sum()
    size = counts[1:] / counts[1:].sum()
    out = np.zeros(5, dtype=np.float64)
    out[0] = p0
    out[1:] = (1.0 - p0) * size
    if not np.isfinite(out).all():
        return discounted
    return _normalize(out)


def predict_experts(queries, index, state, settings):
    """Return (n, experts, 5) in EXPERT_ORDER."""
    rows = []
    for query in queries:
        cutoff = int(query["cutoff"])
        machine_type = query["machine_type"]
        prior = state["prior"][machine_type]
        ticks, labels = past_until(*index["series"][(query["episode_id"], query["machine_id"])], cutoff)
        long = _dirichlet(prior, ticks, labels, cutoff, settings["dirichlet_strength"], settings["dirichlet_decay"], None)
        short = _dirichlet(prior, ticks, labels, cutoff, settings["short_strength"], 1.0, settings["short_window"])
        lookup = {int(tick): int(label) for tick, label in zip(ticks, labels)}
        exact_context = lookup.get(cutoff - 1, 5)
        last_context = 5 if len(labels) == 0 else int(labels[-1])
        exact = _markov(state["exact"][machine_type], prior, exact_context, settings["markov_alpha"])
        last = _markov(state["last"][machine_type], prior, last_context, settings["markov_alpha"])
        factorized = _factorized(prior, ticks, labels, cutoff, settings["factorized_strength"], settings["factorized_decay"])
        peer_total = np.zeros(5, dtype=np.float64)
        for other in index["by_episode"].get(query["episode_id"], []):
            if other == query["machine_id"]:
                continue
            _, peer_labels = past_until(*index["series"][(query["episode_id"], other)], cutoff)
            if len(peer_labels):
                peer_total += np.bincount(peer_labels, minlength=5)
        peer = _normalize(peer_total + settings["dirichlet_strength"] * prior)
        n_own = float(len(labels))
        kappa = float(settings["peer_kappa"])
        own_weight = n_own / (n_own + kappa)
        peer_mix = _normalize(own_weight * long + (1.0 - own_weight) * peer)
        distance = float(np.abs(short - long).sum())
        drift = short if distance > float(settings["drift_tau"]) else long
        rows.append(np.vstack([long, short, exact, last, factorized, peer_mix, drift, prior]))
    cube = np.stack(rows) if rows else np.zeros((0, len(EXPERT_ORDER), 5))
    return _as_simplex(cube.reshape(-1, 5)).reshape(cube.shape)


def predict_dirichlet_grid(queries, index, state, strength, decay):
    rows = []
    for query in queries:
        cutoff = int(query["cutoff"])
        prior = state["prior"][query["machine_type"]]
        ticks, labels = past_until(*index["series"][(query["episode_id"], query["machine_id"])], cutoff)
        rows.append(_dirichlet(prior, ticks, labels, cutoff, strength, decay, None))
    return _as_simplex(np.vstack(rows) if rows else np.zeros((0, 5)))


def predict_peer_kappa(queries, index, state, settings, kappa):
    local = dict(settings, peer_kappa=kappa)
    cube = predict_experts(queries, index, state, local)
    return cube[:, EXPERT_ORDER.index("peer_shrink")]


def predict_drift_tau(queries, index, state, settings, tau):
    local = dict(settings, drift_tau=tau)
    cube = predict_experts(queries, index, state, local)
    return cube[:, EXPERT_ORDER.index("drift_switch")]


def aligned_proba(model, features):
    probabilities = model.predict_proba(features)
    classes = np.asarray(model.classes_, dtype=int)
    full = np.zeros((len(features), 5), dtype=np.float64)
    full[:, classes] = probabilities
    return _as_simplex(full)


def make_logistic(C, seed, elastic=False, max_iter=400):
    from sklearn.linear_model import LogisticRegression
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import StandardScaler

    if elastic:
        classifier = LogisticRegression(
            C=C, l1_ratio=0.5, solver="saga", max_iter=max_iter, random_state=seed,
        )
    else:
        classifier = LogisticRegression(
            C=C, solver="lbfgs", max_iter=max_iter, random_state=seed,
        )
    return make_pipeline(StandardScaler(), classifier)


def make_extra_trees(trees, depth, leaf, seed):
    from sklearn.ensemble import ExtraTreesClassifier

    return ExtraTreesClassifier(
        n_estimators=int(trees), max_depth=None if depth is None else int(depth),
        min_samples_leaf=int(leaf), max_features=0.7, n_jobs=1, random_state=seed,
    )


def make_hist_boost(iters, lr, leaves, l2, seed):
    from sklearn.ensemble import HistGradientBoostingClassifier

    return HistGradientBoostingClassifier(
        max_iter=int(iters), learning_rate=float(lr), max_leaf_nodes=int(leaves),
        l2_regularization=float(l2), early_stopping=False, random_state=seed,
    )


def error_correlation(predictions, labels):
    cube = np.asarray(predictions, dtype=np.float64)
    target = np.eye(5)[np.asarray(labels, dtype=int)]
    losses = np.sum((cube - target[:, None, :]) ** 2, axis=2)
    if len(labels) < 3:
        return None
    corr = np.corrcoef(losses, rowvar=False)
    return [[float(value) for value in row] for row in corr]
