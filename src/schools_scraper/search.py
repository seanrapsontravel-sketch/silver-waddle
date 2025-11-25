"""Full-text search functionality for newsletters."""

import re
from typing import Dict, List, Optional, Tuple

import pandas as pd

from schools_scraper.database import Database


class NewsletterSearch:
    """Search functionality for newsletters using DuckDB text search."""

    def __init__(self, db: Optional[Database] = None) -> None:
        """Initialize search with database connection.

        Args:
            db: Database instance. If None, creates a new one.
        """
        self.db = db or Database()

    def search(
        self,
        query: str,
        table_name: str = "newsletters",
        limit: int = 20,
        min_matches: int = 1,
    ) -> pd.DataFrame:
        """Search newsletters using full-text search.

        Args:
            query: Search query string (can contain multiple keywords).
            table_name: Name of the newsletters table.
            limit: Maximum number of results to return.
            min_matches: Minimum number of keyword matches required.

        Returns:
            DataFrame with matching newsletters, sorted by relevance.
        """
        # Extract keywords from query (split on whitespace, remove empty strings)
        keywords = [k.strip().lower() for k in re.split(r"\s+", query) if k.strip()]
        if not keywords:
            return pd.DataFrame()

        # Build WHERE clause with ILIKE conditions for each keyword
        # Use OR to match any keyword, and count matches for ranking
        conditions = []
        for keyword in keywords:
            # Escape special characters for ILIKE
            escaped_keyword = keyword.replace("%", "\\%").replace("_", "\\_")
            conditions.append(f"full_text ILIKE '%{escaped_keyword}%'")

        where_clause = " OR ".join(conditions)

        # Count matches for ranking (how many keywords appear in the text)
        match_counts = []
        for keyword in keywords:
            escaped_keyword = keyword.replace("%", "\\%").replace("_", "\\_")
            match_counts.append(
                f"CASE WHEN full_text ILIKE '%{escaped_keyword}%' THEN 1 ELSE 0 END"
            )

        match_count_expr = " + ".join(match_counts)

        # Build query with relevance ranking
        sql = f"""
        SELECT 
            id,
            url,
            title,
            heading,
            full_text,
            scraped_at,
            ({match_count_expr}) as match_count,
            LENGTH(full_text) as text_length
        FROM {table_name}
        WHERE full_text IS NOT NULL
          AND ({where_clause})
        ORDER BY match_count DESC, text_length ASC
        LIMIT {limit}
        """

        results = self.db.query(sql)

        # Filter by minimum matches
        if not results.empty and min_matches > 0:
            results = results[results["match_count"] >= min_matches]

        return results

    def search_advanced(
        self,
        query: str,
        table_name: str = "newsletters",
        limit: int = 20,
        search_fields: Optional[List[str]] = None,
    ) -> pd.DataFrame:
        """Advanced search with support for field-specific queries.

        Args:
            query: Search query string.
            table_name: Name of the newsletters table.
            limit: Maximum number of results to return.
            search_fields: List of fields to search (default: ['full_text', 'title', 'heading']).

        Returns:
            DataFrame with matching newsletters.
        """
        if search_fields is None:
            search_fields = ["full_text", "title", "heading"]

        keywords = [k.strip().lower() for k in re.split(r"\s+", query) if k.strip()]
        if not keywords:
            return pd.DataFrame()

        # Build conditions for each field
        field_conditions = []
        for field in search_fields:
            field_keywords = []
            for keyword in keywords:
                escaped_keyword = keyword.replace("%", "\\%").replace("_", "\\_")
                field_keywords.append(f"{field} ILIKE '%{escaped_keyword}%'")
            field_conditions.append(f"({' OR '.join(field_keywords)})")

        where_clause = " OR ".join(field_conditions)

        # Build relevance score (weighted: title/heading matches worth more)
        score_parts = []
        for keyword in keywords:
            escaped_keyword = keyword.replace("%", "\\%").replace("_", "\\_")
            score_parts.append(
                f"(CASE WHEN title ILIKE '%{escaped_keyword}%' THEN 3 ELSE 0 END + "
                f"CASE WHEN heading ILIKE '%{escaped_keyword}%' THEN 2 ELSE 0 END + "
                f"CASE WHEN full_text ILIKE '%{escaped_keyword}%' THEN 1 ELSE 0 END)"
            )

        score_expr = " + ".join(score_parts) if score_parts else "0"

        sql = f"""
        SELECT 
            id,
            url,
            title,
            heading,
            full_text,
            scraped_at,
            ({score_expr}) as relevance_score
        FROM {table_name}
        WHERE ({where_clause})
        ORDER BY relevance_score DESC, scraped_at DESC
        LIMIT {limit}
        """

        return self.db.query(sql)

    def get_relevant_text(
        self,
        query: str,
        table_name: str = "newsletters",
        max_results: int = 20,
        max_chars: int = 10000,
    ) -> Tuple[str, List[Dict[str, str]]]:
        """Get relevant newsletter text for GPT analysis.

        Args:
            query: Search query string.
            table_name: Name of the newsletters table.
            max_results: Maximum number of newsletters to include.
            max_chars: Maximum total characters to include.

        Returns:
            Tuple of (combined text, list of source dicts with url, title, heading).
        """
        results = self.search_advanced(query, table_name=table_name, limit=max_results)

        if results.empty:
            return "No relevant newsletters found.", []

        texts = []
        sources = []
        total_chars = 0

        for _, row in results.iterrows():
            # Build excerpt with title/heading context
            excerpt_parts = []
            title = str(row.get("title", "")) if pd.notna(row.get("title")) else ""
            heading = str(row.get("heading", "")) if pd.notna(row.get("heading")) else ""
            url = str(row.get("url", "")) if pd.notna(row.get("url")) else ""
            
            if title:
                excerpt_parts.append(f"Title: {title}")
            if heading:
                excerpt_parts.append(f"Heading: {heading}")

            full_text = row.get("full_text", "")
            if full_text:
                # Truncate if needed
                remaining_chars = max_chars - total_chars
                if remaining_chars <= 0:
                    break

                if len(full_text) > remaining_chars:
                    full_text = full_text[:remaining_chars] + "... [truncated]"

                excerpt_parts.append(f"Content: {full_text}")
                excerpt = "\n".join(excerpt_parts)
                texts.append(excerpt)
                total_chars += len(excerpt)
                
                # Store source info
                sources.append({
                    "url": url,
                    "title": title,
                    "heading": heading,
                })

                if total_chars >= max_chars:
                    break

        return "\n\n---\n\n".join(texts), sources

    def close(self) -> None:
        """Close database connection if we own it."""
        if self.db:
            self.db.close()

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()

