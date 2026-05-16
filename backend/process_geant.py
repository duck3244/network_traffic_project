"""
GEANT 15분 간격 데이터 전처리 전용 스크립트.
기본 data_processor는 1분 간격 기준이라 lag 값을 GEANT 스텝에 맞게 재설정.
+ outlier clipping (99 percentile) + log1p 변환으로 분포 정규화.
"""
import os
import numpy as np
from utils.data_processor import TrafficDataProcessor
from config import PROCESSED_DATA_DIR

# 15분 간격 기준 lag:
#   lag1   → 15분 전
#   lag4   → 1시간 전
#   lag96  → 1일 전 (24h × 4)
GEANT_LAGS = (1, 4, 96)

INPUT = 'data/raw/geant_traffic.csv'
OUTPUT = 'processed_geant_traffic.csv'


def main():
    p = TrafficDataProcessor()

    print(f"데이터 로딩: {INPUT}")
    df = p.load_data(INPUT)
    print(f"원본 shape: {df.shape}")

    target = 'total_bytes_per_sec'
    cap = df[target].quantile(0.99)
    before_max = df[target].max()
    df[target] = df[target].clip(upper=cap)
    print(f"Outlier 클리핑 (99%): max {before_max:,.0f} → {df[target].max():,.0f}")

    df[target] = np.log1p(df[target])
    print(f"log1p 변환 후 범위: {df[target].min():.3f} ~ {df[target].max():.3f}")
    print(f"※ 이하 모든 통계/lag/평가는 log 공간에서 계산됩니다")

    print("시간 기반 특성 추가...")
    df = p.add_time_features(df)

    # 장기 추세를 명시적 feature로 (test 구간 분포 시프트 대응)
    n = len(df)
    df['trend_index'] = np.arange(n) / n
    df['trend_index_sq'] = df['trend_index'] ** 2
    print(f"Trend feature 추가: trend_index ∈ [0, {df['trend_index'].max():.3f}], trend_index_sq")

    print("통계적 특성 추가...")
    df = p.add_statistical_features(df)

    print(f"Lag 특성 추가 (15분 간격용): {GEANT_LAGS}")
    df = p.add_lag_features(df, lags=GEANT_LAGS)

    lag_cols = [c for c in df.columns if '_lag' in c]
    before = len(df)
    df = df.dropna(subset=lag_cols).reset_index(drop=True)
    print(f"Lag NaN 제거: {before} → {len(df)} 행")

    print("이상치 탐지...")
    df = p.detect_anomalies(df)

    print("결측치 처리...")
    df = df.ffill().bfill().fillna(0)

    out = os.path.join(PROCESSED_DATA_DIR, OUTPUT)
    df.to_csv(out, index=False)
    print(f"\n처리된 shape: {df.shape}")
    print(f"저장: {out}")


if __name__ == "__main__":
    main()
