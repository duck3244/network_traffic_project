"""
네트워크 트래픽 데이터 수집 모듈
"""
import psutil
import time
import pandas as pd
import argparse
from datetime import datetime
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import RAW_DATA_DIR, COLLECTION_INTERVAL, COLLECTION_DURATION


class NetworkTrafficCollector:
    """네트워크 트래픽 데이터 수집기"""
    
    def __init__(self, interface=None, interval=1):
        """
        Args:
            interface: 모니터링할 네트워크 인터페이스 (None이면 전체)
            interval: 데이터 수집 간격 (초)
        """
        self.interface = interface
        self.interval = interval
        self.data = []
        
    def get_network_stats(self):
        """현재 네트워크 통계 수집"""
        net_io = psutil.net_io_counters(pernic=True if self.interface else False)
        
        if self.interface and self.interface in net_io:
            stats = net_io[self.interface]
        elif not self.interface:
            stats = psutil.net_io_counters()
        else:
            raise ValueError(f"Interface {self.interface} not found")
            
        return {
            'bytes_sent': stats.bytes_sent,
            'bytes_recv': stats.bytes_recv,
            'packets_sent': stats.packets_sent,
            'packets_recv': stats.packets_recv,
            'errin': stats.errin,
            'errout': stats.errout,
            'dropin': stats.dropin,
            'dropout': stats.dropout
        }
    
    def collect(self, duration=300):
        """
        지정된 시간 동안 트래픽 데이터 수집
        
        Args:
            duration: 수집 시간 (초)
        """
        print(f"네트워크 트래픽 수집 시작 (간격: {self.interval}초, 지속시간: {duration}초)")
        
        start_time = time.time()
        last_stats = self.get_network_stats()
        
        while time.time() - start_time < duration:
            time.sleep(self.interval)
            
            current_time = datetime.now()
            current_stats = self.get_network_stats()
            
            # 델타 계산 (초당 전송량)
            delta = {
                'timestamp': current_time,
                'bytes_sent_per_sec': (current_stats['bytes_sent'] - last_stats['bytes_sent']) / self.interval,
                'bytes_recv_per_sec': (current_stats['bytes_recv'] - last_stats['bytes_recv']) / self.interval,
                'packets_sent_per_sec': (current_stats['packets_sent'] - last_stats['packets_sent']) / self.interval,
                'packets_recv_per_sec': (current_stats['packets_recv'] - last_stats['packets_recv']) / self.interval,
                'total_bytes_per_sec': ((current_stats['bytes_sent'] - last_stats['bytes_sent']) + 
                                       (current_stats['bytes_recv'] - last_stats['bytes_recv'])) / self.interval,
                'errors': current_stats['errin'] + current_stats['errout'],
                'drops': current_stats['dropin'] + current_stats['dropout']
            }
            
            self.data.append(delta)
            last_stats = current_stats
            
            # 진행 상황 출력
            elapsed = int(time.time() - start_time)
            if elapsed % 10 == 0:
                print(f"수집 중... {elapsed}/{duration}초")
        
        print(f"데이터 수집 완료! 총 {len(self.data)}개 데이터 포인트")
        
    def save_data(self, filename=None):
        """수집된 데이터를 CSV 파일로 저장"""
        if not self.data:
            print("저장할 데이터가 없습니다.")
            return
        
        df = pd.DataFrame(self.data)
        
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"traffic_data_{timestamp}.csv"
        
        filepath = os.path.join(RAW_DATA_DIR, filename)
        df.to_csv(filepath, index=False)
        print(f"데이터 저장 완료: {filepath}")
        
        return filepath
    
    def get_dataframe(self):
        """수집된 데이터를 DataFrame으로 반환"""
        return pd.DataFrame(self.data)


def main():
    parser = argparse.ArgumentParser(description='네트워크 트래픽 데이터 수집')
    parser.add_argument('--interface', type=str, default=None, 
                        help='모니터링할 네트워크 인터페이스')
    parser.add_argument('--interval', type=int, default=COLLECTION_INTERVAL,
                        help='데이터 수집 간격 (초)')
    parser.add_argument('--duration', type=int, default=COLLECTION_DURATION,
                        help='데이터 수집 지속시간 (초)')
    parser.add_argument('--output', type=str, default=None,
                        help='출력 파일명')
    
    args = parser.parse_args()
    
    # 데이터 수집
    collector = NetworkTrafficCollector(interface=args.interface, interval=args.interval)
    collector.collect(duration=args.duration)
    collector.save_data(filename=args.output)


if __name__ == "__main__":
    main()
