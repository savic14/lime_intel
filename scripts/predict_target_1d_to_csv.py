from pathlib import Path
import math
import pandas as pd
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, mean_squared_error

INPUT_PATH = Path("data/processed/market_training_with_usda_signal.csv")
OUTPUT_PATH = Path("data/processed/prediction_target_1d.csv")

df = pd.read_csv(INPUT_PATH)

feature_cols = [
    "official_price",
    "truck_crossings",
    "rain_mm_origin",
    "days_since_market_signal",
    "is_market_signal_day",
    "price_lag_1",
    "price_lag_3",
    "ma_3",
    "price_change_1d",
]

target_col = "target_1d"

use_cols = feature_cols + [target_col, "date", "market", "size", "quality"]
data = df[use_cols].copy().dropna()

if len(data) < 5:
    raise SystemExit("No hay suficientes filas limpias para predecir target_1d.")

data["date"] = pd.to_datetime(data["date"], errors="coerce")
data = data.sort_values("date").reset_index(drop=True)

split_idx = max(1, int(len(data) * 0.8))
train = data.iloc[:split_idx].copy()
test = data.iloc[split_idx:].copy()

X_train = train[feature_cols]
y_train = train[target_col]

model = LinearRegression()
model.fit(X_train, y_train)

pred = model.predict(test[feature_cols])
mae = mean_absolute_error(test[target_col], pred)
rmse = math.sqrt(mean_squared_error(test[target_col], pred))

last_row = data.iloc[-1].copy()
last_features = pd.DataFrame([last_row[feature_cols]])
predicted_price = float(model.predict(last_features)[0])
last_price = float(last_row["official_price"])

if predicted_price > last_price + 0.25:
    direction = "SUBE"
elif predicted_price < last_price - 0.25:
    direction = "BAJA"
else:
    direction = "LATERAL"

out = pd.DataFrame([{
    "run_date": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S"),
    "market": last_row["market"],
    "size": last_row["size"],
    "quality": last_row["quality"],
    "last_date": pd.to_datetime(last_row["date"]).strftime("%Y-%m-%d"),
    "last_official_price": round(last_price, 4),
    "predicted_target_1d": round(predicted_price, 4),
    "direction_1d": direction,
    "mae": round(float(mae), 4),
    "rmse": round(float(rmse), 4),
    "rows_used": int(len(data)),
}])

OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
out.to_csv(OUTPUT_PATH, index=False)
print("ok")
print(OUTPUT_PATH)
