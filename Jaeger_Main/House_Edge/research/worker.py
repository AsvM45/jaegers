"""One isolated CV trial. Public validation and test are absent from fitting/evaluation."""
import argparse
from collections import defaultdict
import json
from pathlib import Path
import time
import importlib
from .common import ROOT, require_python, write_json
from .dataset import conditions, episode_folds, read_labels
from .metrics import diagnostics
from .adapters import FrequencyModel, JaegerModel, core_module


def model_for(config, cache):
    if config.get("factory"):
        module, symbol = config["factory"].split(":",1)
        if not module.startswith("research.models.") or not symbol.isidentifier():
            raise ValueError("Specialist factories must be named research.models.<module>:<factory>")
        return getattr(importlib.import_module(module),symbol)(config,cache)
    family = config["family"]
    if family == "jaeger":
        params = json.loads((ROOT / "jaegers_entry/params.json").read_text())
        params.update(config.get("params", {}))
        return JaegerModel(params, causal=config.get("causal", False))
    if family == "frequency":
        return FrequencyModel(**config.get("params", {}))
    from .learners import HistoricalModel
    return HistoricalModel(family, config["groups"], config.get("params"), str(cache),
                           config.get("supervision", "historical"), config.get("seed", 0), config.get("calibration"))


def subset(queries, history, episodes):
    q = [row for row in queries if row["episode_id"] in episodes]
    keys = {(row["episode_id"],row["machine_id"]) for row in q}
    return q, defaultdict(dict, {k:history[k] for k in keys})


def evaluate(request, out):
    require_python()
    started = time.perf_counter()
    config = request["config"]
    data = Path(request["data"])
    folder = data / "train"
    queries, history = core_module().read_split(str(folder))
    labels, groups = read_labels(folder), conditions(folder)
    folds = request["folds"]
    predictions, fold_records, importances, temporal = {}, [], [], []
    if config.get("walk_forward_ticks") and (config.get("family") == "jaeger" and not config.get("causal") or "current_signal" in config.get("groups",[])):
        raise ValueError("Walk-forward diagnostics cannot reuse unsupported final query signal")
    for fold in sorted(set(folds.values())):
        hold = {ep for ep,f in folds.items() if f == fold}
        fit = set(folds)-hold
        if fit & hold:
            raise ValueError("Episode fold overlap")
        fit_q, fit_h = subset(queries,history,fit)
        hold_q, hold_h = subset(queries,history,hold)
        model = model_for(config, request.get("cache"))
        fit_labels = {q["query_id"]:labels[q["query_id"]] for q in fit_q}
        model.fit(fit_q,fit_h,fit_labels)
        prediction = model.predict_proba(hold_q,hold_h)
        if set(predictions) & set(prediction):
            raise ValueError("Repeated held-out query")
        predictions.update(prediction)
        fold_records.append({"fold":fold,"fit_episodes":sorted(fit),"heldout_episodes":sorted(hold)})
        if hasattr(model,"importance"):
            importances.append(model.importance())
        for tick in config.get("walk_forward_ticks",[]):
            tick=int(tick)
            temporal_q=[dict(q,query_id=q["query_id"]+f"_t{tick}",cutoff=str(tick)) for q in hold_q if tick < int(q["cutoff"])]
            if not temporal_q:
                continue
            temporal_prediction=model.predict_proba(temporal_q,hold_h)
            observed=[q for q in temporal_q if tick in hold_h[(q["episode_id"],q["machine_id"])]]
            if observed:
                from .adapters import PAYOUTS
                temporal_labels={q["query_id"]:PAYOUTS.index(hold_h[(q["episode_id"],q["machine_id"])][tick]) for q in observed}
                condition_by_episode={q["episode_id"]:groups[q["query_id"]] for q in hold_q}
                temporal_groups={q["query_id"]:condition_by_episode[q["episode_id"]] for q in observed}
                temporal.append({"fold":fold,"tick":tick,"metrics":diagnostics(temporal_prediction,observed,temporal_labels,temporal_groups)})
        progress_q=[q for q in queries if q["query_id"] in predictions]
        progress_score=diagnostics(predictions,progress_q,labels,groups)["mean_brier"]
        write_json(out / "progress.json", {"completed_folds":len(fold_records), "folds":fold_records,"mean_brier":progress_score})
        if config.get("save_model"):
            model.save(out / f"fold-{fold}-model.joblib")
    if set(predictions) != {q["query_id"] for q in queries}:
        raise ValueError("Incomplete out-of-fold query coverage")
    result = diagnostics(predictions,queries,labels,groups)
    from slot_forecasting.io import write_submission
    write_submission(out / "oof.csv",predictions)
    result.update(config=config, folds=fold_records, wall_seconds=time.perf_counter()-started,
                  importance=importances, walk_forward=temporal, validation_target_exposure=config["family"] == "jaeger",
                  design_provenance="development-informed; train-only fitting and group-held-out labels",
                  historical_signal_policy="omitted" if config["family"] != "jaeger" or config.get("causal") else "unsupported_copied_signal")
    write_json(out / "result.json",result)
    return result


if __name__ == "__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--request",required=True)
    args=p.parse_args()
    path=Path(args.request).resolve()
    result=evaluate(json.loads(path.read_text()),path.parent)
    print(json.dumps({"mean_brier":result["mean_brier"],"wall_seconds":result["wall_seconds"]}))
