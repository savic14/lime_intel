"""
build_model_base.py
-------------------
Construye el dataset maestro para el modelo de forecast de limon persa.

Features validados por experimentos sobre historia 2018-2026:

PRECIO PROPIO (autoregresivos):
  price_lag_1/3/7, ma_3/7/14, price_change_1d
  momentum_3d/7d, volatility_7d/14d, price_position_14d
  price_accel

CALIBRES CRUZADOS (correlacion 0.95+):
  Todos los sizes BASE como features cruzados con lag 1

SPREADS (señal de tension de mercado):
  spread_200_230 — feature importance top 5
  spread_chg_3d  — cambio del spread en 3 dias

SPIKE CALIBRES CHICOS (señal de corte acelerado):
  spike_230_lag14 — lag optimo confirmado: 14 dias (+0.253)
  spike_250_lag15 — lag optimo confirmado: 15 dias (+0.235)

LLUVIA VERACRUZ — NASA POWER:
  lluvia_14d_lag6 — lag optimo: 6 dias (-0.296) MAS FUERTE
  lluvia_7d_lag7  — lag optimo: 7 dias (-0.236)
  lluvia_3d_lag7  — feature importance top 6

TIPO DE CAMBIO — BANXICO:
  usd_mxn_lag4    — lag optimo: 4 dias (-0.190)
  usd_mxn_chg_7d  — cambio en 7 dias

IMPORTACIONES (Colombia+Peru):
  import_lag2     — lag optimo: 2 dias (+0.340) MAS FUERTE
  import_zscore   — señal relativa vs media 30d

CAMIONES PHARR:
  pharr_lag1      — feature importance top 3
  pharr_sum7d     — acumulado 7 dias

ESTACIONALIDAD:
  month_sin/cos, dow_sin/cos, supply_season

FIXES METODOLOGICOS:
  - Lags de movement calculados en tabla move ANTES del merge
  - Forward-fill del movement (evita NaN en fines de semana)
  - Calibres cruzados con ffill limit=3
  - Features externos con ffill limit=5
"""

from pathlib import Path
import numpy as np
import pandas as pd

# ── Rutas ──────────────────────────────────────────────────────────────────────
PRICE_PATH  = Path("data/processed/shipping_point_core.csv")
MOVE_PATH   = Path("data/processed/movement_core.csv")
FX_PATH     = Path("data/processed/usd_mxn_historico.csv")
RAIN_PATH   = Path("data/processed/lluvia_veracruz_historico.csv")
IMP_PATH    = Path("data/processed/importaciones_historico.csv")
OUTPUT_PATH = Path("data/processed/model_base.csv")

GROUP_COLS       = ["market", "size", "quality"]
DIRECTION_THRESH = 0.50


# ── 1. Movement: preparar ANTES del merge ─────────────────────────────────────

def prepare_movement(move: pd.DataFrame) -> pd.DataFrame:
    move = move.sort_values("date").reset_index(drop=True)

    vol_cols = [c for c in [
        "total_seedless_lb", "pharr_seedless_lb", "mx_seedless_lb",
        "truck_seedless_lb", "colombia_seedless_lb", "peru_seedless_lb",
        "boat_seedless_lb", "organic_seedless_lb",
    ] if c in move.columns]
    move[vol_cols] = move[vol_cols].ffill(limit=5)

    # Lags de movement — calculados sobre serie temporal de mercado (sin groupby de size)
    move["total_movement_lag_1"] = move["total_seedless_lb"].shift(1)
    move["pharr_lag_1"]          = move["pharr_seedless_lb"].shift(1)
    move["movement_change_1d"]   = move["total_seedless_lb"] - move["total_movement_lag_1"]

    # Pharr acumulado — feature importance top 3
    move["pharr_sum7d"]  = move["pharr_seedless_lb"].rolling(7).sum().shift(1)
    move["pharr_sum14d"] = move["pharr_seedless_lb"].rolling(14).sum().shift(1)

    # Zscore del movimiento vs las ultimas 2 semanas
    mv_mean = move["total_seedless_lb"].shift(1).rolling(14, min_periods=5).mean()
    mv_std  = move["total_seedless_lb"].shift(1).rolling(14, min_periods=5).std()
    move["movement_zscore_14d"] = (move["total_movement_lag_1"] - mv_mean) / (mv_std + 1e-6)

    cols_export = [
        "date",
        "total_seedless_lb", "pharr_seedless_lb", "mx_seedless_lb",
        "total_movement_lag_1", "pharr_lag_1", "movement_change_1d",
        "pharr_sum7d", "pharr_sum14d", "movement_zscore_14d",
    ]
    return move[[c for c in cols_export if c in move.columns]]


# ── 2. Tipo de cambio BANXICO ─────────────────────────────────────────────────

def prepare_fx(fx: pd.DataFrame) -> pd.DataFrame:
    fx = fx.sort_values("date").reset_index(drop=True)
    fx["usd_mxn"] = fx["usd_mxn"].ffill(limit=5)

    # Lag optimo confirmado: 4 dias (-0.190)
    fx["usd_mxn_lag4"]    = fx["usd_mxn"].shift(4)
    fx["usd_mxn_chg_3d"]  = fx["usd_mxn"] - fx["usd_mxn"].shift(3)
    fx["usd_mxn_chg_7d"]  = fx["usd_mxn"] - fx["usd_mxn"].shift(7)
    fx["peso_debil_7d"]   = (fx["usd_mxn"] > fx["usd_mxn"].rolling(7).mean()).astype(int)

    cols = ["date", "usd_mxn", "usd_mxn_lag4", "usd_mxn_chg_3d",
            "usd_mxn_chg_7d", "peso_debil_7d"]
    return fx[[c for c in cols if c in fx.columns]]


# ── 3. Lluvia NASA POWER ──────────────────────────────────────────────────────

def prepare_rain(rain: pd.DataFrame) -> pd.DataFrame:
    rain = rain.sort_values("date").reset_index(drop=True)

    # Asegurar columnas rolling si no existen
    if "lluvia_3d" not in rain.columns:
        rain["lluvia_3d"]  = rain["lluvia_mm"].rolling(3).sum()
    if "lluvia_7d" not in rain.columns:
        rain["lluvia_7d"]  = rain["lluvia_mm"].rolling(7).sum()
    if "lluvia_14d" not in rain.columns:
        rain["lluvia_14d"] = rain["lluvia_mm"].rolling(14).sum()

    # Lags optimos confirmados por experimento
    rain["lluvia_14d_lag6"] = rain["lluvia_14d"].shift(6)   # -0.296 MAS FUERTE
    rain["lluvia_7d_lag7"]  = rain["lluvia_7d"].shift(7)    # -0.236
    rain["lluvia_3d_lag7"]  = rain["lluvia_3d"].shift(7)    # feature importance top 6
    rain["lluvia_lag9"]     = rain["lluvia_mm"].shift(9)    # lag optimo lluvia diaria

    # Dias consecutivos con lluvia (proxy de interrupcion de corte)
    consec = []
    count  = 0
    for v in rain["lluvia_mm"]:
        count = count + 1 if v > 5 else 0
        consec.append(count)
    rain["dias_lluvia_consec"]     = consec
    rain["dias_consec_lag5"]       = rain["dias_lluvia_consec"].shift(5)
    rain["evento_lluvia_lag7"]     = (rain["lluvia_mm"] > 20).astype(int).shift(7)

    cols = [
        "date", "lluvia_mm", "lluvia_3d", "lluvia_7d", "lluvia_14d",
        "lluvia_14d_lag6", "lluvia_7d_lag7", "lluvia_3d_lag7", "lluvia_lag9",
        "dias_lluvia_consec", "dias_consec_lag5", "evento_lluvia_lag7",
    ]
    return rain[[c for c in cols if c in rain.columns]]


# ── 4. Importaciones Colombia+Peru ────────────────────────────────────────────

def prepare_importaciones(imp: pd.DataFrame) -> pd.DataFrame:
    imp = imp.sort_values("date").reset_index(drop=True)

    if "import_total" not in imp.columns:
        col_co = "colombia_seedless_lb" if "colombia_seedless_lb" in imp.columns else None
        col_pe = "peru_seedless_lb"     if "peru_seedless_lb"     in imp.columns else None
        if col_co and col_pe:
            imp["import_total"] = imp[col_co].fillna(0) + imp[col_pe].fillna(0)

    if "import_total" in imp.columns:
        imp["import_total"] = imp["import_total"].ffill(limit=5)

        # Lag optimo confirmado: 2 dias (+0.340 — el mas fuerte de todos)
        imp["import_lag2"]     = imp["import_total"].shift(2)
        imp["import_lag5"]     = imp["import_total"].shift(5)
        imp["import_sum7d"]    = imp["import_total"].rolling(7).sum().shift(1)

        # Zscore vs media 30d (señal relativa)
        imp_mean = imp["import_total"].rolling(30, min_periods=10).mean()
        imp_std  = imp["import_total"].rolling(30, min_periods=10).std()
        imp["import_zscore"] = (imp["import_total"] - imp_mean) / (imp_std + 1e-6)
        imp["import_zscore_lag2"] = imp["import_zscore"].shift(2)

    cols = ["date", "import_total", "import_lag2", "import_lag5",
            "import_sum7d", "import_zscore", "import_zscore_lag2"]
    return imp[[c for c in cols if c in imp.columns]]


# ── 5. Features de precio ─────────────────────────────────────────────────────

def add_price_features(df: pd.DataFrame) -> pd.DataFrame:
    for lag, col in [(1,"price_lag_1"),(3,"price_lag_3"),(7,"price_lag_7")]:
        df[col] = df.groupby(GROUP_COLS)["official_price"].shift(lag)

    for w, col in [(3,"ma_3"),(7,"ma_7"),(14,"ma_14")]:
        df[col] = df.groupby(GROUP_COLS)["official_price"].transform(
            lambda s, w=w: s.shift(1).rolling(w, min_periods=1).mean()
        )

    df["price_change_1d"] = df["official_price"] - df["price_lag_1"]
    df["momentum_3d"]     = df["official_price"] - df["price_lag_3"]
    df["momentum_7d"]     = df["official_price"] - df["price_lag_7"]
    df["price_accel"]     = df["price_change_1d"] - df.groupby(GROUP_COLS)["price_change_1d"].shift(1)

    for w, col in [(7,"volatility_7d"),(14,"volatility_14d")]:
        df[col] = df.groupby(GROUP_COLS)["official_price"].transform(
            lambda s, w=w: s.shift(1).rolling(w, min_periods=3).std()
        )

    roll_min = df.groupby(GROUP_COLS)["official_price"].transform(
        lambda s: s.shift(1).rolling(14, min_periods=5).min()
    )
    roll_max = df.groupby(GROUP_COLS)["official_price"].transform(
        lambda s: s.shift(1).rolling(14, min_periods=5).max()
    )
    df["price_position_14d"] = (df["official_price"] - roll_min) / (roll_max - roll_min + 1e-6)

    return df


# ── 6. Calibres cruzados y spreads ────────────────────────────────────────────

def add_cross_size_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Requiere que df ya tenga el pivot de todos los calibres BASE.
    Se calcula sobre el df completo antes de hacer el groupby.
    """
    # Pivot de precios por fecha (solo BASE)
    base_pivot = (df[df["quality"] == "BASE"]
                  .pivot_table(index="date", columns="size", values="official_price")
                  .reset_index())
    base_pivot.columns = ["date"] + ["cross_p"+str(c) for c in base_pivot.columns[1:]]

    # ffill calibres cruzados (fines de semana)
    for col in [c for c in base_pivot.columns if c.startswith("cross_")]:
        base_pivot[col] = base_pivot[col].ffill(limit=3)

    # Lags de calibres cruzados (lag 1)
    for col in [c for c in base_pivot.columns if c.startswith("cross_")]:
        base_pivot[col+"_lag1"] = base_pivot[col].shift(1)

    # Spreads — feature importance top 5
    if "cross_p200" in base_pivot.columns and "cross_p230" in base_pivot.columns:
        base_pivot["spread_200_230"] = base_pivot["cross_p200"].shift(1) - base_pivot["cross_p230"].shift(1)
        base_pivot["spread_chg_3d"]  = base_pivot["spread_200_230"] - base_pivot["spread_200_230"].shift(3)
    if "cross_p175" in base_pivot.columns and "cross_p200" in base_pivot.columns:
        base_pivot["spread_175_200"] = base_pivot["cross_p175"].shift(1) - base_pivot["cross_p200"].shift(1)

    # Spike calibres chicos — lags optimos 14 y 15 dias
    if "cross_p230" in base_pivot.columns:
        spike_230_raw = base_pivot["cross_p230"] - base_pivot["cross_p230"].shift(3)
        base_pivot["spike_230_lag14"] = spike_230_raw.shift(14)  # lag optimo +0.253
        base_pivot["spike_230_lag10"] = spike_230_raw.shift(10)  # lag alternativo
    if "cross_p250" in base_pivot.columns:
        spike_250_raw = base_pivot["cross_p250"] - base_pivot["cross_p250"].shift(3)
        base_pivot["spike_250_lag15"] = spike_250_raw.shift(15)  # lag optimo +0.235
        base_pivot["spike_250_lag10"] = spike_250_raw.shift(10)  # lag alternativo

    # Merge de vuelta al df principal
    cross_cols = [c for c in base_pivot.columns if c != "date"]
    df = df.merge(base_pivot[["date"] + cross_cols], on="date", how="left")

    return df


# ── 7. Estacionalidad ─────────────────────────────────────────────────────────

def add_calendar_features(df: pd.DataFrame) -> pd.DataFrame:
    df["month"]       = df["date"].dt.month
    df["day_of_week"] = df["date"].dt.dayofweek

    df["month_sin"] = np.sin(2 * np.pi * df["month"] / 12)
    df["month_cos"] = np.cos(2 * np.pi * df["month"] / 12)
    df["dow_sin"]   = np.sin(2 * np.pi * df["day_of_week"] / 7)
    df["dow_cos"]   = np.cos(2 * np.pi * df["day_of_week"] / 7)

    supply_map = {
        1:0.6, 2:0.5, 3:0.7, 4:1.0, 5:1.0, 6:0.9,
        7:0.7, 8:0.5, 9:0.3, 10:0.3, 11:0.4, 12:0.5,
    }
    df["supply_season"] = df["month"].map(supply_map)
    return df


# ── 8. Targets ────────────────────────────────────────────────────────────────

def add_targets(df: pd.DataFrame) -> pd.DataFrame:
    g = df.groupby(GROUP_COLS)["official_price"]

    df["target_1d"] = g.shift(-1)
    df["target_2d"] = g.shift(-2)
    df["target_3d"] = g.shift(-3)
    df["target_7d"] = g.shift(-7)

    def label_direction(delta, thresh=DIRECTION_THRESH):
        if delta > thresh:  return "UP"
        if delta < -thresh: return "DOWN"
        return "LATERAL"

    for h, thresh in [(1, 0.50), (2, 0.50), (3, 0.50), (7, 1.00)]:
        col = f"target_{h}d"
        df[f"direction_target_{h}d"] = (
            df[col] - df["official_price"]
        ).apply(lambda d, t=thresh: label_direction(d, t))

    return df


# ── Validaciones ──────────────────────────────────────────────────────────────

def validate_coverage(df: pd.DataFrame) -> None:
    print("\n── Cobertura de fuentes externas ──")
    checks = {
        "Movement (total_seedless_lb)": "total_seedless_lb",
        "BANXICO (usd_mxn_lag4)":       "usd_mxn_lag4",
        "Lluvia (lluvia_14d_lag6)":      "lluvia_14d_lag6",
        "Importaciones (import_lag2)":   "import_lag2",
        "Spike 230 lag14":               "spike_230_lag14",
    }
    for label, col in checks.items():
        if col in df.columns:
            cov = df[col].notna().mean()
            status = "✅" if cov > 0.80 else ("⚠️ " if cov > 0.50 else "❌")
            print(f"   {status} {label:<35} {cov:.1%}")
        else:
            print(f"   ❌ {label:<35} NO DISPONIBLE")


def validate_direction_dist(df: pd.DataFrame) -> None:
    s200 = df[(df["size"] == 200) & (df["quality"] == "BASE")]
    n    = s200["direction_target_1d"].notna().sum()
    print(f"\n── Distribución dirección 1D — 200 BASE (n={n}) ──")
    dist = s200["direction_target_1d"].value_counts(normalize=True)
    for label, pct in dist.items():
        bar = "█" * int(pct * 30)
        print(f"   {label:<8} {pct:.1%}  {bar}")
    if dist.max() > 0.60:
        print("   ⚠️  Clase dominante >60% — usar class_weight='balanced'")
    else:
        print("   ✅ Distribución balanceada")


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    # Validar inputs obligatorios
    if not PRICE_PATH.exists():
        raise SystemExit(f"❌ No existe: {PRICE_PATH}")
    if not MOVE_PATH.exists():
        raise SystemExit(f"❌ No existe: {MOVE_PATH}")

    print("Cargando datos...")
    price = pd.read_csv(PRICE_PATH)
    move  = pd.read_csv(MOVE_PATH)
    price["date"] = pd.to_datetime(price["date"], errors="coerce")
    move["date"]  = pd.to_datetime(move["date"],  errors="coerce")

    print(f"   Precio:   {len(price):,} filas | "
          f"{price['date'].min().date()} → {price['date'].max().date()}")
    print(f"   Movement: {len(move):,} filas  | "
          f"{move['date'].min().date()} → {move['date'].max().date()}")

    # Fuentes opcionales
    fx   = pd.read_csv(FX_PATH)   if FX_PATH.exists()   else None
    rain = pd.read_csv(RAIN_PATH) if RAIN_PATH.exists()  else None
    imp  = pd.read_csv(IMP_PATH)  if IMP_PATH.exists()   else None

    for df, name in [(fx,"FX"),(rain,"Lluvia"),(imp,"Importaciones")]:
        if df is not None:
            df["date"] = pd.to_datetime(df["date"], errors="coerce")
            print(f"   {name}: {len(df):,} filas cargadas ✅")
        else:
            print(f"   {name}: no disponible (opcional)")

    # Preparar movement
    print("\nPreparando movement...")
    move_ready = prepare_movement(move)

    # Merge principal
    print("Mergeando precio + movement...")
    df = price.merge(move_ready, on="date", how="left")
    df = df.sort_values(GROUP_COLS + ["date"]).reset_index(drop=True)

    # Merge fuentes externas opcionales
    if fx is not None:
        print("Mergeando BANXICO...")
        fx_ready = prepare_fx(fx)
        df = df.merge(fx_ready, on="date", how="left")
        for col in ["usd_mxn","usd_mxn_lag4","usd_mxn_chg_3d","usd_mxn_chg_7d","peso_debil_7d"]:
            if col in df.columns:
                df[col] = df[col].ffill(limit=5)

    if rain is not None:
        print("Mergeando lluvia NASA...")
        rain_ready = prepare_rain(rain)
        df = df.merge(rain_ready, on="date", how="left")
        for col in [c for c in rain_ready.columns if c != "date"]:
            if col in df.columns:
                df[col] = df[col].ffill(limit=5)

    if imp is not None:
        print("Mergeando importaciones...")
        imp_ready = prepare_importaciones(imp)
        df = df.merge(imp_ready, on="date", how="left")
        for col in [c for c in imp_ready.columns if c != "date"]:
            if col in df.columns:
                df[col] = df[col].ffill(limit=5)

    # Features de precio
    print("Calculando features de precio...")
    df = add_price_features(df)

    # Calibres cruzados y spreads
    print("Calculando calibres cruzados y spreads...")
    df = add_cross_size_features(df)

    # Estacionalidad
    print("Calculando estacionalidad...")
    df = add_calendar_features(df)

    # Targets
    print("Calculando targets...")
    df = add_targets(df)

    # Guardar
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUTPUT_PATH, index=False)

    # Resumen
    print(f"\n{'═'*55}")
    print(f"✅ model_base.csv generado")
    print(f"   Ruta:     {OUTPUT_PATH}")
    print(f"   Filas:    {len(df):,}")
    print(f"   Columnas: {len(df.columns)}")

    validate_coverage(df)
    validate_direction_dist(df)

    # Muestra 200 BASE
    s200 = df[(df["size"]==200) & (df["quality"]=="BASE")]
    cols_show = [
        "date","official_price","momentum_3d","volatility_7d",
        "lluvia_14d_lag6","usd_mxn_lag4","import_lag2",
        "spike_230_lag14","target_1d","direction_target_1d",
    ]
    cols_show = [c for c in cols_show if c in df.columns]
    print(f"\n── Últimas 5 filas (200 BASE) ──")
    print(s200[cols_show].tail(5).to_string(index=False))
    print(f"{'═'*55}")


if __name__ == "__main__":
    main()
