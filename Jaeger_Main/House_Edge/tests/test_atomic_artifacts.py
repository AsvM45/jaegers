import json
from research import common


def test_atomic_json_retries_transient_windows_lock(tmp_path,monkeypatch):
    replace=common.os.replace
    calls=[]
    def transient(source,target):
        calls.append(1)
        if len(calls) < 3:
            raise PermissionError("simulated reader lock")
        return replace(source,target)
    monkeypatch.setattr(common.os,"replace",transient)
    monkeypatch.setattr(common.time,"sleep",lambda _:None)
    path=tmp_path/"artifact.json"
    common.write_json(path,{"complete":True})
    assert len(calls) == 3
    assert json.loads(path.read_text()) == {"complete":True}
