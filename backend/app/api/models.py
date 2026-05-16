"""학습 산출물(.h5) 목록 라우터 — MVP 골격."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter

from app.schemas.common import ModelOut
from config import MODELS_DIR

router = APIRouter()


@router.get("", response_model=list[ModelOut])
def list_models() -> list[ModelOut]:
    out: list[ModelOut] = []
    for entry in sorted(Path(MODELS_DIR).glob("*.h5")):
        st = entry.stat()
        metrics_path = entry.with_name(entry.stem + "_metrics.json")
        metrics: dict | None = None
        if metrics_path.exists():
            try:
                metrics = json.loads(metrics_path.read_text())
            except json.JSONDecodeError:
                metrics = None
        out.append(
            ModelOut(
                name=entry.name,
                size_bytes=st.st_size,
                modified_at=datetime.fromtimestamp(st.st_mtime),
                metrics=metrics,
            )
        )
    return out
