"""Lawful as-of feature blocks for the HE-87 campaign.

Every payout lookup uses ticks strictly less than the row cutoff. A missing tick is
unknown, never an observed zero. Query signal is not read by the default matrix.
Machine type is treated as intrinsic static metadata.
"""
from __future__ import annotations

import numpy as np

PAYOUT_TO_CLASS = {0: 0, 1: 1, 2: 2, 5: 3, 20: 4}
TYPES = ("steady", "balanced", "jackpot")
GROUP_ORDER = (
    "type",
    "exact_lags",
    "sparse",
    "discounted",
    "sibling",
    "transitions",
    "entropy",
    "changepoint",
    "win_size",
    "rarity20",
    "interactions",
)
DECAYS = (0.9, 0.97, 0.995)
DEFAULT_THRESHOLDS = {
    "short_n": 8,
    "sparse_coverage": 0.5,
    "volatile_l1": 0.3,
    "shared_l1": 0.3,
}


def build_index(history):
    series = {}
    by_episode = {}
    for (episode, machine), rows in history.items():
        ordered = sorted((int(tick), int(payout)) for tick, payout in rows.items())
        ticks = np.array([tick for tick, _ in ordered], dtype=np.int64)
        labels = np.array([PAYOUT_TO_CLASS[payout] for _, payout in ordered], dtype=np.int8)
        series[(episode, machine)] = (ticks, labels)
        by_episode.setdefault(episode, []).append(machine)
    return {"series": series, "by_episode": by_episode}


def past_until(ticks, labels, cutoff):
    stop = int(np.searchsorted(ticks, int(cutoff), side="left"))
    return ticks[:stop], labels[:stop]


def _lookup(ticks, labels):
    return {int(tick): int(label) for tick, label in zip(ticks, labels)}


def _freq(labels, weights=None):
    if weights is None:
        counts = np.bincount(labels, minlength=5).astype(np.float64) if len(labels) else np.zeros(5)
    else:
        counts = np.bincount(labels, weights=weights, minlength=5).astype(np.float64) if len(labels) else np.zeros(5)
    return (counts + 0.5) / (counts.sum() + 2.5), counts


def _entropy(probs):
    clipped = np.clip(probs, 1e-12, 1.0)
    return float(-np.sum(clipped * np.log(clipped)))


def _discounted(ticks, labels, cutoff, decay):
    if len(labels) == 0:
        return np.full(5, 0.2), 0.0, np.zeros(5)
    weights = np.power(decay, (int(cutoff) - 1 - ticks).astype(np.float64))
    freq, counts = _freq(labels, weights)
    return freq, float(weights.sum()), counts


def _window(ticks, labels, cutoff, start, end=None):
    lo = int(cutoff) - int(start)
    hi = int(cutoff) if end is None else int(cutoff) - int(end)
    mask = (ticks >= lo) & (ticks < hi)
    return labels[mask]


def _time_since(ticks, labels, cutoff, mask):
    hits = ticks[mask]
    if len(hits) == 0:
        return float(cutoff)
    return float(int(cutoff) - int(hits[-1]))


def _peer_counts(index, episode, machine, cutoff):
    total = np.zeros(5, dtype=np.float64)
    recent = np.zeros(5, dtype=np.float64)
    machines = 0
    for other in index["by_episode"].get(episode, []):
        if other == machine:
            continue
        ticks, labels = past_until(*index["series"][(episode, other)], cutoff)
        if len(labels) == 0:
            continue
        machines += 1
        total += np.bincount(labels, minlength=5)
        recent_labels = labels[ticks >= int(cutoff) - 24]
        if len(recent_labels):
            recent += np.bincount(recent_labels, minlength=5)
    return total, recent, machines


def row_parts(query, index, thresholds=None):
    """Return feature blocks, regime covariates, and coverage facts for one query."""
    thresholds = dict(DEFAULT_THRESHOLDS if thresholds is None else thresholds)
    cutoff = int(query["cutoff"])
    episode, machine = query["episode_id"], query["machine_id"]
    ticks, labels = past_until(*index["series"][(episode, machine)], cutoff)
    known = _lookup(ticks, labels)
    type_index = TYPES.index(query["machine_type"])
    n_obs = int(len(labels))
    parts = {}
    names = {}

    type_vec = np.eye(3, dtype=np.float64)[type_index]
    parts["type"] = type_vec
    names["type"] = [f"type/{name}" for name in TYPES]

    lag_values = []
    lag_names = []
    lag_known = []
    for lag in range(1, 9):
        observed = known.get(cutoff - lag)
        one = np.zeros(5, dtype=np.float64)
        missing = 1.0
        if observed is not None:
            one[observed] = 1.0
            missing = 0.0
        lag_values.append(one)
        lag_values.append(np.array([missing], dtype=np.float64))
        lag_names.extend([f"exact_lags/lag{lag}_c{cls}" for cls in range(5)])
        lag_names.append(f"exact_lags/lag{lag}_missing")
        lag_known.append(missing == 0.0)
    parts["exact_lags"] = np.concatenate(lag_values)
    names["exact_lags"] = lag_names

    gap = float(cutoff if n_obs == 0 else cutoff - int(ticks[-1]))
    coverage = n_obs / max(cutoff, 1)
    sparse = np.concatenate([
        np.array([coverage, np.log1p(n_obs), gap], dtype=np.float64),
        np.array(lag_known, dtype=np.float64),
    ])
    parts["sparse"] = sparse
    names["sparse"] = ["sparse/coverage", "sparse/log_count", "sparse/gap"] + [f"sparse/lag{lag}_known" for lag in range(1, 9)]

    discounted = []
    discounted_names = []
    decay_cache = {}
    for decay in DECAYS:
        freq, mass, counts = _discounted(ticks, labels, cutoff, decay)
        decay_cache[decay] = (freq, mass, counts)
        discounted.append(freq)
        discounted.append(np.array([np.log1p(mass)], dtype=np.float64))
        tag = str(decay).replace(".", "")
        discounted_names.extend([f"discounted/d{tag}_c{cls}" for cls in range(5)])
        discounted_names.append(f"discounted/d{tag}_logmass")
    parts["discounted"] = np.concatenate(discounted)
    names["discounted"] = discounted_names

    peer_total, peer_recent, peer_machines = _peer_counts(index, episode, machine, cutoff)
    peer_freq = (peer_total + 0.5) / (peer_total.sum() + 2.5)
    peer_recent_freq = (peer_recent + 0.5) / (peer_recent.sum() + 2.5)
    sibling = np.concatenate([
        peer_freq,
        peer_recent_freq,
        np.array([np.log1p(peer_total.sum()), np.log1p(peer_machines)], dtype=np.float64),
    ])
    parts["sibling"] = sibling
    names["sibling"] = (
        [f"sibling/all_c{cls}" for cls in range(5)]
        + [f"sibling/recent_c{cls}" for cls in range(5)]
        + ["sibling/log_mass", "sibling/log_machines"]
    )

    last_class = None if n_obs == 0 else int(labels[-1])
    last_one = np.zeros(6, dtype=np.float64)
    last_one[5 if last_class is None else last_class] = 1.0
    if last_class is None or n_obs < 2:
        conditional = np.full(5, 0.2)
        transition_count = 0
    else:
        previous = labels[:-1]
        nxt = labels[1:]
        chosen = nxt[previous == last_class]
        conditional, conditional_counts = _freq(chosen)
        transition_count = int(len(chosen))
    parts["transitions"] = np.concatenate([last_one, conditional, np.array([np.log1p(transition_count)])])
    names["transitions"] = (
        [f"transitions/last_c{cls}" for cls in range(5)]
        + ["transitions/last_missing", *[f"transitions/cond_c{cls}" for cls in range(5)], "transitions/log_count"]
    )

    own = decay_cache[0.97][0]
    peer_l1 = float(np.abs(own - peer_freq).sum())
    parts["entropy"] = np.array([_entropy(own), _entropy(peer_freq), peer_l1], dtype=np.float64)
    names["entropy"] = ["entropy/own", "entropy/peer", "entropy/l1_disagreement"]

    recent = _window(ticks, labels, cutoff, 24)
    earlier = _window(ticks, labels, cutoff, 64, 24)
    recent_freq, _ = _freq(recent)
    earlier_freq, _ = _freq(earlier)
    delta = recent_freq - earlier_freq
    long_freq = decay_cache[0.995][0]
    own_l1 = float(np.abs(recent_freq - long_freq).sum())
    parts["changepoint"] = np.concatenate([delta, np.array([np.abs(delta).sum(), _entropy(recent_freq)])])
    names["changepoint"] = [f"changepoint/delta_c{cls}" for cls in range(5)] + ["changepoint/l1", "changepoint/recent_entropy"]

    raw_counts = np.bincount(labels, minlength=5).astype(np.float64) if n_obs else np.zeros(5)
    positive = float(raw_counts[1:].sum())
    p_positive = positive / max(n_obs, 1)
    size = (raw_counts[1:] + 0.5) / (raw_counts[1:].sum() + 2.0)
    since_positive = _time_since(ticks, labels, cutoff, labels > 0) if n_obs else float(cutoff)
    parts["win_size"] = np.concatenate([
        np.array([p_positive, np.log1p(since_positive)], dtype=np.float64),
        size,
    ])
    names["win_size"] = ["win_size/p_positive", "win_size/log_time_since_positive"] + [f"win_size/size_c{cls}" for cls in range(1, 5)]

    since_20 = _time_since(ticks, labels, cutoff, labels == 4) if n_obs else float(cutoff)
    last_is_20 = 1.0 if last_class == 4 else 0.0
    parts["rarity20"] = np.array([np.log1p(since_20), last_is_20, np.log1p(raw_counts[4])], dtype=np.float64)
    names["rarity20"] = ["rarity20/log_time_since", "rarity20/last_is_20", "rarity20/log_count"]

    p20 = float(own[4])
    interactions = np.concatenate([
        type_vec * p_positive,
        type_vec * p20,
        np.array([float(lag_known[0]) * p20], dtype=np.float64),
    ])
    parts["interactions"] = interactions
    names["interactions"] = (
        [f"interactions/type_ppos_{name}" for name in TYPES]
        + [f"interactions/type_p20_{name}" for name in TYPES]
        + ["interactions/lag1_known_p20"]
    )

    signal = np.eye(3, dtype=np.float64)[int(query["signal"]) + 1]
    regime_z = np.array([np.log1p(n_obs), coverage, own_l1, peer_l1], dtype=np.float64)
    regime_hard = np.array([
        float(n_obs < int(thresholds["short_n"])),
        float(coverage < float(thresholds["sparse_coverage"])),
        float(own_l1 > float(thresholds["volatile_l1"])),
        float(peer_l1 > float(thresholds["shared_l1"])),
    ], dtype=np.float64)
    facts = {
        "n_obs": n_obs,
        "lag1_known": bool(lag_known[0]),
        "peer_mass": float(peer_total.sum()),
        "seen_20": bool(raw_counts[4] > 0),
        "machine_type": query["machine_type"],
    }
    return parts, names, signal, regime_z, regime_hard, facts


def build_bundle(queries, history, groups=GROUP_ORDER, thresholds=None, index=None):
    index = build_index(history) if index is None else index
    selected = tuple(groups)
    unknown = set(selected) - set(GROUP_ORDER)
    if unknown or len(selected) != len(set(selected)):
        raise ValueError(f"Unknown or duplicate feature groups: {sorted(unknown)}")
    rows, signals, zs, hards = [], [], [], []
    facts = []
    names = None
    slices = {}
    for query in queries:
        parts, part_names, signal, regime_z, regime_hard, fact = row_parts(query, index, thresholds)
        if names is None:
            cursor = 0
            assembled = []
            for group in selected:
                width = len(part_names[group])
                slices[group] = list(range(cursor, cursor + width))
                assembled.extend(part_names[group])
                cursor += width
            names = assembled
        rows.append(np.concatenate([parts[group] for group in selected]))
        signals.append(signal)
        zs.append(regime_z)
        hards.append(regime_hard)
        facts.append(fact)
    matrix = np.vstack(rows).astype(np.float64) if rows else np.zeros((0, 0))
    return {
        "X": matrix,
        "names": names or [],
        "slices": slices,
        "signal": np.vstack(signals) if signals else np.zeros((0, 3)),
        "regime_z": np.vstack(zs) if zs else np.zeros((0, 4)),
        "regime_hard": np.vstack(hards) if hards else np.zeros((0, 4)),
        "facts": facts,
        "index": index,
        "groups": selected,
    }


def columns_for(bundle, groups):
    indexes = []
    for group in groups:
        indexes.extend(bundle["slices"][group])
    return np.array(indexes, dtype=int)


def leakage_controls(queries, history, thresholds=None):
    """Metamorphic checks. They do not use labels."""
    index = build_index(history)
    base = build_bundle(queries, history, index=index, thresholds=thresholds)
    flipped = [dict(query, signal="1" if str(query["signal"]) != "1" else "-1") for query in queries]
    flipped_bundle = build_bundle(flipped, history, index=index, thresholds=thresholds)
    signal_inert = bool(np.array_equal(base["X"], flipped_bundle["X"]))

    future = {key: dict(rows) for key, rows in history.items()}
    probe = queries[0]
    probe_key = (probe["episode_id"], probe["machine_id"])
    future[probe_key][int(probe["cutoff"])] = 20
    future[probe_key][int(probe["cutoff"]) + 3] = 0
    future_bundle = build_bundle(queries, future, thresholds=thresholds)
    future_inert = bool(np.array_equal(base["X"][0], future_bundle["X"][0]))

    peer = {key: dict(rows) for key, rows in history.items()}
    others = [machine for machine in index["by_episode"][probe["episode_id"]] if machine != probe["machine_id"]]
    peer_excluded = True
    if others:
        peer[(probe["episode_id"], others[0])][int(probe["cutoff"])] = 20
        peer_bundle = build_bundle([probe], peer, thresholds=thresholds)
        probe_bundle = build_bundle([probe], history, index=index, thresholds=thresholds)
        peer_excluded = bool(np.array_equal(probe_bundle["X"][0], peer_bundle["X"][0]))

    other_episode = next(query for query in queries if query["episode_id"] != probe["episode_id"])
    cross = {key: dict(rows) for key, rows in history.items()}
    cross_key = (other_episode["episode_id"], other_episode["machine_id"])
    cross[cross_key][0] = 0 if cross[cross_key].get(0, 1) != 0 else 20
    cross_bundle = build_bundle([probe], cross, thresholds=thresholds)
    probe_only = build_bundle([probe], history, index=index, thresholds=thresholds)
    episode_isolated = bool(np.array_equal(probe_only["X"][0], cross_bundle["X"][0]))
    return {
        "signal_inert": signal_inert,
        "future_tick_inert": future_inert,
        "peer_cutoff_excluded": peer_excluded,
        "other_episode_inert": episode_isolated,
        "signal_block_changes_when_requested": not np.array_equal(base["signal"], flipped_bundle["signal"]),
    }
