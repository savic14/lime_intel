"""
fetch_terminals.py — Descarga precios de mercados terminales USDA para limón persa
Mercados: Atlanta (2277), Chicago (2290), LA (2306), NY (2314), Miami (2310)
Uso: python3 scripts/fetch_terminals.py
Fixes v2:
  - Solo cajas de 40 lb (excluye 10 lb y otros formatos)
  - item_size como calibre directo (110s=110, 150s=150, etc.)
  - Separa origen Mexico vs Colombia/Peru
  - Guarda quality_type: Fine Appearance, Fair Quality, o BASE
"""
from pathlib import Path
import requests
import pandas as pd
from datetime import datetime, timedelta

# ── Config ────────────────────────────────────────────────────────────────────
env = {}
for line in Path(".env").read_text().splitlines():
    if "=" in line and not line.strip().startswith("#"):
        k, v = line.split("=", 1)
        env[k.strip()] = v.strip()
API_KEY = env["USDA_API_KEY"]

MARKETS = {
    "terminal_atlanta.csv":  {"id": 2277, "label": "Atlanta"},
    "terminal_chicago.csv":  {"id": 2290, "label": "Chicago"},
    "terminal_la.csv":       {"id": 2306, "label": "Los Angeles"},
    "terminal_ny.csv":       {"id": 2314, "label": "New York"},
    "terminal_miami.csv":    {"id": 2310, "label": "Miami"},
}

OUTPUT_DIR = Path("data/processed")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Calibres válidos en cajas de 40 lb (item_size field)
VALID_SIZES = {
    "110s": 110, "115s": 110,
    "150s": 150, "145s": 150,
    "175s": 175, "180s": 175,
    "200s": 200, "195s": 200,
    "230s": 230, "235s": 230,
    "250s": 250, "245s": 250,
}

def parse_size(size_str):
    s = str(size_str).strip().lower().replace(" ", "")
    return VALID_SIZES.get(s, None)

def parse_quality(item):
    """Determina calidad: Fine Appearance, Fair Quality, o BASE."""
    appearance = str(item.get("appearance", "") or "").upper()
    quality    = str(item.get("quality", "") or "").upper()
    if "FINE" in appearance:
        return "Fine Appearance"
    if "FAIR" in quality or "FAIR" in appearance:
        return "Fair Quality"
    return "BASE"

def fetch_terminal(report_id, label, days_back=60):
    rows = []
    end_date   = datetime.today().date()
    start_date = end_date - timedelta(days=days_back)
    current    = start_date

    while current <= end_date:
        mmddyyyy = current.strftime("%m/%d/%Y")
        url = (f"https://marsapi.ams.usda.gov/services/v1.2/reports/{report_id}"
               f"/report%20details?q=report_date={mmddyyyy}")
        try:
            r = requests.get(url, auth=(API_KEY, ""), timeout=30)
            if r.status_code == 200:
                data  = r.json()
                items = data if isinstance(data, list) else data.get("results", [])
                for item in items:
                    # Solo limón
                    if "LIME" not in str(item.get("commodity", "")).upper():
                        continue
                    # Solo SEEDLESS TYPE (persa), no seeded
                    variety = str(item.get("variety", "")).upper()
                    if "SEEDED TYPE" in variety and "SEEDLESS" not in variety:
                        continue
                    # Solo cajas de 40 lb
                    pkg = str(item.get("package", "")).lower()
                    if "40 lb" not in pkg and "40lb" not in pkg:
                        continue
                    # Calibre válido
                    size = parse_size(str(item.get("item_size", "")))
                    if size is None:
                        continue

                    def tf(v):
                        try: return float(v)
                        except: return None

                    origin   = str(item.get("origin", "") or "").strip()
                    quality  = parse_quality(item)
                    tone     = str(item.get("market_tone_comments", "") or "").strip()
                    reporter = str(item.get("reporter_comment", "") or "").strip()

                    rows.append({
                        "date":              current.isoformat(),
                        "market":            label,
                        "size":              size,
                        "origin":            origin,
                        "quality_type":      quality,
                        "low_price":         tf(item.get("low_price")),
                        "high_price":        tf(item.get("high_price")),
                        "mostly_low_price":  tf(item.get("mostly_low_price")),
                        "mostly_high_price": tf(item.get("mostly_high_price")),
                        "official_price":    tf(item.get("mostly_high_price") or item.get("high_price")),
                        "market_tone":       tone,
                        "reporter_comment":  reporter,
                    })
        except Exception as e:
            print(f"  Error {current}: {e}")
        current += timedelta(days=1)

    return rows

def main():
    print("=" * 60)
    print("LIME INTELLIGENCE — Mercados terminales USDA v2")
    print("=" * 60)

    for fname, cfg in MARKETS.items():
        label = cfg["label"]
        rid   = cfg["id"]
        out   = OUTPUT_DIR / fname
        print(f"\n{label} (report {rid})...")

        if out.exists():
            existing  = pd.read_csv(out)
            last_date = pd.to_datetime(existing["date"]).max().date()
            days_back = (datetime.today().date() - last_date).days + 3
            print(f"  Último dato: {last_date} | Descargando {days_back} días")
        else:
            existing  = pd.DataFrame()
            days_back = 60
            print(f"  Sin datos previos | Descargando {days_back} días")

        rows = fetch_terminal(rid, label, days_back=days_back)

        if rows:
            new_df = pd.DataFrame(rows)
            if not existing.empty:
                combined = pd.concat([existing, new_df], ignore_index=True)
                combined = combined.drop_duplicates(
                    subset=["date","size","origin","quality_type"], keep="last")
                combined = combined.sort_values(["date","size"]).reset_index(drop=True)
            else:
                combined = new_df.sort_values(["date","size"]).reset_index(drop=True)

            combined.to_csv(out, index=False)
            calibres = sorted(combined["size"].dropna().unique().astype(int).tolist())
            mx_rows  = len(combined[combined["origin"].str.upper().str.contains("MEXICO", na=False)])
            print(f"  ✓ {len(rows)} filas nuevas | Total: {len(combined)} | "
                  f"Calibres: {calibres} | Mexico: {mx_rows} filas")
        else:
            print(f"  Sin datos nuevos")

    print("\n" + "=" * 60)
    print("Listo — borra los CSVs viejos y corre de nuevo si los precios siguen mal:")
    print("  rm data/processed/terminal_*.csv && python3 scripts/fetch_terminals.py")
    print("=" * 60)

if __name__ == "__main__":
    main()
