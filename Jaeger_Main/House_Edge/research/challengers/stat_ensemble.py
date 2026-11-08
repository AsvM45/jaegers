"""HE-12 out-of-fold calibration, history-length gating, and ensemble.

Condition labels are never model inputs. Scores are sampled-label Brier, not
official round points. Claude issue #9 forecasts are not refit here.
"""
import argparse
import json
from collections import defaultdict
from pathlib import Path
import numpy as np

from research.common import digest, write_json
from research.dataset import conditions as read_conditions, episode_folds, read_labels
from research.learners import HistoricalModel
from research.metrics import diagnostics, paired
from research.models import PAYOUTS, core_module

CONFIG_PATH = Path(__file__).resolve().parents[1] / "reports" / "stat_ensemble_config.json"


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


def temper(probabilities, temperature):
    scaled = np.log(np.clip(probabilities, 1e-9, 1)) / temperature
    scaled -= scaled.max(axis=1, keepdims=True)
    exponent = np.exp(scaled)
    return exponent / exponent.sum(axis=1, keepdims=True)


def gate_member(n_observed, short_history_max):
    """Observable history length only. Condition names are not accepted."""
    return "no_peer" if n_observed < short_history_max else "ensemble"


def mixture(query, history, config, name):
    cutoff = int(query["cutoff"])
    ticks, labels = observed(history, query["episode_id"], query["machine_id"], cutoff)
    own = distribution(labels, config["prior"])
    recent = distribution([label for tick, label in zip(ticks, labels) if tick >= cutoff - config["window"]], config["prior"])
    earlier = distribution([label for tick, label in zip(ticks, labels) if tick < cutoff - config["window"]], config["prior"])
    if name == "no_peer":
        return own, len(labels)
    if name == "drift":
        return 0.5 * recent + 0.5 * earlier, len(labels)
    raise ValueError(f"Unknown mixture: {name}")


def choose_temperature(probabilities, labels, temperatures):
    best_temperature, best_loss = 1.0, None
    onehot = np.eye(5)[np.asarray(labels, dtype=int)]
    for temperature in temperatures:
        adjusted = temper(probabilities, temperature)
        loss = float(np.mean(np.sum((adjusted - onehot) ** 2, axis=1)))
        if best_loss is None or loss < best_loss:
            best_temperature, best_loss = float(temperature), loss
    return best_temperature


def _fit_learners(train_rows, history, labels, config):
    fitted = []
    for spec in config["learners"]:
        model = HistoricalModel(spec["family"], spec["groups"], params=spec.get("params"), supervision="query", seed=config["seed"])
        model.fit(train_rows, history, labels)
        fitted.append((spec["family"], model))
    return fitted


def _predict_fold(train_rows, test_rows, history, labels, config):
    by_episode = defaultdict(list)
    for query in train_rows:
        by_episode[query["episode_id"]].append(query)
    ordered = sorted(by_episode)
    calibration_episodes = set(ordered[::5])
    core_rows = [query for query in train_rows if query["episode_id"] not in calibration_episodes]
    calibration_rows = [query for query in train_rows if query["episode_id"] in calibration_episodes]
    if not core_rows or not calibration_rows:
        core_rows, calibration_rows = train_rows, train_rows[: max(1, len(train_rows) // 5)]
    temperatures = {}
    core_models = _fit_learners(core_rows, history, labels, config)
    for family, model in core_models:
        predicted = model.predict_proba(calibration_rows, history)
        matrix = np.array([predicted[query["query_id"]] for query in calibration_rows], dtype=float)
        targets = [labels[query["query_id"]] for query in calibration_rows]
        temperatures[family] = choose_temperature(matrix, targets, config["temperatures"])
    mixture_rows = []
    mixture_targets = []
    for query in calibration_rows:
        values, _ = mixture(query, history, config, "no_peer")
        mixture_rows.append(values)
        mixture_targets.append(labels[query["query_id"]])
    temperatures["no_peer"] = choose_temperature(np.array(mixture_rows), mixture_targets, config["temperatures"])
    temperatures["drift"] = temperatures["no_peer"]
    full_models = dict(_fit_learners(train_rows, history, labels, config))
    predictions = defaultdict(dict)
    for query in test_rows:
        for name in ("no_peer", "drift"):
            values, n_observed = mixture(query, history, config, name)
            adjusted = temper(values.reshape(1, 5), temperatures[name])[0]
            predictions[name][query["query_id"]] = adjusted
        member_rows = [predictions["no_peer"][query["query_id"]], predictions["drift"][query["query_id"]]]
        for family, model in full_models.items():
            raw = np.asarray(model.predict_proba([query], history)[query["query_id"]], dtype=float)
            adjusted = temper(raw.reshape(1, 5), temperatures[family])[0]
            predictions[family][query["query_id"]] = adjusted
            member_rows.append(adjusted)
        averaged = np.mean(member_rows, axis=0)
        predictions["ensemble"][query["query_id"]] = averaged / averaged.sum()
        selected = gate_member(n_observed, config["short_history_max"])
        chosen = predictions[selected][query["query_id"]]
        predictions["gated"][query["query_id"]] = chosen / np.asarray(chosen).sum()
    return predictions, temperatures


def _public(report):
    keep = ("evaluation_source", "official_points", "mean_brier", "by_condition", "log_loss", "class_brier", "class_counts", "per_episode")
    return {key: report[key] for key in keep}


def run_screen(queries, history, labels, condition_map, config):
    folds = episode_folds(queries, condition_map, config["fold_count"])
    collected = defaultdict(dict)
    fold_temperatures = {}
    for fold in range(config["fold_count"]):
        train_rows = [query for query in queries if folds[query["episode_id"]] != fold]
        test_rows = [query for query in queries if folds[query["episode_id"]] == fold]
        predictions, temperatures = _predict_fold(train_rows, test_rows, history, labels, config)
        fold_temperatures[str(fold)] = temperatures
        for name, rows in predictions.items():
            collected[name].update(rows)
    summaries, full = {}, {}
    for name, rows in collected.items():
        report = diagnostics(rows, queries, labels, condition_map)
        report.pop("per_query", None)
        report.pop("calibration", None)
        full[name] = report
        summaries[name] = _public(report)
    baseline = full[config["baseline"]]
    comparisons = {name: paired(full[name], baseline, seed=config["seed"]) for name in full if name != config["baseline"]}
    helpful = sorted(name for name, row in comparisons.items() if row["supported_improvement"])
    return {
        "status": "MEASURED_NOT_PROMOTED",
        "verdict": "Do not replace the champion. Out-of-fold Brier is not official points, and Claude #9 forecasts were not included.",
        "evaluation_source": "sampled_outcome_group_cv",
        "official_points": None,
        "validation_target_exposure": False,
        "included_issue9_forecasts": False,
        "condition_labels_used_as_inputs": False,
        "config_sha256": digest(config),
        "fold_manifest_sha256": digest(folds),
        "n_queries": len(queries),
        "temperatures_by_fold": fold_temperatures,
        "models": summaries,
        "versus_baseline": comparisons,
        "supported_improvement_versus_baseline": helpful,
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
        "supported_improvement_versus_baseline": report["supported_improvement_versus_baseline"],
        "config_sha256": report["config_sha256"],
    }, sort_keys=True))


if __name__ == "__main__":
    main()
