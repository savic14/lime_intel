"""Lightweight schema helpers for LimeIntel dataframes."""

from __future__ import annotations

REQUIRED_PRICE_COLUMNS = ["date", "official_price", "market"]
OPTIONAL_PRICE_COLUMNS = ["my_sale_price", "my_cost", "size", "quality", "source", "notes"]


def validate_required_columns(columns) -> None:
    missing = [c for c in REQUIRED_PRICE_COLUMNS if c not in columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")
