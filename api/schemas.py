from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, model_validator


class Thresholds(BaseModel):
    p33: float = Field(ge=0.0, le=1.0)
    p66: float = Field(ge=0.0, le=1.0)

    @model_validator(mode="after")
    def validate_order(self) -> "Thresholds":
        if self.p33 > self.p66:
            raise ValueError("p33 must be <= p66")
        return self


class PredictionRow(BaseModel):
    grid_id: str
    year: int
    prediction: float = Field(ge=0.0, le=1.0)


class PredictionsResponse(BaseModel):
    year: int
    model_id: str
    thresholds: Thresholds
    model_name: str
    model_label: str
    mode: Literal["forecast"] = "forecast"
    train_year_min: int
    train_year_max: int
    predictions: list[PredictionRow]


class ModelOption(BaseModel):
    model_id: str
    label: str
    description: str
    family: str
    valid_r2: float | None = None
    test_r2: float | None = None
    mae: float | None = None
    rmse: float | None = None
    is_default: bool = False


class ModelOptionsResponse(BaseModel):
    default_model_id: str
    models: list[ModelOption]


class FeatureValue(BaseModel):
    key: str
    label: str
    value: float | None
    unit: str | None = None


class ExplanationRow(BaseModel):
    feature_key: str
    feature_label: str
    contribution: float
    direction: Literal["positive", "negative", "neutral"]


class GridResponse(BaseModel):
    grid_id: str
    year: int
    model_id: str
    model_label: str
    observed: float | None = Field(default=None, ge=0.0, le=1.0)
    predicted: float = Field(ge=0.0, le=1.0)
    level: Literal["Low", "Medium", "High"]
    thresholds: Thresholds
    features: list[FeatureValue]
    explanation: list[ExplanationRow]


class ScenarioRequest(BaseModel):
    grid_id: str
    year: Literal[2024, 2025] = 2024
    model_id: str = "xgboost_logistic"
    forest_cover_pct: float = Field(ge=0.0, le=100.0)
    forest_loss_ha: float = Field(ge=0.0)


class ScenarioResponse(BaseModel):
    grid_id: str
    year: int
    model_id: str
    model_label: str
    baseline_predicted: float = Field(ge=0.0, le=1.0)
    scenario_predicted: float = Field(ge=0.0, le=1.0)
    delta: float
    thresholds: Thresholds
    baseline_explanation: list[ExplanationRow]
    scenario_explanation: list[ExplanationRow]
