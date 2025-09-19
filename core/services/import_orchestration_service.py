#!/usr/bin/env python3
"""
导入任务编排服务

提供任务调度和协调的核心服务框架，实现基本的任务队列管理和调度逻辑
支持任务优先级、依赖关系、资源管理和故障恢复
"""

import asyncio
import threading
import time
import uuid
from typing import Dict, List, Any, Optional, Callable, Union, Set
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
from concurrent.futures import ThreadPoolExecutor, Future
from queue import PriorityQueue, Queue, Empty
from loguru import logger

# 导入相关模块
from ..importdata.task_status_manager import (
    TaskStatus, TaskStatusManager, get_task_status_manager
)
from ..importdata.unified_data_import_engine import (
    UnifiedDataImportEngine, UnifiedImportTask, ImportMode
)
from .dependency_resolver import (
    DependencyResolver, TaskDependency as ResolverTaskDependency,
    DependencyType, DependencyStatus, get_dependency_resolver
)


class TaskPriority(Enum):
    """任务优先级"""
    CRITICAL = 1    # 关键任务
    HIGH = 2        # 高优先级
    NORMAL = 3      # 普通优先级
    LOW = 4         # 低优先级
    BACKGROUND = 5  # 后台任务


class SchedulingStrategy(Enum):
    """调度策略"""
    FIFO = "fifo"                    # 先进先出
    PRIORITY = "priority"            # 优先级调度
    ROUND_ROBIN = "round_robin"      # 轮询调度
    SHORTEST_JOB_FIRST = "sjf"       # 最短作业优先
    FAIR_SHARE = "fair_share"        # 公平共享
    DEADLINE_AWARE = "deadline_aware"  # 截止时间感知


class ResourceType(Enum):
    """资源类型"""
    CPU = "cpu"
    MEMORY = "memory"
    NETWORK = "network"
    STORAGE = "storage"
    DATABASE_CONNECTION = "db_connection"
    API_QUOTA = "api_quota"


@dataclass
class ResourceRequirement:
    """资源需求"""
    resource_type: ResourceType
    amount: float
    unit: str = ""
    max_amount: Optional[float] = None

    def __lt__(self, other):
        return self.amount < other.amount


@dataclass
class TaskDependency:
    """任务依赖关系（编排服务内部使用）"""
    task_id: str
    dependency_task_id: str
    dependency_type: str = "completion"  # completion, success, data
    condition: Optional[str] = None

    def to_resolver_dependency(self) -> ResolverTaskDependency:
        """转换为依赖解析器的依赖对象"""
        # 映射依赖类型
        type_mapping = {
            "completion": DependencyType.COMPLETION,
            "success": DependencyType.SUCCESS,
            "data": DependencyType.DATA,
            "resource": DependencyType.RESOURCE,
            "time": DependencyType.TIME,
            "condition": DependencyType.CONDITION
        }

        dependency_type = type_mapping.get(self.dependency_type, DependencyType.COMPLETION)

        return ResolverTaskDependency(
            dependent_task_id=self.task_id,
            prerequisite_task_id=self.dependency_task_id,
            dependency_type=dependency_type,
            condition=self.condition
        )


@dataclass
class OrchestrationTask:
    """编排任务"""
    task_id: str
    import_task: UnifiedImportTask
    priority: TaskPriority = TaskPriority.NORMAL

    # 调度相关
    created_at: datetime = field(default_factory=datetime.now)
    scheduled_at: Optional[datetime] = None
    deadline: Optional[datetime] = None
    max_retries: int = 3
    retry_count: int = 0

    # 资源需求
    resource_requirements: List[ResourceRequirement] = field(default_factory=list)

    # 依赖关系
    dependencies: List[TaskDependency] = field(default_factory=list)
    dependents: List[str] = field(default_factory=list)  # 依赖此任务的任务ID列表

    # 执行相关
    assigned_worker: Optional[str] = None
    execution_start_time: Optional[datetime] = None
    execution_end_time: Optional[datetime] = None

    # 元数据
    metadata: Dict[str, Any] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)

    def __lt__(self, other):
        """用于优先级队列排序"""
        if self.priority.value != other.priority.value:
            return self.priority.value < other.priority.value
        return self.created_at < other.created_at

    @property
    def is_ready_to_execute(self) -> bool:
        """检查任务是否准备好执行"""
        # 检查依赖是否满足
        return len(self.dependencies) == 0

    @property
    def execution_time(self) -> Optional[float]:
        """获取执行时间（秒）"""
        if self.execution_start_time and self.execution_end_time:
            return (self.execution_end_time - self.execution_start_time).total_seconds()
        return None


@dataclass
class WorkerInfo:
    """工作器信息"""
    worker_id: str
    worker_type: str = "default"
    max_concurrent_tasks: int = 1
    current_tasks: int = 0
    available_resources: Dict[ResourceType, float] = field(default_factory=dict)
    capabilities: List[str] = field(default_factory=list)
    status: str = "active"  # active, busy, offline, maintenance
    last_heartbeat: datetime = field(default_factory=datetime.now)

    @property
    def is_available(self) -> bool:
        """检查工作器是否可用"""
        return (self.status == "active" and
                self.current_tasks < self.max_concurrent_tasks)

    def can_handle_task(self, task: OrchestrationTask) -> bool:
        """检查是否能处理指定任务"""
        if not self.is_available:
            return False

        # 检查资源需求
        for req in task.resource_requirements:
            available = self.available_resources.get(req.resource_type, 0)
            if available < req.amount:
                return False

        return True


class TaskScheduler:
    """任务调度器"""

    def __init__(self, strategy: SchedulingStrategy = SchedulingStrategy.PRIORITY):
        self.strategy = strategy
        self.task_queue = PriorityQueue()
        self.scheduled_tasks: Dict[str, OrchestrationTask] = {}
        self._lock = threading.RLock()

    def add_task(self, task: OrchestrationTask):
        """添加任务到调度队列"""
        with self._lock:
            if self.strategy == SchedulingStrategy.PRIORITY:
                self.task_queue.put((task.priority.value, task.created_at, task))
            else:
                self.task_queue.put((0, task.created_at, task))

            self.scheduled_tasks[task.task_id] = task

    def get_next_task(self, worker: WorkerInfo) -> Optional[OrchestrationTask]:
        """获取下一个可执行的任务"""
        with self._lock:
            temp_tasks = []
            selected_task = None

            try:
                while not self.task_queue.empty():
                    priority, created_at, task = self.task_queue.get_nowait()

                    if (task.is_ready_to_execute and
                            worker.can_handle_task(task)):
                        selected_task = task
                        break
                    else:
                        temp_tasks.append((priority, created_at, task))

                # 将未选中的任务放回队列
                for item in temp_tasks:
                    self.task_queue.put(item)

                if selected_task:
                    del self.scheduled_tasks[selected_task.task_id]

                return selected_task

            except Empty:
                return None

    def remove_task(self, task_id: str) -> bool:
        """移除任务"""
        with self._lock:
            if task_id in self.scheduled_tasks:
                del self.scheduled_tasks[task_id]
                return True
            return False

    def get_queue_size(self) -> int:
        """获取队列大小"""
        return self.task_queue.qsize()

    def get_scheduled_tasks(self) -> List[OrchestrationTask]:
        """获取所有调度中的任务"""
        with self._lock:
            return list(self.scheduled_tasks.values())


class ResourceManager:
    """资源管理器"""

    def __init__(self):
        self.available_resources: Dict[ResourceType, float] = {
            ResourceType.CPU: 100.0,
            ResourceType.MEMORY: 100.0,
            ResourceType.NETWORK: 100.0,
            ResourceType.STORAGE: 100.0,
            ResourceType.DATABASE_CONNECTION: 10.0,
            ResourceType.API_QUOTA: 1000.0
        }
        self.allocated_resources: Dict[str, Dict[ResourceType, float]] = {}
        self._lock = threading.RLock()

    def allocate_resources(self, task_id: str, requirements: List[ResourceRequirement]) -> bool:
        """分配资源"""
        with self._lock:
            # 检查资源是否足够
            for req in requirements:
                available = self.available_resources.get(req.resource_type, 0)
                if available < req.amount:
                    return False

            # 分配资源
            allocated = {}
            for req in requirements:
                self.available_resources[req.resource_type] -= req.amount
                allocated[req.resource_type] = req.amount

            self.allocated_resources[task_id] = allocated
            return True

    def release_resources(self, task_id: str):
        """释放资源"""
        with self._lock:
            if task_id in self.allocated_resources:
                allocated = self.allocated_resources[task_id]
                for resource_type, amount in allocated.items():
                    self.available_resources[resource_type] += amount
                del self.allocated_resources[task_id]

    def get_resource_usage(self) -> Dict[ResourceType, Dict[str, float]]:
        """获取资源使用情况"""
        with self._lock:
            usage = {}
            for resource_type in ResourceType:
                total = self.available_resources.get(resource_type, 0)
                allocated = sum(
                    alloc.get(resource_type, 0)
                    for alloc in self.allocated_resources.values()
                )
                usage[resource_type] = {
                    'total': total + allocated,
                    'available': total,
                    'allocated': allocated,
                    'usage_rate': allocated / (total + allocated) if (total + allocated) > 0 else 0
                }
            return usage


class DependencyManager:
    """依赖管理器（集成依赖解析器）"""

    def __init__(self):
        # 使用全局依赖解析器
        self.dependency_resolver = get_dependency_resolver()

        # 保持向后兼容的简单接口
        self.dependencies: Dict[str, List[TaskDependency]] = {}
        self.dependents: Dict[str, List[str]] = {}
        self.completed_tasks: Set[str] = set()
        self._lock = threading.RLock()

    def add_dependency(self, dependency: TaskDependency):
        """添加依赖关系"""
        with self._lock:
            task_id = dependency.task_id
            dep_task_id = dependency.dependency_task_id

            # 添加到本地存储（向后兼容）
            if task_id not in self.dependencies:
                self.dependencies[task_id] = []
            self.dependencies[task_id].append(dependency)

            if dep_task_id not in self.dependents:
                self.dependents[dep_task_id] = []
            self.dependents[dep_task_id].append(task_id)

            # 添加到依赖解析器
            try:
                resolver_dependency = dependency.to_resolver_dependency()
                self.dependency_resolver.add_dependency(resolver_dependency)
                logger.debug(f"添加依赖到解析器: {task_id} -> {dep_task_id}")
            except Exception as e:
                logger.error(f"添加依赖到解析器失败: {e}")
                # 如果解析器添加失败，从本地存储中移除
                self.dependencies[task_id].remove(dependency)
                if not self.dependencies[task_id]:
                    del self.dependencies[task_id]
                self.dependents[dep_task_id].remove(task_id)
                if not self.dependents[dep_task_id]:
                    del self.dependents[dep_task_id]
                raise

    def mark_task_completed(self, task_id: str):
        """标记任务完成"""
        with self._lock:
            self.completed_tasks.add(task_id)
            # 同步到依赖解析器
            self.dependency_resolver.mark_task_completed(task_id)

    def mark_task_failed(self, task_id: str):
        """标记任务失败"""
        with self._lock:
            # 同步到依赖解析器
            self.dependency_resolver.mark_task_failed(task_id)

    def mark_task_cancelled(self, task_id: str):
        """标记任务取消"""
        with self._lock:
            # 同步到依赖解析器
            self.dependency_resolver.mark_task_cancelled(task_id)

    def get_ready_tasks(self, task_ids: List[str]) -> List[str]:
        """获取准备好执行的任务（使用依赖解析器）"""
        with self._lock:
            try:
                # 使用依赖解析器获取准备好的任务
                ready_tasks = self.dependency_resolver.get_ready_tasks(task_ids)
                logger.debug(f"依赖解析器返回准备好的任务: {ready_tasks}")
                return ready_tasks
            except Exception as e:
                logger.error(f"依赖解析器获取准备任务失败，使用简单逻辑: {e}")
                # 回退到简单逻辑
                return self._get_ready_tasks_simple(task_ids)

    def _get_ready_tasks_simple(self, task_ids: List[str]) -> List[str]:
        """简单的准备任务检查（回退逻辑）"""
        ready_tasks = []

        for task_id in task_ids:
            dependencies = self.dependencies.get(task_id, [])

            # 检查所有依赖是否已完成
            all_deps_completed = all(
                dep.dependency_task_id in self.completed_tasks
                for dep in dependencies
            )

            if all_deps_completed:
                ready_tasks.append(task_id)

        return ready_tasks

    def get_dependent_tasks(self, task_id: str) -> List[str]:
        """获取依赖指定任务的任务列表"""
        with self._lock:
            return self.dependents.get(task_id, []).copy()

    def get_topological_order(self, task_ids: List[str]) -> List[str]:
        """获取拓扑排序顺序"""
        try:
            return self.dependency_resolver.get_topological_order(task_ids)
        except Exception as e:
            logger.error(f"获取拓扑排序失败: {e}")
            return task_ids  # 返回原始顺序

    def detect_deadlocks(self) -> List[List[str]]:
        """检测死锁"""
        try:
            return self.dependency_resolver.detect_deadlocks()
        except Exception as e:
            logger.error(f"检测死锁失败: {e}")
            return []

    def validate_dependencies(self) -> Dict[str, Any]:
        """验证依赖关系"""
        try:
            return self.dependency_resolver.validate_dependency_graph()
        except Exception as e:
            logger.error(f"验证依赖关系失败: {e}")
            return {'is_valid': False, 'issues': [str(e)], 'warnings': []}


class ImportOrchestrationService:
    """
    导入任务编排服务

    功能特性：
    1. 任务调度和协调
    2. 优先级管理
    3. 资源管理和分配
    4. 依赖关系处理
    5. 故障恢复和重试
    6. 性能监控和优化
    7. 可扩展的工作器管理
    """

    def __init__(self, max_workers: int = 4,
                 scheduling_strategy: SchedulingStrategy = SchedulingStrategy.PRIORITY):
        """
        初始化编排服务

        Args:
            max_workers: 最大工作器数量
            scheduling_strategy: 调度策略
        """
        self.max_workers = max_workers
        self.scheduling_strategy = scheduling_strategy

        # 核心组件
        self.task_scheduler = TaskScheduler(scheduling_strategy)
        self.resource_manager = ResourceManager()
        self.dependency_manager = DependencyManager()

        # 依赖解析器（通过dependency_manager访问）
        self.dependency_resolver = self.dependency_manager.dependency_resolver

        # 工作器管理
        self.workers: Dict[str, WorkerInfo] = {}
        self.import_engines: Dict[str, UnifiedDataImportEngine] = {}
        self._worker_lock = threading.RLock()

        # 任务管理
        self.active_tasks: Dict[str, OrchestrationTask] = {}
        self.completed_tasks: Dict[str, OrchestrationTask] = {}
        self.failed_tasks: Dict[str, OrchestrationTask] = {}
        self._task_lock = threading.RLock()

        # 服务状态
        self._running = False
        self._scheduler_thread = None
        self._monitor_thread = None

        # 统计信息
        self._stats = {
            'total_tasks_submitted': 0,
            'total_tasks_completed': 0,
            'total_tasks_failed': 0,
            'average_execution_time': 0.0,
            'average_queue_time': 0.0,
            'resource_utilization': {}
        }

        # 任务状态管理器
        self.task_status_manager = get_task_status_manager()

        # 初始化默认工作器
        self._init_default_workers()

        logger.info(f"导入任务编排服务初始化完成 - 最大工作器数: {max_workers}, 调度策略: {scheduling_strategy.value}")

    def _init_default_workers(self):
        """初始化默认工作器"""
        for i in range(self.max_workers):
            worker_id = f"worker_{i}"

            # 创建工作器信息
            worker = WorkerInfo(
                worker_id=worker_id,
                worker_type="unified_import",
                max_concurrent_tasks=1,
                available_resources={
                    ResourceType.CPU: 25.0,
                    ResourceType.MEMORY: 25.0,
                    ResourceType.NETWORK: 25.0,
                    ResourceType.STORAGE: 25.0,
                    ResourceType.DATABASE_CONNECTION: 2.0,
                    ResourceType.API_QUOTA: 250.0
                },
                capabilities=["kline_import", "fundamental_import", "realtime_import"]
            )

            # 创建导入引擎
            import_engine = UnifiedDataImportEngine(
                max_workers=1,
                enable_ai_optimization=True,
                enable_intelligent_config=True
            )

            with self._worker_lock:
                self.workers[worker_id] = worker
                self.import_engines[worker_id] = import_engine

        logger.info(f"初始化了 {self.max_workers} 个默认工作器")

    def start(self):
        """启动编排服务"""
        if self._running:
            logger.warning("编排服务已在运行")
            return

        self._running = True

        # 启动调度线程
        self._scheduler_thread = threading.Thread(
            target=self._scheduler_loop,
            name="OrchestrationScheduler",
            daemon=True
        )
        self._scheduler_thread.start()

        # 启动监控线程
        self._monitor_thread = threading.Thread(
            target=self._monitor_loop,
            name="OrchestrationMonitor",
            daemon=True
        )
        self._monitor_thread.start()

        logger.info("导入任务编排服务已启动")

    def stop(self):
        """停止编排服务"""
        if not self._running:
            return

        logger.info("正在停止导入任务编排服务...")

        self._running = False

        # 等待线程结束
        if self._scheduler_thread and self._scheduler_thread.is_alive():
            self._scheduler_thread.join(timeout=5)

        if self._monitor_thread and self._monitor_thread.is_alive():
            self._monitor_thread.join(timeout=5)

        # 关闭所有导入引擎
        with self._worker_lock:
            for engine in self.import_engines.values():
                try:
                    engine.shutdown()
                except Exception as e:
                    logger.warning(f"关闭导入引擎失败: {e}")

        logger.info("导入任务编排服务已停止")

    def submit_task(self, import_task: UnifiedImportTask,
                    priority: TaskPriority = TaskPriority.NORMAL,
                    deadline: Optional[datetime] = None,
                    dependencies: Optional[List[TaskDependency]] = None,
                    resource_requirements: Optional[List[ResourceRequirement]] = None) -> str:
        """
        提交导入任务

        Args:
            import_task: 导入任务
            priority: 任务优先级
            deadline: 截止时间
            dependencies: 依赖关系
            resource_requirements: 资源需求

        Returns:
            str: 任务ID
        """
        try:
            # 创建编排任务
            orchestration_task = OrchestrationTask(
                task_id=import_task.task_id,
                import_task=import_task,
                priority=priority,
                deadline=deadline,
                dependencies=dependencies or [],
                resource_requirements=resource_requirements or []
            )

            # 添加依赖关系
            for dep in orchestration_task.dependencies:
                try:
                    self.dependency_manager.add_dependency(dep)
                except Exception as e:
                    logger.error(f"添加依赖关系失败: {e}")
                    # 如果有循环依赖等问题，拒绝任务
                    raise ValueError(f"任务依赖关系无效: {e}")

            # 在任务状态管理器中创建任务
            self.task_status_manager.create_task(
                task_id=orchestration_task.task_id,
                priority=priority,
                timeout_seconds=import_task.timeout,
                max_retries=orchestration_task.max_retries
            )

            # 添加到调度队列
            self.task_scheduler.add_task(orchestration_task)

            # 更新统计
            self._stats['total_tasks_submitted'] += 1

            logger.info(f"提交导入任务: {orchestration_task.task_id} (优先级: {priority.name})")

            return orchestration_task.task_id

        except Exception as e:
            logger.error(f"提交导入任务失败: {e}")
            raise

    def cancel_task(self, task_id: str) -> bool:
        """取消任务"""
        try:
            # 从调度队列移除
            removed = self.task_scheduler.remove_task(task_id)

            # 如果任务正在执行，停止执行
            with self._task_lock:
                if task_id in self.active_tasks:
                    task = self.active_tasks[task_id]
                    if task.assigned_worker:
                        engine = self.import_engines.get(task.assigned_worker)
                        if engine:
                            engine.cancel_import_task(task_id, "用户取消")

                    del self.active_tasks[task_id]
                    removed = True

            # 更新任务状态
            if removed:
                self.task_status_manager.update_status(
                    task_id, TaskStatus.CANCELLED, "任务已取消"
                )
                # 标记任务取消
                self.dependency_manager.mark_task_cancelled(task_id)

            logger.info(f"取消任务: {task_id}")
            return removed

        except Exception as e:
            logger.error(f"取消任务失败 {task_id}: {e}")
            return False

    def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """获取任务状态"""
        # 从任务状态管理器获取状态
        status_info = self.task_status_manager.get_task_status(task_id)
        if not status_info:
            return None

        # 获取编排任务信息
        orchestration_task = None
        with self._task_lock:
            orchestration_task = (
                self.active_tasks.get(task_id) or
                self.completed_tasks.get(task_id) or
                self.failed_tasks.get(task_id)
            )

        result = {
            'task_id': task_id,
            'status': status_info.status.value,
            'priority': status_info.priority.name,
            'progress': status_info.progress,
            'message': status_info.message,
            'created_time': status_info.created_time.isoformat(),
            'updated_time': status_info.updated_time.isoformat()
        }

        if orchestration_task:
            result.update({
                'assigned_worker': orchestration_task.assigned_worker,
                'execution_time': orchestration_task.execution_time,
                'retry_count': orchestration_task.retry_count,
                'max_retries': orchestration_task.max_retries
            })

        return result

    def get_queue_status(self) -> Dict[str, Any]:
        """获取队列状态"""
        scheduled_tasks = self.task_scheduler.get_scheduled_tasks()

        with self._task_lock:
            return {
                'queued_tasks': len(scheduled_tasks),
                'active_tasks': len(self.active_tasks),
                'completed_tasks': len(self.completed_tasks),
                'failed_tasks': len(self.failed_tasks),
                'queue_by_priority': self._count_tasks_by_priority(scheduled_tasks),
                'resource_usage': self.resource_manager.get_resource_usage()
            }

    def _count_tasks_by_priority(self, tasks: List[OrchestrationTask]) -> Dict[str, int]:
        """按优先级统计任务数量"""
        counts = {priority.name: 0 for priority in TaskPriority}
        for task in tasks:
            counts[task.priority.name] += 1
        return counts

    def get_worker_status(self) -> Dict[str, Dict[str, Any]]:
        """获取工作器状态"""
        with self._worker_lock:
            return {
                worker_id: {
                    'status': worker.status,
                    'current_tasks': worker.current_tasks,
                    'max_concurrent_tasks': worker.max_concurrent_tasks,
                    'available_resources': {
                        rt.value: amount for rt, amount in worker.available_resources.items()
                    },
                    'last_heartbeat': worker.last_heartbeat.isoformat()
                }
                for worker_id, worker in self.workers.items()
            }

    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        stats = self._stats.copy()
        stats['resource_utilization'] = self.resource_manager.get_resource_usage()

        # 计算成功率
        total_finished = stats['total_tasks_completed'] + stats['total_tasks_failed']
        if total_finished > 0:
            stats['success_rate'] = (stats['total_tasks_completed'] / total_finished) * 100
        else:
            stats['success_rate'] = 0.0

        # 添加依赖解析器统计
        try:
            dependency_stats = self.dependency_resolver.get_statistics()
            stats['dependency_statistics'] = dependency_stats
        except Exception as e:
            logger.error(f"获取依赖统计失败: {e}")
            stats['dependency_statistics'] = {}

        return stats

    def validate_task_dependencies(self) -> Dict[str, Any]:
        """验证任务依赖关系"""
        return self.dependency_manager.validate_dependencies()

    def get_task_dependency_chain(self, task_id: str) -> List[str]:
        """获取任务的完整依赖链"""
        try:
            return self.dependency_resolver.get_dependency_chain(task_id)
        except Exception as e:
            logger.error(f"获取任务依赖链失败: {e}")
            return [task_id]

    def detect_potential_deadlocks(self) -> List[List[str]]:
        """检测潜在的死锁"""
        return self.dependency_manager.detect_deadlocks()

    def add_task_dependency(self, dependent_task_id: str, prerequisite_task_id: str,
                            dependency_type: str = "completion", condition: Optional[str] = None) -> bool:
        """动态添加任务依赖关系"""
        try:
            dependency = TaskDependency(
                task_id=dependent_task_id,
                dependency_task_id=prerequisite_task_id,
                dependency_type=dependency_type,
                condition=condition
            )
            self.dependency_manager.add_dependency(dependency)
            logger.info(f"动态添加依赖关系: {dependent_task_id} -> {prerequisite_task_id}")
            return True
        except Exception as e:
            logger.error(f"动态添加依赖关系失败: {e}")
            return False

    def get_task_dependencies(self, task_id: str) -> List[Dict[str, Any]]:
        """获取任务的所有依赖关系"""
        try:
            dependencies = self.dependency_resolver.get_task_dependencies(task_id)
            return [
                {
                    'prerequisite_task_id': dep.prerequisite_task_id,
                    'dependency_type': dep.dependency_type.value,
                    'condition': dep.condition,
                    'status': dep.status.value,
                    'created_at': dep.created_at.isoformat(),
                    'satisfied_at': dep.satisfied_at.isoformat() if dep.satisfied_at else None
                }
                for dep in dependencies
            ]
        except Exception as e:
            logger.error(f"获取任务依赖关系失败: {e}")
            return []

    def _scheduler_loop(self):
        """调度循环"""
        while self._running:
            try:
                self._schedule_tasks()
                time.sleep(1)  # 每秒检查一次

            except Exception as e:
                logger.error(f"调度循环出错: {e}")
                time.sleep(5)  # 出错后等待5秒

    def _schedule_tasks(self):
        """调度任务（集成依赖解析）"""
        with self._worker_lock:
            available_workers = [
                (worker_id, worker) for worker_id, worker in self.workers.items()
                if worker.is_available
            ]

        # 获取所有调度中的任务
        scheduled_tasks = self.task_scheduler.get_scheduled_tasks()
        scheduled_task_ids = [task.task_id for task in scheduled_tasks]

        # 使用依赖解析器获取准备好的任务
        ready_task_ids = self.dependency_manager.get_ready_tasks(scheduled_task_ids)

        # 按拓扑顺序排序
        if ready_task_ids:
            ready_task_ids = self.dependency_manager.get_topological_order(ready_task_ids)

        for worker_id, worker in available_workers:
            if not ready_task_ids:
                break

            # 获取下一个可执行的任务
            task = self.task_scheduler.get_next_task(worker)
            if not task:
                continue

            # 检查任务是否在准备好的列表中
            if task.task_id not in ready_task_ids:
                # 任务依赖未满足，将任务放回队列
                self.task_scheduler.add_task(task)
                continue

            # 从准备列表中移除
            ready_task_ids.remove(task.task_id)

            # 分配资源
            if not self.resource_manager.allocate_resources(task.task_id, task.resource_requirements):
                # 资源不足，将任务放回队列
                self.task_scheduler.add_task(task)
                continue

            # 分配任务给工作器
            self._assign_task_to_worker(task, worker_id)

    def _assign_task_to_worker(self, task: OrchestrationTask, worker_id: str):
        """将任务分配给工作器"""
        try:
            task.assigned_worker = worker_id
            task.execution_start_time = datetime.now()

            # 更新工作器状态
            with self._worker_lock:
                self.workers[worker_id].current_tasks += 1

            # 添加到活跃任务
            with self._task_lock:
                self.active_tasks[task.task_id] = task

            # 更新任务状态
            self.task_status_manager.update_status(
                task.task_id, TaskStatus.RUNNING, f"分配给工作器 {worker_id}"
            )

            # 启动任务执行
            engine = self.import_engines[worker_id]

            # 创建导入任务并启动
            engine.create_import_task(task.import_task)
            success = engine.start_import_task(task.task_id, use_async=True)

            if not success:
                self._handle_task_failure(task, "启动任务失败")

            logger.info(f"任务 {task.task_id} 分配给工作器 {worker_id}")

        except Exception as e:
            logger.error(f"分配任务失败: {e}")
            self._handle_task_failure(task, str(e))

    def _handle_task_completion(self, task: OrchestrationTask):
        """处理任务完成"""
        try:
            task.execution_end_time = datetime.now()

            # 释放资源
            self.resource_manager.release_resources(task.task_id)

            # 更新工作器状态
            if task.assigned_worker:
                with self._worker_lock:
                    worker = self.workers.get(task.assigned_worker)
                    if worker:
                        worker.current_tasks = max(0, worker.current_tasks - 1)

            # 移动到完成任务
            with self._task_lock:
                if task.task_id in self.active_tasks:
                    del self.active_tasks[task.task_id]
                self.completed_tasks[task.task_id] = task

            # 标记依赖完成
            self.dependency_manager.mark_task_completed(task.task_id)

            # 检查是否有死锁
            deadlocks = self.dependency_manager.detect_deadlocks()
            if deadlocks:
                logger.warning(f"检测到死锁: {deadlocks}")

            # 更新统计
            self._stats['total_tasks_completed'] += 1
            if task.execution_time:
                total_completed = self._stats['total_tasks_completed']
                current_avg = self._stats['average_execution_time']
                self._stats['average_execution_time'] = (
                    (current_avg * (total_completed - 1) + task.execution_time) / total_completed
                )

            logger.info(f"任务完成: {task.task_id}")

        except Exception as e:
            logger.error(f"处理任务完成失败: {e}")

    def _handle_task_failure(self, task: OrchestrationTask, error_message: str):
        """处理任务失败"""
        try:
            task.execution_end_time = datetime.now()

            # 释放资源
            self.resource_manager.release_resources(task.task_id)

            # 更新工作器状态
            if task.assigned_worker:
                with self._worker_lock:
                    worker = self.workers.get(task.assigned_worker)
                    if worker:
                        worker.current_tasks = max(0, worker.current_tasks - 1)

            # 检查是否需要重试
            if task.retry_count < task.max_retries:
                task.retry_count += 1
                task.assigned_worker = None
                task.execution_start_time = None
                task.execution_end_time = None

                # 重新加入调度队列
                self.task_scheduler.add_task(task)

                self.task_status_manager.update_status(
                    task.task_id, TaskStatus.PENDING,
                    f"重试 {task.retry_count}/{task.max_retries}: {error_message}"
                )

                logger.info(f"任务重试: {task.task_id} ({task.retry_count}/{task.max_retries})")
            else:
                # 移动到失败任务
                with self._task_lock:
                    if task.task_id in self.active_tasks:
                        del self.active_tasks[task.task_id]
                    self.failed_tasks[task.task_id] = task

                self.task_status_manager.update_status(
                    task.task_id, TaskStatus.FAILED, error_message
                )

                # 标记任务失败
                self.dependency_manager.mark_task_failed(task.task_id)

                # 更新统计
                self._stats['total_tasks_failed'] += 1

                logger.error(f"任务失败: {task.task_id} - {error_message}")

        except Exception as e:
            logger.error(f"处理任务失败失败: {e}")

    def _monitor_loop(self):
        """监控循环"""
        while self._running:
            try:
                self._monitor_tasks()
                self._monitor_workers()
                time.sleep(10)  # 每10秒监控一次

            except Exception as e:
                logger.error(f"监控循环出错: {e}")
                time.sleep(30)  # 出错后等待30秒

    def _monitor_tasks(self):
        """监控任务状态"""
        current_time = datetime.now()

        with self._task_lock:
            for task_id, task in list(self.active_tasks.items()):
                # 检查任务超时
                if (task.deadline and current_time > task.deadline):
                    self._handle_task_failure(task, "任务超时")
                    continue

                # 检查任务状态
                if task.assigned_worker:
                    engine = self.import_engines.get(task.assigned_worker)
                    if engine:
                        result = engine.get_task_result(task_id)
                        if result:
                            if result.success:
                                self._handle_task_completion(task)
                            elif result.status.name in ['FAILED', 'CANCELLED', 'TIMEOUT']:
                                self._handle_task_failure(task, result.error_message or "任务执行失败")

    def _monitor_workers(self):
        """监控工作器状态"""
        current_time = datetime.now()

        with self._worker_lock:
            for worker_id, worker in self.workers.items():
                # 检查心跳超时
                if (current_time - worker.last_heartbeat).total_seconds() > 300:  # 5分钟超时
                    if worker.status == "active":
                        worker.status = "offline"
                        logger.warning(f"工作器 {worker_id} 心跳超时，标记为离线")


# 全局单例实例
_orchestration_service: Optional[ImportOrchestrationService] = None
_service_lock = threading.Lock()


def get_orchestration_service() -> ImportOrchestrationService:
    """获取全局编排服务实例"""
    global _orchestration_service

    if _orchestration_service is None:
        with _service_lock:
            if _orchestration_service is None:
                _orchestration_service = ImportOrchestrationService()

    return _orchestration_service


def initialize_orchestration_service(max_workers: int = 4,
                                     scheduling_strategy: SchedulingStrategy = SchedulingStrategy.PRIORITY) -> ImportOrchestrationService:
    """初始化全局编排服务"""
    global _orchestration_service

    with _service_lock:
        if _orchestration_service is not None:
            _orchestration_service.stop()

        _orchestration_service = ImportOrchestrationService(
            max_workers=max_workers,
            scheduling_strategy=scheduling_strategy
        )

    return _orchestration_service
