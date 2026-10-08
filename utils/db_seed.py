"""Builds the SQLite test-data database from tests/data/seed.sql.

Usage: python -m utils.db_seed [--force]
"""
from __future__ import annotations

import sqlite3
import sys
from contextlib import closing
from pathlib import Path


def ensure_db(db_path: Path, force: bool = False) -> Path:
    """Create the DB if missing, or rebuild it when seed.sql is newer (so edits are picked up)."""
    db_path = Path(db_path)
    seed = db_path.parent / "seed.sql"
    if not seed.exists():
        raise FileNotFoundError(f"Seed script not found: {seed}")
    if db_path.exists() and not force and db_path.stat().st_mtime >= seed.stat().st_mtime:
        return db_path
    db_path.parent.mkdir(parents=True, exist_ok=True)
    if db_path.exists():
        db_path.unlink()
    with closing(sqlite3.connect(str(db_path))) as con:
        con.executescript(seed.read_text(encoding="utf-8"))
        con.commit()
    return db_path


if __name__ == "__main__":
    from utils.settings import get_settings

    path = ensure_db(get_settings().sqlite_path, force="--force" in sys.argv)
    print(f"SQLite test data ready: {path}")
