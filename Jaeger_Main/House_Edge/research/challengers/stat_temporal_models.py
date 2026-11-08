"""HE-15 temporal challengers (pre-registered in research/configs/stats/temporal_he15/plan.json).

  stat_temporal_hmm         per-type K-state HMM over the five payout classes
  stat_temporal_factorized  HE-09 lag-context P(win) x per-type size-regime HMM P(size | win)
  stat_temporal_ar1         bounded per-class AR(1) indicator baseline, projected onto the simplex

Contract (same as research/CONTRACTS.md): fit(queries, history, labels) -> self; predict_proba(queries, history)
-> {query_id: five probabilities}. Labels are class indices 0-4. Only ticks strictly before each query's cutoff
are read. A missing tick advances the hidden chain with no emission; it is never treated as a 0x payout.
No validation-target constants are used. `factory(config, cache_path)` exposes the models to the #8 registry.
"""
from __future__ import annotations

import numpy as np

from research.adapters import Serializable, validate_predictions
from research.challengers import stat_he09_models as SM

PAYOUTS = (0, 1, 2, 5, 20)
TYPES = ("steady", "balanced", "jackpot")


# --------------------------------------------------------------------------- sequence helpers

def sequences(queries, history, symbols="payout"):
    """(N, T) int matrix, -1 = no emission. symbols='payout' -> classes 0-4; 'size' -> 0-3 on wins only."""
    lens = np.array([int(q["cutoff"]) for q in queries])
    O = np.full((len(queries), max(lens.max(), 1)), -1, dtype=np.int64)
    for i, q in enumerate(queries):
        ticks, ys = SM.past(history, q)
        if symbols == "size":
            keep = ys > 0
            ticks, ys = ticks[keep], ys[keep] - 1
        O[i, ticks] = ys
    return O, lens


# --------------------------------------------------------------------------- HMM core (vectorised over sequences)

def _emissions(O, B):
    E = np.ones(O.shape + (B.shape[0],))
    valid = O >= 0
    E[valid] = B[:, O[valid]].T
    return E


def forward(O, lens, pi, A, B):
    """Scaled forward pass; returns filtered state at each row's last step and total log-likelihood."""
    N, T = O.shape
    E = _emissions(O, B)
    alpha = np.zeros((N, T, len(pi)))
    a = pi[None, :] * E[:, 0]
    c = a.sum(1, keepdims=True); alpha[:, 0] = a / c
    loglik = np.log(c[:, 0])
    for t in range(1, T):
        a = (alpha[:, t - 1] @ A) * E[:, t]
        c = a.sum(1, keepdims=True); alpha[:, t] = a / c
        loglik += np.where(t < lens, np.log(c[:, 0]), 0.0)
    last = alpha[np.arange(N), lens - 1]
    return alpha, E, last, float(loglik.sum())


def baum_welch(O, lens, K, n_sym, iters=40, seed=0, tol=1e-6):
    rng = np.random.default_rng(seed)
    pi = np.full(K, 1.0 / K)
    A = 0.9 * np.eye(K) + 0.1 * rng.dirichlet(np.ones(K), K)
    A /= A.sum(1, keepdims=True)
    B = rng.dirichlet(np.ones(n_sym) * 2, K)
    N, T = O.shape
    step_mask = (np.arange(T)[None, :] < lens[:, None])
    prev, history = -np.inf, []
    for it in range(iters):
        alpha, E, _, ll = forward(O, lens, pi, A, B)
        history.append(ll)
        beta = np.ones((N, T, K))
        for t in range(T - 2, -1, -1):
            b = (E[:, t + 1] * beta[:, t + 1]) @ A.T
            beta[:, t] = b / b.sum(1, keepdims=True)
        gamma = alpha * beta
        gamma /= gamma.sum(2, keepdims=True)
        xi = np.zeros((K, K))
        for t in range(1, T):
            m = alpha[:, t - 1][:, :, None] * A[None] * (E[:, t] * beta[:, t])[:, None, :]
            m /= m.sum((1, 2), keepdims=True)
            xi += (m * step_mask[:, t][:, None, None]).sum(0)
        pi = gamma[:, 0].mean(0) + 1e-6; pi /= pi.sum()
        A = xi + 1e-3; A /= A.sum(1, keepdims=True)
        valid = O >= 0
        Bn = np.full((K, n_sym), 1e-3)
        for s in range(n_sym):
            Bn[:, s] += (gamma * (O == s)[:, :, None] * valid[:, :, None]).sum((0, 1))
        B = Bn / Bn.sum(1, keepdims=True)
        if abs(ll - prev) < tol * max(1.0, abs(ll)):
            break
        prev = ll
    return {"pi": pi, "A": A, "B": B, "loglik": history[-1], "iters": it + 1,
            "converged": abs(history[-1] - (history[-2] if len(history) > 1 else -np.inf)) < tol * max(1.0, abs(history[-1]))}


def best_of_restarts(O, lens, K, n_sym, restarts=3, iters=40):
    fits = [baum_welch(O, lens, K, n_sym, iters=iters, seed=s) for s in range(restarts)]
    return max(fits, key=lambda f: f["loglik"]), fits


def predictive(O, lens, params):
    _, _, last, _ = forward(O, lens, params["pi"], params["A"], params["B"])
    return (last @ params["A"]) @ params["B"]


def _log_score(pred, queries, labels):
    return float(np.mean([np.log(max(pred[i][labels[q["query_id"]]], 1e-12)) for i, q in enumerate(queries)]))


# --------------------------------------------------------------------------- 1. full five-class HMM

class TemporalHMM(Serializable):
    K_GRID = (2, 3)

    def __init__(self, restarts=3, iters=40):
        self.restarts, self.iters = restarts, iters

    def _fit_types(self, queries, history, K):
        params, diag = {}, {}
        for ty in TYPES:
            qs = [q for q in queries if q["machine_type"] == ty]
            O, lens = sequences(qs, history, "payout")
            best, fits = best_of_restarts(O, lens, K, 5, self.restarts, self.iters)
            params[ty] = best
            diag[ty] = {"loglik": best["loglik"], "iters": best["iters"], "converged": best["converged"],
                        "restart_logliks": [f["loglik"] for f in fits]}
        return params, diag

    def _predict(self, params, queries, history):
        out = np.zeros((len(queries), 5))
        for ty in TYPES:
            idx = [i for i, q in enumerate(queries) if q["machine_type"] == ty]
            if idx:
                O, lens = sequences([queries[i] for i in idx], history, "payout")
                out[idx] = predictive(O, lens, params[ty])
        return out / out.sum(1, keepdims=True)

    def fit(self, queries, history, labels):
        best = None
        self.diagnostics = {}
        for K in self.K_GRID:
            params, diag = self._fit_types(queries, history, K)
            score = _log_score(self._predict(params, queries, history), queries, labels)
            self.diagnostics[K] = {"fit_log_score": score, "types": diag}
            if best is None or score > best[0]:
                best = (score, K, params)
        _, self.K, self.params = best
        return self

    def predict_proba(self, queries, history):
        p = self._predict(self.params, queries, history)
        return validate_predictions({q["query_id"]: p[i] for i, q in enumerate(queries)}, queries)


# --------------------------------------------------------------------------- 2. factorized: lag-context win x size-regime HMM

class TemporalFactorized(Serializable):
    K_GRID = (2, 3)

    def __init__(self, restarts=3, iters=40):
        self.restarts, self.iters = restarts, iters

    def _size_fit(self, queries, history, K):
        params = {}
        for ty in TYPES:
            O, lens = sequences([q for q in queries if q["machine_type"] == ty], history, "size")
            params[ty] = best_of_restarts(O, lens, K, 4, self.restarts, self.iters)[0]
        return params

    def _size_predict(self, params, queries, history):
        out = np.zeros((len(queries), 4))
        for ty in TYPES:
            idx = [i for i, q in enumerate(queries) if q["machine_type"] == ty]
            if idx:
                O, lens = sequences([queries[i] for i in idx], history, "size")
                out[idx] = predictive(O, lens, params[ty])
        return out / out.sum(1, keepdims=True)

    def _combine(self, win_model, size_params, queries, history):
        lag = win_model.predict(queries, history)
        pw = np.array([1.0 - lag[q["query_id"]][0] for q in queries])
        size = self._size_predict(size_params, queries, history)
        p = np.column_stack([1.0 - pw, pw[:, None] * size])
        return p / p.sum(1, keepdims=True)

    def fit(self, queries, history, labels):
        self.win = SM.MarkovMixture().fit(queries, history, labels)
        best = None
        self.diagnostics = {}
        for K in self.K_GRID:
            sp = self._size_fit(queries, history, K)
            score = _log_score(self._combine(self.win, sp, queries, history), queries, labels)
            self.diagnostics[K] = {"fit_log_score": score}
            if best is None or score > best[0]:
                best = (score, K, sp)
        _, self.K, self.size_params = best
        return self

    def predict_proba(self, queries, history):
        p = self._combine(self.win, self.size_params, queries, history)
        return validate_predictions({q["query_id"]: p[i] for i, q in enumerate(queries)}, queries)


# --------------------------------------------------------------------------- 3. bounded AR(1) indicator baseline

class TemporalAR1(Serializable):
    def __init__(self, decay=0.97, strength=10.0, floor=1e-4):
        self.decay, self.strength, self.floor = decay, strength, floor

    def fit(self, queries, history, labels=None):
        self.type_mean, self.phi = {}, {}
        for ty in TYPES:
            pairs, counts = [], np.ones(5)
            for q in queries:
                if q["machine_type"] != ty:
                    continue
                ticks, ys = SM.past(history, q)
                counts += np.bincount(ys, minlength=5)
                consecutive = np.nonzero(np.diff(ticks) == 1)[0]
                pairs.extend(zip(ys[consecutive], ys[consecutive + 1]))
            mean = counts / counts.sum()
            phi = np.zeros(5)
            if pairs:
                prev, nxt = np.array(pairs).T
                for k in range(5):
                    x, y = (prev == k) - mean[k], (nxt == k) - mean[k]
                    phi[k] = np.clip((x * y).sum() / max((x * x).sum(), 1e-9), -0.99, 0.99)
            self.type_mean[ty], self.phi[ty] = mean, phi
        return self

    def predict_proba(self, queries, history):
        out = {}
        for q in queries:
            ty, c = q["machine_type"], int(q["cutoff"])
            ticks, ys = SM.past(history, q)
            w = self.decay ** (c - 1 - ticks)
            mu = (self.strength * self.type_mean[ty] + np.bincount(ys, weights=w, minlength=5)) / (self.strength + w.sum())
            p = mu.copy()
            if len(ticks):
                gap = c - ticks[-1]  # steps from last observed tick to the forecast tick
                x_last = np.eye(5)[ys[-1]]
                p = mu + self.phi[ty] ** gap * (x_last - mu)
            p = np.clip(p, self.floor, 1.0)
            out[q["query_id"]] = p / p.sum()
        return validate_predictions(out, queries)


MODELS = {"stat_temporal_hmm": TemporalHMM, "stat_temporal_factorized": TemporalFactorized, "stat_temporal_ar1": TemporalAR1}


def factory(config, cache_path=None):
    """#8 registry factory: {"family": name, "factory": "research.challengers.stat_temporal_models:factory", "model": name}."""
    name = config.get("model", config.get("family"))
    if name not in MODELS:
        raise ValueError(f"Unknown HE-15 model {name!r}; expected one of {sorted(MODELS)}")
    return MODELS[name](**config.get("params", {}))
