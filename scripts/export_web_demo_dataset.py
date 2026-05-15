from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
PROCESSED = ROOT / "notebook_worktree" / "datamining" / "processed"
OUTPUT = ROOT / "public" / "data" / "dataset.csv"


def main() -> None:
    gbif = pd.read_csv(PROCESSED / "gbif_diversity_2009_2024.csv")
    forest = pd.read_csv(PROCESSED / "forest_stats_2009_2024.csv")
    weather = pd.read_csv(PROCESSED / "weather_yearly_2009_2024.csv")

    dataset = (
        gbif[
            [
                "grid_id",
                "year",
                "n_observations",
                "n_species",
                "normalized_richness_01",
            ]
        ]
        .merge(forest, on=["grid_id", "year"], how="left")
        .merge(weather, on=["grid_id", "year"], how="left")
        .rename(columns={"normalized_richness_01": "normalized_richness"})
    )

    columns = [
        "grid_id",
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
        "normalized_richness",
    ]
    dataset = dataset[columns].sort_values(["year", "grid_id"])

    for column in [
        "forest_cover_pct",
        "forest_loss_ha",
        "forest_loss_pct_change",
        "avg_temp",
        "total_rainfall_mm",
        "n_dry_days",
        "n_hot_days",
        "temp_anomaly",
        "normalized_richness",
    ]:
        dataset[column] = dataset[column].round(6)

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    dataset.to_csv(OUTPUT, index=False)

    weather_rows = dataset[["avg_temp", "total_rainfall_mm"]].notna().all(axis=1).sum()
    print(f"Wrote {OUTPUT}")
    print(
        f"Rows={len(dataset):,}, grids={dataset.grid_id.nunique():,}, "
        f"years={dataset.year.min()}-{dataset.year.max()}"
    )
    print(f"Weather coverage={weather_rows:,}/{len(dataset):,} rows")


if __name__ == "__main__":
    main()
