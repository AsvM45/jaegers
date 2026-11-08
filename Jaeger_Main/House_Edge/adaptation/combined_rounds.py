"""Bounded reuse of the frozen forecaster with explicit historical training pools.

Current adaptation validation/test histories never enter the global fitting pool.
Old main test *observed histories* may be reused, never hidden next-spin outcomes.
The original model's documented historical-feature caveats are unchanged.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import json
import shutil
import subprocess
import sys
import tempfile
import time
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read_rows(path):
    with Path(path).open(newline="", encoding="utf-8-sig") as stream:
        return list(csv.DictReader(stream))


def write_rows(path, rows, fields):
    with Path(path).open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def pool_training(data, main_data=None, main_splits=()):
    """Return only explicit released query/history files, with cutoff/ID checks."""
    data = Path(data).resolve()
    meta = json.loads((data/"metadata.json").read_text())
    if meta.get("round") != "adaptation" or meta.get("max_points") != 20:
        raise ValueError("Expected new adaptation kit with max_points=20")
    if len(set(main_splits)) != len(main_splits) or any(s not in {"train", "test"} for s in main_splits):
        raise ValueError("Old main splits must be unique train/test histories")
    sources = [("adaptation/train", data/"train")]
    if main_splits:
        if main_data is None:
            raise ValueError("Explicit main data required")
        main_data = Path(main_data).resolve()
        main_meta = json.loads((main_data/"metadata.json").read_text())
        if main_meta.get("round") != "main" or main_meta.get("season_id") != meta.get("season_id"):
            raise ValueError("Main round/season does not match adaptation")
        sources += [("main/"+s, main_data/s) for s in main_splits]
    queries, history, manifests, qids, machines, episodes = [], [], [], set(), set(), set()
    heldout_episodes = {r["episode_id"] for split in ("validation", "test")
                        for r in read_rows(data/split/"queries.csv")}
    for name, folder in sources:
        q, h = read_rows(folder/"queries.csv"), read_rows(folder/"history.csv")
        current = {(r["episode_id"], r["machine_id"]): int(r["cutoff"]) for r in q}
        source_eps = {r["episode_id"] for r in q}
        if len(current) != len(q) or source_eps & (heldout_episodes | episodes):
            raise ValueError("Duplicate or held-out training episode/machine")
        seen_ticks = set()
        for row in q:
            if row["query_id"] in qids or (row["episode_id"], row["machine_id"]) in machines:
                raise ValueError("Duplicate training identity")
            qids.add(row["query_id"])
            machines.add((row["episode_id"], row["machine_id"]))
        for row in h:
            key = (row["episode_id"], row["machine_id"])
            tick = int(row["tick"])
            if key not in current or tick < 0 or tick >= current[key] or int(row["payout"]) not in {0, 1, 2, 5, 20}:
                raise ValueError("Invalid or unavailable training history")
            if (*key, tick) in seen_ticks:
                raise ValueError("Duplicate history tick")
            seen_ticks.add((*key, tick))
        episodes.update(source_eps)
        queries.extend(q)
        history.extend(h)
        manifests.append({"source": name, "queries": len(q), "episodes": len(source_eps),
            "history_rows": len(h), "queries_sha256": sha(folder/"queries.csv"),
            "history_sha256": sha(folder/"history.csv")})
    return queries, history, manifests


def model_module():
    source = HERE if (HERE/"jaeger_model.py").is_file() else HERE.parent/"jaegers_entry"
    spec = importlib.util.spec_from_file_location("jaeger_model", source/"jaeger_model.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules["jaeger_model"] = module
    spec.loader.exec_module(module)
    return module, source


def forecast(model, checkpoint, data, split, out):
    q, h = model.read_split(str(Path(data)/split))
    predictions = model.predict(q, h, checkpoint["params"], expert_logprior=checkpoint["prior"], stack_w=checkpoint["stack"])
    rows = [{"query_id": r["query_id"], **{"p_"+str(k): repr(float(v)) for k, v in zip(model.PAYOUTS, predictions[r["query_id"]])}} for r in q]
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    write_rows(out, rows, ["query_id", "p_0", "p_1", "p_2", "p_5", "p_20"])


def fit(data, main_data, main_splits, out):
    import cloudpickle
    started = time.perf_counter()
    out = Path(out).resolve()
    out.mkdir(parents=True, exist_ok=False)
    q, h, manifests = pool_training(data, main_data, main_splits)
    model, source = model_module()
    params = json.loads((source/"params.json").read_text())
    with tempfile.TemporaryDirectory(prefix="pool-", dir=out) as temporary:
        folder = Path(temporary)
        write_rows(folder/"queries.csv", q, list(q[0]))
        write_rows(folder/"history.csv", h, list(h[0]))
        prior = model.learn_expert_prior(str(folder), params)
        stack = model.fit_stacker(str(folder), params, prior) if params.get("stack") else None
    checkpoint = {"params": params, "prior": prior, "stack": stack}
    (out/"checkpoint.pkl").write_bytes(cloudpickle.dumps(checkpoint))
    for split in ("validation", "test"):
        forecast(model, checkpoint, data, split, out/(split+".csv"))
    checker = Path(data).resolve().parent/"check_submission.py"
    checks = {}
    for split in ("validation", "test"):
        result = subprocess.run([sys.executable, str(checker), str(out/(split+".csv")), "--data", str(Path(data).resolve()), "--split", split], capture_output=True, text=True, timeout=60)
        checks[split] = result.stdout+result.stderr
        if result.returncode:
            raise RuntimeError(checks[split])
    stage = out/"entry"
    stage.mkdir()
    for name in ("jaeger_model.py", "params.json"):
        shutil.copyfile(source/name, stage/name)
    shutil.copyfile(__file__, stage/"combined_rounds.py")
    shutil.copyfile(out/"checkpoint.pkl", stage/"checkpoint.pkl")
    requirements = source.parent/"requirements-runtime.txt"
    shutil.copyfile(requirements if requirements.is_file() else source/"requirements.txt", stage/"requirements.txt")
    (stage/"README.md").write_text("# House Edge adaptation candidate\nPython 3.13; install pinned requirements.txt.\nRun reproduce.json offline with /data mounted. Loads our fitted checkpoint; no hidden labels.\nTraining pool is recorded in provenance.json. Existing historical-feature caveats remain.\nLocal candidate: cross-host/Linux portability is not certified.\n", encoding="utf-8")
    command = ["python", "combined_rounds.py", "predict", "--data", "/data", "--checkpoint", "checkpoint.pkl", "--out", "/output/submission.csv"]
    (stage/"reproduce.json").write_text(json.dumps({"image": "python", "command": command}, indent=2))
    record = {"status": "LOCAL_CANDIDATE_NOT_PORTABILITY_CERTIFIED", "training_sources": manifests,
        "training_queries": len(q), "training_episodes": len({r["episode_id"] for r in q}),
        "new_validation_or_test_in_fit": False, "hidden_query_outcomes_in_fit": False,
        "model_sha256": sha(source/"jaeger_model.py"), "params_sha256": sha(source/"params.json"),
        "checkpoint_sha256": sha(out/"checkpoint.pkl"), "test_csv_sha256": sha(out/"test.csv"),
        "validation_csv_sha256": sha(out/"validation.csv"), "wall_seconds": time.perf_counter()-started,
        "checks": checks, "historical_feature_caveat": "Original frozen model unchanged; not strict-as-of certified."}
    (stage/"provenance.json").write_text(json.dumps(record, indent=2), encoding="utf-8")
    with zipfile.ZipFile(out/"code.zip", "w", zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(stage.iterdir()):
            archive.write(path, path.name)
    record["code_zip_sha256"] = sha(out/"code.zip")
    (out/"metrics.json").write_text(json.dumps(record, indent=2), encoding="utf-8")
    print(json.dumps(record), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    train = commands.add_parser("fit")
    train.add_argument("--data", required=True)
    train.add_argument("--main-data")
    train.add_argument("--main-splits", nargs="*", default=[])
    train.add_argument("--out", required=True)
    predict = commands.add_parser("predict")
    predict.add_argument("--data", required=True)
    predict.add_argument("--checkpoint", required=True)
    predict.add_argument("--out", required=True)
    predict.add_argument("--split", default="test", choices=["test", "validation"])
    args = parser.parse_args()
    if args.command == "fit":
        fit(args.data, args.main_data, args.main_splits, args.out)
    else:
        import cloudpickle
        model, _ = model_module()
        forecast(model, cloudpickle.loads(Path(args.checkpoint).read_bytes()), args.data, args.split, args.out)


if __name__ == "__main__":
    main()
