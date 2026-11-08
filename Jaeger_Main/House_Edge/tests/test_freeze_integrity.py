"""CHAT-owned freeze integrity tests for issue #1; independent QA adds separate files."""
import pytest
import json
from research.freeze import freeze, verify_frozen
from research.common import file_hash
from research.release import verify, record_failure


def test_freeze_rejects_overwrite_and_changed_source(tmp_path):
    source=tmp_path/"source"
    data=tmp_path/"data"
    source.mkdir(); data.mkdir()
    (source/"predict.py").write_text("# frozen model\n")
    (data/"metadata.json").write_text("{}")
    out=tmp_path/"frozen"
    freeze(out,data,source)
    verify_frozen(out,data)
    with pytest.raises(FileExistsError):
        freeze(out,data,source)
    (out/"entry/predict.py").write_text("# altered\n")
    with pytest.raises(ValueError,match="Frozen champion bytes changed"):
        verify_frozen(out,data)


def test_frozen_data_change_detected(tmp_path):
    source=tmp_path/"source"; data=tmp_path/"data"
    source.mkdir(); data.mkdir()
    (source/"predict.py").write_text("# model\n")
    (data/"metadata.json").write_text("{}")
    freeze(tmp_path/"frozen",data,source)
    (data/"metadata.json").write_text('{"changed":true}')
    with pytest.raises(ValueError,match="data bytes differ"):
        verify_frozen(tmp_path/"frozen",data)


def test_release_failure_invalidates_success_and_cannot_be_hidden(tmp_path):
    release = tmp_path / "release"
    release.mkdir()
    csv = release / "submission.csv"
    csv.write_text("query_id,p_0,p_1,p_2,p_5,p_20\nq1,0.2,0.2,0.2,0.2,0.2\n")
    (release / "code.zip").write_bytes(b"frozen-test-artifact")
    (release / "release.json").write_text(json.dumps({
        "csv_sha256": file_hash(csv), "zip_sha256": file_hash(release / "code.zip")}))
    evidence = release / "environment.json"
    evidence.write_text(json.dumps(dict.fromkeys((
        "network_disabled", "submission_read_only", "data_read_only", "python_313",
        "cpu_limit_enforced", "memory_limit_enforced", "time_limit_enforced"), True)
        | {"status": "SUCCEEDED"}))
    assert verify(release, csv, evidence)["offline_verified"]
    attempt = release / "offline/attempt-0001"
    attempt.mkdir(parents=True)
    record_failure(release, attempt, "Prediction mismatch: 0.09")
    assert not json.loads((release / "verification.json").read_text())["offline_verified"]
    with pytest.raises(ValueError, match="recorded verification failure"):
        verify(release, csv, evidence)
