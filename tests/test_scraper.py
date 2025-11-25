"""Tests for scraper module."""

import pytest
from unittest.mock import Mock, patch

from schools_scraper.scraper import Scraper


def test_scraper_initialization():
    """Test scraper initialization."""
    scraper = Scraper(base_url="https://example.com")
    assert scraper.base_url == "https://example.com"
    assert scraper.user_agent is not None
    scraper.close()


def test_scraper_context_manager():
    """Test scraper as context manager."""
    with Scraper() as scraper:
        assert scraper.client is not None
    # Client should be closed after context exit


def test_parse_html():
    """Test HTML parsing."""
    with Scraper() as scraper:
        html = "<html><body><h1>Test</h1></body></html>"
        soup = scraper.parse_html(html)
        assert soup.find("h1").get_text() == "Test"


def test_extract_links():
    """Test link extraction."""
    with Scraper(base_url="https://example.com") as scraper:
        html = '<html><body><a href="/page1">Link 1</a><a href="https://other.com">Link 2</a></body></html>'
        soup = scraper.parse_html(html)
        links = scraper.extract_links(soup)
        assert len(links) >= 1
        assert any("other.com" in link for link in links)


