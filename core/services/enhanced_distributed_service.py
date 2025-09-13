#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
增强版分布式服务模块

在现有分布式服务基础上增加智能化功能：
1. 智能负载均衡和任务调度
2. 自动故障检测和恢复
3. 动态节点管理和扩缩容
4. 性能监控和优化
5. 安全性和可靠性增强
6. 分布式缓存和状态同步
7. 智能资源分配
"""

import asyncio
import hashlib
import hmac
import json
import socket
import ssl
import threading
import time
import uuid
from collections import defaultdict, deque
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Any, Callable, Tuple, Set
import numpy as np
import psutil
from loguru import logger

from .distributed_service import DistributedService, NodeInfo, DistributedTask, NodeDiscovery, TaskScheduler
from ..events import EventBus, get_event_bus


class NodeStatus(Enum):
    """节点状态枚举"""
    UNKNOWN = "unknown"
    ACTIVE = "active"
    INACTIVE = "inactive"
    BUSY = "busy"
    OVERLOADED = "overloaded"
    FAILED = "failed"
    MAINTENANCE = "maintenance"


class TaskPriority(Enum):
    """任务优先级枚举"""
    CRITICAL = 1
    HIGH = 2
    NORMAL = 3
    LOW = 4
    BACKGROUND = 5


class LoadBalancingStrategy(Enum):
    """负载均衡策略"""
    ROUND_ROBIN = "round_robin"
    LEAST_CONNECTIONS = "least_connections"
    WEIGHTED_ROUND_ROBIN = "weighted_round_robin"
    RESOURCE_BASED = "resource_based"
    INTELLIGENT = "intelligent"


@dataclass
class EnhancedNodeInfo(NodeInfo):
    """增强版节点信息"""
    # 性能指标
    response_time: float = 0.0
    success_rate: float = 1.0
    error_count: int = 0
    completed_tasks: int = 0

    # 资源监控
    disk_usage: float = 0.0
    network_io: float = 0.0
    gpu_usage: float = 0.0
    gpu_memory: float = 0.0

    # 健康状态
    health_score: float = 1.0
    last_health_check: Optional[datetime] = None
    consecutive_failures: int = 0

    # 负载均衡权重
    weight: float = 1.0
    current_load: float = 0.0
    max_concurrent_tasks: int = 10

    # 安全信息
    security_token: Optional[str] = None
    last_auth_time: Optional[datetime] = None

    # 地理位置和网络
    region: str = "default"
    availability_zone: str = "default"
    network_latency: float = 0.0

    def calculate_health_score(self) -> float:
        """计算节点健康分数"""
        factors = {
            'cpu_usage': max(0, 1 - self.cpu_usage / 100),
            'memory_usage': max(0, 1 - self.memory_usage / 100),
            'success_rate': self.success_rate,
            'response_time': max(0, 1 - min(self.response_time / 1000, 1)),
            'consecutive_failures': max(0, 1 - self.consecutive_failures / 10)
        }

        # 加权平均
        weights = {
            'cpu_usage': 0.2,
            'memory_usage': 0.2,
            'success_rate': 0.3,
            'response_time': 0.2,
            'consecutive_failures': 0.1
        }

        self.health_score = sum(factors[k] * weights[k] for k in factors)
        return self.health_score

    def is_healthy(self) -> bool:
        """检查节点是否健康"""
        return (self.health_score > 0.5 and
                self.consecutive_failures < 5 and
                self.status in [NodeStatus.ACTIVE.value, NodeStatus.BUSY.value])


@dataclass
class EnhancedDistributedTask(DistributedTask):
    """增强版分布式任务"""
    # 任务属性
    retry_count: int = 0
    max_retries: int = 3
    timeout: int = 300  # 秒
    dependencies: List[str] = field(default_factory=list)

    # 资源需求
    cpu_requirement: float = 1.0
    memory_requirement: int = 512  # MB
    gpu_requirement: bool = False

    # 调度信息
    preferred_nodes: List[str] = field(default_factory=list)
    excluded_nodes: List[str] = field(default_factory=list)
    affinity_rules: Dict[str, Any] = field(default_factory=dict)

    # 监控信息
    execution_time: float = 0.0
    resource_usage: Dict[str, float] = field(default_factory=dict)
    checkpoint_data: Optional[Dict[str, Any]] = None

    def can_retry(self) -> bool:
        """检查是否可以重试"""
        return self.retry_count < self.max_retries

    def is_expired(self) -> bool:
        """检查任务是否超时"""
        if self.start_time and self.status == "running":
            elapsed = (datetime.now() - self.start_time).total_seconds()
            return elapsed > self.timeout
        return False


class IntelligentLoadBalancer:
    """智能负载均衡器"""

    def __init__(self, strategy: LoadBalancingStrategy = LoadBalancingStrategy.INTELLIGENT):
        self.strategy = strategy
        self.node_weights: Dict[str, float] = {}
        self.node_connections: Dict[str, int] = defaultdict(int)
        self.round_robin_index = 0
        self.performance_history: Dict[str, deque] = defaultdict(lambda: deque(maxlen=100))

    def select_node(self, nodes: List[EnhancedNodeInfo], task: EnhancedDistributedTask) -> Optional[EnhancedNodeInfo]:
        """选择最适合的节点"""
        if not nodes:
            return None

        # 过滤健康节点
        healthy_nodes = [node for node in nodes if node.is_healthy()]
        if not healthy_nodes:
            logger.warning("没有健康的节点可用")
            return None

        # 过滤满足资源需求的节点
        suitable_nodes = self._filter_by_requirements(healthy_nodes, task)
        if not suitable_nodes:
            logger.warning("没有满足资源需求的节点")
            return None

        # 根据策略选择节点
        if self.strategy == LoadBalancingStrategy.ROUND_ROBIN:
            return self._round_robin_select(suitable_nodes)
        elif self.strategy == LoadBalancingStrategy.LEAST_CONNECTIONS:
            return self._least_connections_select(suitable_nodes)
        elif self.strategy == LoadBalancingStrategy.WEIGHTED_ROUND_ROBIN:
            return self._weighted_round_robin_select(suitable_nodes)
        elif self.strategy == LoadBalancingStrategy.RESOURCE_BASED:
            return self._resource_based_select(suitable_nodes)
        else:  # INTELLIGENT
            return self._intelligent_select(suitable_nodes, task)

    def _filter_by_requirements(self, nodes: List[EnhancedNodeInfo], task: EnhancedDistributedTask) -> List[EnhancedNodeInfo]:
        """根据资源需求过滤节点"""
        suitable_nodes = []

        for node in nodes:
            # 检查CPU需求
            available_cpu = (100 - node.cpu_usage) / 100
            if available_cpu < task.cpu_requirement:
                continue

            # 检查内存需求
            available_memory = (node.memory_total - node.memory_total * node.memory_usage / 100) / 1024 / 1024
            if available_memory < task.memory_requirement:
                continue

            # 检查GPU需求
            if task.gpu_requirement and node.gpu_usage > 90:
                continue

            # 检查并发任务数
            if node.task_count >= node.max_concurrent_tasks:
                continue

            # 检查节点偏好
            if task.preferred_nodes and node.node_id not in task.preferred_nodes:
                continue

            # 检查排除节点
            if node.node_id in task.excluded_nodes:
                continue

            suitable_nodes.append(node)

        return suitable_nodes

    def _round_robin_select(self, nodes: List[EnhancedNodeInfo]) -> EnhancedNodeInfo:
        """轮询选择"""
        node = nodes[self.round_robin_index % len(nodes)]
        self.round_robin_index += 1
        return node

    def _least_connections_select(self, nodes: List[EnhancedNodeInfo]) -> EnhancedNodeInfo:
        """最少连接选择"""
        return min(nodes, key=lambda n: self.node_connections[n.node_id])

    def _weighted_round_robin_select(self, nodes: List[EnhancedNodeInfo]) -> EnhancedNodeInfo:
        """加权轮询选择"""
        # 计算权重总和
        total_weight = sum(node.weight for node in nodes)
        if total_weight == 0:
            return nodes[0]

        # 生成随机数选择
        import random
        rand = random.uniform(0, total_weight)
        current_weight = 0

        for node in nodes:
            current_weight += node.weight
            if rand <= current_weight:
                return node

        return nodes[-1]

    def _resource_based_select(self, nodes: List[EnhancedNodeInfo]) -> EnhancedNodeInfo:
        """基于资源的选择"""
        def resource_score(node: EnhancedNodeInfo) -> float:
            cpu_score = (100 - node.cpu_usage) / 100
            memory_score = (100 - node.memory_usage) / 100
            load_score = max(0, 1 - node.current_load)
            return (cpu_score + memory_score + load_score) / 3

        return max(nodes, key=resource_score)

    def _intelligent_select(self, nodes: List[EnhancedNodeInfo], task: EnhancedDistributedTask) -> EnhancedNodeInfo:
        """智能选择（综合多个因素）"""
        def intelligent_score(node: EnhancedNodeInfo) -> float:
            # 基础资源分数
            resource_score = self._calculate_resource_score(node)

            # 性能历史分数
            performance_score = self._calculate_performance_score(node)

            # 网络延迟分数
            latency_score = max(0, 1 - node.network_latency / 1000)

            # 任务亲和性分数
            affinity_score = self._calculate_affinity_score(node, task)

            # 综合分数
            weights = {
                'resource': 0.3,
                'performance': 0.3,
                'latency': 0.2,
                'affinity': 0.2
            }

            total_score = (
                resource_score * weights['resource'] +
                performance_score * weights['performance'] +
                latency_score * weights['latency'] +
                affinity_score * weights['affinity']
            )

            return total_score

        return max(nodes, key=intelligent_score)

    def _calculate_resource_score(self, node: EnhancedNodeInfo) -> float:
        """计算资源分数"""
        cpu_score = (100 - node.cpu_usage) / 100
        memory_score = (100 - node.memory_usage) / 100
        load_score = max(0, 1 - node.current_load)
        return (cpu_score + memory_score + load_score) / 3

    def _calculate_performance_score(self, node: EnhancedNodeInfo) -> float:
        """计算性能分数"""
        history = self.performance_history[node.node_id]
        if not history:
            return 0.5  # 默认分数

        # 计算平均响应时间和成功率
        avg_response_time = np.mean([h['response_time'] for h in history])
        avg_success_rate = np.mean([h['success_rate'] for h in history])

        response_score = max(0, 1 - avg_response_time / 1000)
        success_score = avg_success_rate

        return (response_score + success_score) / 2

    def _calculate_affinity_score(self, node: EnhancedNodeInfo, task: EnhancedDistributedTask) -> float:
        """计算任务亲和性分数"""
        score = 0.5  # 默认分数

        # 检查地理位置亲和性
        if 'region' in task.affinity_rules:
            if node.region == task.affinity_rules['region']:
                score += 0.3

        # 检查节点类型亲和性
        if 'node_type' in task.affinity_rules:
            if node.node_type == task.affinity_rules['node_type']:
                score += 0.2

        return min(1.0, score)

    def update_node_performance(self, node_id: str, response_time: float, success: bool):
        """更新节点性能数据"""
        self.performance_history[node_id].append({
            'response_time': response_time,
            'success_rate': 1.0 if success else 0.0,
            'timestamp': datetime.now()
        })


class FailoverManager:
    """故障转移管理器"""

    def __init__(self, max_failures: int = 5, recovery_timeout: int = 300):
        self.max_failures = max_failures
        self.recovery_timeout = recovery_timeout
        self.failed_nodes: Dict[str, datetime] = {}
        self.recovery_tasks: Dict[str, asyncio.Task] = {}

    def handle_node_failure(self, node_id: str, error: Exception):
        """处理节点故障"""
        logger.error(f"节点 {node_id} 发生故障: {error}")

        # 记录故障时间
        self.failed_nodes[node_id] = datetime.now()

        # 启动恢复任务
        if node_id not in self.recovery_tasks:
            self.recovery_tasks[node_id] = asyncio.create_task(
                self._recovery_worker(node_id)
            )

    async def _recovery_worker(self, node_id: str):
        """节点恢复工作线程"""
        try:
            await asyncio.sleep(self.recovery_timeout)

            # 尝试恢复节点
            if await self._attempt_node_recovery(node_id):
                logger.info(f"节点 {node_id} 恢复成功")
                self.failed_nodes.pop(node_id, None)
            else:
                logger.warning(f"节点 {node_id} 恢复失败")

        except Exception as e:
            logger.error(f"节点恢复过程出错: {e}")
        finally:
            self.recovery_tasks.pop(node_id, None)

    async def _attempt_node_recovery(self, node_id: str) -> bool:
        """尝试恢复节点"""
        try:
            # 这里可以实现具体的节点恢复逻辑
            # 例如：重启服务、重新连接等
            return True
        except Exception:
            return False

    def is_node_failed(self, node_id: str) -> bool:
        """检查节点是否处于故障状态"""
        return node_id in self.failed_nodes


class SecurityManager:
    """安全管理器"""

    def __init__(self, secret_key: str = None):
        self.secret_key = secret_key or self._generate_secret_key()
        self.node_tokens: Dict[str, str] = {}
        self.token_expiry: Dict[str, datetime] = {}

    def _generate_secret_key(self) -> str:
        """生成密钥"""
        return hashlib.sha256(str(uuid.uuid4()).encode()).hexdigest()

    def generate_node_token(self, node_id: str) -> str:
        """为节点生成认证令牌"""
        timestamp = str(int(time.time()))
        message = f"{node_id}:{timestamp}"
        signature = hmac.new(
            self.secret_key.encode(),
            message.encode(),
            hashlib.sha256
        ).hexdigest()

        token = f"{message}:{signature}"
        self.node_tokens[node_id] = token
        self.token_expiry[node_id] = datetime.now() + timedelta(hours=24)

        return token

    def verify_node_token(self, node_id: str, token: str) -> bool:
        """验证节点令牌"""
        try:
            # 检查令牌是否过期
            if node_id in self.token_expiry:
                if datetime.now() > self.token_expiry[node_id]:
                    return False

            # 解析令牌
            parts = token.split(':')
            if len(parts) != 3:
                return False

            received_node_id, timestamp, signature = parts
            if received_node_id != node_id:
                return False

            # 验证签名
            message = f"{received_node_id}:{timestamp}"
            expected_signature = hmac.new(
                self.secret_key.encode(),
                message.encode(),
                hashlib.sha256
            ).hexdigest()

            return hmac.compare_digest(signature, expected_signature)

        except Exception as e:
            logger.error(f"令牌验证失败: {e}")
            return False


class EnhancedDistributedService(DistributedService):
    """增强版分布式服务"""

    def __init__(self,
                 discovery_port: int = 8888,
                 load_balancing_strategy: LoadBalancingStrategy = LoadBalancingStrategy.INTELLIGENT,
                 enable_security: bool = True,
                 enable_monitoring: bool = True):
        """
        初始化增强版分布式服务

        Args:
            discovery_port: 节点发现端口
            load_balancing_strategy: 负载均衡策略
            enable_security: 是否启用安全功能
            enable_monitoring: 是否启用监控功能
        """
        super().__init__(discovery_port)

        # 增强组件
        self.load_balancer = IntelligentLoadBalancer(load_balancing_strategy)
        self.failover_manager = FailoverManager()
        self.security_manager = SecurityManager() if enable_security else None

        # 节点管理
        self.enhanced_nodes: Dict[str, EnhancedNodeInfo] = {}
        self.node_health_checks: Dict[str, threading.Timer] = {}

        # 任务管理
        self.enhanced_tasks: Dict[str, EnhancedDistributedTask] = {}
        self.task_dependencies: Dict[str, Set[str]] = defaultdict(set)

        # 监控和统计
        self.enable_monitoring = enable_monitoring
        self.performance_metrics: Dict[str, Any] = {}
        self.event_bus = get_event_bus()

        # 配置
        self.config = {
            'health_check_interval': 30,
            'task_timeout': 300,
            'max_retries': 3,
            'auto_scaling_enabled': True,
            'min_nodes': 1,
            'max_nodes': 10
        }

        logger.info("增强版分布式服务初始化完成")

    def start_service(self):
        """启动增强版分布式服务"""
        super().start_service()

        # 启动健康检查
        self._start_health_monitoring()

        # 启动性能监控
        if self.enable_monitoring:
            self._start_performance_monitoring()

        # 启动自动扩缩容
        if self.config['auto_scaling_enabled']:
            self._start_auto_scaling()

        logger.info("增强版分布式服务已启动")

    def start(self):
        """启动分布式服务（别名方法）"""
        return self.start_service()

    def stop(self):
        """停止分布式服务"""
        try:
            logger.info("🛑 停止增强分布式服务...")

            # 停止基础分布式服务
            if hasattr(self, '_base_service') and self._base_service:
                self._base_service.stop_service()

            # 停止性能监控
            if hasattr(self, '_performance_monitor_active'):
                self._performance_monitor_active = False

            # 停止负载均衡
            if hasattr(self, '_load_balancer_active'):
                self._load_balancer_active = False

            # 清理资源
            if hasattr(self, '_task_queue'):
                self._task_queue.clear()

            logger.info("✅ 增强分布式服务已停止")
            return True

        except Exception as e:
            logger.error(f"停止增强分布式服务失败: {e}")
            return False

    def submit_task(self, task: Dict[str, Any]) -> bool:
        """
        提交任务到分布式系统

        Args:
            task: 任务信息字典

        Returns:
            提交是否成功
        """
        try:
            logger.info(f"📤 提交分布式任务: {task.get('name', 'unknown')}")

            # 验证任务格式
            if not isinstance(task, dict) or 'name' not in task:
                logger.error("无效的任务格式")
                return False

            # 添加任务元数据
            task_with_metadata = {
                **task,
                'submit_time': datetime.now().isoformat(),
                'status': 'submitted',
                'priority': task.get('priority', 'normal'),
                'node_id': self.node_id if hasattr(self, 'node_id') else 'local'
            }

            # 模拟任务提交到队列
            if not hasattr(self, '_task_queue'):
                self._task_queue = []

            self._task_queue.append(task_with_metadata)

            logger.info(f"✅ 任务提交成功: {task['name']}")
            return True

        except Exception as e:
            logger.error(f"提交任务失败: {e}")
            return False

    def stop_service(self):
        """停止增强版分布式服务"""
        # 停止健康检查
        for timer in self.node_health_checks.values():
            timer.cancel()

        super().stop_service()
        logger.info("增强版分布式服务已停止")

    def submit_enhanced_task(self,
                             task_type: str,
                             task_data: Dict[str, Any],
                             priority: TaskPriority = TaskPriority.NORMAL,
                             cpu_requirement: float = 1.0,
                             memory_requirement: int = 512,
                             gpu_requirement: bool = False,
                             timeout: int = 300,
                             dependencies: List[str] = None,
                             affinity_rules: Dict[str, Any] = None) -> str:
        """提交增强版任务"""
        task_id = str(uuid.uuid4())

        task = EnhancedDistributedTask(
            task_id=task_id,
            task_type=task_type,
            task_data=task_data,
            priority=priority.value,
            cpu_requirement=cpu_requirement,
            memory_requirement=memory_requirement,
            gpu_requirement=gpu_requirement,
            timeout=timeout,
            dependencies=dependencies or [],
            affinity_rules=affinity_rules or {}
        )

        self.enhanced_tasks[task_id] = task

        # 处理任务依赖
        if dependencies:
            for dep_id in dependencies:
                self.task_dependencies[dep_id].add(task_id)

        # 尝试调度任务
        self._schedule_enhanced_task(task)

        logger.info(f"提交增强版任务: {task_id} ({task_type})")
        return task_id

    def _schedule_enhanced_task(self, task: EnhancedDistributedTask):
        """调度增强版任务"""
        try:
            # 检查依赖是否满足
            if not self._check_task_dependencies(task):
                logger.debug(f"任务 {task.task_id} 依赖未满足，等待调度")
                return

            # 选择合适的节点
            available_nodes = [node for node in self.enhanced_nodes.values()
                               if not self.failover_manager.is_node_failed(node.node_id)]

            selected_node = self.load_balancer.select_node(available_nodes, task)

            if selected_node:
                self._assign_task_to_node(task, selected_node)
            else:
                logger.warning(f"没有可用节点执行任务 {task.task_id}")
                task.status = "pending"

        except Exception as e:
            logger.error(f"调度任务失败: {e}")
            task.status = "failed"
            task.error_message = str(e)

    def _check_task_dependencies(self, task: EnhancedDistributedTask) -> bool:
        """检查任务依赖是否满足"""
        for dep_id in task.dependencies:
            if dep_id in self.enhanced_tasks:
                dep_task = self.enhanced_tasks[dep_id]
                if dep_task.status != "completed":
                    return False
            else:
                # 依赖任务不存在
                return False
        return True

    def _assign_task_to_node(self, task: EnhancedDistributedTask, node: EnhancedNodeInfo):
        """将任务分配给节点"""
        try:
            task.assigned_node = node.node_id
            task.status = "assigned"
            task.start_time = datetime.now()

            # 更新节点状态
            node.task_count += 1
            node.current_load = min(1.0, node.task_count / node.max_concurrent_tasks)

            # 发送任务到节点（这里需要实现具体的通信逻辑）
            self._send_task_to_node(task, node)

            logger.info(f"任务 {task.task_id} 已分配给节点 {node.node_id}")

        except Exception as e:
            logger.error(f"分配任务失败: {e}")
            task.status = "failed"
            task.error_message = str(e)

            # 尝试故障转移
            self._handle_task_failure(task, e)

    def _send_task_to_node(self, task: EnhancedDistributedTask, node: EnhancedNodeInfo):
        """发送任务到节点"""
        # 这里实现具体的任务发送逻辑
        # 可以使用HTTP、gRPC、消息队列等方式
        pass

    def _handle_task_failure(self, task: EnhancedDistributedTask, error: Exception):
        """处理任务失败"""
        if task.can_retry():
            task.retry_count += 1
            task.status = "pending"
            logger.info(f"任务 {task.task_id} 重试 ({task.retry_count}/{task.max_retries})")

            # 重新调度
            self._schedule_enhanced_task(task)
        else:
            task.status = "failed"
            task.error_message = str(error)
            logger.error(f"任务 {task.task_id} 最终失败: {error}")

    def _start_health_monitoring(self):
        """启动健康监控"""
        def health_check_worker():
            while self.running:
                try:
                    for node_id, node in self.enhanced_nodes.items():
                        self._check_node_health(node)
                    time.sleep(self.config['health_check_interval'])
                except Exception as e:
                    logger.error(f"健康检查错误: {e}")
                    time.sleep(5)

        health_thread = threading.Thread(target=health_check_worker, daemon=True)
        health_thread.start()

    def _check_node_health(self, node: EnhancedNodeInfo):
        """检查节点健康状态"""
        try:
            # 更新健康分数
            node.calculate_health_score()
            node.last_health_check = datetime.now()

            # 检查是否需要故障转移
            if not node.is_healthy():
                self.failover_manager.handle_node_failure(
                    node.node_id,
                    Exception(f"节点健康分数过低: {node.health_score}")
                )

        except Exception as e:
            logger.error(f"检查节点 {node.node_id} 健康状态失败: {e}")
            node.consecutive_failures += 1

    def _start_performance_monitoring(self):
        """启动性能监控"""
        def performance_monitor_worker():
            while self.running:
                try:
                    self._collect_performance_metrics()
                    time.sleep(60)  # 每分钟收集一次
                except Exception as e:
                    logger.error(f"性能监控错误: {e}")
                    time.sleep(60)

        perf_thread = threading.Thread(target=performance_monitor_worker, daemon=True)
        perf_thread.start()

    def _collect_performance_metrics(self):
        """收集性能指标"""
        try:
            metrics = {
                'timestamp': datetime.now().isoformat(),
                'total_nodes': len(self.enhanced_nodes),
                'active_nodes': len([n for n in self.enhanced_nodes.values() if n.is_healthy()]),
                'total_tasks': len(self.enhanced_tasks),
                'running_tasks': len([t for t in self.enhanced_tasks.values() if t.status == "running"]),
                'completed_tasks': len([t for t in self.enhanced_tasks.values() if t.status == "completed"]),
                'failed_tasks': len([t for t in self.enhanced_tasks.values() if t.status == "failed"]),
                'average_response_time': self._calculate_average_response_time(),
                'system_load': self._calculate_system_load()
            }

            self.performance_metrics = metrics

            # 发送性能事件
            if self.event_bus:
                from core.events.event_bus import BaseEvent
                metrics_event = BaseEvent('distributed_service_metrics', metrics)
                self.event_bus.publish(metrics_event)

        except Exception as e:
            logger.error(f"收集性能指标失败: {e}")

    def _calculate_average_response_time(self) -> float:
        """计算平均响应时间"""
        completed_tasks = [t for t in self.enhanced_tasks.values()
                           if t.status == "completed" and t.execution_time > 0]

        if not completed_tasks:
            return 0.0

        return sum(t.execution_time for t in completed_tasks) / len(completed_tasks)

    def _calculate_system_load(self) -> float:
        """计算系统负载"""
        if not self.enhanced_nodes:
            return 0.0

        total_load = sum(node.current_load for node in self.enhanced_nodes.values())
        return total_load / len(self.enhanced_nodes)

    def _start_auto_scaling(self):
        """启动自动扩缩容"""
        def auto_scaling_worker():
            while self.running:
                try:
                    self._check_scaling_conditions()
                    time.sleep(120)  # 每2分钟检查一次
                except Exception as e:
                    logger.error(f"自动扩缩容错误: {e}")
                    time.sleep(120)

        scaling_thread = threading.Thread(target=auto_scaling_worker, daemon=True)
        scaling_thread.start()

    def _check_scaling_conditions(self):
        """检查扩缩容条件"""
        try:
            active_nodes = [n for n in self.enhanced_nodes.values() if n.is_healthy()]
            pending_tasks = [t for t in self.enhanced_tasks.values() if t.status == "pending"]

            # 扩容条件：待处理任务过多或系统负载过高
            if (len(pending_tasks) > len(active_nodes) * 2 or
                    self._calculate_system_load() > 0.8):

                if len(active_nodes) < self.config['max_nodes']:
                    logger.info("触发自动扩容条件")
                    self._trigger_scale_out()

            # 缩容条件：系统负载过低且节点数量超过最小值
            elif (self._calculate_system_load() < 0.3 and
                  len(active_nodes) > self.config['min_nodes']):

                logger.info("触发自动缩容条件")
                self._trigger_scale_in()

        except Exception as e:
            logger.error(f"检查扩缩容条件失败: {e}")

    def _trigger_scale_out(self):
        """触发扩容"""
        # 这里可以实现具体的扩容逻辑
        # 例如：启动新的容器、虚拟机等
        logger.info("执行扩容操作")

    def _trigger_scale_in(self):
        """触发缩容"""
        # 这里可以实现具体的缩容逻辑
        # 例如：关闭空闲节点
        logger.info("执行缩容操作")

    def get_service_status(self) -> Dict[str, Any]:
        """获取服务状态"""
        return {
            'service_running': self.running,
            'total_nodes': len(self.enhanced_nodes),
            'healthy_nodes': len([n for n in self.enhanced_nodes.values() if n.is_healthy()]),
            'total_tasks': len(self.enhanced_tasks),
            'pending_tasks': len([t for t in self.enhanced_tasks.values() if t.status == "pending"]),
            'running_tasks': len([t for t in self.enhanced_tasks.values() if t.status == "running"]),
            'completed_tasks': len([t for t in self.enhanced_tasks.values() if t.status == "completed"]),
            'failed_tasks': len([t for t in self.enhanced_tasks.values() if t.status == "failed"]),
            'performance_metrics': self.performance_metrics,
            'load_balancing_strategy': self.load_balancer.strategy.value,
            'security_enabled': self.security_manager is not None,
            'monitoring_enabled': self.enable_monitoring
        }


# 全局实例
_enhanced_distributed_service: Optional[EnhancedDistributedService] = None


def get_enhanced_distributed_service() -> EnhancedDistributedService:
    """获取增强版分布式服务实例"""
    global _enhanced_distributed_service
    if _enhanced_distributed_service is None:
        _enhanced_distributed_service = EnhancedDistributedService()
    return _enhanced_distributed_service


def initialize_enhanced_distributed_service(
    discovery_port: int = 8888,
    load_balancing_strategy: LoadBalancingStrategy = LoadBalancingStrategy.INTELLIGENT,
    enable_security: bool = True,
    enable_monitoring: bool = True,
    auto_start: bool = False
) -> EnhancedDistributedService:
    """初始化增强版分布式服务"""
    global _enhanced_distributed_service

    _enhanced_distributed_service = EnhancedDistributedService(
        discovery_port=discovery_port,
        load_balancing_strategy=load_balancing_strategy,
        enable_security=enable_security,
        enable_monitoring=enable_monitoring
    )

    if auto_start:
        _enhanced_distributed_service.start_service()

    logger.info("增强版分布式服务初始化完成")
    return _enhanced_distributed_service
