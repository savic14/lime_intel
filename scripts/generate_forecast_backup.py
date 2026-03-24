"""
generate_forecast.py
--------------------
Genera forecast diario de precio + direccion para limon persa BASE.

Input:  data/processed/model_base.csv
Output: data/processed/daily_forecast_base.csv

Modelos:
  - LinearRegression     → predice nivel de precio (1d, 2d, 3d, 7d)
  - GradientBoosting     → predice direccion UP/DOWN/LATERAL

Features validados por experimentos 2018-2026:
  - Precio propio: lags, momentum, volatilidad, posicion en rango
  - Calibres cruzados: cross_p175/230/250 lag1
  - Spreads: spread_200_230, spread_chg_3d
  - Spike calibres chicos: spike_230_lag14, spike_250_lag15
  - Lluvia Veracruz: lluvia_14d_lag6 (-0.296), lluvia_7d_lag7, lluvia_3d_lag7
  - BANXICO: usd_mxn_lag4 (-0.190)
  - Importaciones: import_lag2 (+0.340)
  - Camiones: pharr_sum7d
  - Estacionalidad: month_sin/cos, dow_sin/cos, supply_season

Uso:
    python3 scripts/generate_forecast.py
"""

from pathlib import Path
import math
import warnings
import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.metrics import mean_absolute_error, mean_squared_error, f1_score

warnings.filterwarnings("ignore")

INPUT_PATH  = Path("data/processed/model_base.csv")
OUTPUT_PATH = Path("data/processed/daily_forecast_base.csv")

SIZES            = [175, 200, 230, 250]
QUALITY          = "BASE"
DIRECTION_THRESH = 0.50
CONFIDENCE_MIN   = 0.55

# Features para REGRESOR — precio propio + externos con lags optimos
REGRESSOR_FEATURES = [
    # Precio propio
    "official_price",
    "price_lag_1", "price_lag_3", "price_lag_7",
    "ma_3", "ma_7", "price_change_1d",
    "momentum_3d", "momentum_7d",
    "volatility_7d", "price_position_14d",
    # Externos con lags optimos
    "lluvia_14d_lag6",   # -0.296 mas fuerte
    "lluvia_7d_lag7",    # -0.236
    "usd_mxn_lag4",      # -0.190
    "import_lag2",       # +0.340 mas fuerte
    "pharr_sum7d",
    "spike_230_lag14",   # +0.253
    "spread_200_230",
    # Estacionalidad
    "month_sin", "month_cos", "supply_season",
]

# Features para CLASIFICADOR — sin official_price, con mas señales
CLASSIFIER_FEATURES = [
    # Precio propio
    "price_lag_1", "price_lag_3", "price_lag_7",
    "ma_3", "ma_7", "price_change_1d",
    "momentum_3d", "momentum_7d",
    "volatility_7d", "price_position_14d", "price_accel",
    # Calibres cruzados
    "cross_p175_lag1", "cross_p230_lag1", "cross_p250_lag1",
    # Spreads
    "spread_200_230", "spread_chg_3d", "spread_175_200",
    # Spike calibres chicos con lags optimos
    "spike_230_lag14", "spike_250_lag15",
    "spike_230_lag10", "spike_250_lag10",
    # Lluvia con lags optimos
    "lluvia_14d_lag6",
    "lluvia_7d_lag7",
    "lluvia_3d_lag7",
    "lluvia_lag9",
    # Tipo de cambio
    "usd_mxn_lag4",
    "usd_mxn_chg_7d",
    # Importaciones
    "import_lag2",
    "import_zscore_lag2",
    # Camiones
    "pharr_sum7d",
    # Estacionalidad
    "month_sin", "month_cos",
    "dow_sin", "dow_cos",
    "supply_season",
]

# Features para modelo de 7 DIAS — señales de mediano plazo
REGRESSOR_7D = [
    "official_price",
    "price_lag_1", "price_lag_7",
    "ma_7", "momentum_7d", "volatility_7d",
    "lluvia_14d_lag6", "lluvia_7d_lag7",
    "spike_230_lag14", "spike_250_lag15",
    "usd_mxn_lag4", "usd_mxn_chg_7d",
    "import_lag2",
    "pharr_sum7d",
    "month_sin", "month_cos", "supply_season",
]


def label_direction(delta: float, thresh: float = DIRECTION_THRESH) -> str:
    if delta > thresh:  return "UP"
    if delta < -thresh: return "DOWN"
    return "LATERAL"


def direction_es(label: str) -> str:
    return {"UP": "SUBE", "DOWN": "BAJA", "LATERAL": "LATERAL"}.get(label, label)


def dynamic_threshold(vol) -> float:
    if vol is None or pd.isna(vol) or vol == 0:
        return 0.30
    return round(max(0.20, min(float(vol) * 0.5, 1.50)), 2)


def get_available(s: pd.DataFrame, feats: list) -> list:
    avail   = [f for f in feats if f in s.columns]
    missing = [f for f in feats if f not in s.columns]
    if missing:
        print(f"    ⚠️  Features no disponibles: {missing}")
    return avail


def fit_regressor(s, target_col, feature_cols):
    cols = ["date"] + feature_cols + [target_col]
    data = s[[c for c in cols if c in s.columns]].dropna().copy()
    data = data.sort_values("date").reset_index(drop=True)
    if len(data) < 30:
        return None
    split     = max(1, int(len(data) * 0.8))
    train, test = data.iloc[:split], data.iloc[split:]
    model     = LinearRegression()
    model.fit(train[feature_cols], train[target_col])
    pred_test = model.predict(test[feature_cols])
    mae  = mean_absolute_error(test[target_col], pred_test)
    rmse = math.sqrt(mean_squared_error(test[target_col], pred_test))
    last_row  = data.iloc[-1].copy()
    pred_live = float(model.predict(pd.DataFrame([last_row[feature_cols]]))[0])
    return {
        "pred": pred_live, "mae": float(mae), "rmse": float(rmse),
        "rows_used": int(len(data)), "last_row": last_row,
    }


def fit_classifier(s, target_dir_col, feature_cols):
    if target_dir_col not in s.columns:
        return None
    cols = ["date"] + feature_cols + [target_dir_col]
    data = s[[c for c in cols if c in s.columns]].dropna().copy()
    data = data.sort_values("date").reset_index(drop=True)
    if len(data) < 50 or data[target_dir_col].nunique() < 2:
        return None
    split       = max(1, int(len(data) * 0.8))
    train, test = data.iloc[:split], data.iloc[split:]
    clf = GradientBoostingClassifier(
        n_estimators=300, learning_rate=0.03,
        max_depth=4, min_samples_leaf=15, random_state=42,
    )
    clf.fit(train[feature_cols], train[target_dir_col])
    f1 = None
    if len(test) >= 10:
        f1 = round(float(f1_score(
            test[target_dir_col], clf.predict(test[feature_cols]),
            average="macro", zero_division=0
        )), 4)
    last_row   = data.iloc[-1].copy()
    proba      = clf.predict_proba(pd.DataFrame([last_row[feature_cols]]))[0]
    classes    = clf.classes_
    proba_dict = dict(zip(classes, proba))
    confidence = float(proba.max())
    pred_class = classes[proba.argmax()]
    if confidence < CONFIDENCE_MIN:
        pred_class = "LATERAL"
    return {
        "direction_clf": pred_class,
        "confidence":    round(confidence, 4),
        "prob_up":       round(proba_dict.get("UP",      0.0), 4),
        "prob_down":     round(proba_dict.get("DOWN",    0.0), 4),
        "prob_lateral":  round(proba_dict.get("LATERAL", 0.0), 4),
        "f1_macro":      f1,
        "rows_used_clf": int(len(data)),
    }


def main() -> None:
    if not INPUT_PATH.exists():
        raise SystemExit(f"❌ No existe: {INPUT_PATH}")

    print("Cargando model_base...")
    df = pd.read_csv(INPUT_PATH)
    df["date"] = pd.to_datetime(df["date"], errors="coerce")

    max_date = df["date"].max()
    days_old = (pd.Timestamp.today().normalize() - max_date).days
    status   = "✅" if days_old <= 3 else "⚠️ "
    print(f"{status} Dato más reciente: {max_date.date()} ({days_old} días atrás)")

    rows = []

    for size in SIZES:
        s = df[(df["size"] == size) & (df["quality"] == QUALITY)].copy()
        s = s.sort_values("date").reset_index(drop=True)
        print(f"\n── {size} BASE ({len(s)} filas) ──")

        reg_f = get_available(s, REGRESSOR_FEATURES)
        clf_f = get_available(s, CLASSIFIER_FEATURES)
        r7_f  = get_available(s, REGRESSOR_7D)

        # Regresores
        r1 = fit_regressor(s, "target_1d", reg_f)
        r2 = fit_regressor(s, "target_2d", reg_f)
        r3 = fit_regressor(s, "target_3d", reg_f)
        r7 = fit_regressor(s, "target_7d", r7_f)

        if r1 is None:
            print("  ⚠️  Sin datos suficientes")
            continue

        last_price = float(r1["last_row"]["official_price"])
        last_date  = pd.to_datetime(r1["last_row"]["date"]).strftime("%Y-%m-%d")

        vol  = s["volatility_7d"].dropna().iloc[-1] if "volatility_7d" in s.columns and s["volatility_7d"].notna().any() else None
        thr1 = dynamic_threshold(vol)
        thr2 = round(thr1 * 1.4, 2)
        thr3 = round(thr1 * 1.8, 2)
        thr7 = round(thr1 * 3.0, 2)

        def dir_reg(pred, thr):
            d = pred - last_price
            if d > thr:  return "SUBE"
            if d < -thr: return "BAJA"
            return "LATERAL"

        # Clasificadores
        c1 = fit_classifier(s, "direction_target_1d", clf_f)
        c7 = fit_classifier(s, "direction_target_7d", clf_f) if "direction_target_7d" in s.columns else None

        print(f"  Precio:       {last_price:.2f}")
        print(f"  Pred 1D:      {r1['pred']:.2f}  MAE={r1['mae']:.4f}")
        print(f"  Dir regresor: {dir_reg(r1['pred'], thr1)}")
        if c1:
            print(f"  Dir clasif:   {c1['direction_clf']}  "
                  f"(conf={c1['confidence']:.2f}  F1={c1['f1_macro']})")
            print(f"  P UP/DOWN/LAT: {c1['prob_up']:.2f} / "
                  f"{c1['prob_down']:.2f} / {c1['prob_lateral']:.2f}")
        if r7:
            print(f"  Pred 7D:      {r7['pred']:.2f}  MAE={r7['mae']:.4f}  "
                  f"Dir={dir_reg(r7['pred'], thr7)}")

        rows.append({
            "run_datetime":          pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S"),
            "forecast_family":       "BASE_MULTI_SIZE_V4",
            "market":                "US_MCALLEN",
            "size":                  int(size),
            "quality":               QUALITY,
            "last_date":             last_date,
            "last_official_price":   round(last_price, 4),
            # 1D regresor
            "predicted_target_1d":   round(r1["pred"], 4),
            "direction_1d":          dir_reg(r1["pred"], thr1),
            "mae_1d":                round(r1["mae"], 4),
            "rmse_1d":               round(r1["rmse"], 4),
            "rows_used_1d":          r1["rows_used"],
            "threshold_1d":          thr1,
            # 1D clasificador
            "direction_clf_1d":      c1["direction_clf"]              if c1 else "",
            "direction_clf_1d_es":   direction_es(c1["direction_clf"]) if c1 else "",
            "confidence_clf_1d":     c1["confidence"]                 if c1 else "",
            "prob_up_1d":            c1["prob_up"]                    if c1 else "",
            "prob_down_1d":          c1["prob_down"]                  if c1 else "",
            "f1_macro_1d":           c1["f1_macro"]                   if c1 else "",
            # 2D
            "predicted_target_2d":   round(r2["pred"], 4)             if r2 else "",
            "direction_2d":          dir_reg(r2["pred"], thr2)        if r2 else "",
            "mae_2d":                round(r2["mae"], 4)              if r2 else "",
            "rmse_2d":               round(r2["rmse"], 4)             if r2 else "",
            # 3D
            "predicted_target_3d":   round(r3["pred"], 4)             if r3 else "",
            "direction_3d":          dir_reg(r3["pred"], thr3)        if r3 else "",
            "mae_3d":                round(r3["mae"], 4)              if r3 else "",
            "rmse_3d":               round(r3["rmse"], 4)             if r3 else "",
            # 7D — nuevo horizonte
            "predicted_target_7d":   round(r7["pred"], 4)             if r7 else "",
            "direction_7d":          dir_reg(r7["pred"], thr7)        if r7 else "",
            "mae_7d":                round(r7["mae"], 4)              if r7 else "",
            "rmse_7d":               round(r7["rmse"], 4)             if r7 else "",
            # 7D clasificador
            "direction_clf_7d":      c7["direction_clf"]              if c7 else "",
            "direction_clf_7d_es":   direction_es(c7["direction_clf"]) if c7 else "",
            "confidence_clf_7d":     c7["confidence"]                 if c7 else "",
            "f1_macro_7d":           c7["f1_macro"]                   if c7 else "",
            # Contexto de señales externas del ultimo dia
            "lluvia_14d_lag6":       round(float(s["lluvia_14d_lag6"].dropna().iloc[-1]), 2) if "lluvia_14d_lag6" in s.columns and s["lluvia_14d_lag6"].notna().any() else "",
            "usd_mxn":               round(float(s["usd_mxn"].dropna().iloc[-1]), 4)         if "usd_mxn"        in s.columns and s["usd_mxn"].notna().any()        else "",
            "spike_230_lag14":       round(float(s["spike_230_lag14"].dropna().iloc[-1]), 2) if "spike_230_lag14" in s.columns and s["spike_230_lag14"].notna().any() else "",
        })

    out = pd.DataFrame(rows).sort_values("size").reset_index(drop=True)
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(OUTPUT_PATH, index=False)

    print("\n" + "═" * 65)
    print("FORECAST GENERADO — V4")
    print("═" * 65)
    cols_show = [
        "size", "last_official_price",
        "predicted_target_1d", "direction_1d",
        "direction_clf_1d_es", "confidence_clf_1d",
        "predicted_target_7d", "direction_7d",
        "mae_1d",
    ]
    print(out[[c for c in cols_show if c in out.columns]].to_string(index=False))
    print(f"\n✅ Guardado en: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
