"""Finite, provenance-bound experiment preflight. Never imports or runs the scheduler.

CLI: python -m research.plan_he85 --grammar plan.json [--runner-spec study.json]
The optional export is only a bounded input to the existing research.sweep runner.
"""
from __future__ import annotations

import argparse
from collections import Counter
from copy import deepcopy
import hashlib
import itertools
import json
import math
from pathlib import Path
import re

SCHEMA = "jaegers.finite_plan"
MAX_ENUMERATION = 100_000
MAX_INTEGER = 2**63 - 1


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def digest(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def _keys(obj, allowed, required=()):
    if not isinstance(obj, dict) or set(obj) - set(allowed) or set(required) - set(obj):
        raise ValueError(f"Expected object with keys {sorted(allowed)}; required {sorted(required)}")


def _integer(value, name, maximum=MAX_INTEGER):
    if type(value) is not int or not 1 <= value <= maximum:
        raise ValueError(f"{name} must be a positive integer <= {maximum}")
    return value


def _positive(value, name):
    if type(value) not in (int, float) or not math.isfinite(value) or not 0 < value <= MAX_INTEGER:
        raise ValueError(f"{name} must be finite, positive and bounded")
    return value


def _names(values, allowed, name):
    if not isinstance(values, list) or any(not isinstance(x, str) for x in values):
        raise ValueError(f"{name} must be a list of names")
    if len(values) != len(set(values)) or set(values) - set(allowed):
        raise ValueError(f"{name} contains duplicate or unknown names")
    return sorted(values)


def _normalize(spec):
    """Normalize unordered axes; reject unknown keys rather than ignoring typos."""
    spec = deepcopy(spec)
    _keys(spec, ("schema", "schema_version", "name", "provenance", "evaluation", "features",
                 "families", "seeds", "resources"),
          ("schema", "schema_version", "name", "provenance", "evaluation", "features", "families", "seeds", "resources"))
    if spec["schema"] != SCHEMA or type(spec["schema_version"]) is not int or spec["schema_version"] != 1:
        raise ValueError("Unsupported finite-plan schema/version")
    if not isinstance(spec["name"], str) or not re.fullmatch(r"[a-zA-Z0-9_-]{1,80}", spec["name"]):
        raise ValueError("name must be a simple study name")
    p = spec["provenance"]
    hashes = ("source_sha256", "data_sha256", "feature_sha256", "runtime_sha256")
    _keys(p, (*hashes, "round", "season_id"), (*hashes, "round", "season_id"))
    if p["round"] not in ("main", "adaptation") or not isinstance(p["season_id"], str) or not p["season_id"]:
        raise ValueError("Explicit main/adaptation round and season_id required")
    for key in hashes:
        if not isinstance(p[key], str) or not re.fullmatch(r"[0-9a-f]{64}", p[key]):
            raise ValueError(f"{key} must be a SHA-256 digest")
    e = spec["evaluation"]
    _keys(e, ("source", "split", "folds", "split_manifest_sha256", "public_validation_exposure"),
          ("source", "split", "folds", "split_manifest_sha256", "public_validation_exposure"))
    if e["source"] != "sampled_outcome_group_cv" or e["split"] != "train":
        raise ValueError("Planning supports train-only episode-grouped sampled Brier; no official points")
    if e["public_validation_exposure"] not in ("development_exposed", "not_used_for_this_plan"):
        raise ValueError("Public validation must not be described as unseen")
    folds = e["folds"]
    if not isinstance(folds, dict) or not folds or any(not isinstance(k, str) or not k for k in folds):
        raise ValueError("folds must map whole episode IDs to folds")
    if any(type(f) is not int or f < 0 for f in folds.values()):
        raise ValueError("Fold IDs must be nonnegative integers")
    if set(folds.values()) != set(range(len(set(folds.values())))) or len(set(folds.values())) < 2:
        raise ValueError("At least two contiguous held-out fold IDs required")
    if e["split_manifest_sha256"] != digest(folds):
        raise ValueError("split_manifest_sha256 does not match the episode manifest")
    f = spec["features"]
    _keys(f, ("catalog", "required", "optional", "mutually_exclusive"), ("catalog", "required", "optional"))
    catalog = f["catalog"]
    if not isinstance(catalog, dict) or not catalog or len(catalog) > 64:
        raise ValueError("Explicit feature catalog with at most 64 groups required")
    for name, group in catalog.items():
        if not isinstance(name, str) or not re.fullmatch(r"[a-zA-Z0-9_]+", name):
            raise ValueError("Invalid feature group name")
        _keys(group, ("requires", "availability"), ("requires", "availability"))
        group["requires"] = _names(group["requires"], catalog, "group prerequisites")
        if name in group["requires"]:
            raise ValueError("A group cannot require itself")
        if group["availability"] not in ("past_only", "static_machine_type", "query_only"):
            raise ValueError("Unknown group availability")
    f["required"] = _names(f["required"], catalog, "required groups")
    f["optional"] = _names(f["optional"], catalog, "optional groups")
    if set(f["required"]) & set(f["optional"]):
        raise ValueError("Required and optional group axes overlap")
    f["mutually_exclusive"] = sorted([_names(x, catalog, "exclusion") for x in f.get("mutually_exclusive", [])])
    if any(len(x) < 2 for x in f["mutually_exclusive"]):
        raise ValueError("An exclusion must contain at least two groups")
    families = spec["families"]
    if not isinstance(families, dict) or not families:
        raise ValueError("At least one model family required")
    for name, family in families.items():
        if not isinstance(name, str) or not name:
            raise ValueError("Invalid family")
        _keys(family, ("base", "allowed_groups", "variants", "parameters"),
              ("base", "allowed_groups", "variants", "parameters"))
        family["allowed_groups"] = _names(family["allowed_groups"], catalog, "allowed groups")
        _config(family["base"])
        variants = family["variants"]
        if not isinstance(variants, dict) or not variants:
            raise ValueError("At least one named variant required")
        for variant in variants.values():
            _keys(variant, ("requires_groups", "config", "transforms"), ("requires_groups", "config", "transforms"))
            variant["requires_groups"] = _names(variant["requires_groups"], catalog, "variant prerequisites")
            _config(variant["config"])
            transforms = variant["transforms"]
            if not isinstance(transforms, dict) or not transforms:
                raise ValueError("Named mutually exclusive transform choices required (identity is allowed)")
            for transform in transforms.values():
                _keys(transform, ("requires_groups", "config"), ("requires_groups", "config"))
                transform["requires_groups"] = _names(transform["requires_groups"], catalog, "transform prerequisites")
                _config(transform["config"])
        params = family["parameters"]
        if not isinstance(params, dict):
            raise ValueError("parameters must be a finite object")
        for key, axis in params.items():
            if not re.fullmatch(r"params\.[a-zA-Z0-9_]+", key):
                raise ValueError("Parameter axes must be params.<name>")
            _keys(axis, ("values", "when"), ("values",))
            values = axis["values"]
            if not isinstance(values, list) or not values or len({canonical(x) for x in values}) != len(values):
                raise ValueError("Finite nonempty unique parameter values required")
            if any(type(x) not in (str, int, float, bool, type(None)) for x in values):
                raise ValueError("Parameter values must be JSON scalars")
            axis["values"] = sorted(values, key=canonical)
            when = axis.setdefault("when", {})
            if not isinstance(when, dict) or set(when) - params.keys() or key in when:
                raise ValueError("Conditional parameters require other declared parameters")
            for parent, choices in when.items():
                if not isinstance(choices, list) or not choices or len({canonical(x) for x in choices}) != len(choices):
                    raise ValueError("Invalid conditional choices")
                if {canonical(x) for x in choices} - {canonical(x) for x in params[parent]["values"]}:
                    raise ValueError("Conditional choice outside parent axis")
                when[parent] = sorted(choices, key=canonical)
        _parameter_order(params)
    seeds = spec["seeds"]
    if not isinstance(seeds, list) or not seeds or any(type(x) is not int or not 0 <= x <= 2**32-1 for x in seeds) or len(seeds) != len(set(seeds)):
        raise ValueError("Unique uint32 seeds required")
    spec["seeds"] = sorted(seeds)
    r = spec["resources"]
    required = ("max_trials", "trial_seconds", "wall_seconds", "workers", "cpus_per_worker", "memory_gib_per_worker")
    _keys(r, required, required)
    _integer(r["max_trials"], "max_trials", MAX_ENUMERATION)
    _integer(r["workers"], "workers", 2)
    _integer(r["cpus_per_worker"], "cpus_per_worker", 2)
    if r["workers"] * r["cpus_per_worker"] > 2:
        raise ValueError("Existing runner supports at most two aggregate CPUs")
    expected_cpus = 2 // r["workers"]
    if r["cpus_per_worker"] != expected_cpus or r["memory_gib_per_worker"] != 8:
        raise ValueError("Existing grid runner uses 2//workers CPUs and 8 GiB per worker")
    for key in ("trial_seconds", "wall_seconds", "memory_gib_per_worker"):
        _positive(r[key], key)
    canonical(spec)  # reject NaN/Infinity even in conditional values/configs
    return spec


def _config(config):
    if not isinstance(config, dict) or set(config) & {"family", "groups", "seed"}:
        raise ValueError("Config fragments must not override family/groups/seed")


def _parameter_order(params):
    pending, order = set(params), []
    while pending:
        ready = sorted(k for k in pending if not set(params[k].get("when", {})) & pending)
        if not ready:
            raise ValueError("Conditional parameter cycle")
        order.extend(ready)
        pending.difference_update(ready)
    return order


def _parameter_rows(params):
    order = _parameter_order(params)
    def walk(index, row):
        if index == len(order):
            yield dict(row)
            return
        key = order[index]
        axis = params[key]
        active = all(parent in row and canonical(row[parent]) in {canonical(x) for x in choices}
                     for parent, choices in axis.get("when", {}).items())
        if active:
            for value in axis["values"]:
                row[key] = value
                yield from walk(index + 1, row)
            row.pop(key, None)
        else:
            yield from walk(index + 1, row)
    return walk(0, {})


def _merge(target, fragment):
    for key, value in fragment.items():
        if key in target:
            if isinstance(value, dict) and isinstance(target[key], dict):
                _merge(target[key], value)
            elif canonical(value) != canonical(target[key]):
                raise ValueError(f"Conflicting config fragments at {key}")
        else:
            target[key] = deepcopy(value)


def _reason(groups, features, family, variant, transform):
    selected = set(groups)
    if not selected:
        return "empty_features"
    if selected - set(family["allowed_groups"]):
        return "family_disallowed_group"
    if any(features["catalog"][group]["availability"] == "query_only" for group in groups):
        return "historical_signal_unavailable"
    for group in groups:
        descriptor = features["catalog"][group]
        if set(descriptor["requires"]) - selected:
            return "missing_group_prerequisite"
    if any(len(selected & set(exclusive)) > 1 for exclusive in features["mutually_exclusive"]):
        return "mutually_exclusive_groups"
    if set(variant["requires_groups"]) - selected:
        return "missing_variant_prerequisite"
    if set(transform["requires_groups"]) - selected:
        return "missing_transform_prerequisite"
    return None


def preflight(grammar, enumeration_limit=MAX_ENUMERATION):
    """Return stable count/budget evidence without launching trials or reading a DB.

    Large independent axes are counted symbolically. Constrained spaces beyond the
    bounded enumeration limit are explicitly blocked; no sampled count is called exact.
    """
    _integer(enumeration_limit, "enumeration_limit", MAX_ENUMERATION)
    spec = _normalize(grammar)
    features, families, resources = spec["features"], spec["families"], spec["resources"]
    factor = 0
    parameter_rows = {}
    for name, family in sorted(families.items()):
        rows = list(itertools.islice(_parameter_rows(family["parameters"]), enumeration_limit + 1))
        if len(rows) > enumeration_limit:
            raise ValueError("Conditional parameter space exceeds bounded enumeration; reduce finite axes")
        parameter_rows[name] = rows
        factor += len(rows) * sum(len(v["transforms"]) for v in family["variants"].values())
    raw = 2**len(features["optional"]) * factor * len(spec["seeds"])
    independent = not features["mutually_exclusive"] and all(
        not features["catalog"][name]["requires"] and features["catalog"][name]["availability"] != "query_only"
        for name in features["required"] + features["optional"]) and all(
        set(f["allowed_groups"]) >= set(features["required"] + features["optional"]) and all(
            not v["requires_groups"] and all(not t["requires_groups"] for t in v["transforms"].values())
            for v in f["variants"].values()) for f in families.values())
    report = {"schema": SCHEMA + ".report", "schema_version": 1, "plan_sha256": digest(spec),
              "grammar": spec, "raw_branch_count": raw, "exact_candidate_count": None,
              "rejected_branches": {}, "candidates": [], "status": "READY", "warnings": [],
              "metric_source": "sampled_outcome_group_cv", "official_points": None}
    if raw > enumeration_limit:
        report["status"] = "BLOCKED_SPACE"
        report["warnings"].append("Space exceeds bounded enumeration; reduce axes before export. No trials launched.")
        if independent:
            # Variants/transforms can be aliases for the same numerical config.
            # Count unique prototypes before multiplying by independent masks.
            prototypes = set()
            for name, family in sorted(families.items()):
                for variant in family["variants"].values():
                    for transform in variant["transforms"].values():
                        for params, seed in itertools.product(parameter_rows[name], spec["seeds"]):
                            config = {"family": name, "seed": seed}
                            for fragment in (family["base"], variant["config"], transform["config"]):
                                _merge(config, fragment)
                            for key, value in params.items():
                                _merge(config, {"params": {key.removeprefix("params."): value}})
                            prototypes.add(canonical(config))
                            if len(prototypes) > enumeration_limit:
                                raise ValueError("Prototype space exceeds bounded enumeration")
            masks = 2**len(features["optional"]) - (not features["required"])
            empty = factor * len(spec["seeds"]) if not features["required"] else 0
            report["exact_candidate_count"] = masks * len(prototypes)
            report["rejected_branches"] = {"empty_features": empty} if empty else {}
            report["duplicate_legal_branches"] = raw - empty - report["exact_candidate_count"]
        else:
            report["warnings"].append("Exact constrained count unavailable within cap; raw_branch_count is an upper bound.")
    else:
        rejected, candidates = Counter(), {}
        for mask in itertools.product((False, True), repeat=len(features["optional"])):
            groups = sorted(features["required"] + [g for g, enabled in zip(features["optional"], mask) if enabled])
            for name, family in sorted(families.items()):
                for variant_name, variant in sorted(family["variants"].items()):
                    for transform_name, transform in sorted(variant["transforms"].items()):
                        reason = _reason(groups, features, family, variant, transform)
                        branch_size = len(parameter_rows[name]) * len(spec["seeds"])
                        if reason:
                            rejected[reason] += branch_size
                            continue
                        for params, seed in itertools.product(parameter_rows[name], spec["seeds"]):
                            config = {"family": name, "groups": groups, "seed": seed}
                            for fragment in (family["base"], variant["config"], transform["config"]):
                                _merge(config, fragment)
                            for key, value in params.items():
                                _merge(config, {"params": {key.removeprefix("params."): value}})
                            candidate_id = digest({"config": config, "provenance": spec["provenance"],
                                                   "evaluation": spec["evaluation"], "resources": resources})
                            entry = candidates.setdefault(candidate_id, {"candidate_id": candidate_id, "config": config, "branches": []})
                            entry["branches"].append({"variant": variant_name, "transform": transform_name})
        report["candidates"] = [candidates[k] for k in sorted(candidates)]
        report["exact_candidate_count"] = len(candidates)
        report["rejected_branches"] = dict(sorted(rejected.items()))
        report["duplicate_legal_branches"] = raw - sum(rejected.values()) - len(candidates)
        if not candidates:
            report["status"] = "BLOCKED_EMPTY"
    count = report["exact_candidate_count"]
    scheduled = min(resources["max_trials"], count) if count is not None else None
    # Scheduler checks remaining wall time at dispatch. Setup/cache time is extra.
    work_seconds = scheduled * resources["trial_seconds"] if scheduled is not None else None
    cpu_seconds = min(work_seconds, resources["workers"] * resources["wall_seconds"]) * resources["cpus_per_worker"] if work_seconds is not None else None
    report["resource_preflight"] = dict(resources, planned_trials=scheduled,
        uncapped_serial_trial_seconds=work_seconds, approximate_max_worker_cpu_seconds=cpu_seconds,
        peak_worker_memory_gib=resources["workers"] * resources["memory_gib_per_worker"],
        estimate_only=True, excludes="coordinator, cache construction, source staging and process cleanup")
    return report


def runner_spec(report):
    """One-way bounded compilation. Registry still assigns authoritative trial IDs."""
    if report != preflight(report["grammar"]) or report["status"] != "READY":
        raise ValueError("Only an unmodified, READY preflight can be exported")
    policy = report["grammar"]["resources"]
    rows = report["candidates"][:policy["max_trials"]]
    return {"name": report["grammar"]["name"], "strategy": "grid", "seed": 0,
            "folds": len(set(report["grammar"]["evaluation"]["folds"].values())),
            "budget": {"trials": len(rows), "workers": policy["workers"],
                       "seconds": policy["wall_seconds"], "trial_seconds": policy["trial_seconds"]},
            "candidates": [deepcopy(r["config"]) for r in rows],
            "preflight": {"plan_sha256": report["plan_sha256"],
                          "warning": "Before execution verify live data/source/runtime and regenerated split manifest match the preregistration; runner owns identity and enforcement."}}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--grammar", required=True)
    parser.add_argument("--runner-spec", help="Optional JSON export; does not execute it")
    parser.add_argument("--out", help="Optional UTF-8 JSON report, avoiding shell redirection encoding")
    args = parser.parse_args(argv)
    try:
        paths = [Path(p).resolve() for p in (args.grammar, args.runner_spec, args.out) if p]
        if len(set(paths)) != len(paths):
            raise ValueError("Grammar and output paths must be distinct")
        report = preflight(json.loads(Path(args.grammar).read_text(encoding="utf-8")))
        if args.runner_spec:
            Path(args.runner_spec).write_text(json.dumps(runner_spec(report), indent=2, sort_keys=True) + "\n", encoding="utf-8")
        rendered = json.dumps(report, indent=2, sort_keys=True, allow_nan=False)
        if args.out:
            Path(args.out).write_text(rendered + "\n", encoding="utf-8")
        print(rendered)
        return 0 if report["status"] == "READY" else 2
    except (ValueError, KeyError, TypeError) as exc:
        parser.error(str(exc))


if __name__ == "__main__":
    raise SystemExit(main())
