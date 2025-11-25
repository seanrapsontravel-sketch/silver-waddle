"""Data analysis utilities."""

import pandas as pd
from typing import Any, Dict, List, Optional

from schools_scraper.database import Database


class Analyzer:
    """Data analysis tools."""

    def __init__(self, db: Optional[Database] = None) -> None:
        """Initialize analyzer.

        Args:
            db: Database instance. If None, creates a new one.
        """
        self.db = db or Database()

    def describe_table(self, table_name: str) -> pd.DataFrame:
        """Get descriptive statistics for a table.

        Args:
            table_name: Name of the table.

        Returns:
            DataFrame with descriptive statistics.
        """
        df = self.db.get_table(table_name)
        return df.describe()

    def count_by_column(self, table_name: str, column: str) -> pd.DataFrame:
        """Count occurrences by column value.

        Args:
            table_name: Name of the table.
            column: Column name to group by.

        Returns:
            DataFrame with counts.
        """
        query = f"SELECT {column}, COUNT(*) as count FROM {table_name} GROUP BY {column} ORDER BY count DESC"
        return self.db.query(query)

    def filter_table(
        self,
        table_name: str,
        conditions: Dict[str, Any],
        limit: Optional[int] = None,
    ) -> pd.DataFrame:
        """Filter table rows based on conditions.

        Args:
            table_name: Name of the table.
            conditions: Dictionary of column: value pairs for filtering.
            limit: Optional limit on number of rows.

        Returns:
            Filtered DataFrame.
        """
        where_clauses = []
        params = []

        for col, value in conditions.items():
            if isinstance(value, str):
                where_clauses.append(f"{col} = ?")
                params.append(value)
            elif isinstance(value, (int, float)):
                where_clauses.append(f"{col} = ?")
                params.append(value)
            elif isinstance(value, list):
                placeholders = ", ".join(["?" for _ in value])
                where_clauses.append(f"{col} IN ({placeholders})")
                params.extend(value)

        where_sql = " AND ".join(where_clauses)
        query = f"SELECT * FROM {table_name} WHERE {where_sql}"

        if limit:
            query += f" LIMIT {limit}"

        return self.db.query(query, tuple(params) if params else None)

    def aggregate(
        self,
        table_name: str,
        group_by: List[str],
        aggregations: Dict[str, str],
    ) -> pd.DataFrame:
        """Perform aggregations on a table.

        Args:
            table_name: Name of the table.
            group_by: List of columns to group by.
            aggregations: Dictionary of column: aggregation_function pairs.
                Supported functions: COUNT, SUM, AVG, MIN, MAX.

        Returns:
            DataFrame with aggregated results.
        """
        agg_clauses = []
        for col, func in aggregations.items():
            agg_clauses.append(f"{func}({col}) as {func.lower()}_{col}")

        group_by_sql = ", ".join(group_by)
        agg_sql = ", ".join(agg_clauses)
        query = (
            f"SELECT {group_by_sql}, {agg_sql} "
            f"FROM {table_name} "
            f"GROUP BY {group_by_sql}"
        )

        return self.db.query(query)

    def close(self) -> None:
        """Close database connection."""
        if self.db:
            self.db.close()

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()



