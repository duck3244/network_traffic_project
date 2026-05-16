"""raw → processed CSV 전처리.

두 가지 프리셋:
- "default": 1분 간격 가정. TrafficDataProcessor.process_and_save를 그대로 호출.
- "geant":  15분 간격 GEANT 데이터. process_geant.py 의 outlier-clip + log1p +
            trend feature + GEANT lag 파이프라인을 인라인.

TF 의존 없음. BackgroundTasks 에서 호출되는 _job 래퍼가 JobRegistry 진행률을 보고한다.
"""

from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path
from typing import Literal

from app.core.state import registry
from app.services.datasets import resolve_dataset
from config import PROCESSED_DATA_DIR

Preset = Literal["default", "geant"]


def _report(job_id: str | None, progress: float, message: str) -> None:
    if job_id is not None:
        registry.update(job_id, progress=progress, message=message)


def _output_path(input_name: str, output_name: str | None) -> str:
    if output_name is None:
        output_name = f"processed_{input_name}"
    safe = Path(output_name).name
    if safe != output_name or not safe.lower().endswith(".csv"):
        raise ValueError(f"invalid output name: {output_name}")
    return os.path.join(PROCESSED_DATA_DIR, safe)


def _run_default(
    input_path: Path,
    output_path: str,
    *,
    add_features: bool,
    detect_anomaly: bool,
    job_id: str | None,
) -> dict:
    from utils.data_processor import TrafficDataProcessor

    _report(job_id, 0.30, "default preset: loading + features")
    processor = TrafficDataProcessor()
    df, saved_path = processor.process_and_save(
        str(input_path),
        os.path.basename(output_path),
        add_features=add_features,
        detect_anomaly=detect_anomaly,
    )
    return {
        "path": saved_path,
        "rows": int(len(df)),
        "columns": int(df.shape[1]),
        "feature_cols": [c for c in df.columns if c != "timestamp"],
    }


def _run_geant(input_path: Path, output_path: str, *, job_id: str | None) -> dict:
    """process_geant.py의 파이프라인을 라우터에서 호출 가능하게 옮긴 버전."""
    import numpy as np

    from utils.data_processor import TrafficDataProcessor

    GEANT_LAGS = (1, 4, 96)

    p = TrafficDataProcessor()
    _report(job_id, 0.15, "geant preset: loading")
    df = p.load_data(str(input_path))

    target = "total_bytes_per_sec"
    if target not in df.columns:
        raise ValueError(f"required column missing: {target}")

    _report(job_id, 0.30, "outlier clip + log1p")
    cap = df[target].quantile(0.99)
    df[target] = df[target].clip(upper=cap)
    df[target] = np.log1p(df[target])

    _report(job_id, 0.50, "time + trend features")
    df = p.add_time_features(df)
    n = len(df)
    df["trend_index"] = np.arange(n) / max(n, 1)
    df["trend_index_sq"] = df["trend_index"] ** 2

    _report(job_id, 0.65, "statistical features + lags")
    df = p.add_statistical_features(df)
    df = p.add_lag_features(df, lags=GEANT_LAGS)

    lag_cols = [c for c in df.columns if "_lag" in c]
    if lag_cols:
        df = df.dropna(subset=lag_cols).reset_index(drop=True)

    _report(job_id, 0.80, "anomaly detection + fill")
    df = p.detect_anomalies(df)
    df = df.ffill().bfill().fillna(0)

    _report(job_id, 0.90, f"writing {Path(output_path).name}")
    df.to_csv(output_path, index=False)
    return {
        "path": output_path,
        "rows": int(len(df)),
        "columns": int(df.shape[1]),
        "feature_cols": [c for c in df.columns if c != "timestamp"],
    }


def run_preprocessing(
    input_name: str,
    *,
    preset: Preset = "default",
    add_features: bool = True,
    detect_anomaly: bool = True,
    output_name: str | None = None,
    job_id: str | None = None,
) -> dict:
    """raw 데이터셋 한 개를 받아 processed CSV를 생성한다.

    job_id 가 주어지면 JobRegistry 에 진행률을 보고. 라우터에서 BackgroundTasks
    로 호출할 때 사용.
    """
    _report(job_id, 0.05, f"resolving {input_name}")
    input_path = resolve_dataset(input_name)
    output_path = _output_path(input_name, output_name)

    if preset == "default":
        info = _run_default(
            input_path,
            output_path,
            add_features=add_features,
            detect_anomaly=detect_anomaly,
            job_id=job_id,
        )
    elif preset == "geant":
        info = _run_geant(input_path, output_path, job_id=job_id)
    else:
        raise ValueError(f"unknown preset: {preset}")

    st = Path(info["path"]).stat()
    info["size_bytes"] = int(st.st_size)
    info["modified_at"] = datetime.fromtimestamp(st.st_mtime).isoformat()
    info["preset"] = preset
    return info


def run_preprocessing_job(
    job_id: str,
    input_name: str,
    *,
    preset: Preset = "default",
    add_features: bool = True,
    detect_anomaly: bool = True,
    output_name: str | None = None,
) -> None:
    """BackgroundTasks 진입점. 예외를 잡 상태에 기록하고 정상 종료한다."""
    try:
        info = run_preprocessing(
            input_name,
            preset=preset,
            add_features=add_features,
            detect_anomaly=detect_anomaly,
            output_name=output_name,
            job_id=job_id,
        )
        registry.update(
            job_id,
            status="succeeded",
            progress=1.0,
            message="done",
            result=info,
        )
    except Exception as e:  # noqa: BLE001 — 잡 실패를 라우터로 흘려보내지 않고 상태에 기록
        registry.update(job_id, status="failed", error=str(e))
