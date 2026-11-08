"""HE-07 additive extension (lane C): size-given-win and win-streak/recency features.

Not wired into ``research/features.py``; lane A owns the registry and decides on integration.
Every value is computed from ``FeatureComputer._past`` (ticks strictly before the row's cutoff),
so it obeys the same as-of contract as the registry. Missing ticks are never read as losses:
streaks stop at the first unobserved tick, and recency counts elapsed ticks, not observed spins.

Columns (prefix ``qa_size_streak/``):
  size_given_win_{0..3}  decayed distribution over (1x, 2x, 5x, 20x) among past WINS (+0.5 smoothing)
  win_mass               log1p of decayed win count behind that distribution
  ticks_since_win        elapsed ticks since the last observed win (cutoff if none), log1p
  ever_won               1 if any past win observed
  streak_len             length of the run of identical win/loss outcomes ending at cutoff-1,
                         counted over CONSECUTIVE observed ticks only (0 if cutoff-1 is missing)
  streak_is_win          1 if that run is wins, 0 if losses or no run
"""
from __future__ import annotations

import numpy as np

GROUP = "qa_size_streak"
DECAY = 0.97
NAMES = tuple(f"{GROUP}/{n}" for n in (
    "size_given_win_0", "size_given_win_1", "size_given_win_2", "size_given_win_3",
    "win_mass", "ticks_since_win", "ever_won", "streak_len", "streak_is_win"))


def row(computer, query, decay=DECAY):
    """Feature vector for one query (or historical origin) using only ticks < cutoff."""
    cutoff = int(query["cutoff"])
    ticks, labels = computer._past(query["episode_id"], query["machine_id"], cutoff)
    wins = labels > 0
    w = decay ** (cutoff - 1 - ticks[wins])
    size = np.bincount(labels[wins] - 1, weights=w, minlength=4).astype(float) + 0.5
    size /= size.sum()
    last_win = ticks[wins][-1] if wins.any() else None
    since = cutoff - last_win if last_win is not None else cutoff

    streak, is_win = 0, 0.0
    if len(ticks) and ticks[-1] == cutoff - 1:
        is_win = float(wins[-1])
        expect = cutoff - 1
        for t, won in zip(ticks[::-1], wins[::-1]):
            if t != expect or won != wins[-1]:
                break
            streak += 1
            expect -= 1
    values = np.concatenate([size, [np.log1p(w.sum()), np.log1p(since), float(wins.any()),
                                    float(streak), is_win if streak else 0.0]])
    return values.astype(np.float32), list(NAMES)
