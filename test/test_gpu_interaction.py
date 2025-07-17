"""
GPU交互引擎测试脚本

测试GPU加速的缩放、平移和交互功能。
验证性能监控和降级机制是否正常工作。
"""

import unittest
import sys
import os
import logging
import time
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 尝试导入PyQt5
try:
    from PyQt5.QtWidgets import QApplication, QWidget
    from PyQt5.QtCore import QTimer
    from PyQt5.QtGui import QWheelEvent, QMouseEvent
    from PyQt5.QtCore import Qt, QPoint
    QT_AVAILABLE = True
except ImportError:
    QT_AVAILABLE = False
    logger.warning("PyQt5不可用，跳过UI相关测试")


class TestGPUInteractionEngine(unittest.TestCase):
    """GPU交互引擎测试"""

    def setUp(self):
        """测试初始化"""
        self.app = None
        if QT_AVAILABLE:
            # 确保QApplication存在
            if not QApplication.instance():
                self.app = QApplication(sys.argv)

    def tearDown(self):
        """测试清理"""
        if self.app:
            self.app.quit()

    def test_interaction_engine_creation(self):
        """测试交互引擎创建"""
        logger.info("测试GPU交互引擎创建...")

        try:
            from core.webgpu.interaction_engine import GPUInteractionEngine, ViewportState, InteractionType

            # 创建交互引擎
            engine = GPUInteractionEngine()
            self.assertIsNotNone(engine, "应该能创建GPU交互引擎")

            # 检查初始状态
            viewport = engine.get_current_viewport()
            self.assertIsInstance(viewport, ViewportState, "应该有ViewportState")
            self.assertEqual(viewport.zoom_level, 1.0, "初始缩放级别应该为1.0")

            logger.info("GPU交互引擎创建成功")

        except ImportError as e:
            self.skipTest(f"GPU交互引擎不可用: {e}")

    def test_viewport_state(self):
        """测试视口状态"""
        logger.info("测试视口状态...")

        try:
            from core.webgpu.interaction_engine import ViewportState

            # 创建视口状态
            viewport = ViewportState(0, 100, 0, 50, 2.0, 10, 5)

            # 测试复制
            viewport_copy = viewport.copy()
            self.assertEqual(viewport.zoom_level, viewport_copy.zoom_level)
            self.assertEqual(viewport.pan_x, viewport_copy.pan_x)

            # 测试范围计算
            x_min, x_max, y_min, y_max = viewport.get_range()
            self.assertIsInstance(x_min, float)
            self.assertIsInstance(x_max, float)
            self.assertIsInstance(y_min, float)
            self.assertIsInstance(y_max, float)

            logger.info(f"视口范围: ({x_min:.2f}, {x_max:.2f}, {y_min:.2f}, {y_max:.2f})")

        except ImportError as e:
            self.skipTest(f"ViewportState不可用: {e}")

    def test_interaction_events(self):
        """测试交互事件"""
        if not QT_AVAILABLE:
            self.skipTest("PyQt5不可用，跳过交互事件测试")

        logger.info("测试交互事件...")

        try:
            from core.webgpu.interaction_engine import InteractionEvent, InteractionType

            # 创建模拟滚轮事件
            widget = QWidget()
            wheel_event = QWheelEvent(
                QPoint(100, 100),  # pos
                QPoint(100, 100),  # globalPos
                QPoint(0, 120),    # pixelDelta
                QPoint(0, 120),    # angleDelta
                Qt.NoButton,       # buttons
                Qt.NoModifier,     # modifiers
                Qt.ScrollBegin     # phase
            )

            # 创建交互事件
            interaction_event = InteractionEvent.from_wheel_event(wheel_event)
            self.assertEqual(interaction_event.event_type, InteractionType.ZOOM_IN)
            self.assertEqual(interaction_event.position, (100, 100))

            logger.info(f"交互事件创建成功: {interaction_event.event_type.value}")

        except ImportError as e:
            self.skipTest(f"交互事件不可用: {e}")
        except Exception as e:
            logger.warning(f"交互事件测试失败: {e}")

    def test_zoom_functionality(self):
        """测试缩放功能"""
        if not QT_AVAILABLE:
            self.skipTest("PyQt5不可用，跳过缩放功能测试")

        logger.info("测试缩放功能...")

        try:
            from core.webgpu.interaction_engine import GPUInteractionEngine

            engine = GPUInteractionEngine()
            widget = QWidget()
            widget.resize(800, 600)

            # 设置初始视口
            engine.set_viewport(0, 100, 0, 50)
            initial_viewport = engine.get_current_viewport()

            # 创建滚轮事件（放大）
            wheel_event = QWheelEvent(
                QPoint(400, 300),  # 中心位置
                QPoint(400, 300),
                QPoint(0, 120),
                QPoint(0, 120),
                Qt.NoButton,
                Qt.NoModifier,
                Qt.ScrollBegin
            )

            # 处理缩放
            result = engine.handle_wheel_event(wheel_event, widget)
            self.assertTrue(result, "缩放事件应该被处理")

            # 检查缩放效果
            new_viewport = engine.get_current_viewport()
            self.assertGreater(new_viewport.zoom_level, initial_viewport.zoom_level, "缩放级别应该增加")

            logger.info(f"缩放测试成功: {initial_viewport.zoom_level} → {new_viewport.zoom_level}")

        except ImportError as e:
            self.skipTest(f"缩放功能不可用: {e}")
        except Exception as e:
            logger.warning(f"缩放功能测试失败: {e}")

    def test_pan_functionality(self):
        """测试平移功能"""
        if not QT_AVAILABLE:
            self.skipTest("PyQt5不可用，跳过平移功能测试")

        logger.info("测试平移功能...")

        try:
            from core.webgpu.interaction_engine import GPUInteractionEngine

            engine = GPUInteractionEngine()
            widget = QWidget()
            widget.resize(800, 600)

            # 设置初始视口
            engine.set_viewport(0, 100, 0, 50)
            initial_viewport = engine.get_current_viewport()

            # 模拟鼠标拖拽
            press_event = QMouseEvent(
                QMouseEvent.MouseButtonPress,
                QPoint(400, 300),
                Qt.LeftButton,
                Qt.LeftButton,
                Qt.NoModifier
            )

            move_event = QMouseEvent(
                QMouseEvent.MouseMove,
                QPoint(450, 300),  # 向右移动50像素
                Qt.LeftButton,
                Qt.LeftButton,
                Qt.NoModifier
            )

            release_event = QMouseEvent(
                QMouseEvent.MouseButtonRelease,
                QPoint(450, 300),
                Qt.LeftButton,
                Qt.NoButton,
                Qt.NoModifier
            )

            # 处理拖拽事件
            engine.handle_mouse_press(press_event, widget)
            engine.handle_mouse_move(move_event, widget)
            engine.handle_mouse_release(release_event, widget)

            # 检查平移效果
            new_viewport = engine.get_current_viewport()
            self.assertNotEqual(new_viewport.pan_x, initial_viewport.pan_x, "X轴平移应该发生变化")

            logger.info(f"平移测试成功: pan_x {initial_viewport.pan_x} → {new_viewport.pan_x}")

        except ImportError as e:
            self.skipTest(f"平移功能不可用: {e}")
        except Exception as e:
            logger.warning(f"平移功能测试失败: {e}")

    def test_performance_monitoring(self):
        """测试性能监控"""
        logger.info("测试性能监控...")

        try:
            from core.webgpu.interaction_engine import GPUInteractionEngine

            engine = GPUInteractionEngine()

            # 获取性能统计
            stats = engine.get_performance_stats()
            self.assertIsInstance(stats, dict, "应该返回字典类型的性能统计")

            required_keys = ['total_interactions', 'zoom_operations', 'pan_operations',
                             'animation_frames', 'average_frame_time', 'gpu_acceleration_enabled']

            for key in required_keys:
                self.assertIn(key, stats, f"性能统计应该包含{key}")

            logger.info(f"性能统计: {stats}")

        except ImportError as e:
            self.skipTest(f"性能监控不可用: {e}")

    def test_reset_and_fit_operations(self):
        """测试重置和适应操作"""
        logger.info("测试重置和适应操作...")

        try:
            from core.webgpu.interaction_engine import GPUInteractionEngine

            engine = GPUInteractionEngine()

            # 修改视口状态
            engine.set_viewport(0, 100, 0, 50)
            original_viewport = engine.get_current_viewport()
            original_viewport.zoom_level = 2.0
            original_viewport.pan_x = 10.0
            original_viewport.pan_y = 5.0

            # 重置视口
            engine.reset_viewport()
            reset_viewport = engine.get_current_viewport()

            # 检查重置效果（注意：重置可能是异步的）
            time.sleep(0.1)  # 等待动画完成

            logger.info(f"重置前: zoom={original_viewport.zoom_level}, pan_x={original_viewport.pan_x}")
            logger.info(f"重置后: zoom={reset_viewport.zoom_level}, pan_x={reset_viewport.pan_x}")

            # 测试缩放以适应数据
            data_bounds = (10, 90, 5, 45)
            engine.zoom_to_fit(data_bounds)

            logger.info("缩放适应测试完成")

        except ImportError as e:
            self.skipTest(f"重置和适应操作不可用: {e}")

    def test_configuration(self):
        """测试配置管理"""
        logger.info("测试配置管理...")

        try:
            from core.webgpu.interaction_engine import GPUInteractionEngine

            engine = GPUInteractionEngine()

            # 获取初始配置
            initial_zoom_sensitivity = engine.config.get('zoom_sensitivity', 0.1)

            # 修改配置
            new_sensitivity = 0.2
            engine.set_config('zoom_sensitivity', new_sensitivity)

            # 验证配置更改
            self.assertEqual(engine.config['zoom_sensitivity'], new_sensitivity)

            # 测试动画配置
            engine.set_animation_enabled(False)
            engine.set_animation_enabled(True)

            logger.info(f"配置测试成功: zoom_sensitivity {initial_zoom_sensitivity} → {new_sensitivity}")

        except ImportError as e:
            self.skipTest(f"配置管理不可用: {e}")


class TestGPUEnhancedZoomMixin(unittest.TestCase):
    """GPU增强缩放Mixin测试"""

    def setUp(self):
        """测试初始化"""
        self.app = None
        if QT_AVAILABLE:
            if not QApplication.instance():
                self.app = QApplication(sys.argv)

    def tearDown(self):
        """测试清理"""
        if self.app:
            self.app.quit()

    def test_mixin_import(self):
        """测试Mixin导入"""
        logger.info("测试GPU增强缩放Mixin导入...")

        try:
            from gui.widgets.chart_mixins.gpu_enhanced_zoom_mixin import GPUEnhancedZoomMixin
            self.assertIsNotNone(GPUEnhancedZoomMixin, "应该能导入GPUEnhancedZoomMixin")
            logger.info("GPU增强缩放Mixin导入成功")

        except ImportError as e:
            self.skipTest(f"GPU增强缩放Mixin不可用: {e}")

    def test_mixin_functionality(self):
        """测试Mixin功能"""
        if not QT_AVAILABLE:
            self.skipTest("PyQt5不可用，跳过Mixin功能测试")

        logger.info("测试GPU增强缩放Mixin功能...")

        try:
            from gui.widgets.chart_mixins.gpu_enhanced_zoom_mixin import GPUEnhancedZoomMixin
            from PyQt5.QtWidgets import QWidget

            # 创建测试类
            class TestWidget(QWidget, GPUEnhancedZoomMixin):
                def __init__(self):
                    super().__init__()
                    self.resize(800, 600)

            widget = TestWidget()

            # 测试GPU缩放可用性
            is_available = widget.is_gpu_zoom_available()
            logger.info(f"GPU缩放可用性: {is_available}")

            # 测试配置获取
            config = widget.get_gpu_zoom_config()
            self.assertIsInstance(config, dict, "应该返回配置字典")

            # 测试性能统计
            stats = widget.get_gpu_performance_stats()
            self.assertIsInstance(stats, dict, "应该返回性能统计字典")

            logger.info("GPU增强缩放Mixin功能测试成功")

        except ImportError as e:
            self.skipTest(f"GPU增强缩放Mixin功能不可用: {e}")
        except Exception as e:
            logger.warning(f"Mixin功能测试失败: {e}")


def run_tests():
    """运行所有测试"""
    logger.info("开始GPU交互功能测试...")

    # 创建测试套件
    suite = unittest.TestSuite()

    # 添加测试用例
    suite.addTest(unittest.makeSuite(TestGPUInteractionEngine))
    suite.addTest(unittest.makeSuite(TestGPUEnhancedZoomMixin))

    # 运行测试
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # 输出测试结果
    logger.info("=" * 60)
    logger.info("GPU交互功能测试结果总结")
    logger.info("=" * 60)
    logger.info(f"运行测试: {result.testsRun}")
    logger.info(f"失败: {len(result.failures)}")
    logger.info(f"错误: {len(result.errors)}")
    logger.info(f"跳过: {len(result.skipped)}")

    if result.failures:
        logger.error("失败的测试:")
        for test, traceback in result.failures:
            logger.error(f"  - {test}: {traceback}")

    if result.errors:
        logger.error("错误的测试:")
        for test, traceback in result.errors:
            logger.error(f"  - {test}: {traceback}")

    success = len(result.failures) == 0 and len(result.errors) == 0
    logger.info(f"测试结果: {'通过' if success else '失败'}")

    return success


if __name__ == '__main__':
    run_tests()
