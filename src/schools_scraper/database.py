"""Database management for storing scraped data."""

import duckdb
import pandas as pd
from pathlib import Path
from typing import Any, Dict, List, Optional

from schools_scraper.config import config


class Database:
    """Database manager using DuckDB."""

    def __init__(self, db_path: Optional[Path] = None) -> None:
        """Initialize database connection.

        Args:
            db_path: Path to database file. Defaults to config.DATABASE_PATH.
        """
        self.db_path = db_path or config.DATABASE_PATH
        config.ensure_data_dir()
        self.conn = duckdb.connect(str(self.db_path))

    def create_table(self, table_name: str, schema: Dict[str, str]) -> None:
        """Create a table with the given schema.

        Args:
            table_name: Name of the table.
            schema: Dictionary mapping column names to SQL types.
        """
        columns = ", ".join([f"{name} {type_}" for name, type_ in schema.items()])
        query = f"CREATE TABLE IF NOT EXISTS {table_name} ({columns})"
        self.conn.execute(query)

    def insert(self, table_name: str, data: Dict[str, Any]) -> None:
        """Insert a single row into the table.

        Args:
            table_name: Name of the table.
            data: Dictionary of column names to values. Columns not in data will use defaults.
        """
        # Filter out None values and get columns/values
        filtered_data = {k: v for k, v in data.items() if v is not None}
        if not filtered_data:
            return
            
        columns = ", ".join(filtered_data.keys())
        placeholders = ", ".join(["?" for _ in filtered_data])
        values = list(filtered_data.values())
        query = f"INSERT INTO {table_name} ({columns}) VALUES ({placeholders})"
        self.conn.execute(query, values)

    def insert_batch(self, table_name: str, data: List[Dict[str, Any]]) -> None:
        """Insert multiple rows into the table.

        Args:
            table_name: Name of the table.
            data: List of dictionaries, each representing a row.
        """
        if not data:
            return

        columns = ", ".join(data[0].keys())
        placeholders = ", ".join(["?" for _ in data[0]])
        values = [tuple(row.values()) for row in data]
        query = f"INSERT INTO {table_name} ({columns}) VALUES ({placeholders})"
        self.conn.executemany(query, values)

    def query(self, sql: str, params: Optional[tuple] = None) -> pd.DataFrame:
        """Execute a SQL query and return results as a DataFrame.

        Args:
            sql: SQL query string.
            params: Optional parameters for parameterized queries.

        Returns:
            DataFrame with query results.
        """
        if params:
            return self.conn.execute(sql, params).df()
        return self.conn.execute(sql).df()

    def get_table(self, table_name: str) -> pd.DataFrame:
        """Get all data from a table.

        Args:
            table_name: Name of the table.

        Returns:
            DataFrame with all table data.
        """
        return self.query(f"SELECT * FROM {table_name}")

    def close(self) -> None:
        """Close the database connection."""
        self.conn.close()

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()


