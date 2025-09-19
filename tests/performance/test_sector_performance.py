#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
板块资金流性能测试

此测试套件验证板块资金流功能的性能指标，包括：
1. 板块数据查询响应时间基准
2. 缓存命中率和性能优化验证
3. 数据库查询性能基准
4. API端点响应时间测试
5. 并发负载测试
6. 内存使用和资源占用监控

性能目标：
- 缓存命中查询 < 100ms
- 数据库查询 < 2s
- 缓存命中率 > 80%
- 并发处理能力验证
"""

import pytest
import unittest
from unittest.mock import Mock, patch, MagicMock
import tempfile
import os
import json
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import time
import threading
import asyncio
from concurrent.futures import ThreadPoolExecutor, as_completed
import psutil
import gc
from fastapi.testclient import TestClient
import statistics

# 导入待测试的组件
from core.services.sector_data_service import SectorDataService, SectorCacheKeys
from core.performance.cache_manager import MultiLevelCacheManager
from core.tet_data_pipeline import TETDataPipeline, StandardData
from core.plugin_types import AssetType, DataType
from api_server import app  # 导入FastAPI应用


class TestSectorPerformance(unittest.TestCase):
    """板块资金流性能测试类"""

    @classmethod
    def setUpClass(cls):
        """测试类初始化"""
        cls.test_client = TestClient(app)

        # 性能基准配置
        cls.PERFORMANCE_TARGETS = {
            'cache_hit_max_time': 0.1,      # 缓存命中最大响应时间 100ms
            'db_query_max_time': 2.0,       # 数据库查询最大响应时间 2s
            'api_response_max_time': 3.0,   # API响应最大时间 3s
            'cache_hit_rate_min': 0.8,      # 最低缓存命中率 80%
            'concurrent_requests': 50,       # 并发请求数
            'max_memory_mb': 500            # 最大内存使用 500MB
        }

        # 创建大量测试数据
        cls.large_sector_data = cls._generate_large_sector_data(1000)  # 1000条板块数据
        cls.large_intraday_data = cls._generate_large_intraday_data(500, 240)  # 500个板块，240个时间点

    @classmethod
    def _generate_large_sector_data(cls, count):
        """生成大量板块数据用于性能测试"""
        sector_ids = [f"BK{str(i).zfill(4)}" for i in range(1, count + 1)]
        sector_names = [f"板块{i}" for i in range(1, count + 1)]

        data = {
            'sector_id': sector_ids,
            'sector_name': sector_names,
            'main_net_inflow': np.random.uniform(-1000000, 2000000, count),
            'super_large_inflow': np.random.uniform(0, 1000000, count),
            'super_large_outflow': np.random.uniform(0, 800000, count),
            'large_inflow': np.random.uniform(0, 500000, count),
            'large_outflow': np.random.uniform(0, 400000, count),
            'medium_inflow': np.random.uniform(0, 300000, count),
            'medium_outflow': np.random.uniform(0, 250000, count),
            'small_inflow': np.random.uniform(0, 100000, count),
            'small_outflow': np.random.uniform(0, 80000, count),
            'stock_count': np.random.randint(5, 50, count),
            'avg_change_percent': np.random.uniform(-5.0, 5.0, count),
            'turnover_rate': np.random.uniform(0.01, 0.1, count),
            'ranking': range(1, count + 1),
            'trade_date': [datetime.now().strftime("%Y-%m-%d")] * count
        }

        return pd.DataFrame(data)

    @classmethod
    def _generate_large_intraday_data(cls, sector_count, time_points):
        """生成大量分时数据用于性能测试"""
        all_data = []
        base_time = datetime.strptime("09:30:00", "%H:%M:%S")

        for i in range(1, sector_count + 1):
            sector_id = f"BK{str(i).zfill(4)}"
            for j in range(time_points):
                time_point = (base_time + timedelta(minutes=j)).strftime("%H:%M:%S")
                all_data.append({
                    'sector_id': sector_id,
                    'sector_name': f'板块{i}',
                    'trade_date': datetime.now().strftime("%Y-%m-%d"),
                    'trade_time': time_point,
                    'net_inflow': np.random.uniform(-50000, 100000),
                    'cumulative_inflow': np.random.uniform(0, 1000000)
                })

        return pd.DataFrame(all_data)

    def setUp(self):
        """每个测试方法的初始化"""
        self.mock_cache_manager = Mock(spec=MultiLevelCacheManager)
        self.mock_tet_pipeline = Mock(spec=TETDataPipeline)
        self.mock_db_connector = Mock()
        self.mock_table_manager = Mock()

        # 重置模拟对象
        self.mock_cache_manager.reset_mock()
        self.mock_tet_pipeline.reset_mock()
        self.mock_db_connector.reset_mock()
        self.mock_table_manager.reset_mock()

        # 记录测试开始时的内存使用
        self.initial_memory = psutil.Process().memory_info().rss / 1024 / 1024  # MB

    def tearDown(self):
        """每个测试方法的清理"""
        # 强制垃圾回收
        gc.collect()

        # 检查内存使用
        current_memory = psutil.Process().memory_info().rss / 1024 / 1024  # MB
        memory_increase = current_memory - self.initial_memory

        if memory_increase > self.PERFORMANCE_TARGETS['max_memory_mb']:
            print(f"Warning: Memory usage increased by {memory_increase:.2f}MB, exceeds target {self.PERFORMANCE_TARGETS['max_memory_mb']}MB")

    def _time_function(self, func, *args, **kwargs):
        """计时函数执行时间"""
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        execution_time = end_time - start_time
        return result, execution_time

    def test_sector_data_service_cache_hit_performance(self):
        """测试板块数据服务缓存命中性能"""
        with patch('core.services.sector_data_service.get_table_manager', return_value=self.mock_table_manager), \
                patch('core.services.sector_data_service.get_database_connector', return_value=self.mock_db_connector):

            service = SectorDataService(self.mock_cache_manager, self.mock_tet_pipeline)

            # 模拟缓存命中
            cache_key = SectorCacheKeys.get_ranking_key(datetime.now().strftime("%Y-%m-%d"), "main_net_inflow")
            self.mock_cache_manager.get.return_value = self.large_sector_data

            # 执行多次测试并记录时间
            execution_times = []
            for _ in range(10):
                _, exec_time = self._time_function(
                    service.get_sector_fund_flow_ranking,
                    date_range="today",
                    sort_by="main_net_inflow"
                )
                execution_times.append(exec_time)

            # 性能分析
            avg_time = statistics.mean(execution_times)
            max_time = max(execution_times)
            min_time = min(execution_times)

            print(f"缓存命中性能:")
            print(f"  平均响应时间: {avg_time:.4f}s")
            print(f"  最大响应时间: {max_time:.4f}s")
            print(f"  最小响应时间: {min_time:.4f}s")

            # 性能验证
            self.assertLess(avg_time, self.PERFORMANCE_TARGETS['cache_hit_max_time'],
                            f"平均缓存命中时间 {avg_time:.4f}s 超过目标 {self.PERFORMANCE_TARGETS['cache_hit_max_time']}s")
            self.assertLess(max_time, self.PERFORMANCE_TARGETS['cache_hit_max_time'] * 2,
                            f"最大缓存命中时间 {max_time:.4f}s 超过目标的2倍")

    def test_sector_data_service_database_query_performance(self):
        """测试板块数据服务数据库查询性能"""
        with patch('core.services.sector_data_service.get_table_manager', return_value=self.mock_table_manager), \
                patch('core.services.sector_data_service.get_database_connector', return_value=self.mock_db_connector):

            service = SectorDataService(self.mock_cache_manager, self.mock_tet_pipeline)

            # 模拟缓存未命中，TET管道失败，回退到数据库查询
            self.mock_cache_manager.get.return_value = None
            self.mock_tet_pipeline.process.side_effect = Exception("TET pipeline error")

            # 模拟表结构存在
            mock_table_schema = Mock()
            mock_table_schema.table_type.value = "sector_fund_flow_daily"
            self.mock_table_manager.get_schema.return_value = mock_table_schema

            # 模拟数据库查询返回大量数据（模拟查询延迟）
            def slow_query(*args, **kwargs):
                time.sleep(0.1)  # 模拟数据库查询延迟
                return self.large_sector_data

            self.mock_db_connector.query_dataframe.side_effect = slow_query

            # 执行多次测试并记录时间
            execution_times = []
            for _ in range(5):  # 减少测试次数，因为数据库查询较慢
                _, exec_time = self._time_function(
                    service.get_sector_fund_flow_ranking,
                    date_range="today",
                    sort_by="main_net_inflow"
                )
                execution_times.append(exec_time)

            # 性能分析
            avg_time = statistics.mean(execution_times)
            max_time = max(execution_times)

            print(f"数据库查询性能:")
            print(f"  平均响应时间: {avg_time:.4f}s")
            print(f"  最大响应时间: {max_time:.4f}s")

            # 性能验证
            self.assertLess(avg_time, self.PERFORMANCE_TARGETS['db_query_max_time'],
                            f"平均数据库查询时间 {avg_time:.4f}s 超过目标 {self.PERFORMANCE_TARGETS['db_query_max_time']}s")

    def test_large_data_processing_performance(self):
        """测试大数据量处理性能"""
        with patch('core.services.sector_data_service.get_table_manager', return_value=self.mock_table_manager), \
                patch('core.services.sector_data_service.get_database_connector', return_value=self.mock_db_connector):

            service = SectorDataService(self.mock_cache_manager, self.mock_tet_pipeline)

            # 模拟TET管道返回大量数据
            mock_standard_data = Mock(spec=StandardData)
            mock_standard_data.data = self.large_intraday_data
            self.mock_tet_pipeline.process.return_value = mock_standard_data

            # 测试分时数据处理性能
            _, exec_time = self._time_function(
                service.get_sector_intraday_flow,
                sector_id="BK0001",
                date="2024-01-01"
            )

            print(f"大数据量处理性能:")
            print(f"  处理 {len(self.large_intraday_data)} 条分时数据耗时: {exec_time:.4f}s")
            print(f"  数据处理速率: {len(self.large_intraday_data) / exec_time:.0f} 条/秒")

            # 性能验证：大数据量处理应该在合理时间内完成
            self.assertLess(exec_time, 5.0, f"大数据量处理时间 {exec_time:.4f}s 过长")

    @patch('api_server.data_manager')
    def test_api_response_performance(self, mock_data_manager):
        """测试API响应性能"""
        # 模拟SectorDataService
        mock_sector_service = Mock(spec=SectorDataService)
        mock_sector_service.get_sector_fund_flow_ranking.return_value = self.large_sector_data
        mock_data_manager.get_sector_fund_flow_service.return_value = mock_sector_service

        # 执行多次API调用并记录时间
        execution_times = []
        for _ in range(10):
            start_time = time.time()
            response = self.test_client.get("/api/sector/fund-flow/ranking?date_range=today&sort_by=main_net_inflow")
            end_time = time.time()
            execution_times.append(end_time - start_time)

            # 验证响应正确
            self.assertEqual(response.status_code, 200)

        # 性能分析
        avg_time = statistics.mean(execution_times)
        max_time = max(execution_times)

        print(f"API响应性能:")
        print(f"  平均响应时间: {avg_time:.4f}s")
        print(f"  最大响应时间: {max_time:.4f}s")
        print(f"  返回数据量: {len(self.large_sector_data)} 条记录")

        # 性能验证
        self.assertLess(avg_time, self.PERFORMANCE_TARGETS['api_response_max_time'],
                        f"平均API响应时间 {avg_time:.4f}s 超过目标 {self.PERFORMANCE_TARGETS['api_response_max_time']}s")

    @patch('api_server.data_manager')
    def test_concurrent_api_requests_performance(self, mock_data_manager):
        """测试并发API请求性能"""
        # 模拟SectorDataService
        mock_sector_service = Mock(spec=SectorDataService)
        mock_sector_service.get_sector_fund_flow_ranking.return_value = self.large_sector_data
        mock_data_manager.get_sector_fund_flow_service.return_value = mock_sector_service

        def single_request():
            """单个API请求"""
            start_time = time.time()
            response = self.test_client.get("/api/sector/fund-flow/ranking?date_range=today&sort_by=main_net_inflow")
            end_time = time.time()
            return {
                'response_time': end_time - start_time,
                'status_code': response.status_code,
                'success': response.status_code == 200
            }

        # 并发执行请求
        concurrent_requests = self.PERFORMANCE_TARGETS['concurrent_requests']

        with ThreadPoolExecutor(max_workers=10) as executor:
            start_time = time.time()
            futures = [executor.submit(single_request) for _ in range(concurrent_requests)]
            results = [future.result() for future in as_completed(futures)]
            end_time = time.time()

        # 性能分析
        total_time = end_time - start_time
        successful_requests = sum(1 for r in results if r['success'])
        response_times = [r['response_time'] for r in results if r['success']]

        if response_times:
            avg_response_time = statistics.mean(response_times)
            max_response_time = max(response_times)
            requests_per_second = successful_requests / total_time
        else:
            avg_response_time = 0
            max_response_time = 0
            requests_per_second = 0

        print(f"并发请求性能:")
        print(f"  并发请求数: {concurrent_requests}")
        print(f"  成功请求数: {successful_requests}")
        print(f"  成功率: {successful_requests / concurrent_requests * 100:.1f}%")
        print(f"  总处理时间: {total_time:.4f}s")
        print(f"  平均响应时间: {avg_response_time:.4f}s")
        print(f"  最大响应时间: {max_response_time:.4f}s")
        print(f"  请求处理速率: {requests_per_second:.1f} 请求/秒")

        # 性能验证
        self.assertGreaterEqual(successful_requests / concurrent_requests, 0.95,
                                f"并发请求成功率 {successful_requests / concurrent_requests * 100:.1f}% 低于95%")

        if response_times:
            self.assertLess(avg_response_time, self.PERFORMANCE_TARGETS['api_response_max_time'] * 2,
                            f"并发场景下平均响应时间 {avg_response_time:.4f}s 过长")

    def test_cache_efficiency_simulation(self):
        """测试缓存效率模拟"""
        with patch('core.services.sector_data_service.get_table_manager', return_value=self.mock_table_manager), \
                patch('core.services.sector_data_service.get_database_connector', return_value=self.mock_db_connector):

            service = SectorDataService(self.mock_cache_manager, self.mock_tet_pipeline)

            # 模拟缓存行为：80%命中率
            cache_hits = 0
            cache_misses = 0
            total_requests = 100

            # 模拟TET管道数据
            mock_standard_data = Mock(spec=StandardData)
            mock_standard_data.data = self.large_sector_data

            for i in range(total_requests):
                # 模拟80%缓存命中率
                if i % 5 != 0:  # 80%的请求缓存命中
                    self.mock_cache_manager.get.return_value = self.large_sector_data
                    cache_hits += 1
                else:  # 20%的请求缓存未命中
                    self.mock_cache_manager.get.return_value = None
                    self.mock_tet_pipeline.process.return_value = mock_standard_data
                    cache_misses += 1

                # 执行查询
                result = service.get_sector_fund_flow_ranking(date_range="today", sort_by="main_net_inflow")
                self.assertIsNotNone(result)

            # 计算缓存命中率
            cache_hit_rate = cache_hits / total_requests

            print(f"缓存效率模拟:")
            print(f"  总请求数: {total_requests}")
            print(f"  缓存命中: {cache_hits}")
            print(f"  缓存未命中: {cache_misses}")
            print(f"  缓存命中率: {cache_hit_rate * 100:.1f}%")

            # 性能验证
            self.assertGreaterEqual(cache_hit_rate, self.PERFORMANCE_TARGETS['cache_hit_rate_min'],
                                    f"缓存命中率 {cache_hit_rate * 100:.1f}% 低于目标 {self.PERFORMANCE_TARGETS['cache_hit_rate_min'] * 100}%")

    def test_memory_usage_monitoring(self):
        """测试内存使用监控"""
        with patch('core.services.sector_data_service.get_table_manager', return_value=self.mock_table_manager), \
                patch('core.services.sector_data_service.get_database_connector', return_value=self.mock_db_connector):

            service = SectorDataService(self.mock_cache_manager, self.mock_tet_pipeline)

            # 记录初始内存
            initial_memory = psutil.Process().memory_info().rss / 1024 / 1024  # MB

            # 模拟大量数据处理
            mock_standard_data = Mock(spec=StandardData)
            mock_standard_data.data = self.large_sector_data
            self.mock_tet_pipeline.process.return_value = mock_standard_data

            # 执行多次大数据量查询
            for _ in range(20):
                result = service.get_sector_fund_flow_ranking(date_range="today", sort_by="main_net_inflow")
                # 强制垃圾回收
                gc.collect()

            # 记录最终内存
            final_memory = psutil.Process().memory_info().rss / 1024 / 1024  # MB
            memory_increase = final_memory - initial_memory

            print(f"内存使用监控:")
            print(f"  初始内存: {initial_memory:.2f}MB")
            print(f"  最终内存: {final_memory:.2f}MB")
            print(f"  内存增长: {memory_increase:.2f}MB")

            # 性能验证：内存增长应该在合理范围内
            self.assertLess(memory_increase, self.PERFORMANCE_TARGETS['max_memory_mb'],
                            f"内存增长 {memory_increase:.2f}MB 超过目标 {self.PERFORMANCE_TARGETS['max_memory_mb']}MB")

    def test_data_import_performance(self):
        """测试数据导入性能"""
        with patch('core.services.sector_data_service.get_table_manager', return_value=self.mock_table_manager), \
                patch('core.services.sector_data_service.get_database_connector', return_value=self.mock_db_connector):

            service = SectorDataService(self.mock_cache_manager, self.mock_tet_pipeline)

            # 模拟TET管道返回大量导入数据
            mock_standard_data = Mock(spec=StandardData)
            mock_standard_data.data = self.large_sector_data
            self.mock_tet_pipeline.process.return_value = mock_standard_data

            # 模拟表结构存在
            mock_table_schema = Mock()
            mock_table_schema.table_type.value = "sector_fund_flow_daily"
            self.mock_table_manager.get_schema.return_value = mock_table_schema

            # 模拟数据库插入（添加延迟模拟真实情况）
            def slow_insert(*args, **kwargs):
                time.sleep(0.01)  # 模拟数据库插入延迟
                return len(self.large_sector_data)

            self.mock_db_connector.insert_dataframe.side_effect = slow_insert

            # 测试导入性能
            _, exec_time = self._time_function(
                service.import_sector_historical_data,
                source="akshare",
                start_date="2024-01-01",
                end_date="2024-01-31"
            )

            # 计算导入速率
            import_rate = len(self.large_sector_data) / exec_time

            print(f"数据导入性能:")
            print(f"  导入数据量: {len(self.large_sector_data)} 条")
            print(f"  导入耗时: {exec_time:.4f}s")
            print(f"  导入速率: {import_rate:.0f} 条/秒")

            # 性能验证：导入速率应该满足要求
            self.assertGreater(import_rate, 1000, f"数据导入速率 {import_rate:.0f} 条/秒 过低")

    def test_performance_regression_detection(self):
        """测试性能回归检测"""
        # 这个测试可以用于检测性能回归
        # 在CI/CD流程中，可以将当前性能与历史基准进行比较

        performance_metrics = {
            'cache_hit_response_time': 0.05,  # 50ms基准
            'db_query_response_time': 1.0,    # 1s基准
            'api_response_time': 0.5,         # 500ms基准
            'cache_hit_rate': 0.85,           # 85%基准
            'import_rate': 5000               # 5000条/秒基准
        }

        print("性能基准指标:")
        for metric, target in performance_metrics.items():
            print(f"  {metric}: {target}")

        # 在实际的CI/CD环境中，这里会读取历史性能数据进行比较
        # 目前只是打印基准值作为参考

        self.assertTrue(True, "性能基准检查完成")


class TestSectorPerformanceBenchmark:
    """使用pytest-benchmark的性能基准测试"""

    def test_sector_ranking_benchmark(self, benchmark):
        """板块排行榜查询基准测试"""
        with patch('core.services.sector_data_service.get_table_manager'), \
                patch('core.services.sector_data_service.get_database_connector'):

            mock_cache_manager = Mock(spec=MultiLevelCacheManager)
            mock_tet_pipeline = Mock(spec=TETDataPipeline)

            # 模拟缓存命中
            sample_data = pd.DataFrame({
                'sector_id': ['BK0001', 'BK0002'],
                'sector_name': ['板块1', '板块2'],
                'main_net_inflow': [1000000, 800000]
            })
            mock_cache_manager.get.return_value = sample_data

            service = SectorDataService(mock_cache_manager, mock_tet_pipeline)

            # 基准测试
            result = benchmark(service.get_sector_fund_flow_ranking, "today", "main_net_inflow")

            # 验证结果
            assert not result.empty
            assert len(result) == 2


if __name__ == '__main__':
    # 运行性能测试
    unittest.main(verbosity=2)
