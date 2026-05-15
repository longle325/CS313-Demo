from __future__ import annotations

import argparse
import json
import shutil
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = ROOT.parent
PROCESSED_DIR = ROOT / "datamining" / "processed"
NOTEBOOK_INPUT_DIR = ROOT / "datamining" / "dataset-2"
REPORT_DIR = ROOT / "reports"
OLD_INPUT_DIR = PROJECT_ROOT / "datamining" / "dataset-2"

YEARS_ALL = list(range(2009, 2025))
YEARS_NOTEBOOK = list(range(2019, 2025))
NORMALIZATION_CAP_Q = 0.99
NORMALIZATION_CAP_TRAIN_CUTOFF_YEAR = 2024


def read_csv(path: Path, columns: list[str] | None = None) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(path)
    return pd.read_csv(path, usecols=columns)


def parse_grid_coordinates(df: pd.DataFrame) -> pd.DataFrame:
    coords = df["grid_id"].astype(str).str.extract(r"^VN_([-0-9.]+)_([-0-9.]+)$")
    out = df.copy()
    out["lat"] = pd.to_numeric(coords[0], errors="coerce")
    out["lon"] = pd.to_numeric(coords[1], errors="coerce")
    return out


def filter_vietnam_bbox(df: pd.DataFrame) -> pd.DataFrame:
    out = parse_grid_coordinates(df)
    return out[out["lat"].between(8, 23.6) & out["lon"].between(102, 110.1)].copy()


def load_augmented_gbif() -> tuple[pd.DataFrame, dict]:
    current = read_csv(
        PROCESSED_DIR / "gbif_diversity_2009_2024.csv",
        ["grid_id", "year", "n_observations", "n_species"],
    )
    current["source"] = "gbif_2009_2024_current"

    old = read_csv(
        OLD_INPUT_DIR / "gbif_cleaned.csv",
        ["grid_id", "year", "n_observations", "n_species"],
    )
    old["source"] = "gbif_2019_2024_old_notebook"

    combined = pd.concat([current, old], ignore_index=True)
    combined = filter_vietnam_bbox(combined)
    combined = combined.dropna(subset=["grid_id", "year"])
    combined["year"] = combined["year"].astype(int)
    combined = combined[combined["year"].isin(YEARS_ALL)]

    # Assumption: both old and current GBIF tables are already grid-year aggregates.
    # For duplicate grid-years, take the larger aggregate rather than summing, so
    # overlapping crawls do not double-count observations/species.
    augmented = (
        combined.groupby(["grid_id", "year"], as_index=False)
        .agg(
            n_observations=("n_observations", "max"),
            n_species=("n_species", "max"),
            sources=("source", lambda values: "+".join(sorted(set(values)))),
        )
        .sort_values(["grid_id", "year"])
        .reset_index(drop=True)
    )
    invalid_after_aggregation = int(((augmented["n_observations"] <= 0) | (augmented["n_species"] < 1)).sum())
    augmented = augmented[(augmented["n_observations"] > 0) & (augmented["n_species"] >= 1)].copy()

    stats = {
        "current_gbif_rows": int(len(current)),
        "old_gbif_rows": int(len(old)),
        "augmented_gbif_rows": int(len(augmented)),
        "augmented_gbif_grids": int(augmented["grid_id"].nunique()),
        "invalid_aggregate_rows_dropped": invalid_after_aggregation,
        "old_keys_added_to_current": int(
            len(
                old[["grid_id", "year"]]
                .drop_duplicates()
                .merge(
                    current[["grid_id", "year"]].drop_duplicates(),
                    on=["grid_id", "year"],
                    how="left",
                    indicator=True,
                )
                .query("_merge == 'left_only'")
            )
        ),
    }
    return augmented, stats


def load_environment_tables() -> tuple[pd.DataFrame, pd.DataFrame]:
    forest = read_csv(PROCESSED_DIR / "forest_stats_2009_2024.csv")
    weather = read_csv(PROCESSED_DIR / "weather_yearly_2009_2024.csv")

    forest = forest[forest["year"].isin(YEARS_ALL)].copy()
    weather = weather[weather["year"].isin(YEARS_ALL)].copy()
    forest["year"] = forest["year"].astype(int)
    weather["year"] = weather["year"].astype(int)

    # Recompute anomaly against each cell's available 2009-2024 climate baseline.
    if "avg_temp" in weather.columns:
        weather["temp_anomaly"] = weather["avg_temp"] - weather.groupby("grid_id")["avg_temp"].transform("mean")

    forest = forest.drop_duplicates(["grid_id", "year"]).sort_values(["grid_id", "year"])
    weather = weather.drop_duplicates(["grid_id", "year"]).sort_values(["grid_id", "year"])
    return forest, weather


def add_targets(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    out = df.copy()
    out["effort_adjusted_richness"] = out["n_species"] / np.log1p(out["n_observations"])
    cap_source = out[out["year"] < NORMALIZATION_CAP_TRAIN_CUTOFF_YEAR]["effort_adjusted_richness"]
    cap = float(cap_source.quantile(NORMALIZATION_CAP_Q))
    if not np.isfinite(cap) or cap <= 0:
        raise ValueError("Cannot compute a positive normalization cap.")
    out["normalized_richness"] = (out["effort_adjusted_richness"].clip(upper=cap) / cap).clip(0, 1)
    out["normalized_richness_01"] = out["normalized_richness"]
    return out, {
        "normalization_formula": "clip(n_species / log1p(n_observations), p99_train_years_before_2024) / p99_cap",
        "normalization_cap_quantile": NORMALIZATION_CAP_Q,
        "normalization_cap_train_cutoff_year": NORMALIZATION_CAP_TRAIN_CUTOFF_YEAR,
        "normalization_cap": cap,
        "target_min": float(out["normalized_richness"].min()),
        "target_max": float(out["normalized_richness"].max()),
    }


def panel_stats(df: pd.DataFrame, years: list[int]) -> dict:
    sub = df[df["year"].isin(years)].copy()
    counts = sub.groupby("grid_id")["year"].nunique()
    required = len(years)
    expected = int(len(counts) * required)
    complete_grids = int((counts == required).sum())
    distribution = {str(int(k)): int(v) for k, v in counts.value_counts().sort_index().items()}
    return {
        "year_min": int(min(years)),
        "year_max": int(max(years)),
        "rows": int(len(sub)),
        "unique_grid_cells": int(sub["grid_id"].nunique()),
        "expected_rows_if_each_observed_grid_has_all_years": expected,
        "missing_rows_on_observed_grid_panel": int(expected - len(sub)),
        "complete_grid_cells": complete_grids,
        "complete_rows": int(complete_grids * required),
        "avg_years_per_grid": float(counts.mean()) if len(counts) else 0.0,
        "grid_year_count_distribution": distribution,
        "rows_by_year": {str(int(k)): int(v) for k, v in sub["year"].value_counts().sort_index().items()},
    }


def rolling_window_stats(df: pd.DataFrame, window: int = 6) -> list[dict]:
    stats = []
    for start in range(min(YEARS_ALL), max(YEARS_ALL) - window + 2):
        years = list(range(start, start + window))
        sub = df[df["year"].isin(years)]
        counts = sub.groupby("grid_id")["year"].nunique()
        complete_grids = int((counts == window).sum())
        stats.append(
            {
                "start_year": start,
                "end_year": start + window - 1,
                "rows": int(len(sub)),
                "unique_grid_cells": int(sub["grid_id"].nunique()),
                "complete_grid_cells": complete_grids,
                "complete_rows": int(complete_grids * window),
            }
        )
    return stats


def write_with_backup(outputs: dict[str, pd.DataFrame], overwrite_notebook_inputs: bool) -> dict[str, str]:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    written: dict[str, str] = {}

    for filename, df in outputs.items():
        path = PROCESSED_DIR / filename
        df.to_csv(path, index=False)
        written[filename] = str(path)

    if overwrite_notebook_inputs:
        backup_dir = NOTEBOOK_INPUT_DIR / f"_previous_inputs_{timestamp}"
        backup_dir.mkdir(parents=True, exist_ok=True)
        for filename in ["gbif_cleaned.csv", "forest_stats.csv", "weather_yearly.csv", "dataset.csv"]:
            existing = NOTEBOOK_INPUT_DIR / filename
            if existing.exists():
                shutil.copy2(existing, backup_dir / filename)

        notebook_files = {
            "gbif_cleaned.csv": outputs["gbif_cleaned_augmented_2009_2024.csv"],
            "forest_stats.csv": outputs["forest_stats_notebook_2009_2024.csv"],
            "weather_yearly.csv": outputs["weather_yearly_notebook_2009_2024.csv"],
            "dataset.csv": outputs["dataset_augmented_2009_2024_inner.csv"],
        }
        for filename, df in notebook_files.items():
            path = NOTEBOOK_INPUT_DIR / filename
            df.to_csv(path, index=False)
            written[f"notebook/{filename}"] = str(path)
        written["notebook_backup_dir"] = str(backup_dir)

    return written


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--overwrite-notebook-inputs", action="store_true")
    args = parser.parse_args()

    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    gbif_augmented, gbif_stats = load_augmented_gbif()
    forest, weather = load_environment_tables()

    merged = gbif_augmented.merge(weather, on=["grid_id", "year"], how="inner")
    merged = merged.merge(forest, on=["grid_id", "year"], how="inner")
    merged = parse_grid_coordinates(merged)
    merged, target_stats = add_targets(merged)
    merged = merged.sort_values(["grid_id", "year"]).reset_index(drop=True)

    complete_2019_grids = (
        merged[merged["year"].isin(YEARS_NOTEBOOK)]
        .groupby("grid_id")["year"]
        .nunique()
        .loc[lambda series: series == len(YEARS_NOTEBOOK)]
        .index
    )
    balanced_2019 = merged[
        merged["year"].isin(YEARS_NOTEBOOK) & merged["grid_id"].isin(complete_2019_grids)
    ].copy()

    complete_2009_grids = (
        merged[merged["year"].isin(YEARS_ALL)]
        .groupby("grid_id")["year"]
        .nunique()
        .loc[lambda series: series == len(YEARS_ALL)]
        .index
    )
    balanced_2009 = merged[merged["grid_id"].isin(complete_2009_grids)].copy()

    gbif_notebook = gbif_augmented[["grid_id", "year", "n_observations", "n_species"]].copy()
    dataset_columns = [
        "grid_id",
        "lat",
        "lon",
        "year",
        "forest_cover_pct",
        "forest_loss_ha",
        "forest_loss_pct_change",
        "avg_temp",
        "total_rainfall_mm",
        "n_dry_days",
        "n_hot_days",
        "temp_anomaly",
        "n_observations",
        "n_species",
        "effort_adjusted_richness",
        "normalized_richness",
        "normalized_richness_01",
    ]
    outputs = {
        "gbif_cleaned_augmented_2009_2024.csv": gbif_notebook,
        "gbif_cleaned_augmented_sources_2009_2024.csv": gbif_augmented,
        "forest_stats_notebook_2009_2024.csv": forest,
        "weather_yearly_notebook_2009_2024.csv": weather,
        "dataset_augmented_2009_2024_inner.csv": merged[dataset_columns],
        "dataset_augmented_2019_2024_inner.csv": merged[merged["year"].isin(YEARS_NOTEBOOK)][dataset_columns],
        "dataset_augmented_2019_2024_balanced.csv": balanced_2019[dataset_columns],
        "dataset_augmented_2009_2024_balanced.csv": balanced_2009[dataset_columns],
    }

    written = write_with_backup(outputs, args.overwrite_notebook_inputs)

    current_only = read_csv(PROCESSED_DIR / "biodiversity_modeling_dataset_2009_2024.csv")
    current_only_inner = current_only.dropna(
        subset=["avg_temp", "total_rainfall_mm", "n_dry_days", "n_hot_days", "forest_cover_pct"]
    )

    report = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "gbif_augmentation": gbif_stats,
        "environment_tables": {
            "forest_rows": int(len(forest)),
            "forest_grid_cells": int(forest["grid_id"].nunique()),
            "weather_rows": int(len(weather)),
            "weather_grid_cells": int(weather["grid_id"].nunique()),
        },
        "target": target_stats,
        "current_only_inner_panel": {
            "panel_2019_2024": panel_stats(current_only_inner, YEARS_NOTEBOOK),
            "panel_2009_2024": panel_stats(current_only_inner, YEARS_ALL),
            "rolling_6_year_windows": rolling_window_stats(current_only_inner),
        },
        "augmented_inner_panel": {
            "panel_2019_2024": panel_stats(merged, YEARS_NOTEBOOK),
            "panel_2009_2024": panel_stats(merged, YEARS_ALL),
            "rolling_6_year_windows": rolling_window_stats(merged),
        },
        "outputs": written,
    }

    json_path = REPORT_DIR / "data_sufficiency_report_2009_2024.json"
    json_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

    md_path = REPORT_DIR / "data_sufficiency_report_2009_2024.md"
    augmented_2019 = report["augmented_inner_panel"]["panel_2019_2024"]
    augmented_all = report["augmented_inner_panel"]["panel_2009_2024"]
    current_2019 = report["current_only_inner_panel"]["panel_2019_2024"]
    best_window = max(
        report["augmented_inner_panel"]["rolling_6_year_windows"],
        key=lambda item: item["complete_grid_cells"],
    )
    md_path.write_text(
        "\n".join(
            [
                "# Data sufficiency report 2009-2024",
                "",
                "## Main conclusion",
                "",
                "- The environmental covariates are broad enough: forest is complete for the grid, weather covers most GBIF grid-years.",
                "- The bottleneck is still GBIF target-label continuity, not forest/weather coverage.",
                "- The augmented 2019-2024 merged panel has "
                f"{augmented_2019['rows']:,} rows over {augmented_2019['unique_grid_cells']:,} grids; "
                f"{augmented_2019['complete_grid_cells']:,} grids have all 6 years.",
                "- Strict LSTM/GRU training on complete 6-year sequences is still thin unless using masking/sparse sequences.",
                "",
                "## Key numbers",
                "",
                f"- Current-only 2019-2024 inner rows: {current_2019['rows']:,}",
                f"- Augmented 2019-2024 inner rows: {augmented_2019['rows']:,}",
                f"- Missing rows if all augmented observed grids had 6 years: {augmented_2019['missing_rows_on_observed_grid_panel']:,}",
                f"- Augmented 2009-2024 inner rows: {augmented_all['rows']:,}",
                f"- Complete 16-year grids: {augmented_all['complete_grid_cells']:,}",
                f"- Best rolling 6-year window: {best_window['start_year']}-{best_window['end_year']} "
                f"with {best_window['complete_grid_cells']:,} complete grids.",
                f"- Normalized richness range: {target_stats['target_min']:.4f}-{target_stats['target_max']:.4f}",
                "",
                "## Outputs",
                "",
                *[f"- `{path}`" for path in written.values()],
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    print(json.dumps(report, indent=2, ensure_ascii=False))
    print(f"\nWrote {json_path}")
    print(f"Wrote {md_path}")


if __name__ == "__main__":
    main()
