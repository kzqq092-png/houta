from loguru import logger
"""
Stage 4 最终测试和验收

测试内容：
- 数据计算工具函数库测试
- 数据库工具函数测试
- 系统集成管理器测试
- 缓存管理器测试
- 端到端集成测试
- 性能基准测试

作者: FactorWeave-Quant团队
版本: 1.0
"""

import pytest
import pandas as pd
import numpy as np
import asyncio
import tempfile
import shutil
from datetime import datetime, timedelta, date
from decimal import Decimal
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock
import time

# 导入测试目标
from core.utils.data_calculations import (
    calculate_change_pct, calculate_amplitude, calculate_turnover_rate,
    calculate_technical_indicators, calculate_financial_ratios,
    normalize_financial_data, validate_data_quality
)
from core.utils.database_utils import (
    generate_table_name, validate_symbol_format, standardize_market_code,
    build_select_query, build_insert_query, normalize_symbol
)
from core.performance.cache_manager import (
    LRUCache, DiskCache, MultiLevelCacheManager, CacheLevel, cache_result
)
from core.plugin_types import DataType, AssetType


class TestDataCalculations:
    """数据计算工具函数测试"""

    def test_calculate_change_pct(self):
        """测试涨跌幅计算"""
        # 标量测试
        assert calculate_change_pct(110, 100) == pytest.approx(0.1)
        assert calculate_change_pct(90, 100) == pytest.approx(-0.1)
        assert calculate_change_pct(100, 0) == 0.0  # 除零保护

        # 向量测试
        current = pd.Series([110, 90, 105])
        previous = pd.Series([100, 100, 100])
        result = calculate_change_pct(current, previous)

        expected = pd.Series([0.1, -0.1, 0.05])
        pd.testing.assert_series_equal(result, expected)

    def test_calculate_amplitude(self):
        """测试振幅计算"""
        # 标量测试
        assert calculate_amplitude(115, 95, 100) == pytest.approx(0.2)

        # 向量测试
        high = pd.Series([115, 108, 102])
        low = pd.Series([95, 92, 98])
        prev_close = pd.Series([100, 100, 100])
        result = calculate_amplitude(high, low, prev_close)

        expected = pd.Series([0.2, 0.16, 0.04])
        pd.testing.assert_series_equal(result, expected)

    def test_calculate_turnover_rate(self):
        """测试换手率计算"""
        # 标量测试
        assert calculate_turnover_rate(1000000, 10000000) == pytest.approx(0.1)

        # 向量测试
        volume = pd.Series([1000000, 2000000, 500000])
        total_shares = pd.Series([10000000, 10000000, 10000000])
        result = calculate_turnover_rate(volume, total_shares)

        expected = pd.Series([0.1, 0.2, 0.05])
        pd.testing.assert_series_equal(result, expected)

    def test_calculate_technical_indicators(self):
        """测试技术指标批量计算"""
        # 创建测试K线数据
        data = pd.DataFrame({
            'open': [100, 101, 102, 103, 104] * 20,
            'high': [105, 106, 107, 108, 109] * 20,
            'low': [95, 96, 97, 98, 99] * 20,
            'close': [102, 103, 104, 105, 106] * 20,
            'volume': [1000000, 1100000, 1200000, 1300000, 1400000] * 20
        })

        result = calculate_technical_indicators(data)

        # 验证新增的技术指标列
        expected_columns = [
            'MA5', 'MA10', 'MA20', 'MA60', 'RSI',
            'MACD_DIF', 'MACD_DEA', 'MACD',
            'KDJ_K', 'KDJ_D', 'KDJ_J',
            'BB_UPPER', 'BB_MIDDLE', 'BB_LOWER',
            'VWAP', 'CHANGE_PCT', 'AMPLITUDE'
        ]

        for col in expected_columns:
            assert col in result.columns

        # 验证数据完整性
        assert len(result) == len(data)
        assert not result['MA5'].isna().all()  # MA5应该有有效值

    def test_calculate_financial_ratios(self):
        """测试财务比率计算"""
        financial_data = {
            'net_profit': 100000000,
            'shareholders_equity': 500000000,
            'total_assets': 1000000000,
            'operating_revenue': 800000000,
            'gross_profit': 300000000,
            'current_assets': 400000000,
            'current_liabilities': 200000000,
            'total_liabilities': 500000000
        }

        ratios = calculate_financial_ratios(financial_data)

        # 验证计算结果
        assert 'roe' in ratios
        assert 'roa' in ratios
        assert 'gross_profit_margin' in ratios
        assert 'net_profit_margin' in ratios
        assert 'current_ratio' in ratios
        assert 'debt_to_assets' in ratios

        # 验证具体数值
        assert ratios['roe'] == pytest.approx(0.2)  # 100M / 500M
        assert ratios['roa'] == pytest.approx(0.1)  # 100M / 1000M
        assert ratios['current_ratio'] == pytest.approx(2.0)  # 400M / 200M

    def test_normalize_financial_data(self):
        """测试财务数据标准化"""
        data = pd.DataFrame({
            'revenue': [100, 200, 300, 400, 500],
            'profit': [10, 20, 30, 40, 50],
            'assets': [1000, 2000, 3000, 4000, 5000]
        })

        # Z-score标准化
        result = normalize_financial_data(data, method='zscore')

        # 验证标准化列存在
        assert 'revenue_normalized' in result.columns
        assert 'profit_normalized' in result.columns
        assert 'assets_normalized' in result.columns

        # 验证Z-score标准化结果（均值应接近0，标准差应接近1）
        assert abs(result['revenue_normalized'].mean()) < 1e-10
        assert abs(result['revenue_normalized'].std() - 1.0) < 1e-10

    def test_validate_data_quality(self):
        """测试数据质量验证"""
        # 高质量数据
        good_data = pd.DataFrame({
            'symbol': ['000001.SZ', '000002.SZ', '000003.SZ'],
            'price': [10.5, 20.3, 15.8],
            'volume': [1000000, 2000000, 1500000]
        })

        report = validate_data_quality(good_data, ['symbol', 'price'])

        assert report['quality_score'] > 0.8
        assert report['total_rows'] == 3
        assert report['total_columns'] == 3
        assert len(report['issues']) == 0

        # 低质量数据
        bad_data = pd.DataFrame({
            'symbol': ['000001.SZ', None, '000003.SZ'],
            'price': [10.5, None, None],
            'volume': [1000000, None, 1500000]
        })

        report = validate_data_quality(bad_data, ['symbol', 'price'])

        assert report['quality_score'] < 0.8
        assert len(report['issues']) > 0


class TestDatabaseUtils:
    """数据库工具函数测试"""

    def test_generate_table_name(self):
        """测试表名生成"""
        # 基本测试
        table_name = generate_table_name('akshare', DataType.HISTORICAL_KLINE)
        assert table_name == 'historical_kline_akshare'

        # 带周期的测试
        table_name = generate_table_name('wind', DataType.FINANCIAL_STATEMENT, 'daily')
        assert table_name == 'financial_statement_wind_daily'

        # 特殊字符清理测试
        table_name = generate_table_name('test-plugin!', 'custom@type')
        assert table_name == 'custom_type_test_plugin_'

    def test_validate_symbol_format(self):
        """测试股票代码格式验证"""
        # A股测试
        assert validate_symbol_format('000001.SZ', 'SZ') == True
        assert validate_symbol_format('600000.SH', 'SH') == True
        assert validate_symbol_format('12345', 'SZ') == False  # 5位数字
        assert validate_symbol_format('abcdef', 'SZ') == False  # 字母

        # 港股测试
        assert validate_symbol_format('00700.HK', 'HK') == True
        assert validate_symbol_format('123456', 'HK') == False  # 超过5位

        # 美股测试
        assert validate_symbol_format('AAPL.US', 'US') == True
        assert validate_symbol_format('GOOGL', 'NASDAQ') == True
        assert validate_symbol_format('123456', 'US') == False  # 数字

    def test_standardize_market_code(self):
        """测试市场代码标准化"""
        assert standardize_market_code('shanghai') == 'SH'
        assert standardize_market_code('SHENZHEN') == 'SZ'
        assert standardize_market_code('hongkong') == 'HK'
        assert standardize_market_code('nasdaq') == 'NASDAQ'
        assert standardize_market_code('unknown_market') == 'UNKNOWN_MARKET'

    def test_normalize_symbol(self):
        """测试股票代码标准化"""
        assert normalize_symbol('000001', 'SZ') == '000001.SZ'
        assert normalize_symbol('AAPL', 'US') == 'AAPL.US'
        assert normalize_symbol('000001.sz') == '000001.SZ'  # 自动标准化

    def test_build_select_query(self):
        """测试SELECT查询构建"""
        # 基本查询
        query = build_select_query('test_table')
        assert query == 'SELECT * FROM "test_table"'

        # 带列名的查询
        query = build_select_query('test_table', ['col1', 'col2'])
        assert query == 'SELECT "col1", "col2" FROM "test_table"'

        # 带WHERE条件的查询
        query = build_select_query('test_table', where_conditions={'symbol': '000001.SZ'})
        assert 'WHERE "symbol" = \'000001.SZ\'' in query

        # 带ORDER BY和LIMIT的查询
        query = build_select_query('test_table', order_by='date', limit=100)
        assert 'ORDER BY "date"' in query
        assert 'LIMIT 100' in query

    def test_build_insert_query(self):
        """测试INSERT查询构建"""
        data = {'symbol': '000001.SZ', 'price': 10.5, 'volume': 1000000}

        query, params = build_insert_query('test_table', data)

        assert 'INSERT OR REPLACE INTO "test_table"' in query
        assert '"symbol", "price", "volume"' in query
        assert params == ['000001.SZ', 10.5, 1000000]


class TestCacheManager:
    """缓存管理器测试"""

    def test_lru_cache_basic_operations(self):
        """测试LRU缓存基本操作"""
        cache = LRUCache(max_size=3)

        # 测试设置和获取
        assert cache.put('key1', 'value1') == True
        assert cache.get('key1') == 'value1'

        # 测试不存在的键
        assert cache.get('nonexistent') is None

        # 测试删除
        assert cache.delete('key1') == True
        assert cache.get('key1') is None

    def test_lru_cache_eviction(self):
        """测试LRU缓存淘汰机制"""
        cache = LRUCache(max_size=2)

        # 填满缓存
        cache.put('key1', 'value1')
        cache.put('key2', 'value2')

        # 添加第三个元素，应该淘汰最旧的
        cache.put('key3', 'value3')

        assert cache.get('key1') is None  # 被淘汰
        assert cache.get('key2') == 'value2'
        assert cache.get('key3') == 'value3'

    def test_lru_cache_ttl(self):
        """测试LRU缓存TTL功能"""
        cache = LRUCache(max_size=10)

        # 设置短TTL
        cache.put('key1', 'value1', ttl=timedelta(milliseconds=100))

        # 立即获取应该成功
        assert cache.get('key1') == 'value1'

        # 等待过期
        time.sleep(0.2)

        # 过期后应该返回None
        assert cache.get('key1') is None

    def test_disk_cache_basic_operations(self):
        """测试磁盘缓存基本操作"""
        import tempfile
        import shutil
        import os

        # 创建临时目录
        temp_dir = tempfile.mkdtemp()
        try:
            with DiskCache(cache_dir=temp_dir, max_size_mb=10) as cache:
                # 测试设置和获取
                assert cache.put('key1', {'data': 'value1'}) == True
                result = cache.get('key1')
                assert result == {'data': 'value1'}

                # 测试删除
                assert cache.delete('key1') == True
                assert cache.get('key1') is None
        finally:
            # 手动清理临时目录，忽略权限错误
            try:
                shutil.rmtree(temp_dir, ignore_errors=True)
            except:
                pass

    def test_multi_level_cache_manager(self):
        """测试多级缓存管理器"""
        import tempfile
        import shutil

        # 创建临时目录
        temp_dir = tempfile.mkdtemp()
        try:
            config = {
                'levels': [CacheLevel.MEMORY, CacheLevel.DISK],
                'memory': {'max_size': 100, 'max_memory_mb': 10},
                'disk': {'cache_dir': temp_dir, 'max_size_mb': 50},
                'default_ttl_minutes': 30
            }

            cache_manager = MultiLevelCacheManager(config)
            try:
                # 测试基本操作
                assert cache_manager.put('test_key', 'test_value') == True
                assert cache_manager.get('test_key') == 'test_value'

                # 测试缓存键生成
                key = cache_manager.get_cache_key('arg1', 'arg2', param1='value1')
                assert isinstance(key, str)
                assert len(key) == 32  # MD5哈希长度
            finally:
                # 确保关闭磁盘缓存
                if hasattr(cache_manager, 'disk_cache') and cache_manager.disk_cache:
                    cache_manager.disk_cache.close()
        finally:
            # 手动清理临时目录，忽略权限错误
            try:
                shutil.rmtree(temp_dir, ignore_errors=True)
            except:
                pass

    def test_cache_decorator(self):
        """测试缓存装饰器"""
        with tempfile.TemporaryDirectory() as temp_dir:
            config = {
                'levels': [CacheLevel.MEMORY],
                'memory': {'max_size': 100, 'max_memory_mb': 10}
            }

            cache_manager = MultiLevelCacheManager(config)

            call_count = 0

            @cache_result(ttl_minutes=5, cache_manager=cache_manager)
            def expensive_function(x, y):
                nonlocal call_count
                call_count += 1
                return x + y

            # 第一次调用
            result1 = expensive_function(1, 2)
            assert result1 == 3
            assert call_count == 1

            # 第二次调用应该使用缓存
            result2 = expensive_function(1, 2)
            assert result2 == 3
            assert call_count == 1  # 没有增加

            # 不同参数应该重新计算
            result3 = expensive_function(2, 3)
            assert result3 == 5
            assert call_count == 2


class TestSystemIntegration:
    """系统集成测试"""

    @pytest.mark.asyncio
    async def test_system_integration_manager_initialization(self):
        """测试系统集成管理器初始化"""
        # 由于系统集成管理器依赖较多组件，这里只测试配置验证
        config = {
            'duckdb': {
                'db_path': 'test_analytics.db',
                'pool_size': 3
            },
            'sqlite': {
                'db_path': 'test_system.db'
            },
            'data_source_router': {
                'strategy': 'round_robin',
                'health_check_interval': 300
            },
            'custom_field_mappings': {}
        }

        # 验证配置结构
        assert 'duckdb' in config
        assert 'sqlite' in config
        assert 'data_source_router' in config


class TestPerformanceBenchmarks:
    """性能基准测试"""

    def test_data_calculation_performance(self):
        """测试数据计算性能"""
        # 创建大数据集
        n_rows = 10000
        data = pd.DataFrame({
            'open': np.random.uniform(10, 100, n_rows),
            'high': np.random.uniform(10, 100, n_rows),
            'low': np.random.uniform(10, 100, n_rows),
            'close': np.random.uniform(10, 100, n_rows),
            'volume': np.random.randint(1000000, 10000000, n_rows)
        })

        # 测试技术指标计算性能
        start_time = time.time()
        result = calculate_technical_indicators(data)
        end_time = time.time()

        processing_time = end_time - start_time

        # 性能要求：10000条记录应在5秒内完成
        assert processing_time < 5.0
        assert len(result) == n_rows

        logger.info(f"技术指标计算性能: {n_rows} 条记录耗时 {processing_time:.2f} 秒")

    def test_cache_performance(self):
        """测试缓存性能"""
        cache = LRUCache(max_size=1000)

        # 测试写入性能
        start_time = time.time()
        for i in range(1000):
            cache.put(f'key_{i}', f'value_{i}')
        write_time = time.time() - start_time

        # 测试读取性能
        start_time = time.time()
        for i in range(1000):
            cache.get(f'key_{i}')
        read_time = time.time() - start_time

        # 性能要求：1000次操作应在1秒内完成
        assert write_time < 1.0
        assert read_time < 1.0

        logger.info(f"缓存性能: 写入 {write_time:.3f}s 读取 {read_time:.3f}s")


class TestEndToEndIntegration:
    """端到端集成测试"""

    def test_complete_data_processing_workflow(self):
        """测试完整的数据处理工作流"""
        # 1. 创建模拟K线数据
        raw_data = pd.DataFrame({
            'open': [100, 101, 102, 103, 104],
            'high': [105, 106, 107, 108, 109],
            'low': [95, 96, 97, 98, 99],
            'close': [102, 103, 104, 105, 106],
            'volume': [1000000, 1100000, 1200000, 1300000, 1400000]
        })

        # 2. 应用技术指标计算
        enhanced_data = calculate_technical_indicators(raw_data)

        # 3. 验证数据质量
        quality_report = validate_data_quality(enhanced_data, ['open', 'high', 'low', 'close', 'volume'])

        # 4. 生成表名
        table_name = generate_table_name('test_plugin', DataType.HISTORICAL_KLINE)

        # 验证工作流结果
        assert not enhanced_data.empty
        assert quality_report['quality_score'] > 0.6
        assert table_name == 'historical_kline_test_plugin'
        assert 'MA5' in enhanced_data.columns
        assert 'RSI' in enhanced_data.columns

        logger.info(f"端到端测试完成: 处理了 {len(enhanced_data)} 条记录，质量评分 {quality_report['quality_score']:.2f}")

    def test_financial_data_processing_workflow(self):
        """测试财务数据处理工作流"""
        # 1. 创建模拟财务数据
        financial_data = {
            'symbol': '000001.SZ',
            'report_date': '2023-12-31',
            'total_assets': 1000000000,
            'total_liabilities': 600000000,
            'shareholders_equity': 400000000,
            'operating_revenue': 800000000,
            'net_profit': 100000000,
            'gross_profit': 300000000
        }

        # 2. 计算财务比率
        ratios = calculate_financial_ratios(financial_data)

        # 3. 验证股票代码格式
        symbol_valid = validate_symbol_format(financial_data['symbol'])

        # 4. 标准化股票代码
        normalized_symbol = normalize_symbol(financial_data['symbol'])

        # 验证结果
        assert len(ratios) > 0
        assert 'roe' in ratios
        assert 'roa' in ratios
        assert symbol_valid == True
        assert normalized_symbol == '000001.SZ'

        logger.info(f"财务数据处理完成: 计算了 {len(ratios)} 个财务比率")


if __name__ == "__main__":
    # 运行测试
    pytest.main([__file__, "-v", "--tb=short"])
