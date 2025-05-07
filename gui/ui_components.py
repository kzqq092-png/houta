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
    QGridLayout
)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal
from PyQt5.QtGui import QIcon
import pandas as pd
import psutil
from datetime import datetime
import traceback
from core.logger import LogManager
from utils.config_types import LoggingConfig


class AnalysisToolsPanel(QWidget):
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
            # 创建主布局
            layout = QVBoxLayout(self)

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

            # 创建参数设置区域
            params_group = QGroupBox("参数设置")
            params_layout = QGridLayout()

            # 添加参数设置控件
            self.param_widgets = {}
            row = 0
            for param in ['快线周期', '慢线周期', '止损比例', '止盈比例']:
                label = QLabel(param)
                spin = QSpinBox()
                spin.setRange(1, 100)
                spin.setValue(20 if '快线' in param else 60)
                params_layout.addWidget(label, row, 0)
                params_layout.addWidget(spin, row, 1)
                self.param_widgets[param] = spin
                row += 1

            params_group.setLayout(params_layout)
            layout.addWidget(params_group)

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

            # 创建按钮区域
            button_layout = QHBoxLayout()

            # 添加功能按钮
            self.analyze_button = QPushButton("分析")
            self.backtest_button = QPushButton("回测")
            self.optimize_button = QPushButton("优化")
            self.export_button = QPushButton("导出结果")

            button_layout.addWidget(self.analyze_button)
            button_layout.addWidget(self.backtest_button)
            button_layout.addWidget(self.optimize_button)
            button_layout.addWidget(self.export_button)

            layout.addLayout(button_layout)

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
            self.backtest_button.clicked.connect(self.on_backtest)
            self.optimize_button.clicked.connect(self.on_optimize)
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
        except Exception as e:
            error_msg = f"策略变更失败: {str(e)}"
            self.log_manager.error(error_msg)
            self.error_occurred.emit(error_msg)

    def on_param_changed(self):
        """处理参数变更"""
        try:
            self.update_parameters()
            self.log_manager.info("参数已更新")
        except Exception as e:
            error_msg = f"参数更新失败: {str(e)}"
            self.log_manager.error(error_msg)
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

    def on_backtest(self):
        """Run backtest"""
        try:
            # 获取回测参数
            params = {
                'initial_capital': self.backtest_widgets['初始资金'].value(),
                'commission_rate': self.backtest_widgets['手续费率'].value(),
                'slippage': self.backtest_widgets['滑点'].value()
            }

            # 发送数据请求信号
            self.data_requested.emit({
                'type': 'backtest',
                'params': params
            })

            self.log_manager.info("开始回测")

        except Exception as e:
            error_msg = f"回测失败: {str(e)}"
            self.log_manager.error(error_msg)
            self.log_manager.error(traceback.format_exc())
            self.error_occurred.emit(error_msg)

    def on_optimize(self):
        """Optimize parameters"""
        try:
            # 获取优化参数
            strategy = self.strategy_combo.currentText()
            params = {name: control.value()
                      for name, control in self.param_widgets.items()}

            # 发送数据请求信号
            self.data_requested.emit({
                'type': 'optimize',
                'strategy': strategy,
                'params': params
            })

            self.log_manager.info(f"开始优化 - 策略: {strategy}")

        except Exception as e:
            error_msg = f"优化失败: {str(e)}"
            self.log_manager.error(error_msg)
            self.log_manager.error(traceback.format_exc())
            self.error_occurred.emit(error_msg)

    def on_export(self):
        """Export analysis results"""
        try:
            file_path, _ = QFileDialog.getSaveFileName(
                self,
                "导出分析结果",
                "",
                "Excel Files (*.xlsx);;CSV Files (*.csv)"
            )

            if file_path:
                results = {
                    'strategy': self.strategy_combo.currentText(),
                    'parameters': {name: control.value() for name, control in self.param_widgets.items()},
                    'metrics': {name: label.text() for name, label in self.metric_labels.items()}
                }

                if file_path.endswith('.xlsx'):
                    df = pd.DataFrame(results)
                    df.to_excel(file_path, index=False)
                else:
                    df = pd.DataFrame(results)
                    df.to_csv(file_path, index=False)

                QMessageBox.information(self, "成功", "分析结果已导出")

        except Exception as e:
            QMessageBox.critical(self, "错误", f"导出失败: {str(e)}")

    def on_backtest_setting_changed(self):
        """处理回测设置变更"""
        try:
            self.log_manager.info("回测设置已更新")
        except Exception as e:
            error_msg = f"回测设置更新失败: {str(e)}"
            self.log_manager.error(error_msg)
            self.error_occurred.emit(error_msg)

    def update_results(self, results: dict):
        """更新分析结果

        Args:
            results: 分析结果字典，包含性能指标等信息
        """
        try:
            # 更新性能指标
            if 'metrics' in results:
                metrics = results['metrics']
                for name, value in metrics.items():
                    if name in self.performance_metrics:
                        self.performance_metrics[name] = value

                # 更新显示
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
        """更新性能指标显示"""
        try:
            # 检查是否有性能指标标签
            if not hasattr(self, 'metric_labels'):
                self.create_metrics_display()

            # 更新标签显示
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
        """创建性能指标显示区域"""
        try:
            # 创建性能指标组
            metrics_group = QGroupBox("性能指标")
            metrics_layout = QFormLayout(metrics_group)

            # 创建指标标签
            self.metric_labels = {}
            for name in self.performance_metrics.keys():
                label = QLabel("--")
                metrics_layout.addRow(f"{name}:", label)
                self.metric_labels[name] = label

            # 添加到布局
            self.layout().addWidget(metrics_group)

        except Exception as e:
            error_msg = f"创建性能指标显示区域失败: {str(e)}"
            self.log_manager.error(error_msg)
            self.log_manager.error(traceback.format_exc())
            self.error_occurred.emit(error_msg)


class LogPanel(QWidget):
    """Log panel for displaying system logs"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()

    def init_ui(self):
        """Initialize the UI"""
        layout = QVBoxLayout(self)

        # Log controls
        controls_layout = QHBoxLayout()

        # Log level filter
        log_level_label = QLabel("日志级别:")
        self.log_level_combo = QComboBox()
        self.log_level_combo.addItems(["全部", "信息", "警告", "错误"])
        self.log_level_combo.currentTextChanged.connect(self.filter_logs)
        controls_layout.addWidget(log_level_label)
        controls_layout.addWidget(self.log_level_combo)

        # Search box
        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("搜索日志...")
        self.search_box.textChanged.connect(self.search_logs)
        controls_layout.addWidget(self.search_box)

        # Clear button
        clear_button = QPushButton("清除")
        clear_button.clicked.connect(self.clear_logs)
        controls_layout.addWidget(clear_button)

        # Export button
        export_button = QPushButton("导出")
        export_button.clicked.connect(self.export_logs)
        controls_layout.addWidget(export_button)

        layout.addLayout(controls_layout)

        # Log text area
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setLineWrapMode(QTextEdit.NoWrap)
        layout.addWidget(self.log_text)

        self.setLayout(layout)

    def log_message(self, message: str, level: str = "info") -> None:
        """记录日志消息

        Args:
            message: 日志消息
            level: 日志级别
        """
        try:
            # 确保日志管理器存在
            if not hasattr(self, 'log_manager'):
                print(f"[ERROR] 日志管理器未初始化: {message}")
                return

            # 将日志级别转换为大写
            level = level.upper()

            # 使用日志管理器记录日志
            if level == "ERROR":
                self.log_manager.error(message)
            elif level == "WARNING":
                self.log_manager.warning(message)
            elif level == "DEBUG":
                self.log_manager.debug(message)
            else:
                self.log_manager.info(message)

        except Exception as e:
            print(f"记录日志失败: {str(e)}")
            if hasattr(self, 'log_manager'):
                self.log_manager.error(f"记录日志失败: {str(e)}")
                self.log_manager.error(traceback.format_exc())

    def filter_logs(self, level):
        """Filter logs by level"""
        # TODO: Implement log filtering
        pass

    def search_logs(self, text):
        """Search logs"""
        # TODO: Implement log searching
        pass

    def clear_logs(self):
        """Clear all logs"""
        self.log_text.clear()

    def export_logs(self):
        """Export logs to file"""
        try:
            file_path, _ = QFileDialog.getSaveFileName(
                self,
                "导出日志",
                "",
                "Text Files (*.txt);;Log Files (*.log)"
            )

            if file_path:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(self.log_text.toPlainText())

                QMessageBox.information(self, "成功", "日志已导出")

        except Exception as e:
            QMessageBox.critical(self, "错误", f"导出失败: {str(e)}")


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
        self.progress_bar.setVisible(False)
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
