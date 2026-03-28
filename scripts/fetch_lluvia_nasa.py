"""
fetch_lluvia_nasa.py — Lluvia 5 zonas productoras de limon persa
Fuente: NASA POWER API (sin autenticacion)
Zonas por participacion en produccion nacional:
  1. Martinez de la Torre, Ver.  54%
  2. Tuxtepec / Papaloapan, Oax. 16%
  3. Huimanguillo, Tabasco        7%
  4. Valladolid, Yucatan          5%
  5. Cd. Valles / Tamazunchale SLP exportacion directa
"""
import requests
import pandas as pd
from pathlib import Path
from datetime import datetime, timedelta

OUTPUT_DIR = Path("data/processed")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

ZONAS = {
    "mtt":       {"nombre": "Martinez de la Torre, Ver.", "lat": 20.0667, "lon": -97.0500, "pct": 54},
    "tuxtepec":  {"nombre": "Tuxtepec, Oax.",             "lat": 18.0833, "lon": -96.1167, "pct": 16},
    "tabasco":   {"nombre": "Huimanguillo, Tabasco",       "lat": 17.8333, "lon": -93.3833, "pct":  7},
    "yucatan":   {"nombre": "Valladolid, Yucatan",         "lat": 20.6897, "lon": -88.2022, "pct":  5},
    "slp":       {"nombre": "Cd. Valles, SLP",             "lat": 21.9833, "lon": -99.0167, "pct":  5},
}

NASA_BASE = "https://power.larc.nasa.gov/api/temporal/daily/point"
PARAMS_NASA = "PRECTOTCORR,T2M_MAX,T2M_MIN"

START_HIST = "20180101"


def fetch_nasa_zone(zona_key: str, zona: dict, start: str, end: str) -> pd.DataFrame:
    params = {
        "parameters": PARAMS_NASA,
        "community":  "AG",
        "longitude":  zona["lon"],
        "latitude":   zona["lat"],
        "start":      start,
        "end":        end,
        "format":     "JSON",
    }
    r = requests.get(NASA_BASE, params=params, timeout=60)
    if r.status_code != 200:
        print(f"  ERROR {zona_key}: {r.status_code}")
        return pd.DataFrame()

    data = r.json()
    lluvia_raw = data["properties"]["parameter"]["PRECTOTCORR"]
    tmax_raw   = data["properties"]["parameter"].get("T2M_MAX", {})
    tmin_raw   = data["properties"]["parameter"].get("T2M_MIN", {})

    rows = []
    for date_str, mm in lluvia_raw.items():
        if mm < 0:
            mm = 0.0
        rows.append({
            "date":     date_str,
            "zona_key": zona_key,
            "zona":     zona["nombre"],
            "lat":      zona["lat"],
            "lon":      zona["lon"],
            "pct_prod": zona["pct"],
            "lluvia_mm": round(float(mm), 3),
            "tmax":     round(float(tmax_raw.get(date_str, -999)), 2),
            "tmin":     round(float(tmin_raw.get(date_str, -999)), 2),
        })

    df = pd.DataFrame(rows)
    df["date"] = pd.to_datetime(df["date"], format="%Y%m%d", errors="coerce")
    df = df.dropna(subset=["date"]).sort_values("date").reset_index(drop=True)
    return df


def add_rolling_features(df: pd.DataFrame) -> pd.DataFrame:
    df = df.sort_values("date").reset_index(drop=True)
    df["lluvia_3d"]  = df["lluvia_mm"].rolling(3,  min_periods=1).sum()
    df["lluvia_7d"]  = df["lluvia_mm"].rolling(7,  min_periods=1).sum()
    df["lluvia_14d"] = df["lluvia_mm"].rolling(14, min_periods=1).sum()

    consec = []
    count = 0
    for v in df["lluvia_mm"]:
        count = count + 1 if v > 5 else 0
        consec.append(count)
    df["dias_lluvia_consec"] = consec
    df["evento_lluvia"] = (df["lluvia_mm"] > 20).astype(int)
    return df


def main():
    today     = datetime.today()
    end_date  = today.strftime("%Y%m%d")

    print("=" * 60)
    print("NASA POWER — Lluvia 5 zonas productoras limon persa")
    print("=" * 60)

    all_zones = []

    for zona_key, zona in ZONAS.items():
        output_path = OUTPUT_DIR / f"lluvia_{zona_key}.csv"

        # Determinar desde cuando descargar
        if output_path.exists():
            existing = pd.read_csv(output_path)
            existing["date"] = pd.to_datetime(existing["date"])
            last_date = existing["date"].max()
            start_date = (last_date + timedelta(days=1)).strftime("%Y%m%d")
            print(f"\n{zona['nombre']} ({zona['pct']}%)")
            print(f"  Existente hasta: {last_date.date()} — descargando desde {start_date}")
        else:
            start_date = START_HIST
            existing   = pd.DataFrame()
            print(f"\n{zona['nombre']} ({zona['pct']}%)")
            print(f"  Primera descarga desde {start_date}")

        if start_date > end_date:
            print("  Ya al dia")
            df_zone = existing
        else:
            # Descargar en bloques de 4 años
            start_dt = datetime.strptime(start_date, "%Y%m%d")
            end_dt   = datetime.strptime(end_date,   "%Y%m%d")
            chunks   = []
            cursor   = start_dt
            while cursor <= end_dt:
                chunk_end = min(cursor + timedelta(days=4*365), end_dt)
                s = cursor.strftime("%Y%m%d")
                e = chunk_end.strftime("%Y%m%d")
                print(f"  Bloque: {s} → {e}")
                df_chunk = fetch_nasa_zone(zona_key, zona, s, e)
                if not df_chunk.empty:
                    chunks.append(df_chunk)
                cursor = chunk_end + timedelta(days=1)

            if chunks:
                new_data = pd.concat(chunks).drop_duplicates("date")
                if not existing.empty:
                    df_zone = pd.concat([existing, new_data]).drop_duplicates("date").sort_values("date").reset_index(drop=True)
                else:
                    df_zone = new_data.sort_values("date").reset_index(drop=True)
            else:
                df_zone = existing

        # Agregar features rolling
        if not df_zone.empty:
            df_zone = add_rolling_features(df_zone)
            df_zone.to_csv(output_path, index=False)
            print(f"  Guardado: {output_path.name} ({len(df_zone):,} filas)")
            print(f"  Rango: {df_zone['date'].min().date()} → {df_zone['date'].max().date()}")
            lluvia_rec = df_zone.tail(7)["lluvia_mm"].sum()
            print(f"  Lluvia ultimos 7d: {lluvia_rec:.1f} mm")

        all_zones.append(df_zone)

    # Crear archivo consolidado (pivot por zona)
    print("\n" + "=" * 60)
    print("Consolidando todas las zonas...")

    dfs = []
    for zona_key, zona in ZONAS.items():
        path = OUTPUT_DIR / f"lluvia_{zona_key}.csv"
        if path.exists():
            df = pd.read_csv(path)
            df["date"] = pd.to_datetime(df["date"])
            df = df[["date", "zona_key", "lluvia_mm", "lluvia_3d", "lluvia_7d", "lluvia_14d",
                      "dias_lluvia_consec", "evento_lluvia"]].copy()
            dfs.append(df)

    if dfs:
        combined = pd.concat(dfs).sort_values(["date", "zona_key"]).reset_index(drop=True)

        # Pivot ancho para compatibilidad con build_model_base.py
        pivot = combined.pivot_table(
            index="date", columns="zona_key",
            values=["lluvia_mm", "lluvia_7d", "lluvia_14d"]
        )
        pivot.columns = ["_".join(c) for c in pivot.columns]
        pivot = pivot.reset_index()

        # Promedio ponderado por produccion (pcts)
        pcts = {k: v["pct"] for k, v in ZONAS.items()}
        total_pct = sum(pcts.values())

        ll_cols = [f"lluvia_mm_{k}" for k in ZONAS.keys() if f"lluvia_mm_{k}" in pivot.columns]
        if ll_cols:
            pivot["lluvia_mm_ponderada"] = sum(
                pivot[f"lluvia_mm_{k}"] * pcts[k] / total_pct
                for k in ZONAS.keys() if f"lluvia_mm_{k}" in pivot.columns
            )
            l7_cols = [f"lluvia_7d_{k}" for k in ZONAS.keys() if f"lluvia_7d_{k}" in pivot.columns]
            pivot["lluvia_7d_ponderada"] = sum(
                pivot[f"lluvia_7d_{k}"] * pcts[k] / total_pct
                for k in ZONAS.keys() if f"lluvia_7d_{k}" in pivot.columns
            )
            l14_cols = [f"lluvia_14d_{k}" for k in ZONAS.keys() if f"lluvia_14d_{k}" in pivot.columns]
            pivot["lluvia_14d_ponderada"] = sum(
                pivot[f"lluvia_14d_{k}"] * pcts[k] / total_pct
                for k in ZONAS.keys() if f"lluvia_14d_{k}" in pivot.columns
            )

        # Mantener compatibilidad: columnas originales = ponderadas
        pivot["lluvia_mm"]  = pivot["lluvia_mm_ponderada"]
        pivot["lluvia_7d"]  = pivot["lluvia_7d_ponderada"]
        pivot["lluvia_14d"] = pivot["lluvia_14d_ponderada"]

        # Features lag para modelo
        pivot = pivot.sort_values("date").reset_index(drop=True)
        pivot["lluvia_14d_lag6"] = pivot["lluvia_14d"].shift(6)
        pivot["lluvia_7d_lag7"]  = pivot["lluvia_7d"].shift(7)
        pivot["lluvia_3d_lag7"]  = pivot.get("lluvia_3d_mtt", pivot["lluvia_mm"]).shift(7) if "lluvia_3d_mtt" in pivot.columns else pivot["lluvia_mm"].shift(7)

        combined_path = OUTPUT_DIR / "lluvia_zonas_consolidado.csv"
        pivot.to_csv(combined_path, index=False)

        # Compatibilidad con scripts existentes — sobreescribir lluvia_veracruz_historico.csv
        # usando la columna ponderada (antes era solo MTT)
        compat = pivot[["date", "lluvia_mm", "lluvia_7d", "lluvia_14d",
                         "lluvia_14d_lag6", "lluvia_7d_lag7"]].copy()

        # Agregar columnas que espera build_model_base
        compat["lluvia_3d"]          = pivot["lluvia_mm"].rolling(3).sum()
        compat["lluvia_lag9"]         = pivot["lluvia_mm"].shift(9)
        compat["lluvia_3d_lag7"]      = compat["lluvia_3d"].shift(7)
        compat["dias_lluvia_consec"]  = 0
        compat["dias_consec_lag5"]    = 0
        compat["evento_lluvia_lag7"]  = 0

        compat.to_csv(OUTPUT_DIR / "lluvia_veracruz_historico.csv", index=False)

        print(f"Consolidado: {combined_path.name} ({len(pivot):,} filas, {len(pivot.columns)} columnas)")
        print(f"Compatibilidad: lluvia_veracruz_historico.csv actualizado con promedio ponderado")

        # Resumen ultimos 7 dias por zona
        print("\n── Lluvia ultimos 7 dias por zona ──")
        for zona_key, zona in ZONAS.items():
            path = OUTPUT_DIR / f"lluvia_{zona_key}.csv"
            if path.exists():
                df = pd.read_csv(path)
                df["date"] = pd.to_datetime(df["date"])
                rec = df.tail(7)["lluvia_mm"].sum()
                nivel = "ALTA" if rec > 40 else ("MEDIA" if rec > 15 else "baja")
                print(f"  {zona['nombre']:<35} {rec:6.1f} mm  {nivel}")

    print("\nDone.")


if __name__ == "__main__":
    main()
