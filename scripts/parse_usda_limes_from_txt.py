from pathlib import Path
import csv
import re
import sys

INPUT_PATH = Path("data/raw/usda_limes_block.txt")
OUTPUT_PATH = Path("data/raw/usda_limes_by_size.csv")

report_date = "2026-03-02"
published_datetime = "2026-03-02 16:00:00"
market = "US_MCALLEN"
commodity = "LIMES"
source_price = "USDA"
report_slug = "IX_FV110"

if not INPUT_PATH.exists():
    raise SystemExit(f"No existe {INPUT_PATH}")

sample_text = INPUT_PATH.read_text()

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

if not OUTPUT_PATH.exists():
    with OUTPUT_PATH.open("w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([
            "report_date","published_datetime","market","commodity","size",
            "price_low","price_high","price_mostly_low","price_mostly_high",
            "price_mid","source_price","report_slug","notes"
        ])

with OUTPUT_PATH.open("a", newline="") as f:
    writer = csv.writer(f)
    writer.writerows(rows)

print("ok")
print("rows_added:", len(rows))
print("output:", OUTPUT_PATH)
