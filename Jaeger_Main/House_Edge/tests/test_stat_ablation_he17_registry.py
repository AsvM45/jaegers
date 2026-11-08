"""HE-17 registry bridge tests.  Run from Jaeger_Main/House_Edge:
    python -m pytest tests/test_stat_ablation_he17_registry.py -q
"""
import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

HE = Path(__file__).resolve().parents[1]
if str(HE) not in sys.path:
    sys.path.insert(0, str(HE))

from research import sweep, worker  # noqa: E402
from research.challengers import stat_ablation_he17_registry as R  # noqa: E402
from research.dataset import conditions, episode_folds, read_labels  # noqa: E402

STUDY = HE / "research/configs/stats/ablations/he17_registry_study.json"
PREREG = HE / "research/configs/stats/ablations/he17_ablations.json"
PARAMS = json.loads((HE / "jaegers_entry/params.json").read_text())
PUB = HE / "public"


def spec():
    return json.loads(STUDY.read_text())


def prereg():
    return {v["name"]: v["change"] for v in json.loads(PREREG.read_text())["variants"]}


def by_label():
    s = spec()
    return {s["labels"][str(i)].split(" ")[0]: c for i, c in enumerate(s["candidates"])}


def test_study_covers_every_preregistered_variant_once():
    s = spec()
    rows = sweep.candidates(s)
    assert len(rows) == len(s["candidates"]) <= s["budget"]["trials"]
    assert set(prereg()) <= set(by_label())
    assert not any(c["family"] not in ("jaeger", "frequency") and c.get("supervision", "historical") != "query" for c in rows)


def test_param_only_variants_match_preregistration():
    pre, lab = prereg(), by_label()
    for name in ("nostack", "no_size_experts", "no_peer_evidence", "no_expert_prior", "slower_forgetting", "faster_forgetting"):
        assert lab[name]["family"] == "jaeger" and lab[name]["params"] == pre[name]["params"], name
    # "=lam"/"=prior" references are written out as numbers for the registry's JaegerModel
    assert lab["no_short_history_prior"]["params"] == {"lam_short": PARAMS["lam"], "prior_short": PARAMS["prior"]}


def test_inline_changes_are_identical_to_preregistration():
    pre, lab = prereg(), by_label()
    for name in R.CODE_LEVEL:
        assert lab[name]["variant"] == name and lab[name]["change"] == pre[name], name


def test_factory_variants_resolve_through_worker():
    for c in spec()["candidates"]:
        if c.get("factory"):
            m = worker.model_for(c, None)
            assert isinstance(m, R.HE17AblationModel) and m.name in R.CODE_LEVEL


def test_unknown_variant_or_change_rejected():
    with pytest.raises(ValueError):
        R.factory({"variant": "nope", "change": {}})
    with pytest.raises(ValueError):
        R.factory({"variant": "nosig", "change": {"mystery": 1}})


def test_exposure_flags_are_champion_derived():
    pre = prereg()
    assert R.exposure_flags(pre["nosig"])["historical_signal_policy"] == "omitted"
    assert R.exposure_flags(pre["single_lag_only"])["historical_signal_policy"] == "unsupported_copied_signal"
    assert R.exposure_flags(pre["train_size_regimes"])["size_regimes_from_validation"] is False
    assert all(R.exposure_flags(pre[n])["validation_target_exposure"] for n in R.CODE_LEVEL)


def test_patches_do_not_leak_into_champion_file_or_shared_module():
    from research.adapters import core_module
    before = hashlib.sha256((HE / "jaegers_entry/jaeger_model.py").read_bytes()).hexdigest()
    R.HE17AblationModel("single_lag_only", {"experts": "single_lag_only"})._core()
    assert len(core_module().EXPERTS) == 73
    assert hashlib.sha256((HE / "jaegers_entry/jaeger_model.py").read_bytes()).hexdigest() == before


def test_factory_imports_inside_registry_snapshot_layout(tmp_path):
    """Regression: workers run from a frozen snapshot without research/analysis or research/configs."""
    snap = tmp_path / "source"
    (snap / "research").mkdir(parents=True)
    for f in (HE / "research").glob("*.py"):
        shutil.copyfile(f, snap / "research" / f.name)
    for d in ("jaegers_entry", "slot_forecasting", "research/models", "research/features",
              "research/challengers", "research/extensions"):
        shutil.copytree(HE / d, snap / d, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    code = ("import json,sys; from research import worker; "
            "c=json.loads(sys.argv[1]); m=worker.model_for(c,None); print(type(m).__name__, len(m._core().EXPERTS))")
    cfg = by_label()["single_lag_only"]
    out = subprocess.run([sys.executable, "-B", "-c", code, json.dumps(cfg)], cwd=snap, capture_output=True, text=True)
    assert out.returncode == 0, out.stderr[-1500:]
    assert out.stdout.split() == ["HE17AblationModel", "17"]


def test_fold_fit_predict_contract_small():
    queries, history = worker.core_module().read_split(str(PUB / "train"))
    labels = read_labels(PUB / "train")
    folds = episode_folds(queries, conditions(PUB / "train"), 4)
    fit_eps = sorted(ep for ep, f in folds.items() if f != 0)[:12]
    hold_eps = sorted(ep for ep, f in folds.items() if f == 0)[:4]
    fit_q, fit_h = worker.subset(queries, history, set(fit_eps))
    hold_q, hold_h = worker.subset(queries, history, set(hold_eps))
    model = R.factory(by_label()["nosig"]).fit(fit_q, fit_h, {q["query_id"]: labels[q["query_id"]] for q in fit_q})
    assert 13 not in model.cols
    pred = model.predict_proba(hold_q, hold_h)
    assert set(pred) == {q["query_id"] for q in hold_q}
