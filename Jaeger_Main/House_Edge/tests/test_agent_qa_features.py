"""HE-07 (lane C): as-of contract tests for the shared feature registry and the qa_size_streak extension.

Run from Jaeger_Main/House_Edge:
    python -m pytest tests/test_agent_qa_features.py -q

Read-only use of lane A's research/features.py and research/dataset.py. Historical-origin tests run on
REAL train histories (sparse short histories included), not only synthetic fixtures.
"""
from __future__ import annotations

import csv
import importlib
import json
import random
import shutil
import sys
from collections import defaultdict
from copy import deepcopy
from pathlib import Path

import numpy as np
import pytest

HE = Path(__file__).resolve().parents[1]
if str(HE) not in sys.path:
    sys.path.insert(0, str(HE))

PUB = HE / "public"
PAYOUTS = (0, 1, 2, 5, 20)


def shared(name):
    try:
        return importlib.import_module(f"research.{name}")
    except ImportError as exc:  # pragma: no cover - lane A rename in flight
        pytest.skip(f"research.{name} unavailable at this HEAD ({exc}); re-point after lane A's rename")


def rows(path):
    with open(path, newline="") as f:
        return list(csv.DictReader(f))


def load(split="train"):
    queries = rows(PUB / split / "queries.csv")
    history = defaultdict(dict)
    for r in rows(PUB / split / "history.csv"):
        history[(r["episode_id"], r["machine_id"])][int(r["tick"])] = int(r["payout"])
    return queries, history


TRAIN_Q, TRAIN_H = load("train")


def origins(n=40, seed=0):
    """(query-with-cutoff=t, t) for random observed historical ticks t of random train machines."""
    rng = random.Random(seed)
    picks = []
    for q in rng.sample(TRAIN_Q, n):
        ticks = sorted(t for t in TRAIN_H[(q["episode_id"], q["machine_id"])] if t < int(q["cutoff"]))
        t = rng.choice(ticks[20:])
        picks.append((dict(q, cutoff=str(t)), t))
    return picks


def scramble_from(history, episode, t, rng):
    """Rewrite every payout at ticks >= t for ALL machines of the episode, and add new future ticks."""
    h = deepcopy(history)
    for (ep, m), r in h.items():
        if ep != episode:
            continue
        for tick in list(r):
            if tick >= t:
                r[tick] = rng.choice(PAYOUTS)
        for tick in range(t, t + 12):
            r.setdefault(tick, rng.choice(PAYOUTS))
    return h


# --------------------------------------------------------------------------- registry: historical-origin as-of

def test_registry_rows_ignore_target_and_sibling_ticks_at_or_after_origin():
    features = shared("features")
    rng = random.Random(1)
    base = features.FeatureComputer(TRAIN_H)
    for q, t in origins():
        before, names = base.row(q, features.HISTORICAL_GROUPS)
        after, names2 = features.FeatureComputer(scramble_from(TRAIN_H, q["episode_id"], t, rng)).row(q, features.HISTORICAL_GROUPS)
        assert names == names2
        np.testing.assert_array_equal(before, after, err_msg=f"{q['query_id']} origin {t}")


def test_registry_rows_change_when_an_earlier_sibling_tick_changes():
    """Positive control: the sibling channel is live before t, so the test above is not vacuous."""
    features = shared("features")
    q, t = origins(1, seed=3)[0]
    sib = next(k for k in TRAIN_H if k[0] == q["episode_id"] and k[1] != q["machine_id"] and (t - 1) in TRAIN_H[k])
    h = deepcopy(TRAIN_H); h[sib][t - 1] = 20 if h[sib][t - 1] == 0 else 0
    a = features.FeatureComputer(TRAIN_H).row(q, ("peers",))[0]
    b = features.FeatureComputer(h).row(q, ("peers",))[0]
    assert np.abs(a - b).max() > 0


def test_registry_exact_lag_missing_mask_on_real_sparse_histories():
    features = shared("features")
    comp = features.FeatureComputer(TRAIN_H)
    checked_missing = 0
    for q, t in origins(80, seed=5):
        values, names = comp.row(q, ("lags", "missingness"))
        named = dict(zip(names, values))
        r = TRAIN_H[(q["episode_id"], q["machine_id"])]
        for k in range(1, 9):
            known = (t - k) in r
            assert named[f"missingness/lag_known_{k-1}"] == float(known)
            assert named[f"lags/lag{k}_0"] == float(not known), "slot 0 must mean 'missing', never payout 0"
            if known:
                assert named[f"lags/lag{k}_{PAYOUTS.index(r[t-k]) + 1}"] == 1.0
            checked_missing += not known
    assert checked_missing > 0, "sample contained no missing exact lags; pick other origins"


def test_registry_current_signal_is_query_only():
    features = shared("features")
    with pytest.raises(ValueError):
        features.validate_groups(("lags", "current_signal"), historical=True)
    q = TRAIN_Q[0]
    comp = features.FeatureComputer(TRAIN_H)
    groups = ("lags", "current_signal")
    a, names = comp.row(dict(q, signal="-1"), groups)
    b, _ = comp.row(dict(q, signal="1"), groups)
    diff = {n for n, x, y in zip(names, a, b) if x != y}
    assert diff and all(n.startswith("current_signal/") for n in diff)
    assert "current_signal" not in features.HISTORICAL_GROUPS


# --------------------------------------------------------------------------- registry: group toggles

def test_group_toggle_selects_exact_columns():
    features = shared("features")
    comp = features.FeatureComputer(TRAIN_H)
    values, names = comp.row(TRAIN_Q[0], features.HISTORICAL_GROUPS)
    all_cols = set(range(len(names)))
    for g in features.HISTORICAL_GROUPS:
        deps = set(features.REGISTRY[g].dependencies)
        on = tuple(sorted(deps | {g}))
        cols = set(features.feature_columns(names, on).tolist())
        assert cols and all(names[i].split("/")[0] in on for i in cols)
        assert cols == {i for i in all_cols if names[i].split("/")[0] in on}
        if not any(g in features.REGISTRY[o].dependencies for o in features.HISTORICAL_GROUPS):
            rest = tuple(x for x in features.HISTORICAL_GROUPS if x != g)
            off = set(features.feature_columns(names, rest).tolist())
            assert off == all_cols - {i for i in all_cols if names[i].startswith(g + "/")}


def test_group_dependencies_enforced():
    features = shared("features")
    with pytest.raises(ValueError):
        features.validate_groups(("pairs",))
    with pytest.raises(ValueError):
        features.validate_groups(("lags", "lags"))
    with pytest.raises(ValueError):
        features.validate_groups(("not_a_group",))


# --------------------------------------------------------------------------- dataset cache identity

def _tiny_round(root, episodes=3):
    keep = sorted({q["episode_id"] for q in TRAIN_Q})[:episodes]
    (root / "train").mkdir(parents=True)
    for name in ("queries.csv", "history.csv"):
        r = [x for x in rows(PUB / "train" / name) if x["episode_id"] in keep]
        with open(root / "train" / name, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=r[0].keys()); w.writeheader(); w.writerows(r)
    ids = {q["query_id"] for q in TRAIN_Q if q["episode_id"] in keep}
    lab = [x for x in rows(PUB / "train" / "labels.csv") if x["query_id"] in ids]
    with open(root / "train" / "labels.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=lab[0].keys()); w.writeheader(); w.writerows(lab)
    return root


def test_cache_key_tracks_inputs_source_and_settings(tmp_path, monkeypatch):
    dataset = shared("dataset")
    data = _tiny_round(tmp_path / "data")
    cache = tmp_path / "cache"
    a = dataset.build_cache(data, cache, stride=16, max_rows=4)
    meta = json.loads((a / "complete.json").read_text())
    assert meta["historical_signal_policy"] == "omitted"
    assert not any(c.startswith("current_signal/") for c in meta["columns"])
    assert dataset.build_cache(data, cache, stride=16, max_rows=4) == a, "identical inputs must reuse the cache"
    assert dataset.build_cache(data, cache, stride=8, max_rows=4) != a, "stride must change the key"
    hist = data / "train" / "history.csv"
    text = hist.read_text().splitlines()
    head, first = text[0], text[1].split(",")
    first[-1] = "20" if first[-1] != "20" else "0"
    hist.write_text("\n".join([head, ",".join(first)] + text[2:]) + "\n")
    changed = dataset.build_cache(data, cache, stride=16, max_rows=4)
    assert changed != a, "input bytes must change the key"
    real = dataset.file_hash
    monkeypatch.setattr(dataset, "file_hash", lambda p: ("x" + real(p)) if Path(p).name == "features.py" else real(p))
    assert dataset.build_cache(data, cache, stride=16, max_rows=4) != changed, "features.py source must change the key"


def test_cache_rows_are_strictly_as_of(tmp_path):
    """Each historical cache row equals a fresh registry row at cutoff=t and is labelled with payout[t]."""
    dataset = shared("dataset"); features = shared("features")
    data = _tiny_round(tmp_path / "data", episodes=2)
    path = dataset.build_cache(data, tmp_path / "cache", stride=16, max_rows=4)
    meta = json.loads((path / "complete.json").read_text())
    q, h = load_from(data / "train")
    by_id = {x["query_id"]: x for x in q}
    comp = features.FeatureComputer(h)
    with np.load(path / "train.npz", allow_pickle=False) as z:
        for X, y, kind, qid, tick in zip(z["X"], z["y"], z["kind"], z["query_id"], z["tick"]):
            if kind != "historical":
                continue
            base = by_id[str(qid).split("@")[0]]
            expect, names = comp.row(dict(base, cutoff=str(int(tick))), features.HISTORICAL_GROUPS)
            assert names == meta["columns"]
            np.testing.assert_allclose(X, expect, rtol=0, atol=1e-6)
            assert int(y) == PAYOUTS.index(h[(base["episode_id"], base["machine_id"])][int(tick)])
            assert int(tick) < int(base["cutoff"])


def load_from(folder):
    queries = rows(folder / "queries.csv")
    history = defaultdict(dict)
    for r in rows(folder / "history.csv"):
        history[(r["episode_id"], r["machine_id"])][int(r["tick"])] = int(r["payout"])
    return queries, history


# --------------------------------------------------------------------------- qa_size_streak extension

def ext():
    features = shared("features")
    from research.extensions import qa_size_streak
    return features, qa_size_streak


def test_extension_as_of_on_real_histories():
    features, mod = ext()
    rng = random.Random(7)
    base = features.FeatureComputer(TRAIN_H)
    for q, t in origins(seed=11):
        a, names = mod.row(base, q)
        b, _ = mod.row(features.FeatureComputer(scramble_from(TRAIN_H, q["episode_id"], t, rng)), q)
        assert names == list(mod.NAMES) and len(a) == len(names)
        np.testing.assert_array_equal(a, b)


def _hand(history_rows, cutoff=10):
    features, mod = ext()
    h = defaultdict(dict); h[("e", "m")] = dict(history_rows)
    q = dict(query_id="q", episode_id="e", machine_id="m", machine_type="steady", signal="0", cutoff=str(cutoff))
    v, names = mod.row(features.FeatureComputer(h), q, decay=1.0)
    return dict(zip([n.split("/")[1] for n in names], v.tolist()))


def test_extension_hand_computed_values():
    # ticks 0..9: wins of size 1x,1x,2x,20x at ticks 2,3,5,7; losses elsewhere; tick 8 missing
    f = _hand({0: 0, 1: 0, 2: 1, 3: 1, 4: 0, 5: 2, 6: 0, 7: 20, 9: 0})
    size = np.array([2, 1, 0, 1]) + 0.5
    np.testing.assert_allclose([f[f"size_given_win_{i}"] for i in range(4)], size / size.sum(), rtol=1e-6)
    assert f["win_mass"] == pytest.approx(np.log1p(4))
    assert f["ticks_since_win"] == pytest.approx(np.log1p(10 - 7))
    assert f["ever_won"] == 1.0
    assert f["streak_len"] == 1.0 and f["streak_is_win"] == 0.0  # tick 8 missing stops the loss run at 1


def test_extension_missing_last_tick_is_not_a_loss():
    observed = _hand({7: 0, 8: 0, 9: 0})
    assert observed["streak_len"] == 3.0 and observed["streak_is_win"] == 0.0
    missing = _hand({7: 0, 8: 0})  # tick 9 = cutoff-1 unknown
    assert missing["streak_len"] == 0.0 and missing["streak_is_win"] == 0.0
    no_wins = _hand({})
    assert no_wins["ever_won"] == 0.0 and no_wins["ticks_since_win"] == pytest.approx(np.log1p(10))


def test_negative_control_leaky_extension_is_caught():
    """Same as-of check against a variant that reads all recorded ticks must fail."""
    features, mod = ext()

    class Leaky(features.FeatureComputer):
        def _past(self, episode, machine, cutoff):
            return super()._past(episode, machine, 10 ** 9)

    rng = random.Random(13)
    q, t = origins(1, seed=17)[0]
    a = mod.row(Leaky(TRAIN_H), q)[0]
    b = mod.row(Leaky(scramble_from(TRAIN_H, q["episode_id"], t, rng)), q)[0]
    # future wins can make ticks_since_win negative (NaN after log1p) - itself a symptom of the leak
    assert np.nanmax(np.abs(a - b)) > 0 or np.isnan(a).any()
