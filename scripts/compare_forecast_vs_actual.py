import pandas as pd
from pathlib import Path
from datetime import datetime

forecast_path = Path("data/processed/daily_forecast_base.csv")
actual_path = Path("data/processed/shipping_point_core.csv")
out_path = Path("data/processed/forecast_vs_actual_base.csv")

if not forecast_path.exists():
    raise SystemExit(f"No existe {forecast_path}")
if not actual_path.exists():
    raise SystemExit(f"No existe {actual_path}")

forecast = pd.read_csv(forecast_path)
actual = pd.read_csv(actual_path)

forecast["last_date"] = pd.to_datetime(forecast["last_date"], errors="coerce")
actual["date"] = pd.to_datetime(actual["date"], errors="coerce")

forecast["expected_date_1d"] = forecast["last_date"] + pd.Timedelta(days=1)
forecast["expected_date_3d"] = forecast["last_date"] + pd.Timedelta(days=3)

actual_base = actual[actual["quality"] == "BASE"].copy()

# 1D actual
actual_1d = actual_base[["date", "size", "quality", "official_price"]].copy()
actual_1d = actual_1d.rename(columns={
    "date": "expected_date_1d",
    "official_price": "actual_price_1d",
})

# 3D actual
actual_3d = actual_base[["date", "size", "quality", "official_price"]].copy()
actual_3d = actual_3d.rename(columns={
    "date": "expected_date_3d",
    "official_price": "actual_price_3d",
})

res = forecast.merge(
    actual_1d,
    on=["expected_date_1d", "size", "quality"],
    how="left"
).merge(
    actual_3d,
    on=["expected_date_3d", "size", "quality"],
    how="left"
)

# Errores
res["error_1d"] = res["actual_price_1d"] - res["predicted_target_1d"]
res["abs_error_1d"] = res["error_1d"].abs()

res["error_3d"] = res["actual_price_3d"] - res["predicted_target_3d"]
res["abs_error_3d"] = res["error_3d"].abs()

# Direcciones reales
def real_direction(last_price, actual_price, threshold):
    if pd.isna(actual_price):
        return ""
    if actual_price > last_price + threshold:
        return "SUBE"
    if actual_price < last_price - threshold:
        return "BAJA"
    return "LATERAL"

res["actual_direction_1d"] = res.apply(
    lambda r: real_direction(r["last_official_price"], r["actual_price_1d"], 0.25), axis=1
)
res["actual_direction_3d"] = res.apply(
    lambda r: real_direction(r["last_official_price"], r["actual_price_3d"], 0.50), axis=1
)

res["direction_hit_1d"] = res.apply(
    lambda r: "" if r["actual_direction_1d"] == "" else str(r["direction_1d"] == r["actual_direction_1d"]).upper(),
    axis=1
)
res["direction_hit_3d"] = res.apply(
    lambda r: "" if r["actual_direction_3d"] == "" else str(r["direction_3d"] == r["actual_direction_3d"]).upper(),
    axis=1
)

res.insert(0, "comparison_run_datetime", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

cols = [
    "comparison_run_datetime",
    "run_datetime",
    "forecast_family",
    "market",
    "size",
    "quality",
    "last_date",
    "last_official_price",
    "expected_date_1d",
    "predicted_target_1d",
    "actual_price_1d",
    "error_1d",
    "abs_error_1d",
    "direction_1d",
    "actual_direction_1d",
    "direction_hit_1d",
    "expected_date_3d",
    "predicted_target_3d",
    "actual_price_3d",
    "error_3d",
    "abs_error_3d",
    "direction_3d",
    "actual_direction_3d",
    "direction_hit_3d",
    "mae_1d",
    "rmse_1d",
    "mae_3d",
    "rmse_3d",
    "rows_used_1d",
    "rows_used_3d",
]

res = res[cols]
out_path.parent.mkdir(parents=True, exist_ok=True)
res.to_csv(out_path, index=False)

print("ok")
print(out_path)
print(res.to_string(index=False))
