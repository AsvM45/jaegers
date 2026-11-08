"""Unified Runtime Session Resolver for Databricks Lakehouse Pipeline

Detects the active execution environment and resolves SparkSession and MLflow clients:
- In native Databricks clusters / Serverless environments with PySpark & MLflow installed,
  uses real PySpark (including Spark Connect on Serverless) and real MLflow.
- Explicitly rejects silent fallback to MockSparkSession / MockMLflow when running on
  Databricks runtime or when `require_live=True`.
- In offline environments (e.g., standard Python 3.13 without Java/PySpark, CI testing)
  when `require_live=False`, falls back to `mock_engine.MockSparkSession` and `MockMLflow`.
"""

from __future__ import annotations

import builtins
import inspect
import logging
import os
import sys
from typing import Any, Dict, Optional

logger = logging.getLogger("jaegers.databricks.session")


def resolve_src_dir(caller_globals: Optional[Dict[str, Any]] = None) -> str:
    """Resolves the `databricks/src` directory even when `__file__` is absent (e.g. Serverless exec)."""
    if caller_globals:
        for key in ("__file__", "filename"):
            cand = caller_globals.get(key)
            if isinstance(cand, str) and cand and not cand.startswith("<"):
                return os.path.dirname(os.path.abspath(cand))

    frame = inspect.currentframe()
    try:
        cur = frame.f_back if frame is not None else None
        while cur is not None:
            co_file = cur.f_code.co_filename
            if isinstance(co_file, str) and co_file and not co_file.startswith("<"):
                cand_dir = os.path.dirname(os.path.abspath(co_file))
                if os.path.isfile(os.path.join(cand_dir, "session.py")):
                    return cand_dir
            cur = cur.f_back
    finally:
        del frame

    if sys.argv and sys.argv[0] and not sys.argv[0].startswith("-"):
        cand_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
        if os.path.isdir(cand_dir):
            return cand_dir

    cwd = os.getcwd()
    for rel in ("", "src", os.path.join("Jaeger_Main", "House_Edge", "databricks", "src")):
        cand = os.path.abspath(os.path.join(cwd, rel))
        if os.path.isfile(os.path.join(cand, "session.py")):
            return cand
    return cwd


def is_databricks_runtime() -> bool:
    """Returns True when executing inside a real Databricks runtime container."""
    return bool(
        os.environ.get("DATABRICKS_RUNTIME_VERSION")
        or os.environ.get("DB_IS_DRIVER")
        or os.environ.get("SPARK_CONNECT_MODE_ENABLED")
    )


def is_mock_forced() -> bool:
    """Returns True if the mock engine has been explicitly forced via environment variable."""
    return os.environ.get("DATABRICKS_RUNTIME_FORCE_MOCK", "0").lower() in ("1", "true", "yes")


def is_live_required(require_live: bool = False) -> bool:
    """Returns True if live Spark/MLflow execution is required and mocks must be rejected."""
    if require_live:
        return True
    if os.environ.get("DATABRICKS_REQUIRE_LIVE", "0").lower() in ("1", "true", "yes"):
        return True
    if is_databricks_runtime() and not is_mock_forced():
        return True
    return False


def is_mock_spark(spark: Any) -> bool:
    """Returns True if `spark` is an offline MockSparkSession instance."""
    return type(spark).__name__ == "MockSparkSession"


def is_mock_mlflow(mlflow_client: Any) -> bool:
    """Returns True if `mlflow_client` is an offline MockMLflow instance."""
    return type(mlflow_client).__name__ == "MockMLflow"


def assert_real_spark(spark: Any) -> None:
    """Raises RuntimeError if `spark` is a MockSparkSession."""
    if spark is None or is_mock_spark(spark):
        raise RuntimeError(
            f"Live PySpark session required, but resolved {type(spark).__name__}. "
            "Mock fallback is forbidden in live verification."
        )


def assert_real_mlflow(mlflow_client: Any) -> None:
    """Raises RuntimeError if `mlflow_client` is a MockMLflow."""
    if mlflow_client is None or is_mock_mlflow(mlflow_client):
        raise RuntimeError(
            f"Live MLflow client required, but resolved {type(mlflow_client).__name__}. "
            "Mock fallback is forbidden in live verification."
        )


def _acquire_native_spark_session(app_name: str = "jaegers_house_edge") -> Any:
    """Acquires an active Databricks Serverless / Spark Connect or local PySpark session.

    Avoids setting static JVM extensions (`spark.sql.extensions`) on existing Serverless
    Spark Connect sessions where static session configs are read-only.
    """
    # 1. Check builtins / __main__ for pre-injected Databricks `spark` session
    for holder in (builtins, sys.modules.get("__main__")):
        if holder is not None and hasattr(holder, "spark"):
            existing = getattr(holder, "spark")
            if existing is not None and hasattr(existing, "createDataFrame") and not is_mock_spark(existing):
                return existing

    # 2. Check IPython user namespace if running inside Databricks ipykernel wrapper
    try:
        import IPython  # type: ignore
        ip = IPython.get_ipython()
        if ip is not None and hasattr(ip, "user_ns"):
            existing = ip.user_ns.get("spark")
            if existing is not None and hasattr(existing, "createDataFrame") and not is_mock_spark(existing):
                return existing
    except Exception:
        pass

    # 3. Check SparkSession.getActiveSession() or SparkSession.builder.getOrCreate()
    from pyspark.sql import SparkSession  # type: ignore

    active = SparkSession.getActiveSession()
    if active is not None:
        return active

    # On Databricks Serverless / Spark Connect, plain getOrCreate() connects cleanly
    try:
        return SparkSession.builder.getOrCreate()
    except Exception:
        return SparkSession.builder.appName(app_name).getOrCreate()


def get_spark_session(
    app_name: str = "jaegers_house_edge",
    catalog: Optional[str] = None,
    schema: Optional[str] = None,
    force_mock: bool = False,
    require_live: bool = False,
) -> Any:
    """Resolves and returns an active SparkSession.

    In live mode (`require_live=True` or on Databricks runtime), never falls back to MockSparkSession.
    Falls back to `MockSparkSession` only in offline environments when `require_live=False`.
    """
    if require_live and (force_mock or is_mock_forced()):
        raise RuntimeError("Live verification explicitly rejects force_mock / MockSession.")

    live_needed = is_live_required(require_live) and not force_mock

    if (force_mock or is_mock_forced()) and not live_needed:
        try:
            from .mock_engine import MockSparkSession
        except (ImportError, ValueError):
            from mock_engine import MockSparkSession
        logger.info("Using offline MockSparkSession (forced)")
        return MockSparkSession.get_instance()

    try:
        session = _acquire_native_spark_session(app_name=app_name)
        if catalog:
            try:
                session.sql(f"USE CATALOG `{catalog}`")
            except Exception as exc:
                logger.debug("Could not execute USE CATALOG %s: %s", catalog, exc)
        if schema:
            try:
                session.sql(f"USE SCHEMA `{schema}`")
            except Exception:
                try:
                    session.sql(f"USE `{schema}`")
                except Exception as exc:
                    logger.debug("Could not execute USE SCHEMA %s: %s", schema, exc)
        if live_needed:
            assert_real_spark(session)
        return session
    except Exception as exc:
        if live_needed:
            raise RuntimeError(
                f"Failed to initialize live PySpark session (mock fallback rejected): {exc}"
            ) from exc
        logger.warning("Native PySpark session initialization failed (%s); falling back to MockSparkSession", exc)
        try:
            from .mock_engine import MockSparkSession
        except (ImportError, ValueError):
            from mock_engine import MockSparkSession
        return MockSparkSession.get_instance()


def get_mlflow(force_mock: bool = False, require_live: bool = False) -> Any:
    """Resolves and returns the MLflow tracking client.

    In live mode (`require_live=True` or on Databricks runtime), never falls back to MockMLflow.
    Falls back to `MockMLflow` only in offline environments when `require_live=False`.
    """
    if require_live and (force_mock or is_mock_forced()):
        raise RuntimeError("Live verification explicitly rejects force_mock / MockSession.")

    live_needed = is_live_required(require_live) and not force_mock

    if (force_mock or is_mock_forced()) and not live_needed:
        try:
            from .mock_engine import MockMLflow
        except (ImportError, ValueError):
            from mock_engine import MockMLflow
        logger.info("Using offline MockMLflow (forced)")
        return MockMLflow()

    try:
        import mlflow  # type: ignore
        if is_databricks_runtime():
            os.environ.setdefault("MLFLOW_TRACKING_URI", "databricks")
            os.environ.setdefault("MLFLOW_REGISTRY_URI", "databricks-uc")
            try:
                mlflow.set_tracking_uri("databricks")
            except Exception:
                pass
            try:
                mlflow.set_registry_uri("databricks-uc")
            except Exception:
                pass
        if live_needed:
            assert_real_mlflow(mlflow)
        return mlflow
    except Exception as exc:
        if live_needed:
            raise RuntimeError(
                f"Failed to import live MLflow client (mock fallback rejected): {exc}"
            ) from exc
        logger.warning("Native MLflow import failed (%s); falling back to MockMLflow", exc)
        try:
            from .mock_engine import MockMLflow
        except (ImportError, ValueError):
            from mock_engine import MockMLflow
        return MockMLflow()
