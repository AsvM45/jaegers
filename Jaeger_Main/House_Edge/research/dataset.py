"""Hashed as-of feature cache and deterministic whole-episode fold manifests."""
import csv
from pathlib import Path
import numpy as np
from .common import digest, file_hash, tree_hashes, write_json
from .feature_api import FeatureComputer, HISTORICAL_GROUPS
from .adapters import core_module, PAYOUTS


def read_labels(folder):
    with (Path(folder) / "labels.csv").open(newline="") as stream:
        return {r["query_id"]: PAYOUTS.index(int(r["outcome"])) for r in csv.DictReader(stream)}


def episode_folds(queries, conditions, count=4):
    grouped = {}
    for q in queries:
        ep, condition = q["episode_id"], conditions[q["query_id"]]
        if ep in grouped and grouped[ep] != condition:
            raise ValueError("Episode crosses condition labels")
        grouped[ep] = condition
    folds = {}
    for condition in sorted(set(grouped.values())):
        ordered = sorted((ep for ep, c in grouped.items() if c == condition), key=digest)
        if len(ordered) < count:
            raise ValueError("Insufficient episodes per condition for grouped CV")
        for index, ep in enumerate(ordered):
            folds[ep] = index % count
    return folds


def conditions(folder):
    with (Path(folder) / "conditions.csv").open(newline="") as stream:
        return {r["query_id"]: r["condition"] for r in csv.DictReader(stream)}


def build_cache(data, cache, stride=8, max_rows=24):
    data, cache = Path(data).resolve(), Path(cache).resolve()
    folder = data / "train"
    identity = {"inputs": tree_hashes(folder), "features": file_hash(Path(__file__).with_name("feature_api.py")),
                "feature_plugins": tree_hashes(Path(__file__).parent / "features"),
                "feature_extensions": tree_hashes(Path(__file__).parent / "extensions"),
                "reader": file_hash(Path(core_module().__file__)),
                "adapters": file_hash(Path(__file__).with_name("adapters.py")),
                "dataset": file_hash(__file__), "stride": stride, "max_rows": max_rows}
    key = digest(identity)
    destination = cache / key
    if (destination / "complete.json").exists():
        return destination
    destination.mkdir(parents=True, exist_ok=True)
    queries, history = core_module().read_split(str(folder))
    labels = read_labels(folder)
    computer = FeatureComputer(history)
    X, y, episodes, ticks, kinds, ids = [], [], [], [], [], []
    names = None
    for q in queries:
        observed = sorted(t for t in history[(q["episode_id"], q["machine_id"])] if t < int(q["cutoff"]))
        selected = observed[20::stride][-max_rows:]
        for t in selected:
            sample = dict(q, cutoff=str(t))
            values, names = computer.row(sample)
            X.append(values); y.append(PAYOUTS.index(history[(q["episode_id"], q["machine_id"])][t]))
            episodes.append(q["episode_id"]); ticks.append(t); kinds.append("historical"); ids.append(q["query_id"]+f"@{t}")
        values, names = computer.row(q)
        X.append(values); y.append(labels[q["query_id"]]); episodes.append(q["episode_id"])
        ticks.append(int(q["cutoff"])); kinds.append("query"); ids.append(q["query_id"])
    # No pickle/object arrays: cache is data, never executable serialization.
    np.savez_compressed(destination / "train.npz", X=np.array(X, dtype=np.float32), y=np.array(y),
                        episode=np.array(episodes), tick=np.array(ticks), kind=np.array(kinds), query_id=np.array(ids))
    write_json(destination / "complete.json", {"identity": identity, "key": key, "rows": len(y),
               "columns": names, "groups": list(HISTORICAL_GROUPS), "historical_signal_policy": "omitted",
               "static_machine_type_assumption": "type is an intrinsic episode machine category",
               "archive_sha256": file_hash(destination / "train.npz")})
    return destination
