"""데이터셋 업로드/조회 라우터 — MVP 골격.

업로드된 CSV는 backend/data/raw/ 에 저장되고, 전처리는 별도 잡으로 트리거된다.
실제 전처리 호출은 utils.data_processor.TrafficDataProcessor 와 연결하면 된다.
"""

from __future__ import annotations

import os
import re
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, File, HTTPException, UploadFile
from pydantic import BaseModel, Field

from app.core.state import registry
from app.schemas.common import DatasetOut, JobOut
from app.services.analysis import run_analysis
from app.services.datasets import resolve_dataset
from app.services.preprocessing import _output_path, run_preprocessing_job
from config import PROCESSED_DATA_DIR, RAW_DATA_DIR

router = APIRouter()

MAX_UPLOAD_BYTES = 100 * 1024 * 1024  # 100 MB
SAFE_NAME = re.compile(r"^[A-Za-z0-9._-]+$")


def _safe_filename(name: str) -> str:
    base = os.path.basename(name)
    if not base or not SAFE_NAME.match(base) or not base.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="invalid filename; csv only")
    return base


def _list_dir(kind: str, path: str) -> list[DatasetOut]:
    out: list[DatasetOut] = []
    for entry in sorted(Path(path).glob("*.csv")):
        st = entry.stat()
        out.append(
            DatasetOut(
                name=entry.name,
                kind=kind,  # type: ignore[arg-type]
                size_bytes=st.st_size,
                modified_at=datetime.fromtimestamp(st.st_mtime),
            )
        )
    return out


@router.get("", response_model=list[DatasetOut])
def list_datasets() -> list[DatasetOut]:
    return _list_dir("raw", RAW_DATA_DIR) + _list_dir("processed", PROCESSED_DATA_DIR)


@router.post("/upload", response_model=DatasetOut)
async def upload(file: UploadFile = File(...)) -> DatasetOut:
    name = _safe_filename(file.filename or "")
    dest = Path(RAW_DATA_DIR) / name

    written = 0
    with dest.open("wb") as f:
        while chunk := await file.read(1024 * 1024):
            written += len(chunk)
            if written > MAX_UPLOAD_BYTES:
                f.close()
                dest.unlink(missing_ok=True)
                raise HTTPException(status_code=413, detail="file too large")
            f.write(chunk)

    st = dest.stat()
    return DatasetOut(
        name=dest.name,
        kind="raw",
        size_bytes=st.st_size,
        modified_at=datetime.fromtimestamp(st.st_mtime),
    )


class ProcessRequest(BaseModel):
    preset: str = Field(default="default", pattern="^(default|geant)$")
    add_features: bool = True
    detect_anomaly: bool = True
    output_name: str | None = None


@router.post("/{name}/process", response_model=JobOut, status_code=202)
def process_dataset(
    name: str,
    background: BackgroundTasks,
    req: ProcessRequest | None = None,
) -> JobOut:
    """전처리를 백그라운드 잡으로 시작. 완료 시 job.result에 처리 결과가 담긴다.

    완료 후 결과 dict 키: path, rows, columns, feature_cols, size_bytes,
    modified_at, preset. 폴링은 GET /api/jobs/{job_id} 로.
    """
    req = req or ProcessRequest()

    # 입력/출력 이름 사전 검증 — 잘못된 요청은 잡 슬롯을 잡기 전에 거절.
    # Why: 비동기 패턴에선 백그라운드에서만 실패하면 클라이언트가 폴링해야 알 수 있어 UX 저하.
    try:
        resolve_dataset(name)
        _output_path(name, req.output_name)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    try:
        job = registry.create("preprocess")
    except RuntimeError as e:
        raise HTTPException(status_code=409, detail=str(e)) from e

    background.add_task(
        run_preprocessing_job,
        job.id,
        name,
        preset=req.preset,  # type: ignore[arg-type]
        add_features=req.add_features,
        detect_anomaly=req.detect_anomaly,
        output_name=req.output_name,
    )
    return JobOut(**job.__dict__)


@router.get("/{name}/analysis")
def analyze_dataset(
    name: str,
    bins: int = 50,
    timeline_max_points: int = 500,
) -> dict:
    """processed 데이터셋 분석 결과(JSON). 프론트 대시보드용."""
    try:
        return run_analysis(
            name,
            bins=max(2, min(bins, 200)),
            timeline_max_points=max(10, min(timeline_max_points, 5000)),
        )
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
