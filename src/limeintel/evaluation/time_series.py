"""Time-based splitting and evaluation for LimeIntel."""

from __future__ import annotations

from typing import Tuple

import numpy as np
import pandas as pd

from limeintel.config.settings import settings


def train_test_time_split(
    df: pd.DataFrame,
    date_col: str | None = None,
    test_fraction: float = 0.2,
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Split a chronological DataFrame into train and test by time."""
    date_col = date_col or settings.date_column

    if not 0 < test_fraction < 1:
        raise ValueError("test_fraction must be strictly between 0 and 1.")

    n = len(df)
    if n < 2:
        raise ValueError("DataFrame must contain at least 2 rows.")

    split_idx = int(n * (1 - test_fraction))
    if split_idx <= 0 or split_idx >= n:
        raise ValueError("test_fraction produces an empty train or test split.")

    train_df = df.iloc[:split_idx]
    test_df = df.iloc[split_idx:]
    return train_df, test_df


def regression_metrics(y_true: pd.Series, y_pred: pd.Series) -> dict:
    """Compute MAE, RMSE, and MAPE for regression."""
    common = y_true.index.intersection(y_pred.index)
    y_true = y_true.loc[common]
    y_pred = y_pred.loc[common]

    diff = y_true - y_pred
    mae = float(diff.abs().mean())
    rmse = float(np.sqrt((diff**2).mean()))

    nonzero = y_true != 0
    if nonzero.any():
        mape = float(np.abs(diff.loc[nonzero] / y_true.loc[nonzero]).mean() * 100)
    else:
        mape = None

    return {"mae": mae, "rmse": rmse, "mape": mape}
