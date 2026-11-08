"""CHAT-owned freeze integrity tests for issue #1; independent QA adds separate files."""
import pytest
from research.freeze import freeze, verify_frozen


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
