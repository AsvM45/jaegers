"""Structural XOR/XNOR lag-rule features for the JAEGERS stacker (issue #58).

Finding: train machines' win rule is almost always XNOR or XOR of win/loss at one of three lag pairs
(1,3), (2,5), (4,7). This challenger keeps the champion unchanged except for 4 extra stacker inputs from an
online Bayesian posterior over those 6 rules (+ a null base-rate hypothesis), computed from ticks strictly
before each row:
    logit(rule-model P(win)), max rule posterior, null posterior, logit * max posterior.

Pre-registered (research/configs/stats/structural/): prereg_gamma, prereg_structural, prereg_stackfeat,
prereg_walkforward. Results: research/reports/stat_structural_stack.md.

`core_predict` is a copy of the champion's `predict()` (via the parity-exact copy in #3) whose stack features
take an optional `extra` array (M, T+1, F); with extra=None it equals the champion exactly (tested).
Constants are read from the champion file. Self-contained for the #8 registry snapshot.
"""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import numpy as np

from research.adapters import Serializable, validate_predictions

HE = Path(__file__).resolve().parents[2]
CHAMPION = HE / "jaegers_entry" / "jaeger_model.py"
PARAMS = HE / "jaegers_entry" / "params.json"
_spec = importlib.util.spec_from_file_location("stat_structural_champion", CHAMPION)
C = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(C)
EXPERTS, SIZE_REGIMES, DEFAULTS, PAYOUTS = C.EXPERTS, C.SIZE_REGIMES, C.DEFAULTS, C.PAYOUTS


# =========================================================================== champion core with extra inputs

def core_predict(queries, hist, params=None, expert_logprior=None, return_ll=False, collect=False, stack_w=None,
                 running_regime=False, collect_logprior=None, extra=None):
    p = dict(DEFAULTS, **(params or {}))
    M = len(queries)
    T = max(int(q["cutoff"]) for q in queries)
    PIDX = {v: i for i, v in enumerate(PAYOUTS)}
    pay = np.full((M, T), -1, dtype=np.int64)
    for m, q in enumerate(queries):
        cut = int(q["cutoff"])
        for t, v in hist[(q["episode_id"], q["machine_id"])].items():
            if t < cut:
                pay[m, t] = PIDX[v]
    cut = np.array([int(q["cutoff"]) for q in queries])
    ep_ids = {e: i for i, e in enumerate(sorted({q["episode_id"] for q in queries}))}
    ep = np.array([ep_ids[q["episode_id"]] for q in queries])
    n_ep = len(ep_ids)

    cat2 = np.where(pay < 0, -1, (pay > 0).astype(np.int64))
    cat3 = np.where(pay < 0, -1, np.minimum(pay, 2))
    E = len(EXPERTS)
    L1 = np.array([e[0] for e in EXPERTS]); L2 = np.array([e[1] for e in EXPERTS])
    B = np.array([e[2] for e in EXPERTS])
    is3 = B == 3
    V = 9

    def regime(count):
        return (np.where(count < 100, p["lam_short"], p["lam"]),
                np.where(count < 100, p.get("prior_short", p["prior"]), p["prior"]))

    nobs = (pay >= 0).sum(axis=1)
    lam_m, prior_m = regime(nobs)          # champion: decided once from total coverage before the cutoff
    if running_regime:
        lam_m, prior_m = regime(np.zeros(M))
    W = np.zeros((M, E, V)); N = np.zeros((M, E, V))
    SE = p.get("size_experts", False)
    if SE:
        SL = np.zeros((M, E, V))
        SLL = np.zeros((M, E))
        R0 = np.array([SIZE_REGIMES[q["machine_type"]][0] for q in queries])
        R1 = np.array([SIZE_REGIMES[q["machine_type"]][1] for q in queries])
    LL = np.zeros((M, E))
    base_w = np.zeros(M); base_n = np.zeros(M)
    llr = np.zeros(M); size_cnt = np.zeros((M, 4))
    types = [q["machine_type"] for q in queries]
    logratio = np.zeros((M, 4))
    for m, ty in enumerate(types):
        logratio[m] = np.log(SIZE_REGIMES[ty][1]) - np.log(SIZE_REGIMES[ty][0])

    def context(t):
        def cat_at(lag):
            tt = t - lag
            out = np.full((M, E), -1, dtype=np.int64)
            ok = (tt >= 0)
            if ok.any():
                ttc = np.clip(tt, 0, T - 1)
                c2 = cat2[:, ttc]; c3 = cat3[:, ttc]
                out = np.where(is3[None, :], c3, c2)
                out = np.where(ok[None, :], out, -1)
            return out
        c1 = np.where((L1 == 0)[None, :], 0, cat_at(L1))
        c2 = np.where((L2 == 0)[None, :], 0, cat_at(L2))
        valid = (c1 >= 0) & (c2 >= 0)
        idx = np.where(valid, c1 * B[None, :] + c2, 0)
        return idx, valid

    def expert_probs(idx, valid):
        p0 = (base_w + p["prior"] * 0.5) / (base_n + p["prior"])
        w = np.take_along_axis(W, idx[:, :, None], 2)[:, :, 0]
        n = np.take_along_axis(N, idx[:, :, None], 2)[:, :, 0]
        pe = (w + prior_m[:, None] * p0[:, None]) / (n + prior_m[:, None])
        pe = np.where(valid, pe, p0[:, None])
        return np.clip(pe, p["clip"], 1 - p["clip"]), p0

    types_arr = np.array([q["machine_type"] for q in queries])
    tbal = (types_arr == "balanced").astype(float); tjac = (types_arr == "jackpot").astype(float)
    sig = np.array([float(q["signal"]) for q in queries])
    seen = np.zeros(M)

    def lg(x):
        x = np.clip(x, 1e-4, 1 - 1e-4); return np.log(x / (1 - x))

    def stack_features(pe, idx, logprior, tt):
        ep_ll = np.zeros((n_ep, E)); np.add.at(ep_ll, ep, LL)
        cnt = np.bincount(ep, minlength=n_ep)[:, None]
        sib = (ep_ll[ep] - LL) / np.maximum(cnt[ep] - 1, 1)
        sc = p["beta"] * (LL + p["ep_weight"] * sib)
        if logprior is not None:
            sc = sc + p.get("gamma", 0.0) * (logprior if logprior.ndim == 2 else logprior[None, :])
        sc = sc - sc.max(axis=1, keepdims=True)
        w = np.exp(sc); w /= w.sum(axis=1, keepdims=True)
        pmix = (w * pe).sum(axis=1)
        order = np.argsort(-w, axis=1)
        top, sec = order[:, 0], order[:, 1]
        r = np.arange(M)
        ptop, psec, wtop = pe[r, top], pe[r, sec], w[r, top]
        dis = np.sqrt((w * (pe - pmix[:, None]) ** 2).sum(axis=1))
        ntop = N[r, top, idx[r, top]]
        p0 = (base_w + p["prior"] * 0.5) / (base_n + p["prior"])
        lm = lg(pmix)
        F = np.column_stack([np.ones(M), lm, lg(ptop), lg(psec), lg(p0), wtop, dis, np.log1p(ntop),
                             lm * wtop, lm * dis, lm * np.log1p(ntop), tbal, tjac, sig, np.log1p(seen)])
        if extra is not None:
            F = np.column_stack([F, extra[:, tt]])
        return F, pmix

    row_prior = collect_logprior if collect_logprior is not None else expert_logprior
    XS, YS = [], []
    for t in range(T):
        obs = pay[:, t] >= 0
        if not obs.any():
            continue
        if running_regime:
            lam_m, prior_m = regime(seen)      # as of this tick: spins observed strictly before t
        win = (pay[:, t] > 0).astype(np.float64)
        idx, valid = context(t)
        pe, _ = expert_probs(idx, valid)
        if collect:
            Fk, _ = stack_features(pe, idx, row_prior, t)
            keep = obs & (seen >= 20)
            if keep.any():
                XS.append(Fk[keep]); YS.append(win[keep])
        o = obs[:, None]
        ll = np.where(win[:, None] > 0, np.log(pe), np.log(1 - pe))
        LL = np.where(o, LL * p["lam_ll"] + ll, LL)
        W = np.where(o[:, :, None], W * lam_m[:, None, None], W)
        N = np.where(o[:, :, None], N * lam_m[:, None, None], N)
        onehot = np.zeros((M, E, V)); np.put_along_axis(onehot, idx[:, :, None], 1.0, 2)
        upd = (o & valid)[:, :, None] * onehot
        W += upd * win[:, None, None]
        N += upd
        seen = seen + obs
        base_w = np.where(obs, base_w * p["base_lam"] + win, base_w)
        base_n = np.where(obs, base_n * p["base_lam"] + 1, base_n)
        wonm = obs & (pay[:, t] > 0)
        if wonm.any():
            s = np.clip(pay[:, t] - 1, 0, 3)
            if SE:
                lr = logratio[np.arange(M), s]
                sl = np.take_along_axis(SL, idx[:, :, None], 2)[:, :, 0]
                sl = np.where(valid, sl, llr[:, None])
                p1e = 1 / (1 + np.exp(-(sl + p["size_prior"])))
                pr_s0 = R0[np.arange(M), s][:, None]; pr_s1 = R1[np.arange(M), s][:, None]
                lik = (1 - p1e) * pr_s0 + p1e * pr_s1
                wm = wonm[:, None]
                SLL = np.where(wm, SLL * p.get("lam_sll", 0.99) + np.log(lik), SLL)
                SL = np.where(wm[:, :, None], SL * p.get("lam_s", 0.95), SL)
                add = (wm & valid)[:, :, None] * onehot * lr[:, None, None]
                SL += add
            llr = np.where(wonm, llr * p["lam_size"] + logratio[np.arange(M), s], llr)
            size_cnt = np.where(wonm[:, None], size_cnt * p["lam_size"], size_cnt)
            size_cnt[np.arange(M)[wonm], s[wonm]] += 1

    if running_regime:
        lam_m, prior_m = regime(seen)          # at the cutoff seen == nobs: identical rule to the champion
    out = {}
    pw_all = np.zeros(M)
    for tcut in np.unique(cut):
        sel = cut == tcut
        idx, valid = context(tcut)
        pe, _ = expert_probs(idx, valid)
        ep_ll = np.zeros((n_ep, E)); np.add.at(ep_ll, ep, LL)
        cnt = np.bincount(ep, minlength=n_ep)[:, None]
        sib = (ep_ll[ep] - LL) / np.maximum(cnt[ep] - 1, 1)
        score = p["beta"] * (LL + p["ep_weight"] * sib)
        if expert_logprior is not None:
            score = score + p.get("gamma", 0.0) * expert_logprior[None, :]
        score -= score.max(axis=1, keepdims=True)
        wts = np.exp(score); wts /= wts.sum(axis=1, keepdims=True)
        pw = (wts * pe).sum(axis=1)
        if stack_w is not None:
            Fc, _ = stack_features(pe, idx, expert_logprior, tcut)
            z = stack_w(Fc) if callable(stack_w) else Fc @ stack_w
            pw = np.clip(1 / (1 + np.exp(-z)), p["clip"], 1 - p["clip"])
        pw_all[sel] = pw[sel]
    post1 = 1 / (1 + np.exp(-(llr + p["size_prior"])))
    if SE:
        post_e = np.zeros(M)
        for tcut in np.unique(cut):
            sel = cut == tcut
            idx_c, valid_c = context(tcut)[:2]
            sl = np.take_along_axis(SL, idx_c[:, :, None], 2)[:, :, 0]
            sl = np.where(valid_c, sl, llr[:, None])
            p1e = 1 / (1 + np.exp(-(sl + p["size_prior"])))
            ep_s = np.zeros((n_ep, E)); np.add.at(ep_s, ep, SLL)
            cnt = np.bincount(ep, minlength=n_ep)[:, None]
            sib = (ep_s[ep] - SLL) / np.maximum(cnt[ep] - 1, 1)
            sc = p.get("beta_s", 1.0) * (SLL + p.get("ep_weight_s", 0.5) * sib)
            sc -= sc.max(axis=1, keepdims=True)
            w = np.exp(sc); w /= w.sum(axis=1, keepdims=True)
            post_e[sel] = (w * p1e).sum(axis=1)[sel]
        post1 = p.get("size_mix", 1.0) * post_e + (1 - p.get("size_mix", 1.0)) * post1
    for m, q in enumerate(queries):
        reg = SIZE_REGIMES[types[m]]
        size = (1 - post1[m]) * reg[0] + post1[m] * reg[1]
        pwm = float(pw_all[m])
        probs = [1 - pwm] + list(pwm * size)
        s = sum(probs)
        out[q["query_id"]] = tuple(x / s for x in probs)
    if collect:
        return out, np.vstack(XS), np.concatenate(YS)
    if return_ll:
        return out, LL
    return out

# =========================================================================== six-rule Bayesian model

PAIRS = ((1, 3), (2, 5), (4, 7))
HYPS = [(a, b, rule) for (a, b) in PAIRS for rule in ("xnor", "xor")]
NULL = len(HYPS)
K = NULL + 1


def _series(history, q):
    c = int(q["cutoff"])
    r = history[(q["episode_id"], q["machine_id"])]
    return {t: int(v > 0) for t, v in r.items() if t < c}, c


def _on(w, t, a, b, rule):
    if (t - a) not in w or (t - b) not in w:
        return None
    same = w[t - a] == w[t - b]
    return same if rule == "xnor" else not same


def run_machine(w, c, p_on, p_off, lam, base_lam=0.97, prior=None):
    """Online pass over observed ticks < c. Returns log-lik per hypothesis and prediction at c."""
    LL = np.zeros(K)
    bw, bn = 0.0, 0.0
    for t in sorted(w):
        rate = (bw + 0.5) / (bn + 1.0)
        y = w[t]
        preds = np.empty(K)
        for k, (a, b, rule) in enumerate(HYPS):
            on = _on(w, t, a, b, rule)
            preds[k] = rate if on is None else (p_on if on else p_off)
        preds[NULL] = rate
        preds = np.clip(preds, 1e-4, 1 - 1e-4)
        LL = lam * LL + np.where(y, np.log(preds), np.log(1 - preds))
        bw, bn = base_lam * bw + y, base_lam * bn + 1.0
    rate = (bw + 0.5) / (bn + 1.0)
    preds = np.empty(K)
    for k, (a, b, rule) in enumerate(HYPS):
        on = _on(w, c, a, b, rule)
        preds[k] = rate if on is None else (p_on if on else p_off)
    preds[NULL] = rate
    score = LL + (np.log(prior) if prior is not None else 0.0)
    post = np.exp(score - score.max()); post /= post.sum()
    return LL, float(np.clip(post @ preds, 1e-4, 1 - 1e-4)), post


class SWM:
    LAMS = (1.0, 0.99, 0.97)

    def fit(self, queries, history, labels):
        series = [_series(history, q) for q in queries]
        p_on, p_off = 0.9, 0.1
        for _ in range(3):  # pool on/off win rates from each machine's best hypothesis
            on_w = on_n = off_w = off_n = 0.0
            best = []
            for w, c in series:
                LL, _, _ = run_machine(w, c, p_on, p_off, 1.0)
                k = int(LL[:NULL].argmax()); best.append(k if LL[k] > LL[NULL] else NULL)
                if best[-1] == NULL:
                    continue
                a, b, rule = HYPS[k]
                for t in w:
                    on = _on(w, t, a, b, rule)
                    if on is None:
                        continue
                    if on: on_w += w[t]; on_n += 1
                    else: off_w += w[t]; off_n += 1
            p_on, p_off = (on_w + 1) / (on_n + 2), (off_w + 1) / (off_n + 2)
        counts = np.bincount(best, minlength=K) + 1.0
        self.prior = counts / counts.sum()
        self.p_on, self.p_off = p_on, p_off
        y = np.array([labels[q["query_id"]] > 0 for q in queries])
        best_lam = None
        for lam in self.LAMS:
            pw = np.array([run_machine(w, c, p_on, p_off, lam, prior=self.prior)[1] for w, c in series])
            ll = np.mean(np.where(y, np.log(pw), np.log(1 - pw)))
            if best_lam is None or ll > best_lam[0]:
                best_lam = (ll, lam)
        self.lam = best_lam[1]
        return self

    def predict_pw(self, queries, history):
        return {q["query_id"]: run_machine(*_series(history, q), self.p_on, self.p_off, self.lam, prior=self.prior)[1]
                for q in queries}


def swm_features(queries, history, m):
    """(M, T+1, 4) features at every tick t, from ticks < t only."""
    T = max(int(q["cutoff"]) for q in queries)
    out = np.zeros((len(queries), T + 1, 4))
    lp = np.log(m.prior)
    for i, q in enumerate(queries):
        c = int(q["cutoff"])
        w = {t: int(v > 0) for t, v in history[(q["episode_id"], q["machine_id"])].items() if t < c}
        LL = np.zeros(K); bw = bn = 0.0
        for t in range(T + 1):
            rate = (bw + 0.5) / (bn + 1.0)
            preds = np.empty(K)
            for k, (a, b, rule) in enumerate(HYPS):
                on = _on(w, t, a, b, rule) if t <= c else None
                preds[k] = rate if on is None else (m.p_on if on else m.p_off)
            preds[NULL] = rate
            preds = np.clip(preds, 1e-4, 1 - 1e-4)
            s = LL + lp; post = np.exp(s - s.max()); post /= post.sum()
            pw = float(np.clip(post @ preds, 1e-4, 1 - 1e-4)); lg = np.log(pw / (1 - pw)); mp = post[:NULL].max()
            out[i, t] = (lg, mp, post[NULL], lg * mp)
            if t in w:                       # update AFTER recording features for tick t
                y = w[t]
                LL = m.lam * LL + np.where(y, np.log(preds), np.log(1 - preds))
                bw, bn = 0.97 * bw + y, 0.97 * bn + 1.0
    return out


# =========================================================================== model

class StructuralStack(Serializable):
    """fit/predict_proba challenger. use_extra=False reproduces the champion exactly."""

    def __init__(self, use_extra=True):
        self.use_extra = use_extra
        self.params = json.loads(PARAMS.read_text())

    def fit(self, queries, history, labels):
        from sklearn.ensemble import HistGradientBoostingClassifier
        p = self.params
        _, LL = core_predict(queries, history, p, return_ll=True)
        wins = np.bincount(LL.argmax(1), minlength=len(EXPERTS)).astype(float)
        self.prior = np.log((wins + 1) / (wins.sum() + len(EXPERTS)))
        self.rules = SWM().fit(queries, history, labels) if self.use_extra else None
        ex = swm_features(queries, history, self.rules) if self.use_extra else None
        _, X, y = core_predict(queries, history, p, expert_logprior=self.prior, collect=True, extra=ex)
        self.model = HistGradientBoostingClassifier(learning_rate=p["stack_lr"], max_leaf_nodes=p["stack_leaves"],
            max_iter=p["stack_iters"], l2_regularization=p["stack_l2"], early_stopping=False, random_state=0).fit(X[:, 1:], y)
        return self

    def _stack(self, F):
        pr = np.clip(self.model.predict_proba(F[:, 1:])[:, 1], 1e-6, 1 - 1e-6)
        return np.log(pr / (1 - pr))

    def predict_proba(self, queries, history, extra=None):
        if extra is None and self.use_extra:
            extra = swm_features(queries, history, self.rules)
        pred = core_predict(queries, history, self.params, expert_logprior=self.prior, stack_w=self._stack, extra=extra)
        return validate_predictions(pred, queries)


def factory(config, cache_path=None):
    """#8 registry factory: {"family": "stat_structural_stack", "factory": "research.challengers.stat_structural_stack:factory"}."""
    return StructuralStack(use_extra=config.get("use_extra", True))
