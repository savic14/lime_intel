from pathlib import Path
import requests
import csv

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

url = "https://marsapi.ams.usda.gov/services/v3.1/reports/2402?lastReports=5"

r = requests.get(url, auth=(API_KEY, ""), timeout=30)
r.raise_for_status()
data = r.json()

rows = [row for row in data["results"] if row["city"] == "Mcallen FOB SC"]

out = Path("data/raw/usda_mcallen_report_headers.csv")
out.parent.mkdir(parents=True, exist_ok=True)

with out.open("w", newline="") as f:
    writer = csv.writer(f)
    writer.writerow(["report_date", "published_Date", "city", "market_type", "slug_name", "report_title"])
    for row in rows:
        writer.writerow([
            row.get("report_date"),
            row.get("published_Date"),
            row.get("city"),
            row.get("market_type"),
            row.get("slug_name"),
            row.get("report_title"),
        ])

print("ok")
print(out)
