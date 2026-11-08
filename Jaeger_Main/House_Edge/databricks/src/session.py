"""Unified Runtime Session Resolver for Databricks Lakehouse Pipeline

Detects the active execution environment and resolves SparkSession and MLflow clients:
- In native Databricks clusters / environments with PySpark & MLflow installed, uses
  real PySpark and MLflow.
- In offline environments (e.g., standard Python 3.13 without Java or MLflow, CI testing),
  seamlessly falls back to the self-contained `mock_engine.MockSparkSession` and
  `mock_engine.MockMLflow`.
"""

from __future__ import annotations

import logging
import os
from typing import Any, Optional

logger = logging.getLogger("jaegers.databricks.session")


def is_mock_forced() -> bool:
    """Returns True if the mock engine has been explicitly forced via environment variable."""
    return os.environ.get("DATABRICKS_RUNTIME_FORCE_MOCK", "0").lower() in ("1", "true", "yes")


def get_spark_session(app_name: str = "jaegers_house_edge", catalog: Optional[str] = None, schema: Optional[str] = None, force_mock: bool = False) -> Any:
    """Resolves and returns an active SparkSession.

    Falls back to `MockSparkSession` if PySpark is not available or if forced.
    """
    if force_mock or is_mock_forced():
        try:
            from .mock_engine import MockSparkSession
        except (ImportError, ValueError):
            from mock_engine import MockSparkSession
        logger.info("Using offline MockSparkSession (forced)")
        session = MockSparkSession.get_instance()
        return session

    try:
        from pyspark.sql import SparkSession
        builder = SparkSession.builder.appName(app_name)
        # Enable Delta Lake extensions if running on native Spark
        builder = (builder
                   .config("spark.sql.extensions", "io.delta.sql.DeltaSparkSessionExtension")
                   .config("spark.sql.catalog.spark_catalog", "org.apache.spark.sql.delta.catalog.DeltaCatalog"))
        session = builder.getOrCreate()
        if catalog:
            try:
                session.sql(f"USE CATALOG {catalog}")
            except Exception:
                pass
        if schema:
            try:
                session.sql(f"USE {schema}")
            except Exception:
                pass
        return session
    except (ImportError, Exception) as exc:
        logger.warning("Native PySpark session initialization failed (%s); falling back to MockSparkSession", exc)
        try:
            from .mock_engine import MockSparkSession
        except (ImportError, ValueError):
            from mock_engine import MockSparkSession
        return MockSparkSession.get_instance()


def get_mlflow(force_mock: bool = False) -> Any:
    """Resolves and returns the MLflow tracking client.

    Falls back to `MockMLflow` if MLflow is not available or if forced.
    """
    if force_mock or is_mock_forced():
        try:
            from .mock_engine import MockMLflow
        except (ImportError, ValueError):
            from mock_engine import MockMLflow
        logger.info("Using offline MockMLflow (forced)")
        return MockMLflow()

    try:
        import mlflow
        return mlflow
    except (ImportError, Exception) as exc:
        logger.warning("Native MLflow import failed (%s); falling back to MockMLflow", exc)
        try:
            from .mock_engine import MockMLflow
        except (ImportError, ValueError):
            from mock_engine import MockMLflow
        return MockMLflow()
