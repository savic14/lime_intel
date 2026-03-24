"""
fetch_lluvia_nasa.py
--------------------
Descarga datos historicos de lluvia y temperatura en Martinez de la Torre,
Veracruz (zona principal de produccion de limon persa) desde NASA POWER API.

Sin registro ni API key requerida.

Uso:
    python3 scripts/fetch_lluvia_nasa.py

Output:
    data/processed/lluvia_veracruz_historico.csv
"""

import urllib.request
import json
import pandas as pd
from pathlib import Path

OUT = Path("data/processed")
OUT.mkdir(parents=True, exist_ok=True)

# Coordenadas Martinez de la Torre, Veracruz
# Principal zona productora de limon persa en Mexico (~70% de produccion)
LAT  = 20.0667
LON  = -97.0500

def fetch_nasa_power(start: str, end: str) -> dict:
    """
    Descarga datos de NASA POWER para un rango de fechas.
    start/end formato: YYYYMMDD
    Parametros:
      PRECTOTCORR = Precipitacion corregida (mm/dia)
      T2M_MAX     = Temperatura maxima a 2m (C)
      T2M_MIN     = Temperatura minima a 2m (C)
    """
    url = (
        "https://power.larc.nasa.gov/api/temporal/daily/point"
        f"?parameters=PRECTOTCORR,T2M_MAX,T2M_MIN"
        f"&community=AG"
        f"&longitude={LON}&latitude={LAT}"
        f"&start={start}&end={end}"
        f"&format=JSON"
    )
    with urllib.request.urlopen(url, timeout=60) as r:
        return json.loads(r.read())

def main():
    print("=" * 55)
    print("NASA POWER — Lluvia Martinez de la Torre, Veracruz")
    print("=" * 55)
    print(f"Coordenadas: {LAT}N, {LON}W")
    print("Descargando 2018-2026...")

    # NASA POWER acepta hasta 10 años por llamado
    # Descargamos en dos bloques para mayor confiabilidad
    bloques = [
        ("20180101", "20211231"),
        ("20220101", "20260324"),
    ]

    all_rows = []

    for i, (start, end) in enumerate(bloques):
        print(f"\n  Bloque {i+1}: {start} → {end}")
        try:
            data = fetch_nasa_power(start, end)
            lluvia = data["properties"]["parameter"]["PRECTOTCORR"]
            tmax   = data["properties"]["parameter"]["T2M_MAX"]
            tmin   = data["properties"]["parameter"]["T2M_MIN"]

            for fecha in lluvia:
                all_rows.append({
                    "date":      pd.to_datetime(fecha, format="%Y%m%d").date(),
                    "lluvia_mm": max(0.0, float(lluvia[fecha])),
                    "temp_max":  float(tmax[fecha]),
                    "temp_min":  float(tmin[fecha]),
                })
            print(f"  OK — {len(lluvia)} dias")
        except Exception as e:
            print(f"  ERROR: {e}")

    if not all_rows:
        raise SystemExit("No se descargaron datos")

    df = pd.DataFrame(all_rows).sort_values("date").reset_index(drop=True)

    # ── Features de lluvia ────────────────────────────────────────────────────

    # Acumulados rolling
    df["lluvia_3d"]  = df["lluvia_mm"].rolling(3).sum()
    df["lluvia_7d"]  = df["lluvia_mm"].rolling(7).sum()
    df["lluvia_14d"] = df["lluvia_mm"].rolling(14).sum()

    # Dias consecutivos con lluvia significativa (>5mm = dificil cortar)
    consec = []
    count  = 0
    for v in df["lluvia_mm"]:
        count = count + 1 if v > 5 else 0
        consec.append(count)
    df["dias_lluvia_consec"] = consec

    # Lags del efecto en oferta
    # Lluvia hoy → menos fruta en McAllen en 3-7 dias
    df["lluvia_lag3"]    = df["lluvia_mm"].shift(3)
    df["lluvia_lag5"]    = df["lluvia_mm"].shift(5)
    df["lluvia_lag7"]    = df["lluvia_mm"].shift(7)
    df["lluvia_3d_lag3"] = df["lluvia_3d"].shift(3)
    df["lluvia_3d_lag5"] = df["lluvia_3d"].shift(5)
    df["lluvia_7d_lag5"] = df["lluvia_7d"].shift(5)
    df["lluvia_7d_lag7"] = df["lluvia_7d"].shift(7)

    # Eventos severos (>20mm = muy probable que no se corte)
    df["evento_lluvia"]      = (df["lluvia_mm"] > 20).astype(int)
    df["evento_lluvia_lag5"] = df["evento_lluvia"].shift(5)
    df["evento_lluvia_lag7"] = df["evento_lluvia"].shift(7)

    # Dias consecutivos con lluvia shifteados
    df["dias_consec_lag3"] = df["dias_lluvia_consec"].shift(3)
    df["dias_consec_lag5"] = df["dias_lluvia_consec"].shift(5)

    # Proxy de sequia (temp alta + sin lluvia reciente)
    df["sequia_proxy"] = (
        (df["temp_max"] > 35) & (df["lluvia_7d"] < 5)
    ).astype(int)

    # Guardar
    out_path = OUT / "lluvia_veracruz_historico.csv"
    df.to_csv(out_path, index=False)

    print(f"\n{'='*55}")
    print(f"OK — {len(df):,} registros totales")
    print(f"Rango: {df['date'].min()} -> {df['date'].max()}")
    print(f"Guardado: {out_path} ({out_path.stat().st_size/1024:.1f} KB)")

    print(f"\n── Estadisticas generales ──")
    print(f"  Dias sin lluvia (0mm):     {(df['lluvia_mm']==0).sum():,}")
    print(f"  Dias lluvia leve (<5mm):   {((df['lluvia_mm']>0)&(df['lluvia_mm']<=5)).sum():,}")
    print(f"  Dias lluvia media (5-20mm):{((df['lluvia_mm']>5)&(df['lluvia_mm']<=20)).sum():,}")
    print(f"  Dias lluvia fuerte (>20mm):{(df['lluvia_mm']>20).sum():,}")

    print(f"\n── Lluvia reciente (ultimos 15 dias) ──")
    print(df[["date","lluvia_mm","lluvia_3d","dias_lluvia_consec","evento_lluvia"]].tail(15).to_string(index=False))

    print(f"\n── Correlacion lluvia vs precio futuro (requiere merge con precios) ──")
    print("  Corre experimento_v4.py para ver correlaciones con precio")

if __name__ == "__main__":
    main()
