from __future__ import annotations

import argparse
import hashlib
import json
import math
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd
import requests


ROOT = Path(__file__).resolve().parents[1]
PROCESSED_DIR = ROOT / "datamining" / "processed"
RAW_DIR = ROOT / "datamining" / "raw" / "openmeteo_api_fast_gridyears_2009_2024"
REPORT_DIR = ROOT / "reports"
API_URL = "https://archive-api.open-meteo.com/v1/archive"
DAILY_VARS = "temperature_2m_mean,temperature_2m_max,precipitation_sum"
HEADERS = {"User-Agent": "CS313-biodiversity-research/0.2"}


def chunked(items: list[dict[str, Any]], size: int) -> list[list[dict[str, Any]]]:
    return [items[index : index + size] for index in range(0, len(items), size)]


def consecutive_ranges(years: list[int]) -> list[tuple[int, int]]:
    if not years:
        return []
    years = sorted(set(years))
    ranges: list[tuple[int, int]] = []
    start = prev = years[0]
    for year in years[1:]:
        if year == prev + 1:
            prev = year
            continue
        ranges.append((start, prev))
        start = prev = year
    ranges.append((start, prev))
    return ranges


def load_diversity() -> pd.DataFrame:
    diversity_path = PROCESSED_DIR / "gbif_diversity_2009_2024.csv"
    if not diversity_path.exists():
        raise FileNotFoundError(f"Missing {diversity_path}")
    return pd.read_csv(diversity_path, usecols=["grid_id", "lat", "lon", "year"])


def load_target_cells(diversity: pd.DataFrame) -> pd.DataFrame:
    return diversity[["grid_id", "lat", "lon"]].drop_duplicates("grid_id").sort_values("grid_id").reset_index(drop=True)


def load_existing_weather() -> pd.DataFrame:
    weather_path = PROCESSED_DIR / "weather_yearly_2009_2024.csv"
    if not weather_path.exists():
        return pd.DataFrame()
    weather = pd.read_csv(weather_path)
    return weather.drop_duplicates(["grid_id", "year"], keep="last")


def build_tasks(
    diversity: pd.DataFrame,
    cells: pd.DataFrame,
    existing: pd.DataFrame,
    start_year: int,
    end_year: int,
    needed_grid_years_only: bool,
) -> list[dict[str, Any]]:
    if needed_grid_years_only:
        wanted_by_grid = (
            diversity[(diversity["year"] >= start_year) & (diversity["year"] <= end_year)]
            .groupby("grid_id")["year"]
            .apply(lambda series: set(series.astype(int)))
            .to_dict()
        )
    else:
        all_years = set(range(start_year, end_year + 1))
        wanted_by_grid = {grid_id: all_years for grid_id in cells["grid_id"]}
    existing_years = (
        existing.groupby("grid_id")["year"].apply(lambda series: set(series.astype(int))).to_dict()
        if not existing.empty
        else {}
    )
    tasks: list[dict[str, Any]] = []
    for row in cells.itertuples(index=False):
        missing_years = sorted(wanted_by_grid.get(row.grid_id, set()) - existing_years.get(row.grid_id, set()))
        for range_start, range_end in [(year, year) for year in missing_years]:
            tasks.append(
                {
                    "grid_id": row.grid_id,
                    "lat": float(row.lat),
                    "lon": float(row.lon),
                    "start_year": range_start,
                    "end_year": range_end,
                }
            )
    return tasks


def aggregate_payload(cell: dict[str, Any], payload: dict[str, Any]) -> list[dict[str, Any]]:
    daily = payload.get("daily", {})
    if not daily or "time" not in daily:
        return []
    frame = pd.DataFrame(
        {
            "date": pd.to_datetime(daily["time"]),
            "temp_mean": pd.to_numeric(pd.Series(daily.get("temperature_2m_mean")), errors="coerce"),
            "temp_max": pd.to_numeric(pd.Series(daily.get("temperature_2m_max")), errors="coerce"),
            "precip": pd.to_numeric(pd.Series(daily.get("precipitation_sum")), errors="coerce"),
        }
    ).dropna(subset=["date"])
    frame["year"] = frame["date"].dt.year
    rows: list[dict[str, Any]] = []
    for year, group in frame.groupby("year"):
        if int(year) < cell["start_year"] or int(year) > cell["end_year"]:
            continue
        rows.append(
            {
                "grid_id": cell["grid_id"],
                "year": int(year),
                "avg_temp": round(float(group["temp_mean"].mean()), 2),
                "total_rainfall_mm": round(float(group["precip"].sum()), 2),
                "n_dry_days": int((group["precip"] < 1.0).sum()),
                "n_hot_days": int((group["temp_max"] > 35.0).sum()),
            }
        )
    return rows


def request_batch(batch: list[dict[str, Any]], model: str, attempt: int) -> list[dict[str, Any]]:
    start_year = batch[0]["start_year"]
    end_year = batch[0]["end_year"]
    params = {
        "latitude": ",".join(f"{item['lat']:.4f}" for item in batch),
        "longitude": ",".join(f"{item['lon']:.4f}" for item in batch),
        "start_date": f"{start_year}-01-01",
        "end_date": f"{end_year}-12-31",
        "daily": DAILY_VARS,
        "timezone": "Asia/Ho_Chi_Minh",
        "models": model,
        "cell_selection": "nearest",
    }
    response = requests.get(API_URL, params=params, headers=HEADERS, timeout=(30, 180))
    if response.status_code == 429:
        retry_after = int(response.headers.get("Retry-After", 3700))
        raise RuntimeError(f"rate_limited:{retry_after}")
    response.raise_for_status()
    payload = response.json()
    payloads = payload if isinstance(payload, list) else [payload]
    rows: list[dict[str, Any]] = []
    for cell, cell_payload in zip(batch, payloads, strict=False):
        rows.extend(aggregate_payload(cell, cell_payload))
    return rows


def batch_output_path(batch_id: int, batch: list[dict[str, Any]]) -> Path:
    year = int(batch[0]["start_year"])
    signature = "|".join(
        f"{item['grid_id']}:{item['start_year']}-{item['end_year']}"
        for item in batch
    )
    digest = hashlib.sha1(signature.encode("utf-8")).hexdigest()[:10]
    return RAW_DIR / f"api_y{year}_batch_{batch_id:05d}_{digest}.csv"


def fetch_batch(batch_id: int, batch: list[dict[str, Any]], args: argparse.Namespace) -> dict[str, Any]:
    out_path = batch_output_path(batch_id, batch)
    if out_path.exists() and not args.force:
        return {"batch_id": batch_id, "status": "skipped", "rows": None}
    for attempt in range(1, args.max_retries + 1):
        try:
            rows = request_batch(batch, args.model, attempt)
            pd.DataFrame(rows).to_csv(out_path, index=False)
            time.sleep(args.sleep)
            return {"batch_id": batch_id, "status": "complete", "rows": len(rows)}
        except Exception as exc:
            message = str(exc)
            if message.startswith("rate_limited:"):
                wait_seconds = int(message.split(":", 1)[1])
            else:
                wait_seconds = min(args.max_backoff, args.base_backoff * (2 ** (attempt - 1)))
            if attempt == args.max_retries:
                return {"batch_id": batch_id, "status": "failed", "error": repr(exc)}
            time.sleep(wait_seconds + min(5, batch_id % 5))
    return {"batch_id": batch_id, "status": "failed", "error": "unreachable"}


def combine_weather(existing: pd.DataFrame) -> pd.DataFrame:
    files = sorted({*RAW_DIR.glob("api_batch_*.csv"), *RAW_DIR.glob("api_y*_batch_*.csv")})
    frames = []
    if not existing.empty:
        frames.append(existing)
    frames.extend(pd.read_csv(path) for path in files if path.stat().st_size > 0)
    if not frames:
        raise RuntimeError("No Open-Meteo API weather rows to combine")
    yearly = pd.concat(frames, ignore_index=True)
    yearly = yearly.drop_duplicates(["grid_id", "year"], keep="last")
    yearly = yearly.sort_values(["grid_id", "year"]).reset_index(drop=True)
    yearly["cell_mean_temp_2009_2024"] = yearly.groupby("grid_id")["avg_temp"].transform("mean")
    yearly["temp_anomaly"] = (yearly["avg_temp"] - yearly["cell_mean_temp_2009_2024"]).round(2)
    yearly = yearly.drop(columns=["cell_mean_temp_2009_2024"])
    yearly.to_csv(PROCESSED_DIR / "weather_yearly_2009_2024.csv", index=False)
    return yearly


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Fast Open-Meteo historical API crawler for GBIF grid cells.")
    parser.add_argument("--start-year", type=int, default=2009)
    parser.add_argument("--end-year", type=int, default=2024)
    parser.add_argument("--batch-size", type=int, default=50)
    parser.add_argument("--workers", type=int, default=1)
    parser.add_argument("--model", default="era5")
    parser.add_argument("--sleep", type=float, default=0.05)
    parser.add_argument("--max-retries", type=int, default=4)
    parser.add_argument("--base-backoff", type=int, default=20)
    parser.add_argument("--max-backoff", type=int, default=3700)
    parser.add_argument(
        "--all-cell-years",
        action="store_true",
        help="Fetch every year for every GBIF grid cell. Default fetches only grid-years present in the GBIF modeling target.",
    )
    parser.add_argument("--force", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    diversity = load_diversity()
    cells = load_target_cells(diversity)
    existing = load_existing_weather()
    tasks = build_tasks(diversity, cells, existing, args.start_year, args.end_year, not args.all_cell_years)
    grouped: dict[int, list[dict[str, Any]]] = {}
    for task in tasks:
        grouped.setdefault(task["start_year"], []).append(task)
    batches: list[list[dict[str, Any]]] = []
    for _, group_tasks in sorted(grouped.items()):
        batches.extend(chunked(group_tasks, args.batch_size))
    print(
        f"Open-Meteo API plan: {len(cells):,} GBIF cells, {len(tasks):,} missing target cell-ranges, "
        f"{len(batches):,} HTTP requests with batch_size={args.batch_size}, workers={args.workers}"
    , flush=True)
    started_at = datetime.now(timezone.utc)
    results: list[dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = {
            executor.submit(fetch_batch, batch_id, batch, args): batch_id
            for batch_id, batch in enumerate(batches)
        }
        for index, future in enumerate(as_completed(futures), start=1):
            result = future.result()
            results.append(result)
            if index % 10 == 0 or result["status"] == "failed":
                complete = sum(1 for item in results if item["status"] in {"complete", "skipped"})
                failed = sum(1 for item in results if item["status"] == "failed")
                print(f"Progress {index}/{len(batches)} done; complete={complete}, failed={failed}", flush=True)
    failed = [result for result in results if result["status"] == "failed"]
    manifest = {
        "created_at": started_at.isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "api": API_URL,
        "model": args.model,
        "daily": DAILY_VARS,
        "target_cells": int(len(cells)),
        "missing_cell_ranges": int(len(tasks)),
        "batches": int(len(batches)),
        "batch_size": args.batch_size,
        "workers": args.workers,
        "failed": failed,
    }
    (REPORT_DIR / "openmeteo_api_fast_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    if failed:
        raise RuntimeError(f"{len(failed)} Open-Meteo API batches failed; see openmeteo_api_fast_manifest.json")
    yearly = combine_weather(existing)
    target_keys = pd.read_csv(PROCESSED_DIR / "gbif_diversity_2009_2024.csv", usecols=["grid_id", "year"]).drop_duplicates()
    coverage = len(target_keys.merge(yearly[["grid_id", "year"]], on=["grid_id", "year"], how="inner")) / max(len(target_keys), 1)
    summary = {
        "rows": int(len(yearly)),
        "unique_grid_cells": int(yearly["grid_id"].nunique()),
        "year_min": int(yearly["year"].min()),
        "year_max": int(yearly["year"].max()),
        "gbif_grid_year_coverage": float(coverage),
        "output": "datamining/processed/weather_yearly_2009_2024.csv",
    }
    (REPORT_DIR / "weather_yearly_2009_2024_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
