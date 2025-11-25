"""Web scraping functionality."""

import time
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup

from schools_scraper.config import config


class Scraper:
    """Web scraper with retry logic and rate limiting."""

    def __init__(
        self,
        base_url: Optional[str] = None,
        user_agent: Optional[str] = None,
        timeout: Optional[int] = None,
        max_retries: Optional[int] = None,
        delay: float = 1.0,
    ) -> None:
        """Initialize scraper.

        Args:
            base_url: Base URL for relative links.
            user_agent: User agent string. Defaults to config.USER_AGENT.
            timeout: Request timeout in seconds. Defaults to config.REQUEST_TIMEOUT.
            max_retries: Maximum retry attempts. Defaults to config.MAX_RETRIES.
            delay: Delay between requests in seconds.
        """
        self.base_url = base_url
        self.user_agent = user_agent or config.USER_AGENT
        self.timeout = timeout or config.REQUEST_TIMEOUT
        self.max_retries = max_retries or config.MAX_RETRIES
        self.delay = delay
        self.client = httpx.Client(
            headers={"User-Agent": self.user_agent},
            timeout=self.timeout,
            follow_redirects=True,
        )

    def fetch(self, url: str) -> Optional[httpx.Response]:
        """Fetch a URL with retry logic.

        Args:
            url: URL to fetch.

        Returns:
            Response object or None if all retries failed.
        """
        if self.base_url and not url.startswith(("http://", "https://")):
            url = urljoin(self.base_url, url)

        for attempt in range(self.max_retries):
            try:
                response = self.client.get(url)
                response.raise_for_status()
                time.sleep(self.delay)  # Rate limiting
                return response
            except httpx.HTTPError as e:
                if attempt == self.max_retries - 1:
                    print(f"Failed to fetch {url} after {self.max_retries} attempts: {e}")
                    return None
                time.sleep(self.delay * (attempt + 1))  # Exponential backoff

        return None

    def parse_html(self, html: str) -> BeautifulSoup:
        """Parse HTML content.

        Args:
            html: HTML string.

        Returns:
            BeautifulSoup object.
        """
        return BeautifulSoup(html, "lxml")

    def scrape_page(self, url: str) -> Optional[BeautifulSoup]:
        """Fetch and parse a page.

        Args:
            url: URL to scrape.

        Returns:
            Parsed BeautifulSoup object or None if fetch failed.
        """
        response = self.fetch(url)
        if response is None:
            return None
        return self.parse_html(response.text)

    def extract_links(self, soup: BeautifulSoup, base_url: Optional[str] = None) -> List[str]:
        """Extract all links from a page.

        Args:
            soup: BeautifulSoup object.
            base_url: Base URL for resolving relative links.

        Returns:
            List of absolute URLs.
        """
        links = []
        base = base_url or self.base_url

        for tag in soup.find_all("a", href=True):
            href = tag["href"]
            if base:
                absolute_url = urljoin(base, href)
            else:
                absolute_url = href

            # Only include http/https links
            if absolute_url.startswith(("http://", "https://")):
                links.append(absolute_url)

        return links

    def extract_all_text(self, soup: BeautifulSoup) -> str:
        """Extract all text content from a page, removing extra whitespace.

        Args:
            soup: BeautifulSoup object.

        Returns:
            Cleaned text content.
        """
        # Remove script and style elements
        for script in soup(["script", "style", "meta", "link"]):
            script.decompose()

        # Get text and clean it up
        text = soup.get_text()
        # Break into lines and remove leading/trailing whitespace
        lines = (line.strip() for line in text.splitlines())
        # Break multi-headlines into a line each
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        # Drop blank lines
        text = "\n".join(chunk for chunk in chunks if chunk)
        return text

    def extract_structured_content(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """Extract structured content from a page.

        Args:
            soup: BeautifulSoup object.

        Returns:
            Dictionary with structured content.
        """
        content: Dict[str, Any] = {}

        # Title
        title_tag = soup.find("title")
        content["title"] = title_tag.get_text().strip() if title_tag else ""

        # Main heading (h1)
        h1_tag = soup.find("h1")
        content["heading"] = h1_tag.get_text().strip() if h1_tag else ""

        # All paragraphs
        paragraphs = soup.find_all("p")
        content["paragraphs"] = [p.get_text().strip() for p in paragraphs if p.get_text().strip()]

        # All headings (h1-h6)
        headings = {}
        for level in range(1, 7):
            h_tags = soup.find_all(f"h{level}")
            headings[f"h{level}"] = [h.get_text().strip() for h in h_tags if h.get_text().strip()]
        content["headings"] = headings

        # All links
        links = []
        for tag in soup.find_all("a", href=True):
            link_text = tag.get_text().strip()
            link_url = tag.get("href", "")
            if link_text or link_url:
                links.append({"text": link_text, "url": link_url})
        content["links"] = links

        # All images
        images = []
        for tag in soup.find_all("img"):
            src = tag.get("src", "")
            alt = tag.get("alt", "")
            if src:
                images.append({"src": src, "alt": alt})
        content["images"] = images

        # Full text
        content["full_text"] = self.extract_all_text(soup)

        return content

    def close(self) -> None:
        """Close the HTTP client."""
        self.client.close()

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()


