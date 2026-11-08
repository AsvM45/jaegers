"""HE-11 peer, drift, and episode-local probability mixtures.

Sibling and own-machine payouts are read only at ticks strictly before the
prediction cutoff. Scores are sampled-label Brier, not official round points.
"""
import argparse
import json
from collections import defaultdict
from pathlib import Path
import time
import numpy as np

from research.common import digest, write_json
from research.dataset import conditions as read_conditions, episode_folds, read_labels
from research.metrics import diagnostics, paired
from research.models import PAYOUTS, core_module

CONFIG_PATH = Path(__file__).resolve().parents[1] / "configs" / "ml" / "temporal_screen.json"


def load_config(path=CONFIG_PATH):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def distribution(labels, prior):
    counts = np.full(5, prior, dtype=float)
    for label in labels:
        counts[int(label)] += 1
    return counts / counts.sum()


def observed(history, episode, machine, cutoff):
    rows = history[(episode, machine)]
    ticks = sorted(tick for tick in rows if tick < cutoff)
    return ticks, [PAYOUTS.index(rows[tick]) for tick in ticks]


def exact_window(ticks, labels, cutoff, width):
    return [label for tick, label in zip(ticks, labels) if cutoff - width <= tick < cutoff]


def sibling_labels(history, episode, machine, cutoff, mode, width):
    gathered = []
    for (other_episode, other_machine), rows in history.items():
        if other_episode != episode or other_machine == machine:
            continue
        ticks = sorted(tick for tick in rows if tick < cutoff)
        labels = [PAYOUTS.index(rows[tick]) for tick in ticks]
        if mode == "all":
            gathered.extend(labels)
        elif mode == "exact":
            gathered.extend(exact_window(ticks, labels, cutoff, width))
        elif mode == "recent":
            gathered.extend(labels[-width:])
        else:
            raise ValueError(f"Unknown sibling mode: {mode}")
    return gathered


def type_priors(queries, history, prior):
    buckets = defaultdict(list)
    for query in queries:
        _, labels = observed(history, query["episode_id"], query["machine_id"], int(query["cutoff"]))
        buckets[query["machine_type"]].extend(labels)
    return {machine_type: distribution(labels, prior) for machine_type, labels in buckets.items()}


def predict_variant(query, history, priors, config, variant):
    cutoff = int(query["cutoff"])
    ticks, labels = observed(history, query["episode_id"], query["machine_id"], cutoff)
    own = distribution(labels, config["prior"])
    width = config["window"]
    recent = distribution(exact_window(ticks, labels, cutoff, width), config["prior"])
    earlier_labels = [label for tick, label in zip(ticks, labels) if tick < cutoff - width]
    earlier = distribution(earlier_labels, config["prior"])
    peers = distribution(sibling_labels(history, query["episode_id"], query["machine_id"], cutoff, "all", width), config["prior"])
    peer_recent = distribution(
        sibling_labels(history, query["episode_id"], query["machine_id"], cutoff, "exact", width), config["prior"]
    )
    global_prior = priors.get(query["machine_type"], np.full(5, 0.2))
    drifted = 0.5 * recent + 0.5 * earlier
    choices = {
        "no_peer": own,
        "peer": 0.5 * own + 0.5 * peers,
        "drift": drifted,
        "peer_drift": 0.5 * drifted + 0.5 * peer_recent,
        "global": global_prior,
        "local": 0.5 * global_prior + 0.5 * own,
    }
    if variant not in choices:
        raise ValueError(f"Unknown variant: {variant}")
    values = np.asarray(choices[variant], dtype=float)
    values = np.clip(values, 0, None)
    total = values.sum()
    if not np.isfinite(total) or total <= 0:
        raise ValueError("Variant produced an empty distribution")
    return values / total


def _public(report):
    keep = ("evaluation_source", "official_points", "mean_brier", "by_condition", "log_loss", "class_brier", "class_counts", "per_episode")
    return {key: report[key] for key in keep}


def evaluate_variant(variant, queries, history, labels, condition_map, priors, config):
    started = time.perf_counter()
    predictions = {
        query["query_id"]: predict_variant(query, history, priors, config, variant).tolist()
        for query in queries
    }
    elapsed = time.perf_counter() - started
    report = diagnostics(predictions, queries, labels, condition_map)
    report.pop("per_query", None)
    report.pop("calibration", None)
    summary = _public(report)
    summary["predict_seconds"] = elapsed
    return report, summary


def run_screen(queries, history, labels, condition_map, config):
    folds = episode_folds(queries, condition_map, config["fold_count"])
    train_rows = [query for query in queries if folds[query["episode_id"]] != config["holdout_fold"]]
    test_rows = [query for query in queries if folds[query["episode_id"]] == config["holdout_fold"]]
    if not train_rows or not test_rows:
        raise ValueError("Fold split produced an empty side")
    priors = type_priors(train_rows, history, config["prior"])
    full, public = {}, {}
    for variant in config["variants"]:
        report, summary = evaluate_variant(variant, test_rows, history, labels, condition_map, priors, config)
        full[variant] = report
        public[variant] = summary
    baseline = config["baseline"]
    comparisons = {
        name: paired(full[name], full[baseline], seed=config["seed"])
        for name in config["variants"] if name != baseline
    }
    local_vs_global = paired(full["local"], full["global"], seed=config["seed"])
    helpful = sorted(name for name, row in comparisons.items() if row["supported_improvement"])
    return {
        "status": "MEASURED_NOT_PROMOTED",
        "verdict": "Reject as a champion replacement. Paired deltas are sampled-label holdout Brier, not official points.",
        "hypotheses": config["hypotheses"],
        "evaluation_source": "sampled_outcome_group_cv",
        "official_points": None,
        "validation_target_exposure": False,
        "config_sha256": digest(config),
        "fold_manifest_sha256": digest(folds),
        "n_fit_queries": len(train_rows),
        "n_holdout_queries": len(test_rows),
        "variants": public,
        "versus_no_peer": comparisons,
        "local_minus_global": local_vs_global,
        "supported_improvement_versus_no_peer": helpful,
    }


def screen_public_train(data, out, config=None):
    config = load_config() if config is None else config
    folder = Path(data) / "train"
    queries, history = core_module().read_split(str(folder))
    report = run_screen(queries, history, read_labels(folder), read_conditions(folder), config)
    write_json(out, report)
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, default=Path(__file__).resolve().parents[2] / "public")
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    report = screen_public_train(args.data, args.out)
    print(json.dumps({
        "status": report["status"],
        "supported_improvement_versus_no_peer": report["supported_improvement_versus_no_peer"],
        "config_sha256": report["config_sha256"],
    }, sort_keys=True))


if __name__ == "__main__":
    main()
