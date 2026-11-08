"""HE-09 statistical challengers (lane D): hierarchical Dirichlet, five-class lag-context Markov mixture,
and Bayesian averaging over half-lives. Pre-registered in research/configs/stats/he09/plan.json.

Contract shared by all three models:
  model.fit(queries, history, labels) -> self      # fit split only: histories + query labels
  model.predict(queries, history)     -> {query_id: (p_0, p_1, p_2, p_5, p_20)}
Only ticks strictly before each query's cutoff are read; a missing tick is unknown (never a 0x);
the query-time signal is used only as a query-level prior tilt, never for historical rows.
No validation-target constants are used anywhere in this module.
"""
from __future__ import annotations

import csv
import itertools
from collections import defaultdict
from pathlib import Path

import numpy as np

PAYOUTS = (0, 1, 2, 5, 20)
TYPES = ("steady", "balanced", "jackpot")
K = 5


# --------------------------------------------------------------------------- data helpers

def read_split(folder):
    folder = Path(folder)
    with open(folder / "queries.csv", newline="") as f:
        queries = list(csv.DictReader(f))
    history = defaultdict(dict)
    with open(folder / "history.csv", newline="") as f:
        for r in csv.DictReader(f):
            history[(r["episode_id"], r["machine_id"])][int(r["tick"])] = int(r["payout"])
    labels = {}
    if (folder / "labels.csv").exists():
        with open(folder / "labels.csv", newline="") as f:
            labels = {r["query_id"]: PAYOUTS.index(int(r["outcome"])) for r in csv.DictReader(f)}
    return queries, history, labels


def past(history, q):
    """(ticks, class indices) strictly before the query cutoff, ascending."""
    c = int(q["cutoff"])
    items = sorted((t, v) for t, v in history[(q["episode_id"], q["machine_id"])].items() if t < c)
    return (np.array([t for t, _ in items], dtype=np.int64),
            np.array([PAYOUTS.index(v) for _, v in items], dtype=np.int64))


def pay_matrix(queries, history):
    """M x T matrix of class indices (-1 = missing or >= cutoff), T = max cutoff."""
    T = max(int(q["cutoff"]) for q in queries)
    pay = np.full((len(queries), T), -1, dtype=np.int64)
    for m, q in enumerate(queries):
        ticks, ys = past(history, q)
        pay[m, ticks] = ys
    return pay


def log_score(pred, queries, labels):
    return float(np.mean([np.log(max(pred[q["query_id"]][labels[q["query_id"]]], 1e-12)) for q in queries]))


# --------------------------------------------------------------------------- hierarchical prior

class TypeSignalPrior:
    """Type-level class frequencies from fit histories, tilted per (type, query signal) by fit query labels."""

    def __init__(self, tilt_strength=50.0):
        self.tilt_strength = tilt_strength

    def fit(self, queries, history, labels):
        base = {ty: np.ones(K) for ty in TYPES}
        for q in queries:
            _, ys = past(history, q)
            base[q["machine_type"]] += np.bincount(ys, minlength=K)
        self.type_mean = {ty: v / v.sum() for ty, v in base.items()}
        cells = defaultdict(lambda: np.zeros(K))
        for q in queries:
            if q["query_id"] in labels:
                cells[(q["machine_type"], q["signal"])][labels[q["query_id"]]] += 1
        self.mean = {}
        for ty in TYPES:
            for sig in ("-1", "0", "1"):
                n = cells[(ty, sig)]
                self.mean[(ty, sig)] = (self.tilt_strength * self.type_mean[ty] + n) / (self.tilt_strength + n.sum())
        return self

    def __call__(self, q):
        return self.mean[(q["machine_type"], q["signal"])]


# --------------------------------------------------------------------------- 1. hierarchical Dirichlet

class DirichletModel:
    DECAYS = (0.90, 0.95, 0.97, 0.99, 1.0)
    STRENGTHS = (1.0, 2.0, 5.0, 10.0, 20.0, 50.0)
    SHORT = 100

    def _counts(self, queries, history, decay):
        out = []
        for q in queries:
            ticks, ys = past(history, q)
            w = decay ** (int(q["cutoff"]) - 1 - ticks)
            out.append((np.bincount(ys, weights=w, minlength=K), len(ticks)))
        return out

    def _posterior(self, queries, counts, s_short, s_long):
        pred = {}
        for q, (cnt, n) in zip(queries, counts):
            s = s_short if n < self.SHORT else s_long
            p = (s * self.prior(q) + cnt) / (s + cnt.sum())
            pred[q["query_id"]] = p
        return pred

    def fit(self, queries, history, labels):
        self.prior = TypeSignalPrior().fit(queries, history, labels)
        short = [q for q in queries if len(past(history, q)[0]) < self.SHORT]
        long_ = [q for q in queries if len(past(history, q)[0]) >= self.SHORT]
        best = None
        for d in self.DECAYS:
            counts = self._counts(queries, history, d)
            for s_short in self.STRENGTHS:
                for s_long in self.STRENGTHS:
                    pred = self._posterior(queries, counts, s_short, s_long)
                    score = log_score(pred, queries, labels)
                    if best is None or score > best[0]:
                        best = (score, d, s_short, s_long)
        _, self.decay, self.s_short, self.s_long = best
        self.n_short, self.n_long = len(short), len(long_)
        return self

    def predict(self, queries, history):
        pred = self._posterior(queries, self._counts(queries, history, self.decay), self.s_short, self.s_long)
        return {k: tuple(v / v.sum()) for k, v in pred.items()}


# --------------------------------------------------------------------------- 2. five-class lag-context mixture

def lag_experts(max_lag=8):
    ex = [(0, 0)]
    ex += [(k, 0) for k in range(1, max_lag + 1)]
    ex += list(itertools.combinations(range(1, max_lag + 1), 2))
    return ex


class MarkovMixture:
    """Experts over lag contexts (3 categories: 0, 1, 2+) predicting all five classes directly."""
    A_GRID = (1.0, 3.0)
    BETA_GRID = (1.0, 2.0)

    def __init__(self, count_decay=0.95, ll_decay=0.995):
        self.count_decay, self.ll_decay = count_decay, ll_decay
        self.experts = lag_experts()

    def _run(self, queries, history, a):
        """Online pass; returns per-query expert predictions at cutoff (M,E,K) and log-likelihoods (M,E)."""
        pay = pay_matrix(queries, history)
        M, T = pay.shape
        E = len(self.experts)
        L1 = np.array([e[0] for e in self.experts]); L2 = np.array([e[1] for e in self.experts])
        cat = np.where(pay < 0, -1, np.minimum(pay, 2))
        C = np.zeros((M, E, 9, K)); marg = np.zeros((M, K)); LL = np.zeros((M, E))
        rows = np.arange(M)

        def ctx(t):
            def at(lag):
                tt = t - lag
                out = np.full(M, -1, dtype=np.int64)
                if tt >= 0:
                    out = cat[:, tt].copy() if tt < T else out
                return out
            cache = {k: at(k) for k in range(1, 9)}
            c1 = np.stack([np.zeros(M, dtype=np.int64) if l == 0 else cache[l] for l in L1], axis=1)
            c2 = np.stack([np.zeros(M, dtype=np.int64) if l == 0 else cache[l] for l in L2], axis=1)
            valid = (c1 >= 0) & (c2 >= 0)
            return np.where(valid, c1 * 3 + c2, 0), valid

        def experts_pred(idx, valid):
            mp = (1.0 + marg) / (K + marg.sum(axis=1, keepdims=True))            # machine decayed marginal
            cnt = np.take_along_axis(C, idx[:, :, None, None].repeat(K, axis=3), axis=2)[:, :, 0, :]
            pe = (a * mp[:, None, :] + cnt) / (a + cnt.sum(axis=2, keepdims=True))
            return np.where(valid[:, :, None], pe, mp[:, None, :])

        for t in range(T):
            obs = pay[:, t] >= 0
            if not obs.any():
                continue
            idx, valid = ctx(t)
            pe = experts_pred(idx, valid)
            y = np.where(obs, pay[:, t], 0)
            ll = np.log(np.clip(pe[rows, :, y], 1e-12, 1))
            LL = np.where(obs[:, None], LL * self.ll_decay + ll, LL)
            dec = np.where(obs, self.count_decay, 1.0)
            C *= dec[:, None, None, None]; marg *= dec[:, None]
            upd = obs[:, None] & valid
            m_i, e_i = np.nonzero(upd)
            np.add.at(C, (m_i, e_i, idx[m_i, e_i], y[m_i]), 1.0)
            marg[rows[obs], y[obs]] += 1.0
        cut = np.array([int(q["cutoff"]) for q in queries])
        out = np.zeros((M, E, K))
        for c in np.unique(cut):
            sel = cut == c
            idx, valid = ctx(int(c))
            out[sel] = experts_pred(idx, valid)[sel]
        return out, LL

    @staticmethod
    def _mix(pe, LL, beta):
        s = beta * LL; s -= s.max(axis=1, keepdims=True)
        w = np.exp(s); w /= w.sum(axis=1, keepdims=True)
        return (w[:, :, None] * pe).sum(axis=1)

    def fit(self, queries, history, labels):
        best = None
        for a in self.A_GRID:
            pe, LL = self._run(queries, history, a)
            for beta in self.BETA_GRID:
                p = self._mix(pe, LL, beta)
                score = log_score({q["query_id"]: p[m] for m, q in enumerate(queries)}, queries, labels)
                if best is None or score > best[0]:
                    best = (score, a, beta)
        _, self.a, self.beta = best
        return self

    def predict(self, queries, history):
        pe, LL = self._run(queries, history, self.a)
        p = self._mix(pe, LL, self.beta)
        return {q["query_id"]: tuple(p[m] / p[m].sum()) for m, q in enumerate(queries)}


# --------------------------------------------------------------------------- 3. Bayesian averaging over half-lives

class DecayBMA:
    DECAYS = (0.80, 0.90, 0.95, 0.97, 0.99, 1.0)
    STRENGTHS = (2.0, 5.0, 10.0, 20.0)

    def __init__(self, ll_decay=0.98):
        self.ll_decay = ll_decay

    def _run(self, queries, history, s):
        pay = pay_matrix(queries, history)
        M, T = pay.shape
        D = np.array(self.DECAYS)
        prior = np.stack([self.prior(q) for q in queries])                      # (M,K)
        C = np.zeros((M, len(D), K)); LL = np.zeros((M, len(D))); rows = np.arange(M)
        for t in range(T):
            obs = pay[:, t] >= 0
            if not obs.any():
                continue
            post = (s * prior[:, None, :] + C) / (s + C.sum(axis=2, keepdims=True))
            y = np.where(obs, pay[:, t], 0)
            ll = np.log(np.clip(post[rows, :, y], 1e-12, 1))
            LL = np.where(obs[:, None], LL * self.ll_decay + ll, LL)
            C = np.where(obs[:, None, None], C * D[None, :, None], C)
            C[rows[obs], :, y[obs]] += 1.0
        post = (s * prior[:, None, :] + C) / (s + C.sum(axis=2, keepdims=True))
        w = LL - LL.max(axis=1, keepdims=True); w = np.exp(w); w /= w.sum(axis=1, keepdims=True)
        return (w[:, :, None] * post).sum(axis=1)

    def fit(self, queries, history, labels):
        self.prior = TypeSignalPrior().fit(queries, history, labels)
        best = None
        for s in self.STRENGTHS:
            p = self._run(queries, history, s)
            score = log_score({q["query_id"]: p[m] for m, q in enumerate(queries)}, queries, labels)
            if best is None or score > best[0]:
                best = (score, s)
        self.s = best[1]
        return self

    def predict(self, queries, history):
        p = self._run(queries, history, self.s)
        return {q["query_id"]: tuple(p[m] / p[m].sum()) for m, q in enumerate(queries)}


MODELS = {"stat_dirichlet": DirichletModel, "stat_markov": MarkovMixture, "stat_decay_bma": DecayBMA}
