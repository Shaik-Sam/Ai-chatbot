import csv
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from src.enricher import OUTPUT_FIELDS, CompanyEnricher


ROOT = Path(__file__).resolve().parent.parent
INPUT_PATH = ROOT / "data" / "input.csv"
OUTPUT_PATH = ROOT / "data" / "output.csv"


def build_session():
    session = requests.Session()
    retry = Retry(
        total=2,
        backoff_factor=0.4,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"],
    )
    adapter = HTTPAdapter(max_retries=retry, pool_connections=20, pool_maxsize=20)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    session.headers.update({"User-Agent": "HighperformrAssessmentBot/1.0"})
    return session


def read_rows(path):
    rows = []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            rows.append(
                (
                    row.get("input-company-name", "") or "",
                    row.get("input-company-domain", "") or "",
                )
            )
    return rows


def write_rows(path, enriched_rows):
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=OUTPUT_FIELDS)
        writer.writeheader()
        writer.writerows(enriched_rows)


def enrich_all(rows, workers=8):
    session = build_session()
    enricher = CompanyEnricher(session)
    results = [None] * len(rows)

    def task(index, name, domain):
        time.sleep(index * 0.02)
        return index, enricher.enrich_row(name, domain)

    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = [
            executor.submit(task, index, name, domain)
            for index, (name, domain) in enumerate(rows)
        ]
        completed = 0
        total = len(futures)
        for future in as_completed(futures):
            index, row = future.result()
            results[index] = row
            completed += 1
            if completed % 25 == 0 or completed == total:
                print(f"Processed {completed}/{total}", flush=True)
    return results


def main():
    input_path = Path(sys.argv[1]) if len(sys.argv) > 1 else INPUT_PATH
    output_path = Path(sys.argv[2]) if len(sys.argv) > 2 else OUTPUT_PATH
    rows = read_rows(input_path)
    print(f"Loaded {len(rows)} rows from {input_path}", flush=True)
    enriched = enrich_all(rows)
    write_rows(output_path, enriched)
    filled_names = sum(1 for row in enriched if row["company-name"])
    filled_domains = sum(1 for row in enriched if row["company-domain"])
    filled_linkedin = sum(1 for row in enriched if row["company-linkedin-url"])
    filled_ceo = sum(1 for row in enriched if row["ceo-founder-name"])
    print(f"Saved {len(enriched)} rows to {output_path}", flush=True)
    print(
        f"Coverage: names={filled_names}, domains={filled_domains}, "
        f"linkedin={filled_linkedin}, ceo_founder={filled_ceo}",
        flush=True,
    )


if __name__ == "__main__":
    main()
