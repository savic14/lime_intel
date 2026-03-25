
from pathlib import Path
from datetime import datetime, timedelta, date
import argparse, subprocess, sys, warnings
warnings.filterwarnings("ignore")
import pandas as pd, requests

ENV_PATH        = Path(".env")
CORE_PATH       = Path("data/processed/shipping_point_core.csv")
BUILD_SCRIPT    = Path("scripts/build_model_base.py")
FORECAST_SCRIPT = Path("scripts/generate_forecast.py")
API_BASE   = "https://marsapi.ams.usda.gov/services/v1.2/reports/2402/report%20details"
DISTRICT   = "MEXICO CROSSINGS THROUGH TEXAS"
COMMODITY  = "LIMES"
VARIETY    = "SEEDLESS TYPE"
PACKAGE    = "40 LB CARTONS"

def load_api_key():
    if not ENV_PATH.exists():
        raise SystemExit("No existe .env")
    env = {}
    for line in ENV_PATH.read_text().splitlines():
        if "=" in line and not line.strip().startswith("#"):
            k, v = line.split("=", 1)
            env[k.strip()] = v.strip()
    key = env.get("USDA_API_KEY")
    if not key:
        raise SystemExit("USDA_API_KEY no encontrada")
    return key

def map_quality(appear):
    a = str(appear).strip().upper()
    if "FINE" in a: return "#1", appear.strip()
    if "FAIR" in a: return "#2", appear.strip()
    return "BASE", "NO_APPEARANCE"

def map_size(item_size):
    s = str(item_size).strip().upper().replace("S","").replace(",","").strip()
    try: return int(float(s))
    except: return None

def compute_price(low, high, ml, mh):
    def safe(v):
        try: return float(v)
        except: return None
    a, b = safe(ml), safe(mh)
    if a and b: return round((a+b)/2, 4)
    a, b = safe(low), safe(high)
    if a and b: return round((a+b)/2, 4)
    return None

def fetch_day(d, api_key):
    url = f"{API_BASE}?q=report_date={d.strftime('%m/%d/%Y')}"
    try:
        r = requests.get(url, auth=(api_key, ""), timeout=60)
    except Exception as e:
        print(f"    Error {d}: {e}"); return []
    if r.status_code != 200 or not r.text.strip():
        print(f"    {d} sin reporte"); return []
    rows = []
    for row in r.json().get("results", []):
        if str(row.get("district","")).strip().upper() != DISTRICT: continue
        if str(row.get("commodity","")).strip().upper() != COMMODITY: continue
        if str(row.get("var","")).strip().upper() != VARIETY: continue
        if str(row.get("pkg","")).strip().upper() != PACKAGE: continue
        size = map_size(row.get("item_size",""))
        if size is None: continue
        price = compute_price(row.get("low_price",""), row.get("high_price",""),
                              row.get("mostly_low_price",""), row.get("mostly_high_price",""))
        if price is None: continue
        quality, appearance_raw = map_quality(row.get("appear",""))
        low_p   = row.get("low_price",   None)
        high_p  = row.get("high_price",  None)
        mlow_p  = row.get("mostly_low_price",  None)
        mhigh_p = row.get("mostly_high_price", None)
        rows.append({"date": d.isoformat(), "market": "US_MCALLEN",
                     "size": size, "quality": quality, "official_price": price,
                     "low_price":         float(low_p)   if low_p   not in (None,"") else None,
                     "high_price":        float(high_p)  if high_p  not in (None,"") else None,
                     "mostly_low_price":  float(mlow_p)  if mlow_p  not in (None,"") else None,
                     "mostly_high_price": float(mhigh_p) if mhigh_p not in (None,"") else None,
                     "appearance_raw": appearance_raw,
                     "market_tone": str(row.get("market_tone_comments","")).strip(),
                     "demand_tone": str(row.get("demand_tone_comments","")).strip(),
                     "commodity_comments": str(row.get("commodity_comments","")).strip(),
                     "source_price": "USDA_SHIPPING_POINT", "source_district": DISTRICT})
    return rows

def append_to_core(new_rows):
    if not new_rows: return 0
    existing = pd.read_csv(CORE_PATH)
    existing["date"] = pd.to_datetime(existing["date"]).dt.date
    new_df = pd.DataFrame(new_rows)
    new_df["date"] = pd.to_datetime(new_df["date"]).dt.date
    exist_keys = set(zip(existing["date"], existing["size"], existing["quality"]))
    new_df = new_df[~new_df.apply(lambda r: (r["date"],r["size"],r["quality"]) in exist_keys, axis=1)]
    if new_df.empty: return 0
    combined = pd.concat([existing, new_df], ignore_index=True)
    combined = combined.sort_values(["date","size","quality"]).reset_index(drop=True)
    combined.to_csv(CORE_PATH, index=False)
    return len(new_df)

def run_script(script):
    if not script.exists():
        print(f"  Script no encontrado: {script}"); return False
    print(f"Corriendo {script.name}...")
    r = subprocess.run([sys.executable, str(script)], capture_output=True, text=True)
    if r.returncode == 0:
        print(f"  OK")
        for line in r.stdout.strip().split(chr(10))[-5:]: print(f"  {line}")
        return True
    print(f"  FALLO"); print(r.stderr[-300:]); return False

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--desde", default=None)
    parser.add_argument("--solo-fetch", action="store_true")
    args = parser.parse_args()
    if not CORE_PATH.exists():
        raise SystemExit(f"No existe {CORE_PATH}")
    api_key = load_api_key()
    existing = pd.read_csv(CORE_PATH)
    last_date = pd.to_datetime(existing["date"]).max().date()
    today = date.today()
    start_date = datetime.strptime(args.desde, "%Y-%m-%d").date() if args.desde else last_date + timedelta(days=1)
    print("="*50)
    print("LIME INTELLIGENCE — Actualizacion de precios")
    print("="*50)
    print(f"  Ultimo dato: {last_date}")
    print(f"  Fetch desde: {start_date}  hasta: {today}")
    if start_date > today:
        print("Datos al dia. Nada que actualizar."); return
    all_rows = []
    current = start_date
    while current <= today:
        rows = fetch_day(current, api_key)
        print(f"  {current} -> {len(rows)} filas" if rows else f"  {current} -> sin datos")
        all_rows.extend(rows)
        current += timedelta(days=1)
    n = append_to_core(all_rows)
    print(f"Filas nuevas: {n}")
    if args.solo_fetch: return
    if run_script(BUILD_SCRIPT):
        run_script(FORECAST_SCRIPT)
    print("Listo.")

if __name__ == "__main__":
    main()
