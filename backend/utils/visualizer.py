"""
네트워크 트래픽 시각화 모듈
"""
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
import numpy as np
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import FIGURE_SIZE, DPI

# 스타일 설정
sns.set_style("whitegrid")
plt.rcParams['figure.figsize'] = FIGURE_SIZE
plt.rcParams['figure.dpi'] = DPI


class TrafficVisualizer:
    """트래픽 데이터 시각화 클래스"""
    
    def __init__(self, figsize=FIGURE_SIZE, dpi=DPI):
        """
        Args:
            figsize: 그래프 크기
            dpi: 해상도
        """
        self.figsize = figsize
        self.dpi = dpi
        
    def plot_traffic_timeline(self, df, save_path=None):
        """트래픽 시계열 그래프"""
        fig, axes = plt.subplots(3, 1, figsize=(self.figsize[0], self.figsize[1]*1.5))
        
        if 'timestamp' in df.columns:
            x = df['timestamp']
        else:
            x = range(len(df))
        
        # 전송/수신 바이트
        if 'bytes_sent_per_sec' in df.columns and 'bytes_recv_per_sec' in df.columns:
            axes[0].plot(x, df['bytes_sent_per_sec'], label='Sent', alpha=0.7)
            axes[0].plot(x, df['bytes_recv_per_sec'], label='Received', alpha=0.7)
            axes[0].set_ylabel('Bytes/sec')
            axes[0].set_title('Network Traffic - Bytes per Second')
            axes[0].legend()
            axes[0].grid(True, alpha=0.3)
        
        # 전체 트래픽
        if 'total_bytes_per_sec' in df.columns:
            axes[1].plot(x, df['total_bytes_per_sec'], color='blue', alpha=0.7)
            axes[1].set_ylabel('Total Bytes/sec')
            axes[1].set_title('Total Network Traffic')
            axes[1].grid(True, alpha=0.3)
            
            # 이동평균이 있다면 함께 표시
            ma_col = [col for col in df.columns if 'total_bytes_per_sec_ma' in col]
            if ma_col:
                axes[1].plot(x, df[ma_col[0]], color='red', 
                           label=f'Moving Average', linestyle='--')
                axes[1].legend()
        
        # 패킷 수
        if 'packets_sent_per_sec' in df.columns and 'packets_recv_per_sec' in df.columns:
            axes[2].plot(x, df['packets_sent_per_sec'], label='Sent', alpha=0.7)
            axes[2].plot(x, df['packets_recv_per_sec'], label='Received', alpha=0.7)
            axes[2].set_ylabel('Packets/sec')
            axes[2].set_title('Network Traffic - Packets per Second')
            axes[2].set_xlabel('Time' if 'timestamp' in df.columns else 'Sample')
            axes[2].legend()
            axes[2].grid(True, alpha=0.3)
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=self.dpi, bbox_inches='tight')
            print(f"그래프 저장: {save_path}")
        
        plt.show()
        
    def plot_anomalies(self, df, save_path=None):
        """이상치 표시"""
        if 'is_anomaly' not in df.columns or 'total_bytes_per_sec' not in df.columns:
            print("이상치 정보가 없습니다.")
            return
        
        fig, ax = plt.subplots(figsize=self.figsize)
        
        if 'timestamp' in df.columns:
            x = df['timestamp']
        else:
            x = range(len(df))
        
        # 정상 데이터
        normal = df[~df['is_anomaly']]
        ax.scatter(x[~df['is_anomaly']], normal['total_bytes_per_sec'], 
                  c='blue', alpha=0.5, s=20, label='Normal')
        
        # 이상치
        anomaly = df[df['is_anomaly']]
        if len(anomaly) > 0:
            ax.scatter(x[df['is_anomaly']], anomaly['total_bytes_per_sec'], 
                      c='red', alpha=0.8, s=50, marker='x', label='Anomaly')
        
        ax.set_xlabel('Time' if 'timestamp' in df.columns else 'Sample')
        ax.set_ylabel('Total Bytes/sec')
        ax.set_title(f'Traffic Anomaly Detection ({len(anomaly)} anomalies detected)')
        ax.legend()
        ax.grid(True, alpha=0.3)
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=self.dpi, bbox_inches='tight')
            print(f"그래프 저장: {save_path}")
        
        plt.show()
        
    def plot_distribution(self, df, save_path=None):
        """트래픽 분포 시각화"""
        fig, axes = plt.subplots(2, 2, figsize=(self.figsize[0], self.figsize[1]*1.2))
        
        # 전체 트래픽 히스토그램
        if 'total_bytes_per_sec' in df.columns:
            axes[0, 0].hist(df['total_bytes_per_sec'], bins=50, alpha=0.7, color='blue')
            axes[0, 0].set_xlabel('Total Bytes/sec')
            axes[0, 0].set_ylabel('Frequency')
            axes[0, 0].set_title('Traffic Distribution')
            axes[0, 0].grid(True, alpha=0.3)
        
        # Box plot
        if 'total_bytes_per_sec' in df.columns:
            axes[0, 1].boxplot(df['total_bytes_per_sec'])
            axes[0, 1].set_ylabel('Total Bytes/sec')
            axes[0, 1].set_title('Traffic Box Plot')
            axes[0, 1].grid(True, alpha=0.3)
        
        # 시간대별 평균 트래픽
        if 'hour' in df.columns and 'total_bytes_per_sec' in df.columns:
            hourly_avg = df.groupby('hour')['total_bytes_per_sec'].mean()
            axes[1, 0].bar(hourly_avg.index, hourly_avg.values, alpha=0.7, color='green')
            axes[1, 0].set_xlabel('Hour of Day')
            axes[1, 0].set_ylabel('Avg Bytes/sec')
            axes[1, 0].set_title('Average Traffic by Hour')
            axes[1, 0].grid(True, alpha=0.3)
        
        # 요일별 평균 트래픽
        if 'day_of_week' in df.columns and 'total_bytes_per_sec' in df.columns:
            daily_avg = df.groupby('day_of_week')['total_bytes_per_sec'].mean()
            days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
            axes[1, 1].bar(range(len(daily_avg)), daily_avg.values, alpha=0.7, color='orange')
            axes[1, 1].set_xticks(range(len(daily_avg)))
            axes[1, 1].set_xticklabels([days[i] for i in daily_avg.index])
            axes[1, 1].set_ylabel('Avg Bytes/sec')
            axes[1, 1].set_title('Average Traffic by Day of Week')
            axes[1, 1].grid(True, alpha=0.3)
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=self.dpi, bbox_inches='tight')
            print(f"그래프 저장: {save_path}")
        
        plt.show()
        
    def plot_predictions(self, actual, predicted, save_path=None):
        """예측 결과 시각화"""
        fig, axes = plt.subplots(2, 1, figsize=(self.figsize[0], self.figsize[1]*1.2))
        
        # 실제 vs 예측
        axes[0].plot(actual, label='Actual', alpha=0.7)
        axes[0].plot(predicted, label='Predicted', alpha=0.7)
        axes[0].set_ylabel('Traffic (Bytes/sec)')
        axes[0].set_title('Actual vs Predicted Traffic')
        axes[0].legend()
        axes[0].grid(True, alpha=0.3)
        
        # 오차
        error = actual - predicted
        axes[1].plot(error, color='red', alpha=0.7)
        axes[1].axhline(y=0, color='black', linestyle='--', alpha=0.3)
        axes[1].set_xlabel('Time Step')
        axes[1].set_ylabel('Prediction Error')
        axes[1].set_title('Prediction Error')
        axes[1].grid(True, alpha=0.3)
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=self.dpi, bbox_inches='tight')
            print(f"그래프 저장: {save_path}")
        
        plt.show()
        
    def plot_correlation_matrix(self, df, save_path=None):
        """특성 간 상관관계 히트맵"""
        # 숫자형 컬럼만 선택
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        
        if len(numeric_cols) < 2:
            print("상관관계를 계산할 숫자형 컬럼이 충분하지 않습니다.")
            return
        
        corr_matrix = df[numeric_cols].corr()
        
        plt.figure(figsize=(12, 10))
        sns.heatmap(corr_matrix, annot=True, fmt='.2f', cmap='coolwarm', 
                   center=0, square=True, linewidths=1)
        plt.title('Feature Correlation Matrix')
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=self.dpi, bbox_inches='tight')
            print(f"그래프 저장: {save_path}")
        
        plt.show()


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='트래픽 데이터 시각화')
    parser.add_argument('--input', type=str, required=True,
                        help='입력 CSV 파일 경로')
    parser.add_argument('--output-dir', type=str, default='.',
                        help='출력 디렉토리')
    
    args = parser.parse_args()
    
    # 데이터 로드
    df = pd.read_csv(args.input)
    if 'timestamp' in df.columns:
        df['timestamp'] = pd.to_datetime(df['timestamp'])
    
    # 시각화
    viz = TrafficVisualizer()
    
    print("트래픽 시계열 그래프 생성...")
    viz.plot_traffic_timeline(df, 
                             save_path=os.path.join(args.output_dir, 'traffic_timeline.png'))
    
    if 'is_anomaly' in df.columns:
        print("이상치 그래프 생성...")
        viz.plot_anomalies(df,
                          save_path=os.path.join(args.output_dir, 'anomalies.png'))
    
    print("분포 그래프 생성...")
    viz.plot_distribution(df,
                         save_path=os.path.join(args.output_dir, 'distribution.png'))
    
    print("상관관계 히트맵 생성...")
    viz.plot_correlation_matrix(df,
                               save_path=os.path.join(args.output_dir, 'correlation.png'))


if __name__ == "__main__":
    main()
