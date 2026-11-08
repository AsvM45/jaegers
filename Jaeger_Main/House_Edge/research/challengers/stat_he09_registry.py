"""HE-09 -> #8 registry bridge: exposes the HE-09 challengers through the shared factory contract.

Trial config (see research/CONTRACTS.md):
    {"family": "stat_dirichlet", "factory": "research.challengers.stat_he09_registry:factory",
     "model": "stat_dirichlet", "supervision": "query"}

The worker passes fold-local queries/history and labels as class indices 0-4, which is exactly what
the HE-09 models expect, so this adapter only renames predict -> predict_proba and validates output.
`supervision: "query"` tells the sweep not to build the historical feature cache, because these models
read raw histories plus fit-split query labels. The models themselves are unchanged
(research/challengers/stat_he09_models.py).
"""
from __future__ import annotations

from research.adapters import Serializable, validate_predictions
from research.challengers import stat_he09_models as SM


class HE09RegistryModel(Serializable):
    def __init__(self, name):
        if name not in SM.MODELS:
            raise ValueError(f"Unknown HE-09 model {name!r}; expected one of {sorted(SM.MODELS)}")
        self.name = name
        self.model = SM.MODELS[name]()

    def fit(self, queries, history, labels):
        self.model.fit(queries, history, labels)
        return self

    def predict_proba(self, queries, history):
        return validate_predictions(dict(self.model.predict(queries, history)), queries)


def factory(config, cache_path=None):
    """Registry factory: `(config, cache_path) -> model`. cache_path is unused (query supervision)."""
    return HE09RegistryModel(config.get("model", config.get("family")))
