from __future__ import annotations

from collections.abc import Mapping, Sequence

import numpy as np
import pandas as pd


TARGET = "normalized_richness_01"
MODEL_YEAR = 2024

TARGETS_AND_DERIVED = {
    TARGET,
    "simpson_diversity",
    "pielou_evenness",
    "observation_density_01",
    "effort_adjusted_richness",
    "shannon_entropy",
    "hill_q0",
    "hill_q1",
    "hill_q2",
}
DROP_FORECAST = {
    "grid_id",
    "year",
    "n_weighted_individuals",
    "n_species",
    "n_observations",
    *TARGETS_AND_DERIVED,
}
FOREST_COLUMNS = ["forest_cover_pct", "forest_loss_ha", "forest_loss_pct_change"]
HISTORY_COLUMNS = [TARGET, "n_observations", "n_species", *FOREST_COLUMNS]


def add_lag_features(df: pd.DataFrame, columns: Sequence[str]) -> pd.DataFrame:
    available_columns = [column for column in columns if column in df.columns]
    if not available_columns:
        return df.copy()

    lag_frame = df[["grid_id", "year", *available_columns]].copy()
    lag_frame["year"] += 1
    lag_frame = lag_frame.rename(
        columns={column: f"{column}_lag1" for column in available_columns}
    )
    out = df.merge(lag_frame, on=["grid_id", "year"], how="left")
    for column in [column for column in out.columns if column.endswith("_lag1")]:
        out[column] = out[column].fillna(out[column].median())
    return out


def add_history_features(df: pd.DataFrame, columns: Sequence[str]) -> pd.DataFrame:
    out = df.sort_values(["grid_id", "year"]).copy()
    grouped = out.groupby("grid_id", group_keys=False, sort=False)
    available_columns = [column for column in columns if column in out.columns]
    for column in available_columns:
        out[f"{column}_last_obs"] = grouped[column].shift(1)
        out[f"{column}_hist_mean"] = grouped[column].transform(
            lambda series: series.shift(1).expanding().mean()
        )
        out[f"{column}_hist_max"] = grouped[column].transform(
            lambda series: series.shift(1).expanding().max()
        )

    out["prev_year_seen"] = grouped["year"].shift(1)
    out["years_since_seen"] = (out["year"] - out["prev_year_seen"]).fillna(99)
    out["prior_records_for_cell"] = grouped.cumcount()
    out["log_prior_records_for_cell"] = np.log1p(out["prior_records_for_cell"])
    return out.drop(columns=["prev_year_seen"])


def select_forecast_features(df: pd.DataFrame) -> list[str]:
    return [
        column
        for column in df.select_dtypes(include=[np.number]).columns
        if column not in DROP_FORECAST
    ]


def build_cell_area_estimates(forest_df: pd.DataFrame) -> pd.Series:
    nonzero_loss_pct = forest_df["forest_loss_pct_change"].ne(0) & forest_df["forest_loss_ha"].gt(0)
    area_frame = forest_df.loc[nonzero_loss_pct, ["grid_id"]].copy()
    area_frame["cell_area_ha"] = (
        -100
        * forest_df.loc[nonzero_loss_pct, "forest_loss_ha"]
        / forest_df.loc[nonzero_loss_pct, "forest_loss_pct_change"]
    )
    area_frame = area_frame.replace([np.inf, -np.inf], np.nan).dropna(
        subset=["cell_area_ha"]
    )
    return area_frame.groupby("grid_id")["cell_area_ha"].median()


def scenario_loss_pct_change(
    grid_id: str,
    baseline_pct_change: float,
    baseline_loss_ha: float,
    scenario_loss_ha: float,
    cell_area_by_grid: Mapping[str, float] | pd.Series,
) -> float:
    cell_area = _lookup_cell_area(grid_id, cell_area_by_grid) or _median_cell_area(cell_area_by_grid)
    if cell_area is not None:
        return -100 * scenario_loss_ha / cell_area
    if baseline_loss_ha and np.isfinite(baseline_loss_ha):
        return baseline_pct_change * (scenario_loss_ha / baseline_loss_ha)
    return baseline_pct_change


def _lookup_cell_area(
    grid_id: str, cell_area_by_grid: Mapping[str, float] | pd.Series
) -> float | None:
    try:
        value = (
            cell_area_by_grid.loc[grid_id]
            if isinstance(cell_area_by_grid, pd.Series)
            else cell_area_by_grid[grid_id]
        )
    except (KeyError, TypeError):
        return None

    if isinstance(value, pd.Series):
        if value.empty:
            return None
        value = value.iloc[0]

    cell_area = float(value)
    if np.isfinite(cell_area) and cell_area > 0:
        return cell_area
    return None


def _median_cell_area(cell_area_by_grid: Mapping[str, float] | pd.Series) -> float | None:
    if isinstance(cell_area_by_grid, pd.Series):
        values = cell_area_by_grid.dropna()
        if values.empty:
            return None
        median_area = float(values.median())
        return median_area if np.isfinite(median_area) and median_area > 0 else None

    values = []
    for value in cell_area_by_grid.values():
        try:
            parsed = float(value)
        except (TypeError, ValueError):
            continue
        if np.isfinite(parsed) and parsed > 0:
            values.append(parsed)
    if not values:
        return None
    median_area = float(np.median(values))
    return median_area if np.isfinite(median_area) and median_area > 0 else None
