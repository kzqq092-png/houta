#!/usr/bin/env python3
"""
智能重试管理器

实现失败任务的智能重试机制，包括：
- 指数退避重试策略
- 错误类型分析
- 重试条件判断
- 重试历史记录
"""

import logging
import time
import json
from typing import Dict, Any, Optional, List, Callable
from datetime import datetime, timedelta
from enum import Enum
from dataclasses import dataclass, asdict
from pathlib import Path
from PyQt5.QtCore import QObject, QTimer, pyqtSignal

logger = logging.getLogger(__name__)


class RetryStrategy(Enum):
    """重试策略"""
    IMMEDIATE = "immediate"  # 立即重试
    LINEAR = "linear"  # 线性退避
    EXPONENTIAL = "exponential"  # 指数退避
    FIXED_INTERVAL = "fixed_interval"  # 固定间隔
    CUSTOM = "custom"  # 自定义策略


class ErrorCategory(Enum):
    """错误类别"""
    NETWORK_ERROR = "network_error"  # 网络错误
    TIMEOUT_ERROR = "timeout_error"  # 超时错误
    PERMISSION_ERROR = "permission_error"  # 权限错误
    RESOURCE_ERROR = "resource_error"  # 资源错误
    LOGIC_ERROR = "logic_error"  # 逻辑错误
    UNKNOWN_ERROR = "unknown_error"  # 未知错误


@dataclass
class RetryConfig:
    """重试配置"""
    max_attempts: int = 3  # 最大重试次数
    strategy: RetryStrategy = RetryStrategy.EXPONENTIAL  # 重试策略
    base_delay: float = 1.0  # 基础延迟（秒）
    max_delay: float = 60.0  # 最大延迟（秒）
    backoff_multiplier: float = 2.0  # 退避倍数
    jitter: bool = True  # 是否添加随机抖动
    retryable_errors: List[ErrorCategory] = None  # 可重试的错误类型

    def __post_init__(self):
        if self.retryable_errors is None:
            self.retryable_errors = [
                ErrorCategory.NETWORK_ERROR,
                ErrorCategory.TIMEOUT_ERROR,
                ErrorCategory.RESOURCE_ERROR
            ]


@dataclass
class RetryAttempt:
    """重试尝试记录"""
    attempt_number: int
    timestamp: str
    error_message: str
    error_category: ErrorCategory
    delay_before_retry: float
    success: bool = False

    def to_dict(self) -> dict:
        """转换为字典"""
        return asdict(self)


@dataclass
class RetryTask:
    """重试任务"""
    task_id: str
    task_type: str
    task_data: dict
    config: RetryConfig
    attempts: List[RetryAttempt]
    created_at: str
    last_attempt_at: Optional[str] = None
    next_retry_at: Optional[str] = None
    status: str = "pending"  # pending, retrying, completed, failed, cancelled

    def to_dict(self) -> dict:
        """转换为字典"""
        data = asdict(self)
        data['config'] = asdict(self.config)
        data['attempts'] = [attempt.to_dict() for attempt in self.attempts]
        return data

    @classmethod
    def from_dict(cls, data: dict) -> 'RetryTask':
        """从字典创建"""
        config_data = data.pop('config')
        attempts_data = data.pop('attempts', [])

        config = RetryConfig(**config_data)
        attempts = [RetryAttempt(**attempt_data) for attempt_data in attempts_data]

        task = cls(config=config, attempts=attempts, **data)
        return task


class ErrorAnalyzer:
    """错误分析器"""

    ERROR_PATTERNS = {
        ErrorCategory.NETWORK_ERROR: [
            "connection", "network", "socket", "dns", "host", "unreachable",
            "timeout", "refused", "reset", "broken pipe"
        ],
        ErrorCategory.TIMEOUT_ERROR: [
            "timeout", "timed out", "deadline", "expired"
        ],
        ErrorCategory.PERMISSION_ERROR: [
            "permission", "access denied", "forbidden", "unauthorized",
            "not allowed", "privilege"
        ],
        ErrorCategory.RESOURCE_ERROR: [
            "memory", "disk", "space", "resource", "limit", "quota",
            "busy", "locked", "unavailable"
        ],
        ErrorCategory.LOGIC_ERROR: [
            "assertion", "value error", "type error", "key error",
            "index error", "attribute error", "import error"
        ]
    }

    @classmethod
    def categorize_error(cls, error_message: str) -> ErrorCategory:
        """分析错误类别"""
        error_lower = error_message.lower()

        for category, patterns in cls.ERROR_PATTERNS.items():
            for pattern in patterns:
                if pattern in error_lower:
                    return category

        return ErrorCategory.UNKNOWN_ERROR

    @classmethod
    def is_retryable(cls, error_message: str, retryable_errors: List[ErrorCategory]) -> bool:
        """判断错误是否可重试"""
        error_category = cls.categorize_error(error_message)
        return error_category in retryable_errors


class RetryDelayCalculator:
    """重试延迟计算器"""

    @staticmethod
    def calculate_delay(attempt_number: int, config: RetryConfig) -> float:
        """计算重试延迟"""
        import random

        if config.strategy == RetryStrategy.IMMEDIATE:
            delay = 0
        elif config.strategy == RetryStrategy.LINEAR:
            delay = config.base_delay * attempt_number
        elif config.strategy == RetryStrategy.EXPONENTIAL:
            delay = config.base_delay * (config.backoff_multiplier ** (attempt_number - 1))
        elif config.strategy == RetryStrategy.FIXED_INTERVAL:
            delay = config.base_delay
        else:  # CUSTOM 或其他
            delay = config.base_delay

        # 限制最大延迟
        delay = min(delay, config.max_delay)

        # 添加随机抖动
        if config.jitter and delay > 0:
            jitter_range = delay * 0.1  # 10% 抖动
            delay += random.uniform(-jitter_range, jitter_range)
            delay = max(0, delay)  # 确保不为负数

        return delay


class SmartRetryManager(QObject):
    """智能重试管理器"""

    # 信号定义
    task_added = pyqtSignal(str)  # 任务ID
    retry_started = pyqtSignal(str, int)  # 任务ID, 尝试次数
    retry_completed = pyqtSignal(str, bool)  # 任务ID, 是否成功
    retry_failed = pyqtSignal(str, str)  # 任务ID, 错误消息
    retry_cancelled = pyqtSignal(str)  # 任务ID

    def __init__(self, storage_path: str = "cache/retry_tasks.json", parent=None):
        super().__init__(parent)
        self.storage_path = Path(storage_path)
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)

        self.tasks: Dict[str, RetryTask] = {}
        self.retry_timers: Dict[str, QTimer] = {}
        self.task_executors: Dict[str, Callable] = {}

        # 加载持久化任务
        self._load_tasks()

        # 启动定期保存定时器
        self.save_timer = QTimer()
        self.save_timer.timeout.connect(self._save_tasks)
        self.save_timer.start(30000)  # 每30秒保存一次

    def register_task_executor(self, task_type: str, executor: Callable):
        """注册任务执行器"""
        self.task_executors[task_type] = executor
        logger.info(f"注册任务执行器: {task_type}")

    def add_retry_task(self, task_id: str, task_type: str, task_data: dict,
                       config: RetryConfig = None) -> bool:
        """添加重试任务"""
        try:
            if task_id in self.tasks:
                logger.warning(f"重试任务已存在: {task_id}")
                return False

            if config is None:
                config = RetryConfig()

            task = RetryTask(
                task_id=task_id,
                task_type=task_type,
                task_data=task_data,
                config=config,
                attempts=[],
                created_at=datetime.now().isoformat()
            )

            self.tasks[task_id] = task
            self.task_added.emit(task_id)

            # 立即尝试执行
            self._schedule_retry(task_id, 0)

            logger.info(f"添加重试任务: {task_id}")
            return True

        except Exception as e:
            logger.error(f"添加重试任务失败: {e}")
            return False

    def cancel_retry_task(self, task_id: str) -> bool:
        """取消重试任务"""
        try:
            if task_id not in self.tasks:
                logger.warning(f"重试任务不存在: {task_id}")
                return False

            # 取消定时器
            if task_id in self.retry_timers:
                self.retry_timers[task_id].stop()
                del self.retry_timers[task_id]

            # 更新任务状态
            self.tasks[task_id].status = "cancelled"
            self.retry_cancelled.emit(task_id)

            logger.info(f"取消重试任务: {task_id}")
            return True

        except Exception as e:
            logger.error(f"取消重试任务失败: {e}")
            return False

    def get_task_status(self, task_id: str) -> Optional[dict]:
        """获取任务状态"""
        if task_id in self.tasks:
            return self.tasks[task_id].to_dict()
        return None

    def get_all_tasks(self) -> List[dict]:
        """获取所有任务"""
        return [task.to_dict() for task in self.tasks.values()]

    def get_active_tasks(self) -> List[dict]:
        """获取活跃任务"""
        return [
            task.to_dict()
            for task in self.tasks.values()
            if task.status in ["pending", "retrying"]
        ]

    def _schedule_retry(self, task_id: str, delay: float):
        """调度重试"""
        try:
            if task_id not in self.tasks:
                return

            task = self.tasks[task_id]

            if delay <= 0:
                # 立即执行
                self._execute_retry(task_id)
            else:
                # 延迟执行
                timer = QTimer()
                timer.setSingleShot(True)
                timer.timeout.connect(lambda: self._execute_retry(task_id))
                timer.start(int(delay * 1000))  # 转换为毫秒

                self.retry_timers[task_id] = timer

                # 更新下次重试时间
                next_retry_time = datetime.now() + timedelta(seconds=delay)
                task.next_retry_at = next_retry_time.isoformat()

                logger.info(f"调度重试任务 {task_id}，延迟 {delay:.2f} 秒")

        except Exception as e:
            logger.error(f"调度重试失败: {e}")

    def _execute_retry(self, task_id: str):
        """执行重试"""
        try:
            if task_id not in self.tasks:
                return

            task = self.tasks[task_id]

            # 检查是否已取消
            if task.status == "cancelled":
                return

            # 检查重试次数
            attempt_number = len(task.attempts) + 1
            if attempt_number > task.config.max_attempts:
                task.status = "failed"
                self.retry_failed.emit(task_id, f"超过最大重试次数 {task.config.max_attempts}")
                return

            # 更新任务状态
            task.status = "retrying"
            task.last_attempt_at = datetime.now().isoformat()

            # 发送重试开始信号
            self.retry_started.emit(task_id, attempt_number)

            # 执行任务
            success, error_message = self._execute_task(task)

            # 记录尝试结果
            error_category = ErrorAnalyzer.categorize_error(error_message) if error_message else ErrorCategory.UNKNOWN_ERROR

            attempt = RetryAttempt(
                attempt_number=attempt_number,
                timestamp=datetime.now().isoformat(),
                error_message=error_message or "",
                error_category=error_category,
                delay_before_retry=0,
                success=success
            )

            task.attempts.append(attempt)

            if success:
                # 成功完成
                task.status = "completed"
                self.retry_completed.emit(task_id, True)
                logger.info(f"重试任务成功完成: {task_id}")
            else:
                # 检查是否可以重试
                if (attempt_number < task.config.max_attempts and
                        ErrorAnalyzer.is_retryable(error_message, task.config.retryable_errors)):

                    # 计算下次重试延迟
                    delay = RetryDelayCalculator.calculate_delay(attempt_number + 1, task.config)
                    attempt.delay_before_retry = delay

                    # 调度下次重试
                    self._schedule_retry(task_id, delay)

                    logger.info(f"重试任务失败，将在 {delay:.2f} 秒后重试: {task_id}")
                else:
                    # 不再重试
                    task.status = "failed"
                    self.retry_failed.emit(task_id, error_message)
                    logger.error(f"重试任务最终失败: {task_id} - {error_message}")

            # 清理定时器
            if task_id in self.retry_timers:
                del self.retry_timers[task_id]

        except Exception as e:
            logger.error(f"执行重试失败: {e}")
            if task_id in self.tasks:
                self.tasks[task_id].status = "failed"
                self.retry_failed.emit(task_id, str(e))

    def _execute_task(self, task: RetryTask) -> tuple[bool, str]:
        """执行任务"""
        try:
            if task.task_type not in self.task_executors:
                return False, f"未找到任务执行器: {task.task_type}"

            executor = self.task_executors[task.task_type]

            # 执行任务
            result = executor(task.task_data)

            if isinstance(result, bool):
                return result, ""
            elif isinstance(result, tuple) and len(result) == 2:
                return result
            else:
                return True, ""

        except Exception as e:
            return False, str(e)

    def _load_tasks(self):
        """加载持久化任务"""
        try:
            if self.storage_path.exists():
                with open(self.storage_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                for task_data in data.get('tasks', []):
                    task = RetryTask.from_dict(task_data)
                    self.tasks[task.task_id] = task

                logger.info(f"加载了 {len(self.tasks)} 个重试任务")

                # 恢复未完成的任务
                self._resume_pending_tasks()

        except Exception as e:
            logger.error(f"加载重试任务失败: {e}")

    def _save_tasks(self):
        """保存任务到文件"""
        try:
            data = {
                'tasks': [task.to_dict() for task in self.tasks.values()],
                'saved_at': datetime.now().isoformat()
            }

            with open(self.storage_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

        except Exception as e:
            logger.error(f"保存重试任务失败: {e}")

    def _resume_pending_tasks(self):
        """恢复待处理的任务"""
        try:
            for task_id, task in self.tasks.items():
                if task.status in ["pending", "retrying"]:
                    # 检查是否需要立即重试
                    if task.next_retry_at:
                        next_retry_time = datetime.fromisoformat(task.next_retry_at)
                        now = datetime.now()

                        if next_retry_time <= now:
                            # 立即重试
                            self._schedule_retry(task_id, 0)
                        else:
                            # 计算剩余延迟时间
                            delay = (next_retry_time - now).total_seconds()
                            self._schedule_retry(task_id, delay)
                    else:
                        # 立即重试
                        self._schedule_retry(task_id, 0)

        except Exception as e:
            logger.error(f"恢复待处理任务失败: {e}")

    def cleanup_completed_tasks(self, days: int = 7):
        """清理已完成的任务"""
        try:
            cutoff_date = datetime.now() - timedelta(days=days)
            tasks_to_remove = []

            for task_id, task in self.tasks.items():
                if task.status in ["completed", "failed", "cancelled"]:
                    created_at = datetime.fromisoformat(task.created_at)
                    if created_at < cutoff_date:
                        tasks_to_remove.append(task_id)

            for task_id in tasks_to_remove:
                del self.tasks[task_id]

            if tasks_to_remove:
                logger.info(f"清理了 {len(tasks_to_remove)} 个过期任务")

        except Exception as e:
            logger.error(f"清理任务失败: {e}")


# 全局服务实例
_smart_retry_manager = None


def get_smart_retry_manager() -> SmartRetryManager:
    """获取智能重试管理器实例"""
    global _smart_retry_manager
    if _smart_retry_manager is None:
        _smart_retry_manager = SmartRetryManager()
    return _smart_retry_manager
