"""
动态资源管理器
建立动态资源分配和任务迁移系统，支持基于负载的自动资源调整
"""

import asyncio
import logging
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Callable, Any, Set, Tuple
from threading import Lock, Event
import threading
import json

logger = logging.getLogger(__name__)


class ResourceType(Enum):
    """资源类型枚举"""
    CPU = "cpu"
    MEMORY = "memory"
    DISK = "disk"
    NETWORK = "network"
    GPU = "gpu"


class AllocationStrategy(Enum):
    """分配策略枚举"""
    BALANCED = "balanced"          # 均衡分配
    PERFORMANCE = "performance"    # 性能优先
    EFFICIENCY = "efficiency"      # 效率优先
    COST_OPTIMIZED = "cost_optimized"  # 成本优化
    ADAPTIVE = "adaptive"          # 自适应


class MigrationReason(Enum):
    """迁移原因枚举"""
    LOAD_BALANCING = "load_balancing"
    RESOURCE_SHORTAGE = "resource_shortage"
    NODE_FAILURE = "node_failure"
    OPTIMIZATION = "optimization"
    MAINTENANCE = "maintenance"


@dataclass
class ResourceQuota:
    """资源配额数据类"""
    cpu_cores: float = 0.0
    memory_gb: float = 0.0
    disk_gb: float = 0.0
    network_mbps: float = 0.0
    gpu_count: int = 0


@dataclass
class ResourceUsage:
    """资源使用情况数据类"""
    cpu_usage: float = 0.0      # CPU使用率 (0-1)
    memory_usage: float = 0.0   # 内存使用率 (0-1)
    disk_usage: float = 0.0     # 磁盘使用率 (0-1)
    network_usage: float = 0.0  # 网络使用率 (0-1)
    gpu_usage: float = 0.0      # GPU使用率 (0-1)
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class TaskResource:
    """任务资源需求数据类"""
    task_id: str
    required_quota: ResourceQuota
    current_usage: ResourceUsage
    node_id: Optional[str] = None
    priority: int = 1
    created_at: datetime = field(default_factory=datetime.now)
    estimated_duration: float = 0.0  # 预估执行时间（秒）


@dataclass
class MigrationPlan:
    """迁移计划数据类"""
    task_id: str
    source_node: str
    target_node: str
    reason: MigrationReason
    estimated_cost: float  # 迁移成本（时间、资源等）
    priority: int
    created_at: datetime = field(default_factory=datetime.now)
    dependencies: List[str] = field(default_factory=list)


@dataclass
class NodeCapacity:
    """节点容量数据类"""
    node_id: str
    total_quota: ResourceQuota
    available_quota: ResourceQuota
    allocated_quota: ResourceQuota
    usage_history: deque = field(default_factory=lambda: deque(maxlen=100))
    last_updated: datetime = field(default_factory=datetime.now)


class ResourceAllocator:
    """资源分配器"""
    
    def __init__(self, strategy: AllocationStrategy = AllocationStrategy.BALANCED):
        self.strategy = strategy
        self.node_capacities: Dict[str, NodeCapacity] = {}
        self.task_allocations: Dict[str, TaskResource] = {}
        self.allocation_history: List[Dict[str, Any]] = []
        self.lock = Lock()
        
        # 分配策略权重
        self.strategy_weights = {
            AllocationStrategy.BALANCED: {'cpu': 0.25, 'memory': 0.25, 'disk': 0.25, 'network': 0.25},
            AllocationStrategy.PERFORMANCE: {'cpu': 0.4, 'memory': 0.3, 'disk': 0.2, 'network': 0.1},
            AllocationStrategy.EFFICIENCY: {'cpu': 0.2, 'memory': 0.2, 'disk': 0.3, 'network': 0.3},
            AllocationStrategy.COST_OPTIMIZED: {'cpu': 0.15, 'memory': 0.15, 'disk': 0.35, 'network': 0.35}
        }
    
    def register_node(self, node_id: str, total_quota: ResourceQuota):
        """注册节点容量"""
        try:
            with self.lock:
                self.node_capacities[node_id] = NodeCapacity(
                    node_id=node_id,
                    total_quota=total_quota,
                    available_quota=ResourceQuota(
                        cpu_cores=total_quota.cpu_cores,
                        memory_gb=total_quota.memory_gb,
                        disk_gb=total_quota.disk_gb,
                        network_mbps=total_quota.network_mbps,
                        gpu_count=total_quota.gpu_count
                    ),
                    allocated_quota=ResourceQuota()
                )
                
            logger.info(f"节点 {node_id} 已注册，容量: CPU {total_quota.cpu_cores}核, 内存 {total_quota.memory_gb}GB")
            
        except Exception as e:
            logger.error(f"注册节点失败: {e}")
    
    def allocate_resources(self, task_resource: TaskResource) -> Optional[str]:
        """分配资源给任务"""
        try:
            with self.lock:
                # 寻找最适合的节点
                best_node = self._find_best_node(task_resource)
                
                if not best_node:
                    logger.warning(f"无法为任务 {task_resource.task_id} 找到合适的节点")
                    return None
                
                # 执行分配
                node_capacity = self.node_capacities[best_node]
                required = task_resource.required_quota
                
                # 更新节点容量
                node_capacity.allocated_quota.cpu_cores += required.cpu_cores
                node_capacity.allocated_quota.memory_gb += required.memory_gb
                node_capacity.allocated_quota.disk_gb += required.disk_gb
                node_capacity.allocated_quota.network_mbps += required.network_mbps
                node_capacity.allocated_quota.gpu_count += required.gpu_count
                
                # 更新可用容量
                node_capacity.available_quota.cpu_cores -= required.cpu_cores
                node_capacity.available_quota.memory_gb -= required.memory_gb
                node_capacity.available_quota.disk_gb -= required.disk_gb
                node_capacity.available_quota.network_mbps -= required.network_mbps
                node_capacity.available_quota.gpu_count -= required.gpu_count
                
                # 记录分配
                task_resource.node_id = best_node
                self.task_allocations[task_resource.task_id] = task_resource
                
                # 记录历史
                self.allocation_history.append({
                    'timestamp': datetime.now(),
                    'task_id': task_resource.task_id,
                    'node_id': best_node,
                    'allocated_quota': {
                        'cpu_cores': required.cpu_cores,
                        'memory_gb': required.memory_gb,
                        'disk_gb': required.disk_gb,
                        'network_mbps': required.network_mbps,
                        'gpu_count': required.gpu_count
                    },
                    'strategy': self.strategy.value
                })
                
                logger.info(f"任务 {task_resource.task_id} 已分配到节点 {best_node}")
                return best_node
                
        except Exception as e:
            logger.error(f"资源分配失败: {e}")
            return None
    
    def _find_best_node(self, task_resource: TaskResource) -> Optional[str]:
        """寻找最适合的节点"""
        try:
            required = task_resource.required_quota
            candidate_nodes = []
            
            # 筛选有足够资源的节点
            for node_id, capacity in self.node_capacities.items():
                available = capacity.available_quota
                
                if (available.cpu_cores >= required.cpu_cores and
                    available.memory_gb >= required.memory_gb and
                    available.disk_gb >= required.disk_gb and
                    available.network_mbps >= required.network_mbps and
                    available.gpu_count >= required.gpu_count):
                    
                    candidate_nodes.append(node_id)
            
            if not candidate_nodes:
                return None
            
            # 根据策略选择最佳节点
            return self._select_best_candidate(candidate_nodes, task_resource)
            
        except Exception as e:
            logger.error(f"寻找最佳节点失败: {e}")
            return None
    
    def _select_best_candidate(self, candidates: List[str], task_resource: TaskResource) -> str:
        """从候选节点中选择最佳节点"""
        try:
            if len(candidates) == 1:
                return candidates[0]
            
            best_node = None
            best_score = float('-inf')
            
            weights = self.strategy_weights.get(self.strategy, self.strategy_weights[AllocationStrategy.BALANCED])
            
            for node_id in candidates:
                score = self._calculate_node_score(node_id, task_resource, weights)
                
                if score > best_score:
                    best_score = score
                    best_node = node_id
            
            return best_node or candidates[0]
            
        except Exception as e:
            logger.error(f"选择最佳候选节点失败: {e}")
            return candidates[0]
    
    def _calculate_node_score(self, node_id: str, task_resource: TaskResource, weights: Dict[str, float]) -> float:
        """计算节点分数"""
        try:
            capacity = self.node_capacities[node_id]
            available = capacity.available_quota
            total = capacity.total_quota
            
            # 计算资源利用率分数（越低越好，表示资源充足）
            cpu_utilization = 1 - (available.cpu_cores / total.cpu_cores) if total.cpu_cores > 0 else 1
            memory_utilization = 1 - (available.memory_gb / total.memory_gb) if total.memory_gb > 0 else 1
            disk_utilization = 1 - (available.disk_gb / total.disk_gb) if total.disk_gb > 0 else 1
            network_utilization = 1 - (available.network_mbps / total.network_mbps) if total.network_mbps > 0 else 1
            
            # 根据策略调整分数
            if self.strategy == AllocationStrategy.BALANCED:
                # 均衡策略：选择资源利用率最均衡的节点
                score = -(weights['cpu'] * cpu_utilization +
                         weights['memory'] * memory_utilization +
                         weights['disk'] * disk_utilization +
                         weights['network'] * network_utilization)
            
            elif self.strategy == AllocationStrategy.PERFORMANCE:
                # 性能策略：优先选择CPU和内存充足的节点
                score = -(weights['cpu'] * cpu_utilization +
                         weights['memory'] * memory_utilization)
            
            elif self.strategy == AllocationStrategy.EFFICIENCY:
                # 效率策略：优先选择磁盘和网络充足的节点
                score = -(weights['disk'] * disk_utilization +
                         weights['network'] * network_utilization)
            
            else:  # COST_OPTIMIZED 或其他
                # 成本优化：选择资源利用率最高但仍能满足需求的节点
                score = -(cpu_utilization + memory_utilization + disk_utilization + network_utilization) / 4
            
            return score
            
        except Exception as e:
            logger.error(f"计算节点分数失败: {e}")
            return 0.0
    
    def deallocate_resources(self, task_id: str) -> bool:
        """释放任务资源"""
        try:
            with self.lock:
                if task_id not in self.task_allocations:
                    logger.warning(f"任务 {task_id} 未找到分配记录")
                    return False
                
                task_resource = self.task_allocations[task_id]
                node_id = task_resource.node_id
                
                if not node_id or node_id not in self.node_capacities:
                    logger.warning(f"任务 {task_id} 的节点信息无效")
                    return False
                
                # 释放资源
                node_capacity = self.node_capacities[node_id]
                required = task_resource.required_quota
                
                # 更新已分配容量
                node_capacity.allocated_quota.cpu_cores -= required.cpu_cores
                node_capacity.allocated_quota.memory_gb -= required.memory_gb
                node_capacity.allocated_quota.disk_gb -= required.disk_gb
                node_capacity.allocated_quota.network_mbps -= required.network_mbps
                node_capacity.allocated_quota.gpu_count -= required.gpu_count
                
                # 更新可用容量
                node_capacity.available_quota.cpu_cores += required.cpu_cores
                node_capacity.available_quota.memory_gb += required.memory_gb
                node_capacity.available_quota.disk_gb += required.disk_gb
                node_capacity.available_quota.network_mbps += required.network_mbps
                node_capacity.available_quota.gpu_count += required.gpu_count
                
                # 移除分配记录
                del self.task_allocations[task_id]
                
                logger.info(f"任务 {task_id} 资源已释放，节点 {node_id}")
                return True
                
        except Exception as e:
            logger.error(f"释放资源失败: {e}")
            return False
    
    def update_resource_usage(self, node_id: str, usage: ResourceUsage):
        """更新节点资源使用情况"""
        try:
            with self.lock:
                if node_id in self.node_capacities:
                    self.node_capacities[node_id].usage_history.append(usage)
                    self.node_capacities[node_id].last_updated = datetime.now()
                    
        except Exception as e:
            logger.error(f"更新资源使用情况失败: {e}")
    
    def get_allocation_statistics(self) -> Dict[str, Any]:
        """获取分配统计信息"""
        try:
            with self.lock:
                total_nodes = len(self.node_capacities)
                total_tasks = len(self.task_allocations)
                
                # 计算总体资源利用率
                total_cpu_allocated = sum(cap.allocated_quota.cpu_cores for cap in self.node_capacities.values())
                total_cpu_capacity = sum(cap.total_quota.cpu_cores for cap in self.node_capacities.values())
                cpu_utilization = total_cpu_allocated / total_cpu_capacity if total_cpu_capacity > 0 else 0
                
                total_memory_allocated = sum(cap.allocated_quota.memory_gb for cap in self.node_capacities.values())
                total_memory_capacity = sum(cap.total_quota.memory_gb for cap in self.node_capacities.values())
                memory_utilization = total_memory_allocated / total_memory_capacity if total_memory_capacity > 0 else 0
                
                return {
                    'strategy': self.strategy.value,
                    'total_nodes': total_nodes,
                    'total_allocated_tasks': total_tasks,
                    'cpu_utilization': cpu_utilization,
                    'memory_utilization': memory_utilization,
                    'allocation_history_count': len(self.allocation_history),
                    'timestamp': datetime.now().isoformat()
                }
                
        except Exception as e:
            logger.error(f"获取分配统计失败: {e}")
            return {'error': str(e)}


class TaskMigrator:
    """任务迁移器"""
    
    def __init__(self, resource_allocator: ResourceAllocator):
        self.resource_allocator = resource_allocator
        self.migration_queue: List[MigrationPlan] = []
        self.migration_history: List[Dict[str, Any]] = []
        self.active_migrations: Dict[str, MigrationPlan] = {}
        self.migration_callbacks: Dict[str, Callable] = {}
        self.lock = Lock()
    
    def register_migration_callback(self, callback_name: str, callback: Callable):
        """注册迁移回调"""
        self.migration_callbacks[callback_name] = callback
    
    def create_migration_plan(self, task_id: str, source_node: str, target_node: str, 
                            reason: MigrationReason, priority: int = 1) -> Optional[MigrationPlan]:
        """创建迁移计划"""
        try:
            # 验证迁移的可行性
            if not self._validate_migration(task_id, source_node, target_node):
                return None
            
            # 估算迁移成本
            estimated_cost = self._estimate_migration_cost(task_id, source_node, target_node)
            
            migration_plan = MigrationPlan(
                task_id=task_id,
                source_node=source_node,
                target_node=target_node,
                reason=reason,
                estimated_cost=estimated_cost,
                priority=priority
            )
            
            return migration_plan
            
        except Exception as e:
            logger.error(f"创建迁移计划失败: {e}")
            return None
    
    def _validate_migration(self, task_id: str, source_node: str, target_node: str) -> bool:
        """验证迁移可行性"""
        try:
            # 检查任务是否存在
            if task_id not in self.resource_allocator.task_allocations:
                logger.warning(f"任务 {task_id} 不存在")
                return False
            
            # 检查源节点
            if source_node not in self.resource_allocator.node_capacities:
                logger.warning(f"源节点 {source_node} 不存在")
                return False
            
            # 检查目标节点
            if target_node not in self.resource_allocator.node_capacities:
                logger.warning(f"目标节点 {target_node} 不存在")
                return False
            
            # 检查目标节点是否有足够资源
            task_resource = self.resource_allocator.task_allocations[task_id]
            target_capacity = self.resource_allocator.node_capacities[target_node]
            required = task_resource.required_quota
            available = target_capacity.available_quota
            
            if (available.cpu_cores < required.cpu_cores or
                available.memory_gb < required.memory_gb or
                available.disk_gb < required.disk_gb or
                available.network_mbps < required.network_mbps or
                available.gpu_count < required.gpu_count):
                
                logger.warning(f"目标节点 {target_node} 资源不足")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"验证迁移可行性失败: {e}")
            return False
    
    def _estimate_migration_cost(self, task_id: str, source_node: str, target_node: str) -> float:
        """估算迁移成本"""
        try:
            # 基础迁移时间
            base_cost = 60.0  # 60秒基础成本
            
            # 根据任务资源需求调整成本
            task_resource = self.resource_allocator.task_allocations[task_id]
            
            # 内存越大，迁移成本越高
            memory_cost = task_resource.required_quota.memory_gb * 5.0  # 每GB内存5秒
            
            # 磁盘越大，迁移成本越高
            disk_cost = task_resource.required_quota.disk_gb * 0.1  # 每GB磁盘0.1秒
            
            # 网络延迟影响（模拟）
            network_cost = 10.0  # 假设网络延迟10秒
            
            total_cost = base_cost + memory_cost + disk_cost + network_cost
            
            return total_cost
            
        except Exception as e:
            logger.error(f"估算迁移成本失败: {e}")
            return 300.0  # 默认5分钟
    
    def schedule_migration(self, migration_plan: MigrationPlan) -> bool:
        """调度迁移"""
        try:
            with self.lock:
                # 检查是否已有相同任务的迁移计划
                for existing_plan in self.migration_queue:
                    if existing_plan.task_id == migration_plan.task_id:
                        logger.warning(f"任务 {migration_plan.task_id} 已有迁移计划")
                        return False
                
                # 按优先级插入队列
                inserted = False
                for i, plan in enumerate(self.migration_queue):
                    if migration_plan.priority < plan.priority:  # 数字越小优先级越高
                        self.migration_queue.insert(i, migration_plan)
                        inserted = True
                        break
                
                if not inserted:
                    self.migration_queue.append(migration_plan)
                
                logger.info(f"迁移计划已调度: 任务 {migration_plan.task_id} 从 {migration_plan.source_node} 到 {migration_plan.target_node}")
                return True
                
        except Exception as e:
            logger.error(f"调度迁移失败: {e}")
            return False
    
    def execute_next_migration(self) -> Optional[MigrationPlan]:
        """执行下一个迁移"""
        try:
            with self.lock:
                if not self.migration_queue:
                    return None
                
                migration_plan = self.migration_queue.pop(0)
                self.active_migrations[migration_plan.task_id] = migration_plan
            
            # 执行迁移
            success = self._execute_migration(migration_plan)
            
            # 记录结果
            with self.lock:
                self.active_migrations.pop(migration_plan.task_id, None)
                
                self.migration_history.append({
                    'timestamp': datetime.now(),
                    'task_id': migration_plan.task_id,
                    'source_node': migration_plan.source_node,
                    'target_node': migration_plan.target_node,
                    'reason': migration_plan.reason.value,
                    'success': success,
                    'estimated_cost': migration_plan.estimated_cost
                })
            
            if success:
                logger.info(f"迁移成功: 任务 {migration_plan.task_id}")
            else:
                logger.error(f"迁移失败: 任务 {migration_plan.task_id}")
            
            return migration_plan
            
        except Exception as e:
            logger.error(f"执行迁移失败: {e}")
            return None
    
    def _execute_migration(self, migration_plan: MigrationPlan) -> bool:
        """执行迁移"""
        try:
            task_id = migration_plan.task_id
            source_node = migration_plan.source_node
            target_node = migration_plan.target_node
            
            # 1. 暂停任务（如果有回调）
            if 'pause_task' in self.migration_callbacks:
                pause_success = self.migration_callbacks['pause_task'](task_id)
                if not pause_success:
                    logger.error(f"暂停任务失败: {task_id}")
                    return False
            
            # 2. 保存任务状态（如果有回调）
            if 'save_task_state' in self.migration_callbacks:
                save_success = self.migration_callbacks['save_task_state'](task_id, source_node)
                if not save_success:
                    logger.error(f"保存任务状态失败: {task_id}")
                    return False
            
            # 3. 在目标节点分配资源
            task_resource = self.resource_allocator.task_allocations[task_id]
            
            # 临时释放源节点资源
            original_node = task_resource.node_id
            task_resource.node_id = None
            
            # 在目标节点分配资源
            allocated_node = self.resource_allocator.allocate_resources(task_resource)
            if allocated_node != target_node:
                # 恢复原始分配
                task_resource.node_id = original_node
                logger.error(f"目标节点资源分配失败: {target_node}")
                return False
            
            # 4. 迁移任务数据（如果有回调）
            if 'migrate_task_data' in self.migration_callbacks:
                migrate_success = self.migration_callbacks['migrate_task_data'](task_id, source_node, target_node)
                if not migrate_success:
                    logger.error(f"迁移任务数据失败: {task_id}")
                    # 回滚资源分配
                    self.resource_allocator.deallocate_resources(task_id)
                    task_resource.node_id = original_node
                    return False
            
            # 5. 在目标节点恢复任务（如果有回调）
            if 'restore_task' in self.migration_callbacks:
                restore_success = self.migration_callbacks['restore_task'](task_id, target_node)
                if not restore_success:
                    logger.error(f"恢复任务失败: {task_id}")
                    return False
            
            # 6. 清理源节点资源
            if 'cleanup_source_node' in self.migration_callbacks:
                self.migration_callbacks['cleanup_source_node'](task_id, source_node)
            
            logger.info(f"任务 {task_id} 成功从 {source_node} 迁移到 {target_node}")
            return True
            
        except Exception as e:
            logger.error(f"执行迁移操作失败: {e}")
            return False
    
    def get_migration_statistics(self) -> Dict[str, Any]:
        """获取迁移统计信息"""
        try:
            with self.lock:
                total_migrations = len(self.migration_history)
                successful_migrations = sum(1 for m in self.migration_history if m['success'])
                
                # 按原因统计
                reason_stats = defaultdict(int)
                for migration in self.migration_history:
                    reason_stats[migration['reason']] += 1
                
                return {
                    'total_migrations': total_migrations,
                    'successful_migrations': successful_migrations,
                    'success_rate': successful_migrations / total_migrations if total_migrations > 0 else 0,
                    'pending_migrations': len(self.migration_queue),
                    'active_migrations': len(self.active_migrations),
                    'migration_reasons': dict(reason_stats),
                    'timestamp': datetime.now().isoformat()
                }
                
        except Exception as e:
            logger.error(f"获取迁移统计失败: {e}")
            return {'error': str(e)}


class DynamicResourceManager:
    """动态资源管理器主类"""
    
    def __init__(self, allocation_strategy: AllocationStrategy = AllocationStrategy.ADAPTIVE):
        self.resource_allocator = ResourceAllocator(allocation_strategy)
        self.task_migrator = TaskMigrator(self.resource_allocator)
        
        # 监控配置
        self.monitoring_enabled = False
        self.monitor_interval = 30.0  # 30秒监控间隔
        self.monitor_thread: Optional[threading.Thread] = None
        self.stop_event = Event()
        
        # 自动调整阈值
        self.load_thresholds = {
            'high_load': 0.8,      # 高负载阈值
            'low_load': 0.3,       # 低负载阈值
            'critical_load': 0.95  # 临界负载阈值
        }
        
        # 注册默认迁移回调
        self._register_default_migration_callbacks()
        
        logger.info("动态资源管理器已初始化")
    
    def start_monitoring(self):
        """启动资源监控"""
        try:
            if self.monitoring_enabled:
                return
            
            self.monitoring_enabled = True
            self.stop_event.clear()
            self.monitor_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
            self.monitor_thread.start()
            
            logger.info("动态资源监控已启动")
            
        except Exception as e:
            logger.error(f"启动资源监控失败: {e}")
            self.monitoring_enabled = False
    
    def stop_monitoring(self):
        """停止资源监控"""
        try:
            if not self.monitoring_enabled:
                return
            
            self.monitoring_enabled = False
            self.stop_event.set()
            
            if self.monitor_thread and self.monitor_thread.is_alive():
                self.monitor_thread.join(timeout=5.0)
            
            logger.info("动态资源监控已停止")
            
        except Exception as e:
            logger.error(f"停止资源监控失败: {e}")
    
    def _monitoring_loop(self):
        """监控循环"""
        while self.monitoring_enabled and not self.stop_event.is_set():
            try:
                # 检查资源使用情况
                self._check_resource_usage()
                
                # 执行待处理的迁移
                self.task_migrator.execute_next_migration()
                
                # 自动优化资源分配
                self._auto_optimize_allocation()
                
            except Exception as e:
                logger.error(f"资源监控循环出错: {e}")
            
            self.stop_event.wait(self.monitor_interval)
    
    def _check_resource_usage(self):
        """检查资源使用情况"""
        try:
            for node_id, capacity in self.resource_allocator.node_capacities.items():
                if not capacity.usage_history:
                    continue
                
                # 获取最新使用情况
                latest_usage = capacity.usage_history[-1]
                
                # 检查是否需要迁移
                if latest_usage.cpu_usage > self.load_thresholds['critical_load']:
                    self._handle_high_load(node_id, 'cpu')
                elif latest_usage.memory_usage > self.load_thresholds['critical_load']:
                    self._handle_high_load(node_id, 'memory')
                
        except Exception as e:
            logger.error(f"检查资源使用情况失败: {e}")
    
    def _handle_high_load(self, node_id: str, resource_type: str):
        """处理高负载情况"""
        try:
            # 寻找该节点上的任务
            tasks_on_node = [
                task for task in self.resource_allocator.task_allocations.values()
                if task.node_id == node_id
            ]
            
            if not tasks_on_node:
                return
            
            # 选择优先级最低的任务进行迁移
            task_to_migrate = min(tasks_on_node, key=lambda t: t.priority)
            
            # 寻找目标节点
            target_node = self._find_migration_target(task_to_migrate, node_id)
            
            if target_node:
                # 创建迁移计划
                migration_plan = self.task_migrator.create_migration_plan(
                    task_to_migrate.task_id,
                    node_id,
                    target_node,
                    MigrationReason.LOAD_BALANCING,
                    priority=1
                )
                
                if migration_plan:
                    self.task_migrator.schedule_migration(migration_plan)
                    logger.info(f"因 {resource_type} 高负载，调度任务 {task_to_migrate.task_id} 迁移")
            
        except Exception as e:
            logger.error(f"处理高负载失败: {e}")
    
    def _find_migration_target(self, task_resource: TaskResource, exclude_node: str) -> Optional[str]:
        """寻找迁移目标节点"""
        try:
            required = task_resource.required_quota
            
            for node_id, capacity in self.resource_allocator.node_capacities.items():
                if node_id == exclude_node:
                    continue
                
                available = capacity.available_quota
                
                if (available.cpu_cores >= required.cpu_cores and
                    available.memory_gb >= required.memory_gb and
                    available.disk_gb >= required.disk_gb and
                    available.network_mbps >= required.network_mbps and
                    available.gpu_count >= required.gpu_count):
                    
                    return node_id
            
            return None
            
        except Exception as e:
            logger.error(f"寻找迁移目标失败: {e}")
            return None
    
    def _auto_optimize_allocation(self):
        """自动优化资源分配"""
        try:
            # 这里可以实现更复杂的优化逻辑
            # 例如：负载均衡、资源碎片整理等
            pass
            
        except Exception as e:
            logger.error(f"自动优化分配失败: {e}")
    
    def _register_default_migration_callbacks(self):
        """注册默认迁移回调"""
        
        def default_pause_task(task_id: str) -> bool:
            logger.info(f"暂停任务: {task_id}")
            return True
        
        def default_save_task_state(task_id: str, node_id: str) -> bool:
            logger.info(f"保存任务状态: {task_id} @ {node_id}")
            return True
        
        def default_migrate_task_data(task_id: str, source: str, target: str) -> bool:
            logger.info(f"迁移任务数据: {task_id} 从 {source} 到 {target}")
            return True
        
        def default_restore_task(task_id: str, node_id: str) -> bool:
            logger.info(f"恢复任务: {task_id} @ {node_id}")
            return True
        
        def default_cleanup_source_node(task_id: str, node_id: str):
            logger.info(f"清理源节点: {task_id} @ {node_id}")
        
        # 注册回调
        self.task_migrator.register_migration_callback('pause_task', default_pause_task)
        self.task_migrator.register_migration_callback('save_task_state', default_save_task_state)
        self.task_migrator.register_migration_callback('migrate_task_data', default_migrate_task_data)
        self.task_migrator.register_migration_callback('restore_task', default_restore_task)
        self.task_migrator.register_migration_callback('cleanup_source_node', default_cleanup_source_node)
    
    # 公共接口方法
    def register_node(self, node_id: str, total_quota: ResourceQuota):
        """注册节点"""
        return self.resource_allocator.register_node(node_id, total_quota)
    
    def allocate_task_resources(self, task_resource: TaskResource) -> Optional[str]:
        """为任务分配资源"""
        return self.resource_allocator.allocate_resources(task_resource)
    
    def deallocate_task_resources(self, task_id: str) -> bool:
        """释放任务资源"""
        return self.resource_allocator.deallocate_resources(task_id)
    
    def update_node_usage(self, node_id: str, usage: ResourceUsage):
        """更新节点使用情况"""
        self.resource_allocator.update_resource_usage(node_id, usage)
    
    def migrate_task(self, task_id: str, target_node: str, reason: MigrationReason = MigrationReason.OPTIMIZATION) -> bool:
        """手动迁移任务"""
        try:
            if task_id not in self.resource_allocator.task_allocations:
                logger.warning(f"任务 {task_id} 不存在")
                return False
            
            source_node = self.resource_allocator.task_allocations[task_id].node_id
            if not source_node:
                logger.warning(f"任务 {task_id} 未分配到节点")
                return False
            
            migration_plan = self.task_migrator.create_migration_plan(
                task_id, source_node, target_node, reason, priority=1
            )
            
            if migration_plan:
                return self.task_migrator.schedule_migration(migration_plan)
            
            return False
            
        except Exception as e:
            logger.error(f"手动迁移任务失败: {e}")
            return False
    
    def get_system_status(self) -> Dict[str, Any]:
        """获取系统状态"""
        try:
            allocation_stats = self.resource_allocator.get_allocation_statistics()
            migration_stats = self.task_migrator.get_migration_statistics()
            
            return {
                'monitoring_enabled': self.monitoring_enabled,
                'allocation_statistics': allocation_stats,
                'migration_statistics': migration_stats,
                'load_thresholds': self.load_thresholds,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"获取系统状态失败: {e}")
            return {'error': str(e)}


# 全局实例
dynamic_resource_manager = DynamicResourceManager()


def get_dynamic_resource_manager() -> DynamicResourceManager:
    """获取动态资源管理器实例"""
    return dynamic_resource_manager
