"""
WebGPU状态监控对话框

显示WebGPU环境、兼容性、性能等详细信息，
提供手动后端切换和性能测试功能。
"""

import logging
from typing import Dict, Any, Optional
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTabWidget, QWidget,
    QLabel, QTableWidget, QTableWidgetItem, QTextEdit, QPushButton,
    QGroupBox, QGridLayout, QProgressBar, QComboBox, QSpinBox,
    QCheckBox, QHeaderView, QMessageBox, QScrollArea
)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal
from PyQt5.QtGui import QFont, QColor

logger = logging.getLogger(__name__)


class WebGPUStatusDialog(QDialog):
    """WebGPU状态监控对话框"""

    backend_change_requested = pyqtSignal(str)  # 请求后端切换
    benchmark_requested = pyqtSignal(int)  # 请求性能测试

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("WebGPU硬件加速状态")
        self.setFixedSize(800, 600)

        # 数据源
        self._webgpu_renderer = None
        self._status_data = {}

        # 初始化UI
        self.init_ui()

        # 定时更新
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_status)
        self.update_timer.start(2000)  # 每2秒更新

        # 尝试获取WebGPU渲染器
        self._init_webgpu_renderer()

    def _init_webgpu_renderer(self):
        """初始化WebGPU渲染器引用"""
        try:
            from optimization.webgpu_chart_renderer import get_webgpu_chart_renderer
            self._webgpu_renderer = get_webgpu_chart_renderer()
            logger.info("WebGPU状态对话框: 获取渲染器成功")
        except Exception as e:
            logger.warning(f"WebGPU状态对话框: 无法获取渲染器: {e}")

    def init_ui(self):
        """初始化用户界面"""
        layout = QVBoxLayout(self)

        # 创建选项卡
        self.tab_widget = QTabWidget()

        # 环境信息选项卡
        self.environment_tab = self._create_environment_tab()
        self.tab_widget.addTab(self.environment_tab, "环境信息")

        # 兼容性选项卡
        self.compatibility_tab = self._create_compatibility_tab()
        self.tab_widget.addTab(self.compatibility_tab, "兼容性")

        # 性能监控选项卡
        self.performance_tab = self._create_performance_tab()
        self.tab_widget.addTab(self.performance_tab, "性能监控")

        # 控制面板选项卡
        self.control_tab = self._create_control_tab()
        self.tab_widget.addTab(self.control_tab, "控制面板")

        layout.addWidget(self.tab_widget)

        # 底部按钮
        button_layout = QHBoxLayout()

        self.refresh_btn = QPushButton("刷新")
        self.refresh_btn.clicked.connect(self.update_status)
        button_layout.addWidget(self.refresh_btn)

        button_layout.addStretch()

        self.close_btn = QPushButton("关闭")
        self.close_btn.clicked.connect(self.accept)
        button_layout.addWidget(self.close_btn)

        layout.addLayout(button_layout)

    def _create_environment_tab(self) -> QWidget:
        """创建环境信息选项卡"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # GPU信息组
        gpu_group = QGroupBox("GPU硬件信息")
        gpu_layout = QGridLayout(gpu_group)

        self.gpu_adapter_label = QLabel("未知")
        self.gpu_vendor_label = QLabel("未知")
        self.gpu_memory_label = QLabel("未知")
        self.gpu_texture_label = QLabel("未知")

        gpu_layout.addWidget(QLabel("适配器名称:"), 0, 0)
        gpu_layout.addWidget(self.gpu_adapter_label, 0, 1)
        gpu_layout.addWidget(QLabel("厂商:"), 1, 0)
        gpu_layout.addWidget(self.gpu_vendor_label, 1, 1)
        gpu_layout.addWidget(QLabel("显存:"), 2, 0)
        gpu_layout.addWidget(self.gpu_memory_label, 2, 1)
        gpu_layout.addWidget(QLabel("最大纹理:"), 3, 0)
        gpu_layout.addWidget(self.gpu_texture_label, 3, 1)

        layout.addWidget(gpu_group)

        # 环境信息组
        env_group = QGroupBox("运行环境")
        env_layout = QGridLayout(env_group)

        self.platform_label = QLabel("未知")
        self.screen_label = QLabel("未知")
        self.support_level_label = QLabel("未知")

        env_layout.addWidget(QLabel("操作系统:"), 0, 0)
        env_layout.addWidget(self.platform_label, 0, 1)
        env_layout.addWidget(QLabel("屏幕分辨率:"), 1, 0)
        env_layout.addWidget(self.screen_label, 1, 1)
        env_layout.addWidget(QLabel("支持级别:"), 2, 0)
        env_layout.addWidget(self.support_level_label, 2, 1)

        layout.addWidget(env_group)

        layout.addStretch()
        return widget

    def _create_compatibility_tab(self) -> QWidget:
        """创建兼容性选项卡"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # 兼容性级别
        compat_group = QGroupBox("兼容性评估")
        compat_layout = QGridLayout(compat_group)

        self.compat_level_label = QLabel("未知")
        self.compat_score_label = QLabel("未知")
        self.recommended_backend_label = QLabel("未知")

        compat_layout.addWidget(QLabel("兼容性级别:"), 0, 0)
        compat_layout.addWidget(self.compat_level_label, 0, 1)
        compat_layout.addWidget(QLabel("性能评分:"), 1, 0)
        compat_layout.addWidget(self.compat_score_label, 1, 1)
        compat_layout.addWidget(QLabel("推荐后端:"), 2, 0)
        compat_layout.addWidget(self.recommended_backend_label, 2, 1)

        layout.addWidget(compat_group)

        # 兼容性问题
        issues_group = QGroupBox("兼容性问题")
        issues_layout = QVBoxLayout(issues_group)

        self.issues_table = QTableWidget()
        self.issues_table.setColumnCount(3)
        self.issues_table.setHorizontalHeaderLabels(["类型", "严重性", "描述"])
        self.issues_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)

        issues_layout.addWidget(self.issues_table)
        layout.addWidget(issues_group)

        # 优化建议
        recommendations_group = QGroupBox("优化建议")
        recommendations_layout = QVBoxLayout(recommendations_group)

        self.recommendations_text = QTextEdit()
        self.recommendations_text.setMaximumHeight(100)
        self.recommendations_text.setReadOnly(True)

        recommendations_layout.addWidget(self.recommendations_text)
        layout.addWidget(recommendations_group)

        return widget

    def _create_performance_tab(self) -> QWidget:
        """创建性能监控选项卡"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # 实时性能
        perf_group = QGroupBox("实时性能")
        perf_layout = QGridLayout(perf_group)

        self.current_backend_label = QLabel("未知")
        self.total_renders_label = QLabel("0")
        self.successful_renders_label = QLabel("0")
        self.failed_renders_label = QLabel("0")
        self.average_time_label = QLabel("0.0ms")
        self.fallback_count_label = QLabel("0")

        perf_layout.addWidget(QLabel("当前后端:"), 0, 0)
        perf_layout.addWidget(self.current_backend_label, 0, 1)
        perf_layout.addWidget(QLabel("总渲染次数:"), 1, 0)
        perf_layout.addWidget(self.total_renders_label, 1, 1)
        perf_layout.addWidget(QLabel("成功渲染:"), 2, 0)
        perf_layout.addWidget(self.successful_renders_label, 2, 1)
        perf_layout.addWidget(QLabel("失败渲染:"), 3, 0)
        perf_layout.addWidget(self.failed_renders_label, 3, 1)
        perf_layout.addWidget(QLabel("平均耗时:"), 4, 0)
        perf_layout.addWidget(self.average_time_label, 4, 1)
        perf_layout.addWidget(QLabel("降级次数:"), 5, 0)
        perf_layout.addWidget(self.fallback_count_label, 5, 1)

        layout.addWidget(perf_group)

        # 性能历史
        history_group = QGroupBox("性能统计")
        history_layout = QVBoxLayout(history_group)

        self.performance_table = QTableWidget()
        self.performance_table.setColumnCount(3)
        self.performance_table.setHorizontalHeaderLabels(["后端", "渲染次数", "平均耗时"])
        self.performance_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)

        history_layout.addWidget(self.performance_table)
        layout.addWidget(history_group)

        return widget

    def _create_control_tab(self) -> QWidget:
        """创建控制面板选项卡"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # 后端控制
        backend_group = QGroupBox("后端控制")
        backend_layout = QVBoxLayout(backend_group)

        # 后端选择
        backend_select_layout = QHBoxLayout()
        backend_select_layout.addWidget(QLabel("切换后端:"))

        self.backend_combo = QComboBox()
        self.backend_combo.addItems(["webgpu", "opengl", "canvas2d", "matplotlib"])
        backend_select_layout.addWidget(self.backend_combo)

        self.switch_backend_btn = QPushButton("切换")
        self.switch_backend_btn.clicked.connect(self._switch_backend)
        backend_select_layout.addWidget(self.switch_backend_btn)

        backend_select_layout.addStretch()
        backend_layout.addLayout(backend_select_layout)

        layout.addWidget(backend_group)

        # 性能测试
        benchmark_group = QGroupBox("性能测试")
        benchmark_layout = QVBoxLayout(benchmark_group)

        # 测试参数
        test_params_layout = QHBoxLayout()
        test_params_layout.addWidget(QLabel("测试迭代次数:"))

        self.iterations_spin = QSpinBox()
        self.iterations_spin.setRange(1, 100)
        self.iterations_spin.setValue(10)
        test_params_layout.addWidget(self.iterations_spin)

        self.benchmark_btn = QPushButton("开始测试")
        self.benchmark_btn.clicked.connect(self._start_benchmark)
        test_params_layout.addWidget(self.benchmark_btn)

        test_params_layout.addStretch()
        benchmark_layout.addLayout(test_params_layout)

        # 测试结果
        self.benchmark_results = QTextEdit()
        self.benchmark_results.setMaximumHeight(150)
        self.benchmark_results.setReadOnly(True)
        benchmark_layout.addWidget(self.benchmark_results)

        layout.addWidget(benchmark_group)

        # 调试控制
        debug_group = QGroupBox("调试控制")
        debug_layout = QVBoxLayout(debug_group)

        debug_controls_layout = QHBoxLayout()

        self.debug_checkbox = QCheckBox("启用调试模式")
        self.debug_checkbox.stateChanged.connect(self._toggle_debug)
        debug_controls_layout.addWidget(self.debug_checkbox)

        self.reset_stats_btn = QPushButton("重置统计")
        self.reset_stats_btn.clicked.connect(self._reset_stats)
        debug_controls_layout.addWidget(self.reset_stats_btn)

        debug_controls_layout.addStretch()
        debug_layout.addLayout(debug_controls_layout)

        layout.addWidget(debug_group)

        layout.addStretch()
        return widget

    def _switch_backend(self):
        """切换后端"""
        backend = self.backend_combo.currentText()
        self.backend_change_requested.emit(backend)

        # 直接调用渲染器切换
        if self._webgpu_renderer and hasattr(self._webgpu_renderer, 'force_webgpu_backend'):
            success = self._webgpu_renderer.force_webgpu_backend(backend)
            if success:
                QMessageBox.information(self, "成功", f"已切换到 {backend} 后端")
            else:
                QMessageBox.warning(self, "失败", f"无法切换到 {backend} 后端")

        # 立即更新状态
        self.update_status()

    def _start_benchmark(self):
        """开始性能测试"""
        iterations = self.iterations_spin.value()
        self.benchmark_requested.emit(iterations)

        # 直接调用渲染器测试
        if self._webgpu_renderer and hasattr(self._webgpu_renderer, 'benchmark_rendering'):
            try:
                # 创建测试数据
                import pandas as pd
                import numpy as np

                test_data = pd.DataFrame({
                    'open': np.random.rand(1000) * 100,
                    'high': np.random.rand(1000) * 100,
                    'low': np.random.rand(1000) * 100,
                    'close': np.random.rand(1000) * 100,
                    'volume': np.random.rand(1000) * 10000
                })

                self.benchmark_btn.setEnabled(False)
                self.benchmark_btn.setText("测试中...")

                results = self._webgpu_renderer.benchmark_rendering(test_data, iterations)

                # 显示结果
                result_text = f"""性能测试结果 (迭代次数: {iterations})

WebGPU平均耗时: {results.get('webgpu_average', 0) * 1000:.1f}ms
matplotlib平均耗时: {results.get('matplotlib_average', 0) * 1000:.1f}ms
加速比: {results.get('speedup_ratio', 0):.1f}x

详细数据:
WebGPU耗时范围: {min(results.get('webgpu_times', [0])) * 1000:.1f}ms - {max(results.get('webgpu_times', [0])) * 1000:.1f}ms
matplotlib耗时范围: {min(results.get('matplotlib_times', [0])) * 1000:.1f}ms - {max(results.get('matplotlib_times', [0])) * 1000:.1f}ms
"""

                self.benchmark_results.setText(result_text)

            except Exception as e:
                self.benchmark_results.setText(f"性能测试失败: {str(e)}")
            finally:
                self.benchmark_btn.setEnabled(True)
                self.benchmark_btn.setText("开始测试")

    def _toggle_debug(self, state):
        """切换调试模式"""
        enable_debug = state == Qt.Checked

        if self._webgpu_renderer and hasattr(self._webgpu_renderer, 'enable_webgpu_debug'):
            self._webgpu_renderer.enable_webgpu_debug(enable_debug)

    def _reset_stats(self):
        """重置统计"""
        if self._webgpu_renderer and hasattr(self._webgpu_renderer, 'reset_webgpu_stats'):
            self._webgpu_renderer.reset_webgpu_stats()
            self.update_status()
            QMessageBox.information(self, "成功", "统计数据已重置")

    def update_status(self):
        """更新状态显示"""
        if not self._webgpu_renderer:
            return

        try:
            # 获取状态数据
            if hasattr(self._webgpu_renderer, 'get_webgpu_status'):
                self._status_data = self._webgpu_renderer.get_webgpu_status()
            else:
                return

            # 更新各个选项卡
            self._update_environment_tab()
            self._update_compatibility_tab()
            self._update_performance_tab()

        except Exception as e:
            logger.error(f"更新WebGPU状态失败: {e}")

    def _update_environment_tab(self):
        """更新环境信息选项卡"""
        try:
            env_data = self._status_data.get('environment', {})
            gpu_data = env_data.get('gpu_capabilities', {})

            self.gpu_adapter_label.setText(gpu_data.get('adapter_name', '未知'))
            self.gpu_vendor_label.setText(gpu_data.get('vendor', '未知'))
            self.gpu_memory_label.setText(f"{gpu_data.get('memory_mb', 0)}MB")
            self.gpu_texture_label.setText(f"{gpu_data.get('max_texture_size', 0)}")

            self.platform_label.setText(self._status_data.get('environment', {}).get('platform', '未知'))
            self.screen_label.setText("未知")  # 需要从环境数据获取
            self.support_level_label.setText(env_data.get('support_level', '未知'))

        except Exception as e:
            logger.error(f"更新环境信息失败: {e}")

    def _update_compatibility_tab(self):
        """更新兼容性选项卡"""
        try:
            compat_data = self._status_data.get('compatibility', {})

            self.compat_level_label.setText(compat_data.get('level', '未知'))
            self.compat_score_label.setText(f"{compat_data.get('performance_score', 0):.1f}/100")

            # 获取推荐建议
            if hasattr(self._webgpu_renderer, 'get_webgpu_recommendations'):
                recommendations = self._webgpu_renderer.get_webgpu_recommendations()
                self.recommendations_text.setText('\n'.join(recommendations))

        except Exception as e:
            logger.error(f"更新兼容性信息失败: {e}")

    def _update_performance_tab(self):
        """更新性能监控选项卡"""
        try:
            perf_data = self._status_data.get('performance', {})
            stats_data = self._status_data.get('stats', {})

            self.current_backend_label.setText(perf_data.get('current_backend', '未知'))
            self.total_renders_label.setText(str(perf_data.get('total_renders', 0)))
            self.successful_renders_label.setText(str(perf_data.get('successful_renders', 0)))
            self.failed_renders_label.setText(str(perf_data.get('failed_renders', 0)))
            self.average_time_label.setText(f"{perf_data.get('average_render_time', 0):.1f}ms")
            self.fallback_count_label.setText(str(stats_data.get('fallback_count', 0)))

        except Exception as e:
            logger.error(f"更新性能信息失败: {e}")

    def set_webgpu_renderer(self, renderer):
        """设置WebGPU渲染器"""
        self._webgpu_renderer = renderer
        self.update_status()
