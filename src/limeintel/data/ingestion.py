"""Data ingestion utilities for LimeIntel."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from limeintel.data.schemas import validate_required_columns


def load_us_mcallen_prices(path: str | Path) -> pd.DataFrame:
    """Load raw U.S. McAllen price history from CSV."""
    path = Path(path)
    df = pd.read_csv(path)
    validate_required_columns(df.columns)
    return df
