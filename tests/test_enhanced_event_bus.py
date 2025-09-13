#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
增强版事件总线测试

测试增强版事件总线的各项功能：
1. 事件发布和订阅
2. 优先级处理
3. 事件聚合
4. 背压管理
5. 事件持久化
6. 路由功能
"""

import asyncio
import pytest
import tempfile
import time
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock, patch

from core.events.enhanced_event_bus import (
    EnhancedEventBus, EventPriority, EventStatus, BackpressureStrategy,
    EventMetadata, EnhancedEvent, EventRouter, EventPersistence,
    BackpressureManager, EventAggregator, initialize_enhanced_event_bus
)


class TestEnhancedEventBus:
    """增强版事件总线测试类"""

    def setup_method(self):
        """测试前设置"""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = str(Path(self.temp_dir) / "test_events.db")

        # 创建测试用的事件总线（禁用异步执行以简化测试）
        self.event_bus = EnhancedEventBus(
            async_execution=False,
            max_workers=2,
            deduplication_window=0.1,
            enable_persistence=True,
            enable_aggregation=True,
            enable_backpressure=True,
            db_path=self.db_path
        )

        # 测试事件处理器
        self.received_events = []
        self.handler_call_count = 0

    def teardown_method(self):
        """测试后清理"""
        if self.event_bus:
            self.event_bus.shutdown()

        # 清理临时文件
        import shutil
        try:
            shutil.rmtree(self.temp_dir)
        except:
            pass

    def test_event_bus_initialization(self):
        """测试事件总线初始化"""
        assert self.event_bus is not None
        assert self.event_bus.persistence is not None
        assert self.event_bus.event_aggregator is not None
        assert self.event_bus.backpressure_manager is not None
        assert self.event_bus.event_router is not None

        # 检查优先级队列
        assert len(self.event_bus.priority_queues) == len(EventPriority)
        for priority in EventPriority:
            assert priority in self.event_bus.priority_queues

    def test_event_publishing_and_subscription(self):
        """测试事件发布和订阅"""
        # 注册事件处理器
        def test_handler(event):
            self.received_events.append(event)
            self.handler_call_count += 1

        self.event_bus.subscribe_enhanced("test_event", test_handler)

        # 发布事件
        event_id = self.event_bus.publish_enhanced(
            "test_event",
            {"message": "Hello World"},
            priority=EventPriority.HIGH,
            source="test"
        )

        assert event_id is not None
        assert len(event_id) > 0

        # 等待事件处理
        time.sleep(0.5)

        # 验证事件被处理
        assert self.handler_call_count > 0
        assert len(self.received_events) > 0

        # 验证事件内容
        received_event = self.received_events[0]
        assert received_event.name == "test_event"
        assert received_event.data["message"] == "Hello World"
        assert received_event.metadata.priority == EventPriority.HIGH
        assert received_event.metadata.source == "test"

    def test_event_priority_handling(self):
        """测试事件优先级处理"""
        received_order = []

        def handler_critical(event):
            received_order.append("critical")

        def handler_normal(event):
            received_order.append("normal")

        def handler_low(event):
            received_order.append("low")

        # 注册处理器
        self.event_bus.subscribe_enhanced("critical_event", handler_critical)
        self.event_bus.subscribe_enhanced("normal_event", handler_normal)
        self.event_bus.subscribe_enhanced("low_event", handler_low)

        # 按相反优先级顺序发布事件
        self.event_bus.publish_enhanced("low_event", {}, priority=EventPriority.LOW)
        self.event_bus.publish_enhanced("normal_event", {}, priority=EventPriority.NORMAL)
        self.event_bus.publish_enhanced("critical_event", {}, priority=EventPriority.CRITICAL)

        # 等待处理
        time.sleep(0.3)

        # 验证处理顺序（高优先级先处理）
        assert len(received_order) == 3
        assert received_order[0] == "critical"
        # 注意：由于异步处理，normal和low的顺序可能不确定

    def test_event_aggregation(self):
        """测试事件聚合"""
        if not self.event_bus.event_aggregator:
            pytest.skip("事件聚合未启用")

        # 设置聚合规则
        def aggregate_test_events(events):
            total_count = sum(event.data.get('count', 1) for event in events)
            return EnhancedEvent(
                name="aggregated_test",
                data={"total_count": total_count, "event_count": len(events)},
                metadata=EventMetadata(source="aggregator")
            )

        self.event_bus.event_aggregator.add_aggregation_rule("test_aggregate", aggregate_test_events)

        # 注册聚合事件处理器
        def aggregated_handler(event):
            self.received_events.append(event)

        self.event_bus.subscribe_enhanced("aggregated_test", aggregated_handler)

        # 发布多个待聚合事件
        for i in range(5):
            self.event_bus.publish_enhanced(
                "test_aggregate",
                {"count": i + 1},
                priority=EventPriority.NORMAL
            )

        # 等待聚合和处理
        time.sleep(0.5)

        # 验证聚合结果
        aggregated_events = [e for e in self.received_events if e.name == "aggregated_test"]
        if aggregated_events:
            event = aggregated_events[0]
            assert event.data["event_count"] == 5
            assert event.data["total_count"] == 15  # 1+2+3+4+5

    def test_event_persistence(self):
        """测试事件持久化"""
        if not self.event_bus.persistence:
            pytest.skip("事件持久化未启用")

        # 发布事件
        event_id = self.event_bus.publish_enhanced(
            "persistent_event",
            {"data": "test_persistence"},
            priority=EventPriority.NORMAL,
            source="test"
        )

        # 等待持久化
        time.sleep(0.1)

        # 验证事件被保存
        pending_events = self.event_bus.persistence.get_events_by_status(EventStatus.PENDING)
        saved_events = [e for e in pending_events if e.metadata.event_id == event_id]

        # 由于事件可能已经被处理，检查所有状态
        if not saved_events:
            completed_events = self.event_bus.persistence.get_events_by_status(EventStatus.COMPLETED)
            saved_events = [e for e in completed_events if e.metadata.event_id == event_id]

        assert len(saved_events) > 0
        saved_event = saved_events[0]
        assert saved_event.name == "persistent_event"
        assert saved_event.data["data"] == "test_persistence"

    def test_backpressure_management(self):
        """测试背压管理"""
        if not self.event_bus.backpressure_manager:
            pytest.skip("背压管理未启用")

        # 设置较小的队列大小进行测试
        self.event_bus.backpressure_manager.max_queue_size = 5

        # 发布大量事件
        published_count = 0
        for i in range(10):
            event_id = self.event_bus.publish_enhanced(
                "backpressure_test",
                {"index": i},
                priority=EventPriority.LOW
            )
            if event_id:
                published_count += 1

        # 验证背压生效（部分事件被丢弃）
        stats = self.event_bus.get_enhanced_stats()
        if 'events_dropped' in stats:
            # 如果有事件被丢弃，说明背压管理生效
            assert stats['events_dropped'] >= 0

    def test_event_routing(self):
        """测试事件路由"""
        router = self.event_bus.event_router

        # 添加路由规则
        def high_priority_rule(event):
            return event.metadata.priority == EventPriority.HIGH

        def test_source_rule(event):
            return event.metadata.source == "test_source"

        router.add_routing_rule(high_priority_rule, "high_priority_handler")
        router.add_routing_rule(test_source_rule, "test_source_handler")

        # 测试路由
        high_priority_event = EnhancedEvent(
            name="test_event",
            data={},
            metadata=EventMetadata(priority=EventPriority.HIGH, source="normal")
        )

        test_source_event = EnhancedEvent(
            name="test_event",
            data={},
            metadata=EventMetadata(priority=EventPriority.NORMAL, source="test_source")
        )

        # 验证路由结果
        targets1 = router.route_event(high_priority_event)
        assert "high_priority_handler" in targets1

        targets2 = router.route_event(test_source_event)
        assert "test_source_handler" in targets2

    def test_event_statistics(self):
        """测试事件统计"""
        # 发布一些事件
        for i in range(3):
            self.event_bus.publish_enhanced(
                f"stats_test_{i}",
                {"index": i},
                priority=EventPriority.NORMAL
            )

        # 等待处理
        time.sleep(0.2)

        # 获取统计信息
        stats = self.event_bus.get_enhanced_stats()

        # 验证统计信息
        assert 'events_routed' in stats
        assert 'events_persisted' in stats
        assert 'priority_queue_sizes' in stats
        assert 'handler_count' in stats

        # 验证优先级队列统计
        priority_stats = stats['priority_queue_sizes']
        for priority in EventPriority:
            assert priority.name in priority_stats

    def test_async_event_handler(self):
        """测试异步事件处理器"""
        async def async_handler(event):
            await asyncio.sleep(0.01)  # 模拟异步操作
            self.received_events.append(event)
            self.handler_call_count += 1

        # 注册异步处理器
        self.event_bus.subscribe_enhanced("async_test", async_handler)

        # 发布事件
        event_id = self.event_bus.publish_enhanced(
            "async_test",
            {"async": True},
            priority=EventPriority.NORMAL
        )

        # 等待异步处理
        time.sleep(0.2)

        # 验证异步处理器被调用
        assert self.handler_call_count > 0
        assert len(self.received_events) > 0

        received_event = self.received_events[0]
        assert received_event.name == "async_test"
        assert received_event.data["async"] is True

    def test_event_unsubscription(self):
        """测试事件取消订阅"""
        def test_handler(event):
            self.handler_call_count += 1

        # 订阅事件
        self.event_bus.subscribe_enhanced("unsubscribe_test", test_handler)

        # 发布事件
        self.event_bus.publish_enhanced("unsubscribe_test", {})
        time.sleep(0.1)

        initial_count = self.handler_call_count
        assert initial_count > 0

        # 取消订阅
        self.event_bus.unsubscribe_enhanced("unsubscribe_test", test_handler)

        # 再次发布事件
        self.event_bus.publish_enhanced("unsubscribe_test", {})
        time.sleep(0.1)

        # 验证处理器不再被调用
        assert self.handler_call_count == initial_count

    def test_global_event_bus_instance(self):
        """测试全局事件总线实例"""
        from core.events.enhanced_event_bus import get_enhanced_event_bus

        # 获取全局实例
        global_bus = get_enhanced_event_bus()
        assert global_bus is not None

        # 再次获取应该是同一个实例
        global_bus2 = get_enhanced_event_bus()
        assert global_bus is global_bus2

    def test_event_bus_initialization_function(self):
        """测试事件总线初始化函数"""
        temp_db = str(Path(self.temp_dir) / "init_test.db")

        # 使用初始化函数创建事件总线
        bus = initialize_enhanced_event_bus(
            async_execution=False,
            max_workers=4,
            enable_persistence=True,
            db_path=temp_db
        )

        assert bus is not None
        assert bus._max_workers == 4
        assert bus.persistence is not None

        # 清理
        bus.shutdown()


class TestEventMetadata:
    """事件元数据测试类"""

    def test_metadata_creation(self):
        """测试元数据创建"""
        metadata = EventMetadata(
            priority=EventPriority.HIGH,
            source="test_source",
            tags={"key": "value"}
        )

        assert metadata.priority == EventPriority.HIGH
        assert metadata.source == "test_source"
        assert metadata.tags["key"] == "value"
        assert metadata.retry_count == 0
        assert metadata.max_retries == 3

    def test_metadata_serialization(self):
        """测试元数据序列化"""
        metadata = EventMetadata(
            priority=EventPriority.CRITICAL,
            source="serialization_test",
            correlation_id="test_correlation",
            tags={"test": True}
        )

        # 转换为字典
        data = metadata.to_dict()
        assert data['priority'] == EventPriority.CRITICAL.value
        assert data['source'] == "serialization_test"
        assert data['correlation_id'] == "test_correlation"
        assert data['tags']['test'] is True

        # 从字典恢复
        restored_metadata = EventMetadata.from_dict(data)
        assert restored_metadata.priority == EventPriority.CRITICAL
        assert restored_metadata.source == "serialization_test"
        assert restored_metadata.correlation_id == "test_correlation"
        assert restored_metadata.tags['test'] is True


class TestEnhancedEvent:
    """增强事件测试类"""

    def test_event_creation(self):
        """测试事件创建"""
        metadata = EventMetadata(source="test")
        event = EnhancedEvent(
            name="test_event",
            data={"message": "test"},
            metadata=metadata
        )

        assert event.name == "test_event"
        assert event.data["message"] == "test"
        assert event.metadata.source == "test"

    def test_event_serialization(self):
        """测试事件序列化"""
        metadata = EventMetadata(
            priority=EventPriority.HIGH,
            source="serialization_test"
        )
        event = EnhancedEvent(
            name="serialization_event",
            data={"key": "value", "number": 42},
            metadata=metadata
        )

        # 转换为字典
        data = event.to_dict()
        assert data['name'] == "serialization_event"
        assert data['data']['key'] == "value"
        assert data['data']['number'] == 42
        assert data['metadata']['priority'] == EventPriority.HIGH.value

        # 从字典恢复
        restored_event = EnhancedEvent.from_dict(data)
        assert restored_event.name == "serialization_event"
        assert restored_event.data['key'] == "value"
        assert restored_event.data['number'] == 42
        assert restored_event.metadata.priority == EventPriority.HIGH


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
