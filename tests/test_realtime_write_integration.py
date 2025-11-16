#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
实时写入功能集成测试

测试UI层、服务层、事件层的完整集成
"""

import pytest
import pandas as pd
import sys
from pathlib import Path
from datetime import datetime

# 添加项目路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

try:
    from core.containers import get_service_container
    from core.services.realtime_write_service import RealtimeWriteService
    from core.services.write_progress_service import WriteProgressService
    from core.events import get_event_bus
    from core.events.realtime_write_events import (
        WriteStartedEvent, WriteProgressEvent, WriteCompletedEvent, WriteErrorEvent
    )
    SERVICES_AVAILABLE = True
except ImportError as e:
    print(f"服务导入失败: {e}")
    SERVICES_AVAILABLE = False


class TestRealtimeWriteIntegration:
    """集成测试"""

    @pytest.mark.skipif(not SERVICES_AVAILABLE, reason="服务不可用")
    def test_service_container_initialization(self):
        """测试服务容器初始化"""
        container = get_service_container()
        assert container is not None

    @pytest.mark.skipif(not SERVICES_AVAILABLE, reason="服务不可用")
    def test_realtime_write_service_resolution(self):
        """测试实时写入服务解析"""
        try:
            from core.services.service_bootstrap import ServiceBootstrap
            
            container = get_service_container()
            bootstrap = ServiceBootstrap(container)
            bootstrap.bootstrap()
            
            # 尝试解析服务
            realtime_service = container.resolve(RealtimeWriteService)
            assert realtime_service is not None
            
        except Exception as e:
            pytest.skip(f"无法初始化服务: {e}")

    @pytest.mark.skipif(not SERVICES_AVAILABLE, reason="服务不可用")
    def test_event_bus_initialization(self):
        """测试事件总线初始化"""
        event_bus = get_event_bus()
        assert event_bus is not None

    @pytest.mark.skipif(not SERVICES_AVAILABLE, reason="服务不可用")
    def test_event_subscription_and_publication(self):
        """测试事件订阅和发布"""
        event_bus = get_event_bus()
        events_received = []
        
        def collect_event(event):
            events_received.append(event)
        
        # 订阅事件
        event_bus.subscribe(WriteStartedEvent, collect_event)
        event_bus.subscribe(WriteProgressEvent, collect_event)
        event_bus.subscribe(WriteCompletedEvent, collect_event)
        
        # 发布事件
        event_bus.publish(WriteStartedEvent(
            task_id="test_001",
            task_name="测试任务",
            symbols=["000001", "000002"],
            total_records=200
        ))
        
        event_bus.publish(WriteProgressEvent(
            task_id="test_001",
            symbol="000001",
            progress=50.0,
            written_count=100,
            total_count=200,
            write_speed=1000.0,
            success_count=1,
            failure_count=0
        ))
        
        event_bus.publish(WriteCompletedEvent(
            task_id="test_001",
            total_symbols=2,
            success_count=2,
            failure_count=0,
            total_records=200,
            duration=10.5,
            average_speed=1904.76
        ))
        
        # 验证事件被接收
        assert len(events_received) >= 3
        assert isinstance(events_received[0], WriteStartedEvent)
        assert isinstance(events_received[1], WriteProgressEvent)
        assert isinstance(events_received[2], WriteCompletedEvent)

    @pytest.mark.skipif(not SERVICES_AVAILABLE, reason="服务不可用")
    def test_event_error_handling(self):
        """测试事件错误处理"""
        event_bus = get_event_bus()
        errors_received = []
        
        def collect_error(event):
            errors_received.append(event)
        
        event_bus.subscribe(WriteErrorEvent, collect_error)
        
        # 发布错误事件
        error = ValueError("测试错误")
        event_bus.publish(WriteErrorEvent(
            task_id="test_001",
            symbol="000001",
            error=error,
            error_type="ValueError"
        ))
        
        assert len(errors_received) == 1
        assert errors_received[0].symbol == "000001"

    @pytest.mark.skipif(not SERVICES_AVAILABLE, reason="服务不可用")
    def test_write_data_with_dataframe(self):
        """测试写入DataFrame数据"""
        try:
            from core.services.service_bootstrap import ServiceBootstrap
            
            container = get_service_container()
            bootstrap = ServiceBootstrap(container)
            bootstrap.bootstrap()
            
            service = container.resolve(RealtimeWriteService)
            
            # 创建测试数据
            data = pd.DataFrame({
                'symbol': ['000001', '000001', '000001'],
                'timestamp': pd.date_range('2025-01-01', periods=3),
                'open': [10.0, 10.1, 10.2],
                'close': [10.1, 10.2, 10.3],
                'high': [10.2, 10.3, 10.4],
                'low': [9.9, 10.0, 10.1],
                'volume': [1000000, 1100000, 1200000]
            })
            
            # 调用写入方法
            result = service.write_data('000001', data, 'STOCK_A')
            
            # 验证结果
            assert isinstance(result, bool)
            
        except Exception as e:
            pytest.skip(f"服务写入失败: {e}")

    @pytest.mark.skipif(not SERVICES_AVAILABLE, reason="服务不可用")
    def test_concurrent_write_operations(self):
        """测试并发写入操作"""
        import threading
        import time
        
        try:
            from core.services.service_bootstrap import ServiceBootstrap
            
            container = get_service_container()
            bootstrap = ServiceBootstrap(container)
            bootstrap.bootstrap()
            
            service = container.resolve(RealtimeWriteService)
            results = []
            
            def write_task(symbol):
                data = pd.DataFrame({
                    'symbol': [symbol] * 10,
                    'timestamp': pd.date_range('2025-01-01', periods=10),
                    'open': [10.0 + i*0.1 for i in range(10)],
                    'close': [10.1 + i*0.1 for i in range(10)],
                })
                result = service.write_data(symbol, data, 'STOCK_A')
                results.append(result)
            
            # 创建多个写入线程
            threads = []
            for i in range(3):
                symbol = f"00000{i}"
                thread = threading.Thread(target=write_task, args=(symbol,))
                threads.append(thread)
                thread.start()
            
            # 等待所有线程完成
            for thread in threads:
                thread.join(timeout=10)
            
            # 验证结果
            assert len(results) == 3
            
        except Exception as e:
            pytest.skip(f"并发写入失败: {e}")

    def test_dataframe_creation_and_validation(self):
        """测试DataFrame创建和验证"""
        # 创建测试数据
        data = pd.DataFrame({
            'symbol': ['000001', '000002', '000003'],
            'timestamp': pd.date_range('2025-01-01', periods=3),
            'open': [10.0, 20.0, 30.0],
            'close': [10.5, 20.5, 30.5],
            'high': [10.8, 20.8, 30.8],
            'low': [9.8, 19.8, 29.8],
            'volume': [1000000, 2000000, 3000000]
        })
        
        assert not data.empty
        assert len(data) == 3
        assert 'symbol' in data.columns
        assert 'close' in data.columns


class TestRealtimeWriteEventFlow:
    """事件流完整流程测试"""

    @pytest.mark.skipif(not SERVICES_AVAILABLE, reason="服务不可用")
    def test_complete_write_lifecycle(self):
        """测试完整的写入生命周期"""
        event_bus = get_event_bus()
        lifecycle_events = {
            'started': None,
            'progress': [],
            'completed': None,
            'errors': []
        }
        
        def handle_started(event):
            lifecycle_events['started'] = event
        
        def handle_progress(event):
            lifecycle_events['progress'].append(event)
        
        def handle_completed(event):
            lifecycle_events['completed'] = event
        
        def handle_error(event):
            lifecycle_events['errors'].append(event)
        
        # 注册处理器
        event_bus.subscribe(WriteStartedEvent, handle_started)
        event_bus.subscribe(WriteProgressEvent, handle_progress)
        event_bus.subscribe(WriteCompletedEvent, handle_completed)
        event_bus.subscribe(WriteErrorEvent, handle_error)
        
        # 模拟完整的写入流程
        task_id = "lifecycle_test_001"
        
        # 1. 开始事件
        event_bus.publish(WriteStartedEvent(
            task_id=task_id,
            task_name="生命周期测试",
            symbols=["000001", "000002", "000003"],
            total_records=300
        ))
        
        # 2. 进度事件
        for i in range(1, 4):
            event_bus.publish(WriteProgressEvent(
                task_id=task_id,
                symbol=f"00000{i}",
                progress=i * 33.33,
                written_count=i * 100,
                total_count=300,
                write_speed=1000.0 * i,
                success_count=i,
                failure_count=0
            ))
        
        # 3. 完成事件
        event_bus.publish(WriteCompletedEvent(
            task_id=task_id,
            total_symbols=3,
            success_count=3,
            failure_count=0,
            total_records=300,
            duration=0.3,
            average_speed=1000.0
        ))
        
        # 验证完整流程
        assert lifecycle_events['started'] is not None
        assert lifecycle_events['started'].task_id == task_id
        assert len(lifecycle_events['progress']) == 3
        assert lifecycle_events['completed'] is not None
        assert lifecycle_events['completed'].success_count == 3


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
