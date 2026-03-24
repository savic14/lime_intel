from pathlib import Path
import math
import pandas as pd
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, mean_squared_error

INPUT_PATH = Path("data/processed/market_training_with_usda_signal.csv")

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

target_col = "target_7d"

use_cols = feature_cols + [target_col, "date", "market", "size", "quality"]
data = df[use_cols].copy().dropna()

if len(data) < 5:
    raise SystemExit("No hay suficientes filas limpias para entrenar target_7d.")

data["date"] = pd.to_datetime(data["date"], errors="coerce")
data = data.sort_values("date").reset_index(drop=True)

split_idx = max(1, int(len(data) * 0.8))
train = data.iloc[:split_idx].copy()
test = data.iloc[split_idx:].copy()

if test.empty:
    raise SystemExit("No hay filas suficientes para test después del split.")

X_train = train[feature_cols]
y_train = train[target_col]
X_test = test[feature_cols]
y_test = test[target_col]

model = LinearRegression()
model.fit(X_train, y_train)

pred = model.predict(X_test)

mae = mean_absolute_error(y_test, pred)
rmse = math.sqrt(mean_squared_error(y_test, pred))

last_features = data.iloc[[-1]][feature_cols]
next_7d_pred = float(model.predict(last_features)[0])
last_price = float(data.iloc[-1]["official_price"])

if next_7d_pred > last_price + 0.5:
    direction = "SUBE"
elif next_7d_pred < last_price - 0.5:
    direction = "BAJA"
else:
    direction = "LATERAL"

print("ok")
print("rows_used:", len(data))
print("train_rows:", len(train))
print("test_rows:", len(test))
print("mae:", round(mae, 4))
print("rmse:", round(rmse, 4))
print("last_official_price:", round(last_price, 4))
print("predicted_target_7d:", round(next_7d_pred, 4))
print("direction_7d:", direction)
