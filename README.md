# Vietnam Biodiversity Prediction System

Interactive CS313.Q23 Data Mining and Applications project for grid-level biodiversity richness forecasting in Vietnam. The repository contains the React + Leaflet web demo, FastAPI inference backend, final reproducible notebook, processed 2009-2024 datasets, and scripts used to crawl/prepare GBIF, Hansen forest, and Open-Meteo data.

The demo visualizes a fixed-scale 0-1 biodiversity richness index, selected-grid model inference, model leaderboard comparison, a 2025 projection workflow, feature audit explanations, and forest scenario simulation across Vietnam grid-year records.

## Project Summary

- **Spatial unit:** `grid_id × year`, using a 0.09° × 0.09° grid, approximately 10 km × 10 km.
- **Study area:** Vietnam.
- **Time range:** 2009-2024 observed data; 2025 is a demo projection year, not observed ground truth.
- **Data sources:** GBIF biodiversity records, Hansen Global Forest Change, and Open-Meteo historical weather.
- **Prediction target:** `normalized_richness_01`, a unitless relative biodiversity richness index in `[0, 1]`.
- **Final selected model:** `xgboost_logistic`, selected by 2023 validation R², then refit on 2009-2023 and tested once on 2024.
- **Final 2024 holdout result:** R² `0.6892`, MAE `0.0816`, RMSE `0.1214`.
- **Grid-based robustness check:** GroupKFold by `grid_id` R² `0.578 ± 0.041`.

The output is **not** an absolute species count. It is a relative observed richness score corrected for uneven GBIF observation effort.

## Target Definition

The notebook first computes effort-adjusted richness:

```text
effort_adjusted_richness = n_species / log(1 + n_observations)
```

Then it caps the value at the training 99th percentile and scales it to `[0, 1]`:

```text
normalized_richness_01 = min(effort_adjusted_richness, p99_cap) / p99_cap
```

Interpretation:

- `0` means relatively low observed richness after correcting for observation effort.
- `1` means very high observed richness relative to the capped maximum in the training data.
- It should be interpreted as a relative biodiversity condition indicator, not a literal number of species.

The frontend uses one map layer only: `Vietnam Biodiversity richness index`. Color is always scaled from `0.00` to `1.00`. The map can browse observed years `2009-2024`; selecting a 2024 grid opens a 2025 projection setup using latest grid history plus editable 2025 forest inputs.

## Repository Structure

```text
.
├── api/                         # FastAPI model inference backend
├── src/                         # React + Leaflet web demo
├── public/data/dataset.csv      # Web-demo-friendly merged table
├── notebook_worktree/
│   ├── datamining/
│   │   ├── FINAL_FULL_PIPELINE_CS313_BIODIVERSITY.ipynb
│   │   ├── processed/
│   │   │   ├── gbif_diversity_2009_2024.csv
│   │   │   ├── forest_stats_2009_2024.csv
│   │   │   └── weather_yearly_2009_2024.csv
│   │   └── dataset-2/gadm41_VNM.gpkg
│   └── scripts/                 # GBIF, Hansen, Open-Meteo preparation scripts
├── data/intermediate/grid_cells.csv
├── docs/normalized_richness_explanation.md
├── DEMO_SCRIPT.md
├── scripts/export_web_demo_dataset.py
├── requirements-python.txt
└── package.json
```

## Data Files

| File | Purpose |
|---|---|
| `notebook_worktree/datamining/processed/gbif_diversity_2009_2024.csv` | Final GBIF grid-year biodiversity labels and diversity metrics. |
| `notebook_worktree/datamining/processed/forest_stats_2009_2024.csv` | Hansen forest cover/loss features for grid-years. |
| `notebook_worktree/datamining/processed/weather_yearly_2009_2024.csv` | Open-Meteo yearly temperature/rainfall summaries. |
| `notebook_worktree/datamining/dataset-2/gadm41_VNM.gpkg` | Vietnam province boundaries used for notebook map plots. |
| `data/intermediate/grid_cells.csv` | 10 km Vietnam grid used by Hansen export scripts. |
| `public/data/dataset.csv` | Web-demo-friendly merged data generated from the processed tables. |

Processed table validation from the notebook:

| Source | Rows | Grid cells | Years | Coverage note |
|---|---:|---:|---|---|
| GBIF biodiversity | 9,245 | 2,569 | 2009-2024 | target labels |
| Hansen forest | 246,352 | 15,397 | 2009-2024 | 100% coverage over GBIF rows |
| Open-Meteo weather | 87,850 | 9,777 | 2009-2024 | 63.7% coverage over GBIF rows |

Weather values are incomplete for some GBIF grid-years. They were evaluated in ablation, but the final demo UI focuses on historical biodiversity and forest context because those are the strongest deployable features in the selected model.

## Run the Final Notebook

Create a Python environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements-python.txt
```

Open the notebook:

```bash
jupyter notebook notebook_worktree/datamining/FINAL_FULL_PIPELINE_CS313_BIODIVERSITY.ipynb
```

Or execute it end-to-end:

```bash
jupyter nbconvert \
  --to notebook \
  --execute notebook_worktree/datamining/FINAL_FULL_PIPELINE_CS313_BIODIVERSITY.ipynb \
  --inplace \
  --ExecutePreprocessor.timeout=3600
```

The notebook is self-contained with respect to project data. It reads only the processed CSV files and optional GPKG map file listed above. Leaderboards, ablation CSVs, figures, and reports are generated outputs, not required inputs.

## Run the Web Demo

The frontend calls the FastAPI backend through Vite's `/api` proxy, so run both servers during the live demo.

### 1. Backend API

From the repository root:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -r api/requirements.txt
.venv/bin/python -m uvicorn api.app:app --host 127.0.0.1 --port 8000 --reload
```

Health check:

```bash
curl http://127.0.0.1:8000/api/health
```

Expected response includes `"status":"ok"`, `"model_year":2024`, and
`"forecast_years":[2024,2025]`.

Useful backend endpoints:

```bash
curl http://127.0.0.1:8000/api/models
curl "http://127.0.0.1:8000/api/predictions?year=2024"
curl "http://127.0.0.1:8000/api/predictions?year=2025&model_id=extra_trees"
curl "http://127.0.0.1:8000/api/grid?year=2025&grid_id=VN_22.62_102.77&model_id=xgboost_logistic"
```

### 2. Frontend UI

Open a second terminal from the repository root:

```bash
npm install
npm run dev -- --host 127.0.0.1 --port 5173
```

Open `http://127.0.0.1:5173/`.

Keep the backend running on `http://127.0.0.1:8000`; otherwise model selection,
2025 prediction, feature audit, and scenario panels cannot load. The audit
reports every model feature with its active value, training median, and local
score sensitivity.

For the presentation flow, use `DEMO_SCRIPT.md`.

## Validate

```bash
.venv/bin/python -m unittest api.test_smoke
npm test -- --run
npm run build
```

Regenerate the web-demo dataset after updating processed data:

```bash
.venv/bin/python scripts/export_web_demo_dataset.py
```

## Data Crawling / Processing Scripts

### GBIF

Official GBIF download flow:

```bash
export GBIF_USERNAME="your_username"
export GBIF_PASSWORD="your_password"
export GBIF_EMAIL="your_email@example.com"
python notebook_worktree/scripts/request_gbif_download.py --start-year 2009 --end-year 2024 --poll --download
python notebook_worktree/scripts/aggregate_gbif_diversity.py --start-year 2009 --end-year 2024
```

Direct GBIF occurrence API crawler is also provided:

```bash
python notebook_worktree/scripts/crawl_gbif_occurrences.py --start-year 2009 --end-year 2024
python notebook_worktree/scripts/aggregate_gbif_diversity.py --start-year 2009 --end-year 2024
```

### Hansen Global Forest Change / Google Earth Engine

Authenticate Earth Engine first. For normal user OAuth:

```bash
earthengine authenticate
python notebook_worktree/scripts/submit_hansen_exports_2009_2024.py --auth-mode user --submit
```

For service-account auth, keep the JSON key outside the repository:

```bash
python notebook_worktree/scripts/submit_hansen_exports_2009_2024.py \
  --auth-mode service-account \
  --project your-gcp-project \
  --service-account your-service-account@project.iam.gserviceaccount.com \
  --key-file /path/to/service-account-key.json \
  --submit
```

After Drive exports are downloaded into `notebook_worktree/datamining/raw/hansen_exports_2009_2024/`, merge them:

```bash
python notebook_worktree/scripts/merge_hansen_exports_2009_2024.py
```

### Open-Meteo

Use the historical weather API crawler conservatively to avoid rate limits:

```bash
python notebook_worktree/scripts/crawl_openmeteo_api_fast.py \
  --start-year 2009 \
  --end-year 2024 \
  --batch-size 10 \
  --workers 1 \
  --max-retries 4 \
  --base-backoff 10 \
  --max-backoff 3700
```

If previous weather CSVs exist, normalize/import them first:

```bash
python notebook_worktree/scripts/import_existing_openmeteo.py
```

## Security / Files Intentionally Not Committed

The repository intentionally excludes:

- GBIF passwords or `.env` files.
- Google Earth Engine service-account JSON keys.
- Raw GBIF downloads and Open-Meteo cache batches.
- Notebook backup files, logs, `__pycache__`, local virtual environments, and generated report folders.

If a script needs credentials, pass them through environment variables or CLI arguments and keep the credential files outside Git.
