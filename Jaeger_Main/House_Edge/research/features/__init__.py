"""Public feature compatibility exports and namespace for specialist features."""
from ..feature_api import (
    HISTORICAL_GROUPS,
    REGISTRY,
    FeatureComputer,
    Group,
    feature_columns,
    validate_groups,
)

__all__ = [
    "HISTORICAL_GROUPS", "REGISTRY", "FeatureComputer", "Group",
    "feature_columns", "validate_groups",
]
