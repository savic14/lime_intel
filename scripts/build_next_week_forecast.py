from pathlib import Path
import pandas as pd

pred1_path = Path("data/processed/prediction_target_1d.csv")
pred3_path = Path("data/processed/prediction_target_3d.csv")
out_path = Path("data/processed/next_week_forecast.csv")

if not pred1_path.exists():
    raise SystemExit("No existe prediction_target_1d.csv")
if not pred3_path.exists():
    raise SystemExit("No existe prediction_target_3d.csv")

p1 = pd.read_csv(pred1_path).iloc[0]
p3 = pd.read_csv(pred3_path).iloc[0]

base_date = pd.to_datetime(p1["last_date"])
last_price = float(p1["last_official_price"])
pred_1d = float(p1["predicted_target_1d"])
pred_3d = float(p3["predicted_target_3d"])

# Próximo martes después de la fecha base
days_until_next_tuesday = (1 - base_date.weekday()) % 7
start_date = base_date + pd.Timedelta(days=days_until_next_tuesday)
future_dates = [start_date + pd.Timedelta(days=i) for i in range(7)]

slope_13 = (pred_3d - pred_1d) / 2.0
max_daily_move = 1.5
slope_13 = max(-max_daily_move, min(max_daily_move, slope_13))

forecast_rows = []
for i, dt in enumerate(future_dates, start=1):
    if i == 1:
        val = pred_1d + slope_13
    elif i == 2:
        val = pred_3d
    else:
        val = forecast_rows[-1]["forecast_price"] + slope_13

    prev_ref = last_price if i == 1 else forecast_rows[-1]["forecast_price"]

    if val > prev_ref + 0.25:
        direction = "SUBE"
    elif val < prev_ref - 0.25:
        direction = "BAJA"
    else:
        direction = "LATERAL"

    forecast_rows.append({
        "forecast_date": dt.strftime("%Y-%m-%d"),
        "day_name": dt.strftime("%A"),
        "forecast_price": round(float(val), 4),
        "direction": direction,
    })

out = pd.DataFrame(forecast_rows)
out_path.parent.mkdir(parents=True, exist_ok=True)
out.to_csv(out_path, index=False)

print("ok")
print(out_path)
