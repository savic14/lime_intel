from pathlib import Path
import csv
import re

sample_text = """
MEXICO CROSSINGS THROUGH TEXAS
---LIMES: DEMAND FAIRLY GOOD. MARKET ABOUT STEADY. Wide range in quality and condition. Many present shipments from prior bookings and/or previous commitments.
SEEDLESS TYPE
40 lb cartons
110s 40.00-44.00 mostly 42.00 occasional higher and lower
Fine Appearance 50.00-55.00 mostly 52.00-54.00 occasional higher
Fair Appearance 34.00-38.00 mostly 36.00-38.00 occasional higher and lower
150s 41.00-44.00 mostly 44.00 occasional higher and lower
Fine Appearance 50.00-55.00 mostly 52.00-54.00 occasional higher
Fair Appearance 36.00-41.00 mostly 38.00 occasional higher and lower
175s 41.00-46.00 mostly 44.00-46.00 occasional higher and lower
Fine Appearance 50.00-55.00 mostly 52.00-54.00 occasional higher
Fair Appearance 36.00-41.00 mostly 40.00 occasional higher and lower
200s 43.00-48.00 mostly 44.00-46.00 occasional higher
Fine Appearance 52.00-56.00 mostly 54.00-56.00 occasional higher
Fair Appearance 38.00-42.00 mostly 40.00-42.00 occasional higher and lower
230s 43.00-48.00 mostly 44.00-46.00 occasional higher and lower
Fine Appearance 51.00-56.00 mostly 54.00-56.00 occasional higher
Fair Appearance 38.00-42.00 mostly 38.00-40.00 occasional higher and lower
250s 41.00-45.00 mostly 42.00-44.00 occasional higher and lower
Fine Appearance 50.00-56.00 mostly 52.00-54.00 occasional higher
Fair Appearance 37.00-40.00 mostly 40.00 occasional higher and lower
""".strip()

report_date = "2026-03-13"
published_datetime = "2026-03-13 16:00:24"
market = "US_MCALLEN"
commodity = "LIMES"
source_price = "USDA"
report_slug = "IX_FV110"

lines = [line.strip() for line in sample_text.splitlines() if line.strip()]
notes_line = ""
rows = []

size_pat = re.compile(r'\b(110|150|175|200|230|250|275)s\b', re.IGNORECASE)
range_pat = re.compile(r'(\d+\.\d+)-(\d+\.\d+)')
mostly_pat = re.compile(r'mostly\s+(\d+\.\d+)(?:-(\d+\.\d+))?', re.IGNORECASE)

for line in lines:
    if "SUPPLY" in line or "DEMAND" in line or "MARKET" in line:
        notes_line = line
        continue

    size_m = size_pat.search(line)
    ranges = range_pat.findall(line)
    mostly_m = mostly_pat.search(line)

    if not size_m or not ranges:
        continue

    size = size_m.group(1)
    low, high = map(float, ranges[0])

    if mostly_m:
        mlow = float(mostly_m.group(1))
        mhigh = float(mostly_m.group(2)) if mostly_m.group(2) else float(mostly_m.group(1))
        price_mid = round((mlow + mhigh) / 2, 4)
    else:
        mlow = ""
        mhigh = ""
        price_mid = round((low + high) / 2, 4)

    rows.append([
        report_date,
        published_datetime,
        market,
        commodity,
        size,
        low,
        high,
        mlow,
        mhigh,
        price_mid,
        source_price,
        report_slug,
        notes_line,
    ])

out = Path("data/raw/usda_limes_by_size_sample.csv")
with out.open("w", newline="") as f:
    writer = csv.writer(f)
    writer.writerow([
        "report_date","published_datetime","market","commodity","size",
        "price_low","price_high","price_mostly_low","price_mostly_high",
        "price_mid","source_price","report_slug","notes"
    ])
    writer.writerows(rows)

print("ok")
print(out)
print("rows:", len(rows))
