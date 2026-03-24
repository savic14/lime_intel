"""Time-series-safe feature engineering for LimeIntel."""

from __future__ import annotations

from typing import List, Tuple

import pandas as pd

from limeintel.config.settings import settings


def build_price_features(
    df: pd.DataFrame,
    price_col: str | None = None,
    date_col: str | None = None,
    lags: Tuple[int, ...] = (1, 7, 14),
    rolling_windows: Tuple[int, ...] = (7,),
) -> pd.DataFrame:
    """Add lag and rolling features using only past data."""
    price_col = price_col or settings.price_column
    date_col = date_col or settings.date_column
    out = df[[date_col, price_col]].copy()

    for lag in lags:
        out[f"lag_{lag}"] = out[price_col].shift(lag)

    for w in rolling_windows:
        out[f"rolling_mean_{w}"] = (
            out[price_col].shift(1).rolling(window=w, min_periods=1).mean()
        )

    if pd.api.types.is_datetime64_any_dtype(out[date_col]):
        out["day_of_week"] = out[date_col].dt.dayofweek
        out["month"] = out[date_col].dt.month

    return out


def make_X_y(
    df: pd.DataFrame,
    target_col: str | None = None,
    horizon: int | None = None,
    feature_columns: List[str] | None = None,
):
    """Prepare aligned feature matrix X and target vector y."""
    target_col = target_col or settings.price_column
    horizon = horizon if horizon is not None else settings.prediction_horizon_days

    y = df[target_col].shift(-horizon)
    valid = y.notna()
    y = y.loc[valid]

    numeric = df.select_dtypes(include=["number"]).columns.tolist()
    if target_col in numeric:
        numeric.remove(target_col)

    use_cols = feature_columns or numeric
    use_cols = [c for c in use_cols if c in df.columns]

    X = df.loc[valid, use_cols]

    non_nan = X.notna().all(axis=1)
    X = X.loc[non_nan]
    y = y.loc[non_nan]

    return X, y
