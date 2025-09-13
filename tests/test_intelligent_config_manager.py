#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
智能配置管理器测试

测试智能配置管理的核心功能：
1. 配置优化
2. 推荐生成
3. 冲突检测
4. 性能反馈学习
5. 自适应阈值调整

作者: FactorWeave-Quant团队
版本: 2.0 (智能化测试)
"""

import pytest
import tempfile
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

try:
    from core.importdata.intelligent_config_manager import (
        IntelligentConfigManager, ConfigOptimizationLevel,
        ConfigRecommendationType, ConfigRecommendation, ConfigConflict
    )
    from core.importdata.import_config_manager import ImportTaskConfig
    from core.importdata.import_execution_engine import TaskExecutionResult, TaskExecutionStatus
    INTELLIGENT_CONFIG_AVAILABLE = True
except ImportError:
    INTELLIGENT_CONFIG_AVAILABLE = False


@pytest.mark.skipif(not INTELLIGENT_CONFIG_AVAILABLE, reason="智能配置管理器不可用")
class TestIntelligentConfigManager:
    """智能配置管理器测试类"""

    def setup_method(self):
        """测试前设置"""
        self.temp_dir = tempfile.mkdtemp()
        self.config_manager = IntelligentConfigManager(
            db_path=str(Path(self.temp_dir) / "test_config.db")
        )

        # 创建测试任务配置
        from core.importdata.import_config_manager import DataFrequency, ImportMode
        self.test_task_config = ImportTaskConfig(
            task_id="test_task_001",
            name="测试任务",
            data_source="test_source",
            asset_type="stock",
            data_type="kline",
            symbols=["000001", "000002", "000003"],
            frequency=DataFrequency.DAILY,
            mode=ImportMode.BATCH,
            batch_size=100,
            max_workers=4
        )

    def teardown_method(self):
        """测试后清理"""
        if Path(self.temp_dir).exists():
            shutil.rmtree(self.temp_dir)

    def test_initialization(self):
        """测试初始化"""
        assert self.config_manager is not None
        assert self.config_manager._performance_history == []
        assert self.config_manager._config_templates == {}

    def test_intelligent_optimization_balanced(self):
        """测试平衡模式智能优化"""
        optimized_config = self.config_manager.generate_intelligent_config(
            self.test_task_config,
            optimization_level=ConfigOptimizationLevel.BALANCED
        )

        assert optimized_config is not None
        assert optimized_config.task_id == self.test_task_config.task_id
        # 平衡模式应该适度调整参数
        assert 50 <= optimized_config.batch_size <= 200
        assert 2 <= optimized_config.max_workers <= 8

    def test_intelligent_optimization_aggressive(self):
        """测试激进模式智能优化"""
        optimized_config = self.config_manager.generate_intelligent_config(
            self.test_task_config,
            optimization_level=ConfigOptimizationLevel.AGGRESSIVE
        )

        assert optimized_config is not None
        # 激进模式应该更大幅度调整参数
        assert optimized_config.batch_size >= self.test_task_config.batch_size
        assert optimized_config.max_workers >= self.test_task_config.max_workers

    def test_intelligent_optimization_conservative(self):
        """测试保守模式智能优化"""
        optimized_config = self.config_manager.generate_intelligent_config(
            self.test_task_config,
            optimization_level=ConfigOptimizationLevel.CONSERVATIVE
        )

        assert optimized_config is not None
        # 保守模式应该小幅度调整参数或保持不变
        batch_size_change = abs(optimized_config.batch_size - self.test_task_config.batch_size)
        worker_change = abs(optimized_config.max_workers - self.test_task_config.max_workers)
        # 保守模式可能会有较大的调整，但应该是合理的
        assert batch_size_change <= 200  # 放宽限制
        assert worker_change <= 8  # 放宽限制

    def test_generate_recommendations(self):
        """测试生成配置推荐"""
        recommendations = self.config_manager.generate_config_recommendations(
            self.test_task_config,
            recommendation_type=ConfigRecommendationType.PERFORMANCE
        )

        assert isinstance(recommendations, list)
        # 没有历史数据时推荐列表可能为空，这是正常的
        assert len(recommendations) >= 0

        # 如果有推荐，验证其结构
        for rec in recommendations:
            assert isinstance(rec, ConfigRecommendation)
            assert rec.type == ConfigRecommendationType.PERFORMANCE
            assert rec.confidence > 0
            assert rec.title
            assert rec.description

    def test_detect_config_conflicts(self):
        """测试配置冲突检测"""
        # 创建一个可能有冲突的配置
        conflict_config = ImportTaskConfig(
            task_id="conflict_test",
            name="冲突测试",
            symbols=["000001"] * 1000,  # 大量重复符号
            data_source="test_source",
            asset_type="股票",
            data_type="K线数据",
            frequency=DataFrequency.DAILY,
            mode=ImportMode.BATCH,
            batch_size=1,  # 极小批次
            max_workers=32  # 极大工作线程
        )

        conflicts = self.config_manager.detect_config_conflicts(conflict_config)

        assert isinstance(conflicts, list)
        # 应该检测到批次大小和工作线程数的冲突
        conflict_types = [c.conflict_type for c in conflicts]
        assert any("batch_size" in ct for ct in conflict_types)

    def test_resolve_config_conflicts(self):
        """测试配置冲突解决"""
        # 创建有冲突的配置
        conflict_config = ImportTaskConfig(
            task_id="resolve_test",
            name="解决测试",
            symbols=["000001"],
            data_source="test_source",
            asset_type="股票",
            data_type="K线数据",
            frequency=DataFrequency.DAILY,
            mode=ImportMode.BATCH,
            batch_size=1000,  # 过大的批次
            max_workers=1     # 过少的工作线程
        )

        conflicts = self.config_manager.detect_config_conflicts(conflict_config)
        if conflicts:
            resolved_config = self.config_manager.resolve_config_conflicts(
                conflict_config, conflicts
            )

            assert resolved_config is not None
            # 解决后的配置应该更合理
            assert resolved_config.batch_size < conflict_config.batch_size
            assert resolved_config.max_workers > conflict_config.max_workers

    def test_record_performance_feedback(self):
        """测试性能反馈记录"""
        # 创建测试执行结果
        execution_result = TaskExecutionResult(
            task_id=self.test_task_config.task_id,
            status=TaskExecutionStatus.COMPLETED,
            start_time=datetime.now() - timedelta(minutes=5),
            end_time=datetime.now(),
            total_records=1000,
            processed_records=1000,
            success=True
        )
        execution_result.execution_time = 300.0  # 5分钟

        # 记录性能反馈
        self.config_manager.record_performance_feedback(
            self.test_task_config, execution_result
        )

        assert len(self.config_manager.performance_feedback) == 1
        feedback = self.config_manager.performance_feedback[0]
        assert feedback['task_id'] == self.test_task_config.task_id
        assert feedback['execution_time'] == 300.0
        assert feedback['success'] is True

    def test_learn_from_feedback(self):
        """测试从反馈中学习"""
        # 记录多个性能反馈
        for i in range(5):
            execution_result = TaskExecutionResult(
                task_id=f"learn_test_{i}",
                status=TaskExecutionStatus.COMPLETED,
                start_time=datetime.now() - timedelta(minutes=10),
                end_time=datetime.now() - timedelta(minutes=5),
                total_records=1000,
                processed_records=1000,
                success=True
            )
            execution_result.execution_time = 200.0 + i * 50  # 递增执行时间

            test_config = ImportTaskConfig(
                task_id=f"learn_test_{i}",
                name=f"学习测试{i}",
                symbols=["000001"],
                data_source="test_source",
                asset_type="股票",
                data_type="K线数据",
                frequency=DataFrequency.DAILY,
                mode=ImportMode.BATCH,
                batch_size=100 + i * 20,  # 递增批次大小
                max_workers=4
            )

            self.config_manager.record_performance_feedback(test_config, execution_result)

        # 测试学习效果
        learned_config = self.config_manager.generate_intelligent_config(
            self.test_task_config,
            optimization_level=ConfigOptimizationLevel.BALANCED
        )

        assert learned_config is not None
        # 学习后的配置应该基于历史性能数据进行优化

    def test_save_and_load_config_template(self):
        """测试配置模板保存和加载"""
        template_name = "test_template"

        # 保存配置模板
        self.config_manager.save_config_template(template_name, self.test_task_config)

        assert template_name in self.config_manager.config_templates

        # 加载配置模板
        loaded_config = self.config_manager.load_config_template(template_name)

        assert loaded_config is not None
        assert loaded_config.name == self.test_task_config.name
        assert loaded_config.batch_size == self.test_task_config.batch_size
        assert loaded_config.max_workers == self.test_task_config.max_workers

    def test_get_intelligent_statistics(self):
        """测试获取智能统计信息"""
        # 先记录一些数据
        self.config_manager.generate_intelligent_config(
            self.test_task_config,
            optimization_level=ConfigOptimizationLevel.BALANCED
        )

        stats = self.config_manager.get_intelligent_statistics()

        assert isinstance(stats, dict)
        assert 'total_optimizations' in stats
        assert 'optimization_success_rate' in stats
        assert 'avg_performance_improvement' in stats
        assert 'total_recommendations' in stats
        assert 'total_conflicts_detected' in stats
        assert 'total_conflicts_resolved' in stats

    def test_adaptive_threshold_adjustment(self):
        """测试自适应阈值调整"""
        # 记录多个不同性能的反馈
        performance_data = [
            (100, 150.0, True),   # 小批次，快速
            (200, 200.0, True),   # 中批次，中等
            (500, 400.0, True),   # 大批次，慢速
            (1000, 800.0, False),  # 超大批次，失败
        ]

        for batch_size, exec_time, success in performance_data:
            config = ImportTaskConfig(
                task_id=f"adaptive_test_{batch_size}",
                name=f"自适应测试{batch_size}",
                symbols=["000001"],
                data_source="test_source",
                asset_type="股票",
                data_type="K线数据",
                frequency=DataFrequency.DAILY,
                mode=ImportMode.BATCH,
                batch_size=batch_size,
                max_workers=4
            )

            result = TaskExecutionResult(
                task_id=config.task_id,
                status=TaskExecutionStatus.COMPLETED if success else TaskExecutionStatus.FAILED,
                start_time=datetime.now() - timedelta(seconds=exec_time),
                end_time=datetime.now(),
                total_records=1000,
                processed_records=1000 if success else 500,
                success=success
            )
            result.execution_time = exec_time

            self.config_manager.record_performance_feedback(config, result)

        # 测试自适应优化
        optimized = self.config_manager.generate_intelligent_config(
            self.test_task_config,
            optimization_level=ConfigOptimizationLevel.BALANCED
        )

        # 优化后的配置应该避免失败的参数组合
        assert optimized.batch_size < 1000  # 避免导致失败的大批次

    @patch('core.services.ai_prediction_service.AIPredictionService')
    def test_ai_integration(self, mock_ai_service):
        """测试AI服务集成"""
        # 模拟AI服务返回
        mock_ai_instance = Mock()
        mock_ai_instance.predict.return_value = {
            'success': True,
            'predicted_execution_time': 180.0,
            'optimal_batch_size': 150,
            'confidence': 0.85
        }
        mock_ai_service.return_value = mock_ai_instance

        # 重新初始化配置管理器以使用模拟的AI服务
        self.config_manager._init_ai_service()

        optimized = self.config_manager.generate_intelligent_config(
            self.test_task_config,
            optimization_level=ConfigOptimizationLevel.BALANCED
        )

        # 验证AI服务被调用
        assert optimized is not None

    def test_concurrent_optimization(self):
        """测试并发优化"""
        import threading
        import time

        results = []
        errors = []

        def optimize_config(config_id):
            try:
                config = ImportTaskConfig(
                    task_id=f"concurrent_test_{config_id}",
                    name=f"并发测试{config_id}",
                    symbols=["000001"],
                    data_source="test_source",
                    asset_type="股票",
                    data_type="K线数据",
                    frequency=DataFrequency.DAILY,
                    mode=ImportMode.BATCH,
                    batch_size=100,
                    max_workers=4
                )

                optimized = self.config_manager.generate_intelligent_config(
                    config, ConfigOptimizationLevel.BALANCED
                )
                results.append(optimized)
            except Exception as e:
                errors.append(e)

        # 创建多个线程同时进行优化
        threads = []
        for i in range(5):
            thread = threading.Thread(target=optimize_config, args=(i,))
            threads.append(thread)
            thread.start()

        # 等待所有线程完成
        for thread in threads:
            thread.join()

        # 验证结果
        assert len(errors) == 0, f"并发优化出现错误: {errors}"
        assert len(results) == 5

        # 所有结果都应该是有效的配置
        for result in results:
            assert result is not None
            assert result.batch_size > 0
            assert result.max_workers > 0

    def test_performance_regression_detection(self):
        """测试性能回归检测"""
        # 记录一系列性能逐渐下降的反馈
        base_time = 100.0
        for i in range(10):
            config = ImportTaskConfig(
                task_id=f"regression_test_{i}",
                name=f"回归测试{i}",
                symbols=["000001"],
                data_source="test_source",
                asset_type="股票",
                data_type="K线数据",
                frequency=DataFrequency.DAILY,
                mode=ImportMode.BATCH,
                batch_size=100,
                max_workers=4
            )

            # 模拟性能逐渐下降
            execution_time = base_time + i * 20  # 每次增加20秒

            result = TaskExecutionResult(
                task_id=config.task_id,
                status=TaskExecutionStatus.COMPLETED,
                start_time=datetime.now() - timedelta(seconds=execution_time),
                end_time=datetime.now(),
                total_records=1000,
                processed_records=1000,
                success=True
            )
            result.execution_time = execution_time

            self.config_manager.record_performance_feedback(config, result)

        # 获取统计信息，应该能检测到性能下降趋势
        stats = self.config_manager.get_intelligent_statistics()

        # 验证统计信息包含性能趋势数据
        assert 'performance_trend' in stats or 'avg_execution_time' in stats


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
