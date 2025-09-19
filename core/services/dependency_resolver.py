#!/usr/bin/env python3
"""
任务依赖关系解析器

实现任务间依赖关系的检测和处理，支持复杂的任务依赖图管理
确保任务按正确顺序执行，检测循环依赖，处理依赖失败
"""

from typing import Dict, List, Set, Optional, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
from collections import defaultdict, deque
from loguru import logger


class DependencyType(Enum):
    """依赖类型"""
    COMPLETION = "completion"       # 完成依赖：等待前置任务完成
    SUCCESS = "success"            # 成功依赖：等待前置任务成功完成
    DATA = "data"                  # 数据依赖：等待前置任务产生数据
    RESOURCE = "resource"          # 资源依赖：等待资源释放
    TIME = "time"                  # 时间依赖：等待特定时间
    CONDITION = "condition"        # 条件依赖：等待特定条件满足


class DependencyStatus(Enum):
    """依赖状态"""
    PENDING = "pending"            # 等待中
    SATISFIED = "satisfied"        # 已满足
    FAILED = "failed"             # 失败
    TIMEOUT = "timeout"           # 超时
    CANCELLED = "cancelled"       # 已取消


@dataclass
class TaskDependency:
    """任务依赖"""
    dependent_task_id: str         # 依赖任务ID
    prerequisite_task_id: str      # 前置任务ID
    dependency_type: DependencyType = DependencyType.COMPLETION
    condition: Optional[str] = None  # 依赖条件
    timeout: Optional[datetime] = None  # 超时时间
    status: DependencyStatus = DependencyStatus.PENDING
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    satisfied_at: Optional[datetime] = None

    def __hash__(self):
        return hash((self.dependent_task_id, self.prerequisite_task_id, self.dependency_type.value))

    def __eq__(self, other):
        if not isinstance(other, TaskDependency):
            return False
        return (self.dependent_task_id == other.dependent_task_id and
                self.prerequisite_task_id == other.prerequisite_task_id and
                self.dependency_type == other.dependency_type)


@dataclass
class DependencyGraph:
    """依赖图"""
    nodes: Set[str] = field(default_factory=set)  # 任务节点
    edges: Dict[str, Set[str]] = field(default_factory=lambda: defaultdict(set))  # 依赖边
    reverse_edges: Dict[str, Set[str]] = field(default_factory=lambda: defaultdict(set))  # 反向边
    dependencies: Dict[Tuple[str, str], TaskDependency] = field(default_factory=dict)  # 依赖详情

    def add_node(self, task_id: str):
        """添加节点"""
        self.nodes.add(task_id)

    def add_dependency(self, dependency: TaskDependency):
        """添加依赖关系"""
        dependent = dependency.dependent_task_id
        prerequisite = dependency.prerequisite_task_id

        # 添加节点
        self.add_node(dependent)
        self.add_node(prerequisite)

        # 添加边
        self.edges[prerequisite].add(dependent)
        self.reverse_edges[dependent].add(prerequisite)

        # 存储依赖详情
        key = (dependent, prerequisite)
        self.dependencies[key] = dependency

    def remove_dependency(self, dependent_task_id: str, prerequisite_task_id: str):
        """移除依赖关系"""
        # 移除边
        if prerequisite_task_id in self.edges:
            self.edges[prerequisite_task_id].discard(dependent_task_id)

        if dependent_task_id in self.reverse_edges:
            self.reverse_edges[dependent_task_id].discard(prerequisite_task_id)

        # 移除依赖详情
        key = (dependent_task_id, prerequisite_task_id)
        if key in self.dependencies:
            del self.dependencies[key]

    def get_prerequisites(self, task_id: str) -> Set[str]:
        """获取前置任务"""
        return self.reverse_edges.get(task_id, set()).copy()

    def get_dependents(self, task_id: str) -> Set[str]:
        """获取依赖任务"""
        return self.edges.get(task_id, set()).copy()

    def get_dependency(self, dependent_task_id: str, prerequisite_task_id: str) -> Optional[TaskDependency]:
        """获取依赖详情"""
        key = (dependent_task_id, prerequisite_task_id)
        return self.dependencies.get(key)


class CircularDependencyError(Exception):
    """循环依赖错误"""

    def __init__(self, cycle: List[str]):
        self.cycle = cycle
        super().__init__(f"检测到循环依赖: {' -> '.join(cycle)}")


class DependencyResolver:
    """
    任务依赖关系解析器

    功能特性：
    1. 依赖图构建和管理
    2. 循环依赖检测
    3. 拓扑排序
    4. 依赖状态跟踪
    5. 依赖失败处理
    6. 条件依赖评估
    7. 死锁预防
    """

    def __init__(self):
        """初始化依赖解析器"""
        self.dependency_graph = DependencyGraph()
        self.task_status: Dict[str, str] = {}  # 任务状态缓存
        self.completed_tasks: Set[str] = set()
        self.failed_tasks: Set[str] = set()
        self.cancelled_tasks: Set[str] = set()

        # 条件评估器
        self.condition_evaluators: Dict[str, callable] = {}

        # 统计信息
        self._stats = {
            'total_dependencies': 0,
            'satisfied_dependencies': 0,
            'failed_dependencies': 0,
            'circular_dependencies_detected': 0,
            'deadlocks_prevented': 0
        }

        logger.info("任务依赖关系解析器初始化完成")

    def add_dependency(self, dependency: TaskDependency) -> bool:
        """
        添加依赖关系

        Args:
            dependency: 依赖关系

        Returns:
            bool: 是否成功添加
        """
        try:
            # 检查是否会产生循环依赖
            temp_graph = DependencyGraph()
            temp_graph.nodes = self.dependency_graph.nodes.copy()
            temp_graph.edges = {k: v.copy() for k, v in self.dependency_graph.edges.items()}
            temp_graph.reverse_edges = {k: v.copy() for k, v in self.dependency_graph.reverse_edges.items()}

            # 临时添加依赖
            temp_graph.add_dependency(dependency)

            # 检查循环依赖
            cycle = self._detect_cycle(temp_graph)
            if cycle:
                self._stats['circular_dependencies_detected'] += 1
                raise CircularDependencyError(cycle)

            # 添加到实际图中
            self.dependency_graph.add_dependency(dependency)
            self._stats['total_dependencies'] += 1

            logger.info(f"添加依赖关系: {dependency.dependent_task_id} -> {dependency.prerequisite_task_id}")
            return True

        except CircularDependencyError:
            logger.error(f"循环依赖检测失败，拒绝添加依赖: {dependency.dependent_task_id} -> {dependency.prerequisite_task_id}")
            raise
        except Exception as e:
            logger.error(f"添加依赖关系失败: {e}")
            return False

    def remove_dependency(self, dependent_task_id: str, prerequisite_task_id: str) -> bool:
        """移除依赖关系"""
        try:
            self.dependency_graph.remove_dependency(dependent_task_id, prerequisite_task_id)
            logger.info(f"移除依赖关系: {dependent_task_id} -> {prerequisite_task_id}")
            return True
        except Exception as e:
            logger.error(f"移除依赖关系失败: {e}")
            return False

    def _detect_cycle(self, graph: DependencyGraph) -> Optional[List[str]]:
        """检测循环依赖"""
        # 使用DFS检测循环
        visited = set()
        rec_stack = set()

        def dfs(node: str, path: List[str]) -> Optional[List[str]]:
            if node in rec_stack:
                # 找到循环，返回循环路径
                cycle_start = path.index(node)
                return path[cycle_start:] + [node]

            if node in visited:
                return None

            visited.add(node)
            rec_stack.add(node)
            path.append(node)

            # 访问所有依赖节点
            for dependent in graph.edges.get(node, set()):
                cycle = dfs(dependent, path.copy())
                if cycle:
                    return cycle

            rec_stack.remove(node)
            return None

        # 对所有节点进行DFS
        for node in graph.nodes:
            if node not in visited:
                cycle = dfs(node, [])
                if cycle:
                    return cycle

        return None

    def detect_cycles(self) -> Optional[List[str]]:
        """
        检测依赖图中的循环依赖

        Returns:
            Optional[List[str]]: 如果存在循环依赖，返回循环路径；否则返回None
        """
        return self._detect_cycle(self.dependency_graph)

    def get_ready_tasks(self, task_ids: List[str]) -> List[str]:
        """
        获取准备好执行的任务

        Args:
            task_ids: 候选任务ID列表

        Returns:
            List[str]: 准备好执行的任务ID列表
        """
        ready_tasks = []

        for task_id in task_ids:
            if self._is_task_ready(task_id):
                ready_tasks.append(task_id)

        return ready_tasks

    def _is_task_ready(self, task_id: str) -> bool:
        """检查任务是否准备好执行"""
        # 获取所有前置任务
        prerequisites = self.dependency_graph.get_prerequisites(task_id)

        if not prerequisites:
            return True  # 没有依赖，可以执行

        # 检查所有依赖是否满足
        for prereq_id in prerequisites:
            dependency = self.dependency_graph.get_dependency(task_id, prereq_id)
            if not dependency:
                continue

            if not self._is_dependency_satisfied(dependency):
                return False

        return True

    def _is_dependency_satisfied(self, dependency: TaskDependency) -> bool:
        """检查依赖是否满足"""
        if dependency.status == DependencyStatus.SATISFIED:
            return True

        if dependency.status in [DependencyStatus.FAILED, DependencyStatus.CANCELLED]:
            return False

        # 检查超时
        if dependency.timeout and datetime.now() > dependency.timeout:
            dependency.status = DependencyStatus.TIMEOUT
            return False

        # 根据依赖类型检查
        prereq_id = dependency.prerequisite_task_id

        if dependency.dependency_type == DependencyType.COMPLETION:
            # 完成依赖：前置任务已完成（成功或失败）
            if prereq_id in self.completed_tasks or prereq_id in self.failed_tasks:
                dependency.status = DependencyStatus.SATISFIED
                dependency.satisfied_at = datetime.now()
                self._stats['satisfied_dependencies'] += 1
                return True

        elif dependency.dependency_type == DependencyType.SUCCESS:
            # 成功依赖：前置任务成功完成
            if prereq_id in self.completed_tasks:
                dependency.status = DependencyStatus.SATISFIED
                dependency.satisfied_at = datetime.now()
                self._stats['satisfied_dependencies'] += 1
                return True
            elif prereq_id in self.failed_tasks:
                dependency.status = DependencyStatus.FAILED
                self._stats['failed_dependencies'] += 1
                return False

        elif dependency.dependency_type == DependencyType.DATA:
            # 数据依赖：检查数据是否可用
            if self._check_data_availability(dependency):
                dependency.status = DependencyStatus.SATISFIED
                dependency.satisfied_at = datetime.now()
                self._stats['satisfied_dependencies'] += 1
                return True

        elif dependency.dependency_type == DependencyType.CONDITION:
            # 条件依赖：评估条件
            if self._evaluate_condition(dependency):
                dependency.status = DependencyStatus.SATISFIED
                dependency.satisfied_at = datetime.now()
                self._stats['satisfied_dependencies'] += 1
                return True

        elif dependency.dependency_type == DependencyType.TIME:
            # 时间依赖：检查时间条件
            if self._check_time_condition(dependency):
                dependency.status = DependencyStatus.SATISFIED
                dependency.satisfied_at = datetime.now()
                self._stats['satisfied_dependencies'] += 1
                return True

        return False

    def _check_data_availability(self, dependency: TaskDependency) -> bool:
        """检查数据可用性"""
        # 这里可以实现具体的数据检查逻辑
        # 例如检查文件是否存在、数据库表是否有数据等
        prereq_id = dependency.prerequisite_task_id

        # 简单实现：如果前置任务完成，则认为数据可用
        return prereq_id in self.completed_tasks

    def _evaluate_condition(self, dependency: TaskDependency) -> bool:
        """评估条件依赖"""
        if not dependency.condition:
            return True

        # 查找条件评估器
        evaluator = self.condition_evaluators.get(dependency.condition)
        if evaluator:
            try:
                return evaluator(dependency)
            except Exception as e:
                logger.error(f"条件评估失败: {e}")
                return False

        # 默认条件评估逻辑
        return self._default_condition_evaluation(dependency)

    def _default_condition_evaluation(self, dependency: TaskDependency) -> bool:
        """默认条件评估"""
        # 简单的条件评估实现
        condition = dependency.condition
        prereq_id = dependency.prerequisite_task_id

        if condition == "success":
            return prereq_id in self.completed_tasks
        elif condition == "failure":
            return prereq_id in self.failed_tasks
        elif condition == "any":
            return (prereq_id in self.completed_tasks or
                    prereq_id in self.failed_tasks)

        return False

    def _check_time_condition(self, dependency: TaskDependency) -> bool:
        """检查时间条件"""
        # 时间依赖的具体实现
        # 可以根据metadata中的时间条件进行检查
        time_condition = dependency.metadata.get('time_condition')
        if not time_condition:
            return True

        current_time = datetime.now()

        if isinstance(time_condition, datetime):
            return current_time >= time_condition
        elif isinstance(time_condition, str):
            # 解析时间字符串
            try:
                target_time = datetime.fromisoformat(time_condition)
                return current_time >= target_time
            except ValueError:
                logger.error(f"无效的时间条件: {time_condition}")
                return False

        return False

    def mark_task_completed(self, task_id: str):
        """标记任务完成"""
        self.completed_tasks.add(task_id)
        self.task_status[task_id] = "completed"

        # 检查依赖此任务的其他任务
        dependents = self.dependency_graph.get_dependents(task_id)
        for dependent_id in dependents:
            dependency = self.dependency_graph.get_dependency(dependent_id, task_id)
            if dependency and dependency.status == DependencyStatus.PENDING:
                self._is_dependency_satisfied(dependency)

        logger.info(f"任务完成: {task_id}")

    def mark_task_failed(self, task_id: str):
        """标记任务失败"""
        self.failed_tasks.add(task_id)
        self.task_status[task_id] = "failed"

        # 处理依赖此任务的其他任务
        dependents = self.dependency_graph.get_dependents(task_id)
        for dependent_id in dependents:
            dependency = self.dependency_graph.get_dependency(dependent_id, task_id)
            if dependency and dependency.dependency_type == DependencyType.SUCCESS:
                dependency.status = DependencyStatus.FAILED
                self._stats['failed_dependencies'] += 1

        logger.info(f"任务失败: {task_id}")

    def mark_task_cancelled(self, task_id: str):
        """标记任务取消"""
        self.cancelled_tasks.add(task_id)
        self.task_status[task_id] = "cancelled"

        # 取消依赖此任务的其他任务的相关依赖
        dependents = self.dependency_graph.get_dependents(task_id)
        for dependent_id in dependents:
            dependency = self.dependency_graph.get_dependency(dependent_id, task_id)
            if dependency:
                dependency.status = DependencyStatus.CANCELLED

        logger.info(f"任务取消: {task_id}")

    def get_topological_order(self, task_ids: List[str]) -> List[str]:
        """
        获取拓扑排序顺序

        Args:
            task_ids: 任务ID列表

        Returns:
            List[str]: 拓扑排序后的任务ID列表
        """
        try:
            # 使用Kahn算法进行拓扑排序
            in_degree = {}

            # 计算入度
            for task_id in task_ids:
                in_degree[task_id] = len(self.dependency_graph.get_prerequisites(task_id))

            # 初始化队列
            queue = deque([task_id for task_id in task_ids if in_degree[task_id] == 0])
            result = []

            while queue:
                current = queue.popleft()
                result.append(current)

                # 更新依赖任务的入度
                for dependent in self.dependency_graph.get_dependents(current):
                    if dependent in in_degree:
                        in_degree[dependent] -= 1
                        if in_degree[dependent] == 0:
                            queue.append(dependent)

            # 检查是否所有任务都被处理
            if len(result) != len(task_ids):
                remaining_tasks = [task_id for task_id in task_ids if task_id not in result]
                logger.warning(f"拓扑排序未完成，剩余任务: {remaining_tasks}")

            return result

        except Exception as e:
            logger.error(f"拓扑排序失败: {e}")
            return task_ids  # 返回原始顺序

    def detect_deadlocks(self) -> List[List[str]]:
        """检测死锁"""
        deadlocks = []

        # 查找强连通分量
        strongly_connected_components = self._find_strongly_connected_components()

        for component in strongly_connected_components:
            if len(component) > 1:
                # 多个节点的强连通分量可能是死锁
                if self._is_deadlock(component):
                    deadlocks.append(component)
                    self._stats['deadlocks_prevented'] += 1

        return deadlocks

    def _find_strongly_connected_components(self) -> List[List[str]]:
        """查找强连通分量（使用Tarjan算法）"""
        index_counter = [0]
        stack = []
        lowlinks = {}
        index = {}
        on_stack = {}
        components = []

        def strongconnect(node):
            index[node] = index_counter[0]
            lowlinks[node] = index_counter[0]
            index_counter[0] += 1
            stack.append(node)
            on_stack[node] = True

            # 访问所有依赖节点
            for dependent in self.dependency_graph.edges.get(node, set()):
                if dependent not in index:
                    strongconnect(dependent)
                    lowlinks[node] = min(lowlinks[node], lowlinks[dependent])
                elif on_stack.get(dependent, False):
                    lowlinks[node] = min(lowlinks[node], index[dependent])

            # 如果node是强连通分量的根
            if lowlinks[node] == index[node]:
                component = []
                while True:
                    w = stack.pop()
                    on_stack[w] = False
                    component.append(w)
                    if w == node:
                        break
                components.append(component)

        # 对所有未访问的节点执行算法
        for node in self.dependency_graph.nodes:
            if node not in index:
                strongconnect(node)

        return components

    def _is_deadlock(self, component: List[str]) -> bool:
        """检查强连通分量是否为死锁"""
        # 简单检查：如果组件中的任务都在等待其他任务完成，则可能是死锁
        for task_id in component:
            if task_id in self.completed_tasks or task_id in self.failed_tasks:
                return False  # 如果有任务已完成，则不是死锁

        # 检查是否所有任务都有未满足的依赖
        for task_id in component:
            if self._is_task_ready(task_id):
                return False  # 如果有任务准备好执行，则不是死锁

        return True

    def register_condition_evaluator(self, condition_name: str, evaluator: callable):
        """注册条件评估器"""
        self.condition_evaluators[condition_name] = evaluator
        logger.info(f"注册条件评估器: {condition_name}")

    def get_dependency_status(self, dependent_task_id: str, prerequisite_task_id: str) -> Optional[DependencyStatus]:
        """获取依赖状态"""
        dependency = self.dependency_graph.get_dependency(dependent_task_id, prerequisite_task_id)
        return dependency.status if dependency else None

    def get_task_dependencies(self, task_id: str) -> List[TaskDependency]:
        """获取任务的所有依赖"""
        dependencies = []
        prerequisites = self.dependency_graph.get_prerequisites(task_id)

        for prereq_id in prerequisites:
            dependency = self.dependency_graph.get_dependency(task_id, prereq_id)
            if dependency:
                dependencies.append(dependency)

        return dependencies

    def get_dependency_chain(self, task_id: str) -> List[str]:
        """获取任务的完整依赖链"""
        visited = set()
        chain = []

        def dfs(current_task_id: str):
            if current_task_id in visited:
                return

            visited.add(current_task_id)
            prerequisites = self.dependency_graph.get_prerequisites(current_task_id)

            for prereq_id in prerequisites:
                dfs(prereq_id)

            chain.append(current_task_id)

        dfs(task_id)
        return chain

    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        stats = self._stats.copy()
        stats.update({
            'total_tasks': len(self.dependency_graph.nodes),
            'completed_tasks': len(self.completed_tasks),
            'failed_tasks': len(self.failed_tasks),
            'cancelled_tasks': len(self.cancelled_tasks),
            'pending_dependencies': self._stats['total_dependencies'] - self._stats['satisfied_dependencies'] - self._stats['failed_dependencies']
        })
        return stats

    def clear_completed_tasks(self, older_than_hours: int = 24):
        """清理已完成的任务记录"""
        # 这里可以实现基于时间的清理逻辑
        # 暂时保持简单实现
        pass

    def validate_dependency_graph(self) -> Dict[str, Any]:
        """验证依赖图的完整性"""
        validation_result = {
            'is_valid': True,
            'issues': [],
            'warnings': []
        }

        # 检查循环依赖
        cycle = self._detect_cycle(self.dependency_graph)
        if cycle:
            validation_result['is_valid'] = False
            validation_result['issues'].append(f"检测到循环依赖: {' -> '.join(cycle)}")

        # 检查死锁
        deadlocks = self.detect_deadlocks()
        if deadlocks:
            validation_result['warnings'].extend([
                f"检测到潜在死锁: {deadlock}" for deadlock in deadlocks
            ])

        # 检查孤立节点
        isolated_nodes = []
        for node in self.dependency_graph.nodes:
            if (not self.dependency_graph.get_prerequisites(node) and
                    not self.dependency_graph.get_dependents(node)):
                isolated_nodes.append(node)

        if isolated_nodes:
            validation_result['warnings'].append(f"发现孤立节点: {isolated_nodes}")

        return validation_result


# 全局单例实例
_dependency_resolver: Optional[DependencyResolver] = None


def get_dependency_resolver() -> DependencyResolver:
    """获取全局依赖解析器实例"""
    global _dependency_resolver

    if _dependency_resolver is None:
        _dependency_resolver = DependencyResolver()

    return _dependency_resolver
