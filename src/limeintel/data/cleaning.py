"""Data cleaning utilities for LimeIntel."""

from __future__ import annotations

import pandas as pd

from limeintel.config.settings import settings


def clean_us_mcallen_prices(df: pd.DataFrame) -> pd.DataFrame:
    """Clean and normalize raw McAllen price data."""
    out = df.copy()

    out[settings.date_column] = pd.to_datetime(out[settings.date_column], errors="coerce")
    out[settings.price_column] = pd.to_numeric(out[settings.price_column], errors="coerce")

    if "my_sale_price" in out.columns:
        out["my_sale_price"] = pd.to_numeric(out["my_sale_price"], errors="coerce")

    if "my_cost" in out.columns:
        out["my_cost"] = pd.to_numeric(out["my_cost"], errors="coerce")

    if "boxes" in out.columns:
        out["boxes"] = pd.to_numeric(out["boxes"], errors="coerce")

    out = out.dropna(subset=[settings.date_column, settings.price_column])

    if settings.market_column in out.columns:
        out[settings.market_column] = out[settings.market_column].astype(str).str.upper()
        out = out[out[settings.market_column] == settings.default_market]

    out = out.sort_values(settings.date_column).reset_index(drop=True)
    return out
