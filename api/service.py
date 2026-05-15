from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sklearn.ensemble import ExtraTreesRegressor, HistGradientBoostingRegressor, RandomForestRegressor
from sklearn.linear_model import ElasticNet, LinearRegression, Ridge
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import RobustScaler
from xgboost import XGBRegressor

from api.feature_engineering import (
    HISTORY_COLUMNS,
    MODEL_YEAR,
    TARGET,
    TARGETS_AND_DERIVED,
    add_history_features,
    add_lag_features,
    build_cell_area_estimates,
    scenario_loss_pct_change,
    select_forecast_features,
)
from api.schemas import (
    ExplanationRow,
    FeatureValue,
    GridResponse,
    ModelOption,
    ModelOptionsResponse,
    PredictionRow,
    PredictionsResponse,
    ScenarioRequest,
    ScenarioResponse,
    Thresholds,
)


FORECAST_YEARS = (MODEL_YEAR, MODEL_YEAR + 1)

FEATURE_SUMMARY = (
    ("forest_cover_pct", "Forest cover", "%"),
    ("forest_loss_ha", "Forest loss", "ha"),
    ("normalized_richness_01_lag1", "Previous-year richness (lag1)", None),
    ("years_since_seen", "Years since seen", "years"),
)

FEATURE_LABELS = {
    "lat": "Latitude",
    "lon": "Longitude",
    "forest_cover_pct": "Forest cover",
    "forest_loss_ha": "Forest loss",
    "forest_loss_pct_change": "Forest loss (% change)",
    "normalized_richness_01": "Richness",
    "normalized_richness_01_lag1": "Previous-year richness (lag1)",
    "n_observations": "Observations",
    "n_species": "Species",
    "years_since_seen": "Years since seen",
    "prior_records_for_cell": "Prior records for cell",
    "log_prior_records_for_cell": "Log prior records for cell",
}

HISTORY_SUFFIX_LABELS = {
    "_lag1": "lag1",
    "_last_obs": "last observed",
    "_hist_mean": "history mean",
    "_hist_max": "history max",
}

DEFAULT_MODEL_ID = "xgboost_logistic"

MODEL_OPTIONS = (
    ModelOption(
        model_id="xgboost_logistic",
        label="XGBoost logistic",
        description=(
            "Selected by 2023 validation R², then retrained on 2009–2023 "
            "for the locked 2024 forecast."
        ),
        family="Boosted trees",
        valid_r2=0.6303427284106216,
        test_r2=0.6891833875999477,
        mae=0.08160801969262592,
        rmse=0.12144162890051456,
        is_default=True,
    ),
    ModelOption(
        model_id="hist_gradient_boosting",
        label="HistGradientBoosting",
        description="Strong sklearn boosted-tree model on the same final feature set.",
        family="Boosted trees",
        valid_r2=0.5838988073784994,
        test_r2=0.6862899088411016,
        mae=0.08133847886847616,
        rmse=0.12200558647247409,
    ),
    ModelOption(
        model_id="extra_trees",
        label="ExtraTrees",
        description="Randomized tree ensemble benchmark on the same final feature set.",
        family="Bagging trees",
        valid_r2=0.5798543504679957,
        test_r2=0.6834781243043673,
        mae=0.08144644142820542,
        rmse=0.12255113498940177,
    ),
    ModelOption(
        model_id="random_forest",
        label="Random Forest",
        description="Bagging-tree benchmark retained from the final model-family leaderboard.",
        family="Bagging trees",
        valid_r2=0.573925618712197,
        test_r2=0.6667486798596314,
        mae=0.08373713109365018,
        rmse=0.1257480941805511,
    ),
    ModelOption(
        model_id="ridge",
        label="Ridge regression",
        description="Regularized linear baseline on the same engineered features.",
        family="Linear baseline",
        valid_r2=0.6066829960647204,
        test_r2=0.6609784480467107,
        mae=0.08147610736700445,
        rmse=0.12683208334623927,
    ),
    ModelOption(
        model_id="linear_regression",
        label="Linear regression",
        description="Unregularized linear baseline used to compare nonlinear gains.",
        family="Linear baseline",
        valid_r2=0.6059294751145645,
        test_r2=0.6606948665578973,
        mae=0.081471066852819,
        rmse=0.1268851178990289,
    ),
    ModelOption(
        model_id="elastic_net",
        label="ElasticNet",
        description="Sparse regularized linear baseline from the final leaderboard.",
        family="Linear baseline",
        valid_r2=0.612979313712306,
        test_r2=0.6487717259349797,
        mae=0.08493212367056074,
        rmse=0.12909523344862694,
        is_default=False,
    ),
)

MODEL_LABELS = {option.model_id: option.label for option in MODEL_OPTIONS}


@dataclass(frozen=True, slots=True)
class ModelService:
    models: dict[str, Any]
    feature_cols: tuple[str, ...]
    medians: pd.Series
    frame_by_model_year: dict[str, dict[int, pd.DataFrame]]
    x_by_model_year: dict[str, dict[int, pd.DataFrame]]
    predictions_by_model_year: dict[str, dict[int, pd.Series]]
    thresholds_by_model_year: dict[str, dict[int, Thresholds]]
    cell_area_by_grid: pd.Series
    model_year: int = MODEL_YEAR
    default_model_id: str = DEFAULT_MODEL_ID
    mode: str = "forecast"
    train_year_min: int = 2009
    train_year_max: int = MODEL_YEAR - 1

    @classmethod
    def build(cls) -> "ModelService":
        project_root = Path(__file__).resolve().parents[1]
        gbif_path = (
            project_root
            / "notebook_worktree"
            / "datamining"
            / "processed"
            / "gbif_diversity_2009_2024.csv"
        )
        forest_path = (
            project_root
            / "notebook_worktree"
            / "datamining"
            / "processed"
            / "forest_stats_2009_2024.csv"
        )

        gbif_df = pd.read_csv(gbif_path)
        forest_df = pd.read_csv(forest_path)
        base_frame = gbif_df.merge(
            forest_df,
            on=["grid_id", "year"],
            how="left",
            validate="one_to_one",
        ).sort_values(["grid_id", "year"])
        forecast_base_frame = _append_projection_rows(base_frame, FORECAST_YEARS)
        feature_frame = _build_feature_frame(forecast_base_frame)

        feature_cols = tuple(select_forecast_features(feature_frame))
        train_frame = feature_frame.loc[feature_frame["year"].lt(MODEL_YEAR)].dropna(subset=[TARGET])
        frame_2024 = feature_frame.loc[feature_frame["year"].eq(MODEL_YEAR)].copy()
        if train_frame.empty:
            raise ValueError("No training rows available before model year 2024")
        if frame_2024.empty:
            raise ValueError("No prediction rows available for model year 2024")

        x_train = train_frame.loc[:, feature_cols].copy()
        medians = x_train.median().fillna(0)
        x_train = x_train.fillna(medians)
        y_train = train_frame[TARGET]

        models = _build_candidate_models()
        for model in models.values():
            model.fit(x_train, y_train)

        frame_by_model_year: dict[str, dict[int, pd.DataFrame]] = {}
        x_by_model_year: dict[str, dict[int, pd.DataFrame]] = {}
        predictions_by_model_year: dict[str, dict[int, pd.Series]] = {}
        thresholds_by_model_year: dict[str, dict[int, Thresholds]] = {}

        for model_id, model in models.items():
            working_frame = forecast_base_frame.copy()
            frame_by_model_year[model_id] = {}
            x_by_model_year[model_id] = {}
            predictions_by_model_year[model_id] = {}
            thresholds_by_model_year[model_id] = {}

            for forecast_year in FORECAST_YEARS:
                forecast_features = _build_feature_frame(working_frame)
                year_frame = forecast_features.loc[forecast_features["year"].eq(forecast_year)].copy()
                if year_frame.empty:
                    raise ValueError(f"No rows available for forecast year {forecast_year}")

                x_year = year_frame.loc[:, feature_cols].copy().fillna(medians)
                x_year.index = year_frame["grid_id"]
                predictions = pd.Series(
                    np.clip(model.predict(x_year), 0.0, 1.0),
                    index=x_year.index,
                    name="prediction",
                )

                frame_by_model_year[model_id][forecast_year] = year_frame.set_index("grid_id", drop=False)
                x_by_model_year[model_id][forecast_year] = x_year
                predictions_by_model_year[model_id][forecast_year] = predictions
                thresholds_by_model_year[model_id][forecast_year] = Thresholds(
                    p33=float(predictions.quantile(0.33)),
                    p66=float(predictions.quantile(0.66)),
                )

                if forecast_year > MODEL_YEAR:
                    forecast_mask = working_frame["year"].eq(forecast_year)
                    working_frame.loc[forecast_mask, TARGET] = working_frame.loc[
                        forecast_mask,
                        "grid_id",
                    ].map(predictions)

        return cls(
            models=models,
            feature_cols=feature_cols,
            medians=medians,
            frame_by_model_year=frame_by_model_year,
            x_by_model_year=x_by_model_year,
            predictions_by_model_year=predictions_by_model_year,
            thresholds_by_model_year=thresholds_by_model_year,
            cell_area_by_grid=build_cell_area_estimates(forest_df),
            train_year_min=int(train_frame["year"].min()),
            train_year_max=int(train_frame["year"].max()),
        )

    @property
    def model_name(self) -> str:
        return self.default_model_id

    def get_model_options_response(self) -> ModelOptionsResponse:
        return ModelOptionsResponse(
            default_model_id=self.default_model_id,
            models=list(MODEL_OPTIONS),
        )

    def get_predictions_response(self, model_id: str | None = None, year: int = MODEL_YEAR) -> PredictionsResponse:
        resolved_model_id = self._resolve_model_id(model_id)
        resolved_year = self._resolve_year(year)
        predictions_for_model = self.predictions_by_model_year[resolved_model_id][resolved_year]
        predictions = [
            PredictionRow(
                grid_id=str(grid_id),
                year=resolved_year,
                prediction=float(prediction),
            )
            for grid_id, prediction in predictions_for_model.items()
        ]
        return PredictionsResponse(
            year=resolved_year,
            model_id=resolved_model_id,
            thresholds=self.thresholds_by_model_year[resolved_model_id][resolved_year],
            model_name=resolved_model_id,
            model_label=self._model_label(resolved_model_id),
            mode=self.mode,
            train_year_min=self.train_year_min,
            train_year_max=self.train_year_max,
            predictions=predictions,
        )

    def get_grid_response(self, grid_id: str, model_id: str | None = None, year: int = MODEL_YEAR) -> GridResponse:
        resolved_model_id = self._resolve_model_id(model_id)
        resolved_year = self._resolve_year(year)
        frame_row = self._frame_row(grid_id, resolved_model_id, resolved_year)
        x_row = self._x_row(grid_id, resolved_model_id, resolved_year)
        predicted = float(self.predictions_by_model_year[resolved_model_id][resolved_year].loc[grid_id])
        return GridResponse(
            grid_id=grid_id,
            year=resolved_year,
            model_id=resolved_model_id,
            model_label=self._model_label(resolved_model_id),
            observed=_optional_float(frame_row.get(TARGET)) if resolved_year == MODEL_YEAR else None,
            predicted=predicted,
            level=self._level(predicted, resolved_model_id, resolved_year),
            thresholds=self.thresholds_by_model_year[resolved_model_id][resolved_year],
            features=self._feature_values(frame_row),
            explanation=self._explain(x_row, resolved_model_id),
        )

    def run_scenario(self, payload: ScenarioRequest) -> ScenarioResponse:
        resolved_model_id = self._resolve_model_id(payload.model_id)
        resolved_year = self._resolve_year(payload.year)
        frame_row = self._frame_row(payload.grid_id, resolved_model_id, resolved_year)
        baseline_x = self._x_row(payload.grid_id, resolved_model_id, resolved_year)
        scenario_x = baseline_x.copy()

        forest_loss_pct_change = scenario_loss_pct_change(
            grid_id=payload.grid_id,
            baseline_pct_change=_finite_or_nan(frame_row.get("forest_loss_pct_change")),
            baseline_loss_ha=_finite_or_nan(frame_row.get("forest_loss_ha")),
            scenario_loss_ha=payload.forest_loss_ha,
            cell_area_by_grid=self.cell_area_by_grid,
        )
        scenario_values = {
            "forest_cover_pct": payload.forest_cover_pct,
            "forest_loss_ha": payload.forest_loss_ha,
            "forest_loss_pct_change": forest_loss_pct_change,
        }
        for feature_key, value in scenario_values.items():
            if feature_key in scenario_x.columns:
                scenario_x.loc[:, feature_key] = value

        baseline_predicted = float(
            self.predictions_by_model_year[resolved_model_id][resolved_year].loc[payload.grid_id]
        )
        scenario_predicted = self._predict_one(scenario_x, resolved_model_id)
        return ScenarioResponse(
            grid_id=payload.grid_id,
            year=resolved_year,
            model_id=resolved_model_id,
            model_label=self._model_label(resolved_model_id),
            baseline_predicted=baseline_predicted,
            scenario_predicted=scenario_predicted,
            delta=scenario_predicted - baseline_predicted,
            thresholds=self.thresholds_by_model_year[resolved_model_id][resolved_year],
            baseline_features=_forest_scenario_features(
                forest_cover_pct=_finite_or_nan(frame_row.get("forest_cover_pct")),
                forest_loss_ha=_finite_or_nan(frame_row.get("forest_loss_ha")),
                forest_loss_pct_change=_finite_or_nan(frame_row.get("forest_loss_pct_change")),
            ),
            scenario_features=_forest_scenario_features(
                forest_cover_pct=payload.forest_cover_pct,
                forest_loss_ha=payload.forest_loss_ha,
                forest_loss_pct_change=forest_loss_pct_change,
            ),
            baseline_explanation=self._explain(baseline_x, resolved_model_id),
            scenario_explanation=self._explain(scenario_x, resolved_model_id),
        )

    def _resolve_model_id(self, model_id: str | None) -> str:
        resolved_model_id = model_id or self.default_model_id
        if resolved_model_id not in self.models:
            raise KeyError(f"Unknown model_id: {resolved_model_id}")
        return resolved_model_id

    def _resolve_year(self, year: int) -> int:
        if year not in FORECAST_YEARS:
            raise KeyError(f"Unsupported forecast year: {year}")
        return year

    def _model_label(self, model_id: str) -> str:
        return MODEL_LABELS.get(model_id, model_id)

    def _frame_row(self, grid_id: str, model_id: str, year: int) -> pd.Series:
        frame = self.frame_by_model_year[model_id][year]
        if grid_id not in frame.index:
            raise KeyError(f"Unknown grid_id: {grid_id}")
        return frame.loc[grid_id]

    def _x_row(self, grid_id: str, model_id: str, year: int) -> pd.DataFrame:
        x_year = self.x_by_model_year[model_id][year]
        if grid_id not in x_year.index:
            raise KeyError(f"Unknown grid_id: {grid_id}")
        row = x_year.loc[[grid_id], list(self.feature_cols)].copy()
        row.index = [grid_id]
        return row

    def _feature_values(self, row: pd.Series) -> list[FeatureValue]:
        return [
            FeatureValue(
                key=key,
                label=label,
                value=_optional_float(row.get(key)),
                unit=unit,
            )
            for key, label, unit in FEATURE_SUMMARY
        ]

    def _explain(self, x_row: pd.DataFrame, model_id: str) -> list[ExplanationRow]:
        baseline_prediction = self._predict_one(x_row, model_id)
        feature_values = x_row.iloc[0]
        explanation_rows: list[ExplanationRow] = []
        for feature_key in self.feature_cols:
            perturbed = x_row.copy()
            reference_value = float(self.medians.get(feature_key, 0.0))
            perturbed.loc[:, feature_key] = reference_value
            contribution = baseline_prediction - self._predict_one(perturbed, model_id)
            explanation_rows.append(
                ExplanationRow(
                    feature_key=feature_key,
                    feature_label=_humanize_feature(feature_key),
                    value=_optional_float(feature_values.get(feature_key)),
                    reference_value=_optional_float(reference_value),
                    contribution=float(contribution),
                    direction=_direction(float(contribution)),
                )
            )
        return sorted(explanation_rows, key=lambda row: abs(row.contribution), reverse=True)

    def _predict_one(self, x_row: pd.DataFrame, model_id: str) -> float:
        prediction = self.models[model_id].predict(x_row.loc[:, self.feature_cols])
        return float(np.clip(prediction[0], 0.0, 1.0))

    def _level(self, prediction: float, model_id: str, year: int) -> str:
        thresholds = self.thresholds_by_model_year[model_id][year]
        if prediction <= thresholds.p33:
            return "Low"
        if prediction <= thresholds.p66:
            return "Medium"
        return "High"


def _build_candidate_models() -> dict[str, Any]:
    return {
        "xgboost_logistic": Pipeline(
            [
                ("scale", RobustScaler()),
                (
                    "model",
                    XGBRegressor(
                        objective="reg:logistic",
                        n_estimators=600,
                        max_depth=3,
                        learning_rate=0.03,
                        subsample=0.85,
                        colsample_bytree=0.9,
                        reg_lambda=5,
                        random_state=42,
                        n_jobs=4,
                        tree_method="hist",
                    ),
                ),
            ]
        ),
        "hist_gradient_boosting": HistGradientBoostingRegressor(
            loss="squared_error",
            learning_rate=0.025,
            max_iter=600,
            max_leaf_nodes=31,
            l2_regularization=0.1,
            random_state=42,
        ),
        "extra_trees": ExtraTreesRegressor(
            n_estimators=450,
            max_depth=18,
            min_samples_leaf=3,
            max_features=0.7,
            random_state=42,
            n_jobs=4,
        ),
        "random_forest": RandomForestRegressor(
            n_estimators=350,
            max_depth=18,
            min_samples_leaf=5,
            max_features="sqrt",
            random_state=42,
            n_jobs=4,
        ),
        "ridge": Pipeline(
            [
                ("scale", RobustScaler()),
                ("model", Ridge(alpha=1.0)),
            ]
        ),
        "linear_regression": Pipeline(
            [
                ("scale", RobustScaler()),
                ("model", LinearRegression()),
            ]
        ),
        "elastic_net": Pipeline(
            [
                ("scale", RobustScaler()),
                (
                    "model",
                    ElasticNet(
                        alpha=0.005,
                        l1_ratio=0.5,
                        max_iter=20_000,
                        random_state=42,
                    ),
                ),
            ]
        ),
    }


def _build_feature_frame(base_frame: pd.DataFrame) -> pd.DataFrame:
    out = base_frame.sort_values(["grid_id", "year"]).copy()
    out = add_lag_features(out, HISTORY_COLUMNS)
    return add_history_features(out, HISTORY_COLUMNS)


def _append_projection_rows(base_frame: pd.DataFrame, forecast_years: tuple[int, ...]) -> pd.DataFrame:
    out = base_frame.sort_values(["grid_id", "year"]).copy()
    current_like_columns = [
        "n_observations",
        "n_species",
        "n_weighted_individuals",
        *TARGETS_AND_DERIVED,
    ]

    for forecast_year in sorted(year for year in forecast_years if year > MODEL_YEAR):
        if out["year"].eq(forecast_year).any():
            continue

        source_year = forecast_year - 1
        source_rows = out.loc[out["year"].eq(source_year)].copy()
        if source_rows.empty:
            raise ValueError(f"Cannot build projection rows for {forecast_year}: missing {source_year}")

        projection_rows = source_rows.copy()
        projection_rows.loc[:, "year"] = forecast_year

        for column in current_like_columns:
            if column in projection_rows.columns:
                projection_rows[column] = projection_rows[column].astype("float64")
                projection_rows[column] = np.nan

        if "forest_loss_ha" in projection_rows.columns:
            projection_rows.loc[:, "forest_loss_ha"] = 0.0
        if "forest_loss_pct_change" in projection_rows.columns:
            projection_rows.loc[:, "forest_loss_pct_change"] = 0.0

        out = pd.concat([out, projection_rows], ignore_index=True)

    return out.sort_values(["grid_id", "year"])


def _humanize_feature(feature_key: str) -> str:
    if feature_key in FEATURE_LABELS:
        return FEATURE_LABELS[feature_key]
    for suffix, suffix_label in HISTORY_SUFFIX_LABELS.items():
        if feature_key.endswith(suffix):
            base_key = feature_key[: -len(suffix)]
            base_label = FEATURE_LABELS.get(
                base_key,
                base_key.replace("_", " ").title(),
            )
            return f"{base_label} ({suffix_label})"
    return feature_key.replace("_", " ").title()


def _direction(contribution: float) -> str:
    if contribution > 1e-12:
        return "positive"
    if contribution < -1e-12:
        return "negative"
    return "neutral"


def _optional_float(value: object) -> float | None:
    if value is None or pd.isna(value):
        return None
    numeric_value = float(value)
    if not np.isfinite(numeric_value):
        return None
    return numeric_value


def _forest_scenario_features(
    forest_cover_pct: float,
    forest_loss_ha: float,
    forest_loss_pct_change: float,
) -> list[FeatureValue]:
    return [
        FeatureValue(
            key="forest_cover_pct",
            label="Forest cover",
            value=_optional_float(forest_cover_pct),
            unit="%",
        ),
        FeatureValue(
            key="forest_loss_ha",
            label="Forest loss",
            value=_optional_float(forest_loss_ha),
            unit="ha",
        ),
        FeatureValue(
            key="forest_loss_pct_change",
            label="Forest loss (% change)",
            value=_optional_float(forest_loss_pct_change),
            unit="%",
        ),
    ]


def _finite_or_nan(value: object) -> float:
    numeric_value = _optional_float(value)
    return float("nan") if numeric_value is None else numeric_value
