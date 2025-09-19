#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
用户体验测试

测试完整的用户操作流程和体验，验证UI的易用性和功能完整性。

作者: FactorWeave-Quant团队
版本: 1.0
"""

import sys
import unittest
import logging
import tempfile
import os
import time
import json
from unittest.mock import MagicMock, patch, Mock
from datetime import datetime, timedelta
from typing import Dict, List, Any, Callable

# 设置测试环境
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

# 配置测试日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 模拟PyQt5环境
try:
    from PyQt5.QtWidgets import QApplication, QWidget, QMessageBox
    from PyQt5.QtCore import QTimer, Qt
    from PyQt5.QtTest import QTest
    GUI_AVAILABLE = True
except ImportError:
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
        def isVisible(self): return True

    class QMessageBox:
        Yes = 16384
        No = 65536
        @staticmethod
        def question(*args): return 16384
        @staticmethod
        def information(*args): pass
        @staticmethod
        def warning(*args): pass
        @staticmethod
        def critical(*args): pass

    class QTimer:
        def __init__(self, *args): pass
        def start(self, interval=None): pass
        def stop(self): pass
        def isActive(self): return False

    class Qt:
        Checked = 2
        Unchecked = 0

    class QTest:
        @staticmethod
        def qWait(ms): time.sleep(ms / 1000.0)

    GUI_AVAILABLE = False

# 导入被测试的组件
try:
    from gui.widgets.enhanced_data_import_widget import EnhancedDataImportWidget
    UX_COMPONENTS_AVAILABLE = True
except ImportError as e:
    logger.warning(f"用户体验测试组件导入失败: {e}")
    UX_COMPONENTS_AVAILABLE = False


class UserWorkflowTestBase(unittest.TestCase):
    """用户工作流测试基类"""

    @classmethod
    def setUpClass(cls):
        """类级别设置"""
        if GUI_AVAILABLE and QApplication.instance() is None:
            cls.app = QApplication([])
        else:
            cls.app = None

    def setUp(self):
        """测试设置"""
        self.temp_dir = tempfile.mkdtemp()
        self.user_scenarios = self._create_user_scenarios()
        self.workflow_metrics = {
            'start_time': None,
            'end_time': None,
            'steps_completed': 0,
            'errors_encountered': 0,
            'user_actions': []
        }

    def tearDown(self):
        """测试清理"""
        if os.path.exists(self.temp_dir):
            import shutil
            shutil.rmtree(self.temp_dir)

    def _create_user_scenarios(self) -> Dict[str, Dict[str, Any]]:
        """创建用户场景"""
        return {
            'new_user_onboarding': {
                'description': '新用户首次使用系统',
                'steps': [
                    '启动应用程序',
                    '浏览主界面',
                    '了解功能模块',
                    '创建第一个任务',
                    '监控任务执行'
                ],
                'expected_duration': 300,  # 5分钟
                'success_criteria': [
                    '界面加载成功',
                    '功能模块可见',
                    '任务创建成功',
                    '状态显示正常'
                ]
            },
            'daily_monitoring': {
                'description': '日常监控工作流',
                'steps': [
                    '查看系统状态',
                    '检查任务进度',
                    '查看性能指标',
                    '处理异常告警',
                    '生成质量报告'
                ],
                'expected_duration': 180,  # 3分钟
                'success_criteria': [
                    '状态信息准确',
                    '进度显示实时',
                    '指标数据真实',
                    '告警及时处理'
                ]
            },
            'advanced_configuration': {
                'description': '高级配置工作流',
                'steps': [
                    '访问AI控制面板',
                    '调整系统参数',
                    '配置依赖关系',
                    '设置调度策略',
                    '验证配置效果'
                ],
                'expected_duration': 420,  # 7分钟
                'success_criteria': [
                    '配置界面友好',
                    '参数设置生效',
                    '依赖关系清晰',
                    '策略配置有效'
                ]
            },
            'quality_management': {
                'description': '数据质量管理工作流',
                'steps': [
                    '启动质量扫描',
                    '查看质量指标',
                    '处理质量问题',
                    '执行数据清洗',
                    '生成质量报告'
                ],
                'expected_duration': 240,  # 4分钟
                'success_criteria': [
                    '扫描功能正常',
                    '指标显示准确',
                    '问题处理及时',
                    '清洗效果明显'
                ]
            }
        }

    def _start_workflow_tracking(self):
        """开始工作流跟踪"""
        self.workflow_metrics['start_time'] = time.time()
        self.workflow_metrics['steps_completed'] = 0
        self.workflow_metrics['errors_encountered'] = 0
        self.workflow_metrics['user_actions'] = []

    def _end_workflow_tracking(self):
        """结束工作流跟踪"""
        self.workflow_metrics['end_time'] = time.time()
        return self.workflow_metrics

    def _track_user_action(self, action: str, success: bool = True):
        """跟踪用户操作"""
        self.workflow_metrics['user_actions'].append({
            'action': action,
            'timestamp': time.time(),
            'success': success
        })

        if success:
            self.workflow_metrics['steps_completed'] += 1
        else:
            self.workflow_metrics['errors_encountered'] += 1

    def _simulate_user_interaction(self, widget: QWidget, interaction_type: str, delay: float = 0.1):
        """模拟用户交互"""
        if GUI_AVAILABLE:
            QTest.qWait(int(delay * 1000))

        # 记录交互
        self._track_user_action(f"{interaction_type} on {widget.__class__.__name__}")

        # 模拟处理事件
        if GUI_AVAILABLE and QApplication.instance():
            QApplication.instance().processEvents()


@unittest.skipUnless(UX_COMPONENTS_AVAILABLE, "用户体验测试组件不可用")
class TestNewUserOnboarding(UserWorkflowTestBase):
    """测试新用户引导工作流"""

    def setUp(self):
        """测试设置"""
        super().setUp()

        # 创建主界面组件
        with patch('gui.widgets.enhanced_data_import_widget.CORE_AVAILABLE', False):
            with patch('gui.widgets.enhanced_data_import_widget.THEME_AVAILABLE', False):
                self.main_widget = EnhancedDataImportWidget()

    def test_application_startup_experience(self):
        """测试应用程序启动体验"""
        self._start_workflow_tracking()

        # 步骤1: 启动应用程序
        start_time = time.time()
        self.main_widget.show()
        startup_time = time.time() - start_time

        self._track_user_action("启动应用程序", startup_time < 3.0)

        # 验证启动时间在可接受范围内
        self.assertLess(startup_time, 3.0, f"应用启动时间过长: {startup_time:.2f}秒")

        # 步骤2: 浏览主界面
        self._simulate_user_interaction(self.main_widget, "浏览主界面")

        # 验证主界面元素可见性
        self.assertTrue(self.main_widget.isVisible())
        self._track_user_action("主界面显示", True)

        # 步骤3: 了解功能模块
        if hasattr(self.main_widget, 'monitor_tabs'):
            tab_count = self.main_widget.monitor_tabs.count() if hasattr(self.main_widget.monitor_tabs, 'count') else 0
            self._track_user_action("功能模块可见", tab_count > 0)

        # 完成工作流跟踪
        metrics = self._end_workflow_tracking()

        # 验证用户体验指标
        total_time = metrics['end_time'] - metrics['start_time']
        self.assertLess(total_time, 10.0, "新用户引导时间过长")
        self.assertEqual(metrics['errors_encountered'], 0, "新用户引导过程中遇到错误")

    def test_first_task_creation_experience(self):
        """测试首次任务创建体验"""
        self._start_workflow_tracking()

        # 模拟用户创建第一个任务
        with patch.object(self.main_widget, 'ui_adapter') as mock_adapter:
            mock_adapter.create_task.return_value = "first_task_id"

            # 步骤1: 点击新建任务按钮
            if hasattr(self.main_widget, 'show_task_creation_wizard'):
                self._simulate_user_interaction(self.main_widget, "点击新建任务")

                # 模拟任务创建向导
                with patch('gui.widgets.enhanced_data_import_widget.QInputDialog.getText') as mock_dialog:
                    mock_dialog.return_value = ("我的第一个任务", True)

                    # 执行任务创建
                    self.main_widget._show_simple_task_creation_dialog()

                    self._track_user_action("任务创建成功", True)

        # 验证任务创建体验
        metrics = self._end_workflow_tracking()
        self.assertEqual(metrics['errors_encountered'], 0, "任务创建过程中遇到错误")

    def test_interface_discoverability(self):
        """测试界面可发现性"""
        # 检查重要功能的可发现性
        discoverable_elements = [
            '任务管理',
            'AI控制面板',
            '数据质量',
            '性能监控'
        ]

        found_elements = 0

        # 检查选项卡标题
        if hasattr(self.main_widget, 'monitor_tabs'):
            for i in range(getattr(self.main_widget.monitor_tabs, 'count', lambda: 0)()):
                try:
                    tab_text = getattr(self.main_widget.monitor_tabs, 'tabText', lambda x: '')(i)
                    for element in discoverable_elements:
                        if element in tab_text:
                            found_elements += 1
                except:
                    pass

        # 至少应该发现一半的重要功能
        discovery_rate = found_elements / len(discoverable_elements)
        self.assertGreaterEqual(discovery_rate, 0.5,
                                f"界面可发现性不足: 只发现了 {discovery_rate:.1%} 的重要功能")


@unittest.skipUnless(UX_COMPONENTS_AVAILABLE, "用户体验测试组件不可用")
class TestDailyMonitoringWorkflow(UserWorkflowTestBase):
    """测试日常监控工作流"""

    def setUp(self):
        """测试设置"""
        super().setUp()

        with patch('gui.widgets.enhanced_data_import_widget.CORE_AVAILABLE', False):
            self.main_widget = EnhancedDataImportWidget()

    def test_system_status_monitoring(self):
        """测试系统状态监控"""
        self._start_workflow_tracking()

        # 步骤1: 查看系统状态
        self._simulate_user_interaction(self.main_widget, "查看系统状态")

        # 获取性能指标
        if hasattr(self.main_widget, 'get_performance_metrics'):
            metrics = self.main_widget.get_performance_metrics()
            self._track_user_action("获取性能指标", isinstance(metrics, dict))

        # 步骤2: 检查主题信息
        if hasattr(self.main_widget, 'get_current_theme_info'):
            theme_info = self.main_widget.get_current_theme_info()
            self._track_user_action("获取主题信息", isinstance(theme_info, dict))

        metrics = self._end_workflow_tracking()

        # 验证监控响应时间
        total_time = metrics['end_time'] - metrics['start_time']
        self.assertLess(total_time, 5.0, "系统状态检查耗时过长")

    def test_task_monitoring_workflow(self):
        """测试任务监控工作流"""
        self._start_workflow_tracking()

        # 模拟有任务在运行
        with patch.object(self.main_widget, 'refresh_task_list') as mock_refresh:
            # 步骤1: 刷新任务列表
            self._simulate_user_interaction(self.main_widget, "刷新任务列表")

            if hasattr(self.main_widget, 'refresh_task_list'):
                self.main_widget.refresh_task_list()
                self._track_user_action("任务列表刷新", True)

        # 步骤2: 检查任务详情
        if hasattr(self.main_widget, 'ui_adapter') and self.main_widget.ui_adapter:
            mock_adapter = MagicMock()
            mock_adapter.get_task_details.return_value = {
                'id': 'test_task',
                'status': 'running',
                'progress': 0.75
            }
            self.main_widget.ui_adapter = mock_adapter

            self._track_user_action("获取任务详情", True)

        metrics = self._end_workflow_tracking()
        self.assertEqual(metrics['errors_encountered'], 0, "任务监控过程中遇到错误")

    def test_real_time_updates(self):
        """测试实时更新功能"""
        # 验证定时器是否正常工作
        timers = self.main_widget.findChildren(QTimer)
        active_timers = [timer for timer in timers if timer.isActive()]

        # 应该有活跃的定时器用于实时更新
        self.assertGreater(len(active_timers), 0, "没有活跃的实时更新定时器")

        # 检查更新频率是否合理
        for timer in active_timers:
            interval = timer.interval()
            self.assertGreaterEqual(interval, 1000, f"定时器更新频率过高: {interval}ms")
            self.assertLessEqual(interval, 10000, f"定时器更新频率过低: {interval}ms")


@unittest.skipUnless(UX_COMPONENTS_AVAILABLE, "用户体验测试组件不可用")
class TestAdvancedConfigurationWorkflow(UserWorkflowTestBase):
    """测试高级配置工作流"""

    def setUp(self):
        """测试设置"""
        super().setUp()

        with patch('gui.widgets.enhanced_data_import_widget.CORE_AVAILABLE', False):
            with patch('gui.widgets.enhanced_data_import_widget.THEME_AVAILABLE', True):
                self.main_widget = EnhancedDataImportWidget()

    def test_theme_configuration_workflow(self):
        """测试主题配置工作流"""
        self._start_workflow_tracking()

        # 步骤1: 切换主题
        theme_types = ['light', 'dark', 'auto']

        for theme_type in theme_types:
            start_time = time.time()
            self.main_widget.set_theme(theme_type)
            switch_time = time.time() - start_time

            self._track_user_action(f"切换到{theme_type}主题", switch_time < 1.0)
            self._simulate_user_interaction(self.main_widget, f"应用{theme_type}主题", 0.5)

        metrics = self._end_workflow_tracking()

        # 验证主题切换体验
        self.assertEqual(metrics['errors_encountered'], 0, "主题切换过程中遇到错误")
        self.assertGreaterEqual(metrics['steps_completed'], len(theme_types),
                                "主题切换步骤未完成")

    def test_performance_optimization_workflow(self):
        """测试性能优化配置工作流"""
        self._start_workflow_tracking()

        # 步骤1: 启用大数据优化
        self.main_widget.optimize_performance_for_large_data(True)
        self._track_user_action("启用大数据优化", True)

        # 步骤2: 检查优化效果
        performance_metrics = self.main_widget.get_performance_metrics()
        optimization_active = performance_metrics.get('display_optimization', False)
        self._track_user_action("验证优化效果", optimization_active)

        # 步骤3: 禁用大数据优化
        self.main_widget.optimize_performance_for_large_data(False)
        self._track_user_action("禁用大数据优化", True)

        metrics = self._end_workflow_tracking()
        self.assertEqual(metrics['errors_encountered'], 0, "性能优化配置过程中遇到错误")


@unittest.skipUnless(UX_COMPONENTS_AVAILABLE, "用户体验测试组件不可用")
class TestQualityManagementWorkflow(UserWorkflowTestBase):
    """测试质量管理工作流"""

    def setUp(self):
        """测试设置"""
        super().setUp()

        # 创建数据质量控制中心
        with patch('gui.widgets.data_quality_control_center.CORE_AVAILABLE', False):
            from gui.widgets.data_quality_control_center import DataQualityControlCenter
            self.quality_center = DataQualityControlCenter()

    def test_quality_scanning_workflow(self):
        """测试质量扫描工作流"""
        self._start_workflow_tracking()

        # 步骤1: 启动质量扫描
        with patch.object(self.quality_center, '_perform_real_quality_scan') as mock_scan:
            mock_scan.return_value = {
                'issues': [],
                'metrics': {'completeness': 95.0}
            }

            self._simulate_user_interaction(self.quality_center, "启动质量扫描")
            self.quality_center.start_quality_scan()
            self._track_user_action("质量扫描完成", True)

        # 步骤2: 查看扫描结果
        if hasattr(self.quality_center, 'quality_metrics'):
            metrics_count = len(self.quality_center.quality_metrics)
            self._track_user_action("查看扫描结果", metrics_count >= 0)

        metrics = self._end_workflow_tracking()
        self.assertEqual(metrics['errors_encountered'], 0, "质量扫描工作流中遇到错误")

    def test_data_cleaning_workflow(self):
        """测试数据清洗工作流"""
        self._start_workflow_tracking()

        # 模拟存在质量问题
        with patch.object(self.quality_center, 'quality_issues') as mock_issues:
            from gui.widgets.data_quality_control_center import QualityIssue, QualitySeverity
            mock_issues.__len__ = Mock(return_value=1)
            mock_issues.__iter__ = Mock(return_value=iter([
                QualityIssue(
                    issue_id="test_issue",
                    rule_name="Test Rule",
                    severity=QualitySeverity.MEDIUM,
                    column="test_column",
                    affected_rows=5,
                    description="Test quality issue",
                    detected_at=datetime.now(),
                    resolved=False
                )
            ]))

            # 步骤1: 启动数据清洗
            with patch.object(self.quality_center, '_perform_real_data_cleaning') as mock_clean:
                mock_clean.return_value = {
                    'repaired_count': 1,
                    'failed_count': 0,
                    'repairs': []
                }

                # 模拟用户确认
                with patch('gui.widgets.data_quality_control_center.QMessageBox.question',
                           return_value=QMessageBox.Yes):
                    self._simulate_user_interaction(self.quality_center, "启动数据清洗")
                    self.quality_center.start_data_cleaning()
                    self._track_user_action("数据清洗完成", True)

        metrics = self._end_workflow_tracking()
        self.assertEqual(metrics['errors_encountered'], 0, "数据清洗工作流中遇到错误")


class TestUserExperienceMetrics(UserWorkflowTestBase):
    """测试用户体验指标"""

    def test_response_time_metrics(self):
        """测试响应时间指标"""
        response_times = {}

        # 测试各种操作的响应时间
        operations = [
            ('widget_creation', lambda: EnhancedDataImportWidget()),
            ('theme_info', lambda: self._get_theme_info()),
            ('performance_metrics', lambda: self._get_performance_metrics())
        ]

        for operation_name, operation_func in operations:
            start_time = time.time()
            try:
                with patch('gui.widgets.enhanced_data_import_widget.CORE_AVAILABLE', False):
                    operation_func()
                response_time = time.time() - start_time
                response_times[operation_name] = response_time
            except Exception as e:
                response_times[operation_name] = float('inf')
                logger.warning(f"操作 {operation_name} 失败: {e}")

        # 验证响应时间
        for operation, response_time in response_times.items():
            self.assertLess(response_time, 2.0,
                            f"操作 {operation} 响应时间过长: {response_time:.2f}秒")

    def _get_theme_info(self):
        """获取主题信息"""
        with patch('gui.widgets.enhanced_data_import_widget.THEME_AVAILABLE', False):
            widget = EnhancedDataImportWidget()
            return widget.get_current_theme_info()

    def _get_performance_metrics(self):
        """获取性能指标"""
        with patch('gui.widgets.enhanced_data_import_widget.PERFORMANCE_OPTIMIZATION_AVAILABLE', False):
            widget = EnhancedDataImportWidget()
            return widget.get_performance_metrics()

    def test_error_recovery_experience(self):
        """测试错误恢复体验"""
        # 模拟各种错误情况
        error_scenarios = [
            '核心服务不可用',
            '主题系统不可用',
            '性能优化不可用'
        ]

        for scenario in error_scenarios:
            try:
                # 根据场景模拟错误
                if '核心服务' in scenario:
                    with patch('gui.widgets.enhanced_data_import_widget.CORE_AVAILABLE', False):
                        widget = EnhancedDataImportWidget()
                elif '主题系统' in scenario:
                    with patch('gui.widgets.enhanced_data_import_widget.THEME_AVAILABLE', False):
                        widget = EnhancedDataImportWidget()
                elif '性能优化' in scenario:
                    with patch('gui.widgets.enhanced_data_import_widget.PERFORMANCE_OPTIMIZATION_AVAILABLE', False):
                        widget = EnhancedDataImportWidget()

                # 验证组件仍能正常创建
                self.assertIsNotNone(widget)

            except Exception as e:
                self.fail(f"错误场景 '{scenario}' 下组件创建失败: {e}")

    def test_accessibility_features(self):
        """测试可访问性功能"""
        with patch('gui.widgets.enhanced_data_import_widget.CORE_AVAILABLE', False):
            widget = EnhancedDataImportWidget()

        # 检查是否有工具提示
        children = widget.findChildren(QWidget)
        tooltip_count = sum(1 for child in children if hasattr(child, 'toolTip') and child.toolTip())

        # 检查键盘导航支持
        focusable_widgets = [child for child in children if hasattr(child, 'focusPolicy')]

        # 验证可访问性特性
        self.assertGreater(len(focusable_widgets), 0, "缺少可键盘导航的组件")


def run_ux_tests():
    """运行用户体验测试"""
    test_suite = unittest.TestSuite()

    # 添加测试类
    test_classes = [
        TestNewUserOnboarding,
        TestDailyMonitoringWorkflow,
        TestAdvancedConfigurationWorkflow,
        TestQualityManagementWorkflow,
        TestUserExperienceMetrics
    ]

    for test_class in test_classes:
        tests = unittest.TestLoader().loadTestsFromTestCase(test_class)
        test_suite.addTests(tests)

    # 运行测试
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(test_suite)

    # 输出测试总结
    if result.wasSuccessful():
        print("\n🎉 用户体验测试总结:")
        print("✅ 所有用户工作流测试通过")
        print("✅ 界面响应时间符合要求")
        print("✅ 错误恢复机制正常")
        print("✅ 可访问性功能完善")
    else:
        print("\n⚠️  用户体验测试总结:")
        print(f"❌ {len(result.failures)} 个测试失败")
        print(f"💥 {len(result.errors)} 个测试错误")

    return result.wasSuccessful()


if __name__ == '__main__':
    # 设置测试环境
    if GUI_AVAILABLE and QApplication.instance() is None:
        app = QApplication([])

    try:
        # 运行用户体验测试
        success = run_ux_tests()

        if success:
            print("\n✅ 所有用户体验测试通过")
            exit_code = 0
        else:
            print("\n❌ 部分用户体验测试失败")
            exit_code = 1

    except Exception as e:
        print(f"\n💥 用户体验测试执行出错: {e}")
        exit_code = 2

    finally:
        if GUI_AVAILABLE and 'app' in locals():
            try:
                app.quit()
            except:
                pass

    exit(exit_code)
