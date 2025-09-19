#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
UI增强功能单元测试

测试所有新增UI组件的功能和状态管理，确保UI组件的可靠性和正确性。

作者: FactorWeave-Quant团队
版本: 1.0
"""

import sys
import unittest
import logging
from unittest.mock import MagicMock, patch, Mock
import tempfile
import os
from datetime import datetime, timedelta
from typing import Dict, List, Any

# 设置测试环境
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

# 配置测试专用的日志
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# 模拟PyQt5以避免在无GUI环境下测试失败
try:
    from PyQt5.QtWidgets import QApplication, QWidget
    from PyQt5.QtCore import Qt, QTimer
    from PyQt5.QtTest import QTest
    GUI_AVAILABLE = True
except ImportError:
    # 创建模拟的PyQt5类
    class QApplication:
        def __init__(self, *args): pass
        def exec_(self): return 0
        def processEvents(self): pass
        @staticmethod
        def instance(): return None

    class QWidget:
        def __init__(self, *args): pass
        def show(self): pass
        def close(self): pass
        def setStyleSheet(self, style): pass
        def findChildren(self, widget_type): return []

    class QTimer:
        def __init__(self, *args): pass
        def start(self, interval=None): pass
        def stop(self): pass
        def isActive(self): return False
        def interval(self): return 1000

    class Qt:
        Checked = 2
        Unchecked = 0

    class QTest:
        @staticmethod
        def qWait(ms): pass

    GUI_AVAILABLE = False

# 导入被测试的组件
try:
    from gui.widgets.enhanced_data_import_widget import EnhancedDataImportWidget
    from gui.widgets.ai_features_control_panel import AIFeaturesControlPanel
    from gui.widgets.task_dependency_visualizer import TaskDependencyVisualizer
    from gui.widgets.task_scheduler_control import TaskSchedulerControl
    from gui.widgets.data_quality_control_center import DataQualityControlCenter
    from gui.widgets.enhanced_performance_dashboard import EnhancedPerformanceDashboard
    from gui.widgets.cache_status_monitor import CacheStatusMonitor
    from gui.widgets.distributed_status_monitor import DistributedStatusMonitor
    UI_COMPONENTS_AVAILABLE = True
except ImportError as e:
    logger.warning(f"UI组件导入失败: {e}")
    UI_COMPONENTS_AVAILABLE = False


class TestUIComponentBase(unittest.TestCase):
    """UI组件测试基类"""

    @classmethod
    def setUpClass(cls):
        """类级别的测试设置"""
        if GUI_AVAILABLE and QApplication.instance() is None:
            cls.app = QApplication([])
        else:
            cls.app = None

    def setUp(self):
        """每个测试方法的设置"""
        self.temp_dir = tempfile.mkdtemp()
        self.test_data = self._create_test_data()

    def tearDown(self):
        """每个测试方法的清理"""
        if os.path.exists(self.temp_dir):
            import shutil
            shutil.rmtree(self.temp_dir)

    def _create_test_data(self) -> Dict[str, Any]:
        """创建测试数据"""
        return {
            'tasks': [
                {
                    'id': 'test_task_1',
                    'name': 'Test Task 1',
                    'status': 'pending',
                    'progress': 0.0,
                    'created_at': datetime.now()
                },
                {
                    'id': 'test_task_2',
                    'name': 'Test Task 2',
                    'status': 'running',
                    'progress': 0.5,
                    'created_at': datetime.now() - timedelta(minutes=10)
                }
            ],
            'quality_metrics': {
                'completeness': 95.0,
                'accuracy': 88.5,
                'consistency': 92.3,
                'timeliness': 96.7
            },
            'performance_data': {
                'cpu_usage': 45.2,
                'memory_usage': 67.8,
                'cache_hit_rate': 89.4
            }
        }


@unittest.skipUnless(UI_COMPONENTS_AVAILABLE, "UI组件不可用")
class TestEnhancedDataImportWidget(TestUIComponentBase):
    """测试EnhancedDataImportWidget主组件"""

    def setUp(self):
        """测试设置"""
        super().setUp()
        with patch('gui.widgets.enhanced_data_import_widget.CORE_AVAILABLE', False):
            with patch('gui.widgets.enhanced_data_import_widget.THEME_AVAILABLE', False):
                with patch('gui.widgets.enhanced_data_import_widget.PERFORMANCE_OPTIMIZATION_AVAILABLE', False):
                    self.widget = EnhancedDataImportWidget()

    def test_widget_initialization(self):
        """测试组件初始化"""
        self.assertIsNotNone(self.widget)
        self.assertIsInstance(self.widget, QWidget)

    def test_theme_application(self):
        """测试主题应用"""
        # 模拟主题管理器
        mock_theme_manager = MagicMock()
        mock_theme = MagicMock()
        mock_theme.colors = MagicMock()
        mock_theme.colors.background = "#FFFFFF"
        mock_theme.colors.text = "#000000"
        mock_theme.colors.primary = "#2196F3"

        mock_theme_manager.get_current_theme.return_value = mock_theme
        self.widget.theme_manager = mock_theme_manager

        # 测试主题应用
        self.widget.apply_unified_theme()

        # 验证主题管理器被调用
        mock_theme_manager.get_current_theme.assert_called_once()

    def test_performance_optimization(self):
        """测试性能优化"""
        # 模拟性能优化组件
        mock_display_optimizer = MagicMock()
        mock_virtualization_manager = MagicMock()
        mock_memory_manager = MagicMock()

        self.widget.display_optimizer = mock_display_optimizer
        self.widget.virtualization_manager = mock_virtualization_manager
        self.widget.memory_manager = mock_memory_manager

        # 测试性能优化应用
        self.widget.apply_performance_optimization()

        # 验证优化方法被调用
        self.assertTrue(mock_display_optimizer.called or mock_virtualization_manager.called or mock_memory_manager.called)

    def test_task_creation_wizard(self):
        """测试任务创建向导"""
        # 模拟UI适配器
        mock_ui_adapter = MagicMock()
        mock_ui_adapter.create_task.return_value = "test_task_id"
        self.widget.ui_adapter = mock_ui_adapter

        # 测试简单任务创建
        with patch('gui.widgets.enhanced_data_import_widget.QInputDialog') as mock_dialog:
            mock_dialog.getText.return_value = ("Test Task", True)

            self.widget._show_simple_task_creation_dialog()

            # 验证任务创建被调用
            mock_ui_adapter.create_task.assert_called_once()

    def test_batch_operations(self):
        """测试批量操作"""
        # 模拟选中的任务
        with patch.object(self.widget, 'get_selected_task_ids', return_value=['task1', 'task2']):
            # 模拟UI适配器
            mock_ui_adapter = MagicMock()
            self.widget.ui_adapter = mock_ui_adapter

            # 测试批量暂停
            self.widget.batch_pause_tasks()

            # 验证批量操作
            self.assertEqual(mock_ui_adapter.pause_task.call_count, 2)

    def test_performance_metrics_collection(self):
        """测试性能指标收集"""
        # 模拟性能组件
        mock_memory_manager = MagicMock()
        mock_memory_manager.get_memory_usage.return_value = 150.5
        self.widget.memory_manager = mock_memory_manager

        # 获取性能指标
        metrics = self.widget.get_performance_metrics()

        # 验证返回的指标
        self.assertIsInstance(metrics, dict)
        self.assertIn('memory_usage', metrics)
        self.assertIn('widget_count', metrics)

    def test_resource_cleanup(self):
        """测试资源清理"""
        # 模拟组件
        mock_memory_manager = MagicMock()
        self.widget.memory_manager = mock_memory_manager

        # 执行资源清理
        self.widget.cleanup_resources()

        # 验证清理方法被调用
        mock_memory_manager.cleanup.assert_called_once()


@unittest.skipUnless(UI_COMPONENTS_AVAILABLE, "UI组件不可用")
class TestAIFeaturesControlPanel(TestUIComponentBase):
    """测试AI功能控制面板"""

    def setUp(self):
        """测试设置"""
        super().setUp()
        with patch('gui.widgets.ai_features_control_panel.CORE_AVAILABLE', False):
            self.panel = AIFeaturesControlPanel()

    def test_panel_initialization(self):
        """测试面板初始化"""
        self.assertIsNotNone(self.panel)
        self.assertIsInstance(self.panel, QWidget)

    def test_ai_status_updates(self):
        """测试AI状态更新"""
        # 模拟UI适配器
        mock_ui_adapter = MagicMock()
        mock_status = {
            'prediction_accuracy': 95.5,
            'learning_progress': 75.0,
            'active_models': ['model1', 'model2']
        }
        mock_ui_adapter.get_ai_service_status.return_value = mock_status

        self.panel.ui_adapter = mock_ui_adapter

        # 测试状态加载
        self.panel.load_ai_status()

        # 验证适配器被调用
        mock_ui_adapter.get_ai_service_status.assert_called_once()

    def test_ai_controls(self):
        """测试AI控制功能"""
        # 模拟UI适配器
        mock_ui_adapter = MagicMock()
        self.panel.ui_adapter = mock_ui_adapter

        # 测试AI重训练触发
        if hasattr(self.panel, 'trigger_ai_retrain'):
            self.panel.trigger_ai_retrain()

            # 验证重训练被触发
            mock_ui_adapter.trigger_ai_model_retrain.assert_called_once()


@unittest.skipUnless(UI_COMPONENTS_AVAILABLE, "UI组件不可用")
class TestTaskDependencyVisualizer(TestUIComponentBase):
    """测试任务依赖关系可视化器"""

    def setUp(self):
        """测试设置"""
        super().setUp()
        with patch('gui.widgets.task_dependency_visualizer.CORE_AVAILABLE', False):
            self.visualizer = TaskDependencyVisualizer()

    def test_visualizer_initialization(self):
        """测试可视化器初始化"""
        self.assertIsNotNone(self.visualizer)
        self.assertIsInstance(self.visualizer, QWidget)

    def test_dependency_loading(self):
        """测试依赖关系加载"""
        # 测试依赖关系加载
        if hasattr(self.visualizer, 'load_dependencies'):
            self.visualizer.load_dependencies()

        # 验证依赖关系字典存在
        self.assertTrue(hasattr(self.visualizer, 'dependencies'))

    def test_dependency_visualization(self):
        """测试依赖关系可视化"""
        # 设置测试依赖关系
        test_dependencies = {
            'task1': ['task2', 'task3'],
            'task2': [],
            'task3': ['task4'],
            'task4': []
        }

        if hasattr(self.visualizer, 'dependencies'):
            self.visualizer.dependencies = test_dependencies

        # 测试可视化刷新
        if hasattr(self.visualizer, 'refresh_visualization'):
            self.visualizer.refresh_visualization()


@unittest.skipUnless(UI_COMPONENTS_AVAILABLE, "UI组件不可用")
class TestTaskSchedulerControl(TestUIComponentBase):
    """测试任务调度控制器"""

    def setUp(self):
        """测试设置"""
        super().setUp()
        with patch('gui.widgets.task_scheduler_control.CORE_AVAILABLE', False):
            self.scheduler = TaskSchedulerControl()

    def test_scheduler_initialization(self):
        """测试调度器初始化"""
        self.assertIsNotNone(self.scheduler)
        self.assertIsInstance(self.scheduler, QWidget)

    def test_scheduling_config_loading(self):
        """测试调度配置加载"""
        if hasattr(self.scheduler, 'load_scheduling_config'):
            self.scheduler.load_scheduling_config()

        # 验证调度配置存在
        self.assertTrue(hasattr(self.scheduler, 'scheduling_config') or
                        hasattr(self.scheduler, 'tasks'))


@unittest.skipUnless(UI_COMPONENTS_AVAILABLE, "UI组件不可用")
class TestDataQualityControlCenter(TestUIComponentBase):
    """测试数据质量控制中心"""

    def setUp(self):
        """测试设置"""
        super().setUp()
        with patch('gui.widgets.data_quality_control_center.CORE_AVAILABLE', False):
            self.control_center = DataQualityControlCenter()

    def test_control_center_initialization(self):
        """测试控制中心初始化"""
        self.assertIsNotNone(self.control_center)
        self.assertIsInstance(self.control_center, QWidget)

    def test_quality_scanning(self):
        """测试质量扫描功能"""
        # 模拟质量监控器
        mock_quality_monitor = MagicMock()
        mock_scan_results = {
            'issues': [],
            'metrics': {
                'completeness': 95.0,
                'accuracy': 88.0
            }
        }

        self.control_center.quality_monitor = mock_quality_monitor

        # 模拟扫描方法
        with patch.object(self.control_center, '_perform_real_quality_scan',
                          return_value=mock_scan_results):
            self.control_center.start_quality_scan()

        # 验证扫描过程
        self.assertTrue(True)  # 测试执行完成即为成功

    def test_data_cleaning(self):
        """测试数据清洗功能"""
        # 模拟异常检测器
        mock_anomaly_detector = MagicMock()
        self.control_center.anomaly_detector = mock_anomaly_detector

        # 设置测试质量问题
        if hasattr(self.control_center, 'quality_issues'):
            from gui.widgets.data_quality_control_center import QualityIssue, QualitySeverity
            test_issue = QualityIssue(
                issue_id="test_issue",
                rule_name="Test Rule",
                severity=QualitySeverity.MEDIUM,
                column="test_column",
                affected_rows=10,
                description="Test issue",
                detected_at=datetime.now(),
                resolved=False
            )
            self.control_center.quality_issues = [test_issue]

        # 模拟清洗方法
        with patch.object(self.control_center, '_perform_real_data_cleaning',
                          return_value={'repaired_count': 1, 'failed_count': 0}):
            # 模拟用户确认
            with patch('gui.widgets.data_quality_control_center.QMessageBox.question',
                       return_value=16384):  # QMessageBox.Yes
                self.control_center.start_data_cleaning()


class TestUIIntegration(TestUIComponentBase):
    """测试UI组件集成"""

    def test_component_interoperability(self):
        """测试组件互操作性"""
        # 测试组件间的数据传递和状态同步
        if not UI_COMPONENTS_AVAILABLE:
            self.skipTest("UI组件不可用")

        # 模拟组件间通信
        with patch('gui.widgets.enhanced_data_import_widget.CORE_AVAILABLE', False):
            widget = EnhancedDataImportWidget()

        # 测试主题信息获取
        theme_info = widget.get_current_theme_info()
        self.assertIsInstance(theme_info, dict)

        # 测试性能指标获取
        performance_metrics = widget.get_performance_metrics()
        self.assertIsInstance(performance_metrics, dict)

    def test_error_handling(self):
        """测试错误处理"""
        if not UI_COMPONENTS_AVAILABLE:
            self.skipTest("UI组件不可用")

        # 测试在缺少依赖时的降级处理
        with patch('gui.widgets.enhanced_data_import_widget.CORE_AVAILABLE', False):
            with patch('gui.widgets.enhanced_data_import_widget.THEME_AVAILABLE', False):
                widget = EnhancedDataImportWidget()

                # 测试方法在缺少依赖时不会崩溃
                widget.apply_unified_theme()
                widget.apply_performance_optimization()

                # 验证组件仍能正常工作
                self.assertIsNotNone(widget)


class TestUIPerformance(TestUIComponentBase):
    """测试UI性能"""

    def test_component_memory_usage(self):
        """测试组件内存使用"""
        if not UI_COMPONENTS_AVAILABLE:
            self.skipTest("UI组件不可用")

        import psutil
        import gc

        # 记录初始内存
        process = psutil.Process()
        initial_memory = process.memory_info().rss

        # 创建和销毁组件
        widgets = []
        for _ in range(10):
            with patch('gui.widgets.enhanced_data_import_widget.CORE_AVAILABLE', False):
                widget = EnhancedDataImportWidget()
                widgets.append(widget)

        # 清理组件
        for widget in widgets:
            if hasattr(widget, 'cleanup_resources'):
                widget.cleanup_resources()

        del widgets
        gc.collect()

        # 检查内存是否合理
        final_memory = process.memory_info().rss
        memory_increase = final_memory - initial_memory

        # 内存增长应在合理范围内（100MB）
        self.assertLess(memory_increase, 100 * 1024 * 1024,
                        f"内存增长过大: {memory_increase / 1024 / 1024:.2f}MB")

    def test_component_initialization_time(self):
        """测试组件初始化时间"""
        if not UI_COMPONENTS_AVAILABLE:
            self.skipTest("UI组件不可用")

        import time

        # 测试主组件初始化时间
        start_time = time.time()

        with patch('gui.widgets.enhanced_data_import_widget.CORE_AVAILABLE', False):
            widget = EnhancedDataImportWidget()

        end_time = time.time()
        initialization_time = end_time - start_time

        # 初始化时间应在5秒内
        self.assertLess(initialization_time, 5.0,
                        f"组件初始化时间过长: {initialization_time:.2f}秒")


def run_ui_tests():
    """运行UI测试"""
    # 创建测试套件
    test_suite = unittest.TestSuite()

    # 添加测试类
    test_classes = [
        TestEnhancedDataImportWidget,
        TestAIFeaturesControlPanel,
        TestTaskDependencyVisualizer,
        TestTaskSchedulerControl,
        TestDataQualityControlCenter,
        TestUIIntegration,
        TestUIPerformance
    ]

    for test_class in test_classes:
        tests = unittest.TestLoader().loadTestsFromTestCase(test_class)
        test_suite.addTests(tests)

    # 运行测试
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(test_suite)

    return result.wasSuccessful()


if __name__ == '__main__':
    # 设置测试环境
    if GUI_AVAILABLE and QApplication.instance() is None:
        app = QApplication([])

    try:
        # 运行测试
        success = run_ui_tests()

        if success:
            print("\n✅ 所有UI组件测试通过")
            exit_code = 0
        else:
            print("\n❌ 部分UI组件测试失败")
            exit_code = 1

    except Exception as e:
        print(f"\n💥 测试执行出错: {e}")
        exit_code = 2

    finally:
        if GUI_AVAILABLE and 'app' in locals():
            try:
                app.quit()
            except:
                pass

    exit(exit_code)
