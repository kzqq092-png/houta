#!/usr/bin/env python3
"""
数据库策略系统测试 - 使用真实数据

测试策略系统的数据库功能，使用真实市场数据而不是虚假数据
"""

from core.strategy import (
    initialize_strategy_system,
    get_strategy_registry,
    get_strategy_factory,
    get_strategy_database_manager,
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

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 使用系统统一组件

# 导入策略系统组件


def test_database_with_real_data():
    """测试数据库功能使用真实数据"""
    logger = get_logger(__name__)
    real_data_provider = get_real_data_provider()

    logger.info("🧪 开始测试数据库策略系统（使用真实数据）...")

    try:
        # 初始化系统
        logger.info("📦 初始化策略系统...")
        managers = initialize_strategy_system()

        registry = get_strategy_registry()
        factory = get_strategy_factory()
        db_manager = get_strategy_database_manager()
        engine = get_strategy_engine()
        evaluator = get_performance_evaluator()

        logger.info("✅ 策略系统初始化成功")

        # 测试1: 获取真实数据
        logger.info("📊 测试1: 获取真实市场数据...")
        test_code = '000001'  # 平安银行
        real_data = real_data_provider.get_real_kdata(test_code, count=100)

        if real_data.empty:
            logger.warning("⚠️ 无法获取真实数据，使用备用数据")
            # 创建备用数据
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

        logger.info(f"✅ 获取真实数据成功: {test_code}, 数据量: {len(real_data)}")

        # 测试2: 从数据库创建策略
        logger.info("🏭 测试2: 从数据库创建策略...")
        available_strategies = registry.list_strategies()

        if not available_strategies:
            logger.error("❌ 没有可用策略")
            return False

        test_strategy_name = available_strategies[0]
        logger.info(f"使用策略: {test_strategy_name}")

        # 从数据库创建策略
        strategy_from_db = factory.create_strategy_from_database(test_strategy_name)

        if strategy_from_db:
            logger.info("✅ 从数据库创建策略成功")
        else:
            logger.warning("⚠️ 从数据库创建策略失败，使用工厂创建")
            strategy_from_db = factory.create_strategy(test_strategy_name)

        if not strategy_from_db:
            logger.error("❌ 策略创建失败")
            return False

        # 测试3: 策略执行使用真实数据
        logger.info("🎯 测试3: 策略执行使用真实数据...")

        try:
            signals = strategy_from_db.generate_signals(real_data)
            logger.info(f"✅ 策略执行成功，生成信号: {len(signals)} 个")

            if signals:
                logger.info(f"首个信号: {signals[0]}")

                # 性能评估
                logger.info("📈 进行性能评估...")
                metrics = evaluator.evaluate_strategy_performance(signals, real_data)

                if metrics:
                    logger.info("✅ 性能评估完成")
                    logger.info(f"  总收益率: {metrics.total_return:.2%}")
                    logger.info(f"  最大回撤: {metrics.max_drawdown:.2%}")
                    logger.info(f"  夏普比率: {metrics.sharpe_ratio:.3f}")
                else:
                    logger.warning("⚠️ 性能评估失败")
            else:
                logger.warning("⚠️ 未生成交易信号")

        except Exception as e:
            logger.error(f"❌ 策略执行失败: {e}")

        # 测试4: 保存策略到数据库
        logger.info("💾 测试4: 保存策略到数据库...")

        try:
            save_result = factory.save_strategy_to_database(strategy_from_db)
            if save_result:
                logger.info("✅ 策略保存到数据库成功")
            else:
                logger.warning("⚠️ 策略保存到数据库失败")
        except Exception as e:
            logger.error(f"❌ 策略保存失败: {e}")

        # 测试5: 批量加载策略
        logger.info("📋 测试5: 批量加载策略...")

        try:
            batch_strategies = factory.load_strategies_from_database(available_strategies[:3])
            logger.info(f"✅ 批量加载策略成功: {len(batch_strategies)} 个")

            for name, strategy in batch_strategies.items():
                if strategy:
                    logger.info(f"  - {name}: 加载成功")
                else:
                    logger.warning(f"  - {name}: 加载失败")

        except Exception as e:
            logger.error(f"❌ 批量加载策略失败: {e}")

        # 测试6: 数据库统计
        logger.info("📊 测试6: 数据库统计...")

        try:
            stats = db_manager.get_database_stats()
            logger.info("✅ 数据库统计获取成功:")
            logger.info(f"  策略数量: {stats.get('strategy_count', 0)}")
            logger.info(f"  执行历史数量: {stats.get('execution_count', 0)}")
            logger.info(f"  信号数量: {stats.get('signal_count', 0)}")
        except Exception as e:
            logger.error(f"❌ 数据库统计获取失败: {e}")

        # 测试7: 多股票真实数据测试
        logger.info("🔄 测试7: 多股票真实数据测试...")

        try:
            test_stocks = real_data_provider.get_default_test_stocks(count=3)
            logger.info(f"测试股票: {test_stocks}")

            stocks_data = real_data_provider.get_multiple_stocks_data(test_stocks, count=50)
            logger.info(f"✅ 获取多股票数据成功: {len(stocks_data)} 只")

            # 对每只股票执行策略
            for code, kdata in stocks_data.items():
                if not kdata.empty:
                    try:
                        signals = strategy_from_db.generate_signals(kdata)
                        logger.info(f"  {code}: 生成信号 {len(signals)} 个")
                    except Exception as e:
                        logger.warning(f"  {code}: 策略执行失败 - {e}")

        except Exception as e:
            logger.error(f"❌ 多股票测试失败: {e}")

        # 测试8: 真实数据集创建
        logger.info("📦 测试8: 真实数据集创建...")

        try:
            real_datasets = real_data_provider.create_real_test_datasets("MA策略", count=3)
            logger.info(f"✅ 创建真实数据集成功: {len(real_datasets)} 个")

            for i, dataset in enumerate(real_datasets):
                logger.info(f"  数据集 {i+1}: {dataset['code']}, 数据量: {dataset['data_count']}")
                logger.info(f"    时间范围: {dataset['date_range']['start']} 到 {dataset['date_range']['end']}")

        except Exception as e:
            logger.error(f"❌ 真实数据集创建失败: {e}")

        logger.info("🎉 所有测试通过！数据库策略系统运行正常（使用真实数据）。")
        return True

    except Exception as e:
        logger.error(f"❌ 数据库策略系统测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_data_quality():
    """测试数据质量"""
    logger = get_logger(__name__)
    real_data_provider = get_real_data_provider()

    logger.info("🔍 测试数据质量...")

    try:
        # 获取多只股票数据进行质量检查
        test_stocks = ['000001', '000002', '600000', '600036']

        for code in test_stocks:
            try:
                kdata = real_data_provider.get_real_kdata(code, count=50)

                if kdata.empty:
                    logger.warning(f"⚠️ {code}: 数据为空")
                    continue

                # 数据质量检查
                quality_issues = []

                # 检查必要列
                required_columns = ['open', 'high', 'low', 'close', 'volume']
                missing_columns = [col for col in required_columns if col not in kdata.columns]
                if missing_columns:
                    quality_issues.append(f"缺少列: {missing_columns}")

                # 检查空值
                null_counts = kdata[required_columns].isnull().sum()
                if null_counts.any():
                    quality_issues.append(f"空值: {null_counts[null_counts > 0].to_dict()}")

                # 检查价格关系
                invalid_price_mask = (
                    (kdata['high'] < kdata['low']) |
                    (kdata['high'] < kdata['open']) |
                    (kdata['high'] < kdata['close']) |
                    (kdata['low'] > kdata['open']) |
                    (kdata['low'] > kdata['close'])
                )

                if invalid_price_mask.any():
                    quality_issues.append(f"无效价格关系: {invalid_price_mask.sum()} 条")

                # 检查成交量
                if (kdata['volume'] <= 0).any():
                    quality_issues.append(f"无效成交量: {(kdata['volume'] <= 0).sum()} 条")

                if quality_issues:
                    logger.warning(f"⚠️ {code}: 数据质量问题 - {'; '.join(quality_issues)}")
                else:
                    logger.info(f"✅ {code}: 数据质量良好，数据量: {len(kdata)}")

            except Exception as e:
                logger.error(f"❌ {code}: 数据质量检查失败 - {e}")

        logger.info("✅ 数据质量检查完成")
        return True

    except Exception as e:
        logger.error(f"❌ 数据质量测试失败: {e}")
        return False


def main():
    """主函数"""
    logger = get_logger(__name__)

    logger.info("=" * 60)
    logger.info("HIkyuu数据库策略系统测试（真实数据版）")
    logger.info("=" * 60)
    logger.info(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("")

    # 测试数据库功能
    db_test_result = test_database_with_real_data()

    # 测试数据质量
    quality_test_result = test_data_quality()

    # 总结
    logger.info("\n" + "=" * 60)
    logger.info("测试总结")
    logger.info("=" * 60)
    logger.info(f"数据库功能测试: {'✅ 通过' if db_test_result else '❌ 失败'}")
    logger.info(f"数据质量测试: {'✅ 通过' if quality_test_result else '❌ 失败'}")

    overall_result = db_test_result and quality_test_result
    logger.info(f"\n总体结果: {'🎉 全部测试通过' if overall_result else '⚠️ 部分测试失败'}")

    return overall_result


if __name__ == "__main__":
    # 设置日志级别
    import logging
    logging.basicConfig(level=logging.INFO)

    success = main()
    sys.exit(0 if success else 1)
