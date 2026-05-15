from __future__ import annotations

import argparse
import json
import time
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = ROOT.parent
GRID_PATH = PROJECT_ROOT / "data" / "intermediate" / "grid_cells.csv"
REPORT_DIR = ROOT / "reports"
HANSEN_ASSET = "UMD/hansen/global_forest_change_2024_v1_12"


def init_ee(project: str, auth_mode: str, key_file: Path | None, service_account: str | None):
    import ee

    if auth_mode == "service-account":
        if key_file is None or service_account is None:
            raise ValueError("--key-file and --service-account are required for service-account auth")
        credentials = ee.ServiceAccountCredentials(service_account, str(key_file))
        ee.Initialize(credentials, project=project)
    else:
        # Use the developer's Earth Engine OAuth credentials. This is important
        # for Drive exports because service accounts often have no Drive quota.
        ee.Initialize(project=project)
    return ee


def build_grid_fc(ee, grid_df: pd.DataFrame):
    features = []
    for _, row in grid_df.iterrows():
        rect = ee.Geometry.Rectangle(
            [
                float(row["min_lon"]),
                float(row["min_lat"]),
                float(row["max_lon"]),
                float(row["max_lat"]),
            ]
        )
        features.append(ee.Feature(rect, {"grid_id": row["grid_id"]}))
    return ee.FeatureCollection(features)


def year_image(ee, hansen, year: int):
    loss_value = year - 2000
    treecover = hansen.select("treecover2000")
    lossyear = hansen.select("lossyear")
    pixel_ha = ee.Image.pixelArea().divide(10_000)
    loss_this_year = lossyear.eq(loss_value).rename("loss_this_year")
    cum_loss = lossyear.gt(0).And(lossyear.lte(loss_value)).rename("cum_loss")
    loss_area_ha = loss_this_year.multiply(pixel_ha).rename("loss_area_ha")
    cum_loss_area_ha = cum_loss.multiply(pixel_ha).rename("cum_loss_area_ha")
    cell_area_ha = pixel_ha.rename("cell_area_ha")
    return treecover.addBands([loss_this_year, cum_loss, loss_area_ha, cum_loss_area_ha, cell_area_ha])


def submit_task(
    ee,
    hansen,
    batch_df: pd.DataFrame,
    year: int,
    batch_index: int,
    drive_folder: str,
    task_prefix: str,
):
    image = year_image(ee, hansen, year)

    def reduce_cell(feature):
        stats = image.reduceRegion(
            reducer=ee.Reducer.mean().combine(ee.Reducer.sum(), sharedInputs=True),
            geometry=feature.geometry(),
            scale=30,
            maxPixels=1e8,
        )
        return feature.set(stats).set("year", year)

    fc = build_grid_fc(ee, batch_df).map(reduce_cell)
    task_name = f"{task_prefix}_y{year}_b{batch_index:03d}"
    task = ee.batch.Export.table.toDrive(
        collection=fc,
        description=task_name,
        folder=drive_folder,
        fileNamePrefix=task_name,
        fileFormat="CSV",
    )
    task.start()
    return task_name, task.id


def list_existing_task_ids_by_name(ee) -> dict[str, str]:
    try:
        tasks = ee.batch.Task.list()
    except Exception as exc:
        print(f"Could not list existing Earth Engine tasks; continuing with local manifest only: {exc}")
        return {}
    out: dict[str, str] = {}
    for task in tasks:
        status = task.status()
        description = status.get("description")
        task_id = status.get("id")
        if description and task_id:
            out[description] = task_id
    return out


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Submit Hansen GFC Earth Engine Drive exports for 2009-2024.")
    parser.add_argument("--project", default="crawlhansen")
    parser.add_argument("--start-year", type=int, default=2009)
    parser.add_argument("--end-year", type=int, default=2024)
    parser.add_argument("--batch-size", type=int, default=2000)
    parser.add_argument("--drive-folder", default="earth_engine_exports_2009_2024")
    parser.add_argument("--auth-mode", choices=["user", "service-account"], default="user")
    parser.add_argument("--key-file", type=Path, default=None, help="Service-account JSON key; do not commit this file.")
    parser.add_argument("--service-account", default=None, help="Earth Engine service-account email.")
    parser.add_argument("--task-prefix", default="hansen_user_2009_2024")
    parser.add_argument("--manifest-name", default=None)
    parser.add_argument("--submit", action="store_true")
    parser.add_argument("--sleep", type=float, default=2.0)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    grid = pd.read_csv(GRID_PATH)
    batches = [
        grid.iloc[start : start + args.batch_size].copy()
        for start in range(0, len(grid), args.batch_size)
    ]
    years = list(range(args.start_year, args.end_year + 1))
    print(
        f"Hansen export plan: {len(grid):,} grid cells × {len(years)} years × "
        f"{len(batches)} batches = {len(years) * len(batches)} Drive export tasks"
    )
    manifest_name = args.manifest_name or f"{args.task_prefix}_manifest.json"
    manifest_path = REPORT_DIR / manifest_name
    manifest = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "asset": HANSEN_ASSET,
        "project": args.project,
        "auth_mode": args.auth_mode,
        "task_prefix": args.task_prefix,
        "drive_folder": args.drive_folder,
        "start_year": args.start_year,
        "end_year": args.end_year,
        "batch_size": args.batch_size,
        "grid_cells": int(len(grid)),
        "planned_tasks": len(years) * len(batches),
        "tasks": [],
    }
    if manifest_path.exists():
        previous = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["created_at"] = previous.get("created_at", manifest["created_at"])
        manifest["tasks"] = previous.get("tasks", [])
    if not args.submit:
        print("Dry run only. Re-run with --submit to create Earth Engine export tasks.")
        (REPORT_DIR / "hansen_exports_2009_2024_plan.json").write_text(
            json.dumps(manifest, indent=2),
            encoding="utf-8",
        )
        return

    ee = init_ee(args.project, args.auth_mode, args.key_file, args.service_account)
    hansen = ee.Image(HANSEN_ASSET)
    existing_task_ids = list_existing_task_ids_by_name(ee)
    submitted_names = {task["name"] for task in manifest["tasks"]}
    for year in years:
        for batch_index, batch_df in enumerate(batches):
            task_name = f"{args.task_prefix}_y{year}_b{batch_index:03d}"
            if task_name in submitted_names:
                print(f"SKIP already recorded {task_name}")
                continue
            if task_name in existing_task_ids:
                task_id = existing_task_ids[task_name]
                name = task_name
                print(f"RECOVER existing Earth Engine task {name}: {task_id}")
            else:
                try:
                    name, task_id = submit_task(
                        ee,
                        hansen,
                        batch_df,
                        year,
                        batch_index,
                        args.drive_folder,
                        args.task_prefix,
                    )
                except Exception as exc:
                    existing_task_ids = list_existing_task_ids_by_name(ee)
                    if task_name in existing_task_ids:
                        name = task_name
                        task_id = existing_task_ids[task_name]
                        print(f"RECOVER after submit error {name}: {task_id}")
                    else:
                        raise
            manifest["tasks"].append(
                {
                    "name": name,
                    "task_id": task_id,
                    "year": year,
                    "batch_index": batch_index,
                    "cells": int(len(batch_df)),
                }
            )
            submitted_names.add(name)
            print(f"SUBMITTED {name}: {task_id}")
            manifest_path.write_text(
                json.dumps(manifest, indent=2),
                encoding="utf-8",
            )
            time.sleep(args.sleep)


if __name__ == "__main__":
    main()
