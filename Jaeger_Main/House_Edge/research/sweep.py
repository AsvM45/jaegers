"""Resumable grid/random/Optuna studies with bounded subprocess workers."""
import argparse
from concurrent.futures import ThreadPoolExecutor, wait, FIRST_COMPLETED
from copy import deepcopy
import itertools
import json
from pathlib import Path
import random
import shutil
import sys
import time
import traceback
from .common import ROOT, digest, environment, file_hash, git, now, require_python, tree_hashes, write_json
from .dataset import build_cache, conditions, episode_folds
from .adapters import core_module
from .process import run
from .registry import Registry


def set_path(config, key, value):
    parts = key.split(".")
    target = config
    for part in parts[:-1]:
        target = target.setdefault(part, {})
    target[parts[-1]] = value


def candidates(spec):
    rows = list(spec.get("candidates", []))
    space = spec.get("space", {})
    if space:
        for values in itertools.product(*(space[k] for k in space)):
            config = deepcopy(spec.get("base", {}))
            for key,value in zip(space,values):
                set_path(config,key,value)
            rows.append(config)
    seen, unique = set(), []
    for row in rows:
        row = dict(row, seed=row.get("seed", spec.get("seed",0)))
        key = digest(row)
        if key not in seen:
            seen.add(key); unique.append(row)
    if spec.get("strategy") == "random":
        random.Random(spec.get("seed",0)).shuffle(unique)
    return unique


def identity(data, folds):
    numerical = ("__init__.py", "common.py", "dataset.py", "feature_api.py", "learners.py", "adapters.py", "metrics.py",
                 "worker.py", "sweep.py", "registry.py", "process.py")
    metadata=json.loads((Path(data)/"metadata.json").read_text())
    return {"head":git("rev-parse","HEAD"), "round":metadata["round"],"season_id":metadata["season_id"],
            "source_sha256":{n:file_hash(Path(__file__).with_name(n)) for n in numerical},
            "model_plugins_sha256":tree_hashes(ROOT/"research/models"),
            "feature_plugins_sha256":tree_hashes(ROOT/"research/features"),
            "challenger_plugins_sha256":tree_hashes(ROOT/"research/challengers"),
            "feature_extensions_sha256":tree_hashes(ROOT/"research/extensions"),
            "scorer_sha256":tree_hashes(ROOT/"slot_forecasting"),
            "champion_sha256":tree_hashes(ROOT / "jaegers_entry"),
            "train_sha256":tree_hashes(Path(data)/"train"), "metadata_sha256":file_hash(Path(data)/"metadata.json"),
            "split_manifest_sha256":digest(folds), "environment":environment()}


def snapshot_source(destination, provenance):
    """Running workers import immutable copies, never another agent's live edits."""
    destination=Path(destination)
    (destination/"research").mkdir(parents=True,exist_ok=False)
    for name,expected in provenance["source_sha256"].items():
        source=ROOT/"research"/name
        target=destination/"research"/name
        shutil.copyfile(source,target)
        if file_hash(target) != expected:
            raise ValueError(f"Source changed while staging trial: {name}; restart study with current identity")
    for directory,key,target_parent in (("jaegers_entry","champion_sha256",destination),
                                         ("slot_forecasting","scorer_sha256",destination),
                                         ("research/models","model_plugins_sha256",destination),
                                         ("research/features","feature_plugins_sha256",destination),
                                         ("research/challengers","challenger_plugins_sha256",destination),
                                         ("research/extensions","feature_extensions_sha256",destination)):
        source=ROOT/directory
        expected=provenance[key]
        if tree_hashes(source) != expected:
            raise ValueError(f"Source changed while staging trial: {directory}")
        if source.exists():
            target=target_parent/directory
            shutil.copytree(source,target,ignore=shutil.ignore_patterns("__pycache__","*.pyc"))
            if tree_hashes(target) != expected:
                raise ValueError(f"Source changed while staging trial: {directory}")
    write_json(destination/"source-manifest.json",provenance)
    return destination


def execute(registry, trial_id, config, provenance, data, folds, cache, timeout, slot, cpus, retry=False):
    artifact = registry.start(trial_id,retry)
    if artifact is None:
        return "SKIPPED"
    request = {"trial_id":trial_id,"config":config,"identity":provenance,"data":str(data),
               "folds":folds,"cache":str(cache) if cache else None}
    write_json(artifact / "request.json", request)
    started = time.perf_counter()
    try:
        frozen_source=snapshot_source(artifact/"source",provenance)
        process = run([sys.executable,"-B","-m","research.worker","--request",artifact/"request.json"],
                      frozen_source,artifact/"process",timeout=timeout,memory_gib=8,cpus=cpus,slot=slot)
        result = json.loads((artifact/"result.json").read_text())
        registry.finish(trial_id,"SUCCEEDED",result,wall_seconds=process["wall_seconds"])
        print(f"SUCCEEDED {config['family']} {trial_id[:10]} Brier={result['mean_brier']:.6f}",flush=True)
        return "SUCCEEDED"
    except Exception as exc:
        process_path = artifact/"process/process.json"
        process = json.loads(process_path.read_text()) if process_path.exists() else {}
        status = process.get("status","FAILED")
        if status not in ("TIMEOUT","MEMORY_LIMIT"):
            status = "FAILED"
        error = f"{type(exc).__name__}: {exc}"
        write_json(artifact/"failure.json",{"error":error,"traceback":traceback.format_exc(),"recorded_at":now()})
        registry.finish(trial_id,status,error=error,wall_seconds=time.perf_counter()-started)
        print(f"{status} {config['family']} {trial_id[:10]} — see {artifact}",flush=True)
        return status


def sweep(spec, data, root, retry=False):
    require_python()
    data, root = Path(data).resolve(), Path(root).resolve()
    registry = Registry(root)
    budget = spec.get("budget",{})
    workers = min(2,max(1,int(budget.get("workers",1))))
    maximum = int(budget.get("trials",3))
    wall = float(budget.get("seconds",1800))
    timeout = float(budget.get("trial_seconds",600))
    if maximum < 1 or wall <= 0 or timeout <= 0:
        raise ValueError("Budgets must be positive")
    started = time.perf_counter()
    with registry.coordinator():
        from slot_forecasting.rounds import round_metadata
        metadata=round_metadata(data)
        round_identity={"round":metadata["round"],"season_id":metadata["season_id"]}
        round_file=root/"round.json"
        if round_file.exists() and json.loads(round_file.read_text()) != round_identity:
            raise ValueError("Use a distinct registry directory for each round/season")
        if not round_file.exists():
            write_json(round_file,round_identity)
        queries,_ = core_module().read_split(str(data/"train"))
        folds = episode_folds(queries,conditions(data/"train"),int(spec.get("folds",4)))
        provenance = identity(data,folds)
        write_json(root/"splits"/(digest(folds)+".json"),folds)
        prepared = candidates(spec)
        check_configs = prepared + ([spec["base"]] if spec.get("strategy") == "optuna" else [])
        need_cache = any(c["family"] not in ("jaeger","frequency") and c.get("supervision","historical") != "query" for c in check_configs)
        cache = build_cache(data,root/"cache") if need_cache else None
        if spec.get("strategy") == "optuna":
            import optuna
            name = spec["name"]+"-"+digest(provenance)[:12]
            study = optuna.create_study(study_name=name,storage="sqlite:///"+str(root/"optuna.sqlite"),
                load_if_exists=True,direction="minimize",sampler=optuna.samplers.TPESampler(seed=spec.get("seed",0)))
            def objective(trial):
                config = deepcopy(spec["base"])
                config["seed"] = spec.get("seed",0)
                for key,distribution in spec["optuna_space"].items():
                    if "choices" in distribution:
                        value = trial.suggest_categorical(key,distribution["choices"])
                    elif distribution.get("type") == "int":
                        value = trial.suggest_int(key,distribution["low"],distribution["high"],log=distribution.get("log",False))
                    else:
                        value = trial.suggest_float(key,distribution["low"],distribution["high"],log=distribution.get("log",False))
                    set_path(config,key,value)
                if "feature_set" in config:
                    config["groups"]=spec["feature_sets"][config["feature_set"]]
                trial_id = registry.register(spec["name"],config,provenance)
                trial.set_user_attr("registry_trial_id",trial_id)
                remaining = wall-(time.perf_counter()-started)
                if remaining <= 0:
                    raise optuna.TrialPruned("Wall budget exhausted")
                execute(registry,trial_id,config,provenance,data,folds,cache,min(timeout,remaining),0,2,retry)
                row = next(r for r in registry.rows() if r["id"] == trial_id)
                if row["status"] != "SUCCEEDED":
                    raise optuna.TrialPruned("Recorded trial did not complete successfully")
                return row["mean_brier"]
            completed = len(study.get_trials(states=(optuna.trial.TrialState.COMPLETE,)))
            if completed < maximum:
                study.optimize(objective,n_trials=maximum-completed,timeout=max(1,wall-(time.perf_counter()-started)))
        else:
            with ThreadPoolExecutor(max_workers=workers) as executor:
                pending, slots = {}, list(range(workers))
                cursor = 0
                while cursor < min(len(prepared),maximum) or pending:
                    while slots and cursor < min(len(prepared),maximum):
                        remaining = wall-(time.perf_counter()-started)
                        if remaining <= 0:
                            cursor = maximum
                            break
                        config = prepared[cursor]; cursor += 1
                        trial_id = registry.register(spec["name"],config,provenance)
                        slot=slots.pop(0)
                        future=executor.submit(execute,registry,trial_id,config,provenance,data,folds,cache,
                                               min(timeout,remaining),slot,2//workers,retry)
                        pending[future]=slot
                    if pending:
                        done,_ = wait(pending,return_when=FIRST_COMPLETED)
                        for future in done:
                            slots.append(pending.pop(future)); future.result()
        rows=registry.export()
        summary={"study":spec["name"],"identity":digest(provenance),"requested_configurations":maximum,
                 "statuses":{s:sum(r["status"]==s for r in rows) for s in sorted({r["status"] for r in rows})},
                 "wall_seconds":time.perf_counter()-started,"finished_at":now()}
        write_json(root/"studies"/(spec["name"]+"-"+digest(provenance)[:12]+".json"),summary)
        print(json.dumps(summary),flush=True)
        return summary


if __name__ == "__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--study",required=True)
    p.add_argument("--data",default=str(ROOT/"public"))
    p.add_argument("--out",default=str(ROOT/"research_runs/main"))
    p.add_argument("--retry-failed",action="store_true")
    a=p.parse_args()
    sweep(json.loads(Path(a.study).read_text()),a.data,a.out,a.retry_failed)
