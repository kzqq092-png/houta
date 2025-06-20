"""
基础分析面板模块

包含基础分析面板类，提供通用的分析面板功能
"""

from typing import Optional
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel
from PyQt5.QtCore import pyqtSignal


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

    def __init__(self, parent=None, log_manager=None):
        """初始化基础分析面板

        Args:
            parent: 父控件
            log_manager: 日志管理器
        """
        super().__init__(parent)
        self.log_manager = log_manager
        self.param_widgets = {}
        self.metric_labels = {}

        # 初始化UI
        self.init_base_ui()
        self.init_base_signals()

    @classmethod
    def register_custom_indicator(cls, name: str, func):
        """注册自定义指标

        Args:
            name: 指标名称
            func: 指标函数
        """
        cls._global_custom_indicators[name] = func
        if hasattr(cls, 'log_manager') and cls.log_manager:
            cls.log_manager.info(f"注册自定义指标: {name}")

    @classmethod
    def get_custom_indicator(cls, name: str):
        """获取自定义指标

        Args:
            name: 指标名称

        Returns:
            指标函数或None
        """
        return cls._global_custom_indicators.get(name)

    def emit_custom_signal(self, event: str, data: object):
        """发送自定义信号

        Args:
            event: 事件名称
            data: 事件数据
        """
        self.custom_signal.emit(event, data)

    def connect_custom_signal(self, slot):
        """连接自定义信号

        Args:
            slot: 信号槽函数
        """
        self.custom_signal.connect(slot)

    def init_base_ui(self):
        """初始化基础UI"""
        try:
            # 创建主布局
            self.main_layout = QVBoxLayout(self)

            # 创建控制按钮布局
            self.control_layout = QHBoxLayout()

            # 创建分析按钮
            self.analyze_button = QPushButton("开始分析")
            self.analyze_button.clicked.connect(self.on_base_panel_analyze)
            self.control_layout.addWidget(self.analyze_button)

            # 创建导出按钮
            self.export_button = QPushButton("导出结果")
            self.export_button.clicked.connect(self.on_export)
            self.control_layout.addWidget(self.export_button)

            self.main_layout.addLayout(self.control_layout)

        except Exception as e:
            if self.log_manager:
                self.log_manager.error(f"初始化基础UI失败: {str(e)}")

    def init_base_signals(self):
        """初始化基础信号连接"""
        pass

    def on_base_panel_analyze(self):
        """基础分析按钮点击处理"""
        try:
            # 验证参数
            if not self.validate_params():
                return

            # 设置按钮状态
            self.analyze_button.setEnabled(False)
            self.analyze_button.setText("分析中...")

            # 子类需要重写此方法
            self.perform_analysis()

        except Exception as e:
            error_msg = f"分析失败: {str(e)}"
            if self.log_manager:
                self.log_manager.error(error_msg)
            self.error_occurred.emit(error_msg)
        finally:
            # 恢复按钮状态
            self.analyze_button.setEnabled(True)
            self.analyze_button.setText("开始分析")

    def on_export(self):
        """导出结果"""
        try:
            from PyQt5.QtWidgets import QFileDialog, QMessageBox

            # 选择保存文件
            file_path, _ = QFileDialog.getSaveFileName(
                self,
                "导出分析结果",
                "analysis_result.csv",
                "CSV Files (*.csv);;Excel Files (*.xlsx);;JSON Files (*.json)"
            )

            if file_path:
                # 子类需要重写此方法
                self.export_results(file_path)
                QMessageBox.information(self, "导出成功", f"结果已导出到: {file_path}")

        except Exception as e:
            error_msg = f"导出失败: {str(e)}"
            if self.log_manager:
                self.log_manager.error(error_msg)

            from PyQt5.QtWidgets import QMessageBox
            QMessageBox.critical(self, "导出失败", error_msg)

    def add_param_widget(self, name: str, widget: QWidget):
        """添加参数控件

        Args:
            name: 参数名称
            widget: 控件对象
        """
        self.param_widgets[name] = widget

        # 连接参数变化信号
        if hasattr(widget, 'textChanged'):
            widget.textChanged.connect(self._on_param_widget_changed)
        elif hasattr(widget, 'valueChanged'):
            widget.valueChanged.connect(self._on_param_widget_changed)
        elif hasattr(widget, 'currentTextChanged'):
            widget.currentTextChanged.connect(self._on_param_widget_changed)

    def _on_param_widget_changed(self):
        """参数控件变化处理"""
        # 仅做UI提示，不做业务校验，参数校验统一由子类实现
        pass

    def add_metric_label(self, name: str, label: QLabel):
        """添加指标标签"""
        self.metric_labels[name] = label

    def validate_params(self):
        """验证参数 - 子类需要重写"""
        return True

    def set_status_message(self, message: str, error: bool = False):
        """设置状态消息

        Args:
            message: 消息内容
            error: 是否为错误消息
        """
        try:
            if self.log_manager:
                if error:
                    self.log_manager.error(message)
                else:
                    self.log_manager.info(message)

            # 如果有父窗口的状态栏，更新状态栏
            parent = self.parent()
            while parent:
                if hasattr(parent, 'status_bar') and parent.status_bar:
                    parent.status_bar.set_status(message, error)
                    break
                parent = parent.parent()

        except Exception as e:
            print(f"设置状态消息失败: {str(e)}")

    def __del__(self):
        """析构函数"""
        # 防止QLabel重复删除导致wrapped C/C++ object of type QLabel has been deleted
        try:
            self.param_widgets.clear()
            self.metric_labels.clear()
        except:
            pass

    def perform_analysis(self):
        """执行分析 - 子类需要重写"""
        raise NotImplementedError("子类必须实现perform_analysis方法")

    def export_results(self, file_path: str):
        """导出结果 - 子类需要重写"""
        raise NotImplementedError("子类必须实现export_results方法")
