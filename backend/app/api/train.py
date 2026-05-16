"""학습 트리거 라우터."""

from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel

from app.core.state import registry
from app.schemas.common import JobOut
from app.services.prediction import invalidate as invalidate_forecaster_cache
from app.services.training import run_training

router = APIRouter()


class TrainRequest(BaseModel):
    dataset: str
    model_type: str = "lstm"
    epochs: int | None = None
    batch_size: int | None = None
    sequence_length: int | None = None


def _execute(job_id: str, req: TrainRequest) -> None:
    # 학습 시작 전 예측 캐시 비우기 — best_model.h5 등 같은 이름의 산출물이 갱신될 수 있음
    invalidate_forecaster_cache()
    run_training(
        job_id,
        req.dataset,
        model_type=req.model_type,
        epochs=req.epochs,
        batch_size=req.batch_size,
        sequence_length=req.sequence_length,
    )


@router.post("", response_model=JobOut, status_code=202)
def start_training(req: TrainRequest, background: BackgroundTasks) -> JobOut:
    try:
        job = registry.create("train")
    except RuntimeError as e:
        raise HTTPException(status_code=409, detail=str(e)) from e

    background.add_task(_execute, job.id, req)
    return JobOut(**job.__dict__)


@router.get("/{job_id}", response_model=JobOut)
def get_job(job_id: str) -> JobOut:
    job = registry.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="job not found")
    return JobOut(**job.__dict__)
