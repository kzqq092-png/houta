#!/usr/bin/env python3
"""
策略系统测试 - 使用真实数据

测试策略系统的各个组件，使用真实市场数据而不是虚假数据
"""

from core.strategy import (
    initialize_strategy_system,
    get_strategy_registry,
    get_strategy_factory,
    get_strategy_engine,
    get_performance_evaluator,
    BaseStrategy,
    StrategySignal,
    StrategyParameter
)
from core.real_data_provider import get_real_data_provider
from core.adapters import get_logger
import sys
import os
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import unittest

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 使用系统统一组件

# 导入策略系统组件


class TestStrategySystemWithRealData(unittest.TestCase):
    """策略系统真实数据测试"""

    @classmethod
    def setUpClass(cls):
        """测试类初始化"""
        cls.logger = get_logger(__name__)
        cls.real_data_provider = get_real_data_provider()

        # 初始化策略系统
        cls.managers = initialize_strategy_system()
        cls.registry = get_strategy_registry()
        cls.factory = get_strategy_factory()
        cls.engine = get_strategy_engine()
        cls.evaluator = get_performance_evaluator()

        cls.logger.info("策略系统真实数据测试初始化完成")

    def test_real_data_provider(self):
        """测试真实数据提供器"""
        self.logger.info("测试真实数据提供器...")

        # 测试获取真实K线数据
        test_code = '000001'  # 平安银行
        kdata = self.real_data_provider.get_real_kdata(test_code, count=100)

        self.assertFalse(kdata.empty, "真实K线数据不应为空")
        self.assertIn('open', kdata.columns, "应包含开盘价列")
        self.assertIn('high', kdata.columns, "应包含最高价列")
        self.assertIn('low', kdata.columns, "应包含最低价列")
        self.assertIn('close', kdata.columns, "应包含收盘价列")
        self.assertIn('volume', kdata.columns, "应包含成交量列")

        # 验证价格关系
        self.assertTrue((kdata['high'] >= kdata['low']).all(), "最高价应大于等于最低价")
        self.assertTrue((kdata['high'] >= kdata['open']).all(), "最高价应大于等于开盘价")
        self.assertTrue((kdata['high'] >= kdata['close']).all(), "最高价应大于等于收盘价")
        self.assertTrue((kdata['low'] <= kdata['open']).all(), "最低价应小于等于开盘价")
        self.assertTrue((kdata['low'] <= kdata['close']).all(), "最低价应小于等于收盘价")

        self.logger.info(f"✓ 真实数据验证通过: {test_code}, 数据量: {len(kdata)}")

    def test_strategy_with_real_data(self):
        """测试策略使用真实数据"""
        self.logger.info("测试策略使用真实数据...")

        # 获取可用策略
        available_strategies = self.registry.list_strategies()
        self.assertGreater(len(available_strategies), 0, "应有可用策略")

        # 选择第一个策略进行测试
        strategy_name = available_strategies[0]
        self.logger.info(f"测试策略: {strategy_name}")

        # 创建策略实例
        strategy = self.factory.create_strategy(strategy_name)
        self.assertIsNotNone(strategy, f"策略 {strategy_name} 创建失败")

        # 获取真实数据
        test_code = '000001'
        real_data = self.real_data_provider.get_real_kdata(test_code, count=100)
        self.assertFalse(real_data.empty, "真实数据不应为空")

        # 执行策略
        signals = strategy.generate_signals(real_data)
        self.assertIsInstance(signals, list, "策略信号应为列表")

        self.logger.info(f"✓ 策略 {strategy_name} 使用真实数据测试通过，生成信号: {len(signals)} 个")

    def test_performance_evaluation_with_real_data(self):
        """测试使用真实数据进行性能评估"""
        self.logger.info("测试使用真实数据进行性能评估...")

        # 获取真实测试数据集
        test_datasets = self.real_data_provider.create_real_test_datasets("MA策略", count=3)
        self.assertGreater(len(test_datasets), 0, "应创建真实测试数据集")

        # 选择第一个数据集
        dataset = test_datasets[0]
        real_data = dataset['data']
        test_code = dataset['code']

        self.logger.info(f"使用真实数据评估: {test_code}, 数据量: {len(real_data)}")

        # 创建MA策略
        strategy = self.factory.create_strategy("MA策略")
        self.assertIsNotNone(strategy, "MA策略创建失败")

        # 生成信号
        signals = strategy.generate_signals(real_data)

        # 性能评估
        if signals:
            metrics = self.evaluator.evaluate_strategy_performance(signals, real_data)
            self.assertIsNotNone(metrics, "性能评估结果不应为空")

            self.logger.info(f"✓ 真实数据性能评估完成:")
            self.logger.info(f"  总收益率: {metrics.total_return:.2%}")
            self.logger.info(f"  最大回撤: {metrics.max_drawdown:.2%}")
            self.logger.info(f"  夏普比率: {metrics.sharpe_ratio:.3f}")
        else:
            self.logger.warning("未生成交易信号")

    def test_multiple_stocks_real_data(self):
        """测试多只股票真实数据"""
        self.logger.info("测试多只股票真实数据...")

        # 获取默认测试股票
        test_stocks = self.real_data_provider.get_default_test_stocks(count=3)
        self.assertGreater(len(test_stocks), 0, "应获取到测试股票")

        # 批量获取数据
        stocks_data = self.real_data_provider.get_multiple_stocks_data(test_stocks, count=50)

        self.assertGreater(len(stocks_data), 0, "应获取到股票数据")

        for code, kdata in stocks_data.items():
            self.assertFalse(kdata.empty, f"股票 {code} 数据不应为空")
            self.assertGreater(len(kdata), 10, f"股票 {code} 数据量应足够")

            # 验证数据质量
            self.assertTrue((kdata['volume'] > 0).all(), f"股票 {code} 成交量应为正数")

        self.logger.info(f"✓ 多只股票真实数据测试通过: {list(stocks_data.keys())}")

    def test_cache_functionality(self):
        """测试缓存功能"""
        self.logger.info("测试缓存功能...")

        test_code = '000001'

        # 第一次获取数据（应从数据源获取）
        start_time = datetime.now()
        kdata1 = self.real_data_provider.get_real_kdata(test_code, count=50)
        first_duration = (datetime.now() - start_time).total_seconds()

        # 第二次获取数据（应从缓存获取）
        start_time = datetime.now()
        kdata2 = self.real_data_provider.get_real_kdata(test_code, count=50)
        second_duration = (datetime.now() - start_time).total_seconds()

        # 验证数据一致性
        pd.testing.assert_frame_equal(kdata1, kdata2, "缓存数据应与原始数据一致")

        # 验证缓存效果（第二次应更快）
        self.assertLess(second_duration, first_duration * 0.5, "缓存应提高获取速度")

        # 获取缓存统计
        cache_stats = self.real_data_provider.get_cache_stats()
        self.assertGreater(cache_stats['total_cached'], 0, "应有缓存数据")

        self.logger.info(f"✓ 缓存功能测试通过: 首次 {first_duration:.3f}s, 缓存 {second_duration:.3f}s")

    def test_data_validation(self):
        """测试数据验证功能"""
        self.logger.info("测试数据验证功能...")

        # 获取真实数据
        test_code = '000002'  # 万科A
        kdata = self.real_data_provider.get_real_kdata(test_code, count=100)

        self.assertFalse(kdata.empty, "数据不应为空")

        # 验证数据完整性
        required_columns = ['open', 'high', 'low', 'close', 'volume']
        for col in required_columns:
            self.assertIn(col, kdata.columns, f"应包含 {col} 列")
            self.assertFalse(kdata[col].isna().any(), f"{col} 列不应有空值")

        # 验证价格逻辑
        self.assertTrue((kdata['high'] >= kdata['low']).all(), "价格逻辑验证失败")
        self.assertTrue((kdata['volume'] > 0).all(), "成交量应为正数")

        # 验证时间索引
        self.assertIsInstance(kdata.index, pd.DatetimeIndex, "索引应为时间类型")
        self.assertTrue(kdata.index.is_monotonic_increasing, "时间索引应递增")

        self.logger.info(f"✓ 数据验证通过: {test_code}, 数据量: {len(kdata)}")


def create_real_test_data_for_legacy_tests():
    """为旧测试创建真实数据"""
    logger = get_logger(__name__)
    real_data_provider = get_real_data_provider()

    logger.info("为旧测试创建真实数据...")

    # 获取真实数据
    test_code = '000001'
    real_data = real_data_provider.get_real_kdata(test_code, count=100)

    if real_data.empty:
        logger.warning("无法获取真实数据，使用默认数据")
        # 创建最小化的默认数据
        dates = pd.date_range(start='2023-01-01', periods=100, freq='D')
        real_data = pd.DataFrame({
            'open': np.random.uniform(10, 20, 100),
            'high': np.random.uniform(15, 25, 100),
            'low': np.random.uniform(8, 15, 100),
            'close': np.random.uniform(10, 20, 100),
            'volume': np.random.randint(1000000, 10000000, 100)
        }, index=dates)

        # 确保价格关系正确
        real_data['high'] = np.maximum.reduce([real_data['open'], real_data['high'],
                                               real_data['low'], real_data['close']])
        real_data['low'] = np.minimum.reduce([real_data['open'], real_data['high'],
                                              real_data['low'], real_data['close']])

    logger.info(f"创建真实测试数据完成: {len(real_data)} 条")
    return real_data


if __name__ == '__main__':
    # 设置日志级别
    import logging
    logging.basicConfig(level=logging.INFO)

    # 运行测试
    unittest.main(verbosity=2)
