"""Prevent cache reuse/comparisons across the numerical policies that changed forecasts."""
import json
from pathlib import Path
import pytest
from research.common import environment
from research.registry import Registry
from research.report import evaluation_key
from research.sweep import identity, candidates
from research.feature_api import validate_groups


def round_data(tmp_path):
    data = tmp_path / "data"
    (data / "train").mkdir(parents=True)
    (data / "metadata.json").write_text(json.dumps({"round": "main", "season_id": "fixture"}))
    (data / "train/history.csv").write_text("episode_id,machine_id,tick,payout\ne,m,1,0\n")
    return data


@pytest.mark.parametrize("name,value", [
    ("NPY_DISABLE_CPU_FEATURES", "X86_V3,X86_V4"),
    ("OPENBLAS_CORETYPE", "Nehalem"),
    ("PYTHONHASHSEED", "0"),
])
def test_numeric_policy_changes_trial_and_comparison_context(tmp_path, monkeypatch, name, value):
    data = round_data(tmp_path)
    monkeypatch.delenv(name, raising=False)
    first = identity(data, {"e": 0})
    registry = Registry(tmp_path / "registry")
    config = {"family": "frequency"}
    before = registry.register("first", config, first)
    assert registry.register("repeat", config, first) == before
    monkeypatch.setenv(name, value)
    second = identity(data, {"e": 0})
    assert second["environment"]["numeric_environment"][name] == value
    assert registry.register("changed", config, second) != before
    assert evaluation_key({"identity": json.dumps(first)}) != evaluation_key({"identity": json.dumps(second)})


def test_worker_thread_policy_is_numeric_identity(tmp_path):
    data = round_data(tmp_path)
    one, two = (identity(data, {"e": 0}, worker_cpus=n) for n in (1, 2))
    assert one["execution_policy"]["thread_limits"]["OMP_NUM_THREADS"] == "1"
    assert two["execution_policy"]["thread_limits"]["OPENBLAS_NUM_THREADS"] == "2"
    registry = Registry(tmp_path / "registry")
    assert registry.register("one", {}, one) != registry.register("two", {}, two)
    assert evaluation_key({"identity": json.dumps(one)}) != evaluation_key({"identity": json.dumps(two)})


def test_only_allowlisted_numeric_environment_is_recorded(monkeypatch):
    monkeypatch.setenv("UNRELATED_PRIVATE_VALUE", "must-not-be-collected")
    record = environment()
    assert "UNRELATED_PRIVATE_VALUE" not in json.dumps(record)


def test_feature_cache_separates_numeric_runtime_policy(tmp_path, monkeypatch):
    from test_agent_qa_features import _tiny_round
    from research.dataset import build_cache
    data = _tiny_round(tmp_path / "round")
    monkeypatch.delenv("NPY_DISABLE_CPU_FEATURES", raising=False)
    first = build_cache(data, tmp_path / "cache", stride=16, max_rows=4)
    assert build_cache(data, tmp_path / "cache", stride=16, max_rows=4) == first
    monkeypatch.setenv("NPY_DISABLE_CPU_FEATURES", "X86_V3")
    second = build_cache(data, tmp_path / "cache", stride=16, max_rows=4)
    assert second != first
    assert (first / "complete.json").exists() and (second / "complete.json").exists()


def test_preregistered_screen_is_diverse_causal_and_bounded():
    path = Path(__file__).resolve().parents[1] / "studies/chat_diverse_screen.json"
    spec = json.loads(path.read_text())
    rows = candidates(spec)
    assert len(rows) == 35
    assert len({row["family"] for row in rows}) == 13
    assert spec["budget"] == {"workers": 2, "trials": 35, "seconds": 1800, "trial_seconds": 120}
    for row in rows:
        if "groups" in row:
            validate_groups(row["groups"], historical=True)
            assert "current_signal" not in row["groups"]
