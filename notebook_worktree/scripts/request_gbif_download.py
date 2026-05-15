from __future__ import annotations

import argparse
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from zipfile import ZipFile

import requests


ROOT = Path(__file__).resolve().parents[1]
DOWNLOAD_DIR = ROOT / "datamining" / "raw" / "gbif_download_2009_2024"
REQUEST_URL = "https://api.gbif.org/v1/occurrence/download/request"
STATUS_URL = "https://api.gbif.org/v1/occurrence/download/{key}"
HEADERS = {"User-Agent": "CS313-biodiversity-demo/0.1", "Connection": "close"}


def get_with_retries(url: str, *, stream: bool = False, retries: int = 6) -> requests.Response:
    for attempt in range(retries):
        try:
            response = requests.get(url, stream=stream, timeout=(30, 180), headers=HEADERS)
            response.raise_for_status()
            return response
        except requests.RequestException:
            if attempt == retries - 1:
                raise
            time.sleep(min(60, 2**attempt))
    raise RuntimeError("unreachable")


def build_payload(username: str, email: str, start_year: int, end_year: int) -> dict:
    return {
        "creator": username,
        "notificationAddresses": [email],
        "format": "SIMPLE_CSV",
        "predicate": {
            "type": "and",
            "predicates": [
                {"type": "equals", "key": "COUNTRY", "value": "VN", "matchCase": False},
                {"type": "equals", "key": "HAS_COORDINATE", "value": "true", "matchCase": False},
                {"type": "equals", "key": "HAS_GEOSPATIAL_ISSUE", "value": "false", "matchCase": False},
                {"type": "equals", "key": "OCCURRENCE_STATUS", "value": "present", "matchCase": False},
                {"type": "greaterThanOrEquals", "key": "YEAR", "value": str(start_year), "matchCase": False},
                {"type": "lessThanOrEquals", "key": "YEAR", "value": str(end_year), "matchCase": False},
            ],
        },
    }


def submit_download(username: str, password: str, email: str, start_year: int, end_year: int) -> str:
    payload = build_payload(username, email, start_year, end_year)
    DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)
    (DOWNLOAD_DIR / "request_payload.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    response = requests.post(
        REQUEST_URL,
        auth=(username, password),
        json=payload,
        timeout=(20, 90),
        headers=HEADERS,
    )
    if response.status_code >= 400:
        raise RuntimeError(f"GBIF download request failed: {response.status_code} {response.text[:1000]}")
    response.raise_for_status()
    key = response.text.strip().strip('"')
    (DOWNLOAD_DIR / "download_key.txt").write_text(key, encoding="utf-8")
    return key


def poll_status(key: str, wait_seconds: int) -> dict:
    while True:
        response = get_with_retries(STATUS_URL.format(key=key))
        status = response.json()
        state = status.get("status")
        print(f"{datetime.now(timezone.utc).isoformat()} {key}: {state}")
        (DOWNLOAD_DIR / "download_status.json").write_text(json.dumps(status, indent=2), encoding="utf-8")
        if state in {"SUCCEEDED", "KILLED", "CANCELLED", "FAILED"}:
            return status
        time.sleep(wait_seconds)


def download_zip(status: dict) -> Path:
    download_link = status.get("downloadLink")
    key = status.get("key")
    if not download_link:
        download_link = f"https://api.gbif.org/v1/occurrence/download/request/{key}.zip"
    zip_path = DOWNLOAD_DIR / f"{key}.zip"
    with get_with_retries(download_link, stream=True) as response:
        with zip_path.open("wb") as handle:
            for chunk in response.iter_content(chunk_size=1024 * 1024):
                if chunk:
                    handle.write(chunk)
    with ZipFile(zip_path) as archive:
        archive.extractall(DOWNLOAD_DIR / key)
    return zip_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Submit and download an official GBIF occurrence download.")
    parser.add_argument("--start-year", type=int, default=2009)
    parser.add_argument("--end-year", type=int, default=2024)
    parser.add_argument("--poll", action="store_true")
    parser.add_argument("--download", action="store_true")
    parser.add_argument("--wait-seconds", type=int, default=60)
    parser.add_argument("--key", default=os.environ.get("GBIF_DOWNLOAD_KEY"))
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)
    key = args.key
    if not key:
        username = os.environ.get("GBIF_USERNAME")
        password = os.environ.get("GBIF_PASSWORD")
        email = os.environ.get("GBIF_EMAIL")
        missing = [
            name
            for name, value in [
                ("GBIF_USERNAME", username),
                ("GBIF_PASSWORD", password),
                ("GBIF_EMAIL", email),
            ]
            if not value
        ]
        if missing:
            raise SystemExit(
                "Missing GBIF credentials: "
                + ", ".join(missing)
                + ". Set them in the shell to submit an official DOI-backed download."
            )
        key = submit_download(username, password, email, args.start_year, args.end_year)
        print(f"Submitted GBIF download: {key}")

    if args.poll or args.download:
        status = poll_status(key, args.wait_seconds)
        if status.get("status") != "SUCCEEDED":
            raise SystemExit(f"GBIF download did not succeed: {status.get('status')}")
        if args.download:
            zip_path = download_zip(status)
            print(f"Downloaded and extracted: {zip_path}")


if __name__ == "__main__":
    main()
