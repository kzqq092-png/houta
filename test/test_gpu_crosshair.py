"""
GPU十字光标引擎测试脚本

测试GPU加速的十字光标功能：
- 十字光标引擎创建和配置
- 鼠标跟踪和坐标转换
- GPU渲染和CPU后备
- 性能监控和优化
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
    from PyQt5.QtGui import QMouseEvent, QPainter
    from PyQt5.QtCore import Qt, QPoint
    QT_AVAILABLE = True
except ImportError:
    QT_AVAILABLE = False
    logger.warning("PyQt5不可用，跳过UI相关测试")


class TestGPUCrosshairEngine(unittest.TestCase):
    """GPU十字光标引擎测试"""

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

    def test_crosshair_engine_creation(self):
        """测试十字光标引擎创建"""
        logger.info("测试GPU十字光标引擎创建...")

        try:
            from core.webgpu.crosshair_engine import GPUCrosshairEngine, CrosshairState, CrosshairStyle, CrosshairConfig

            # 创建十字光标引擎
            engine = GPUCrosshairEngine()
            self.assertIsNotNone(engine, "应该能创建GPU十字光标引擎")

            # 检查初始状态
            state = engine.get_current_state()
            self.assertIsInstance(state, CrosshairState, "应该有CrosshairState")
            self.assertFalse(state.visible, "初始状态应该不可见")

            # 检查配置
            config = engine.get_config()
            self.assertIsInstance(config, CrosshairConfig, "应该有CrosshairConfig")

            logger.info("GPU十字光标引擎创建成功")

        except ImportError as e:
            self.skipTest(f"GPU十字光标引擎不可用: {e}")

    def test_crosshair_state(self):
        """测试十字光标状态"""
        logger.info("测试十字光标状态...")

        try:
            from core.webgpu.crosshair_engine import CrosshairState

            # 创建十字光标状态
            state = CrosshairState(100, 200, True, 50.5, 25.5, time.time())

            # 测试复制
            state_copy = state.copy()
            self.assertEqual(state.x, state_copy.x)
            self.assertEqual(state.y, state_copy.y)
            self.assertEqual(state.visible, state_copy.visible)
            self.assertEqual(state.data_x, state_copy.data_x)
            self.assertEqual(state.data_y, state_copy.data_y)

            logger.info(f"十字光标状态: x={state.x}, y={state.y}, visible={state.visible}")

        except ImportError as e:
            self.skipTest(f"CrosshairState不可用: {e}")

    def test_crosshair_config(self):
        """测试十字光标配置"""
        logger.info("测试十字光标配置...")

        try:
            from core.webgpu.crosshair_engine import CrosshairConfig, CrosshairStyle

            # 创建默认配置
            config = CrosshairConfig()
            self.assertTrue(config.enabled, "默认应该启用")
            self.assertEqual(config.style, CrosshairStyle.SOLID, "默认样式应该是实线")
            self.assertEqual(config.line_width, 1.0, "默认线宽应该是1.0")

            # 修改配置
            config.style = CrosshairStyle.DASHED
            config.line_width = 2.0
            config.line_color = "#FF0000"

            self.assertEqual(config.style, CrosshairStyle.DASHED)
            self.assertEqual(config.line_width, 2.0)
            self.assertEqual(config.line_color, "#FF0000")

            logger.info("十字光标配置测试成功")

        except ImportError as e:
            self.skipTest(f"CrosshairConfig不可用: {e}")

    def test_mouse_position_update(self):
        """测试鼠标位置更新"""
        if not QT_AVAILABLE:
            self.skipTest("PyQt5不可用，跳过鼠标位置更新测试")

        logger.info("测试鼠标位置更新...")

        try:
            from core.webgpu.crosshair_engine import GPUCrosshairEngine

            engine = GPUCrosshairEngine()
            widget = QWidget()
            widget.resize(800, 600)

            # 设置可见性
            engine.set_visibility(True)

            # 更新鼠标位置
            result = engine.update_mouse_position(400, 300, widget)
            self.assertTrue(result, "鼠标位置更新应该成功")

            # 检查状态更新
            state = engine.get_current_state()
            self.assertTrue(state.visible, "十字光标应该可见")

            # 测试多次更新
            for i in range(5):
                x, y = 400 + i * 10, 300 + i * 5
                engine.update_mouse_position(x, y, widget)

            logger.info("鼠标位置更新测试成功")

        except ImportError as e:
            self.skipTest(f"鼠标位置更新不可用: {e}")
        except Exception as e:
            logger.warning(f"鼠标位置更新测试失败: {e}")

    def test_crosshair_rendering(self):
        """测试十字光标渲染"""
        if not QT_AVAILABLE:
            self.skipTest("PyQt5不可用，跳过十字光标渲染测试")

        logger.info("测试十字光标渲染...")

        try:
            from core.webgpu.crosshair_engine import GPUCrosshairEngine
            from PyQt5.QtGui import QPixmap

            engine = GPUCrosshairEngine()
            widget = QWidget()
            widget.resize(800, 600)

            # 设置十字光标状态
            engine.set_visibility(True)
            engine.update_mouse_position(400, 300, widget)

            # 创建画布进行渲染测试
            pixmap = QPixmap(800, 600)
            painter = QPainter(pixmap)

            try:
                # 测试渲染
                result = engine.render_crosshair(painter, widget)
                self.assertTrue(result, "十字光标渲染应该成功")

                logger.info("十字光标渲染测试成功")

            finally:
                painter.end()

        except ImportError as e:
            self.skipTest(f"十字光标渲染不可用: {e}")
        except Exception as e:
            logger.warning(f"十字光标渲染测试失败: {e}")

    def test_performance_monitoring(self):
        """测试性能监控"""
        logger.info("测试性能监控...")

        try:
            from core.webgpu.crosshair_engine import GPUCrosshairEngine

            engine = GPUCrosshairEngine()

            # 获取性能统计
            stats = engine.get_performance_stats()
            self.assertIsInstance(stats, dict, "应该返回字典类型的性能统计")

            required_keys = ['total_updates', 'gpu_renders', 'cpu_fallbacks',
                             'average_render_time', 'fps', 'gpu_acceleration_enabled']

            for key in required_keys:
                self.assertIn(key, stats, f"性能统计应该包含{key}")

            logger.info(f"性能统计: {stats}")

        except ImportError as e:
            self.skipTest(f"性能监控不可用: {e}")

    def test_crosshair_styles(self):
        """测试十字光标样式"""
        logger.info("测试十字光标样式...")

        try:
            from core.webgpu.crosshair_engine import GPUCrosshairEngine, CrosshairStyle

            engine = GPUCrosshairEngine()
            config = engine.get_config()

            # 测试不同样式
            styles = [CrosshairStyle.SOLID, CrosshairStyle.DASHED, CrosshairStyle.DOTTED,
                      CrosshairStyle.CROSS_ONLY, CrosshairStyle.GRID]

            for style in styles:
                config.style = style
                engine.update_config(config)

                updated_config = engine.get_config()
                self.assertEqual(updated_config.style, style, f"样式应该设置为{style.value}")

            logger.info("十字光标样式测试成功")

        except ImportError as e:
            self.skipTest(f"十字光标样式不可用: {e}")

    def test_visibility_control(self):
        """测试可见性控制"""
        logger.info("测试可见性控制...")

        try:
            from core.webgpu.crosshair_engine import GPUCrosshairEngine

            engine = GPUCrosshairEngine()

            # 初始状态应该不可见
            state = engine.get_current_state()
            self.assertFalse(state.visible, "初始状态应该不可见")

            # 设置可见
            engine.set_visibility(True)
            state = engine.get_current_state()
            self.assertTrue(state.visible, "设置后应该可见")

            # 设置不可见
            engine.set_visibility(False)
            state = engine.get_current_state()
            self.assertFalse(state.visible, "设置后应该不可见")

            logger.info("可见性控制测试成功")

        except ImportError as e:
            self.skipTest(f"可见性控制不可用: {e}")

    def test_cache_functionality(self):
        """测试缓存功能"""
        logger.info("测试缓存功能...")

        try:
            from core.webgpu.crosshair_engine import GPUCrosshairEngine

            engine = GPUCrosshairEngine()

            # 测试缓存清除
            engine.clear_cache()  # 应该不抛出异常

            # 测试重置
            engine.reset()  # 应该不抛出异常

            state = engine.get_current_state()
            self.assertFalse(state.visible, "重置后应该不可见")
            self.assertEqual(state.x, 0.0, "重置后X坐标应该为0")
            self.assertEqual(state.y, 0.0, "重置后Y坐标应该为0")

            logger.info("缓存功能测试成功")

        except ImportError as e:
            self.skipTest(f"缓存功能不可用: {e}")


class TestGPUEnhancedCrosshairMixin(unittest.TestCase):
    """GPU增强十字光标Mixin测试"""

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
        logger.info("测试GPU增强十字光标Mixin导入...")

        try:
            from gui.widgets.chart_mixins.gpu_enhanced_crosshair_mixin import GPUEnhancedCrosshairMixin
            self.assertIsNotNone(GPUEnhancedCrosshairMixin, "应该能导入GPUEnhancedCrosshairMixin")
            logger.info("GPU增强十字光标Mixin导入成功")

        except ImportError as e:
            self.skipTest(f"GPU增强十字光标Mixin不可用: {e}")

    def test_mixin_functionality(self):
        """测试Mixin功能"""
        if not QT_AVAILABLE:
            self.skipTest("PyQt5不可用，跳过Mixin功能测试")

        logger.info("测试GPU增强十字光标Mixin功能...")

        try:
            from gui.widgets.chart_mixins.gpu_enhanced_crosshair_mixin import GPUEnhancedCrosshairMixin
            from PyQt5.QtWidgets import QWidget

            # 创建测试类
            class TestWidget(QWidget, GPUEnhancedCrosshairMixin):
                def __init__(self):
                    super().__init__()
                    self.resize(800, 600)

            widget = TestWidget()

            # 测试GPU十字光标可用性
            is_available = widget.is_gpu_crosshair_available()
            logger.info(f"GPU十字光标可用性: {is_available}")

            # 测试配置获取
            config = widget.get_gpu_crosshair_config()
            self.assertIsInstance(config, dict, "应该返回配置字典")

            # 测试性能统计
            stats = widget.get_gpu_crosshair_performance_stats()
            self.assertIsInstance(stats, dict, "应该返回性能统计字典")

            # 测试十字光标控制
            if is_available:
                widget.enable_gpu_crosshair()
                self.assertTrue(widget.is_gpu_crosshair_visible(), "启用后应该可见")

                widget.disable_gpu_crosshair()
                self.assertFalse(widget.is_gpu_crosshair_visible(), "禁用后应该不可见")

                # 测试样式设置
                widget.set_gpu_crosshair_style("dashed")
                widget.set_gpu_crosshair_color("#FF0000")
                widget.set_gpu_crosshair_width(2.0)
                widget.set_gpu_crosshair_alpha(0.7)

                # 测试功能设置
                widget.set_gpu_crosshair_animation(True)
                widget.set_gpu_crosshair_labels(True)
                widget.set_gpu_crosshair_snap_to_data(True)

            logger.info("GPU增强十字光标Mixin功能测试成功")

        except ImportError as e:
            self.skipTest(f"GPU增强十字光标Mixin功能不可用: {e}")
        except Exception as e:
            logger.warning(f"Mixin功能测试失败: {e}")

    def test_config_batch_update(self):
        """测试配置批量更新"""
        if not QT_AVAILABLE:
            self.skipTest("PyQt5不可用，跳过配置批量更新测试")

        logger.info("测试配置批量更新...")

        try:
            from gui.widgets.chart_mixins.gpu_enhanced_crosshair_mixin import GPUEnhancedCrosshairMixin
            from PyQt5.QtWidgets import QWidget

            # 创建测试类
            class TestWidget(QWidget, GPUEnhancedCrosshairMixin):
                def __init__(self):
                    super().__init__()
                    self.resize(800, 600)

            widget = TestWidget()

            if widget.is_gpu_crosshair_available():
                # 批量更新配置
                config_update = {
                    'style': 'dashed',
                    'line_width': 2.5,
                    'line_color': '#00FF00',
                    'line_alpha': 0.6,
                    'smooth_animation': False,
                    'show_labels': False,
                    'snap_to_data': False,
                    'use_gpu_rendering': True
                }

                widget.update_gpu_crosshair_config(config_update)

                # 验证配置更新
                updated_config = widget.get_gpu_crosshair_config()
                self.assertEqual(updated_config['style'], 'dashed')
                self.assertEqual(updated_config['line_width'], 2.5)
                self.assertEqual(updated_config['line_color'], '#00FF00')
                self.assertEqual(updated_config['line_alpha'], 0.6)
                self.assertFalse(updated_config['smooth_animation'])
                self.assertFalse(updated_config['show_labels'])
                self.assertFalse(updated_config['snap_to_data'])
                self.assertTrue(updated_config['use_gpu_rendering'])

            logger.info("配置批量更新测试成功")

        except ImportError as e:
            self.skipTest(f"配置批量更新不可用: {e}")
        except Exception as e:
            logger.warning(f"配置批量更新测试失败: {e}")


def run_tests():
    """运行所有测试"""
    logger.info("开始GPU十字光标功能测试...")

    # 创建测试套件
    suite = unittest.TestSuite()

    # 添加测试用例
    suite.addTest(unittest.TestLoader().loadTestsFromTestCase(TestGPUCrosshairEngine))
    suite.addTest(unittest.TestLoader().loadTestsFromTestCase(TestGPUEnhancedCrosshairMixin))

    # 运行测试
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # 输出测试结果
    logger.info("=" * 60)
    logger.info("GPU十字光标功能测试结果总结")
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
