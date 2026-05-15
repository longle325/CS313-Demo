# Vietnam Biodiversity Web Demo

Interactive web demo for the CS313 biodiversity project. It visualizes a single
fixed-scale 0–1 biodiversity richness index, explicit selected-grid model
inference, leaderboard model comparison, a 2025 projection year, model
explanations, and forest scenario simulation across Vietnam grid-year records.

## Data

- Source file: `public/data/dataset.csv`
- Upstream sources:
  - `../notebook_worktree/datamining/processed/gbif_diversity_2009_2024.csv`
  - `../notebook_worktree/datamining/processed/forest_stats_2009_2024.csv`
  - `../notebook_worktree/datamining/processed/weather_yearly_2009_2024.csv`
- Unit of analysis: one `grid_id` + `year`
- Coordinates: parsed from `grid_id` in the format `VN_{lat}_{lon}`
- Main biodiversity metric: `normalized_richness`, a unitless 0–1 index derived
  from `n_species / log1p(n_observations)`, capped at the training p99 and scaled
  to `[0, 1]`

The file is aggregated, so `n_species` is a distinct species count per grid-year,
not a full species checklist.

Weather values are incomplete for some GBIF grid-years. They were evaluated in
ablation, but the final demo UI does not surface missing rainfall/weather fields
because the selected model is explained through historical biodiversity and
forest context.

The default inference model is `xgboost_logistic`, selected by 2023 validation
R² before the locked 2024 test. The backend exposes the deployable final
leaderboard models used in the demo: XGBoost logistic, HistGradientBoosting,
ExtraTrees, Random Forest, Ridge, Linear Regression, and ElasticNet.

The frontend uses one map layer only: `Biodiversity richness index`. Color is
always scaled from `0.00` to `1.00`, so colors are comparable across years.
Year 2025 is a projection year under persistence assumptions, not observed
ground truth.

## Run

The frontend calls the FastAPI backend through Vite's `/api` proxy, so run both
servers during the live demo.

### 1. Backend API

From `web-demo/`:

```bash
# Use the project virtualenv if it already exists.
../.venv/bin/python -m pip install -r api/requirements.txt
../.venv/bin/python -m uvicorn api.app:app --host 127.0.0.1 --port 8000 --reload
```

Health check:

```bash
curl http://127.0.0.1:8000/api/health
```

Expected response includes `"status":"ok"` and `"model_year":2024`.

Useful backend endpoints:

```bash
curl http://127.0.0.1:8000/api/models
curl "http://127.0.0.1:8000/api/predictions?year=2024"
curl "http://127.0.0.1:8000/api/predictions?year=2025&model_id=extra_trees"
curl "http://127.0.0.1:8000/api/grid?year=2025&grid_id=VN_22.62_102.77&model_id=xgboost_logistic"
```

If `../.venv` does not exist yet:

```bash
python3 -m venv ../.venv
../.venv/bin/python -m pip install --upgrade pip
../.venv/bin/python -m pip install -r api/requirements.txt
```

### 2. Frontend UI

Open a second terminal from `web-demo/`:

```bash
npm install
npm run dev -- --host 127.0.0.1 --port 5173
```

Open `http://127.0.0.1:5173/`.

Keep the backend running on `http://127.0.0.1:8000`; otherwise the map falls
back to observed metrics and prediction/explanation/scenario panels cannot load.

For the presentation flow, use `DEMO_SCRIPT.md`.

## Validate

```bash
../.venv/bin/python -m unittest api.test_smoke
npm test -- --run
npm run build
```

## Replace Data

After regenerating the pipeline output, copy the new processed CSV into the demo:

```bash
python scripts/export_web_demo_dataset.py
```

If the export script is unavailable, keep the same column names used by
`src/utils/biodiversityMetrics.ts`.
