"""Tests for database module."""

import tempfile
from pathlib import Path

import pytest

from schools_scraper.database import Database


def test_database_creation():
    """Test database creation and table operations."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        with Database(db_path) as db:
            schema = {
                "id": "INTEGER",
                "name": "VARCHAR",
                "value": "DOUBLE",
            }
            db.create_table("test_table", schema)

            # Insert data
            db.insert("test_table", {"id": 1, "name": "test", "value": 1.5})
            db.insert_batch(
                "test_table",
                [
                    {"id": 2, "name": "test2", "value": 2.5},
                    {"id": 3, "name": "test3", "value": 3.5},
                ],
            )

            # Query data
            df = db.get_table("test_table")
            assert len(df) == 3
            assert df.iloc[0]["name"] == "test"


def test_database_query():
    """Test SQL query execution."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        with Database(db_path) as db:
            schema = {"id": "INTEGER", "name": "VARCHAR"}
            db.create_table("test_table", schema)
            db.insert("test_table", {"id": 1, "name": "test"})

            df = db.query("SELECT * FROM test_table WHERE id = ?", (1,))
            assert len(df) == 1
            assert df.iloc[0]["name"] == "test"


