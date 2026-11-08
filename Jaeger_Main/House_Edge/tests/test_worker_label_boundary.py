"""The runner must never hand held-out query labels to any specialist model."""
from collections import defaultdict
from research import worker


def test_fit_receives_only_fit_episode_history_and_labels(tmp_path,monkeypatch):
    queries=[]; history=defaultdict(dict); labels={}; conditions={}; folds={}
    for episode in range(8):
        ep=f"ep{episode}"
        folds[ep]=episode%2
        for machine in range(2):
            q=dict(query_id=f"q{episode}_{machine}",episode_id=ep,machine_id=f"m{machine}",
                   machine_type="steady",signal="0",cutoff="32")
            queries.append(q); history[(ep,q["machine_id"])][0]=1
            labels[q["query_id"]]=episode%5
            conditions[q["query_id"]]=("stable","short_history","drift","shared_change")[episode//2]
    class Core:
        def read_split(self,path):
            return queries,history
    seen=[]
    class Model:
        def fit(self,q,h,y):
            assert set(y) == {row["query_id"] for row in q}
            assert {key[0] for key in h} == {row["episode_id"] for row in q}
            seen.append(set(y))
            return self
        def predict_proba(self,q,h):
            return {row["query_id"]:[.2]*5 for row in q}
    monkeypatch.setattr(worker,"core_module",lambda:Core())
    monkeypatch.setattr(worker,"read_labels",lambda path:labels)
    monkeypatch.setattr(worker,"conditions",lambda path:conditions)
    monkeypatch.setattr(worker,"model_for",lambda config,cache:Model())
    result=worker.evaluate({"config":{"family":"frequency"},"data":str(tmp_path),"folds":folds},tmp_path)
    assert len(seen) == 2 and seen[0].isdisjoint(seen[1])
    assert len(result["per_query"]) == len(queries)
