from loguru import logger
#!/usr/bin/env python3
"""
HIkyuu策略管理系统全面集成测试

测试策略管理系统的所有组件协作和完整功能
"""

# Loguru导入已完成
from core.strategy import (
    initialize_strategy_system,
    get_strategy_registry,
    get_strategy_factory,
    get_strategy_database_manager,
    get_strategy_engine,
    get_lifecycle_manager,
    get_performance_evaluator
)
import sys
import os
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import time
import threading
from concurrent.futures import ThreadPoolExecutor

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def create_comprehensive_test_data() -> pd.DataFrame:
    """创建全面的测试数据"""
    # 创建一年的日线数据
    dates = pd.date_range(start='2023-01-01', end='2023-12-31', freq='D')
    np.random.seed(42)

    # 生成更真实的股价数据
    base_price = 100.0
    prices = [base_price]

    # 模拟趋势和波动
    trend = 0.0005  # 轻微上涨趋势
    volatility = 0.02

    for i in range(1, len(dates)):
        # 添加趋势和随机波动
        daily_return = trend + np.random.normal(0, volatility)

        # 添加一些特殊模式
        if i % 50 == 0:  # 每50天一个小幅调整
            daily_return -= 0.05
        elif i % 100 == 0:  # 每100天一个反弹
            daily_return += 0.08

        new_price = prices[-1] * (1 + daily_return)
        prices.append(max(new_price, 1.0))  # 价格不能为负

    # 创建OHLCV数据
    data = pd.DataFrame({
        'open': [p * (1 + np.random.normal(0, 0.003)) for p in prices],
        'high': [p * (1 + abs(np.random.normal(0, 0.015))) for p in prices],
        'low': [p * (1 - abs(np.random.normal(0, 0.015))) for p in prices],
        'close': prices,
        'volume': np.random.randint(500000, 5000000, len(dates))
    }, index=dates)

    # 确保OHLC关系正确
    data['high'] = data[['open', 'high', 'close']].max(axis=1)
    data['low'] = data[['open', 'low', 'close']].min(axis=1)

    return data

def test_system_initialization():
    """测试系统初始化"""
    logger = logger.bind(module=__name__)
    logger.info("=" * 80)
    logger.info("开始全面策略管理系统集成测试")
    logger.info("=" * 80)

    try:
        logger.info("1. 初始化策略管理系统...")
        start_time = time.time()

        # 初始化所有组件
        managers = initialize_strategy_system()

        registry = get_strategy_registry()
        factory = get_strategy_factory()
        db_manager = get_strategy_database_manager()
        engine = get_strategy_engine()
        lifecycle_manager = get_lifecycle_manager()
        performance_evaluator = get_performance_evaluator()

        init_time = time.time() - start_time
        logger.info(f"系统初始化完成，耗时: {init_time:.3f} 秒")

        # 验证组件
        components = {
            '策略注册器': registry,
            '策略工厂': factory,
            '数据库管理器': db_manager,
            '策略引擎': engine,
            '生命周期管理器': lifecycle_manager,
            '性能评估器': performance_evaluator
        }

        all_components_ok = True
        for name, component in components.items():
            if component is not None:
                logger.info(f" {name}: {type(component).__name__}")
            else:
                logger.error(f" {name}: 初始化失败 (component is {component})")
                all_components_ok = False

        return all_components_ok

    except Exception as e:
        logger.error(f"系统初始化失败: {e}", exc_info=True)
        return False

def test_strategy_lifecycle():
    """测试策略完整生命周期"""
    logger = logger.bind(module=__name__)
    logger.info("\n2. 测试策略完整生命周期...")

    try:
        registry = get_strategy_registry()
        factory = get_strategy_factory()
        db_manager = get_strategy_database_manager()
        lifecycle_manager = get_lifecycle_manager()

        # 获取可用策略
        available_strategies = registry.list_strategies()
        logger.info(f"可用策略: {len(available_strategies)} 个")

        if not available_strategies:
            logger.error("没有可用策略")
            return False

        test_strategy_name = available_strategies[0]
        logger.info(f"测试策略: {test_strategy_name}")

        # 1. 创建策略实例
        logger.info("  1.1 创建策略实例...")

        # 根据策略类型设置正确的参数
        strategy_params = {}
        if "MA策略" in test_strategy_name:
            strategy_params = {
                "short_period": 10,
                "long_period": 30,
                "min_confidence": 0.6
            }
        elif "MACD策略" in test_strategy_name:
            strategy_params = {
                "fast_period": 12,
                "slow_period": 26,
                "signal_period": 9,
                "min_confidence": 0.6
            }
        elif "RSI策略" in test_strategy_name:
            strategy_params = {
                "period": 14,
                "oversold": 30,
                "overbought": 70,
                "min_confidence": 0.6
            }
        elif "KDJ策略" in test_strategy_name:
            strategy_params = {
                "period": 9,
                "k_period": 3,
                "d_period": 3,
                "oversold": 20,
                "overbought": 80,
                "min_confidence": 0.6
            }
        elif "布林带策略" in test_strategy_name:
            strategy_params = {
                "period": 20,
                "std_dev": 2.0,
                "min_confidence": 0.6
            }
        else:
            # 默认参数
            strategy_params = {
                "min_confidence": 0.6
            }

        strategy = factory.create_strategy(
            strategy_name=test_strategy_name,
            instance_name=f"lifecycle_test_{test_strategy_name}",
            **strategy_params
        )

        if not strategy:
            logger.error("策略实例创建失败")
            return False

        logger.info(f"   策略实例创建成功: {strategy.name}")

        # 2. 保存到数据库
        logger.info("  1.2 保存策略到数据库...")
        save_success = factory.save_strategy_to_database(strategy.name)
        if save_success:
            logger.info("   策略保存到数据库成功")
        else:
            logger.warning("   策略保存到数据库失败")

        # 3. 从数据库加载
        logger.info("  1.3 从数据库加载策略...")
        loaded_strategy = factory.create_strategy_from_database(
            test_strategy_name)
        if loaded_strategy:
            logger.info(f"   从数据库加载策略成功: {loaded_strategy.name}")
        else:
            logger.warning("   从数据库加载策略失败")

        # 4. 生命周期管理
        logger.info("  1.4 测试生命周期管理...")
        lifecycle_info = lifecycle_manager.get_strategy_lifecycle(
            strategy.name)
        logger.info(f"  生命周期信息: {lifecycle_info}")

        # 5. 策略克隆
        logger.info("  1.5 测试策略克隆...")
        cloned_strategy = factory.clone_strategy(
            strategy.name,
            f"cloned_{strategy.name}"
        )
        if cloned_strategy:
            logger.info(f"   策略克隆成功: {cloned_strategy.name}")
        else:
            logger.warning("   策略克隆失败")

        return True

    except Exception as e:
        logger.error(f"策略生命周期测试失败: {e}", exc_info=True)
        return False

def test_parallel_execution():
    """测试并行执行"""
    logger = logger.bind(module=__name__)
    logger.info("\n3. 测试并行策略执行...")

    try:
        registry = get_strategy_registry()
        factory = get_strategy_factory()
        engine = get_strategy_engine()

        # 创建测试数据
        test_data = create_comprehensive_test_data()
        logger.info(f"测试数据: {len(test_data)} 行")

        # 获取可用策略
        available_strategies = registry.list_strategies()[:3]  # 取前3个策略
        logger.info(f"并行测试策略: {available_strategies}")

        # 创建策略实例
        strategies = {}
        for strategy_name in available_strategies:
            # 根据策略类型设置正确的参数
            strategy_params = {}
            if "MA策略" in strategy_name:
                strategy_params = {
                    "short_period": 5,
                    "long_period": 20,
                    "min_confidence": 0.6
                }
            elif "MACD策略" in strategy_name:
                strategy_params = {
                    "fast_period": 12,
                    "slow_period": 26,
                    "signal_period": 9,
                    "min_confidence": 0.6
                }
            elif "RSI策略" in strategy_name:
                strategy_params = {
                    "period": 14,
                    "oversold": 30,
                    "overbought": 70,
                    "min_confidence": 0.6
                }
            elif "KDJ策略" in strategy_name:
                strategy_params = {
                    "period": 9,
                    "k_period": 3,
                    "d_period": 3,
                    "oversold": 20,
                    "overbought": 80,
                    "min_confidence": 0.6
                }
            elif "布林带策略" in strategy_name:
                strategy_params = {
                    "period": 20,
                    "std_dev": 2.0,
                    "min_confidence": 0.6
                }
            else:
                # 默认参数
                strategy_params = {
                    "min_confidence": 0.6
                }

            strategy = factory.create_strategy(
                strategy_name=strategy_name,
                instance_name=f"parallel_{strategy_name}",
                **strategy_params
            )
            if strategy:
                strategies[strategy_name] = strategy

        logger.info(f"创建策略实例: {len(strategies)} 个")

        # 并行执行测试
        def execute_strategy(strategy_name):
            try:
                start_time = time.time()
                signals, execution_info = engine.execute_strategy(
                    strategy_name=f"parallel_{strategy_name}",
                    data=test_data,
                    use_cache=True,
                    save_to_db=True
                )
                execution_time = time.time() - start_time

                return {
                    'strategy_name': strategy_name,
                    'signals_count': len(signals),
                    'execution_time': execution_time,
                    'cache_hit': execution_info.get('cache_hit', False),
                    'success': True
                }
            except Exception as e:
                logger.error(f"并行执行策略失败 {strategy_name}: {e}")
                return {
                    'strategy_name': strategy_name,
                    'success': False,
                    'error': str(e)
                }

        # 使用线程池并行执行
        logger.info("  开始并行执行...")
        start_time = time.time()

        with ThreadPoolExecutor(os.cpu_count() * 2) as executor:
            futures = [executor.submit(execute_strategy, name)
                       for name in strategies.keys()]
            results = [future.result() for future in futures]

        total_time = time.time() - start_time
        logger.info(f"  并行执行完成，总耗时: {total_time:.3f} 秒")

        # 分析结果
        successful_count = sum(1 for r in results if r['success'])
        total_signals = sum(r.get('signals_count', 0)
                            for r in results if r['success'])

        logger.info(f"  成功执行: {successful_count}/{len(results)} 个策略")
        logger.info(f"  总信号数: {total_signals}")

        for result in results:
            if result['success']:
                logger.info(f"    {result['strategy_name']}: {result['signals_count']} 信号, "
                            f"{result['execution_time']:.3f}s, 缓存: {result['cache_hit']}")
            else:
                logger.error(
                    f"    {result['strategy_name']}: 执行失败 - {result['error']}")

        return successful_count > 0

    except Exception as e:
        logger.error(f"并行执行测试失败: {e}", exc_info=True)
        return False

def test_performance_evaluation():
    """测试性能评估"""
    logger = logger.bind(module=__name__)
    logger.info("\n4. 测试性能评估...")

    try:
        factory = get_strategy_factory()
        engine = get_strategy_engine()
        performance_evaluator = get_performance_evaluator()

        # 创建测试数据
        test_data = create_comprehensive_test_data()

        # 选择一个策略进行性能评估
        registry = get_strategy_registry()
        available_strategies = registry.list_strategies()

        if not available_strategies:
            logger.warning("没有可用策略进行性能评估")
            return True

        test_strategy_name = available_strategies[0]
        logger.info(f"性能评估策略: {test_strategy_name}")

        # 创建策略实例
        # 根据策略类型设置正确的参数
        strategy_params = {}
        if "MA策略" in test_strategy_name:
            strategy_params = {
                "short_period": 10,
                "long_period": 30,
                "min_confidence": 0.6
            }
        elif "MACD策略" in test_strategy_name:
            strategy_params = {
                "fast_period": 12,
                "slow_period": 26,
                "signal_period": 9,
                "min_confidence": 0.6
            }
        elif "RSI策略" in test_strategy_name:
            strategy_params = {
                "period": 14,
                "oversold": 30,
                "overbought": 70,
                "min_confidence": 0.6
            }
        elif "KDJ策略" in test_strategy_name:
            strategy_params = {
                "period": 9,
                "k_period": 3,
                "d_period": 3,
                "oversold": 20,
                "overbought": 80,
                "min_confidence": 0.6
            }
        elif "布林带策略" in test_strategy_name:
            strategy_params = {
                "period": 20,
                "std_dev": 2.0,
                "min_confidence": 0.6
            }
        else:
            # 默认参数
            strategy_params = {
                "min_confidence": 0.6
            }

        strategy = factory.create_strategy(
            strategy_name=test_strategy_name,
            instance_name=f"perf_test_{test_strategy_name}",
            **strategy_params
        )

        if not strategy:
            logger.error("策略实例创建失败")
            return False

        # 执行策略
        logger.info("  执行策略...")
        signals, execution_info = engine.execute_strategy(
            strategy_name=strategy.name,
            data=test_data,
            use_cache=False,
            save_to_db=True
        )

        logger.info(f"  生成信号: {len(signals)} 个")

        # 性能评估
        logger.info("  进行性能评估...")
        performance_result = performance_evaluator.evaluate_strategy_performance(
            signals=signals,
            price_data=test_data
        )

        if performance_result:
            logger.info("   性能评估完成")
            logger.info(f"    总收益率: {performance_result.total_return:.2%}")
            logger.info(f"    年化收益率: {performance_result.annual_return:.2%}")
            logger.info(f"    最大回撤: {performance_result.max_drawdown:.2%}")
            logger.info(f"    夏普比率: {performance_result.sharpe_ratio:.3f}")
            logger.info(f"    胜率: {performance_result.win_rate:.2%}")
        else:
            logger.warning("   性能评估失败")

        return True

    except Exception as e:
        logger.error(f"性能评估测试失败: {e}", exc_info=True)
        return False

def test_database_operations():
    """测试数据库操作"""
    logger = logger.bind(module=__name__)
    logger.info("\n5. 测试数据库操作...")

    try:
        db_manager = get_strategy_database_manager()
        factory = get_strategy_factory()

        # 数据库统计
        logger.info("  5.1 数据库统计...")
        db_stats = db_manager.get_database_stats()
        logger.info(f"    数据库统计: {db_stats}")

        # 列出数据库中的策略
        logger.info("  5.2 列出数据库策略...")
        db_strategies = db_manager.list_strategies()
        logger.info(f"    数据库策略数量: {len(db_strategies)}")

        for strategy_info in db_strategies[:5]:  # 显示前5个
            logger.info(
                f"      - {strategy_info['name']}: {strategy_info['description']}")

        # 批量加载策略
        logger.info("  5.3 批量加载策略...")
        loaded_strategies = factory.load_strategies_from_database(
            category="技术分析")
        logger.info(f"    加载策略数量: {len(loaded_strategies)}")

        # 测试策略导出
        logger.info("  5.4 测试策略导出...")
        if loaded_strategies:
            first_strategy_name = list(loaded_strategies.keys())[0]
            export_success = db_manager.export_strategy(
                first_strategy_name, f"export_{first_strategy_name}.json")
            if export_success:
                logger.info(f"     策略导出成功: {first_strategy_name}")
            else:
                logger.warning(f"     策略导出失败: {first_strategy_name}")

        return True

    except Exception as e:
        logger.error(f"数据库操作测试失败: {e}", exc_info=True)
        return False

def test_system_statistics():
    """测试系统统计"""
    logger = logger.bind(module=__name__)
    logger.info("\n6. 获取系统统计信息...")

    try:
        registry = get_strategy_registry()
        factory = get_strategy_factory()
        engine = get_strategy_engine()
        db_manager = get_strategy_database_manager()

        # 注册器统计
        registry_stats = registry.get_registry_stats()
        logger.info(f"  注册器统计: {registry_stats}")

        # 工厂统计
        factory_stats = factory.get_creation_stats()
        logger.info(f"  工厂统计: {factory_stats}")

        # 引擎统计
        engine_stats = engine.get_engine_stats()
        logger.info(f"  引擎统计: {engine_stats}")

        # 数据库统计
        db_stats = db_manager.get_database_stats()
        logger.info(f"  数据库统计: {db_stats}")

        # 系统配置
        config = get_config()
        strategy_config = config.get('strategy_system', {})
        logger.info(f"  系统配置: {strategy_config}")

        return True

    except Exception as e:
        logger.error(f"系统统计测试失败: {e}", exc_info=True)
        return False

def run_comprehensive_test():
    """运行全面测试"""
    logger = logger.bind(module=__name__)

    test_results = []

    # 测试项目列表
    tests = [
        ("系统初始化", test_system_initialization),
        ("策略生命周期", test_strategy_lifecycle),
        ("并行执行", test_parallel_execution),
        ("性能评估", test_performance_evaluation),
        ("数据库操作", test_database_operations),
        ("系统统计", test_system_statistics)
    ]

    start_time = time.time()

    for test_name, test_func in tests:
        logger.info(f"\n{'='*20} {test_name} {'='*20}")
        try:
            result = test_func()
            test_results.append((test_name, result))
            status = " 通过" if result else " 失败"
            logger.info(f"{test_name}: {status}")
        except Exception as e:
            logger.error(f"{test_name} 执行异常: {e}", exc_info=True)
            test_results.append((test_name, False))

    total_time = time.time() - start_time

    # 汇总结果
    logger.info("\n" + "="*80)
    logger.info("全面集成测试结果汇总")
    logger.info("="*80)

    passed_count = sum(1 for _, result in test_results if result)
    total_count = len(test_results)

    logger.info(f"测试总数: {total_count}")
    logger.info(f"通过数量: {passed_count}")
    logger.info(f"失败数量: {total_count - passed_count}")
    logger.info(f"通过率: {passed_count/total_count*100:.1f}%")
    logger.info(f"总耗时: {total_time:.2f} 秒")

    logger.info("\n详细结果:")
    for test_name, result in test_results:
        status = " 通过" if result else " 失败"
        logger.info(f"  {test_name}: {status}")

    return passed_count == total_count

if __name__ == "__main__":
    logger.info("HIkyuu策略管理系统全面集成测试")
    logger.info("="*80)

    success = run_comprehensive_test()

    if success:
        logger.info("\n 所有测试通过！策略管理系统运行正常。")
        sys.exit(0)
    else:
        logger.info("\n  部分测试失败，请检查日志了解详情。")
        sys.exit(1)
