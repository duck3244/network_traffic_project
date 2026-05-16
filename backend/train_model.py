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
        """
        print("데이터 준비 중...")

        if target_col not in df.columns:
            raise ValueError(f"Target column '{target_col}' not found in DataFrame")

        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()

        # target 누설 차단: target의 구성요소(sent/recv)와 파생값(ma/std/diff) 제외
        leakage_cols = {
            target_col,
            'bytes_sent_per_sec', 'bytes_recv_per_sec',
            f'{target_col}_ma10', f'{target_col}_std10', f'{target_col}_diff',
        }
        exclude_cols = {'is_anomaly', 'z_score', 'errors', 'drops'} | leakage_cols
        feature_cols = [c for c in numeric_cols if c not in exclude_cols]

        print(f"사용할 특성: {len(feature_cols)}개")
        print(f"특성 목록: {feature_cols}")

        # 시계열 분할: 스케일러 fit 전에 먼저 분리 (테스트 누설 차단)
        split_idx = int(len(df) * (1 - test_size))
        train_df = df.iloc[:split_idx]
        test_df = df.iloc[split_idx:]
        print(f"행 단위 분할 - train: {len(train_df)}, test: {len(test_df)}")

        from sklearn.preprocessing import MinMaxScaler
        self.scaler = MinMaxScaler().fit(train_df[feature_cols])
        self.target_scaler = MinMaxScaler().fit(train_df[[target_col]])

        train_X_scaled = self.scaler.transform(train_df[feature_cols])
        test_X_scaled = self.scaler.transform(test_df[feature_cols])
        train_y_scaled = self.target_scaler.transform(train_df[[target_col]]).flatten()
        test_y_scaled = self.target_scaler.transform(test_df[[target_col]]).flatten()

        seq_len = self.sequence_length

        # train 시퀀스
        X_train = np.array([train_X_scaled[i:i+seq_len] for i in range(len(train_X_scaled) - seq_len)])
        y_train = np.array([train_y_scaled[i+seq_len] for i in range(len(train_X_scaled) - seq_len)])

        # test 시퀀스: 시간적 연속성 위해 train 끝 seq_len을 워밍업으로 prepend
        combined_X = np.concatenate([train_X_scaled[-seq_len:], test_X_scaled])
        combined_y = np.concatenate([train_y_scaled[-seq_len:], test_y_scaled])
        X_test = np.array([combined_X[i:i+seq_len] for i in range(len(combined_X) - seq_len)])
        y_test = np.array([combined_y[i+seq_len] for i in range(len(combined_X) - seq_len)])

        print(f"시퀀스 shape: X_train={X_train.shape}, X_test={X_test.shape}")

        self.feature_cols = feature_cols
        return X_train, X_test, y_train, y_test, feature_cols
    
    def train(self, X_train, y_train, X_val=None, y_val=None, epochs=EPOCHS, batch_size=BATCH_SIZE,
              extra_callbacks=None):
        """
        모델 학습

        Args:
            X_train: 학습 데이터
            y_train: 학습 라벨
            X_val: 검증 데이터
            y_val: 검증 라벨
            epochs: 학습 에포크 수
            batch_size: 배치 크기
            extra_callbacks: 기본 콜백(EarlyStopping/ModelCheckpoint)에 추가할 Keras 콜백 리스트.
                서비스 계층에서 진행률 보고용 콜백을 주입할 때 사용.
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
        if extra_callbacks:
            callbacks.extend(extra_callbacks)
        
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
        """모델 평가 (원본 스케일 기준)"""
        print("\n모델 평가 중...")

        y_pred = self.model.predict(X_test).flatten()
        y_test = np.asarray(y_test).flatten()

        y_test_orig = self.target_scaler.inverse_transform(y_test.reshape(-1, 1)).flatten()
        y_pred_orig = self.target_scaler.inverse_transform(y_pred.reshape(-1, 1)).flatten()

        mse = mean_squared_error(y_test_orig, y_pred_orig)
        rmse = np.sqrt(mse)
        mae = mean_absolute_error(y_test_orig, y_pred_orig)
        r2 = r2_score(y_test_orig, y_pred_orig)

        print(f"\n평가 결과 (원본 스케일):")
        print(f"  MSE: {mse:,.2f}")
        print(f"  RMSE: {rmse:,.2f} bytes/sec")
        print(f"  MAE: {mae:,.2f} bytes/sec")
        print(f"  R² Score: {r2:.6f}")

        metrics = {
            'mse': float(mse),
            'rmse': float(rmse),
            'mae': float(mae),
            'r2': float(r2),
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
