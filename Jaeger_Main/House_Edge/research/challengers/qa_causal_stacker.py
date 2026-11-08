"""HE-03 follow-up: as-of ("causal") stacker challenger for the JAEGERS champion.

Pre-registered in research/configs/qa_causal_stacker/plan.json. The protected champion
(jaegers_entry/jaeger_model.py, sha256 LF 10da55e6...) is never edited: `core_predict` is a copy of its
`predict()` with three switchable fixes for the train/serve look-aheads found by the #3 audit:

  running_regime  lam/prior regime from observed spins SO FAR (seen < 100) at each tick, not from the
                  machine's total pre-cutoff coverage
  collect_logprior  per-row expert log-prior for the stacker's historical rows (cross-fitted by episode group),
                  so a row never sees its own machine's final log-likelihood
  (signal)        handled by the model class: historical rows drop column 13; signal re-enters only through a
                  query-time logistic head fitted on fit-split QUERY rows

With every fix off, `core_predict` must equal the champion's `predict` exactly (parity test).
Constants (EXPERTS, SIZE_REGIMES, DEFAULTS, PAYOUTS) are read from the champion module, not duplicated.
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
SIGNAL_COL = 13
GROUPS = 4


def champion_module():
    spec = importlib.util.spec_from_file_location("qa_causal_champion_core", CHAMPION)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


C = champion_module()
EXPERTS, SIZE_REGIMES, DEFAULTS, PAYOUTS = C.EXPERTS, C.SIZE_REGIMES, C.DEFAULTS, C.PAYOUTS


def core_predict(queries, hist, params=None, expert_logprior=None, return_ll=False, collect=False, stack_w=None,
                 running_regime=False, collect_logprior=None):
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

    def stack_features(pe, idx, logprior):
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
            Fk, _ = stack_features(pe, idx, row_prior)
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
            Fc, _ = stack_features(pe, idx, expert_logprior)
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


# --------------------------------------------------------------------------- priors

def logprior_from_ll(LL, smooth=1.0):
    wins = np.bincount(LL.argmax(axis=1), minlength=len(EXPERTS)).astype(float)
    return np.log((wins + smooth) / (wins.sum() + smooth * len(EXPERTS)))


def episode_groups(queries, k=GROUPS):
    eps = sorted({q["episode_id"] for q in queries})
    gid = {e: i % k for i, e in enumerate(eps)}
    return np.array([gid[q["episode_id"]] for q in queries])


# --------------------------------------------------------------------------- model

class CausalStacker(Serializable):
    """fit/predict_proba challenger. All three fixes off == the champion (JaegerModel)."""

    def __init__(self, signal_head=True, drop_signal=True, running_regime=True, crossfit_prior=True):
        self.signal_head, self.drop_signal = signal_head, drop_signal
        self.running_regime, self.crossfit_prior = running_regime, crossfit_prior
        self.params = json.loads(PARAMS.read_text())

    def fit(self, queries, history, labels=None):
        p = self.params
        _, LL = core_predict(queries, history, p, return_ll=True, running_regime=self.running_regime)
        self.prior = logprior_from_ll(LL)
        rows = None
        if self.crossfit_prior:
            g = episode_groups(queries)
            rows = np.zeros((len(queries), len(EXPERTS)))
            for k in np.unique(g):
                rows[g == k] = logprior_from_ll(LL[g != k])[None, :]
        from sklearn.ensemble import HistGradientBoostingClassifier
        _, X, y = core_predict(queries, history, p, expert_logprior=self.prior, collect=True,
                               running_regime=self.running_regime, collect_logprior=rows)
        self.cols = [i for i in range(1, X.shape[1]) if not (self.drop_signal and i == SIGNAL_COL)]
        self.model = HistGradientBoostingClassifier(
            learning_rate=p.get("stack_lr", 0.05), max_leaf_nodes=p.get("stack_leaves", 15),
            max_iter=p.get("stack_iters", 300), l2_regularization=p.get("stack_l2", 1.0),
            early_stopping=False, random_state=0).fit(X[:, self.cols], y)
        self.head = None
        if self.signal_head:
            if labels is None:
                raise ValueError("signal_head needs fit-split query labels")
            base = self._base(queries, history)
            Z = self._head_inputs(base, queries)
            yq = np.array([labels[q["query_id"]] > 0 for q in queries], dtype=int)
            from sklearn.linear_model import LogisticRegression
            self.head = LogisticRegression(C=1.0, max_iter=1000).fit(Z, yq)
        return self

    def _stack(self, F):
        pr = np.clip(self.model.predict_proba(F[:, self.cols])[:, 1], 1e-6, 1 - 1e-6)
        return np.log(pr / (1 - pr))

    def _base(self, queries, history):
        return core_predict(queries, history, self.params, expert_logprior=self.prior, stack_w=self._stack,
                            running_regime=self.running_regime)

    @staticmethod
    def _head_inputs(base, queries):
        pw = np.clip(np.array([1 - base[q["query_id"]][0] for q in queries]), 1e-4, 1 - 1e-4)
        sig = np.array([int(float(q["signal"])) + 1 for q in queries])
        return np.column_stack([np.log(pw / (1 - pw)), np.eye(3)[sig]])

    def predict_proba(self, queries, history):
        base = self._base(queries, history)
        if self.head is None:
            return validate_predictions(base, queries)
        clip = self.params.get("clip", 0.03)
        pw_new = np.clip(self.head.predict_proba(self._head_inputs(base, queries))[:, 1], clip, 1 - clip)
        out = {}
        for q, pw in zip(queries, pw_new):
            b = np.asarray(base[q["query_id"]])
            size = b[1:] / b[1:].sum()
            v = np.concatenate([[1 - pw], pw * size])
            out[q["query_id"]] = v / v.sum()
        return validate_predictions(out, queries)


VARIANTS = {
    "parity": dict(signal_head=False, drop_signal=False, running_regime=False, crossfit_prior=False),
    "causal_all": dict(signal_head=True, drop_signal=True, running_regime=True, crossfit_prior=True),
    "causal_all_nohead": dict(signal_head=False, drop_signal=True, running_regime=True, crossfit_prior=True),
    "regime_only": dict(signal_head=False, drop_signal=False, running_regime=True, crossfit_prior=False),
    "prior_only": dict(signal_head=False, drop_signal=False, running_regime=False, crossfit_prior=True),
}


def factory(config, cache_path=None):
    name = config.get("variant")
    if name not in VARIANTS:
        raise ValueError(f"Unknown causal-stacker variant {name!r}; expected one of {sorted(VARIANTS)}")
    return CausalStacker(**VARIANTS[name])
