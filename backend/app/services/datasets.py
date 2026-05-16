"""raw/processed 디렉토리에서 데이터셋 파일 경로 해석."""

from __future__ import annotations

from pathlib import Path

from config import PROCESSED_DATA_DIR, RAW_DATA_DIR


def resolve_dataset(name: str) -> Path:
    """데이터셋 파일을 raw → processed 순으로 찾는다.

    Why: 학습/예측 라우터가 모두 '파일명만' 받아서 디스크 경로를 풀어야 하므로 한 곳에 집약.
    경로 traversal 차단 위해 basename만 허용.
    """
    safe = Path(name).name
    if not safe or safe != name:
        raise FileNotFoundError(f"invalid dataset name: {name}")
    for base in (RAW_DATA_DIR, PROCESSED_DATA_DIR):
        candidate = Path(base) / safe
        if candidate.exists():
            return candidate
    raise FileNotFoundError(f"dataset not found: {safe}")
