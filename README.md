# Vietnam Biodiversity Web Demo

Interactive web demo for the CS313 biodiversity project. It visualizes GBIF
species richness, Hansen forest features, and available Open-Meteo weather
features across Vietnam grid-year records.

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

Weather values are incomplete for some GBIF grid-years. The UI keeps those
records visible for biodiversity/forest metrics and shows missing weather values
as `N/A`.

## Run

```bash
npm install
npm run dev -- --host 127.0.0.1 --port 5173
```

Open `http://127.0.0.1:5173/`.

## Validate

```bash
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
