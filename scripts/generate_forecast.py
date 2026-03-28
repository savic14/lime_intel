"""
generate_forecast.py V6 — Modelo Delta + Cadena de calibres
-------------------------------------------------------------
- Predice CAMBIO de precio (delta), no precio absoluto
- Precio predicho = Precio actual + Delta esperado
- Calibres sin datos recientes se estiman desde calibre adyacente
  usando spreads historicos dinamicos segun nivel de precio
"""
from pathlib import Path
import math, warnings
import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.metrics import mean_absolute_error, mean_squared_error, f1_score

warnings.filterwarnings("ignore")

INPUT_PATH  = Path("data/processed/model_base.csv")
OUTPUT_PATH = Path("data/processed/daily_forecast_base.csv")

SIZES          = [110, 150, 175, 200, 230, 250]
QUALITY        = "BASE"
CONFIDENCE_MIN = 0.55

# Spreads historicos entre calibres adyacentes (2018-2026)
# Cuando precio alto (>$33) los spreads se amplian ligeramente
SPREADS = {
    (110, 150): {"base": 0.09, "alto": 0.09},
    (150, 175): {"base": 0.40, "alto": 0.55},
    (175, 200): {"base": 1.10, "alto": 1.40},
    (200, 230): {"base": 1.76, "alto": 2.50},
    (230, 250): {"base": 2.07, "alto": 2.30},
}

DELTA_FEATURES = [
    "price_change_1d",
    "price_lag_1", "price_lag_3", "price_lag_7",
    "ma_3", "ma_7",
    "momentum_3d", "momentum_7d",
    "volatility_7d", "price_position_14d",
    "lluvia_14d_lag6", "lluvia_7d_lag7", "lluvia_3d_lag7",
    "usd_mxn_lag4", "usd_mxn_chg_7d",
    "import_lag2", "import_zscore_lag2",
    "pharr_sum7d",
    "spike_230_lag14", "spike_250_lag15",
    "spread_200_230", "spread_chg_3d",
    "month_sin", "month_cos", "supply_season",
    "dow_sin", "dow_cos",
]

CLASSIFIER_FEATURES = [
    "price_change_1d",
    "price_lag_1", "price_lag_3", "price_lag_7",
    "ma_3", "ma_7",
    "momentum_3d", "momentum_7d",
    "volatility_7d", "price_position_14d",
    "cross_p175_lag1", "cross_p230_lag1", "cross_p250_lag1",
    "spread_200_230", "spread_chg_3d", "spread_175_200",
    "spike_230_lag14", "spike_250_lag15",
    "spike_230_lag10", "spike_250_lag10",
    "lluvia_14d_lag6", "lluvia_7d_lag7", "lluvia_3d_lag7", "lluvia_lag9",
    "usd_mxn_lag4", "usd_mxn_chg_7d",
    "import_lag2", "import_zscore_lag2",
    "pharr_sum7d",
    "month_sin", "month_cos", "dow_sin", "dow_cos", "supply_season",
]


def dir_label(d, thresh=0.50):
    if d > thresh:  return "UP"
    if d < -thresh: return "DOWN"
    return "LATERAL"


def dir_es(label):
    return {"UP": "SUBE", "DOWN": "BAJA", "LATERAL": "ESTABLE"}.get(str(label), "ESTABLE")


def avail(s, feats):
    seen = set()
    return [f for f in feats if f in s.columns and not (f in seen or seen.add(f))]


def get_last_price(s, feats):
    """
    Ultima fila con features completos para prediccion live.
    ffill de features con lag largo para no perder el precio actual
    cuando movement o importaciones tienen retraso de ~10 dias.
    """
    s2 = s[feats + ["date", "official_price"]].copy()
    lag_feats = [f for f in feats if any(x in f for x in
                 ["pharr", "import", "lluvia", "usd_mxn", "spike", "spread"])]
    s2[lag_feats] = s2[lag_feats].ffill(limit=15)
    return s2.dropna().reset_index(drop=True).iloc[-1]


def get_spread(size_high, size_low, base_price):
    """Spread dinamico entre calibres segun nivel de precio actual"""
    key = (size_low, size_high) if size_low < size_high else (size_high, size_low)
    if key not in SPREADS:
        return 1.0
    sp = SPREADS[key]
    return sp["alto"] if base_price > 33 else sp["base"]


def fit_delta_regressor(s, horizon_days, feature_cols):
    s_sorted = s.sort_values("date").reset_index(drop=True)
    target_col = f"delta_{horizon_days}d_tmp"
    s_sorted[target_col] = s_sorted["official_price"].shift(-horizon_days) - s_sorted["official_price"]

    data = s_sorted[feature_cols + [target_col, "official_price", "date"]].dropna().sort_values("date").reset_index(drop=True)
    if len(data) < 30: return None

    split = max(1, int(len(data) * 0.8))
    train, test = data.iloc[:split], data.iloc[split:]

    model = Ridge(alpha=1.0)
    model.fit(train[feature_cols], train[target_col])

    pred_delta_test = model.predict(test[feature_cols])
    pred_price_test = test["official_price"].values + pred_delta_test
    real_price_test = test["official_price"].values + test[target_col].values
    mae  = mean_absolute_error(real_price_test, pred_price_test)
    rmse = math.sqrt(mean_squared_error(real_price_test, pred_price_test))

    last       = get_last_price(s_sorted, feature_cols)
    last_price = float(last["official_price"])
    pred_delta = float(model.predict(np.array(last[feature_cols].values, dtype=float).reshape(1, -1))[0])
    pred_price = last_price + pred_delta

    return {
        "pred":       pred_price,
        "delta":      pred_delta,
        "mae":        float(mae),
        "rmse":       float(rmse),
        "rows":       int(len(data)),
        "last_price": last_price,
        "last_date":  pd.to_datetime(last["date"]).strftime("%Y-%m-%d"),
    }


def fit_classifier(s, feature_cols):
    if "direction_target_1d" not in s.columns: return None
    s_sorted = s.sort_values("date").reset_index(drop=True)
    data = s_sorted[feature_cols + ["direction_target_1d", "date"]].dropna().sort_values("date").reset_index(drop=True)
    if len(data) < 50 or data["direction_target_1d"].nunique() < 2: return None

    split = max(1, int(len(data) * 0.8))
    train, test = data.iloc[:split], data.iloc[split:]

    clf = GradientBoostingClassifier(
        n_estimators=300, learning_rate=0.03,
        max_depth=4, min_samples_leaf=15, random_state=42,
    )
    clf.fit(train[feature_cols], train["direction_target_1d"])

    f1 = None
    if len(test) >= 10:
        f1 = round(float(f1_score(test["direction_target_1d"], clf.predict(test[feature_cols]),
                                   average="macro", zero_division=0)), 4)

    last     = s_sorted[feature_cols + ["date"]].copy()
    lag_f    = [f for f in feature_cols if any(x in f for x in ["pharr","import","lluvia","usd_mxn","spike","spread"])]
    last[lag_f] = last[lag_f].ffill(limit=15)
    last     = last.dropna().reset_index(drop=True).iloc[-1]

    proba    = clf.predict_proba(np.array(last[feature_cols].values, dtype=float).reshape(1, -1))[0]
    classes  = clf.classes_
    pd_      = dict(zip(classes, proba))
    conf     = float(proba.max())
    pred_cls = classes[proba.argmax()] if conf >= CONFIDENCE_MIN else "LATERAL"

    return {
        "dir":  pred_cls,
        "conf": round(conf, 4),
        "up":   round(pd_.get("UP",      0.0), 4),
        "down": round(pd_.get("DOWN",    0.0), 4),
        "lat":  round(pd_.get("LATERAL", 0.0), 4),
        "f1":   f1,
    }


def dir_thr(delta, thresh):
    if delta > thresh:  return "SUBE"
    if delta < -thresh: return "BAJA"
    return "ESTABLE"


def get_last_val(s, col):
    try: return round(float(s[col].dropna().iloc[-1]), 4)
    except: return ""


def main():
    if not INPUT_PATH.exists():
        raise SystemExit(f"No existe {INPUT_PATH}")

    print("Cargando model_base...")
    df = pd.read_csv(INPUT_PATH)
    df["date"] = pd.to_datetime(df["date"], errors="coerce")

    max_date = df["date"].max()
    days_old = (pd.Timestamp.today().normalize() - max_date).days
    print(f"{'OK' if days_old<=3 else 'AVISO'} Ultimo dato: {max_date.date()} ({days_old}d)")

    rows = []
    # Guardar predicciones por size para la cadena
    preds_by_size = {}

    for size in SIZES:
        s = df[(df["size"]==size) & (df["quality"]==QUALITY)].sort_values("date").reset_index(drop=True)
        print(f"\n-- {size} BASE ({len(s)} filas)")
        if len(s) < 30: continue

        df_ = avail(s, DELTA_FEATURES)
        cf_ = avail(s, CLASSIFIER_FEATURES)

        r1 = fit_delta_regressor(s, 1, df_)
        r2 = fit_delta_regressor(s, 2, df_)
        r3 = fit_delta_regressor(s, 3, df_)
        r7 = fit_delta_regressor(s, 7, df_)
        c1 = fit_classifier(s, cf_)

        if r1 is None: continue

        lp  = r1["last_price"]
        ld  = r1["last_date"]
        mae1 = r1["mae"]

        vol = s["volatility_7d"].dropna().iloc[-1] if "volatility_7d" in s.columns and s["volatility_7d"].notna().any() else 1.0
        t1  = round(max(0.20, min(float(vol)*0.5, 1.50)), 2)
        t3  = round(t1*1.8, 2)
        t7  = round(t1*3.0, 2)

        print(f"  Precio ({ld}): ${lp:.2f}")
        print(f"  Delta 1d: {r1['delta']:+.2f} → pred ${r1['pred']:.2f}  Dir={dir_thr(r1['delta'],t1)}  MAE=${mae1:.4f}")
        if c1:
            print(f"  Clasif: {dir_es(c1['dir'])} conf={c1['conf']:.0%}  F1={c1['f1']}")
        if r7:
            print(f"  Delta 7d: {r7['delta']:+.2f} → pred ${r7['pred']:.2f}  Dir={dir_thr(r7['delta'],t7)}")

        preds_by_size[size] = {
            "pred_1d": r1["pred"], "delta_1d": r1["delta"],
            "last_price": lp, "last_date": ld,
            "estimated": False,
        }

        rows.append({
            "run_datetime":        pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S"),
            "forecast_family":     "DELTA_V6",
            "market":              "US_MCALLEN",
            "size":                int(size),
            "quality":             QUALITY,
            "last_date":           ld,
            "last_official_price": round(lp, 4),
            "estimated_price":     False,
            "predicted_target_1d": round(r1["pred"], 4),
            "predicted_delta_1d":  round(r1["delta"], 4),
            "direction_1d":        dir_thr(r1["delta"], t1),
            "mae_1d":              round(mae1, 4),
            "rmse_1d":             round(r1["rmse"], 4),
            "threshold_1d":        t1,
            "direction_clf_1d":    c1["dir"]           if c1 else "",
            "direction_clf_1d_es": dir_es(c1["dir"])   if c1 else "",
            "confidence_clf_1d":   c1["conf"]          if c1 else "",
            "prob_up_1d":          c1["up"]             if c1 else "",
            "prob_down_1d":        c1["down"]           if c1 else "",
            "f1_macro_1d":         c1["f1"]             if c1 else "",
            "predicted_target_2d": round(r2["pred"], 4) if r2 else "",
            "predicted_delta_2d":  round(r2["delta"], 4) if r2 else "",
            "direction_2d":        dir_thr(r2["delta"], t3) if r2 else "",
            "mae_2d":              round(r2["mae"], 4) if r2 else "",
            "predicted_target_3d": round(r3["pred"], 4) if r3 else "",
            "predicted_delta_3d":  round(r3["delta"], 4) if r3 else "",
            "direction_3d":        dir_thr(r3["delta"], t3) if r3 else "",
            "mae_3d":              round(r3["mae"], 4) if r3 else "",
            "predicted_target_7d": round(r7["pred"], 4) if r7 else "",
            "predicted_delta_7d":  round(r7["delta"], 4) if r7 else "",
            "direction_7d":        dir_thr(r7["delta"], t7) if r7 else "",
            "mae_7d":              round(r7["mae"], 4) if r7 else "",
            "lluvia_14d_lag6":     get_last_val(s, "lluvia_14d_lag6"),
            "usd_mxn":             get_last_val(s, "usd_mxn"),
            "spike_230_lag14":     get_last_val(s, "spike_230_lag14"),
            "import_lag2":         get_last_val(s, "import_lag2"),
        })

    # ── Cadena de calibres: estimar desde adyacente si datos viejos ───────────
    print("\n-- Cadena de calibres (estimacion desde adyacente) --")

    # Determinar fecha mas reciente disponible
    dates_by_size = {size: preds_by_size[size]["last_date"] for size in preds_by_size}
    max_avail_date = max(dates_by_size.values())

    out = pd.DataFrame(rows)

    # Cadena descendente: 175 → 150 → 110
    for size_high, size_low in [(175, 150), (150, 110)]:
        if size_high not in preds_by_size or size_low not in preds_by_size:
            continue

        date_high = preds_by_size[size_high]["last_date"]
        date_low  = preds_by_size[size_low]["last_date"]

        if date_low < date_high:
            # El calibre bajo tiene datos mas viejos — estimar desde el alto
            pred_high  = preds_by_size[size_high]["pred_1d"]
            price_high = preds_by_size[size_high]["last_price"]
            spread     = get_spread(size_high, size_low, price_high)

            # Precio estimado actual = precio_high + spread
            price_est  = price_high + spread
            # Prediccion = pred_high + spread (mismo delta, diferente base)
            pred_est   = pred_high + spread
            delta_est  = pred_est - price_est

            # Actualizar en out
            mask = out["size"] == size_low
            out.loc[mask, "last_official_price"] = round(price_est, 4)
            out.loc[mask, "last_date"]           = date_high + " (est.)"
            out.loc[mask, "predicted_target_1d"] = round(pred_est, 4)
            out.loc[mask, "predicted_delta_1d"]  = round(delta_est, 4)
            out.loc[mask, "estimated_price"]     = True

            # Para 7d tambien
            if size_high in preds_by_size and preds_by_size[size_high].get("pred_1d"):
                if not out[out["size"]==size_high]["predicted_target_7d"].iloc[0] == "":
                    pred7_high = float(out[out["size"]==size_high]["predicted_target_7d"].iloc[0]) if out[out["size"]==size_high]["predicted_target_7d"].iloc[0] != "" else pred_high
                    pred7_est  = pred7_high + spread
                    out.loc[mask, "predicted_target_7d"] = round(pred7_est, 4)

            # Actualizar preds_by_size para la siguiente iteracion en cadena
            preds_by_size[size_low] = {
                "pred_1d": pred_est,
                "delta_1d": delta_est,
                "last_price": price_est,
                "last_date": date_high,
                "estimated": True,
            }
            print(f"  {size_low} estimado desde {size_high}: precio=${price_est:.2f}  pred=${pred_est:.2f}  spread={spread:+.2f}")

    out = out.sort_values("size").reset_index(drop=True)
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(OUTPUT_PATH, index=False)

    print("\n" + "="*65)
    print("FORECAST V6 — MODELO DELTA + CADENA DE CALIBRES")
    print("="*65)
    cols = ["size","last_date","last_official_price","estimated_price",
            "predicted_delta_1d","predicted_target_1d","direction_1d",
            "direction_clf_1d_es","confidence_clf_1d","mae_1d"]
    print(out[[c for c in cols if c in out.columns]].to_string(index=False))
    print(f"\nGuardado: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
