"""I/O utilities for data export."""

import pandas as pd
from pathlib import Path
from typing import Optional

from schools_scraper.config import config


def write_csv(df: pd.DataFrame, path: str, index: bool = False) -> None:
    """Write DataFrame to CSV file.

    Args:
        df: DataFrame to write.
        path: Output file path.
        index: Whether to include index in output.
    """
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path, index=index)


def write_parquet(df: pd.DataFrame, path: str) -> None:
    """Write DataFrame to Parquet file.

    Args:
        df: DataFrame to write.
        path: Output file path.
    """
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(output_path)



