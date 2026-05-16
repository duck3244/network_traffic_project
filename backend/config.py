"""
프로젝트 설정 파일
"""
import os

# 경로 설정
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, 'data')
RAW_DATA_DIR = os.path.join(DATA_DIR, 'raw')
PROCESSED_DATA_DIR = os.path.join(DATA_DIR, 'processed')
PREDICTIONS_DIR = os.path.join(DATA_DIR, 'predictions')
MODELS_DIR = os.path.join(BASE_DIR, 'models')

# 디렉토리 생성
for directory in [RAW_DATA_DIR, PROCESSED_DATA_DIR, PREDICTIONS_DIR, MODELS_DIR]:
    os.makedirs(directory, exist_ok=True)

# 데이터 수집 설정
COLLECTION_INTERVAL = 1  # 초
COLLECTION_DURATION = 300  # 초 (5분)
INTERFACE = None  # None이면 기본 인터페이스 사용

# 데이터 전처리 설정
SEQUENCE_LENGTH = 120  # 1초 간격 데이터 기준 2분 윈도우 (단기 패턴 포착용)
TRAIN_TEST_SPLIT = 0.8  # 학습/테스트 데이터 비율

# 모델 설정
LSTM_UNITS = [32, 16]
DROPOUT_RATE = 0.2
LEARNING_RATE = 0.001
EPOCHS = 50
BATCH_SIZE = 32

# 예측 설정
PREDICTION_STEPS = 24  # 예측할 미래 시점 수

# 시각화 설정
FIGURE_SIZE = (15, 6)
DPI = 100

# 로깅 설정
LOG_LEVEL = 'INFO'
