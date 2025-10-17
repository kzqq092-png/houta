#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
自适应DuckDB连接池管理系统

根据实际负载自动动态调整连接池配置，实现智能资源管理。

核心特性:
1. 实时监控连接池使用情况
2. 智能决策何时扩容/缩容
3. 平滑热重载配置
4. 防止频繁调整（冷却期）
5. 安全边界保护

作者: AI Assistant
日期: 2025-10-13
版本: 1.0
"""

import threading
import time
from collections import deque
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from loguru import logger

from .duckdb_connection_pool import DuckDBConnectionPool
from .connection_pool_config import ConnectionPoolConfig


@dataclass
class AdaptivePoolConfig:
    """自适应连接池配置"""

    # 边界
    min_pool_size: int = 3
    max_pool_size: int = 50

    # 阈值
    scale_up_usage_threshold: float = 0.8
    scale_down_usage_threshold: float = 0.3
    scale_up_overflow_threshold: float = 0.5  # 溢出连接/pool_size

    # 时间窗口
    metrics_window_seconds: int = 60
    cooldown_seconds: int = 60

    # 采集间隔
    collection_interval: int = 10

    # 调整策略
    scale_up_factor: float = 1.5
    scale_down_factor: float = 0.8

    # 是否启用
    enabled: bool = True

    def validate(self) -> bool:
        """验证配置有效性"""
        if self.min_pool_size < 1 or self.max_pool_size > 100:
            return False
        if self.min_pool_size >= self.max_pool_size:
            return False
        if not (0 < self.scale_up_usage_threshold <= 1.0):
            return False
        if not (0 < self.scale_down_usage_threshold <= 1.0):
            return False
        return True


class MetricsCollector:
    """连接池指标收集器"""

    def __init__(self, pool: DuckDBConnectionPool, interval: int = 10):
        """
        初始化指标收集器

        Args:
            pool: DuckDB连接池实例
            interval: 采集间隔（秒）
        """
        self.pool = pool
        self.interval = interval
        self.metrics_history = deque(maxlen=1000)  # 最近1000条记录
        self._running = False
        self._thread = None
        self._lock = threading.Lock()

    def start(self):
        """启动指标收集"""
        if self._running:
            logger.warning("MetricsCollector已在运行")
            return

        self._running = True
        self._thread = threading.Thread(target=self._collect_loop, daemon=True, name="MetricsCollector")
        self._thread.start()
        logger.info(f"📊 指标收集器已启动，采集间隔={self.interval}秒")

    def stop(self):
        """停止指标收集"""
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)
        logger.info("⏸️ 指标收集器已停止")

    def _collect_loop(self):
        """指标收集循环"""
        while self._running:
            try:
                metrics = self._collect_metrics()
                with self._lock:
                    self.metrics_history.append(metrics)
            except Exception as e:
                logger.error(f"指标收集失败: {e}")

            time.sleep(self.interval)

    def _collect_metrics(self) -> Dict[str, Any]:
        """收集当前指标"""
        try:
            status = self.pool.get_pool_status()

            pool_size = status.get('pool_size', 0)
            checked_out = status.get('checked_out', 0)
            overflow = status.get('overflow', 0)

            usage_rate = checked_out / pool_size if pool_size > 0 else 0.0

            return {
                'timestamp': datetime.now(),
                'pool_size': pool_size,
                'checked_out': checked_out,
                'checked_in': status.get('checked_in', 0),
                'overflow': overflow,
                'usage_rate': usage_rate
            }
        except Exception as e:
            logger.error(f"收集指标失败: {e}")
            return {
                'timestamp': datetime.now(),
                'pool_size': 0,
                'checked_out': 0,
                'checked_in': 0,
                'overflow': 0,
                'usage_rate': 0.0
            }

    def get_recent_metrics(self, window_seconds: int = 60) -> List[Dict]:
        """
        获取最近N秒的指标

        Args:
            window_seconds: 时间窗口（秒）

        Returns:
            最近的指标列表
        """
        cutoff = datetime.now() - timedelta(seconds=window_seconds)
        with self._lock:
            return [m for m in self.metrics_history if m['timestamp'] > cutoff]

    def get_latest_metrics(self) -> Optional[Dict]:
        """获取最新指标"""
        with self._lock:
            return self.metrics_history[-1] if self.metrics_history else None


class AdaptiveDecisionEngine:
    """自适应决策引擎"""

    def __init__(self, collector: MetricsCollector, config: AdaptivePoolConfig):
        """
        初始化决策引擎

        Args:
            collector: 指标收集器
            config: 自适应配置
        """
        self.collector = collector
        self.config = config
        self.last_adjustment_time = None
        self.adjustment_count = 0

    def should_adjust(self) -> tuple[bool, Optional[int], Optional[str]]:
        """
        判断是否需要调整

        Returns:
            (是否调整, 新的pool_size, 调整原因)
        """
        # 冷却期检查
        if self.last_adjustment_time:
            elapsed = (datetime.now() - self.last_adjustment_time).total_seconds()
            if elapsed < self.config.cooldown_seconds:
                return False, None, f"冷却期中（剩余{self.config.cooldown_seconds - elapsed:.0f}秒）"

        # 获取最近指标
        recent = self.collector.get_recent_metrics(window_seconds=self.config.metrics_window_seconds)
        if not recent:
            return False, None, "无可用指标"

        # 计算平均指标
        avg_usage = sum(m['usage_rate'] for m in recent) / len(recent)
        avg_overflow = sum(m.get('overflow', 0) for m in recent) / len(recent)
        current_pool_size = recent[-1]['pool_size']

        # 扩容决策
        if self._should_scale_up(avg_usage, avg_overflow, current_pool_size):
            new_size = self._calculate_scale_up(current_pool_size)
            if new_size > current_pool_size:
                reason = f"高负载（使用率={avg_usage*100:.1f}%, 溢出={avg_overflow:.1f}）"
                return True, new_size, reason

        # 缩容决策
        if self._should_scale_down(recent, avg_usage, current_pool_size):
            new_size = self._calculate_scale_down(current_pool_size)
            if new_size < current_pool_size:
                reason = f"低负载（使用率={avg_usage*100:.1f}%）"
                return True, new_size, reason

        return False, None, f"稳定（使用率={avg_usage*100:.1f}%）"

    def _should_scale_up(self, avg_usage: float, avg_overflow: float, pool_size: int) -> bool:
        """判断是否应该扩容"""
        # 使用率过高
        if avg_usage > self.config.scale_up_usage_threshold:
            return True

        # 溢出连接过多
        if pool_size > 0 and avg_overflow > pool_size * self.config.scale_up_overflow_threshold:
            return True

        return False

    def _should_scale_down(self, recent: List[Dict], avg_usage: float, pool_size: int) -> bool:
        """判断是否应该缩容"""
        # 当前池大小已经是最小值
        if pool_size <= self.config.min_pool_size:
            return False

        # 所有recent指标的使用率都低于阈值
        if not all(m['usage_rate'] < self.config.scale_down_usage_threshold for m in recent):
            return False

        # 没有溢出连接
        if not all(m.get('overflow', 0) == 0 for m in recent):
            return False

        return True

    def _calculate_scale_up(self, current_size: int) -> int:
        """计算扩容后的大小"""
        new_size = int(current_size * self.config.scale_up_factor)
        return min(new_size, self.config.max_pool_size)

    def _calculate_scale_down(self, current_size: int) -> int:
        """计算缩容后的大小"""
        new_size = int(current_size * self.config.scale_down_factor)
        return max(new_size, self.config.min_pool_size)


class AdaptiveConnectionPoolManager:
    """自适应连接池管理器"""

    def __init__(self, db, config: Optional[AdaptivePoolConfig] = None):
        """
        初始化自适应管理器

        Args:
            db: FactorWeaveAnalyticsDB实例
            config: 自适应配置（可选）
        """
        self.db = db
        self.config = config or AdaptivePoolConfig()

        if not self.config.validate():
            raise ValueError("无效的自适应配置")

        self.collector = MetricsCollector(db.pool, interval=self.config.collection_interval)
        self.decision_engine = AdaptiveDecisionEngine(self.collector, self.config)
        self._running = False
        self._thread = None

    def start(self):
        """启动自适应管理"""
        if not self.config.enabled:
            logger.info("自适应连接池管理已禁用")
            return

        if self._running:
            logger.warning("自适应管理器已在运行")
            return

        logger.info("🔄 启动自适应连接池管理...")

        # 启动指标收集
        self.collector.start()

        # 启动调整循环
        self._running = True
        self._thread = threading.Thread(target=self._adjustment_loop, daemon=True, name="AdaptiveManager")
        self._thread.start()

        logger.info(f"✅ 自适应连接池管理已启动 (min={self.config.min_pool_size}, max={self.config.max_pool_size})")

    def stop(self):
        """停止自适应管理"""
        self._running = False
        self.collector.stop()

        if self._thread:
            self._thread.join(timeout=5)

        logger.info("⏸️ 自适应连接池管理已停止")

    def _adjustment_loop(self):
        """调整循环"""
        check_interval = 30  # 每30秒检查一次

        while self._running:
            try:
                should_adjust, new_pool_size, reason = self.decision_engine.should_adjust()

                if should_adjust and new_pool_size:
                    self._apply_adjustment(new_pool_size, reason)
                    self.decision_engine.last_adjustment_time = datetime.now()
                    self.decision_engine.adjustment_count += 1
                else:
                    # 记录决策日志（调试用）
                    if logger.level("DEBUG").no <= logger._core.min_level:
                        logger.debug(f"连接池稳定: {reason}")

            except Exception as e:
                logger.error(f"自适应调整失败: {e}")
                import traceback
                logger.error(traceback.format_exc())

            time.sleep(check_interval)

    def _apply_adjustment(self, new_pool_size: int, reason: str):
        """应用调整"""
        old_size = self.db.pool.pool.size()  # pool.pool是QueuePool实例

        logger.info(f"🔄 自动调整连接池: {old_size} -> {new_pool_size} ({reason})")

        try:
            # 创建新配置
            new_config = ConnectionPoolConfig(pool_size=new_pool_size)

            # 热重载
            success = self.db.reload_pool(new_config)

            if success:
                logger.info(f"✅ 连接池已自动调整: pool_size={new_pool_size}")
            else:
                logger.error(f"❌ 连接池自动调整失败")

        except Exception as e:
            logger.error(f"❌ 连接池自动调整异常: {e}")

    def get_status(self) -> Dict[str, Any]:
        """
        获取自适应管理器状态

        Returns:
            状态信息字典
        """
        latest_metrics = self.collector.get_latest_metrics()

        return {
            'enabled': self.config.enabled,
            'running': self._running,
            'adjustment_count': self.decision_engine.adjustment_count,
            'last_adjustment': self.decision_engine.last_adjustment_time.isoformat()
            if self.decision_engine.last_adjustment_time else None,
            'current_pool_size': latest_metrics['pool_size'] if latest_metrics else None,
            'current_usage_rate': f"{latest_metrics['usage_rate']*100:.1f}%" if latest_metrics else None,
            'config': {
                'min_pool_size': self.config.min_pool_size,
                'max_pool_size': self.config.max_pool_size,
                'scale_up_threshold': f"{self.config.scale_up_usage_threshold*100:.0f}%",
                'scale_down_threshold': f"{self.config.scale_down_usage_threshold*100:.0f}%",
                'cooldown_seconds': self.config.cooldown_seconds
            }
        }


# ========================================
# 全局管理器实例（可选）
# ========================================

_global_adaptive_manager: Optional[AdaptiveConnectionPoolManager] = None
_manager_lock = threading.Lock()


def get_adaptive_manager(db=None, config: Optional[AdaptivePoolConfig] = None) -> AdaptiveConnectionPoolManager:
    """
    获取全局自适应管理器实例（单例）

    Args:
        db: FactorWeaveAnalyticsDB实例（首次调用时必需）
        config: 自适应配置（可选）

    Returns:
        AdaptiveConnectionPoolManager实例
    """
    global _global_adaptive_manager

    with _manager_lock:
        if _global_adaptive_manager is None:
            if db is None:
                raise ValueError("首次调用get_adaptive_manager需要提供db参数")

            _global_adaptive_manager = AdaptiveConnectionPoolManager(db, config)

        return _global_adaptive_manager


def start_adaptive_management(db, config: Optional[AdaptivePoolConfig] = None):
    """
    启动全局自适应管理（便捷函数）

    Args:
        db: FactorWeaveAnalyticsDB实例
        config: 自适应配置（可选）
    """
    manager = get_adaptive_manager(db, config)
    manager.start()
    return manager


def stop_adaptive_management():
    """停止全局自适应管理（便捷函数）"""
    global _global_adaptive_manager

    with _manager_lock:
        if _global_adaptive_manager:
            _global_adaptive_manager.stop()
