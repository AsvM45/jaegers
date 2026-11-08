"""Small preregistered platform acceptance study using the authoritative sweep.

This is a bounded integration benchmark, not Grok's model-search campaign.
Default is prepare-only; --execute invokes the existing runner explicitly.
"""
import argparse
import json
from pathlib import Path

from ..adapters import core_module
from ..common import ROOT, digest, environment, file_hash, require_python, write_json
from ..dataset import conditions, episode_folds
from ..sweep import identity, sweep
from .chat_he88_evidence import audit_registry


def study_spec():
    """Fixed hypotheses; no public-target selection and no parameter optimization."""
    base = ["type", "windows", "missingness"]
    return {"name": "chat_he88_platform_acceptance", "strategy": "grid", "seed": 0, "folds": 4,
            "budget": {"workers": 1, "trials": 6, "seconds": 900, "trial_seconds": 240},
            "candidates": [
                {"family": "jaeger", "causal": False, "seed": 0},
                {"family": "frequency", "params": {"strength": 20, "decay": 1}, "seed": 0},
                {"family": "frequency", "params": {"strength": 10, "decay": .97, "peer": .1}, "seed": 0},
                {"family": "logistic", "supervision": "query", "groups": base, "params": {"C": .1}, "seed": 0},
                {"family": "logistic", "supervision": "query", "groups": base + ["lags"], "params": {"C": .1}, "seed": 0},
                {"family": "logistic", "supervision": "query", "groups": base + ["lags", "peers"], "params": {"C": .1}, "seed": 0},
            ]}


def prepare(data, out):
    require_python()
    data, out = Path(data).resolve(), Path(out).resolve()
    queries, _ = core_module().read_split(str(data/"train"))
    spec = study_spec()
    folds = episode_folds(queries, conditions(data/"train"), spec["folds"])
    provenance = identity(data, folds, worker_cpus=2)
    payload = {"schema": "jaegers.he88_preregistration", "schema_version": 1,
               "spec": spec, "identity": provenance, "folds": folds,
               "analysis_source_sha256": {p.name: file_hash(p) for p in sorted(Path(__file__).parent.glob("chat_he88_*.py"))},
               "environment": environment(), "metric_source": "sampled_outcome_group_cv", "official_points": None,
               "purpose": "Pipeline acceptance and matched-fold feature diagnostics, not champion selection",
               "exposure": "Model architecture development-informed; no public validation scoring in this study",
               "champion_caveat": "Frozen unmodified anchor retains unsupported historical copied-signal policy; do not certify or promote it."}
    prereg = dict(payload, content_sha256=digest(payload))
    path = out/"he88_preregistration.json"
    if path.exists():
        previous = json.loads(path.read_text(encoding="utf-8"))
        # HEAD can advance for report/docs only; the runner uses numerical source bytes.
        comparable = lambda r: {k: v for k, v in r.items() if k != "content_sha256"}
        old, new = comparable(previous), comparable(prereg)
        old["identity"] = {k: v for k, v in old["identity"].items() if k != "head"}
        new["identity"] = {k: v for k, v in new["identity"].items() if k != "head"}
        if previous.get("content_sha256") != digest(comparable(previous)) or old != new:
            raise ValueError("Existing preregistration conflicts; use a new registry directory")
        return previous
    write_json(path, prereg)
    return prereg


def execute(data, out):
    prereg = prepare(data, out)
    summary = sweep(prereg["spec"], data, out)
    audit = audit_registry(out)
    write_json(Path(out)/"he88_attempt_audit.json", audit)
    return {"summary": summary, "audit_ok": audit["ok"],
            "preregistration_sha256": prereg["content_sha256"], "export": str(Path(out)/"exports/v1/registry.json")}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", default=str(ROOT/"public"))
    parser.add_argument("--out", required=True, help="New or identically preregistered single-host registry")
    parser.add_argument("--execute", action="store_true", help="Explicitly run the six bounded existing-runner trials")
    args = parser.parse_args(argv)
    result = execute(args.data, args.out) if args.execute else prepare(args.data, args.out)
    print(json.dumps(result, sort_keys=True, allow_nan=False))


if __name__ == "__main__":
    main()
