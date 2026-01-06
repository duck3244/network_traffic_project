"""
네트워크 트래픽 예측 스크립트
"""
import numpy as np
import pandas as pd
import argparse
import os
import joblib
from datetime import datetime, timedelta
from tensorflow import keras

from utils.data_processor import TrafficDataProcessor
from utils.visualizer import TrafficVisualizer
from config import PREDICTION_STEPS, MODELS_DIR, PREDICTIONS_DIR, SEQUENCE_LENGTH


class TrafficForecaster:
    """트래픽 예측 클래스"""
    
    def __init__(self, model_path, scaler_path=None):
        """
        Args:
            model_path: 학습된 모델 파일 경로
            scaler_path: 스케일러 파일 경로
        """
        self.model_path = model_path
        
        # 모델 로드
        print(f"모델 로드: {model_path}")
        self.model = keras.models.load_model(model_path)
        
        # 스케일러 로드
        if scaler_path is None:
            scaler_path = model_path.replace('.h5', '_scaler.pkl')
        
        if os.path.exists(scaler_path):
            print(f"스케일러 로드: {scaler_path}")
            self.scaler = joblib.load(scaler_path)
        else:
            print("경고: 스케일러 파일을 찾을 수 없습니다.")
            self.scaler = None
        
        # target_scaler 로드 (있으면)
        target_scaler_path = model_path.replace('.h5', '_target_scaler.pkl')
        if os.path.exists(target_scaler_path):
            print(f"타겟 스케일러 로드: {target_scaler_path}")
            self.target_scaler = joblib.load(target_scaler_path)
        else:
            self.target_scaler = None
            
        self.processor = TrafficDataProcessor()
        
    def predict_next_steps(self, data, steps=PREDICTION_STEPS):
        """
        향후 N 스텝 예측
        
        Args:
            data: 최근 데이터 (DataFrame 또는 numpy array)
            steps: 예측할 미래 시점 수
            
        Returns:
            predictions: 예측 결과 array
        """
        print(f"향후 {steps} 스텝 예측 중...")
        
        # 데이터 준비
        if isinstance(data, pd.DataFrame):
            # 숫자형 컬럼만 선택 (학습 시와 동일한 방식)
            numeric_cols = data.select_dtypes(include=[np.number]).columns.tolist()
            exclude_cols = ['is_anomaly', 'z_score', 'errors', 'drops']
            feature_cols = [col for col in numeric_cols if col not in exclude_cols]
            
            # 스케일러가 있으면 스케일러의 feature_names를 사용
            if self.scaler and hasattr(self.scaler, 'feature_names_in_'):
                scaler_features = self.scaler.feature_names_in_.tolist()
                # 스케일러에 있는 특성만 선택
                feature_cols = [col for col in scaler_features if col in data.columns]
                print(f"스케일러 기준 특성 사용: {len(feature_cols)}개")
            
            input_data = data[feature_cols].values
        else:
            input_data = data
        
        # 정규화
        if self.scaler:
            input_data = self.scaler.transform(input_data)
        
        # 시퀀스 길이 확인
        sequence_length = self.model.input_shape[1]
        
        if len(input_data) < sequence_length:
            raise ValueError(f"입력 데이터 길이({len(input_data)})가 시퀀스 길이({sequence_length})보다 작습니다.")
        
        # 마지막 시퀀스 추출
        current_sequence = input_data[-sequence_length:].reshape(1, sequence_length, -1)
        
        predictions = []
        
        for i in range(steps):
            # 예측
            pred = self.model.predict(current_sequence, verbose=0)
            predictions.append(pred[0, 0])
            
            # 다음 입력을 위해 시퀀스 업데이트
            # 예측값을 첫 번째 특성으로 사용하고 나머지는 마지막 값 반복
            next_input = current_sequence[0, -1, :].copy()
            next_input[0] = pred[0, 0]
            
            # 시퀀스를 한 칸씩 이동
            current_sequence = np.concatenate([
                current_sequence[:, 1:, :],
                next_input.reshape(1, 1, -1)
            ], axis=1)
        
        predictions = np.array(predictions)
        
        # 역정규화
        if self.target_scaler:
            # target_scaler가 있으면 사용
            predictions = self.target_scaler.inverse_transform(predictions.reshape(-1, 1)).flatten()
        elif self.scaler:
            # 없으면 일반 scaler의 첫 번째 특성(target) 사용
            predictions = predictions * (self.scaler.data_max_[0] - self.scaler.data_min_[0]) + self.scaler.data_min_[0]
        
        return predictions
    
    def predict_with_confidence(self, data, steps=PREDICTION_STEPS, n_simulations=100):
        """
        불확실성을 포함한 예측 (몬테카를로 드롭아웃)
        
        Args:
            data: 입력 데이터
            steps: 예측할 스텝 수
            n_simulations: 시뮬레이션 반복 횟수
        """
        print(f"신뢰구간을 포함한 예측 중... (시뮬레이션 {n_simulations}회)")
        
        all_predictions = []
        
        for i in range(n_simulations):
            pred = self.predict_next_steps(data, steps)
            all_predictions.append(pred)
            
            if (i + 1) % 20 == 0:
                print(f"진행: {i+1}/{n_simulations}")
        
        all_predictions = np.array(all_predictions)
        
        # 통계 계산
        mean_pred = np.mean(all_predictions, axis=0)
        std_pred = np.std(all_predictions, axis=0)
        lower_bound = np.percentile(all_predictions, 5, axis=0)
        upper_bound = np.percentile(all_predictions, 95, axis=0)
        
        return {
            'mean': mean_pred,
            'std': std_pred,
            'lower_bound': lower_bound,
            'upper_bound': upper_bound,
            'all_predictions': all_predictions
        }
    
    def save_predictions(self, predictions, timestamps=None, output_path=None):
        """예측 결과 저장"""
        if output_path is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = os.path.join(PREDICTIONS_DIR, f'predictions_{timestamp}.csv')
        
        # DataFrame 생성
        if timestamps is None:
            timestamps = pd.date_range(
                start=datetime.now(),
                periods=len(predictions),
                freq='1min'
            )
        
        df = pd.DataFrame({
            'timestamp': timestamps,
            'predicted_traffic': predictions
        })
        
        df.to_csv(output_path, index=False)
        print(f"예측 결과 저장: {output_path}")
        
        return output_path


def main():
    parser = argparse.ArgumentParser(description='네트워크 트래픽 예측')
    parser.add_argument('--model', type=str, required=True,
                        help='학습된 모델 파일 경로')
    parser.add_argument('--data', type=str, required=True,
                        help='입력 데이터 CSV 파일 경로')
    parser.add_argument('--steps', type=int, default=PREDICTION_STEPS,
                        help='예측할 미래 시점 수')
    parser.add_argument('--confidence', action='store_true',
                        help='신뢰구간 포함 예측')
    parser.add_argument('--visualize', action='store_true',
                        help='예측 결과 시각화')
    parser.add_argument('--output', type=str, default=None,
                        help='예측 결과 저장 경로')
    
    args = parser.parse_args()
    
    # 데이터 로드
    print(f"데이터 로드: {args.data}")
    df = pd.read_csv(args.data)
    
    if 'timestamp' in df.columns:
        df['timestamp'] = pd.to_datetime(df['timestamp'])
    
    # 예측기 생성
    forecaster = TrafficForecaster(args.model)
    
    # 예측
    if args.confidence:
        result = forecaster.predict_with_confidence(df, steps=args.steps)
        predictions = result['mean']
        
        print("\n예측 결과 (신뢰구간 포함):")
        for i in range(len(predictions)):
            print(f"  Step {i+1}: {predictions[i]:,.2f} ± {result['std'][i]:,.2f} bytes/sec "
                  f"[{result['lower_bound'][i]:,.2f} - {result['upper_bound'][i]:,.2f}]")
    else:
        predictions = forecaster.predict_next_steps(df, steps=args.steps)
        
        print("\n예측 결과:")
        for i, pred in enumerate(predictions):
            print(f"  Step {i+1}: {pred:,.2f} bytes/sec ({pred/1024/1024:.2f} MB/sec)")
    
    # 예측 결과 저장
    if 'timestamp' in df.columns:
        last_time = df['timestamp'].max()
        interval = df['timestamp'].diff().median()
        future_timestamps = pd.date_range(
            start=last_time + interval,
            periods=len(predictions),
            freq=interval
        )
    else:
        future_timestamps = None
    
    output_path = forecaster.save_predictions(predictions, future_timestamps, args.output)
    
    # 시각화
    if args.visualize:
        print("\n예측 결과 시각화...")
        import matplotlib.pyplot as plt
        
        fig, ax = plt.subplots(figsize=(15, 6))
        
        # 실제 데이터
        if 'total_bytes_per_sec' in df.columns:
            if 'timestamp' in df.columns:
                ax.plot(df['timestamp'], df['total_bytes_per_sec'], 
                       label='Actual', alpha=0.7)
                
                if future_timestamps is not None:
                    ax.plot(future_timestamps, predictions, 
                           label='Predicted', color='red', linestyle='--', alpha=0.7)
                    
                    if args.confidence:
                        ax.fill_between(future_timestamps, 
                                       result['lower_bound'], 
                                       result['upper_bound'],
                                       alpha=0.2, color='red', 
                                       label='90% Confidence Interval')
            else:
                actual_len = len(df)
                ax.plot(range(actual_len), df['total_bytes_per_sec'], 
                       label='Actual', alpha=0.7)
                ax.plot(range(actual_len, actual_len + len(predictions)), 
                       predictions, label='Predicted', 
                       color='red', linestyle='--', alpha=0.7)
        
        ax.set_xlabel('Time')
        ax.set_ylabel('Traffic (bytes/sec)')
        ax.set_title('Network Traffic Prediction')
        ax.legend()
        ax.grid(True, alpha=0.3)
        
        plt.tight_layout()
        
        viz_path = output_path.replace('.csv', '.png')
        plt.savefig(viz_path, dpi=100, bbox_inches='tight')
        print(f"시각화 저장: {viz_path}")
        
        plt.show()
    
    print("\n예측 완료!")


if __name__ == "__main__":
    main()
