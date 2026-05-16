"""
네트워크 트래픽 분석 스크립트
"""
import pandas as pd
import numpy as np
import argparse
import os
from utils.data_processor import TrafficDataProcessor
from utils.visualizer import TrafficVisualizer
from config import PROCESSED_DATA_DIR


class TrafficAnalyzer:
    """트래픽 분석 클래스"""
    
    def __init__(self, data_path):
        """
        Args:
            data_path: 분석할 데이터 파일 경로
        """
        self.data_path = data_path
        self.df = None
        self.load_data()
        
    def load_data(self):
        """데이터 로드"""
        print(f"데이터 로딩: {self.data_path}")
        self.df = pd.read_csv(self.data_path)
        
        if 'timestamp' in self.df.columns:
            self.df['timestamp'] = pd.to_datetime(self.df['timestamp'])
            
        print(f"데이터 shape: {self.df.shape}")
        print(f"컬럼: {list(self.df.columns)}")
        
    def basic_statistics(self):
        """기본 통계 정보 출력"""
        print("\n" + "="*80)
        print("기본 통계 정보")
        print("="*80)
        
        # 트래픽 관련 컬럼
        traffic_cols = ['bytes_sent_per_sec', 'bytes_recv_per_sec', 
                       'total_bytes_per_sec', 'packets_sent_per_sec', 
                       'packets_recv_per_sec']
        
        available_cols = [col for col in traffic_cols if col in self.df.columns]
        
        if available_cols:
            stats = self.df[available_cols].describe()
            print(stats)
        
        # 전체 데이터 기간
        if 'timestamp' in self.df.columns:
            print(f"\n데이터 기간: {self.df['timestamp'].min()} ~ {self.df['timestamp'].max()}")
            duration = self.df['timestamp'].max() - self.df['timestamp'].min()
            print(f"총 기간: {duration}")
        
        # 에러 및 드롭 통계
        if 'errors' in self.df.columns:
            total_errors = self.df['errors'].sum()
            print(f"\n총 에러 수: {total_errors}")
            
        if 'drops' in self.df.columns:
            total_drops = self.df['drops'].sum()
            print(f"총 드롭 수: {total_drops}")
            
    def peak_analysis(self):
        """피크 트래픽 분석"""
        print("\n" + "="*80)
        print("피크 트래픽 분석")
        print("="*80)
        
        if 'total_bytes_per_sec' not in self.df.columns:
            print("트래픽 데이터가 없습니다.")
            return
        
        # 최대/최소 트래픽
        max_traffic = self.df['total_bytes_per_sec'].max()
        min_traffic = self.df['total_bytes_per_sec'].min()
        avg_traffic = self.df['total_bytes_per_sec'].mean()
        median_traffic = self.df['total_bytes_per_sec'].median()
        
        print(f"최대 트래픽: {max_traffic:,.2f} bytes/sec ({max_traffic/1024/1024:.2f} MB/sec)")
        print(f"최소 트래픽: {min_traffic:,.2f} bytes/sec ({min_traffic/1024/1024:.2f} MB/sec)")
        print(f"평균 트래픽: {avg_traffic:,.2f} bytes/sec ({avg_traffic/1024/1024:.2f} MB/sec)")
        print(f"중앙값: {median_traffic:,.2f} bytes/sec ({median_traffic/1024/1024:.2f} MB/sec)")
        
        # 최대 트래픽 발생 시점
        if 'timestamp' in self.df.columns:
            max_idx = self.df['total_bytes_per_sec'].idxmax()
            max_time = self.df.loc[max_idx, 'timestamp']
            print(f"\n최대 트래픽 발생 시각: {max_time}")
        
        # Top 10 피크 시점
        top10 = self.df.nlargest(10, 'total_bytes_per_sec')
        print("\nTop 10 피크 트래픽:")
        for idx, row in top10.iterrows():
            traffic = row['total_bytes_per_sec']
            if 'timestamp' in row:
                print(f"  {row['timestamp']}: {traffic:,.2f} bytes/sec")
            else:
                print(f"  Index {idx}: {traffic:,.2f} bytes/sec")
                
    def pattern_analysis(self):
        """트래픽 패턴 분석"""
        print("\n" + "="*80)
        print("트래픽 패턴 분석")
        print("="*80)
        
        if 'total_bytes_per_sec' not in self.df.columns:
            print("트래픽 데이터가 없습니다.")
            return
        
        # 시간대별 평균 트래픽
        if 'hour' in self.df.columns:
            hourly_avg = self.df.groupby('hour')['total_bytes_per_sec'].agg(['mean', 'std', 'max'])
            print("\n시간대별 트래픽 (bytes/sec):")
            print(hourly_avg)
            
            # 피크 시간대
            peak_hour = hourly_avg['mean'].idxmax()
            print(f"\n가장 트래픽이 많은 시간대: {peak_hour}시")
        
        # 요일별 평균 트래픽
        if 'day_of_week' in self.df.columns:
            days = ['월요일', '화요일', '수요일', '목요일', '금요일', '토요일', '일요일']
            daily_avg = self.df.groupby('day_of_week')['total_bytes_per_sec'].agg(['mean', 'std', 'max'])
            
            print("\n요일별 트래픽 (bytes/sec):")
            for day_idx, row in daily_avg.iterrows():
                if day_idx < len(days):
                    print(f"  {days[day_idx]}: 평균 {row['mean']:,.2f}, 최대 {row['max']:,.2f}")
                    
    def anomaly_analysis(self):
        """이상치 분석"""
        print("\n" + "="*80)
        print("이상치 분석")
        print("="*80)
        
        if 'is_anomaly' in self.df.columns:
            anomaly_count = self.df['is_anomaly'].sum()
            anomaly_ratio = anomaly_count / len(self.df) * 100
            
            print(f"총 이상치 수: {anomaly_count} ({anomaly_ratio:.2f}%)")
            
            if anomaly_count > 0:
                anomalies = self.df[self.df['is_anomaly']]
                
                if 'total_bytes_per_sec' in anomalies.columns:
                    print(f"이상치 평균 트래픽: {anomalies['total_bytes_per_sec'].mean():,.2f} bytes/sec")
                    print(f"이상치 최대 트래픽: {anomalies['total_bytes_per_sec'].max():,.2f} bytes/sec")
                
                # 이상치 발생 시각 (최대 10개)
                if 'timestamp' in anomalies.columns:
                    print("\n이상치 발생 시각 (최대 10개):")
                    for idx, row in anomalies.head(10).iterrows():
                        traffic = row.get('total_bytes_per_sec', 0)
                        print(f"  {row['timestamp']}: {traffic:,.2f} bytes/sec")
        else:
            print("이상치 정보가 없습니다. 데이터 전처리를 먼저 수행하세요.")
            
    def generate_report(self, output_path=None):
        """종합 리포트 생성"""
        print("\n" + "="*80)
        print("네트워크 트래픽 분석 리포트")
        print("="*80)
        
        self.basic_statistics()
        self.peak_analysis()
        self.pattern_analysis()
        self.anomaly_analysis()
        
        if output_path:
            # 리포트를 파일로 저장하는 기능 추가 가능
            print(f"\n리포트 저장: {output_path}")


def main():
    parser = argparse.ArgumentParser(description='네트워크 트래픽 데이터 분석')
    parser.add_argument('--input', type=str, required=True,
                        help='분석할 CSV 파일 경로')
    parser.add_argument('--visualize', action='store_true',
                        help='시각화 생성')
    parser.add_argument('--output-dir', type=str, default='.',
                        help='출력 디렉토리 (시각화용)')
    
    args = parser.parse_args()
    
    # 분석 수행
    analyzer = TrafficAnalyzer(args.input)
    analyzer.generate_report()
    
    # 시각화
    if args.visualize:
        print("\n시각화 생성 중...")
        viz = TrafficVisualizer()
        
        viz.plot_traffic_timeline(analyzer.df,
                                 save_path=os.path.join(args.output_dir, 'traffic_timeline.png'))
        
        if 'is_anomaly' in analyzer.df.columns:
            viz.plot_anomalies(analyzer.df,
                             save_path=os.path.join(args.output_dir, 'anomalies.png'))
        
        viz.plot_distribution(analyzer.df,
                            save_path=os.path.join(args.output_dir, 'distribution.png'))


if __name__ == "__main__":
    main()
