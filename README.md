# Network Traffic Analysis & Prediction Project

네트워크 트래픽 데이터를 수집, 분석하고 향후 트래픽을 예측하는 프로젝트입니다.

---

## 프로젝트 구조

```
network_traffic_project/
├── data/                      # 데이터 저장 디렉토리
│   ├── raw/                   # 원본 데이터
│   ├── processed/             # 전처리된 데이터
│   └── predictions/           # 예측 결과
├── models/                    # 학습된 모델 저장
├── utils/                     # 유틸리티 함수
│   ├── data_collector.py      # 데이터 수집
│   ├── data_processor.py      # 데이터 전처리
│   └── visualizer.py          # 시각화
├── generate_sample_data.py    # Sample 데이터 생성 스크립트
├── train_model.py             # 모델 학습 스크립트
├── predict.py                 # 예측 스크립트
├── analyze_traffic.py         # 트래픽 분석 스크립트
├── requirements.txt           # 의존성 패키지
└── config.py                  # 설정 파일
```

---

## 주요 기능

1. **데이터 수집**: 네트워크 트래픽 데이터 실시간/배치 수집
2. **데이터 분석**: 트래픽 패턴, 이상 탐지, 통계 분석
3. **트래픽 예측**: LSTM을 사용한 시계열 예측
4. **시각화**: 트래픽 추이, 예측 결과 시각화

---

## 설치 방법

```bash
pip install -r requirements.txt
```

---

## 사용 방법

### 1. 데이터 수집
```bash
python -m utils.data_collector --duration 300 --interval 1
```

### 2. 트래픽 분석
```bash
python analyze_traffic.py --input data/raw/traffic_data.csv
```

### 3. 모델 학습
```bash
python train_model.py --data data/processed/traffic_processed.csv --model lstm
```

### 4. 트래픽 예측
```bash
python predict.py --model models/traffic_lstm.h5 --steps 24
```

---