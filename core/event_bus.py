#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
事件总线模块
用于事件驱动架构的事件发布和订阅
"""

from typing import Dict, List, Callable, Any, Optional, Type
import threading
import weakref
from functools import wraps
import logging

logger = logging.getLogger(__name__)


class EventBus:
    """事件总线类"""

    def __init__(self):
        self._listeners: Dict[str, List[weakref.WeakMethod]] = {}
        self._lock = threading.RLock()
        self._enabled = True

    def subscribe(self, event_class: Type, callback: Callable):
        """订阅事件"""
        with self._lock:
            event_type_str = event_class.event_type
            if event_type_str not in self._listeners:
                self._listeners[event_type_str] = []

            # 使用弱引用避免内存泄漏
            if hasattr(callback, '__self__'):
                weak_callback = weakref.WeakMethod(callback)
            else:
                weak_callback = weakref.ref(callback)

            self._listeners[event_type_str].append(weak_callback)

    def unsubscribe(self, event_class: Type, callback: Callable):
        """取消订阅事件"""
        with self._lock:
            event_type_str = event_class.event_type
            if event_type_str in self._listeners:
                # 查找并移除回调
                listeners = self._listeners[event_type_str]
                for i, weak_callback in enumerate(listeners):
                    if weak_callback() == callback:
                        del listeners[i]
                        break

                # 如果没有监听器了，删除事件类型
                if not listeners:
                    del self._listeners[event_type_str]

    def publish(self, event: Any):
        """发布事件"""
        if not self._enabled:
            return

        with self._lock:
            event_type_str = type(event).event_type
            if event_type_str not in self._listeners:
                return

            # 复制监听器列表，避免在迭代时修改
            listeners = self._listeners[event_type_str].copy()

        # 调用监听器
        dead_refs = []
        for weak_callback in listeners:
            callback = weak_callback()
            if callback is None:
                dead_refs.append(weak_callback)
                continue

            try:
                callback(event)
            except Exception as e:
                logger.error(f"事件处理器异常: {e}", exc_info=True)

        # 清理死引用
        if dead_refs:
            with self._lock:
                event_type_str = type(event).event_type
                if event_type_str in self._listeners:
                    for dead_ref in dead_refs:
                        try:
                            self._listeners[event_type_str].remove(dead_ref)
                        except ValueError:
                            pass

    def emit(self, event_type: str, data: Any = None, source: Any = None):
        """发射事件（便捷方法）"""
        event = Event(event_type, data, source)
        self.publish(event)
        return event

    def clear(self):
        """清空所有监听器"""
        with self._lock:
            self._listeners.clear()

    def enable(self):
        """启用事件总线"""
        self._enabled = True

    def disable(self):
        """禁用事件总线"""
        self._enabled = False

    def is_enabled(self) -> bool:
        """检查事件总线是否启用"""
        return self._enabled

    def get_listener_count(self, event_type: str) -> int:
        """获取指定事件类型的监听器数量"""
        with self._lock:
            if event_type not in self._listeners:
                return 0
            return len(self._listeners[event_type])

    def get_all_event_types(self) -> List[str]:
        """获取所有事件类型"""
        with self._lock:
            return list(self._listeners.keys())


# 全局事件总线实例
global_event_bus = EventBus()
