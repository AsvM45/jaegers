"""Finite planner acceptance: scientific provenance, exact counting and no execution."""
from copy import deepcopy
import json

import pytest

from research.plan_he85 import digest, main, preflight, runner_spec


def grammar():
    folds = {"train_ep_a": 0, "train_ep_b": 1, "train_ep_c": 0, "train_ep_d": 1}
    return {
        "schema": "jaegers.finite_plan", "schema_version": 1, "name": "he85_smoke",
        "provenance": {"round": "main", "season_id": "fixture_only",
                       **{k: "a"*64 for k in ("source_sha256", "data_sha256", "feature_sha256", "runtime_sha256")}},
        "evaluation": {"source": "sampled_outcome_group_cv", "split": "train", "folds": folds,
                       "split_manifest_sha256": digest(folds), "public_validation_exposure": "development_exposed"},
        "features": {"catalog": {"type": {"requires": [], "availability": "static_machine_type"},
                                  "lags": {"requires": [], "availability": "past_only"},
                                  "pairs": {"requires": ["lags"], "availability": "past_only"}},
                     "required": ["type"], "optional": ["lags", "pairs"]},
        "families": {"logistic": {"base": {"supervision": "historical"},
                                  "allowed_groups": ["type", "lags", "pairs"],
                                  "variants": {"plain": {"requires_groups": [], "config": {},
                                                         "transforms": {"identity": {"requires_groups": [], "config": {}}}}},
                                  "parameters": {"params.C": {"values": [.1, 1.]}}}},
        "seeds": [0, 7],
        "resources": {"max_trials": 5, "workers": 1, "cpus_per_worker": 2,
                      "memory_gib_per_worker": 8, "trial_seconds": 30, "wall_seconds": 90},
    }


def test_exact_constraints_count_and_resource_bounds():
    report = preflight(grammar())
    assert report["raw_branch_count"] == 16
    assert report["exact_candidate_count"] == 12
    assert report["rejected_branches"] == {"missing_group_prerequisite": 4}
    resources = report["resource_preflight"]
    assert resources["planned_trials"] == 5
    assert resources["approximate_max_worker_cpu_seconds"] == 180
    assert resources["peak_worker_memory_gib"] == 8
    assert resources["estimate_only"] is True
    assert report["official_points"] is None


def test_order_independent_digest_candidates_and_report():
    first = grammar()
    other = json.loads(json.dumps(first, sort_keys=True))
    other["seeds"].reverse()
    other["features"]["optional"].reverse()
    other["families"]["logistic"]["allowed_groups"].reverse()
    other["families"]["logistic"]["parameters"]["params.C"]["values"].reverse()
    assert preflight(first) == preflight(other)
    assert first == grammar()  # no caller mutation


def test_conditional_axes_only_expand_when_active_and_topological():
    spec = grammar()
    spec["families"]["logistic"]["parameters"] = {
        "params.C": {"values": [.1, 1.], "when": {"params.mode": ["fit"]}},
        "params.mode": {"values": ["fixed", "fit"]},
    }
    report = preflight(spec)
    assert report["raw_branch_count"] == 24  # three parameter rows, not four
    assert report["exact_candidate_count"] == 18
    fixed = [r["config"] for r in report["candidates"] if r["config"]["params"]["mode"] == "fixed"]
    assert all("C" not in c["params"] for c in fixed)


def test_variants_transforms_exclusions_and_alias_deduplication():
    spec = grammar()
    spec["features"]["catalog"]["pairs"]["requires"] = []
    spec["features"]["mutually_exclusive"] = [["lags", "pairs"]]
    family = spec["families"]["logistic"]
    variant = family["variants"]["plain"]
    variant["transforms"]["scaled"] = {"requires_groups": ["lags"], "config": {"scaling": "standard"}}
    family["variants"]["lag_variant"] = {"requires_groups": ["lags"], "config": {"variant": "lag"},
                                         "transforms": {"identity": {"requires_groups": [], "config": {}}}}
    report = preflight(spec)
    assert report["rejected_branches"]["mutually_exclusive_groups"] == 12
    assert report["rejected_branches"]["missing_variant_prerequisite"] == 8
    assert report["rejected_branches"]["missing_transform_prerequisite"] == 8
    assert report["exact_candidate_count"] == 20
    alias = deepcopy(family["variants"]["plain"])
    family["variants"]["alias"] = alias
    with_alias = preflight(spec)
    assert with_alias["exact_candidate_count"] == 20
    assert with_alias["duplicate_legal_branches"] == 16


def test_family_allowlist_and_historical_signal_are_rejections():
    spec = grammar()
    spec["families"]["logistic"]["allowed_groups"] = ["type"]
    assert preflight(spec)["rejected_branches"] == {"family_disallowed_group": 12}
    spec = grammar()
    spec["features"]["catalog"]["type"]["availability"] = "query_only"
    report = preflight(spec)
    assert report["status"] == "BLOCKED_EMPTY"
    assert report["rejected_branches"] == {"historical_signal_unavailable": 16}
    with pytest.raises(ValueError, match="READY"):
        runner_spec(report)


def test_twenty_toggles_counted_without_materialization_or_launch():
    spec = grammar()
    names = [f"g{i}" for i in range(20)]
    spec["features"]["catalog"].update({g: {"requires": [], "availability": "past_only"} for g in names})
    spec["features"]["optional"] = names
    spec["families"]["logistic"]["allowed_groups"] = names + ["type"]
    spec["families"]["logistic"]["parameters"] = {}
    spec["seeds"] = [0]
    report = preflight(spec)
    assert report["status"] == "BLOCKED_SPACE"
    assert report["raw_branch_count"] == report["exact_candidate_count"] == 1_048_576
    assert report["candidates"] == []
    spec["families"]["logistic"]["variants"]["alias"] = deepcopy(spec["families"]["logistic"]["variants"]["plain"])
    assert preflight(spec)["exact_candidate_count"] == 1_048_576


def test_constrained_explosion_is_honestly_unknown_and_blocked():
    report = preflight(grammar(), enumeration_limit=4)
    assert report["status"] == "BLOCKED_SPACE"
    assert report["raw_branch_count"] == 16
    assert report["exact_candidate_count"] is None
    assert report["candidates"] == []
    assert report["resource_preflight"]["planned_trials"] is None


@pytest.mark.parametrize("key,value", [("max_trials", 0), ("max_trials", 100001), ("max_trials", 2**70),
    ("workers", 0), ("workers", 3), ("workers", True), ("trial_seconds", 0), ("trial_seconds", float("inf")),
    ("wall_seconds", -1), ("wall_seconds", float("nan")), ("memory_gib_per_worker", 16), ("cpus_per_worker", 1)])
def test_invalid_caps(key, value):
    spec = grammar()
    spec["resources"][key] = value
    with pytest.raises(ValueError):
        preflight(spec)


@pytest.mark.parametrize("mutation", [
    lambda s: s.update(schema_version=2), lambda s: s.update(seeds=[]),
    lambda s: s["evaluation"].pop("split_manifest_sha256"),
    lambda s: s["evaluation"].update(source="official_points"),
    lambda s: s["evaluation"].update(split="validation"),
    lambda s: s["evaluation"].update(public_validation_exposure="unseen"),
    lambda s: s["evaluation"].update(split_manifest_sha256="b"*64),
    lambda s: s["provenance"].update(data_sha256="missing"),
    lambda s: s["features"].update(optional=["unknown"]),
    lambda s: s["features"].update(optional=["lags", "lags"]),
    lambda s: s["features"].update(typo=[]),
    lambda s: s["families"]["logistic"]["parameters"].update({"params.C": {"values": []}}),
    lambda s: s["families"]["logistic"]["parameters"].update({"params.C": {"values": [1, 1]}}),
    lambda s: s["families"]["logistic"]["parameters"].update({"params.C": {"values": [1], "when": {"missing": [1]}}}),
    lambda s: s["families"]["logistic"]["base"].update(family="frequency"),
])
def test_invalid_grammar(mutation):
    spec = grammar()
    mutation(spec)
    with pytest.raises(ValueError):
        preflight(spec)


def test_parameter_cycle_and_contradictory_config_rejected():
    spec = grammar()
    spec["families"]["logistic"]["parameters"] = {
        "params.a": {"values": [1], "when": {"params.b": [1]}},
        "params.b": {"values": [1], "when": {"params.a": [1]}}}
    with pytest.raises(ValueError, match="cycle"):
        preflight(spec)
    spec = grammar()
    spec["families"]["logistic"]["base"]["params"] = {"C": 999}
    with pytest.raises(ValueError, match="Conflicting"):
        preflight(spec)


def test_plan_and_candidate_identity_bind_provenance_and_policy():
    first = preflight(grammar())
    for section, key, value in [("provenance", "data_sha256", "b"*64), ("provenance", "runtime_sha256", "b"*64),
                                ("resources", "wall_seconds", 100)]:
        spec = grammar()
        spec[section][key] = value
        changed = preflight(spec)
        assert changed["plan_sha256"] != first["plan_sha256"]
        assert {r["candidate_id"] for r in first["candidates"]}.isdisjoint(r["candidate_id"] for r in changed["candidates"])


def test_runner_export_is_capped_compatible_and_rejects_tampering():
    from research.sweep import candidates
    report = preflight(grammar())
    compiled = runner_spec(report)
    assert len(candidates(compiled)) == compiled["budget"]["trials"] == 5
    assert compiled["budget"]["workers"] == 1
    report["resource_preflight"]["planned_trials"] = 999
    with pytest.raises(ValueError):
        runner_spec(report)


def test_cli_only_writes_requested_json_and_has_stable_report(tmp_path, capsys):
    source, export, report_path = tmp_path/"grammar.json", tmp_path/"study.json", tmp_path/"report.json"
    source.write_text(json.dumps(grammar()), encoding="utf-8")
    assert main(["--grammar", str(source), "--runner-spec", str(export), "--out", str(report_path)]) == 0
    first = capsys.readouterr().out
    assert main(["--grammar", str(source)]) == 0
    assert capsys.readouterr().out == first
    assert sorted(p.name for p in tmp_path.iterdir()) == ["grammar.json", "report.json", "study.json"]
    assert json.loads(report_path.read_text(encoding="utf-8")) == json.loads(first)
    assert json.loads(export.read_text())["preflight"]["plan_sha256"] == json.loads(first)["plan_sha256"]


def test_cli_rejects_overwriting_grammar(tmp_path):
    source = tmp_path/"grammar.json"
    before = json.dumps(grammar())
    source.write_text(before, encoding="utf-8")
    with pytest.raises(SystemExit):
        main(["--grammar", str(source), "--out", str(source)])
    assert source.read_text(encoding="utf-8") == before


def test_parameter_explosion_and_enumeration_limit_are_bounded():
    spec = grammar()
    spec["families"]["logistic"]["parameters"] = {"params.C": {"values": list(range(101))}}
    with pytest.raises(ValueError, match="parameter space"):
        preflight(spec, enumeration_limit=100)
    with pytest.raises(ValueError):
        preflight(spec, enumeration_limit=0)
