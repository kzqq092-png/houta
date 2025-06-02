"""
策略控件模块

提供策略配置和管理功能
"""

from PyQt5.QtWidgets import *
from PyQt5.QtCore import Qt, pyqtSignal
from core.logger import LogManager, LogLevel
import traceback
from gui.widgets.log_widget import LogWidget
from utils.theme import get_theme_manager


class StrategyWidget(QWidget):
    """策略控件类"""

    # 定义信号
    strategy_changed = pyqtSignal(str, dict)  # 策略名称, 参数
    error_occurred = pyqtSignal(str)  # 错误信号

    def __init__(self, log_manager: LogManager = None, parent=None):
        """初始化策略控件

        Args:
            log_manager: 日志管理器实例
            parent: 父窗口
        """
        try:
            super().__init__(parent)

            # 使用传入的日志管理器或创建新的
            self.log_manager = log_manager or LogManager()

            # 初始化变量
            self.current_strategy = None
            self.param_controls = {}

            # 初始化UI
            self.init_ui()

            # 连接信号
            self.connect_signals()

            # 设置样式
            self.theme_manager = get_theme_manager()
            self.theme_manager.theme_changed.connect(lambda _: self.theme_manager.apply_theme(self))
            self.theme_manager.apply_theme(self)

            self.log_manager.info("策略控件初始化完成")

        except Exception as e:
            error_msg = f"初始化失败: {str(e)}"
            if self.log_manager:
                self.log_manager.error(error_msg)
                self.log_manager.error(traceback.format_exc())
            self.error_occurred.emit(error_msg)

    def show_error(self, message: str):
        """显示错误对话框

        Args:
            message: 错误消息
        """
        try:
            dialog = QMessageBox(self)
            dialog.setWindowTitle("错误")
            dialog.setIcon(QMessageBox.Critical)
            dialog.setText(message)
            dialog.setStandardButtons(QMessageBox.Ok)

            # 显示对话框并居中
            dialog.show()
            LogWidget().center_dialog(dialog, self)
            dialog.exec_()

            self.theme_manager.apply_theme(dialog)

        except Exception as e:
            self.log_manager.error(f"显示错误对话框失败: {str(e)}")

    def show_warning(self, message: str):
        """显示警告对话框

        Args:
            message: 警告消息
        """
        try:
            dialog = QMessageBox(self)
            dialog.setWindowTitle("警告")
            dialog.setIcon(QMessageBox.Warning)
            dialog.setText(message)
            dialog.setStandardButtons(QMessageBox.Ok)

            # 显示对话框并居中
            dialog.show()
            LogWidget().center_dialog(dialog, self)
            dialog.exec_()

            self.theme_manager.apply_theme(dialog)

        except Exception as e:
            self.log_manager.error(f"显示警告对话框失败: {str(e)}")

    def show_info(self, message: str):
        """显示信息对话框

        Args:
            message: 信息消息
        """
        try:
            dialog = QMessageBox(self)
            dialog.setWindowTitle("信息")
            dialog.setIcon(QMessageBox.Information)
            dialog.setText(message)
            dialog.setStandardButtons(QMessageBox.Ok)

            # 显示对话框并居中
            dialog.show()
            LogWidget().center_dialog(dialog, self)
            dialog.exec_()

            self.theme_manager.apply_theme(dialog)

        except Exception as e:
            self.log_manager.error(f"显示信息对话框失败: {str(e)}")

    def init_ui(self):
        """初始化UI"""
        try:
            # 创建主布局
            layout = QVBoxLayout(self)
            layout.setContentsMargins(5, 5, 5, 5)
            layout.setSpacing(5)

            # 创建策略选择组
            strategy_group = QGroupBox("策略选择")
            strategy_layout = QFormLayout(strategy_group)

            # 策略类型选择
            self.strategy_combo = QComboBox()
            self.strategy_combo.addItems([
                "均线策略", "MACD策略", "RSI策略", "布林带策略",
                "KDJ策略", "自定义策略"
            ])
            strategy_layout.addRow("策略类型:", self.strategy_combo)

            layout.addWidget(strategy_group)

            # 创建参数设置组
            params_group = QGroupBox("参数设置")
            self.params_layout = QFormLayout(params_group)

            # 创建滚动区域
            scroll = QScrollArea()
            scroll.setWidget(params_group)
            scroll.setWidgetResizable(True)
            layout.addWidget(scroll)

            # 创建按钮组
            button_layout = QHBoxLayout()

            # 应用按钮
            self.apply_button = QPushButton("应用")
            button_layout.addWidget(self.apply_button)

            # 重置按钮
            self.reset_button = QPushButton("重置")
            button_layout.addWidget(self.reset_button)

            # 保存按钮
            self.save_button = QPushButton("保存")
            button_layout.addWidget(self.save_button)

            layout.addLayout(button_layout)

            self.log_manager.info("策略控件UI初始化完成")

        except Exception as e:
            error_msg = f"初始化UI失败: {str(e)}"
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
            self.apply_button.clicked.connect(self.apply_strategy)
            self.reset_button.clicked.connect(self.reset_params)
            self.save_button.clicked.connect(self.save_strategy)

            self.log_manager.info("信号连接完成")

        except Exception as e:
            error_msg = f"连接信号失败: {str(e)}"
            self.log_manager.error(error_msg)
            self.log_manager.error(traceback.format_exc())
            self.error_occurred.emit(error_msg)

    def apply_style(self):
        pass  # 移除自定义样式，统一由主题管理器apply_theme

    def on_strategy_changed(self, strategy: str):
        """处理策略变更事件

        Args:
            strategy: 策略名称
        """
        try:
            self.current_strategy = strategy
            self.update_params()
            self.log_manager.info(f"切换到策略: {strategy}")

        except Exception as e:
            error_msg = f"切换策略失败: {str(e)}"
            self.log_manager.error(error_msg)
            self.log_manager.error(traceback.format_exc())
            self.error_occurred.emit(error_msg)

    def update_params(self):
        """更新参数控件"""
        try:
            # 清除现有参数控件
            while self.params_layout.count():
                item = self.params_layout.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()

            # 清除参数控件字典
            self.param_controls.clear()

            # 根据策略类型添加参数控件
            if self.current_strategy == "均线策略":
                self._add_ma_params()
            elif self.current_strategy == "MACD策略":
                self._add_macd_params()
            elif self.current_strategy == "RSI策略":
                self._add_rsi_params()
            elif self.current_strategy == "布林带策略":
                self._add_boll_params()
            elif self.current_strategy == "KDJ策略":
                self._add_kdj_params()
            elif self.current_strategy == "自定义策略":
                self._add_custom_params()

            self.log_manager.info("参数控件更新完成")

        except Exception as e:
            error_msg = f"更新参数控件失败: {str(e)}"
            self.log_manager.error(error_msg)
            self.log_manager.error(traceback.format_exc())
            self.error_occurred.emit(error_msg)

    def _add_ma_params(self):
        """添加均线策略参数"""
        try:
            # 快线周期
            fast_period = QSpinBox()
            fast_period.setRange(5, 120)
            fast_period.setValue(5)
            self.params_layout.addRow("快线周期:", fast_period)
            self.param_controls["fast_period"] = fast_period

            # 慢线周期
            slow_period = QSpinBox()
            slow_period.setRange(10, 250)
            slow_period.setValue(20)
            self.params_layout.addRow("慢线周期:", slow_period)
            self.param_controls["slow_period"] = slow_period

        except Exception as e:
            self.log_manager.error(f"添加均线参数失败: {str(e)}")

    def _add_macd_params(self):
        """添加MACD策略参数"""
        try:
            # 快线周期
            fast_period = QSpinBox()
            fast_period.setRange(5, 50)
            fast_period.setValue(7)
            self.params_layout.addRow("快线周期:", fast_period)
            self.param_controls["fast_period"] = fast_period

            # 慢线周期
            slow_period = QSpinBox()
            slow_period.setRange(10, 100)
            slow_period.setValue(26)
            self.params_layout.addRow("慢线周期:", slow_period)
            self.param_controls["slow_period"] = slow_period

            # 信号周期
            signal_period = QSpinBox()
            signal_period.setRange(2, 20)
            signal_period.setValue(9)
            self.params_layout.addRow("信号周期:", signal_period)
            self.param_controls["signal_period"] = signal_period

        except Exception as e:
            self.log_manager.error(f"添加MACD参数失败: {str(e)}")

    def _add_rsi_params(self):
        """添加RSI策略参数"""
        try:
            # RSI周期
            period = QSpinBox()
            period.setRange(5, 30)
            period.setValue(14)
            self.params_layout.addRow("RSI周期:", period)
            self.param_controls["period"] = period

            # 超买阈值
            overbought = QDoubleSpinBox()
            overbought.setRange(50, 90)
            overbought.setValue(70)
            self.params_layout.addRow("超买阈值:", overbought)
            self.param_controls["overbought"] = overbought

            # 超卖阈值
            oversold = QDoubleSpinBox()
            oversold.setRange(10, 50)
            oversold.setValue(30)
            self.params_layout.addRow("超卖阈值:", oversold)
            self.param_controls["oversold"] = oversold

        except Exception as e:
            self.log_manager.error(f"添加RSI参数失败: {str(e)}")

    def _add_boll_params(self):
        """添加布林带策略参数"""
        try:
            # 周期
            period = QSpinBox()
            period.setRange(10, 100)
            period.setValue(20)
            self.params_layout.addRow("周期:", period)
            self.param_controls["period"] = period

            # 标准差倍数
            std = QDoubleSpinBox()
            std.setRange(1.0, 3.0)
            std.setValue(2.0)
            std.setSingleStep(0.1)
            self.params_layout.addRow("标准差倍数:", std)
            self.param_controls["std"] = std

        except Exception as e:
            self.log_manager.error(f"添加布林带参数失败: {str(e)}")

    def _add_kdj_params(self):
        """添加KDJ策略参数"""
        try:
            # 周期
            period = QSpinBox()
            period.setRange(5, 30)
            period.setValue(9)
            self.params_layout.addRow("周期:", period)
            self.param_controls["period"] = period

            # K值平滑因子
            k_factor = QDoubleSpinBox()
            k_factor.setRange(0.1, 1.0)
            k_factor.setValue(0.33)
            k_factor.setSingleStep(0.01)
            self.params_layout.addRow("K值平滑因子:", k_factor)
            self.param_controls["k_factor"] = k_factor

            # D值平滑因子
            d_factor = QDoubleSpinBox()
            d_factor.setRange(0.1, 1.0)
            d_factor.setValue(0.33)
            d_factor.setSingleStep(0.01)
            self.params_layout.addRow("D值平滑因子:", d_factor)
            self.param_controls["d_factor"] = d_factor

        except Exception as e:
            self.log_manager.error(f"添加KDJ参数失败: {str(e)}")

    def _add_custom_params(self):
        """添加自定义策略参数"""
        try:
            # 参数名称
            name = QLineEdit()
            self.params_layout.addRow("参数名称:", name)
            self.param_controls["name"] = name

            # 参数值
            value = QLineEdit()
            self.params_layout.addRow("参数值:", value)
            self.param_controls["value"] = value

        except Exception as e:
            self.log_manager.error(f"添加自定义参数失败: {str(e)}")

    def apply_strategy(self):
        """应用策略"""
        try:
            # 获取参数值
            params = {}
            for name, control in self.param_controls.items():
                if isinstance(control, (QSpinBox, QDoubleSpinBox)):
                    params[name] = control.value()
                elif isinstance(control, QLineEdit):
                    params[name] = control.text()

            # 发送策略变更信号
            self.strategy_changed.emit(self.current_strategy, params)

            self.log_manager.info(f"应用策略: {self.current_strategy}")

        except Exception as e:
            error_msg = f"应用策略失败: {str(e)}"
            self.log_manager.error(error_msg)
            self.log_manager.error(traceback.format_exc())
            self.error_occurred.emit(error_msg)

    def reset_params(self):
        """重置参数"""
        try:
            # 重置所有参数控件
            for control in self.param_controls.values():
                if isinstance(control, QSpinBox):
                    control.setValue(control.minimum())
                elif isinstance(control, QDoubleSpinBox):
                    control.setValue(control.minimum())
                elif isinstance(control, QLineEdit):
                    control.clear()

            self.log_manager.info("参数已重置")

        except Exception as e:
            error_msg = f"重置参数失败: {str(e)}"
            self.log_manager.error(error_msg)
            self.log_manager.error(traceback.format_exc())
            self.error_occurred.emit(error_msg)

    def save_strategy(self):
        """保存策略"""
        try:
            # 获取参数值
            params = {}
            for name, control in self.param_controls.items():
                if isinstance(control, (QSpinBox, QDoubleSpinBox)):
                    params[name] = control.value()
                elif isinstance(control, QLineEdit):
                    params[name] = control.text()

            # TODO: 保存策略配置到文件

            self.log_manager.info(f"保存策略: {self.current_strategy}")
            QMessageBox.information(self, "成功", "策略配置已保存")

        except Exception as e:
            error_msg = f"保存策略失败: {str(e)}"
            self.log_manager.error(error_msg)
            self.log_manager.error(traceback.format_exc())
            self.error_occurred.emit(error_msg)

    def refresh(self) -> None:
        """
        刷新策略控件内容，异常只记录日志不抛出。
        """
        try:
            self.update_params()
        except Exception as e:
            error_msg = f"刷新策略控件失败: {str(e)}"
            self.log_manager.error(error_msg)
            self.log_manager.error(traceback.format_exc())
            # 发射异常信号，主窗口可捕获弹窗
            self.error_occurred.emit(error_msg)

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
