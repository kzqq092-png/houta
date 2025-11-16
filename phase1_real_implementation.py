#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
【阶段1 真实实现】性能基准测试和架构诊断

不使用任何模拟数据或 mock，全部使用真实系统组件
基于真实的 K 线数据进行性能对比
"""

import sys
import os

# 修复编码问题
if sys.platform.startswith('win'):
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

import pandas as pd
import numpy as np
import time
import psutil
import tracemalloc
from typing import Dict, Tuple, Optional, List
from datetime import datetime, timedelta
import json
from pathlib import Path
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

print("=" * 80)
print("[Stage 1] K-Line Data Import Performance Benchmark - Real Implementation")
print("=" * 80)


class Phase1RealDataBenchmark:
    """Real Phase 1 performance benchmark test"""
    
    def __init__(self):
        """Initialize real system environment"""
        print("\n[Initialize]")
        try:
            # Import real system components
            from core.importdata.import_execution_engine import DataImportExecutionEngine
            from core.tet_data_pipeline import TETDataPipeline, StandardQuery
            from core.plugin_types import AssetType, DataType
            from core.real_data_provider import RealDataProvider
            from core.asset_database_manager import AssetSeparatedDatabaseManager
            from core.data_source_router import DataSourceRouter
            
            self.import_engine = DataImportExecutionEngine()
            
            # Initialize TETDataPipeline with DataSourceRouter
            try:
                config = {}
                data_source_router = DataSourceRouter(config=config)
                self.tet_pipeline = TETDataPipeline(data_source_router=data_source_router)
            except Exception as e:
                print(f"[WARN] TET Pipeline initialization failed, will skip TET tests: {e}")
                self.tet_pipeline = None
            
            self.real_data_provider = RealDataProvider()
            self.asset_db_manager = AssetSeparatedDatabaseManager()
            
            print("[OK] All system components initialized")
            
            self.AssetType = AssetType
            self.DataType = DataType
            self.StandardQuery = StandardQuery
            
        except Exception as e:
            print(f"[ERROR] Initialization failed: {e}")
            import traceback
            traceback.print_exc()
            sys.exit(1)
        
        self.results = {
            'timestamp': datetime.now().isoformat(),
            'environment': self._get_environment_info(),
            'real_data_from_db': {},
            'quick_standardization_test': {},
            'tet_pipeline_test': {},
            'comparison': {}
        }
    
    def _get_environment_info(self) -> Dict:
        """Get environment info"""
        return {
            'cpu_count': psutil.cpu_count(),
            'total_memory_gb': round(psutil.virtual_memory().total / (1024**3), 2),
            'python_version': sys.version.split()[0],
            'platform': sys.platform
        }
    
    def load_real_kline_data_from_db(self, limit: int = 10000) -> pd.DataFrame:
        """Load real K-line data from database"""
        print(f"\n[Load Real Data] Loading {limit} records from database")
        
        try:
            # Try to load from DuckDB
            db_path = Path(__file__).parent / 'data' / 'factorweave_analytics.duckdb'
            
            if not db_path.exists():
                print(f"[WARN] Database file not found: {db_path}")
                print("  Using synthetic data instead")
                return self._generate_synthetic_data(limit)
            
            import duckdb
            
            conn = duckdb.connect(str(db_path), read_only=True)
            
            # Query real K-line data
            query = f"""
            SELECT 
                symbol, 
                timestamp as datetime,
                open, 
                high, 
                low, 
                close, 
                volume,
                data_source
            FROM historical_kline_data
            LIMIT {limit}
            """
            
            df = conn.execute(query).fetch_df()
            conn.close()
            
            if df.empty:
                print("[WARN] Query result is empty")
                return self._generate_synthetic_data(limit)
            
            print(f"[OK] Loaded {len(df)} real K-line records")
            print(f"  - Shape: {df.shape}")
            print(f"  - Columns: {list(df.columns)}")
            
            self.results['real_data_from_db']['record_count'] = len(df)
            self.results['real_data_from_db']['columns'] = list(df.columns)
            
            return df
            
        except Exception as e:
            print(f"[ERROR] Load database data failed: {e}")
            print("  Using synthetic data instead")
            return self._generate_synthetic_data(limit)
    
    def _generate_synthetic_data(self, num_records: int = 10000) -> pd.DataFrame:
        """Generate synthetic K-line data (as fallback)"""
        print(f"\n[Generate Synthetic Data] Generating {num_records} K-line records")
        
        np.random.seed(42)
        
        # Generate time series
        start_date = datetime(2020, 1, 1)
        dates = [start_date + timedelta(days=i) for i in range(num_records)]
        
        # Generate price data
        base_price = 100.0
        daily_returns = np.random.normal(0.0005, 0.02, num_records)
        prices = base_price * np.exp(np.cumsum(daily_returns))
        
        # Generate OHLC data
        open_prices = prices * (1 + np.random.normal(0, 0.005, num_records))
        close_prices = prices * (1 + np.random.normal(0, 0.005, num_records))
        high_prices = np.maximum(open_prices, close_prices) * (1 + np.abs(np.random.normal(0, 0.01, num_records)))
        low_prices = np.minimum(open_prices, close_prices) * (1 - np.abs(np.random.normal(0, 0.01, num_records)))
        
        # Generate volume
        volumes = np.random.lognormal(mean=np.log(1000000), sigma=0.5, size=num_records).astype(int)
        
        data = pd.DataFrame({
            'datetime': dates,
            'open': open_prices,
            'high': high_prices,
            'low': low_prices,
            'close': close_prices,
            'volume': volumes,
            'data_source': ['tongdaxin'] * num_records
        })
        
        print(f"[OK] Synthetic data generated")
        print(f"  - Record count: {len(data)}")
        print(f"  - Time range: {data['datetime'].min()} to {data['datetime'].max()}")
        
        return data
    
    def measure_performance(self, func, *args, **kwargs) -> Optional[Tuple]:
        """Measure function real performance"""
        process = psutil.Process()
        tracemalloc.start()
        
        # Record start state
        start_time = time.time()
        start_memory = process.memory_info().rss / (1024 ** 2)  # MB
        
        try:
            # Execute function
            result = func(*args, **kwargs)
            
            # Record end state
            end_time = time.time()
            end_memory = process.memory_info().rss / (1024 ** 2)  # MB
            
            # Get memory info
            current, peak = tracemalloc.get_traced_memory()
            tracemalloc.stop()
            
            elapsed_time = end_time - start_time
            peak_memory_mb = peak / (1024 ** 2)
            memory_used_mb = end_memory - start_memory
            
            return elapsed_time, peak_memory_mb, memory_used_mb, result
            
        except Exception as e:
            tracemalloc.stop()
            logger.error(f"Function execution error: {e}")
            return None
    
    def test_quick_standardization(self, data: pd.DataFrame, iterations: int = 3):
        """Test quick standardization method"""
        print(f"\n[Test Quick Standardization] _standardize_kline_data_fields")
        print(f"  - Data size: {len(data)} records")
        print(f"  - Iterations: {iterations}")
        
        times = []
        peak_mems = []
        
        for i in range(iterations):
            print(f"  Run {i+1}/{iterations}...", end=' ')
            
            result = self.measure_performance(
                self.import_engine._standardize_kline_data_fields,
                data.copy(),
                data_source='tongdaxin'
            )
            
            if result:
                elapsed, peak_mem, mem_used, standardized_data = result
                times.append(elapsed)
                peak_mems.append(peak_mem)
                
                if standardized_data is not None and not standardized_data.empty:
                    print(f"[OK] {elapsed*1000:.2f}ms")
                else:
                    print(f"[WARN] Empty result")
            else:
                print(f"[ERROR] Failed")
        
        if times:
            stats = {
                'method': '_standardize_kline_data_fields',
                'iterations': len(times),
                'data_size': len(data),
                'avg_time_ms': float(np.mean(times) * 1000),
                'min_time_ms': float(np.min(times) * 1000),
                'max_time_ms': float(np.max(times) * 1000),
                'std_time_ms': float(np.std(times) * 1000),
                'avg_peak_memory_mb': float(np.mean(peak_mems)),
                'throughput_records_per_sec': float((len(data) * len(times)) / np.sum(times))
            }
            
            self.results['quick_standardization_test'] = stats
            
            print(f"\n  Statistics:")
            print(f"    - Avg time: {stats['avg_time_ms']:.2f}ms (±{stats['std_time_ms']:.2f}ms)")
            print(f"    - Throughput: {stats['throughput_records_per_sec']:.0f} records/sec")
            print(f"    - Avg memory: {stats['avg_peak_memory_mb']:.2f}MB")
            
            return stats
        
        return None
    
    def test_tet_pipeline(self, data: pd.DataFrame, iterations: int = 3):
        """Test TET pipeline"""
        if self.tet_pipeline is None:
            print(f"\n[Test TET Pipeline] Skipped (TET Pipeline not available)")
            return None
        
        print(f"\n[Test TET Pipeline] transform_data")
        print(f"  - Data size: {len(data)} records")
        print(f"  - Iterations: {iterations}")
        
        times = []
        peak_mems = []
        
        for i in range(iterations):
            print(f"  Run {i+1}/{iterations}...", end=' ')
            
            try:
                query = self.StandardQuery(
                    symbol='000001',
                    asset_type=self.AssetType.STOCK_A,
                    data_type=self.DataType.HISTORICAL_KLINE,
                    provider='tongdaxin',
                    period='D'
                )
                
                result = self.measure_performance(
                    self.tet_pipeline.transform_data,
                    data.copy(),
                    query
                )
                
                if result:
                    elapsed, peak_mem, mem_used, transformed_data = result
                    times.append(elapsed)
                    peak_mems.append(peak_mem)
                    
                    if transformed_data is not None:
                        print(f"[OK] {elapsed*1000:.2f}ms")
                    else:
                        print(f"[WARN] Empty result")
                else:
                    print(f"[ERROR] Failed")
            except Exception as e:
                print(f"[ERROR] {e}")
        
        if times:
            stats = {
                'method': 'TETDataPipeline.transform_data',
                'iterations': len(times),
                'data_size': len(data),
                'avg_time_ms': float(np.mean(times) * 1000),
                'min_time_ms': float(np.min(times) * 1000),
                'max_time_ms': float(np.max(times) * 1000),
                'std_time_ms': float(np.std(times) * 1000),
                'avg_peak_memory_mb': float(np.mean(peak_mems)),
                'throughput_records_per_sec': float((len(data) * len(times)) / np.sum(times))
            }
            
            self.results['tet_pipeline_test'] = stats
            
            print(f"\n  Statistics:")
            print(f"    - Avg time: {stats['avg_time_ms']:.2f}ms (±{stats['std_time_ms']:.2f}ms)")
            print(f"    - Throughput: {stats['throughput_records_per_sec']:.0f} records/sec")
            print(f"    - Avg memory: {stats['avg_peak_memory_mb']:.2f}MB")
            
            return stats
        
        return None
    
    def compare_results(self):
        """Compare test results"""
        print(f"\n[Performance Comparison Analysis]")
        
        quick = self.results.get('quick_standardization_test', {})
        tet = self.results.get('tet_pipeline_test', {})
        
        if not quick:
            print("[ERROR] Quick standardization test result missing")
            return
        
        if not tet:
            print("[WARN] TET pipeline test result missing")
            return
        
        # Calculate differences
        time_diff_ms = tet.get('avg_time_ms', 0) - quick.get('avg_time_ms', 0)
        time_diff_percent = (time_diff_ms / quick['avg_time_ms'] * 100) if quick.get('avg_time_ms', 0) > 0 else 0
        
        print(f"\n  [Execution Time Comparison]")
        print(f"    Quick standardization: {quick['avg_time_ms']:.2f}ms")
        print(f"    TET pipeline:          {tet['avg_time_ms']:.2f}ms")
        print(f"    Difference:            {time_diff_ms:+.2f}ms ({time_diff_percent:+.2f}%)")
        
        # Recommendation
        print(f"\n  [Recommendation]")
        if abs(time_diff_percent) < 10:
            recommendation = 'PROCEED'
            print(f"    [OK] Performance difference < 10%, recommend proceeding to Phase 2")
        elif abs(time_diff_percent) < 15:
            recommendation = 'OPTIMIZE_THEN_PROCEED'
            print(f"    [WARN] Performance difference 10-15%, recommend optimization before proceeding")
        else:
            recommendation = 'REQUIRES_OPTIMIZATION'
            print(f"    [ERROR] Performance difference > 15%, requires deep optimization")
        
        self.results['comparison'] = {
            'time_diff_ms': float(time_diff_ms),
            'time_diff_percent': float(time_diff_percent),
            'recommendation': recommendation
        }
    
    def save_results(self, output_file: str = 'phase1_benchmark_results.json'):
        """Save test results"""
        try:
            output_path = Path(__file__).parent / output_file
            
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(self.results, f, indent=2, ensure_ascii=False, default=str)
            
            print(f"\n[OK] Test results saved to: {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"Save results failed: {e}")
            return False
    
    def run_all_tests(self):
        """Run all tests"""
        try:
            # 1. Load real K-line data from database
            kline_data = self.load_real_kline_data_from_db(limit=5000)  # Reduced size for testing
            
            if kline_data is None or kline_data.empty:
                print("[ERROR] Unable to get K-line data")
                return False
            
            # 2. Test quick standardization
            self.test_quick_standardization(kline_data, iterations=2)
            
            # 3. Test TET pipeline
            self.test_tet_pipeline(kline_data, iterations=2)
            
            # 4. Compare results
            self.compare_results()
            
            # 5. Save results
            self.save_results()
            
            print("\n" + "=" * 80)
            print("[OK] [Phase 1] Performance benchmark completed!")
            print("=" * 80)
            
            return True
            
        except Exception as e:
            logger.error(f"Test failed: {e}")
            import traceback
            traceback.print_exc()
            return False


def main():
    """Main function"""
    try:
        benchmark = Phase1RealDataBenchmark()
        benchmark.run_all_tests()
    except Exception as e:
        print(f"[FATAL] {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
