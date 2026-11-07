"""
jaeger_model.py - JAEGERS House Edge forecaster.

Structure found in the simulator (from validation targets):
  * P(payout) = P(win) * P(size | win) + (1 - P(win)) on 0x.
  * P(win) is close to a switch, driven by the machine's own payouts at a pair
    of lags (e.g. 4&7, 1&3, 2&5); the mapping differs per machine and can drift
    or change abruptly.
  * P(size | win) takes one of two fixed shapes per machine type (two regimes).

Win model: a bank of "experts", one per lag context (single lags and lag pairs,
binary win/loss or 3-way 0/1/2+ categories). Each expert keeps exponentially
forgotten counts of wins per context value (per machine) and predicts with a
Beta prior centered on the machine's recent win rate. Experts are mixed by
softmax of their forgotten log-likelihood on that machine's own history, plus
the episode's (experts that predict well on sibling machines get a boost).

Size model: forgotten likelihood ratio between the two size regimes using the
machine's recent winning payouts, mixed with a forgotten empirical estimate.

Only observations strictly before each prediction tick are used. Missing ticks
are unknown (an expert whose context is missing abstains and falls back).
"""

from __future__ import annotations

import csv
import itertools
from collections import defaultdict

import numpy as np

PAYOUTS = (0, 1, 2, 5, 20)

# Size-given-win distributions over (1x, 2x, 5x, 20x) for the two regimes of each type
# (read off the public validation targets; they are simulator constants).
SIZE_REGIMES = {
    "steady":   np.array([[0.754, 0.197, 0.048, 0.001], [0.455, 0.436, 0.107, 0.002]]),
    "balanced": np.array([[0.500, 0.348, 0.130, 0.022], [0.214, 0.547, 0.205, 0.034]]),
    "jackpot":  np.array([[0.335, 0.245, 0.315, 0.105], [0.121, 0.324, 0.416, 0.139]]),
}

DEFAULTS = dict(
    lam=0.985, # forgetting factor for context counts (per tick)
    lam_short = 0.99,
    lam_ll=0.97,      # forgetting factor for expert log-likelihoods
    prior=2.0,        # Beta prior strength toward the machine's recent win rate
    beta=1.0,         # sharpness of expert weighting
    ep_weight=0.5,    # weight of sibling machines' log-likelihood #Look to tweek this weight
    lam_size=0.97,    # forgetting for size-regime evidence
    size_prior=0.0,   # prior log-odds for regime 1 vs 0
    clip=0.003,       # minimum probability for win / loss
    base_lam=0.97,    # forgetting for the machine's base win rate
)


def make_experts(max_lag=8):
    """(lag1, lag2, base): lag2 = 0 means a single-lalamg expert; base = 2 or 3 categories."""
    ex = [(0, 0, 1)]  # base expert: no context
    for base in (2, 3):
        for k in range(1, max_lag + 1):
            ex.append((k, 0, base))
        for k1, k2 in itertools.combinations(range(1, max_lag + 1), 2):
            ex.append((k1, k2, base))
    return ex


EXPERTS = make_experts()


def read_split(folder):
    with open(f"{folder}/queries.csv", newline="") as f:
        queries = list(csv.DictReader(f))
    hist = defaultdict(dict)
    with open(f"{folder}/history.csv", newline="") as f:
        for r in csv.DictReader(f):
            hist[(r["episode_id"], r["machine_id"])][int(r["tick"])] = int(r["payout"])
    return queries, hist


def predict(queries, hist, params=None, expert_logprior=None, return_ll=False, collect=False, stack_w=None):
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
    # episode index for sibling pooling
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

    nobs = (pay >= 0).sum(axis=1)                      # how many spins each machine has before its cutoff
    lam_m = np.where(nobs < 100, p["lam_short"], p["lam"])   # short histories remember longer
    prior_m = np.where(nobs < 100, p.get("prior_short", p["prior"]), p["prior"])   # short histories smooth more
    W = np.zeros((M, E, V)); N = np.zeros((M, E, V))
    # size experts: per (machine, expert, context) forgotten evidence (log-likelihood ratio mode1 vs mode0)
    SE = p.get("size_experts", False)
    if SE:
        SL = np.zeros((M, E, V))      # summed log-ratio of observed win sizes in each context
        SLL = np.zeros((M, E))        # forgotten log-likelihood of each size expert
        R0 = np.array([SIZE_REGIMES[q["machine_type"]][0] for q in queries])
        R1 = np.array([SIZE_REGIMES[q["machine_type"]][1] for q in queries])
    LL = np.zeros((M, E))
    base_w = np.zeros(M); base_n = np.zeros(M)
    # size regime evidence (log-likelihood ratio), and forgotten size counts
    llr = np.zeros(M); size_cnt = np.zeros((M, 4))
    types = [q["machine_type"] for q in queries]
    logratio = np.zeros((M, 4))
    for m, ty in enumerate(types):
        logratio[m] = np.log(SIZE_REGIMES[ty][1]) - np.log(SIZE_REGIMES[ty][0])

    rows = np.arange(M)[:, None]

    def context(t):
        """Context index per (machine, expert) at tick t, -1 if unavailable."""
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
        p0 = (base_w + p["prior"] * 0.5) / (base_n + p["prior"])  # machine's recent win rate
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

    def stack_features(pe, idx):
        """Features describing the expert blend for each machine (used by the stacking layer)."""
        ep_ll = np.zeros((n_ep, E)); np.add.at(ep_ll, ep, LL)
        cnt = np.bincount(ep, minlength=n_ep)[:, None]
        sib = (ep_ll[ep] - LL) / np.maximum(cnt[ep] - 1, 1)
        sc = p["beta"] * (LL + p["ep_weight"] * sib)
        if expert_logprior is not None:
            sc = sc + p.get("gamma", 0.0) * expert_logprior[None, :]
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

    XS, YS = [], []
    for t in range(T):
        obs = pay[:, t] >= 0
        if not obs.any():
            continue
        win = (pay[:, t] > 0).astype(np.float64)
        idx, valid = context(t)
        pe, _ = expert_probs(idx, valid)
        if collect:
            # training rows for the stacking layer: features from BEFORE this spin, label = this spin
            Fk, _ = stack_features(pe, idx)
            keep = obs & (seen >= 20)
            if keep.any():
                XS.append(Fk[keep]); YS.append(win[keep])
        o = obs[:, None]
        # log-likelihood of the realized outcome under each expert
        ll = np.where(win[:, None] > 0, np.log(pe), np.log(1 - pe))
        LL = np.where(o, LL * p["lam_ll"] + ll, LL)
        # update counts (forget everything for observed machines, then add)
        W = np.where(o[:, :, None], W * lam_m[:, None, None], W)
        N = np.where(o[:, :, None], N * lam_m[:, None, None], N)
        onehot = np.zeros((M, E, V)); np.put_along_axis(onehot, idx[:, :, None], 1.0, 2)
        upd = (o & valid)[:, :, None] * onehot
        W += upd * win[:, None, None]
        N += upd
        seen = seen + obs
        base_w = np.where(obs, base_w * p["base_lam"] + win, base_w)
        base_n = np.where(obs, base_n * p["base_lam"] + 1, base_n)
        # size evidence from winning spins
        wonm = obs & (pay[:, t] > 0)
        if wonm.any():
            s = np.clip(pay[:, t] - 1, 0, 3)
            if SE:
                lr = logratio[np.arange(M), s]                               # evidence carried by this win
                sl = np.take_along_axis(SL, idx[:, :, None], 2)[:, :, 0]     # each expert's evidence for current context
                sl = np.where(valid, sl, llr[:, None])                       # abstain -> machine-level evidence (before this win)
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

    # predict at each machine's cutoff
    out = {}
    pw_all = np.zeros(M)
    # contexts at cutoff (per machine its own t = cutoff)
    for tcut in np.unique(cut):
        sel = cut == tcut
        idx, valid = context(tcut)
        pe, _ = expert_probs(idx, valid)
        # episode pooling of log-likelihoods
        ep_ll = np.zeros((n_ep, E)); np.add.at(ep_ll, ep, LL)
        cnt = np.bincount(ep, minlength=n_ep)[:, None]
        sib = (ep_ll[ep] - LL) / np.maximum(cnt[ep] - 1, 1)
        score = p["beta"] * (LL + p["ep_weight"] * sib)
        if expert_logprior is not None:
            # head start for lag patterns that were common on the training machines
            score = score + p.get("gamma", 0.0) * expert_logprior[None, :]
        score -= score.max(axis=1, keepdims=True)
        wts = np.exp(score); wts /= wts.sum(axis=1, keepdims=True)
        pw = (wts * pe).sum(axis=1)
        if stack_w is not None:
            # stacking layer: corrects the blended win chance using the blend's features
            Fc, _ = stack_features(pe, idx)
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
        pw = float(pw_all[m])
        probs = [1 - pw] + list(pw * size)
        s = sum(probs)
        out[q["query_id"]] = tuple(x / s for x in probs)
    if collect:
        return out, np.vstack(XS), np.concatenate(YS)
    if return_ll:
        return out, LL
    return out


def learn_expert_prior(folder, params, smooth=1.0):
    """Count how often each expert ends up the most trusted one across the machines
    in `folder` (the round's train split) and return log-frequencies as a prior.
    Relearned from whatever data is mounted, so round two picks up its own patterns."""
    q, h = read_split(folder)
    _, LL = predict(q, h, params, return_ll=True)
    wins = np.bincount(LL.argmax(axis=1), minlength=len(EXPERTS)).astype(float)
    freq = (wins + smooth) / (wins.sum() + smooth * len(EXPERTS))
    return np.log(freq)


def fit_stacker(folder, params, expert_logprior=None):
    """Train the gradient-boosting stacking layer on the round's TRAIN machines.

    Every past tick (after 20 observed spins) becomes one row: features describe the
    expert blend using only earlier spins; the label is whether that spin won.
    Deterministic: fixed settings, no early stopping, random_state=0.
    Returns a function mapping feature rows -> log-odds of winning.
    """
    from sklearn.ensemble import HistGradientBoostingClassifier
    q, h = read_split(folder)
    _, X, y = predict(q, h, params, expert_logprior=expert_logprior, collect=True)
    model = HistGradientBoostingClassifier(
        learning_rate=params.get("stack_lr", 0.05), max_leaf_nodes=params.get("stack_leaves", 15),
        max_iter=params.get("stack_iters", 300), l2_regularization=params.get("stack_l2", 1.0),
        early_stopping=False, random_state=0).fit(X[:, 1:], y)

    def log_odds(F):
        pr = np.clip(model.predict_proba(F[:, 1:])[:, 1], 1e-6, 1 - 1e-6)
        return np.log(pr / (1 - pr))
    return log_odds


def score_validation(pred, folder="public/validation"):
    """Mean over conditions of (our error / reference error), as in the contest."""
    tg = {}
    with open(f"{folder}/targets.csv", newline="") as f:
        for r in csv.DictReader(f):
            tg[r["query_id"]] = (r["episode_id"], np.array([float(r[f"p_{k}"]) for k in PAYOUTS]))
    ref = {}
    with open(f"{folder}/reference.csv", newline="") as f:
        for r in csv.DictReader(f):
            ref[r["query_id"]] = np.array([float(r[f"p_{k}"]) for k in PAYOUTS])
    cond = {}
    with open(f"{folder}/conditions.csv", newline="") as f:
        for r in csv.DictReader(f):
            cond[r["query_id"]] = r["condition"]
    res = {}
    for c in sorted(set(cond.values())):
        e_ep, b_ep = defaultdict(list), defaultdict(list)
        for qid, cc in cond.items():
            if cc != c:
                continue
            e, t = tg[qid]
            e_ep[e].append(((np.array(pred[qid]) - t) ** 2).sum())
            b_ep[e].append(((ref[qid] - t) ** 2).sum())
        E = np.mean([np.mean(v) for v in e_ep.values()])
        Bv = np.mean([np.mean(v) for v in b_ep.values()])
        res[c] = E / Bv
    R = float(np.mean(list(res.values())))
    return R, res, 60 / (1 + R)
