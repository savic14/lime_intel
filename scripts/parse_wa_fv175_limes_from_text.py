from pathlib import Path
import csv
import re

INPUT_PATH = Path("data/raw/wa_fv175_limes_block.txt")
OUTPUT_PATH = Path("data/processed/wa_fv175_limes.csv")

report_date = "2026-03-17"
movement_date = "2026-03-16"
source_report = "WA_FV175"

if not INPUT_PATH.exists():
    raise SystemExit(f"No existe {INPUT_PATH}")

text = INPUT_PATH.read_text()

rows = []

# Ejemplos:
# LIMES SEEDLESS TYPE CB B 1,283,115 128
# LIMES SEEDLESS TYPE Organic MX T 7,172 1
pat = re.compile(
    r'^LIMES\s+'
    r'(SEEDED TYPES|SEEDLESS TYPE)\s+'
    r'(Organic\s+)?'
    r'([A-Z]{2})\s+'
    r'([TAB])\s+'
    r'([\d,]+)\s+'
    r'([\d*]+)$',
    re.MULTILINE
)

for m in pat.finditer(text):
    type_label = m.group(1)
    organic_flag = "Y" if m.group(2) else "N"
    origin_code = m.group(3)
    transport_mode = m.group(4)
    weight_lb = int(m.group(5).replace(",", ""))
    load_count = None if m.group(6) == "*" else int(m.group(6))

    rows.append({
        "report_date": report_date,
        "movement_date": movement_date,
        "commodity": "LIMES",
        "type_label": type_label,
        "origin_code": origin_code,
        "transport_mode": transport_mode,
        "weight_lb": weight_lb,
        "load_count": load_count,
        "organic_flag": organic_flag,
        "source_report": source_report,
    })

OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
with OUTPUT_PATH.open("w", newline="") as f:
    writer = csv.DictWriter(
        f,
        fieldnames=[
            "report_date", "movement_date", "commodity", "type_label",
            "origin_code", "transport_mode", "weight_lb", "load_count",
            "organic_flag", "source_report"
        ]
    )
    writer.writeheader()
    writer.writerows(rows)

print("ok")
print(OUTPUT_PATH)
print("rows:", len(rows))
