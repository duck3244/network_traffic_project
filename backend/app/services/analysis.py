"""analyze_traffic.py 의 분석 로직을 JSON 시리얼라이즈 가능한 dict 로 노출.

라우터에서 동기로 호출. 시각화는 프론트가 Recharts 등으로 렌더링하므로 여기선
숫자 배열까지만 제공한다 (matplotlib 의존성 제거).
"""

from __future__ import annotations

from pathlib import Path

from app.services.datasets import resolve_dataset

TARGET = "total_bytes_per_sec"


def run_analysis(
    name: str,
    *,
    bins: int = 50,
    timeline_max_points: int = 500,
    top_n_peaks: int = 10,
    anomaly_samples: int = 10,
) -> dict:
    """processed 데이터셋 한 개에 대한 분석 결과 dict."""
    import numpy as np
    import pandas as pd

    path: Path = resolve_dataset(name)
    df = pd.read_csv(path)
    if "timestamp" in df.columns:
        df["timestamp"] = pd.to_datetime(df["timestamp"])

    out: dict = {
        "name": path.name,
        "rows": int(len(df)),
        "columns": list(df.columns),
        "stats": None,
        "period": None,
        "peaks": None,
        "hourly": None,
        "daily": None,
        "anomalies": None,
        "distribution": None,
        "timeline": None,
    }

    if "timestamp" in df.columns and len(df) > 0:
        out["period"] = {
            "start": df["timestamp"].min().isoformat(),
            "end": df["timestamp"].max().isoformat(),
        }

    if TARGET not in df.columns:
        return out

    s = df[TARGET].astype(float)

    out["stats"] = {
        "min": float(s.min()),
        "max": float(s.max()),
        "mean": float(s.mean()),
        "median": float(s.median()),
        "std": float(s.std() or 0.0),
        "p95": float(s.quantile(0.95)),
        "p99": float(s.quantile(0.99)),
    }

    top = df.nlargest(top_n_peaks, TARGET)
    out["peaks"] = [
        {
            "timestamp": (
                row["timestamp"].isoformat() if "timestamp" in row else None
            ),
            "value": float(row[TARGET]),
        }
        for _, row in top.iterrows()
    ]

    if "hour" in df.columns:
        h = df.groupby("hour")[TARGET].agg(["mean", "std", "max"]).reset_index()
        out["hourly"] = [
            {
                "hour": int(r["hour"]),
                "mean": float(r["mean"]),
                "std": float(r["std"] or 0.0),
                "max": float(r["max"]),
            }
            for _, r in h.iterrows()
        ]

    if "day_of_week" in df.columns:
        d = df.groupby("day_of_week")[TARGET].agg(["mean", "std", "max"]).reset_index()
        out["daily"] = [
            {
                "day_of_week": int(r["day_of_week"]),
                "mean": float(r["mean"]),
                "std": float(r["std"] or 0.0),
                "max": float(r["max"]),
            }
            for _, r in d.iterrows()
        ]

    if "is_anomaly" in df.columns:
        mask = df["is_anomaly"].astype(bool)
        count = int(mask.sum())
        samples: list[dict] = []
        if count > 0:
            head = df[mask].head(anomaly_samples)
            for _, row in head.iterrows():
                samples.append(
                    {
                        "timestamp": (
                            row["timestamp"].isoformat()
                            if "timestamp" in row
                            else None
                        ),
                        "value": float(row[TARGET]),
                        "z_score": (
                            float(row["z_score"]) if "z_score" in row else None
                        ),
                    }
                )
        out["anomalies"] = {
            "count": count,
            "ratio": float(count / len(df)) if len(df) else 0.0,
            "samples": samples,
        }

    values = s.dropna().to_numpy()
    if values.size > 0:
        counts, edges = np.histogram(values, bins=bins)
        out["distribution"] = {
            "bin_edges": [float(x) for x in edges],
            "counts": [int(x) for x in counts],
        }

    if "timestamp" in df.columns and len(df) > 0:
        step = max(1, len(df) // max(1, timeline_max_points))
        sampled = df.iloc[::step][["timestamp", TARGET]]
        out["timeline"] = [
            {
                "timestamp": r["timestamp"].isoformat(),
                "value": float(r[TARGET]),
            }
            for _, r in sampled.iterrows()
        ]

    return out
