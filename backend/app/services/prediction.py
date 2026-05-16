"""예측 실행 — TrafficForecaster를 캐싱하면서 라우터에서 재사용한다.

- 첫 호출 시 .h5 + 스케일러 로딩 (수 초). 이후 호출은 캐시 히트.
- 단일 사용자 MVP라 프로세스 내 dict 캐시로 충분.
- TF는 forecaster 생성 시 lazy import.
"""

from __future__ import annotations

import threading
from pathlib import Path
from typing import Any

from app.services.datasets import resolve_dataset
from config import MODELS_DIR

_cache_lock = threading.Lock()
_cache: dict[str, Any] = {}


def _get_forecaster(model_name: str):
    """model_name(파일명) 기준 TrafficForecaster 캐싱."""
    safe = Path(model_name).name
    if safe != model_name or not safe.endswith(".h5"):
        raise FileNotFoundError(f"invalid model name: {model_name}")

    with _cache_lock:
        cached = _cache.get(safe)
        if cached is not None:
            return cached

        path = Path(MODELS_DIR) / safe
        if not path.exists():
            raise FileNotFoundError(f"model not found: {safe}")

        from predict import TrafficForecaster  # lazy: TF 로딩 지연

        forecaster = TrafficForecaster(str(path))
        _cache[safe] = forecaster
        return forecaster


def invalidate(model_name: str | None = None) -> None:
    """학습 후 같은 이름의 모델을 갱신할 때 캐시에서 제거."""
    with _cache_lock:
        if model_name is None:
            _cache.clear()
        else:
            _cache.pop(Path(model_name).name, None)


def _required_features(forecaster: Any) -> list[str] | None:
    """모델 학습 시 사용된 feature 이름 목록 (없으면 None).

    Why: 학습 때 fit 된 sklearn scaler 의 feature_names_in_ 만이 권위 있는 정보다.
    데이터가 일부 feature 만 가지고 있어도 sklearn 은 정확히 12개 같은 fixed shape 을
    요구하므로, transform 전에 사전 검증해서 의미 있는 에러를 돌려줘야 한다.
    """
    scaler = getattr(forecaster, "scaler", None)
    if scaler is None:
        return None
    names = getattr(scaler, "feature_names_in_", None)
    return list(names) if names is not None else None


def run_prediction(model_name: str, dataset: str, steps: int) -> list[dict]:
    """예측 결과를 [{t, value}, ...] 시계열 포인트 배열로 반환."""
    import pandas as pd

    data_path = resolve_dataset(dataset)
    df = pd.read_csv(data_path)
    if "timestamp" in df.columns:
        df["timestamp"] = pd.to_datetime(df["timestamp"])

    forecaster = _get_forecaster(model_name)

    required = _required_features(forecaster)
    if required is not None:
        missing = [c for c in required if c not in df.columns]
        if missing:
            preview = ", ".join(missing[:6])
            more = "" if len(missing) <= 6 else f" (+{len(missing) - 6} more)"
            raise ValueError(
                f"dataset '{dataset}' is missing {len(missing)} feature(s) "
                f"required by model '{model_name}': {preview}{more}. "
                f"This model expects {len(required)} features in total. "
                f"Train a new model on this dataset, or regenerate the dataset "
                f"with matching preprocessing (preset/lags)."
            )

    predictions = forecaster.predict_next_steps(df, steps=steps)
    return [{"t": i, "value": float(v)} for i, v in enumerate(predictions)]
