"""Sampled-label diagnostics; never mislabeled as official competition points."""
from collections import defaultdict
import numpy as np


def diagnostics(predictions, queries, labels, conditions):
    by_episode = defaultdict(list)
    rows, per_query = [], []
    for q in queries:
        key = q["query_id"]
        p = np.array(predictions[key], dtype=float)
        y = labels[key]
        loss = float(np.sum((p-np.eye(5)[y])**2))
        by_episode[q["episode_id"]].append(loss)
        rows.append((p,y))
        per_query.append({"query_id": key, "episode_id": q["episode_id"], "condition": conditions[key],
                          "label": int(y), "brier": loss, "probabilities": p.tolist()})
    ep_condition = {q["episode_id"]:conditions[q["query_id"]] for q in queries}
    episodes = {ep:float(np.mean(v)) for ep,v in by_episode.items()}
    per_condition = {c:float(np.mean([v for ep,v in episodes.items() if ep_condition[ep] == c]))
                     for c in sorted(set(ep_condition.values()))}
    p = np.array([r[0] for r in rows]); y = np.array([r[1] for r in rows])
    calibration = []
    for k in range(5):
        for b in range(10):
            mask = (p[:,k] >= b/10) & (p[:,k] < (b+1)/10 if b < 9 else p[:,k] <= 1)
            if mask.any():
                calibration.append({"class": k, "bin": b, "count": int(mask.sum()),
                                    "predicted": float(p[mask,k].mean()), "observed": float((y[mask] == k).mean())})
    return {"evaluation_source": "sampled_outcome_group_cv", "official_points": None,
            "mean_brier": float(np.mean(list(per_condition.values()))), "by_condition": per_condition,
            "per_episode": episodes, "episode_conditions": ep_condition, "per_query": per_query,
            "log_loss": float(-np.log(np.clip(p[np.arange(len(y)),y], 1e-12,1)).mean()),
            "class_brier": np.mean((p-np.eye(5)[y])**2,axis=0).tolist(),
            "class_counts": np.bincount(y,minlength=5).tolist(), "calibration": calibration}


def paired(candidate, baseline, bootstrap=2000, seed=0):
    if set(candidate["per_episode"]) != set(baseline["per_episode"]):
        raise ValueError("Paired comparison requires identical held-out episodes")
    if candidate["episode_conditions"] != baseline["episode_conditions"]:
        raise ValueError("Paired comparison condition mapping differs")
    differences = {ep:candidate["per_episode"][ep]-baseline["per_episode"][ep] for ep in baseline["per_episode"]}
    rng = np.random.default_rng(seed)
    draws = np.zeros(bootstrap)
    groups = sorted(set(baseline["episode_conditions"].values()))
    means = []
    for c in groups:
        values = np.array([d for ep,d in differences.items() if baseline["episode_conditions"][ep] == c])
        means.append(values.mean())
        draws += rng.choice(values, size=(bootstrap,len(values)),replace=True).mean(axis=1)/len(groups)
    return {"mean_delta_brier": float(np.mean(means)), "ci95": np.quantile(draws,[.025,.975]).tolist(),
            "episodes": len(differences), "bootstrap": bootstrap, "seed": seed,
            "supported_improvement": bool(np.quantile(draws,.975) < 0)}
