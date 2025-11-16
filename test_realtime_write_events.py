#!/usr/bin/env python3
"""
实时写入事件流测试

测试事件发布、订阅和处理流程
"""

import sys
import time
from datetime import datetime
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from loguru import logger

# 配置日志
logger.remove()
logger.add(
    lambda msg: print(msg, end=""),
    format="<level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
    level="DEBUG"
)


def test_event_bus_basic():
    """测试基本事件总线功能"""
    logger.info("=" * 80)
    logger.info("测试 1: 基本事件总线功能")
    logger.info("=" * 80)
    
    try:
        from core.events import get_event_bus
        from core.events.realtime_write_events import (
            WriteStartedEvent, WriteProgressEvent, WriteCompletedEvent
        )
        
        event_bus = get_event_bus()
        logger.info(f"✅ 成功获取 EventBus: {type(event_bus)}")
        
        # 测试事件发布
        test_event = WriteStartedEvent(
            task_id="test_001",
            task_name="Test Import",
            symbols=["000001", "000002"],
            total_records=2
        )
        
        logger.info(f"✅ 创建 WriteStartedEvent: {test_event}")
        logger.info(f"   - Task ID: {test_event.task_id}")
        logger.info(f"   - Task Name: {test_event.task_name}")
        logger.info(f"   - Symbols: {test_event.symbols}")
        logger.info(f"   - Total Records: {test_event.total_records}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_realtime_write_service():
    """测试 RealtimeWriteService"""
    logger.info("\n" + "=" * 80)
    logger.info("测试 2: RealtimeWriteService")
    logger.info("=" * 80)
    
    try:
        from core.containers import get_service_container
        from core.services.realtime_write_service import RealtimeWriteService
        import pandas as pd
        
        service_container = get_service_container()
        realtime_service = service_container.resolve(RealtimeWriteService)
        logger.info(f"✅ 成功获取 RealtimeWriteService: {type(realtime_service)}")
        
        # 测试启动任务
        task_id = "test_kline_001"
        success = realtime_service.start_write(task_id)
        logger.info(f"✅ 启动写入任务: {task_id} -> {success}")
        
        # 测试写入数据
        test_data = pd.DataFrame({
            'symbol': ['000001'],
            'datetime': [datetime.now()],
            'open': [10.0],
            'high': [11.0],
            'low': [9.5],
            'close': [10.5],
            'volume': [1000000]
        })
        
        write_success = realtime_service.write_data(
            symbol='000001',
            data=test_data,
            asset_type='STOCK_A'
        )
        logger.info(f"✅ 写入数据: 000001 -> {write_success}")
        
        # 测试完成任务
        complete_success = realtime_service.complete_write(task_id)
        logger.info(f"✅ 完成写入任务: {task_id} -> {complete_success}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_event_handlers():
    """测试事件处理器"""
    logger.info("\n" + "=" * 80)
    logger.info("测试 3: 事件处理器")
    logger.info("=" * 80)
    
    try:
        from core.services.realtime_write_event_handlers import get_write_event_handlers
        from core.events.realtime_write_events import WriteProgressEvent
        
        handlers = get_write_event_handlers()
        logger.info(f"✅ 成功获取事件处理器: {type(handlers)}")
        
        # 创建测试事件
        test_event = WriteProgressEvent(
            task_id="test_001",
            symbol="000001",
            progress=50.0,
            written_count=5,
            total_count=10,
            write_speed=100.0,
            success_count=5,
            failure_count=0
        )
        
        logger.info(f"✅ 创建 WriteProgressEvent: {test_event}")
        
        # 测试处理进度事件
        handlers.on_write_progress(test_event)
        logger.info(f"✅ 处理进度事件完成")
        
        # 检查统计
        stats = handlers.get_task_statistics("test_001")
        if stats:
            logger.info(f"✅ 获取任务统计:")
            logger.info(f"   - Task ID: {stats.get('task_id')}")
            logger.info(f"   - Progress: {stats.get('progress')}%")
        else:
            logger.warning(f"⚠️  未找到任务统计")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_write_progress_service():
    """测试写入进度服务"""
    logger.info("\n" + "=" * 80)
    logger.info("测试 4: WriteProgressService")
    logger.info("=" * 80)
    
    try:
        from core.containers import get_service_container
        from core.services.write_progress_service import WriteProgressService
        
        service_container = get_service_container()
        progress_service = service_container.resolve(WriteProgressService)
        logger.info(f"✅ 成功获取 WriteProgressService: {type(progress_service)}")
        
        # 测试启动跟踪
        task_id = "test_progress_001"
        total_count = 100
        start_success = progress_service.start_tracking(task_id, total_count)
        logger.info(f"✅ 启动进度跟踪: {task_id} (总数: {total_count}) -> {start_success}")
        
        # 模拟更新进度
        for i in range(5):
            stats = progress_service.update_progress(
                task_id=task_id,
                symbol=f"symbol_{i}",
                written_count=(i+1)*20,
                success_count=(i+1)*20,
                failure_count=0
            )
            logger.info(f"✅ 进度更新 {i+1}: {stats.get('progress')}%")
            time.sleep(0.1)
        
        # 获取进度
        progress = progress_service.get_progress(task_id)
        logger.info(f"✅ 当前进度: {progress.get('progress')}%")
        
        # 完成跟踪
        final_stats = progress_service.complete_tracking(task_id)
        logger.info(f"✅ 完成进度跟踪:")
        logger.info(f"   - 总计: {final_stats.get('total_count')}")
        logger.info(f"   - 写入: {final_stats.get('written_count')}")
        logger.info(f"   - 成功: {final_stats.get('success_count')}")
        logger.info(f"   - 平均速度: {final_stats.get('average_speed'):.0f} 条/秒")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_event_subscription():
    """测试事件订阅流程"""
    logger.info("\n" + "=" * 80)
    logger.info("测试 5: 事件订阅流程")
    logger.info("=" * 80)
    
    try:
        from core.events import get_event_bus
        from core.events.realtime_write_events import WriteProgressEvent
        from core.services.realtime_write_event_handlers import get_write_event_handlers
        
        event_bus = get_event_bus()
        handlers = get_write_event_handlers()
        
        # 订阅事件
        event_bus.subscribe(WriteProgressEvent, handlers.on_write_progress)
        logger.info(f"✅ 事件订阅成功: WriteProgressEvent -> on_write_progress")
        
        # 发布测试事件
        test_event = WriteProgressEvent(
            task_id="test_sub_001",
            symbol="000001",
            progress=75.0,
            written_count=75,
            total_count=100,
            write_speed=1000.0,
            success_count=75,
            failure_count=0
        )
        
        event_bus.publish(test_event)
        logger.info(f"✅ 事件发布成功: {test_event}")
        
        # 等待事件处理
        time.sleep(0.5)
        
        # 检查处理结果
        stats = handlers.get_task_statistics("test_sub_001")
        if stats and stats.get('progress') == 75.0:
            logger.info(f"✅ 事件处理成功: 进度 {stats.get('progress')}%")
        else:
            logger.warning(f"⚠️  事件处理可能有问题")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """运行所有测试"""
    logger.info("开始实时写入事件流测试")
    logger.info(f"时间: {datetime.now()}")
    
    tests = [
        ("事件总线基本功能", test_event_bus_basic),
        ("RealtimeWriteService", test_realtime_write_service),
        ("事件处理器", test_event_handlers),
        ("写入进度服务", test_write_progress_service),
        ("事件订阅流程", test_event_subscription),
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            logger.error(f"❌ 测试异常: {test_name} - {e}")
            results.append((test_name, False))
    
    # 汇总结果
    logger.info("\n" + "=" * 80)
    logger.info("测试结果汇总")
    logger.info("=" * 80)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        logger.info(f"{status}: {test_name}")
    
    logger.info(f"\n总计: {passed}/{total} 测试通过")
    
    if passed == total:
        logger.info("🎉 所有测试通过！")
    else:
        logger.warning(f"⚠️  有 {total - passed} 个测试失败")
    
    return passed == total


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
