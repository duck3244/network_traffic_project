# Quick Start Guide - 네트워크 트래픽 분석 및 예측

이 가이드는 프로젝트를 빠르게 시작하는 방법을 설명합니다.

## 1. 환경 설정

### 필수 패키지 설치
```bash
pip install -r requirements.txt
```

## 2. 테스트 시나리오

### 시나리오 A: 샘플 데이터로 전체 파이프라인 테스트

#### Step 1: 샘플 데이터 생성
```bash
python generate_sample_data.py --duration 120 --interval 1
```
- `--duration`: 생성할 데이터 기간 (분)
- `--interval`: 데이터 수집 간격 (초)

#### Step 2: 데이터 전처리
```bash
python -m utils.data_processor --input data/raw/sample_traffic_YYYYMMDD_HHMMSS.csv
```

#### Step 3: 트래픽 분석
```bash
python analyze_traffic.py --input data/processed/processed_sample_traffic_YYYYMMDD_HHMMSS.csv --visualize
```

#### Step 4: 모델 학습
```bash
python train_model.py --data data/processed/processed_sample_traffic_YYYYMMDD_HHMMSS.csv --epochs 50 --batch-size 32
```

#### Step 5: 예측 수행
```bash
python predict.py --model models/traffic_lstm_YYYYMMDD_HHMMSS.h5 --data data/processed/processed_sample_traffic_YYYYMMDD_HHMMSS.csv --steps 24 --visualize
```

---

### 시나리오 B: 실제 네트워크 트래픽 수집 및 분석

#### Step 1: 실시간 데이터 수집
```bash
# 5분간 데이터 수집 (1초 간격)
python -m utils.data_collector --duration 300 --interval 1

# 특정 인터페이스 지정 (예: eth0)
python -m utils.data_collector --duration 300 --interval 1 --interface eth0
```

#### Step 2: 데이터 전처리
```bash
python -m utils.data_processor --input data/raw/traffic_data_YYYYMMDD_HHMMSS.csv
```

#### Step 3: 분석 및 시각화
```bash
python analyze_traffic.py --input data/processed/processed_traffic_data_YYYYMMDD_HHMMSS.csv --visualize --output-dir ./reports
```

#### Step 4: 모델 학습
```bash
python train_model.py --data data/processed/processed_traffic_data_YYYYMMDD_HHMMSS.csv --epochs 100
```

#### Step 5: 미래 트래픽 예측
```bash
# 기본 예측 (24 스텝)
python predict.py --model models/traffic_lstm_YYYYMMDD_HHMMSS.h5 --data data/processed/processed_traffic_data_YYYYMMDD_HHMMSS.csv --steps 24 --visualize

# 신뢰구간 포함 예측
python predict.py --model models/traffic_lstm_YYYYMMDD_HHMMSS.h5 --data data/processed/processed_traffic_data_YYYYMMDD_HHMMSS.csv --steps 24 --confidence --visualize
```

---

## 3. 주요 명령어 옵션

### 데이터 수집 (`data_collector.py`)
- `--interface`: 네트워크 인터페이스 지정
- `--interval`: 수집 간격 (초)
- `--duration`: 수집 지속시간 (초)
- `--output`: 출력 파일명

### 데이터 전처리 (`data_processor.py`)
- `--input`: 입력 CSV 파일 경로
- `--output`: 출력 파일명
- `--no-features`: 추가 특성 생성 안함
- `--no-anomaly`: 이상치 탐지 안함

### 트래픽 분석 (`analyze_traffic.py`)
- `--input`: 분석할 CSV 파일
- `--visualize`: 시각화 생성
- `--output-dir`: 출력 디렉토리

### 모델 학습 (`train_model.py`)
- `--data`: 학습 데이터 CSV 파일
- `--model`: 모델 타입 (lstm, gru)
- `--epochs`: 학습 에포크 수
- `--batch-size`: 배치 크기
- `--sequence-length`: 입력 시퀀스 길이
- `--output`: 모델 저장 경로

### 예측 (`predict.py`)
- `--model`: 학습된 모델 파일
- `--data`: 입력 데이터 CSV 파일
- `--steps`: 예측할 미래 시점 수
- `--confidence`: 신뢰구간 포함 예측
- `--visualize`: 예측 결과 시각화
- `--output`: 예측 결과 저장 경로

---

## 4. 일반적인 워크플로우

```
데이터 수집 → 전처리 → 분석 → 모델 학습 → 예측
    ↓           ↓        ↓        ↓         ↓
  raw/    processed/  시각화   models/  predictions/
```

---

## 5. 팁 및 문제 해결

### 데이터가 너무 적을 때
- 샘플 데이터 생성 시 `--duration`을 늘리세요 (예: 1440분 = 1일)
- 또는 실제 데이터 수집 시간을 늘리세요

### 모델 성능이 낮을 때
- 더 많은 데이터 수집
- `--epochs` 증가
- `--sequence-length` 조정
- 학습률 조정 (config.py에서 LEARNING_RATE 수정)

### 메모리 부족
- `--batch-size` 감소
- 데이터 샘플링 (일부만 사용)

### 네트워크 인터페이스를 모를 때
```bash
# Linux/Mac
ifconfig

# Windows
ipconfig
```

---

## 6. 출력 파일 위치

- **원본 데이터**: `data/raw/`
- **전처리된 데이터**: `data/processed/`
- **학습된 모델**: `models/`
- **예측 결과**: `data/predictions/`
- **시각화 이미지**: 명령어에서 지정한 경로

---
