"""단일 사용자 MVP용 인메모리 잡 상태.

학습/전처리 같은 장시간 작업의 동시 실행을 막고 진행 상태를 폴링할 수 있도록
프로세스 내 단일 슬롯 잡 레지스트리를 제공한다. 영속성이 필요해지면
SQLite/JSON 파일 백킹으로 교체한다.
"""

from __future__ import annotations

import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal

JobStatus = Literal["pending", "running", "succeeded", "failed"]


@dataclass
class Job:
    id: str
    kind: str
    status: JobStatus = "pending"
    progress: float = 0.0
    message: str = ""
    result: dict | None = None
    error: str | None = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)


class JobRegistry:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._jobs: dict[str, Job] = {}
        self._active_id: str | None = None

    def create(self, kind: str) -> Job:
        with self._lock:
            if self._active_id is not None:
                raise RuntimeError("another job is already running")
            job = Job(id=uuid.uuid4().hex, kind=kind, status="running")
            self._jobs[job.id] = job
            self._active_id = job.id
            return job

    def update(
        self,
        job_id: str,
        *,
        progress: float | None = None,
        message: str | None = None,
        status: JobStatus | None = None,
        result: dict | None = None,
        error: str | None = None,
    ) -> None:
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                return
            if progress is not None:
                job.progress = progress
            if message is not None:
                job.message = message
            if status is not None:
                job.status = status
            if result is not None:
                job.result = result
            if error is not None:
                job.error = error
            job.updated_at = datetime.utcnow()
            if status in ("succeeded", "failed") and self._active_id == job_id:
                self._active_id = None

    def get(self, job_id: str) -> Job | None:
        return self._jobs.get(job_id)

    def active(self) -> Job | None:
        return self._jobs.get(self._active_id) if self._active_id else None


registry = JobRegistry()
