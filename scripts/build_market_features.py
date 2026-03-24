from pathlib import Path
import pandas as pd

INPUT_PATH = Path("data/raw/market_master.csv")
OUTPUT_PATH = Path("data/processed/market_features.csv")

OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

df = pd.read_csv(INPUT_PATH)

df["date"] = pd.to_datetime(df["date"], errors="coerce")
df["official_price"] = pd.to_numeric(df["official_price"], errors="coerce")

df = df.sort_values(["market", "size", "quality", "date"]).reset_index(drop=True)

group_cols = ["market", "size", "quality"]

df["price_lag_1"] = df.groupby(group_cols)["official_price"].shift(1)
df["price_lag_3"] = df.groupby(group_cols)["official_price"].shift(3)
df["price_lag_7"] = df.groupby(group_cols)["official_price"].shift(7)

df["ma_3"] = (
    df.groupby(group_cols)["official_price"]
    .transform(lambda s: s.shift(1).rolling(3, min_periods=1).mean())
)

df["ma_7"] = (
    df.groupby(group_cols)["official_price"]
    .transform(lambda s: s.shift(1).rolling(7, min_periods=1).mean())
)

df["price_change_1d"] = df["official_price"] - df["price_lag_1"]
df["price_change_7d"] = df["official_price"] - df["price_lag_7"]

df.to_csv(OUTPUT_PATH, index=False)
print(f"ok -> {OUTPUT_PATH}")
