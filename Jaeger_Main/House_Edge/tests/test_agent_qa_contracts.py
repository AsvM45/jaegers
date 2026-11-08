"""HE-02 (lane C, QA): independent scorer parity and temporal/data-boundary contracts.

Run from Jaeger_Main/House_Edge:
    python -m pytest tests/test_agent_qa_contracts.py -q

Design: each invariant is a reusable checker (``assert_*``). Positive tests apply the checker to the
champion (``jaegers_entry/jaeger_model.py``, loaded read-only) or the shared feature registry.
Negative controls apply the same checker to a deliberately leaky predictor and require it to FAIL,
so a passing suite cannot be vacuous. Nothing here edits champion, organizer or shared research code.
"""
from __future__ import annotations

import contextlib
import csv
import importlib
import importlib.util
import io
import random
import shutil
import subprocess
import sys
from collections import defaultdict
from copy import deepcopy
from pathlib import Path

import numpy as np
import pytest

HE = Path(__file__).resolve().parents[1]
if str(HE) not in sys.path:
    sys.path.insert(0, str(HE))

from slot_forecasting.io import read_submission  # noqa: E402
from slot_forecasting.rounds import score_round  # noqa: E402
from slot_forecasting.schema import ValidationError  # noqa: E402

PUB = HE / "public"
COLS = ("p_0", "p_1", "p_2", "p_5", "p_20")
PAYOUTS = (0, 1, 2, 5, 20)
NO_STACK = {"stack": False}  # stacker needs a train split; covered by the end-to-end test below


# --------------------------------------------------------------------------- helpers

def champion():
    """Champion module loaded from its file, independent of research/ adapter names."""
    path = HE / "jaegers_entry" / "jaeger_model.py"
    spec = importlib.util.spec_from_file_location("qa_champion_core", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


CORE = champion()


def shared(name):
    """Import a shared research module; skip (not fail) if lane A renamed it."""
    try:
        return importlib.import_module(f"research.{name}")
    except ImportError as exc:  # pragma: no cover - depends on lane A integration state
        pytest.skip(f"research.{name} unavailable at this HEAD ({exc}); re-point after the adapter rename")


def rows(path):
    with open(path, newline="") as f:
        return list(csv.DictReader(f))


def fixture(episodes=2, machines=4, cutoff=96, seed=0, sparse=False):
    """Small deterministic episode fixture with lag structure; all episodes reuse machine IDs m000..

    Cutoffs differ by episode (cutoff + 16*e), as in the real kit (192-256). With one shared cutoff a
    leaky ``t <= cutoff+k`` filter is invisible, because the champion sizes its tick array to the
    largest cutoff and drops later ticks anyway (verified by mutation, see PR notes)."""
    rng = random.Random(seed)
    queries, history = [], defaultdict(dict)
    types = ("steady", "balanced", "jackpot")
    base_cutoff = cutoff
    for e in range(episodes):
        cutoff = base_cutoff + 16 * e
        for m in range(machines):
            q = dict(query_id=f"ep{e}-m{m:03d}-next", episode_id=f"ep{e}", machine_id=f"m{m:03d}",
                     machine_type=types[m % 3], signal=str((m % 3) - 1), cutoff=str(cutoff))
            queries.append(q)
            prev = [0] * 8
            for t in range(cutoff):
                win = rng.random() < (0.75 if (prev[1] > 0) != (prev[3] > 0) else 0.2)
                y = rng.choice((1, 1, 2, 5, 20)) if win else 0
                prev = [y] + prev[:-1]
                if sparse and t < cutoff - 40 and rng.random() < 0.6:
                    continue
                history[(q["episode_id"], q["machine_id"])][t] = y
    return queries, history


def champion_predict(queries, history):
    return CORE.predict(queries, history, NO_STACK)


def max_diff(a, b, keys=None):
    keys = list(keys if keys is not None else a)
    return max(float(np.abs(np.asarray(a[k]) - np.asarray(b[k])).max()) for k in keys)


# --------------------------------------------------------------------------- reusable checkers

def assert_cutoff_invariant(predict, queries, history, *, target_only=None):
    """Payouts at/after each cutoff (target and/or siblings) must not change any forecast."""
    base = predict(queries, history)
    mutated = deepcopy(history)
    for q in queries:
        key = (q["episode_id"], q["machine_id"])
        if target_only is True and q is not queries[0]:
            continue
        if target_only is False and q is queries[0]:
            continue
        c = int(q["cutoff"])
        for t, v in ((c, 20), (c + 1, 0), (c + 5, 20)):
            mutated[key][t] = v
    after = predict(queries, mutated)
    assert max_diff(base, after) == 0.0, "forecast changed when payouts at/after the cutoff were injected"


def assert_episode_isolated(predict, queries, history):
    """Rewriting every payout of episode ep1 must not move any ep0 forecast (machine IDs are shared)."""
    base = predict(queries, history)
    mutated = deepcopy(history)
    for (ep, _m), r in mutated.items():
        if ep == "ep1":
            for t in r:
                r[t] = 20 if r[t] == 0 else 0
    after = predict(queries, mutated)
    ep0 = [q["query_id"] for q in queries if q["episode_id"] == "ep0"]
    assert max_diff(base, after, ep0) == 0.0, "another episode's history leaked into ep0 via shared machine IDs"


def assert_missing_is_not_zero(predict, queries, history, lag=2):
    """Deleting tick c-lag (unknown) must differ from recording it as a 0x loss."""
    q = queries[0]
    key, c = (q["episode_id"], q["machine_id"]), int(q["cutoff"])
    missing = deepcopy(history); missing[key].pop(c - lag, None)
    zero = deepcopy(history); zero[key][c - lag] = 0
    a =predict(queries, missing)[q["query_id"]]
    b = predict(queries, zero)[q["query_id"]]
    assert float(np.abs(np.asarray(a) - np.asarray(b)).max()) > 0.0, "missing tick c-%d is treated as a 0x payout" % lag


def assert_order_invariant(predict, queries, history, seed=1):
    base = predict(queries, history)
    rng = random.Random(seed)
    q2 = queries[:]; rng.shuffle(q2)
    h2 = defaultdict(dict)
    keys = list(history); rng.shuffle(keys)
    for k in keys:
        items = list(history[k].items()); rng.shuffle(items)
        h2[k] = dict(items)
    after = predict(q2, h2)
    assert set(after) == set(base)
    assert max_diff(base, after) <= 1e-12, "forecasts depend on CSV row order"


def assert_simplex(predictions, expected_ids):
    assert set(predictions) == set(expected_ids) and len(predictions) == len(expected_ids)
    for k, v in predictions.items():
        p = np.asarray(v, dtype=float)
        assert p.shape == (5,) and np.isfinite(p).all() and (p >= 0).all() and (p <= 1).all(), k
        assert abs(p.sum() - 1) <= 1e-9, k


# --------------------------------------------------------------------------- deliberately leaky predictors

def leaky_future(queries, history):
    """Uses every recorded tick, including ticks >= cutoff."""
    out = {}
    for q in queries:
        ys = list(history[(q["episode_id"], q["machine_id"])].values())
        counts = np.bincount([PAYOUTS.index(y) for y in ys], minlength=5) + 1.0
        out[q["query_id"]] = counts / counts.sum()
    return out


def leaky_machine_id(queries, history):
    """Pools by machine_id across episodes (identity transfer)."""
    out = {}
    for q in queries:
        c = int(q["cutoff"]); counts = np.ones(5)
        for (ep, m), r in history.items():
            if m == q["machine_id"]:
                counts += np.bincount([PAYOUTS.index(y) for t, y in r.items() if t < c], minlength=5)
        out[q["query_id"]] = counts / counts.sum()
    return out


def leaky_zero_fill(queries, history):
    """Honest about time, but fills unknown lag-2 with 0x - indistinguishable from a recorded loss."""
    out = {}
    for q in queries:
        c = int(q["cutoff"]); r = history[(q["episode_id"], q["machine_id"])]
        lag2 = r.get(c - 2, 0)
        p = np.full(5, 0.1); p[PAYOUTS.index(lag2)] += 0.5
        out[q["query_id"]] = p / p.sum()
    return out


def order_dependent(queries, history):
    """Depends on query order (first-row bias)."""
    first = queries[0]["query_id"]
    return {q["query_id"]: (np.array([.6, .1, .1, .1, .1]) if q["query_id"] == first else np.full(5, .2)) for q in queries}


# --------------------------------------------------------------------------- 1. official scorer parity

def independent_points(pred, folder=PUB / "validation", max_points=60, pooled=False):
    """Re-derivation of the 60/40 kit score from its documented definition (no slot_forecasting code).

    pooled=True is WRONG on purpose (negative control): one global error ratio over all conditions
    instead of the mean of four per-condition ratios. (Query- vs episode-pooling cannot serve as a
    control here: every episode has exactly 8 machines, so both averages coincide.)"""
    tg = {r["query_id"]: (r["episode_id"], np.array([float(r[c]) for c in COLS])) for r in rows(folder / "targets.csv")}
    ref = {r["query_id"]: np.array([float(r[c]) for c in COLS]) for r in rows(folder / "reference.csv")}
    cond = {r["query_id"]: r["condition"] for r in rows(folder / "conditions.csv")}
    ratios, num, den = [], [], []
    for c in sorted(set(cond.values())):
        e, b = defaultdict(list), defaultdict(list)
        for qid, cc in cond.items():
            if cc == c:
                ep, t = tg[qid]
                e[ep].append(((np.asarray(pred[qid]) - t) ** 2).sum())
                b[ep].append(((ref[qid] - t) ** 2).sum())
        num += [np.mean(v) for v in e.values()]
        den += [np.mean(v) for v in b.values()]
        ratios.append(np.mean([np.mean(v) for v in e.values()]) / np.mean([np.mean(v) for v in b.values()]))
    ratio = float(np.mean(num) / np.mean(den)) if pooled else float(np.mean(ratios))
    return max_points / (1 + ratio)


def write_csv(path, pred):
    with open(path, "w", newline="") as f:
        w = csv.writer(f); w.writerow(("query_id",) + COLS)
        for k, v in pred.items():
            w.writerow([k] + [repr(float(x)) for x in v])


def official(pred, tmp_path):
    path = tmp_path / "sub.csv"; write_csv(path, pred)
    return score_round(path, PUB)


def _from_file(name):
    return {r["query_id"]: [float(r[c]) for c in COLS] for r in rows(PUB / "validation" / name)}


def test_scorer_reference_scores_exactly_half(tmp_path):
    r = official(_from_file("reference.csv"), tmp_path)
    assert r["technical_points"] == pytest.approx(30.0, abs=1e-12)
    assert all(v["loss_ratio"] == pytest.approx(1.0, abs=1e-12) for v in r["by_condition"].values())


def test_scorer_truth_scores_maximum(tmp_path):
    truth = _from_file("targets.csv")
    assert official(truth, tmp_path)["technical_points"] == pytest.approx(60.0, abs=1e-12)


@pytest.mark.parametrize("kind", ["uniform", "skewed", "reference_mix"])
def test_scorer_matches_independent_formula(tmp_path, kind):
    ref = _from_file("reference.csv")
    rng = np.random.default_rng(len(kind))
    if kind == "uniform":
        pred = {k: [0.2] * 5 for k in ref}
    elif kind == "skewed":
        pred = {k: list(rng.dirichlet([5, 2, 1, .5, .2])) for k in ref}
    else:
        truth = _from_file("targets.csv")
        pred = {k: list(0.5 * np.array(ref[k]) + 0.5 * np.array(truth[k])) for k in ref}
    assert official(pred, tmp_path)["technical_points"] == pytest.approx(independent_points(pred), abs=1e-9)


def test_negative_control_pooled_formula_is_detected(tmp_path):
    """The parity test is sensitive: pooling conditions into one ratio gives a different number."""
    rng = np.random.default_rng(3)
    pred = {k: list(rng.dirichlet([5, 2, 1, .5, .2])) for k in _from_file("reference.csv")}
    assert abs(official(pred, tmp_path)["technical_points"] - independent_points(pred, pooled=True)) > 1e-6


def test_test_split_check_is_format_only(tmp_path):
    """check_submission on test reports format + hash, never a loss, and public/test holds no truth."""
    assert sorted(p.name for p in (PUB / "test").iterdir()) == ["history.csv", "queries.csv", "sample_submission.csv"]
    import check_submission
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        code = check_submission.main([str(PUB / "test" / "sample_submission.csv"), "--data", str(PUB), "--split", "test"])
    out = buf.getvalue()
    assert code == 0 and "VALID FORMAT" in out
    assert "Validation points" not in out and "loss ratio" not in out


# --------------------------------------------------------------------------- 2. submission contract

def _sample():
    return {r["query_id"]: [float(r[c]) for c in COLS] for r in rows(PUB / "test" / "sample_submission.csv")}


def _ids():
    return {r["query_id"] for r in rows(PUB / "test" / "queries.csv")}


def test_contract_accepts_sample_and_exact_ids(tmp_path):
    p = tmp_path / "ok.csv"; write_csv(p, _sample())
    assert set(read_submission(p, _ids())) == _ids()


@pytest.mark.parametrize("break_it", ["missing_id", "duplicate_id", "nan", "negative", "sum_off", "extra_id"])
def test_contract_rejects_invalid_rows(tmp_path, break_it):
    sub = _sample(); key = next(iter(sub))
    lines = [("query_id",) + COLS] + [(k,) + tuple(repr(x) for x in v) for k, v in sub.items()]
    if break_it == "missing_id":
        lines.pop(1)
    elif break_it == "duplicate_id":
        lines.append(lines[1])
    elif break_it == "nan":
        lines[1] = (key, "nan", "0.25", "0.25", "0.25", "0.25")
    elif break_it == "negative":
        lines[1] = (key, "-0.1", "0.4", "0.3", "0.2", "0.2")
    elif break_it == "sum_off":
        lines[1] = (key, "0.3", "0.3", "0.3", "0.3", "0.3")
    else:
        lines.append(("not-a-real-query", "0.2", "0.2", "0.2", "0.2", "0.2"))
    path = tmp_path / "bad.csv"
    with open(path, "w", newline="") as f:
        csv.writer(f).writerows(lines)
    with pytest.raises(ValidationError):
        read_submission(path, _ids())


# --------------------------------------------------------------------------- 3. champion temporal / boundary contracts

def test_champion_simplex_and_ids():
    q, h = fixture(sparse=True)
    assert_simplex(champion_predict(q, h), [x["query_id"] for x in q])


@pytest.mark.parametrize("target_only", [True, False], ids=["target_machine", "siblings_only"])
def test_champion_ignores_payouts_at_or_after_cutoff(target_only):
    q, h = fixture()
    assert_cutoff_invariant(champion_predict, q, h, target_only=target_only)


def test_champion_sibling_channel_is_live():
    """Positive control: an EARLIER sibling payout may move the target, so the cutoff test is not vacuous."""
    q, h = fixture()
    target = q[0]; sib = (target["episode_id"], q[1]["machine_id"]); c = int(target["cutoff"])
    base = champion_predict(q, h)[target["query_id"]]
    for t in range(c - 30, c):
        h[sib][t] = 20 if h[sib].get(t, 0) == 0 else 0
    assert float(np.abs(np.asarray(champion_predict(q, h)[target["query_id"]]) - np.asarray(base)).max()) > 0


def test_champion_isolates_episodes_with_shared_machine_ids():
    q, h = fixture()
    assert {x["machine_id"] for x in q if x["episode_id"] == "ep0"} == {x["machine_id"] for x in q if x["episode_id"] == "ep1"}
    assert_episode_isolated(champion_predict, q, h)


def test_champion_missing_lag2_is_not_zero():
    q, h = fixture()
    assert_missing_is_not_zero(champion_predict, q, h, lag=2)


def test_champion_row_order_invariant():
    q, h = fixture(sparse=True)
    assert_order_invariant(champion_predict, q, h)


# --------------------------------------------------------------------------- 4. negative controls: checkers must fail on leaks

@pytest.mark.parametrize("checker,leaky", [
    (lambda p, q, h: assert_cutoff_invariant(p, q, h), leaky_future),
    (lambda p, q, h: assert_cutoff_invariant(p, q, h, target_only=False), leaky_future),
    (assert_episode_isolated, leaky_machine_id),
    (assert_missing_is_not_zero, leaky_zero_fill),
    (assert_order_invariant, order_dependent),
], ids=["future_target", "future_sibling", "cross_episode_identity", "missing_as_zero", "row_order"])
def test_negative_controls_fail(checker, leaky):
    q, h = fixture()
    with pytest.raises(AssertionError):
        checker(leaky, q, h)


# --------------------------------------------------------------------------- 5. shared feature registry (read-only)

def _feature_predict(groups):
    features = shared("features")

    def predict(queries, history):
        comp = features.FeatureComputer(history)
        return {q["query_id"]: comp.row(q, groups)[0].astype(float) for q in queries}
    return predict


def test_features_cutoff_episode_and_order_contracts():
    features = shared("features")
    groups = features.HISTORICAL_GROUPS
    q, h = fixture(sparse=True)
    fn = _feature_predict(groups)
    assert_cutoff_invariant(fn, q, h)
    assert_cutoff_invariant(fn, q, h, target_only=False)
    assert_episode_isolated(fn, q, h)
    assert_order_invariant(fn, q, h)


def test_features_missing_lag2_is_flagged_unknown():
    features = shared("features")
    q, h = fixture()
    key, c = (q[0]["episode_id"], q[0]["machine_id"]), int(q[0]["cutoff"])
    h[key].pop(c - 2, None)
    values, names = features.FeatureComputer(h).row(q[0], ("lags", "missingness"))
    named = dict(zip(names, values))
    assert named["lags/lag2_0"] == 1.0, "lag2 one-hot must select the 'missing' slot"
    assert named["missingness/lag_known_1"] == 0.0
    q2, h2 = fixture()
    assert_missing_is_not_zero(_feature_predict(("lags",)), q2, h2, lag=2)


def test_features_current_signal_blocked_for_historical_rows():
    features = shared("features")
    with pytest.raises(ValueError):
        features.validate_groups(("lags", "current_signal"), historical=True)
    features.validate_groups(("lags", "current_signal"), historical=False)


# --------------------------------------------------------------------------- 6. grouped folds

def test_episode_folds_are_disjoint_and_condition_balanced():
    dataset = shared("dataset")
    qs = rows(PUB / "train" / "queries.csv")
    cond = {r["query_id"]: r["condition"] for r in rows(PUB / "train" / "conditions.csv")}
    folds = dataset.episode_folds(qs, cond, count=4)
    by_fold = defaultdict(set)
    for q in qs:
        by_fold[folds[q["episode_id"]]].add(q["episode_id"])
    eps = [e for s in by_fold.values() for e in s]
    assert len(eps) == len(set(eps)) == len({q["episode_id"] for q in qs}), "an episode appears in two folds"
    ep_cond = {q["episode_id"]: cond[q["query_id"]] for q in qs}
    for c in set(ep_cond.values()):
        sizes = [sum(ep_cond[e] == c for e in by_fold[f]) for f in range(4)]
        assert max(sizes) - min(sizes) <= 1, (c, sizes)
    assert folds == dataset.episode_folds(list(reversed(qs)), cond, count=4), "fold manifest depends on row order"


def test_episode_folds_reject_condition_crossing_episode():
    dataset = shared("dataset")
    qs = rows(PUB / "train" / "queries.csv")[:16]
    cond = {q["query_id"]: "stable" for q in qs}
    cond[qs[1]["query_id"]] = "drift"  # same episode as qs[0]
    assert qs[0]["episode_id"] == qs[1]["episode_id"]
    with pytest.raises(ValueError):
        dataset.episode_folds(qs, cond, count=1)


# --------------------------------------------------------------------------- 7. end-to-end: inference reads no truth files

def _subset_split(src, dst, episodes):
    dst.mkdir(parents=True)
    keep = set(episodes)
    for name in ("queries.csv", "history.csv"):
        r = rows(src / name)
        with open(dst / name, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=r[0].keys()); w.writeheader()
            w.writerows(x for x in r if x["episode_id"] in keep)


def test_predict_runs_without_labels_conditions_or_targets(tmp_path):
    """Champion CLI (stacker on) succeeds when ONLY queries/history exist; truth files are absent."""
    data = tmp_path / "data"
    train_eps = sorted({r["episode_id"] for r in rows(PUB / "train" / "queries.csv")})[:8]
    test_eps = sorted({r["episode_id"] for r in rows(PUB / "test" / "queries.csv")})[:4]
    _subset_split(PUB / "train", data / "train", train_eps)
    _subset_split(PUB / "test", data / "test", test_eps)
    code = tmp_path / "entry"
    shutil.copytree(HE / "jaegers_entry", code, ignore=shutil.ignore_patterns("__pycache__", "README.md"))
    out = tmp_path / "out.csv"
    proc = subprocess.run([sys.executable, "predict.py", "--data", str(data), "--out", str(out)],
                          cwd=code, capture_output=True, text=True, timeout=600)
    assert proc.returncode == 0, proc.stderr[-2000:]
    expected = [r["query_id"] for r in rows(data / "test" / "queries.csv")]
    assert_simplex(read_submission(out, set(expected)), expected)
    for split in ("train", "test"):
        assert sorted(p.name for p in (data / split).iterdir()) == ["history.csv", "queries.csv"]
