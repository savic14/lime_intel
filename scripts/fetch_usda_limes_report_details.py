from pathlib import Path
import csv
import requests
from datetime import datetime, timedelta

env = {}
for line in Path(".env").read_text().splitlines():
    if "=" in line and not line.strip().startswith("#"):
        k, v = line.split("=", 1)
        env[k.strip()] = v.strip()

API_KEY = env["USDA_API_KEY"]

OUTPUT_PATH = Path("data/raw/usda_limes_report_details.csv")
OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

start_date = datetime.strptime("2026-03-02", "%Y-%m-%d").date()
end_date = datetime.strptime("2026-03-17", "%Y-%m-%d").date()

fieldnames = [
    "report_date",
    "published_date",
    "market_location_name",
    "district",
    "commodity",
    "var",
    "pkg",
    "item_size",
    "appear",
    "low_price",
    "high_price",
    "mostly_low_price",
    "mostly_high_price",
    "market_tone_comments",
    "demand_tone_comments",
    "commodity_comments",
    "report_title",
    "slug_name",
]

rows_out = []

current = start_date
while current <= end_date:
    mmddyyyy = current.strftime("%m/%d/%Y")
    url = f"https://marsapi.ams.usda.gov/services/v1.2/reports/2402/report%20details?q=report_date={mmddyyyy}"
    r = requests.get(url, auth=(API_KEY, ""), timeout=60)

    print(current.isoformat(), r.status_code)

    if r.status_code == 200 and r.text:
        data = r.json()
        for row in data.get("results", []):
            if str(row.get("district", "")).strip().upper() != "MEXICO CROSSINGS THROUGH TEXAS":
                continue
            if str(row.get("commodity", "")).strip().upper() != "LIMES":
                continue
            if str(row.get("var", "")).strip().upper() != "SEEDLESS TYPE":
                continue

            rows_out.append({
                "report_date": row.get("report_date", ""),
                "published_date": row.get("published_date", ""),
                "market_location_name": row.get("market_location_name", ""),
                "district": row.get("district", ""),
                "commodity": row.get("commodity", ""),
                "var": row.get("var", ""),
                "pkg": row.get("pkg", ""),
                "item_size": row.get("item_size", ""),
                "appear": row.get("appear", ""),
                "low_price": row.get("low_price", ""),
                "high_price": row.get("high_price", ""),
                "mostly_low_price": row.get("mostly_low_price", ""),
                "mostly_high_price": row.get("mostly_high_price", ""),
                "market_tone_comments": row.get("market_tone_comments", ""),
                "demand_tone_comments": row.get("demand_tone_comments", ""),
                "commodity_comments": row.get("commodity_comments", ""),
                "report_title": row.get("report_title", ""),
                "slug_name": row.get("slug_name", ""),
            })

    current += timedelta(days=1)

with OUTPUT_PATH.open("w", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(rows_out)

print("ok")
print(OUTPUT_PATH)
print("rows:", len(rows_out))
