#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FactorWeave-Quant 性能监控中心高频交易环境性能测试脚本
"""

import sys
import time
import threading
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Any
import random
import uuid
from concurrent.futures import ThreadPoolExecutor
from loguru import logger

# 添加项目路径
sys.path.append('.')


def test_risk_monitoring_performance():
    """测试风险监控性能"""
    logger.info("开始风险监控性能测试...")

    try:
        from gui.widgets.performance.tabs.risk_control_center_tab import ModernRiskControlCenterTab
        from db.models.performance_history_models import get_performance_history_manager, RiskHistoryRecord

        # 创建风险控制标签页
        risk_tab = ModernRiskControlCenterTab()
        history_manager = get_performance_history_manager()

        # 模拟高频风险数据更新
        test_duration = 60  # 测试60秒
        update_interval = 0.1  # 每100ms更新一次
        total_updates = int(test_duration / update_interval)

        start_time = time.time()
        update_count = 0

        logger.info(f"开始高频风险数据更新测试: {total_updates}次更新，间隔{update_interval}秒")

        for i in range(total_updates):
            # 生成模拟风险数据
            risk_metrics = {
                'VaR(95%)': random.uniform(1.0, 5.0),
                '最大回撤': random.uniform(5.0, 15.0),
                '波动率': random.uniform(10.0, 25.0),
                'Beta系数': random.uniform(0.8, 1.2),
                '夏普比率': random.uniform(0.5, 2.5),
                '仓位风险': random.uniform(30.0, 80.0),
                '市场风险': random.uniform(20.0, 60.0),
                '行业风险': random.uniform(15.0, 45.0),
                '流动性风险': random.uniform(10.0, 40.0),
                '信用风险': random.uniform(5.0, 30.0),
                '操作风险': random.uniform(5.0, 25.0),
                '集中度风险': random.uniform(20.0, 50.0)
            }

            # 更新风险数据
            update_start = time.time()
            risk_tab.update_risk_data(risk_metrics)
            update_duration = time.time() - update_start

            update_count += 1

            # 每100次更新输出一次进度
            if update_count % 100 == 0:
                logger.info(f"风险监控更新进度: {update_count}/{total_updates}, 平均耗时: {update_duration*1000:.2f}ms")

            # 控制更新频率
            time.sleep(update_interval)

        total_time = time.time() - start_time
        avg_update_time = total_time / total_updates

        logger.info(f"风险监控性能测试完成:")
        logger.info(f"  总更新次数: {update_count}")
        logger.info(f"  总耗时: {total_time:.2f}秒")
        logger.info(f"  平均更新耗时: {avg_update_time*1000:.2f}ms")
        logger.info(f"  更新频率: {update_count/total_time:.2f} updates/sec")

        return {
            'total_updates': update_count,
            'total_time': total_time,
            'avg_update_time': avg_update_time,
            'update_rate': update_count / total_time
        }

    except Exception as e:
        logger.error(f"风险监控性能测试失败: {e}")
        return None


def test_execution_monitoring_performance():
    """测试执行监控性能"""
    logger.info("开始执行监控性能测试...")

    try:
        from gui.widgets.performance.tabs.trading_execution_monitor_tab import ModernTradingExecutionMonitorTab
        from db.models.performance_history_models import get_performance_history_manager, ExecutionHistoryRecord

        # 创建执行监控标签页
        execution_tab = ModernTradingExecutionMonitorTab()
        history_manager = get_performance_history_manager()

        # 模拟高频订单数据
        test_duration = 30  # 测试30秒
        order_interval = 0.05  # 每50ms一个订单
        total_orders = int(test_duration / order_interval)

        start_time = time.time()
        order_count = 0

        logger.info(f"开始高频订单处理测试: {total_orders}个订单，间隔{order_interval}秒")

        symbols = ['000001', '000002', '600000', '600036', '000858']

        for i in range(total_orders):
            # 生成模拟订单数据
            order_data = {
                'time': datetime.now().strftime('%H:%M:%S'),
                'order_id': str(uuid.uuid4())[:8],
                'symbol': random.choice(symbols),
                'direction': random.choice(['buy', 'sell']),
                'quantity': random.randint(100, 10000),
                'order_price': random.uniform(10.0, 50.0),
                'price': random.uniform(10.0, 50.0),
                'status': random.choice(['filled', 'partial', 'cancelled']),
                'latency': random.uniform(5.0, 100.0),
                'slippage': random.uniform(-0.5, 0.5),
                'cost': random.uniform(0.01, 0.1),
                'market_impact': random.uniform(0.0, 0.2)
            }

            # 处理订单
            order_start = time.time()
            execution_tab.add_realtime_order(order_data)
            execution_tab.save_execution_record(order_data)
            order_duration = time.time() - order_start

            order_count += 1

            # 每50个订单输出一次进度
            if order_count % 50 == 0:
                logger.info(f"执行监控处理进度: {order_count}/{total_orders}, 平均耗时: {order_duration*1000:.2f}ms")

            # 控制订单频率
            time.sleep(order_interval)

        total_time = time.time() - start_time
        avg_order_time = total_time / total_orders

        logger.info(f"执行监控性能测试完成:")
        logger.info(f"  总订单数: {order_count}")
        logger.info(f"  总耗时: {total_time:.2f}秒")
        logger.info(f"  平均处理耗时: {avg_order_time*1000:.2f}ms")
        logger.info(f"  处理频率: {order_count/total_time:.2f} orders/sec")

        return {
            'total_orders': order_count,
            'total_time': total_time,
            'avg_order_time': avg_order_time,
            'order_rate': order_count / total_time
        }

    except Exception as e:
        logger.error(f"执行监控性能测试失败: {e}")
        return None


def test_data_quality_monitoring_performance():
    """测试数据质量监控性能"""
    logger.info("开始数据质量监控性能测试...")

    try:
        from gui.widgets.performance.tabs.data_quality_monitor_tab import ModernDataQualityMonitorTab

        # 创建数据质量监控标签页
        quality_tab = ModernDataQualityMonitorTab()

        # 模拟数据质量检查
        test_duration = 30  # 测试30秒
        check_interval = 0.2  # 每200ms检查一次
        total_checks = int(test_duration / check_interval)

        start_time = time.time()
        check_count = 0

        logger.info(f"开始数据质量检查测试: {total_checks}次检查，间隔{check_interval}秒")

        for i in range(total_checks):
            # 生成模拟质量数据
            quality_metrics = {
                '数据完整性': random.uniform(90.0, 99.5),
                '数据及时性': random.uniform(85.0, 98.0),
                '数据准确性': random.uniform(95.0, 99.9),
                '数据一致性': random.uniform(90.0, 98.5),
                '连接稳定性': random.uniform(88.0, 99.0),
                '延迟水平': random.uniform(10.0, 50.0),
                '缺失率': random.uniform(0.0, 5.0),
                '异常率': random.uniform(0.0, 3.0),
                '重复率': random.uniform(0.0, 2.0),
                '更新频率': random.uniform(95.0, 99.8),
                '网络质量': random.uniform(85.0, 98.0),
                '数据新鲜度': random.uniform(90.0, 99.0)
            }

            # 更新质量数据
            check_start = time.time()
            quality_tab.update_data({'quality_metrics': quality_metrics})
            check_duration = time.time() - check_start

            check_count += 1

            # 每25次检查输出一次进度
            if check_count % 25 == 0:
                logger.info(f"数据质量检查进度: {check_count}/{total_checks}, 平均耗时: {check_duration*1000:.2f}ms")

            # 控制检查频率
            time.sleep(check_interval)

        total_time = time.time() - start_time
        avg_check_time = total_time / total_checks

        logger.info(f"数据质量监控性能测试完成:")
        logger.info(f"  总检查次数: {check_count}")
        logger.info(f"  总耗时: {total_time:.2f}秒")
        logger.info(f"  平均检查耗时: {avg_check_time*1000:.2f}ms")
        logger.info(f"  检查频率: {check_count/total_time:.2f} checks/sec")

        return {
            'total_checks': check_count,
            'total_time': total_time,
            'avg_check_time': avg_check_time,
            'check_rate': check_count / total_time
        }

    except Exception as e:
        logger.error(f"数据质量监控性能测试失败: {e}")
        return None


def test_database_performance():
    """测试数据库性能"""
    logger.info("开始数据库性能测试...")

    try:
        from db.models.performance_history_models import get_performance_history_manager, RiskHistoryRecord, ExecutionHistoryRecord

        history_manager = get_performance_history_manager()

        # 测试批量插入性能
        batch_size = 1000
        logger.info(f"测试批量插入{batch_size}条风险记录...")

        start_time = time.time()

        for i in range(batch_size):
            record = RiskHistoryRecord(
                timestamp=datetime.now() - timedelta(minutes=i),
                symbol=f"TEST{i%10:03d}",
                var_95=random.uniform(1.0, 5.0),
                max_drawdown=random.uniform(5.0, 15.0),
                volatility=random.uniform(10.0, 25.0),
                beta=random.uniform(0.8, 1.2),
                sharpe_ratio=random.uniform(0.5, 2.5),
                position_risk=random.uniform(30.0, 80.0),
                market_risk=random.uniform(20.0, 60.0),
                sector_risk=random.uniform(15.0, 45.0),
                liquidity_risk=random.uniform(10.0, 40.0),
                credit_risk=random.uniform(5.0, 30.0),
                operational_risk=random.uniform(5.0, 25.0),
                concentration_risk=random.uniform(20.0, 50.0),
                overall_risk_score=random.uniform(20.0, 80.0),
                risk_level="测试风险",
                portfolio_value=random.uniform(100000, 1000000)
            )

            history_manager.save_risk_record(record)

        insert_time = time.time() - start_time

        # 测试查询性能
        logger.info("测试查询性能...")
        query_start = time.time()

        records = history_manager.get_risk_history(limit=500)

        query_time = time.time() - query_start

        # 测试统计性能
        logger.info("测试统计性能...")
        stats_start = time.time()

        stats = history_manager.get_risk_statistics(days=7)

        stats_time = time.time() - stats_start

        logger.info(f"数据库性能测试完成:")
        logger.info(f"  批量插入{batch_size}条记录耗时: {insert_time:.2f}秒")
        logger.info(f"  平均插入耗时: {insert_time/batch_size*1000:.2f}ms/record")
        logger.info(f"  查询{len(records)}条记录耗时: {query_time*1000:.2f}ms")
        logger.info(f"  统计计算耗时: {stats_time*1000:.2f}ms")

        return {
            'insert_time': insert_time,
            'avg_insert_time': insert_time / batch_size,
            'query_time': query_time,
            'stats_time': stats_time,
            'records_count': len(records)
        }

    except Exception as e:
        logger.error(f"数据库性能测试失败: {e}")
        return None


def run_comprehensive_performance_test():
    """运行综合性能测试"""
    logger.info("=" * 60)
    logger.info("FactorWeave-Quant 性能监控中心综合性能测试开始")
    logger.info("=" * 60)

    results = {}

    # 1. 风险监控性能测试
    logger.info("\n1. 风险监控性能测试")
    logger.info("-" * 40)
    results['risk_monitoring'] = test_risk_monitoring_performance()

    # 2. 执行监控性能测试
    logger.info("\n2. 执行监控性能测试")
    logger.info("-" * 40)
    results['execution_monitoring'] = test_execution_monitoring_performance()

    # 3. 数据质量监控性能测试
    logger.info("\n3. 数据质量监控性能测试")
    logger.info("-" * 40)
    results['data_quality_monitoring'] = test_data_quality_monitoring_performance()

    # 4. 数据库性能测试
    logger.info("\n4. 数据库性能测试")
    logger.info("-" * 40)
    results['database'] = test_database_performance()

    # 输出综合测试结果
    logger.info("\n" + "=" * 60)
    logger.info("综合性能测试结果汇总")
    logger.info("=" * 60)

    for test_name, result in results.items():
        if result:
            logger.info(f"\n{test_name.upper()}:")
            for key, value in result.items():
                if isinstance(value, float):
                    if 'time' in key:
                        logger.info(f"  {key}: {value:.3f}s")
                    elif 'rate' in key:
                        logger.info(f"  {key}: {value:.2f}/sec")
                    else:
                        logger.info(f"  {key}: {value:.3f}")
                else:
                    logger.info(f"  {key}: {value}")
        else:
            logger.error(f"{test_name.upper()}: 测试失败")

    logger.info("\n" + "=" * 60)
    logger.info("性能测试完成")
    logger.info("=" * 60)

    return results


if __name__ == "__main__":
    # 配置日志
    logger.remove()
    logger.add(
        sys.stdout,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        level="INFO"
    )

    # 运行性能测试
    try:
        results = run_comprehensive_performance_test()

        # 保存测试结果
        import json
        with open(f"performance_test_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json", 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False, default=str)

        logger.info("测试结果已保存到文件")

    except Exception as e:
        logger.error(f"性能测试执行失败: {e}")
        import traceback
        traceback.print_exc()
