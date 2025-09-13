"""
数据标准化引擎测试

测试数据标准化引擎的核心功能，包括：
1. 数据格式识别和转换
2. 字段映射和类型转换
3. 质量检查和验证
4. 标准化规则管理
5. 数据存储集成

作者: FactorWeave-Quant团队
版本: 1.0
"""

from core.data_router import DataSource
from core.plugin_types import AssetType, DataType
from core.data_standardization_engine import (
    DataStandardizationEngine, FieldMapping, StandardDataSchema,
    StandardizationRule, StandardizationResult, DataFormat,
    get_data_standardization_engine
)
import unittest
import tempfile
import shutil
import pandas as pd
import numpy as np
from datetime import datetime, date
from unittest.mock import Mock, patch, MagicMock

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestFieldMapping(unittest.TestCase):
    """测试字段映射功能"""

    def test_basic_field_mapping(self):
        """测试基本字段映射"""
        mapping = FieldMapping(
            source_field="price",
            target_field="close",
            data_type="float"
        )

        # 测试正常转换
        result = mapping.apply_transform("100.5")
        self.assertEqual(result, 100.5)

        # 测试整数转换
        mapping.data_type = "int"
        result = mapping.apply_transform("100.5")
        self.assertEqual(result, 100)

    def test_field_mapping_with_transform_func(self):
        """测试带转换函数的字段映射"""
        def price_transform(value):
            return float(value) * 100  # 价格乘以100

        mapping = FieldMapping(
            source_field="price",
            target_field="price_cents",
            transform_func=price_transform
        )

        result = mapping.apply_transform("1.23")
        self.assertEqual(result, 123.0)

    def test_field_mapping_default_value(self):
        """测试默认值处理"""
        mapping = FieldMapping(
            source_field="volume",
            target_field="volume",
            data_type="int",
            default_value=0,
            is_required=False
        )

        # 测试空值使用默认值
        result = mapping.apply_transform(None)
        self.assertEqual(result, 0)

        result = mapping.apply_transform(np.nan)
        self.assertEqual(result, 0)

    def test_field_mapping_validation(self):
        """测试字段验证"""
        def positive_validator(value):
            return value > 0

        mapping = FieldMapping(
            source_field="price",
            target_field="price",
            data_type="float",
            validation_func=positive_validator
        )

        # 正常值
        result = mapping.apply_transform("100.5")
        self.assertEqual(result, 100.5)

        # 验证失败
        with self.assertRaises(ValueError):
            mapping.apply_transform("-10")


class TestStandardDataSchema(unittest.TestCase):
    """测试标准数据模式"""

    def setUp(self):
        """设置测试数据"""
        self.schema = StandardDataSchema(
            name="test_schema",
            description="测试模式",
            fields=[
                FieldMapping("symbol", "symbol", "str"),
                FieldMapping("price", "close", "float"),
                FieldMapping("vol", "volume", "int")
            ],
            primary_key=["symbol", "timestamp"]
        )

    def test_get_field_mapping(self):
        """测试获取字段映射"""
        mapping = self.schema.get_field_mapping("price")
        self.assertIsNotNone(mapping)
        self.assertEqual(mapping.target_field, "close")

        # 不存在的字段
        mapping = self.schema.get_field_mapping("nonexistent")
        self.assertIsNone(mapping)

    def test_get_target_fields(self):
        """测试获取目标字段列表"""
        fields = self.schema.get_target_fields()
        expected = ["symbol", "close", "volume"]
        self.assertEqual(fields, expected)


class TestDataStandardizationEngine(unittest.TestCase):
    """测试数据标准化引擎"""

    def setUp(self):
        """设置测试环境"""
        self.temp_dir = tempfile.mkdtemp()

        # Mock asset database manager
        self.mock_asset_db_manager = Mock()
        self.mock_connection = Mock()
        self.mock_asset_db_manager.get_connection.return_value.__enter__ = Mock(return_value=self.mock_connection)
        self.mock_asset_db_manager.get_connection.return_value.__exit__ = Mock(return_value=None)

        # 创建引擎实例
        with patch('core.data_standardization_engine.get_asset_database_manager', return_value=self.mock_asset_db_manager):
            self.engine = DataStandardizationEngine()

    def tearDown(self):
        """清理测试环境"""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_engine_initialization(self):
        """测试引擎初始化"""
        self.assertIsNotNone(self.engine)
        self.assertGreater(len(self.engine._builtin_schemas), 0)
        self.assertGreater(len(self.engine._standardization_rules), 0)

    def test_builtin_schemas(self):
        """测试内置数据模式"""
        # 检查K线模式
        kline_schema = self.engine._builtin_schemas.get("kline")
        self.assertIsNotNone(kline_schema)
        self.assertEqual(kline_schema.name, "standard_kline")

        # 检查必要字段
        target_fields = kline_schema.get_target_fields()
        required_fields = ["symbol", "timestamp", "open", "high", "low", "close"]
        for field in required_fields:
            self.assertIn(field, target_fields)

    def test_register_standardization_rule(self):
        """测试注册标准化规则"""
        schema = self.engine._builtin_schemas["kline"]

        # 注册新规则
        self.engine.register_standardization_rule(
            source=DataSource.YAHOO,
            data_type=DataType.HISTORICAL_KLINE,
            asset_type=AssetType.STOCK_US,
            schema=schema
        )

        # 验证规则已注册
        rule_key = f"{DataSource.YAHOO.value}_{DataType.HISTORICAL_KLINE.value}_{AssetType.STOCK_US.value}"
        self.assertIn(rule_key, self.engine._standardization_rules)

    def test_preprocess_tongdaxin_kline(self):
        """测试通达信K线数据预处理"""
        # 模拟通达信数据格式
        raw_data = pd.DataFrame({
            'Datetime': ['2023-01-01', '2023-01-02'],
            'Open': [100.0, 101.0],
            'High': [102.0, 103.0],
            'Low': [99.0, 100.0],
            'Close': [101.0, 102.0],
            'Volume': [1000, 1100],
            'Amount': [101000.0, 112200.0]
        })

        result = self.engine._preprocess_tongdaxin_kline(raw_data)

        # 验证字段映射
        self.assertIn('timestamp', result.columns)
        self.assertIn('open', result.columns)
        self.assertIn('data_source', result.columns)
        self.assertEqual(result['data_source'].iloc[0], 'tongdaxin')

    def test_preprocess_binance_kline(self):
        """测试币安K线数据预处理"""
        # 模拟币安数据格式（嵌套列表）
        raw_data = [
            [1640995200000, "47000.0", "48000.0", "46000.0", "47500.0", "100.5",
             1641081599999, "4750000.0", 1000, "50.0", "2375000.0", "0"],
            [1641081600000, "47500.0", "48500.0", "47000.0", "48000.0", "120.3",
             1641167999999, "5760000.0", 1200, "60.0", "2880000.0", "0"]
        ]

        result = self.engine._preprocess_binance_kline(raw_data)

        # 验证数据转换
        self.assertIn('timestamp', result.columns)
        self.assertIn('data_source', result.columns)
        self.assertEqual(result['data_source'].iloc[0], 'binance')
        self.assertEqual(len(result), 2)

    def test_kline_price_validity_check(self):
        """测试K线价格有效性检查"""
        # 正常数据
        good_data = pd.DataFrame({
            'open': [100.0, 101.0],
            'high': [102.0, 103.0],
            'low': [99.0, 100.0],
            'close': [101.0, 102.0]
        })

        issues = self.engine._check_kline_price_validity(good_data)
        self.assertEqual(len(issues), 0)

        # 异常数据：最高价低于开盘价
        bad_data = pd.DataFrame({
            'open': [100.0],
            'high': [99.0],  # 最高价低于开盘价
            'low': [98.0],
            'close': [99.5]
        })

        issues = self.engine._check_kline_price_validity(bad_data)
        self.assertGreater(len(issues), 0)
        self.assertTrue(any("最高价不合理" in issue for issue in issues))

    def test_kline_completeness_check(self):
        """测试K线数据完整性检查"""
        # 完整数据
        complete_data = pd.DataFrame({
            'symbol': ['AAPL', 'AAPL'],
            'timestamp': ['2023-01-01', '2023-01-02'],
            'open': [100.0, 101.0],
            'high': [102.0, 103.0],
            'low': [99.0, 100.0],
            'close': [101.0, 102.0]
        })

        issues = self.engine._check_kline_completeness(complete_data)
        self.assertEqual(len(issues), 0)

        # 缺失数据
        incomplete_data = pd.DataFrame({
            'symbol': ['AAPL', None],  # 缺失symbol
            'timestamp': ['2023-01-01', '2023-01-02'],
            'open': [100.0, 101.0],
            'high': [102.0, 103.0],
            'low': [99.0, 100.0],
            'close': [101.0, 102.0]
        })

        issues = self.engine._check_kline_completeness(incomplete_data)
        self.assertGreater(len(issues), 0)
        self.assertTrue(any("缺失值" in issue for issue in issues))

    def test_standardize_data_success(self):
        """测试数据标准化成功场景"""
        # 准备测试数据
        raw_data = pd.DataFrame({
            'Datetime': ['2023-01-01'],
            'Open': [100.0],
            'High': [102.0],
            'Low': [99.0],
            'Close': [101.0],
            'Volume': [1000],
            'Amount': [101000.0]
        })

        # 执行标准化
        result = self.engine.standardize_data(
            raw_data=raw_data,
            source=DataSource.TONGDAXIN,
            data_type=DataType.HISTORICAL_KLINE,
            asset_type=AssetType.STOCK_A,
            symbol="000001.SZ"
        )

        # 验证结果
        self.assertTrue(result.success)
        self.assertIsNotNone(result.data)
        self.assertEqual(result.original_count, 1)
        self.assertEqual(result.standardized_count, 1)
        self.assertGreater(result.quality_score, 0.0)

        # 验证标准化后的数据结构
        self.assertIn('symbol', result.data.columns)
        self.assertIn('timestamp', result.data.columns)
        self.assertIn('open', result.data.columns)
        self.assertEqual(result.data['symbol'].iloc[0], "000001.SZ")

    def test_standardize_data_no_rule(self):
        """测试没有匹配规则的情况"""
        raw_data = pd.DataFrame({'test': [1, 2, 3]})

        result = self.engine.standardize_data(
            raw_data=raw_data,
            source=DataSource.YAHOO,  # 没有注册的规则
            data_type=DataType.HISTORICAL_KLINE,
            asset_type=AssetType.CRYPTO,
            symbol="BTC"
        )

        self.assertFalse(result.success)
        self.assertIn('未找到标准化规则', result.metadata.get('error', ''))

    def test_standardize_and_store(self):
        """测试标准化并存储"""
        raw_data = pd.DataFrame({
            'Datetime': ['2023-01-01'],
            'Open': [100.0],
            'High': [102.0],
            'Low': [99.0],
            'Close': [101.0],
            'Volume': [1000],
            'Amount': [101000.0]
        })

        result = self.engine.standardize_and_store(
            raw_data=raw_data,
            source=DataSource.TONGDAXIN,
            data_type=DataType.HISTORICAL_KLINE,
            asset_type=AssetType.STOCK_A,
            symbol="000001.SZ"
        )

        # 验证标准化成功
        self.assertTrue(result.success)

        # 验证数据库操作被调用
        self.mock_asset_db_manager.get_connection.assert_called_with(AssetType.STOCK_A)
        self.mock_connection.execute.assert_called()

    def test_apply_schema_mapping(self):
        """测试模式映射应用"""
        schema = self.engine._builtin_schemas["kline"]

        # 测试DataFrame输入
        data = pd.DataFrame({
            'symbol': ['AAPL'],
            'timestamp': ['2023-01-01'],
            'open': [100.0],
            'high': [102.0],
            'low': [99.0],
            'close': [101.0],
            'volume': [1000],
            'amount': [101000.0],
            'data_source': ['test']
        })

        result = self.engine._apply_schema_mapping(data, schema, "AAPL")

        # 验证映射结果
        self.assertFalse(result.empty)
        expected_columns = schema.get_target_fields()
        for col in expected_columns:
            self.assertIn(col, result.columns)

        # 测试字典输入
        dict_data = {
            'symbol': 'AAPL',
            'timestamp': '2023-01-01',
            'open': 100.0,
            'high': 102.0,
            'low': 99.0,
            'close': 101.0,
            'volume': 1000,
            'amount': 101000.0,
            'data_source': 'test'
        }

        result = self.engine._apply_schema_mapping(dict_data, schema, "AAPL")
        self.assertFalse(result.empty)
        self.assertEqual(len(result), 1)

    def test_processing_statistics(self):
        """测试处理统计功能"""
        # 执行一些标准化操作
        raw_data = pd.DataFrame({
            'Datetime': ['2023-01-01'],
            'Open': [100.0],
            'High': [102.0],
            'Low': [99.0],
            'Close': [101.0],
            'Volume': [1000],
            'Amount': [101000.0]
        })

        self.engine.standardize_data(
            raw_data=raw_data,
            source=DataSource.TONGDAXIN,
            data_type=DataType.HISTORICAL_KLINE,
            asset_type=AssetType.STOCK_A,
            symbol="000001.SZ"
        )

        # 获取统计信息
        stats = self.engine.get_processing_statistics()

        self.assertIn('rules_count', stats)
        self.assertIn('schemas_count', stats)
        self.assertIn('processing_stats', stats)
        self.assertIn('success_rate', stats)

        self.assertGreater(stats['rules_count'], 0)
        self.assertGreater(stats['schemas_count'], 0)

    def test_get_supported_combinations(self):
        """测试获取支持的组合"""
        combinations = self.engine.get_supported_combinations()

        self.assertIsInstance(combinations, list)
        self.assertGreater(len(combinations), 0)

        # 验证组合结构
        for combo in combinations:
            self.assertIn('source', combo)
            self.assertIn('data_type', combo)
            self.assertIn('asset_type', combo)
            self.assertIn('schema', combo)


class TestGlobalInstance(unittest.TestCase):
    """测试全局实例管理"""

    def test_get_data_standardization_engine(self):
        """测试获取全局引擎实例"""
        with patch('core.data_standardization_engine.get_asset_database_manager'):
            engine1 = get_data_standardization_engine()
            engine2 = get_data_standardization_engine()

            # 验证单例模式
            self.assertIs(engine1, engine2)


if __name__ == '__main__':
    unittest.main()
