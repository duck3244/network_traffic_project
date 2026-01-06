"""
네트워크 트래픽 데이터 전처리 모듈
"""
import pandas as pd
import numpy as np
from sklearn.preprocessing import MinMaxScaler, StandardScaler
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import PROCESSED_DATA_DIR, SEQUENCE_LENGTH


class TrafficDataProcessor:
    """트래픽 데이터 전처리 클래스"""
    
    def __init__(self, scaler_type='minmax'):
        """
        Args:
            scaler_type: 스케일링 방법 ('minmax' 또는 'standard')
        """
        self.scaler_type = scaler_type
        self.scaler = MinMaxScaler() if scaler_type == 'minmax' else StandardScaler()
        
    def load_data(self, filepath):
        """CSV 파일에서 데이터 로드"""
        df = pd.read_csv(filepath)
        
        # timestamp를 datetime으로 변환
        if 'timestamp' in df.columns:
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            df = df.sort_values('timestamp')
        
        return df
    
    def add_time_features(self, df):
        """시간 기반 특성 추가"""
        if 'timestamp' not in df.columns:
            return df
        
        df = df.copy()
        df['hour'] = df['timestamp'].dt.hour
        df['day_of_week'] = df['timestamp'].dt.dayofweek
        df['minute'] = df['timestamp'].dt.minute
        
        # 주기적 특성으로 변환 (사인/코사인)
        df['hour_sin'] = np.sin(2 * np.pi * df['hour'] / 24)
        df['hour_cos'] = np.cos(2 * np.pi * df['hour'] / 24)
        df['day_sin'] = np.sin(2 * np.pi * df['day_of_week'] / 7)
        df['day_cos'] = np.cos(2 * np.pi * df['day_of_week'] / 7)
        
        return df
    
    def add_statistical_features(self, df, window_size=10):
        """통계적 특성 추가 (이동평균, 표준편차 등)"""
        df = df.copy()
        
        traffic_col = 'total_bytes_per_sec'
        
        if traffic_col in df.columns:
            # 이동평균
            df[f'{traffic_col}_ma{window_size}'] = df[traffic_col].rolling(
                window=window_size, min_periods=1).mean()
            
            # 이동 표준편차
            df[f'{traffic_col}_std{window_size}'] = df[traffic_col].rolling(
                window=window_size, min_periods=1).std().fillna(0)
            
            # 변화율
            df[f'{traffic_col}_diff'] = df[traffic_col].diff().fillna(0)
            
        return df
    
    def detect_anomalies(self, df, column='total_bytes_per_sec', threshold=3):
        """이상치 탐지 (Z-score 기반)"""
        df = df.copy()
        
        if column in df.columns:
            mean = df[column].mean()
            std = df[column].std()
            
            df['z_score'] = (df[column] - mean) / std
            df['is_anomaly'] = np.abs(df['z_score']) > threshold
            
        return df
    
    def create_sequences(self, data, sequence_length=24, target_col='total_bytes_per_sec'):
        """
        시계열 예측을 위한 시퀀스 생성
        
        Args:
            data: numpy array 또는 DataFrame
            sequence_length: 입력 시퀀스 길이
            target_col: 예측 대상 컬럼
            
        Returns:
            X: 입력 시퀀스 (samples, sequence_length, features)
            y: 타겟 값 (samples,)
        """
        if isinstance(data, pd.DataFrame):
            if target_col not in data.columns:
                raise ValueError(f"Column '{target_col}' not found in DataFrame")
            
            # 타겟 컬럼을 제외한 특성들
            feature_cols = [col for col in data.columns if col not in ['timestamp', target_col]]
            
            if feature_cols:
                X_data = data[feature_cols].values
            else:
                X_data = data[[target_col]].values
                
            y_data = data[target_col].values
        else:
            X_data = data
            y_data = data[:, 0] if len(data.shape) > 1 else data
        
        X, y = [], []
        
        for i in range(len(X_data) - sequence_length):
            X.append(X_data[i:i+sequence_length])
            y.append(y_data[i+sequence_length])
        
        return np.array(X), np.array(y)
    
    def process_and_save(self, input_filepath, output_filename=None, 
                        add_features=True, detect_anomaly=True):
        """
        전체 전처리 파이프라인 실행 및 저장
        
        Args:
            input_filepath: 입력 파일 경로
            output_filename: 출력 파일명
            add_features: 추가 특성 생성 여부
            detect_anomaly: 이상치 탐지 여부
        """
        print(f"데이터 로딩: {input_filepath}")
        df = self.load_data(input_filepath)
        
        print(f"원본 데이터 shape: {df.shape}")
        
        # 특성 추가
        if add_features:
            print("시간 기반 특성 추가...")
            df = self.add_time_features(df)
            
            print("통계적 특성 추가...")
            df = self.add_statistical_features(df)
        
        # 이상치 탐지
        if detect_anomaly:
            print("이상치 탐지...")
            df = self.detect_anomalies(df)
        
        # 결측치 처리
        print("결측치 처리...")
        df = df.fillna(method='ffill').fillna(method='bfill').fillna(0)
        
        print(f"처리된 데이터 shape: {df.shape}")
        
        # 저장
        if output_filename is None:
            base_name = os.path.basename(input_filepath)
            output_filename = f"processed_{base_name}"
        
        output_path = os.path.join(PROCESSED_DATA_DIR, output_filename)
        df.to_csv(output_path, index=False)
        print(f"전처리된 데이터 저장: {output_path}")
        
        return df, output_path


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='트래픽 데이터 전처리')
    parser.add_argument('--input', type=str, required=True,
                        help='입력 CSV 파일 경로')
    parser.add_argument('--output', type=str, default=None,
                        help='출력 파일명')
    parser.add_argument('--no-features', action='store_true',
                        help='추가 특성 생성 안함')
    parser.add_argument('--no-anomaly', action='store_true',
                        help='이상치 탐지 안함')
    
    args = parser.parse_args()
    
    processor = TrafficDataProcessor()
    processor.process_and_save(
        args.input, 
        args.output,
        add_features=not args.no_features,
        detect_anomaly=not args.no_anomaly
    )


if __name__ == "__main__":
    main()
