"""
fetch_movement.py — Descarga movimiento semanal Pharr/McAllen (USDA) y USD/MXN (Banxico)
Outputs:
    data/processed/movement_core.csv   — cruces semanales Pharr
    data/processed/usd_mxn_historico.csv — tipo de cambio actualizado
Uso: python3 scripts/fetch_movement.py
"""
import requests
import json
import urllib.request
import pandas as pd
from pathlib import Path
from datetime import datetime, timedelta

OUT = Path("data/processed")
OUT.mkdir(parents=True, exist_ok=True)

# ── Cargar API keys desde .env ────────────────────────────────────────────────
env = {}
for p in [Path(".env"), Path(__file__).parent.parent / ".env"]:
    if p.exists():
        for line in p.read_text().splitlines():
            if "=" in line and not line.strip().startswith("#"):
                k, v = line.split("=", 1)
                env[k.strip()] = v.strip()
        break

USDA_KEY     = env.get("USDA_API_KEY", "")
BANXICO_TOKEN = env.get("BANXICO_TOKEN", "dedb0da9788f565887b391f93c2f351da47274d91707de5e644690c1e547d435")

# ── 1. USDA Movement — Reporte semanal Pharr/McAllen ─────────────────────────
# Report ID 2491 = WA_FV175 = National Shipping Point Trends (FVWTRDS)
# Contiene cruces semanales de limón persa por Texas

def fetch_usda_movement(days_back=90):
    print("=" * 55)
    print("MOVIMIENTO PHARR/MCALLEN — USDA")
    print("=" * 55)

    out_path = OUT / "movement_core.csv"
    existing = pd.read_csv(out_path) if out_path.exists() else pd.DataFrame()

    if not existing.empty:
        existing["date"] = pd.to_datetime(existing["date"], errors="coerce")
        last_date = existing["date"].max().date()
        days_back = (datetime.today().date() - last_date).days + 7
        print(f"  Último dato: {last_date} | Descargando {days_back} días")
    else:
        print(f"  Sin datos previos | Descargando {days_back} días")

    end_date   = datetime.today().date()
    start_date = end_date - timedelta(days=days_back)

    # USDA MARS API — reporte semanal de movimiento por limón/Texas
    # Usamos el endpoint de shipping point trends
    url = (f"https://marsapi.ams.usda.gov/services/v1.2/reports/2491"
           f"/report%20details?q=report_begin_date={start_date.strftime('%m/%d/%Y')}")

    rows = []
    try:
        r = requests.get(url, auth=(USDA_KEY, ""), timeout=45)
        if r.status_code == 200:
            data  = r.json()
            items = data if isinstance(data, list) else data.get("results", [])
            for item in items:
                comm = str(item.get("commodity", "")).upper()
                if "LIME" not in comm:
                    continue
                variety = str(item.get("variety", "")).upper()
                if "SEEDED" in variety and "SEEDLESS" not in variety:
                    continue
                district = str(item.get("district", "") or "").upper()
                if "TEXAS" not in district and "PHARR" not in district and "TX" not in district:
                    continue
                try:
                    report_date = pd.to_datetime(item.get("report_date", ""), errors="coerce")
                    crossings   = item.get("crossings", item.get("quantity", None))
                    if crossings and report_date:
                        rows.append({
                            "date":              report_date.date().isoformat(),
                            "pharr_seedless_lb": float(crossings) * 100000,
                            "mx_seedless_lb":    float(crossings) * 100000,
                            "total_seedless_lb": float(crossings) * 100000,
                            "source":            "usda_mars",
                        })
                except Exception:
                    continue
        else:
            print(f"  MARS API status {r.status_code} — intentando PDF parser")
    except Exception as e:
        print(f"  Error MARS: {e}")

    # Fallback: parsear el PDF del reporte semanal directamente
    if not rows:
        rows = fetch_fvwtrds_pdf()

    if rows:
        new_df = pd.DataFrame(rows)
        new_df["date"] = pd.to_datetime(new_df["date"])
        if not existing.empty:
            combined = pd.concat([existing, new_df], ignore_index=True)
            combined = combined.drop_duplicates(subset=["date"], keep="last")
        else:
            combined = new_df
        combined = combined.sort_values("date").reset_index(drop=True)
        combined.to_csv(out_path, index=False)
        print(f"  ✓ {len(rows)} filas nuevas | Total: {len(combined)}")
    else:
        print("  Sin datos nuevos de movimiento")

    return rows


def fetch_fvwtrds_pdf():
    """
    Parsea el reporte FVWTRDS (National Shipping Point Trends) directamente
    desde el PDF de USDA para extraer cruces semanales de limón por Texas.
    """
    print("  Intentando parsear FVWTRDS PDF...")
    rows = []
    try:
        import urllib.request
        url = "https://www.ams.usda.gov/mnreports/fvwtrds.pdf"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            pdf_bytes = resp.read()

        # Extraer texto del PDF usando pypdf si disponible
        try:
            import io
            from pypdf import PdfReader
            reader = PdfReader(io.BytesIO(pdf_bytes))
            text = "\n".join(page.extract_text() or "" for page in reader.pages)
        except ImportError:
            print("  pypdf no instalado — pip3 install pypdf")
            return rows

        # Parsear línea de cruces de limón por Texas
        # Ejemplo: "MEXICO CROSSINGS THROUGH TEXAS Crossings 198-171-197"
        import re
        # Buscar fecha del reporte
        date_match = re.search(r"(\w+ \d+, \d{4})", text[:500])
        report_date_str = date_match.group(1) if date_match else None

        # Buscar cruces de limón
        lime_match = re.search(
            r"---LIMES.*?MEXICO CROSSINGS THROUGH TEXAS\s+Crossings\s+([\d]+)-([\d]+)-([\d]+)",
            text, re.DOTALL | re.IGNORECASE
        )
        if lime_match and report_date_str:
            # Los 3 números son semanas: dos anteriores + la más reciente
            c1, c2, c3 = [int(x) for x in lime_match.groups()]
            report_date = pd.to_datetime(report_date_str)

            # Semana más reciente = report_date - 7 días (semana que termina)
            for i, cwt in enumerate([c3, c2, c1]):
                week_end = report_date.date() - timedelta(days=i*7)
                week_start = week_end - timedelta(days=6)
                # Distribuir cwt entre los días de la semana
                lbs = cwt * 100000  # cwt = 100 lbs
                rows.append({
                    "date":              week_end.isoformat(),
                    "pharr_seedless_lb": lbs,
                    "mx_seedless_lb":    lbs,
                    "total_seedless_lb": lbs,
                    "cwt":               cwt,
                    "source":            "fvwtrds_pdf",
                })
            print(f"  ✓ Cruces encontrados: {c1}-{c2}-{c3} cwt | Reporte: {report_date_str}")
        else:
            print("  No se encontraron cruces de limón en el PDF")

    except Exception as e:
        print(f"  Error PDF: {e}")

    return rows


# ── 2. BANXICO — USD/MXN actualizado ─────────────────────────────────────────

def fetch_banxico():
    print("\n" + "=" * 55)
    print("BANXICO — USD/MXN")
    print("=" * 55)

    out_path  = OUT / "usd_mxn_historico.csv"
    today_str = datetime.today().strftime("%Y-%m-%d")
    start_str = "2018-01-01"

    # Verificar si ya tenemos datos recientes
    if out_path.exists():
        existing  = pd.read_csv(out_path)
        existing["date"] = pd.to_datetime(existing["date"], errors="coerce")
        last_date = existing["date"].max().date()
        days_old  = (datetime.today().date() - last_date).days
        if days_old <= 2:
            print(f"  Datos al día ({last_date}) — sin necesidad de actualizar")
            return
        start_str = (last_date - timedelta(days=5)).strftime("%Y-%m-%d")
        print(f"  Último dato: {last_date} | Actualizando desde {start_str}")
    else:
        existing = pd.DataFrame()
        print(f"  Sin datos previos | Descargando desde {start_str}")

    # Convertir fechas a formato Banxico (yyyy-mm-dd)
    url = (f"https://www.banxico.org.mx/SieAPIRest/service/v1/series/"
           f"SF43718/datos/{start_str}/{today_str}?token={BANXICO_TOKEN}")
    try:
        req = urllib.request.Request(url, headers={"Bmx-Token": BANXICO_TOKEN})
        with urllib.request.urlopen(req, timeout=30) as r:
            data = json.loads(r.read())

        series = data["bmx"]["series"][0]["datos"]
        rows   = []
        for item in series:
            try:
                rows.append({
                    "date":    pd.to_datetime(item["fecha"], format="%d/%m/%Y").date().isoformat(),
                    "usd_mxn": float(item["dato"]),
                })
            except Exception:
                continue

        if rows:
            new_df = pd.DataFrame(rows)
            new_df["date"] = pd.to_datetime(new_df["date"])
            if not existing.empty:
                combined = pd.concat([existing, new_df], ignore_index=True)
                combined = combined.drop_duplicates(subset=["date"], keep="last")
            else:
                combined = new_df
            combined = combined.sort_values("date").reset_index(drop=True)
            # Calcular cambio 7d
            combined["usd_mxn_chg_7d"] = combined["usd_mxn"].diff(5)
            combined.to_csv(out_path, index=False)
            last = combined.iloc[-1]
            print(f"  ✓ {len(rows)} filas nuevas | Último: {last['date'].strftime('%d %b')} = {float(last['usd_mxn']):.4f}")
        else:
            print("  Sin datos nuevos")

    except Exception as e:
        print(f"  Error Banxico: {e}")


if __name__ == "__main__":
    fetch_banxico()
    fetch_usda_movement()
    print("\n✅ Listo")
