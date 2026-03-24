"""Central configuration for the LimeIntel project."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    project_root: Path = Path(__file__).resolve().parents[3]
    data_dir: Path = project_root / "data"
    raw_data_dir: Path = data_dir / "raw"

    us_mcallen_raw_prices_path: Path = raw_data_dir / "us_mcallen_prices.csv"

    date_column: str = "date"
    price_column: str = "official_price"
    market_column: str = "market"
    default_market: str = "US_MCALLEN"

    prediction_horizon_days: int = 7


settings = Settings()
