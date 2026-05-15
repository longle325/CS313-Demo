# Data Pipeline Scripts

These scripts reproduce the processed data used by the final notebook.

Recommended order:

1. GBIF: `request_gbif_download.py` or `crawl_gbif_occurrences.py`
2. GBIF aggregation: `aggregate_gbif_diversity.py`
3. Hansen exports: `submit_hansen_exports_2009_2024.py`
4. Hansen merge: `merge_hansen_exports_2009_2024.py`
5. Open-Meteo: `import_existing_openmeteo.py` and/or `crawl_openmeteo_api_fast.py`
6. Notebook compatibility helper: `build_notebook_inputs.py` when old notebook-style inputs are needed

Do not commit credential files or raw API caches.
