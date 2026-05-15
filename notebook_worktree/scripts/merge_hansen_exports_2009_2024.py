from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
RAW_EXPORT_DIR = ROOT / "datamining" / "raw" / "hansen_exports_2009_2024"
OUT_DIR = ROOT / "datamining" / "processed"
REPORT_DIR = ROOT / "reports"


def pick_column(columns: list[str], contains: list[str], default: str | None = None) -> str | None:
    lowered = {column: column.lower() for column in columns}
    for column, lower in lowered.items():
        if all(token in lower for token in contains):
            return column
    return default


def exact_or_pick(columns: list[str], exact: str, contains: list[str]) -> str | None:
    if exact in columns:
        return exact
    return pick_column(columns, contains)


def main() -> None:
    parser = argparse.ArgumentParser(description="Merge downloaded Hansen Earth Engine CSV exports.")
    parser.add_argument("--input-dir", type=Path, default=RAW_EXPORT_DIR)
    parser.add_argument("--pattern", default="hansen*_2009_2024_y*.csv")
    args = parser.parse_args()
    files = sorted(args.input_dir.glob(args.pattern))
    if not files:
        raise FileNotFoundError(f"No Hansen export CSVs found in {args.input_dir}")

    frames = [pd.read_csv(path) for path in files]
    raw = pd.concat(frames, ignore_index=True)
    columns = list(raw.columns)
    tree_col = exact_or_pick(columns, "treecover2000_mean", ["treecover2000", "mean"]) or pick_column(columns, ["treecover"])
    loss_ha_col = exact_or_pick(columns, "loss_area_ha_sum", ["loss_area_ha", "sum"])
    cum_loss_ha_col = exact_or_pick(columns, "cum_loss_area_ha_sum", ["cum_loss_area_ha", "sum"])
    cell_area_ha_col = exact_or_pick(columns, "cell_area_ha_sum", ["cell_area_ha", "sum"])
    if not all([tree_col, loss_ha_col, cum_loss_ha_col, cell_area_ha_col]):
        raise ValueError(
            "Could not map Hansen export columns. "
            f"tree={tree_col}, loss_ha={loss_ha_col}, cum_loss_ha={cum_loss_ha_col}, area={cell_area_ha_col}. "
            f"Available={columns}"
        )

    df = raw[["grid_id", "year", tree_col, loss_ha_col, cum_loss_ha_col, cell_area_ha_col]].copy()
    df = df.rename(
        columns={
            tree_col: "treecover2000_mean",
            loss_ha_col: "forest_loss_ha",
            cum_loss_ha_col: "cum_loss_ha",
            cell_area_ha_col: "cell_area_ha",
        }
    )
    for column in ["treecover2000_mean", "forest_loss_ha", "cum_loss_ha", "cell_area_ha"]:
        df[column] = pd.to_numeric(df[column], errors="coerce").fillna(0)
    df["cum_loss_fraction"] = np.where(df["cell_area_ha"] > 0, df["cum_loss_ha"] / df["cell_area_ha"], 0)
    df["forest_cover_pct"] = (df["treecover2000_mean"] * (1 - df["cum_loss_fraction"])).clip(lower=0).round(2)
    df = df.sort_values(["grid_id", "year"]).reset_index(drop=True)
    df["prev_cover"] = df.groupby("grid_id")["forest_cover_pct"].shift(1)
    df["forest_loss_pct_change"] = np.where(
        df["prev_cover"] > 0,
        -100 * df["forest_loss_ha"] / df["cell_area_ha"].replace(0, np.nan),
        0,
    )
    result = df[["grid_id", "year", "forest_cover_pct", "forest_loss_ha", "forest_loss_pct_change"]].copy()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUT_DIR / "forest_stats_2009_2024.csv"
    result.to_csv(out_path, index=False)
    summary = {
        "rows": int(len(result)),
        "unique_grid_cells": int(result["grid_id"].nunique()),
        "year_min": int(result["year"].min()),
        "year_max": int(result["year"].max()),
        "output": str(out_path.relative_to(ROOT)),
    }
    (REPORT_DIR / "forest_stats_2009_2024_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
