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
from api.schemas import ScenarioRequest
from api.service import FORECAST_YEARS, ModelService


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

        self.assertNotIn("year", selected_features)
        self.assertIn("forest_cover_pct", frame.columns)
        self.assertIn("normalized_richness_01_lag1", frame.columns)
        self.assertGreater(len(selected_features), 10)
        self.assertGreater(len(forecast_frame), 1000)

    def test_model_service_exposes_2025_projection_without_ground_truth(self) -> None:
        self.assertIn(2025, FORECAST_YEARS)

        service = ModelService.build()
        self.assertNotIn("year", service.feature_cols)
        self.assertNotIn(
            "validation-selected final",
            service.get_model_options_response().models[0].label,
        )
        predictions = service.get_predictions_response(year=2025)
        self.assertGreater(len(predictions.predictions), 1000)

        grid_id = predictions.predictions[0].grid_id
        grid = service.get_grid_response(grid_id=grid_id, year=2025)
        self.assertIsNone(grid.observed)
        self.assertFalse(any(row.feature_key == "year" for row in grid.explanation))
        self.assertEqual(len(grid.explanation), len(service.feature_cols))
        self.assertIsNotNone(grid.explanation[0].value)
        self.assertIsNotNone(grid.explanation[0].reference_value)
        self.assertTrue(
            any(
                feature.key == "normalized_richness_01_lag1" and feature.value is not None
                for feature in grid.features
            )
        )

        scenario = service.run_scenario(
            ScenarioRequest(
                grid_id=grid_id,
                year=2025,
                model_id=predictions.model_id,
                forest_cover_pct=25.0,
                forest_loss_ha=50.0,
            )
        )
        self.assertEqual(scenario.year, 2025)
        self.assertGreaterEqual(scenario.scenario_predicted, 0.0)
        self.assertLessEqual(scenario.scenario_predicted, 1.0)


if __name__ == "__main__":
    unittest.main()
