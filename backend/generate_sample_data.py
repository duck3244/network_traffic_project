"""
테스트용 샘플 네트워크 트래픽 데이터 생성 스크립트
"""
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import argparse
import os
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from config import RAW_DATA_DIR


def generate_sample_traffic(duration_minutes=60, interval_seconds=1, 
                           base_traffic=1_000_000, noise_level=0.3):
    """
    샘플 네트워크 트래픽 데이터 생성
    
    Args:
        duration_minutes: 생성할 데이터 기간 (분)
        interval_seconds: 데이터 수집 간격 (초)
        base_traffic: 기본 트래픽 (bytes/sec)
        noise_level: 노이즈 레벨 (0-1)
    """
    print(f"샘플 데이터 생성 중... (기간: {duration_minutes}분, 간격: {interval_seconds}초)")
    
    # 타임스탬프 생성
    start_time = datetime.now() - timedelta(minutes=duration_minutes)
    timestamps = []
    current_time = start_time
    
    while current_time < datetime.now():
        timestamps.append(current_time)
        current_time += timedelta(seconds=interval_seconds)
    
    n_samples = len(timestamps)
    
    # 시간 기반 패턴 (일일 주기)
    hours = np.array([t.hour + t.minute/60 for t in timestamps])
    
    # 피크 시간대 패턴 (오전 9-12시, 오후 2-6시)
    daily_pattern = np.zeros(n_samples)
    for i, hour in enumerate(hours):
        if 9 <= hour < 12:  # 오전 피크
            daily_pattern[i] = 1.5
        elif 14 <= hour < 18:  # 오후 피크
            daily_pattern[i] = 2.0
        elif 18 <= hour < 22:  # 저녁 시간
            daily_pattern[i] = 1.2
        else:  # 야간
            daily_pattern[i] = 0.5
    
    # 트렌드 생성 (점진적 증가)
    trend = np.linspace(0, 0.3, n_samples)
    
    # 주기적 패턴 (더 미세한 변동)
    periodic = 0.2 * np.sin(2 * np.pi * np.arange(n_samples) / (60/interval_seconds))
    
    # 랜덤 노이즈
    noise = np.random.normal(0, noise_level, n_samples)
    
    # 최종 트래픽 계산
    total_bytes = base_traffic * (daily_pattern + trend + periodic + noise)
    total_bytes = np.maximum(total_bytes, 0)  # 음수 방지
    
    # 송신/수신 분리 (비율은 랜덤)
    send_ratio = np.random.uniform(0.3, 0.7, n_samples)
    bytes_sent = total_bytes * send_ratio
    bytes_recv = total_bytes * (1 - send_ratio)
    
    # 패킷 수 계산 (평균 패킷 크기 1500 bytes)
    avg_packet_size = 1500
    packets_sent = bytes_sent / avg_packet_size
    packets_recv = bytes_recv / avg_packet_size
    
    # 에러 및 드롭 (가끔 발생)
    errors = np.random.poisson(0.01, n_samples)
    drops = np.random.poisson(0.01, n_samples)
    
    # 이상치 추가 (5% 확률)
    anomaly_indices = np.random.choice(n_samples, size=int(n_samples*0.05), replace=False)
    for idx in anomaly_indices:
        total_bytes[idx] *= np.random.uniform(3, 5)
        bytes_sent[idx] = total_bytes[idx] * send_ratio[idx]
        bytes_recv[idx] = total_bytes[idx] * (1 - send_ratio[idx])
    
    # DataFrame 생성
    df = pd.DataFrame({
        'timestamp': timestamps,
        'bytes_sent_per_sec': bytes_sent,
        'bytes_recv_per_sec': bytes_recv,
        'packets_sent_per_sec': packets_sent,
        'packets_recv_per_sec': packets_recv,
        'total_bytes_per_sec': total_bytes,
        'errors': errors,
        'drops': drops
    })
    
    print(f"생성 완료: {len(df)} 개 데이터 포인트")
    print(f"트래픽 범위: {df['total_bytes_per_sec'].min():,.0f} - {df['total_bytes_per_sec'].max():,.0f} bytes/sec")
    
    return df


def main():
    parser = argparse.ArgumentParser(description='샘플 트래픽 데이터 생성')
    parser.add_argument('--duration', type=int, default=60,
                        help='생성할 데이터 기간 (분)')
    parser.add_argument('--interval', type=int, default=1,
                        help='데이터 수집 간격 (초)')
    parser.add_argument('--base-traffic', type=int, default=1_000_000,
                        help='기본 트래픽 (bytes/sec)')
    parser.add_argument('--noise', type=float, default=0.3,
                        help='노이즈 레벨 (0-1)')
    parser.add_argument('--output', type=str, default=None,
                        help='출력 파일명')
    
    args = parser.parse_args()
    
    # 샘플 데이터 생성
    df = generate_sample_traffic(
        duration_minutes=args.duration,
        interval_seconds=args.interval,
        base_traffic=args.base_traffic,
        noise_level=args.noise
    )
    
    # 저장
    if args.output is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"sample_traffic_{timestamp}.csv"
    else:
        filename = args.output
    
    filepath = os.path.join(RAW_DATA_DIR, filename)
    df.to_csv(filepath, index=False)
    print(f"데이터 저장: {filepath}")
    
    # 기본 통계 출력
    print("\n데이터 통계:")
    print(df.describe())


if __name__ == "__main__":
    main()
