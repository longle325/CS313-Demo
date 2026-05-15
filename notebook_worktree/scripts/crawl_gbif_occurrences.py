from __future__ import annotations

import argparse
import csv
import gzip
import json
import time
import urllib.error
import urllib.parse
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests


ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "datamining" / "raw" / "gbif_occurrences_2009_2024"
MANIFEST_PATH = RAW_DIR / "manifest.json"
API_URL = "https://api.gbif.org/v1/occurrence/search"
DEFAULT_LIMIT = 300
USER_AGENT = "CS313-biodiversity-demo/0.1 (GBIF occurrence aggregation; contact: local research project)"
REQUEST_HEADERS = {
    "Accept": "application/json",
    "User-Agent": USER_AGENT,
    "Connection": "close",
}

CSV_FIELDS = [
    "gbifID",
    "datasetKey",
    "publishingOrgKey",
    "basisOfRecord",
    "scientificName",
    "acceptedScientificName",
    "species",
    "speciesKey",
    "taxonRank",
    "kingdom",
    "phylum",
    "class",
    "order",
    "family",
    "genus",
    "decimalLatitude",
    "decimalLongitude",
    "coordinateUncertaintyInMeters",
    "eventDate",
    "year",
    "month",
    "day",
    "individualCount",
    "organismQuantity",
    "organismQuantityType",
    "occurrenceStatus",
    "issues",
    "recordedBy",
    "institutionCode",
    "collectionCode",
    "catalogNumber",
    "license",
    "lastInterpreted",
]


def request_json(params: dict[str, Any], retries: int = 6) -> dict[str, Any]:
    for attempt in range(retries):
        try:
            response = requests.get(API_URL, params=params, headers=REQUEST_HEADERS, timeout=(20, 90))
            response.raise_for_status()
            return response.json()
        except (requests.RequestException, ValueError) as exc:
            if attempt == retries - 1:
                raise
            wait_seconds = min(60, 2**attempt)
            print(f"Request failed ({exc}); retrying in {wait_seconds}s")
            time.sleep(wait_seconds)
    raise RuntimeError("unreachable")


def load_manifest() -> dict[str, Any]:
    if MANIFEST_PATH.exists():
        return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    return {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "source": API_URL,
        "query": {
            "country": "VN",
            "hasCoordinate": True,
            "hasGeospatialIssue": False,
            "occurrenceStatus": "PRESENT",
        },
        "shards": {},
    }


def save_manifest(manifest: dict[str, Any]) -> None:
    manifest["updated_at"] = datetime.now(timezone.utc).isoformat()
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2), encoding="utf-8")


def base_params(year: int, month: int) -> dict[str, Any]:
    return {
        "country": "VN",
        "hasCoordinate": "true",
        "hasGeospatialIssue": "false",
        "occurrenceStatus": "PRESENT",
        "year": year,
        "month": month,
    }


def flatten_record(record: dict[str, Any]) -> dict[str, Any]:
    flattened: dict[str, Any] = {}
    for field in CSV_FIELDS:
        value = record.get(field)
        if field == "gbifID" and value is None:
            value = record.get("key")
        if field == "issues" and isinstance(value, list):
            value = ";".join(value)
        elif isinstance(value, (dict, list)):
            value = json.dumps(value, ensure_ascii=False)
        flattened[field] = value
    return flattened


def count_shard(year: int, month: int) -> int:
    data = request_json({**base_params(year, month), "limit": 0})
    return int(data.get("count", 0))


def crawl_shard(
    year: int,
    month: int,
    count: int,
    limit: int,
    sleep_seconds: float,
    force: bool,
    manifest: dict[str, Any],
) -> None:
    shard_id = f"{year}-{month:02d}"
    final_path = RAW_DIR / f"gbif_vn_{shard_id}.csv.gz"
    temp_path = RAW_DIR / f"gbif_vn_{shard_id}.csv.gz.part"
    existing = manifest["shards"].get(shard_id, {})
    if (
        not force
        and existing.get("status") == "complete"
        and existing.get("records_written") == count
        and final_path.exists()
    ):
        print(f"SKIP {shard_id}: already complete ({count:,})")
        return

    print(f"CRAWL {shard_id}: {count:,} records")
    records_written = 0
    with gzip.open(temp_path, "wt", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_FIELDS)
        writer.writeheader()
        for offset in range(0, count, limit):
            params = {**base_params(year, month), "limit": limit, "offset": offset}
            data = request_json(params)
            results = data.get("results", [])
            for record in results:
                writer.writerow(flatten_record(record))
            records_written += len(results)
            print(f"  {shard_id} offset {offset:,}: +{len(results):,} ({records_written:,}/{count:,})")
            if data.get("endOfRecords") or not results:
                break
            if sleep_seconds:
                time.sleep(sleep_seconds)

    temp_path.replace(final_path)
    manifest["shards"][shard_id] = {
        "year": year,
        "month": month,
        "expected_count": count,
        "records_written": records_written,
        "path": str(final_path.relative_to(ROOT)),
        "status": "complete" if records_written == count else "partial",
    }
    save_manifest(manifest)
    if records_written != count:
        raise RuntimeError(f"{shard_id}: expected {count}, wrote {records_written}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Crawl GBIF Vietnam occurrence records by year-month shards.")
    parser.add_argument("--start-year", type=int, default=2009)
    parser.add_argument("--end-year", type=int, default=2024)
    parser.add_argument("--limit", type=int, default=DEFAULT_LIMIT)
    parser.add_argument("--sleep", type=float, default=0.03)
    parser.add_argument("--count-sleep", type=float, default=0.15)
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--count-only", action="store_true")
    parser.add_argument("--reuse-counts", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    manifest = load_manifest()

    total_expected = 0
    counts: dict[str, int] = {}
    expected_shards = [
        f"{year}-{month:02d}"
        for year in range(args.start_year, args.end_year + 1)
        for month in range(1, 13)
    ]
    manifest_counts = manifest.get("counts", {})
    if args.reuse_counts and all(shard in manifest_counts for shard in expected_shards):
        counts = {shard: int(manifest_counts[shard]) for shard in expected_shards}
        total_expected = sum(counts.values())
        print(f"Reusing {len(counts)} shard counts from manifest.")
    else:
        for year in range(args.start_year, args.end_year + 1):
            for month in range(1, 13):
                count = count_shard(year, month)
                shard_id = f"{year}-{month:02d}"
                counts[shard_id] = count
                total_expected += count
                print(f"COUNT {shard_id}: {count:,}")
                if args.count_sleep:
                    time.sleep(args.count_sleep)

    manifest["start_year"] = args.start_year
    manifest["end_year"] = args.end_year
    manifest["total_expected"] = total_expected
    manifest["counts"] = counts
    save_manifest(manifest)
    print(f"TOTAL expected: {total_expected:,}")

    if args.count_only:
        return

    for year in range(args.start_year, args.end_year + 1):
        for month in range(1, 13):
            shard_id = f"{year}-{month:02d}"
            crawl_shard(
                year=year,
                month=month,
                count=counts[shard_id],
                limit=args.limit,
                sleep_seconds=args.sleep,
                force=args.force,
                manifest=manifest,
            )


if __name__ == "__main__":
    main()
