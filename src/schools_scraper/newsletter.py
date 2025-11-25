"""Newsletter-specific scraping functionality."""

import json
import time
from typing import Dict, Any, List, Optional
from datetime import datetime

from schools_scraper.database import Database
from schools_scraper.scraper import Scraper


def scrape_newsletter(url: str, table_name: str = "newsletters") -> Dict[str, Any]:
    """Scrape a newsletter page and store in database.

    Args:
        url: URL of the newsletter page.
        table_name: Name of the database table.

    Returns:
        Dictionary with scraping results.
    """
    with Scraper() as scraper:
        soup = scraper.scrape_page(url)
        if soup is None:
            raise ValueError(f"Failed to scrape page: {url}")

        # Extract structured content
        content = scraper.extract_structured_content(soup)

        # Store in database
        with Database() as db:
            # Create sequence for auto-incrementing ID
            seq_name = f"{table_name}_id_seq"
            db.conn.execute(f"CREATE SEQUENCE IF NOT EXISTS {seq_name}")
            
            # Create table schema
            schema = {
                "id": "INTEGER PRIMARY KEY",
                "url": "VARCHAR",
                "title": "VARCHAR",
                "heading": "VARCHAR",
                "full_text": "TEXT",
                "content_json": "TEXT",  # Store structured content as JSON
                "scraped_at": "TIMESTAMP",
            }
            db.create_table(table_name, schema)

            # Prepare data with auto-generated ID
            data = {
                "id": f"NEXTVAL('{seq_name}')",
                "url": url,
                "title": content.get("title", ""),
                "heading": content.get("heading", ""),
                "full_text": content.get("full_text", ""),
                "content_json": json.dumps(content, ensure_ascii=False),
                "scraped_at": datetime.now().isoformat(),
            }

            # Use raw SQL for sequence
            columns = ", ".join([k for k in data.keys() if k != "id"] + ["id"])
            values_str = ", ".join(["?" for _ in data.keys() if _ != "id"] + [f"NEXTVAL('{seq_name}')"])
            query = f"INSERT INTO {table_name} ({columns}) VALUES ({values_str})"
            values = [v for k, v in data.items() if k != "id"]
            db.conn.execute(query, values)

        return {
            "success": True,
            "url": url,
            "table": table_name,
            "title": content.get("title", ""),
            "text_length": len(content.get("full_text", "")),
            "paragraphs_count": len(content.get("paragraphs", [])),
            "links_count": len(content.get("links", [])),
            "images_count": len(content.get("images", [])),
        }


def scrape_newsletter_range(
    base_url: str,
    start_id: int,
    end_id: int,
    table_name: str = "newsletters",
    delay: float = 1.0,
    continue_on_error: bool = True,
) -> Dict[str, Any]:
    """Scrape multiple newsletter pages by ID range.

    Args:
        base_url: Base URL template (e.g., "https://www.westst.org.uk/parentportal/newsletter/?id={id}")
        start_id: Starting newsletter ID (inclusive).
        end_id: Ending newsletter ID (inclusive).
        table_name: Name of the database table.
        delay: Delay between requests in seconds.
        continue_on_error: Whether to continue scraping if one page fails.

    Returns:
        Dictionary with scraping results summary.
    """
    results = {
        "successful": [],
        "failed": [],
        "total": end_id - start_id + 1,
        "success_count": 0,
        "fail_count": 0,
    }

    with Scraper(delay=delay) as scraper:
        with Database() as db:
            # Create table schema once
            seq_name = f"{table_name}_id_seq"
            db.conn.execute(f"CREATE SEQUENCE IF NOT EXISTS {seq_name}")
            
            schema = {
                "id": "INTEGER PRIMARY KEY",
                "url": "VARCHAR",
                "title": "VARCHAR",
                "heading": "VARCHAR",
                "full_text": "TEXT",
                "content_json": "TEXT",
                "scraped_at": "TIMESTAMP",
            }
            db.create_table(table_name, schema)

            for newsletter_id in range(start_id, end_id + 1):
                url = base_url.format(id=newsletter_id)
                print(f"Scraping ID {newsletter_id} ({newsletter_id - start_id + 1}/{results['total']})...", end=" ")

                try:
                    soup = scraper.scrape_page(url)
                    if soup is None:
                        raise ValueError(f"Failed to fetch page")

                    # Extract structured content
                    content = scraper.extract_structured_content(soup)

                    # Check if this URL already exists in database
                    existing = db.query(
                        f"SELECT id FROM {table_name} WHERE url = ?",
                        (url,)
                    )

                    if not existing.empty:
                        print(f"✓ Already exists (skipped)")
                        results["successful"].append({
                            "id": newsletter_id,
                            "url": url,
                            "status": "already_exists"
                        })
                        results["success_count"] += 1
                        continue

                    # Insert into database
                    columns = ", ".join(["url", "title", "heading", "full_text", "content_json", "scraped_at", "id"])
                    values_str = ", ".join(["?" for _ in range(6)] + [f"NEXTVAL('{seq_name}')"])
                    query = f"INSERT INTO {table_name} ({columns}) VALUES ({values_str})"
                    values = [
                        url,
                        content.get("title", ""),
                        content.get("heading", ""),
                        content.get("full_text", ""),
                        json.dumps(content, ensure_ascii=False),
                        datetime.now().isoformat(),
                    ]
                    db.conn.execute(query, values)

                    text_length = len(content.get("full_text", ""))
                    print(f"✓ Scraped ({text_length:,} chars)")
                    results["successful"].append({
                        "id": newsletter_id,
                        "url": url,
                        "title": content.get("title", ""),
                        "text_length": text_length,
                    })
                    results["success_count"] += 1

                except Exception as e:
                    error_msg = str(e)
                    print(f"✗ Failed: {error_msg}")
                    results["failed"].append({
                        "id": newsletter_id,
                        "url": url,
                        "error": error_msg,
                    })
                    results["fail_count"] += 1

                    if not continue_on_error:
                        raise

                # Rate limiting
                if delay > 0:
                    time.sleep(delay)

    return results

