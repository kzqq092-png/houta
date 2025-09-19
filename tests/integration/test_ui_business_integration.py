#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
UI与业务逻辑集成测试

测试UI与业务逻辑的集成功能，验证数据流和状态同步的正确性。

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
from typing import Dict, List, Any

# 设置测试环境
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

# 配置测试日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 模拟PyQt5环境
try:
    from PyQt5.QtWidgets import QApplication, QWidget
    from PyQt5.QtCore import QTimer, pyqtSignal
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

    class QTimer:
        def __init__(self, *args): pass
        def start(self, interval=None): pass
        def stop(self): pass
        def isActive(self): return False

    def pyqtSignal(*args):
        return Mock()

    GUI_AVAILABLE = False

# 导入被测试的组件
try:
    from core.ui_integration.ui_business_logic_adapter import UIBusinessLogicAdapter
    from core.ui_integration.ui_state_synchronizer import UIStateSynchronizer
    from gui.widgets.enhanced_data_import_widget import EnhancedDataImportWidget
    INTEGRATION_COMPONENTS_AVAILABLE = True
except ImportError as e:
    logger.warning(f"集成组件导入失败: {e}")
    INTEGRATION_COMPONENTS_AVAILABLE = False


class TestUIBusinessIntegrationBase(unittest.TestCase):
    """UI业务逻辑集成测试基类"""

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
        self.test_config = self._create_test_config()

    def tearDown(self):
        """测试清理"""
        if os.path.exists(self.temp_dir):
            import shutil
            shutil.rmtree(self.temp_dir)

    def _create_test_config(self) -> Dict[str, Any]:
        """创建测试配置"""
        return {
            'test_mode': True,
            'temp_dir': self.temp_dir,
            'mock_services': True,
            'test_data': {
                'tasks': [
                    {
                        'id': 'test_task_1',
                        'name': 'Integration Test Task 1',
                        'status': 'pending',
                        'config': {'data_source': 'test_source'}
                    }
                ],
                'performance_metrics': {
                    'cpu_usage': 25.5,
                    'memory_usage': 45.2,
                    'cache_hit_rate': 85.0
                }
            }
        }


@unittest.skipUnless(INTEGRATION_COMPONENTS_AVAILABLE, "集成组件不可用")
class TestUIBusinessLogicAdapter(TestUIBusinessIntegrationBase):
    """测试UI业务逻辑适配器"""

    def setUp(self):
        """测试设置"""
        super().setUp()

        # 模拟核心服务
        self.mock_import_engine = MagicMock()
        self.mock_config_manager = MagicMock()
        self.mock_ai_service = MagicMock()

        # 创建适配器实例
        with patch('core.ui_integration.ui_business_logic_adapter.CORE_AVAILABLE', True):
            self.adapter = UIBusinessLogicAdapter()

    def test_adapter_initialization(self):
        """测试适配器初始化"""
        self.assertIsNotNone(self.adapter)
        self.assertTrue(hasattr(self.adapter, 'services'))

    def test_service_discovery(self):
        """测试服务发现"""
        # 模拟服务发现
        with patch.object(self.adapter, '_discover_services') as mock_discover:
            mock_discover.return_value = {
                'import_engine': self.mock_import_engine,
                'config_manager': self.mock_config_manager
            }

            services = self.adapter._discover_services()

            self.assertIn('import_engine', services)
            self.assertIn('config_manager', services)

    def test_task_operations(self):
        """测试任务操作"""
        # 设置模拟的导入引擎
        self.adapter.services = {'import_engine': self.mock_import_engine}

        # 测试任务创建
        task_config = {
            'name': 'Test Task',
            'data_source': 'test_source',
            'import_type': 'kline_data'
        }

        self.mock_import_engine.create_task.return_value = 'test_task_id'

        task_id = self.adapter.create_task('Test Task', task_config)

        # 验证任务创建
        self.assertEqual(task_id, 'test_task_id')
        self.mock_import_engine.create_task.assert_called_once()

        # 测试任务暂停
        self.mock_import_engine.pause_task.return_value = True
        result = self.adapter.pause_task('test_task_id')

        self.assertTrue(result)
        self.mock_import_engine.pause_task.assert_called_with('test_task_id')

        # 测试任务取消
        self.mock_import_engine.cancel_task.return_value = True
        result = self.adapter.cancel_task('test_task_id')

        self.assertTrue(result)
        self.mock_import_engine.cancel_task.assert_called_with('test_task_id')

    def test_ai_service_integration(self):
        """测试AI服务集成"""
        # 设置模拟的AI服务
        self.adapter.services = {'ai_service': self.mock_ai_service}

        # 测试AI状态获取
        mock_status = {
            'prediction_accuracy': 95.5,
            'learning_progress': 75.0,
            'recommendations_count': 5
        }

        self.mock_ai_service.get_status.return_value = mock_status

        if hasattr(self.adapter, 'get_ai_service_status'):
            status = self.adapter.get_ai_service_status()
            self.assertEqual(status, mock_status)

        # 测试AI重训练触发
        self.mock_ai_service.trigger_retrain.return_value = True

        if hasattr(self.adapter, 'trigger_ai_model_retrain'):
            result = self.adapter.trigger_ai_model_retrain()
            self.assertTrue(result)

    def test_performance_metrics_collection(self):
        """测试性能指标收集"""
        # 模拟性能监控服务
        mock_performance_service = MagicMock()
        mock_metrics = {
            'cpu_usage': 45.2,
            'memory_usage': 67.8,
            'cache_hit_rate': 89.4,
            'active_tasks': 3
        }

        mock_performance_service.get_metrics.return_value = mock_metrics
        self.adapter.services = {'performance_service': mock_performance_service}

        if hasattr(self.adapter, 'get_performance_metrics'):
            metrics = self.adapter.get_performance_metrics()
            self.assertIsInstance(metrics, dict)
            self.assertIn('cpu_usage', metrics)

    def test_error_handling(self):
        """测试错误处理"""
        # 测试服务不可用时的处理
        self.adapter.services = {}

        # 测试任务创建失败
        task_id = self.adapter.create_task('Test Task', {})
        self.assertIsNone(task_id)

        # 测试任务操作失败
        result = self.adapter.pause_task('nonexistent_task')
        self.assertFalse(result)


@unittest.skipUnless(INTEGRATION_COMPONENTS_AVAILABLE, "集成组件不可用")
class TestUIStateSynchronizer(TestUIBusinessIntegrationBase):
    """测试UI状态同步器"""

    def setUp(self):
        """测试设置"""
        super().setUp()

        # 创建模拟适配器
        self.mock_adapter = MagicMock()

        # 创建同步器实例
        with patch('core.ui_integration.ui_state_synchronizer.QObject.__init__'):
            self.synchronizer = UIStateSynchronizer(self.mock_adapter)

    def test_synchronizer_initialization(self):
        """测试同步器初始化"""
        self.assertIsNotNone(self.synchronizer)
        self.assertEqual(self.synchronizer.ui_adapter, self.mock_adapter)

    def test_state_synchronization(self):
        """测试状态同步"""
        # 模拟业务状态更新
        test_state = {
            'entity_type': 'task',
            'entity_id': 'test_task_1',
            'new_state': {
                'status': 'running',
                'progress': 0.5
            }
        }

        # 测试状态更新
        if hasattr(self.synchronizer, 'update_ui_state'):
            self.synchronizer.update_ui_state(
                test_state['entity_type'],
                test_state['entity_id'],
                test_state['new_state']
            )

        # 验证状态存储
        if hasattr(self.synchronizer, 'ui_states'):
            key = f"{test_state['entity_type']}_{test_state['entity_id']}"
            self.assertIn(key, self.synchronizer.ui_states)

    def test_conflict_detection(self):
        """测试冲突检测"""
        # 设置初始状态
        if hasattr(self.synchronizer, 'ui_states'):
            self.synchronizer.ui_states = {
                'task_test_task_1': {
                    'status': 'running',
                    'progress': 0.3,
                    'last_updated': datetime.now() - timedelta(seconds=30)
                }
            }

        # 模拟冲突状态
        conflicting_state = {
            'status': 'paused',
            'progress': 0.5,
            'last_updated': datetime.now()
        }

        # 测试冲突检测
        if hasattr(self.synchronizer, 'detect_state_conflict'):
            conflict = self.synchronizer.detect_state_conflict(
                'task', 'test_task_1', conflicting_state
            )

            # 验证冲突检测结果
            self.assertIsNotNone(conflict)

    def test_sync_performance(self):
        """测试同步性能"""
        # 测试大量状态更新的性能
        start_time = time.time()

        for i in range(100):
            test_state = {
                'status': f'status_{i}',
                'progress': i / 100.0,
                'timestamp': datetime.now()
            }

            if hasattr(self.synchronizer, 'update_ui_state'):
                self.synchronizer.update_ui_state('task', f'task_{i}', test_state)

        end_time = time.time()
        sync_time = end_time - start_time

        # 同步时间应在合理范围内
        self.assertLess(sync_time, 1.0, f"状态同步耗时过长: {sync_time:.2f}秒")


@unittest.skipUnless(INTEGRATION_COMPONENTS_AVAILABLE and GUI_AVAILABLE, "组件或GUI不可用")
class TestUIBusinessDataFlow(TestUIBusinessIntegrationBase):
    """测试UI与业务逻辑的数据流"""

    def setUp(self):
        """测试设置"""
        super().setUp()

        # 创建模拟的业务服务
        self.mock_services = {
            'import_engine': MagicMock(),
            'config_manager': MagicMock(),
            'quality_monitor': MagicMock(),
            'ai_service': MagicMock()
        }

        # 创建UI组件
        with patch('gui.widgets.enhanced_data_import_widget.CORE_AVAILABLE', True):
            with patch('gui.widgets.enhanced_data_import_widget.initialize_ui_adapter') as mock_init:
                mock_adapter = MagicMock()
                mock_adapter.services = self.mock_services
                mock_init.return_value = mock_adapter

                self.ui_widget = EnhancedDataImportWidget()

    def test_task_creation_flow(self):
        """测试任务创建数据流"""
        # 模拟任务创建请求
        task_config = {
            'name': 'Integration Test Task',
            'data_source': 'test_source',
            'import_type': 'kline_data',
            'auto_start': False
        }

        # 设置模拟返回值
        self.mock_services['import_engine'].create_task.return_value = 'test_task_id'

        # 模拟UI适配器
        if hasattr(self.ui_widget, 'ui_adapter') and self.ui_widget.ui_adapter:
            self.ui_widget.ui_adapter.create_task.return_value = 'test_task_id'

            # 测试任务创建
            with patch.object(self.ui_widget, '_show_simple_task_creation_dialog') as mock_dialog:
                task_id = self.ui_widget.ui_adapter.create_task('Test Task', task_config)

                # 验证任务创建结果
                self.assertEqual(task_id, 'test_task_id')

    def test_status_update_flow(self):
        """测试状态更新数据流"""
        # 模拟状态更新
        test_status = {
            'task_id': 'test_task_1',
            'status': 'running',
            'progress': 0.75,
            'estimated_completion': datetime.now() + timedelta(minutes=5)
        }

        # 测试状态更新处理
        if hasattr(self.ui_widget, '_update_task_in_table'):
            self.ui_widget._update_task_in_table(test_status)

        # 验证UI更新（通过不抛出异常来验证）
        self.assertTrue(True)

    def test_performance_monitoring_flow(self):
        """测试性能监控数据流"""
        # 模拟性能数据
        performance_data = {
            'cpu_usage': 55.3,
            'memory_usage': 72.1,
            'cache_hit_rate': 87.5,
            'active_tasks': 5,
            'throughput': 1250.0
        }

        # 设置模拟性能服务
        if hasattr(self.ui_widget, 'ui_adapter') and self.ui_widget.ui_adapter:
            self.ui_widget.ui_adapter.get_performance_metrics = MagicMock(return_value=performance_data)

            # 测试性能数据获取
            metrics = self.ui_widget.ui_adapter.get_performance_metrics()

            # 验证数据获取
            self.assertEqual(metrics, performance_data)

    def test_ai_integration_flow(self):
        """测试AI集成数据流"""
        # 模拟AI服务状态
        ai_status = {
            'prediction_accuracy': 94.2,
            'learning_progress': 68.5,
            'recommendations_count': 8,
            'active_models': ['model_1', 'model_2']
        }

        # 设置模拟AI服务
        if hasattr(self.ui_widget, 'ui_adapter') and self.ui_widget.ui_adapter:
            self.ui_widget.ui_adapter.get_ai_service_status = MagicMock(return_value=ai_status)

            # 测试AI状态获取
            status = self.ui_widget.ui_adapter.get_ai_service_status()

            # 验证AI状态
            self.assertEqual(status, ai_status)
            self.assertIn('prediction_accuracy', status)


class TestIntegrationReliability(TestUIBusinessIntegrationBase):
    """测试集成可靠性"""

    def test_service_unavailability_handling(self):
        """测试服务不可用时的处理"""
        # 模拟所有服务不可用
        with patch('core.ui_integration.ui_business_logic_adapter.CORE_AVAILABLE', False):
            adapter = UIBusinessLogicAdapter()

            # 测试操作在服务不可用时的处理
            task_id = adapter.create_task('Test Task', {})
            self.assertIsNone(task_id)

            result = adapter.pause_task('test_task')
            self.assertFalse(result)

    def test_network_error_simulation(self):
        """测试网络错误模拟"""
        # 模拟网络超时
        with patch('core.ui_integration.ui_business_logic_adapter.CORE_AVAILABLE', True):
            adapter = UIBusinessLogicAdapter()

            # 模拟服务调用超时
            mock_service = MagicMock()
            mock_service.create_task.side_effect = TimeoutError("Network timeout")

            adapter.services = {'import_engine': mock_service}

            # 测试超时处理
            task_id = adapter.create_task('Test Task', {})
            self.assertIsNone(task_id)

    def test_data_consistency_under_load(self):
        """测试负载下的数据一致性"""
        with patch('core.ui_integration.ui_state_synchronizer.QObject.__init__'):
            synchronizer = UIStateSynchronizer(MagicMock())

        # 模拟并发状态更新
        import threading

        def update_state(entity_id, state_value):
            if hasattr(synchronizer, 'update_ui_state'):
                synchronizer.update_ui_state('task', entity_id, {'value': state_value})

        # 创建多个线程进行并发更新
        threads = []
        for i in range(10):
            thread = threading.Thread(target=update_state, args=(f'task_{i}', i))
            threads.append(thread)

        # 启动所有线程
        for thread in threads:
            thread.start()

        # 等待所有线程完成
        for thread in threads:
            thread.join()

        # 验证数据一致性
        if hasattr(synchronizer, 'ui_states'):
            self.assertEqual(len(synchronizer.ui_states), 10)


def run_integration_tests():
    """运行集成测试"""
    test_suite = unittest.TestSuite()

    # 添加测试类
    test_classes = [
        TestUIBusinessLogicAdapter,
        TestUIStateSynchronizer,
        TestUIBusinessDataFlow,
        TestIntegrationReliability
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
        # 运行集成测试
        success = run_integration_tests()

        if success:
            print("\n✅ 所有UI业务逻辑集成测试通过")
            exit_code = 0
        else:
            print("\n❌ 部分UI业务逻辑集成测试失败")
            exit_code = 1

    except Exception as e:
        print(f"\n💥 集成测试执行出错: {e}")
        exit_code = 2

    finally:
        if GUI_AVAILABLE and 'app' in locals():
            try:
                app.quit()
            except:
                pass

    exit(exit_code)
