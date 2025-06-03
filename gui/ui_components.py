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
    QGridLayout, QToolTip, QListWidget, QTableWidget, QTableWidgetItem
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
        # self.setStyleSheet(qss)

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

    def __del__(self):
        # 防止QLabel重复删除导致wrapped C/C++ object of type QLabel has been deleted
        if hasattr(self, 'metric_labels'):
            self.metric_labels.clear()


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
        # 1. 先置空关键属性，防止部分流程未初始化时报错
        self.strategy_combo = None
        self.performance_metrics = {}
        self.backtest_widgets = {}
        self.data_cache = {}
        self.current_strategy = None
        self.default_params = {}
        try:
            # 初始化日志管理器
            if hasattr(parent, 'log_manager'):
                self.log_manager = parent.log_manager
            else:
                from core.logger import LogManager
                self.log_manager = LogManager()

            self.log_manager.info("初始化策略回测UI组件")
            super().__init__(parent)
            # 修正：确保main_layout已初始化
            if not hasattr(self, 'main_layout'):
                self.main_layout = QVBoxLayout(self)
            # 初始化UI
            try:
                self.init_ui()
            except Exception as e:
                self.log_manager.error(f"init_ui异常: {str(e)}")
                self.log_manager.error(traceback.format_exc())
            # 初始化数据
            try:
                self.init_data()
            except Exception as e:
                self.log_manager.error(f"init_data异常: {str(e)}")
                self.log_manager.error(traceback.format_exc())
            # 连接信号
            try:
                self.connect_signals()
            except Exception as e:
                self.log_manager.error(f"connect_signals异常: {str(e)}")
                self.log_manager.error(traceback.format_exc())
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
            self.log_manager.info("初始化策略回测区域")
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
            self.log_manager.info("初始化策略回测数据")
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
            self.log_manager.info("连接策略选择信号")
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
            self.main_layout.addWidget(metrics_group)
        except Exception as e:
            error_msg = f"创建性能指标显示区域失败: {str(e)}"
            self.log_manager.error(error_msg)
            self.log_manager.error(traceback.format_exc())
            self.error_occurred.emit(error_msg)

    def refresh(self) -> None:
        """
        刷新分析工具面板内容，自动刷新回测结果和性能指标。
        """
        try:
            # 重新执行分析和回测（如有方法）
            if hasattr(self, 'on_analyze'):
                self.on_analyze()
            # 刷新性能指标显示
            if hasattr(self, 'update_metrics_display'):
                self.update_metrics_display()
        except Exception as e:
            if hasattr(self, 'log_manager'):
                self.log_manager.error(f"刷新分析工具面板失败: {str(e)}")

    def update(self) -> None:
        """
        兼容旧接口，重定向到refresh。
        """
        self.refresh()

    def reload(self) -> None:
        """
        兼容旧接口，重定向到refresh。
        """
        self.refresh()

    def init_ui(self):
        super().init_ui()
        # 新增批量回测/参数调优Tab
        self.tab_widget = QTabWidget()
        self.tab_widget.addTab(QWidget(), "单次回测")
        self.batch_tab = QWidget()
        batch_layout = QVBoxLayout(self.batch_tab)
        # 股票批量输入
        self.batch_stock_input = QLineEdit()
        self.batch_stock_input.setPlaceholderText("输入多个股票代码，用逗号分隔")
        batch_layout.addWidget(QLabel("批量股票代码："))
        batch_layout.addWidget(self.batch_stock_input)
        # 策略多选
        self.batch_strategy_list = QListWidget()
        self.batch_strategy_list.setSelectionMode(QListWidget.MultiSelection)
        for s in [
            '双均线策略', 'MACD策略', 'KDJ策略', 'RSI策略', 'BOLL策略',
            'CCI策略', 'ATR策略', 'OBV策略', 'WR策略', 'DMI策略',
            'SAR策略', 'ROC策略', 'TRIX策略', 'MFI策略', 'ADX策略',
                'BBW策略', 'AD策略', 'CMO策略', 'DX策略', '自定义策略']:
            self.batch_strategy_list.addItem(s)
        batch_layout.addWidget(QLabel("批量策略选择："))
        batch_layout.addWidget(self.batch_strategy_list)
        # 参数网格设置
        self.param_grid_table = QTableWidget(0, 3)
        self.param_grid_table.setHorizontalHeaderLabels(["参数名", "起始值", "终止值"])
        batch_layout.addWidget(QLabel("参数范围设置（可选）："))
        batch_layout.addWidget(self.param_grid_table)
        # 添加参数行按钮
        add_param_btn = QPushButton("添加参数")
        add_param_btn.clicked.connect(lambda: self.param_grid_table.insertRow(self.param_grid_table.rowCount()))
        batch_layout.addWidget(add_param_btn)
        # 一键批量回测按钮
        self.run_batch_btn = QPushButton("一键批量回测")
        batch_layout.addWidget(self.run_batch_btn)
        # 进度条
        self.batch_progress = QProgressBar()
        batch_layout.addWidget(self.batch_progress)
        # 结果表格
        self.batch_result_table = QTableWidget()
        self.batch_result_table.setColumnCount(12)
        self.batch_result_table.setHorizontalHeaderLabels([
            "股票代码", "策略", "参数组合", "年化收益率", "最大回撤", "夏普比率", "卡玛比率", "索提诺比率", "信息比率", "胜率", "盈亏比", "最优标记"])
        batch_layout.addWidget(self.batch_result_table)
        # 一键导出按钮
        self.export_batch_btn = QPushButton("导出全部回测结果")
        batch_layout.addWidget(self.export_batch_btn)
        self.tab_widget.addTab(self.batch_tab, "批量回测/参数调优")
        self.main_layout.addWidget(self.tab_widget)
        # 信号绑定
        self.run_batch_btn.clicked.connect(self.run_batch_backtest)
        self.export_batch_btn.clicked.connect(self.export_batch_results)
        # 新增AI/智能功能Tab
        self.ai_tab_widget = QTabWidget()
        # 1. AI智能选股Tab
        self.ai_stock_tab = QWidget()
        ai_stock_layout = QVBoxLayout(self.ai_stock_tab)
        self.ai_stock_input = QTextEdit()
        self.ai_stock_input.setPlaceholderText("请输入选股需求或因子描述（如：高ROE、低估值、强势资金流等，或直接用自然语言描述）")
        ai_stock_layout.addWidget(QLabel("AI智能选股（支持自然语言/参数化因子输入）："))
        ai_stock_layout.addWidget(self.ai_stock_input)
        self.ai_stock_run_btn = QPushButton("一键AI选股")
        ai_stock_layout.addWidget(self.ai_stock_run_btn)
        self.ai_stock_result_table = QTableWidget()
        ai_stock_layout.addWidget(self.ai_stock_result_table)
        self.ai_stock_export_btn = QPushButton("导出选股结果")
        ai_stock_layout.addWidget(self.ai_stock_export_btn)
        self.ai_tab_widget.addTab(self.ai_stock_tab, "AI智能选股")
        # 2. AI策略生成Tab
        self.ai_strategy_tab = QWidget()
        ai_strategy_layout = QVBoxLayout(self.ai_strategy_tab)
        self.ai_strategy_input = QTextEdit()
        self.ai_strategy_input.setPlaceholderText("请输入策略描述（如：均线金叉买入，MACD背离等，或直接用自然语言描述）")
        ai_strategy_layout.addWidget(QLabel("AI策略生成（自然语言转策略代码+回测）："))
        ai_strategy_layout.addWidget(self.ai_strategy_input)
        self.ai_strategy_run_btn = QPushButton("一键生成并回测")
        ai_strategy_layout.addWidget(self.ai_strategy_run_btn)
        self.ai_strategy_code = QTextEdit()
        self.ai_strategy_code.setReadOnly(True)
        ai_strategy_layout.addWidget(QLabel("生成的策略代码："))
        ai_strategy_layout.addWidget(self.ai_strategy_code)
        self.ai_strategy_result_table = QTableWidget()
        ai_strategy_layout.addWidget(self.ai_strategy_result_table)
        self.ai_strategy_export_btn = QPushButton("导出回测结果")
        ai_strategy_layout.addWidget(self.ai_strategy_export_btn)
        self.ai_tab_widget.addTab(self.ai_strategy_tab, "AI策略生成")
        # 3. 智能预警Tab
        self.ai_alert_tab = QWidget()
        ai_alert_layout = QVBoxLayout(self.ai_alert_tab)
        self.ai_alert_condition = QTextEdit()
        self.ai_alert_condition.setPlaceholderText("请输入预警条件（如：单日涨跌幅超10%，主力资金异动，热点板块异动等）")
        ai_alert_layout.addWidget(QLabel("智能预警条件设置："))
        ai_alert_layout.addWidget(self.ai_alert_condition)
        self.ai_alert_push_type = QComboBox()
        self.ai_alert_push_type.addItems(["桌面弹窗", "邮件", "微信", "短信"])
        ai_alert_layout.addWidget(QLabel("推送方式："))
        ai_alert_layout.addWidget(self.ai_alert_push_type)
        self.ai_alert_run_btn = QPushButton("启动智能预警")
        ai_alert_layout.addWidget(self.ai_alert_run_btn)
        self.ai_alert_history = QTableWidget()
        ai_alert_layout.addWidget(QLabel("历史预警记录："))
        ai_alert_layout.addWidget(self.ai_alert_history)
        self.ai_tab_widget.addTab(self.ai_alert_tab, "智能预警")
        # 4. 智能报告Tab
        self.ai_report_tab = QWidget()
        ai_report_layout = QVBoxLayout(self.ai_report_tab)
        self.ai_report_object = QLineEdit()
        self.ai_report_object.setPlaceholderText("输入个股/板块/策略名称")
        ai_report_layout.addWidget(QLabel("报告对象："))
        ai_report_layout.addWidget(self.ai_report_object)
        self.ai_report_type = QComboBox()
        self.ai_report_type.addItems(["个股深度分析", "板块深度分析", "策略深度分析"])
        ai_report_layout.addWidget(QLabel("报告类型："))
        ai_report_layout.addWidget(self.ai_report_type)
        self.ai_report_run_btn = QPushButton("一键生成报告")
        ai_report_layout.addWidget(self.ai_report_run_btn)
        self.ai_report_content = QTextEdit()
        self.ai_report_content.setReadOnly(True)
        ai_report_layout.addWidget(QLabel("报告内容预览："))
        ai_report_layout.addWidget(self.ai_report_content)
        self.ai_report_export_btn = QPushButton("导出报告（PDF/Word）")
        ai_report_layout.addWidget(self.ai_report_export_btn)
        self.ai_tab_widget.addTab(self.ai_report_tab, "智能报告")
        # 5. AI助手Tab
        self.ai_assistant_tab = QWidget()
        ai_assistant_layout = QVBoxLayout(self.ai_assistant_tab)
        self.ai_assistant_chat = QTextEdit()
        self.ai_assistant_chat.setPlaceholderText("请输入您的问题、数据分析需求、策略优化等（支持多轮对话）")
        ai_assistant_layout.addWidget(QLabel("AI助手对话区："))
        ai_assistant_layout.addWidget(self.ai_assistant_chat)
        self.ai_assistant_send_btn = QPushButton("发送")
        ai_assistant_layout.addWidget(self.ai_assistant_send_btn)
        self.ai_assistant_response = QTextEdit()
        self.ai_assistant_response.setReadOnly(True)
        ai_assistant_layout.addWidget(QLabel("AI助手回复："))
        ai_assistant_layout.addWidget(self.ai_assistant_response)
        self.ai_tab_widget.addTab(self.ai_assistant_tab, "AI助手")
        # 加入主界面
        self.main_layout.addWidget(self.ai_tab_widget)
        # 新增多模态AI分析Tab
        self.multimodal_tab = QWidget()
        mm_layout = QVBoxLayout(self.multimodal_tab)
        # 图片上传
        self.mm_image_btn = QPushButton("上传图片（K线/财报等）")
        self.mm_image_path = QLineEdit()
        self.mm_image_path.setReadOnly(True)
        mm_layout.addWidget(self.mm_image_btn)
        mm_layout.addWidget(self.mm_image_path)
        # 表格上传
        self.mm_table_btn = QPushButton("上传表格（csv/xlsx）")
        self.mm_table_path = QLineEdit()
        self.mm_table_path.setReadOnly(True)
        mm_layout.addWidget(self.mm_table_btn)
        mm_layout.addWidget(self.mm_table_path)
        # 文本输入
        self.mm_text_input = QTextEdit()
        self.mm_text_input.setPlaceholderText("可选：补充分析说明或问题")
        mm_layout.addWidget(QLabel("补充说明/问题："))
        mm_layout.addWidget(self.mm_text_input)
        # 分析按钮
        self.mm_run_btn = QPushButton("一键多模态AI分析")
        mm_layout.addWidget(self.mm_run_btn)
        # 结果展示
        self.mm_result = QTextEdit()
        self.mm_result.setReadOnly(True)
        mm_layout.addWidget(QLabel("分析结果："))
        mm_layout.addWidget(self.mm_result)
        self.ai_tab_widget.addTab(self.multimodal_tab, "多模态AI分析")
        # 文件选择事件

        def select_image():
            path, _ = QFileDialog.getOpenFileName(self, "选择图片", "", "Images (*.png *.jpg *.jpeg *.bmp)")
            if path:
                self.mm_image_path.setText(path)
        self.mm_image_btn.clicked.connect(select_image)

        def select_table():
            path, _ = QFileDialog.getOpenFileName(self, "选择表格", "", "CSV Files (*.csv);;Excel Files (*.xlsx *.xls)")
            if path:
                self.mm_table_path.setText(path)
        self.mm_table_btn.clicked.connect(select_table)
        # 分析按钮事件

        def run_multimodal():
            from components.ai_multimodal import AIMultimodalAnalyzer
            api_key = self.get_openai_key()
            analyzer = AIMultimodalAnalyzer(api_key)
            image_path = self.mm_image_path.text()
            table_path = self.mm_table_path.text()
            user_input = self.mm_text_input.toPlainText()
            self.mm_run_btn.setEnabled(False)

            def worker():
                res = None
                if image_path:
                    res = analyzer.analyze_image(image_path, user_input)
                elif table_path:
                    res = analyzer.analyze_table(table_path, user_input)
                elif user_input:
                    res = analyzer.analyze_text(user_input)
                else:
                    res = {"error": "请上传图片/表格或输入文本"}
                self.mm_run_btn.setEnabled(True)
                if 'error' in res:
                    QMessageBox.critical(self, "多模态AI分析异常", res['error'])
                    return
                self.mm_result.setPlainText(res.get('result', ''))
            threading.Thread(target=worker, daemon=True).start()
        self.mm_run_btn.clicked.connect(run_multimodal)

        # 新增AI行情解读Tab
        import threading
        self.market_news_tab = QWidget()
        mn_layout = QVBoxLayout(self.market_news_tab)
        # 文本输入
        self.mn_text_input = QTextEdit()
        self.mn_text_input.setPlaceholderText("请输入公告、新闻、行情描述等文本")
        mn_layout.addWidget(QLabel("文本输入："))
        mn_layout.addWidget(self.mn_text_input)
        # URL输入
        self.mn_url_input = QLineEdit()
        self.mn_url_input.setPlaceholderText("可选：输入新闻/公告URL，自动抓取内容")
        mn_layout.addWidget(QLabel("新闻/公告URL："))
        mn_layout.addWidget(self.mn_url_input)
        # 分析按钮
        self.mn_run_btn = QPushButton("一键AI行情解读")
        mn_layout.addWidget(self.mn_run_btn)
        # 结果展示
        self.mn_result = QTextEdit()
        self.mn_result.setReadOnly(True)
        mn_layout.addWidget(QLabel("解读结果："))
        mn_layout.addWidget(self.mn_result)
        self.ai_tab_widget.addTab(self.market_news_tab, "AI行情解读")
        # 分析按钮事件

        def run_market_news():
            from components.ai_market_news import AIMarketNewsAnalyzer
            api_key = self.get_openai_key()
            analyzer = AIMarketNewsAnalyzer(api_key)
            user_input = self.mn_text_input.toPlainText()
            url = self.mn_url_input.text()
            self.mn_run_btn.setEnabled(False)

            def worker():
                res = analyzer.analyze(user_input, url)
                self.mn_run_btn.setEnabled(True)
                if 'error' in res:
                    QMessageBox.critical(self, "AI行情解读异常", res['error'])
                    return
                self.mn_result.setPlainText(res.get('result', ''))
            threading.Thread(target=worker, daemon=True).start()
        self.mn_run_btn.clicked.connect(run_market_news)

        # 新增AI知识图谱Tab
        import threading
        self.kg_tab = QWidget()
        kg_layout = QVBoxLayout(self.kg_tab)
        # 文本输入
        self.kg_text_input = QTextEdit()
        self.kg_text_input.setPlaceholderText("请输入公告、研报、新闻等文本，自动抽取知识图谱")
        kg_layout.addWidget(QLabel("文本输入："))
        kg_layout.addWidget(self.kg_text_input)
        # 构建图谱按钮
        self.kg_build_btn = QPushButton("一键构建知识图谱")
        kg_layout.addWidget(self.kg_build_btn)
        # 三元组展示
        self.kg_triples = QTextEdit()
        self.kg_triples.setReadOnly(True)
        kg_layout.addWidget(QLabel("知识三元组："))
        kg_layout.addWidget(self.kg_triples)
        # 问答输入
        self.kg_qa_input = QLineEdit()
        self.kg_qa_input.setPlaceholderText("请输入与图谱相关的问题，如：主要股东有哪些？")
        kg_layout.addWidget(QLabel("智能问答："))
        kg_layout.addWidget(self.kg_qa_input)
        # 问答按钮
        self.kg_qa_btn = QPushButton("图谱智能问答")
        kg_layout.addWidget(self.kg_qa_btn)
        # 问答结果
        self.kg_qa_result = QTextEdit()
        self.kg_qa_result.setReadOnly(True)
        kg_layout.addWidget(QLabel("问答结果："))
        kg_layout.addWidget(self.kg_qa_result)
        self.ai_tab_widget.addTab(self.kg_tab, "AI知识图谱")
        # 构建图谱事件

        def run_kg_build():
            from components.ai_kg import AIKnowledgeGraph
            api_key = self.get_openai_key()
            kg = AIKnowledgeGraph(api_key)
            text = self.kg_text_input.toPlainText()
            self.kg_build_btn.setEnabled(False)

            def worker():
                res = kg.build_graph(text)
                self.kg_build_btn.setEnabled(True)
                if 'error' in res:
                    QMessageBox.critical(self, "知识图谱构建异常", res['error'])
                    return
                triples = res.get('triples', [])
                self.kg_triples.setPlainText(str(triples))
                self._ai_kg_instance = kg  # 缓存实例供问答用
            threading.Thread(target=worker, daemon=True).start()
        self.kg_build_btn.clicked.connect(run_kg_build)
        # 问答事件

        def run_kg_qa():
            kg = getattr(self, '_ai_kg_instance', None)
            if not kg:
                QMessageBox.warning(self, "请先构建知识图谱", "请先输入文本并构建知识图谱")
                return
            question = self.kg_qa_input.text()
            self.kg_qa_btn.setEnabled(False)

            def worker():
                res = kg.ask(question)
                self.kg_qa_btn.setEnabled(True)
                if 'error' in res:
                    QMessageBox.critical(self, "知识图谱问答异常", res['error'])
                    return
                self.kg_qa_result.setPlainText(res.get('answer', ''))
            threading.Thread(target=worker, daemon=True).start()

        # 新增AI调仓/风控Tab
        import threading
        self.rebalance_tab = QWidget()
        rb_layout = QVBoxLayout(self.rebalance_tab)
        # 持仓表格
        self.rb_table = QTableWidget(0, 4)
        self.rb_table.setHorizontalHeaderLabels(["股票代码", "名称", "持仓数量", "持仓成本"])
        rb_layout.addWidget(QLabel("当前持仓："))
        rb_layout.addWidget(self.rb_table)
        self.rb_add_row_btn = QPushButton("添加持仓行")
        rb_layout.addWidget(self.rb_add_row_btn)

        def add_rb_row():
            self.rb_table.insertRow(self.rb_table.rowCount())
        self.rb_add_row_btn.clicked.connect(add_rb_row)
        # 策略输入
        self.rb_strategy = QLineEdit()
        self.rb_strategy.setPlaceholderText("可选：策略描述，如多因子、趋势等")
        rb_layout.addWidget(QLabel("策略描述："))
        rb_layout.addWidget(self.rb_strategy)
        # 风控参数
        self.rb_risk = QLineEdit()
        self.rb_risk.setPlaceholderText("可选：风控参数，如最大回撤、单股权重上限等")
        rb_layout.addWidget(QLabel("风控参数："))
        rb_layout.addWidget(self.rb_risk)
        # 补充说明
        self.rb_user_input = QLineEdit()
        self.rb_user_input.setPlaceholderText("可选：补充说明")
        rb_layout.addWidget(QLabel("补充说明："))
        rb_layout.addWidget(self.rb_user_input)
        # 一键AI调仓按钮
        self.rb_run_btn = QPushButton("一键AI调仓/风控分析")
        rb_layout.addWidget(self.rb_run_btn)
        # 结果展示
        self.rb_result = QTextEdit()
        self.rb_result.setReadOnly(True)
        rb_layout.addWidget(QLabel("调仓建议与风险分析："))
        rb_layout.addWidget(self.rb_result)
        # 自然语言问答
        self.rb_qa_input = QLineEdit()
        self.rb_qa_input.setPlaceholderText("可直接提问，如：如何优化当前持仓？")
        rb_layout.addWidget(QLabel("自然语言调仓/风控问答："))
        rb_layout.addWidget(self.rb_qa_input)
        self.rb_qa_btn = QPushButton("AI调仓/风控问答")
        rb_layout.addWidget(self.rb_qa_btn)
        self.rb_qa_result = QTextEdit()
        self.rb_qa_result.setReadOnly(True)
        rb_layout.addWidget(QLabel("问答结果："))
        rb_layout.addWidget(self.rb_qa_result)
        self.ai_tab_widget.addTab(self.rebalance_tab, "AI调仓/风控")
        # 一键AI调仓事件

        def run_rebalance():
            from components.ai_rebalance import AIRebalancer
            api_key = self.get_openai_key()
            rebalancer = AIRebalancer(api_key)
            positions = []
            for row in range(self.rb_table.rowCount()):
                code = self.rb_table.item(row, 0).text() if self.rb_table.item(row, 0) else ''
                name = self.rb_table.item(row, 1).text() if self.rb_table.item(row, 1) else ''
                amount = self.rb_table.item(row, 2).text() if self.rb_table.item(row, 2) else ''
                cost = self.rb_table.item(row, 3).text() if self.rb_table.item(row, 3) else ''
                if code:
                    positions.append({"code": code, "name": name, "amount": amount, "cost": cost})
            strategy = self.rb_strategy.text()
            risk_params = self.rb_risk.text()
            user_input = self.rb_user_input.text()
            self.rb_run_btn.setEnabled(False)

            def worker():
                res = rebalancer.rebalance(positions, strategy, risk_params, user_input)
                self.rb_run_btn.setEnabled(True)
                if 'error' in res:
                    QMessageBox.critical(self, "AI调仓/风控异常", res['error'])
                    return
                self.rb_result.setPlainText(res.get('result', ''))
            threading.Thread(target=worker, daemon=True).start()
        self.rb_run_btn.clicked.connect(run_rebalance)
        # AI调仓/风控问答事件

        def run_rb_qa():
            from components.ai_rebalance import AIRebalancer
            api_key = self.get_openai_key()
            rebalancer = AIRebalancer(api_key)
            user_input = self.rb_qa_input.text()
            self.rb_qa_btn.setEnabled(False)

            def worker():
                res = rebalancer.ask(user_input)
                self.rb_qa_btn.setEnabled(True)
                if 'error' in res:
                    QMessageBox.critical(self, "AI调仓/风控问答异常", res['error'])
                    return
                self.rb_qa_result.setPlainText(res.get('result', ''))
            threading.Thread(target=worker, daemon=True).start()
        self.rb_qa_btn.clicked.connect(run_rb_qa)

    def run_batch_backtest(self):
        """一键批量回测，自动遍历参数组合，异步执行，进度实时显示"""
        try:
            codes = [c.strip() for c in self.batch_stock_input.text().split(',') if c.strip()]
            strategies = [item.text() for item in self.batch_strategy_list.selectedItems()]
            param_grid = []
            for row in range(self.param_grid_table.rowCount()):
                pname = self.param_grid_table.item(row, 0)
                pstart = self.param_grid_table.item(row, 1)
                pend = self.param_grid_table.item(row, 2)
                if pname and pstart and pend:
                    param_grid.append((pname.text(), float(pstart.text()), float(pend.text())))
            if not codes or not strategies:
                QMessageBox.warning(self, "参数错误", "请至少输入股票代码和选择策略")
                return
            # 生成参数组合
            from itertools import product
            param_combos = [{}]
            if param_grid:
                param_ranges = [list(range(int(start), int(end)+1)) for _, start, end in param_grid]
                param_names = [name for name, _, _ in param_grid]
                param_combos = [dict(zip(param_names, vals)) for vals in product(*param_ranges)]
            # 进度条设置
            total = len(codes) * len(strategies) * len(param_combos)
            self.batch_progress.setMaximum(total)
            self.batch_progress.setValue(0)
            self.batch_result_table.setRowCount(0)
            import threading
            results = []

            def worker():
                row = 0
                for code in codes:
                    for strategy in strategies:
                        for params in param_combos:
                            try:
                                # 调用后端回测接口
                                from core.trading_system import run_backtest
                                res = run_backtest(code, strategy, params)
                                items = [code, strategy, str(params)]
                                for key in ["annualized_return", "max_drawdown", "sharpe_ratio", "calmar_ratio", "sortino_ratio", "info_ratio", "win_rate", "profit_factor"]:
                                    items.append(f"{res.get(key, '-')}")
                                results.append((items, res))
                                self.batch_result_table.insertRow(row)
                                for col, val in enumerate(items):
                                    self.batch_result_table.setItem(row, col, QTableWidgetItem(str(val)))
                                row += 1
                            except Exception as e:
                                self.batch_result_table.insertRow(row)
                                for col, val in enumerate([code, strategy, str(params)] + ["异常"]*9):
                                    self.batch_result_table.setItem(row, col, QTableWidgetItem(str(val)))
                                row += 1
                            self.batch_progress.setValue(self.batch_progress.value()+1)
                # 最优参数标记
                if results:
                    import numpy as np
                    arr = np.array([float(r[1].get("annualized_return", 0) or 0) for r in results])
                    if len(arr) > 0:
                        best_idx = arr.argmax()
                        self.batch_result_table.setItem(best_idx, 11, QTableWidgetItem("最优"))
            threading.Thread(target=worker, daemon=True).start()
        except Exception as e:
            QMessageBox.critical(self, "批量回测异常", str(e))

    def export_batch_results(self):
        try:
            import pandas as pd
            row_count = self.batch_result_table.rowCount()
            if row_count == 0:
                QMessageBox.warning(self, "无数据", "没有可导出的批量回测结果")
                return
            data = []
            for row in range(row_count):
                data.append([
                    self.batch_result_table.item(row, col).text() if self.batch_result_table.item(row, col) else ''
                    for col in range(self.batch_result_table.columnCount())
                ])
            df = pd.DataFrame(data, columns=["股票代码", "策略", "参数组合", "年化收益率", "最大回撤", "夏普比率", "卡玛比率", "索提诺比率", "信息比率", "胜率", "盈亏比", "最优标记"])
            file_path, _ = QFileDialog.getSaveFileName(self, "导出批量回测结果", "批量回测结果", "Excel Files (*.xlsx);;CSV Files (*.csv)")
            if file_path:
                if file_path.endswith('.xlsx'):
                    df.to_excel(file_path, index=False)
                else:
                    df.to_csv(file_path, index=False)
                QMessageBox.information(self, "导出成功", "批量回测结果已导出")
        except Exception as e:
            QMessageBox.critical(self, "导出失败", f"导出批量回测结果失败: {str(e)}")

    def get_openai_key(self):
        # TODO: 从配置或环境变量安全获取OpenAI API Key
        return "YOUR_OPENAI_API_KEY"


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

    def set_progress(self, value):
        """Set progress bar value, ensure in main thread and value in 0-100, dynamic color"""
        value = max(0, min(100, int(value)))

        def update():
            self.progress_bar.setValue(value)
            # 动态设置颜色
            if value >= 90:
                color = "#FF0000"
            elif value >= 70:
                color = "#FFA500"
            elif value >= 50:
                color = "#FFD700"
            else:
                color = "#4CAF50"
            self.progress_bar.setStyleSheet(f"""
                QProgressBar::chunk {{
                    background-color: {color};
                    border-radius: 4px;
                }}
            """)
        QTimer.singleShot(0, update)

    def set_progress_error(self, message="任务失败"):
        def update():
            self.progress_bar.setStyleSheet("""
                QProgressBar::chunk {
                    background-color: #FF0000;
                    border-radius: 4px;
                }
            """)
            self.status_label.setText(message)
        QTimer.singleShot(0, update)

    def show_progress(self, visible=True):
        self.progress_bar.setVisible(visible)
        if not visible:
            self.set_progress(0)
            self.status_label.setText("就绪")

    def set_status(self, message):
        """Set status message"""
        self.status_label.setText(message)
