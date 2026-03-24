import pandas as pd
from pathlib import Path

src = Path("data/processed/daily_forecast_scorecard.csv")
hist = Path("data/processed/scorecard_history.csv")

if not src.exists():
    raise SystemExit(f"No existe {src}")

df = pd.read_csv(src)

# Si existe la corrida, usa ese timestamp; si no, deja vacío
cmp_path = Path("data/processed/forecast_vs_actual_base.csv")
if cmp_path.exists():
    cmp = pd.read_csv(cmp_path)
    if "comparison_run_datetime" in cmp.columns:
        run_ts = str(cmp["comparison_run_datetime"].iloc[0])
        df.insert(0, "comparison_run_datetime", run_ts)

if hist.exists():
    old = pd.read_csv(hist)
    out = pd.concat([old, df], ignore_index=True)
    out = out.drop_duplicates(
        subset=[c for c in ["comparison_run_datetime", "size", "quality", "pred_1d", "real_1d"] if c in out.columns],
        keep="last"
    )
else:    out = df.copy()

hist.parent.mkdir(parents=True, exist_ok=True)
out.to_csv(hist, index=False)

print("ok")
print(hist)
print(out.tail(20).to_string(index=False))
