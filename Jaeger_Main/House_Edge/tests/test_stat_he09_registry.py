"""HE-09 registry bridge tests: factory contract, study config, and one end-to-end worker evaluation.

Run from Jaeger_Main/House_Edge:  python -m pytest tests/test_stat_he09_registry.py -q
"""
import json
import sys
from pathlib import Path

import pytest

HE = Path(__file__).resolve().parents[1]
if str(HE) not in sys.path:
    sys.path.insert(0, str(HE))

from research import worker, sweep  # noqa: E402
from research.challengers import stat_he09_models as SM  # noqa: E402
from research.challengers.stat_he09_registry import HE09RegistryModel, factory  # noqa: E402
from research.dataset import conditions, episode_folds, read_labels  # noqa: E402

STUDY = HE / "research/configs/stats/he09/registry_study.json"
PUB = HE / "public"


def study():
    return json.loads(STUDY.read_text())


def test_worker_resolves_factory_for_every_he09_model():
    for config in study()["candidates"]:
        if config.get("factory"):
            model = worker.model_for(config, None)
            assert isinstance(model, HE09RegistryModel) and model.name == config["model"]


def test_unknown_model_rejected():
    with pytest.raises(ValueError):
        factory({"model": "not_a_model"})


def test_study_config_is_valid_and_skips_feature_cache():
    spec = study()
    rows = sweep.candidates(spec)
    assert {r["family"] for r in rows} == {"jaeger", "frequency", *SM.MODELS}
    assert spec["budget"]["trials"] >= len(rows)
    factory_rows = [r for r in rows if r.get("factory")]
    assert all(r.get("supervision") == "query" for r in factory_rows)
    need_cache = any(c["family"] not in ("jaeger", "frequency") and c.get("supervision", "historical") != "query" for c in rows)
    assert not need_cache


@pytest.mark.parametrize("name", sorted(SM.MODELS))
def test_fold_fit_predict_contract(name):
    queries, history, _ = SM.read_split(PUB / "train")
    labels = read_labels(PUB / "train")
    folds = episode_folds(queries, conditions(PUB / "train"), 4)
    hold = {ep for ep, f in folds.items() if f == 0}
    fit_q, fit_h = worker.subset(queries, history, set(folds) - hold)
    hold_q, hold_h = worker.subset(queries, history, hold)
    model = factory({"model": name}).fit(fit_q, fit_h, {q["query_id"]: labels[q["query_id"]] for q in fit_q})
    pred = model.predict_proba(hold_q, hold_h)
    assert set(pred) == {q["query_id"] for q in hold_q}  # validate_predictions already checked the simplex


def test_worker_evaluate_end_to_end(tmp_path):
    queries, _, _ = SM.read_split(PUB / "train")
    folds = episode_folds(queries, conditions(PUB / "train"), 4)
    config = next(c for c in study()["candidates"] if c.get("model") == "stat_dirichlet")
    result = worker.evaluate({"config": config, "data": str(PUB), "folds": folds, "cache": None}, tmp_path)
    assert (tmp_path / "result.json").exists() and (tmp_path / "oof.csv").exists()
    assert 0 < result["mean_brier"] < 1 and result["validation_target_exposure"] is False
    assert result["historical_signal_policy"] == "omitted"
    held = [ep for f in result["folds"] for ep in f["heldout_episodes"]]
    assert len(held) == len(set(held)) == len(folds)
