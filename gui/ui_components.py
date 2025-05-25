"""
UI components for the trading system

This module contains reusable UI components for the trading system.
"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
    QPushButton, QLineEdit, QProgressBar, QTextEdit,
    QGroupBox, QFormLayout, QSpinBox, QDoubleSpinBox,
    QStatusBar, QToolBar, QMenuBar, QMenu, QAction,
    QFileDialog, QMessageBox, QSplitter, QTabWidget,
    QGridLayout, QToolTip
)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QPoint, QObject
from PyQt5.QtGui import QIcon
import pandas as pd
import psutil
from datetime import datetime
import traceback
from core.logger import LogManager
from utils.config_types import LoggingConfig
from typing import Optional, Dict, Any


class BaseAnalysisPanel(QWidget):
    """基础分析面板，统一参数设置、导出、日志、信号、按钮等通用功能"""
    # 通用信号
    analysis_completed = pyqtSignal(dict)
    data_requested = pyqtSignal(dict)
    error_occurred = pyqtSignal(str)
    # 全局自定义指标注册表（类变量）
    _global_custom_indicators = {}
    # 全局联动信号（类变量）
    custom_signal = pyqtSignal(str, object)  # (事件名, 数据)

    def __init__(self, parent=None, log_manager: Optional[LogManager] = None):
        super().__init__(parent)
        self.apply_theme()
        self.log_manager = log_manager or LogManager()
        self.param_widgets: Dict[str, Any] = {}
        self.metric_labels: Dict[str, QLabel] = {}
        self.init_base_ui()
        self.init_base_signals()

    @classmethod
    def register_custom_indicator(cls, name: str, func):
        """
        全局注册自定义指标
        Args:
            name: 指标名称
            func: 计算函数
        """
        cls._global_custom_indicators[name] = func

    @classmethod
    def get_custom_indicator(cls, name: str):
        """
        获取全局自定义指标
        Args:
            name: 指标名称
        Returns:
            func: 计算函数或None
        """
        return cls._global_custom_indicators.get(name)

    def emit_custom_signal(self, event: str, data: object):
        """
        发送全局联动信号
        Args:
            event: 事件名
            data: 任意数据
        """
        BaseAnalysisPanel.custom_signal.emit(event, data)

    def connect_custom_signal(self, slot):
        """
        连接全局联动信号
        Args:
            slot: 槽函数，参数(event, data)
        """
        BaseAnalysisPanel.custom_signal.connect(slot)

    def apply_theme(self):
        """应用统一主题色、字体、控件间距等QSS样式"""
        qss = """
        QWidget {
            font-family: 'Microsoft YaHei', Arial, sans-serif;
            font-size: 14px;
        }
        QGroupBox {
            border: 1px solid #1976D2;
            border-radius: 8px;
            margin-top: 8px;
            padding: 8px;
        }
        QPushButton {
            background-color: #1976D2;
            color: white;
            border-radius: 6px;
            padding: 6px 16px;
            min-width: 80px;
        }
        QPushButton:hover {
            background-color: #1565C0;
        }
        QComboBox, QLineEdit, QSpinBox, QDoubleSpinBox {
            border: 1px solid #1976D2;
            border-radius: 4px;
            padding: 4px 8px;
        }
        QLabel {
            color: #222;
        }
        QTabWidget::pane {
            border: 1px solid #1976D2;
            border-radius: 8px;
        }
        QTableWidget {
            gridline-color: #1976D2;
            selection-background-color: #E3F2FD;
            selection-color: #1976D2;
        }
        QMessageBox {
            background: #fff;
            font-size: 15px;
        }
        """
        self.setStyleSheet(qss)

    def init_base_ui(self):
        """初始化通用UI区域（参数、导出、按钮等）"""
        self.main_layout = QVBoxLayout(self)
        # 参数设置区域（子类可扩展）
        self.params_group = QGroupBox("参数设置")
        self.params_layout = QGridLayout()
        self.params_group.setLayout(self.params_layout)
        self.main_layout.addWidget(self.params_group)
        # 控制按钮区域
        self.button_layout = QHBoxLayout()
        self.analyze_button = QPushButton("市场情绪分析")
        self.export_button = QPushButton("导出结果")
        self.button_layout.addWidget(self.analyze_button)
        self.button_layout.addWidget(self.export_button)
        self.main_layout.addLayout(self.button_layout)

    def init_base_signals(self):
        self.analyze_button.clicked.connect(self.on_analyze)
        self.export_button.clicked.connect(self.on_export)

    def on_analyze(self):
        """分析按钮通用处理，子类可重写"""
        try:
            self.log_manager.info("分析按钮被点击")
            # 子类实现具体分析逻辑
            QMessageBox.information(self, "市场情绪分析", "市场情绪分析已启动，结果将在完成后自动展示。")
        except Exception as e:
            self.log_manager.error(f"市场情绪分析启动失败: {str(e)}")
            QMessageBox.critical(self, "市场情绪分析错误", f"市场情绪分析启动失败: {str(e)}")
            self.error_occurred.emit(f"市场情绪分析启动失败: {str(e)}")

    def on_export(self):
        """统一导出逻辑，子类可扩展"""
        try:
            file_path, _ = QFileDialog.getSaveFileName(
                self,
                "导出分析结果",
                "",
                "Excel Files (*.xlsx);;CSV Files (*.csv)"
            )
            if file_path:
                # 子类实现具体导出内容
                self.log_manager.info(f"结果已导出到: {file_path}")
                QMessageBox.information(self, "导出成功", f"结果已导出到: {file_path}")
        except Exception as e:
            self.log_manager.error(f"导出失败: {str(e)}")
            QMessageBox.critical(self, "导出错误", f"导出失败: {str(e)}")
            self.error_occurred.emit(f"导出失败: {str(e)}")

    def add_param_widget(self, name: str, widget: QWidget):
        self.param_widgets[name] = widget
        row = self.params_layout.rowCount()
        self.params_layout.addWidget(QLabel(name), row, 0)
        self.params_layout.addWidget(widget, row, 1)
        # 增加实时校验信号
        if hasattr(widget, 'valueChanged'):
            widget.valueChanged.connect(self._on_param_widget_changed)
        elif hasattr(widget, 'editingFinished'):
            widget.editingFinished.connect(self._on_param_widget_changed)
        # 增加气泡提示
        widget.setToolTip("")

    def _on_param_widget_changed(self):
        valid, msg = self.validate_params()
        if not valid:
            self.set_status_message(msg, error=True)
            # 气泡提示美化：在控件右侧弹出气泡
            for name, widget in self.param_widgets.items():
                widget.setToolTip("")
            for name, widget in self.param_widgets.items():
                if widget.styleSheet():
                    # 计算气泡显示位置（控件右侧）
                    pos = widget.mapToGlobal(
                        QPoint(widget.width(), widget.height() // 2))
                    QToolTip.showText(pos, msg, widget, widget.rect(), 3000)
                    widget.setToolTip(msg)
        else:
            self.set_status_message("参数校验通过", error=False)
            for name, widget in self.param_widgets.items():
                widget.setToolTip("")

    def add_metric_label(self, name: str, label: QLabel):
        self.metric_labels[name] = label

    def validate_params(self) -> (bool, str):
        """
        校验所有参数控件的输入，支持QSpinBox、QDoubleSpinBox、QLineEdit等。
        校验失败时高亮控件并返回错误信息。
        Returns:
            (bool, str): 是否通过校验，错误信息
        """
        valid = True
        error_msgs = []
        for name, widget in self.param_widgets.items():
            # 还原样式
            widget.setStyleSheet("")
            value = None
            if hasattr(widget, 'value'):
                value = widget.value()
                # 检查范围
                if hasattr(widget, 'minimum') and hasattr(widget, 'maximum'):
                    if value < widget.minimum() or value > widget.maximum():
                        valid = False
                        error_msgs.append(
                            f"{name} 超出允许范围 [{widget.minimum()}, {widget.maximum()}]")
                        widget.setStyleSheet("border: 2px solid red;")
            elif hasattr(widget, 'text'):
                value = widget.text()
                if not value:
                    valid = False
                    error_msgs.append(f"{name} 不能为空")
                    widget.setStyleSheet("border: 2px solid red;")
            # 可扩展更多控件类型
        return valid, "\n".join(error_msgs)

    def set_status_message(self, message: str, error: bool = False):
        """
        在主界面状态栏显示提示信息，error为True时高亮显示
        """
        if hasattr(self.parent(), 'statusBar'):
            bar = self.parent().statusBar()
            if error:
                bar.setStyleSheet("color: red;")
            else:
                bar.setStyleSheet("")
            bar.showMessage(message, 5000)
        # 兼容自带status_label
        elif hasattr(self, 'status_label'):
            self.status_label.setText(message)
            if error:
                self.status_label.setStyleSheet("color: red;")
            else:
                self.status_label.setStyleSheet("")


class AnalysisToolsPanel(BaseAnalysisPanel):
    """Analysis tools panel for the right side of the main window"""

    # 定义信号
    analysis_completed = pyqtSignal(dict)  # 分析完成信号
    data_requested = pyqtSignal(dict)  # 数据请求信号
    error_occurred = pyqtSignal(str)  # 错误信号

    def __init__(self, parent=None):
        """初始化UI组件

        Args:
            parent: 父窗口
        """
        try:
            super().__init__(parent)

            # 初始化日志管理器
            if hasattr(parent, 'log_manager'):
                self.log_manager = parent.log_manager
            else:
                from core.logger import LogManager
                self.log_manager = LogManager()

            # 初始化UI
            self.init_ui()

            # 初始化数据
            self.init_data()

            # 连接信号
            self.connect_signals()

            self.log_manager.info("分析工具面板初始化完成")

        except Exception as e:
            print(f"初始化UI组件失败: {str(e)}")
            if hasattr(self, 'log_manager'):
                self.log_manager.error(f"初始化UI组件失败: {str(e)}")
                self.log_manager.error(traceback.format_exc())
            self.error_occurred.emit(f"初始化失败: {str(e)}")

    def init_ui(self):
        """初始化UI"""
        try:
            layout = self.main_layout  # 修复：直接用父类的主布局，避免重复设置布局
            # 创建策略选择区域
            strategy_group = QGroupBox("策略选择")
            strategy_layout = QVBoxLayout()

            # 添加策略选择下拉框
            self.strategy_combo = QComboBox()
            self.strategy_combo.addItems([
                '双均线策略', 'MACD策略', 'KDJ策略', 'RSI策略', 'BOLL策略',
                'CCI策略', 'ATR策略', 'OBV策略', 'WR策略', 'DMI策略',
                'SAR策略', 'ROC策略', 'TRIX策略', 'MFI策略', 'ADX策略',
                'BBW策略', 'AD策略', 'CMO策略', 'DX策略', '自定义策略'
            ])
            strategy_layout.addWidget(self.strategy_combo)
            strategy_group.setLayout(strategy_layout)
            layout.addWidget(strategy_group)

            # 创建回测设置区域
            backtest_group = QGroupBox("回测设置")
            backtest_layout = QGridLayout()

            # 添加回测设置控件
            self.backtest_widgets = {}
            row = 0
            for setting in ['初始资金', '手续费率', '滑点']:
                label = QLabel(setting)
                spin = QDoubleSpinBox()
                spin.setRange(0, 1000000)
                spin.setValue(100000 if setting == '初始资金' else 0.0003)
                backtest_layout.addWidget(label, row, 0)
                backtest_layout.addWidget(spin, row, 1)
                self.backtest_widgets[setting] = spin
                row += 1

            backtest_group.setLayout(backtest_layout)
            layout.addWidget(backtest_group)

            self.log_manager.info("分析工具面板UI初始化完成")

        except Exception as e:
            error_msg = f"初始化UI失败: {str(e)}"
            self.log_manager.error(error_msg)
            self.log_manager.error(traceback.format_exc())
            self.error_occurred.emit(error_msg)

    def init_data(self):
        """初始化数据"""
        try:
            # 初始化数据缓存
            self.data_cache = {}

            # 初始化当前选中的策略
            self.current_strategy = None

            # 初始化参数默认值
            self.default_params = {
                "均线周期": 20,
                "MACD快线": 12,
                "MACD慢线": 26,
                "MACD信号线": 9,
                "RSI周期": 14,
                "布林带周期": 20,
                "布林带标准差": 2.0,
                "自适应周期": 20,
                "自适应阈值": 0.5,
                "多因子数量": 5
            }

            # 初始化性能指标
            self.performance_metrics = {
                "年化收益率": 0.0,
                "最大回撤": 0.0,
                "夏普比率": 0.0,
                "胜率": 0.0,
                "盈亏比": 0.0,
                "波动率": 0.0,
                "信息比率": 0.0,
                "索提诺比率": 0.0,
                "卡玛比率": 0.0,
                "Alpha": 0.0,
                "Beta": 0.0,
                "跟踪误差": 0.0,
                "换手率": 0.0,
                "最大连续亏损": 0,
                "平均持仓时间": 0
            }

            self.log_manager.info("数据初始化完成")

        except Exception as e:
            error_msg = f"初始化数据失败: {str(e)}"
            self.log_manager.error(error_msg)
            self.log_manager.error(traceback.format_exc())
            self.error_occurred.emit(error_msg)

    def connect_signals(self):
        """连接信号"""
        try:
            # 连接策略选择信号
            self.strategy_combo.currentTextChanged.connect(
                self.on_strategy_changed)

            # 连接按钮信号
            self.analyze_button.clicked.connect(self.on_analyze)
            self.export_button.clicked.connect(self.on_export)

            # 连接参数变化信号
            for widget in self.param_widgets.values():
                widget.valueChanged.connect(self.on_param_changed)

            # 连接回测设置变化信号
            for widget in self.backtest_widgets.values():
                widget.valueChanged.connect(self.on_backtest_setting_changed)

            self.log_manager.info("信号连接完成")

        except Exception as e:
            error_msg = f"连接信号失败: {str(e)}"
            self.log_manager.error(error_msg)
            self.log_manager.error(traceback.format_exc())
            self.error_occurred.emit(error_msg)

    def on_strategy_changed(self, strategy: str):
        """处理策略变更"""
        try:
            self.current_strategy = strategy
            self.update_parameters_visibility()
            self.log_manager.info(f"策略已更改为: {strategy}")
            QMessageBox.information(self, "策略切换", f"已切换到策略: {strategy}")
        except Exception as e:
            error_msg = f"策略变更失败: {str(e)}"
            self.log_manager.error(error_msg)
            QMessageBox.warning(self, "策略切换错误", error_msg)
            self.error_occurred.emit(error_msg)

    def on_param_changed(self):
        """处理参数变更"""
        try:
            self.update_parameters()
            self.log_manager.info("参数已更新")
            QMessageBox.information(self, "参数更新", "参数已成功更新。")
        except Exception as e:
            error_msg = f"参数更新失败: {str(e)}"
            self.log_manager.error(error_msg)
            QMessageBox.warning(self, "参数错误", error_msg)
            self.error_occurred.emit(error_msg)

    def update_parameters_visibility(self):
        """根据当前策略更新参数可见性"""
        try:
            # 获取当前策略的参数配置
            strategy_params = self.get_strategy_parameters(
                self.current_strategy)

            # 更新参数控件的可见性
            for name, control in self.param_widgets.items():
                control.setVisible(name in strategy_params)

            self.log_manager.info("参数可见性已更新")

        except Exception as e:
            error_msg = f"更新参数可见性失败: {str(e)}"
            self.log_manager.error(error_msg)
            self.error_occurred.emit(error_msg)

    def update_parameters(self):
        """更新参数值"""
        try:
            # 获取当前策略的参数配置
            strategy_params = self.get_strategy_parameters(
                self.current_strategy)

            # 更新参数值
            for name, control in self.param_widgets.items():
                if name in strategy_params:
                    control.setValue(strategy_params[name])

            self.log_manager.info("参数值已更新")

        except Exception as e:
            error_msg = f"更新参数值失败: {str(e)}"
            self.log_manager.error(error_msg)
            self.error_occurred.emit(error_msg)

    def get_strategy_parameters(self, strategy: str) -> dict:
        """获取策略参数配置"""
        # 这里可以根据实际策略返回对应的参数配置
        return self.default_params.copy()

    def on_analyze(self):
        """Perform analysis"""
        try:
            valid, msg = self.validate_params()
            if not valid:
                QMessageBox.warning(self, "参数错误", f"请修正以下参数后再分析：\n{msg}")
                return
            # 获取当前策略和参数
            strategy = self.strategy_combo.currentText()
            params = {name: control.value()
                      for name, control in self.param_widgets.items()}
            # 发送数据请求信号
            self.data_requested.emit({
                'type': 'analysis',
                'strategy': strategy,
                'params': params
            })
            self.log_manager.info(f"开始分析 - 策略: {strategy}")
        except Exception as e:
            error_msg = f"分析失败: {str(e)}"
            self.log_manager.error(error_msg)
            self.log_manager.error(traceback.format_exc())
            self.error_occurred.emit(error_msg)

    def on_backtest_setting_changed(self):
        """处理回测设置变更"""
        try:
            self.log_manager.info("回测设置已更新")
            QMessageBox.information(self, "回测设置", "回测设置已更新。")
        except Exception as e:
            error_msg = f"回测设置更新失败: {str(e)}"
            self.log_manager.error(error_msg)
            QMessageBox.warning(self, "回测设置错误", error_msg)
            self.error_occurred.emit(error_msg)

    def update_signals(self, signals):
        """统一更新交易信号显示，便于子类扩展"""
        # 这里可以实现信号表格或图表的更新逻辑，子类可重写
        self.log_manager.info(f"收到{len(signals)}条交易信号")
        # 示例：弹窗提示
        # QMessageBox.information(self, "信号更新", f"收到{len(signals)}条交易信号")

    def update_results(self, results: dict):
        """统一更新分析结果，包含性能指标、图表、信号等"""
        try:
            # 更新性能指标
            if 'metrics' in results:
                metrics = results['metrics']
                for name, value in metrics.items():
                    if name in self.performance_metrics:
                        self.performance_metrics[name] = value
                self.update_metrics_display()
            # 更新图表数据
            if 'chart_data' in results:
                self.chart_updated.emit(results['chart_data'])
            # 更新交易信号
            if 'signals' in results:
                self.update_signals(results['signals'])
            # 发送分析完成信号
            self.analysis_completed.emit(results)
            self.log_manager.info("分析结果更新完成")
        except Exception as e:
            error_msg = f"更新结果失败: {str(e)}"
            self.log_manager.error(error_msg)
            self.log_manager.error(traceback.format_exc())
            self.error_occurred.emit(error_msg)

    def update_metrics_display(self):
        """统一更新性能指标显示，风格与主界面一致"""
        try:
            if not hasattr(self, 'metric_labels') or not self.metric_labels:
                self.create_metrics_display()
            for name, value in self.performance_metrics.items():
                if name in self.metric_labels:
                    if isinstance(value, float):
                        formatted_value = f"{value:.2%}" if "率" in name else f"{value:.2f}"
                    else:
                        formatted_value = str(value)
                    self.metric_labels[name].setText(formatted_value)
        except Exception as e:
            error_msg = f"更新性能指标显示失败: {str(e)}"
            self.log_manager.error(error_msg)
            self.log_manager.error(traceback.format_exc())
            self.error_occurred.emit(error_msg)

    def create_metrics_display(self):
        """统一创建性能指标显示区域，风格与主界面一致"""
        try:
            metrics_group = QGroupBox("性能指标")
            metrics_layout = QFormLayout(metrics_group)
            self.metric_labels = {}
            for name in self.performance_metrics.keys():
                label = QLabel("--")
                metrics_layout.addRow(f"{name}:", label)
                self.metric_labels[name] = label
            self.layout.addWidget(metrics_group)
        except Exception as e:
            error_msg = f"创建性能指标显示区域失败: {str(e)}"
            self.log_manager.error(error_msg)
            self.log_manager.error(traceback.format_exc())
            self.error_occurred.emit(error_msg)


class StatusBar(QStatusBar):
    """Custom status bar with system information"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()

    def init_ui(self):
        """Initialize the UI"""
        # Status message
        self.status_label = QLabel("就绪")
        self.addWidget(self.status_label)

        # CPU usage
        self.cpu_label = QLabel("CPU: 0%")
        self.addPermanentWidget(self.cpu_label)

        # Memory usage
        self.memory_label = QLabel("内存: 0%")
        self.addPermanentWidget(self.memory_label)

        # Time
        self.time_label = QLabel("时间: 00:00:00")
        self.addPermanentWidget(self.time_label)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setMaximumWidth(200)
        self.progress_bar.setVisible(True)
        self.addPermanentWidget(self.progress_bar)

        # Start update timer
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_status)
        self.update_timer.start(1000)  # Update every second

    def update_status(self):
        """Update status information"""
        # Update CPU usage
        cpu_percent = psutil.cpu_percent()
        self.cpu_label.setText(f"CPU: {cpu_percent}%")

        # Update memory usage
        memory = psutil.virtual_memory()
        memory_percent = memory.percent
        self.memory_label.setText(f"内存: {memory_percent}%")

        # Update time
        current_time = datetime.now().strftime("%H:%M:%S")
        self.time_label.setText(f"时间: {current_time}")

    def show_progress(self, visible=True):
        """Show or hide progress bar"""
        self.progress_bar.setVisible(visible)

    def set_progress(self, value):
        """Set progress bar value"""
        self.progress_bar.setValue(value)

    def set_status(self, message):
        """Set status message"""
        self.status_label.setText(message)
