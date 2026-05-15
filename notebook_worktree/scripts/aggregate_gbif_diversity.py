from __future__ import annotations

import argparse
import json
import math
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "datamining" / "raw" / "gbif_occurrences_2009_2024"
DOWNLOAD_DIR = ROOT / "datamining" / "raw" / "gbif_download_2009_2024"
DATA_DIR = ROOT / "datamining" / "dataset-2"
OUT_DIR = ROOT / "datamining" / "processed"
REPORT_DIR = ROOT / "reports"

VIETNAM_BBOX = {
    "lat_min": 8.0,
    "lat_max": 23.6,
    "lon_min": 102.0,
    "lon_max": 110.1,
}
MAX_COORDINATE_UNCERTAINTY_M = 10_000
TRAIN_CUTOFF_YEAR = 2024
NORMALIZATION_CAP_Q = 0.99
BAD_ISSUES = {
    "ZERO_COORDINATE",
    "COORDINATE_OUT_OF_RANGE",
    "COUNTRY_COORDINATE_MISMATCH",
    "COORDINATE_INVALID",
    "PRESUMED_NEGATED_LONGITUDE",
    "PRESUMED_NEGATED_LATITUDE",
    "PRESUMED_SWAPPED_COORDINATE",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Aggregate raw GBIF occurrence shards into biodiversity metrics.")
    parser.add_argument("--start-year", type=int, default=2009)
    parser.add_argument("--end-year", type=int, default=2024)
    parser.add_argument("--chunk-size", type=int, default=100_000)
    parser.add_argument("--allow-partial", action="store_true")
    return parser.parse_args()


def load_grid_centroids() -> tuple[np.ndarray, np.ndarray]:
    processed_forest = OUT_DIR / "forest_stats_2009_2024.csv"
    fallback_forest = DATA_DIR / "forest_stats.csv"
    forest_path = processed_forest if processed_forest.exists() else fallback_forest
    forest = pd.read_csv(forest_path, usecols=["grid_id"])
    coords = forest["grid_id"].str.extract(r"^VN_([-0-9.]+)_([-0-9.]+)$").astype(float)
    lat_centers = np.array(sorted(coords[0].unique()))
    lon_centers = np.array(sorted(coords[1].unique()))
    return lat_centers, lon_centers


def nearest_centers(values: pd.Series, centers: np.ndarray) -> np.ndarray:
    arr = values.to_numpy(dtype=float)
    idx = np.searchsorted(centers, arr)
    idx = np.clip(idx, 1, len(centers) - 1)
    left = centers[idx - 1]
    right = centers[idx]
    nearest = np.where(np.abs(arr - left) <= np.abs(right - arr), left, right)
    return nearest


def has_bad_issue(issue_text: object) -> bool:
    if pd.isna(issue_text):
        return False
    issues = set(str(issue_text).split(";"))
    return bool(issues & BAD_ISSUES)


def clean_chunk(chunk: pd.DataFrame, lat_centers: np.ndarray, lon_centers: np.ndarray) -> pd.DataFrame:
    chunk = chunk.copy()
    for column in [
        "decimalLatitude",
        "decimalLongitude",
        "coordinateUncertaintyInMeters",
        "year",
        "speciesKey",
        "individualCount",
    ]:
        chunk[column] = pd.to_numeric(chunk[column], errors="coerce")

    before = len(chunk)
    chunk = chunk.drop_duplicates(subset=["gbifID"])
    chunk = chunk[
        chunk["decimalLatitude"].between(VIETNAM_BBOX["lat_min"], VIETNAM_BBOX["lat_max"])
        & chunk["decimalLongitude"].between(VIETNAM_BBOX["lon_min"], VIETNAM_BBOX["lon_max"])
        & chunk["year"].between(2009, 2024)
        & chunk["speciesKey"].notna()
        & (chunk["occurrenceStatus"].fillna("PRESENT") == "PRESENT")
        & (
            chunk["coordinateUncertaintyInMeters"].isna()
            | (chunk["coordinateUncertaintyInMeters"] <= MAX_COORDINATE_UNCERTAINTY_M)
        )
    ].copy()
    if "issues" in chunk.columns:
        chunk = chunk[~chunk["issues"].map(has_bad_issue)].copy()

    if chunk.empty:
        return chunk

    chunk["grid_lat"] = nearest_centers(chunk["decimalLatitude"], lat_centers)
    chunk["grid_lon"] = nearest_centers(chunk["decimalLongitude"], lon_centers)
    chunk["grid_id"] = (
        "VN_"
        + chunk["grid_lat"].map(lambda value: f"{value:.2f}")
        + "_"
        + chunk["grid_lon"].map(lambda value: f"{value:.2f}")
    )
    chunk["speciesKey"] = chunk["speciesKey"].astype("int64")
    chunk["year"] = chunk["year"].astype("int64")
    chunk["occurrence_weight"] = np.where(
        chunk["individualCount"].between(1, 10_000),
        chunk["individualCount"],
        1,
    )
    chunk["quality_rows_removed_in_chunk"] = before - len(chunk)
    return chunk


def diversity_from_counts(counts: pd.Series) -> dict[str, float]:
    values = counts.to_numpy(dtype=float)
    total = values.sum()
    species = len(values)
    if total <= 0 or species <= 0:
        return {
            "shannon_entropy": 0.0,
            "simpson_diversity": 0.0,
            "pielou_evenness": 0.0,
            "hill_q0": 0.0,
            "hill_q1": 0.0,
            "hill_q2": 0.0,
        }
    proportions = values / total
    shannon = float(-(proportions * np.log(proportions)).sum())
    simpson_concentration = float((proportions**2).sum())
    simpson_diversity = 1.0 - simpson_concentration
    pielou = shannon / math.log(species) if species > 1 else 0.0
    return {
        "shannon_entropy": shannon,
        "simpson_diversity": simpson_diversity,
        "pielou_evenness": float(pielou),
        "hill_q0": float(species),
        "hill_q1": float(math.exp(shannon)),
        "hill_q2": float(1.0 / simpson_concentration) if simpson_concentration > 0 else 0.0,
    }


def main() -> None:
    args = parse_args()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    lat_centers, lon_centers = load_grid_centroids()
    output_suffix = "_partial" if args.allow_partial else ""

    raw_files = sorted(RAW_DIR.glob("gbif_vn_*.csv.gz"))
    download_files = sorted(DOWNLOAD_DIR.glob("*/occurrence.txt")) + sorted(DOWNLOAD_DIR.glob("*/*.csv"))
    if download_files:
        input_files = download_files
        input_sep = "\t"
        print(f"Using official GBIF download file(s): {[path.name for path in input_files]}")
    elif raw_files:
        manifest_path = RAW_DIR / "manifest.json"
        if manifest_path.exists() and not args.allow_partial:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            expected_shards = (args.end_year - args.start_year + 1) * 12
            complete_shards = [
                shard
                for shard in manifest.get("shards", {}).values()
                if shard.get("status") == "complete"
            ]
            complete_records = sum(int(shard.get("records_written", 0)) for shard in complete_shards)
            expected_records = int(manifest.get("total_expected", 0))
            if len(complete_shards) != expected_shards or complete_records != expected_records:
                raise SystemExit(
                    "Public API shards are incomplete "
                    f"({len(complete_shards)}/{expected_shards} shards, "
                    f"{complete_records:,}/{expected_records:,} records). "
                    "Use the official GBIF download path or pass --allow-partial for a smoke test."
                )
        input_files = raw_files
        input_sep = ","
        print(f"Using public API shard file(s): {len(input_files)}")
    else:
        raise FileNotFoundError(f"No GBIF raw shards in {RAW_DIR} and no official download in {DOWNLOAD_DIR}")

    usecols = [
        "gbifID",
        "speciesKey",
        "species",
        "acceptedScientificName",
        "kingdom",
        "decimalLatitude",
        "decimalLongitude",
        "coordinateUncertaintyInMeters",
        "year",
        "individualCount",
        "occurrenceStatus",
        "issues",
    ]
    cleaned_parts: list[pd.DataFrame] = []
    raw_rows = 0
    cleaned_rows = 0

    for path in input_files:
        print(f"READ {path.name}")
        for chunk in pd.read_csv(path, sep=input_sep, usecols=lambda column: column in usecols, chunksize=args.chunk_size, low_memory=False):
            for missing_column in set(usecols) - set(chunk.columns):
                chunk[missing_column] = np.nan
            raw_rows += len(chunk)
            cleaned = clean_chunk(chunk, lat_centers, lon_centers)
            cleaned_rows += len(cleaned)
            if not cleaned.empty:
                cleaned_parts.append(
                    cleaned[
                        [
                            "gbifID",
                            "grid_id",
                            "year",
                            "speciesKey",
                            "species",
                            "acceptedScientificName",
                            "kingdom",
                            "occurrence_weight",
                        ]
                    ]
                )

    occurrences = pd.concat(cleaned_parts, ignore_index=True)
    occurrences = occurrences.drop_duplicates(subset=["gbifID"]).copy()
    occurrence_out = OUT_DIR / f"gbif_occurrences_cleaned_2009_2024{output_suffix}.csv.gz"
    occurrences.to_csv(occurrence_out, index=False, compression="gzip")

    species_counts = (
        occurrences.groupby(["grid_id", "year", "speciesKey"], as_index=False)
        .agg(
            occurrence_records=("gbifID", "count"),
            weighted_individuals=("occurrence_weight", "sum"),
            species=("species", "first"),
            acceptedScientificName=("acceptedScientificName", "first"),
            kingdom=("kingdom", "first"),
        )
    )
    species_counts.to_csv(
        OUT_DIR / f"gbif_grid_year_species_counts_2009_2024{output_suffix}.csv.gz",
        index=False,
        compression="gzip",
    )

    base = (
        species_counts.groupby(["grid_id", "year"], as_index=False)
        .agg(
            n_observations=("occurrence_records", "sum"),
            n_species=("speciesKey", "nunique"),
            n_weighted_individuals=("weighted_individuals", "sum"),
        )
    )

    metric_rows = []
    for (grid_id, year), group in species_counts.groupby(["grid_id", "year"]):
        metrics = diversity_from_counts(group.set_index("speciesKey")["occurrence_records"])
        metrics.update({"grid_id": grid_id, "year": int(year)})
        metric_rows.append(metrics)
    metrics_df = pd.DataFrame(metric_rows)
    diversity = base.merge(metrics_df, on=["grid_id", "year"], how="left")

    diversity["effort_adjusted_richness"] = diversity["n_species"] / np.log1p(diversity["n_observations"])
    cap_source = diversity.loc[
        diversity["year"] < TRAIN_CUTOFF_YEAR,
        "effort_adjusted_richness",
    ]
    richness_cap = float(cap_source.quantile(NORMALIZATION_CAP_Q))
    diversity["normalized_richness_01"] = (
        diversity["effort_adjusted_richness"].clip(upper=richness_cap) / richness_cap
    ).clip(0, 1)
    density_cap = float(np.log1p(diversity.loc[diversity["year"] < TRAIN_CUTOFF_YEAR, "n_observations"]).quantile(NORMALIZATION_CAP_Q))
    diversity["observation_density_01"] = (
        np.log1p(diversity["n_observations"]).clip(upper=density_cap) / density_cap
    ).clip(0, 1)
    coords = diversity["grid_id"].str.extract(r"^VN_([-0-9.]+)_([-0-9.]+)$").astype(float)
    diversity["lat"] = coords[0]
    diversity["lon"] = coords[1]
    diversity = diversity[
        [
            "grid_id",
            "lat",
            "lon",
            "year",
            "n_observations",
            "n_species",
            "n_weighted_individuals",
            "effort_adjusted_richness",
            "normalized_richness_01",
            "observation_density_01",
            "shannon_entropy",
            "simpson_diversity",
            "pielou_evenness",
            "hill_q0",
            "hill_q1",
            "hill_q2",
        ]
    ].sort_values(["grid_id", "year"])
    diversity_out = OUT_DIR / f"gbif_diversity_2009_2024{output_suffix}.csv"
    diversity.to_csv(diversity_out, index=False)

    summary = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "raw_rows_read": int(raw_rows),
        "cleaned_occurrence_rows": int(len(occurrences)),
        "grid_year_rows": int(len(diversity)),
        "unique_grid_cells": int(diversity["grid_id"].nunique()),
        "unique_species": int(occurrences["speciesKey"].nunique()),
        "year_min": int(diversity["year"].min()),
        "year_max": int(diversity["year"].max()),
        "normalization": {
            "train_cutoff_year": TRAIN_CUTOFF_YEAR,
            "richness_cap_quantile": NORMALIZATION_CAP_Q,
            "richness_cap": richness_cap,
            "density_cap_log1p_p99": density_cap,
        },
        "quality_filters": {
            "vietnam_bbox": VIETNAM_BBOX,
            "max_coordinate_uncertainty_m": MAX_COORDINATE_UNCERTAINTY_M,
            "bad_issues": sorted(BAD_ISSUES),
            "species_key_required": True,
            "occurrence_status": "PRESENT",
        },
        "outputs": {
            "occurrences_cleaned": str(occurrence_out.relative_to(ROOT)),
            "species_counts": f"datamining/processed/gbif_grid_year_species_counts_2009_2024{output_suffix}.csv.gz",
            "diversity": str(diversity_out.relative_to(ROOT)),
        },
    }
    (REPORT_DIR / f"gbif_diversity_2009_2024{output_suffix}_summary.json").write_text(
        json.dumps(summary, indent=2),
        encoding="utf-8",
    )
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
