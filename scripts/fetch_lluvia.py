"""
fetch_external_data.py
----------------------
Descarga datos externos para el modelo de forecast de limon persa:
  1. Tipo de cambio USD/MXN (BANXICO)
  2. Lluvia en Veracruz - Martinez de la Torre (Open-Meteo)
  3. Importaciones Colombia y Peru (movement_core.csv)

Uso:
    python3 scripts/fetch_external_data.py

Outputs:
    data/processed/usd_mxn_historico.csv
    data/processed/lluvia_veracruz_historico.csv
    data/processed/importaciones_historico.csv
"""

import urllib.request
import json
import pandas as pd
from pathlib import Path

OUT   = Path("data/processed")
TOKEN = "dedb0da9788f565887b391f93c2f351da47274d91707de5e644690c1e547d435"
OUT.mkdir(parents=True, exist_ok=True)


# ── 1. BANXICO — USD/MXN historico 2018-2026 ─────────────────────────────────

def fetch_banxico():
    print("=== BANXICO — USD/MXN ===")
    url = (
        "https://www.banxico.org.mx/SieAPIRest/service/v1/series/"
        "SF43718/datos/2018-01-01/2026-03-24?token=" + TOKEN
    )
    req = urllib.request.Request(url, headers={"Bmx-Token": TOKEN})
    with urllib.request.urlopen(req, timeout=30) as r:
        data = json.loads(r.read())

    series = data["bmx"]["series"][0]["datos"]
    rows = []
    for item in series:
        try:
            rows.append({
                "date":    pd.to_datetime(item["fecha"], format="%d/%m/%Y").date(),
                "usd_mxn": float(item["dato"]),
            })
        except Exception:
            pass

    df = pd.DataFrame(rows)
    df = df.sort_values("date").reset_index(drop=True)

    # Features derivados del tipo de cambio
    df["usd_mxn_lag1"]    = df["usd_mxn"].shift(1)
    df["usd_mxn_lag3"]    = df["usd_mxn"].shift(3)
    df["usd_mxn_chg_3d"]  = df["usd_mxn"] - df["usd_mxn"].shift(3)
    df["usd_mxn_chg_7d"]  = df["usd_mxn"] - df["usd_mxn"].shift(7)
    df["usd_mxn_ma7"]     = df["usd_mxn"].rolling(7).mean()
    # Peso debil (MXN alto) = mas incentivo a exportar = mas oferta = precio baja
    df["peso_debil_7d"]   = (df["usd_mxn"] > df["usd_mxn_ma7"]).astype(int)

    out_path = OUT / "usd_mxn_historico.csv"
    df.to_csv(out_path, index=False)
    print(f"  OK — {len(df):,} registros")
    print(f"  Rango: {df['date'].min()} -> {df['date'].max()}")
    print(f"  Ultimo: {df[['date','usd_mxn','usd_mxn_chg_3d']].tail(3).to_string(index=False)}")
    print(f"  Guardado: {out_path}")
    return df


# ── 2. Open-Meteo — Lluvia Veracruz historico 2018-2026 ──────────────────────

def fetch_lluvia():
    print("\n=== OPEN-METEO — Lluvia Martinez de la Torre, Veracruz ===")
    # Coordenadas: Martinez de la Torre, Veracruz (zona principal de limon persa)
    url = (
        "https://archive.open-meteo.com/v1/archive"
        "?latitude=20.0667&longitude=-97.0500"
        "&start_date=2018-01-01&end_date=2026-03-24"
        "&daily=precipitation_sum,rain_sum,temperature_2m_max,temperature_2m_min"
        "&timezone=America%2FMexico_City"
    )
    with urllib.request.urlopen(url, timeout=60) as r:
        d = json.loads(r.read())

    df = pd.DataFrame({
        "date":      pd.to_datetime(d["daily"]["time"]).date,
        "lluvia_mm": d["daily"]["precipitation_sum"],
        "temp_max":  d["daily"]["temperature_2m_max"],
        "temp_min":  d["daily"]["temperature_2m_min"],
    })
    df = df.sort_values("date").reset_index(drop=True)

    # Features de lluvia
    df["lluvia_3d"]   = df["lluvia_mm"].rolling(3).sum()
    df["lluvia_7d"]   = df["lluvia_mm"].rolling(7).sum()
    df["lluvia_14d"]  = df["lluvia_mm"].rolling(14).sum()

    # Dias consecutivos con lluvia significativa (>5mm = no se corta bien)
    df["dia_lluvia"]  = (df["lluvia_mm"] > 5).astype(int)
    consec = []
    count  = 0
    for v in df["dia_lluvia"]:
        count = count + 1 if v == 1 else 0
        consec.append(count)
    df["dias_lluvia_consec"] = consec

    # Lags del efecto (lluvia hoy afecta oferta en 3-7 dias)
    df["lluvia_lag3"] = df["lluvia_mm"].shift(3)
    df["lluvia_lag5"] = df["lluvia_mm"].shift(5)
    df["lluvia_lag7"] = df["lluvia_mm"].shift(7)
    df["lluvia_3d_lag3"] = df["lluvia_3d"].shift(3)
    df["lluvia_3d_lag5"] = df["lluvia_3d"].shift(5)

    # Evento severo: mas de 20mm en un dia
    df["evento_lluvia"] = (df["lluvia_mm"] > 20).astype(int)
    df["evento_lluvia_lag5"] = df["evento_lluvia"].shift(5)

    # Temperatura extrema (sequia proxy: temp alta + sin lluvia)
    df["sequia_proxy"] = ((df["temp_max"] > 35) & (df["lluvia_7d"] < 5)).astype(int)

    out_path = OUT / "lluvia_veracruz_historico.csv"
    df.to_csv(out_path, index=False)
    print(f"  OK — {len(df):,} registros")
    print(f"  Rango: {df['date'].min()} -> {df['date'].max()}")
    print(f"\n  Lluvia reciente (ultimos 10 dias):")
    print(df[["date","lluvia_mm","lluvia_3d","dias_lluvia_consec","evento_lluvia"]].tail(10).to_string(index=False))
    print(f"\n  Guardado: {out_path}")
    return df


# ── 3. Colombia y Peru — del movement_core ───────────────────────────────────

def process_importaciones():
    print("\n=== COLOMBIA Y PERU — movement_core ===")
    move_path = Path("data/processed/movement_core.csv")
    if not move_path.exists():
        print(f"  ERROR: No existe {move_path}")
        return None

    move = pd.read_csv(move_path)
    move["date"] = pd.to_datetime(move["date"])
    move = move.sort_values("date").reset_index(drop=True)

    cols = ["date","total_seedless_lb","mx_seedless_lb",
            "colombia_seedless_lb","peru_seedless_lb",
            "truck_seedless_lb","boat_seedless_lb"]
    cols = [c for c in cols if c in move.columns]
    df = move[cols].copy()

    # Total importado (no mexicano)
    if "colombia_seedless_lb" in df.columns and "peru_seedless_lb" in df.columns:
        df["import_total"] = (
            df["colombia_seedless_lb"].fillna(0) +
            df["peru_seedless_lb"].fillna(0)
        )
        # Ratio importado vs mexicano (competencia directa)
        if "mx_seedless_lb" in df.columns:
            df["import_vs_mx_ratio"] = df["import_total"] / (df["mx_seedless_lb"] + 1)

        # Lags del efecto importaciones (tarda 3-7 dias en llegar al mercado)
        for col in ["colombia_seedless_lb","peru_seedless_lb","import_total"]:
            df[col+"_lag3"]  = df[col].shift(3)
            df[col+"_lag5"]  = df[col].shift(5)
            df[col+"_lag7"]  = df[col].shift(7)
            df[col+"_sum7d"] = df[col].rolling(7).sum()

        # Zscore importaciones vs media 30d (senial relativa)
        df["import_zscore_30d"] = (
            (df["import_total"] - df["import_total"].rolling(30).mean()) /
            (df["import_total"].rolling(30).std() + 1)
        )

    out_path = OUT / "importaciones_historico.csv"
    df.to_csv(out_path, index=False)

    print(f"  OK — {len(df):,} registros")
    print(f"  Rango: {df['date'].min().date()} -> {df['date'].max().date()}")
    print(f"\n  Ultimas 5 filas:")
    show_cols = ["date","colombia_seedless_lb","peru_seedless_lb","import_total"]
    show_cols = [c for c in show_cols if c in df.columns]
    print(df[show_cols].tail(5).to_string(index=False))
    print(f"\n  Guardado: {out_path}")
    return df


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    print("=" * 55)
    print("LIME INTELLIGENCE — Fetch datos externos")
    print("=" * 55)

    results = {}

    try:
        results["fx"]   = fetch_banxico()
    except Exception as e:
        print(f"  ERROR BANXICO: {e}")

    try:
        results["rain"] = fetch_lluvia()
    except Exception as e:
        print(f"  ERROR OPEN-METEO: {e}")

    try:
        results["imp"]  = process_importaciones()
    except Exception as e:
        print(f"  ERROR IMPORTACIONES: {e}")

    print("\n" + "=" * 55)
    print("ARCHIVOS GENERADOS:")
    for fname in ["usd_mxn_historico.csv","lluvia_veracruz_historico.csv","importaciones_historico.csv"]:
        p = OUT / fname
        if p.exists():
            print(f"  {fname}: {p.stat().st_size/1024:.1f} KB")
        else:
            print(f"  {fname}: NO GENERADO")
    print("=" * 55)


if __name__ == "__main__":
    main()
