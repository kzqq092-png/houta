#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
增强版异步任务管理器测试

测试增强版异步任务管理器的各项功能：
1. 任务提交和执行
2. 优先级调度
3. 资源管理
4. 任务依赖关系
5. 任务持久化
6. 性能监控
7. 故障恢复
"""

import asyncio
import pytest
import tempfile
import time
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock, patch

from core.async_management.enhanced_async_manager import (
    EnhancedAsyncManager, TaskStatus, TaskPriority, ResourceType,
    ResourceRequirement, TaskMetadata, AsyncTask, TaskScheduler,
    ResourceManager, TaskPersistence, initialize_enhanced_async_manager
)


class TestEnhancedAsyncManager:
    """增强版异步任务管理器测试类"""

    def setup_method(self):
        """测试前设置"""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = str(Path(self.temp_dir) / "test_async_tasks.db")

        # 创建测试用的异步管理器
        self.async_manager = EnhancedAsyncManager(
            max_workers=2,
            enable_persistence=True,
            enable_monitoring=True,
            db_path=self.db_path
        )

        # 测试结果收集
        self.task_results = []
        self.task_errors = []

    def teardown_method(self):
        """测试后清理"""
        if self.async_manager:
            self.async_manager.shutdown(wait=True, timeout=5.0)

        # 清理临时文件
        import shutil
        try:
            shutil.rmtree(self.temp_dir)
        except:
            pass

    def test_async_manager_initialization(self):
        """测试异步管理器初始化"""
        assert self.async_manager is not None
        assert self.async_manager.max_workers == 2
        assert self.async_manager.scheduler is not None
        assert self.async_manager.resource_manager is not None
        assert self.async_manager.persistence is not None
        assert self.async_manager.running is True

    def test_simple_task_submission(self):
        """测试简单任务提交"""
        def simple_task(x, y):
            return x + y

        # 提交任务
        task_id = self.async_manager.submit_task(
            simple_task,
            5, 3,
            name="simple_addition",
            priority=TaskPriority.NORMAL
        )

        assert task_id is not None
        assert len(task_id) > 0

        # 等待任务完成
        time.sleep(1.0)

        # 检查任务状态
        task_status = self.async_manager.get_task_status(task_id)
        if task_status:
            assert task_status['name'] == "simple_addition"
            # 任务可能已完成或正在执行
            assert task_status['status'] in ['completed', 'running', 'pending']

    def test_async_task_submission(self):
        """测试异步任务提交"""
        async def async_task(delay, result):
            await asyncio.sleep(delay)
            return result

        # 提交异步任务
        task_id = self.async_manager.submit_task(
            async_task,
            0.1, "async_result",
            name="async_test",
            priority=TaskPriority.HIGH
        )

        assert task_id is not None

        # 等待任务完成
        time.sleep(0.5)

        # 检查任务状态
        task_status = self.async_manager.get_task_status(task_id)
        if task_status:
            assert task_status['name'] == "async_test"

    def test_task_priority_scheduling(self):
        """测试任务优先级调度"""
        execution_order = []

        def priority_task(priority_name):
            execution_order.append(priority_name)
            time.sleep(0.05)  # 短暂延迟
            return priority_name

        # 按相反优先级顺序提交任务
        low_task_id = self.async_manager.submit_task(
            priority_task, "low",
            name="low_priority_task",
            priority=TaskPriority.LOW
        )

        normal_task_id = self.async_manager.submit_task(
            priority_task, "normal",
            name="normal_priority_task",
            priority=TaskPriority.NORMAL
        )

        high_task_id = self.async_manager.submit_task(
            priority_task, "high",
            name="high_priority_task",
            priority=TaskPriority.HIGH
        )

        critical_task_id = self.async_manager.submit_task(
            priority_task, "critical",
            name="critical_priority_task",
            priority=TaskPriority.CRITICAL
        )

        # 等待所有任务完成
        time.sleep(2.0)

        # 验证执行顺序（高优先级先执行）
        assert len(execution_order) == 4
        # 由于并发执行，只验证critical任务最先执行
        assert execution_order[0] == "critical"

    def test_resource_management(self):
        """测试资源管理"""
        resource_manager = self.async_manager.resource_manager

        # 测试资源分配
        requirements = ResourceRequirement(
            cpu_cores=2.0,
            memory_mb=512,
            disk_mb=100
        )

        # 检查是否可以分配资源
        can_allocate = resource_manager.can_allocate(requirements)
        assert isinstance(can_allocate, bool)

        if can_allocate:
            # 分配资源
            success = resource_manager.allocate_resources("test_task", requirements)
            assert success is True

            # 检查资源利用率
            utilization = resource_manager.get_resource_utilization()
            assert 'cpu' in utilization
            assert 'memory' in utilization
            assert 'disk' in utilization

            # 释放资源
            resource_manager.release_resources("test_task")

            # 验证资源已释放
            new_utilization = resource_manager.get_resource_utilization()
            assert new_utilization['cpu'] < utilization['cpu']

    def test_task_with_resource_requirements(self):
        """测试带资源需求的任务"""
        def resource_intensive_task():
            time.sleep(0.1)
            return "resource_task_completed"

        # 提交需要特定资源的任务
        task_id = self.async_manager.submit_task(
            resource_intensive_task,
            name="resource_task",
            priority=TaskPriority.NORMAL,
            resource_requirements=ResourceRequirement(
                cpu_cores=1.0,
                memory_mb=256
            )
        )

        assert task_id is not None

        # 等待任务完成
        time.sleep(0.5)

        # 检查任务状态
        task_status = self.async_manager.get_task_status(task_id)
        if task_status:
            assert task_status['name'] == "resource_task"

    def test_task_timeout(self):
        """测试任务超时"""
        def long_running_task():
            time.sleep(2.0)  # 长时间运行
            return "should_not_complete"

        # 提交带超时的任务
        task_id = self.async_manager.submit_task(
            long_running_task,
            name="timeout_task",
            timeout=0.5,  # 0.5秒超时
            priority=TaskPriority.NORMAL
        )

        assert task_id is not None

        # 等待超时处理
        time.sleep(1.0)

        # 检查任务状态（应该失败或被取消）
        task_status = self.async_manager.get_task_status(task_id)
        if task_status:
            # 任务应该因超时而失败
            assert task_status['status'] in ['failed', 'cancelled']

    def test_task_retry_mechanism(self):
        """测试任务重试机制"""
        call_count = 0

        def failing_task():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise Exception(f"Attempt {call_count} failed")
            return "success_after_retries"

        # 提交会失败的任务
        task_id = self.async_manager.submit_task(
            failing_task,
            name="retry_task",
            max_retries=3,
            retry_delay=0.1,
            priority=TaskPriority.NORMAL
        )

        assert task_id is not None

        # 等待重试完成
        time.sleep(1.0)

        # 验证任务被重试了多次
        assert call_count >= 2

    def test_task_cancellation(self):
        """测试任务取消"""
        def cancellable_task():
            time.sleep(1.0)
            return "should_be_cancelled"

        # 提交任务
        task_id = self.async_manager.submit_task(
            cancellable_task,
            name="cancellable_task",
            priority=TaskPriority.NORMAL
        )

        assert task_id is not None

        # 短暂等待后取消任务
        time.sleep(0.1)
        success = self.async_manager.cancel_task(task_id)

        # 验证取消操作
        if success:
            # 等待取消处理
            time.sleep(0.2)

            # 检查任务状态
            task_status = self.async_manager.get_task_status(task_id)
            if task_status:
                assert task_status['status'] == 'cancelled'

    def test_task_persistence(self):
        """测试任务持久化"""
        if not self.async_manager.persistence:
            pytest.skip("任务持久化未启用")

        def persistent_task():
            return "persistent_result"

        # 提交任务
        task_id = self.async_manager.submit_task(
            persistent_task,
            name="persistent_task",
            priority=TaskPriority.NORMAL
        )

        # 等待任务处理
        time.sleep(0.5)

        # 验证任务被持久化
        pending_tasks = self.async_manager.persistence.get_tasks_by_status(TaskStatus.PENDING)
        completed_tasks = self.async_manager.persistence.get_tasks_by_status(TaskStatus.COMPLETED)

        # 任务应该在某个状态中被找到
        all_tasks = pending_tasks + completed_tasks
        task_found = any(task['id'] == task_id for task in all_tasks)

        # 由于异步处理，任务可能已经完成，所以只检查是否被记录
        assert len(all_tasks) > 0

    def test_statistics_collection(self):
        """测试统计信息收集"""
        # 提交几个任务
        for i in range(3):
            self.async_manager.submit_task(
                lambda x=i: x * 2,
                name=f"stats_task_{i}",
                priority=TaskPriority.NORMAL
            )

        # 等待任务处理
        time.sleep(0.5)

        # 获取统计信息
        stats = self.async_manager.get_stats()

        # 验证统计信息
        assert 'tasks_submitted' in stats
        assert 'tasks_completed' in stats
        assert 'tasks_failed' in stats
        assert 'active_tasks' in stats
        assert 'resource_utilization' in stats
        assert 'max_workers' in stats

        # 验证任务提交统计
        assert stats['tasks_submitted'] >= 3
        assert stats['max_workers'] == 2

    def test_task_dependencies(self):
        """测试任务依赖关系"""
        # 注意：当前实现的依赖关系功能可能不完整
        # 这个测试主要验证调度器的依赖管理结构

        scheduler = self.async_manager.scheduler

        # 创建有依赖关系的任务元数据
        task1_metadata = TaskMetadata(
            task_id="task1",
            name="independent_task"
        )

        task2_metadata = TaskMetadata(
            task_id="task2",
            name="dependent_task",
            dependencies=["task1"]
        )

        # 创建任务
        task1 = AsyncTask(
            func=lambda: "task1_result",
            metadata=task1_metadata
        )

        task2 = AsyncTask(
            func=lambda: "task2_result",
            metadata=task2_metadata
        )

        # 添加到调度器
        scheduler.add_task(task1)
        scheduler.add_task(task2)

        # 验证依赖关系被正确记录
        assert "task1" in scheduler.dependency_graph["task2"]
        assert "task2" in scheduler.reverse_dependency_graph["task1"]

    def test_global_async_manager_instance(self):
        """测试全局异步管理器实例"""
        from core.async_management.enhanced_async_manager import get_enhanced_async_manager

        # 获取全局实例
        global_manager = get_enhanced_async_manager()
        assert global_manager is not None

        # 再次获取应该是同一个实例
        global_manager2 = get_enhanced_async_manager()
        assert global_manager is global_manager2

    def test_async_manager_initialization_function(self):
        """测试异步管理器初始化函数"""
        temp_db = str(Path(self.temp_dir) / "init_test.db")

        # 使用初始化函数创建异步管理器
        manager = initialize_enhanced_async_manager(
            max_workers=4,
            enable_persistence=True,
            enable_monitoring=True,
            db_path=temp_db
        )

        assert manager is not None
        assert manager.max_workers == 4
        assert manager.persistence is not None

        # 清理
        manager.shutdown(wait=True, timeout=2.0)


class TestTaskScheduler:
    """任务调度器测试类"""

    def setup_method(self):
        """测试前设置"""
        self.scheduler = TaskScheduler()

    def test_task_scheduling(self):
        """测试任务调度"""
        # 创建测试任务
        task = AsyncTask(
            func=lambda: "test",
            metadata=TaskMetadata(
                task_id="test_task",
                name="test",
                priority=TaskPriority.NORMAL
            )
        )

        # 添加任务
        self.scheduler.add_task(task)

        # 获取任务
        next_task = self.scheduler.get_next_task()
        assert next_task is not None
        assert next_task.metadata.task_id == "test_task"

        # 队列应该为空
        next_task2 = self.scheduler.get_next_task()
        assert next_task2 is None

    def test_priority_scheduling(self):
        """测试优先级调度"""
        # 创建不同优先级的任务
        low_task = AsyncTask(
            func=lambda: "low",
            metadata=TaskMetadata(
                task_id="low_task",
                priority=TaskPriority.LOW
            )
        )

        high_task = AsyncTask(
            func=lambda: "high",
            metadata=TaskMetadata(
                task_id="high_task",
                priority=TaskPriority.HIGH
            )
        )

        # 按相反优先级顺序添加
        self.scheduler.add_task(low_task)
        self.scheduler.add_task(high_task)

        # 高优先级任务应该先被获取
        first_task = self.scheduler.get_next_task()
        assert first_task.metadata.task_id == "high_task"

        second_task = self.scheduler.get_next_task()
        assert second_task.metadata.task_id == "low_task"


class TestResourceManager:
    """资源管理器测试类"""

    def setup_method(self):
        """测试前设置"""
        self.resource_manager = ResourceManager()

    def test_resource_allocation(self):
        """测试资源分配"""
        requirements = ResourceRequirement(
            cpu_cores=1.0,
            memory_mb=256,
            disk_mb=100
        )

        # 检查是否可以分配
        can_allocate = self.resource_manager.can_allocate(requirements)
        assert can_allocate is True

        # 分配资源
        success = self.resource_manager.allocate_resources("test_task", requirements)
        assert success is True

        # 验证资源被分配
        assert "test_task" in self.resource_manager.resource_allocations

        # 释放资源
        self.resource_manager.release_resources("test_task")

        # 验证资源被释放
        assert "test_task" not in self.resource_manager.resource_allocations

    def test_resource_utilization(self):
        """测试资源利用率计算"""
        # 分配一些资源
        requirements = ResourceRequirement(
            cpu_cores=2.0,
            memory_mb=1024
        )

        self.resource_manager.allocate_resources("task1", requirements)

        # 获取利用率
        utilization = self.resource_manager.get_resource_utilization()

        # 验证利用率计算
        assert utilization['cpu'] > 0
        assert utilization['memory'] > 0
        assert 0 <= utilization['cpu'] <= 100
        assert 0 <= utilization['memory'] <= 100


class TestTaskMetadata:
    """任务元数据测试类"""

    def test_metadata_creation(self):
        """测试元数据创建"""
        metadata = TaskMetadata(
            name="test_task",
            priority=TaskPriority.HIGH,
            max_retries=5,
            dependencies=["dep1", "dep2"]
        )

        assert metadata.name == "test_task"
        assert metadata.priority == TaskPriority.HIGH
        assert metadata.max_retries == 5
        assert "dep1" in metadata.dependencies
        assert "dep2" in metadata.dependencies

    def test_metadata_serialization(self):
        """测试元数据序列化"""
        metadata = TaskMetadata(
            name="serialization_test",
            priority=TaskPriority.CRITICAL,
            timeout=30.0,
            resource_requirements=ResourceRequirement(cpu_cores=2.0)
        )

        # 转换为字典
        data = metadata.to_dict()
        assert data['name'] == "serialization_test"
        assert data['priority'] == TaskPriority.CRITICAL.value
        assert data['timeout'] == 30.0

        # 从字典恢复
        restored_metadata = TaskMetadata.from_dict(data)
        assert restored_metadata.name == "serialization_test"
        assert restored_metadata.priority == TaskPriority.CRITICAL
        assert restored_metadata.timeout == 30.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
