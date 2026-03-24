import pandas as pd
import streamlit as st
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]

st.set_page_config(page_title="Lime Intelligence Dashboard", layout="wide")
st.title("Lime Intelligence Dashboard")

forecast_path = PROJECT_ROOT / "data/processed/daily_forecast_base.csv"
scorecard_path = PROJECT_ROOT / "data/processed/daily_forecast_scorecard.csv"

forecast_cols = [
    "size",
    "quality",
    "last_official_price",
    "predicted_target_1d",
    "direction_1d",
    "predicted_target_2d",
    "direction_2d",
    "predicted_target_3d",
    "direction_3d",
    "mae_1d",
]

score_cols = [
    "rank_del_dia",
    "size",
    "pred_1d",
    "real_1d",
    "abs_error_1d",
    "pred_dir_1d",
    "real_dir_1d",
    "hit_1d",
]

if forecast_path.exists():
    forecast_df = pd.read_csv(forecast_path).sort_values("size").reset_index(drop=True)
else:
    forecast_df = pd.DataFrame()

if scorecard_path.exists():
    score_df = pd.read_csv(scorecard_path).sort_values("rank_del_dia").reset_index(drop=True)
else:
    score_df = pd.DataFrame()

if not forecast_df.empty:
    last_date_txt = str(forecast_df["last_date"].iloc[0])
    target_1d_txt = (pd.to_datetime(last_date_txt) + pd.Timedelta(days=1)).strftime("%Y-%m-%d")
    target_2d_txt = (pd.to_datetime(last_date_txt) + pd.Timedelta(days=2)).strftime("%Y-%m-%d")
    target_3d_txt = (pd.to_datetime(last_date_txt) + pd.Timedelta(days=3)).strftime("%Y-%m-%d")
    st.caption(
        f"Último precio usado: {last_date_txt} | "
        f"Pronóstico 1D para: {target_1d_txt} | "
        f"Pronóstico 2D para: {target_2d_txt} | "
        f"Pronóstico 3D para: {target_3d_txt}"
    )

st.subheader("Resumen ejecutivo")

c1, c2, c3 = st.columns(3)

if not score_df.empty:
    best_row = score_df.iloc[0]
    worst_row = score_df.sort_values("abs_error_1d", ascending=False).iloc[0]
    hits = int(score_df["hit_1d"].astype(str).str.upper().eq("TRUE").sum())

    c1.metric("Mejor calibre del día", f'{int(best_row["size"])} {best_row["quality"]}')
    c2.metric("Aciertos 1D", f"{hits}/{len(score_df)}")
    c3.metric("Mayor error 1D", f'{int(worst_row["size"])} | {worst_row["abs_error_1d"]:.3f}')
else:
    c1.metric("Mejor calibre del día", "-")
    c2.metric("Aciertos 1D", "-")
    c3.metric("Mayor error 1D", "-")

st.subheader("Forecast BASE Multi-Size")
if not forecast_df.empty:
    st.dataframe(forecast_df[forecast_cols], use_container_width=True, hide_index=True)
else:
    st.info("No existe daily_forecast_base.csv")

st.subheader("Scorecard del día")
if not score_df.empty:
    st.dataframe(score_df[score_cols], use_container_width=True, hide_index=True)
else:
    st.info("No existe daily_forecast_scorecard.csv")
