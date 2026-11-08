import json
import pytest
from research.common import ROOT, file_hash
from research.sweep import identity, snapshot_source


def test_worker_source_is_copied_and_stale_source_rejected(tmp_path):
    provenance=identity(ROOT/"public",{"fixture":0})
    source=snapshot_source(tmp_path/"source",provenance)
    assert file_hash(source/"research/worker.py") == provenance["source_sha256"]["worker.py"]
    assert file_hash(source/"jaegers_entry/jaeger_model.py") == provenance["champion_sha256"]["jaeger_model.py"]
    stale=json.loads(json.dumps(provenance))
    stale["source_sha256"]["worker.py"]="not-the-current-bytes"
    with pytest.raises(ValueError,match="Source changed while staging"):
        snapshot_source(tmp_path/"stale",stale)


def test_completed_trial_identity_ignores_docs_only_head_change(tmp_path):
    from research.registry import Registry
    registry=Registry(tmp_path/"registry")
    a=registry.register("a",{"family":"frequency"},{"head":"a","source":"same"})
    b=registry.register("b",{"family":"frequency"},{"head":"b","source":"same"})
    assert a == b


def test_failed_trial_retries_only_explicitly(tmp_path):
    from research.registry import Registry
    registry=Registry(tmp_path/"registry")
    trial=registry.register("a",{"family":"frequency"},{"source":"same"})
    first=registry.start(trial)
    (first/"evidence.txt").write_text("failed original")
    registry.finish(trial,"FAILED",error="test failure")
    assert registry.start(trial) is None
    second=registry.start(trial,retry_failed=True)
    assert first != second
    assert (first/"evidence.txt").read_text() == "failed original"


def test_entry_readme_change_does_not_duplicate_numerical_trial(tmp_path):
    from research.registry import Registry
    registry=Registry(tmp_path/"registry")
    a={"champion_sha256":{"jaeger_model.py":"model","params.json":"params","README.md":"old"}}
    b={"champion_sha256":{"jaeger_model.py":"model","params.json":"params","README.md":"new"}}
    assert registry.register("a",{"family":"frequency"},a) == registry.register("b",{"family":"frequency"},b)
    b["champion_sha256"]["jaeger_model.py"]="different model"
    assert registry.register("b",{"family":"frequency"},b) != registry.register("a",{"family":"frequency"},a)
