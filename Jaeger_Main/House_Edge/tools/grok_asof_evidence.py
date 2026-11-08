"""Independent as-of witness for the champion historical stacker.

Calls ``jaegers_entry/jaeger_model.py`` on synthetic episodes. It does not fit the
gradient-boosting stacker, does not read the public splits, and does not modify
the champion. A passing witness means the measured channel is present. It is not
a certification that organizers accept the frozen entry.
"""

from __future__ import annotations

import csv
import hashlib
import importlib.util
import json
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np

HOUSE = Path(__file__).resolve().parents[1]
REPO = HOUSE.parents[1]
MODEL_PATH = HOUSE / "jaegers_entry" / "jaeger_model.py"
PARAMS_PATH = HOUSE / "jaegers_entry" / "params.json"
RULES_PATH = HOUSE / "RULES.md"
DATA_PATH = HOUSE / "DATA.md"

RULES_ASOF = (
    "Use observations strictly before the prediction tick, including when making "
    "training examples from earlier history."
)
DATA_FUTURE_FEATURE = (
    "When building training examples from history, a future observation can be a "
    "label for its earlier prediction, but never a feature for that prediction."
)
DATA_SIGNAL = "the observable `signal` is -1, 0, or 1."

# stack_features column order in jaeger_model.py. Column 0 is dropped by fit_stacker.
COLUMNS = (
    {"index": 0, "name": "ones", "family": "constant",
     "source": "np.ones inside stack_features",
     "allowed": "not a tick observation",
     "role": "Dropped before HistGradientBoosting (X[:, 1:])."},
    {"index": 1, "name": "logit_blend", "family": "expert_blend",
     "source": "logit of the softmax mixture of expert win probabilities",
     "allowed": "payouts at ticks < t, same episode",
     "role": "Weights include gamma * expert_logprior and counts decayed by the final-coverage regime."},
    {"index": 2, "name": "logit_top_expert", "family": "expert_blend",
     "source": "logit of the highest-weight expert's win probability",
     "allowed": "payouts at ticks < t, same episode",
     "role": "The selected expert depends on weights. Those weights include the prior and the final-coverage regime."},
    {"index": 3, "name": "logit_second_expert", "family": "expert_blend",
     "source": "logit of the second-highest-weight expert's win probability",
     "allowed": "payouts at ticks < t, same episode",
     "role": "Same selection path as logit_top_expert."},
    {"index": 4, "name": "logit_base_rate", "family": "base_rate",
     "source": "forgotten base win rate using base_lam and the fixed prior strength",
     "allowed": "this machine's payouts at ticks < t",
     "role": "Does not read expert weights, expert_logprior, lam_short, or prior_short."},
    {"index": 5, "name": "top_weight", "family": "expert_blend",
     "source": "softmax weight of the top expert",
     "allowed": "payouts at ticks < t, same episode",
     "role": "Directly reads the weight vector that adds gamma * expert_logprior."},
    {"index": 6, "name": "disagreement", "family": "expert_blend",
     "source": "weight-standard-deviation of expert win probabilities",
     "allowed": "payouts at ticks < t, same episode",
     "role": "Uses the same prior-shifted weights."},
    {"index": 7, "name": "log1p_top_count", "family": "expert_blend",
     "source": "log1p of the selected expert's forgotten count in the current context",
     "allowed": "payouts at ticks < t, same episode",
     "role": "The count state is as-of. Which expert is selected can depend on the prior and on final coverage."},
    {"index": 8, "name": "blend_times_top_weight", "family": "interaction",
     "source": "logit_blend * top_weight",
     "allowed": "payouts at ticks < t, same episode",
     "role": "Inherits whichever parent moved."},
    {"index": 9, "name": "blend_times_disagreement", "family": "interaction",
     "source": "logit_blend * disagreement",
     "allowed": "payouts at ticks < t, same episode",
     "role": "Inherits whichever parent moved."},
    {"index": 10, "name": "blend_times_log1p_top_count", "family": "interaction",
     "source": "logit_blend * log1p_top_count",
     "allowed": "payouts at ticks < t, same episode",
     "role": "Inherits whichever parent moved."},
    {"index": 11, "name": "type_balanced", "family": "static_type",
     "source": "1 if query machine_type is balanced",
     "allowed": "static query field",
     "role": "Not computed from payout ticks."},
    {"index": 12, "name": "type_jackpot", "family": "static_type",
     "source": "1 if query machine_type is jackpot",
     "allowed": "static query field",
     "role": "Not computed from payout ticks."},
    {"index": 13, "name": "query_signal", "family": "query_signal",
     "source": "float(query signal) copied into every historical row",
     "allowed": "RULES.md does not define a per-tick signal",
     "role": "The value is the cutoff query's signal, not a signal measured at t."},
    {"index": 14, "name": "log1p_seen", "family": "asof_count",
     "source": "log1p of observed spins strictly before t",
     "allowed": "observed ticks < t on this machine",
     "role": "Incremented only after the row snapshot."},
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _git_head() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=REPO, text=True, stderr=subprocess.DEVNULL
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        return "UNAVAILABLE"


def load_champion():
    spec = importlib.util.spec_from_file_location("jaeger_champion_asof_witness", MODEL_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    params = json.loads(PARAMS_PATH.read_text(encoding="utf-8"))
    return module, params


def _pattern(kind: str, n: int) -> list[int]:
    if kind == "alt":
        return [0 if t % 2 == 0 else 1 for t in range(n)]
    if kind == "persist":
        return [0 if (t // 8) % 2 == 0 else 1 for t in range(n)]
    if kind == "zeros":
        return [0] * n
    raise ValueError(kind)


def _query(qid, episode, machine, machine_type, signal, cutoff) -> dict:
    return {
        "query_id": qid,
        "episode_id": episode,
        "machine_id": machine,
        "machine_type": machine_type,
        "signal": str(signal),
        "cutoff": str(cutoff),
    }


def _write_split(folder: Path, queries, history) -> None:
    columns = ("query_id", "episode_id", "machine_id", "machine_type", "signal", "cutoff")
    with (folder / "queries.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        writer.writerows(queries)
    with (folder / "history.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(("episode_id", "machine_id", "tick", "payout"))
        for (episode, machine), rows in history.items():
            for tick, payout in sorted(rows.items()):
                writer.writerow((episode, machine, tick, payout))


def _learn_prior(module, queries, history, params):
    with tempfile.TemporaryDirectory(prefix="grok-asof-") as directory:
        _write_split(Path(directory), queries, history)
        return module.learn_expert_prior(directory, params)


def _row(features, tick: int, n_queries: int, query_index: int = 0):
    """Row collected at ``tick`` when every earlier tick is observed for every query."""
    return features[(tick - 20) * n_queries + query_index]


def _abs_delta(left, right) -> list[float]:
    return [float(x) for x in np.abs(np.asarray(left) - np.asarray(right))]


def _pair(module, params, left, right, tick: int, n_queries: int, query_index: int = 0):
    """Compare one historical row when each side learns its own full-history prior."""
    prior_left = _learn_prior(module, *left, params)
    prior_right = _learn_prior(module, *right, params)
    _, x_left, y_left = module.predict(*left, params, expert_logprior=prior_left, collect=True)
    _, x_right, y_right = module.predict(*right, params, expert_logprior=prior_right, collect=True)
    row_left = _row(x_left, tick, n_queries, query_index)
    row_right = _row(x_right, tick, n_queries, query_index)
    blocked = dict(params)
    blocked["gamma"] = 0.0
    prior_left_g = _learn_prior(module, *left, blocked)
    prior_right_g = _learn_prior(module, *right, blocked)
    _, g_left, _ = module.predict(*left, blocked, expert_logprior=prior_left_g, collect=True)
    _, g_right, _ = module.predict(*right, blocked, expert_logprior=prior_right_g, collect=True)
    _, f_left, _ = module.predict(*left, params, expert_logprior=prior_left, collect=True)
    _, f_right, _ = module.predict(*right, params, expert_logprior=prior_left, collect=True)
    return {
        "prior_max_abs": float(np.max(np.abs(prior_left - prior_right))),
        "prior_argmax": [int(np.argmax(prior_left)), int(np.argmax(prior_right))],
        "row_abs_delta": _abs_delta(row_left, row_right),
        "labels": [float(y_left[(tick - 20) * n_queries + query_index]),
                   float(y_right[(tick - 20) * n_queries + query_index])],
        "seen": [float(row_left[14]), float(row_right[14])],
        "gamma0_rows_equal": bool(np.array_equal(_row(g_left, tick, n_queries, query_index),
                                                 _row(g_right, tick, n_queries, query_index))),
        "frozen_prior_rows_equal": bool(np.array_equal(_row(f_left, tick, n_queries, query_index),
                                                       _row(f_right, tick, n_queries, query_index))),
    }


def _history_pair(early: str, late_left: str, late_right: str, cutoff: int, switch: int):
    def build(late: str):
        values = _pattern(early, switch) + _pattern(late, cutoff - switch)
        queries = [_query("q0", "e0", "m0", "steady", "0", cutoff)]
        history = {("e0", "m0"): {t: values[t] for t in range(cutoff)}}
        return queries, history
    return build(late_left), build(late_right)


def _other_episode(late_b: str, cutoff=160, switch=40):
    series_a = _pattern("alt", cutoff)
    series_b = _pattern("alt", switch) + _pattern(late_b, cutoff - switch)
    queries = [
        _query("qA", "eA", "mA", "steady", "0", cutoff),
        _query("qB", "eB", "mB", "jackpot", "1", cutoff),
    ]
    history = {
        ("eA", "mA"): {t: series_a[t] for t in range(cutoff)},
        ("eB", "mB"): {t: series_b[t] for t in range(cutoff)},
    }
    return queries, history


def _coverage(module, params, delete: bool, matched: bool, cutoff=128, tick=30):
    values = _pattern("alt", cutoff)
    queries = [_query("q0", "e0", "m0", "steady", "0", cutoff)]
    rows = {t: values[t] for t in range(cutoff)}
    if delete:
        for t in range(70, cutoff):
            del rows[t]
    used = dict(params)
    if matched:
        used["lam_short"] = used["lam"]
        used["prior_short"] = used["prior"]
    _, features, _ = module.predict(queries, {("e0", "m0"): rows}, used, expert_logprior=None, collect=True)
    return _row(features, tick, 1)


def _signal_rows(module, params, signal: str, cutoff=80, tick=30):
    values = _pattern("alt", cutoff)
    queries = [_query("q0", "e0", "m0", "steady", signal, cutoff)]
    history = {("e0", "m0"): {t: values[t] for t in range(cutoff)}}
    _, features, _ = module.predict(queries, history, params, expert_logprior=None, collect=True)
    return _row(features, tick, 1)


def _typed_row(module, params, machine_type: str, cutoff=80, tick=30):
    values = _pattern("alt", cutoff)
    queries = [_query("q0", "e0", "m0", machine_type, "0", cutoff)]
    history = {("e0", "m0"): {t: values[t] for t in range(cutoff)}}
    _, features, _ = module.predict(queries, history, params, expert_logprior=None, collect=True)
    return _row(features, tick, 1)


def _sibling(module, params, mutate: str, cutoff=80, tick=30):
    left = _pattern("alt", cutoff)
    right = list(left)
    if mutate == "same_tick":
        right[tick] = 0 if right[tick] else 1
    elif mutate == "later":
        right[40:] = _pattern("persist", cutoff - 40)
    elif mutate != "none":
        raise ValueError(mutate)
    queries = [
        _query("q0", "e0", "m0", "steady", "0", cutoff),
        _query("q1", "e0", "m1", "steady", "0", cutoff),
    ]
    history = {
        ("e0", "m0"): {t: left[t] for t in range(cutoff)},
        ("e0", "m1"): {t: right[t] for t in range(cutoff)},
    }
    _, features, _ = module.predict(queries, history, params, expert_logprior=None, collect=True)
    return _row(features, tick, 2, 0)


def _cutoff_predictions(module, params, cutoff=64):
    values = _pattern("alt", cutoff)
    queries = [_query("q0", "e0", "m0", "steady", "0", cutoff)]
    history = {("e0", "m0"): {t: values[t] for t in range(cutoff)}}
    baseline = module.predict(queries, history, params)
    future = {("e0", "m0"): dict(history[("e0", "m0")])}
    future[("e0", "m0")][cutoff] = 20
    future[("e0", "m0")][cutoff + 1] = 0
    return baseline, module.predict(queries, future, params)


def _matrix(result) -> list[dict]:
    prior_a = result["own_future_alt_persist"]["row_abs_delta"]
    prior_z = result["own_future_zeros_alt"]["row_abs_delta"]
    coverage = result["coverage"]["row_abs_delta"]
    signal = result["signal"]["row_abs_delta"]
    rows = []
    for spec in COLUMNS:
        i = spec["index"]
        prior_hit = prior_a[i] > 1e-5 or prior_z[i] > 1e-5
        coverage_hit = coverage[i] > 1e-6
        signal_hit = signal[i] > 1e-8
        if i == 13 and signal_hit and not prior_hit and not coverage_hit:
            verdict = "AMBIGUOUS"
            proven = "Uses the final query signal on this historical row. RULES.md does not say whether that value existed at tick t."
        elif prior_hit or coverage_hit:
            verdict = "FAIL"
            parts = []
            if prior_hit:
                parts.append("expert prior fit on later payouts")
            if coverage_hit:
                parts.append("final cutoff coverage")
            proven = "Synthetic row changed through " + " and ".join(parts) + "."
        elif signal_hit:
            verdict = "FAIL"
            proven = "Changed when only the query signal changed."
        else:
            verdict = "PASS"
            proven = "Unchanged by later payouts, final-coverage deletion, and the query signal in these fixtures."
        if i in (2, 3) and not prior_hit and coverage_hit:
            proven += " Prior-only fixtures did not move this logit. The zeros fixture did move log1p_top_count, so the prior changed which expert was selected while these probabilities stayed tied."
        rows.append({**spec, "verdict": verdict, "proven": proven,
                     "prior_alt_delta": prior_a[i], "prior_zeros_delta": prior_z[i],
                     "coverage_delta": coverage[i], "signal_delta": signal[i]})
    return rows


def _concerns(result) -> list[dict]:
    own = result["own_future_alt_persist"]
    zeros = result["own_future_zeros_alt"]
    other = result["other_episode"]
    coverage = result["coverage"]
    own_supported = (
        own["prior_argmax"][0] != own["prior_argmax"][1]
        and own["row_abs_delta"][5] > 0.1
        and own["gamma0_rows_equal"]
        and own["frozen_prior_rows_equal"]
        and zeros["row_abs_delta"][7] > 0.01
    )
    other_supported = other["prior_max_abs"] > 0.5 and other["row_abs_delta"][5] > 0.05 and other["frozen_prior_rows_equal"]
    coverage_supported = (not coverage["rows_equal"]) and coverage["matched_rows_equal"] and coverage["row_abs_delta"][2] > 1e-4
    return [
        {"id": "same_machine_expert_prior",
         "behavior": "SUPPORTED" if own_supported else "UNSUPPORTED",
         "rule": "NEEDS_ORGANIZER_RULING",
         "statement": "Changing this machine's payouts after tick t changes learn_expert_prior and, with champion gamma, changes the fixed historical row."},
        {"id": "other_episode_expert_prior",
         "behavior": "SUPPORTED" if other_supported else "UNSUPPORTED",
         "rule": "NEEDS_ORGANIZER_RULING",
         "statement": "Changing another training episode's later payouts changes the shared prior and this episode's fixed historical row."},
        {"id": "final_history_coverage",
         "behavior": "SUPPORTED" if coverage_supported else "UNSUPPORTED",
         "rule": "PLAIN_READING",
         "statement": "Deleting ticks after t changes earlier stacker rows by switching the final-coverage smoothing regime. Matching lam_short/prior_short removes that difference."},
        {"id": "historical_query_signal",
         "behavior": "SUPPORTED" if result["signal"]["only_column"] == 13 else "UNSUPPORTED",
         "rule": "NEEDS_ORGANIZER_RULING",
         "statement": "Column 13 of a historical row is the cutoff query's signal. The kit does not release signal(t)."},
        {"id": "snapshot_uses_later_payouts",
         "behavior": "UNSUPPORTED" if own["frozen_prior_rows_equal"] and result["sibling"]["same_tick_equal"] and result["sibling"]["later_equal"] else "SUPPORTED",
         "rule": "PLAIN_READING",
         "statement": "With the prior held fixed, later payout values, a sibling payout at tick t, and a sibling's later payouts do not change the row."},
        {"id": "inference_uses_ticks_at_or_after_cutoff",
         "behavior": "UNSUPPORTED" if result["cutoff_future_equal"] else "SUPPORTED",
         "rule": "PLAIN_READING",
         "statement": "Ticks at or after the query cutoff do not change predict() output."},
        {"id": "hidden_test_label_leakage",
         "behavior": "UNSUPPORTED",
         "rule": "PLAIN_READING",
         "statement": "These fixtures have no test labels. The historical label is the outcome at t. Nothing here shows hidden-test leakage."},
    ]


def evaluate() -> dict:
    module, params = load_champion()
    rules = RULES_PATH.read_text(encoding="utf-8")
    data = DATA_PATH.read_text(encoding="utf-8")
    own_left, own_right = _history_pair("alt", "alt", "persist", 120, 40)
    zero_left, zero_right = _history_pair("zeros", "zeros", "alt", 120, 40)
    other_left = _other_episode("alt")
    other_right = _other_episode("persist")
    full = _coverage(module, params, delete=False, matched=False)
    short = _coverage(module, params, delete=True, matched=False)
    matched_full = _coverage(module, params, delete=False, matched=True)
    matched_short = _coverage(module, params, delete=True, matched=True)
    signal_zero = _signal_rows(module, params, "0")
    signal_neg = _signal_rows(module, params, "-1")
    steady = _typed_row(module, params, "steady")
    jackpot = _typed_row(module, params, "jackpot")
    sibling_base = _sibling(module, params, "none")
    cutoff_base, cutoff_future = _cutoff_predictions(module, params)
    signal_delta = _abs_delta(signal_zero, signal_neg)
    signal_hits = [i for i, value in enumerate(signal_delta) if value > 1e-8]
    result = {
        "evidence_rating": "NOT_CERTIFIED",
        "source": {
            "commit": _git_head(),
            "model_sha256": _sha256(MODEL_PATH),
            "params_sha256": _sha256(PARAMS_PATH),
            "python": sys.version.split()[0],
            "numpy": np.__version__,
            "gamma": params.get("gamma"),
            "lam": params.get("lam"),
            "lam_short": params.get("lam_short"),
            "prior": params.get("prior"),
            "prior_short": params.get("prior_short"),
        },
        "rules_quote_present": RULES_ASOF in rules,
        "data_quote_present": DATA_FUTURE_FEATURE in data and DATA_SIGNAL in data,
        "own_future_alt_persist": _pair(module, params, own_left, own_right, tick=20, n_queries=1),
        "own_future_zeros_alt": _pair(module, params, zero_left, zero_right, tick=20, n_queries=1),
        "other_episode": _pair(module, params, other_left, other_right, tick=30, n_queries=2, query_index=0),
        "coverage": {
            "row_abs_delta": _abs_delta(full, short),
            "rows_equal": bool(np.array_equal(full, short)),
            "matched_rows_equal": bool(np.array_equal(matched_full, matched_short)),
            "seen": [float(full[14]), float(short[14])],
        },
        "signal": {
            "row_abs_delta": signal_delta,
            "values": [float(signal_zero[13]), float(signal_neg[13])],
            "only_column": signal_hits[0] if signal_hits == [13] else None,
        },
        "type_columns": {
            "diff_columns": [i for i, value in enumerate(_abs_delta(steady, jackpot)) if value > 1e-8],
        },
        "sibling": {
            "same_tick_equal": bool(np.array_equal(sibling_base, _sibling(module, params, "same_tick"))),
            "later_equal": bool(np.array_equal(sibling_base, _sibling(module, params, "later"))),
        },
        "cutoff_future_equal": cutoff_base == cutoff_future,
        "expected_seen_tick20": float(np.log1p(20)),
        "expected_seen_tick30": float(np.log1p(30)),
    }
    result["columns"] = _matrix(result)
    result["concerns"] = _concerns(result)
    return result


def format_text(result) -> str:
    source = result["source"]
    lines = [
        f"evidence_rating={result['evidence_rating']}",
        f"commit={source['commit']}",
        f"model_sha256={source['model_sha256']}",
        f"params_sha256={source['params_sha256']}",
        f"python={source['python']} numpy={source['numpy']}",
        f"gamma={source['gamma']} lam={source['lam']} lam_short={source['lam_short']} prior={source['prior']} prior_short={source['prior_short']}",
        f"rules_quote_present={result['rules_quote_present']} data_quote_present={result['data_quote_present']}",
        "",
        "column verdict prior_alt prior_zeros coverage signal",
    ]
    for row in result["columns"]:
        lines.append(
            f"{row['index']:2d} {row['name']:<28} {row['verdict']:<10} "
            f"{row['prior_alt_delta']:.6g} {row['prior_zeros_delta']:.6g} "
            f"{row['coverage_delta']:.6g} {row['signal_delta']:.6g}"
        )
    lines.append("")
    for key in ("own_future_alt_persist", "own_future_zeros_alt", "other_episode"):
        item = result[key]
        lines.append(
            f"{key} argmax={item['prior_argmax']} prior_max_abs={item['prior_max_abs']:.6g} "
            f"labels={item['labels']} seen={item['seen']} gamma0={item['gamma0_rows_equal']} "
            f"frozen={item['frozen_prior_rows_equal']}"
        )
    coverage = result["coverage"]
    lines.append(
        f"coverage rows_equal={coverage['rows_equal']} matched_rows_equal={coverage['matched_rows_equal']} seen={coverage['seen']}"
    )
    lines.append(
        f"signal values={result['signal']['values']} only_column={result['signal']['only_column']} "
        f"type_diff={result['type_columns']['diff_columns']}"
    )
    lines.append(
        f"sibling same_tick={result['sibling']['same_tick_equal']} later={result['sibling']['later_equal']} "
        f"cutoff_future_equal={result['cutoff_future_equal']}"
    )
    lines.append("")
    for concern in result["concerns"]:
        lines.append(f"{concern['id']} behavior={concern['behavior']} rule={concern['rule']}")
    return "\n".join(lines) + "\n"


def main() -> int:
    print(format_text(evaluate()), end="")
    return 0


if __name__ == "__main__":
    sys.exit(main())
