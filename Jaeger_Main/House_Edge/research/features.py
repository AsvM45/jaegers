"""Observable feature registry. Every payout lookup is strictly before target tick."""
from dataclasses import dataclass
from itertools import combinations
import numpy as np
from .models import PAYOUTS


@dataclass(frozen=True)
class Group:
    dependencies: tuple = ()
    availability: str = "past_only"


REGISTRY = {
    "type": Group(availability="static_machine_type"),
    "lags": Group(), "pairs": Group(("lags",)), "windows": Group(), "decays": Group(),
    "transitions": Group(("lags",)), "missingness": Group(), "changes": Group(("windows",)),
    "peers": Group(), "type_lag": Group(("type", "lags")),
    "current_signal": Group(availability="query_only"),
}
HISTORICAL_GROUPS = tuple(k for k in REGISTRY if k != "current_signal")


def validate_groups(groups, historical=True):
    if not groups or len(groups) != len(set(groups)) or set(groups)-REGISTRY.keys():
        raise ValueError("Feature groups must be nonempty, unique registry members")
    for group in groups:
        missing = set(REGISTRY[group].dependencies)-set(groups)
        if missing:
            raise ValueError(f"{group} requires {sorted(missing)}")
        if historical and REGISTRY[group].availability == "query_only":
            raise ValueError("Current signal is unavailable for historical supervision")


class FeatureComputer:
    def __init__(self, history):
        self.history = history
        self.arrays = {}
        self.episodes = {}
        for (episode, machine), rows in history.items():
            ordered = sorted(rows.items())
            ticks = np.array([t for t, _ in ordered], dtype=np.int32)
            labels = np.array([PAYOUTS.index(y) for _, y in ordered], dtype=np.int8)
            self.arrays[(episode, machine)] = (ticks, labels)
            self.episodes.setdefault(episode, []).append(machine)

    def _past(self, episode, machine, cutoff):
        ticks, labels = self.arrays[(episode, machine)]
        stop = np.searchsorted(ticks, cutoff, side="left")
        return ticks[:stop], labels[:stop]

    def row(self, query, groups=HISTORICAL_GROUPS):
        cutoff = int(query["cutoff"])
        episode, machine = query["episode_id"], query["machine_id"]
        ticks, labels = self._past(episode, machine, cutoff)
        rows = self.history[(episode, machine)]
        past = {int(t): int(y) for t, y in zip(ticks, labels)}
        lag = [past.get(cutoff-k, -1) for k in range(1, 9)]
        type_index = ("steady", "balanced", "jackpot").index(query["machine_type"])
        output, names = [], []

        def add(name, values):
            values = np.atleast_1d(values)
            output.extend(values.tolist())
            names.extend([f"{group}/{name}_{i}" for i in range(len(values))])

        def distribution(values, weights=None):
            counts = np.bincount(values, weights=weights, minlength=5).astype(float)+.5
            return counts / counts.sum()

        for group in groups:
            if group == "type":
                add("onehot", np.eye(3)[type_index])
            elif group == "lags":
                for k, value in enumerate(lag, 1):
                    add(f"lag{k}", np.eye(6)[value+1])
            elif group == "pairs":
                for a, b in combinations(range(8), 2):
                    ca = -1 if lag[a] < 0 else min(lag[a], 2)
                    cb = -1 if lag[b] < 0 else min(lag[b], 2)
                    index = 0 if ca < 0 or cb < 0 else 1+ca*3+cb
                    add(f"pair{a+1}_{b+1}", np.eye(10)[index])
            elif group == "windows":
                for width in (8, 24, 64):
                    values = labels[ticks >= cutoff-width]
                    add(f"freq{width}", distribution(values))
                    add(f"count{width}", np.log1p(len(values)))
            elif group == "decays":
                for decay in (.9, .97, .995):
                    weights = decay ** (cutoff-1-ticks)
                    add(f"freq{decay}", distribution(labels, weights))
                    add(f"mass{decay}", np.log1p(weights.sum()))
            elif group == "transitions":
                for k in range(1, 9):
                    values = [y for t, y in past.items() if lag[k-1] >= 0 and past.get(t-k, -2) == lag[k-1]]
                    add(f"conditional{k}", distribution(values))
                    add(f"count{k}", np.log1p(len(values)))
            elif group == "missingness":
                add("coverage", [len(ticks)/max(cutoff, 1), np.log1p(len(ticks)),
                                  cutoff-1-ticks[-1] if len(ticks) else cutoff])
                add("lag_known", [v >= 0 for v in lag])
            elif group == "changes":
                recent = distribution(labels[ticks >= cutoff-24])
                earlier = distribution(labels[(ticks >= cutoff-64) & (ticks < cutoff-24)])
                add("recent_minus_past", recent-earlier)
                add("distance", [np.abs(recent-earlier).sum(), -np.sum(recent*np.log(recent))])
            elif group == "peers":
                counts = np.zeros(5)
                peer_recent = np.zeros(5)
                for other in self.episodes[episode]:
                    if other != machine:
                        tt, yy = self._past(episode, other, cutoff)
                        counts += np.bincount(yy, minlength=5)
                        peer_recent += np.bincount(yy[tt >= cutoff-24], minlength=5)
                add("freq", (counts+.5)/(counts.sum()+2.5))
                add("recent", (peer_recent+.5)/(peer_recent.sum()+2.5))
                add("mass", np.log1p(counts.sum()))
            elif group == "type_lag":
                wins = np.array([0 if x < 0 else float(x > 0) for x in lag])
                add("interaction", (np.eye(3)[type_index, :, None]*wins[None, :]).ravel())
            elif group == "current_signal":
                add("signal", np.eye(3)[int(query["signal"])+1])
            else:
                raise ValueError(group)
        return np.asarray(output, dtype=np.float32), names


def feature_columns(names, groups, historical=True):
    validate_groups(groups, historical)
    return np.array([i for i, name in enumerate(names) if name.split("/")[0] in groups], dtype=int)
