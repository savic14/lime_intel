from pathlib import Path
import pandas as pd

INPUT_PATH = Path("data/processed/market_master_with_usda_signal.csv")
OUTPUT_PATH = Path("data/processed/market_features_with_usda_signal.csv")

OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

df = pd.read_csv(INPUT_PATH)

df["date"] = pd.to_datetime(df["date"], errors="coerce")
df["official_price"] = pd.to_numeric(df["official_price"], errors="coerce")
df["truck_crossings"] = pd.to_numeric(df["truck_crossings"], errors="coerce")
df["rain_mm_origin"] = pd.to_numeric(df["rain_mm_origin"], errors="coerce")
df["usda_publish_hour"] = pd.to_numeric(df["usda_publish_hour"], errors="coerce")
df["is_tuesday_usda"] = pd.to_numeric(df["is_tuesday_usda"], errors="coerce").fillna(0)
df["is_usda_publish_day"] = pd.to_numeric(df["is_usda_publish_day"], errors="coerce").fillna(0)

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
