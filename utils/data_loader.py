"""Data-driven testing: CSV and SQLite sources behind one interface (Strategy pattern).

    load_cases("login_invalid")                                    # tests/data/csv/login_invalid.csv
    load_cases("dashboards_view", source="sqlite",
               json_columns=("panels",))                           # table/view in tests/data/test_data.db

Every row must have an `id` (used as the pytest test id). CSV values are strings; SQLite keeps its types.
"""
from __future__ import annotations

import csv
import json
import re
import sqlite3
from contextlib import closing
from pathlib import Path
from typing import Any, Iterable, Protocol

import pytest

from utils.db_seed import ensure_db
from utils.settings import get_settings

_IDENTIFIER = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


class DataSource(Protocol):
    def rows(self) -> list[dict[str, Any]]: ...


class CsvSource:
    def __init__(self, path: Path):
        self.path = Path(path)

    def rows(self) -> list[dict[str, Any]]:
        if not self.path.exists():
            raise FileNotFoundError(f"CSV data file not found: {self.path}")
        with open(self.path, newline="", encoding="utf-8-sig") as fh:
            return [dict(row) for row in csv.DictReader(fh)]


class SqliteSource:
    def __init__(self, db_path: Path, table: str, json_columns: Iterable[str] = ()):
        self.db_path = Path(db_path)
        self.table = table
        self.json_columns = tuple(json_columns)

    def rows(self) -> list[dict[str, Any]]:
        if not _IDENTIFIER.match(self.table):  # table names can't be bound as parameters, so validate
            raise ValueError(f"Illegal table/view name: {self.table!r}")
        ensure_db(self.db_path)
        with closing(sqlite3.connect(str(self.db_path))) as con:
            con.row_factory = sqlite3.Row
            con.execute("PRAGMA query_only = ON")  # tests must never modify their own data
            result = [dict(r) for r in con.execute(f"SELECT * FROM {self.table} ORDER BY id")]
        for row in result:
            for col in self.json_columns:
                if row.get(col) is not None:
                    row[col] = json.loads(row[col])
        return result


def _validated(rows: list[dict[str, Any]], origin: str) -> list[dict[str, Any]]:
    if not rows:
        raise ValueError(f"No data rows in {origin}")
    ids = [r.get("id") for r in rows]
    if any(i in (None, "") for i in ids):
        raise ValueError(f"Every row in {origin} needs a non-empty 'id' column")
    duplicates = {i for i in ids if ids.count(i) > 1}
    if duplicates:
        raise ValueError(f"Duplicate ids in {origin}: {sorted(map(str, duplicates))}")
    return rows


def load_rows(name: str, source: str = "csv", json_columns: Iterable[str] = ()) -> list[dict[str, Any]]:
    s = get_settings()
    if source == "csv":
        origin: DataSource = CsvSource(s.data_dir / "csv" / f"{name}.csv")
    elif source == "sqlite":
        origin = SqliteSource(s.sqlite_path, name, json_columns)
    else:
        raise ValueError(f"Unknown data source '{source}' (use 'csv' or 'sqlite')")
    return _validated(origin.rows(), f"{source}:{name}")


def load_cases(name: str, source: str = "csv", json_columns: Iterable[str] = ()) -> list:
    """Rows -> pytest.param objects with readable ids, ready for @pytest.mark.parametrize."""
    return [pytest.param(row, id=str(row["id"])) for row in load_rows(name, source, json_columns)]
