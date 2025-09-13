from loguru import logger
"""
回测资源管理器
实现上下文管理器模式，确保资源的正确分配和释放
"""

import gc
import threading
import weakref
from contextlib import contextmanager
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime
import psutil
import os
from pathlib import Path


class BacktestResourceManager:
    """
    回测资源管理器
    使用上下文管理器模式确保资源正确释放
    """

    def __init__(self):
        self._resources = []
        self._temp_files = []
        self._threads = []
        self._processes = []
        self._memory_snapshots = []
        self._cleanup_callbacks = []
        self._lock = threading.Lock()

    def __enter__(self):
        """进入上下文，开始资源管理"""
        with self._lock:
            # 记录初始内存状态
            initial_memory = psutil.virtual_memory().used
            self._memory_snapshots.append({
                'timestamp': datetime.now(),
                'memory_used': initial_memory,
                'type': 'enter'
            })
            logger.info(f"资源管理器启动 - 初始内存: {initial_memory / 1024 / 1024:.2f}MB")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """退出上下文，清理所有资源"""
        try:
            self.cleanup_all()

            # 记录最终内存状态
            final_memory = psutil.virtual_memory().used
            self._memory_snapshots.append({
                'timestamp': datetime.now(),
                'memory_used': final_memory,
                'type': 'exit'
            })

            # 计算内存使用情况
            if len(self._memory_snapshots) >= 2:
                initial = self._memory_snapshots[0]['memory_used']
                final = self._memory_snapshots[-1]['memory_used']
                memory_diff = final - initial

                if memory_diff > 0:
                    logger.warning(f"可能存在内存泄露: {memory_diff / 1024 / 1024:.2f}MB")
                else:
                    logger.info(f"内存使用正常，释放: {-memory_diff / 1024 / 1024:.2f}MB")

        except Exception as e:
            logger.error(f"资源清理失败: {e}")
            if exc_type is None:  # 如果没有其他异常，抛出清理异常
                raise

    def register_resource(self, resource: Any, cleanup_func: Optional[Callable] = None):
        """注册需要管理的资源"""
        with self._lock:
            self._resources.append({
                'resource': resource,
                'cleanup_func': cleanup_func,
                'created_at': datetime.now()
            })

    def register_temp_file(self, file_path: Path):
        """注册临时文件"""
        with self._lock:
            self._temp_files.append(file_path)

    def register_thread(self, thread: threading.Thread):
        """注册线程"""
        with self._lock:
            self._threads.append(thread)

    def register_cleanup_callback(self, callback: Callable):
        """注册清理回调函数"""
        with self._lock:
            self._cleanup_callbacks.append(callback)

    def cleanup_all(self):
        """清理所有资源"""
        logger.info("开始清理所有资源...")

        # 1. 执行清理回调
        self._cleanup_callbacks_safe()

        # 2. 清理线程
        self._cleanup_threads()

        # 3. 清理临时文件
        self._cleanup_temp_files()

        # 4. 清理注册的资源
        self._cleanup_resources()

        # 5. 强制垃圾回收
        self._force_garbage_collection()

        logger.info("资源清理完成")

    def _cleanup_callbacks_safe(self):
        """安全执行清理回调"""
        for callback in self._cleanup_callbacks:
            try:
                callback()
            except Exception as e:
                logger.error(f"清理回调执行失败: {e}")

    def _cleanup_threads(self):
        """清理线程"""
        for thread in self._threads:
            try:
                if thread.is_alive():
                    logger.info(f"等待线程结束: {thread.name}")
                    thread.join(timeout=5.0)
                    if thread.is_alive():
                        logger.warning(f"线程未能正常结束: {thread.name}")
            except Exception as e:
                logger.error(f"清理线程失败: {e}")

    def _cleanup_temp_files(self):
        """清理临时文件"""
        for file_path in self._temp_files:
            try:
                if file_path.exists():
                    file_path.unlink()
                    logger.debug(f"删除临时文件: {file_path}")
            except Exception as e:
                logger.error(f"删除临时文件失败 {file_path}: {e}")

    def _cleanup_resources(self):
        """清理注册的资源"""
        for resource_info in self._resources:
            try:
                resource = resource_info['resource']
                cleanup_func = resource_info['cleanup_func']

                if cleanup_func:
                    cleanup_func(resource)
                elif hasattr(resource, 'cleanup'):
                    resource.cleanup()
                elif hasattr(resource, 'close'):
                    resource.close()
                elif hasattr(resource, '__del__'):
                    del resource

            except Exception as e:
                logger.error(f"清理资源失败: {e}")

    def _force_garbage_collection(self):
        """强制垃圾回收"""
        try:
            # 多次垃圾回收确保清理彻底
            for i in range(3):
                collected = gc.collect()
                if collected > 0:
                    logger.debug(f"垃圾回收第{i+1}轮: 清理了{collected}个对象")
                else:
                    break
        except Exception as e:
            logger.error(f"垃圾回收失败: {e}")

    def get_memory_usage(self) -> Dict[str, Any]:
        """获取内存使用情况"""
        memory_info = psutil.virtual_memory()
        return {
            'total': memory_info.total,
            'available': memory_info.available,
            'used': memory_info.used,
            'percentage': memory_info.percent,
            'snapshots': self._memory_snapshots.copy()
        }


@contextmanager
def managed_backtest_resources():
    """便捷的上下文管理器函数"""
    manager = BacktestResourceManager()
    try:
        yield manager
    finally:
        manager.cleanup_all()


class SmartDataManager:
    """
    智能数据管理器
    减少不必要的数据复制，优化内存使用
    """

    def __init__(self, max_cache_size: int = 100):
        self._cache = {}
        self._max_cache_size = max_cache_size
        self._access_count = {}

    def get_data_copy(self, data, copy_strategy: str = 'smart'):
        """
        智能数据复制策略

        Args:
            data: 原始数据
            copy_strategy: 复制策略 ('smart', 'shallow', 'deep', 'view')
        """
        if copy_strategy == 'smart':
            # 根据数据大小和类型智能选择策略
            if hasattr(data, 'memory_usage'):
                memory_usage = data.memory_usage(deep=True).sum()
                if memory_usage > 100 * 1024 * 1024:  # 100MB
                    return data.copy(deep=False)  # 浅复制
                else:
                    return data.copy()  # 深复制
            else:
                return data.copy()

        elif copy_strategy == 'shallow':
            return data.copy(deep=False)
        elif copy_strategy == 'deep':
            return data.copy(deep=True)
        elif copy_strategy == 'view':
            # 尽可能返回视图而不是复制
            if hasattr(data, 'view'):
                return data.view()
            else:
                return data
        else:
            return data.copy()

    def cache_data(self, key: str, data: Any):
        """缓存数据"""
        if len(self._cache) >= self._max_cache_size:
            # LRU淘汰策略
            least_used_key = min(self._access_count, key=self._access_count.get)
            del self._cache[least_used_key]
            del self._access_count[least_used_key]

        self._cache[key] = data
        self._access_count[key] = 0

    def get_cached_data(self, key: str):
        """获取缓存数据"""
        if key in self._cache:
            self._access_count[key] += 1
            return self._cache[key]
        return None

    def clear_cache(self):
        """清理缓存"""
        self._cache.clear()
        self._access_count.clear()
        gc.collect()


# 全局数据管理器实例
global_data_manager = SmartDataManager()
