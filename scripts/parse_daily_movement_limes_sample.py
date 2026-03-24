from pathlib import Path
import csv
import re

input_path = Path("data/raw/daily_movement_limes_sample.txt")
output_path = Path("data/processed/daily_movement_limes_sample.csv")

if not input_path.exists():
    raise SystemExit(f"No existe {input_path}")

text = input_path.read_text()

# Fecha manual para esta muestra; luego la automatizamos desde metadata/release
report_date = "2026-03-17"

rows = []

# Ejemplos esperados:
# LIMES SEEDLESS TYPE MX T 1,231,117 123
# LIMES SEEDLESS TYPE PE B 216,568 22
# LIMES SEEDLESS TYPE Organic MX T 7,172 1
pat = re.compile(
    r'^LIMES\s+SEEDLESS\s+TYPE\s+(Organic\s+)?([A-Z]{2})\s+([TAB])\s+([\d,]+)\s+([\d*]+)$',
    re.MULTILINE
)

for m in pat.finditer(text):
    organic = "Y" if m.group(1) else "N"
    origin_code = m.group(2)
    transport_mode = m.group(3)
    weight_lb = int(m.group(4).replace(",", ""))
    load_count = m.group(5)
    load_count = None if load_count == "*" else int(load_count)

    rows.append({
        "date": report_date,
        "commodity": "LIMES",
        "type_label": "SEEDLESS TYPE",
        "origin_code": origin_code,
        "transport_mode": transport_mode,
        "weight_lb": weight_lb,
        "load_count": load_count,
        "organic_flag": organic,
        "source_report": "WA_FV175",
    })

output_path.parent.mkdir(parents=True, exist_ok=True)
with output_path.open("w", newline="") as f:
    writer = csv.DictWriter(
        f,
        fieldnames=[
            "date", "commodity", "type_label", "origin_code",
            "transport_mode", "weight_lb", "load_count",
            "organic_flag", "source_report"
        ]
    )
    writer.writeheader()
    writer.writerows(rows)

print("ok")
print(output_path)
print("rows:", len(rows))
