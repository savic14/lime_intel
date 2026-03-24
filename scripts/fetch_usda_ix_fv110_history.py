from __future__ import annotations

from pathlib import Path
from datetime import date, timedelta, datetime
import argparse
import csv
import re
import requests


RAW_DIR = Path("data/raw/usda_ix_fv110")
INDEX_CSV = Path("data/processed/usda_ix_fv110_file_index.csv")

TIMEOUT = 60


def daterange(start: date, end: date):
    current = start
    while current <= end:
        yield current
        current += timedelta(days=1)


def build_candidate_urls(d: date) -> list[tuple[str, str]]:
    """
    Devuelve candidatos de URL para una fecha.
    Formato:
      - antiguos: TXT tipo IX_FV110YYYYMMDD.TXT
      - transición y nuevos: txt/pdf tipo ams_2402_xxxxx.txt/.pdf
    Ojo: los IDs numéricos de carpeta/archivo no se pueden inferir perfecto.
    Esta v1 usa rutas conocidas cuando existan en índice previo o intenta variantes simples.
    """
    ymd = d.strftime("%Y-%m-%d")
    ymd_compact = d.strftime("%Y%m%d")

    candidates: list[tuple[str, str]] = []

    # Patrón antiguo TXT
    candidates.append((
        "TXT_OLD",
        f"https://mymarketnews.ams.usda.gov/filerepo/sites/default/files/2402/{ymd}/UNKNOWN/IX_FV110{ymd_compact}.TXT"
    ))

    # Patrones MARS nuevos; el id numérico no lo sabemos aún
    candidates.append((
        "TXT_NEW",
        f"https://mymarketnews.ams.usda.gov/filerepo/sites/default/files/2402/{ymd}/UNKNOWN/ams_2402_UNKNOWN.txt"
    ))
    candidates.append((
        "PDF_NEW",
        f"https://mymarketnews.ams.usda.gov/filerepo/sites/default/files/2402/{ymd}/UNKNOWN/ams_2402_UNKNOWN.pdf"
    ))

    return candidates


def head_or_get(url: str) -> requests.Response | None:
    try:
        r = requests.get(url, timeout=TIMEOUT, allow_redirects=True)
        if r.status_code == 200 and r.content:
            return r
    except Exception:
        return None
    return None


def ensure_dirs():
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    INDEX_CSV.parent.mkdir(parents=True, exist_ok=True)


def append_index(rows: list[dict]):
    file_exists = INDEX_CSV.exists()
    with INDEX_CSV.open("a", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["report_date", "source_format", "url", "local_path", "status"]
        )
        if not file_exists:
            writer.writeheader()
        writer.writerows(rows)


def load_known_urls() -> dict[str, dict[str, str]]:
    """
    Índice manual de URLs conocidas. Aquí puedes ir agregando las que ya detectamos.
    """
    return {
        "2017-10-02": {
            "source_format": "TXT",
            "url": "https://mymarketnews.ams.usda.gov/filerepo/sites/default/files/2402/2017-10-02/782524/IX_FV11020171002.TXT",
        },
        "2024-05-15": {
            "source_format": "TXT",
            "url": "https://mymarketnews.ams.usda.gov/filerepo/sites/default/files/2402/2024-05-15/1120236/ams_2402_01060.txt",
        },
        "2024-05-16": {
            "source_format": "PDF",
            "url": "https://mymarketnews.ams.usda.gov/filere/sites/default/files/2402/2024-05-16/1120594/ams_2402_01061.pdf",
        },
        "2026-03-02": {
            "source_format": "PDF",
            "url": "https://mymarketnews.ams.usda.gov/filerepo/sites/default/files/2402/2026-03-02/1307941/ams_2402_01502.pdf",
        },
        "2026-03-17": {
            "source_format": "PDF",
            "url": "https://mymarketnews.ams.usda.gov/filerepo/sites/default/files/2402/2026-03-17/1311413/ams_2402_01513.pdf",
        },
    }


def safe_suffix_from_format(source_format: str) -> str:
    return ".txt" if source_format.upper() == "TXT" else ".pdf"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", required=True, help="YYYY-MM-DD")
    parser.add_argument("--end", required=True, help="YYYY-MM-DD")
    args = parser.parse_args()

    start = datetime.strptime(args.start, "%Y-%m-%d").date()
    end = datetime.strptime(args.end, "%Y-%m-%d").date()

    ensure_dirs()
    known = load_known_urls()

    rows_to_append: list[dict] = []

    for d in daterange(start, end):
        ds = d.strftime("%Y-%m-%d")

        if ds in known:
            meta = known[ds]
            url = meta["url"]
            source_format = meta["source_format"]
            suffix = safe_suffix_from_format(source_format)
            local_path = RAW_DIR / f"{ds}{suffix}"

            if not local_path.exists():
                r = head_or_get(url)
                if r is not None:
                    local_path.write_bytes(r.content)
                    status = "downloaded"
                else:
                    status = "failed_known_url"
            else:
                status = "already_exists"

            rows_to_append.append({
                "report_date": ds,
                "source_format": source_format,
                "url": url,
                "local_path": str(local_path),
                "status": status,
            })
            print(ds, source_format, status)
        else:
            rows_to_append.append({
                "report_date": ds,
                "source_format": "",
                "url": "",
                "local_path": "",
                "status": "unknown_url_pattern",
            })
            print(ds, "UNKNOWN", "unknown_url_pattern")

    append_index(rows_to_append)
    print("ok")
    print(INDEX_CSV)


if __name__ == "__main__":
    main()
