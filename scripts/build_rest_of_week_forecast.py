from pathlib import Path
import pandas as pd

pred1_path = Path("data/processed/prediction_target_1d.csv")
out_path = Path("data/processed/rest_of_week_forecast.csv")

if not pred1_path.exists():
    raise SystemExit("No existe prediction_target_1d.csv")

p1 = pd.read_csv(pred1_path).iloc[0]

base_date = pd.to_datetime(p1["last_date"])
base_price = float(p1["last_official_price"])
pred_1d = float(p1["predicted_target_1d"])

# Solo hasta el lunes de la semana actual (ciclo martes->lunes)
days_ahead = 7 - base_date.weekday()  # Monday=0 ... Sunday=6
future_dates = [base_date + pd.Timedelta(days=i) for i in range(1, days_ahead + 1)]

forecast_rows = []
for i, dt in enumerate(future_dates, start=1):
    # Por ahora, usar solo el pronóstico 1d para el resto inmediato de la semana
    val = pred_1d if i == 1 else pred_1d

    prev_ref = base_price if i == 1 else forecast_rows[-1]["forecast_price"]
    if val > prev_ref + 0.25:
        direction = "SUBE"
    elif val < prev_ref - 0.25:
        direction = "BAJA"
    else:
        direction = "LATERAL"

    forecast_rows.append({
        "forecast_date": dt.strftime("%Y-%m-%d"),
        "day_name": dt.strftime("%A"),
        "forecast_price": round(val, 4),
        "direction": direction,
    })

out = pd.DataFrame(forecast_rows)
out_path.parent.mkdir(parents=True, exist_ok=True)
out.to_csv(out_path, index=False)

print("ok")
print(out_path)
