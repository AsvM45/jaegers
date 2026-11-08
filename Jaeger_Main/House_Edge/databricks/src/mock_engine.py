"""Offline Mock Engine for Databricks Lakehouse Pipeline (PySpark & MLflow)

Provides an offline, zero-dependency (pure Python stdlib + Pandas/NumPy)
emulation of the PySpark DataFrame API and MLflow tracking client.
Allows 100% test coverage and validation of Medallion pipelines, feature
transformations, SQL queries, and model governance without requiring Java,
JVM, or a live cloud Databricks workspace.
"""

from __future__ import annotations

import copy
import hashlib
import json
import math
import os
import re
import sqlite3
import time
import uuid
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple, Union

import numpy as np
import pandas as pd


# ---------------------------------------------------------------------------
# Data Types and Schema
# ---------------------------------------------------------------------------

class DataType:
    """Base class for mock data types."""
    def __init__(self, name: str):
        self.name = name

    def __call__(self) -> DataType:
        return self

    def __repr__(self) -> str:
        return self.name


StringType = DataType("StringType")
IntegerType = DataType("IntegerType")
LongType = DataType("LongType")
FloatType = DataType("FloatType")
DoubleType = DataType("DoubleType")
BooleanType = DataType("BooleanType")
TimestampType = DataType("TimestampType")


class StructField:
    """Mock StructField representing a single schema column."""
    def __init__(self, name: str, dataType: Union[DataType, str], nullable: bool = True):
        self.name = name
        self.dataType = dataType if isinstance(dataType, DataType) else DataType(str(dataType))
        self.nullable = nullable

    def __repr__(self) -> str:
        return f"StructField({self.name}, {self.dataType}, {self.nullable})"


class StructType:
    """Mock StructType representing DataFrame schema."""
    def __init__(self, fields: Optional[Sequence[StructField]] = None):
        self.fields = list(fields or [])
        self.names = [f.name for f in self.fields]

    def add(self, field_or_name: Union[StructField, str], data_type: Optional[Union[DataType, str]] = None, nullable: bool = True) -> StructType:
        if isinstance(field_or_name, StructField):
            self.fields.append(field_or_name)
        else:
            self.fields.append(StructField(field_or_name, data_type or StringType, nullable))
        self.names = [f.name for f in self.fields]
        return self

    def __iter__(self):
        return iter(self.fields)

    def __len__(self) -> int:
        return len(self.fields)

    def __getitem__(self, item: Union[int, str]) -> StructField:
        if isinstance(item, int):
            return self.fields[item]
        for f in self.fields:
            if f.name == item:
                return f
        raise KeyError(item)

    def __repr__(self) -> str:
        return f"StructType({self.fields})"


class Row:
    """Mock PySpark Row object allowing both attribute and dictionary access."""
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)

    def __getitem__(self, key: str) -> Any:
        return getattr(self, key)

    def asDict(self, recursive: bool = False) -> Dict[str, Any]:
        return dict(self.__dict__)

    def __repr__(self) -> str:
        items = ", ".join(f"{k}={v!r}" for k, v in self.__dict__.items())
        return f"Row({items})"

    def __eq__(self, other: Any) -> bool:
        if isinstance(other, Row):
            return self.__dict__ == other.__dict__
        return False


# ---------------------------------------------------------------------------
# Column Expressions
# ---------------------------------------------------------------------------

class MockColumn:
    """Mock PySpark Column supporting arithmetic, comparisons, logical ops, and functions."""

    def __init__(self, eval_fn: Callable[[pd.DataFrame], pd.Series], name: Optional[str] = None):
        self._eval_fn = eval_fn
        self._name = name
        self._alias: Optional[str] = None
        self._ascending = True

    def eval(self, df: pd.DataFrame) -> Union[pd.Series, np.ndarray, Any]:
        return self._eval_fn(df)

    def alias(self, alias_name: str) -> MockColumn:
        c = copy.copy(self)
        c._alias = alias_name
        return c

    def asc(self) -> MockColumn:
        c = copy.copy(self)
        c._ascending = True
        return c

    def desc(self) -> MockColumn:
        c = copy.copy(self)
        c._ascending = False
        return c

    def isin(self, values: Sequence[Any]) -> MockColumn:
        val_list = list(values)
        return MockColumn(lambda df: self.eval(df).isin(val_list))

    def isNull(self) -> MockColumn:
        return MockColumn(lambda df: self.eval(df).isna())

    def isNotNull(self) -> MockColumn:
        return MockColumn(lambda df: self.eval(df).notna())

    def cast(self, to_type: Union[str, DataType]) -> MockColumn:
        type_str = str(to_type).lower()
        def _cast(df: pd.DataFrame):
            s = self.eval(df)
            if "int" in type_str:
                return pd.to_numeric(s, errors="coerce").fillna(0).astype(int)
            elif "float" in type_str or "double" in type_str:
                return pd.to_numeric(s, errors="coerce").astype(float)
            elif "str" in type_str:
                return s.astype(str)
            elif "bool" in type_str:
                return s.astype(bool)
            return s
        return MockColumn(_cast)

    def substr(self, startPos: int, length: int) -> MockColumn:
        # 1-indexed PySpark substr
        return MockColumn(lambda df: self.eval(df).astype(str).str.slice(startPos - 1, startPos - 1 + length))

    # Binary arithmetic
    def __add__(self, other: Any) -> MockColumn:
        return MockColumn(lambda df: self.eval(df) + (other.eval(df) if isinstance(other, MockColumn) else other))

    def __radd__(self, other: Any) -> MockColumn:
        return MockColumn(lambda df: (other.eval(df) if isinstance(other, MockColumn) else other) + self.eval(df))

    def __sub__(self, other: Any) -> MockColumn:
        return MockColumn(lambda df: self.eval(df) - (other.eval(df) if isinstance(other, MockColumn) else other))

    def __rsub__(self, other: Any) -> MockColumn:
        return MockColumn(lambda df: (other.eval(df) if isinstance(other, MockColumn) else other) - self.eval(df))

    def __mul__(self, other: Any) -> MockColumn:
        return MockColumn(lambda df: self.eval(df) * (other.eval(df) if isinstance(other, MockColumn) else other))

    def __rmul__(self, other: Any) -> MockColumn:
        return MockColumn(lambda df: (other.eval(df) if isinstance(other, MockColumn) else other) * self.eval(df))

    def __truediv__(self, other: Any) -> MockColumn:
        return MockColumn(lambda df: self.eval(df) / (other.eval(df) if isinstance(other, MockColumn) else other))

    def __rtruediv__(self, other: Any) -> MockColumn:
        return MockColumn(lambda df: (other.eval(df) if isinstance(other, MockColumn) else other) / self.eval(df))

    # Comparison ops
    def __eq__(self, other: Any) -> MockColumn:  # type: ignore[override]
        return MockColumn(lambda df: self.eval(df) == (other.eval(df) if isinstance(other, MockColumn) else other))

    def __ne__(self, other: Any) -> MockColumn:  # type: ignore[override]
        return MockColumn(lambda df: self.eval(df) != (other.eval(df) if isinstance(other, MockColumn) else other))

    def __lt__(self, other: Any) -> MockColumn:
        return MockColumn(lambda df: self.eval(df) < (other.eval(df) if isinstance(other, MockColumn) else other))

    def __le__(self, other: Any) -> MockColumn:
        return MockColumn(lambda df: self.eval(df) <= (other.eval(df) if isinstance(other, MockColumn) else other))

    def __gt__(self, other: Any) -> MockColumn:
        return MockColumn(lambda df: self.eval(df) > (other.eval(df) if isinstance(other, MockColumn) else other))

    def __ge__(self, other: Any) -> MockColumn:
        return MockColumn(lambda df: self.eval(df) >= (other.eval(df) if isinstance(other, MockColumn) else other))

    # Logical ops
    def __and__(self, other: Any) -> MockColumn:
        return MockColumn(lambda df: (self.eval(df).astype(bool)) & (other.eval(df).astype(bool) if isinstance(other, MockColumn) else bool(other)))

    def __or__(self, other: Any) -> MockColumn:
        return MockColumn(lambda df: (self.eval(df).astype(bool)) | (other.eval(df).astype(bool) if isinstance(other, MockColumn) else bool(other)))

    def __invert__(self) -> MockColumn:
        return MockColumn(lambda df: ~self.eval(df).astype(bool))

    def __repr__(self) -> str:
        return f"Column('{self._alias or self._name or 'expr'}')"


class MockWhen(MockColumn):
    """Chained when-otherwise conditional builder matching PySpark functions.when."""

    def __init__(self, condition: MockColumn, value: Any):
        self._clauses: List[Tuple[MockColumn, Any]] = [(condition, value)]
        self._otherwise_val: Any = None
        super().__init__(self._evaluate)

    def when(self, condition: MockColumn, value: Any) -> MockWhen:
        self._clauses.append((condition, value))
        return self

    def otherwise(self, value: Any) -> MockColumn:
        self._otherwise_val = value
        return self

    def _evaluate(self, df: pd.DataFrame) -> pd.Series:
        if len(df) == 0:
            return pd.Series([], dtype=object)
        conditions = [cond.eval(df).astype(bool) for cond, _ in self._clauses]
        choices = []
        for _, val in self._clauses:
            if isinstance(val, MockColumn):
                choices.append(val.eval(df))
            else:
                choices.append(val)
        default = (self._otherwise_val.eval(df) if isinstance(self._otherwise_val, MockColumn)
                   else self._otherwise_val)
        res = np.select(conditions, choices, default=default)
        return pd.Series(res, index=df.index)


# Helper constructor functions
def col(name: str) -> MockColumn:
    return MockColumn(lambda df: df[name], name=name)

def lit(val: Any) -> MockColumn:
    return MockColumn(lambda df: pd.Series([val] * len(df), index=df.index), name=str(val))

def when(condition: MockColumn, value: Any) -> MockWhen:
    return MockWhen(condition, value)

def coalesce(*cols: Union[MockColumn, str]) -> MockColumn:
    def _coalesce(df: pd.DataFrame) -> pd.Series:
        result = None
        for c in cols:
            series = col(c).eval(df) if isinstance(c, str) else c.eval(df)
            if result is None:
                result = series
            else:
                result = result.combine_first(series)
        return result if result is not None else pd.Series(index=df.index, dtype=object)
    return MockColumn(_coalesce, name="coalesce")

def count(target: Union[MockColumn, str] = "*") -> MockColumn:
    if target == "*":
        return MockColumn(lambda df: pd.Series(len(df), index=df.index), name="count(*)")
    c = col(target) if isinstance(target, str) else target
    return MockColumn(lambda df: pd.Series(c.eval(df).count(), index=df.index), name=f"count({c._name or 'expr'})")

def sum(target: Union[MockColumn, str]) -> MockColumn:
    c = col(target) if isinstance(target, str) else target
    return MockColumn(lambda df: pd.Series(c.eval(df).sum(), index=df.index), name=f"sum({c._name or 'expr'})")

def avg(target: Union[MockColumn, str]) -> MockColumn:
    c = col(target) if isinstance(target, str) else target
    return MockColumn(lambda df: pd.Series(c.eval(df).mean(), index=df.index), name=f"avg({c._name or 'expr'})")

mean = avg

def min(target: Union[MockColumn, str]) -> MockColumn:
    c = col(target) if isinstance(target, str) else target
    return MockColumn(lambda df: pd.Series(c.eval(df).min(), index=df.index), name=f"min({c._name or 'expr'})")

def max(target: Union[MockColumn, str]) -> MockColumn:
    c = col(target) if isinstance(target, str) else target
    return MockColumn(lambda df: pd.Series(c.eval(df).max(), index=df.index), name=f"max({c._name or 'expr'})")

def abs(target: Union[MockColumn, str]) -> MockColumn:
    c = col(target) if isinstance(target, str) else target
    return MockColumn(lambda df: np.abs(c.eval(df)), name=f"abs({c._name or 'expr'})")

def log(target: Union[MockColumn, str]) -> MockColumn:
    c = col(target) if isinstance(target, str) else target
    return MockColumn(lambda df: np.log(np.maximum(c.eval(df).astype(float), 1e-12)), name=f"log({c._name or 'expr'})")

def round(target: Union[MockColumn, str], scale: int = 0) -> MockColumn:
    c = col(target) if isinstance(target, str) else target
    return MockColumn(lambda df: np.round(c.eval(df).astype(float), scale), name=f"round({c._name or 'expr'}, {scale})")

def concat(*cols: Union[MockColumn, str]) -> MockColumn:
    def _concat(df: pd.DataFrame) -> pd.Series:
        res = pd.Series("", index=df.index, dtype=str)
        for c in cols:
            s = col(c).eval(df) if isinstance(c, str) else c.eval(df)
            res = res + s.astype(str)
        return res
    return MockColumn(_concat, name="concat")

def sha2(target: Union[MockColumn, str], num_bits: int = 256) -> MockColumn:
    c = col(target) if isinstance(target, str) else target
    def _sha2(df: pd.DataFrame) -> pd.Series:
        s = c.eval(df).astype(str)
        return s.map(lambda val: hashlib.sha256(val.encode()).hexdigest())
    return MockColumn(_sha2, name=f"sha2({num_bits})")

def current_timestamp() -> MockColumn:
    return MockColumn(lambda df: pd.Series(pd.Timestamp.now().isoformat(), index=df.index), name="current_timestamp")


# ---------------------------------------------------------------------------
# Mock DataFrame & Grouped Data
# ---------------------------------------------------------------------------

class MockGroupedData:
    """Mock PySpark GroupedData supporting .agg(), .count(), .sum(), etc."""

    def __init__(self, df: MockDataFrame, group_cols: List[str]):
        self._df = df
        self._group_cols = group_cols

    def count(self) -> MockDataFrame:
        grouped = self._df._pdf.groupby(self._group_cols, as_index=False, dropna=False).size()
        grouped = grouped.rename(columns={"size": "count"})
        return MockDataFrame(grouped, self._df._session)

    def agg(self, *exprs: Union[MockColumn, Dict[str, str]]) -> MockDataFrame:
        pdf = self._df._pdf
        if not exprs:
            raise ValueError("agg requires at least one aggregate expression")

        # Case 1: Dictionary syntax, e.g. {"machine_id": "count", "cutoff": "min"}
        if len(exprs) == 1 and isinstance(exprs[0], dict):
            agg_dict = exprs[0]
            grouped = pdf.groupby(self._group_cols, as_index=False, dropna=False).agg(agg_dict)
            return MockDataFrame(grouped, self._df._session)

        # Case 2: MockColumn expressions with .alias()
        grouped_gb = pdf.groupby(self._group_cols, dropna=False)
        out_records = []
        for name, group in grouped_gb:
            if not isinstance(name, tuple):
                name = (name,)
            rec = {col_name: val for col_name, val in zip(self._group_cols, name)}
            for expr in exprs:
                if isinstance(expr, MockColumn):
                    series = expr.eval(group)
                    val = series.iloc[0] if len(series) > 0 else None
                    alias_name = expr._alias or expr._name or "agg"
                    rec[alias_name] = val
            out_records.append(rec)

        res_df = pd.DataFrame(out_records)
        return MockDataFrame(res_df, self._df._session)

    def applyInPandas(self, func: Callable[[pd.DataFrame], pd.DataFrame], schema: Optional[Any] = None) -> MockDataFrame:
        pdf = self._df._pdf
        if len(pdf) == 0:
            return MockDataFrame(pd.DataFrame(), self._df._session)
        results = []
        for _, group in pdf.groupby(self._group_cols, dropna=False, sort=False):
            res = func(group.copy())
            if res is not None and len(res) > 0:
                results.append(res)
        if results:
            out_pdf = pd.concat(results, ignore_index=True)
        else:
            out_pdf = pd.DataFrame()
        return MockDataFrame(out_pdf, self._df._session)



class MockDataFrameWriter:
    """Mock PySpark DataFrameWriter supporting Delta saveAsTable and format/mode."""

    def __init__(self, df: MockDataFrame, session: MockSparkSession):
        self._df = df
        self._session = session
        self._format = "delta"
        self._mode = "overwrite"

    def format(self, fmt: str) -> MockDataFrameWriter:
        self._format = fmt
        return self

    def mode(self, mode_str: str) -> MockDataFrameWriter:
        self._mode = mode_str.lower()
        return self

    def saveAsTable(self, table_name: str) -> None:
        self._session._register_table(table_name, self._df, mode=self._mode)

    def save(self, path: str) -> None:
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        if self._format == "csv":
            self._df._pdf.to_csv(path, index=False)
        elif self._format == "parquet":
            self._df._pdf.to_parquet(path, index=False)
        else:
            self._df._pdf.to_csv(path, index=False)


class MockDataFrame:
    """Mock PySpark DataFrame backed by Pandas and SQLite."""

    def __init__(self, pdf: Union[pd.DataFrame, Sequence[Dict[str, Any]]], session: Optional[MockSparkSession] = None):
        if isinstance(pdf, pd.DataFrame):
            self._pdf = pdf.copy()
        elif isinstance(pdf, Sequence):
            self._pdf = pd.DataFrame(list(pdf))
        else:
            self._pdf = pd.DataFrame()
        self._session = session or MockSparkSession.get_instance()

    @property
    def columns(self) -> List[str]:
        return list(self._pdf.columns)

    @property
    def dtypes(self) -> List[Tuple[str, str]]:
        type_map = {
            "int64": "bigint", "int32": "int", "float64": "double",
            "float32": "float", "object": "string", "bool": "boolean",
            "datetime64[ns]": "timestamp"
        }
        return [(str(c), type_map.get(str(t), "string")) for c, t in self._pdf.dtypes.items()]

    @property
    def schema(self) -> StructType:
        st = StructType()
        for col_name, type_str in self.dtypes:
            st.add(col_name, type_str)
        return st

    @property
    def write(self) -> MockDataFrameWriter:
        return MockDataFrameWriter(self, self._session)

    def toPandas(self) -> pd.DataFrame:
        return self._pdf.copy()

    def count(self) -> int:
        return len(self._pdf)

    def collect(self) -> List[Row]:
        return [Row(**row) for row in self._pdf.to_dict(orient="records")]

    def first(self) -> Optional[Row]:
        records = self.collect()
        return records[0] if records else None

    def head(self, n: int = 1) -> Union[Row, List[Row]]:
        records = self.collect()
        if n == 1:
            return records[0] if records else None  # type: ignore[return-value]
        return records[:n]

    def select(self, *cols: Union[str, MockColumn, Sequence[Union[str, MockColumn]]]) -> MockDataFrame:
        flat_cols: List[Union[str, MockColumn]] = []
        for c in cols:
            if isinstance(c, (list, tuple)):
                flat_cols.extend(c)
            else:
                flat_cols.append(c)

        new_pdf = pd.DataFrame(index=self._pdf.index)
        for c in flat_cols:
            if isinstance(c, str):
                new_pdf[c] = self._pdf[c]
            elif isinstance(c, MockColumn):
                col_name = c._alias or c._name or f"col_{len(new_pdf.columns)}"
                new_pdf[col_name] = c.eval(self._pdf)
            else:
                raise TypeError(f"Unsupported select item: {type(c)}")
        return MockDataFrame(new_pdf, self._session)

    def filter(self, condition: Union[MockColumn, str]) -> MockDataFrame:
        if isinstance(condition, MockColumn):
            mask = condition.eval(self._pdf).astype(bool)
            filtered = self._pdf[mask].copy()
            return MockDataFrame(filtered, self._session)
        elif isinstance(condition, str):
            filtered = self._pdf.query(condition).copy()
            return MockDataFrame(filtered, self._session)
        raise TypeError(f"Unsupported filter condition type: {type(condition)}")

    where = filter

    def withColumn(self, col_name: str, col_expr: Union[MockColumn, Any]) -> MockDataFrame:
        new_pdf = self._pdf.copy()
        if isinstance(col_expr, MockColumn):
            new_pdf[col_name] = col_expr.eval(new_pdf)
        elif callable(col_expr):
            new_pdf[col_name] = col_expr(new_pdf)
        else:
            new_pdf[col_name] = col_expr
        return MockDataFrame(new_pdf, self._session)

    def withColumnRenamed(self, existing: str, new_name: str) -> MockDataFrame:
        new_pdf = self._pdf.rename(columns={existing: new_name})
        return MockDataFrame(new_pdf, self._session)

    def drop(self, *cols: str) -> MockDataFrame:
        drop_set = set(cols)
        existing = [c for c in self._pdf.columns if c not in drop_set]
        return MockDataFrame(self._pdf[existing].copy(), self._session)

    def distinct(self) -> MockDataFrame:
        return MockDataFrame(self._pdf.drop_duplicates().copy(), self._session)

    def dropDuplicates(self, subset: Optional[Sequence[str]] = None) -> MockDataFrame:
        sub = list(subset) if subset else None
        return MockDataFrame(self._pdf.drop_duplicates(subset=sub).copy(), self._session)

    def join(self, other: MockDataFrame, on: Optional[Union[str, Sequence[str], MockColumn]] = None, how: str = "inner") -> MockDataFrame:
        left = self._pdf
        right = other._pdf

        how_map = {
            "inner": "inner", "left": "left", "left_outer": "left",
            "right": "right", "right_outer": "right", "outer": "outer",
            "full": "outer", "full_outer": "outer"
        }
        pd_how = how_map.get(how.lower(), "inner")

        if isinstance(on, str):
            res = left.merge(right, on=on, how=pd_how)
        elif isinstance(on, (list, tuple)):
            res = left.merge(right, on=list(on), how=pd_how)
        elif isinstance(on, MockColumn):
            # Evaluate on expression if it's equality or boolean mask
            res = left.merge(right, how=pd_how)
        elif on is None:
            # Cross join
            left_temp = left.assign(_cross_key=1)
            right_temp = right.assign(_cross_key=1)
            res = left_temp.merge(right_temp, on="_cross_key", how="outer").drop(columns=["_cross_key"])
        else:
            res = left.merge(right, on=on, how=pd_how)
        return MockDataFrame(res, self._session)

    def groupBy(self, *cols: Union[str, MockColumn]) -> MockGroupedData:
        col_names = [c if isinstance(c, str) else (c._name or "") for c in cols]
        return MockGroupedData(self, col_names)

    groupby = groupBy

    def orderBy(self, *cols: Union[str, MockColumn], ascending: Union[bool, Sequence[bool]] = True) -> MockDataFrame:
        sort_cols: List[str] = []
        asc_list: List[bool] = []
        for c in cols:
            if isinstance(c, str):
                sort_cols.append(c)
                asc_list.append(True if isinstance(ascending, bool) else True)
            elif isinstance(c, MockColumn):
                sort_cols.append(c._name or "col")
                asc_list.append(c._ascending)
        if isinstance(ascending, bool) and len(cols) == 1:
            asc_list = [ascending]
        sorted_pdf = self._pdf.sort_values(by=sort_cols, ascending=asc_list).copy()
        return MockDataFrame(sorted_pdf, self._session)

    sort = orderBy

    def limit(self, num: int) -> MockDataFrame:
        return MockDataFrame(self._pdf.head(num).copy(), self._session)

    def createOrReplaceTempView(self, name: str) -> None:
        self._session._register_table(name, self, mode="overwrite")

    def alias(self, alias_name: str) -> MockDataFrame:
        return self

    def union(self, other: MockDataFrame) -> MockDataFrame:
        concatenated = pd.concat([self._pdf, other._pdf], ignore_index=True)
        return MockDataFrame(concatenated, self._session)

    def unionByName(self, other: MockDataFrame, allowMissingColumns: bool = False) -> MockDataFrame:
        concatenated = pd.concat([self._pdf, other._pdf], ignore_index=True)
        return MockDataFrame(concatenated, self._session)


    def show(self, n: int = 20, truncate: bool = True) -> None:
        sample = self._pdf.head(n)
        print(sample.to_string(index=False, max_cols=20))

    def printSchema(self) -> None:
        print("root")
        for col_name, col_type in self.dtypes:
            print(f" |-- {col_name}: {col_type} (nullable = true)")


# ---------------------------------------------------------------------------
# Mock DataFrame Reader
# ---------------------------------------------------------------------------

class MockDataFrameReader:
    """Mock PySpark DataFrameReader supporting CSV, Table, and Parquet."""

    def __init__(self, session: MockSparkSession):
        self._session = session
        self._header = True
        self._inferSchema = True
        self._format = "csv"

    def option(self, key: str, value: Any) -> MockDataFrameReader:
        if key.lower() == "header":
            self._header = bool(value)
        elif key.lower() == "inferschema":
            self._inferSchema = bool(value)
        return self

    def options(self, **options: Any) -> MockDataFrameReader:
        for k, v in options.items():
            self.option(k, v)
        return self

    def format(self, fmt: str) -> MockDataFrameReader:
        self._format = fmt
        return self

    def csv(self, path: Union[str, Sequence[str]], header: bool = True, inferSchema: bool = True) -> MockDataFrame:
        if isinstance(path, (list, tuple)):
            dfs = [pd.read_csv(p, header=0 if header else None) for p in path]
            combined = pd.concat(dfs, ignore_index=True)
            return MockDataFrame(combined, self._session)
        if not os.path.exists(path):
            raise FileNotFoundError(f"File not found: {path}")
        pdf = pd.read_csv(path, header=0 if header else None)
        return MockDataFrame(pdf, self._session)

    def parquet(self, path: str) -> MockDataFrame:
        pdf = pd.read_parquet(path)
        return MockDataFrame(pdf, self._session)

    def table(self, table_name: str) -> MockDataFrame:
        return self._session.table(table_name)


# ---------------------------------------------------------------------------
# Mock Spark Session
# ---------------------------------------------------------------------------

class MockSparkSession:
    """Mock SparkSession managing catalog, temp views, and SQLite SQL engine."""

    _instance: Optional[MockSparkSession] = None

    def __init__(self, app_name: str = "MockSpark"):
        self.app_name = app_name
        self._tables: Dict[str, MockDataFrame] = {}
        self._sqlite_conn = sqlite3.connect(":memory:")
        self._init_sqlite_functions()
        self.read = MockDataFrameReader(self)
        MockSparkSession._instance = self

    @classmethod
    def get_instance(cls) -> MockSparkSession:
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def _init_sqlite_functions(self) -> None:
        """Register custom SQLite functions matching Spark SQL expressions."""
        self._sqlite_conn.create_function("log", 1, lambda x: np.log(max(float(x), 1e-12)) if x is not None else None)
        self._sqlite_conn.create_function("exp", 1, lambda x: float(np.exp(float(x))) if x is not None else None)
        self._sqlite_conn.create_function("pow", 2, lambda x, y: float(math.pow(float(x), float(y))) if x is not None and y is not None else None)
        self._sqlite_conn.create_function("sqrt", 1, lambda x: float(math.sqrt(float(x))) if x is not None else None)
        self._sqlite_conn.create_function("sha2", 2, lambda val, bits: hashlib.sha256(str(val).encode()).hexdigest() if val is not None else None)

    def _normalize_name(self, name: str) -> str:
        # Handles catalog.schema.table -> returns clean table name
        return name.split(".")[-1]

    def _register_table(self, table_name: str, df: MockDataFrame, mode: str = "overwrite") -> None:
        self._tables[table_name] = df
        clean_name = self._normalize_name(table_name)
        self._tables[clean_name] = df

        pdf = df.toPandas()
        if_exists = "append" if mode == "append" else "replace"
        pdf.to_sql(clean_name, self._sqlite_conn, if_exists=if_exists, index=False)
        qualified_name = table_name.replace(".", "_")
        if qualified_name != clean_name:
            pdf.to_sql(qualified_name, self._sqlite_conn, if_exists=if_exists, index=False)

    def table(self, table_name: str) -> MockDataFrame:
        clean_name = self._normalize_name(table_name)
        if table_name in self._tables:
            return self._tables[table_name]
        if clean_name in self._tables:
            return self._tables[clean_name]
        # Try reading from SQLite directly
        try:
            pdf = pd.read_sql_query(f"SELECT * FROM {clean_name}", self._sqlite_conn)
            df = MockDataFrame(pdf, self)
            self._tables[table_name] = df
            return df
        except Exception as e:
            raise KeyError(f"Table '{table_name}' does not exist in mock catalog. Existing: {list(self._tables.keys())}") from e

    def createDataFrame(self, data: Union[pd.DataFrame, Sequence[Any]], schema: Optional[Union[StructType, Sequence[str]]] = None) -> MockDataFrame:
        if isinstance(data, pd.DataFrame):
            pdf = data.copy()
            if schema and isinstance(schema, (list, tuple)):
                pdf.columns = list(schema)
            return MockDataFrame(pdf, self)
        elif isinstance(data, Sequence):
            if len(data) > 0 and isinstance(data[0], Row):
                pdf = pd.DataFrame([r.asDict() for r in data])
            elif len(data) > 0 and isinstance(data[0], dict):
                pdf = pd.DataFrame(data)
            elif schema and isinstance(schema, StructType):
                pdf = pd.DataFrame(data, columns=schema.names)
            elif schema and isinstance(schema, (list, tuple)):
                pdf = pd.DataFrame(data, columns=list(schema))
            else:
                pdf = pd.DataFrame(data)
            return MockDataFrame(pdf, self)
        raise TypeError(f"Cannot create DataFrame from type: {type(data)}")

    def sql(self, query: str) -> MockDataFrame:
        """Executes SQL query in SQLite, handling DDL, DML, and qualified catalog.schema.table names."""
        # Clean catalog.schema.table references to clean table names
        cleaned_query = re.sub(r'([a-zA-Z0-9_]+)\.([a-zA-Z0-9_]+)\.([a-zA-Z0-9_]+)', r'\3', query)
        cleaned_query = re.sub(r'([a-zA-Z0-9_]+)\.([a-zA-Z0-9_]+)', r'\2', cleaned_query)
        # SQLite syntax adjustments
        cleaned_query = re.sub(r'(?i)CREATE\s+(?:OR\s+REPLACE\s+)?TEMPORARY\s+VIEW', 'CREATE TEMP VIEW', cleaned_query)
        cleaned_query = re.sub(r'(?i)CREATE\s+(?:OR\s+REPLACE\s+)?TEMP\s+VIEW', 'CREATE TEMP VIEW', cleaned_query)
        
        stripped = cleaned_query.strip().upper()
        # Handle non-SELECT DDL/DML
        is_command = any(stripped.startswith(cmd) for cmd in (
            "CREATE", "DROP", "ALTER", "INSERT", "UPDATE", "DELETE", "USE", "REFRESH", "SET"
        ))
        try:
            if is_command:
                cursor = self._sqlite_conn.cursor()
                cursor.execute(cleaned_query)
                self._sqlite_conn.commit()
                return MockDataFrame(pd.DataFrame(), self)
            else:
                pdf = pd.read_sql_query(cleaned_query, self._sqlite_conn)
                return MockDataFrame(pdf, self)
        except Exception as e:
            raise RuntimeError(f"Error executing Mock SQL query:\nOriginal: {query}\nCleaned: {cleaned_query}\nError: {e}") from e

    def range(self, start: int, end: Optional[int] = None, step: int = 1) -> MockDataFrame:
        if end is None:
            end = start
            start = 0
        ids = list(range(start, end, step))
        return MockDataFrame(pd.DataFrame({"id": ids}), self)

    def stop(self) -> None:
        self._tables.clear()
        try:
            self._sqlite_conn.close()
        except Exception:
            pass
        MockSparkSession._instance = None


# ---------------------------------------------------------------------------
# Mock MLflow Tracking Client
# ---------------------------------------------------------------------------

class MockRunInfo:
    """Mock MLflow RunInfo."""
    def __init__(self, run_id: str, experiment_id: str, run_name: Optional[str] = None):
        self.run_id = run_id
        self.experiment_id = experiment_id
        self.run_name = run_name or f"run_{run_id[:8]}"
        self.status = "RUNNING"
        self.start_time = int(time.time() * 1000)
        self.end_time: Optional[int] = None


class MockRun:
    """Mock MLflow Run object returned by start_run()."""
    def __init__(self, run_id: str, experiment_id: str, run_name: Optional[str] = None, client: Optional[MockMLflow] = None):
        self.info = MockRunInfo(run_id, experiment_id, run_name)
        self.data: Dict[str, Any] = {
            "params": {},
            "metrics": {},
            "tags": {},
            "artifacts": []
        }
        self._client = client

    def __enter__(self) -> MockRun:
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        if self._client:
            self._client.end_run(status="FAILED" if exc_type else "FINISHED")


class MockMLflowModels:
    """Mock mlflow.models module for offline signature inference."""
    @staticmethod
    def infer_signature(model_input: Any, model_output: Any = None) -> Dict[str, Any]:
        return {
            "inputs": str(type(model_input)),
            "outputs": str(type(model_output)) if model_output is not None else None,
        }


class MockMLflow:
    """Offline Mock MLflow Tracking Client persisting runs to in-memory ledger and JSON."""

    def __init__(self, storage_file: str = "mlflow_mock_runs.json"):
        self._storage_file = storage_file
        self._active_run: Optional[MockRun] = None
        self._runs: Dict[str, MockRun] = {}
        self._current_experiment_id: str = "0"
        self._current_experiment_name: str = "/Shared/jaegers_house_edge_experiments"
        self._tracking_uri: str = "file:///tmp/mlruns"
        self.models = MockMLflowModels()

    def set_tracking_uri(self, uri: str) -> None:
        self._tracking_uri = uri

    def get_tracking_uri(self) -> str:
        return self._tracking_uri

    def set_experiment(self, experiment_name: str) -> str:
        import builtins
        self._current_experiment_name = experiment_name
        self._current_experiment_id = str(builtins.abs(hash(experiment_name)) % 10000)
        return self._current_experiment_id

    def start_run(self, run_id: Optional[str] = None, run_name: Optional[str] = None, experiment_id: Optional[str] = None, nested: bool = False) -> MockRun:
        rid = run_id or uuid.uuid4().hex
        exp_id = experiment_id or self._current_experiment_id
        run = MockRun(rid, exp_id, run_name, client=self)
        self._active_run = run
        self._runs[rid] = run
        return run

    def end_run(self, status: str = "FINISHED") -> None:
        if self._active_run:
            self._active_run.info.status = status
            self._active_run.info.end_time = int(time.time() * 1000)
            self._persist_ledger()
            self._active_run = None

    def active_run(self) -> Optional[MockRun]:
        return self._active_run

    def log_param(self, key: str, value: Any) -> None:
        if self._active_run:
            self._active_run.data["params"][key] = str(value)

    def log_params(self, params: Dict[str, Any]) -> None:
        if self._active_run:
            for k, v in params.items():
                self._active_run.data["params"][k] = str(v)

    def log_metric(self, key: str, value: float, step: Optional[int] = None) -> None:
        if self._active_run:
            self._active_run.data["metrics"][key] = float(value)

    def log_metrics(self, metrics: Dict[str, float], step: Optional[int] = None) -> None:
        if self._active_run:
            for k, v in metrics.items():
                self._active_run.data["metrics"][k] = float(v)

    def set_tag(self, key: str, value: Any) -> None:
        if self._active_run:
            self._active_run.data["tags"][key] = str(value)

    def set_tags(self, tags: Dict[str, Any]) -> None:
        if self._active_run:
            for k, v in tags.items():
                self._active_run.data["tags"][k] = str(v)

    def log_artifact(self, local_path: str, artifact_path: Optional[str] = None) -> None:
        if self._active_run:
            dest = (f"{artifact_path.rstrip('/')}/{os.path.basename(local_path)}"
                    if artifact_path else os.path.basename(local_path))
            self._active_run.data["artifacts"].append({
                "local_path": local_path,
                "artifact_path": dest
            })

    def log_dict(self, dictionary: Dict[str, Any], artifact_file: str) -> None:
        if self._active_run:
            self._active_run.data["artifacts"].append({
                "content_dict": dictionary,
                "artifact_path": artifact_file
            })

    def log_text(self, text: str, artifact_file: str) -> None:
        if self._active_run:
            self._active_run.data["artifacts"].append({
                "content_text": text,
                "artifact_path": artifact_file
            })

    def log_figure(self, figure: Any, artifact_file: str) -> None:
        if self._active_run:
            self._active_run.data["artifacts"].append({
                "figure": figure,
                "artifact_path": artifact_file
            })
            try:
                import tempfile
                tmp_dir = tempfile.mkdtemp()
                tmp_path = os.path.join(tmp_dir, os.path.basename(artifact_file))
                figure.savefig(tmp_path)
                self.log_artifact(tmp_path, artifact_file)
            except Exception:
                pass

    def search_runs(self, experiment_ids: Optional[Sequence[str]] = None, filter_string: Optional[str] = None, run_view_type: int = 1, max_results: int = 1000, order_by: Optional[Sequence[str]] = None) -> pd.DataFrame:
        records = []
        for rid, run in self._runs.items():
            rec: Dict[str, Any] = {
                "run_id": rid,
                "experiment_id": run.info.experiment_id,
                "status": run.info.status,
                "start_time": run.info.start_time,
                "end_time": run.info.end_time,
                "tags.mlflow.runName": run.info.run_name
            }
            for pk, pv in run.data["params"].items():
                rec[f"params.{pk}"] = pv
            for mk, mv in run.data["metrics"].items():
                rec[f"metrics.{mk}"] = mv
            for tk, tv in run.data["tags"].items():
                rec[f"tags.{tk}"] = tv
            records.append(rec)
        return pd.DataFrame(records)

    def _persist_ledger(self) -> None:
        """Serializes completed runs to JSON ledger for provenance auditing."""
        try:
            records = {}
            for rid, run in self._runs.items():
                records[rid] = {
                    "run_id": rid,
                    "experiment_id": run.info.experiment_id,
                    "run_name": run.info.run_name,
                    "status": run.info.status,
                    "start_time": run.info.start_time,
                    "end_time": run.info.end_time,
                    "params": run.data["params"],
                    "metrics": run.data["metrics"],
                    "tags": run.data["tags"],
                    "artifact_count": len(run.data["artifacts"])
                }
            with open(self._storage_file, "w", encoding="utf-8") as f:
                json.dump(records, f, indent=2)
        except Exception:
            pass  # Non-fatal if filesystem is read-only
