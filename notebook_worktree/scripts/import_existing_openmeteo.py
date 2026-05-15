from __future__ import annotations

import json
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = ROOT.parent
PROCESSED_DIR = ROOT / "datamining" / "processed"
REPORT_DIR = ROOT / "reports"


def main() -> None:
    worktree_weather = PROCESSED_DIR / "weather_yearly_2009_2024.csv"
    existing_candidates = [
        PROJECT_ROOT / "data" / "intermediate" / "weather_yearly.csv",
        PROJECT_ROOT / "dataset" / "weather_yearly.csv",
    ]
    frames = []
    if worktree_weather.exists():
        frames.append(pd.read_csv(worktree_weather))
    for path in existing_candidates:
        if path.exists():
            frames.append(pd.read_csv(path))
    if not frames:
        raise FileNotFoundError("No existing Open-Meteo weather_yearly.csv found.")
    weather = pd.concat(frames, ignore_index=True)
    weather = weather.drop_duplicates(["grid_id", "year"], keep="last")
    weather = weather.sort_values(["grid_id", "year"]).reset_index(drop=True)
    weather["cell_mean_temp_2009_2024"] = weather.groupby("grid_id")["avg_temp"].transform("mean")
    weather["temp_anomaly"] = (weather["avg_temp"] - weather["cell_mean_temp_2009_2024"]).round(2)
    weather = weather.drop(columns=["cell_mean_temp_2009_2024"])
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    weather.to_csv(worktree_weather, index=False)
    gbif_path = PROCESSED_DIR / "gbif_diversity_2009_2024.csv"
    coverage = None
    if gbif_path.exists():
        gbif = pd.read_csv(gbif_path, usecols=["grid_id", "year"]).drop_duplicates()
        coverage = len(gbif.merge(weather[["grid_id", "year"]], on=["grid_id", "year"], how="inner")) / len(gbif)
    summary = {
        "rows": int(len(weather)),
        "unique_grid_cells": int(weather["grid_id"].nunique()),
        "year_min": int(weather["year"].min()),
        "year_max": int(weather["year"].max()),
        "gbif_grid_year_coverage": coverage,
        "output": str(worktree_weather.relative_to(ROOT)),
        "sources": [str(path) for path in existing_candidates if path.exists()],
    }
    (REPORT_DIR / "weather_yearly_2009_2024_summary.json").write_text(
        json.dumps(summary, indent=2),
        encoding="utf-8",
    )
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
