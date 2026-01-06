"""
네트워크 트래픽 예측 모델 학습 스크립트
"""
import numpy as np
import pandas as pd
import argparse
import os
import json
from datetime import datetime

from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
import tensorflow as tf
from tensorflow import keras
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM, Dense, Dropout
from tensorflow.keras.callbacks import EarlyStopping, ModelCheckpoint

from utils.data_processor import TrafficDataProcessor
from config import (SEQUENCE_LENGTH, TRAIN_TEST_SPLIT, LSTM_UNITS, 
                   DROPOUT_RATE, LEARNING_RATE, EPOCHS, BATCH_SIZE, MODELS_DIR)


class TrafficPredictor:
    """트래픽 예측 모델 클래스"""
    
    def __init__(self, sequence_length=SEQUENCE_LENGTH, model_type='lstm'):
        """
        Args:
            sequence_length: 입력 시퀀스 길이
            model_type: 모델 타입 ('lstm', 'gru', 'simple_rnn')
        """
        self.sequence_length = sequence_length
        self.model_type = model_type
        self.model = None
        self.scaler = None
        self.processor = TrafficDataProcessor()
        
    def build_lstm_model(self, input_shape):
        """LSTM 모델 구축"""
        model = Sequential([
            LSTM(LSTM_UNITS[0], return_sequences=True, input_shape=input_shape),
            Dropout(DROPOUT_RATE),
            LSTM(LSTM_UNITS[1], return_sequences=False),
            Dropout(DROPOUT_RATE),
            Dense(16, activation='relu'),
            Dense(1)
        ])
        
        optimizer = keras.optimizers.Adam(learning_rate=LEARNING_RATE)
        model.compile(optimizer=optimizer, loss='mse', metrics=['mae'])
        
        return model
    
    def prepare_data(self, df, target_col='total_bytes_per_sec', test_size=0.2):
        """
        학습 데이터 준비
        
        Args:
            df: 입력 DataFrame
            target_col: 예측 대상 컬럼
            test_size: 테스트 데이터 비율
        """
        print("데이터 준비 중...")
        
        # 타겟 컬럼 확인
        if target_col not in df.columns:
            raise ValueError(f"Target column '{target_col}' not found in DataFrame")
        
        # 특성 선택 (숫자형 컬럼만)
        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        
        # 제외할 컬럼 (target_col도 create_sequences에서 제외되므로 여기서도 제외)
        exclude_cols = ['is_anomaly', 'z_score', 'errors', 'drops', target_col]
        feature_cols = [col for col in numeric_cols if col not in exclude_cols]
        
        print(f"사용할 특성: {len(feature_cols)}개")
        print(f"특성 목록: {feature_cols}")
        
        # 데이터 정규화
        from sklearn.preprocessing import MinMaxScaler
        self.scaler = MinMaxScaler()
        
        scaled_data = self.scaler.fit_transform(df[feature_cols])
        scaled_df = pd.DataFrame(scaled_data, columns=feature_cols)
        
        # target 컬럼도 스케일링 (예측값 역변환을 위해)
        target_scaler = MinMaxScaler()
        scaled_target = target_scaler.fit_transform(df[[target_col]])
        scaled_df[target_col] = scaled_target
        
        # 시퀀스 생성 (이제 target_col이 포함된 상태)
        X, y = self.processor.create_sequences(
            scaled_df, 
            sequence_length=self.sequence_length,
            target_col=target_col
        )
        
        # target_scaler도 저장
        self.target_scaler = target_scaler
        
        print(f"시퀀스 shape: X={X.shape}, y={y.shape}")
        
        # 학습/테스트 분할
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=test_size, shuffle=False
        )
        
        print(f"학습 데이터: {X_train.shape}, 테스트 데이터: {X_test.shape}")
        
        return X_train, X_test, y_train, y_test, feature_cols
    
    def train(self, X_train, y_train, X_val=None, y_val=None, epochs=EPOCHS, batch_size=BATCH_SIZE):
        """
        모델 학습
        
        Args:
            X_train: 학습 데이터
            y_train: 학습 라벨
            X_val: 검증 데이터
            y_val: 검증 라벨
            epochs: 학습 에포크 수
            batch_size: 배치 크기
        """
        print("모델 구축 중...")
        
        input_shape = (X_train.shape[1], X_train.shape[2])
        
        if self.model_type == 'lstm':
            self.model = self.build_lstm_model(input_shape)
        else:
            raise ValueError(f"Unsupported model type: {self.model_type}")
        
        print(self.model.summary())
        
        # 콜백 설정
        callbacks = [
            EarlyStopping(monitor='val_loss', patience=10, restore_best_weights=True),
            ModelCheckpoint(
                os.path.join(MODELS_DIR, 'best_model.h5'),
                monitor='val_loss',
                save_best_only=True
            )
        ]
        
        # 학습
        print("모델 학습 시작...")
        
        validation_data = (X_val, y_val) if X_val is not None else None
        
        history = self.model.fit(
            X_train, y_train,
            validation_data=validation_data,
            epochs=epochs,
            batch_size=batch_size,
            callbacks=callbacks,
            verbose=1
        )
        
        return history
    
    def evaluate(self, X_test, y_test):
        """모델 평가"""
        print("\n모델 평가 중...")
        
        y_pred = self.model.predict(X_test)
        
        # 메트릭 계산
        mse = mean_squared_error(y_test, y_pred)
        rmse = np.sqrt(mse)
        mae = mean_absolute_error(y_test, y_pred)
        r2 = r2_score(y_test, y_pred)
        
        # 원래 스케일로 복원하여 평가
        if hasattr(self, 'target_scaler'):
            y_test_orig = self.target_scaler.inverse_transform(y_test.reshape(-1, 1)).flatten()
            y_pred_orig = self.target_scaler.inverse_transform(y_pred).flatten()
        else:
            # target_scaler가 없으면 일반 scaler의 첫 번째 특성 사용
            y_test_orig = y_test * (self.scaler.data_max_[0] - self.scaler.data_min_[0]) + self.scaler.data_min_[0]
            y_pred_orig = y_pred.flatten() * (self.scaler.data_max_[0] - self.scaler.data_min_[0]) + self.scaler.data_min_[0]
        
        mae_orig = mean_absolute_error(y_test_orig, y_pred_orig)
        
        print(f"\n평가 결과:")
        print(f"  MSE: {mse:.6f}")
        print(f"  RMSE: {rmse:.6f}")
        print(f"  MAE: {mae:.6f}")
        print(f"  MAE (원본 스케일): {mae_orig:.2f} bytes/sec")
        print(f"  R² Score: {r2:.6f}")
        
        metrics = {
            'mse': float(mse),
            'rmse': float(rmse),
            'mae': float(mae),
            'mae_original': float(mae_orig),
            'r2': float(r2)
        }
        
        return metrics, y_pred
    
    def save_model(self, filepath):
        """모델 저장"""
        self.model.save(filepath)
        print(f"모델 저장: {filepath}")
        
        # 스케일러도 함께 저장
        import joblib
        scaler_path = filepath.replace('.h5', '_scaler.pkl')
        joblib.dump(self.scaler, scaler_path)
        print(f"스케일러 저장: {scaler_path}")
        
        # target_scaler도 저장 (예측값 역변환용)
        if hasattr(self, 'target_scaler'):
            target_scaler_path = filepath.replace('.h5', '_target_scaler.pkl')
            joblib.dump(self.target_scaler, target_scaler_path)
            print(f"타겟 스케일러 저장: {target_scaler_path}")
        
    def load_model(self, filepath):
        """모델 로드"""
        self.model = keras.models.load_model(filepath)
        print(f"모델 로드: {filepath}")
        
        # 스케일러도 함께 로드
        import joblib
        scaler_path = filepath.replace('.h5', '_scaler.pkl')
        if os.path.exists(scaler_path):
            self.scaler = joblib.load(scaler_path)
            print(f"스케일러 로드: {scaler_path}")


def main():
    parser = argparse.ArgumentParser(description='트래픽 예측 모델 학습')
    parser.add_argument('--data', type=str, required=True,
                        help='학습 데이터 CSV 파일 경로')
    parser.add_argument('--model', type=str, default='lstm',
                        choices=['lstm', 'gru'],
                        help='모델 타입')
    parser.add_argument('--epochs', type=int, default=EPOCHS,
                        help='학습 에포크 수')
    parser.add_argument('--batch-size', type=int, default=BATCH_SIZE,
                        help='배치 크기')
    parser.add_argument('--sequence-length', type=int, default=SEQUENCE_LENGTH,
                        help='입력 시퀀스 길이')
    parser.add_argument('--output', type=str, default=None,
                        help='모델 저장 경로')
    
    args = parser.parse_args()
    
    # 데이터 로드
    print(f"데이터 로드: {args.data}")
    df = pd.read_csv(args.data)
    
    # 모델 생성
    predictor = TrafficPredictor(
        sequence_length=args.sequence_length,
        model_type=args.model
    )
    
    # 데이터 준비
    X_train, X_test, y_train, y_test, feature_cols = predictor.prepare_data(df)
    
    # 검증 데이터 분할
    split_idx = int(len(X_train) * 0.9)
    X_val = X_train[split_idx:]
    y_val = y_train[split_idx:]
    X_train = X_train[:split_idx]
    y_train = y_train[:split_idx]
    
    # 학습
    history = predictor.train(
        X_train, y_train,
        X_val, y_val,
        epochs=args.epochs,
        batch_size=args.batch_size
    )
    
    # 평가
    metrics, y_pred = predictor.evaluate(X_test, y_test)
    
    # 모델 저장
    if args.output is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        model_path = os.path.join(MODELS_DIR, f'traffic_{args.model}_{timestamp}.h5')
    else:
        model_path = args.output
    
    predictor.save_model(model_path)
    
    # 메트릭 저장
    metrics_path = model_path.replace('.h5', '_metrics.json')
    with open(metrics_path, 'w') as f:
        json.dump(metrics, f, indent=2)
    print(f"메트릭 저장: {metrics_path}")
    
    print("\n학습 완료!")


if __name__ == "__main__":
    main()
