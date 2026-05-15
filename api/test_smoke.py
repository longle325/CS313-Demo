from __future__ import annotations

import unittest
from pathlib import Path

import pandas as pd

from api.feature_engineering import (
    HISTORY_COLUMNS,
    MODEL_YEAR,
    add_history_features,
    add_lag_features,
    select_forecast_features,
)


ROOT = Path("/Users/longle/CS313/biodiversity")
PROCESSED = ROOT / "notebook_worktree" / "datamining" / "processed"


class FeatureEngineeringSmokeTest(unittest.TestCase):
    def test_builds_2024_forecast_feature_frame(self) -> None:
        diversity = pd.read_csv(PROCESSED / "gbif_diversity_2009_2024.csv")
        forest = pd.read_csv(PROCESSED / "forest_stats_2009_2024.csv")
        frame = diversity.merge(forest, on=["grid_id", "year"], how="left")

        frame = add_lag_features(frame, HISTORY_COLUMNS)
        frame = add_history_features(frame, HISTORY_COLUMNS)
        selected_features = select_forecast_features(frame)
        forecast_frame = frame.loc[frame["year"] == MODEL_YEAR, selected_features]

        self.assertIn("forest_cover_pct", frame.columns)
        self.assertIn("normalized_richness_01_lag1", frame.columns)
        self.assertGreater(len(selected_features), 10)
        self.assertGreater(len(forecast_frame), 1000)


if __name__ == "__main__":
    unittest.main()
