from pathlib import Path
import csv
import requests

BASE_URL = "https://api.census.gov/data/timeseries/intltrade/imports/hs"

months = []
for year in range(2013, 2027):
    for month in range(1, 13):
        months.append(f"{year}-{month:02d}")

rows_out = []

for ym in months:
    params = {
        "get": "CTY_CODE,CTY_NAME,I_COMMODITY,GEN_VAL_MO,GEN_VAL_YR",
        "time": ym,
        "I_COMMODITY": "080550",
    }
    try:
        r = requests.get(BASE_URL, params=params, timeout=60)
        print("month:", ym, "status:", r.status_code)
        if r.status_code != 200 or not r.text:
            continue

        data = r.json()
        if len(data) <= 1:
            continue

        for row in data[1:]:
            cty_code = str(row[0]).strip()
            cty_name = str(row[1]).strip().upper()
            if cty_code == "3010" and cty_name == "COLOMBIA":
                rows_out.append([row[0], row[1], row[2], row[3], row[4], ym])
                print("MATCH:", ym, row[3])
    except Exception as e:
        print("ERROR:", ym, str(e))
        continue

out = Path("data/raw/colombia_imports_monthly.csv")
out.parent.mkdir(parents=True, exist_ok=True)

with out.open("w", newline="") as f:
    writer = csv.writer(f)
    writer.writerow(["CTY_CODE", "CTY_NAME", "I_COMMODITY", "GEN_VAL_MO", "GEN_VAL_YR", "time"])
    writer.writerows(rows_out)

print("ok")
print(out)
print("rows:", len(rows_out))
