"""Baseline models for LimeIntel using scikit-learn only."""

from __future__ import annotations

from typing import Any

import pandas as pd
from sklearn.linear_model import Ridge
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler


def train_baseline_model(X_train: pd.DataFrame, y_train: pd.Series) -> Any:
    """Train a baseline Ridge regression model with scaling."""
    pipeline = Pipeline(
        [
            ("scaler", StandardScaler()),
            ("model", Ridge(alpha=1.0)),
        ]
    )
    pipeline.fit(X_train, y_train)
    return pipeline


def predict_baseline(model: Any, X: pd.DataFrame) -> pd.Series:
    """Generate predictions from a trained baseline model."""
    pred = model.predict(X)
    return pd.Series(pred, index=X.index, name="predicted")
