"""예측 라우터."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.services.prediction import run_prediction

router = APIRouter()


class PredictRequest(BaseModel):
    model: str
    dataset: str
    steps: int = Field(default=24, ge=1, le=1024)


class PredictPoint(BaseModel):
    t: int
    value: float


class PredictResponse(BaseModel):
    model: str
    dataset: str
    steps: int
    points: list[PredictPoint]


@router.post("", response_model=PredictResponse)
def predict(req: PredictRequest) -> PredictResponse:
    try:
        points = run_prediction(req.model, req.dataset, req.steps)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    return PredictResponse(
        model=req.model,
        dataset=req.dataset,
        steps=req.steps,
        points=[PredictPoint(**p) for p in points],
    )
