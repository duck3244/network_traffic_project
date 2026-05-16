from datetime import datetime
from typing import Literal

from pydantic import BaseModel

JobStatus = Literal["pending", "running", "succeeded", "failed"]


class JobOut(BaseModel):
    id: str
    kind: str
    status: JobStatus
    progress: float
    message: str
    result: dict | None = None
    error: str | None = None
    created_at: datetime
    updated_at: datetime


class DatasetOut(BaseModel):
    name: str
    kind: Literal["raw", "processed"]
    size_bytes: int
    modified_at: datetime


class ModelOut(BaseModel):
    name: str
    size_bytes: int
    modified_at: datetime
    metrics: dict | None = None
