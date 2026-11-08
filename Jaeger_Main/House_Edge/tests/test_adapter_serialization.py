import numpy as np
from research.learners import HistoricalModel
from research.adapters import Serializable
from test_temporal import fixture


def test_supervised_schema_order_and_serialization(tmp_path):
    queries,history=fixture()
    labels={q["query_id"]:i%5 for i,q in enumerate(queries)}
    model=HistoricalModel("hist_boost",["windows","type"],{"iters":2},supervision="query")
    model.fit(queries,history,labels)
    before=model.predict_proba(queries,history)
    model.save(tmp_path/"model.joblib")
    after=Serializable.load(tmp_path/"model.joblib").predict_proba(queries,history)
    for key in before:
        np.testing.assert_array_equal(before[key],after[key])
