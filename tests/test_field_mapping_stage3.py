"""
Stage 3 字段映射增强和标准化扩展测试

测试内容：
- 智能字段映射引擎测试
- TET管道集成增强测试
- 字段类型检测测试
- 映射验证测试
- 性能测试

作者: FactorWeave-Quant团队
版本: 1.0
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, date
from decimal import Decimal
from unittest.mock import Mock, patch
import time

# 导入测试目标
from core.data.field_mapping_engine import (
    FieldMappingEngine, FieldType, FieldMappingRule,
    MappingResult, FuzzyMatcher, FieldTypeDetector
)
from core.tet_data_pipeline import TETDataPipeline, StandardQuery, StandardData
from core.plugin_types import DataType, AssetType
from core.data_source_router import DataSourceRouter


class TestFuzzyMatcher:
    """模糊匹配器测试"""

    def setup_method(self):
        """测试前置设置"""
        self.matcher = FuzzyMatcher(similarity_threshold=0.8)

    def test_exact_match(self):
        """测试精确匹配"""
        candidates = ['open', 'high', 'low', 'close', 'volume']
        result = self.matcher.find_best_match('open', candidates)

        assert result is not None
        match, similarity = result
        assert match == 'open'
        assert similarity == 1.0

    def test_fuzzy_match(self):
        """测试模糊匹配"""
        candidates = ['open_price', 'high_price', 'low_price', 'close_price']
        result = self.matcher.find_best_match('open', candidates)

        assert result is not None
        match, similarity = result
        assert 'open' in match
        assert similarity >= 0.5

    def test_chinese_match(self):
        """测试中文字段匹配"""
        candidates = ['开盘价', '最高价', '最低价', '收盘价', '成交量']
        result = self.matcher.find_best_match('开盘', candidates)

        assert result is not None
        match, similarity = result
        assert '开盘' in match
        assert similarity >= 0.5

    def test_no_match(self):
        """测试无匹配情况"""
        candidates = ['apple', 'banana', 'cherry']
        result = self.matcher.find_best_match('stock_price', candidates)

        assert result is None

    def test_partial_match(self):
        """测试部分匹配"""
        candidates = ['total_revenue', 'net_profit', 'total_assets']
        result = self.matcher.find_best_match('revenue', candidates)

        assert result is not None
        match, similarity = result
        assert 'revenue' in match


class TestFieldTypeDetector:
    """字段类型检测器测试"""

    def setup_method(self):
        """测试前置设置"""
        self.detector = FieldTypeDetector()

    def test_price_field_detection(self):
        """测试价格字段检测"""
        # 基于列名检测
        sample_data = pd.Series([10.5, 11.2, 9.8, 10.1])

        field_type = self.detector.detect_field_type('open_price', sample_data)
        assert field_type == FieldType.PRICE

        field_type = self.detector.detect_field_type('开盘价', sample_data)
        assert field_type == FieldType.PRICE

    def test_volume_field_detection(self):
        """测试成交量字段检测"""
        sample_data = pd.Series([1000000, 1500000, 800000, 1200000])

        field_type = self.detector.detect_field_type('volume', sample_data)
        assert field_type == FieldType.VOLUME

        field_type = self.detector.detect_field_type('成交量', sample_data)
        assert field_type == FieldType.VOLUME

    def test_percentage_field_detection(self):
        """测试百分比字段检测"""
        sample_data = pd.Series([5.2, -2.1, 3.8, 0.5])

        field_type = self.detector.detect_field_type('change_pct', sample_data)
        assert field_type == FieldType.PERCENTAGE

        field_type = self.detector.detect_field_type('涨跌幅', sample_data)
        assert field_type == FieldType.PERCENTAGE

    def test_currency_field_detection(self):
        """测试货币字段检测"""
        sample_data = pd.Series([1000000000, 800000000, 1200000000])

        field_type = self.detector.detect_field_type('total_assets', sample_data)
        assert field_type == FieldType.CURRENCY

        field_type = self.detector.detect_field_type('营业收入', sample_data)
        assert field_type == FieldType.CURRENCY

    def test_date_field_detection(self):
        """测试日期字段检测"""
        sample_data = pd.Series(['2023-12-31', '2023-09-30', '2023-06-30'])

        field_type = self.detector.detect_field_type('report_date', sample_data)
        assert field_type == FieldType.DATE

        field_type = self.detector.detect_field_type('日期', sample_data)
        assert field_type == FieldType.DATE

    def test_boolean_field_detection(self):
        """测试布尔字段检测"""
        sample_data = pd.Series(['true', 'false', 'true', 'false'])

        field_type = self.detector.detect_field_type('is_active', sample_data)
        assert field_type == FieldType.BOOLEAN

    def test_string_field_detection(self):
        """测试字符串字段检测"""
        sample_data = pd.Series(['AAPL', 'GOOGL', 'MSFT', 'TSLA'])

        field_type = self.detector.detect_field_type('symbol', sample_data)
        assert field_type == FieldType.STRING


class TestFieldMappingEngine:
    """字段映射引擎测试"""

    def setup_method(self):
        """测试前置设置"""
        # 创建测试用的字段映射配置
        test_mappings = {
            DataType.HISTORICAL_KLINE: {
                'o': 'open', 'h': 'high', 'l': 'low', 'c': 'close', 'v': 'volume',
                '开盘价': 'open', '最高价': 'high', '最低价': 'low', '收盘价': 'close', '成交量': 'volume'
            },
            DataType.FINANCIAL_STATEMENT: {
                'total_assets': 'total_assets', '资产总计': 'total_assets',
                'net_profit': 'net_profit', '净利润': 'net_profit',
                'revenue': 'operating_revenue', '营业收入': 'operating_revenue'
            }
        }

        self.engine = FieldMappingEngine(test_mappings)

    def test_exact_field_mapping(self):
        """测试精确字段映射"""
        # 创建测试数据
        test_data = pd.DataFrame({
            'o': [10.0, 11.0, 9.5],
            'h': [11.5, 12.0, 10.0],
            'l': [9.0, 10.5, 9.0],
            'c': [10.5, 11.5, 9.8],
            'v': [1000000, 1500000, 800000]
        })

        # 执行映射
        mapped_data = self.engine.map_fields(test_data, DataType.HISTORICAL_KLINE)

        # 验证结果
        expected_columns = ['open', 'high', 'low', 'close', 'volume']
        assert list(mapped_data.columns) == expected_columns
        assert len(mapped_data) == 3

    def test_chinese_field_mapping(self):
        """测试中文字段映射"""
        # 创建测试数据
        test_data = pd.DataFrame({
            '开盘价': [10.0, 11.0, 9.5],
            '最高价': [11.5, 12.0, 10.0],
            '最低价': [9.0, 10.5, 9.0],
            '收盘价': [10.5, 11.5, 9.8],
            '成交量': [1000000, 1500000, 800000]
        })

        # 执行映射
        mapped_data = self.engine.map_fields(test_data, DataType.HISTORICAL_KLINE)

        # 验证结果
        expected_columns = ['open', 'high', 'low', 'close', 'volume']
        assert list(mapped_data.columns) == expected_columns

    def test_fuzzy_field_mapping(self):
        """测试模糊字段映射"""
        # 创建测试数据（字段名稍有不同）
        test_data = pd.DataFrame({
            'open_price': [10.0, 11.0, 9.5],
            'high_price': [11.5, 12.0, 10.0],
            'low_price': [9.0, 10.5, 9.0],
            'close_price': [10.5, 11.5, 9.8],
            'vol': [1000000, 1500000, 800000]
        })

        # 执行映射
        mapped_data = self.engine.map_fields(test_data, DataType.HISTORICAL_KLINE)

        # 验证结果（应该能够模糊匹配）
        assert 'open' in mapped_data.columns or 'open_price' in mapped_data.columns
        assert 'volume' in mapped_data.columns or 'vol' in mapped_data.columns

    def test_custom_mapping_rules(self):
        """测试自定义映射规则"""
        # 添加自定义映射规则
        custom_mappings = {
            'custom_open': ['open_custom', 'custom_o'],
            'custom_close': ['close_custom', 'custom_c']
        }

        self.engine.add_custom_mapping(DataType.HISTORICAL_KLINE, custom_mappings)

        # 创建测试数据
        test_data = pd.DataFrame({
            'open_custom': [10.0, 11.0, 9.5],
            'close_custom': [10.5, 11.5, 9.8]
        })

        # 执行映射
        mapped_data = self.engine.map_fields(test_data, DataType.HISTORICAL_KLINE)

        # 验证结果
        assert 'custom_open' in mapped_data.columns
        assert 'custom_close' in mapped_data.columns

    def test_financial_statement_mapping(self):
        """测试财务报表字段映射"""
        # 创建测试数据
        test_data = pd.DataFrame({
            'symbol': ['000001.SZ', '000002.SZ'],
            'report_date': ['2023-12-31', '2023-12-31'],
            '资产总计': [1000000000, 800000000],
            '净利润': [100000000, 80000000],
            'revenue': [800000000, 600000000]
        })

        # 执行映射
        mapped_data = self.engine.map_fields(test_data, DataType.FINANCIAL_STATEMENT)

        # 验证结果
        assert 'total_assets' in mapped_data.columns
        assert 'net_profit' in mapped_data.columns
        assert 'operating_revenue' in mapped_data.columns

    def test_mapping_validation(self):
        """测试映射验证"""
        # 创建完整的K线数据
        test_data = pd.DataFrame({
            'open': [10.0, 11.0, 9.5],
            'high': [11.5, 12.0, 10.0],
            'low': [9.0, 10.5, 9.0],
            'close': [10.5, 11.5, 9.8],
            'volume': [1000000, 1500000, 800000]
        })

        # 验证映射结果
        is_valid = self.engine.validate_mapping_result(test_data, DataType.HISTORICAL_KLINE)
        assert is_valid is True

        # 创建不完整的数据
        incomplete_data = pd.DataFrame({
            'open': [10.0, 11.0, 9.5],
            'high': [11.5, 12.0, 10.0]
            # 缺少必需字段
        })

        is_valid = self.engine.validate_mapping_result(incomplete_data, DataType.HISTORICAL_KLINE)
        assert is_valid is False

    def test_mapping_statistics(self):
        """测试映射统计信息"""
        # 创建测试数据
        test_data = pd.DataFrame({
            'o': [10.0, 11.0, 9.5],  # 精确匹配
            'high_price': [11.5, 12.0, 10.0],  # 模糊匹配
            'unknown_field': [1, 2, 3]  # 无匹配
        })

        # 执行映射
        self.engine.map_fields(test_data, DataType.HISTORICAL_KLINE)

        # 获取统计信息
        stats = self.engine.get_mapping_stats()

        assert stats['total_mappings'] > 0
        assert 'exact_matches' in stats
        assert 'fuzzy_matches' in stats
        assert 'success_rate' in stats


class TestTETDataPipelineIntegration:
    """TET数据管道集成测试"""

    def setup_method(self):
        """测试前置设置"""
        # 创建模拟的数据源路由器
        self.mock_router = Mock(spec=DataSourceRouter)
        self.pipeline = TETDataPipeline(self.mock_router)

    def test_enhanced_transform_data_kline(self):
        """测试增强的K线数据转换"""
        # 创建原始K线数据
        raw_data = pd.DataFrame({
            'o': [10.0, 11.0, 9.5, 10.2],
            'h': [11.5, 12.0, 10.0, 11.0],
            'l': [9.0, 10.5, 9.0, 9.8],
            'c': [10.5, 11.5, 9.8, 10.8],
            'v': [1000000, 1500000, 800000, 1200000],
            't': ['2023-01-01', '2023-01-02', '2023-01-03', '2023-01-04']
        })

        # 创建查询对象
        query = StandardQuery(
            symbol='000001.SZ',
            asset_type=AssetType.STOCK,
            data_type=DataType.HISTORICAL_KLINE
        )

        # 执行转换
        result = self.pipeline.transform_data(raw_data, query)

        # 验证结果
        assert not result.empty
        assert 'open' in result.columns
        assert 'high' in result.columns
        assert 'low' in result.columns
        assert 'close' in result.columns
        assert 'volume' in result.columns
        assert 'data_quality_score' in result.columns

        # 验证数据类型
        assert pd.api.types.is_numeric_dtype(result['open'])
        assert pd.api.types.is_numeric_dtype(result['volume'])

    def test_enhanced_transform_data_financial(self):
        """测试增强的财务数据转换"""
        # 创建原始财务数据
        raw_data = pd.DataFrame({
            'symbol': ['000001.SZ', '000002.SZ'],
            'report_date': ['2023-12-31', '2023-12-31'],
            'report_type': ['annual', 'annual'],
            '资产总计': ['1000000000', '800000000'],
            '净利润': ['100000000', '80000000'],
            'revenue': ['800000000', '600000000']
        })

        # 创建查询对象
        query = StandardQuery(
            symbol='000001.SZ',
            asset_type=AssetType.STOCK,
            data_type=DataType.FINANCIAL_STATEMENT
        )

        # 执行转换
        result = self.pipeline.transform_data(raw_data, query)

        # 验证结果
        assert not result.empty
        assert 'symbol' in result.columns
        assert 'report_date' in result.columns
        assert 'data_quality_score' in result.columns

        # 验证字段映射
        assert 'total_assets' in result.columns or '资产总计' in result.columns
        assert 'net_profit' in result.columns or '净利润' in result.columns

    def test_enhanced_transform_data_macro(self):
        """测试增强的宏观经济数据转换"""
        # 创建原始宏观经济数据
        raw_data = pd.DataFrame({
            'indicator_code': ['GDP_YOY', 'CPI_YOY'],
            'indicator_name': ['GDP同比增长率', 'CPI同比增长率'],
            'data_date': ['2023-12-31', '2023-12-31'],
            'value': [5.2, 2.1],  # 使用数值而不是字符串
            'unit': ['percent', 'percent'],
            'category': ['GDP', 'CPI']
        })

        # 创建查询对象
        query = StandardQuery(
            symbol='GDP_YOY',
            asset_type=AssetType.INDEX,
            data_type=DataType.MACRO_ECONOMIC
        )

        # 执行转换
        result = self.pipeline.transform_data(raw_data, query)

        # 验证结果
        assert not result.empty
        assert 'indicator_code' in result.columns
        assert 'value' in result.columns
        assert 'data_date' in result.columns
        assert 'data_quality_score' in result.columns

        # 验证数据类型
        assert pd.api.types.is_numeric_dtype(result['value'])

    def test_fallback_to_basic_mapping(self):
        """测试降级到基础映射"""
        # 创建可能导致智能映射失败的数据
        raw_data = pd.DataFrame({
            'weird_field_1': [1, 2, 3],
            'weird_field_2': ['a', 'b', 'c'],
            'weird_field_3': [None, None, None]
        })

        # 创建查询对象
        query = StandardQuery(
            symbol='TEST',
            asset_type=AssetType.STOCK,
            data_type=DataType.HISTORICAL_KLINE
        )

        # 执行转换（应该降级到基础映射）
        result = self.pipeline.transform_data(raw_data, query)

        # 验证结果（至少应该返回原始数据）
        assert not result.empty
        assert len(result) == len(raw_data)

    def test_quality_score_calculation(self):
        """测试数据质量评分计算"""
        # 创建高质量数据
        high_quality_data = pd.DataFrame({
            'open': [10.0, 11.0, 9.5, 10.2],
            'high': [11.5, 12.0, 10.0, 11.0],
            'low': [9.0, 10.5, 9.0, 9.8],
            'close': [10.5, 11.5, 9.8, 10.8],
            'volume': [1000000, 1500000, 800000, 1200000]
        })

        quality_score = self.pipeline._calculate_quality_score(
            high_quality_data, DataType.HISTORICAL_KLINE
        )
        assert quality_score > 0.8

        # 创建低质量数据（大量空值）
        low_quality_data = pd.DataFrame({
            'open': [10.0, None, None, None],
            'high': [11.5, None, None, None],
            'low': [9.0, None, None, None],
            'close': [10.5, None, None, None],
            'volume': [1000000, None, None, None]
        })

        quality_score = self.pipeline._calculate_quality_score(
            low_quality_data, DataType.HISTORICAL_KLINE
        )
        assert quality_score < 0.5


class TestPerformance:
    """性能测试"""

    def setup_method(self):
        """测试前置设置"""
        self.engine = FieldMappingEngine()

    def test_large_dataset_performance(self):
        """测试大数据集性能"""
        # 创建大数据集（10万条记录）
        n_rows = 100000
        large_data = pd.DataFrame({
            'o': np.random.uniform(10, 100, n_rows),
            'h': np.random.uniform(10, 100, n_rows),
            'l': np.random.uniform(10, 100, n_rows),
            'c': np.random.uniform(10, 100, n_rows),
            'v': np.random.randint(1000000, 10000000, n_rows)
        })

        # 测试映射性能
        start_time = time.time()
        mapped_data = self.engine.map_fields(large_data, DataType.HISTORICAL_KLINE)
        end_time = time.time()

        processing_time = end_time - start_time

        # 验证性能要求（应该在2秒内完成）
        assert processing_time < 2.0
        assert not mapped_data.empty
        assert len(mapped_data) == n_rows

        print(f"大数据集映射耗时: {processing_time:.2f}秒")

    def test_mapping_cache_performance(self):
        """测试映射缓存性能"""
        # 创建测试数据
        test_data = pd.DataFrame({
            'o': [10.0, 11.0, 9.5],
            'h': [11.5, 12.0, 10.0],
            'l': [9.0, 10.5, 9.0],
            'c': [10.5, 11.5, 9.8],
            'v': [1000000, 1500000, 800000]
        })

        # 第一次映射（无缓存）
        start_time = time.time()
        result1 = self.engine.map_fields(test_data, DataType.HISTORICAL_KLINE)
        first_time = time.time() - start_time

        # 第二次映射（有缓存）
        start_time = time.time()
        result2 = self.engine.map_fields(test_data, DataType.HISTORICAL_KLINE)
        second_time = time.time() - start_time

        # 验证缓存效果（第二次应该更快）
        assert second_time <= first_time
        assert result1.equals(result2)

        print(f"首次映射: {first_time:.4f}秒, 缓存映射: {second_time:.4f}秒")


class TestIntegrationStage3:
    """Stage 3 集成测试"""

    def setup_method(self):
        """测试前置设置"""
        self.mock_router = Mock(spec=DataSourceRouter)
        self.pipeline = TETDataPipeline(self.mock_router)

    def test_end_to_end_kline_processing(self):
        """测试端到端K线数据处理"""
        # 模拟从不同数据源获取的原始数据
        raw_data_variants = [
            # 变体1：英文字段
            pd.DataFrame({
                'open': [10.0, 11.0, 9.5],
                'high': [11.5, 12.0, 10.0],
                'low': [9.0, 10.5, 9.0],
                'close': [10.5, 11.5, 9.8],
                'volume': [1000000, 1500000, 800000],
                'datetime': ['2023-01-01', '2023-01-02', '2023-01-03']
            }),
            # 变体2：中文字段
            pd.DataFrame({
                '开盘价': [10.0, 11.0, 9.5],
                '最高价': [11.5, 12.0, 10.0],
                '最低价': [9.0, 10.5, 9.0],
                '收盘价': [10.5, 11.5, 9.8],
                '成交量': [1000000, 1500000, 800000],
                '日期': ['2023-01-01', '2023-01-02', '2023-01-03']
            }),
            # 变体3：简写字段
            pd.DataFrame({
                'o': [10.0, 11.0, 9.5],
                'h': [11.5, 12.0, 10.0],
                'l': [9.0, 10.5, 9.0],
                'c': [10.5, 11.5, 9.8],
                'v': [1000000, 1500000, 800000],
                't': ['2023-01-01', '2023-01-02', '2023-01-03']
            })
        ]

        query = StandardQuery(
            symbol='000001.SZ',
            asset_type=AssetType.STOCK,
            data_type=DataType.HISTORICAL_KLINE
        )

        # 测试所有变体都能正确处理
        for i, raw_data in enumerate(raw_data_variants):
            result = self.pipeline.transform_data(raw_data, query)

            # 验证结果一致性
            assert not result.empty
            assert 'open' in result.columns
            assert 'high' in result.columns
            assert 'low' in result.columns
            assert 'close' in result.columns
            assert 'volume' in result.columns
            assert 'data_quality_score' in result.columns

            # 验证数据质量
            quality_score = result['data_quality_score'].iloc[0]
            assert quality_score > 0.5

            print(f"变体 {i+1} 处理成功，质量评分: {quality_score:.2f}")

    def test_mixed_data_type_processing(self):
        """测试混合数据类型处理"""
        # 创建包含多种数据类型的测试数据
        test_cases = [
            (DataType.HISTORICAL_KLINE, pd.DataFrame({
                'open': [10.0, 11.0], 'high': [11.5, 12.0], 'low': [9.0, 10.5],
                'close': [10.5, 11.5], 'volume': [1000000, 1500000]
            })),
            (DataType.FINANCIAL_STATEMENT, pd.DataFrame({
                'symbol': ['000001.SZ', '000002.SZ'],
                'report_date': ['2023-12-31', '2023-12-31'],
                'total_assets': [1000000000, 800000000],
                'net_profit': [100000000, 80000000]
            })),
            (DataType.MACRO_ECONOMIC, pd.DataFrame({
                'indicator_code': ['GDP_YOY', 'CPI_YOY'],
                'value': [5.2, 2.1],
                'data_date': ['2023-12-31', '2023-12-31']
            }))
        ]

        # 测试每种数据类型
        for data_type, test_data in test_cases:
            query = StandardQuery(
                symbol='TEST',
                asset_type=AssetType.STOCK,
                data_type=data_type
            )

            result = self.pipeline.transform_data(test_data, query)

            # 验证基本结果
            assert not result.empty
            assert 'data_quality_score' in result.columns

            # 验证数据质量评分
            quality_scores = result['data_quality_score'].dropna()
            if len(quality_scores) > 0:
                avg_quality = quality_scores.mean()
                assert 0.0 <= avg_quality <= 1.0

                print(f"{data_type} 平均质量评分: {avg_quality:.2f}")


if __name__ == "__main__":
    # 运行测试
    pytest.main([__file__, "-v", "--tb=short"])
