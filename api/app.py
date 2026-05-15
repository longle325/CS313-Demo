from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, Query, Request

from api.schemas import (
    GridResponse,
    ModelOptionsResponse,
    PredictionsResponse,
    ScenarioRequest,
    ScenarioResponse,
)
from api.service import FORECAST_YEARS, ModelService


@asynccontextmanager
async def lifespan(fastapi_app: FastAPI):
    service = ModelService.build()
    fastapi_app.state.service = service
    yield


def get_service(request: Request) -> ModelService:
    service = getattr(request.app.state, "service", None)
    if service is None:
        raise RuntimeError("ModelService is not initialized")
    return service


def not_found(error: KeyError) -> HTTPException:
    return HTTPException(status_code=404, detail=str(error))


app = FastAPI(lifespan=lifespan)


@app.get("/api/health")
def health(service: ModelService = Depends(get_service)) -> dict:
    return {
        "status": "ok",
        "model_year": service.model_year,
        "forecast_years": list(FORECAST_YEARS),
        "model_name": service.model_name,
        "available_models": [model.model_id for model in service.get_model_options_response().models],
        "mode": service.mode,
    }


@app.get("/api/models", response_model=ModelOptionsResponse)
def models(service: ModelService = Depends(get_service)) -> ModelOptionsResponse:
    return service.get_model_options_response()


@app.get("/api/predictions", response_model=PredictionsResponse)
def predictions(
    year: int = Query(2024),
    model_id: str | None = Query(default=None),
    service: ModelService = Depends(get_service),
) -> PredictionsResponse:
    if year not in FORECAST_YEARS:
        raise HTTPException(
            status_code=400,
            detail=f"Predictions available for years={list(FORECAST_YEARS)} only",
        )
    try:
        return service.get_predictions_response(model_id=model_id, year=year)
    except KeyError as error:
        raise not_found(error) from error


@app.get("/api/grid", response_model=GridResponse)
def grid(
    grid_id: str,
    year: int = Query(2024),
    model_id: str | None = Query(default=None),
    service: ModelService = Depends(get_service),
) -> GridResponse:
    if year not in FORECAST_YEARS:
        raise HTTPException(
            status_code=400,
            detail=f"Grid endpoint available for years={list(FORECAST_YEARS)} only",
        )
    try:
        return service.get_grid_response(grid_id=grid_id, model_id=model_id, year=year)
    except KeyError as error:
        raise not_found(error) from error


@app.post("/api/scenario", response_model=ScenarioResponse)
def scenario(
    payload: ScenarioRequest,
    service: ModelService = Depends(get_service),
) -> ScenarioResponse:
    if payload.year not in FORECAST_YEARS:
        raise HTTPException(
            status_code=400,
            detail=f"Scenario available for years={list(FORECAST_YEARS)} only",
        )
    try:
        return service.run_scenario(payload)
    except KeyError as error:
        raise not_found(error) from error
