from collections import defaultdict
import json
import numpy as np
import pytest
from research.feature_api import FeatureComputer, validate_groups
from research.dataset import episode_folds
from research.metrics import paired
from research.registry import Registry
from research.adapters import FrequencyModel, Serializable
from slot_forecasting.contest import contest_score
from slot_forecasting.schema import Target


def data():
    history=defaultdict(dict)
    q=dict(query_id="q",episode_id="ep",machine_id="m0",machine_type="steady",signal="1",cutoff="30")
    history[("ep","m0")]={t:(0,1,2,5,20)[t%5] for t in range(40)}
    history[("ep","m1")]={t:20 for t in range(40)}
    return q,history


def test_exact_lag_missing_and_future_invariance():
    q,h=data()
    first,names=FeatureComputer(h).row(q)
    h[("ep","m0")][30]=20
    h[("ep","m1")][30]=0
    np.testing.assert_array_equal(first,FeatureComputer(h).row(q)[0])
    del h[("ep","m0")][28]
    values,names=FeatureComputer(h).row(q,("lags",))
    assert values[6] == 1  # lag 2 is missing, not the previous observed row
    assert values[7:12].sum() == 0


def test_feature_dependencies_and_historical_signal_guard():
    with pytest.raises(ValueError):
        validate_groups(["pairs"])
    with pytest.raises(ValueError):
        validate_groups(["current_signal"])
    validate_groups(["type","current_signal"],historical=False)


def test_grouped_folds_reproducible_stratified():
    queries=[]; conditions={}
    for c in ("stable","short_history","drift","shared_change"):
        for e in range(8):
            for m in range(2):
                q={"query_id":f"{c}{e}{m}","episode_id":f"{c}{e}"}
                queries.append(q); conditions[q["query_id"]]=c
    folds=episode_folds(queries,conditions)
    assert folds == episode_folds(list(reversed(queries)),conditions)
    for fold in range(4):
        eps={ep for ep,f in folds.items() if f == fold}
        assert len(eps) == 8
        assert eps.isdisjoint({ep for ep,f in folds.items() if f != fold})


def test_official_scorer_known_perfect_and_reference():
    target=[]; groups={}; exact={}; reference={}
    for c in ("stable","short_history","drift","shared_change"):
        target.append(Target(c,c,(.6,.2,.1,.08,.02),0))
        groups[c]=c; exact[c]=(.6,.2,.1,.08,.02); reference[c]=(.2,)*5
    assert contest_score(exact,target,groups,reference,max_points=60)["technical_points"] == 60
    assert contest_score(reference,target,groups,reference,max_points=60)["technical_points"] == 30


def test_registry_resume_and_failed_attempt_preservation(tmp_path):
    registry=Registry(tmp_path)
    with registry.coordinator():
        trial=registry.register("test",{"family":"frequency"},{"split":"x"})
        first=registry.start(trial)
        (first/"evidence.txt").write_text("original")
        second=registry.start(trial)
        assert first != second
        assert (first/"evidence.txt").read_text() == "original"
        registry.finish(trial,"SUCCEEDED",{"mean_brier":.4})
        assert registry.start(trial) is None
        assert registry.rows()[0]["attempt"] == 2


def test_serialized_model_predictions_match(tmp_path):
    q,h=data()
    model=FrequencyModel().fit([q],h)
    path=tmp_path/"model.joblib"
    model.save(path)
    loaded=Serializable.load(path)
    np.testing.assert_array_equal(model.predict_proba([q],h)["q"],loaded.predict_proba([q],h)["q"])


def test_paired_comparison_rejects_mismatched_episodes():
    baseline={"per_episode":{"a":.4},"episode_conditions":{"a":"stable"}}
    with pytest.raises(ValueError):
        paired({"per_episode":{"b":.3},"episode_conditions":{"b":"stable"}},baseline)
