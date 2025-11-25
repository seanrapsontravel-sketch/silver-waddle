"""Configuration management for the schools scraper."""

import os
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class Config:
    """Application configuration."""

    # OpenAI
    OPENAI_API_KEY: Optional[str] = os.getenv("OPENAI_API_KEY")

    # Database
    DATABASE_PATH: Path = Path(
        os.getenv("DATABASE_PATH", "data/schools.db")
    ).expanduser()

    # Scraper settings
    USER_AGENT: str = os.getenv(
        "USER_AGENT",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    )
    REQUEST_TIMEOUT: int = int(os.getenv("REQUEST_TIMEOUT", "30"))
    MAX_RETRIES: int = int(os.getenv("MAX_RETRIES", "3"))

    @classmethod
    def ensure_data_dir(cls) -> None:
        """Ensure data directory exists."""
        cls.DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)


config = Config()


