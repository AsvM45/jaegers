"""Bounded HE-10 screen over the existing learner adapters.

This module does not modify research/learners.py. Scores are sampled-label
Brier on episode-held-out train queries, not official round points.
"""
import argparse
import json
from pathlib import Path
import time
import numpy as np

from research.common import digest, write_json
from research.dataset import conditions as read_conditions, episode_folds, read_labels
from research.features import FeatureComputer
from research.learners import HistoricalModel
from research.metrics import diagnostics, paired
from research.models import PAYOUTS, core_module

CONFIG_PATH = Path(__file__).resolve().parents[1] / "configs" / "ml" / "screen.json"
QUERY_GROUPS = ("type", "lags", "missingness", "current_signal")
HISTORICAL_GROUPS = ("type", "lags", "missingness")


def load_config(path=CONFIG_PATH):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def historical_matrix(queries, history, groups, stride, max_rows):
    """Labeled rows at ticks strictly before each query cutoff. Signal is not a feature."""
    if "current_signal" in groups:
        raise ValueError("Historical rows cannot use query-time signal")
    computer = FeatureComputer(history)
    changed = FeatureComputer({key: dict(rows) for key, rows in history.items()})
    features, labels, episodes, names = [], [], [], None
    for query in queries:
        key = (query["episode_id"], query["machine_id"])
        cutoff = int(query["cutoff"])
        observed = sorted(tick for tick in history[key] if tick < cutoff)
        for tick in observed[::stride][-max_rows:]:
            sample = dict(query, cutoff=str(tick))
            values, names = computer.row(sample, groups)
            altered = dict(sample, signal="1" if str(query["signal"]) != "1" else "-1")
            if not np.array_equal(values, changed.row(altered, groups)[0]):
                raise ValueError("Historical features changed when only query signal changed")
            features.append(values)
            labels.append(PAYOUTS.index(history[key][tick]))
            episodes.append(query["episode_id"])
    if not features:
        raise ValueError("No historical rows before cutoff")
    return np.asarray(features, dtype=np.float32), np.asarray(labels), np.asarray(episodes), names


def write_historical_cache(folder, features, labels, episodes, names):
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    archive = folder / "train.npz"
    np.savez_compressed(
        archive,
        X=features,
        y=labels,
        episode=episodes,
        tick=np.zeros(len(labels), dtype=np.int32),
        kind=np.array(["historical"] * len(labels)),
        query_id=np.array([f"row{i}" for i in range(len(labels))]),
    )
    from research.common import file_hash
    write_json(folder / "complete.json", {"columns": names, "archive_sha256": file_hash(archive), "rows": int(len(labels))})
    return folder


def fit_model(family, params, seed, queries, history, labels, groups, supervision, cache):
    model = HistoricalModel(family, groups, params=params, cache=cache, supervision=supervision, seed=seed)
    started = time.perf_counter()
    model.fit(queries, history, labels)
    return model, time.perf_counter() - started


def holdout_report(model, queries, history, labels, condition_map):
    predictions = model.predict_proba(queries, history)
    report = diagnostics(predictions, queries, labels, condition_map)
    report.pop("per_query", None)
    report.pop("calibration", None)
    return report


def run_screen(queries, history, labels, condition_map, config, cache_dir):
    folds = episode_folds(queries, condition_map, config["fold_count"])
    holdout = config["holdout_fold"]
    train_rows = [query for query in queries if folds[query["episode_id"]] != holdout]
    test_rows = [query for query in queries if folds[query["episode_id"]] == holdout]
    if not train_rows or not test_rows:
        raise ValueError("Fold split produced an empty side")
    features, y, episodes, names = historical_matrix(
        train_rows, history, tuple(config["historical_groups"]), config["historical_stride"], config["historical_max_rows"]
    )
    cache = write_historical_cache(cache_dir, features, y, episodes, names)
    families = {}
    comparisons = {}
    for family, params in config["families"].items():
        query_model, query_seconds = fit_model(
            family, params, config["seed"], train_rows, history, labels, tuple(config["query_groups"]), "query", None
        )
        historical_model, historical_seconds = fit_model(
            family, params, config["seed"], train_rows, history, labels, tuple(config["historical_groups"]), "historical", cache
        )
        query_report = holdout_report(query_model, test_rows, history, labels, condition_map)
        historical_report = holdout_report(historical_model, test_rows, history, labels, condition_map)
        families[family] = {
            "query_supervision": {**_public(query_report), "fit_seconds": query_seconds},
            "historical_supervision": {**_public(historical_report), "fit_seconds": historical_seconds},
            "query_minus_historical": paired(query_report, historical_report, seed=config["seed"]),
        }
        comparisons[family] = query_report
    boost_vs_logistic = paired(comparisons["hist_boost"], comparisons["logistic"], seed=config["seed"])
    return {
        "status": "MEASURED_NOT_PROMOTED",
        "verdict": "Reject as a champion replacement. This is a sampled-label episode holdout, not official validation points.",
        "evaluation_source": "sampled_outcome_group_cv",
        "official_points": None,
        "validation_target_exposure": False,
        "config_sha256": digest(config),
        "fold_manifest_sha256": digest(folds),
        "holdout_fold": holdout,
        "n_fit_queries": len(train_rows),
        "n_holdout_queries": len(test_rows),
        "families": families,
        "hist_boost_minus_logistic_query": boost_vs_logistic,
        "supported_improvement": boost_vs_logistic["supported_improvement"],
    }


def _public(report):
    keep = ("evaluation_source", "official_points", "mean_brier", "by_condition", "log_loss", "class_brier", "class_counts", "per_episode")
    return {key: report[key] for key in keep}


def screen_public_train(data, out, config=None):
    config = load_config() if config is None else config
    folder = Path(data) / "train"
    queries, history = core_module().read_split(str(folder))
    labels = read_labels(folder)
    condition_map = read_conditions(folder)
    out = Path(out)
    report = run_screen(queries, history, labels, condition_map, config, out.with_suffix(".cache"))
    write_json(out, report)
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, default=Path(__file__).resolve().parents[2] / "public")
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    report = screen_public_train(args.data, args.out)
    print(json.dumps({"status": report["status"], "config_sha256": report["config_sha256"],
                      "supported_improvement": report["supported_improvement"]}, sort_keys=True))


if __name__ == "__main__":
    main()
