"""학습/전처리 잡 공용 폴링 엔드포인트."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse

from app.core.state import registry
from app.schemas.common import JobOut

router = APIRouter()


@router.get("/active")
def get_active() -> JSONResponse:
    """현재 실행 중인 잡(있으면). 없으면 null 반환."""
    job = registry.active()
    if job is None:
        return JSONResponse(content=None)
    return JSONResponse(content=JobOut(**job.__dict__).model_dump(mode="json"))


@router.get("/{job_id}", response_model=JobOut)
def get_job(job_id: str) -> JobOut:
    job = registry.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="job not found")
    return JobOut(**job.__dict__)
