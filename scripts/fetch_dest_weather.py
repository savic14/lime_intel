"""
fetch_dest_weather.py — Temperatura en ciudades destino de limón persa
Ciudades: Chicago, Atlanta, New York, Los Angeles, Houston, Miami
Uso: python3 scripts/fetch_dest_weather.py

¿Por qué importa?
  - Temperatura alta (>25°C / >77°F) en destino = más consumo de bebidas = más demanda limón
  - Ola de calor en Chicago/NY en verano puede subir precios 10-15% en 1-2 semanas
  - Frío extremo reduce consumo → presión bajista
  - Correlación más fuerte en Mayo-Septiembre (temporada de calor)

Fuente: Open-Meteo API (gratis, sin API key, funciona en tu red)
"""
import requests
import pandas as pd
from pathlib import Path
from datetime import datetime, timedelta

OUTPUT_PATH = Path("data/processed/dest_weather.csv")
OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

# Ciudades destino con coordenadas
CITIES = {
    "Chicago":     {"lat": 41.8781, "lon": -87.6298},
    "Atlanta":     {"lat": 33.7490, "lon": -84.3880},
    "New York":    {"lat": 40.7128, "lon": -74.0060},
    "Los Angeles": {"lat": 34.0522, "lon": -118.2437},
    "Houston":     {"lat": 29.7604, "lon": -95.3698},
    "Miami":       {"lat": 25.7617, "lon": -80.1918},
}

OPEN_METEO_FORECAST = "https://api.open-meteo.com/v1/forecast"
OPEN_METEO_ARCHIVE  = "https://archive.open-meteo.com/v1/archive"


def fetch_forecast(city: str, lat: float, lon: float, days: int = 14) -> list:
    """Fetch 14-day temperature forecast."""
    params = {
        "latitude":   lat,
        "longitude":  lon,
        "daily":      "temperature_2m_max,temperature_2m_min,precipitation_sum",
        "timezone":   "America/Chicago",
        "forecast_days": days,
    }
    try:
        r = requests.get(OPEN_METEO_FORECAST, params=params, timeout=15)
        r.raise_for_status()
        data = r.json()
        daily = data.get("daily", {})
        rows = []
        for i, date_str in enumerate(daily.get("time", [])):
            rows.append({
                "date":      date_str,
                "city":      city,
                "temp_max":  daily["temperature_2m_max"][i],
                "temp_min":  daily["temperature_2m_min"][i],
                "precip_mm": daily.get("precipitation_sum", [None]*len(daily["time"]))[i],
                "tipo":      "forecast",
            })
        return rows
    except Exception as e:
        print(f"  Error forecast {city}: {e}")
        return []


def fetch_historical(city: str, lat: float, lon: float, days_back: int = 30) -> list:
    """Fetch historical temperature data."""
    end   = datetime.today().date() - timedelta(days=1)
    start = end - timedelta(days=days_back)
    params = {
        "latitude":   lat,
        "longitude":  lon,
        "start_date": start.isoformat(),
        "end_date":   end.isoformat(),
        "daily":      "temperature_2m_max,temperature_2m_min,precipitation_sum",
        "timezone":   "America/Chicago",
    }
    try:
        r = requests.get(OPEN_METEO_ARCHIVE, params=params, timeout=20)
        r.raise_for_status()
        data = r.json()
        daily = data.get("daily", {})
        rows = []
        for i, date_str in enumerate(daily.get("time", [])):
            rows.append({
                "date":      date_str,
                "city":      city,
                "temp_max":  daily["temperature_2m_max"][i],
                "temp_min":  daily["temperature_2m_min"][i],
                "precip_mm": daily.get("precipitation_sum", [None]*len(daily["time"]))[i],
                "tipo":      "historico",
            })
        return rows
    except Exception as e:
        # Archive API may be blocked on some networks — use forecast as fallback
        print(f"  Archive bloqueado para {city}, usando solo forecast")
        return []


def heat_signal(temp_max_c: float) -> str:
    """Classify temperature as demand signal."""
    if temp_max_c is None:
        return "—"
    if temp_max_c >= 32:
        return "🔥 Calor alto — demanda ↑↑"
    if temp_max_c >= 25:
        return "☀️  Calor moderado — demanda ↑"
    if temp_max_c >= 15:
        return "🌤  Templado — demanda normal"
    return "❄️  Frío — demanda ↓"


def main():
    print("=" * 60)
    print("LIME INTELLIGENCE — Temperatura ciudades destino")
    print("=" * 60)

    # Cargar existente
    if OUTPUT_PATH.exists():
        existing = pd.read_csv(OUTPUT_PATH)
        last_date = pd.to_datetime(existing["date"]).max().date()
        days_back = (datetime.today().date() - last_date).days + 2
        print(f"Último dato: {last_date} | Actualizando {days_back} días")
    else:
        existing  = pd.DataFrame()
        days_back = 30
        print("Sin datos previos | Descargando 30 días histórico + 14 días forecast")

    all_rows = []

    for city, coords in CITIES.items():
        print(f"\n{city}...")
        lat, lon = coords["lat"], coords["lon"]

        # Histórico
        hist = fetch_historical(city, lat, lon, days_back=days_back)
        all_rows.extend(hist)
        if hist:
            print(f"  Histórico: {len(hist)} días")

        # Forecast
        fc = fetch_forecast(city, lat, lon, days=14)
        all_rows.extend(fc)
        if fc:
            # Mostrar próximos 3 días
            for r in fc[:3]:
                sig = heat_signal(r["temp_max"])
                print(f"  {r['date']}: máx {r['temp_max']:.1f}°C | {sig}")

    if all_rows:
        new_df = pd.DataFrame(all_rows)
        if not existing.empty:
            combined = pd.concat([existing, new_df], ignore_index=True)
            combined = combined.drop_duplicates(subset=["date", "city", "tipo"], keep="last")
            combined = combined.sort_values(["date", "city"]).reset_index(drop=True)
        else:
            combined = new_df.sort_values(["date", "city"]).reset_index(drop=True)

        combined.to_csv(OUTPUT_PATH, index=False)
        print(f"\n✓ Guardado {OUTPUT_PATH} — {len(combined)} filas")

        # Resumen de señal de calor próximos 7 días
        print("\n📊 SEÑAL DE DEMANDA — PRÓXIMOS 7 DÍAS:")
        fc_df = combined[combined["tipo"] == "forecast"].copy()
        fc_df["date"] = pd.to_datetime(fc_df["date"])
        next7 = fc_df[fc_df["date"] <= pd.Timestamp.today() + timedelta(days=7)]
        for city in ["Chicago", "Atlanta", "New York", "Los Angeles"]:
            city_df = next7[next7["city"] == city]
            if not city_df.empty:
                avg_max = city_df["temp_max"].mean()
                sig = heat_signal(avg_max)
                print(f"  {city:12s}: avg máx {avg_max:.1f}°C | {sig}")
    else:
        print("\n⚠️  Sin datos")

    print("\n" + "=" * 60)


if __name__ == "__main__":
    main()
