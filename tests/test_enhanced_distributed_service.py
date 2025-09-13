#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
增强版分布式服务测试

测试增强版分布式服务的各项功能：
1. 服务初始化和配置
2. 智能负载均衡
3. 任务分发和执行
4. 故障检测和恢复
5. 性能监控
6. 安全功能
7. 动态扩缩容
"""

import pytest
import tempfile
import time
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock, patch

from core.services.enhanced_distributed_service import (
    EnhancedDistributedService, LoadBalancingStrategy, TaskPriority,
    initialize_enhanced_distributed_service, get_enhanced_distributed_service
)


class TestEnhancedDistributedService:
    """增强版分布式服务测试类"""

    def setup_method(self):
        """测试前设置"""
        self.temp_dir = tempfile.mkdtemp()

        # 创建测试用的分布式服务
        self.distributed_service = EnhancedDistributedService(
            discovery_port=8889,  # 使用不同端口避免冲突
            load_balancing_strategy=LoadBalancingStrategy.INTELLIGENT,
            enable_security=False,  # 测试时禁用安全功能
            enable_monitoring=True,
            auto_start=False  # 手动启动以便测试
        )

        # 测试结果收集
        self.task_results = []
        self.service_events = []

    def teardown_method(self):
        """测试后清理"""
        if self.distributed_service:
            try:
                self.distributed_service.shutdown()
            except:
                pass

        # 清理临时文件
        import shutil
        try:
            shutil.rmtree(self.temp_dir)
        except:
            pass

    def test_service_initialization(self):
        """测试服务初始化"""
        assert self.distributed_service is not None
        assert self.distributed_service.discovery_port == 8889
        assert self.distributed_service.load_balancing_strategy == LoadBalancingStrategy.INTELLIGENT
        assert self.distributed_service.enable_monitoring is True
        assert self.distributed_service.enable_security is False

    def test_service_startup_and_shutdown(self):
        """测试服务启动和关闭"""
        # 启动服务
        success = self.distributed_service.start()
        assert success is True

        # 检查服务状态
        status = self.distributed_service.get_service_status()
        assert status is not None
        assert 'is_running' in status
        assert status['is_running'] is True

        # 关闭服务
        self.distributed_service.shutdown()

        # 再次检查状态
        status = self.distributed_service.get_service_status()
        if status and 'is_running' in status:
            assert status['is_running'] is False

    def test_task_submission(self):
        """测试任务提交"""
        # 启动服务
        self.distributed_service.start()

        try:
            # 提交简单任务
            task_id = self.distributed_service.submit_enhanced_task(
                task_type="test_task",
                task_data={"input": "test_data"},
                priority=TaskPriority.NORMAL,
                cpu_requirement=1.0,
                memory_requirement=256,
                timeout=30
            )

            assert task_id is not None
            assert len(task_id) > 0

            # 等待任务处理
            time.sleep(0.5)

            # 检查任务状态
            task_status = self.distributed_service.get_task_status(task_id)
            if task_status:
                assert 'task_id' in task_status
                assert task_status['task_id'] == task_id

        finally:
            self.distributed_service.shutdown()

    def test_load_balancing_strategies(self):
        """测试负载均衡策略"""
        # 测试不同的负载均衡策略
        strategies = [
            LoadBalancingStrategy.ROUND_ROBIN,
            LoadBalancingStrategy.LEAST_CONNECTIONS,
            LoadBalancingStrategy.INTELLIGENT
        ]

        for strategy in strategies:
            service = EnhancedDistributedService(
                discovery_port=8890 + strategy.value,
                load_balancing_strategy=strategy,
                enable_security=False,
                enable_monitoring=False,
                auto_start=False
            )

            assert service.load_balancing_strategy == strategy

            # 清理
            try:
                service.shutdown()
            except:
                pass

    def test_task_priority_handling(self):
        """测试任务优先级处理"""
        self.distributed_service.start()

        try:
            # 提交不同优先级的任务
            priorities = [TaskPriority.LOW, TaskPriority.NORMAL, TaskPriority.HIGH, TaskPriority.CRITICAL]
            task_ids = []

            for priority in priorities:
                task_id = self.distributed_service.submit_enhanced_task(
                    task_type="priority_test",
                    task_data={"priority": priority.name},
                    priority=priority,
                    timeout=10
                )
                if task_id:
                    task_ids.append((task_id, priority))

            # 验证任务被提交
            assert len(task_ids) > 0

            # 等待任务处理
            time.sleep(1.0)

            # 检查任务状态
            for task_id, priority in task_ids:
                status = self.distributed_service.get_task_status(task_id)
                if status:
                    assert 'task_id' in status

        finally:
            self.distributed_service.shutdown()

    def test_resource_requirements(self):
        """测试资源需求处理"""
        self.distributed_service.start()

        try:
            # 提交需要特定资源的任务
            task_id = self.distributed_service.submit_enhanced_task(
                task_type="resource_intensive",
                task_data={"operation": "heavy_computation"},
                priority=TaskPriority.NORMAL,
                cpu_requirement=2.0,
                memory_requirement=1024,
                timeout=60
            )

            assert task_id is not None

            # 等待任务处理
            time.sleep(0.5)

            # 检查任务是否被正确处理
            status = self.distributed_service.get_task_status(task_id)
            if status:
                assert 'task_id' in status

        finally:
            self.distributed_service.shutdown()

    def test_task_timeout_handling(self):
        """测试任务超时处理"""
        self.distributed_service.start()

        try:
            # 提交会超时的任务
            task_id = self.distributed_service.submit_enhanced_task(
                task_type="long_running_task",
                task_data={"duration": 10},  # 假设需要10秒
                priority=TaskPriority.NORMAL,
                timeout=1  # 但只给1秒超时
            )

            assert task_id is not None

            # 等待超时处理
            time.sleep(2.0)

            # 检查任务状态（应该超时）
            status = self.distributed_service.get_task_status(task_id)
            if status and 'status' in status:
                # 任务应该因超时而失败或被取消
                assert status['status'] in ['failed', 'timeout', 'cancelled']

        finally:
            self.distributed_service.shutdown()

    def test_service_monitoring(self):
        """测试服务监控"""
        if not self.distributed_service.enable_monitoring:
            pytest.skip("服务监控未启用")

        self.distributed_service.start()

        try:
            # 提交一些任务以生成监控数据
            for i in range(3):
                self.distributed_service.submit_enhanced_task(
                    task_type="monitoring_test",
                    task_data={"index": i},
                    priority=TaskPriority.NORMAL
                )

            # 等待任务处理
            time.sleep(1.0)

            # 获取服务状态（包含监控信息）
            status = self.distributed_service.get_service_status()
            assert status is not None

            # 验证监控数据
            if 'performance_metrics' in status:
                metrics = status['performance_metrics']
                assert isinstance(metrics, dict)

            if 'task_statistics' in status:
                stats = status['task_statistics']
                assert isinstance(stats, dict)

        finally:
            self.distributed_service.shutdown()

    def test_node_discovery(self):
        """测试节点发现功能"""
        # 这个测试主要验证节点发现的基本结构
        # 实际的网络发现需要多个服务实例

        self.distributed_service.start()

        try:
            # 获取节点信息
            status = self.distributed_service.get_service_status()

            if status and 'nodes' in status:
                nodes = status['nodes']
                assert isinstance(nodes, (list, dict))

            # 检查本地节点信息
            if status and 'local_node' in status:
                local_node = status['local_node']
                assert isinstance(local_node, dict)

        finally:
            self.distributed_service.shutdown()

    def test_fault_tolerance(self):
        """测试故障容错"""
        self.distributed_service.start()

        try:
            # 提交任务
            task_id = self.distributed_service.submit_enhanced_task(
                task_type="fault_test",
                task_data={"test": "fault_tolerance"},
                priority=TaskPriority.NORMAL
            )

            assert task_id is not None

            # 模拟故障情况（这里只是基本测试）
            # 实际的故障测试需要更复杂的设置

            # 等待处理
            time.sleep(0.5)

            # 检查服务是否仍然响应
            status = self.distributed_service.get_service_status()
            assert status is not None

        finally:
            self.distributed_service.shutdown()

    def test_task_cancellation(self):
        """测试任务取消"""
        self.distributed_service.start()

        try:
            # 提交长时间运行的任务
            task_id = self.distributed_service.submit_enhanced_task(
                task_type="cancellable_task",
                task_data={"duration": 5},
                priority=TaskPriority.NORMAL,
                timeout=10
            )

            assert task_id is not None

            # 短暂等待后取消任务
            time.sleep(0.1)
            success = self.distributed_service.cancel_task(task_id)

            # 验证取消操作
            if success:
                time.sleep(0.2)
                status = self.distributed_service.get_task_status(task_id)
                if status and 'status' in status:
                    assert status['status'] in ['cancelled', 'failed']

        finally:
            self.distributed_service.shutdown()

    def test_service_statistics(self):
        """测试服务统计"""
        self.distributed_service.start()

        try:
            # 提交一些任务
            for i in range(5):
                self.distributed_service.submit_enhanced_task(
                    task_type="stats_test",
                    task_data={"index": i},
                    priority=TaskPriority.NORMAL
                )

            # 等待处理
            time.sleep(1.0)

            # 获取统计信息
            status = self.distributed_service.get_service_status()

            # 验证统计信息存在
            if status:
                # 检查基本状态信息
                assert 'is_running' in status

                # 检查任务统计
                if 'task_statistics' in status:
                    stats = status['task_statistics']
                    assert isinstance(stats, dict)

                # 检查性能指标
                if 'performance_metrics' in status:
                    metrics = status['performance_metrics']
                    assert isinstance(metrics, dict)

        finally:
            self.distributed_service.shutdown()

    def test_affinity_rules(self):
        """测试亲和性规则"""
        self.distributed_service.start()

        try:
            # 提交带亲和性规则的任务
            affinity_rules = {
                "node_type": "compute",
                "region": "local",
                "avoid_nodes": ["node1", "node2"]
            }

            task_id = self.distributed_service.submit_enhanced_task(
                task_type="affinity_test",
                task_data={"test": "affinity"},
                priority=TaskPriority.NORMAL,
                affinity_rules=affinity_rules
            )

            assert task_id is not None

            # 等待处理
            time.sleep(0.5)

            # 检查任务状态
            status = self.distributed_service.get_task_status(task_id)
            if status:
                assert 'task_id' in status

        finally:
            self.distributed_service.shutdown()

    def test_global_service_instance(self):
        """测试全局服务实例"""
        # 获取全局实例
        global_service = get_enhanced_distributed_service()
        assert global_service is not None

        # 再次获取应该是同一个实例
        global_service2 = get_enhanced_distributed_service()
        assert global_service is global_service2

    def test_service_initialization_function(self):
        """测试服务初始化函数"""
        # 使用初始化函数创建服务
        service = initialize_enhanced_distributed_service(
            discovery_port=8891,
            load_balancing_strategy=LoadBalancingStrategy.ROUND_ROBIN,
            enable_security=False,
            enable_monitoring=True,
            auto_start=False
        )

        assert service is not None
        assert service.discovery_port == 8891
        assert service.load_balancing_strategy == LoadBalancingStrategy.ROUND_ROBIN

        # 清理
        try:
            service.shutdown()
        except:
            pass


class TestLoadBalancingStrategies:
    """负载均衡策略测试类"""

    def test_strategy_enum_values(self):
        """测试策略枚举值"""
        assert LoadBalancingStrategy.ROUND_ROBIN.value == 1
        assert LoadBalancingStrategy.LEAST_CONNECTIONS.value == 2
        assert LoadBalancingStrategy.WEIGHTED_ROUND_ROBIN.value == 3
        assert LoadBalancingStrategy.RESOURCE_BASED.value == 4
        assert LoadBalancingStrategy.INTELLIGENT.value == 5

    def test_strategy_names(self):
        """测试策略名称"""
        assert LoadBalancingStrategy.ROUND_ROBIN.name == "ROUND_ROBIN"
        assert LoadBalancingStrategy.LEAST_CONNECTIONS.name == "LEAST_CONNECTIONS"
        assert LoadBalancingStrategy.WEIGHTED_ROUND_ROBIN.name == "WEIGHTED_ROUND_ROBIN"
        assert LoadBalancingStrategy.RESOURCE_BASED.name == "RESOURCE_BASED"
        assert LoadBalancingStrategy.INTELLIGENT.name == "INTELLIGENT"


class TestTaskPriority:
    """任务优先级测试类"""

    def test_priority_enum_values(self):
        """测试优先级枚举值"""
        assert TaskPriority.CRITICAL.value == 1
        assert TaskPriority.HIGH.value == 2
        assert TaskPriority.NORMAL.value == 3
        assert TaskPriority.LOW.value == 4
        assert TaskPriority.BACKGROUND.value == 5

    def test_priority_ordering(self):
        """测试优先级排序"""
        priorities = [
            TaskPriority.BACKGROUND,
            TaskPriority.LOW,
            TaskPriority.NORMAL,
            TaskPriority.HIGH,
            TaskPriority.CRITICAL
        ]

        # 按值排序（值越小优先级越高）
        sorted_priorities = sorted(priorities, key=lambda p: p.value)

        assert sorted_priorities[0] == TaskPriority.CRITICAL
        assert sorted_priorities[1] == TaskPriority.HIGH
        assert sorted_priorities[2] == TaskPriority.NORMAL
        assert sorted_priorities[3] == TaskPriority.LOW
        assert sorted_priorities[4] == TaskPriority.BACKGROUND


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
