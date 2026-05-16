"""
TOTEM GEANT traffic matrix XML들을 현 프로젝트 CSV 스키마로 변환.

각 XML(15분 간격)의 모든 src→dst kbps를 합산해 네트워크 전체 트래픽으로 변환.
kbps × 125 = bytes/sec.
"""
import os
import re
import xml.etree.ElementTree as ET
from datetime import datetime
import pandas as pd

SRC_DIR = 'data/raw/geant/traffic-matrices'
OUT_PATH = 'data/raw/geant_traffic.csv'

FNAME_RE = re.compile(r'IntraTM-(\d{4})-(\d{2})-(\d{2})-(\d{2})-(\d{2})\.xml')


def parse_file(path):
    tree = ET.parse(path)
    total_kbps = 0.0
    for dst in tree.iter('dst'):
        total_kbps += float(dst.text)
    return total_kbps


def main():
    files = sorted(os.listdir(SRC_DIR))
    print(f"파싱 대상: {len(files)}개 XML")

    records = []
    for i, fname in enumerate(files):
        m = FNAME_RE.match(fname)
        if not m:
            continue
        ts = datetime(*[int(x) for x in m.groups()])
        kbps = parse_file(os.path.join(SRC_DIR, fname))
        records.append({
            'timestamp': ts,
            'total_bytes_per_sec': kbps * 125.0,  # kbps → bytes/sec
        })
        if (i + 1) % 1000 == 0:
            print(f"  {i+1}/{len(files)} 진행")

    df = pd.DataFrame(records).sort_values('timestamp').reset_index(drop=True)
    df.to_csv(OUT_PATH, index=False)
    print(f"\n저장 완료: {OUT_PATH}")
    print(f"행 수: {len(df)}")
    print(f"기간: {df['timestamp'].min()} ~ {df['timestamp'].max()}")
    print(f"트래픽 범위(bytes/sec): {df['total_bytes_per_sec'].min():,.0f} ~ {df['total_bytes_per_sec'].max():,.0f}")
    print(f"평균: {df['total_bytes_per_sec'].mean():,.0f}")


if __name__ == "__main__":
    main()
