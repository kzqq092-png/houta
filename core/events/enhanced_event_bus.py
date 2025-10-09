#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
增强版事件总线模块

在现有事件总线基础上增加智能化功能：
1. 智能事件路由和优先级处理
2. 事件流控制和背压管理
3. 分布式事件处理
4. 事件持久化和重放
5. 智能错误恢复和重试
6. 事件监控和分析
7. 动态事件处理器管理
8. 事件聚合和批处理
"""

import asyncio
import json
import pickle
import sqlite3
import threading
import time
import uuid
from collections import defaultdict, deque
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Type, Union, Tuple
import weakref
from loguru import logger

from .event_bus import EventBus, SimpleEventHandler
from .events import BaseEvent
from .event_handler import EventHandler, AsyncEventHandler

class EventPriority(Enum):
    """事件优先级"""
    CRITICAL = 1
    HIGH = 2
    NORMAL = 3
    LOW = 4
    BACKGROUND = 5

class EventStatus(Enum):
    """事件状态"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"
    CANCELLED = "cancelled"

class BackpressureStrategy(Enum):
    """背压策略"""
    DROP_OLDEST = "drop_oldest"
    DROP_NEWEST = "drop_newest"
    BLOCK = "block"
    BUFFER = "buffer"
    SAMPLE = "sample"

@dataclass
class EventMetadata:
    """事件元数据"""
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = field(default_factory=datetime.now)
    priority: EventPriority = EventPriority.NORMAL
    source: str = "unknown"
    correlation_id: Optional[str] = None
    retry_count: int = 0
    max_retries: int = 3
    timeout: Optional[float] = None
    tags: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        data = asdict(self)
        data['timestamp'] = self.timestamp.isoformat()
        data['priority'] = self.priority.value
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'EventMetadata':
        """从字典创建"""
        if 'timestamp' in data:
            data['timestamp'] = datetime.fromisoformat(data['timestamp'])
        if 'priority' in data:
            data['priority'] = EventPriority(data['priority'])
        return cls(**data)

@dataclass
class EnhancedEvent:
    """增强版事件"""
    name: str
    data: Dict[str, Any]
    metadata: EventMetadata

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'name': self.name,
            'data': self.data,
            'metadata': self.metadata.to_dict()
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'EnhancedEvent':
        """从字典创建"""
        return cls(
            name=data['name'],
            data=data['data'],
            metadata=EventMetadata.from_dict(data['metadata'])
        )

class EventRouter:
    """智能事件路由器"""

    def __init__(self):
        self.routing_rules: List[Tuple[Callable[[EnhancedEvent], bool], str]] = []
        self.load_balancing_strategies: Dict[str, Callable] = {}

    def add_routing_rule(self, condition: Callable[[EnhancedEvent], bool], target: str):
        """添加路由规则"""
        self.routing_rules.append((condition, target))

    def route_event(self, event: EnhancedEvent) -> List[str]:
        """路由事件到目标处理器"""
        targets = []
        for condition, target in self.routing_rules:
            try:
                if condition(event):
                    targets.append(target)
            except Exception as e:
                logger.error(f"路由规则执行失败: {e}")

        return targets or ["default"]

class EventPersistence:
    """事件持久化管理器"""

    def __init__(self, db_path: str = "events.db"):
        self.db_path = Path(db_path)
        self._init_database()

    def _init_database(self):
        """初始化数据库"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # 事件表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS events (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    data TEXT NOT NULL,
                    metadata TEXT NOT NULL,
                    status TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # 事件处理记录表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS event_processing (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_id TEXT NOT NULL,
                    handler_name TEXT NOT NULL,
                    status TEXT NOT NULL,
                    result TEXT,
                    error_message TEXT,
                    processing_time REAL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (event_id) REFERENCES events (id)
                )
            """)

            # 创建索引
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_events_name ON events (name)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_events_status ON events (status)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_events_created_at ON events (created_at)")

            conn.commit()

    def save_event(self, event: EnhancedEvent, status: EventStatus = EventStatus.PENDING):
        """保存事件"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT OR REPLACE INTO events (id, name, data, metadata, status)
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    event.metadata.event_id,
                    event.name,
                    json.dumps(event.data),
                    json.dumps(event.metadata.to_dict()),
                    status.value
                ))
                conn.commit()
        except Exception as e:
            logger.error(f"保存事件失败: {e}")

    def update_event_status(self, event_id: str, status: EventStatus):
        """更新事件状态"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE events SET status = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, (status.value, event_id))
                conn.commit()
        except Exception as e:
            logger.error(f"更新事件状态失败: {e}")

    def get_events_by_status(self, status: EventStatus, limit: int = 100) -> List[EnhancedEvent]:
        """根据状态获取事件"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT name, data, metadata FROM events
                    WHERE status = ? ORDER BY created_at LIMIT ?
                """, (status.value, limit))

                events = []
                for row in cursor.fetchall():
                    name, data_json, metadata_json = row
                    event = EnhancedEvent(
                        name=name,
                        data=json.loads(data_json),
                        metadata=EventMetadata.from_dict(json.loads(metadata_json))
                    )
                    events.append(event)

                return events
        except Exception as e:
            logger.error(f"获取事件失败: {e}")
            return []

    def record_processing_result(self, event_id: str, handler_name: str,
                                 status: EventStatus, result: Any = None,
                                 error_message: str = None, processing_time: float = 0.0):
        """记录处理结果"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO event_processing 
                    (event_id, handler_name, status, result, error_message, processing_time)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    event_id, handler_name, status.value,
                    json.dumps(result) if result else None,
                    error_message, processing_time
                ))
                conn.commit()
        except Exception as e:
            logger.error(f"记录处理结果失败: {e}")

class BackpressureManager:
    """背压管理器"""

    def __init__(self, max_queue_size: int = 10000, strategy: BackpressureStrategy = BackpressureStrategy.DROP_OLDEST):
        self.max_queue_size = max_queue_size
        self.strategy = strategy
        self.queue_sizes: Dict[str, int] = defaultdict(int)
        self.dropped_events: int = 0

    def should_accept_event(self, queue_name: str, event: EnhancedEvent) -> bool:
        """检查是否应该接受事件"""
        current_size = self.queue_sizes.get(queue_name, 0)

        if current_size < self.max_queue_size:
            return True

        # 应用背压策略
        if self.strategy == BackpressureStrategy.DROP_NEWEST:
            self.dropped_events += 1
            logger.warning(f"队列 {queue_name} 已满，丢弃新事件: {event.metadata.event_id}")
            return False
        elif self.strategy == BackpressureStrategy.BLOCK:
            # 阻塞直到有空间
            return True
        elif self.strategy == BackpressureStrategy.SAMPLE:
            # 采样策略：只接受高优先级事件
            if event.metadata.priority in [EventPriority.CRITICAL, EventPriority.HIGH]:
                return True
            else:
                self.dropped_events += 1
                return False

        return True

    def update_queue_size(self, queue_name: str, size: int):
        """更新队列大小"""
        self.queue_sizes[queue_name] = size

class EventAggregator:
    """事件聚合器"""

    def __init__(self, window_size: float = 1.0, max_batch_size: int = 100):
        self.window_size = window_size
        self.max_batch_size = max_batch_size
        self.pending_events: Dict[str, List[EnhancedEvent]] = defaultdict(list)
        self.last_flush: Dict[str, float] = {}
        self.aggregation_rules: Dict[str, Callable[[List[EnhancedEvent]], EnhancedEvent]] = {}

    def add_aggregation_rule(self, event_pattern: str, aggregator: Callable[[List[EnhancedEvent]], EnhancedEvent]):
        """添加聚合规则"""
        self.aggregation_rules[event_pattern] = aggregator

    def add_event(self, event: EnhancedEvent) -> Optional[EnhancedEvent]:
        """添加事件，返回聚合后的事件（如果需要）"""
        event_key = self._get_aggregation_key(event)
        self.pending_events[event_key].append(event)

        current_time = time.time()
        last_flush_time = self.last_flush.get(event_key, current_time)

        # 检查是否需要刷新
        should_flush = (
            len(self.pending_events[event_key]) >= self.max_batch_size or
            current_time - last_flush_time >= self.window_size
        )

        if should_flush:
            return self._flush_events(event_key)

        return None

    def _get_aggregation_key(self, event: EnhancedEvent) -> str:
        """获取聚合键"""
        # 简单实现：按事件名称聚合
        return event.name

    def _flush_events(self, event_key: str) -> Optional[EnhancedEvent]:
        """刷新事件"""
        events = self.pending_events[event_key]
        if not events:
            return None

        # 应用聚合规则
        if event_key in self.aggregation_rules:
            aggregated_event = self.aggregation_rules[event_key](events)
        else:
            # 默认聚合：合并所有事件数据
            aggregated_event = self._default_aggregation(events)

        # 清空待处理事件
        self.pending_events[event_key] = []
        self.last_flush[event_key] = time.time()

        return aggregated_event

    def _default_aggregation(self, events: List[EnhancedEvent]) -> EnhancedEvent:
        """默认聚合策略"""
        if len(events) == 1:
            return events[0]

        # 合并事件数据
        aggregated_data = {
            'event_count': len(events),
            'events': [event.data for event in events],
            'time_range': {
                'start': min(event.metadata.timestamp for event in events).isoformat(),
                'end': max(event.metadata.timestamp for event in events).isoformat()
            }
        }

        # 使用第一个事件的元数据作为基础
        base_metadata = events[0].metadata
        aggregated_metadata = EventMetadata(
            event_id=str(uuid.uuid4()),
            timestamp=datetime.now(),
            priority=min(event.metadata.priority for event in events),
            source=base_metadata.source,
            correlation_id=base_metadata.correlation_id,
            tags={**base_metadata.tags, 'aggregated': True}
        )

        return EnhancedEvent(
            name=f"{events[0].name}_aggregated",
            data=aggregated_data,
            metadata=aggregated_metadata
        )

class EnhancedEventBus(EventBus):
    """增强版事件总线"""

    def __init__(self,
                 async_execution: bool = True,
                 max_workers: int = 8,
                 deduplication_window: float = 0.5,
                 enable_persistence: bool = True,
                 enable_aggregation: bool = True,
                 enable_backpressure: bool = True,
                 db_path: str = "enhanced_events.db"):
        """
        初始化增强版事件总线

        Args:
            async_execution: 是否异步执行
            max_workers: 最大工作线程数
            deduplication_window: 去重时间窗口
            enable_persistence: 是否启用持久化
            enable_aggregation: 是否启用事件聚合
            enable_backpressure: 是否启用背压管理
            db_path: 数据库路径
        """
        super().__init__(async_execution, max_workers, deduplication_window)

        # 增强功能组件
        self.event_router = EventRouter()
        self.persistence = EventPersistence(db_path) if enable_persistence else None
        self.backpressure_manager = BackpressureManager() if enable_backpressure else None
        self.event_aggregator = EventAggregator() if enable_aggregation else None

        # 优先级队列
        self.priority_queues: Dict[EventPriority, deque] = {
            priority: deque() for priority in EventPriority
        }

        # 处理器管理
        self.enhanced_handlers: Dict[str, List[Callable]] = defaultdict(list)
        self.handler_metadata: Dict[str, Dict[str, Any]] = {}

        # 监控和统计
        self.enhanced_stats = {
            'events_routed': 0,
            'events_aggregated': 0,
            'events_persisted': 0,
            'events_dropped': 0,
            'processing_times': defaultdict(list),
            'handler_performance': defaultdict(dict)
        }

        # 异步处理控制
        self.processing_loop_running = False
        self.processing_loop_task = None

        # 启动处理循环
        if async_execution:
            self._start_processing_loop()

        logger.info("增强版事件总线初始化完成")

    def _run_event_loop(self):
        """在新线程中运行事件循环"""
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            self.processing_loop_task = loop.create_task(self._processing_loop())
            loop.run_forever()
        except Exception as e:
            logger.error(f"事件循环运行错误: {e}")
        finally:
            try:
                loop.close()
            except:
                pass

    def _start_processing_loop(self):
        """启动异步处理循环"""
        if not self.processing_loop_running:
            self.processing_loop_running = True
            try:
                # 尝试在现有事件循环中创建任务
                self.processing_loop_task = asyncio.create_task(self._processing_loop())
            except RuntimeError:
                # 如果没有运行的事件循环，则在线程中启动新的事件循环
                import threading
                self.loop_thread = threading.Thread(target=self._run_event_loop, daemon=True)
                self.loop_thread.start()

    async def _processing_loop(self):
        """异步处理循环"""
        while self.processing_loop_running:
            try:
                # 按优先级处理事件
                for priority in EventPriority:
                    queue = self.priority_queues[priority]
                    if queue:
                        event = queue.popleft()
                        await self._process_enhanced_event(event)

                # 处理聚合事件
                if self.event_aggregator:
                    self._process_aggregated_events()

                await asyncio.sleep(0.01)  # 避免CPU占用过高

            except Exception as e:
                logger.error(f"事件处理循环错误: {e}")
                await asyncio.sleep(1)

    def publish_enhanced(self,
                         event_name: str,
                         event_data: Dict[str, Any],
                         priority: EventPriority = EventPriority.NORMAL,
                         source: str = "unknown",
                         correlation_id: str = None,
                         tags: Dict[str, Any] = None) -> str:
        """发布增强版事件"""
        try:
            # 创建事件元数据
            metadata = EventMetadata(
                priority=priority,
                source=source,
                correlation_id=correlation_id,
                tags=tags or {}
            )

            # 创建增强事件
            enhanced_event = EnhancedEvent(
                name=event_name,
                data=event_data,
                metadata=metadata
            )

            # 检查背压
            if self.backpressure_manager:
                if not self.backpressure_manager.should_accept_event("main", enhanced_event):
                    self.enhanced_stats['events_dropped'] += 1
                    return metadata.event_id

            # 持久化事件
            if self.persistence:
                self.persistence.save_event(enhanced_event)
                self.enhanced_stats['events_persisted'] += 1

            # 事件聚合
            if self.event_aggregator:
                aggregated_event = self.event_aggregator.add_event(enhanced_event)
                if aggregated_event:
                    enhanced_event = aggregated_event
                    self.enhanced_stats['events_aggregated'] += 1
                else:
                    # 事件被聚合，暂不处理
                    return metadata.event_id

            # 路由事件
            targets = self.event_router.route_event(enhanced_event)
            self.enhanced_stats['events_routed'] += len(targets)

            # 添加到优先级队列
            self.priority_queues[priority].append(enhanced_event)

            # 同步处理（如果不是异步模式）
            if not self._async_execution:
                # 在非异步模式下直接处理事件
                import threading
                threading.Thread(
                    target=self._process_enhanced_event_sync,
                    args=(enhanced_event,),
                    daemon=True
                ).start()

            return metadata.event_id

        except Exception as e:
            logger.error(f"发布增强事件失败: {e}")
            self._stats['errors'] += 1
            return ""

    async def _process_enhanced_event(self, event: EnhancedEvent):
        """处理增强事件"""
        start_time = time.time()

        try:
            # 更新事件状态
            if self.persistence:
                self.persistence.update_event_status(event.metadata.event_id, EventStatus.PROCESSING)

            # 获取处理器
            handlers = self.enhanced_handlers.get(event.name, [])
            handlers.extend(self.enhanced_handlers.get("*", []))  # 全局处理器

            if not handlers:
                logger.debug(f"没有找到事件 {event.name} 的处理器")
                return

            # 并行执行处理器
            tasks = []
            for handler in handlers:
                if asyncio.iscoroutinefunction(handler):
                    task = asyncio.create_task(self._execute_async_handler(handler, event))
                else:
                    task = asyncio.create_task(self._execute_sync_handler(handler, event))
                tasks.append(task)

            # 等待所有处理器完成
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # 处理结果
            success_count = 0
            for i, result in enumerate(results):
                handler_name = getattr(handlers[i], '__name__', str(handlers[i]))

                if isinstance(result, Exception):
                    logger.error(f"处理器 {handler_name} 执行失败: {result}")
                    if self.persistence:
                        self.persistence.record_processing_result(
                            event.metadata.event_id, handler_name,
                            EventStatus.FAILED, error_message=str(result)
                        )
                else:
                    success_count += 1
                    if self.persistence:
                        self.persistence.record_processing_result(
                            event.metadata.event_id, handler_name,
                            EventStatus.COMPLETED, result=result
                        )

            # 更新最终状态
            final_status = EventStatus.COMPLETED if success_count > 0 else EventStatus.FAILED
            if self.persistence:
                self.persistence.update_event_status(event.metadata.event_id, final_status)

            # 记录性能统计
            processing_time = time.time() - start_time
            self.enhanced_stats['processing_times'][event.name].append(processing_time)

        except Exception as e:
            logger.error(f"处理增强事件失败: {e}")
            if self.persistence:
                self.persistence.update_event_status(event.metadata.event_id, EventStatus.FAILED)

    def _process_enhanced_event_sync(self, event: EnhancedEvent):
        """同步处理增强事件"""
        start_time = time.time()

        try:
            # 更新事件状态
            if self.persistence:
                self.persistence.update_event_status(event.metadata.event_id, EventStatus.PROCESSING)

            # 获取处理器
            handlers = self.enhanced_handlers.get(event.name, [])
            handlers.extend(self.enhanced_handlers.get("*", []))  # 全局处理器

            if not handlers:
                logger.debug(f"没有找到事件 {event.name} 的处理器")
                return

            # 同步执行处理器
            success_count = 0
            for handler in handlers:
                handler_name = getattr(handler, '__name__', str(handler))

                try:
                    if asyncio.iscoroutinefunction(handler):
                        # 异步处理器在同步模式下跳过或使用简单包装
                        logger.warning(f"跳过异步处理器 {handler_name} (同步模式)")
                        continue
                    else:
                        # 同步处理器
                        result = handler(event)
                        success_count += 1

                        if self.persistence:
                            self.persistence.record_processing_result(
                                event.metadata.event_id, handler_name,
                                EventStatus.COMPLETED, result=result
                            )

                except Exception as e:
                    logger.error(f"处理器 {handler_name} 执行失败: {e}")
                    if self.persistence:
                        self.persistence.record_processing_result(
                            event.metadata.event_id, handler_name,
                            EventStatus.FAILED, error_message=str(e)
                        )

            # 更新最终状态
            final_status = EventStatus.COMPLETED if success_count > 0 else EventStatus.FAILED
            if self.persistence:
                self.persistence.update_event_status(event.metadata.event_id, final_status)

            # 记录性能统计
            processing_time = time.time() - start_time
            self.enhanced_stats['processing_times'][event.name].append(processing_time)

        except Exception as e:
            logger.error(f"同步处理增强事件失败: {e}")
            if self.persistence:
                self.persistence.update_event_status(event.metadata.event_id, EventStatus.FAILED)

    async def _execute_async_handler(self, handler: Callable, event: EnhancedEvent):
        """执行异步处理器"""
        return await handler(event)

    async def _execute_sync_handler(self, handler: Callable, event: EnhancedEvent):
        """执行同步处理器"""
        return handler(event)

    def subscribe_enhanced(self,
                           event_name: str,
                           handler: Callable,
                           priority: int = 5,
                           timeout: float = None,
                           retry_count: int = 0):
        """订阅增强事件"""
        self.enhanced_handlers[event_name].append(handler)

        # 记录处理器元数据
        handler_id = f"{event_name}:{getattr(handler, '__name__', str(handler))}"
        self.handler_metadata[handler_id] = {
            'priority': priority,
            'timeout': timeout,
            'retry_count': retry_count,
            'registered_at': datetime.now().isoformat()
        }

        logger.info(f"注册增强事件处理器: {handler_id}")

    def unsubscribe_enhanced(self, event_name: str, handler: Callable):
        """取消订阅增强事件"""
        if event_name in self.enhanced_handlers:
            try:
                self.enhanced_handlers[event_name].remove(handler)
                logger.info(f"取消订阅增强事件处理器: {event_name}")
            except ValueError:
                logger.warning(f"处理器未找到: {event_name}")

    def _process_aggregated_events(self):
        """处理聚合事件"""
        if not self.event_aggregator:
            return

        # 强制刷新所有待处理的聚合事件
        for event_key in list(self.event_aggregator.pending_events.keys()):
            if self.event_aggregator.pending_events[event_key]:
                aggregated_event = self.event_aggregator._flush_events(event_key)
                if aggregated_event:
                    # 将聚合事件添加到处理队列
                    priority = aggregated_event.metadata.priority
                    self.priority_queues[priority].append(aggregated_event)

    def get_enhanced_stats(self) -> Dict[str, Any]:
        """获取增强统计信息"""
        stats = {
            **self._stats,
            **self.enhanced_stats,
            'priority_queue_sizes': {
                priority.name: len(queue)
                for priority, queue in self.priority_queues.items()
            },
            'handler_count': sum(len(handlers) for handlers in self.enhanced_handlers.values()),
            'average_processing_times': {}
        }

        # 计算平均处理时间
        for event_name, times in self.enhanced_stats['processing_times'].items():
            if times:
                stats['average_processing_times'][event_name] = sum(times) / len(times)

        return stats

    def replay_events(self,
                      start_time: datetime = None,
                      end_time: datetime = None,
                      event_names: List[str] = None,
                      status_filter: EventStatus = None) -> int:
        """重放事件"""
        if not self.persistence:
            logger.warning("事件持久化未启用，无法重放事件")
            return 0

        try:
            # 获取要重放的事件
            if status_filter:
                events = self.persistence.get_events_by_status(status_filter)
            else:
                # 这里需要扩展persistence类来支持更复杂的查询
                events = self.persistence.get_events_by_status(EventStatus.FAILED)

            # 过滤事件
            if event_names:
                events = [e for e in events if e.name in event_names]

            if start_time or end_time:
                events = [e for e in events
                          if (not start_time or e.metadata.timestamp >= start_time) and
                          (not end_time or e.metadata.timestamp <= end_time)]

            # 重放事件
            replayed_count = 0
            for event in events:
                # 重置事件状态
                event.metadata.event_id = str(uuid.uuid4())
                event.metadata.timestamp = datetime.now()
                event.metadata.retry_count = 0

                # 重新发布事件
                self.priority_queues[event.metadata.priority].append(event)
                replayed_count += 1

            logger.info(f"重放了 {replayed_count} 个事件")
            return replayed_count

        except Exception as e:
            logger.error(f"重放事件失败: {e}")
            return 0

    def shutdown(self):
        """关闭事件总线"""
        self.processing_loop_running = False

        if self.processing_loop_task:
            self.processing_loop_task.cancel()

        # 处理剩余事件
        if self.event_aggregator:
            self._process_aggregated_events()

        # 关闭线程池
        if self._executor:
            self._executor.shutdown(wait=True)

        logger.info("增强版事件总线已关闭")

# 全局实例
_enhanced_event_bus: Optional[EnhancedEventBus] = None

def get_enhanced_event_bus() -> EnhancedEventBus:
    """获取增强版事件总线实例"""
    global _enhanced_event_bus
    if _enhanced_event_bus is None:
        _enhanced_event_bus = EnhancedEventBus()
    return _enhanced_event_bus

def initialize_enhanced_event_bus(
    async_execution: bool = True,
    max_workers: int = 8,
    deduplication_window: float = 0.5,
    enable_persistence: bool = True,
    enable_aggregation: bool = True,
    enable_backpressure: bool = True,
    db_path: str = "enhanced_events.db"
) -> EnhancedEventBus:
    """初始化增强版事件总线"""
    global _enhanced_event_bus

    _enhanced_event_bus = EnhancedEventBus(
        async_execution=async_execution,
        max_workers=max_workers,
        deduplication_window=deduplication_window,
        enable_persistence=enable_persistence,
        enable_aggregation=enable_aggregation,
        enable_backpressure=enable_backpressure,
        db_path=db_path
    )

    logger.info("增强版事件总线初始化完成")
    return _enhanced_event_bus
