from pathlib import Path
import pandas as pd

INPUT_PATH = Path("data/processed/market_features.csv")
OUTPUT_PATH = Path("data/processed/market_training_data.csv")

df = pd.read_csv(INPUT_PATH)

df["date"] = pd.to_datetime(df["date"], errors="coerce")
df = df.sort_values(["market", "size", "quality", "date"]).reset_index(drop=True)

group_cols = ["market", "size", "quality"]

for horizon in [1, 3, 7, 10, 14]:
    df[f"target_{horizon}d"] = (
        df.groupby(group_cols)["official_price"].shift(-horizon)
    )

df.to_csv(OUTPUT_PATH, index=False)
print(f"ok -> {OUTPUT_PATH}")
