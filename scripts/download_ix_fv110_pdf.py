from pathlib import Path
import re
import requests

env_path = Path(".env")
if not env_path.exists():
    raise SystemExit("No existe .env")

env_text = env_path.read_text().splitlines()
env = {}
for line in env_text:
    if "=" in line and not line.strip().startswith("#"):
        k, v = line.split("=", 1)
        env[k.strip()] = v.strip()

API_KEY = env.get("USDA_API_KEY")
if not API_KEY:
    raise SystemExit("USDA_API_KEY no encontrada en .env")

REPORT_URL = "https://marsapi.ams.usda.gov/services/v3.1/reports/2402?lastReports=1"
REPORTS_PAGE = "https://mymarketnews.ams.usda.gov/filerepo/reports"

OUT_DIR = Path("data/raw/usda_pdfs")
OUT_DIR.mkdir(parents=True, exist_ok=True)

r = requests.get(REPORT_URL, auth=(API_KEY, ""), timeout=30)
r.raise_for_status()
data = r.json()
report_date = data["results"][0]["report_date"]
mm, dd, yyyy = report_date.split("/")
date_slug = f"{yyyy}-{mm}-{dd}"

page = requests.get(REPORTS_PAGE, timeout=30)
page.raise_for_status()
html = page.text

pattern = rf'https://mymarketnews\.ams\.usda\.gov/filerepo/sites/default/files/2402/{date_slug}/\d+/ams_2402_\d+\.pdf'
matches = re.findall(pattern, html)

if not matches:
    raise SystemExit(f"No encontré PDF para IX_FV110 en fecha {date_slug}")

pdf_url = matches[0]
pdf_response = requests.get(pdf_url, timeout=60)
pdf_response.raise_for_status()

out_path = OUT_DIR / f"IX_FV110_{date_slug}.pdf"
out_path.write_bytes(pdf_response.content)

print("ok")
print("report_date:", report_date)
print("pdf_url:", pdf_url)
print("saved_to:", out_path)
